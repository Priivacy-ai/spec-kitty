"""#2157a: one-pass charter-preflight prerequisite gate (WP04).

Before this fix, ``_derive_blocked_reason`` (``preflight/runner.py``) picked
only the FIRST non-passing check among the charter-owed chain
(``charter_source -> synced_bundle -> synthesized_drg``), so an operator with
multiple simultaneously-broken prerequisites had to fix one, re-run
preflight, discover the next, and repeat. This module locks in the fix:
``blocked_reason`` now enumerates EVERY non-passing check in one pass.

Covers:

- ``test_blocked_reason_enumerates_all_non_passing_checks``: T014 red-first
  repro -- construct >=2 simultaneously non-passing checks and assert ALL of
  them (not just the first) are named in ``blocked_reason``. Written against
  the DESIRED (post-fix) behaviour, so it is RED against the unmodified
  ``_derive_blocked_reason`` and GREEN after the T015 fix.
- ``test_single_failing_check_blocked_reason_unchanged`` /
  ``test_all_pass_blocked_reason_still_none``: behaviour-preserving pins --
  the all-pass and single-failing-check outcomes are byte-for-byte identical
  to the pre-fix format.
- ``test_multi_failure_per_check_verdicts_pinned``: R-07 guard -- aggregation
  is additive only; no per-check verdict (state/remediation) changes because
  another check also failed.
- ``test_blocked_reason_schema_stays_a_single_string``: OUTPUT-SHAPE PIN --
  ``blocked_reason`` stays a single ``str | None`` field on
  ``CharterPreflightResult`` (``result.py`` is not owned by this WP).
- ``test_end_to_end_activation_induced_drg_staleness_surfaces_in_report``:
  ties the WP03 dependency to value -- an activation-induced
  ``synthesized_drg`` staleness (the #2759 seam) is correctly surfaced by
  the (now-fixed) aggregation.
- ``test_activation_driven_check_enumerated_alongside_another_failure``:
  exercises ``_derive_blocked_reason`` directly with a REAL activation-driven
  ``synthesized_drg`` check plus a synthetic second failure, because the
  freshness computer's own cascade rule (the activation-parity read is only
  reached once ``synced_bundle`` is independently fresh) makes it
  structurally impossible to combine a genuine activation-parity
  ``synthesized_drg`` failure with an independently-stale
  ``charter_source``/``synced_bundle`` through ``compute_freshness`` alone.
- ``test_c004_fence_analysis_report_not_invoked``: the analyzer-freshness
  gate (``check_analysis_report_current``, #2157b) is a different subsystem
  and must not be touched by this fix.
- ``test_refresh_command_prefix_is_hoisted_shared_constant``: campsite
  (S1192) -- the three refresh commands share a hoisted
  ``["spec-kitty", "charter"]`` prefix constant instead of repeating the
  literal (their tails differ).
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from textwrap import dedent

import pytest
from ruamel.yaml import YAML

from charter.invocation_context import ProjectContext
from charter.pack_manager import CharterPackManager
from specify_cli.charter_runtime.freshness import compute_freshness
from specify_cli.charter_runtime.preflight import (
    CharterPreflightCheck,
    CharterPreflightResult,
    run_charter_preflight,
)
from specify_cli.charter_runtime.preflight import runner as runner_module
from specify_cli.charter_runtime.preflight.runner import _PASS_STATES

pytestmark = [pytest.mark.git_repo]

from ..charter_preflight._fixtures import (
    init_git_repo,
    make_fresh_repo,
    seed_bundle_files,
    seed_charter,
    seed_manifest,
    write_metadata,
)

# Real, stable built-in artifact (production-shaped id, not a placeholder --
# mirrors the pinning rationale already established in
# ``test_freshness_activation_visibility.py``).
_REAL_DIRECTIVE_STEM = "001-architectural-integrity-standard"


# ---------------------------------------------------------------------------
# Local fixture helpers (WP03 activation seam) -- kept local to this WP's
# owned test file rather than importing a sibling test module's private
# helper.
# ---------------------------------------------------------------------------


def _write_references(charter_dir: Path, entries: list[dict[str, str]]) -> None:
    charter_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0.0",
        "generated_at": "2026-07-17T00:00:00Z",
        "mission": "software-dev",
        "template_set": "software-dev-default",
        "languages": ["python"],
        "references": entries,
    }
    yaml = YAML()
    yaml.default_flow_style = False
    with (charter_dir / "references.yaml").open("w", encoding="utf-8") as handle:
        yaml.dump(payload, handle)


def _seed_project_graph(repo: Path) -> None:
    graph_path = repo / ".kittify" / "doctrine" / "graph.yaml"
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph_path.write_text(
        dedent(
            """\
            schema_version: '1.0'
            generated_at: '2026-07-17T00:00:00Z'
            generated_by: test-fixture
            nodes: []
            edges: []
            """
        ),
        encoding="utf-8",
    )


def _write_config(repo: Path, content: str) -> None:
    kittify = repo / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text(content, encoding="utf-8")


def _seed_synthesized_repo(repo: Path) -> None:
    """Build a fully-fresh repo whose ``synthesized_drg`` read-path reaches
    the activation-parity check (all three layers ``fresh``)."""
    init_git_repo(repo)
    charter_path, metadata_path = seed_charter(repo)
    write_metadata(metadata_path, charter_path)
    charter_dir = repo / ".kittify" / "charter"
    (charter_dir / "governance.yaml").write_text("schema_version: '1'\n", encoding="utf-8")
    (charter_dir / "directives.yaml").write_text("schema_version: '1'\n", encoding="utf-8")
    _write_references(charter_dir, [])
    seed_manifest(repo, built_in_only=False)
    _seed_project_graph(repo)


def _activate_real_directive(repo: Path) -> None:
    _write_config(repo, "activated_directives: []\n")
    CharterPackManager().activate(ProjectContext.from_repo(repo), "directive", _REAL_DIRECTIVE_STEM)


# ---------------------------------------------------------------------------
# T014 -- red-first: multi-failure enumeration
# ---------------------------------------------------------------------------


def test_blocked_reason_enumerates_all_non_passing_checks(tmp_path: Path) -> None:
    """Core #2157a fix: when multiple charter-owed checks are simultaneously
    non-passing, ``blocked_reason`` names ALL of them instead of only the
    first.

    Construction: a mismatched charter hash makes ``charter_source`` stale;
    because the synced-bundle files exist, that staleness cascades to
    ``synced_bundle`` (``_compute_synced_bundle``'s upstream-staleness rule);
    with no manifest/graph, ``synthesized_drg`` reports ``missing``. All
    three checks are non-passing at once -- pre-fix, only the first
    (``charter_source``) would have been named.
    """
    init_git_repo(tmp_path)
    charter_path, metadata_path = seed_charter(tmp_path)
    write_metadata(metadata_path, charter_path, mismatched=True)
    seed_bundle_files(tmp_path)
    # No manifest, no graph.yaml -> synthesized_drg = missing.

    result = run_charter_preflight(tmp_path, auto_refresh=False)

    assert result.passed is False
    non_passing = [c for c in result.checks if c.state not in _PASS_STATES]
    assert len(non_passing) >= 2  # precondition: genuinely multi-failure

    assert result.blocked_reason is not None
    for check in non_passing:
        remediation = check.remediation or "spec-kitty charter status"
        expected_line = f"{check.name} {check.state}; run `{remediation}`"
        assert expected_line in result.blocked_reason, (
            f"expected {check.name!r} to be enumerated in blocked_reason, "
            f"got: {result.blocked_reason!r}"
        )


# ---------------------------------------------------------------------------
# Behaviour-preserving pins
# ---------------------------------------------------------------------------


def test_single_failing_check_blocked_reason_unchanged(tmp_path: Path) -> None:
    """Exactly one non-passing check still produces the identical
    single-line format used before this WP (no list wrapping, no newline)."""
    init_git_repo(tmp_path)
    charter_path, metadata_path = seed_charter(tmp_path)
    write_metadata(metadata_path, charter_path)
    seed_bundle_files(tmp_path)
    # charter_source and synced_bundle are fresh; no manifest/graph ->
    # synthesized_drg is the ONLY non-passing check.

    result = run_charter_preflight(tmp_path, auto_refresh=False)

    assert result.passed is False
    non_passing = [c for c in result.checks if c.state not in _PASS_STATES]
    assert [c.name for c in non_passing] == ["synthesized_drg"]
    assert result.blocked_reason == "synthesized_drg missing; run `spec-kitty charter synthesize`"


def test_all_pass_blocked_reason_still_none(tmp_path: Path) -> None:
    """The all-pass outcome is unaffected by the enumerate-all change."""
    make_fresh_repo(tmp_path)

    result = run_charter_preflight(tmp_path, auto_refresh=False)

    assert result.passed is True
    assert result.blocked_reason is None


def test_multi_failure_per_check_verdicts_pinned(tmp_path: Path) -> None:
    """R-07: aggregation is additive only -- each check's own verdict
    (state/remediation) is unaffected by how many OTHER checks also fail."""
    init_git_repo(tmp_path)
    charter_path, metadata_path = seed_charter(tmp_path)
    write_metadata(metadata_path, charter_path, mismatched=True)
    seed_bundle_files(tmp_path)

    result = run_charter_preflight(tmp_path, auto_refresh=False)

    by_name = {c.name: c for c in result.checks}
    assert by_name["charter_source"].state == "stale"
    assert by_name["charter_source"].remediation == "spec-kitty charter sync"
    assert by_name["synced_bundle"].state == "stale"
    assert by_name["synced_bundle"].remediation == "spec-kitty charter sync"
    assert by_name["synthesized_drg"].state == "missing"
    assert by_name["synthesized_drg"].remediation == "spec-kitty charter synthesize"


def test_blocked_reason_schema_stays_a_single_string(tmp_path: Path) -> None:
    """OUTPUT-SHAPE PIN: the enumerate-all report is a single ``str`` on the
    existing ``blocked_reason`` field -- not a ``list[str]`` (that would
    spill into the un-owned ``result.py`` schema)."""
    init_git_repo(tmp_path)
    charter_path, metadata_path = seed_charter(tmp_path)
    write_metadata(metadata_path, charter_path, mismatched=True)
    seed_bundle_files(tmp_path)

    result = run_charter_preflight(tmp_path, auto_refresh=False)

    assert isinstance(result.blocked_reason, str)
    field_types = {f.name: f.type for f in dataclasses.fields(CharterPreflightResult)}
    assert field_types["blocked_reason"] == "str | None"


# ---------------------------------------------------------------------------
# WP03 dependency -- activation-induced synthesized_drg staleness
# ---------------------------------------------------------------------------


def test_end_to_end_activation_induced_drg_staleness_surfaces_in_report(tmp_path: Path) -> None:
    """Ties the WP03 dependency to value: an activation-induced
    ``synthesized_drg`` staleness (the #2759 seam WP03 wired into the
    freshness read-path) is correctly surfaced by the (now-fixed) one-pass
    aggregation -- proving it reports the activation-visible signal, not
    just the pre-existing content-identity staleness reasons.
    """
    _seed_synthesized_repo(tmp_path)
    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"  # baseline

    _activate_real_directive(tmp_path)
    assert compute_freshness(tmp_path).synthesized_drg.state == "stale"  # WP03 seam fired

    result = run_charter_preflight(tmp_path, auto_refresh=False)

    assert result.passed is False
    assert result.blocked_reason is not None
    assert "synthesized_drg stale; run `spec-kitty charter generate && spec-kitty charter synthesize`" in result.blocked_reason
    drg = next(c for c in result.checks if c.name == "synthesized_drg")
    assert drg.state == "stale"
    assert drg.detail is not None
    assert f"directive/{_REAL_DIRECTIVE_STEM}" in drg.detail


def test_activation_driven_check_enumerated_alongside_another_failure(tmp_path: Path) -> None:
    """The activation-driven ``synthesized_drg`` check (WP03's real signal)
    is enumerated correctly even when it is not the only non-passing check.

    Exercises ``_derive_blocked_reason`` directly (the fixed #2157a
    function) with a REAL activation-driven ``synthesized_drg`` check
    (obtained via ``compute_freshness`` + a real ``CharterPackManager``
    activation) alongside a synthetic second failure -- the freshness
    computer's own cascade rule (the activation-parity read is only reached
    once ``synced_bundle`` is independently ``fresh``) makes it structurally
    impossible to combine a genuine activation-parity ``synthesized_drg``
    failure with an independently-stale ``charter_source``/``synced_bundle``
    through ``compute_freshness`` alone.
    """
    _seed_synthesized_repo(tmp_path)
    _activate_real_directive(tmp_path)
    real_checks = runner_module._build_checks(compute_freshness(tmp_path))
    real_drg_check = next(c for c in real_checks if c.name == "synthesized_drg")
    assert real_drg_check.state == "stale"  # sanity: genuinely activation-driven

    synthetic_source_check = CharterPreflightCheck(
        name="charter_source",
        state="stale",
        detail="charter source is stale",
        remediation="spec-kitty charter sync",
    )
    checks = [synthetic_source_check, real_drg_check]

    reason = runner_module._derive_blocked_reason(checks)

    assert "charter_source stale; run `spec-kitty charter sync`" in reason
    assert "synthesized_drg stale; run `spec-kitty charter generate && spec-kitty charter synthesize`" in reason
    assert reason.index("charter_source") < reason.index("synthesized_drg")  # ordering preserved


# ---------------------------------------------------------------------------
# C-004 fence -- the analyzer-freshness gate is a different subsystem
# ---------------------------------------------------------------------------


def test_c004_fence_analysis_report_not_invoked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """C-004: the analyzer-freshness gate (``check_analysis_report_current``,
    #2157b) is a DIFFERENT subsystem and must not be touched/invoked by this
    WP's one-pass charter-preflight aggregation fix."""
    import specify_cli.analysis_report as analysis_report_module

    def _must_not_be_called(*args: object, **kwargs: object) -> None:
        raise AssertionError(
            "check_analysis_report_current must not be invoked by charter "
            "preflight (#2157a/#2157b fence)"
        )

    monkeypatch.setattr(analysis_report_module, "check_analysis_report_current", _must_not_be_called)

    init_git_repo(tmp_path)
    charter_path, metadata_path = seed_charter(tmp_path)
    write_metadata(metadata_path, charter_path, mismatched=True)
    seed_bundle_files(tmp_path)

    result = run_charter_preflight(tmp_path, auto_refresh=False)

    assert result.passed is False  # sanity: exercised the failure/aggregation path


# ---------------------------------------------------------------------------
# Campsite (S1192): hoisted refresh-command prefix
# ---------------------------------------------------------------------------


def test_refresh_command_prefix_is_hoisted_shared_constant() -> None:
    """The three refresh commands (``sync`` / ``synthesize`` /
    ``bundle validate``) share a hoisted ``["spec-kitty", "charter"]``
    prefix constant instead of each repeating the literal."""
    assert list(runner_module._SPEC_KITTY_CHARTER_PREFIX) == ["spec-kitty", "charter"]
