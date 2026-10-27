#!/usr/bin/env python3
"""Run one independent, explicitly configured Codex attempt per benchmark task.

The instruction-only mode copies public inputs to temporary workspaces. It does
not provide a filesystem read allowlist or establish an enforced network boundary.
"""

# Contents (search the numbered section headings below):
# 1. Submission contract and error types
# 2. Bundle integrity and reference validation
# 3. Process control and result metadata
# 4. Independent attempt execution
# 5. Command-line interface

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Iterator, Sequence
import uuid


# 1. Submission contract and error types

SUBMISSION_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "derivation": {"type": "string"},
        "complete": {"type": "boolean"},
    },
    "required": ["answer", "derivation", "complete"],
    "additionalProperties": False,
}
ANSWER_TYPES = {"manual", "exact_integer", "exact_rational", "exact_json", "numeric"}


class BundleError(ValueError):
    """The bundle or requested configuration is invalid."""


@lru_cache(maxsize=1)
def _settings() -> Any:
    source = Path(__file__).resolve().with_name("evaluation_settings.py")
    spec = importlib.util.spec_from_file_location("_paper_math_bench_settings", source)
    if spec is None or spec.loader is None:
        raise BundleError("The evaluation settings validator is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunInterrupted(KeyboardInterrupt):
    """A termination signal interrupted the run."""

    def __init__(self, signum: int):
        self.signum = signum
        super().__init__(f"Interrupted by signal {signum}")


# 2. Bundle integrity and reference validation

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_object(data: bytes, label: str) -> dict[str, Any]:
    def distinct_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=distinct_keys)
    except (UnicodeError, ValueError) as exc:
        raise BundleError(f"Invalid JSON in {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise BundleError(f"{label} must contain a JSON object")
    return value


def _safe_path(root: Path, relative: Any, *, directory: bool = False) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or "\0" in relative:
        raise BundleError(f"Unsafe bundle path: {relative!r}")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in {".", ".."} for part in relative.split("/")):
        raise BundleError(f"Unsafe bundle path: {relative!r}")
    candidate = root.joinpath(*pure.parts)
    cursor = root
    for part in pure.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise BundleError(f"Symlinks are not accepted in bundle paths: {relative}")
    if not candidate.resolve().is_relative_to(root):
        raise BundleError(f"Bundle path escapes its root: {relative}")
    if not (candidate.is_dir() if directory else candidate.is_file()):
        raise BundleError(f"Missing {'directory' if directory else 'file'}: {relative}")
    return candidate


def _require_hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise BundleError(f"Invalid SHA-256 for {label}")
    return value


@lru_cache(maxsize=1)
def _reference_checker() -> Any:
    """Load the reference validator from the trusted sibling scoring script."""
    source = Path(__file__).resolve().with_name("score_run.py")
    spec = importlib.util.spec_from_file_location("_paper_math_bench_reference_checker", source)
    if spec is None or spec.loader is None:
        raise BundleError("The trusted scoring script is unavailable")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except (OSError, ImportError) as exc:
        raise BundleError(f"The trusted scoring script is unavailable: {exc}") from exc
    return module.automatic_answer


