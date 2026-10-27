# Contents
# 1. Module setup: imports.
# 2. module(): isolated script loading.
# 3. IntegrationTests: project-to-report workflow and frozen artifacts.
# 4. Test entry point: unittest.main().

"""Exercise the complete project-to-report workflow with a fake Codex process."""

# Module setup
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import os
import sys
import tempfile
import unittest


# Script loader
def module(name):
    path = Path(__file__).resolve().parents[1] / "scripts" / (name + ".py")
    spec = importlib.util.spec_from_file_location("integration_" + name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


# IntegrationTests: complete local workflow
class IntegrationTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "The real subprocess runner uses Unix process groups.")
    def test_new_project_export_fake_execution_review_and_frozen_report(self):
        init, prepare, runner, scorer = [module(name) for name in
                                       ("init_project", "prepare_eval", "run_eval", "score_run")]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            init.initialize(project)
            tex = project / "main.tex"
            text = tex.read_text()
            text = text.replace(r"\section{T2}", r"""\section{T2}
\begin{problem}
\label{prob:addition}
Compute $1+1$ and justify the answer.
\end{problem}
\noindent\textit{Source.} An arithmetic test fixture.
""")
            text = text.replace(r"\section{Solutions}", r"""\section{Solutions}
\subsection*{Solution to Problem~\ref{prob:addition}}
The sum of two unit integers is $2$.
""")
            tex.write_text(text)
            bundle = prepare.prepare(tex, root / "bundle")
            private_path = bundle / "private/task-0001.json"
            private = json.loads(private_path.read_text())
            private["rubric"].update(
                review_status="reviewed", reference_status="verified",
                answer_type="exact_integer", accepted_answer="2", requires_proof=True,
                requirements=["Exact sum and mathematical justification."],
                verification_evidence=["The sum is verified by integer addition."],
            )
            private_path.write_text(json.dumps(private))
            fake = root / "fake-codex"
            fake.write_text("#!" + sys.executable + "\n" + r'''
import json, pathlib, sys
if "--version" in sys.argv:
    print("fake-codex integration fixture")
    raise SystemExit(0)
# Paired AppleDouble files contain OS metadata, not additional solver inputs.
names = {p.name for p in pathlib.Path.cwd().iterdir()}
assert names - {"._prompt.md", "._task.json"} == {"prompt.md", "task.json"}
prompt = sys.stdin.read()
assert "The sum of two unit integers" not in prompt
assert "Do not use the web" in prompt
out = pathlib.Path(sys.argv[sys.argv.index("--output-last-message") + 1])
out.write_text(json.dumps({"answer":"2","derivation":"Adding two units gives two.","complete":True}))
print(json.dumps({"type":"thread.started","model":"fixture-request","reasoning_effort":"high"}))
print(json.dumps({"type":"turn.completed","usage":{"input_tokens":1,"output_tokens":1}}))
''')
            fake.chmod(0o700)
            now = datetime.now(timezone.utc)
            manifest_bytes = (bundle / "manifest.json").read_bytes()
            manifest = json.loads(manifest_bytes)
            configuration = root / "configuration.json"
            configuration.write_text(json.dumps({
                "schema_version": 1, "invocation_id": "integration-operation", "operation": "evaluation",
                "invocation_started_at": (now - timedelta(seconds=2)).isoformat(), "created_at": now.isoformat(),
                "binding": {"bundle": str(bundle.resolve()), "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                            "benchmark_sha256": manifest["benchmark_sha256"], "task_ids": ["task-0001"]},
                "qa": [{"question": "Use the integration fixture configuration?", "answer": "Yes, local pilot.",
                        "user_reply_ref": "integration-fixture", "answered_at": (now - timedelta(seconds=1)).isoformat()}],
                "settings": {"profile": "local-pilot", "model": "fixture-request", "effort": "high", "wall_seconds": 5},
            }))
            run = runner.run_bundle(bundle, model="fixture-request", effort="high",
                                    wall_seconds=5, isolation="instruction-only", codex=str(fake),
                                    profile="local-pilot", configuration=configuration, invocation_id="integration-operation",
                                    work_root=root / "task-temp")
            scorer.score(bundle, run)
            grading = json.loads((run / "grading.json").read_text())
            self.assertEqual(grading["model_reported"], "fixture-request")
            self.assertEqual(grading["tasks"][0]["answer_status"], "PASS")
            self.assertEqual(grading["tasks"][0]["full_task_status"], "REVIEW")
            record = json.loads((run / "run.json").read_text())
            self.assertEqual(Path(record["work_root"]), (root / "task-temp").resolve())
            attempt = record["attempts"][0]
            self.assertEqual(Path(attempt["workspace_dir"]).parent, Path(record["work_root"]))
            reviews = root / "reviews.json"
            reviews.write_text(json.dumps({"schema_version":1,"run_id":record["run_id"],"reviews":[{
                "id":attempt["id"],"statement_sha256":attempt["statement_sha256"],
                "private_sha256":attempt["private_sha256"],"submission_sha256":attempt["submission_sha256"],
                "answer_correct":True,"derivation_correct":True,"reviewer":"integration fixture",
                "notes":"Integer addition and the submitted justification are checked.",
            }]}))
            scorer.score(bundle, run, reviews)
            grading = json.loads((run / "grading.json").read_text())
            self.assertEqual(grading["tasks"][0]["full_task_status"], "PASS")
            final = run / attempt["submission_file"]
            self.assertEqual(hashlib.sha256(final.read_bytes()).hexdigest(), attempt["submission_sha256"])
            final.write_text(json.dumps({"answer":"999","derivation":"Incorrect.","complete":True}))
            with self.assertRaisesRegex(ValueError, "submission changed"):
                scorer.score(bundle, run, reviews)


# Test entry point
if __name__ == "__main__":
    unittest.main()
