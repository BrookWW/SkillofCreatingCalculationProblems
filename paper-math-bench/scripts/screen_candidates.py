"""Classify frozen formal trials under the local-pilot reported-I/O tier policy.

Use BUNDLE RUN [--reviews FILE] after run_eval.py. Valid submissions failing the
requested mathematical obligations are T4; full passes are T2 through S, T3
above S through B, and T4 above B. Native
budget exhaustion without a valid answer is distinct from mathematical failure.
Unresolved reviews and operational failures remain pending. No source is deleted.
"""

# Contents: 1. Frozen evidence and decisions; 2. Versioned output; 3. CLI.
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any
import score_run

# 1. Frozen evidence and decisions
SCHEMA_VERSION = 2
POLICY = "local_pilot_tiers"
POLICY_VERSION = 1
TERMINAL_STATUSES = {"completed", "timeout", "token_limit", "error", "interrupted"}
MEASUREMENT_SCOPE = (
    "Reported solver input plus output only. Cached input and reasoning output "
    "are included subtotals and are not added again. Coverage of failed or "
    "retried backend requests and complete account billing is unverified. "
    "Native rollout-budget units are not assumed to equal full I/O."
)


def frozen_thresholds(record: dict[str, Any]) -> dict[str, Any]:
    """Read thresholds only from the frozen budget, without defaults."""
    budget = record.get("budget")
    budget = budget if isinstance(budget, dict) else {}
    total = budget.get("total_input_output_tokens_requested")
    submit = budget.get("submit_after_tokens_requested")
    total_valid = type(total) is int and total > 0
    submit_valid = type(submit) is int and total_valid and 0 < submit < total
    return {"B": total, "S": submit, "B_valid": total_valid, "S_valid": submit_valid,
            "source": "run.json:budget.total_input_output_tokens_requested/submit_after_tokens_requested",
            "defaults_applied": False}


def _usage_total(usage: Any) -> int | None:
    if isinstance(usage, list):
        totals = [_usage_total(item) for item in usage]
        return sum(totals) if totals and all(value is not None for value in totals) else None
    if not isinstance(usage, dict):
        return None
    values = (usage.get("input_tokens", usage.get("inputTokens")),
              usage.get("output_tokens", usage.get("outputTokens")))
    return sum(values) if all(type(value) is int and value >= 0 for value in values) else None


def reported_usage(attempt: dict[str, Any]) -> dict[str, Any]:
    """Preserve explicit unknowns and reject contradictory reported totals."""
    measured = _usage_total(attempt.get("usage"))
    source = "run.json:attempt.total_input_output_tokens"
    if "total_input_output_tokens" not in attempt:
        return {"U": measured, "source": "run.json:attempt.usage.input_tokens+output_tokens",
                "issue": None if measured is not None else "reported_usage_unknown"}
    total = attempt["total_input_output_tokens"]
    if total is None:
        return {"U": None, "source": source, "issue": "reported_usage_unknown"}
    if type(total) is not int or total < 0:
        return {"U": None, "source": source, "issue": "reported_usage_invalid"}
    if measured is not None and measured != total:
        return {"U": None, "source": source, "issue": "reported_usage_inconsistent"}
    return {"U": total, "source": source, "issue": None}


def classify(result: dict[str, Any], attempt: dict[str, Any],
             thresholds: dict[str, Any]) -> dict[str, Any]:
    """Apply the local trial policy, without inferring a human difficulty tier."""
    usage = reported_usage(attempt)
    decision = {"decision": "pending", "tier": None, "reported_full_io": usage,
                "attempt_started": bool(attempt.get("command")),
                "recorded_usage_scope": attempt.get("usage_scope"),
                "recorded_usage_coverage": attempt.get("usage_coverage")}

    def finish(tier: str | None, code: str, reason: str) -> dict[str, Any]:
        return {**decision, "decision": "classify" if tier is not None else "pending",
                "tier": tier, "reason_code": code, "reason": reason}

    status, answer = result.get("execution_status"), result.get("answer_status")
    full = result.get("full_task_status")
    if (attempt.get("configuration_mismatch") or result.get("configuration_mismatch")
            or attempt.get("error_kind") == "configuration_mismatch"
            or result.get("execution_error_kind") == "configuration_mismatch"):
        return finish(None, "configuration_mismatch", "The requested trial configuration was not preserved.")
    if not decision["attempt_started"]:
        return finish(None, "attempt_not_started", "No recorded solver process was started for this attempt.")
    if (status not in {"completed", "token_limit"} or answer in {"ERROR", "TIMEOUT"}
            or full in {"ERROR", "TIMEOUT"}):
        return finish(None, "execution_unresolved", "Operational failure or interruption is not tier evidence.")
    if full == "REVIEW":
        return finish(None, "mathematical_review_pending", "The requested mathematical obligations still require review.")
    if result.get("submission_valid") is True and full == "FAIL":
        return finish("T4", "mathematical_fail", "The valid submission fails the requested mathematical obligations.")
    if (status == "token_limit" and result.get("submission_valid") is False
            and answer == "TOKEN_LIMIT"):
        return finish("T4", "budget_exhausted_unsolved",
                      "The native budget was exhausted without a valid correct final answer; this is not a mathematical FAIL or proof of full-I/O excess.")
    if result.get("submission_valid") is not True or full != "PASS":
        return finish(None, "valid_answer_unavailable", "A valid, mathematically assessed final answer is unavailable.")
    if usage["U"] is None:
        return finish(None, usage["issue"], "A correct answer has no consistent known reported full-I/O total.")
    if not thresholds["B_valid"]:
        return finish(None, "frozen_budget_unavailable", "The frozen run has no valid B; no default is substituted.")
    if usage["U"] > thresholds["B"]:
        return finish("T4", "correct_above_budget", "The correct answer's reported full I/O exceeds the frozen B.")
    if not thresholds["S_valid"]:
        return finish(None, "frozen_submission_threshold_unavailable", "The frozen run does not establish 0 < S < B; no default is substituted.")
    if usage["U"] <= thresholds["S"]:
        return finish("T2", "correct_by_submission_threshold", "The correct answer's reported full I/O is at or below the frozen S.")
    return finish("T3", "correct_within_budget", "The correct answer's reported full I/O is above S and at or below B.")


