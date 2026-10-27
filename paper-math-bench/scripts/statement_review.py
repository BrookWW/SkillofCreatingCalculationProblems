#!/usr/bin/env python3
"""Freeze anonymous review inputs and validate exact-version statement reviews.

Role declarations and semantic findings are review evidence, not machine proofs
or enforced filesystem isolation. Reader inputs contain no private reference.
"""

# Contents: 1. Records and bindings; 2. Immutable packets; 3. Review gate; 4. CLI.

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any


# 1. Records and bindings

POLICY = "statement-review-v1"
SEMANTIC_FIELDS = ("objects", "domains", "quantifiers", "assumptions", "conventions",
                   "target", "answer_contract")
BINDINGS = ("id", "stable_id", "statement_sha256", "solution_sha256", "private_sha256")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def schema_hash(schema: dict) -> str:
    if not isinstance(schema, dict) or not schema:
        raise ValueError("Answer interface must be a nonempty JSON schema object")
    return _sha(_canonical(schema))


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"Invalid SHA-256 for {label}")
    return value


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate review key: {key}")
        result[key] = value
    return result


def _read(path: Path) -> tuple[dict, bytes]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Missing regular review file: {path}")
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_object,
                       parse_constant=lambda value: (_ for _ in ()).throw(
                           ValueError(f"Nonfinite review value: {value}")))
    if not isinstance(value, dict):
        raise ValueError(f"Review file must be an object: {path}")
    return value, raw


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def _regular_child(root: Path, *parts: str) -> Path:
    """Read review-controlled descendants without traversing symlinks."""
    cursor = root
    if cursor.is_symlink() or not cursor.is_dir():
        raise ValueError(f"Unsafe review directory: {cursor}")
    for part in parts:
        if not part or part in {".", ".."} or "/" in part or "\\" in part:
            raise ValueError("Unsafe review input path component")
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"Symlink in review input path: {cursor}")
    if not cursor.is_file():
        raise ValueError(f"Missing regular review input: {cursor}")
    return cursor


def _origin_path(bundle: Path, stable_id: str) -> Path:
    folder = bundle / ".statement-review-origins"
    if folder.is_symlink():
        raise ValueError("Review origin directory must not be a symlink")
    return folder / (_sha(stable_id.encode("utf-8")) + ".json")


def _origin_record(stable_id: str, original: dict, binding: dict) -> dict:
    return {"schema_version": 1, "policy": POLICY, "stable_id": stable_id,
            "origin_packet": binding, "original_sha256": _sha(_canonical(original))}


def _validate_origin(bundle: Path, stable_id: str, original: dict, binding: dict) -> dict:
    path = _origin_path(bundle, stable_id)
    value, _ = _read(path)
    if value != _origin_record(stable_id, original, binding):
        raise ValueError(f"Review original baseline conflicts with its pinned bundle origin: {stable_id}")
    return value


def _task_snapshot(bundle: Path, task: dict, answer_hash: str) -> dict:
    task_id = _text(task.get("id"), "task id")
    if re.fullmatch(r"task-[0-9]{4,}", task_id) is None:
        raise ValueError(f"Invalid review task ID: {task_id}")
    private_path = bundle / "private" / (task_id + ".json")
    private, private_raw = _read(private_path)
    prompt = task.get("prompt")
    if not isinstance(prompt, bytes):
        raise ValueError(f"Review task {task_id} needs its exact prompt bytes")
    prompt_path = bundle / "public" / task_id / "prompt.md"
    public, _ = _read(bundle / "public" / task_id / "task.json")
    if prompt_path.is_symlink() or prompt_path.read_bytes() != prompt or \
            public.get("id") != task_id or public.get("statement_sha256") != task.get("statement_sha256"):
        raise ValueError(f"Public review inputs changed: {task_id}")
    result = {key: task[key] for key in BINDINGS}
    result.update(answer_schema_sha256=answer_hash, prompt_utf8=prompt.decode("utf-8"),
                  private_json_utf8=private_raw.decode("utf-8"))
    _validate_snapshot(result)
    if private.get("rubric", {}).get("reference_status") != "verified" or \
            private.get("rubric", {}).get("review_status") != "reviewed":
        raise ValueError(f"Reference and rubric must be verified before review: {task_id}")
    return result


