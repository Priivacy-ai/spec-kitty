"""WP03 (FR-003) — single home-resolution authority enumerating guard.

The retrospective home (``retrospective.yaml``) must be resolved through ONE
primary-anchored authority (``resolve_retrospective_home`` →
``primary_feature_dir_for_mission`` gated by ``is_primary_artifact_kind``). Today
SIX placement sites used to resolve the home independently — five via the
coord-aware ``resolve_feature_dir_for_*`` resolvers, one via a hardcoded
``.kittify/missions/<id>/retrospective.yaml`` payload string. Any of them landed
the record in the ephemeral coord worktree (or reported a stale path), re-splitting
the brain (#1771).

This module is the anti-rename-vacuous guard: it ENUMERATES the home-resolution
surfaces by AST (no hardcoded count) and asserts that NONE of the placement
modules reintroduces an independent resolution. A 7th site — or reverting site #6
to its hardcoded payload — FAILS the build here, so a future edit cannot quietly
re-open the coord-leak.

Discipline (#2071): the assertion is over the observable AST of the placement
surfaces, derived dynamically — not a frozen list of line numbers.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import specify_cli.post_merge.retrospective_terminus as post_merge_terminus
import specify_cli.retrospective.lifecycle_events as lifecycle_events
import specify_cli.retrospective.writer as writer
import runtime.next._internal_runtime.retrospective_terminus as runtime_terminus

# AST-based import-boundary / single-authority structural guard. Selected by the
# `misc` integration shard's `(git_repo or integration or architectural)` marker
# expr; `unit` is selected by NO CI gate, so it ran in zero gates (gate-coverage
# orphan ratchet).
pytestmark = [pytest.mark.architectural]

# The retrospective PLACEMENT surfaces — the modules that resolve the home a
# record is written to (NOT the read-only resolver module itself, which keeps the
# coord-aware primitives for genuine STATUS reads). Derived from the WP03
# ``owned_files`` placement set.
_PLACEMENT_MODULES = (
    writer,
    lifecycle_events,
    post_merge_terminus,
    runtime_terminus,
)

# The retired coord-aware resolvers — a placement site that CALLS one of these is
# an independent home-resolution (the #1771 leak source). They remain importable
# (genuine topology-aware STATUS reads use them), but NEVER from a placement site.
_COORD_AWARE_RESOLVERS = frozenset(
    {"resolve_feature_dir_for_slug", "resolve_feature_dir_for_mission"}
)

# The single sanctioned authority surface a placement site may route through.
_AUTHORITY_NAMES = frozenset(
    {"resolve_retrospective_home", "canonical_record_path", "primary_feature_dir_for_mission"}
)

# Functions that are RE-HOMED-OFF the placement partition: load-bearing
# back-compat READ paths (C-004 KEEP). ``_legacy_record_path`` constructs the
# pre-#1771 ``.kittify/missions/<id>/retrospective.yaml`` READ path so archived
# records still resolve — it is NOT a placement (write) site and is excepted from
# the hardcoded-payload scan. (An EXCEPTION, not an exemption: it stays a READ
# path; reintroducing the literal in a placement function still fails.)
_READ_PATH_FUNCTIONS = frozenset({"_legacy_record_path", "resolve_existing_record_path"})


def _module_source(module: object) -> tuple[str, str]:
    """Return ``(path, source)`` for a module object."""
    path = Path(module.__file__)  # type: ignore[attr-defined]
    return str(path), path.read_text(encoding="utf-8")


def _called_names(tree: ast.AST) -> set[str]:
    """Return the set of called function NAMES across a module AST.

    Captures both ``name(...)`` (``ast.Name``) and ``obj.name(...)``
    (``ast.Attribute``) call targets so a coord-aware resolver invoked either way
    is discovered.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def _placement_string_literals(tree: ast.AST) -> set[str]:
    """Return string constants from PLACEMENT code only (read-path funcs excluded).

    The load-bearing back-compat READ paths (:data:`_READ_PATH_FUNCTIONS`)
    legitimately construct the legacy ``.kittify/missions/<id>/`` literal so
    archived records still resolve (C-004 KEEP); their bodies are excluded so the
    scan flags only a PLACEMENT (write) site that hardcodes the payload.
    """
    skip_funcs = {
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name in _READ_PATH_FUNCTIONS
    }
    skip_nodes: set[int] = set()
    for func in skip_funcs:
        skip_nodes.update(id(n) for n in ast.walk(func))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in skip_nodes
    }


def _hardcoded_kittify_retrospective_payloads(tree: ast.AST) -> list[str]:
    """Return ``.kittify/missions/.../retrospective.yaml`` style hardcoded joins.

    Detects the site #6 anti-pattern: a PLACEMENT path constructed from the literal
    ``.kittify`` + ``missions`` + ``retrospective.yaml`` segments (a hardcoded
    placement that bypasses the authority). Enumerated from the AST string
    constants of placement code, never a frozen count.
    """
    literals = _placement_string_literals(tree)
    offenders: list[str] = []
    if {".kittify", "missions"} <= literals and "retrospective.yaml" in literals:
        offenders.append(".kittify/missions/<id>/retrospective.yaml")
    return offenders


