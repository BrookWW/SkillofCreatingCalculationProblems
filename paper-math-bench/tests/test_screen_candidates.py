"""Check local-pilot tier boundaries, frozen evidence, and immutable reports."""

# Contents: 1. Shared fixtures; 2. Classification policy; 3. Integrity and output.
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import sys
import unittest
import test_score_run as fixtures

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
try:
    spec = importlib.util.spec_from_file_location("bench_screen", SCRIPTS / "screen_candidates.py")
    screening = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(screening)
finally:
    sys.path.pop(0)

# 1. Shared fixtures
class ScreeningTests(unittest.TestCase):
    def setUp(self):
        self.fixture_case = fixtures.ScoreTests()
        self.fixture_case.setUp()
        self.addCleanup(self.fixture_case.doCleanups)
        self.root = self.fixture_case.root.resolve()
        self.bundle = self.fixture_case.bundle.resolve()
        self.run = self.fixture_case.run.resolve()

    def fixture(self, *, total=500000, B=1000000, S=660000, **kwargs):
        result = self.fixture_case.fixture(**kwargs)
        record = json.loads((self.run / "run.json").read_text())
        record.update(status=kwargs.get("status", "completed"), dry_run=False, wall_seconds=300,
                      budget={"total_input_output_tokens_requested": B,
                              "submit_after_tokens_requested": S})
        record["attempts"][0].update(command=["fixture-codex", "exec"], exit_code=0,
                                     total_input_output_tokens=total,
                                     usage=None if total is None else {"input_tokens": total, "output_tokens": 0})
        fixtures.write_json(self.run / "run.json", record)
        return result

    def update_record(self, **values):
        record = json.loads((self.run / "run.json").read_text())
        record.update(values)
        fixtures.write_json(self.run / "run.json", record)

    def update_attempt(self, **values):
        record = json.loads((self.run / "run.json").read_text())
        record["attempts"][0].update(values)
        fixtures.write_json(self.run / "run.json", record)

    def delete_attempt_field(self, key):
        record = json.loads((self.run / "run.json").read_text())
        record["attempts"][0].pop(key, None)
        fixtures.write_json(self.run / "run.json", record)

    def submission(self, value):
        final = self.run / "attempts/task-0001/final.txt"
        if isinstance(value, bytes):
            final.write_bytes(value)
        else:
            fixtures.write_json(final, value)
        self.update_attempt(submission_sha256=screening.score_run.digest(final))

    def reviews(self, *, answer=True, derivation=False, **overrides):
        record = json.loads((self.run / "run.json").read_text())
        attempt = record["attempts"][0]
        review = {"id": attempt["id"], "statement_sha256": attempt["statement_sha256"],
                  "private_sha256": attempt["private_sha256"],
                  "submission_sha256": attempt["submission_sha256"],
                  "answer_correct": answer, "derivation_correct": derivation,
                  "reviewer": "screening test", "notes": "Answer and derivation checked separately.",
                  **overrides}
        path = self.root / "reviews.json"
        fixtures.write_json(path, {"schema_version": 1, "run_id": "fixture", "reviews": [review]})
        return path

    def screen(self, reviews=None):
        path = screening.screen(self.bundle, self.run, reviews)
        self.assertEqual(path.parent, self.run)
        self.assertTrue(path.name.startswith("screening-v2"))
        return json.loads(path.read_text())

    def candidate(self, reviews=None):
        candidate, = self.screen(reviews)["candidates"]
        return candidate

