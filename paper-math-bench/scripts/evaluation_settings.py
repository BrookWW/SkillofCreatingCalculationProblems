"""Validate current-operation evidence and resolve reproducible evaluation settings."""

# Contents (search the numbered section headings below):
# 1. JSON, timestamps, and profile discovery
# 2. Current-operation configuration validation
# 3. Runtime budget instructions and measured usage

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any


# 1. JSON, timestamps, and profile discovery

EPOCH_PROFILE = "epoch-tier4-v2"
LOCAL_PROFILE = "local-pilot"
DEFAULT_PROFILE = LOCAL_PROFILE
DEFAULT_MODEL = "gpt-5.6-sol"
DEFAULT_EFFORT = "max"
DEFAULT_TOTAL_TOKENS = 1000000
DEFAULT_SUBMIT_AFTER_TOKENS = 660000
PROFILES = {EPOCH_PROFILE, LOCAL_PROFILE}
SETTING_KEYS = {"profile", "model", "effort", "wall_seconds",
                "total_input_output_tokens", "submit_after_tokens"}
PROFILE_PATH = Path(__file__).resolve().parents[1] / "data" / "epoch-settings.json"


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate configuration key: {key}")
        result[key] = value
    return result


def read_object(path: Path) -> tuple[dict[str, Any], str]:
    data = path.read_bytes()
    if len(data) > 1024 * 1024:
        raise ValueError("Configuration exceeds 1 MiB")
    value = json.loads(data.decode("utf-8"), object_pairs_hook=_object,
                       parse_constant=lambda value: (_ for _ in ()).throw(
                           ValueError(f"Nonfinite configuration value: {value}")))
    if not isinstance(value, dict):
        raise ValueError("Configuration must contain a JSON object")
    return value, hashlib.sha256(data).hexdigest()


def semantic_hash(value: dict[str, Any]) -> str:
    canonical = json.dumps(value, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be an ISO-8601 timestamp with timezone")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid {label}") from exc
    if result.tzinfo is None:
        raise ValueError(f"{label} needs a timezone")
    return result.astimezone(timezone.utc)


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a nonempty string without surrounding whitespace")
    return value