def _validate_snapshot(item: dict) -> None:
    if not isinstance(item, dict):
        raise ValueError("Packet task snapshot must be an object")
    for key in ("id", "stable_id"):
        _text(item.get(key), "snapshot " + key)
    for key in ("statement_sha256", "solution_sha256", "private_sha256", "answer_schema_sha256"):
        _hash(item.get(key), "snapshot " + key)
    prompt = _text(item.get("prompt_utf8"), "snapshot prompt")
    private_text = _text(item.get("private_json_utf8"), "snapshot private reference")
    if _sha(prompt.encode("utf-8")) != item["statement_sha256"] or \
            _sha(private_text.encode("utf-8")) != item["private_sha256"]:
        raise ValueError("Stale original prompt/private snapshot hash")
    private = json.loads(private_text, object_pairs_hook=_object)
    if not isinstance(private, dict):
        raise ValueError("Original private snapshot must contain an object")
    for key in ("id", "stable_id", "statement_sha256", "solution_sha256"):
        if private.get(key) != item[key]:
            raise ValueError(f"Original private snapshot has mismatched {key}")
    reference = private.get("reference_solution_tex")
    if not isinstance(reference, str) or _sha(reference.encode("utf-8")) != item["solution_sha256"]:
        raise ValueError("Stale original reference snapshot hash")
    if private.get("rubric", {}).get("reference_status") != "verified" or \
            private.get("rubric", {}).get("review_status") != "reviewed":
        raise ValueError("Original baseline reference and rubric must be verified")


# 2. Immutable packets

def _packet(path: Path, *, depth: int = 0) -> tuple[dict, bytes]:
    if depth > 8:
        raise ValueError("Review baseline chain is cyclic or too deep")
    value, raw = _read(path)
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1 or \
            value.get("policy") != POLICY:
        raise ValueError("Unsupported statement review packet")
    _hash(value.get("manifest_sha256"), "packet manifest")
    answer_hash = schema_hash(value.get("answer_schema"))
    if answer_hash != value.get("answer_schema_sha256"):
        raise ValueError("Stale packet answer interface hash")
    records = value.get("tasks")
    if not isinstance(records, list) or not records:
        raise ValueError("Review packet needs nonempty tasks")
    seen_ids, seen_stable = set(), set()
    for record in records:
        _validate_snapshot(record)
        original = record.get("original")
        _validate_snapshot(original)
        if record["stable_id"] != original["stable_id"] or \
                record["answer_schema_sha256"] != answer_hash or \
                original["answer_schema_sha256"] != answer_hash:
            raise ValueError("Baseline identity or answer interface changed")
        if record["id"] in seen_ids or record["stable_id"] in seen_stable:
            raise ValueError("Duplicate packet task identity")
        seen_ids.add(record["id"])
        seen_stable.add(record["stable_id"])
    parent = value.get("baseline_packet")
    if parent is not None:
        if not isinstance(parent, dict):
            raise ValueError("Invalid baseline packet binding")
        parent_path = Path(_text(parent.get("path"), "baseline packet path"))
        if not parent_path.is_absolute():
            raise ValueError("Baseline packet path must be absolute")
        prior, prior_raw = _packet(parent_path, depth=depth + 1)
        if _sha(prior_raw) != _hash(parent.get("sha256"), "baseline packet"):
            raise ValueError("Stale baseline packet hash")
        old = {item["stable_id"]: item["original"] for item in prior["tasks"]}
        for record in records:
            if old.get(record["stable_id"]) != record["original"]:
                raise ValueError("Original baseline was replaced or belongs to another task")
    else:
        for record in records:
            if {key: value for key, value in record.items() if key != "original"} != record["original"]:
                raise ValueError("Initial review packet must freeze its current original version")
    return value, raw


def _root_origin(path: Path) -> tuple[dict, dict]:
    """Return the first packet binding in the declared baseline lineage."""
    packet, raw = _packet(path)
    while packet.get("baseline_packet") is not None:
        path = Path(packet["baseline_packet"]["path"])
        packet, raw = _packet(path)
    return {"path": str(path), "sha256": _sha(raw)}, packet