# 2. Classification policy
    def test_diagnostic_record_cannot_supply_final_screening(self):
        self.fixture()
        self.update_record(trial_purpose="diagnostic")
        with self.assertRaisesRegex(ValueError, "diagnostic"):
            self.screen()

    def test_correct_answer_boundaries_S_Splus1_B_Bplus1(self):
        for total, tier in [(660000, "T2"), (660001, "T3"), (1000000, "T3"), (1000001, "T4")]:
            with self.subTest(total=total):
                self.fixture(total=total)
                candidate = self.candidate()
                self.assertEqual(candidate["tier"], tier)
                self.assertEqual(candidate["decision"], "classify")
                self.assertEqual(candidate["reported_full_io"]["U"], total)

    def test_custom_frozen_thresholds_are_used_instead_of_defaults(self):
        self.fixture(total=121, B=200, S=120)
        result = self.screen()
        self.assertEqual(result["candidates"][0]["tier"], "T3")
        self.assertEqual((result["frozen_thresholds"]["B"], result["frozen_thresholds"]["S"]), (200, 120))
        self.assertFalse(result["frozen_thresholds"]["defaults_applied"])

    def test_failed_required_proof_is_T4_even_when_final_value_passes(self):
        self.fixture(proof=True)
        candidate = self.candidate(self.reviews(derivation=False))
        self.assertEqual(candidate["answer_status"], "PASS")
        self.assertEqual(candidate["full_task_status"], "FAIL")
        self.assertEqual(candidate["tier"], "T4")
        self.assertEqual(candidate["reason_code"], "mathematical_fail")

    def test_unreviewed_required_proof_is_pending_even_when_value_passes(self):
        self.fixture(proof=True)
        candidate = self.candidate()
        self.assertEqual(candidate["answer_status"], "PASS")
        self.assertEqual(candidate["full_task_status"], "REVIEW")
        self.assertEqual(candidate["reason_code"], "mathematical_review_pending")

    def test_reviewed_required_proof_full_pass_uses_usage(self):
        self.fixture(proof=True, total=660001)
        candidate = self.candidate(self.reviews(derivation=True))
        self.assertEqual(candidate["full_task_status"], "PASS")
        self.assertEqual(candidate["tier"], "T3")

    def test_known_failed_proof_controls_full_task_even_if_value_is_unreviewed(self):
        for status in ("completed", "token_limit"):
            with self.subTest(status=status):
                self.fixture(proof=True, kind="manual", expected=None, status=status, total=None)
                candidate = self.candidate(self.reviews(answer=None, derivation=False))
                self.assertEqual(candidate["answer_status"], "REVIEW")
                self.assertEqual(candidate["full_task_status"], "FAIL")
                self.assertEqual(candidate["tier"], "T4")

    def test_solver_complete_false_does_not_override_a_correct_value(self):
        self.fixture()
        self.submission({"answer": "2", "derivation": "Arithmetic.", "complete": False})
        candidate = self.candidate()
        self.assertFalse(candidate["solver_complete"])
        self.assertEqual(candidate["answer_status"], "PASS")
        self.assertEqual(candidate["tier"], "T2")

    def test_wrong_valid_answer_is_T4_even_with_unknown_usage_and_thresholds(self):
        self.fixture(answer="3", total=None)
        self.update_record(budget={})
        candidate = self.candidate()
        self.assertTrue(candidate["submission_valid"])
        self.assertEqual(candidate["tier"], "T4")
        self.assertEqual(candidate["reason_code"], "mathematical_fail")
        self.assertIsNone(candidate["reported_full_io"]["U"])

    def test_unreviewed_answer_stays_pending_until_reviewed(self):
        self.fixture(answer="1+1", kind="manual", expected=None)
        self.assertEqual(self.candidate()["reason_code"], "mathematical_review_pending")
        self.assertEqual(self.candidate(self.reviews())["tier"], "T2")

    def test_correct_unknown_usage_stays_pending(self):
        self.fixture(total=None)
        candidate = self.candidate()
        self.assertEqual(candidate["decision"], "pending")
        self.assertEqual(candidate["reason_code"], "reported_usage_unknown")

    def test_explicit_null_usage_is_not_replaced_by_visible_subtotals(self):
        self.fixture(total=None)
        self.update_attempt(usage={"input_tokens": 1, "output_tokens": 2})
        self.assertIsNone(self.candidate()["reported_full_io"]["U"])

    def test_absent_total_can_be_derived_only_from_complete_frozen_usage(self):
        self.fixture()
        self.delete_attempt_field("total_input_output_tokens")
        self.update_attempt(usage=[{"input_tokens": 300000, "output_tokens": 100000,
                                    "cached_input_tokens": 200000, "reasoning_output_tokens": 90000},
                                   {"input_tokens": 100000, "output_tokens": 160001}])
        candidate = self.candidate()
        self.assertEqual(candidate["reported_full_io"]["U"], 660001)
        self.assertIn("attempt.usage", candidate["reported_full_io"]["source"])
        self.assertEqual(candidate["tier"], "T3")
        self.update_attempt(usage=[{"input_tokens": 1, "output_tokens": 1}, None])
        self.assertEqual(self.candidate()["decision"], "pending")

    def test_cached_input_and_reasoning_output_are_not_added_again(self):
        self.fixture(total=600000)
        self.update_attempt(usage={"input_tokens": 500000, "output_tokens": 100000,
                                   "cached_input_tokens": 490000, "reasoning_output_tokens": 90000})
        self.assertEqual(self.candidate()["tier"], "T2")
        self.assertEqual(self.candidate()["reported_full_io"]["U"], 600000)

    def test_invalid_or_conflicting_reported_totals_stay_pending(self):
        for total, code in [(True, "reported_usage_invalid"), (-1, "reported_usage_invalid"),
                            (1.5, "reported_usage_invalid"), (10, "reported_usage_inconsistent")]:
            with self.subTest(total=total):
                self.fixture()
                self.update_attempt(total_input_output_tokens=total)
                self.assertEqual(self.candidate()["reason_code"], code)

    def test_missing_frozen_budget_is_not_filled_from_current_configuration_defaults(self):
        self.fixture()
        self.update_record(budget={}, configuration_evidence={"settings": {
            "total_input_output_tokens": 1000000, "submit_after_tokens": 660000}})
        self.assertEqual(self.candidate()["reason_code"], "frozen_budget_unavailable")

    def test_missing_S_is_pending_below_B_but_unneeded_above_known_B(self):
        self.fixture(total=200)
        self.update_record(budget={"total_input_output_tokens_requested": 1000})
        self.assertEqual(self.candidate()["reason_code"], "frozen_submission_threshold_unavailable")
        self.update_attempt(total_input_output_tokens=1001, usage={"input_tokens": 1001, "output_tokens": 0})
        self.assertEqual(self.candidate()["tier"], "T4")

    def test_invalid_frozen_thresholds_are_not_silently_normalized(self):
        for B, S in [(None, 660000), (True, 1), (-1, 1), (1000000, None),
                     (1000000, True), (1000000, 0), (1000000, 1000000)]:
            with self.subTest(B=B, S=S):
                self.fixture(B=B, S=S)
                self.assertEqual(self.candidate()["decision"], "pending")

    def test_native_exhaustion_without_valid_final_is_T4_not_mathematical_FAIL(self):
        for raw in (b"", b"not JSON", b'{"answer":"2"}'):
            with self.subTest(raw=raw):
                self.fixture(status="token_limit", total=None)
                self.submission(raw)
                candidate = self.candidate()
                self.assertEqual(candidate["answer_status"], "TOKEN_LIMIT")
                self.assertFalse(candidate["submission_valid"])
                self.assertEqual(candidate["tier"], "T4")
                self.assertEqual(candidate["reason_code"], "budget_exhausted_unsolved")
                self.assertIn("not a mathematical FAIL", candidate["reason"])
                self.assertIn("not a mathematical FAIL or proof of full-I/O excess", candidate["reason"])

    def test_valid_correct_token_limit_final_uses_reported_usage_boundaries(self):
        for total, tier in [(660000, "T2"), (660001, "T3"), (1000000, "T3"), (1000001, "T4")]:
            with self.subTest(total=total):
                self.fixture(status="token_limit", total=total)
                candidate = self.candidate()
                self.assertTrue(candidate["submission_valid"])
                self.assertEqual(candidate["execution_status"], "token_limit")
                self.assertEqual(candidate["answer_status"], "PASS")
                self.assertEqual(candidate["tier"], tier)

    def test_valid_correct_token_limit_with_unknown_usage_is_pending(self):
        self.fixture(status="token_limit", total=None)
        self.assertEqual(self.candidate()["reason_code"], "reported_usage_unknown")

    def test_wrong_valid_token_limit_is_mathematical_T4(self):
        self.fixture(status="token_limit", answer="3", total=None)
        self.assertEqual(self.candidate()["reason_code"], "mathematical_fail")

    def test_unreviewed_valid_token_limit_is_pending(self):
        self.fixture(status="token_limit", answer="unknown", kind="manual", expected=None)
        self.assertEqual(self.candidate()["reason_code"], "mathematical_review_pending")

    def test_errors_timeouts_and_interruptions_are_not_hardness(self):
        for status in ("error", "timeout", "interrupted"):
            with self.subTest(status=status):
                self.fixture(status=status)
                self.assertEqual(self.candidate()["decision"], "pending")
                self.assertIsNone(self.candidate()["tier"])

    def test_configuration_mismatch_cannot_be_overridden_by_correct_or_wrong_final(self):
        for answer in ("2", "3"):
            with self.subTest(answer=answer):
                self.fixture(answer=answer)
                self.update_attempt(configuration_mismatch={"model": "different"}, error_kind="configuration_mismatch")
                candidate = self.candidate()
                self.assertEqual(candidate["decision"], "pending")
                self.assertEqual(candidate["reason_code"], "configuration_mismatch")

    def test_not_started_error_stays_pending(self):
        self.fixture(status="error")
        self.submission(b"")
        self.update_attempt(command=None, exit_code=None, error="Not started: prior process failed.")
        self.assertEqual(self.candidate()["reason_code"], "attempt_not_started")

    def test_malformed_completed_final_is_not_mathematical_FAIL(self):
        self.fixture()
        self.submission(b"partial output")
        candidate = self.candidate()
        self.assertEqual(candidate["decision"], "pending")
        self.assertEqual(candidate["answer_status"], "REVIEW")

