"""Execution-state context objects (canonical surface, internal module).

This is an **internal** submodule of the :mod:`mission_runtime` umbrella. It is
import-forbidden from outside the package — consumers use the symbols re-exported
from :mod:`mission_runtime` only (see ADR 2026-06-07-1 and
``tests/architectural/test_mission_runtime_surface.py``).

WP03 grows the hardened context value object into the **doc-09 fragment /
op-composite** model
(``docs/engineering_notes/runtime_and_state_overhaul/09-context-decomposition-model.md``).
``MissionExecutionContext`` is NOT a flat field bag: it is a deep module whose
hidden structure is a set of cohesive, domain-owned **value-object fragments**
(Identity, BranchRef, Workspace, StatusSurface, ArtifactPlacement, PromptSource).
An *operation* assembles only the fragments it needs (the op-composite); the
builder lives in :mod:`mission_runtime.resolution` (doc-09 §5 layer law).

Strangler compatibility (C-004 / NFR-001): the historical flat
:class:`ExecutionContext` substrate fields
(``feature_dir`` / ``target_branch`` / ``workspace_path`` / ``branch_name`` /
``execution_mode`` / ``mission_slug``) are preserved verbatim so consumers that
have not yet been converted keep reading the same attributes. The fragments are
*attached* to the same object; nothing is removed. ``ActionContext`` remains a
re-exported alias of the canonical :class:`ExecutionContext` name.

Single-derivation invariants (T009 / FR-012 / C-CTX-3): ``mid8`` is derived
**exactly once** (in :class:`IdentityFragment`, as ``mission_id[:8]``) and
``target_branch`` is resolved **exactly once** (carried on
:class:`BranchRefFragment`); no other call site recomputes either value.
"""
from __future__ import annotations

import enum
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, ClassVar


class ExecutionMode(enum.Enum):
    """How an action's execution context is resolved.

    ``WORKTREE`` resolves against a lane worktree; ``CODE_CHANGE`` resolves
    against an in-place checkout. The resolved string mode is surfaced on
    :attr:`ExecutionContext.execution_mode` (which carries the raw workspace
    string), so this enum is the typed vocabulary callers may compare against.
    """

    WORKTREE = "worktree"
    CODE_CHANGE = "code_change"


class CommitTargetKind(enum.Enum):
    """Topology classification of a :class:`CommitTarget` (ADR-2026-06-03-2).

    ``PRIMARY`` — the ref is the primary-checkout branch (no coordination split).
    ``COORDINATION`` — the ref is a separate coordination branch distinct from
    the mission target branch.
    ``FLATTENED`` — landing == coordination == target on a single branch; there
    is no primary↔coordination split to reconcile (C-001).
    """

    PRIMARY = "primary"
    COORDINATION = "coordination"
    FLATTENED = "flattened"


@dataclass(frozen=True)
class CommitTarget:
    """The ONE ref that artifacts + status events resolve to (ADR-2026-06-03-2).

    A self-validating value object that makes the FR-004 invariant
    (planning artifacts AND status events resolve to the **same**
    ``destination_ref``) a *type* rather than a runtime check: a caller that
    holds a :class:`CommitTarget` cannot commit to a mismatched pair because the
    pairing of ``ref`` and topology ``kind`` is captured here once.

    Under flattened topology ``kind == FLATTENED`` and there is no
    primary↔coordination split to reconcile.
    """

    ref: str
    kind: CommitTargetKind


@dataclass(frozen=True)
class IdentityFragment:
    """F0 — the canonical mission identity every other fragment keys on.

    ``mid8`` is the **single derivation point** for the 8-char branch/worktree
    disambiguator: it is computed as ``mission_id[:8]`` here and nowhere else
    (FR-012 / C-CTX-3). The ``__post_init__`` invariant guards against a caller
    constructing an inconsistent fragment.
    """

    mission_id: str
    mid8: str
    mission_slug: str

    def __post_init__(self) -> None:
        expected = self.mission_id[:8]
        if self.mid8 != expected:
            raise ValueError(
                "IdentityFragment.mid8 must be mission_id[:8] "
                f"(got mid8={self.mid8!r}, mission_id={self.mission_id!r}); "
                "mid8 is single-derived (FR-012 / C-CTX-3)."
            )

    @classmethod
    def derive(cls, *, mission_id: str, mission_slug: str) -> IdentityFragment:
        """Construct the fragment, deriving ``mid8`` once from ``mission_id``."""
        return cls(
            mission_id=mission_id,
            mid8=mission_id[:8],
            mission_slug=mission_slug,
        )


@dataclass(frozen=True)
class BranchRefFragment:
    """F3 — version-control scape: the branch/ref fields for a mission.

    ``target_branch`` is the **single resolution source** (FR-012): it is
    resolved once by the builder and carried here; no surface re-derives it from
    ``meta.json`` or git independently. ``coordination_branch`` is ``None`` under
    flattened topology (C-001). ``destination_ref`` is the ONE
    :class:`CommitTarget` artifacts + status resolve to.
    """

    target_branch: str
    coordination_branch: str | None
    destination_ref: CommitTarget


