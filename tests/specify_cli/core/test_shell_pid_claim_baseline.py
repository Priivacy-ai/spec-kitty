"""Tests for the PID-reuse identity baseline claim-write helper (#2575, WP02).

Covers:
- FR-004/FR-005: the ONE claim-write helper (:func:`write_shell_pid_claim`)
  co-writes ``shell_pid`` and its creation-time baseline via a single write
  mechanism (``set_scalar`` string mutation), and the file-based route used by
  ``spec-kitty implement`` (:func:`write_shell_pid_claim_to_file`) round-trips
  through the same mechanism.
- FR-004/FR-005/D3a: ``core.stale_detection``'s claim-liveness consumer
  compares the baseline when present (mismatch -> not-alive -> falls through
  to the commit-timestamp heuristic, never a hard-stale flag) and preserves
  today's live-PID trust when the baseline is absent (a legacy claim).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from specify_cli.core.process_liveness import capture_creation_time_baseline
from specify_cli.core.stale_detection import LIVE_CLAIM_PROCESS_REASON, check_wp_staleness
from specify_cli.frontmatter import (
    SHELL_PID_BASELINE_FIELD,
    write_shell_pid_claim,
    write_shell_pid_claim_to_file,
)
from specify_cli.task_utils.support import extract_scalar
from specify_cli.status.wp_metadata import WPMetadata

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ── Direct unit tests of the claim-write helper (T010 / T016 coverage) ─────


def test_write_shell_pid_claim_co_writes_shell_pid_and_baseline() -> None:
    """The helper writes BOTH shell_pid and its baseline in one call (D3b)."""
    own_pid = os.getpid()
    frontmatter = "work_package_id: WP01\ntitle: Example\nhistory: []\n"

    updated = write_shell_pid_claim(frontmatter, own_pid)

    assert extract_scalar(updated, "shell_pid") == str(own_pid)
    baseline = extract_scalar(updated, SHELL_PID_BASELINE_FIELD)
    assert baseline is not None
    # The written baseline matches a direct capture for the same live pid.
    assert baseline == capture_creation_time_baseline(own_pid)


def test_write_shell_pid_claim_overwrites_existing_values() -> None:
    """Re-claiming (e.g. review overwriting the implement claim) replaces both fields."""
    own_pid = os.getpid()
    frontmatter = (
        "work_package_id: WP01\n"
        'shell_pid: "111111"\n'
        f'{SHELL_PID_BASELINE_FIELD}: "0.0"\n'
        "history: []\n"
    )

    updated = write_shell_pid_claim(frontmatter, own_pid)

    assert extract_scalar(updated, "shell_pid") == str(own_pid)
    assert extract_scalar(updated, SHELL_PID_BASELINE_FIELD) == capture_creation_time_baseline(own_pid)


def test_write_shell_pid_claim_omits_baseline_when_uncapturable(monkeypatch: pytest.MonkeyPatch) -> None:
    """C-007: a claim still succeeds (shell_pid written) even when the baseline can't be captured."""
    monkeypatch.setattr(
        "specify_cli.core.process_liveness.capture_creation_time_baseline",
        lambda pid: None,
    )
    frontmatter = "work_package_id: WP01\nhistory: []\n"

    updated = write_shell_pid_claim(frontmatter, 999999)

    assert extract_scalar(updated, "shell_pid") == "999999"
    assert extract_scalar(updated, SHELL_PID_BASELINE_FIELD) is None


def test_write_shell_pid_claim_to_file_round_trips(tmp_path: Path) -> None:
    """T011/T016: the file-based route (spec-kitty implement) round-trips through the same helper."""
    wp_file = tmp_path / "WP01.md"
    wp_file.write_text(
        "---\nwork_package_id: WP01\ntitle: Example\nhistory: []\n---\n\n# Body\n",
        encoding="utf-8",
    )
    own_pid = os.getpid()

    write_shell_pid_claim_to_file(wp_file, own_pid)

    written = wp_file.read_text(encoding="utf-8")
    assert f'shell_pid: "{own_pid}"' in written
    baseline = capture_creation_time_baseline(own_pid)
    assert baseline is not None
    assert f'{SHELL_PID_BASELINE_FIELD}: "{baseline}"' in written
    # Body must survive the round trip untouched.
    assert "# Body" in written


# ── T009 coverage: WPMetadata parses the new additive field ────────────────


def test_wp_metadata_parses_shell_pid_baseline_field() -> None:
    """WPMetadata (extra='forbid') must accept the new additive frontmatter field."""
    meta = WPMetadata.model_validate(
        {
            "work_package_id": "WP01",
            "shell_pid": "4242",
            SHELL_PID_BASELINE_FIELD: "1700000000.5",
        }
    )
    assert meta.shell_pid == 4242
    assert meta.shell_pid_created_at == "1700000000.5"


def test_wp_metadata_baseline_field_defaults_to_none() -> None:
    """Legacy WP files without the baseline field parse with it defaulted to None."""
    meta = WPMetadata.model_validate({"work_package_id": "WP01", "shell_pid": "4242"})
    assert meta.shell_pid_created_at is None


# ── stale_detection consumer wiring (T013 / T014 / T017 coverage) ──────────


def test_check_wp_staleness_legacy_absent_baseline_preserves_live_pid_trust(tmp_path: Path) -> None:
    """T017: a legacy claim (no baseline) preserves today's exact live-PID trust."""
    own_pid = str(os.getpid())

    result = check_wp_staleness(
        "WP01",
        tmp_path,
        threshold_minutes=10,
        shell_pid=own_pid,
        shell_pid_baseline=None,
    )

    assert result.stale.status == "fresh"
    assert result.stale.reason == LIVE_CLAIM_PROCESS_REASON


def test_check_wp_staleness_baseline_match_short_circuits_alive(tmp_path: Path) -> None:
    """Baseline present AND matches -> alive (positive branch, D3a)."""
    own_pid = os.getpid()
    baseline = capture_creation_time_baseline(own_pid)
    assert baseline is not None

    result = check_wp_staleness(
        "WP01",
        tmp_path,
        threshold_minutes=10,
        shell_pid=str(own_pid),
        shell_pid_baseline=baseline,
    )

    assert result.stale.status == "fresh"
    assert result.stale.reason == LIVE_CLAIM_PROCESS_REASON


def test_check_wp_staleness_baseline_mismatch_falls_to_timestamp_heuristic(tmp_path: Path) -> None:
    """T014: a present-but-MISMATCHED baseline (simulated reuse) -> not alive.

    Asserts the claim-liveness short-circuit is bypassed (reason is NOT
    ``LIVE_CLAIM_PROCESS_REASON``) and the check falls through to the
    commit-timestamp heuristic, never a hard-stale flag: on a non-git
    ``tmp_path`` with no commits detectable, the timestamp fallback treats
    "can't determine" as fresh (D3a: mismatch -> timestamp fallback, not a
    forced stale verdict).
    """
    own_pid = str(os.getpid())
    deliberately_wrong_baseline = "1.0"  # will not match the real process's create_time()

    result = check_wp_staleness(
        "WP01",
        tmp_path,
        threshold_minutes=10,
        shell_pid=own_pid,
        shell_pid_baseline=deliberately_wrong_baseline,
    )

    # Did NOT take the live-claim short-circuit path.
    assert result.stale.reason != LIVE_CLAIM_PROCESS_REASON
    # Fell through to the timestamp heuristic; no commits detectable on a bare
    # tmp_path -> "fresh" via the "can't determine, no commits yet" branch,
    # never a hard-coded stale verdict from the liveness compare itself.
    assert result.stale.status == "fresh"