def validate_wall(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError("wall_seconds must be null or a positive finite number")
    return float(value)


def _token_limits(total: Any, submit: Any) -> tuple[int | None, int | None]:
    if total is None and submit is None:
        return None, None
    if type(total) is not int or type(submit) is not int or not 0 < submit < total:
        raise ValueError("Token limits must be paired positive integers with 0 < submit_after_tokens < total_input_output_tokens")
    return total, submit


def epoch_settings(path: Path = PROFILE_PATH) -> dict[str, Any]:
    """Load the attributed settings snapshot; never infer a model's published effort."""
    snapshot, snapshot_hash = read_object(path)
    if snapshot.get("profile_id") != EPOCH_PROFILE:
        raise ValueError("The Epoch snapshot has an unexpected profile")
    models = snapshot.get("model_efforts")
    if not isinstance(models, dict) or not models:
        raise ValueError("The Epoch snapshot needs a model-to-published-effort mapping")
    settings = {
        "models": models,
        "total_input_output_tokens": snapshot.get("limits", {}).get("total_token_limit"),
        "submit_after_tokens": snapshot.get("limits", {}).get("submission_threshold_tokens"),
        "snapshot_sha256": snapshot_hash,
        "source": snapshot.get("methodology_url"),
        "verified_at": snapshot.get("verified_on"),
    }
    if settings["total_input_output_tokens"] != 1000000 or settings["submit_after_tokens"] != 660000:
        raise ValueError("The Epoch snapshot budget is unsupported by this profile")
    return settings


# 2. Current-operation configuration validation

def _validate_user_evidence(evidence: dict[str, Any], started: datetime,
                            created: datetime) -> None:
    """Accept a current user instruction, Q&A, or both; validate every supplied record."""
    if "qa" not in evidence and "user_instructions" not in evidence:
        raise ValueError("Configuration needs current user instructions or Q&A")
    if "qa" in evidence:
        qa = evidence["qa"]
        if not isinstance(qa, list) or not qa:
            raise ValueError("Q&A configuration needs at least one question and user answer")
        for item in qa:
            if not isinstance(item, dict):
                raise ValueError("Each Q&A entry must be an object")
            for key in ("question", "answer", "user_reply_ref"):
                _text(item.get(key), f"Q&A {key}")
            answered = _timestamp(item.get("answered_at"), "Q&A answered_at")
            if not started <= answered <= created:
                raise ValueError("Stale Q&A answer: it must belong to the current operation")
    if "user_instructions" in evidence:
        instructions = evidence["user_instructions"]
        if not isinstance(instructions, list) or not instructions:
            raise ValueError("user_instructions needs at least one current user instruction")
        for item in instructions:
            if not isinstance(item, dict):
                raise ValueError("Each user instruction must be an object")
            for key in ("text", "user_message_ref"):
                _text(item.get(key), f"User instruction {key}")
            provided = _timestamp(item.get("provided_at"), "User instruction provided_at")
            if not started <= provided <= created:
                raise ValueError("Stale user instruction: it must belong to the current operation")


def resolve(*, configuration: str | Path | None, invocation_id: str | None,
            bundle: Path, manifest_sha256: str, benchmark_sha256: str,
            task_ids: list[str], profile: str | None, model: str | None,
            effort: str | None, wall_seconds: float | None,
            required: bool, snapshot_path: Path = PROFILE_PATH) -> dict[str, Any]:
    """Check workflow evidence; default dry-runs to the local pilot settings."""
    evidence = None
    evidence_hash = None
    if configuration is not None:
        evidence, evidence_hash = read_object(Path(configuration).expanduser().resolve())
    if profile is None:
        selected_profile = evidence.get("settings") if evidence is not None else None
        profile = (selected_profile.get("profile") if isinstance(selected_profile, dict)
                   else DEFAULT_PROFILE if evidence is None else None)
    if profile not in PROFILES:
        raise ValueError(f"Unknown evaluation profile: {profile}")
    wall_seconds = validate_wall(wall_seconds)
    snapshot = epoch_settings(snapshot_path) if profile == EPOCH_PROFILE else None
    total_tokens, submit_tokens = ((snapshot["total_input_output_tokens"], snapshot["submit_after_tokens"])
                                  if snapshot else (DEFAULT_TOTAL_TOKENS, DEFAULT_SUBMIT_AFTER_TOKENS))
    if configuration is None:
        if required:
            raise ValueError("A real run requires the current operation's instruction/Q&A configuration and invocation_id")
        if profile == DEFAULT_PROFILE:
            model = DEFAULT_MODEL if model is None else model
            effort = DEFAULT_EFFORT if effort is None else effort
    else:
        if evidence.get("schema_version") != 1:
            raise ValueError("Unsupported configuration schema_version")
        if not invocation_id or evidence.get("invocation_id") != invocation_id:
            raise ValueError("Configuration invocation_id does not match the current operation")
        _text(invocation_id, "invocation_id")
        if evidence.get("operation") not in {"authoring", "evaluation"}:
            raise ValueError("Configuration operation must be authoring or evaluation")
        started = _timestamp(evidence.get("invocation_started_at"), "invocation_started_at")
        created = _timestamp(evidence.get("created_at"), "created_at")
        if started > created or created > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("Configuration timestamps do not describe a valid current operation")
        binding = evidence.get("binding")
        if not isinstance(binding, dict) or binding != {
            "bundle": str(bundle), "manifest_sha256": manifest_sha256,
            "benchmark_sha256": benchmark_sha256, "task_ids": task_ids,
        }:
            raise ValueError("Configuration binding does not match this bundle, manifest, benchmark, or task selection")
        _validate_user_evidence(evidence, started, created)
        selected = evidence.get("settings")
        if not isinstance(selected, dict) or selected.get("profile") != profile:
            raise ValueError("Configuration profile differs from the requested profile")
        unknown = set(selected) - SETTING_KEYS
        if unknown:
            raise ValueError("Unsupported configuration settings: " + ", ".join(sorted(unknown)))
        total_tokens, submit_tokens = _token_limits(selected.get("total_input_output_tokens"),
                                                  selected.get("submit_after_tokens"))
        selected_model = _text(selected.get("model"), "Configuration model")
        selected_effort = _text(selected.get("effort"), "Configuration effort")
        selected_wall = validate_wall(selected.get("wall_seconds"))
        if model is not None and model != selected_model:
            raise ValueError("Requested model differs from the recorded configuration")
        if effort is not None and effort != selected_effort:
            raise ValueError("Requested effort differs from the recorded configuration")
        if wall_seconds is not None and wall_seconds != selected_wall:
            raise ValueError("Operational wall timeout differs from the recorded configuration")
        model, effort, wall_seconds = selected_model, selected_effort, selected_wall
        if profile == EPOCH_PROFILE:
            if selected.get("total_input_output_tokens") != snapshot["total_input_output_tokens"] or selected.get("submit_after_tokens") != snapshot["submit_after_tokens"]:
                raise ValueError("Configuration token budgets differ from the Epoch profile")
            if evidence.get("acknowledge_cli_differences") is not True:
                raise ValueError("The current configuration must acknowledge the CLI's accounting, forced-submission, and tool-interface differences")
    model = _text(model, "model")
    if profile == EPOCH_PROFILE:
        published = snapshot["models"].get(model)
        if isinstance(published, dict):
            published = published.get("effort")
        if not isinstance(published, str) or not published:
            raise ValueError("Model has no published setting in the Epoch snapshot; select an explicit local-pilot profile for custom settings")
        if effort is not None and effort != published:
            raise ValueError(f"Epoch profile requires published effort {published!r}, not {effort!r}")
        effort = published
    effort = _text(effort, "effort")
    budget = {
        "total_input_output_tokens_requested": total_tokens,
        "submit_after_tokens_requested": submit_tokens,
        "native_accounting_verified": False,
        "forced_submission_enforced": False,
        "epoch_protocol_match": False,
        "native_rollout_budget_requested": total_tokens is not None,
    }
    return {
        "profile": profile, "model": model, "effort": effort, "wall_seconds": wall_seconds,
        "configuration_evidence": evidence, "configuration_sha256": evidence_hash,
        "configuration_semantic_sha256": semantic_hash(evidence) if evidence is not None else None,
        "profile_snapshot": snapshot, "budget": budget,
    }


# 3. Runtime budget instructions and measured usage

def native_budget_override(budget: dict[str, Any]) -> str | None:
    if not budget.get("native_rollout_budget_requested"):
        return None
    limit = budget["total_input_output_tokens_requested"]
    remaining = limit - budget["submit_after_tokens_requested"]
    return ("features.rollout_budget={enabled=true,limit_tokens=" + str(limit)
            + ",reminder_at_remaining_tokens=[" + str(remaining)
            + "],sampling_token_weight=1.0,prefill_token_weight=1.0}")


def budget_instructions(budget: dict[str, Any], *, profile: str = DEFAULT_PROFILE) -> bytes:
    if not budget.get("native_rollout_budget_requested"):
        return b""
    total = budget["total_input_output_tokens_requested"]
    remaining = total - budget["submit_after_tokens_requested"]
    prefix = (
        f"Evaluation budget: {total:,} cumulative input plus output tokens requested. "
        f"When the native rollout-budget reminder shows {remaining:,} or fewer remaining tokens, "
    )
    if profile == EPOCH_PROFILE:
        instruction = (
            "stop further exploration and submit your best final JSON immediately, using exactly "
            "answer, derivation, complete. Submit earlier when finished.\n\n"
        )
    else:
        instruction = (
            "reserve enough tokens for your final JSON. If unfinished, continue solving within "
            f"the {total:,} total token budget. Submit as soon as finished, using exactly "
            "answer, derivation, complete.\n\n"
        )
    return (prefix + instruction).encode("utf-8")


def measured_total(usage: Any) -> int | None:
    """Count input plus output; cached input and reasoning are included subtotals."""
    if usage is None:
        return None
    if isinstance(usage, list):
        totals = [measured_total(item) for item in usage]
        return sum(totals) if totals and all(item is not None for item in totals) else None
    if not isinstance(usage, dict):
        return None
    input_tokens = usage.get("input_tokens", usage.get("inputTokens"))
    output_tokens = usage.get("output_tokens", usage.get("outputTokens"))
    if any(type(item) is not int or item < 0 for item in (input_tokens, output_tokens)):
        return None
    return input_tokens + output_tokens
