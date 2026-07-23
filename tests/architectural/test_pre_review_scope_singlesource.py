"""FR-006 — pre-review scope-derivation single-source invariant.

Mission ``review-regression-gate-01KWX6DF`` WP01 (closes #572 + the per-WP
review-blind-spot facet of #1979; part of #2283). Proves
``specify_cli.review.scope_source.GateCoverageScopeSource`` reads the LIVE
CI-topology authorities in ``tests.architectural._gate_coverage`` for BOTH
group shapes:

- **per-shard groups** — their glob set already carries ``tests/**`` entries;
  the live authority is ``aggregate_filter_groups()``.
- **composite groups** — src-only glob sets; the live authority is the
  census's committed ``_COMPOSITE_ROUTING`` cone_roots.

...and that the catch-all exclusion (``core_misc``/``e2e``/``any_src``) holds
even though ``core_misc`` also matches the same files as a genuine per-shard
group would (it carries ``tests/**`` globs too — it is excluded by name, for
breadth, not by shape).

The mutation-bite tests below feed the derivation a stale/hand-authored
``filter_groups`` map, and a ``composite_routing`` map with every cone emptied
(simulating "the derivation consults only ``aggregate_filter_groups()``" —
the exact silent-under-coverage risk FR-006 exists to catch) and show the
derived scope changes accordingly — proving the DEFAULT (unoverridden) path
is not a hardcoded shard table shadowing these live authorities.

**Migrated (mission scopesource-gate-followup-01KY6S9P WP04).** The
derivation this file pins used to live as ``pre_review_gate.derive_test_scope``
+ its module-level glob/path helpers; WP04 retired that public copy (FR-001)
— the LIVE derivation now lives exclusively as a PRIVATE copy inside
:class:`~specify_cli.review.scope_source.GateCoverageScopeSource`. Every
assertion below is unchanged in substance, only retargeted onto the
surviving port: ``pre_review_gate.derive_test_scope(...)`` ->
``GateCoverageScopeSource(repo_root=..., *_override=...).scope_breakdown(path)``
/ ``.file_to_scope(path)``, and the module-level glob helpers ->
``scope_source``'s own private copies (``_glob_matches_file`` /
``_glob_to_pytest_target`` / ``_resolve_excluded_catchall_groups`` /
``_NAMED_CATCHALL_GROUPS``).
"""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from specify_cli.review import scope_source
from specify_cli.review.scope_source import GateCoverageScopeSource
from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.architectural]

REPO_ROOT = gc.REPO_ROOT

_STATUS_FILE = "src/specify_cli/status/emit.py"
_GIT_FILE = "src/specify_cli/git/git_ops.py"
_VALIDATORS_FILE = "src/specify_cli/validators/schema.py"


def _live_impl(
    *,
    filter_groups_override: Mapping[str, tuple[str, ...]] | None = None,
    composite_routing_override: Mapping[str, scope_source._CompositeRoute] | None = None,
) -> GateCoverageScopeSource:
    return GateCoverageScopeSource(
        repo_root=REPO_ROOT,
        filter_groups_override=filter_groups_override,
        composite_routing_override=composite_routing_override,
    )


@pytest.fixture(scope="module")
def live_groups() -> dict[str, tuple[str, ...]]:
    return gc.aggregate_filter_groups(gc.load_workflow_models())


# ---------------------------------------------------------------------------
# Grounding precondition (the spec's own worked example)
# ---------------------------------------------------------------------------


def test_status_file_is_a_member_of_status_core_misc_and_execution_context(
    live_groups: dict[str, tuple[str, ...]],
) -> None:
    """status/emit.py is genuinely ambiguous input: a member of >=1 catch-all
    (core_misc) AND >=1 focused per-shard group (status, execution_context) —
    so the shape derivation + exclusion actually has something to resolve,
    per the spec's own grounding."""
    members = {
        name
        for name, globs in live_groups.items()
        if any(scope_source._glob_matches_file(g, _STATUS_FILE) for g in globs)
    }
    assert {"status", "core_misc", "execution_context"} <= members