def test_no_placement_site_calls_a_coord_aware_resolver() -> None:
    """No placement module resolves the home via a coord-aware resolver (FR-003).

    Enumerates every placement surface's call graph by AST and asserts none calls
    ``resolve_feature_dir_for_slug`` / ``resolve_feature_dir_for_mission`` — those
    select the coord worktree and re-open #1771. A 7th site that reintroduces one
    fails HERE.
    """
    offenders: list[str] = []
    for module in _PLACEMENT_MODULES:
        path, source = _module_source(module)
        called = _called_names(ast.parse(source))
        leaked = called & _COORD_AWARE_RESOLVERS
        if leaked:
            offenders.append(f"{path}: calls {sorted(leaked)}")

    assert not offenders, (
        "Retrospective placement site(s) resolve the home independently via a "
        "coord-aware resolver (the #1771 coord-leak). Route through "
        "resolve_retrospective_home instead:\n" + "\n".join(offenders)
    )


def test_no_placement_site_hardcodes_kittify_retrospective_payload() -> None:
    """No placement module hardcodes the ``.kittify/missions/.../retrospective.yaml`` path.

    Reverting site #6 (``runtime ... retrospective_terminus._record_path_str``) to
    its hardcoded ``.kittify`` payload re-splits the brain (the event reports a path
    the record no longer lives at). This enumerating check FAILS on any such revert.
    """
    offenders: list[str] = []
    for module in _PLACEMENT_MODULES:
        path, source = _module_source(module)
        hits = _hardcoded_kittify_retrospective_payloads(ast.parse(source))
        if hits:
            offenders.append(f"{path}: {hits}")

    assert not offenders, (
        "Retrospective placement site(s) hardcode a .kittify/missions/ "
        "retrospective payload instead of routing through the authority:\n"
        + "\n".join(offenders)
    )


def test_every_placement_module_routes_through_the_authority() -> None:
    """Each placement module references the single authority surface (positive guard).

    Beyond the negative checks above, assert each placement module actually CALLS
    the sanctioned authority (``resolve_retrospective_home`` / ``canonical_record_path``
    / ``primary_feature_dir_for_mission``) — so a module that drops home-resolution
    to an unrelated improvised path (neither coord-aware NOR authority) is caught.
    """
    missing: list[str] = []
    for module in _PLACEMENT_MODULES:
        path, source = _module_source(module)
        called = _called_names(ast.parse(source))
        if not (called & _AUTHORITY_NAMES):
            missing.append(path)

    assert not missing, (
        "Placement module(s) do not route home-resolution through the single "
        "authority surface:\n" + "\n".join(missing)
    )


def test_writer_authority_gates_on_primary_partition_kind() -> None:
    """The authority is gated by ``is_primary_artifact_kind(RETROSPECTIVE)``.

    A rename-only "consolidation" that drops the partition gate would silently
    re-home the record if RETROSPECTIVE were ever re-partitioned to a coord kind.
    Pin that the authority body references both the gate predicate and the kind.
    """
    _path, source = _module_source(writer)
    tree = ast.parse(source)
    func = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "resolve_retrospective_home"
    )
    names = _called_names(func)
    referenced = {
        node.attr
        for node in ast.walk(func)
        if isinstance(node, ast.Attribute)
    } | {
        node.id for node in ast.walk(func) if isinstance(node, ast.Name)
    }

    assert "is_primary_artifact_kind" in names, (
        "resolve_retrospective_home must gate on is_primary_artifact_kind(RETROSPECTIVE)."
    )
    assert "RETROSPECTIVE" in referenced, (
        "resolve_retrospective_home must reference MissionArtifactKind.RETROSPECTIVE."
    )
    assert "primary_feature_dir_for_mission" in names, (
        "resolve_retrospective_home must compose through primary_feature_dir_for_mission."
    )
    # FR-011 write leg (#2136/#2164): the handle MUST be canonicalized before the
    # topology-blind primitive composes it. Pin the CONTRACT (one of the sanctioned
    # caller-side canonicalizers is called), not a single function name — #2164
    # upgraded the fold from ``_canonicalize_bare_modern_handle`` (bare-human-slug
    # ONLY) to the fuller ``_canonicalize_primary_read_handle`` (identity forms +
    # bare-human-slug), so a name-pinned assertion would false-red on the cure.
    _SANCTIONED_CANONICALIZERS = {
        "_canonicalize_primary_read_handle",
        "_canonicalize_bare_modern_handle",
    }
    assert names & _SANCTIONED_CANONICALIZERS, (
        "resolve_retrospective_home must canonicalize the handle (FR-011 write leg) "
        f"via one of {sorted(_SANCTIONED_CANONICALIZERS)}; called: {sorted(names)}"
    )