@dataclass(frozen=True)
class WorkspaceFragment:
    """F2 — filesystem layout: the path fields for a mission/operation.

    ``primary_root`` is the **canonical** main-checkout root (IC-04): it is
    resolved via the single worktree-pointer parser so consumers never trust a
    lane-supplied root for coord topology (WP02 reviewer carry-forward).
    ``current_cwd`` is where the command is actually running; the two differ
    whenever the operator sits in a lane worktree.
    """

    primary_root: Path
    current_cwd: Path
    coord_worktree: Path | None
    execution_workspace: Path | None
    allowed_command_cwd: Path


@dataclass(frozen=True)
class StatusSurfaceFragment:
    """F5 (read locus) — where status events are read from / written to.

    Resolved by WP02's :func:`resolve_status_surface` (IC-01) and **carried** on
    the context — consumers (esp. ``status_transition._identity_for_request``)
    must NOT re-derive it (FR-003/FR-008/#1737). Under flattened topology
    ``status_read_dir == status_write_dir``.
    """

    status_read_dir: Path
    status_write_dir: Path


@dataclass(frozen=True)
class ArtifactPlacementFragment:
    """Where planning artifacts (spec/plan/tasks/analysis) commit (IC-05).

    ``placement_ref`` is the same :class:`CommitTarget` that status events
    resolve to (C-PLACE-1): one artifact-placement ref, no independent
    primary/coord logic.
    """

    placement_ref: CommitTarget


@dataclass(frozen=True)
class PromptSourceFragment:
    """Where implement/review prompt files are resolved (FR-012)."""

    prompt_source_dir: Path


@dataclass
class ExecutionContext:
    """Fully-resolved context for a single action — a doc-09 op-composite.

    The canonical surface is expressed over **this object**, never over loose
    path fragments: consumers receive a resolved context and never reconstruct
    the mission-spec directory from ``main_repo_root`` + the specs dir name +
    ``mission_slug`` themselves (FR-009).

    The flat fields below are the historical substrate (NFR-001 / C-004): they
    are preserved so every existing consumer continues to read the same
    attributes while the Strangler conversion proceeds. The doc-09 **fragments**
    (``identity`` / ``branch_ref`` / ``workspace`` / ``status_surface`` /
    ``artifact_placement`` / ``prompt_source``) are *attached* by the builder
    (:func:`mission_runtime.resolution.resolve_action_context`); each operation
    assembles only the fragments it needs (op-composite). A fragment is ``None``
    only when the operation does not consume it.
    """

    action: str
    mission_slug: str
    feature_dir: str
    target_branch: str
    detection_method: str
    wp_id: str | None = None
    wp_file: str | None = None
    lane: str | None = None
    lane_id: str | None = None
    branch_name: str | None = None
    execution_mode: str | None = None
    resolution_kind: str | None = None
    dependencies: list[str] = field(default_factory=list)
    resolved_base: str | None = None
    auto_merge: bool = False
    workspace_path: str | None = None
    commands: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    # doc-09 fragments (op-composite). Attached by the builder; ``None`` when the
    # operation does not consume the fragment. Excluded from ``to_dict`` so the
    # historical serialized shape (NFR-001) is byte-for-byte preserved.
    identity: IdentityFragment | None = field(default=None)
    branch_ref: BranchRefFragment | None = field(default=None)
    workspace: WorkspaceFragment | None = field(default=None)
    status_surface: StatusSurfaceFragment | None = field(default=None)
    artifact_placement: ArtifactPlacementFragment | None = field(default=None)
    prompt_source: PromptSourceFragment | None = field(default=None)

    _FRAGMENT_FIELDS: ClassVar[tuple[str, ...]] = (
        "identity",
        "branch_ref",
        "workspace",
        "status_surface",
        "artifact_placement",
        "prompt_source",
    )

    def to_dict(self) -> dict[str, Any]:
        """Return the historical flat-substrate mapping.

        The doc-09 fragments are intentionally excluded so the serialized shape
        is identical to the pre-fragment context (NFR-001) — fragments are an
        in-process composition concern, not a wire-format change. ``asdict`` is
        retained (rather than a shallow ``getattr`` copy) so the deep-copy
        semantics of the historical implementation are preserved for the
        substrate collections (``dependencies`` / ``commands`` / ``warnings``).
        """
        data = asdict(self)
        for fragment_field in self._FRAGMENT_FIELDS:
            data.pop(fragment_field, None)
        return data


# Transitional alias: the historical name used by ``core/execution_context`` and
# its consumers. Kept so the Stage-C shim re-exports a single relocated type
# rather than introducing a parallel implementation (NFR-002).
ActionContext = ExecutionContext


__all__ = [
    "ActionContext",
    "ArtifactPlacementFragment",
    "BranchRefFragment",
    "CommitTarget",
    "CommitTargetKind",
    "ExecutionContext",
    "ExecutionMode",
    "IdentityFragment",
    "PromptSourceFragment",
    "StatusSurfaceFragment",
    "WorkspaceFragment",
]