@lru_cache(maxsize=1)
def _statement_reviewer() -> Any:
    """Load the trusted exact-version review validator."""
    source = Path(__file__).resolve().with_name("statement_review.py")
    spec = importlib.util.spec_from_file_location("_paper_math_bench_statement_review", source)
    if spec is None or spec.loader is None:
        raise BundleError("The statement review validator is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validate_rubric(private: dict[str, Any], task_id: str, *, reviewed: bool) -> None:
    rubric = private.get("rubric")
    if not isinstance(rubric, dict):
        raise BundleError(f"Missing rubric for {task_id}")
    if rubric.get("answer_type") not in ANSWER_TYPES:
        raise BundleError(f"Invalid answer_type in rubric for {task_id}")
    if not isinstance(rubric.get("requires_proof"), bool):
        raise BundleError(f"Missing boolean requires_proof in rubric for {task_id}")
    if "accepted_answer" not in rubric:
        raise BundleError(f"Missing accepted_answer in rubric for {task_id}")
    if reviewed:
        if rubric.get("review_status") != "reviewed":
            raise BundleError(f"Rubric for {task_id} must be reviewed before a real run")
        if rubric.get("reference_status") != "verified":
            raise BundleError(f"Reference for {task_id} must be verified before a real run")
        for key in ("requirements", "verification_evidence"):
            items = rubric.get(key)
            if not isinstance(items, list) or not items or any(
                not isinstance(item, str) or not item.strip() for item in items
            ):
                raise BundleError(f"Reviewed rubric for {task_id} needs nonempty {key}")
        try:
            _reference_checker()("0", rubric)
        except (ValueError, TypeError, ArithmeticError) as exc:
            raise BundleError(f"Invalid grading contract for {task_id}: {exc}") from exc


def _load_bundle(bundle: Path, ids: Sequence[str] | None, *, reviewed: bool) -> tuple[dict, list[dict], str]:
    manifest_bytes = _safe_path(bundle, "manifest.json").read_bytes()
    manifest = _json_object(manifest_bytes, "manifest.json")
    if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        raise BundleError("Unsupported manifest schema_version; expected 1")
    _require_hash(manifest.get("benchmark_sha256"), "benchmark")
    if not isinstance(manifest.get("source_tex"), str) or not manifest["source_tex"]:
        raise BundleError("Missing source_tex in manifest")
    entries = manifest.get("tasks")
    if not isinstance(entries, list) or not entries:
        raise BundleError("The manifest must contain at least one task")
    requested = list(ids) if ids is not None else None
    if requested is not None and (not requested or len(set(requested)) != len(requested)):
        raise BundleError("Task selection must contain distinct task IDs")
    known: set[str] = set()
    stable_ids: set[str] = set()
    tasks = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise BundleError("Each manifest task must be an object")
        task_id = entry.get("id")
        if not isinstance(task_id, str) or not re.fullmatch(r"task-[0-9]{4,}", task_id):
            raise BundleError(f"Invalid task ID: {task_id!r}")
        if task_id in known:
            raise BundleError(f"Duplicate task ID: {task_id}")
        known.add(task_id)
        stable_id = entry.get("stable_id")
        if not isinstance(stable_id, str) or not stable_id or stable_id in stable_ids:
            raise BundleError(f"Missing or duplicate stable_id for {task_id}")
        stable_ids.add(stable_id)
        statement_hash = _require_hash(entry.get("statement_sha256"), task_id + " statement")
        solution_hash = _require_hash(entry.get("solution_sha256"), task_id + " solution")
        _safe_path(bundle, entry.get("public_dir"), directory=True)
        private_file = _safe_path(bundle, entry.get("private_file"))
        if entry["public_dir"] != f"public/{task_id}" or entry["private_file"] != f"private/{task_id}.json":
            raise BundleError(f"Unexpected public/private path for {task_id}")
        prompt = _safe_path(bundle, f"public/{task_id}/prompt.md").read_bytes()
        public_bytes = _safe_path(bundle, f"public/{task_id}/task.json").read_bytes()
        public = _json_object(public_bytes, f"{task_id}/task.json")
        private_bytes = private_file.read_bytes()
        private = _json_object(private_bytes, f"private/{task_id}.json")
        if set(public) != {"schema_version", "id", "statement_sha256"}:
            raise BundleError(f"Unexpected public metadata fields for {task_id}")
        for record, label in ((public, "public"), (private, "private")):
            if type(record.get("schema_version")) is not int or record["schema_version"] != 1:
                raise BundleError(f"Invalid {label} schema_version for {task_id}")
            if record.get("id") != task_id or record.get("statement_sha256") != statement_hash:
                raise BundleError(f"Stale {label} statement metadata for {task_id}")
        if _sha256(prompt) != statement_hash:
            raise BundleError(f"Stale statement hash for {task_id}")
        try:
            prompt.decode("utf-8")
        except UnicodeError as exc:
            raise BundleError(f"Prompt for {task_id} must be UTF-8") from exc
        solution = private.get("reference_solution_tex")
        if private.get("stable_id") != stable_id or private.get("solution_sha256") != solution_hash:
            raise BundleError(f"Stale private gold metadata for {task_id}")
        if not isinstance(solution, str) or _sha256(solution.encode("utf-8")) != solution_hash:
            raise BundleError(f"Stale private gold hash for {task_id}")
        selected = requested is None or task_id in requested
        _validate_rubric(private, task_id, reviewed=reviewed and selected)
        if selected:
            tasks.append({
                "id": task_id, "stable_id": stable_id,
                "statement_sha256": statement_hash, "solution_sha256": solution_hash,
                "private_sha256": _sha256(private_bytes), "prompt": prompt,
                "public_bytes": public_bytes,
            })
    if requested is not None and set(requested) - known:
        raise BundleError("Unknown task IDs: " + ", ".join(sorted(set(requested) - known)))
    return manifest, tasks, _sha256(manifest_bytes)


# 3. Process control and result metadata

def _write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _claim_configuration(runs: Path, configuration_hash: str,
                         configuration_semantic_hash: str, run_id: str) -> None:
    """Reserve one real invocation atomically, including records predating claims."""
    for directory in runs.iterdir():
        if directory.name.startswith(".") or not directory.is_dir():
            continue
        previous = directory / "run.json"
        if not previous.is_file():
            continue
        try:
            record = _json_object(previous.read_bytes(), str(previous))
        except (OSError, ValueError) as exc:
            raise BundleError(f"Cannot validate previous configuration use: {previous}") from exc
        previous_evidence = record.get("configuration_evidence")
        previous_semantic_hash = record.get("configuration_semantic_sha256")
        if previous_semantic_hash is None and isinstance(previous_evidence, dict):
            previous_semantic_hash = _settings().semantic_hash(previous_evidence)
        if record.get("dry_run") is False and (
            previous_semantic_hash == configuration_semantic_hash
            or record.get("configuration_sha256") == configuration_hash
        ):
            raise BundleError("This configuration already recorded a real invocation; record current-operation evidence for a new invocation")
    claims = runs / ".configuration-uses"
    if claims.is_symlink():
        raise BundleError("The configuration usage directory must not be a symlink")
    claims.mkdir(exist_ok=True)
    if (claims / (configuration_hash + ".json")).exists():
        raise BundleError("This configuration already recorded a real invocation; record current-operation evidence for a new invocation")
    try:
        with (claims / (configuration_semantic_hash + ".json")).open("x", encoding="utf-8") as stream:
            json.dump({"configuration_sha256": configuration_hash,
                       "configuration_semantic_sha256": configuration_semantic_hash, "run_id": run_id,
                       "recorded_at": _utc_now()}, stream)
            stream.write("\n")
    except FileExistsError as exc:
        raise BundleError("This configuration already recorded a real invocation; record current-operation evidence for a new invocation") from exc


def _temporary_parent(bundle: Path, *, work_root: str | Path | None = None,
                      source_tex: str | None = None) -> Path:
    """Validate an explicit work root, or retain the external temporary default."""
    if work_root is not None:
        if isinstance(work_root, str) and not work_root.strip():
            raise BundleError("work_root must name a directory")
        try:
            parent = Path(work_root).expanduser().resolve()
            if parent.is_relative_to(bundle) or bundle.is_relative_to(parent):
                raise BundleError("work_root must be separate from the evaluation bundle")
            if source_tex is not None:
                source = Path(source_tex).expanduser().resolve()
                if source.is_relative_to(parent):
                    raise BundleError("work_root must not contain the manuscript source")
            parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".paper-math-bench-check-", dir=parent) as check:
                (Path(check) / "writable").write_bytes(b"")
        except (OSError, ValueError, TypeError, RuntimeError) as exc:
            raise BundleError(f"Cannot use work_root {work_root!s}: {exc}") from exc
        return parent
    excluded_roots = [Path(__file__).resolve().parents[1]]
    if source_tex is not None:
        excluded_roots.append(Path(source_tex).expanduser().resolve().parent)
    for candidate in (Path(tempfile.gettempdir()), Path("/private/tmp"), Path("/tmp")):
        parent = candidate.resolve()
        if (parent.is_dir() and not parent.is_relative_to(bundle)
                and not any(parent.is_relative_to(root) for root in excluded_roots)):
            return parent
    raise BundleError("No temporary directory is available outside the bundle, skill package, and source folder")


