"""Deterministic #4017 concurrency interleave test (WP01, flipped by WP03).

Cluster A (#4017): concurrent installed-CLI invocations sharing one cold
``spec-kitty-home`` used to abort with ``RuntimeError``. The mechanism
(grounded in research.md Decision 1):

- The cold-installer anchor flock already serializes correctly
  (``asset_preparation.py:516-522``).
- ``assess_runtime()`` computes the loser's plan against an EMPTY home
  (``bootstrap.py:157-190``) -- a full create-tree.
- The post-lock re-check (``check_assets`` inside ``recheck_assets``,
  ``asset_preparation.py:482-496``) used to re-validate the loser's STALE
  observation snapshot and see the winner's materialized HOME destination
  nodes -> raised ``"Global asset input changed"``.

This module captured that race RED-FIRST (WP01), before any production-code
change. WP02 (role-tagged ``observe()``/``check_assets`` tolerance) and WP03
(re-assess-under-lock, ``bootstrap.ensure_runtime``) landed the fix; this
test is flipped (out-of-map edit, recorded per the WP03 handoff) to assert
the FIXED outcome: the loser converges to a no-op instead of raising. The
test still drives the REAL ``ensure_runtime()`` / ``assess_runtime()`` /
``check_assets()`` / ``recheck_assets()`` production path -- nothing about
the convergence is hand-asserted by the test. The interleave is forced
DETERMINISTICALLY (not a flaky repeat-N): the "loser" assessment is
captured for real against a genuinely cold home, the "winner" is driven to
materialize that same home for real via ``ensure_runtime()``, and
``assess_runtime`` is monkeypatched to return that exact captured stale
assessment ONLY on its first invocation during the loser's second
``ensure_runtime()`` call -- reproducing precisely what an independent
concurrent process would have observed before acquiring the lock, while
letting WP03's re-assess-under-lock (the SECOND call the fix makes) run
for real against the now-warm home, exactly as a genuine re-assess would.

The pre-fix witness this module originally pinned to (see the WP01 handoff
report and ``tests/e2e/test_worktree_owned_root_concurrency.py::
test_installed_cli_keeps_two_owned_worktrees_isolated``, T002) is retained
below as a negative assertion: that signal must never reappear.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import specify_cli.runtime.bootstrap as bootstrap
from specify_cli.runtime.bootstrap import assess_runtime, ensure_runtime

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# Exact witness substring, pinned to the T002 installed-CLI snapshot
# (see WP01 handoff report). Pre-fix, ``check_assets``
# (asset_preparation.py:490) raised ``f"Global asset input changed: ..."``.
# Post-fix (WP03) this signal must never be raised for this interleave.
GLOBAL_ASSET_INPUT_CHANGED_SIGNAL = "Global asset input changed"
GLOBAL_ASSET_WRITE_FAILED_SIGNAL = "global_asset_write_failed"

# OPERATOR_SIGNAL_CONTRACT (research.md Decision 2 / contracts/
# operator-signal-and-coverage.md): the human sentence WP03 emits on the
# converged-no-op path via the existing ``bootstrap`` module logger.
CONCURRENT_PEER_NO_OP_SIGNAL = "already materialized by a concurrent peer; nothing applied"


@pytest.fixture()
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ``SPEC_KITTY_HOME`` at a genuinely cold (nonexistent) directory."""
    home = tmp_path / "kittify"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    return home


@pytest.fixture()
def fake_assets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a minimal fake package asset root and point discovery at it.

    Mirrors ``tests/runtime/test_bootstrap_unit.py``'s fixture of the same
    name so ``assess_runtime()``/``ensure_runtime()`` can run for real
    without a full installed package layout.
    """
    pkg_root = tmp_path / "package"
    missions = pkg_root / "missions"
    (missions / "software-dev").mkdir(parents=True)
    (missions / "software-dev" / "mission.yaml").write_text("test-mission")
    (missions / "software-dev" / "templates").mkdir()
    (missions / "software-dev" / "templates" / "spec.md").write_text("test-template")

    scripts = pkg_root / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "validate.py").write_text("# validate")

    (pkg_root / "AGENTS.md").write_text("# Agents")

    monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(missions))
    return missions


class TestEnsureRuntimeConcurrentColdHomeInterleave:
    """#4017: a loser that observed a cold home mid-materialize converges.

    Structural/deterministic capture (FR-006, SC-002). NOT a dice-roll
    ``range(N)`` repeat: the interleave is forced by capturing the loser's
    real stale assessment first, materializing the home for real via a
    genuine winner ``ensure_runtime()`` call, then handing the loser's own
    already-captured stale assessment back to a second real
    ``ensure_runtime()`` call via a monkeypatched ``assess_runtime`` seam
    that only intercepts the FIRST call the loser's ``ensure_runtime()``
    makes -- WP03's re-assess-under-lock (the SECOND call) reaches the
    real, unpatched ``assess_runtime()`` and observes the genuinely warm
    home, exactly as an independent concurrent process's re-assess would.
    """

    def test_loser_reassess_against_materialized_home_converges_to_no_op(
        self,
        fake_home: Path,
        fake_assets: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # --- Arrange: the loser observes the shared home while it is cold. ---
        assert not fake_home.exists(), "fixture must start genuinely cold"
        loser_stale_assessment = assess_runtime()
        assert loser_stale_assessment.complete, "the cold-home assessment must be a usable create-plan for the interleave to be meaningful"
        assert loser_stale_assessment.effects, (
            "a cold home must produce a non-empty create-plan (full populate); an empty-effects plan would take the warm fast-path and could never observe the race"
        )

        # --- Act (winner): materialize the home for real through the ---
        # --- production path, using a genuinely fresh assessment. ---
        ensure_runtime()
        assert fake_home.is_dir(), "winner must have materialized the shared home"

        # --- Act (loser): force the deterministic interleave. The loser's ---
        # second ``ensure_runtime()`` call is handed back the EXACT stale
        # assessment it captured before the winner ran -- exactly what an
        # independent concurrent process would carry into its own
        # recheck-under-lock -- but ONLY ONCE: the real ``assess_runtime``
        # is restored immediately after, so WP03's re-assess-under-lock
        # (the fix's own second internal call) genuinely re-observes the
        # now-warm home rather than replaying the same stale object.
        real_assess_runtime = bootstrap.assess_runtime
        calls = {"n": 0}

        def _fake_assess_runtime(**kwargs: object) -> object:
            calls["n"] += 1
            if calls["n"] == 1:
                return loser_stale_assessment
            return real_assess_runtime(**kwargs)

        monkeypatch.setattr(bootstrap, "assess_runtime", _fake_assess_runtime)

        with caplog.at_level("INFO", logger=bootstrap.logger.name):
            ensure_runtime()  # must NOT raise -- the loser converges to a no-op.

        # --- Assert: the race signals are absent, and the operator signal ---
        # --- (OPERATOR_SIGNAL_CONTRACT) was emitted on the existing log sink. ---
        assert calls["n"] >= 2, "the fix must re-assess under the held lock, not just once up front"
        joined = "\n".join(caplog.messages)
        assert GLOBAL_ASSET_INPUT_CHANGED_SIGNAL not in joined
        assert GLOBAL_ASSET_WRITE_FAILED_SIGNAL not in joined
        assert CONCURRENT_PEER_NO_OP_SIGNAL in joined, (
            f"expected the OPERATOR_SIGNAL_CONTRACT sentence on the converged-no-op path, got log lines: {caplog.messages!r}"
        )