# 2. Versioned output and frozen input validation

def _write_record(run_root: Path, payload: bytes) -> Path:
    destination = run_root / "screening-v2.json"
    if destination.exists():
        if destination.read_bytes() == payload:
            return destination
        destination = run_root / ("screening-v2-" + hashlib.sha256(payload).hexdigest() + ".json")
    try:
        with destination.open("xb") as stream:
            stream.write(payload)
    except FileExistsError:
        if destination.read_bytes() != payload:
            raise ValueError("An existing classification has different content; it was not overwritten.")
    return destination


def screen(bundle: str | Path, run: str | Path,
           reviews: str | Path | None = None) -> Path:
    """Write a versioned classification without replacing prior artifacts."""
    bundle, run_root = Path(bundle).resolve(), Path(run).resolve()
    if not run_root.is_dir():
        run_root = score_run.contained(bundle, "runs/" + str(run))
    run_path = run_root / "run.json"
    run_hash = score_run.digest(run_path)
    record = score_run.read_json(run_path)
    if not isinstance(record, dict):
        raise ValueError("The run must contain a JSON object.")
    if record.get("dry_run") or record.get("status") == "planned":
        raise ValueError("A dry run supplies no model evidence and cannot classify candidates.")
    if record.get("trial_purpose") == "diagnostic":
        raise ValueError("A diagnostic attempt cannot supply final formal screening.")
    if record.get("status") not in TERMINAL_STATUSES:
        raise ValueError("Classification requires a finished run.")
    attempts = record.get("attempts")
    if not isinstance(attempts, list) or any(
        not isinstance(attempt, dict) or attempt.get("status") not in TERMINAL_STATUSES
        for attempt in attempts
    ):
        raise ValueError("Classification requires every assigned attempt to be finished.")
    reviews_path = Path(reviews).resolve() if reviews is not None else None
    reviews_hash = score_run.digest(reviews_path) if reviews_path is not None else None
    grading = score_run.assess(bundle, run_root, reviews_path)
    thresholds = frozen_thresholds(record)
    by_id = {attempt["id"]: attempt for attempt in attempts}
    candidates = [{**result, "private_sha256": by_id[result["id"]]["private_sha256"],
                   "submission_sha256": by_id[result["id"]].get("submission_sha256"),
                   **classify(result, by_id[result["id"]], thresholds)} for result in grading["tasks"]]
    tiers = Counter(candidate["tier"] for candidate in candidates)
    output = {
        "schema_version": SCHEMA_VERSION, "policy": POLICY, "policy_version": POLICY_VERSION,
        "run_id": grading["run_id"], "run_sha256": run_hash,
        "manifest_sha256": record["manifest_sha256"], "benchmark_sha256": grading["benchmark_sha256"],
        "reviews_sha256": reviews_hash,
        "model_requested": grading["model_requested"], "model_reported": grading["model_reported"],
        "effort_requested": grading["effort_requested"], "effort_reported": grading["effort_reported"],
        **{key: grading[key] for key in score_run.RUN_METADATA_FIELDS if key in grading},
        "wall_seconds": record.get("wall_seconds"), "isolation": grading["isolation"],
        "strict_blind": grading["strict_blind"], "network_enforced": grading["network_enforced"],
        "frozen_thresholds": thresholds, "measurement_scope": MEASUREMENT_SCOPE,
        "usage_scope": {"basis": "reported_solver_input_plus_output",
                        "cached_input_is_included_subtotal": True,
                        "reasoning_output_is_included_subtotal": True,
                        "failed_or_retried_request_coverage": "unverified",
                        "complete_account_billing_coverage": "unverified",
                        "recorded_run_scope": record.get("usage_scope"),
                        "recorded_run_coverage": record.get("usage_coverage")},
        "summary": {"assigned": len(candidates), "classified": len(candidates) - tiers[None],
                    "pending": tiers[None], "tier_counts": {tier: tiers[tier] for tier in ("T2", "T3", "T4")}},
        "candidates": candidates,
        "interpretation": (
            "Versioned local-pilot trial classification, not an official FrontierMath or human-difficulty tier. "
            "No question is deleted or automatically rewritten; historical runs, grading and submissions are preserved."
        ),
    }
    if score_run.digest(run_path) != run_hash:
        raise ValueError("The run changed during classification.")
    if reviews_path is not None and score_run.digest(reviews_path) != reviews_hash:
        raise ValueError("The reviews changed during classification.")
    return _write_record(run_root, (json.dumps(output, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


# 3. Command-line interface

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="Prepared candidate evaluation bundle")
    parser.add_argument("run", help="Finished run directory or its ID under BUNDLE/runs")
    parser.add_argument("--reviews", type=Path, help="Hash-bound answer reviews, as used by score_run.py")
    args = parser.parse_args()
    try:
        print(screen(args.bundle, args.run, args.reviews))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