def _reader_inputs(packet_path: Path, task: dict, answer_schema: dict) -> None:
    task_id = task["id"]
    root = packet_path.parent
    prompt_path = _regular_child(root, "reader", task_id, "prompt.md")
    schema_path = _regular_child(root, "reader", task_id, "answer-schema.json")
    names = {path.name for path in prompt_path.parent.iterdir()}
    logical_names = {name for name in names if not (name.startswith("._") and name[2:] in names)}
    if logical_names != {"prompt.md", "answer-schema.json"}:
        raise ValueError(f"Unexpected files in anonymous reader inputs: {task_id}")
    if prompt_path.read_bytes() != task["prompt_utf8"].encode("utf-8"):
        raise ValueError(f"Anonymous reader prompt changed: {task_id}")
    schema, _ = _read(schema_path)
    if schema != answer_schema or schema_hash(schema) != task["answer_schema_sha256"]:
        raise ValueError(f"Anonymous reader answer interface changed: {task_id}")


def prepare_review(bundle: Path, destination: Path, tasks: list[dict], manifest_hash: str,
                   answer_schema: dict, *, baseline_packet: Path | None = None) -> Path:
    """Create a new packet, preserving the original baseline across revisions."""
    bundle = Path(bundle).expanduser().resolve()
    destination = Path(destination).expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Review destination already exists: {destination}")
    _hash(manifest_hash, "manifest")
    if _sha((bundle / "manifest.json").read_bytes()) != manifest_hash:
        raise ValueError("Bundle manifest changed before review preparation")
    answer_hash = schema_hash(answer_schema)
    prior_binding, original_map, root_binding, root_packet = None, None, None, None
    if baseline_packet is not None:
        baseline_path = Path(baseline_packet).expanduser().absolute()
        previous, previous_raw = _packet(baseline_path)
        if previous["answer_schema_sha256"] != answer_hash:
            raise ValueError("Editorial revision cannot change the answer interface")
        original_map = {item["stable_id"]: item["original"] for item in previous["tasks"]}
        prior_binding = {"path": str(baseline_path), "sha256": _sha(previous_raw)}
        root_binding, root_packet = _root_origin(baseline_path)
    records = []
    for task in tasks:
        current = _task_snapshot(bundle, task, answer_hash)
        original = current.copy() if original_map is None else original_map.get(current["stable_id"])
        if original is None:
            raise ValueError(f"Missing original baseline for {current['stable_id']}")
        marker = _origin_path(bundle, current["stable_id"])
        if marker.exists() or marker.is_symlink():
            if baseline_packet is None:
                raise ValueError(f"Original baseline is already pinned; use --baseline-packet: {current['stable_id']}")
            _validate_origin(bundle, current["stable_id"], original, root_binding)
        if root_packet is not None:
            _validate_origin(Path(root_packet["bundle"]), current["stable_id"], original, root_binding)
        records.append(dict(current, original=original))
    if not records or len({r["id"] for r in records}) != len(records) or \
            len({r["stable_id"] for r in records}) != len(records):
        raise ValueError("Review preparation needs distinct nonempty tasks")
    packet = {"schema_version": 1, "policy": POLICY,
              "created_at": datetime.now(timezone.utc).isoformat(),
              "bundle": str(bundle), "manifest_sha256": manifest_hash,
              "answer_schema": answer_schema, "answer_schema_sha256": answer_hash,
              "baseline_packet": prior_binding, "tasks": records}
    destination.mkdir(parents=True, exist_ok=False)
    created_markers = []
    try:
        packet_path = destination / "packet.json"
        _write(packet_path, packet)
        for record in records:
            reader = destination / "reader" / record["id"]
            reader.mkdir(parents=True)
            (reader / "prompt.md").write_text(record["prompt_utf8"], encoding="utf-8")
            _write(reader / "answer-schema.json", answer_schema)
        template = {"schema_version": 1, "policy": POLICY, "bundle": str(bundle),
                    "manifest_sha256": manifest_hash,
                    "packet": {"path": str(packet_path), "sha256": _sha(packet_path.read_bytes())},
                    "author_agent_id": "", "reviews": []}
        for record in records:
            original = record["original"]
            review = {key: record[key] for key in BINDINGS}
            review["answer_schema_sha256"] = answer_hash
            review.update({"baseline_" + key: original[key] for key in
                           ("statement_sha256", "solution_sha256", "private_sha256")})
            review["reader"] = {"agent_id": "", "fresh_context": False,
                                "input_scope": "statement-and-answer-interface",
                                "status": "PENDING", "restatement": "", "issues": []}
            review["semantic_check"] = {"agent_id": "", "status": "PENDING",
                                        "meaning_preserved": False, "no_solution_hints": False,
                                        "evidence": {key: "" for key in SEMANTIC_FIELDS}, "issues": []}
            template["reviews"].append(review)
        _write(destination / "review-template.json", template)
        if root_binding is None:
            root_binding = {"path": str(packet_path), "sha256": _sha(packet_path.read_bytes())}
        for record in records:
            marker = _origin_path(bundle, record["stable_id"])
            marker.parent.mkdir(exist_ok=True)
            if marker.exists() or marker.is_symlink():
                _validate_origin(bundle, record["stable_id"], record["original"], root_binding)
            else:
                _write(marker, _origin_record(record["stable_id"], record["original"], root_binding))
                created_markers.append(marker)
        return packet_path
    except BaseException:
        for marker in created_markers:
            marker.unlink()
        shutil.rmtree(destination)
        raise