# ---------------------------------------------------------------------------
# Both shapes read the LIVE authorities (default, unoverridden path)
# ---------------------------------------------------------------------------


def test_per_shard_shape_reads_live_test_globs_from_aggregate_filter_groups(
    live_groups: dict[str, tuple[str, ...]],
) -> None:
    """SC-003: status/emit.py resolves via the live status group's OWN test
    globs — not a hand-authored map."""
    expected = {
        scope_source._glob_to_pytest_target(g) for g in live_groups["status"] if g.startswith("tests/")
    }
    assert expected, "sanity: the live status group must carry >=1 tests/ glob"
    breakdown = _live_impl().scope_breakdown(_STATUS_FILE)
    assert expected <= set(breakdown.test_targets)


def test_catch_all_exclusion_holds_status_resolves_to_status_not_core_misc(
    live_groups: dict[str, tuple[str, ...]],
) -> None:
    """SC-003/SC-004/SC-005: the ~53-glob core_misc cone must NOT leak into
    the derived scope even though it also matches status/emit.py."""
    core_misc_only_targets = {
        scope_source._glob_to_pytest_target(g)
        for g in live_groups["core_misc"]
        if g.startswith("tests/") and g not in live_groups.get("status", ())
    }
    assert core_misc_only_targets, "sanity: core_misc must carry >=1 tests/ glob status doesn't share"
    breakdown = _live_impl().scope_breakdown(_STATUS_FILE)
    assert "tests/status" in breakdown.test_targets
    assert not (core_misc_only_targets & set(breakdown.test_targets))
    assert "core_misc" not in breakdown.matched_shard_groups


def test_composite_shape_reads_live_cone_roots_from_composite_routing() -> None:
    """SC-003: a git/** change resolves via the LIVE _COMPOSITE_ROUTING
    cone_roots, not any dorny test glob (auth_audit_git carries none)."""
    _, _, expected_cone_roots = gc._COMPOSITE_ROUTING["git"]
    assert expected_cone_roots, "sanity: git's committed cone_roots must be non-empty"
    breakdown = _live_impl().scope_breakdown(_GIT_FILE)
    assert set(expected_cone_roots) <= set(breakdown.test_targets)
    assert "git" in breakdown.matched_composite_dirs


def test_empty_cone_composite_dir_is_a_no_coverage_warn_not_silently_empty() -> None:
    """SC-007: validators is a real composite dir with EMPTY committed
    cone_roots — the derivation must surface it as unverified, never
    silently drop it as "clean"."""
    _, _, cone_roots = gc._COMPOSITE_ROUTING["validators"]
    assert cone_roots == (), "sanity: validators' committed cone_roots must be empty"
    breakdown = _live_impl().scope_breakdown(_VALIDATORS_FILE)
    assert not breakdown.test_targets
    assert breakdown.empty_cone_composite_dirs == ("validators",)


# ---------------------------------------------------------------------------
# Mutation-bite proofs: the derivation genuinely CONSULTS these authorities
# rather than shadowing them with a hardcoded table.
# ---------------------------------------------------------------------------


def test_stale_filter_groups_map_changes_the_derived_scope(
    live_groups: dict[str, tuple[str, ...]],
) -> None:
    """A stale/hand-authored map that strips status's test globs must change
    the derived scope — if the derivation ignored its ``filter_groups_override``
    input (i.e. shadowed it with a hardcoded shard table), this override would
    have NO effect and the test would fail to observe any difference."""
    stale_groups = {
        name: (tuple(g for g in globs if not g.startswith("tests/")) if name == "status" else globs)
        for name, globs in live_groups.items()
    }
    live_breakdown = _live_impl().scope_breakdown(_STATUS_FILE)
    stale_breakdown = _live_impl(filter_groups_override=stale_groups).scope_breakdown(_STATUS_FILE)
    assert "tests/status" in live_breakdown.test_targets
    assert "tests/status" not in stale_breakdown.test_targets
    assert stale_breakdown.test_targets != live_breakdown.test_targets