def _command(codex: str, model: str, effort: str, workspace: Path, schema: Path,
             final: Path, native_budget: str | None = None) -> list[str]:
    command = [
        codex, "exec", "--model", model, "--ignore-user-config", "--ephemeral",
        "--json", "--skip-git-repo-check", "--sandbox", "workspace-write", "--cd", str(workspace),
    ]
    overrides = [
        "model_reasoning_effort=" + json.dumps(effort, ensure_ascii=False),
        'approval_policy="never"', 'web_search="disabled"',
        "sandbox_workspace_write.network_access=false", "project_doc_max_bytes=0",
        "memories.use_memories=false", "memories.generate_memories=false",
        "features.memories=false", "features.multi_agent=false", "features.plugins=false",
        "features.remote_plugin=false", "features.apps=false", "mcp_servers={}",
    ]
    if native_budget:
        overrides.append(native_budget)
    for override in overrides:
        command.extend(["-c", override])
    return command + ["--output-schema", str(schema), "--output-last-message", str(final), "-"]


def _stop_group(process: subprocess.Popen) -> None:
    """Terminate the Unix process group, including surviving tool children."""
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        process.kill()
    process.wait()
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None and not stream.closed:
            stream.close()


def _version(codex: str, *, env: dict[str, str] | None = None) -> tuple[str | None, str | None]:
    process = None
    try:
        process = subprocess.Popen([codex, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   env=env, start_new_session=(os.name == "posix"))
        stdout, stderr = process.communicate(timeout=10)
        if process.returncode != 0:
            return None, f"Codex --version exited {process.returncode}: {stderr.decode('utf-8', 'replace').strip()}"
        version = stdout.decode("utf-8", "replace").strip()
        return (version, None) if version else (None, "Codex --version returned no version")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    finally:
        if process is not None:
            _stop_group(process)


def _budget_preflight(codex: str, override: str, run_dir: Path,
                      *, env: dict[str, str] | None = None) -> dict:
    """Check local feature acceptance without sending a solver request."""
    command = [codex, "-c", override, "features", "list"]
    process = None
    result = {"command": command, "accepted": False, "error": None,
              "stdout_file": "budget-preflight.stdout.txt", "stderr_file": "budget-preflight.stderr.txt"}
    stdout = stderr = b""
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   env=env, start_new_session=(os.name == "posix"))
        stdout, stderr = process.communicate(timeout=10)
        feature_enabled = any(re.fullmatch(r"rollout_budget\s+.+\s+true\s*", line)
                              for line in stdout.decode("utf-8", "replace").splitlines())
        result["accepted"] = process.returncode == 0 and feature_enabled
        if not result["accepted"]:
            result["error"] = ("Native rollout budget configuration was not accepted: "
                               + stderr.decode("utf-8", "replace").strip())
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["error"] = f"Native rollout budget preflight failed: {exc}"
    finally:
        if process is not None:
            _stop_group(process)
        (run_dir / result["stdout_file"]).write_bytes(stdout)
        (run_dir / result["stderr_file"]).write_bytes(stderr)
    return result


