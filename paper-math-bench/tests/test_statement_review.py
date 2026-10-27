"""Exercise immutable review packets and exact-version semantic review gates."""

# Contents: 1. Fixtures; 2. Packet and gate tests; 3. Test entry point.

from __future__ import annotations

from contextlib import redirect_stdout
import copy
import io
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


# 1. Fixtures

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("statement_review_tests", ROOT / "scripts/statement_review.py")
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)
SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}


def digest(data):
    return hashlib.sha256(data).hexdigest()


class StatementReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bundle = self.root / "bundle"
        self.tasks, self.manifest_hash = self.make_bundle(self.bundle)
        self.packet = review.prepare_review(self.bundle, self.root / "review", self.tasks,
                                            self.manifest_hash, SCHEMA)
        self.path = self.passing_review(self.packet)

    def write_json(self, path, value):
        path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")

    def make_bundle(self, bundle, *, statement="Compute $1+1$.", stable_id="prob:one", count=1):
        bundle.mkdir()
        (bundle / "private").mkdir()
        tasks = []
        for index in range(1, count + 1):
            task_id = f"task-{index:04d}"
            public = bundle / "public" / task_id
            public.mkdir(parents=True)
            prompt = statement.encode()
            gold = "The sum is 2."
            private = {"schema_version": 1, "id": task_id, "stable_id": stable_id + str(index),
                       "statement_sha256": digest(prompt), "solution_sha256": digest(gold.encode()),
                       "reference_solution_tex": gold,
                       "rubric": {"review_status": "reviewed", "reference_status": "verified",
                                  "answer_type": "exact_integer", "accepted_answer": "2", "requires_proof": False,
                                  "requirements": ["Return the exact integer sum."],
                                  "verification_evidence": ["Integer addition checked."]}}
            private_path = bundle / "private" / (task_id + ".json")
            self.write_json(private_path, private)
            (public / "prompt.md").write_bytes(prompt)
            public_value = {"schema_version": 1, "id": task_id, "statement_sha256": digest(prompt)}
            self.write_json(public / "task.json", public_value)
            tasks.append({"id": task_id, "stable_id": private["stable_id"],
                          "statement_sha256": private["statement_sha256"],
                          "solution_sha256": private["solution_sha256"],
                          "private_sha256": digest(private_path.read_bytes()), "prompt": prompt,
                          "public_bytes": (public / "task.json").read_bytes()})
        entries = [{key: task[key] for key in review.BINDINGS if key != "private_sha256"} for task in tasks]
        for entry in entries:
            entry.update(public_dir="public/" + entry["id"], private_file="private/" + entry["id"] + ".json")
        manifest_raw = json.dumps({"schema_version": 1, "source_tex": str(self.root / "source.tex"),
                                   "benchmark_sha256": digest(b"source"), "tasks": entries}).encode()
        (bundle / "manifest.json").write_bytes(manifest_raw)
        return tasks, digest(manifest_raw)

    def passing_review(self, packet):
        value = json.loads((packet.parent / "review-template.json").read_text())
        value["author_agent_id"] = "constructor"
        for item in value["reviews"]:
            item["reader"].update(agent_id="independent-reader", fresh_context=True,
                                  status="PASS", restatement="Compute the exact integer sum of the two given units.")
            item["semantic_check"].update(agent_id="mathematical-checker", status="PASS",
                                          meaning_preserved=True, no_solution_hints=True,
                                          evidence={key: "Compared original and final: unchanged " + key
                                                    for key in review.SEMANTIC_FIELDS})
        path = packet.parent / "reviews.json"
        self.write_json(path, value)
        return path

    def validate(self, path=None, tasks=None, manifest_hash=None, schema=None, bundle=None):
        return review.validate_for_run(bundle or self.bundle, tasks or self.tasks,
                                       manifest_hash or self.manifest_hash,
                                       schema or SCHEMA, path or self.path)

    def mutate_review(self, change):
        value = json.loads(self.path.read_text())
        change(value)
        self.write_json(self.path, value)