def test_composite_routing_override_is_genuinely_consulted_not_only_filter_groups() -> None:
    """The FR-006 headline risk: if the derivation consulted ONLY
    aggregate_filter_groups() — i.e. never read _COMPOSITE_ROUTING — a
    composite dir like ``git`` would end up with an EMPTY test scope
    (composite groups carry no tests/** globs at all), the exact
    silent-under-coverage the mission exists to prevent. Emptying every
    _COMPOSITE_ROUTING entry simulates that and must turn a genuinely
    covered dir into a no_coverage warn; the un-mutated default path must
    NOT be empty, proving it actually reads the live cone_roots."""
    emptied_routing = dict.fromkeys(gc._COMPOSITE_ROUTING, (None, None, ()))
    live_breakdown = _live_impl().scope_breakdown(_GIT_FILE)
    groups_only_breakdown = _live_impl(composite_routing_override=emptied_routing).scope_breakdown(_GIT_FILE)
    assert live_breakdown.test_targets
    assert not groups_only_breakdown.test_targets
    assert groups_only_breakdown.empty_cone_composite_dirs == ("git",)


def test_named_catchalls_are_the_breadth_judgment_pair(
    live_groups: dict[str, tuple[str, ...]],
) -> None:
    """The by-name half of the exclusion is exactly the breadth-judgment
    catch-alls (core_misc/e2e) — the ones whose breadth is NOT a structural
    property _gate_coverage.py exposes, so they cannot be tree-derived."""
    assert frozenset({"core_misc", "e2e"}) == scope_source._NAMED_CATCHALL_GROUPS
    # Both must be genuinely present in the live topology (guards a silent
    # rename of a real catch-all group slipping the by-name exclusion).
    assert {"core_misc", "e2e"} <= set(live_groups)


def test_resolver_also_excludes_every_src_star_whole_tree_probe_group(
    live_groups: dict[str, tuple[str, ...]],
) -> None:
    """The mechanical half: any group globbing the literal ``src/**`` whole-tree
    probe is excluded too. ``any_src`` (ci-quality.yml) and ``windows_critical``
    (ci-windows.yml, which globs ``src/**`` alongside ~20 windows-regression test
    files) are both live examples — merged into one namespace by
    aggregate_filter_groups(), so both must fall to the same exclusion or every
    src touch would drag in unrelated files and mask an SC-007 empty scope."""
    excluded = scope_source._resolve_excluded_catchall_groups(live_groups)
    src_star_groups = {name for name, globs in live_groups.items() if "src/**" in globs}
    assert src_star_groups, "sanity: >=1 live group must carry the src/** probe glob"
    assert "any_src" in src_star_groups
    assert src_star_groups <= excluded
    # The full exclusion is the named pair UNION the whole-tree probe groups.
    assert excluded == scope_source._NAMED_CATCHALL_GROUPS | src_star_groups


def test_windows_critical_src_star_group_does_not_leak_into_a_status_scope(
    live_groups: dict[str, tuple[str, ...]],
) -> None:
    """Regression guard for the ci-windows.yml ``src/**`` merge: a status/emit.py
    change must NOT pull windows_critical's ~20 specific test files into scope —
    they are unrelated windows-regression suites, and admitting them would both
    inflate cost and hide a genuinely-empty scope."""
    windows_only_targets = {
        scope_source._glob_to_pytest_target(g)
        for g in live_groups.get("windows_critical", ())
        if g.startswith("tests/")
    }
    if not windows_only_targets:
        pytest.skip("windows_critical carries no tests/ globs in this topology")
    breakdown = _live_impl().scope_breakdown(_STATUS_FILE)
    assert not (windows_only_targets & set(breakdown.test_targets))