def _is_budget_exhaustion(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_is_budget_exhaustion(item) for item in value.values())
    if isinstance(value, list):
        return any(_is_budget_exhaustion(item) for item in value)
    return isinstance(value, str) and (
        value in {"sessionBudgetExceeded", "session_budget_exceeded"}
        or "shared rollout token budget exhausted" in value.lower()
    )


def _event_metadata(path: Path) -> dict:
    result: dict[str, Any] = {"usage": None, "model_reported": None, "effort_reported": None,
                              "budget_exhausted": False,
                              "event_errors": [], "unparsed_event_lines": 0}
    usage_events = []
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except ValueError:
                result["unparsed_event_lines"] += 1
                continue
            if not isinstance(event, dict):
                result["unparsed_event_lines"] += 1
                continue
            if isinstance(event.get("usage"), dict):
                usage_events.append(event["usage"])
            candidates = [event]
            candidates.extend(event[key] for key in ("session", "metadata", "thread", "turn")
                              if isinstance(event.get(key), dict))
            for item in candidates:
                if isinstance(item.get("model"), str):
                    result["model_reported"] = item["model"]
                for key in ("model_reasoning_effort", "reasoning_effort", "effort"):
                    if isinstance(item.get(key), str):
                        result["effort_reported"] = item[key]
            if event.get("type") in {"turn.failed", "error"}:
                result["event_errors"].append(event.get("error", event.get("message", event["type"])))
                result["budget_exhausted"] = result["budget_exhausted"] or _is_budget_exhaustion(event)
    if usage_events:
        result["usage"] = usage_events[-1] if len(usage_events) == 1 else usage_events
    result["total_input_output_tokens"] = _settings().measured_total(result["usage"])
    return result


