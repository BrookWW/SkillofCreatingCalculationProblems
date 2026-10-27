# Contents
# 1. Module setup: imports and scorer loader.
# 2. write_json() and hashed(): frozen fixture helpers.
# 3. ScoreTests: mathematical acceptance, review integrity, and score accounting.
# 4. Test entry point: unittest.main().

"""Check mathematical acceptance, frozen references, and honest score accounting."""

from __future__ import annotations

# Module setup
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
spec = importlib.util.spec_from_file_location("bench_score", SCRIPTS / "score_run.py")
score_run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score_run)


# Fixture helpers
def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def hashed(text):
    return hashlib.sha256(text.encode()).hexdigest()


# ScoreTests: grading and artifact integrity
class ScoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / "bundle"
        self.run = self.bundle / "runs" / "fixture"
        self.run.mkdir(parents=True)

    def fixture(self, answer="2", kind="exact_integer", expected="2", proof=False,
                status="completed", complete=True):
        prompt = "Compute one plus one."
        public = self.bundle / "public" / "task-0001"
        public.mkdir(parents=True, exist_ok=True)
        (public / "prompt.md").write_text(prompt)
        private = {
            "schema_version": 1, "id": "task-0001", "stable_id": "prob:addition",
            "statement_sha256": hashed(prompt), "solution_sha256": hashed("The answer is two."),
            "reference_solution_tex": "The answer is two.",
            "rubric": {
                "review_status": "reviewed", "reference_status": "verified",
                "requirements": ["Compute the exact value."],
                "verification_evidence": ["Integer addition."],
                "answer_type": kind, "accepted_answer": expected,
                "requires_proof": proof,
            },
        }
        private_path = self.bundle / "private" / "task-0001.json"
        write_json(private_path, private)
        task = {
            "id": "task-0001", "stable_id": "prob:addition",
            "statement_sha256": hashed(prompt), "solution_sha256": private["solution_sha256"],
            "public_dir": "public/task-0001", "private_file": "private/task-0001.json",
        }
        attempt = {
            "id": "task-0001", "statement_sha256": hashed(prompt),
            "private_sha256": score_run.digest(private_path), "status": status,
            "submission_file": "attempts/task-0001/final.txt", "elapsed_seconds": 0.5,
        }
        write_json(self.run / attempt["submission_file"], {
            "answer": answer, "derivation": "Integer arithmetic.", "complete": complete,
        })
        attempt["submission_sha256"] = score_run.digest(self.run / attempt["submission_file"])
        write_json(self.bundle / "manifest.json", {
            "schema_version": 1, "benchmark_sha256": "snapshot", "tasks": [task],
        })
        write_json(self.run / "run.json", {
            "schema_version": 1, "run_id": "fixture", "benchmark_sha256": "snapshot",
            "manifest_sha256": score_run.digest(self.bundle / "manifest.json"),
            "model_requested": "fixture-model", "model_reported": None,
            "effort_requested": "high", "effort_reported": None,
            "isolation": "instruction-only", "attempts": [attempt],
        })
        return private, private_path, attempt

    def grade(self, reviews=None):
        score_run.score(self.bundle, self.run, reviews)
        return json.loads((self.run / "grading.json").read_text())

    def freeze_statement_review(self, *, operation="authoring"):
        tools = score_run._statement_review_tools()
        record = json.loads((self.run / "run.json").read_text())
        task = json.loads((self.bundle / "manifest.json").read_text())["tasks"][0]
        public = self.bundle / task["public_dir"]
        write_json(public / "task.json", {"schema_version": 1, "id": task["id"],
                                          "statement_sha256": task["statement_sha256"]})
        current = {key: task[key] for key in tools.BINDINGS if key != "private_sha256"}
        current.update(private_sha256=record["attempts"][0]["private_sha256"],
                       prompt=(public / "prompt.md").read_bytes(),
                       public_bytes=(public / "task.json").read_bytes())
        schema = {"type": "object", "properties": {"answer": {"type": "string"},
                  "derivation": {"type": "string"}, "complete": {"type": "boolean"}},
                  "required": ["answer", "derivation", "complete"], "additionalProperties": False}
        packet = tools.prepare_review(self.bundle, self.root / "external-review", [current],
                                      record["manifest_sha256"], schema)
        review = json.loads((packet.parent / "review-template.json").read_text())
        review["author_agent_id"] = "fixture-author"
        for item in review["reviews"]:
            item["reader"].update(agent_id="fixture-reader", fresh_context=True, status="PASS",
                                  restatement="Return the exact sum of the given integers.")
            item["semantic_check"].update(agent_id="fixture-checker", status="PASS",
                                          meaning_preserved=True, no_solution_hints=True,
                                          evidence={key: "Original and final have identical " + key
                                                    for key in tools.SEMANTIC_FIELDS})
        review_path = packet.parent / "review.json"
        write_json(review_path, review)
        audit = tools.validate_for_run(self.bundle, [current], record["manifest_sha256"], schema, review_path)
        audit_path = self.run / "statement-review.json"
        write_json(audit_path, audit)
        record["attempts"][0].update({key: current[key] for key in tools.BINDINGS})
        record.update(trial_purpose="formal", configuration_evidence={"operation": operation},
                      answer_schema_sha256=tools.schema_hash(schema),
                      statement_review={"required": operation == "authoring", "status": "PASS",
                                        "file": audit_path.name, "sha256": score_run.digest(audit_path)})
        write_json(self.run / "run.json", record)
        return audit_path, packet

    def refreeze_statement_audit(self, path, value):
        tools = score_run._statement_review_tools()
        for name in ("packet", "review"):
            if name == "review":
                value[name]["packet"]["sha256"] = value["packet_sha256"]
            value[name + "_utf8"] = json.dumps(value[name], ensure_ascii=False)
            value[name + "_sha256"] = tools._sha(value[name + "_utf8"].encode("utf-8"))
        write_json(path, value)
        record = json.loads((self.run / "run.json").read_text())
        record["statement_review"]["sha256"] = score_run.digest(path)
        write_json(self.run / "run.json", record)

    def freeze_submission(self, content):
        path = self.run / "attempts/task-0001/final.txt"
        path.write_bytes(content)
        record = json.loads((self.run / "run.json").read_text())
        record["attempts"][0]["submission_sha256"] = score_run.digest(path)
        write_json(self.run / "run.json", record)

    def review(self, *, answer=True, derivation=None):
        attempt = json.loads((self.run / "run.json").read_text())["attempts"][0]
        path = self.root / "reviews.json"
        write_json(path, {"schema_version": 1, "run_id": "fixture", "reviews": [{
            "id": attempt["id"], "statement_sha256": attempt["statement_sha256"],
            "private_sha256": attempt["private_sha256"],
            "submission_sha256": attempt["submission_sha256"],
            "answer_correct": answer, "derivation_correct": derivation,
            "reviewer": "test reviewer", "notes": "Requested mathematical obligations checked.",
        }]})
        return path

    def test_exact_and_non_expression_answers(self):
        self.fixture()
        result = self.grade()
        self.assertEqual(result["tasks"][0]["full_task_status"], "PASS")
        self.fixture(answer="1+1")
        self.assertEqual(self.grade()["tasks"][0]["answer_status"], "FAIL")

    def test_rational_equivalence(self):
        self.fixture(answer="2/6", kind="exact_rational", expected="1/3")
        self.assertEqual(self.grade()["tasks"][0]["answer_status"], "PASS")

    def test_json_object_key_order(self):
        self.fixture(answer='{"b": 2, "a": 1}', kind="exact_json", expected={"a": 1, "b": 2})
        self.assertEqual(self.grade()["tasks"][0]["answer_status"], "PASS")

    def test_duplicate_json_keys_are_not_silently_discarded(self):
        rule = {"answer_type": "exact_json", "accepted_answer": {"x": 2}}
        self.assertFalse(score_run.automatic_answer('{"x": 1, "x": 2}', rule))

    def test_proof_is_not_automatically_accepted(self):
        private, path, attempt = self.fixture(proof=True)
        result = self.grade()["tasks"][0]
        self.assertEqual(result["answer_status"], "PASS")
        self.assertEqual(result["full_task_status"], "REVIEW")
        reviews = self.root / "reviews.json"
        write_json(reviews, {"schema_version": 1, "run_id": "fixture", "reviews": [{
            "id": "task-0001", "statement_sha256": private["statement_sha256"],
            "private_sha256": attempt["private_sha256"], "answer_correct": True,
            "submission_sha256": attempt["submission_sha256"],
            "derivation_correct": True, "reviewer": "test reviewer", "notes": "Exact derivation checked.",
        }]})
        self.assertEqual(self.grade(reviews)["tasks"][0]["full_task_status"], "PASS")

    def test_manual_unknown_remains_review(self):
        self.fixture(answer="an implicit formula", kind="manual", expected=None)
        self.assertEqual(self.grade()["tasks"][0]["answer_status"], "REVIEW")

    def test_stale_gold_rejected(self):
        private, path, _ = self.fixture()
        private["rubric"]["accepted_answer"] = "3"
        write_json(path, private)
        with self.assertRaisesRegex(ValueError, "changed after running"):
            self.grade()

    def test_changed_statement_rejected(self):
        self.fixture()
        (self.bundle / "public/task-0001/prompt.md").write_text("Different problem.")
        with self.assertRaisesRegex(ValueError, "statement changed"):
            self.grade()

    def test_dry_run_not_a_model_result(self):
        self.fixture(status="planned")
        with self.assertRaisesRegex(ValueError, "dry run"):
            self.grade()

    def test_timeout_visible_in_assigned_denominator(self):
        self.fixture(status="timeout")
        result = self.grade()
        self.assertEqual(result["tasks"][0]["full_task_status"], "TIMEOUT")
        self.assertEqual(result["summary"]["confirmed_full_task_pass_fraction"], {"numerator": 0, "denominator": 1})

    def test_token_limit_valid_correct_final_is_graded_with_execution_preserved(self):
        self.fixture(status="token_limit")
        result = self.grade()
        task, = result["tasks"]
        self.assertEqual(task["answer_status"], "PASS")
        self.assertEqual(task["full_task_status"], "PASS")
        self.assertEqual(task["execution_status"], "token_limit")
        self.assertTrue(task["submission_valid"])
        self.assertIs(task["solver_complete"], True)
        self.assertEqual(result["summary"]["execution_counts"], {"token_limit": 1})
        self.assertEqual(result["summary"]["confirmed_answer_pass_fraction"], {"numerator": 1, "denominator": 1})

    def test_token_limit_valid_wrong_final_is_a_mathematical_failure(self):
        self.fixture(status="token_limit", answer="3")
        task, = self.grade()["tasks"]
        self.assertEqual(task["execution_status"], "token_limit")
        self.assertEqual(task["answer_status"], "FAIL")
        self.assertEqual(task["full_task_status"], "FAIL")
        self.assertTrue(task["submission_valid"])

    def test_token_limit_without_valid_final_is_not_a_mathematical_failure(self):
        for content in (b"", b"unfinished", b'{"answer":"2"}',
                        b'{"answer":"2","derivation":"","complete":"true"}',
                        b'{"answer":"2","answer":"3","derivation":"","complete":true}'):
            with self.subTest(content=content):
                self.fixture(status="token_limit")
                self.freeze_submission(content)
                result = self.grade()
                task, = result["tasks"]
                self.assertEqual(task["execution_status"], "token_limit")
                self.assertEqual(task["answer_status"], "TOKEN_LIMIT")
                self.assertEqual(task["full_task_status"], "TOKEN_LIMIT")
                self.assertFalse(task["submission_valid"])
                self.assertIsNone(task["solver_complete"])
                self.assertEqual(result["summary"]["confirmed_answer_pass_fraction"], {"numerator": 0, "denominator": 1})

    def test_valid_manual_token_limit_final_still_needs_answer_review(self):
        self.fixture(status="token_limit", kind="manual", expected=None)
        task, = self.grade()["tasks"]
        self.assertTrue(task["submission_valid"])
        self.assertEqual(task["answer_status"], "REVIEW")
        self.assertEqual(self.grade(self.review())["tasks"][0]["answer_status"], "PASS")

    def test_review_cannot_replace_a_missing_token_limited_final(self):
        self.fixture(status="token_limit", kind="manual", expected=None)
        self.freeze_submission(b"")
        task, = self.grade(self.review())["tasks"]
        self.assertFalse(task["submission_valid"])
        self.assertEqual(task["answer_status"], "TOKEN_LIMIT")
        self.assertEqual(task["full_task_status"], "TOKEN_LIMIT")

    def test_solver_incomplete_flag_does_not_fail_a_correct_calculation(self):
        for status in ("completed", "token_limit"):
            with self.subTest(status=status):
                self.fixture(status=status, complete=False)
                task, = self.grade()["tasks"]
                self.assertIs(task["solver_complete"], False)
                self.assertTrue(task["submission_valid"])
                self.assertEqual(task["answer_status"], "PASS")
                self.assertEqual(task["full_task_status"], "PASS")

    def test_required_proof_depends_on_review_not_solver_complete_flag(self):
        for status in ("completed", "token_limit"):
            with self.subTest(status=status):
                self.fixture(proof=True, complete=False, status=status)
                task, = self.grade()["tasks"]
                self.assertEqual(task["answer_status"], "PASS")
                self.assertEqual(task["full_task_status"], "REVIEW")
                self.assertEqual(self.grade(self.review(derivation=True))["tasks"][0]["full_task_status"], "PASS")
                self.assertEqual(self.grade(self.review(derivation=False))["tasks"][0]["full_task_status"], "FAIL")

    def test_execution_failures_do_not_become_mathematical_results(self):
        for status in ("error", "interrupted", "timeout"):
            with self.subTest(status=status):
                self.fixture(status=status)
                task, = self.grade(self.review())["tasks"]
                expected = "TIMEOUT" if status == "timeout" else "ERROR"
                self.assertEqual(task["answer_status"], expected)
                self.assertEqual(task["full_task_status"], expected)
                self.assertEqual(task["execution_status"], status)
                self.assertTrue(task["submission_valid"])

    def test_configuration_mismatch_and_not_started_cannot_be_graded(self):
        for changes in (
            {"status": "error", "error_kind": "configuration_mismatch"},
            {"configuration_mismatch": {"effort": {"requested": "max", "reported": "high"}}},
            {"status": "error", "command": None, "exit_code": None,
             "error": "Not started: the preceding process failed."},
        ):
            with self.subTest(changes=changes):
                self.fixture()
                path = self.run / "run.json"
                record = json.loads(path.read_text())
                record["attempts"][0].update(changes)
                write_json(path, record)
                task, = self.grade(self.review())["tasks"]
                self.assertEqual(task["answer_status"], "ERROR")
                self.assertEqual(task["full_task_status"], "ERROR")

    def test_report_separates_execution_submission_and_mathematics(self):
        self.fixture(status="token_limit", complete=False)
        self.grade()
        report = (self.run / "report.md").read_text()
        self.assertIn("| Execution | Valid final | Solver complete | Final answer | Full task |", report)
        self.assertIn("| task-0001 | token_limit | true | false | PASS | PASS |", report)

    def test_assessment_and_scoring_preserve_frozen_input_bytes(self):
        for status in ("completed", "token_limit", "error"):
            with self.subTest(status=status):
                self.fixture(status=status, complete=False)
                inputs = [path for path in self.bundle.rglob("*")
                          if path.is_file() and path.name not in {"grading.json", "report.md"}]
                originals = {path: path.read_bytes() for path in inputs}
                score_run.assess(self.bundle, self.run)
                self.grade()
                for path, content in originals.items():
                    self.assertEqual(path.read_bytes(), content, str(path))

    def test_token_limit_does_not_bypass_frozen_input_validation(self):
        for changed in ("prompt", "private", "submission", "manifest"):
            with self.subTest(changed=changed):
                _, private, _ = self.fixture(status="token_limit")
                paths = {
                    "prompt": self.bundle / "public/task-0001/prompt.md",
                    "private": private,
                    "submission": self.run / "attempts/task-0001/final.txt",
                    "manifest": self.bundle / "manifest.json",
                }
                path = paths[changed]
                path.write_text(path.read_text() + "\n")
                with self.assertRaisesRegex(ValueError, "changed"):
                    self.grade()

    def test_report_has_opening_navigation(self):
        self.fixture()
        self.grade()
        report = (self.run / "report.md").read_text()
        self.assertLess(report.index("## Contents"), report.index("## Configuration"))
        for heading in ("Configuration", "Results", "Interpretation"):
            self.assertIn(f"[{heading}](#{heading.lower()})", report)
            self.assertIn(f"## {heading}", report)

    def test_optional_configuration_and_usage_are_preserved_without_inference(self):
        self.fixture(status="token_limit")
        path = self.run / "run.json"
        record = json.loads(path.read_text())
        metadata = {
            "profile": "epoch_tier4_v2",
            "budget": {"total_input_output_tokens_requested": 1000000,
                       "submit_after_tokens_requested": 660000,
                       "native_accounting_verified": False,
                       "forced_submission_enforced": False,
                       "epoch_protocol_match": False},
            "configuration_sha256": "configuration hash",
            "configuration_evidence": {"invocation_id": "current invocation", "answers": ["max"]},
            "wall_seconds": None,
        }
        record.update(metadata)
        record["attempts"][0]["total_input_output_tokens"] = None
        write_json(path, record)
        result = self.grade()
        for key, expected in metadata.items():
            self.assertEqual(result[key], expected)
        self.assertIsNone(result["tasks"][0]["total_input_output_tokens"])
        report = (self.run / "report.md").read_text()
        self.assertIn('"epoch_protocol_match": false', report)
        self.assertIn('"invocation_id": "current invocation"', report)

    def test_recorded_token_usage_is_preserved(self):
        self.fixture()
        path = self.run / "run.json"
        record = json.loads(path.read_text())
        record["attempts"][0]["total_input_output_tokens"] = 123456
        write_json(path, record)
        self.assertEqual(self.grade()["tasks"][0]["total_input_output_tokens"], 123456)

    def test_numeric_requires_explicit_tolerances(self):
        with self.assertRaisesRegex(ValueError, "both tolerances"):
            score_run.automatic_answer("1.01", {"answer_type": "numeric", "accepted_answer": "1"})
        rule = {"answer_type": "numeric", "accepted_answer": "1", "absolute_tolerance": "0.01", "relative_tolerance": "0"}
        self.assertTrue(score_run.automatic_answer("1.005", rule))
        self.assertFalse(score_run.automatic_answer("1.02", rule))
        self.assertFalse(score_run.automatic_answer("NaN", rule))

    def test_manual_review_cannot_change_fixed_answer_rule(self):
        for status in ("completed", "token_limit"):
            with self.subTest(status=status):
                self.fixture(answer="3", status=status)
                with self.assertRaisesRegex(ValueError, "contradicts"):
                    self.grade(self.review(answer=True))

    def test_modified_submission_cannot_reuse_review(self):
        self.fixture(kind="manual", expected=None)
        final = self.run / "attempts/task-0001/final.txt"
        write_json(final, {"answer": "999", "derivation": "wrong", "complete": True})
        with self.assertRaisesRegex(ValueError, "submission changed"):
            self.grade()

    def test_changed_manifest_cannot_change_source_identity(self):
        self.fixture()
        path = self.bundle / "manifest.json"
        data = json.loads(path.read_text())
        data["tasks"][0]["stable_id"] = "prob:different"
        write_json(path, data)
        with self.assertRaisesRegex(ValueError, "manifest changed"):
            self.grade()

    def test_actual_model_and_effort_are_preserved(self):
        self.fixture()
        path = self.run / "run.json"
        data = json.loads(path.read_text())
        data["attempts"][0].update(model_reported="reported-model", effort_reported="reported-effort")
        write_json(path, data)
        result = self.grade()
        self.assertEqual(result["model_reported"], "reported-model")
        self.assertEqual(result["effort_reported"], "reported-effort")

    def test_frozen_statement_review_survives_external_packet_removal(self):
        self.fixture()
        _, packet = self.freeze_statement_review()
        shutil.rmtree(packet.parent)
        result = self.grade()
        self.assertEqual(result["tasks"][0]["full_task_status"], "PASS")
        self.assertEqual(result["trial_purpose"], "formal")
        self.assertEqual(result["statement_review"]["status"], "PASS")
        self.assertIn("answer_schema_sha256", result)

    def test_formal_authoring_requires_complete_passing_frozen_review(self):
        self.fixture()
        audit_path, _ = self.freeze_statement_review()
        original_record = json.loads((self.run / "run.json").read_text())
        original_audit = audit_path.read_bytes()
        for change in ("missing", "false-required", "pending", "error", "missing-file", "stale-hash", "tampered-file"):
            with self.subTest(change=change):
                record = json.loads(json.dumps(original_record))
                audit_path.write_bytes(original_audit)
                if change == "missing":
                    del record["statement_review"]
                elif change == "false-required":
                    record["statement_review"]["required"] = False
                elif change in {"pending", "error"}:
                    record["statement_review"]["status"] = change.upper()
                elif change == "missing-file":
                    audit_path.unlink()
                elif change == "stale-hash":
                    record["statement_review"]["sha256"] = "0" * 64
                else:
                    audit_path.write_text('{"status":"FAIL"}')
                write_json(self.run / "run.json", record)
                with self.assertRaises((ValueError, OSError)):
                    self.grade()

    def test_optional_evaluation_statement_review_is_checked_when_supplied(self):
        self.fixture()
        audit_path, _ = self.freeze_statement_review(operation="evaluation")
        self.assertEqual(self.grade()["tasks"][0]["full_task_status"], "PASS")
        audit_path.write_text(audit_path.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "frozen statement review changed"):
            self.grade()
        record = json.loads((self.run / "run.json").read_text())
        record["statement_review"] = {"required": False, "status": "not-required", "file": None, "sha256": None}
        write_json(self.run / "run.json", record)
        self.assertEqual(self.grade()["tasks"][0]["full_task_status"], "PASS")

    def test_frozen_statement_review_manifest_and_task_bindings_are_checked(self):
        self.fixture()
        audit_path, _ = self.freeze_statement_review()
        original = json.loads(audit_path.read_text())
        for change in ("manifest", "statement_sha256", "solution_sha256", "private_sha256", "answer_schema_sha256"):
            with self.subTest(change=change):
                audit = json.loads(json.dumps(original))
                if change == "manifest":
                    audit["manifest_sha256"] = "0" * 64
                else:
                    audit["tasks"][0][change] = "0" * 64
                self.refreeze_statement_audit(audit_path, audit)
                with self.assertRaisesRegex(ValueError, "manifest|task bindings"):
                    self.grade()

    def test_frozen_statement_review_canonical_schema_must_match_run(self):
        self.fixture()
        audit_path, _ = self.freeze_statement_review()
        original = json.loads(audit_path.read_text())
        for self_consistent in (False, True):
            with self.subTest(self_consistent=self_consistent):
                audit = json.loads(json.dumps(original))
                audit["packet"]["answer_schema"]["additionalProperties"] = True
                if self_consistent:
                    changed_hash = score_run._statement_review_tools().schema_hash(audit["packet"]["answer_schema"])
                    audit["answer_schema_sha256"] = audit["packet"]["answer_schema_sha256"] = changed_hash
                self.refreeze_statement_audit(audit_path, audit)
                with self.assertRaisesRegex(ValueError, "answer interface"):
                    self.grade()

    def test_frozen_current_packet_and_review_baseline_bindings_are_checked(self):
        self.fixture()
        audit_path, _ = self.freeze_statement_review()
        original = json.loads(audit_path.read_text())
        for change in ("current-packet", "baseline-review"):
            with self.subTest(change=change):
                audit = json.loads(json.dumps(original))
                if change == "current-packet":
                    audit["packet"]["tasks"][0]["answer_schema_sha256"] = "0" * 64
                else:
                    audit["review"]["reviews"][0]["baseline_private_sha256"] = "0" * 64
                self.refreeze_statement_audit(audit_path, audit)
                with self.assertRaisesRegex(ValueError, "task bindings|baseline bindings"):
                    self.grade()

    def test_frozen_review_raw_hash_and_parsed_content_are_both_checked(self):
        self.fixture()
        audit_path, _ = self.freeze_statement_review()
        original = json.loads(audit_path.read_text())
        for change in ("raw-hash", "parsed-content"):
            with self.subTest(change=change):
                audit = json.loads(json.dumps(original))
                if change == "raw-hash":
                    audit["review_utf8"] += "\n"
                else:
                    audit["review"]["reviews"][0]["reader"]["restatement"] = "Different task."
                write_json(audit_path, audit)
                record = json.loads((self.run / "run.json").read_text())
                record["statement_review"]["sha256"] = score_run.digest(audit_path)
                write_json(self.run / "run.json", record)
                with self.assertRaisesRegex(ValueError, "stale review hash|inconsistent review content"):
                    self.grade()

    def test_frozen_reader_and_semantic_attestations_must_still_pass(self):
        self.fixture()
        audit_path, _ = self.freeze_statement_review()
        original = json.loads(audit_path.read_text())
        for role in ("reader", "semantic_check"):
            with self.subTest(role=role):
                audit = json.loads(json.dumps(original))
                audit["review"]["reviews"][0][role]["status"] = "PENDING"
                self.refreeze_statement_audit(audit_path, audit)
                with self.assertRaisesRegex(ValueError, "reader has not passed|semantic review has not passed"):
                    self.grade()


# Test entry point
if __name__ == "__main__":
    unittest.main()
