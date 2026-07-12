"""Identity/coord resolution seam for ``runtime.next.runtime_bridge`` (#2531 WP10).

**The hottest fracture line in the god-module decomposition** — coord-branch
naming, mission-ULID resolution, and primary-feature-dir resolution. It
carries the mission's fattest scar debt (#2091/#1978/#1918/#1814/#2069) and is
correctness-critical: a malformed coord branch composed here eventually drives
a ``git worktree`` call that exits 128. It is cut LAST (behind the fattest
golden coverage: the WP01 parity oracle + WP02 compat guard, both proven green
on every prior extraction) because a silent drift in this cluster is the most
dangerous possible regression in the whole mission.

Sole home of:

- :func:`_primary_runtime_feature_dir` — the topology-BLIND primary-checkout
  mission dir resolver identity/meta reads anchor on (the #2091 fix).
- :func:`_resolve_coordination_branch` — coord-branch naming: reads the
  declared ``coordination_branch`` from ``meta.json`` when present, otherwise
  composes it via the fail-closed :func:`mission_branch_name_required` seam
  (#1978). Raises :class:`BranchIdentityUnresolved` for a genuinely
  unresolvable modern mission — this fail-loud contract is preserved EXACTLY,
  never swallowed by a fallback (C-001; the exit-128 scar this WP is named
  for is what a silently-wrong compose here would eventually cause).
- :func:`_resolve_mission_ulid` — reads the canonical ULID ``mission_id`` from
  ``meta.json`` via the identity SSOT (:func:`resolve_mission_identity`),
  fail-closed (``None``, never the slug, when absent — FR-004).

**KEEP-IN-PLACE / not moved.** ``_wrap_with_decision_git_log`` and
``_mission_routes_through_coordination`` stay in the residual
(``runtime_bridge.py``) per research.md §Compat — they are the *callers* of
this cluster, not part of it, and moving them is neither requested by this WP
nor necessary (their bare intra-module calls to the thin delegates below
already resolve correctly against ``runtime_bridge``'s own patchable globals,
since caller and patch target share a module).

**The 🔴 grounded false-green minefield this seam exists to close (research.md
§Compat).** ``_primary_runtime_feature_dir`` is patched 6x
(``tests/runtime/test_runtime_bridge_identity.py:71-222``) via
``monkeypatch``/``unittest.mock.patch("runtime.next.runtime_bridge.
_primary_runtime_feature_dir", ...)``. Before this WP, its two callers
(``_resolve_coordination_branch`` / ``_resolve_mission_ulid``) lived in the
SAME module as the patch target, so their bare calls resolved against that
module's own globals — patchable by construction. Now that all three symbols
live together in *this* seam module, a bare intra-seam call from either caller
to ``_primary_runtime_feature_dir`` would resolve against **this module's**
globals instead, making every one of those 6 patches a silent no-op (the exact
mechanism ``tests/runtime/test_bridge_compat_surface.py``'s module docstring
names as the guard's reason for existing). Both callers therefore route their
``_primary_runtime_feature_dir`` lookup through a **live, deferred import of
``runtime_bridge`` itself** (``from runtime.next import runtime_bridge as _rb``,
function-scoped — the same ``_rb.<name>(...)`` lazy-accessor idiom
``runtime_bridge_io``/``runtime_bridge_composition``/``runtime_bridge_
retrospective`` already use for their own intra-seam-call risks), so
``monkeypatch.setattr(runtime_bridge, "_primary_runtime_feature_dir", ...)``
is observed identically to the pre-extraction behavior. The deferred (not
top-level) import also breaks the residual<->identity import cycle:
``runtime_bridge`` imports this module at its own top level to source the
thin compat delegates below, so a top-level back-import here would be
circular.

``runtime_bridge.py`` keeps a **native thin compat delegate** — a real
``def`` statement, never a plain ``import`` alias — under each of these three
names. This is mandatory, not stylistic: a plain re-export changes the
symbol's ``__module__`` to ``runtime_bridge_identity``, which would flip
``tests/runtime/test_bridge_compat_surface.py::
test_guard_b_identity_reexport_for_relocated_symbols`` (a FROZEN gate file
that asserts the cross-module compat surface is EXACTLY the pre-existing
3-symbol ``runtime.next.decision`` baseline) — the same mechanism WP03's
``runtime_bridge_engine``, WP04's ``runtime_bridge_retrospective``, WP05's
``runtime_bridge_io``, and WP08's ``runtime_bridge_composition`` docstrings
each document for their own relocated symbols.

Import DAG (research.md §Import DAG): this module may import
``runtime_bridge_io`` (not needed today — none of the three functions above
requires an I/O-port call); it must NOT be imported by ``runtime_bridge_
cores`` (enforced by ``tests/runtime/test_bridge_identity.py``'s architecture
boundary test). No top-level ``decision.py -> runtime_bridge*`` edge is
introduced (C-007) — this module imports neither ``runtime_bridge`` nor
``decision`` at module scope.

De-godding effort: https://github.com/Priivacy-ai/spec-kitty/issues/2531
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specify_cli.mission_metadata import load_meta_or_empty


def _primary_runtime_feature_dir(repo_root: Path, mission_slug: str) -> Path:
    """Return the PRIMARY-checkout mission feature dir for identity/meta reads.

    Mission identity (``mission_id``, ``coordination_branch``, stored topology)
    is persisted ONLY on the primary checkout's ``meta.json``. Under coordination
    topology the topology-aware resolver (``candidate_feature_dir_for_mission``)
    returns the coordination worktree once it is materialized — whose mission dir
    has NO ``meta.json`` — so reading identity there found nothing and fell back
    to the bare slug, yielding an empty ``mid8`` and a malformed
    ``kitty/mission-<slug>-`` coord branch (#2091). Anchor on the topology-BLIND
    :func:`primary_feature_dir_for_mission`, mirroring
    :func:`_mission_routes_through_coordination` (``runtime_bridge.py``) and the
    canonical precedent in ``core/paths.py`` (the same bug-class fixed for the
    merge target): the coord-aware resolver fail-closes for a
    materialized-but-empty coord worktree, so it must not gate primary-anchored
    identity reads.
    """
    from specify_cli.missions._read_path_resolver import (
        _canonicalize_primary_read_handle,
        primary_feature_dir_for_mission,
    )

    # WP05/FR-005: route through _canonicalize_primary_read_handle. The local
    # annotation re-narrows the specify_cli.* import from Any back to Path --
    # the project's follow_imports = "skip" mypy override for specify_cli.*
    # (pyproject.toml) means a cross-package call is otherwise seen as Any.
    result: Path = primary_feature_dir_for_mission(
        repo_root,
        _canonicalize_primary_read_handle(repo_root, mission_slug),
    )
    return result


def _resolve_coordination_branch(mission_slug: str, repo_root: Path) -> str:
    """Return the coordination branch for a mission from meta.json.

    When meta.json declares ``coordination_branch`` explicitly, that value is
    authoritative. Otherwise the branch is composed via the fail-closed WP01
    seam (:func:`coord_branch_name`/:func:`mission_branch_name_required`) using
    the declared ``mission_id``, instead of a bare ``kitty/mission-<slug>``
    f-string that drops the ``-<mid8>`` disambiguator (#1978). When the mission
    is legacy/unresolvable the seam still composes the legacy branch; a modern
    slug with no recoverable identity raises :class:`BranchIdentityUnresolved`,
    surfacing the lost identity rather than silently mis-composing (the
    malformed-coord-branch correctness path this WP is named for — preserved
    exactly, never swallowed here).
    """
    from runtime.next import runtime_bridge as _rb  # noqa: PLC0415 — deferred: breaks the residual<->identity import cycle AND routes the intra-seam _primary_runtime_feature_dir call through runtime_bridge's patchable namespace (module docstring — the identity-trio's grounded false-green trap)

    # load_meta_or_empty (post-#2091 silent contract) absorbs a missing or
    # malformed meta.json to {}, matching the prior try/except-{} absorption.
    meta: dict[str, Any] = load_meta_or_empty(
        _rb._primary_runtime_feature_dir(repo_root, mission_slug)
    )
    branch = meta.get("coordination_branch")
    if isinstance(branch, str) and branch.strip():
        return branch.strip()

    from specify_cli.lanes.branch_naming import mission_branch_name_required

    mission_id = meta.get("mission_id")
    resolved_id = mission_id.strip() if isinstance(mission_id, str) and mission_id.strip() else None
    # Local annotation re-narrows the specify_cli.* import from Any back to
    # str (follow_imports = "skip" mypy override, see the note above).
    composed: str = mission_branch_name_required(mission_slug, resolved_id)
    return composed


def _resolve_mission_ulid(mission_slug: str, repo_root: Path) -> str | None:
    """Read the canonical ULID mission_id from meta.json via the identity SSOT.

    WP04/FR-004: Routes through ``mission_metadata.resolve_mission_identity``
    (the single source of truth) instead of hand-rolling a json.loads read.
    Returns the ULID string when present, or ``None`` when absent — fail-closed:
    callers must NOT substitute the slug for the absent ULID.
    """
    from runtime.next import runtime_bridge as _rb  # noqa: PLC0415 — deferred: breaks the residual<->identity import cycle AND routes the intra-seam _primary_runtime_feature_dir call through runtime_bridge's patchable namespace (module docstring — the identity-trio's grounded false-green trap)
    from specify_cli.mission_metadata import resolve_mission_identity  # noqa: PLC0415

    feature_dir = _rb._primary_runtime_feature_dir(repo_root, mission_slug)
    # Local annotation re-narrows the specify_cli.* import from Any back to
    # str | None (follow_imports = "skip" mypy override, see the note above).
    mission_id: str | None = resolve_mission_identity(feature_dir).mission_id
    return mission_id