def _configuration_mismatch(attempt: dict, model: str, effort: str) -> dict:
    """Unknown runtime metadata stays unknown; differing reported settings need review."""
    mismatch = {}
    for field, requested in (("model", model), ("effort", effort)):
        reported = attempt.get(field + "_reported")
        if reported is not None and reported != requested:
            mismatch[field] = {"requested": requested, "reported": reported}
    return mismatch


def _submission_error(path: Path) -> str | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        return f"Final response is not a JSON submission: {exc}"
    if not isinstance(value, dict) or set(value) != {"answer", "derivation", "complete"}:
        return "Final response must contain exactly answer, derivation, and complete"
    if not isinstance(value["answer"], str) or not isinstance(value["derivation"], str) or type(value["complete"]) is not bool:
        return "Final response has invalid answer, derivation, or complete types"
    return None


@contextmanager
def _interrupt_handlers() -> Iterator[None]:
    previous = {}
    if threading.current_thread() is threading.main_thread():
        def interrupt(signum: int, _frame: Any) -> None:
            raise RunInterrupted(signum)
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, interrupt)
    try:
        yield
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


# 4. Independent attempt execution

def run_bundle(bundle: str | Path, *, model: str | None = None, effort: str | None = None,
               wall_seconds: float | None = None, isolation: str,
               profile: str | None = None, configuration: str | Path | None = None,
               invocation_id: str | None = None, ids: Sequence[str] | None = None,
               dry_run: bool = False, codex: str = "codex",
               work_root: str | Path | None = None,
               statement_reviews: str | Path | None = None,
               trial_purpose: str = "formal") -> Path:
    """Validate a bundle and persist serial attempts; return its run directory."""
    if isolation != "instruction-only":
        raise BundleError("Only instruction-only isolation is supported")
    if not isinstance(codex, str) or not codex.strip():
        raise BundleError("codex must name an executable")
    if trial_purpose not in {"formal", "diagnostic"}:
        raise BundleError("trial_purpose must be formal or diagnostic")
    if "/" in codex or "\\" in codex:
        codex = str(Path(codex).expanduser().resolve())
    if os.name != "posix" and not dry_run:
        raise BundleError("Real runs require Unix process-group termination support")
    bundle = Path(bundle).expanduser().resolve()
    manifest, tasks, manifest_hash = _load_bundle(bundle, ids, reviewed=not dry_run)
    try:
        selected = _settings().resolve(
            configuration=configuration, invocation_id=invocation_id, bundle=bundle,
            manifest_sha256=manifest_hash, benchmark_sha256=manifest["benchmark_sha256"],
            task_ids=[task["id"] for task in tasks], profile=profile, model=model,
            effort=effort, wall_seconds=wall_seconds, required=not dry_run,
        )
    except (OSError, ValueError, TypeError) as exc:
        raise BundleError(str(exc)) from exc
    operation = (selected["configuration_evidence"] or {}).get("operation")
    review_required = operation == "authoring" and trial_purpose == "formal"
    review_snapshot = None
    if statement_reviews is not None:
        try:
            review_snapshot = _statement_reviewer().validate_for_run(
                bundle, tasks, manifest_hash, SUBMISSION_SCHEMA,
                Path(statement_reviews).expanduser().resolve(),
            )
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise BundleError(f"Statement review gate: {exc}") from exc
    elif review_required and not dry_run:
        raise BundleError("Formal authoring trials require --statement-reviews for the exact verified version")
    profile = selected["profile"]
    model, effort, wall_seconds = selected["model"], selected["effort"], selected["wall_seconds"]
    native_budget = _settings().native_budget_override(selected["budget"])
    runtime_instructions = _settings().budget_instructions(selected["budget"], profile=profile)
    temp_parent = _temporary_parent(bundle, work_root=work_root, source_tex=manifest["source_tex"])
    temporary_environment = {key: str(temp_parent) for key in ("TMPDIR", "TMP", "TEMP")}
    child_environment = dict(os.environ, **temporary_environment)
    runs = bundle / "runs"
    if runs.is_symlink():
        raise BundleError("The runs directory must not be a symlink")
    runs.mkdir(exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid.uuid4().hex
    if not dry_run:
        _claim_configuration(runs, selected["configuration_sha256"],
                             selected["configuration_semantic_sha256"], run_id)
    run_dir = runs / run_id
    run_dir.mkdir()
    record = {
        "schema_version": 1, "run_id": run_id, "created_at": _utc_now(), "completed_at": None,
        "trial_purpose": trial_purpose,
        "statement_review": {
            "required": review_required,
            "status": "PASS" if review_snapshot is not None else "pending" if review_required else "not-required",
            "file": "statement-review.json" if review_snapshot is not None else None,
            "sha256": None,
        },
        "benchmark_sha256": manifest["benchmark_sha256"], "manifest_sha256": manifest_hash,
        "answer_schema_sha256": _sha256(json.dumps(
            SUBMISSION_SCHEMA, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")),
        "model_requested": model, "effort_requested": effort, "wall_seconds": wall_seconds,
        "profile": profile, "budget": selected["budget"],
        "configuration_evidence": selected["configuration_evidence"],
        "configuration_sha256": selected["configuration_sha256"],
        "configuration_semantic_sha256": selected["configuration_semantic_sha256"],
        "profile_snapshot": selected["profile_snapshot"], "budget_preflight": None,
        "work_root_requested": str(work_root) if work_root is not None else None,
        "work_root": str(temp_parent), "controller_dir": None,
        "temporary_environment": temporary_environment,
        "isolation": isolation, "strict_blind": False, "network_enforced": False,
        "sandbox_requested": "workspace-write", "cli_version": None, "cli_version_error": None,
        "controls_requested": {
            "ignore_user_config": True, "ephemeral": True, "web_search": "disabled",
            "sandbox_network_access": False, "project_doc_max_bytes": 0,
            "memories": False, "multi_agent": False, "plugins": False,
            "remote_plugins": False, "apps": False, "mcp_servers": {},
            "native_rollout_budget": native_budget,
        },
        "limitations": [
            "Instruction-only isolation does not restrict reads to the copied public files.",
            "Network, memory, plugin, and MCP settings are requests; managed configuration may affect their enforcement.",
            "Native rollout-budget accounting is unverified; the submission reminder is an instruction, not forced tool choice.",
            "The CLI shell/Python interface differs from Epoch's stateless Python and 30-second tool calls.",
        ],
        "dry_run": dry_run, "status": "planned", "attempts": [],
    }
    if review_snapshot is not None:
        snapshot_path = run_dir / "statement-review.json"
        _write_json(snapshot_path, review_snapshot)
        record["statement_review"]["sha256"] = _sha256(snapshot_path.read_bytes())
    for task in tasks:
        relative = Path("attempts") / task["id"]
        (run_dir / relative).mkdir(parents=True)
        attempt = {key: task[key] for key in ("id", "stable_id", "statement_sha256", "solution_sha256", "private_sha256")}
        attempt.update({
            "status": "planned", "model_requested": model, "effort_requested": effort,
            "model_reported": None, "effort_reported": None, "elapsed_seconds": 0.0,
            "exit_code": None, "command": None, "usage": None, "error": None,
            "error_kind": None, "configuration_mismatch": None,
            "total_input_output_tokens": None, "budget_exhausted": False,
            "submission_sha256": None,
            "workspace_dir": None,
            "execution_prompt_sha256": _sha256(runtime_instructions + task["prompt"]),
            "execution_prompt_file": (relative / "execution-prompt.txt").as_posix(),
            "submission_file": (relative / "final.txt").as_posix(),
            "events_file": (relative / "events.jsonl").as_posix(),
            "stderr_file": (relative / "stderr.txt").as_posix(),
        })
        for key in ("submission_file", "events_file", "stderr_file"):
            (run_dir / attempt[key]).touch()
        (run_dir / attempt["execution_prompt_file"]).write_bytes(runtime_instructions + task["prompt"])
        record["attempts"].append(attempt)
    metadata_path = run_dir / "run.json"
    _write_json(metadata_path, record)
    with _interrupt_handlers():
        try:
            if not dry_run:
                record["cli_version"], record["cli_version_error"] = _version(codex, env=child_environment)
                if record["cli_version_error"]:
                    for attempt in record["attempts"]:
                        attempt.update(status="error", error=record["cli_version_error"])
                    record["status"] = "error"
                    return run_dir
                if native_budget:
                    record["budget_preflight"] = _budget_preflight(codex, native_budget, run_dir,
                                                                   env=child_environment)
                    if not record["budget_preflight"]["accepted"]:
                        for attempt in record["attempts"]:
                            attempt.update(status="error", error=record["budget_preflight"]["error"])
                        record["status"] = "error"
                        return run_dir
            with tempfile.TemporaryDirectory(prefix="paper-math-bench-controller-", dir=temp_parent) as control:
                record["controller_dir"] = control
                schema = Path(control) / "submission.schema.json"
                _write_json(schema, SUBMISSION_SCHEMA)
                for task, attempt in zip(tasks, record["attempts"]):
                    with tempfile.TemporaryDirectory(prefix="paper-math-bench-task-", dir=temp_parent) as temporary:
                        workspace = Path(temporary)
                        attempt["workspace_dir"] = str(workspace)
                        (workspace / "prompt.md").write_bytes(task["prompt"])
                        (workspace / "task.json").write_bytes(task["public_bytes"])
                        command = _command(codex, model, effort, workspace, schema,
                                           run_dir / attempt["submission_file"], native_budget)
                        attempt["command"] = command
                        _write_json(metadata_path, record)
                        if dry_run:
                            continue
                        record["status"] = attempt["status"] = "running"
                        _write_json(metadata_path, record)
                        process = None
                        started = time.monotonic()
                        try:
                            with (run_dir / attempt["events_file"]).open("wb") as events, (run_dir / attempt["stderr_file"]).open("wb") as stderr:
                                process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=events, stderr=stderr,
                                                           cwd=workspace, env=child_environment, start_new_session=True)
                                remaining = (max(0.001, wall_seconds - (time.monotonic() - started))
                                             if wall_seconds is not None else None)
                                process.communicate(input=runtime_instructions + task["prompt"], timeout=remaining)
                            attempt["exit_code"] = process.returncode
                            attempt["status"] = "completed" if process.returncode == 0 else "error"
                            if process.returncode != 0:
                                attempt["error"] = f"Codex exited with code {process.returncode}"
                        except subprocess.TimeoutExpired:
                            attempt.update(status="timeout", error=f"Wall limit of {wall_seconds} seconds exceeded")
                        except OSError as exc:
                            attempt.update(status="error", error=str(exc))
                            with (run_dir / attempt["stderr_file"]).open("a", encoding="utf-8") as stderr:
                                stderr.write(str(exc) + "\n")
                        except KeyboardInterrupt:
                            attempt.update(status="interrupted", error="Run interrupted")
                            raise
                        finally:
                            if process is not None:
                                _stop_group(process)
                                attempt["exit_code"] = process.returncode
                            attempt["submission_sha256"] = _sha256((run_dir / attempt["submission_file"]).read_bytes())
                            attempt["elapsed_seconds"] = time.monotonic() - started
                            attempt.update(_event_metadata(run_dir / attempt["events_file"]))
                            if _is_budget_exhaustion((run_dir / attempt["stderr_file"]).read_text(encoding="utf-8", errors="replace")):
                                attempt["budget_exhausted"] = True
                            if attempt["budget_exhausted"] and attempt["status"] not in {"timeout", "interrupted"}:
                                attempt.update(status="token_limit", error="Native rollout token budget exhausted before a completed final submission")
                            mismatch = _configuration_mismatch(attempt, model, effort)
                            if mismatch:
                                attempt.update(status="error", error_kind="configuration_mismatch",
                                               configuration_mismatch=mismatch,
                                               error="Runtime reported settings differ from the recorded configuration: " + json.dumps(mismatch, sort_keys=True))
                            if attempt["status"] == "completed":
                                error = _submission_error(run_dir / attempt["submission_file"])
                                if error or attempt["event_errors"]:
                                    attempt.update(status="error", error=error or "Codex reported an event error")
                            _write_json(metadata_path, record)
                        if attempt["status"] == "error" and (attempt["exit_code"] != 0 or attempt["error_kind"] == "configuration_mismatch"):
                            for pending in record["attempts"]:
                                if pending["status"] == "planned":
                                    pending.update(status="error", error_kind=attempt["error_kind"],
                                                   error="Not started: the preceding Codex process or configuration failed; the batch was stopped without retry or substitution.")
                            break
            statuses = {attempt["status"] for attempt in record["attempts"]}
            record["status"] = ("planned" if dry_run else "error" if "error" in statuses
                                else "timeout" if "timeout" in statuses else "token_limit"
                                if "token_limit" in statuses else "completed")
        except KeyboardInterrupt:
            record["status"] = "interrupted"
            for attempt in record["attempts"]:
                if attempt["status"] in {"running", "planned"}:
                    attempt.update(status="interrupted", error="Run interrupted")
            raise
        finally:
            for attempt in record["attempts"]:
                if attempt["status"] != "planned" and attempt["submission_sha256"] is None:
                    attempt["submission_sha256"] = _sha256((run_dir / attempt["submission_file"]).read_bytes())
            record["completed_at"] = _utc_now()
            _write_json(metadata_path, record)
    return run_dir


# 5. Command-line interface

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--profile", choices=sorted(_settings().PROFILES),
                        help="Use the configuration's profile, or local-pilot without a configuration")
    parser.add_argument("--configuration", type=Path, help="Current-operation, bundle-bound user-instruction/Q&A JSON")
    parser.add_argument("--invocation-id", help="Caller-supplied identity of the current authoring/evaluation operation")
    parser.add_argument("--model", help=f"Optional override; must match the configuration; default {_settings().DEFAULT_MODEL}")
    parser.add_argument("--effort", help=f"Optional override; must match the configuration/profile; local default {_settings().DEFAULT_EFFORT}")
    parser.add_argument("--wall-seconds", type=float, help="Optional operational timeout, recorded in the configuration")
    parser.add_argument("--isolation", required=True, choices=["instruction-only"])
    parser.add_argument("--ids", nargs="+")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--statement-reviews", type=Path,
                        help="Exact-version independent reader and semantic-preservation review JSON")
    parser.add_argument("--trial-purpose", choices=["formal", "diagnostic"], default="formal",
                        help="Diagnostics are development evidence and cannot supply final screening")
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--work-root",
                        help="Parent for controller/task temporary directories and child TMPDIR/TMP/TEMP")
    args = parser.parse_args(argv)
    try:
        run_dir = run_bundle(args.bundle, model=args.model, effort=args.effort,
                             wall_seconds=args.wall_seconds, isolation=args.isolation,
                             profile=args.profile, configuration=args.configuration,
                             invocation_id=args.invocation_id,
                             ids=args.ids, dry_run=args.dry_run, codex=args.codex,
                             work_root=args.work_root, statement_reviews=args.statement_reviews,
                             trial_purpose=args.trial_purpose)
    except BundleError as exc:
        parser.error(str(exc))
    except KeyboardInterrupt as exc:
        print("Run interrupted; partial metadata and logs were saved.", file=sys.stderr)
        return 128 + exc.signum if isinstance(exc, RunInterrupted) else 130
    print(run_dir)
    status = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))["status"]
    return 0 if status in {"completed", "planned"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