# 2. Packet and gate tests

    def test_passing_review_freezes_complete_json_serializable_audit(self):
        result = self.validate()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["tasks"][0]["statement_sha256"], self.tasks[0]["statement_sha256"])
        self.assertEqual(result["packet"]["tasks"][0]["original"]["prompt_utf8"], "Compute $1+1$.")
        self.assertIn("reference_solution_tex", result["packet"]["tasks"][0]["original"]["private_json_utf8"])
        frozen = json.loads(json.dumps(result))
        self.assertEqual(digest(frozen["review_utf8"].encode("utf-8")), result["review_sha256"])
        self.assertEqual(digest(frozen["packet_utf8"].encode("utf-8")), result["packet_sha256"])
        self.assertEqual(json.loads(frozen["review_utf8"]), frozen["review"])
        self.assertEqual(json.loads(frozen["packet_utf8"]), frozen["packet"])

    def test_reader_directory_contains_exact_public_inputs_only(self):
        reader = self.packet.parent / "reader/task-0001"
        self.assertEqual({path.name for path in reader.iterdir()}, {"prompt.md", "answer-schema.json"})
        self.assertEqual((reader / "prompt.md").read_bytes(), self.tasks[0]["prompt"])
        self.assertEqual(json.loads((reader / "answer-schema.json").read_text()), SCHEMA)
        self.assertNotIn("The sum is 2.", (reader / "prompt.md").read_text())

    def test_packet_creation_never_overwrites_review_history(self):
        before = self.packet.read_bytes()
        with self.assertRaises(FileExistsError):
            review.prepare_review(self.bundle, self.packet.parent, self.tasks, self.manifest_hash, SCHEMA)
        self.assertEqual(self.packet.read_bytes(), before)

    def test_pending_template_cannot_pass(self):
        with self.assertRaises(ValueError):
            self.validate(path=self.packet.parent / "review-template.json")

    def test_missing_malformed_and_duplicate_review_records_rejected(self):
        with self.assertRaises(ValueError):
            self.validate(path=self.root / "missing.json")
        self.path.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.validate()
        self.path = self.passing_review(self.packet)
        self.mutate_review(lambda x: x["reviews"].append(copy.deepcopy(x["reviews"][0])))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.validate()

    def test_unresolved_reader_issue_and_nonfresh_context_rejected(self):
        for field, value in (("issues", ["The target is ambiguous."]), ("fresh_context", False),
                             ("status", "PENDING"), ("input_scope", "statement-and-solution")):
            with self.subTest(field=field):
                self.path = self.passing_review(self.packet)
                self.mutate_review(lambda x: x["reviews"][0]["reader"].update({field: value}))
                with self.assertRaisesRegex(ValueError, "reader"):
                    self.validate()

    def test_meaning_change_uncertainty_hints_and_missing_evidence_rejected(self):
        for field, value in (("meaning_preserved", False), ("no_solution_hints", False),
                             ("status", "UNCERTAIN"), ("issues", ["A quantifier was weakened."])):
            with self.subTest(field=field):
                self.path = self.passing_review(self.packet)
                self.mutate_review(lambda x: x["reviews"][0]["semantic_check"].update({field: value}))
                with self.assertRaisesRegex(ValueError, "Meaning preservation"):
                    self.validate()
        self.path = self.passing_review(self.packet)
        self.mutate_review(lambda x: x["reviews"][0]["semantic_check"]["evidence"].pop("quantifiers"))
        with self.assertRaisesRegex(ValueError, "quantifiers"):
            self.validate()

    def test_reader_author_and_semantic_checker_must_be_distinct(self):
        for role in ("reader", "semantic_check"):
            self.path = self.passing_review(self.packet)
            self.mutate_review(lambda x: x["reviews"][0][role].update(agent_id="constructor"))
            with self.assertRaisesRegex(ValueError, "distinct"):
                self.validate()
        self.path = self.passing_review(self.packet)
        self.mutate_review(lambda x: x["reviews"][0]["semantic_check"].update(agent_id="independent-reader"))
        with self.assertRaisesRegex(ValueError, "distinct"):
            self.validate()

    def test_stale_statement_private_interface_and_manifest_rejected(self):
        for key in ("statement_sha256", "private_sha256", "solution_sha256", "answer_schema_sha256"):
            with self.subTest(key=key):
                self.path = self.passing_review(self.packet)
                self.mutate_review(lambda x: x["reviews"][0].update({key: "0" * 64}))
                with self.assertRaisesRegex(ValueError, "Stale"):
                    self.validate()
        self.path = self.passing_review(self.packet)
        with self.assertRaisesRegex(ValueError, "answer interface"):
            self.validate(schema={"type": "string"})
        (self.bundle / "manifest.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "manifest"):
            self.validate()

    def test_actual_private_and_public_mutation_after_loading_rejected(self):
        private = self.bundle / "private/task-0001.json"
        private.write_text(private.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "snapshot hash"):
            self.validate()
        self.tasks[0]["private_sha256"] = digest(private.read_bytes())
        (self.bundle / "public/task-0001/prompt.md").write_text("Compute 1+2.")
        with self.assertRaisesRegex(ValueError, "Public review inputs changed"):
            self.validate()

    def test_cross_task_identity_substitution_rejected(self):
        self.mutate_review(lambda x: x["reviews"][0].update(stable_id="prob:other"))
        with self.assertRaisesRegex(ValueError, "stable_id"):
            self.validate()

    def test_revision_keeps_original_baseline_and_reviews_exact_final_prompt(self):
        final_bundle = self.root / "revised-bundle"
        tasks, manifest_hash = self.make_bundle(final_bundle, statement="Calculate $1+1$.")
        packet = review.prepare_review(final_bundle, self.root / "final-review", tasks, manifest_hash,
                                       SCHEMA, baseline_packet=self.packet)
        path = self.passing_review(packet)
        result = self.validate(path=path, tasks=tasks, manifest_hash=manifest_hash, bundle=final_bundle)
        self.assertEqual(result["packet"]["tasks"][0]["original"]["prompt_utf8"], "Compute $1+1$.")
        self.assertEqual(result["packet"]["tasks"][0]["prompt_utf8"], "Calculate $1+1$.")
        self.assertEqual((packet.parent / "reader/task-0001/prompt.md").read_bytes(), tasks[0]["prompt"])
        original = json.loads(self.packet.read_text())
        original["tasks"][0]["prompt_utf8"] = "Changed baseline"
        self.write_json(self.packet, original)
        with self.assertRaisesRegex(ValueError, "snapshot hash"):
            self.validate(path=path, tasks=tasks, manifest_hash=manifest_hash, bundle=final_bundle)

    def test_revision_cannot_substitute_original_or_change_answer_interface(self):
        with self.assertRaisesRegex(ValueError, "answer interface"):
            review.prepare_review(self.bundle, self.root / "other-schema", self.tasks, self.manifest_hash,
                                  {"type": "string"}, baseline_packet=self.packet)
        final_bundle = self.root / "wrong-stable"
        tasks, manifest_hash = self.make_bundle(final_bundle, stable_id="prob:other")
        with self.assertRaisesRegex(ValueError, "Missing original baseline"):
            review.prepare_review(final_bundle, self.root / "wrong-review", tasks, manifest_hash,
                                  SCHEMA, baseline_packet=self.packet)
        self.mutate_review(lambda x: x["reviews"][0].update(baseline_statement_sha256="0" * 64))
        with self.assertRaisesRegex(ValueError, "original baseline"):
            self.validate()

    def test_cli_prepares_and_validates_with_the_runners_actual_answer_schema(self):
        destination = self.root / "cli-review"
        bundle = self.root / "cli-bundle"
        self.make_bundle(bundle)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(review.main(["prepare", str(bundle), str(destination)]), 0)
        packet = destination / "packet.json"
        path = self.passing_review(packet)
        runner = review._runner()
        self.assertEqual(json.loads((destination / "reader/task-0001/answer-schema.json").read_text()),
                         runner.SUBMISSION_SCHEMA)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(review.main(["validate", str(bundle), str(path)]), 0)
        self.assertFalse((bundle / "runs").exists())

    def test_reader_copy_corruption_and_unexpected_private_file_are_rejected(self):
        folder = self.packet.parent / "reader/task-0001"
        prompt = folder / "prompt.md"
        prompt.write_text("Different question.")
        with self.assertRaisesRegex(ValueError, "reader prompt changed"):
            self.validate()
        prompt.write_bytes(self.tasks[0]["prompt"])
        schema = folder / "answer-schema.json"
        self.write_json(schema, {"type": "string"})
        with self.assertRaisesRegex(ValueError, "reader answer interface changed"):
            self.validate()
        self.write_json(schema, SCHEMA)
        (folder / "private-answer.json").write_text('{"answer":2}')
        with self.assertRaisesRegex(ValueError, "Unexpected files"):
            self.validate()

    def test_reader_file_and_directory_symlinks_are_rejected(self):
        folder = self.packet.parent / "reader/task-0001"
        prompt = folder / "prompt.md"
        copy_path = self.root / "prompt-copy.md"
        copy_path.write_bytes(prompt.read_bytes())
        prompt.unlink()
        prompt.symlink_to(copy_path)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            self.validate()
        prompt.unlink()
        prompt.write_bytes(copy_path.read_bytes())
        moved = self.root / "moved-reader"
        folder.rename(moved)
        folder.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            self.validate()

    def test_bundle_origin_cannot_be_reset_by_new_prepare(self):
        marker = review._origin_path(self.bundle, self.tasks[0]["stable_id"])
        original_marker = marker.read_bytes()
        with self.assertRaisesRegex(ValueError, "already pinned"):
            review.prepare_review(self.bundle, self.root / "new-root", self.tasks, self.manifest_hash, SCHEMA)
        # Even an internally consistent replacement cannot silently become the original.
        prompt = b"Compute $1+2$."
        task = self.tasks[0]
        task["prompt"] = prompt
        task["statement_sha256"] = digest(prompt)
        public_dir = self.bundle / "public/task-0001"
        (public_dir / "prompt.md").write_bytes(prompt)
        public = json.loads((public_dir / "task.json").read_text())
        public["statement_sha256"] = digest(prompt)
        self.write_json(public_dir / "task.json", public)
        task["public_bytes"] = (public_dir / "task.json").read_bytes()
        private_path = self.bundle / "private/task-0001.json"
        private = json.loads(private_path.read_text())
        private["statement_sha256"] = digest(prompt)
        self.write_json(private_path, private)
        task["private_sha256"] = digest(private_path.read_bytes())
        manifest = json.loads((self.bundle / "manifest.json").read_text())
        manifest["tasks"][0]["statement_sha256"] = digest(prompt)
        self.write_json(self.bundle / "manifest.json", manifest)
        self.manifest_hash = digest((self.bundle / "manifest.json").read_bytes())
        with self.assertRaisesRegex(ValueError, "already pinned"):
            review.prepare_review(self.bundle, self.root / "edited-root", self.tasks, self.manifest_hash, SCHEMA)
        self.assertEqual(marker.read_bytes(), original_marker)
        packet = review.prepare_review(self.bundle, self.root / "explicit-revision", self.tasks,
                                       self.manifest_hash, SCHEMA, baseline_packet=self.packet)
        value = json.loads(packet.read_text())
        self.assertEqual(value["tasks"][0]["original"]["prompt_utf8"], "Compute $1+1$.")
        self.assertEqual(marker.read_bytes(), original_marker)

    def test_derived_bundle_pins_same_origin_and_rejects_missing_or_conflicting_marker(self):
        final_bundle = self.root / "derived"
        tasks, manifest_hash = self.make_bundle(final_bundle, statement="Calculate $1+1$.")
        packet = review.prepare_review(final_bundle, self.root / "derived-review", tasks, manifest_hash,
                                       SCHEMA, baseline_packet=self.packet)
        path = self.passing_review(packet)
        marker = review._origin_path(final_bundle, tasks[0]["stable_id"])
        original = review._origin_path(self.bundle, self.tasks[0]["stable_id"])
        self.assertEqual(json.loads(marker.read_text()), json.loads(original.read_text()))
        self.validate(path=path, tasks=tasks, manifest_hash=manifest_hash, bundle=final_bundle)
        saved = marker.read_bytes()
        marker.unlink()
        with self.assertRaisesRegex(ValueError, "Missing regular review file"):
            self.validate(path=path, tasks=tasks, manifest_hash=manifest_hash, bundle=final_bundle)
        marker.write_bytes(saved)
        value = json.loads(marker.read_text())
        value["original_sha256"] = "0" * 64
        self.write_json(marker, value)
        with self.assertRaisesRegex(ValueError, "pinned bundle origin"):
            self.validate(path=path, tasks=tasks, manifest_hash=manifest_hash, bundle=final_bundle)

    def test_origin_marker_symlink_is_rejected(self):
        marker = review._origin_path(self.bundle, self.tasks[0]["stable_id"])
        moved = self.root / "moved-origin.json"
        marker.rename(moved)
        marker.symlink_to(moved)
        with self.assertRaisesRegex(ValueError, "Missing regular review file"):
            self.validate()

    def test_subset_review_does_not_require_unselected_tasks_to_be_rereviewed(self):
        bundle = self.root / "two-tasks"
        tasks, manifest_hash = self.make_bundle(bundle, count=2)
        packet = review.prepare_review(bundle, self.root / "two-review", tasks, manifest_hash, SCHEMA)
        path = self.passing_review(packet)
        result = self.validate(path=path, tasks=tasks[:1], manifest_hash=manifest_hash, bundle=bundle)
        self.assertEqual(len(result["tasks"]), 1)
        self.assertEqual(len(result["review"]["reviews"]), 2)


# 3. Test entry point
if __name__ == "__main__":
    unittest.main()