# 3. Review gate

def validate_for_run(bundle: Path, tasks: list[dict], manifest_hash: str,
                     answer_schema: dict, review_path: Path) -> dict:
    """Return a frozen, JSON-serializable audit only for exact passing reviews."""
    bundle = Path(bundle).expanduser().resolve()
    review_path = Path(review_path).expanduser().absolute()
    review, review_raw = _read(review_path)
    if type(review.get("schema_version")) is not int or review["schema_version"] != 1 or \
            review.get("policy") != POLICY:
        raise ValueError("Unsupported statement review schema/policy")
    if review.get("bundle") != str(bundle) or review.get("manifest_sha256") != manifest_hash or \
            _sha((bundle / "manifest.json").read_bytes()) != manifest_hash:
        raise ValueError("Stale statement review bundle/manifest binding")
    packet_binding = review.get("packet")
    if not isinstance(packet_binding, dict):
        raise ValueError("Statement review needs an original packet binding")
    packet_path = Path(_text(packet_binding.get("path"), "review packet path"))
    if not packet_path.is_absolute():
        raise ValueError("Review packet path must be absolute")
    packet, packet_raw = _packet(packet_path)
    packet_hash = _sha(packet_raw)
    if packet_hash != _hash(packet_binding.get("sha256"), "review packet"):
        raise ValueError("Stale statement review packet hash")
    answer_hash = schema_hash(answer_schema)
    if packet.get("bundle") != str(bundle) or packet["manifest_sha256"] != manifest_hash or \
            packet["answer_schema_sha256"] != answer_hash:
        raise ValueError("Stale statement review packet/version or answer interface")
    root_binding, root_packet = _root_origin(packet_path)
    author = _text(review.get("author_agent_id"), "author agent identity")
    records = review.get("reviews")
    if not isinstance(records, list) or not records:
        raise ValueError("Statement review needs nonempty review records")
    by_id = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("id"), str) or record["id"] in by_id:
            raise ValueError("Duplicate or malformed statement review task")
        by_id[record["id"]] = record
    packet_tasks = {item["id"]: item for item in packet["tasks"]}
    selected_ids = {task["id"] for task in tasks}
    if not tasks or not selected_ids <= set(by_id) or set(by_id) != set(packet_tasks):
        raise ValueError("Statement review task selection does not match its packet")
    accepted = []
    for task in tasks:
        current = _task_snapshot(bundle, task, answer_hash)
        record = by_id[task["id"]]
        frozen = packet_tasks.get(task["id"])
        if frozen is None or {key: value for key, value in frozen.items() if key != "original"} != current:
            raise ValueError(f"Stale statement review snapshot: {task['id']}")
        _reader_inputs(packet_path, frozen, answer_schema)
        _validate_origin(bundle, current["stable_id"], frozen["original"], root_binding)
        _validate_origin(Path(root_packet["bundle"]), current["stable_id"], frozen["original"], root_binding)
        for key in BINDINGS + ("answer_schema_sha256",):
            if record.get(key) != current[key]:
                raise ValueError(f"Stale statement review {key}: {task['id']}")
        for key in ("statement_sha256", "solution_sha256", "private_sha256"):
            if record.get("baseline_" + key) != frozen["original"][key]:
                raise ValueError(f"Stale original baseline {key}: {task['id']}")
        reader = record.get("reader")
        semantic = record.get("semantic_check")
        if not isinstance(reader, dict) or not isinstance(semantic, dict):
            raise ValueError("Missing independent reader or semantic review")
        reader_id = _text(reader.get("agent_id"), "reader agent identity")
        checker_id = _text(semantic.get("agent_id"), "semantic checker identity")
        if len({author, reader_id, checker_id}) != 3:
            raise ValueError("Author, independent reader and semantic checker must be distinct agents")
        if reader.get("status") != "PASS" or reader.get("fresh_context") is not True or \
                reader.get("input_scope") != "statement-and-answer-interface" or reader.get("issues") != []:
            raise ValueError(f"Statement reader has not passed or has unresolved issues: {task['id']}")
        _text(reader.get("restatement"), "reader task restatement")
        if semantic.get("status") != "PASS" or semantic.get("meaning_preserved") is not True or \
                semantic.get("no_solution_hints") is not True or semantic.get("issues") != []:
            raise ValueError(f"Meaning preservation has not passed or remains uncertain: {task['id']}")
        evidence = semantic.get("evidence")
        if not isinstance(evidence, dict):
            raise ValueError("Missing before/after semantic preservation evidence")
        for key in SEMANTIC_FIELDS:
            _text(evidence.get(key), "semantic evidence for " + key)
        accepted.append({key: record[key] for key in BINDINGS + ("answer_schema_sha256",)})
    return {"schema_version": 1, "policy": POLICY, "status": "PASS",
            "review_sha256": _sha(review_raw), "packet_sha256": packet_hash,
            "manifest_sha256": manifest_hash, "answer_schema_sha256": answer_hash,
            "tasks": accepted, "review": review, "packet": packet,
            "review_utf8": review_raw.decode("utf-8"), "packet_utf8": packet_raw.decode("utf-8"),
            "origin_packet": root_binding,
            "origins": [_origin_record(task["stable_id"], packet_tasks[task["id"]]["original"], root_binding) for task in tasks],
            "limitations": ["Role identities, fresh-context declarations and mathematical equivalence are review evidence; hashes do not prove them.",
                            "Anonymous reader inputs do not establish enforced filesystem isolation.",
                            "Origin markers preserve the first declared baseline within this bundle lineage; they do not authenticate earlier undeclared history."]}