# 3. Integrity and immutable output
    def test_formal_authoring_checks_frozen_statement_review_before_classification(self):
        self.fixture()
        audit_path, _ = self.fixture_case.freeze_statement_review()
        result = self.screen()
        self.assertEqual(result["candidates"][0]["tier"], "T2")
        self.assertEqual(result["trial_purpose"], "formal")
        self.assertEqual(result["statement_review"]["status"], "PASS")
        audit_path.write_text('{"status":"FAIL"}')
        with self.assertRaisesRegex(ValueError, "frozen statement review changed"):
            self.screen()

    def test_formal_authoring_missing_frozen_statement_review_cannot_classify(self):
        self.fixture()
        audit_path, _ = self.fixture_case.freeze_statement_review()
        audit_path.unlink()
        with self.assertRaises((ValueError, OSError)):
            self.screen()

    def test_changed_frozen_inputs_and_stale_reviews_are_rejected(self):
        for changed in ("prompt", "private", "submission", "manifest"):
            with self.subTest(changed=changed):
                _, private, _ = self.fixture()
                path = {"prompt": self.bundle / "public/task-0001/prompt.md", "private": private,
                        "submission": self.run / "attempts/task-0001/final.txt",
                        "manifest": self.bundle / "manifest.json"}[changed]
                path.write_text(path.read_text() + "\n")
                with self.assertRaisesRegex(ValueError, "changed"):
                    self.screen()
        self.fixture(kind="manual", expected=None)
        for field in ("statement_sha256", "private_sha256", "submission_sha256"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "Review"):
                    self.screen(self.reviews(**{field: "stale"}))

    def test_noncompleted_final_still_has_frozen_hash_validation(self):
        for status in ("token_limit", "error", "timeout", "interrupted"):
            with self.subTest(status=status):
                self.fixture(status=status)
                final = self.run / "attempts/task-0001/final.txt"
                final.write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "frozen submission changed"):
                    self.screen()

    def test_schema_metadata_hashes_and_accounting_scope_are_preserved(self):
        self.fixture()
        self.update_record(configuration_sha256="configuration hash", configuration_evidence={"invocation_id": "fixture"})
        reviews = self.reviews()
        result = self.screen(reviews)
        record = json.loads((self.run / "run.json").read_text())
        candidate = result["candidates"][0]
        self.assertEqual((result["schema_version"], result["policy"], result["policy_version"]),
                         (2, "local_pilot_tiers", 1))
        self.assertEqual(result["summary"], {"assigned": 1, "classified": 1, "pending": 0,
                                            "tier_counts": {"T2": 1, "T3": 0, "T4": 0}})
        self.assertEqual(result["run_sha256"], screening.score_run.digest(self.run / "run.json"))
        self.assertEqual(result["reviews_sha256"], screening.score_run.digest(reviews))
        for key in ("manifest_sha256", "benchmark_sha256", "budget", "configuration_sha256", "configuration_evidence"):
            self.assertEqual(result[key], record[key])
        for key in ("private_sha256", "submission_sha256"):
            self.assertEqual(candidate[key], record["attempts"][0][key])
        self.assertIn("Coverage of failed or retried", result["measurement_scope"])
        self.assertIn("complete account billing is unverified", result["measurement_scope"])
        self.assertEqual(result["usage_scope"]["failed_or_retried_request_coverage"], "unverified")
        self.assertEqual(result["usage_scope"]["complete_account_billing_coverage"], "unverified")

    def test_recorded_usage_scope_is_preserved_without_certifying_coverage(self):
        self.fixture()
        self.update_record(usage_scope="reported responses", usage_coverage={"failed_requests": "unknown"})
        self.update_attempt(usage_scope="solver only", usage_coverage={"retries": "unverified"})
        result = self.screen()
        self.assertEqual(result["usage_scope"]["recorded_run_scope"], "reported responses")
        self.assertEqual(result["usage_scope"]["recorded_run_coverage"], {"failed_requests": "unknown"})
        self.assertEqual(result["candidates"][0]["recorded_usage_scope"], "solver only")
        self.assertEqual(result["candidates"][0]["recorded_usage_coverage"], {"retries": "unverified"})

    def test_existing_legacy_and_raw_reports_are_preserved(self):
        self.fixture()
        fixtures.write_json(self.run / "screening.json", {"schema_version": 1, "policy": "discard_answer_pass"})
        fixtures.write_json(self.run / "grading.json", {"external_annotation": "keep"})
        (self.run / "report.md").write_text("Additional mathematical commentary.\n")
        originals = {path: path.read_bytes() for path in self.bundle.rglob("*") if path.is_file()}
        path = screening.screen(self.bundle, self.run)
        self.assertEqual(path, self.run / "screening-v2.json")
        for p, expected in originals.items():
            self.assertEqual(p.read_bytes(), expected, str(p))

    def test_identical_payload_is_idempotent_and_changed_payload_gets_hash_suffix(self):
        self.fixture(kind="manual", expected=None)
        first = screening.screen(self.bundle, self.run)
        original = first.read_bytes()
        self.assertEqual(screening.screen(self.bundle, self.run), first)
        second = screening.screen(self.bundle, self.run, self.reviews())
        self.assertNotEqual(first, second)
        self.assertEqual(first.read_bytes(), original)
        self.assertEqual(second.name, "screening-v2-" + screening.hashlib.sha256(second.read_bytes()).hexdigest() + ".json")
        self.assertEqual(screening.screen(self.bundle, self.run, self.reviews()), second)

    def test_dry_runs_and_unfinished_runs_cannot_classify(self):
        for values in ({"status": "planned"}, {"dry_run": True}, {"status": "running"}):
            with self.subTest(values=values):
                self.fixture()
                self.update_record(**values)
                with self.assertRaisesRegex(ValueError, "dry run|finished run"):
                    self.screen()
        self.fixture(status="planned")
        self.update_record(status="completed")
        with self.assertRaisesRegex(ValueError, "every assigned attempt"):
            self.screen()

    def test_run_id_interface_returns_actual_versioned_path(self):
        self.fixture()
        self.assertEqual(screening.screen(self.bundle, "fixture"), self.run / "screening-v2.json")


if __name__ == "__main__":
    unittest.main()
