"""Score frozen submissions, separating execution, self-reports, and mathematical obligations."""

# Contents (search the numbered section headings below):
# 1. Integrity checks and input loading
# 2. Answer normalization and automatic checks
# 3. Review validation and individual grading
# 4. Run assessment and report output
# 5. Command-line interface

from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from functools import lru_cache
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from typing import Any


# 1. Integrity checks and input loading

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: Path) -> Any:
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError(f"JSON input exceeds 8 MiB: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          ValueError(f"Non-finite JSON value: {value}")))


def contained(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError("Manifest paths must be nonempty relative paths.")
    target = (root / value).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError("A manifest path escapes its owning directory.")
    return target


@lru_cache(maxsize=1)
def _statement_review_tools():
    source = Path(__file__).resolve().with_name("statement_review.py")
    spec = importlib.util.spec_from_file_location("_score_statement_review", source)
    if spec is None or spec.loader is None:
        raise ValueError("The statement review validator is unavailable.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_statement_review(run_root: Path, record: dict[str, Any]) -> None:
    """Check frozen review evidence without reading external review packet paths.

    Content hashes preserve the recorded attestations and reviewed versions; they
    do not establish mathematical equivalence or authenticate agent identities.
    """
    if not {"trial_purpose", "statement_review", "answer_schema_sha256"} & record.keys():
        return
    tools = _statement_review_tools()
    purpose = record.get("trial_purpose")
    configuration = record.get("configuration_evidence")
    operation = configuration.get("operation") if isinstance(configuration, dict) else None
    if purpose not in {"formal", "diagnostic"} or operation not in {"authoring", "evaluation"}:
        raise ValueError("Statement review requires a recorded trial purpose and operation.")
    answer_hash = tools._hash(record.get("answer_schema_sha256"), "run answer interface")
    required = operation == "authoring" and purpose == "formal"
    binding = record.get("statement_review")
    if not isinstance(binding, dict) or binding.get("required") is not required:
        raise ValueError("Statement review requirement does not match the recorded operation.")
    if not required and binding.get("status") == "not-required":
        if binding.get("file") is not None or binding.get("sha256") is not None:
            raise ValueError("An optional statement review file must have a passing audit.")
        return
    if binding.get("status") != "PASS":
        raise ValueError("The required or supplied statement review has not passed.")
    audit_path = contained(run_root, binding.get("file"))
    audit, audit_raw = tools._read(audit_path)
    if tools._sha(audit_raw) != tools._hash(binding.get("sha256"), "frozen statement review"):
        raise ValueError("The frozen statement review changed after running.")
    if type(audit.get("schema_version")) is not int or audit["schema_version"] != 1 or \
            audit.get("policy") != tools.POLICY or audit.get("status") != "PASS":
        raise ValueError("The frozen statement review is not a supported passing audit.")
    embedded = {}
    for name in ("review", "packet"):
        raw = tools._text(audit.get(name + "_utf8"), "frozen " + name).encode("utf-8")
        if tools._sha(raw) != tools._hash(audit.get(name + "_sha256"), "frozen " + name):
            raise ValueError("The frozen statement review has a stale " + name + " hash.")
        value = json.loads(raw, object_pairs_hook=unique_object,
                           parse_constant=lambda value: (_ for _ in ()).throw(
                               ValueError("Non-finite frozen review value: " + value)))
        if not isinstance(value, dict) or value != audit.get(name):
            raise ValueError("The frozen statement review has inconsistent " + name + " content.")
        if type(value.get("schema_version")) is not int or value["schema_version"] != 1 or \
                value.get("policy") != tools.POLICY:
            raise ValueError("Unsupported frozen statement review " + name + ".")
        embedded[name] = value
    review, packet = embedded["review"], embedded["packet"]
    if any(value.get("manifest_sha256") != record.get("manifest_sha256")
           for value in (audit, review, packet)):
        raise ValueError("The frozen statement review belongs to another manifest.")
    if review.get("bundle") != packet.get("bundle") or \
            not isinstance(review.get("packet"), dict) or \
            review["packet"].get("sha256") != audit["packet_sha256"]:
        raise ValueError("The frozen statement review packet binding is inconsistent.")
    if tools.schema_hash(packet.get("answer_schema")) != answer_hash or any(
        value.get("answer_schema_sha256") != answer_hash for value in (audit, packet)
    ):
        raise ValueError("The frozen statement review answer interface does not match the run.")

    def by_id(items, label):
        if not isinstance(items, list) or not items:
            raise ValueError("Missing frozen statement review " + label + ".")
        result = {}
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str) or item["id"] in result:
                raise ValueError("Duplicate or malformed frozen statement review " + label + ".")
            result[item["id"]] = item
        return result

    attempts = by_id(record.get("attempts"), "attempts")
    accepted = by_id(audit.get("tasks"), "accepted tasks")
    packet_tasks = by_id(packet.get("tasks"), "packet tasks")
    reviews = by_id(review.get("reviews"), "reviews")
    if set(attempts) != set(accepted) or set(packet_tasks) != set(reviews) or not set(attempts) <= set(packet_tasks):
        raise ValueError("The frozen statement review task selection does not match the run.")
    author = tools._text(review.get("author_agent_id"), "frozen author identity")
    for identity, attempt in attempts.items():
        current, entry = packet_tasks[identity], reviews[identity]
        tools._validate_snapshot(current)
        original = current.get("original")
        tools._validate_snapshot(original)
        if original["stable_id"] != current["stable_id"] or original["answer_schema_sha256"] != answer_hash:
            raise ValueError("The frozen statement review original identity or answer interface changed.")
        expected = {key: attempt.get(key) for key in tools.BINDINGS}
        expected["answer_schema_sha256"] = answer_hash
        if accepted[identity] != expected or any(
            value.get(key) != expected[key]
            for value in (current, entry) for key in expected
        ):
            raise ValueError("The frozen statement review task bindings do not match: " + identity)
        if any(entry.get("baseline_" + key) != original[key]
               for key in ("statement_sha256", "solution_sha256", "private_sha256")):
            raise ValueError("The frozen statement review baseline bindings do not match: " + identity)
        reader, semantic = entry.get("reader"), entry.get("semantic_check")
        if not isinstance(reader, dict) or not isinstance(semantic, dict):
            raise ValueError("Missing frozen reader or semantic review.")
        identities = {author, tools._text(reader.get("agent_id"), "frozen reader identity"),
                      tools._text(semantic.get("agent_id"), "frozen semantic checker identity")}
        if len(identities) != 3 or reader.get("status") != "PASS" or \
                reader.get("fresh_context") is not True or \
                reader.get("input_scope") != "statement-and-answer-interface" or reader.get("issues") != []:
            raise ValueError("The frozen independent reader has not passed.")
        tools._text(reader.get("restatement"), "frozen reader restatement")
        if semantic.get("status") != "PASS" or semantic.get("meaning_preserved") is not True or \
                semantic.get("no_solution_hints") is not True or semantic.get("issues") != []:
            raise ValueError("The frozen semantic review has not passed.")
        evidence = semantic.get("evidence")
        if not isinstance(evidence, dict):
            raise ValueError("Missing frozen semantic review evidence.")
        for key in tools.SEMANTIC_FIELDS:
            tools._text(evidence.get(key), "frozen semantic evidence for " + key)


# 2. Answer normalization and automatic checks

def integer(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("An exact integer must be a decimal string or integer.")
    text = str(value).strip()
    if not re.fullmatch(r"[+-]?\d+", text):
        raise ValueError("Expected a literal integer, without expressions.")
    return int(text)


def rational(value: Any) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("An exact rational must be an integer or fraction string.")
    text = str(value).strip()
    if not re.fullmatch(r"[+-]?\d+(?:/[+-]?\d+)?", text):
        raise ValueError("Expected an integer or literal numerator/denominator.")
    return Fraction(text)


def decimal(value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("Expected a finite decimal value.")
    result = Decimal(str(value).strip())
    if not result.is_finite():
        raise ValueError("Non-finite numerical answers are not accepted.")
    return result


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def automatic_answer(answer: str, rubric: dict[str, Any]) -> bool | None:
    kind = rubric.get("answer_type")
    expected = rubric.get("accepted_answer")
    if kind == "manual":
        return None
    if kind == "exact_integer":
        reference = integer(expected)
        try:
            return integer(answer) == reference
        except (ValueError, OverflowError):
            return False
    if kind == "exact_rational":
        reference = rational(expected)
        try:
            return rational(answer) == reference
        except (ValueError, ZeroDivisionError, OverflowError):
            return False
    if kind == "exact_json":
        reference = canonical(expected)
        try:
            actual = json.loads(answer, object_pairs_hook=unique_object,
                                parse_constant=lambda x: (_ for _ in ()).throw(
                ValueError(f"Non-finite JSON value: {x}")))
            return canonical(actual) == reference
        except (ValueError, TypeError, OverflowError):
            return False
    if kind == "numeric":
        if "absolute_tolerance" not in rubric or "relative_tolerance" not in rubric:
            raise ValueError("A numerical rubric must specify both tolerances.")
        reference = decimal(expected)
        absolute = decimal(rubric["absolute_tolerance"])
        relative = decimal(rubric["relative_tolerance"])
        if absolute < 0 or relative < 0:
            raise ValueError("Numerical tolerances must be nonnegative.")
        try:
            actual = decimal(answer)
        except (ValueError, InvalidOperation):
            return False
        return abs(actual - reference) <= max(absolute, relative * abs(reference))
    raise ValueError(f"Unsupported answer_type: {kind!r}")


# 3. Review validation and individual grading

def load_reviews(path: Path | None, run_id: str) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError("Reviews must be a JSON object.")
    if data.get("schema_version") != 1 or data.get("run_id") != run_id:
        raise ValueError("Review schema or run_id does not match this run.")
    reviews: dict[str, dict[str, Any]] = {}
    if not isinstance(data.get("reviews"), list):
        raise ValueError("Reviews must contain a reviews list.")
    for item in data["reviews"]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("Each review needs a task ID.")
        if item.get("id") in reviews:
            raise ValueError("Duplicate task review.")
        for key in ("answer_correct", "derivation_correct"):
            if item.get(key) is not None and type(item[key]) is not bool:
                raise ValueError(f"Review {key} must be boolean or null.")
        if not item.get("reviewer") or not item.get("notes"):
            raise ValueError("Every review needs reviewer and notes.")
        reviews[item["id"]] = item
    return reviews


def validate_reference(private: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    if private.get("statement_sha256") != task.get("statement_sha256"):
        raise ValueError("The private reference belongs to another statement.")
    reference = private.get("reference_solution_tex", "")
    reference_hash = hashlib.sha256(reference.encode("utf-8")).hexdigest()
    if (reference_hash != task.get("solution_sha256")
            or reference_hash != private.get("solution_sha256")):
        raise ValueError("The reference solution hash is stale.")
    rubric = private.get("rubric", {})
    if (rubric.get("review_status") != "reviewed"
            or rubric.get("reference_status") != "verified"
            or not rubric.get("requirements")
            or not rubric.get("verification_evidence")):
        raise ValueError("Scoring requires a reviewed rubric and verified reference.")
    if type(rubric.get("requires_proof")) is not bool:
        raise ValueError("requires_proof must be explicitly true or false.")
    return rubric


def grade_one(bundle: Path, run_root: Path, task: dict[str, Any],
              attempt: dict[str, Any], review: dict[str, Any] | None) -> dict[str, Any]:
    if attempt.get("statement_sha256") != task.get("statement_sha256"):
        raise ValueError(f"Stale statement in run: {task['id']}")
    public = contained(bundle, task["public_dir"])
    if digest(public / "prompt.md") != task["statement_sha256"]:
        raise ValueError(f"Exported statement changed: {task['id']}")
    private_path = contained(bundle, task["private_file"])
    if digest(private_path) != attempt.get("private_sha256"):
        raise ValueError(f"Private reference or rubric changed after running: {task['id']}")
    private = read_json(private_path)
    rubric = validate_reference(private, task)
    if review is not None:
        if (review.get("statement_sha256") != task["statement_sha256"]
                or review.get("private_sha256") != attempt["private_sha256"]):
            raise ValueError(f"Review hashes do not match: {task['id']}")
    result: dict[str, Any] = {
        "id": task["id"], "stable_id": task["stable_id"],
        "statement_sha256": task["statement_sha256"],
        "answer_status": "REVIEW", "full_task_status": "REVIEW",
        "requires_proof": rubric["requires_proof"], "notes": [],
        "submission_valid": False, "solver_complete": None,
        "elapsed_seconds": attempt.get("elapsed_seconds"),
        "model_reported": attempt.get("model_reported"),
        "effort_reported": attempt.get("effort_reported"),
        "usage": attempt.get("usage"),
        "execution_status": attempt.get("status"),
        "execution_error": attempt.get("error"),
        "execution_error_kind": attempt.get("error_kind"),
        "configuration_mismatch": attempt.get("configuration_mismatch"),
    }
    if "total_input_output_tokens" in attempt:
        result["total_input_output_tokens"] = attempt["total_input_output_tokens"]
    status = attempt.get("status")
    if status == "planned":
        raise ValueError("A dry run is not a model evaluation and cannot be scored.")
    submission = contained(run_root, attempt["submission_file"])
    if digest(submission) != attempt.get("submission_sha256"):
        raise ValueError(f"The frozen submission changed after running: {task['id']}")
    result["submission_sha256"] = attempt["submission_sha256"]
    if review is not None and review.get("submission_sha256") != attempt["submission_sha256"]:
        raise ValueError(f"Review belongs to another submission: {task['id']}")
    data = None
    try:
        data = read_json(submission)
        if (not isinstance(data, dict) or set(data) != {"answer", "derivation", "complete"}
                or not isinstance(data.get("answer"), str)
                or not isinstance(data.get("derivation"), str)
                or type(data.get("complete")) is not bool):
            raise ValueError("Expected answer/derivation strings and a complete boolean.")
    except (OSError, ValueError, TypeError) as exc:
        result["notes"].append(f"Final output requires review: {exc}")
        data = None
    if data is not None:
        result.update(submission_valid=True, solver_complete=data["complete"])
    invalid_configuration = (bool(attempt.get("configuration_mismatch"))
                             or attempt.get("error_kind") == "configuration_mismatch")
    not_started = str(attempt.get("error") or "").startswith("Not started:")
    if status not in {"completed", "token_limit"} or invalid_configuration or not_started:
        label = ("TIMEOUT" if status == "timeout" and not invalid_configuration
                 and not not_started else "ERROR")
        result.update(answer_status=label, full_task_status=label)
        result["notes"].append("Mathematical grading is unavailable for this execution state or configuration.")
        if attempt.get("error"):
            result["notes"].append(str(attempt["error"]))
        return result
    if data is None:
        if status == "token_limit":
            result.update(answer_status="TOKEN_LIMIT", full_task_status="TOKEN_LIMIT")
            result["notes"].append("The token-limited attempt has no valid final submission; no mathematical failure is inferred.")
        return result
    if status == "token_limit":
        result["notes"].append("The execution reached its token limit; its valid frozen final submission is graded separately.")
    try:
        correct = automatic_answer(data["answer"], rubric)
    except (ValueError, InvalidOperation, ZeroDivisionError) as exc:
        raise ValueError(f"Invalid reference rubric for {task['id']}: {exc}") from exc
    if review is not None and review.get("answer_correct") is not None:
        reviewed = review["answer_correct"]
        if correct is not None and correct != reviewed:
            raise ValueError(f"Review contradicts the fixed automatic answer rule: {task['id']}")
        correct = reviewed
    result["answer_status"] = "REVIEW" if correct is None else ("PASS" if correct else "FAIL")
    proof = review.get("derivation_correct") if review is not None else None
    if not data["complete"]:
        result["notes"].append("The solver marked complete=false; mathematical status follows the requested obligations.")
    if correct is False or (rubric["requires_proof"] and proof is False):
        result["full_task_status"] = "FAIL"
    elif correct is True and (not rubric["requires_proof"] or proof is True):
        result["full_task_status"] = "PASS"
    if rubric["requires_proof"] and proof is None:
        result["notes"].append("The required mathematical derivation has not been reviewed.")
    if review is not None:
        result["reviewer"] = review["reviewer"]
        result["notes"].append(review["notes"])
    if correct is None:
        result["notes"].append("This answer type needs an explicit mathematical review.")
    return result


# 4. Run assessment and report output

RUN_METADATA_FIELDS = (
    "profile", "budget", "configuration_sha256", "configuration_semantic_sha256",
    "configuration_evidence", "wall_seconds", "trial_purpose", "statement_review", "answer_schema_sha256",
)

def assess(bundle: str | Path, run: str | Path,
           reviews: str | Path | None = None) -> dict[str, Any]:
    """Validate and grade a frozen run without writing or replacing artifacts."""
    bundle = Path(bundle).resolve()
    run_root = Path(run).resolve()
    if not run_root.is_dir():
        run_root = contained(bundle, "runs/" + str(run))
    manifest = read_json(bundle / "manifest.json")
    record = read_json(run_root / "run.json")
    if not isinstance(manifest, dict) or not isinstance(record, dict):
        raise ValueError("The manifest and run must contain JSON objects.")
    if manifest.get("schema_version") != 1 or record.get("schema_version") != 1:
        raise ValueError("Unsupported manifest or run schema.")
    if record.get("benchmark_sha256") != manifest.get("benchmark_sha256"):
        raise ValueError("The run and preparation refer to different benchmark snapshots.")
    if digest(bundle / "manifest.json") != record.get("manifest_sha256"):
        raise ValueError("The frozen preparation manifest changed after running.")
    validate_statement_review(run_root, record)
    tasks = {task["id"]: task for task in manifest["tasks"]}
    if len(tasks) != len(manifest["tasks"]):
        raise ValueError("Duplicate manifest task IDs.")
    reviewed = load_reviews(Path(reviews) if reviews is not None else None, record["run_id"])
    attempts = record.get("attempts", [])
    if not isinstance(attempts, list):
        raise ValueError("The run must contain an attempts list.")
    seen: set[str] = set()
    results = []
    for attempt in attempts:
        identity = attempt["id"]
        if identity in seen or identity not in tasks:
            raise ValueError("Duplicate or unknown run task ID.")
        seen.add(identity)
        results.append(grade_one(bundle, run_root, tasks[identity], attempt, reviewed.get(identity)))
    if not results or set(reviewed) - seen:
        raise ValueError("No attempts to score, or a review refers to a task outside this run.")
    answers = Counter(row["answer_status"] for row in results)
    full = Counter(row["full_task_status"] for row in results)
    def homogeneous(field):
        values = [row.get(field) for row in results]
        return values[0] if values and all(value and value == values[0] for value in values) else None
    model_reported = homogeneous("model_reported")
    effort_reported = homogeneous("effort_reported")
    summary = {
        "assigned": len(results), "answer_counts": dict(answers),
        "full_task_counts": dict(full),
        "execution_counts": dict(Counter(row["execution_status"] for row in results)),
        "confirmed_answer_pass_fraction": {"numerator": answers["PASS"], "denominator": len(results)},
        "confirmed_full_task_pass_fraction": {"numerator": full["PASS"], "denominator": len(results)},
        "denominator_policy": "All assigned attempts, including timeouts, token limits, errors, and pending reviews.",
    }
    return {
        "schema_version": 1, "run_id": record["run_id"],
        "benchmark_sha256": manifest["benchmark_sha256"],
        "model_requested": record.get("model_requested"),
        "model_reported": model_reported,
        "effort_requested": record.get("effort_requested"),
        "effort_reported": effort_reported,
        **{key: record[key] for key in RUN_METADATA_FIELDS if key in record},
        "isolation": record.get("isolation"), "strict_blind": False,
        "network_enforced": False, "summary": summary, "tasks": results,
        "interpretation": "Local pilot evidence; no official tier certification or contamination guarantee.",
    }


def score(bundle: str | Path, run: str | Path, reviews: str | Path | None = None) -> Path:
    output = assess(bundle, run, reviews)
    bundle = Path(bundle).resolve()
    run_root = Path(run).resolve()
    if not run_root.is_dir():
        run_root = contained(bundle, "runs/" + str(run))
    record = output
    results = output["tasks"]
    answers = Counter(output["summary"]["answer_counts"])
    full = Counter(output["summary"]["full_task_counts"])
    model_reported = output["model_reported"]
    effort_reported = output["effort_reported"]
    text = ["# Codex mathematics pilot", "", "## Contents", "",
            "- [Configuration](#configuration)", "- [Results](#results)",
            "- [Interpretation](#interpretation)", "", "## Configuration", "",
            f"Run: `{record['run_id']}`", "",
            f"Requested model: `{record.get('model_requested')}`; reported model: `{model_reported or 'unknown or mixed'}`.",
            f"Requested effort: `{record.get('effort_requested')}`; reported effort: `{effort_reported or 'unknown or mixed'}`.",
            "", "Isolation: instruction-only. Hard filesystem and network isolation are not certified."]
    metadata = {key: record[key] for key in RUN_METADATA_FIELDS if key in record}
    if metadata:
        text.extend(["", "Recorded profile, budget, and configuration evidence:", "", "```json",
                     json.dumps(metadata, indent=2, ensure_ascii=False), "```"])
    text.extend(["", "## Results", "",
            f"Confirmed final-answer passes: {answers['PASS']}/{len(results)} assigned attempts.",
            f"Confirmed full-task passes: {full['PASS']}/{len(results)} assigned attempts.",
            "Timeouts, token limits, infrastructure errors, and pending reviews remain visible in the denominator.",
            "", "| Task | Execution | Valid final | Solver complete | Final answer | Full task | Notes |",
            "|---|---|---|---|---|---|---|"])
    for row in results:
        note = " ".join(row["notes"]).replace("|", "\\|").replace("\n", " ")
        complete = "unknown" if row["solver_complete"] is None else str(row["solver_complete"]).lower()
        valid = str(row["submission_valid"]).lower()
        text.append(f"| {row['id']} | {row['execution_status']} | {valid} | {complete} | "
                    f"{row['answer_status']} | {row['full_task_status']} | {note} |")
    text.extend(["", "## Interpretation", "",
                 "These are local single-attempt results under the recorded conditions.",
                 "They do not establish an official FrontierMath tier or exclude training contamination.", ""])
    (run_root / "grading.json").write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_root / "report.md").write_text("\n".join(text), encoding="utf-8")
    return run_root / "report.md"


# 5. Command-line interface

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("run", help="Run directory or its ID under BUNDLE/runs")
    parser.add_argument("--reviews", type=Path)
    args = parser.parse_args()
    try:
        print(score(args.bundle, args.run, args.reviews))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
