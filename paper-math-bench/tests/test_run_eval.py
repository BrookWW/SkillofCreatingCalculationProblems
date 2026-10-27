# Contents
# 1. Module setup: imports and runner loader.
# 2. digest(): fixture hashing.
# 3. RunnerTests: fake executions, configuration, validation, and process cleanup.
# 4. Test entry point: unittest.main().

"""Exercise the runner with local fake executables and synthetic bundles."""

from __future__ import annotations

# Module setup
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
SPEC = importlib.util.spec_from_file_location("paper_math_bench_run_eval", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


# Hashing helper
def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# RunnerTests: execution and lifecycle checks
class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="test-paper-math-runner-")
        self.root = Path(self.temporary.name)
        self.bundle = self.root / "bundle"
        self.bundle.mkdir()
        self.make_bundle()

    def tearDown(self):
        self.temporary.cleanup()

    def write_json(self, path: Path, value):
        path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")

    def make_bundle(self, count=1, reviewed=True):
        tasks = []
        for index in range(1, count + 1):
            task_id = f"task-{index:04d}"
            public = self.bundle / "public" / task_id
            public.mkdir(parents=True, exist_ok=True)
            private = self.bundle / "private"
            private.mkdir(exist_ok=True)
            prompt = f"Find {index} + 1. Return answer, derivation, complete as JSON.\n".encode()
            solution = f"The answer is {index + 1}."
            statement_hash = digest(prompt)
            solution_hash = digest(solution.encode())
            (public / "prompt.md").write_bytes(prompt)
            self.write_json(public / "task.json", {
                "schema_version": 1, "id": task_id, "statement_sha256": statement_hash,
            })
            self.write_json(private / f"{task_id}.json", {
                "schema_version": 1, "id": task_id, "stable_id": f"exercise-{index}",
                "statement_sha256": statement_hash, "solution_sha256": solution_hash,
                "reference_solution_tex": solution,
                "rubric": {
                    "review_status": "reviewed" if reviewed else "unreviewed",
                    "reference_status": "verified" if reviewed else "unverified",
                    "answer_type": "exact_integer", "accepted_answer": str(index + 1),
                    "requires_proof": False,
                    "requirements": ["Return the sum."] if reviewed else [],
                    "verification_evidence": ["Integer addition checked."] if reviewed else [],
                },
            })
            tasks.append({
                "id": task_id, "stable_id": f"exercise-{index}",
                "statement_sha256": statement_hash, "solution_sha256": solution_hash,
                "public_dir": f"public/{task_id}", "private_file": f"private/{task_id}.json",
            })
        self.write_json(self.bundle / "manifest.json", {
            "schema_version": 1, "source_tex": str(self.root / "moved-source.tex"),
            "benchmark_sha256": digest(b"original source"), "tasks": tasks,
        })

    def fake_codex(self, mode="success") -> str:
        executable = self.root / "fake-codex"
        executable.write_text(f"#!{sys.executable}\n" + r'''
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time

root = pathlib.Path(__file__).resolve().parent
mode = MODE
args = sys.argv[1:]
with (root / "calls.jsonl").open("a") as stream:
    stream.write(json.dumps(args) + "\n")
with tempfile.TemporaryDirectory(prefix="fake-child-") as child_temp:
    (pathlib.Path(child_temp) / "child-temp.txt").write_text("temporary")
    with (root / "environment-snapshots.jsonl").open("a") as stream:
        stream.write(json.dumps({
            "args": args, "temporary": child_temp,
            "environment": {key: os.environ.get(key) for key in ("TMPDIR", "TMP", "TEMP")},
        }) + "\n")
if args == ["--version"]:
    print("fake-codex 1.0")
    raise SystemExit(0)
if args[-2:] == ["features", "list"]:
    if mode == "no_budget":
        print("unsupported rollout budget", file=sys.stderr)
        raise SystemExit(2)
    print("rollout_budget under development true")
    raise SystemExit(0)
if mode == "unsupported":
    print("error: unsupported configuration features.plugins", file=sys.stderr)
    raise SystemExit(2)
workspace = pathlib.Path(args[args.index("--cd") + 1])
schema = pathlib.Path(args[args.index("--output-schema") + 1])
final = pathlib.Path(args[args.index("--output-last-message") + 1])
prompt = sys.stdin.read()
# macOS can add AppleDouble companions for the two public input files.
snapshot = {
    "files": sorted(path.name for path in workspace.iterdir()
                    if path.name not in {"._prompt.md", "._task.json"}),
    "public_file_sidecars": sorted(path.name for path in workspace.iterdir()
                                   if path.name in {"._prompt.md", "._task.json"}),
    "cwd": str(pathlib.Path.cwd()), "workspace": str(workspace),
    "prompt": prompt, "prompt_file": (workspace / "prompt.md").read_text(),
    "task": json.loads((workspace / "task.json").read_text()),
    "schema": json.loads(schema.read_text()), "schema_path": str(schema),
}
with (root / "snapshots.jsonl").open("a") as stream:
    stream.write(json.dumps(snapshot) + "\n")
if mode == "timeout_partial":
    final.write_text('{"answer":"partial"')
    print(json.dumps({"type": "thread.started", "thread_id": "fake"}), flush=True)
    time.sleep(30)
if mode in {"timeout", "interrupt"}:
    child_code = "import pathlib,time; time.sleep(1); pathlib.Path(" + repr(str(root / "child-survived")) + ").write_text('alive')"
    child = subprocess.Popen([sys.executable, "-c", child_code])
    (root / "child.pid").write_text(str(child.pid))
    print(json.dumps({"type": "thread.started", "thread_id": "fake"}), flush=True)
    (root / "ready").write_text("ready")
    time.sleep(30)
if mode == "failure":
    print(json.dumps({"type": "turn.failed", "error": {"message": "fake failure"}}))
    print("failure details", file=sys.stderr)
    raise SystemExit(7)
if mode == "token_limit":
    print(json.dumps({"type":"turn.failed", "error":{"codex_error_info":"sessionBudgetExceeded", "message":"shared rollout token budget exhausted"}}))
    raise SystemExit(1)
if mode == "bad_submission":
    final.write_text('{"answer": 2}')
elif mode == "malformed_event":
    final.write_text(json.dumps({"answer": "2", "derivation": "1+1=2", "complete": True}))
    print("not a JSON event")
else:
    final.write_text(json.dumps({"answer": "2", "derivation": "1+1=2", "complete": True}))
if mode == "reported":
    print(json.dumps({"type": "session.started", "session": {"model": "reported-model", "reasoning_effort": "reported-effort"}}))
if mode == "effort_downgrade":
    print(json.dumps({"type": "session.started", "session": {"model": args[args.index("--model") + 1], "reasoning_effort": "high"}}))
if mode == "model_substitution":
    print(json.dumps({"type": "session.started", "session": {"model": "gpt-6-sol", "reasoning_effort": "max"}}))
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 12, "cached_input_tokens": 3, "output_tokens": 5}}))
'''.replace("MODE", repr(mode)), encoding="utf-8")
        executable.chmod(0o700)
        return str(executable)

    def configuration(self, *, model="explicit-test-model", effort="explicit-test-effort",
                      wall_seconds=2, profile="local-pilot", ids=None):
        manifest = json.loads((self.bundle / "manifest.json").read_text())
        now = datetime.now(timezone.utc)
        settings = {"profile": profile, "model": model, "effort": effort, "wall_seconds": wall_seconds}
        if profile == "epoch-tier4-v2":
            settings.update(total_input_output_tokens=1000000, submit_after_tokens=660000)
        value = {
            "schema_version": 1, "invocation_id": "current-test-operation", "operation": "evaluation",
            "invocation_started_at": (now - timedelta(seconds=2)).isoformat(), "created_at": now.isoformat(),
            "binding": {"bundle": str(self.bundle.resolve()), "manifest_sha256": digest((self.bundle / "manifest.json").read_bytes()),
                        "benchmark_sha256": manifest["benchmark_sha256"],
                        "task_ids": [task["id"] for task in manifest["tasks"] if ids is None or task["id"] in ids]},
            "qa": [{"question": "Select this test profile?", "answer": "Use the fixture configuration.",
                    "user_reply_ref": "test-fixture-reply", "answered_at": (now - timedelta(seconds=1)).isoformat()}],
            "settings": settings, "acknowledge_cli_differences": True,
        }
        path = self.root / "configuration.json"
        self.write_json(path, value)
        return path

    def run_bundle(self, **kwargs):
        options = {
            "model": "explicit-test-model", "effort": "explicit-test-effort",
            "wall_seconds": 2, "isolation": "instruction-only",
            "profile": "local-pilot", "invocation_id": "current-test-operation",
        }
        options.update(kwargs)
        if "configuration" not in options:
            options["configuration"] = self.configuration(**{
                key: options[key] for key in ("model", "effort", "wall_seconds", "profile")
            }, ids=options.get("ids"))
        if "codex" not in options:
            options["codex"] = self.fake_codex()
        result = runner.run_bundle(self.bundle, **options)
        return result, json.loads((result / "run.json").read_text())

    def test_success_records_explicit_configuration_and_only_copies_public_files(self):
        (self.bundle / "public" / "task-0001" / "secret.txt").write_text("do not copy")
        private_hash = digest((self.bundle / "private" / "task-0001.json").read_bytes())
        run_dir, record = self.run_bundle()
        self.assertEqual(record["status"], "completed")
        self.assertFalse(record["strict_blind"])
        self.assertFalse(record["network_enforced"])
        self.assertEqual(record["cli_version"], "fake-codex 1.0")
        self.assertEqual(record["benchmark_sha256"], digest(b"original source"))
        attempt, = record["attempts"]
        self.assertEqual(attempt["status"], "completed")
        self.assertEqual(attempt["private_sha256"], private_hash)
        self.assertEqual(attempt["submission_sha256"], digest((run_dir / attempt["submission_file"]).read_bytes()))
        self.assertEqual(attempt["exit_code"], 0)
        self.assertGreater(attempt["elapsed_seconds"], 0)
        self.assertEqual(attempt["model_requested"], "explicit-test-model")
        self.assertEqual(attempt["effort_requested"], "explicit-test-effort")
        self.assertIsNone(attempt["model_reported"])
        self.assertIsNone(attempt["effort_reported"])
        self.assertEqual(attempt["usage"], {"input_tokens": 12, "cached_input_tokens": 3, "output_tokens": 5})
        command = attempt["command"]
        self.assertEqual(command[command.index("--model") + 1], "explicit-test-model")
        self.assertIn('model_reasoning_effort="explicit-test-effort"', command)
        for argument in ("--ignore-user-config", "--ephemeral", "--json", "--skip-git-repo-check"):
            self.assertIn(argument, command)
        self.assertEqual(command[command.index("--sandbox") + 1], "workspace-write")
        self.assertIn('approval_policy="never"', command)
        self.assertIn('web_search="disabled"', command)
        self.assertIn("sandbox_workspace_write.network_access=false", command)
        self.assertIn("project_doc_max_bytes=0", command)
        self.assertNotIn("--ignore-rules", command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)
        snapshot, = [json.loads(line) for line in (self.root / "snapshots.jsonl").read_text().splitlines()]
        self.assertEqual(snapshot["files"], ["prompt.md", "task.json"])
        self.assertEqual(snapshot["prompt"], snapshot["prompt_file"])
        self.assertEqual(snapshot["cwd"], snapshot["workspace"])
        self.assertFalse(Path(snapshot["workspace"]).is_relative_to(self.bundle))
        self.assertFalse(Path(snapshot["schema_path"]).is_relative_to(Path(snapshot["workspace"])))
        self.assertEqual(snapshot["schema"], runner.SUBMISSION_SCHEMA)
        self.assertFalse(Path(snapshot["workspace"]).exists())
        for key in ("submission_file", "events_file", "stderr_file"):
            self.assertFalse(Path(attempt[key]).is_absolute())
            self.assertTrue((run_dir / attempt[key]).is_file())
        self.assertNotIn("cost", record)

    def authoring_configuration(self):
        path = self.configuration()
        value = json.loads(path.read_text())
        value["operation"] = "authoring"
        self.write_json(path, value)
        return path

    def passing_statement_reviews(self):
        gate = runner._statement_reviewer()
        _, tasks, manifest_hash = runner._load_bundle(self.bundle.resolve(), None, reviewed=True)
        packet = gate.prepare_review(self.bundle, self.root / "statement-review", tasks,
                                     manifest_hash, runner.SUBMISSION_SCHEMA)
        value = json.loads((packet.parent / "review-template.json").read_text())
        value["author_agent_id"] = "fixture-author"
        for item in value["reviews"]:
            item["reader"].update(agent_id="fixture-reader", fresh_context=True, status="PASS",
                                  restatement="Return the exact integer sum of the given integers.")
            item["semantic_check"].update(
                agent_id="fixture-semantic-checker", status="PASS", meaning_preserved=True,
                no_solution_hints=True,
                evidence={key: "Original and final have identical " + key for key in gate.SEMANTIC_FIELDS},
            )
        path = packet.parent / "reviews.json"
        self.write_json(path, value)
        return path

    def test_formal_authoring_without_review_stops_before_any_cli_call(self):
        with self.assertRaisesRegex(runner.BundleError, "require --statement-reviews"):
            self.run_bundle(configuration=self.authoring_configuration())
        self.assertFalse((self.root / "calls.jsonl").exists())
        self.assertFalse((self.bundle / "runs").exists())

    def test_authoring_dry_run_records_pending_review_without_calling_a_model(self):
        _, record = self.run_bundle(configuration=self.authoring_configuration(), dry_run=True)
        self.assertEqual(record["status"], "planned")
        self.assertEqual(record["statement_review"]["status"], "pending")
        self.assertTrue(record["statement_review"]["required"])
        self.assertFalse((self.root / "calls.jsonl").exists())

    def test_authoring_diagnostic_does_not_trigger_the_final_statement_gate(self):
        _, record = self.run_bundle(configuration=self.authoring_configuration(), trial_purpose="diagnostic")
        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["trial_purpose"], "diagnostic")
        self.assertEqual(record["statement_review"]["status"], "not-required")

    def test_formal_authoring_freezes_review_audit_but_exposes_only_public_solver_inputs(self):
        reviews = self.passing_statement_reviews()
        run_dir, record = self.run_bundle(configuration=self.authoring_configuration(),
                                          statement_reviews=reviews)
        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["trial_purpose"], "formal")
        audit = record["statement_review"]
        self.assertTrue(audit["required"])
        self.assertEqual(audit["status"], "PASS")
        raw = (run_dir / audit["file"]).read_bytes()
        self.assertEqual(digest(raw), audit["sha256"])
        snapshot = json.loads(raw)
        self.assertEqual(snapshot["review_sha256"], digest(reviews.read_bytes()))
        self.assertEqual(snapshot["tasks"][0]["statement_sha256"], record["attempts"][0]["statement_sha256"])
        solver = json.loads((self.root / "snapshots.jsonl").read_text().splitlines()[0])
        self.assertEqual(solver["files"], ["prompt.md", "task.json"])
        self.assertNotIn("fixture-semantic-checker", solver["prompt"])
        self.assertNotIn("The answer is", solver["prompt"])
        reviews.unlink()
        self.assertEqual((run_dir / audit["file"]).read_bytes(), raw)

    def test_consistently_rehashed_statement_cannot_reuse_its_old_review(self):
        reviews = self.passing_statement_reviews()
        prompt = self.bundle / "public/task-0001/prompt.md"
        prompt.write_bytes(b"Find 2 + 1. Return answer, derivation, complete as JSON.\n")
        current_hash = digest(prompt.read_bytes())
        for path in (self.bundle / "public/task-0001/task.json", self.bundle / "private/task-0001.json"):
            value = json.loads(path.read_text())
            value["statement_sha256"] = current_hash
            self.write_json(path, value)
        manifest_path = self.bundle / "manifest.json"
        value = json.loads(manifest_path.read_text())
        value["tasks"][0]["statement_sha256"] = current_hash
        self.write_json(manifest_path, value)
        with self.assertRaisesRegex(runner.BundleError, "Statement review gate:.*Stale"):
            self.run_bundle(configuration=self.authoring_configuration(), statement_reviews=reviews)
        self.assertFalse((self.root / "calls.jsonl").exists())

    def test_changed_answer_interface_cannot_reuse_its_old_review(self):
        reviews = self.passing_statement_reviews()
        configuration = self.authoring_configuration()
        with mock.patch.dict(runner.SUBMISSION_SCHEMA, additionalProperties=True):
            with self.assertRaisesRegex(runner.BundleError, "Statement review gate:.*answer interface"):
                self.run_bundle(configuration=configuration, statement_reviews=reviews)
        self.assertFalse((self.root / "calls.jsonl").exists())

    def test_supplied_evaluation_review_is_validated_even_when_optional(self):
        reviews = self.passing_statement_reviews()
        value = json.loads(reviews.read_text())
        value["reviews"][0]["semantic_check"]["meaning_preserved"] = False
        self.write_json(reviews, value)
        with self.assertRaisesRegex(runner.BundleError, "Meaning preservation"):
            self.run_bundle(statement_reviews=reviews)
        self.assertFalse((self.root / "calls.jsonl").exists())

    def test_reported_values_only_come_from_events(self):
        _, record = self.run_bundle(codex=self.fake_codex("reported"),
                                   model="reported-model", effort="reported-effort")
        attempt = record["attempts"][0]
        self.assertEqual(attempt["model_reported"], "reported-model")
        self.assertEqual(attempt["effort_reported"], "reported-effort")

    def test_default_temporary_root_supports_shallow_skill_installation(self):
        with mock.patch.object(runner, "__file__", "/skills/paper-math-bench/scripts/run_eval.py"), \
                mock.patch.object(runner.tempfile, "gettempdir", return_value=str(self.root)):
            parent = runner._temporary_parent(self.bundle)
        self.assertEqual(parent, self.root.resolve())

    def test_default_temporary_root_stays_outside_manuscript_folder(self):
        manuscript = self.root / "manuscript" / "main.tex"
        candidate = manuscript.parent / "temporary"
        candidate.mkdir(parents=True)
        with mock.patch.object(runner.tempfile, "gettempdir", return_value=str(candidate)):
            parent = runner._temporary_parent(self.bundle, source_tex=str(manuscript))
        self.assertFalse(parent.is_relative_to(manuscript.parent))

    def test_explicit_work_root_contains_real_workspaces_and_all_child_temp_paths(self):
        work_root = self.root / "cache" / "task-work"
        work_root.mkdir(parents=True)
        sentinel = work_root / "keep.txt"
        sentinel.write_bytes(b"preserve existing content")
        existing_children = {path.name for path in work_root.iterdir()}
        path = self.configuration(model="gpt-5.6-terra", effort="max", wall_seconds=None,
                                  profile="epoch-tier4-v2")
        _, record = self.run_bundle(
            model=None, effort=None, wall_seconds=None, profile="epoch-tier4-v2",
            configuration=path, work_root=work_root,
        )
        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["work_root_requested"], str(work_root))
        self.assertEqual(record["work_root"], str(work_root.resolve()))
        expected_environment = {key: str(work_root.resolve()) for key in ("TMPDIR", "TMP", "TEMP")}
        self.assertEqual(record["temporary_environment"], expected_environment)
        controller = Path(record["controller_dir"])
        workspace = Path(record["attempts"][0]["workspace_dir"])
        self.assertEqual(controller.parent, work_root.resolve())
        self.assertEqual(workspace.parent, work_root.resolve())
        snapshot, = [json.loads(line) for line in (self.root / "snapshots.jsonl").read_text().splitlines()]
        self.assertEqual(snapshot["files"], ["prompt.md", "task.json"])
        self.assertEqual(snapshot["workspace"], str(workspace))
        self.assertEqual(Path(snapshot["schema_path"]).parent, controller)
        environments = [json.loads(line) for line in (self.root / "environment-snapshots.jsonl").read_text().splitlines()]
        self.assertEqual(len(environments), 3)
        self.assertEqual(environments[0]["args"], ["--version"])
        self.assertEqual(environments[1]["args"][-2:], ["features", "list"])
        for item in environments:
            self.assertEqual(item["environment"], expected_environment)
            self.assertEqual(Path(item["temporary"]).parent, work_root.resolve())
            self.assertFalse(Path(item["temporary"]).exists())
        self.assertFalse(controller.exists())
        self.assertFalse(workspace.exists())
        self.assertEqual(sentinel.read_bytes(), b"preserve existing content")
        self.assertEqual({path.name for path in work_root.iterdir()}, existing_children)

    def test_unusable_work_root_fails_before_any_cli_or_configuration_claim(self):
        work_root = self.root / "not-a-directory"
        work_root.write_bytes(b"preserve this file")
        path = self.configuration()
        codex = self.fake_codex()
        with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
            with self.assertRaisesRegex(runner.BundleError, "Cannot use work_root"):
                self.run_bundle(configuration=path, codex=codex, work_root=work_root)
        self.assertFalse((self.bundle / "runs").exists())
        self.assertFalse((self.root / "calls.jsonl").exists())
        self.assertEqual(work_root.read_bytes(), b"preserve this file")
        _, record = self.run_bundle(configuration=path, codex=codex, work_root=self.root / "fresh" / "temp")
        self.assertEqual(record["status"], "completed")

    def test_explicit_work_root_rejects_bundle_overlap_and_source_ancestors(self):
        manuscript = self.root / "project" / "bank" / "main.tex"
        manuscript.parent.mkdir(parents=True)
        manuscript.write_bytes(b"manuscript stays unchanged")
        manifest = json.loads((self.bundle / "manifest.json").read_text())
        manifest["source_tex"] = str(manuscript)
        self.write_json(self.bundle / "manifest.json", manifest)
        invalid = [self.bundle, self.bundle / "temp", self.root, manuscript.parent,
                   manuscript, manuscript.parent.parent]
        with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
            for work_root in invalid:
                with self.subTest(work_root=work_root), self.assertRaises(runner.BundleError):
                    self.run_bundle(work_root=work_root)
        self.assertFalse((self.bundle / "runs").exists())
        work_root = manuscript.parent.parent / "cache" / "temp"
        _, record = self.run_bundle(work_root=work_root)
        self.assertEqual(record["work_root"], str(work_root.resolve()))
        self.assertEqual(manuscript.read_bytes(), b"manuscript stays unchanged")

    def test_explicit_work_root_checks_resolved_symlink_destination(self):
        work_root = self.root / "linked-work"
        work_root.symlink_to(self.bundle / "public", target_is_directory=True)
        with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
            with self.assertRaisesRegex(runner.BundleError, "separate from the evaluation bundle"):
                self.run_bundle(work_root=work_root)
        self.assertFalse((self.bundle / "runs").exists())

    def test_empty_explicit_work_root_is_rejected_by_api_and_cli(self):
        with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
            with self.assertRaisesRegex(runner.BundleError, "must name a directory"):
                self.run_bundle(work_root="")
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                runner.main([str(self.bundle), "--work-root", "", "--isolation", "instruction-only", "--dry-run"])
        self.assertEqual(raised.exception.code, 2)
        self.assertFalse((self.bundle / "runs").exists())

    def test_cli_and_api_share_work_root_and_create_fresh_parent(self):
        work_root = self.root / "new-cache" / "temp"
        output = io.StringIO()
        with redirect_stdout(output), mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
            result = runner.main([
                str(self.bundle), "--work-root", str(work_root),
                "--isolation", "instruction-only", "--dry-run",
            ])
        self.assertEqual(result, 0)
        cli_record = json.loads((Path(output.getvalue().strip()) / "run.json").read_text())
        _, api_record = self.run_bundle(work_root=work_root, dry_run=True)
        for record in (cli_record, api_record):
            self.assertEqual(record["work_root"], str(work_root.resolve()))
            self.assertEqual(record["work_root_requested"], str(work_root))
            self.assertEqual(Path(record["controller_dir"]).parent, work_root.resolve())
            self.assertEqual(Path(record["attempts"][0]["workspace_dir"]).parent, work_root.resolve())
        self.assertEqual(list(work_root.iterdir()), [])

    def test_dry_run_does_not_start_any_process_and_allows_unreviewed_rubrics(self):
        self.make_bundle(reviewed=False)
        with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
            run_dir, record = self.run_bundle(dry_run=True, codex="/missing/codex")
        self.assertEqual(record["status"], "planned")
        self.assertIsNone(record["cli_version"])
        attempt, = record["attempts"]
        self.assertEqual(attempt["status"], "planned")
        self.assertIsNone(attempt["usage"])
        self.assertIsNone(attempt["submission_sha256"])
        self.assertEqual((run_dir / attempt["events_file"]).read_bytes(), b"")
        self.assertFalse((self.root / "calls.jsonl").exists())

    def test_cli_dry_run_materializes_current_local_defaults_without_configuration(self):
        output = io.StringIO()
        with redirect_stdout(output), mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
            self.assertEqual(runner.main([str(self.bundle), "--isolation", "instruction-only", "--dry-run"]), 0)
        run_dir = Path(output.getvalue().strip())
        record = json.loads((run_dir / "run.json").read_text())
        self.assertEqual(record["profile"], "local-pilot")
        self.assertEqual(record["model_requested"], "gpt-5.6-sol")
        self.assertEqual(record["effort_requested"], "max")
        self.assertIsNone(record["wall_seconds"])
        self.assertIsNone(record["configuration_evidence"])
        self.assertIsNone(record["profile_snapshot"])
        self.assertEqual(record["budget"]["total_input_output_tokens_requested"], 1000000)
        self.assertEqual(record["budget"]["submit_after_tokens_requested"], 660000)
        self.assertFalse(record["budget"]["epoch_protocol_match"])
        attempt, = record["attempts"]
        self.assertIn('model_reasoning_effort="max"', attempt["command"])
        self.assertIn("limit_tokens=1000000", record["controls_requested"]["native_rollout_budget"])
        self.assertIn("340,000 or fewer", (run_dir / attempt["execution_prompt_file"]).read_text())

    def test_local_dry_run_preserves_explicit_model_effort_and_wall_overrides(self):
        for override, expected in (
            ({"model": "custom-model"}, ("custom-model", "max", None)),
            ({"effort": "ultra"}, ("gpt-5.6-sol", "ultra", None)),
            ({"effort": "high"}, ("gpt-5.6-sol", "high", None)),
            ({"model": "custom-model", "effort": "max", "wall_seconds": 7},
             ("custom-model", "max", 7.0)),
        ):
            with self.subTest(override=override):
                run_dir = runner.run_bundle(self.bundle, isolation="instruction-only", dry_run=True, **override)
                record = json.loads((run_dir / "run.json").read_text())
                self.assertEqual((record["model_requested"], record["effort_requested"], record["wall_seconds"]), expected)

    def test_omitted_cli_profile_uses_supplied_epoch_configuration(self):
        path = self.configuration(model="gpt-5.6-terra", effort="max", wall_seconds=None, profile="epoch-tier4-v2")
        output = io.StringIO()
        with redirect_stdout(output), mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
            self.assertEqual(runner.main([
                str(self.bundle), "--configuration", str(path), "--invocation-id", "current-test-operation",
                "--isolation", "instruction-only", "--dry-run",
            ]), 0)
        record = json.loads((Path(output.getvalue().strip()) / "run.json").read_text())
        self.assertEqual(record["profile"], "epoch-tier4-v2")
        self.assertEqual(record["model_requested"], "gpt-5.6-terra")
        self.assertEqual(record["effort_requested"], "max")
        self.assertIsNotNone(record["profile_snapshot"])

    def test_explicit_profile_cannot_override_a_different_recorded_profile(self):
        path = self.configuration(model="gpt-5.6-terra", effort="max", wall_seconds=None, profile="epoch-tier4-v2")
        with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
            with self.assertRaisesRegex(runner.BundleError, "profile differs"):
                self.run_bundle(configuration=path, model=None, effort=None, wall_seconds=None, profile="local-pilot")

    def test_failure_and_unsupported_configuration_are_errors_without_retry(self):
        for mode, expected_code in (("failure", 7), ("unsupported", 2)):
            with self.subTest(mode=mode):
                calls = self.root / "calls.jsonl"
                calls.unlink(missing_ok=True)
                run_dir, record = self.run_bundle(codex=self.fake_codex(mode))
                self.assertEqual(record["status"], "error")
                attempt, = record["attempts"]
                self.assertEqual(attempt["exit_code"], expected_code)
                self.assertEqual(attempt["status"], "error")
                self.assertEqual(attempt["submission_sha256"], digest(b""))
                self.assertTrue((run_dir / attempt["stderr_file"]).read_text())
                invocations = [json.loads(line) for line in calls.read_text().splitlines()]
                self.assertEqual(len(invocations), 2)
                self.assertEqual(invocations[0], ["--version"])
                self.assertEqual(invocations[1].count("exec"), 1)

    @unittest.skipUnless(os.name == "posix", "Unix process groups are required")
    def test_timeout_terminates_child_process_and_preserves_events(self):
        started = time.monotonic()
        work_root = self.root / "timeout-work"
        run_dir, record = self.run_bundle(codex=self.fake_codex("timeout"), wall_seconds=0.2,
                                          work_root=work_root)
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual(record["status"], "timeout")
        attempt, = record["attempts"]
        self.assertEqual(attempt["status"], "timeout")
        self.assertLess(attempt["exit_code"], 0)
        self.assertTrue((run_dir / attempt["events_file"]).read_text())
        self.assertIsNone(attempt["usage"])
        self.assertEqual(attempt["submission_sha256"], digest(b""))
        self.assertFalse(Path(attempt["workspace_dir"]).exists())
        self.assertFalse(Path(record["controller_dir"]).exists())
        self.assertEqual(list(work_root.iterdir()), [])
        time.sleep(1.05)
        self.assertFalse((self.root / "child-survived").exists())

    def test_timeout_freezes_partial_submission_bytes(self):
        run_dir, record = self.run_bundle(codex=self.fake_codex("timeout_partial"), wall_seconds=0.2)
        attempt, = record["attempts"]
        self.assertEqual(attempt["status"], "timeout")
        partial = (run_dir / attempt["submission_file"]).read_bytes()
        self.assertEqual(partial, b'{"answer":"partial"')
        self.assertEqual(attempt["submission_sha256"], digest(partial))

    def test_failed_process_stops_the_batch_without_repeated_requests(self):
        self.make_bundle(count=3)
        _, record = self.run_bundle(codex=self.fake_codex("unsupported"))
        calls = [json.loads(line) for line in (self.root / "calls.jsonl").read_text().splitlines()]
        self.assertEqual(sum(call[0] == "exec" for call in calls), 1)
        self.assertTrue(all(attempt["status"] == "error" for attempt in record["attempts"]))
        self.assertIn("Not started", record["attempts"][1]["error"])
        self.assertIsNone(record["attempts"][1]["command"])

    def test_missing_or_stale_inputs_fail_before_process_creation(self):
        changes = {
            "statement": lambda: (self.bundle / "public/task-0001/prompt.md").write_text("changed"),
            "gold": lambda: self.change_private("reference_solution_tex", "changed"),
            "private_hash": lambda: self.change_private("solution_sha256", "a" * 64),
            "missing_public": lambda: (self.bundle / "public/task-0001/task.json").unlink(),
            "missing_private": lambda: (self.bundle / "private/task-0001.json").unlink(),
            "missing_rubric": lambda: self.change_private("rubric", None),
        }
        for label, change in changes.items():
            with self.subTest(label=label):
                self.make_bundle()
                change()
                with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
                    with self.assertRaises(runner.BundleError):
                        self.run_bundle()

    def test_duplicate_public_metadata_keys_are_rejected(self):
        path = self.bundle / "public/task-0001/task.json"
        metadata = json.loads(path.read_text())
        path.write_text('{"id":"unapproved embedded content",' + json.dumps(metadata)[1:])
        with self.assertRaisesRegex(runner.BundleError, "Duplicate JSON key"):
            self.run_bundle(dry_run=True)

    def test_relative_codex_path_is_resolved_before_changing_workspace(self):
        executable = Path(self.fake_codex())
        relative = os.path.relpath(executable, Path.cwd())
        _, record = self.run_bundle(codex=relative)
        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["attempts"][0]["command"][0], str(executable.resolve()))

    def change_private(self, key, value):
        path = self.bundle / "private/task-0001.json"
        private = json.loads(path.read_text())
        private[key] = value
        self.write_json(path, private)

    def test_real_run_requires_review_and_reference_evidence(self):
        for key, value in (("review_status", "unreviewed"), ("reference_status", "unverified"),
                           ("requirements", []), ("verification_evidence", [""])):
            with self.subTest(key=key):
                self.make_bundle()
                path = self.bundle / "private/task-0001.json"
                private = json.loads(path.read_text())
                private["rubric"][key] = value
                self.write_json(path, private)
                with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
                    with self.assertRaises(runner.BundleError):
                        self.run_bundle()

    def test_real_run_validates_grading_contract_before_any_process(self):
        invalid = [
            {"answer_type": "exact_integer", "accepted_answer": "2+1"},
            {"answer_type": "exact_integer", "accepted_answer": True},
            {"answer_type": "exact_rational", "accepted_answer": "1/0"},
            {"answer_type": "exact_json", "accepted_answer": {"x": float("nan")}},
            {"answer_type": "numeric", "accepted_answer": "2"},
            {"answer_type": "numeric", "accepted_answer": "2", "absolute_tolerance": "0"},
            {"answer_type": "numeric", "accepted_answer": "2", "absolute_tolerance": "-0.1", "relative_tolerance": "0"},
            {"answer_type": "numeric", "accepted_answer": "2", "absolute_tolerance": "0", "relative_tolerance": "-0.1"},
            {"answer_type": "numeric", "accepted_answer": "Infinity", "absolute_tolerance": "0", "relative_tolerance": "0"},
            {"answer_type": "numeric", "accepted_answer": "2", "absolute_tolerance": "NaN", "relative_tolerance": "0"},
            {"answer_type": "numeric", "accepted_answer": "invalid", "absolute_tolerance": "0", "relative_tolerance": "0"},
        ]
        for grading in invalid:
            with self.subTest(grading=grading):
                self.make_bundle()
                path = self.bundle / "private/task-0001.json"
                private = json.loads(path.read_text())
                private["rubric"].update(grading)
                self.write_json(path, private)
                with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
                    with self.assertRaisesRegex(runner.BundleError, "Invalid grading contract"):
                        self.run_bundle()

    def test_manual_null_reference_is_allowed_and_dry_run_skips_grading_preflight(self):
        path = self.bundle / "private/task-0001.json"
        private = json.loads(path.read_text())
        private["rubric"].update(answer_type="manual", accepted_answer=None)
        self.write_json(path, private)
        _, record = self.run_bundle()
        self.assertEqual(record["status"], "completed")
        private["rubric"].update(answer_type="numeric", accepted_answer="unreviewed")
        self.write_json(path, private)
        with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
            _, record = self.run_bundle(dry_run=True)
        self.assertEqual(record["status"], "planned")

    def test_unsafe_paths_and_symlinks_are_rejected(self):
        for relative in ("../private/task-0001.json", "/tmp/task.json", "private/../private/task-0001.json", "private\\task-0001.json"):
            with self.subTest(relative=relative):
                self.make_bundle()
                path = self.bundle / "manifest.json"
                manifest = json.loads(path.read_text())
                manifest["tasks"][0]["private_file"] = relative
                self.write_json(path, manifest)
                with self.assertRaises(runner.BundleError):
                    self.run_bundle(dry_run=True)
        self.make_bundle()
        path = self.bundle / "public/task-0001/prompt.md"
        target = self.root / "outside-prompt.md"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
        with self.assertRaises(runner.BundleError):
            self.run_bundle(dry_run=True)

    def test_task_selection_is_serial_and_unknown_or_duplicate_ids_fail(self):
        self.make_bundle(count=3)
        _, record = self.run_bundle(ids=["task-0001", "task-0003"])
        self.assertEqual([item["id"] for item in record["attempts"]], ["task-0001", "task-0003"])
        invocations = (self.root / "calls.jsonl").read_text().splitlines()
        self.assertEqual(len(invocations), 3)
        for ids in (["task-9999"], ["task-0001", "task-0001"], []):
            with self.assertRaises(runner.BundleError):
                self.run_bundle(ids=ids, dry_run=True)

    def test_local_defaults_allow_omitted_model_effort_but_isolation_is_required(self):
        complete = [str(self.bundle), "--profile", "local-pilot", "--model", "M", "--effort", "E", "--isolation", "instruction-only", "--dry-run"]
        for flag in ("--isolation",):
            arguments = complete[:]
            index = arguments.index(flag)
            del arguments[index:index + 2]
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                runner.main(arguments)
            self.assertEqual(raised.exception.code, 2)
        for kwargs in ({"model": ""}, {"effort": " "}, {"wall_seconds": 0},
                       {"wall_seconds": float("inf")}, {"wall_seconds": float("nan")},
                       {"isolation": "strict"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(runner.BundleError):
                self.run_bundle(dry_run=True, **kwargs)

    def test_invalid_submission_is_preserved_and_marked_error(self):
        run_dir, record = self.run_bundle(codex=self.fake_codex("bad_submission"))
        attempt, = record["attempts"]
        self.assertEqual(attempt["status"], "error")
        self.assertIn("Final response", attempt["error"])
        self.assertEqual((run_dir / attempt["submission_file"]).read_text(), '{"answer": 2}')
        self.assertEqual(attempt["submission_sha256"], digest(b'{"answer": 2}'))

    def test_real_runs_require_current_qa_before_starting_any_process(self):
        with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
            with self.assertRaisesRegex(runner.BundleError, "current operation"):
                self.run_bundle(configuration=None)
            path = self.configuration()
            with self.assertRaisesRegex(runner.BundleError, "invocation_id"):
                self.run_bundle(configuration=path, invocation_id="different-operation")

    def instruction_configuration(self):
        path = self.configuration(model="gpt-5.6-sol", effort="ultra", wall_seconds=None)
        data = json.loads(path.read_text())
        answer = data.pop("qa")[0]
        data["user_instructions"] = [{
            "text": "Evaluate this bundle with gpt-5.6-sol / ultra and the default token budget.",
            "user_message_ref": "current-user-request",
            "provided_at": answer["answered_at"],
        }]
        data["settings"].update(total_input_output_tokens=1000000, submit_after_tokens=660000)
        self.write_json(path, data)
        return path

    def test_current_direct_instruction_replaces_fresh_qa_and_is_single_use(self):
        path = self.instruction_configuration()
        run_dir = runner.run_bundle(
            self.bundle, isolation="instruction-only", configuration=path,
            invocation_id="current-test-operation", codex=self.fake_codex(),
        )
        record = json.loads((run_dir / "run.json").read_text())
        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["profile"], "local-pilot")
        self.assertEqual(record["model_requested"], "gpt-5.6-sol")
        self.assertEqual(record["effort_requested"], "ultra")
        self.assertNotIn("qa", record["configuration_evidence"])
        self.assertEqual(record["configuration_evidence"]["user_instructions"][0]["user_message_ref"], "current-user-request")
        with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
            with self.assertRaisesRegex(runner.BundleError, "already recorded a real invocation"):
                runner.run_bundle(self.bundle, isolation="instruction-only", configuration=path,
                                  invocation_id="current-test-operation")

    def test_direct_instruction_evidence_rejects_missing_malformed_or_stale_records(self):
        mutations = {
            "no_evidence": lambda d: d.pop("user_instructions"),
            "null_instructions": lambda d: d.update(user_instructions=None),
            "empty_instructions": lambda d: d.update(user_instructions=[]),
            "non_object": lambda d: d.update(user_instructions=["user said yes"]),
            "empty_text": lambda d: d["user_instructions"][0].update(text=""),
            "missing_reference": lambda d: d["user_instructions"][0].pop("user_message_ref"),
            "missing_time": lambda d: d["user_instructions"][0].pop("provided_at"),
            "no_timezone": lambda d: d["user_instructions"][0].update(provided_at="2026-10-19T12:00:00"),
            "stale_instruction": lambda d: d["user_instructions"][0].update(provided_at="2000-01-01T00:00:00Z"),
            "future_instruction": lambda d: d["user_instructions"][0].update(provided_at="2100-01-01T00:00:00Z"),
            "bad_qa_with_valid_instruction": lambda d: d.update(qa=[]),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                path = self.instruction_configuration()
                data = json.loads(path.read_text())
                mutate(data)
                self.write_json(path, data)
                with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
                    with self.assertRaises(runner.BundleError):
                        runner.run_bundle(self.bundle, isolation="instruction-only", configuration=path,
                                          invocation_id="current-test-operation")

    def test_direct_instruction_does_not_bypass_existing_qa_validation(self):
        path = self.instruction_configuration()
        data = json.loads(path.read_text())
        data["qa"] = [{"question": "Use this configuration?", "answer": "Yes.",
                       "user_reply_ref": "stale-answer", "answered_at": "2000-01-01T00:00:00Z"}]
        self.write_json(path, data)
        with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
            with self.assertRaisesRegex(runner.BundleError, "Stale Q&A answer"):
                runner.run_bundle(self.bundle, isolation="instruction-only", configuration=path,
                                  invocation_id="current-test-operation")

    def test_qa_does_not_bypass_malformed_direct_instruction_evidence(self):
        path = self.configuration()
        data = json.loads(path.read_text())
        data["user_instructions"] = [{"text": "Use this configuration.", "provided_at": data["created_at"]}]
        self.write_json(path, data)
        with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
            with self.assertRaisesRegex(runner.BundleError, "user_message_ref"):
                self.run_bundle(configuration=path)

    def test_qa_must_match_bundle_hash_selection_and_actual_settings(self):
        mutations = {
            "old_answer": lambda d: d["qa"][0].update(answered_at="2000-01-01T00:00:00Z"),
            "no_reply_reference": lambda d: d["qa"][0].pop("user_reply_ref"),
            "no_answer": lambda d: d["qa"][0].update(answer=""),
            "wrong_bundle": lambda d: d["binding"].update(bundle="/different/bundle"),
            "changed_manifest": lambda d: d["binding"].update(manifest_sha256="f" * 64),
            "changed_bank": lambda d: d["binding"].update(benchmark_sha256="f" * 64),
            "changed_ids": lambda d: d["binding"].update(task_ids=["task-0002"]),
            "different_model": lambda d: d["settings"].update(model="other-model"),
            "different_effort": lambda d: d["settings"].update(effort="other-effort"),
            "different_wall": lambda d: d["settings"].update(wall_seconds=3),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                path = self.configuration()
                data = json.loads(path.read_text())
                mutate(data)
                self.write_json(path, data)
                with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
                    with self.assertRaises(runner.BundleError):
                        self.run_bundle(configuration=path)

    def test_budget_instructions_default_to_local_pilot(self):
        settings = runner._settings()
        budget = {
            "native_rollout_budget_requested": True,
            "total_input_output_tokens_requested": 1000000,
            "submit_after_tokens_requested": 660000,
        }
        self.assertEqual(settings.budget_instructions(budget),
                         settings.budget_instructions(budget, profile="local-pilot"))
        self.assertIn(b"continue solving within the 1,000,000 total token budget",
                      settings.budget_instructions(budget))

    def test_solver_budget_reminder_uses_the_resolved_profile(self):
        native_budget = "features.rollout_budget={enabled=true,limit_tokens=1000000,reminder_at_remaining_tokens=[340000],sampling_token_weight=1.0,prefill_token_weight=1.0}"
        for profile in ("local-pilot", "epoch-tier4-v2"):
            with self.subTest(profile=profile):
                path = self.configuration(model="gpt-5.6-terra", effort="max",
                                          wall_seconds=None, profile=profile)
                data = json.loads(path.read_text())
                data["settings"].update(total_input_output_tokens=1000000, submit_after_tokens=660000)
                self.write_json(path, data)
                run_dir, record = self.run_bundle(model=None, effort=None, wall_seconds=None,
                                                  profile=None, configuration=path)
                self.assertEqual(record["status"], "completed")
                self.assertEqual(record["profile"], profile)
                self.assertEqual(record["budget"]["total_input_output_tokens_requested"], 1000000)
                self.assertEqual(record["budget"]["submit_after_tokens_requested"], 660000)
                attempt, = record["attempts"]
                self.assertIn(native_budget, attempt["command"])
                snapshot = json.loads((self.root / "snapshots.jsonl").read_text().splitlines()[-1])
                prompt = snapshot["prompt"]
                self.assertEqual(prompt, (run_dir / attempt["execution_prompt_file"]).read_text())
                self.assertIn("340,000 or fewer remaining tokens", prompt)
                if profile == "local-pilot":
                    self.assertIn("reserve enough tokens for your final JSON", prompt)
                    self.assertIn("continue solving within the 1,000,000 total token budget", prompt)
                    self.assertIn("Submit as soon as finished", prompt)
                    self.assertNotIn("stop further exploration", prompt)
                else:
                    self.assertIn("stop further exploration and submit your best final JSON immediately", prompt)
                    self.assertIn("Submit earlier when finished", prompt)
                    self.assertNotIn("continue solving", prompt)

    def test_epoch_requests_published_max_and_native_budget_without_wall_limit(self):
        path = self.configuration(model="gpt-5.6-terra", effort="max", wall_seconds=None, profile="epoch-tier4-v2")
        run_dir, record = self.run_bundle(model=None, effort=None, wall_seconds=None,
                                          profile="epoch-tier4-v2", configuration=path)
        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["effort_requested"], "max")
        self.assertIsNone(record["wall_seconds"])
        self.assertTrue(record["budget_preflight"]["accepted"])
        self.assertFalse(record["budget"]["native_accounting_verified"])
        self.assertFalse(record["budget"]["forced_submission_enforced"])
        self.assertFalse(record["budget"]["epoch_protocol_match"])
        self.assertEqual(record["configuration_sha256"], digest(path.read_bytes()))
        attempt, = record["attempts"]
        override = "features.rollout_budget={enabled=true,limit_tokens=1000000,reminder_at_remaining_tokens=[340000],sampling_token_weight=1.0,prefill_token_weight=1.0}"
        self.assertIn(override, attempt["command"])
        self.assertIn('model_reasoning_effort="max"', attempt["command"])
        self.assertEqual(attempt["total_input_output_tokens"], 17)
        execution_prompt = (run_dir / attempt["execution_prompt_file"]).read_bytes()
        self.assertIn(b"340,000 or fewer", execution_prompt)
        self.assertEqual(digest(execution_prompt), attempt["execution_prompt_sha256"])
        self.assertEqual(digest((self.bundle / "public/task-0001/prompt.md").read_bytes()), attempt["statement_sha256"])

    def test_epoch_rejects_ultra_wrong_budgets_and_unacknowledged_cli_differences(self):
        mutations = {
            "ultra": lambda d: d["settings"].update(effort="ultra"),
            "short_budget": lambda d: d["settings"].update(total_input_output_tokens=20000),
            "other_threshold": lambda d: d["settings"].update(submit_after_tokens=500000),
            "no_acknowledgement": lambda d: d.pop("acknowledge_cli_differences"),
            "unpublished_model": lambda d: d["settings"].update(model="gpt-5.6-sol_promax"),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                path = self.configuration(model="gpt-5.6-terra", effort="max", wall_seconds=None, profile="epoch-tier4-v2")
                data = json.loads(path.read_text())
                mutate(data)
                self.write_json(path, data)
                with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
                    with self.assertRaises(runner.BundleError):
                        self.run_bundle(model=None, effort=None, wall_seconds=None,
                                        profile="epoch-tier4-v2", configuration=path)

    def test_epoch_preflight_failure_stops_before_solver_call(self):
        path = self.configuration(model="gpt-5.6-terra", effort="max", wall_seconds=None, profile="epoch-tier4-v2")
        _, record = self.run_bundle(model=None, effort=None, wall_seconds=None,
                                   profile="epoch-tier4-v2", configuration=path, codex=self.fake_codex("no_budget"))
        self.assertEqual(record["status"], "error")
        self.assertFalse(record["budget_preflight"]["accepted"])
        self.assertIsNone(record["attempts"][0]["command"])
        calls = [json.loads(line) for line in (self.root / "calls.jsonl").read_text().splitlines()]
        self.assertEqual(len(calls), 2)
        self.assertFalse(any(call and call[0] == "exec" for call in calls))

    def test_token_exhaustion_is_distinct_and_does_not_stop_other_tasks(self):
        self.make_bundle(count=2)
        run_dir, record = self.run_bundle(codex=self.fake_codex("token_limit"))
        self.assertEqual(record["status"], "token_limit")
        self.assertTrue(all(item["status"] == "token_limit" for item in record["attempts"]))
        self.assertTrue(all(item["budget_exhausted"] for item in record["attempts"]))
        self.assertTrue(all(item["usage"] is None for item in record["attempts"]))
        self.assertTrue(all(item["total_input_output_tokens"] is None for item in record["attempts"]))
        self.assertTrue(all(item["submission_sha256"] == digest(b"") for item in record["attempts"]))

    def test_usage_subtotals_are_not_added_twice_and_missing_usage_is_unknown(self):
        measured = runner._settings().measured_total
        self.assertEqual(measured({"input_tokens": 12, "cached_input_tokens": 3,
                                   "output_tokens": 5, "reasoning_output_tokens": 4}), 17)
        self.assertEqual(measured([{"input_tokens": 12, "output_tokens": 5},
                                   {"input_tokens": 20, "output_tokens": 4}]), 41)
        self.assertIsNone(measured(None))
        self.assertIsNone(measured({"total_tokens": 100}))
        self.assertIsNone(measured({"input_tokens": True, "output_tokens": 4}))
        self.assertIsNone(measured([{"input_tokens": 2, "output_tokens": 4}, {}]))

    def test_unknown_semantic_settings_are_rejected_before_any_solver_call(self):
        for key, value in (("reasoning_mode", "pro"), ("mode", "promax"), ("temperature", 0.1),
                           ("unimplemented_setting", True)):
            with self.subTest(key=key):
                path = self.configuration()
                data = json.loads(path.read_text())
                data["settings"][key] = value
                self.write_json(path, data)
                with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
                    with self.assertRaisesRegex(runner.BundleError, "Unsupported configuration settings"):
                        self.run_bundle(configuration=path)

    def test_local_custom_token_limits_are_applied_to_native_budget_and_prompt(self):
        path = self.configuration()
        data = json.loads(path.read_text())
        data["settings"].update(total_input_output_tokens=20000, submit_after_tokens=12000)
        self.write_json(path, data)
        run_dir, record = self.run_bundle(configuration=path)
        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["budget"]["total_input_output_tokens_requested"], 20000)
        self.assertEqual(record["budget"]["submit_after_tokens_requested"], 12000)
        self.assertTrue(record["budget_preflight"]["accepted"])
        attempt, = record["attempts"]
        self.assertIn("features.rollout_budget={enabled=true,limit_tokens=20000,reminder_at_remaining_tokens=[8000],sampling_token_weight=1.0,prefill_token_weight=1.0}", attempt["command"])
        prompt = (run_dir / attempt["execution_prompt_file"]).read_text()
        self.assertIn("20,000 cumulative", prompt)
        self.assertIn("8,000 or fewer", prompt)
        self.assertIn("continue solving within the 20,000 total token budget", prompt)
        self.assertNotIn("340,000", prompt)

    def test_partial_or_invalid_local_token_limits_are_rejected(self):
        values = [(20000, None), (None, 12000), (20000, 20000), (20000, 25000),
                  (0, 1), (20000, 0), (True, 1), (20000.0, 12000)]
        for total, submit in values:
            with self.subTest(total=total, submit=submit):
                path = self.configuration()
                data = json.loads(path.read_text())
                data["settings"].update(total_input_output_tokens=total, submit_after_tokens=submit)
                self.write_json(path, data)
                with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
                    with self.assertRaisesRegex(runner.BundleError, "Token limits"):
                        self.run_bundle(configuration=path)

    def test_real_run_consumes_qa_configuration_but_dry_run_does_not(self):
        path = self.configuration()
        self.run_bundle(configuration=path, dry_run=True)
        self.run_bundle(configuration=path, dry_run=True)
        _, record = self.run_bundle(configuration=path)
        self.assertEqual(record["status"], "completed")
        with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
            with self.assertRaisesRegex(runner.BundleError, "already recorded a real invocation"):
                self.run_bundle(configuration=path)
            self.run_bundle(configuration=path, dry_run=True)

    def test_replay_guard_recognizes_real_records_without_a_claim_file(self):
        path = self.configuration()
        self.run_bundle(configuration=path)
        claim, = (path for path in (self.bundle / "runs/.configuration-uses").glob("*.json")
                  if re.fullmatch(r"[0-9a-f]{64}\.json", path.name))
        claim.unlink()
        with self.assertRaisesRegex(runner.BundleError, "already recorded a real invocation"):
            self.run_bundle(configuration=path)

    def test_reformatted_or_reordered_qa_cannot_replay_a_real_invocation(self):
        path = self.configuration()
        _, record = self.run_bundle(configuration=path)
        original_hash = record["configuration_sha256"]
        data = json.loads(path.read_text())
        path.write_text(json.dumps(data, sort_keys=True, indent=7) + "\n", encoding="utf-8")
        self.assertNotEqual(digest(path.read_bytes()), original_hash)
        self.assertEqual(runner._settings().semantic_hash(data), record["configuration_semantic_sha256"])
        with mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("No process allowed")):
            with self.assertRaisesRegex(runner.BundleError, "already recorded a real invocation"):
                self.run_bundle(configuration=path)

    def test_legacy_evidence_is_canonicalized_for_replay_guard(self):
        path = self.configuration()
        run_dir, record = self.run_bundle(configuration=path)
        record.pop("configuration_semantic_sha256")
        self.write_json(run_dir / "run.json", record)
        for claim in (self.bundle / "runs/.configuration-uses").glob("*.json"):
            if re.fullmatch(r"[0-9a-f]{64}\.json", claim.name):
                claim.unlink()
        data = json.loads(path.read_text())
        path.write_text(json.dumps(data, sort_keys=True, indent=3), encoding="utf-8")
        self.assertNotEqual(digest(path.read_bytes()), record["configuration_sha256"])
        with self.assertRaisesRegex(runner.BundleError, "already recorded a real invocation"):
            self.run_bundle(configuration=path)

    def test_reported_effort_downgrade_is_error_and_stops_batch_on_exit_zero(self):
        self.make_bundle(count=2)
        path = self.configuration(model="gpt-5.6-terra", effort="max", wall_seconds=None, profile="epoch-tier4-v2")
        run_dir, record = self.run_bundle(model=None, effort=None, wall_seconds=None, profile="epoch-tier4-v2",
                                         configuration=path, codex=self.fake_codex("effort_downgrade"))
        self.assertEqual(record["status"], "error")
        first, second = record["attempts"]
        self.assertEqual(first["exit_code"], 0)
        self.assertEqual(first["status"], "error")
        self.assertEqual(first["error_kind"], "configuration_mismatch")
        self.assertEqual(first["configuration_mismatch"], {"effort": {"requested": "max", "reported": "high"}})
        self.assertEqual(second["status"], "error")
        self.assertIsNone(second["command"])
        self.assertIn("Not started", second["error"])
        calls = [json.loads(line) for line in (self.root / "calls.jsonl").read_text().splitlines()]
        self.assertEqual(sum(bool(call) and call[0] == "exec" for call in calls), 1)
        scoring_spec = importlib.util.spec_from_file_location("downgrade_score", SCRIPT.with_name("score_run.py"))
        scoring = importlib.util.module_from_spec(scoring_spec)
        scoring_spec.loader.exec_module(scoring)
        graded = scoring.assess(self.bundle, run_dir)
        self.assertEqual([task["answer_status"] for task in graded["tasks"]], ["ERROR", "ERROR"])
        self.assertEqual(graded["tasks"][0]["execution_error_kind"], "configuration_mismatch")
        with mock.patch.dict(sys.modules, {"score_run": scoring}):
            screening_spec = importlib.util.spec_from_file_location("downgrade_screen", SCRIPT.with_name("screen_candidates.py"))
            screening = importlib.util.module_from_spec(screening_spec)
            screening_spec.loader.exec_module(screening)
            screened = json.loads(screening.screen(self.bundle, run_dir).read_text())
        self.assertEqual(screened["summary"]["pending"], 2)
        self.assertEqual(screened["summary"]["classified"], 0)
        self.assertEqual(screened["summary"]["tier_counts"], {"T2": 0, "T3": 0, "T4": 0})

    def test_explicitly_different_model_is_not_silently_accepted(self):
        _, record = self.run_bundle(model="gpt-5.6-terra", effort="max", codex=self.fake_codex("model_substitution"))
        attempt, = record["attempts"]
        self.assertEqual(attempt["status"], "error")
        self.assertEqual(attempt["configuration_mismatch"], {"model": {"requested": "gpt-5.6-terra", "reported": "gpt-6-sol"}})

    @unittest.skipUnless(os.name == "posix", "Unix signals are required")
    def test_sigterm_saves_interrupted_metadata_and_terminates_children(self):
        codex = self.fake_codex("interrupt")
        work_root = self.root / "interrupt-work"
        process = subprocess.Popen([
            sys.executable, str(SCRIPT), str(self.bundle), "--model", "M", "--effort", "E",
            "--profile", "local-pilot", "--configuration", str(self.configuration(model="M", effort="E", wall_seconds=20)),
            "--invocation-id", "current-test-operation", "--wall-seconds", "20", "--isolation", "instruction-only", "--codex", codex,
            "--work-root", str(work_root),
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 5
            while not (self.root / "ready").exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue((self.root / "ready").exists())
            process.send_signal(signal.SIGTERM)
            process.communicate(timeout=3)
            self.assertEqual(process.returncode, 143)
            run_file, = list((self.bundle / "runs").glob("*/run.json"))
            record = json.loads(run_file.read_text())
            self.assertEqual(record["status"], "interrupted")
            self.assertEqual(record["attempts"][0]["status"], "interrupted")
            self.assertTrue(record["completed_at"])
            self.assertFalse(Path(record["controller_dir"]).exists())
            self.assertFalse(Path(record["attempts"][0]["workspace_dir"]).exists())
            self.assertEqual(list(work_root.iterdir()), [])
            time.sleep(1.05)
            self.assertFalse((self.root / "child-survived").exists())
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()


# Test entry point
if __name__ == "__main__":
    unittest.main()
