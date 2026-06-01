from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/release/check_canary_verification.py")


def _run(tmp_path: Path, payload: dict[str, object], *extra: str) -> subprocess.CompletedProcess[str]:
    artifact = tmp_path / "canary-verified.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--artifact",
            str(artifact),
            "--candidate-version",
            "3.2.0rc31",
            *extra,
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def _passed_payload() -> dict[str, object]:
    return {
        "status": "passed",
        "candidate_version": "3.2.0rc31",
        "target": "https://spec-kitty-dev.fly.dev/",
        "verified_at": "2026-06-01T08:00:00Z",
        "clean_runs": [
            {
                "run_id": f"canary-{idx}",
                "result": "passed",
                "completed_at": f"2026-06-01T08:0{idx}:00Z",
                "target": "https://spec-kitty-dev.fly.dev/",
                "health_ready_status": "ok",
            }
            for idx in range(1, 5)
        ],
    }


def test_passed_artifact_requires_four_clean_runs(tmp_path: Path) -> None:
    result = _run(tmp_path, _passed_payload())

    assert result.returncode == 0, result.stderr
    assert "clean_runs: 4" in result.stdout


def test_passed_artifact_rejects_too_few_runs(tmp_path: Path) -> None:
    payload = _passed_payload()
    payload["clean_runs"] = payload["clean_runs"][:3]  # type: ignore[index]

    result = _run(tmp_path, payload)

    assert result.returncode == 1
    assert "requires at least 4 clean runs" in result.stderr


def test_candidate_version_must_match_release_tag(tmp_path: Path) -> None:
    payload = _passed_payload()
    payload["candidate_version"] = "3.2.0rc30"

    result = _run(tmp_path, payload)

    assert result.returncode == 1
    assert "candidate_version mismatch" in result.stderr


def test_clean_runs_must_have_unique_run_ids(tmp_path: Path) -> None:
    payload = _passed_payload()
    for run in payload["clean_runs"]:  # type: ignore[union-attr]
        run["run_id"] = "duplicated-run"  # type: ignore[index]

    result = _run(tmp_path, payload)

    assert result.returncode == 1
    assert "run_id must be unique" in result.stderr


def test_clean_run_targets_must_match_expected_target(tmp_path: Path) -> None:
    payload = _passed_payload()
    payload["clean_runs"][0]["target"] = "https://not-spec-kitty-dev.example/"  # type: ignore[index]

    result = _run(tmp_path, payload)

    assert result.returncode == 1
    assert "clean_runs[1].target mismatch" in result.stderr


def test_waiver_requires_explicit_allow_waiver(tmp_path: Path) -> None:
    payload = {
        "status": "waived",
        "candidate_version": "3.2.0rc31",
        "target": "https://spec-kitty-dev.fly.dev/",
        "verified_at": "2026-06-01T08:00:00Z",
        "waiver": {
            "reason": "Fly credentials were unavailable; release owner accepted documented residual risk.",
            "approved_by": "release-owner",
            "issue_url": "https://github.com/Priivacy-ai/spec-kitty/issues/1112",
            "expires_at": "2999-01-01T00:00:00Z",
        },
    }

    rejected = _run(tmp_path, payload)
    accepted = _run(tmp_path, payload, "--allow-waiver")

    assert rejected.returncode == 1
    assert "waivers are not allowed" in rejected.stderr
    assert accepted.returncode == 0, accepted.stderr
