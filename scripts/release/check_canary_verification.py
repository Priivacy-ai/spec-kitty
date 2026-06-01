#!/usr/bin/env python3
"""Validate Spec Kitty dev canary evidence before release publication."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, help="Path to canary evidence JSON")
    parser.add_argument("--candidate-version", required=True)
    parser.add_argument(
        "--expected-target",
        default="https://spec-kitty-dev.fly.dev/",
        help="Canary target that must have been exercised.",
    )
    parser.add_argument("--required-clean-runs", type=int, default=4)
    parser.add_argument(
        "--allow-waiver",
        action="store_true",
        help="Accept a structured release-owner waiver instead of passed canaries.",
    )
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Canary verification artifact not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Canary verification artifact is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("Canary verification artifact must be a JSON object")
    return data


def _normalise_url(value: str) -> str:
    return value.rstrip("/") + "/"


def _require_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"Canary verification artifact missing non-empty string: {key}")
    return value.strip()


def _parse_datetime(value: str, *, key: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SystemExit(f"{key} must be an ISO-8601 timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise SystemExit(f"{key} must include timezone information: {value!r}")
    return parsed


def _validate_common(data: dict[str, Any], *, candidate_version: str, expected_target: str) -> None:
    artifact_version = _require_str(data, "candidate_version")
    if artifact_version != candidate_version:
        raise SystemExit(
            "Canary verification candidate_version mismatch: "
            f"expected {candidate_version!r}, got {artifact_version!r}"
        )

    target = _require_str(data, "target")
    if _normalise_url(target) != _normalise_url(expected_target):
        raise SystemExit(
            "Canary verification target mismatch: "
            f"expected {expected_target!r}, got {target!r}"
        )

    _parse_datetime(_require_str(data, "verified_at"), key="verified_at")


def _validate_passed(data: dict[str, Any], *, required_clean_runs: int) -> None:
    clean_runs = data.get("clean_runs")
    if not isinstance(clean_runs, list):
        raise SystemExit("Passed canary artifact must include clean_runs list")
    if len(clean_runs) < required_clean_runs:
        raise SystemExit(
            f"Canary verification requires at least {required_clean_runs} clean runs; "
            f"artifact contains {len(clean_runs)}"
        )

    for index, raw_run in enumerate(clean_runs, start=1):
        if not isinstance(raw_run, dict):
            raise SystemExit(f"clean_runs[{index}] must be a JSON object")
        if raw_run.get("result") != "passed":
            raise SystemExit(f"clean_runs[{index}] result must be 'passed'")
        _require_str(raw_run, "run_id")
        _parse_datetime(_require_str(raw_run, "completed_at"), key=f"clean_runs[{index}].completed_at")
        if "target" in raw_run and not isinstance(raw_run["target"], str):
            raise SystemExit(f"clean_runs[{index}].target must be a string when present")
        if "health_ready_status" in raw_run and raw_run["health_ready_status"] not in {"ok", "pass", "passed"}:
            raise SystemExit(
                f"clean_runs[{index}].health_ready_status must be ok/pass/passed when present"
            )


def _validate_waiver(data: dict[str, Any], *, allow_waiver: bool) -> None:
    if not allow_waiver:
        raise SystemExit("Canary verification artifact is waived, but waivers are not allowed here")

    waiver = data.get("waiver")
    if not isinstance(waiver, dict):
        raise SystemExit("Waived canary artifact must include waiver object")

    reason = _require_str(waiver, "reason")
    if len(reason) < 20:
        raise SystemExit("Canary waiver reason must be specific, not a placeholder")
    _require_str(waiver, "approved_by")
    issue_url = _require_str(waiver, "issue_url")
    if not issue_url.startswith("https://github.com/Priivacy-ai/spec-kitty/issues/"):
        raise SystemExit("Canary waiver issue_url must point at a Priivacy-ai/spec-kitty issue")

    expires_at = _parse_datetime(_require_str(waiver, "expires_at"), key="waiver.expires_at")
    if expires_at <= datetime.now(UTC):
        raise SystemExit("Canary waiver has expired")


def main() -> int:
    args = parse_args()
    data = _load_json(Path(args.artifact))
    _validate_common(
        data,
        candidate_version=args.candidate_version,
        expected_target=args.expected_target,
    )

    status = data.get("status")
    if status == "passed":
        _validate_passed(data, required_clean_runs=args.required_clean_runs)
    elif status == "waived":
        _validate_waiver(data, allow_waiver=args.allow_waiver)
    else:
        raise SystemExit("Canary verification status must be 'passed' or 'waived'")

    print("Canary Verification Summary")
    print("---------------------------")
    print(f"- status: {status}")
    print(f"- candidate_version: {data['candidate_version']}")
    print(f"- target: {data['target']}")
    if status == "passed":
        print(f"- clean_runs: {len(data['clean_runs'])}")
    else:
        print(f"- waiver_issue: {data['waiver']['issue_url']}")
    print("\nCanary verification check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