# 4. CLI

def _runner():
    path = Path(__file__).with_name("run_eval.py")
    spec = importlib.util.spec_from_file_location("_statement_review_runner", path)
    if spec is None or spec.loader is None:
        raise ValueError("Trusted evaluation runner is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="Freeze a new, non-overwriting review packet")
    prepare.add_argument("bundle", type=Path)
    prepare.add_argument("destination", type=Path)
    prepare.add_argument("--baseline-packet", type=Path)
    prepare.add_argument("--ids", nargs="+")
    validate = sub.add_parser("validate", help="Validate final independent reviews without a model call")
    validate.add_argument("bundle", type=Path)
    validate.add_argument("reviews", type=Path)
    validate.add_argument("--ids", nargs="+")
    args = parser.parse_args(argv)
    try:
        runner = _runner()
        bundle = args.bundle.expanduser().resolve()
        _, tasks, manifest_hash = runner._load_bundle(bundle, args.ids, reviewed=True)
        if args.command == "prepare":
            path = prepare_review(bundle, args.destination, tasks, manifest_hash,
                                  runner.SUBMISSION_SCHEMA, baseline_packet=args.baseline_packet)
            print(path)
        else:
            result = validate_for_run(bundle, tasks, manifest_hash, runner.SUBMISSION_SCHEMA, args.reviews)
            print(json.dumps({key: value for key, value in result.items() if key not in {"review", "packet", "review_utf8", "packet_utf8"}}, indent=2))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
