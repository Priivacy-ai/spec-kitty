"""Narrow I/O ports for ``runtime.next.runtime_bridge`` (IC-04, #2531 WP05).

**Sole home of the narrow, near-mechanical I/O ports** IC-04 identifies: the
``feature-runs.json`` tracked-mission-to-run index (``load_feature_runs`` /
``save_feature_runs``), mission-runtime template/pack discovery, run
lifecycle (start / lookup), and the OperationalContext (OC) builder cluster.
Also hosts the two new port-shaped additions this WP introduces:

- ``gather_artifact_presence`` (T018, FR-009) — the fact-gathering counterpart
  of the guard inversion WP06 completes. It reads the SAME filesystem /
  status / bulk-edit / requirement-mapping facts ``_check_cli_guards``
  (still defined on ``runtime_bridge``, unmoved by this WP) /
  ``_check_composed_action_guard`` (moved to ``runtime_bridge_composition``
  by #2531 WP08; the residual keeps a thin compat delegate under the same
  name) read today, packaged as an
  :class:`ArtifactPresenceSnapshot`, so a future pure ``evaluate_guards``
  (WP06) can decide pass/fail without doing I/O itself. This function
  GATHERS ONLY — it makes no pass/fail decisions, and nothing in the current
  production call graph invokes it yet (wiring it in is WP06's job).
- ``resolve_commit_target`` (T019) — the ONE pure decision that was
  interleaved inside ``_wrap_with_decision_git_log`` (mid8 derivation +
  fail-closed validation + ``CommitTarget``/worktree_root-candidate
  selection). ``_wrap_with_decision_git_log`` itself is KEEP-IN-PLACE in the
  residual (contracts/compat-surface.md) — only its pure selection moved
  out; see that function's docstring for why the remaining ``.exists()``
  check stays a residual I/O concern.

``runtime_bridge.py`` keeps a **native thin compat delegate** — a real
``def``/``class`` statement, never a plain ``import`` alias — under every one
of the moved symbols the WP02 compat guard binds. This is mandatory, not
stylistic: ``tests/runtime/test_bridge_compat_surface.py::
test_guard_b_identity_reexport_for_relocated_symbols`` (a FROZEN gate file)
asserts that the set of compat symbols whose ``__module__`` differs from
``runtime_bridge`` equals a **hardcoded 3-element baseline** (the
pre-existing ``runtime.next.decision``-origin symbols). A plain re-export of
any OTHER compat-tracked symbol would flip that assertion and fail
deterministically — the exact mechanism WP04's ``runtime_bridge_retrospective``
docstring documents for its own 9 symbols. ``_feature_runs_path`` /
``save_feature_runs`` and the handful of names nothing patches (see each
function's docstring below) are untracked and therefore fine as plain
internal helpers with no residual shim at all.

**The intra-seam live-lookup risk (research.md §Compat / WP03-WP04
precedent).** Several of the moved, compat-tracked symbols call each other
now that they live together in this module (``get_or_start_run`` ->
``_load_feature_runs`` / ``_build_run_ref`` / ``_mission_key_for_run_ref`` /
``_runtime_template_key`` / ``_build_discovery_context``;
``_runtime_template_key`` -> ``_build_discovery_context`` /
``_resolve_runtime_template_in_root``; ``_start_ephemeral_query_run`` ->
``_runtime_template_key`` / ``_build_discovery_context``;
``_existing_run_ref`` -> ``_load_feature_runs`` / ``_build_run_ref``;
``build_operational_context_for_claim`` -> ``_resolve_run_dir_for_mission`` /
``_resolve_tech_stack_for_profile``; ``_build_operational_context_for_decision``
-> ``_resolve_tech_stack_for_profile``). Several ALSO call back into
compat-tracked names reachable at ``runtime_bridge.<name>`` — some still
natively defined in the residual (``_resolve_mission_ulid``,
``_resolve_runtime_feature_dir``, ``_has_raw_dependencies_field``,
``_check_requirement_mapping_ready``, ``_occurrence_gate_failures``), others
now thin compat delegates onto ``runtime_bridge_composition`` after #2531
WP08 (``_resolve_step_agent_profile``, ``_count_source_documented_events``,
``_publication_approved``) or plain re-exports from that same seam
(``_has_generated_docs``). Every one of these calls is routed through a
**local, live import of ``runtime_bridge``**
(``from runtime.next import runtime_bridge as _rb; _rb.<name>(...)``,
deferred to function scope — ``runtime_bridge`` imports this module at its
own top level, so a top-level back-import here would be circular) so a
``monkeypatch.setattr(runtime_bridge, "<name>", …)`` is still observed
exactly as before the extraction — the same false-green mitigation WP03's
``runtime_bridge_engine`` and WP04's ``runtime_bridge_retrospective`` already
apply. ``_build_discovery_context`` is the grounded high-risk case flagged by
``research.md`` §Compat (patched at ``test_query_mode_unit.py:751``, reached
only via intra-seam movers); the rule above closes it the same way it closes
every other compat-tracked intra-seam call in this module.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict, cast

import yaml
from mission_runtime import CommitTarget
from runtime.next._internal_runtime import (
    DiscoveryContext,
    MissionPolicySnapshot,
    MissionRunRef,
    NullEmitter,
    start_mission_run,
)
from runtime.next._internal_runtime.schema import MissionTemplate, load_mission_template_file
from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.core.atomic import atomic_write
from specify_cli.core.constants import MISSION_TYPE_SOFTWARE_DEV
from specify_cli.lanes.branch_naming import resolve_mid8
from specify_cli.mission_metadata import load_meta
from specify_cli.status import CanonicalStatusNotFoundError, get_wp_lane

if TYPE_CHECKING:
    from charter.activation.invocation_context import OperationalContext as OperationalContextT

# Local literal duplicates of runtime_bridge's module constants — avoids a
# circular top-level import back into runtime_bridge for four small string
# literals (``runtime_bridge`` imports THIS module at its own top level).
# Mirrors the "small local constant, no cross-module coupling" convention
# already used by the WP03/WP04 seams for their own leaf constants.
KITTIFY_DIR = ".kittify"
MISSION_RUNTIME_YAML = "mission-runtime.yaml"
MISSION_YAML = "mission.yaml"
_FEATURE_RUNS_FILE = "feature-runs.json"
STATE_FILE = "state.json"

# WP06 (FR-010/FR-011, IC-06): named diagnostics for Walk B's previously
# swallowed template-load and sidecar-co-presence failures. A real
# ``logging.Logger`` -- not ``warnings.warn`` -- because ``warnings.warn``
# deduplicates per call site by default: a long-running process (`spec-kitty
# next` driving many mission resolutions) would see an identical malformed
# org-tier fixture warned about once, then silently lose the signal on every
# later resolution of the same broken file. ``logging.warning`` fires every
# time, matching the always-visible behavior Walk A's `DiscoveryWarning`
# channel already gives operators.
_logger = logging.getLogger(__name__)


class _FeatureRunEntry(TypedDict, total=False):
    """Shape of one ``feature-runs.json`` index entry.

    ``run_id`` / ``run_dir`` are always real strings once persisted (the
    ``Path(entry["run_dir"])`` / ``_build_run_ref(run_id=..., run_dir=...)``
    call sites below rely on that); ``mission_id`` is genuinely ``str | None``
    because :func:`_resolve_mission_ulid` (fail-closed) returns ``None`` when
    no ULID is declared yet.
    """

    run_id: str
    run_dir: str
    mission_type: str
    mission_key: str
    mission_id: str | None
    mission_slug: str


# ---------------------------------------------------------------------------
# Feature -> Run index (T017)
# ---------------------------------------------------------------------------


def _feature_runs_path(repo_root: Path) -> Path:
    """Untracked helper (no test binds this name) — repo_root -> index path."""
    return repo_root / KITTIFY_DIR / "runtime" / _FEATURE_RUNS_FILE


def load_feature_runs(path: Path) -> dict[str, _FeatureRunEntry]:
    """Textbook narrow port: read the feature->run index JSON file at ``path``.

    ``data-model.md`` §Ports names this the canonical path-based port
    signature; ``runtime_bridge._load_feature_runs`` (repo_root-keyed,
    compat-tracked) is a thin residual delegate over this + :func:`_feature_runs_path`.
    See :class:`_FeatureRunEntry` for why ``mission_id`` alone is ``str | None``.
    """
    if not path.exists():
        return {}
    try:
        loaded: dict[str, _FeatureRunEntry] = json.loads(path.read_text(encoding="utf-8"))
        return loaded
    except (json.JSONDecodeError, OSError):
        return {}


def save_feature_runs(path: Path, index: dict[str, _FeatureRunEntry]) -> None:
    """Textbook narrow port: durably persist the feature->run index JSON file.

    Untracked (no test patches ``_save_feature_runs`` on ``runtime_bridge`` —
    its sole pre-WP05 caller, ``get_or_start_run``, moved into this same
    module), so no residual compat shim is needed for this name at all.
    """
    content = json.dumps(index, indent=2, sort_keys=True)
    atomic_write(path, content, mkdir=True)


def _mission_key_for_run_ref(run_ref: MissionRunRef, default: str) -> str:
    """Read the mission key from either runtime field name."""
    mission_key = getattr(run_ref, "mission_key", None)
    if isinstance(mission_key, str) and mission_key.strip():
        return mission_key
    mission_type = getattr(run_ref, "mission_type", None)
    if isinstance(mission_type, str) and mission_type.strip():
        return mission_type
    return default


def _build_run_ref(
    *,
    run_id: str,
    run_dir: str,
    mission_type: str,
    run_ref_cls: Callable[..., MissionRunRef] = MissionRunRef,
) -> MissionRunRef:
    """Construct MissionRunRef across runtime versions.

    ``run_ref_cls`` defaults to this module's own :class:`MissionRunRef` import
    but callers (notably the ``runtime_bridge._build_run_ref`` compat delegate)
    pass their own module-level binding through explicitly. This is load-bearing:
    ``tests/next/test_runtime_bridge_unit.py::
    test_build_run_ref_falls_back_when_runtime_uses_mission_type`` monkeypatches
    ``runtime_bridge.MissionRunRef`` to a fake class and expects the delegate to
    honor that substitution rather than closing over this module's own import.

    Typed as ``Callable[..., MissionRunRef]`` rather than ``type[MissionRunRef]``
    deliberately: the ``except TypeError`` fallback below calls it with a
    ``mission_type=`` keyword that the *current* ``MissionRunRef`` field
    (``mission_key``) does not accept — that branch exists for legacy/fake
    run-ref constructors from other runtime versions (see the test above), so
    pinning the parameter to the exact present-day field shape would make
    mypy correctly reject a call this function must support duck-typed.
    """
    try:
        return run_ref_cls(
            run_id=run_id,
            run_dir=run_dir,
            mission_key=mission_type,
        )
    except TypeError:
        return run_ref_cls(
            run_id=run_id,
            run_dir=run_dir,
            mission_type=mission_type,
        )


# ---------------------------------------------------------------------------
# Template / pack discovery (T017)
# ---------------------------------------------------------------------------


def _build_discovery_context(repo_root: Path) -> DiscoveryContext:
    """Build a DiscoveryContext that finds the runtime mission template.

    Populates ``org_roots`` (FR-008, DEC-006 site 1 -- the construction site
    that feeds Walk A for both ``spec-kitty next`` and query-mode runs) via
    the lazy ``charter.drg.resolve_org_roots`` facade, mirroring the five
    existing ``specify_cli/**`` call sites and WP03's identical pattern in
    the template resolvers (DEC-004: never a direct ``doctrine.*`` import
    from ``src/runtime/next/**``). No ``try/except`` wraps the call --
    ``OrgPackSubdirEscapeError``/``OrgPackEnvVarUnsetError`` are deliberately
    raised and must propagate (DEC-005, NFR-001). With no org packs
    configured, ``resolve_org_roots`` returns ``[]`` and this is a verified
    no-op (NFR-005/SC-007). ``quiet=True``: this helper backs a resolution
    hot path (``spec-kitty next``, query-mode) that may run many times per
    invocation -- an unparseable config.yaml with no readable org intent
    must not spam a UserWarning per call (see load_pack_registry's
    docstring). A genuinely declared-but-broken org pack still raises a
    loud UserWarning regardless.
    """
    import specify_cli  # noqa: PLC0415

    # Runtime bridge uses the legacy runtime templates under specify_cli/missions.
    # The doctrine mission catalog is not behaviorally equivalent yet.
    package_root = Path(specify_cli.__file__).resolve().parent / "missions"

    from charter.drg import resolve_org_roots  # noqa: PLC0415 — lazy, mirrors existing pattern

    return DiscoveryContext(
        project_dir=repo_root,
        builtin_roots=[package_root],
        org_roots=list(resolve_org_roots(repo_root, quiet=True)),
    )


def _split_env_paths(value: str) -> list[Path]:
    if not value.strip():
        return []
    return [Path(chunk) for chunk in value.split(os.pathsep) if chunk.strip()]


def _project_config_pack_paths(repo_root: Path) -> list[Path]:
    config_file = repo_root / KITTIFY_DIR / "config.yaml"
    if not config_file.exists():
        return []
    try:
        raw = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    mission_packs = raw.get("mission_packs", [])
    if not isinstance(mission_packs, list):
        return []
    return [repo_root / pack for pack in mission_packs if isinstance(pack, str)]


def _candidate_templates_for_root(root: Path, mission_type: str) -> list[Path]:
    candidates: list[Path] = []

    if root.is_file():
        if root.name in {MISSION_RUNTIME_YAML, MISSION_YAML}:
            candidates.append(root)
    elif root.exists() and root.is_dir():
        candidates.extend(
            [
                root / mission_type / MISSION_RUNTIME_YAML,
                root / mission_type / MISSION_YAML,
                root / "missions" / mission_type / MISSION_RUNTIME_YAML,
                root / "missions" / mission_type / MISSION_YAML,
                root / MISSION_RUNTIME_YAML,
                root / MISSION_YAML,
            ]
        )

    # De-duplicate while preserving order.
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _builtin_missions_root() -> Path:
    """The package-shipped ``missions/`` directory.

    Same expression ``_build_discovery_context`` (WP04) uses for
    ``builtin_roots`` — recomputed locally rather than imported from there to
    avoid coupling to a function this WP does not own (plan.md IC-06's
    `owned_files` note: WP04 owns `_build_discovery_context`, this WP owns
    `_template_key_for_file`/`_resolve_runtime_template_in_root`). Both
    expressions must stay in sync by construction — there is exactly one
    place `specify_cli`'s package-relative missions directory is defined.
    """
    import specify_cli  # noqa: PLC0415

    return (Path(specify_cli.__file__).resolve().parent / "missions").resolve()


def _is_builtin_missions_dir(parent: Path) -> bool:
    """True when ``parent`` is a direct child of the package's ``missions/``
    directory (FR-011 Acceptance Scenario 2) — i.e. one of the four built-in
    mission directories (``plan``, ``research``, ``documentation``,
    ``software-dev``) that already legitimately ship both sidecar files.
    Structural (parent-of-parent identity against the one canonical built-in
    root), not a hardcoded name list, so it stays correct if a fifth
    built-in mission is ever added.
    """
    try:
        resolved_parent = parent.resolve()
    except OSError:
        return False
    return resolved_parent.parent == _builtin_missions_root()


def _warn_non_builtin_sidecar_pairs(candidates: list[Path], mission_type: str) -> None:
    """FR-011: name a diagnostic when a non-built-in tier ships both
    ``mission.yaml`` and ``mission-runtime.yaml`` for the same mission key.

    Built-in mission directories already legitimately ship both and MUST
    stay silent (Acceptance Scenario 2) — filtered via
    ``_is_builtin_missions_dir``. Purely observational: does not raise, and
    does not change which file the existing sidecar preference (C-005, the
    ``candidate.name == MISSION_YAML`` branch in
    ``_resolve_runtime_template_in_root`` below) resolves to. Runs once, up
    front, over the already-computed candidate list, independent of which
    candidate the main resolution loop happens to match first — the
    mission-runtime.yaml candidate is checked ahead of mission.yaml in
    ``_candidate_templates_for_root``'s ordering and resolves (and returns)
    before the loop ever reaches the mission.yaml candidate, so a
    diagnostic hook placed only inside that loop would never fire for a
    directory-shaped root.
    """
    seen_parents: set[Path] = set()
    for candidate in candidates:
        parent = candidate.parent
        if parent in seen_parents:
            continue
        mission_yaml = parent / MISSION_YAML
        mission_runtime_yaml = parent / MISSION_RUNTIME_YAML
        if not (mission_yaml.is_file() and mission_runtime_yaml.is_file()):
            continue
        seen_parents.add(parent)
        if _is_builtin_missions_dir(parent):
            continue
        _logger.warning(
            "Walk B: non-built-in tier at %s ships both %s and %s for "
            "mission %r; %s wins (existing sidecar preference unchanged).",
            parent,
            MISSION_YAML,
            MISSION_RUNTIME_YAML,
            mission_type,
            MISSION_RUNTIME_YAML,
        )


def _template_key_for_file(path: Path, *, tier: str = "unknown") -> str | None:
    """Load a mission key from ``path``, or ``None`` on any load failure.

    FR-010: a load failure is also routed into a named
    :func:`logging.Logger.warning` naming the offending path (and, when the
    caller supplies one, the resolution tier/root it was found under) so a
    malformed org-tier (or any-tier) ``mission.yaml``/``mission-runtime.yaml``
    is diagnosable instead of silently discarded. The return-value contract
    is unchanged — callers that depend on ``None`` meaning "skip this
    candidate" (``_resolve_runtime_template_in_root``) keep working exactly
    as before; only the caller-invisible logging side channel is new.
    """
    try:
        template = load_mission_template_file(path)
        return template.mission.key
    except Exception as exc:
        _logger.warning(
            "Walk B: failed to load mission template at %s (tier=%s): %s",
            path,
            tier,
            exc,
        )
        return None


def _resolve_runtime_template_in_root(root: Path, mission_type: str) -> Path | None:
    candidates = _candidate_templates_for_root(root, mission_type)
    _warn_non_builtin_sidecar_pairs(candidates, mission_type)

    for candidate in candidates:
        if not candidate.exists() or not candidate.is_file():
            continue

        paths_to_try = [candidate]
        # Prefer mission-runtime.yaml sidecar when candidate is mission.yaml.
        if candidate.name == MISSION_YAML:
            runtime_sidecar = candidate.with_name(MISSION_RUNTIME_YAML)
            if runtime_sidecar.exists() and runtime_sidecar.is_file():
                paths_to_try = [runtime_sidecar, candidate]

        for path in paths_to_try:
            template_key = _template_key_for_file(path, tier=str(root))
            if template_key == mission_type:
                return path.resolve()

    return None


def _runtime_template_key(mission_type: str, repo_root: Path) -> str:
    """Resolve the runtime template path for a mission key.

    Uses deterministic runtime discovery precedence for mission-runtime YAML:
    explicit -> env -> project override -> project legacy -> org (FR-009) ->
    project config -> user global -> built-in.

    For the built-in ``software-dev`` mission, the packaged runtime template is
    canonical after this composition rewrite. Stale user-global mission packs
    from earlier installs must not reintroduce the legacy tasks_* DAG, while
    explicit, env, and project-scoped overrides remain honored.
    """
    from runtime.next import runtime_bridge as _rb  # noqa: PLC0415

    context = _rb._build_discovery_context(repo_root)
    env_value = os.environ.get(context.env_var_name, "")
    # Org tier (FR-009) sits immediately after the project-legacy entry
    # (`.kittify/missions`) and before the project-config/global/builtin
    # tiers below -- the same relative position Walk A's `_build_tiers`
    # gives the org tier. Reuses `context.org_roots`, already populated by
    # `_build_discovery_context` above, rather than calling
    # `resolve_org_roots` a second time.
    project_tiers: list[list[Path]] = [
        list(context.explicit_paths),
        _split_env_paths(env_value),
        [repo_root / KITTIFY_DIR / "overrides" / "missions"],
        [repo_root / KITTIFY_DIR / "missions"],
        list(context.org_roots),
        _project_config_pack_paths(repo_root),
    ]
    global_tier = [context.user_home / KITTIFY_DIR / "missions"]
    builtin_tier = list(context.builtin_roots)
    tiers = (
        project_tiers + [builtin_tier, global_tier]
        if mission_type == MISSION_TYPE_SOFTWARE_DEV
        else project_tiers + [global_tier, builtin_tier]
    )

    for roots in tiers:
        for root in roots:
            resolved = _rb._resolve_runtime_template_in_root(root, mission_type)
            if resolved is not None:
                return str(resolved)

    # Fallback: let runtime resolve mission key via mission.yaml discovery.
    return mission_type


def _workflow_runtime_template(
    mission_slug: str,
    mission_type: str,
    repo_root: Path,
    template_key: str,
) -> tuple[MissionTemplate | None, str | None]:
    """Compose a runtime template when mission meta selects a workflow.

    Untracked (no test binds this name on ``runtime_bridge``).
    """
    from runtime.next import runtime_bridge as _rb  # noqa: PLC0415

    del mission_type
    mission_dir = _rb._resolve_runtime_feature_dir(repo_root, mission_slug)
    # load_meta (post-#2091 canonical contract): allow_missing=True absorbs a
    # missing meta.json to None; malformed content still raises (on_malformed
    # defaults to "raise"), matching the prior unguarded json.loads.
    meta = load_meta(mission_dir)
    if meta is None:
        return None, None

    workflow_id = meta.get("workflow_id")
    if workflow_id is None:
        return None, None

    from runtime.next._internal_runtime.discovery import load_mission_template
    from runtime.next._internal_runtime.planner import compose_template_with_workflow
    from runtime.next._internal_runtime.workflow_registry import get_workflow

    context = _rb._build_discovery_context(repo_root)
    base_template = load_mission_template(template_key, context=context)
    workflow = get_workflow(str(workflow_id), project_root=repo_root)
    template = compose_template_with_workflow(base_template, workflow)
    template_path = f"{template_key}#workflow:{workflow.workflow_id}"
    return template, template_path


# ---------------------------------------------------------------------------
# Run lifecycle (T017: start / lookup)
# ---------------------------------------------------------------------------


def _existing_run_ref(
    mission_slug: str,
    repo_root: Path,
    mission_type: str,
) -> MissionRunRef | None:
    """Return an existing run without creating a new one."""
    from runtime.next import runtime_bridge as _rb  # noqa: PLC0415

    index = _rb._load_feature_runs(repo_root)

    if mission_slug not in index:
        return None

    entry = index[mission_slug]
    run_dir = Path(entry["run_dir"])
    if not (run_dir / STATE_FILE).exists():
        return None

    stored_mission_type = entry.get("mission_type") or entry.get("mission_key") or mission_type
    return _rb._build_run_ref(
        run_id=entry["run_id"],
        run_dir=entry["run_dir"],
        mission_type=stored_mission_type,
    )


def _start_ephemeral_query_run(
    mission_slug: str,
    mission_type: str,
    repo_root: Path,
) -> tuple[MissionRunRef, Path]:
    """Start a fresh query-only run outside the repository.

    This keeps fresh query mode non-mutating for the project working tree and
    `.kittify/runtime/feature-runs.json` while still using the runtime's own
    snapshot/bootstrap behavior. The temp run store is cleaned up if any
    bootstrap step raises so we never leak directories on failure paths.
    """
    from runtime.next import runtime_bridge as _rb  # noqa: PLC0415

    run_store = Path(tempfile.mkdtemp(prefix="spec-kitty-query-run-"))
    try:
        template_key = _rb._runtime_template_key(mission_type, repo_root)
        template_override, template_path_override = _workflow_runtime_template(
            mission_slug, mission_type, repo_root, template_key
        )
        context = _rb._build_discovery_context(repo_root)

        run_ref = start_mission_run(
            template_key=template_key,
            inputs={"mission_slug": mission_slug},
            policy_snapshot=MissionPolicySnapshot(),
            context=context,
            run_store=run_store,
            emitter=NullEmitter(),
            template_override=template_override,
            template_path_override=template_path_override,
        )
    except Exception:
        shutil.rmtree(run_store, ignore_errors=True)
        raise
    return run_ref, run_store


def get_or_start_run(
    mission_slug: str,
    repo_root: Path,
    mission_type: str,
    *,
    emitter: Any | None = None,
) -> MissionRunRef:
    """Load existing run or start a new one.

    Run mapping stored in .kittify/runtime/feature-runs.json:
    { "042-test-feature": { "run_id": "abc", "run_dir": "..." } }
    """
    from runtime.next import runtime_bridge as _rb  # noqa: PLC0415

    index = _rb._load_feature_runs(repo_root)

    if mission_slug in index:
        entry = index[mission_slug]
        run_dir = Path(entry["run_dir"])
        if (run_dir / STATE_FILE).exists():
            stored_mission_type = entry.get("mission_type") or entry.get("mission_key") or mission_type
            return _rb._build_run_ref(
                run_id=entry["run_id"],
                run_dir=entry["run_dir"],
                mission_type=stored_mission_type,
            )

    # Start a new run
    run_store = repo_root / KITTIFY_DIR / "runtime" / "runs"
    template_key = _rb._runtime_template_key(mission_type, repo_root)
    template_override, template_path_override = _workflow_runtime_template(
        mission_slug, mission_type, repo_root, template_key
    )
    context = _rb._build_discovery_context(repo_root)

    run_ref = start_mission_run(
        template_key=template_key,
        inputs={"mission_slug": mission_slug},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=run_store,
        emitter=emitter or NullEmitter(),
        template_override=template_override,
        template_path_override=template_path_override,
    )

    # Persist to index
    resolved_mission_type = _rb._mission_key_for_run_ref(run_ref, mission_type)
    resolved_mission_id = _rb._resolve_mission_ulid(mission_slug, repo_root)
    index[mission_slug] = {
        "run_id": run_ref.run_id,
        "run_dir": run_ref.run_dir,
        "mission_type": resolved_mission_type,
        "mission_key": resolved_mission_type,
        "mission_id": resolved_mission_id,
        "mission_slug": mission_slug,
    }
    save_feature_runs(_feature_runs_path(repo_root), index)

    return run_ref


# ---------------------------------------------------------------------------
# OperationalContext wiring (T017; FR-017, NFR-004)
# ---------------------------------------------------------------------------


def _resolve_run_dir_for_mission(
    repo_root: Path, mission_slug: str
) -> Path | None:
    """Return the persisted run directory for ``mission_slug``, read-only.

    Looks the run up in the durable ``feature-runs.json`` index without
    starting a new run (unlike :func:`get_or_start_run`). Returns ``None`` when
    no run has been recorded yet. This keeps OC construction at the claim sites
    free of any run-start side effect (NFR-004).
    """
    from runtime.next import runtime_bridge as _rb  # noqa: PLC0415

    index = _rb._load_feature_runs(repo_root)
    entry = index.get(mission_slug)
    if not entry:
        return None
    run_dir_raw = entry.get("run_dir")
    if not run_dir_raw:
        return None
    return Path(run_dir_raw)


def _resolve_tech_stack_for_profile(
    repo_root: Path, profile_id: str | None
) -> frozenset[str]:
    """Best-effort resolution of the in-scope tech stack for ``profile_id``.

    The tech stack is sourced from the resolved agent profile's
    ``applies_to_languages`` / specialization-context languages (charter/meta
    per data-model §7). This is best-effort: any resolution failure yields an
    empty frozenset rather than raising, so populating an
    :class:`~charter.activation.invocation_context.OperationalContext` never blocks a
    claim or decision. The lookup is read-only and creates no worktree or
    status side effects (NFR-004).
    """
    if not profile_id:
        return frozenset()
    try:
        # WP02 (charter-sole-door-bypass-closure-01KZ3WAA, FR-001): route
        # through the charter-mediated factory's lineage/mutation accessor
        # rather than constructing ``AgentProfileRepository`` directly.
        # ``resolve_profile()`` (lineage composition via ``specializes_from``)
        # is not available on the gated ``agent_profiles`` dict — a dict has
        # no such method — so this call site needs the raw accessor, not the
        # filtered property (contracts/charter-doctrine-service-contract.md
        # "Lineage/mutation accessor semantics").
        from charter.activation.doctrine_service_builder import (  # noqa: PLC0415
            build_activation_aware_doctrine_service,
        )

        service = build_activation_aware_doctrine_service(repo_root)
        repo = service.agent_profile_repository
        profile = repo.resolve_profile(profile_id)
    except Exception:
        return frozenset()
    if profile is None:
        return frozenset()
    languages: list[str] = list(getattr(profile, "applies_to_languages", []) or [])
    spec_ctx = getattr(profile, "specialization_context", None)
    if spec_ctx is not None:
        languages.extend(getattr(spec_ctx, "languages", []) or [])
    return frozenset(lang for lang in languages if lang)


def build_operational_context_for_claim(
    *,
    repo_root: Path,
    feature_dir: Path,  # noqa: ARG001 — accepted for call-site symmetry; OC fields derive from run state/profile
    mission_slug: str,
    wp_id: str,
    actor: str | None,
    active_model: str | None,
    active_role: str | None,
    current_activity: str = "implement",
    active_profile: str | None = None,
) -> OperationalContextT:
    """Build a populated ``OperationalContext`` for a WP-claim call site.

    Shared by the two claim entry points (``implement.py`` and
    ``agent/workflow.py``) so OC-construction logic is not forked between them
    (T062/T063). Resolves the active profile from the frozen mission template
    step (via :func:`_resolve_step_agent_profile`) when the caller does not
    supply one explicitly, and derives ``tech_stack`` from that profile.

    This builder is read-only: it consults durable run state and profile
    definitions but performs no worktree allocation and emits no status event,
    so callers may invoke it before or after their own precondition checks
    without violating NFR-004.

    Args:
        repo_root: Repository root.
        feature_dir: Feature directory for the mission.
        mission_slug: Mission slug (used to locate the run directory).
        wp_id: Work package being claimed (current activity scope).
        actor: Claim actor — becomes ``active_role`` when ``active_role`` is
            not supplied.
        active_model: The ``--agent`` value for the claim.
        active_role: Explicit active role; falls back to ``actor``.
        current_activity: Activity label (defaults to ``"implement"``).
        active_profile: Explicit profile id; resolved from the template step
            when ``None``.

    Returns:
        A populated :class:`~charter.activation.invocation_context.OperationalContext`.
    """
    from charter.activation.invocation_context import build_operational_context  # noqa: PLC0415
    from runtime.next import runtime_bridge as _rb  # noqa: PLC0415

    resolved_profile = active_profile
    if resolved_profile is None:
        try:
            run_dir = _rb._resolve_run_dir_for_mission(repo_root, mission_slug)
            if run_dir is not None:
                resolved_profile = _rb._resolve_step_agent_profile(
                    run_dir, current_activity
                )
        except Exception:
            resolved_profile = None

    return build_operational_context(
        active_model=active_model,
        active_profile=resolved_profile,
        active_role=active_role or actor,
        current_activity=current_activity or wp_id,
        tech_stack=_rb._resolve_tech_stack_for_profile(repo_root, resolved_profile),
    )


def _build_operational_context_for_decision(
    *,
    agent: str,
    run_ref: MissionRunRef,
    feature_dir: Path,  # noqa: ARG001 — part of the R-011-E helper contract; OC fields derive from run_ref/step_id
    repo_root: Path,
    step_id: str | None,
    mission_state: str | None = None,
) -> OperationalContextT:
    """Build a populated ``OperationalContext`` for the ``next`` decision boundary.

    Extracted helper (T064) so ``decide_next_via_runtime`` — already flagged
    ``# noqa: C901`` — does not grow in complexity. Resolves the active profile
    from the issued step via :func:`_resolve_step_agent_profile`, uses
    ``step_id`` / ``mission_state`` as the current activity, and derives the
    tech stack from the resolved profile. Read-only; no side effects (NFR-004).
    """
    from charter.activation.invocation_context import build_operational_context  # noqa: PLC0415
    from runtime.next import runtime_bridge as _rb  # noqa: PLC0415

    activity = step_id or mission_state
    resolved_profile: str | None = None
    if step_id is not None:
        try:
            resolved_profile = _rb._resolve_step_agent_profile(
                Path(run_ref.run_dir), step_id
            )
        except Exception:
            resolved_profile = None

    return build_operational_context(
        active_model=agent,
        active_profile=resolved_profile,
        active_role=agent,
        current_activity=activity,
        tech_stack=_rb._resolve_tech_stack_for_profile(repo_root, resolved_profile),
    )


# ---------------------------------------------------------------------------
# T018 — gather_artifact_presence fact-port (FR-009)
# ---------------------------------------------------------------------------


def _presence_filenames_for(
    mission_family: str, repo_root: Path | None = None
) -> frozenset[str]:
    """Resolve the per-type presence filename set for *mission_family* (FR-011, #3597).

    Sources filenames from the single per-type ``expected-artifacts.yaml``
    ``path_pattern`` authority (WP04's seam, #3599) -- the same authority
    :func:`specify_cli.runtime.resolver.required_artifacts_for` /
    :func:`~specify_cli.runtime.resolver.resolve_configured_artifact_name`
    draw from -- instead of the previously-closed 10-tuple literal this
    function replaces (``_PRESENCE_FILE_TAGS``).

    Family-scoped (every step's ``required_always`` + ``required_by_step``
    + ``optional_always`` path_patterns, unioned via
    :func:`charter.offering.missions.project_artifact_name_set`),
    deliberately NOT filtered to the caller's ``step_id`` (byte-compat,
    NFR-003): the guard vocabulary calling this port is not uniform across
    mission families or dispatch paths. Software-dev's own manifest keys
    (mission.yaml state ids: specify/plan/tasks_outline/tasks_packages/
    tasks_finalize/...) match its CLI-native guard's ``step_id`` 1:1, but
    neither the *composed* ``"tasks"`` action (no such manifest key --
    disambiguated only by ``legacy_step_id``) nor the ``plan`` mission
    family's composed action names (``specify``/``plan``, vs. its own
    manifest's ``goals``/``draft`` step keys) resolve correctly if this
    port filtered to one caller-supplied ``step_id``. Scanning the whole
    family set instead -- exactly what the old global 10-tuple effectively
    did for every family it was blindly reused across -- avoids silently
    turning either mismatch into a spurious block. (A step-scoped design
    was tried during this WP's implementation and reverted after it red
    ``tests/runtime/test_bridge_parity.py::test_coverage_floor_is_met`` by
    incorrectly blocking the software-dev composed ``tasks`` guard and the
    ``plan``-family ``specify``/``plan`` guards even when their artifacts
    were present.)

    A custom mission family gates on its own filenames (AC-10) as long as
    it ships an ``expected-artifacts.yaml`` -- present -> passes, absent ->
    blocks -- regardless of which step is being gathered for; a family
    with no manifest resolves to an empty set. The distinct guard-table
    *dispatch* fail-closed concern for a genuinely unregistered family is a
    separate, retained mechanism: ``runtime_bridge_cores.evaluate_guards_strict``
    still raises ``UnregisteredMissionFamilyError`` when ``_GUARD_TABLES``
    has no entry for the family (per the ADR).

    Every one of the 10 built-in filenames the old tuple hardcoded still
    resolves identically (NFR-003) -- see
    ``tests/specify_cli/runtime/test_configured_artifact_name.py`` for the
    per-(family, artifact_key) byte-compat characterization.

    FR-008 (WP02): when *repo_root* is given and resolves to 1+ existing
    configured org roots, an org-pack
    ``<org_root>/missions/<mission_family>/expected-artifacts.yaml`` takes
    precedence over the built-in file, whole-file -- never field-merged with
    it (same last-existing-match-wins / whole-file-replacement precedence
    :func:`charter.org_expected_artifacts.resolve_org_expected_artifacts`
    itself implements). *repo_root* defaults to ``None`` (today's exact
    behavior: no org lookup, built-in tree only).

    Raises:
        ManifestSchemaError: A *found*, syntactically-valid manifest that
            fails schema validation (``extra="forbid"``) raises this instead
            of a bare ``pydantic.ValidationError`` (FR-010, #3704 pr-merged-001
            fix round) -- for BOTH tiers, mirroring
            :func:`specify_cli.runtime.resolver._load_expected_artifact_manifest`'s
            own wrap. Carries a branch-specific ``origin``: the built-in
            branch's real ``ConfigResult.origin``, or a synthesized org-tier
            label (no single source file path is available there).
    """
    from charter.offering.missions import (  # noqa: PLC0415
        ExpectedArtifactManifest,
        MissionTemplateRepository,
        project_artifact_name_set,
    )
    from pydantic import ValidationError  # noqa: PLC0415

    from specify_cli.dossier.manifest import ManifestSchemaError  # noqa: PLC0415

    org_parsed = _resolve_org_manifest_mapping(mission_family, repo_root)
    if org_parsed is not None:
        try:
            manifest = ExpectedArtifactManifest.model_validate(org_parsed)
        except ValidationError as exc:
            # Org-tier branch: no `ConfigResult` of type `config` is in
            # scope here, so `.origin` cannot be read off one (that would
            # raise `AttributeError`, not `ManifestSchemaError`). Synthesize
            # a descriptive origin naming the org tier + mission family,
            # mirroring resolver.py::_load_expected_artifact_manifest's own
            # org-tier `ManifestSchemaError` construction.
            origin = (
                f"org-tier expected-artifacts.yaml for mission type {mission_family!r} "
                "(no single source file path available)"
            )
            raise ManifestSchemaError(mission_family, origin) from exc
    else:
        config = MissionTemplateRepository.default().get_expected_artifacts(mission_family)
        if config is None:
            return frozenset()
        try:
            manifest = ExpectedArtifactManifest.model_validate(config.parsed)
        except ValidationError as exc:
            # Built-in branch: `config.origin` is a real, reachable
            # attribute, mirroring resolver.py's built-in-branch handling.
            raise ManifestSchemaError(mission_family, config.origin) from exc
    name_set = project_artifact_name_set(manifest) or {}
    return frozenset(name_set.values())


def _resolve_org_manifest_mapping(
    mission_family: str, repo_root: Path | None
) -> Mapping[str, Any] | None:
    """Return the resolved org-tier ``expected-artifacts.yaml`` mapping for
    *mission_family*, or ``None`` when *repo_root* is ``None``, resolves no
    existing org roots, or no org root has a matching file.

    Shared by :func:`_presence_filenames_for` and
    :func:`_expected_artifacts_manifest_resolves` so both consult the exact
    same org-tier precedence (FR-008) rather than each re-deriving it.
    """
    if repo_root is None:
        return None
    from charter.drg import resolve_existing_org_roots  # noqa: PLC0415
    from charter.activation.org_expected_artifacts import (  # noqa: PLC0415
        resolve_org_expected_artifacts,
    )

    org_roots = resolve_existing_org_roots(repo_root)
    if not org_roots:
        return None
    # `charter.*` is `follow_imports = "skip"` in [tool.mypy] (pyproject.toml)
    # so unrelated pre-existing strict debt elsewhere in the charter package
    # isn't walked by every importer's mypy run; that also erases
    # `resolve_org_expected_artifacts`'s real `Mapping[str, Any] | None`
    # return type to plain `Any` at this call boundary. The cast documents
    # the type this function actually returns at runtime.
    return cast("Mapping[str, Any] | None", resolve_org_expected_artifacts(org_roots, mission_family))


def _expected_artifacts_manifest_resolves(mission_family: str, repo_root: Path | None) -> bool:
    """True when an expected-artifacts manifest resolves for *mission_family*
    at either tier -- org first (FR-008), built-in fallback.

    The single per-:func:`gather_artifact_presence`-call source for
    ``ArtifactPresenceSnapshot.blocking_artifact_names``'s ``None`` vs. real
    ``frozenset`` distinction (SPEC-FRESH-001) -- reuses the exact same
    tier-checking logic :func:`_presence_filenames_for` runs internally,
    factored out via :func:`_resolve_org_manifest_mapping` so the two
    functions share one source of truth.
    """
    if _resolve_org_manifest_mapping(mission_family, repo_root) is not None:
        return True

    from charter.offering.missions import MissionTemplateRepository  # noqa: PLC0415

    return MissionTemplateRepository.default().get_expected_artifacts(mission_family) is not None


@dataclass(frozen=True)
class ArtifactPresenceSnapshot:
    """FR-009 guard fact-port output (data-model.md §ArtifactPresenceSnapshot).

    A plain, I/O-free value object carrying the filesystem/status facts the
    CLI-level guards (``_check_cli_guards``, still defined on
    ``runtime_bridge``; ``_check_composed_action_guard``, moved to
    ``runtime_bridge_composition`` by #2531 WP08 behind a thin residual
    compat delegate under the same name) read today, gathered
    ONCE by :func:`gather_artifact_presence` so the pure
    ``runtime_bridge_cores.evaluate_guards(snapshot)`` (WP06) can decide
    pass/fail without doing I/O itself.

    ``wp_advance_ready`` (WP06, T022) is deliberately NOT populated by
    :func:`gather_artifact_presence` — it defaults to ``None`` here and is
    filled in by the residual guard delegates in ``runtime_bridge.py`` for
    ``step_id``/``action`` in ``{"implement", "review"}`` via
    ``dataclasses.replace(snapshot, wp_advance_ready=...)``, threading the
    pre-existing (unmoved) ``_should_advance_wp_step`` I/O read through so
    both its own WP02 compat reach AND this port's already-green
    ``tests/runtime/test_bridge_io.py`` (which does not stub
    ``_should_advance_wp_step``) stay intact.

    ``blocking_artifact_names`` (WP01, FR-001/FR-002/FR-006, #3704 Part 1)
    IS populated by :func:`gather_artifact_presence` — ``None`` when no
    expected-artifacts manifest is reachable for ``mission_family`` at any
    tier, or a real (possibly empty) ``frozenset`` naming the blocking
    artifacts for ``step_id`` when a manifest was resolved. Consumed by
    ``runtime_bridge_cores.evaluate_guards_strict`` for its dispatch-miss
    branch. This WP populates the field via a **minimal test-only stub**
    that only distinguishes "no manifest" from "manifest present" — WP02
    replaces the stub with real org-tier-aware resolution; the default of
    ``None`` keeps every existing construction call site (including test
    fixtures) compiling unchanged.
    """

    present_artifacts: frozenset[str]
    status_facts: Mapping[str, Any]
    mission_family: str
    step_id: str
    legacy_step_id: str | None = None
    wp_advance_ready: bool | None = None
    blocking_artifact_names: frozenset[str] | None = None


def gather_artifact_presence(
    feature_dir: Path,
    *,
    mission_family: str,
    step_id: str,
    legacy_step_id: str | None = None,
    repo_root: Path | None = None,
) -> ArtifactPresenceSnapshot:
    """Gather (never decide) the facts the two CLI-level guards read today.

    Mirrors the exact set of filesystem/status/bulk-edit/requirement-mapping
    reads ``_check_cli_guards`` / ``_check_composed_action_guard`` perform
    across all four mission families (software-dev / research /
    documentation / plan), so a downstream pure ``evaluate_guards(snapshot)`` can
    reproduce identical ``guard_failures`` content and ordering (SC-007)
    without touching disk again. The guard-helper calls below
    (``_check_requirement_mapping_ready``, ``_occurrence_gate_failures``,
    ``_has_raw_dependencies_field``) stay natively defined on
    ``runtime_bridge`` (unmoved by this WP); ``_count_source_documented_events``
    / ``_publication_approved`` are now thin compat delegates onto
    ``runtime_bridge_composition`` and ``_has_generated_docs`` is a plain
    re-export from that same seam (#2531 WP08) — all still reachable at
    ``runtime_bridge.<name>``. Several are compat-tracked, so every one is
    invoked through a live lookup — never a bare/cached import — exactly
    like every other cross-seam call in this module.

    Presence is checked with ``Path.is_file()`` uniformly — the stricter of
    the two predicates the guards mix today (research/documentation branches
    already use ``is_file()``; software-dev's ``exists()`` checks are
    equivalent for every artifact name here since none is expected to collide
    with a same-named directory in practice). Flagged for WP06 to
    cross-check against each guard branch's exact predicate before this
    snapshot replaces the guards' own reads.

    ``repo_root`` (WP02, FR-008) is forwarded to :func:`_presence_filenames_for`
    and :func:`specify_cli.runtime.resolver.required_artifacts_for` for
    org-tier manifest resolution; defaults to ``None`` (built-in tree only,
    today's exact behavior).
    """
    from runtime.next import runtime_bridge as _rb  # noqa: PLC0415
    from runtime.next import runtime_bridge_composition as _composition  # noqa: PLC0415 — deferred; composition imports this module at top level

    present: set[str] = set()
    for tag in _presence_filenames_for(mission_family, repo_root=repo_root):
        if (feature_dir / tag).is_file():
            present.add(tag)

    tasks_dir = feature_dir / "tasks"
    tasks_dir_is_dir = tasks_dir.is_dir()
    wp_files = sorted(tasks_dir.glob("WP*.md")) if tasks_dir_is_dir else []
    if wp_files:
        present.add("tasks_wp_files")

    # WP18 (#2561): reach _has_generated_docs directly from its owning seam now
    # that the runtime_bridge façade re-export was retired (nothing patches
    # ``runtime_bridge._has_generated_docs``).
    has_generated_docs = bool(_composition._has_generated_docs(feature_dir))
    if has_generated_docs:
        present.add("generated_docs")

    wp_lane_raw: dict[str, str] = {}
    wp_dependencies_present: dict[str, bool] = {}
    # Ordered (full file stem, has_dependencies_field) pairs, in the same
    # sorted-glob order the pre-extraction guards iterated wp_files in —
    # WP06's evaluate_guards needs the FULL stem (e.g. "WP03-foo") for its
    # break-on-first-missing failure message, which `wp_dependencies_present`
    # (keyed by the short "WP03"-style id) cannot reconstruct.
    wp_dependency_records: list[tuple[str, bool]] = []
    for wp_file in wp_files:
        wp_match = re.match(r"(WP\d+)", wp_file.stem)
        wp_id = wp_match.group(1) if wp_match else wp_file.stem
        try:
            wp_lane_raw[wp_id] = get_wp_lane(feature_dir, wp_id)
        except CanonicalStatusNotFoundError:
            # No canonical status.events.jsonl yet (e.g. WP files scaffolded
            # ahead of `finalize-tasks`/status bootstrap in a unit-test
            # fixture, or a real mission mid-scaffold). None of the CLI-level
            # guards this snapshot feeds (evaluate_guards, WP06) read
            # `wp_lane_raw` for their decision — `wp_advance_ready` (also
            # threaded through this snapshot, but computed separately by the
            # residual via the unmoved `_should_advance_wp_step`) is what
            # implement/review actually consult — so this fact is gathered
            # best-effort and a missing event log must not turn a narrow
            # tasks_packages/tasks_finalize dependency-field check into an
            # unrelated crash (regression guard:
            # tests/next/test_runtime_bridge_unit.py::TestAtomicTaskSteps,
            # tests/next/test_occurrence_gate_next_loop.py).
            wp_lane_raw[wp_id] = ""
        has_dependencies_field = bool(_rb._has_raw_dependencies_field(wp_file))
        wp_dependencies_present[wp_id] = has_dependencies_field
        wp_dependency_records.append((wp_file.stem, has_dependencies_field))

    status_facts: dict[str, Any] = {
        "tasks_dir_is_dir": tasks_dir_is_dir,
        "wp_ids": tuple(sorted(wp_lane_raw)),
        "wp_lane_raw": wp_lane_raw,
        "wp_dependencies_present": wp_dependencies_present,
        "wp_dependency_records": tuple(wp_dependency_records),
        "requirement_mapping_failures": tuple(_rb._check_requirement_mapping_ready(feature_dir)),
        "bare_prose_requirement_failures": tuple(_rb._check_bare_prose_requirements_ready(feature_dir)),
        "occurrence_gate_failures": tuple(_rb._occurrence_gate_failures(feature_dir)),
        "source_documented_count": _rb._count_source_documented_events(feature_dir),
        "publication_approved": bool(_rb._publication_approved(feature_dir)),
        "has_generated_docs": has_generated_docs,
    }

    blocking_artifact_names: frozenset[str] | None = None
    if _expected_artifacts_manifest_resolves(mission_family, repo_root):
        from specify_cli.runtime.resolver import required_artifacts_for  # noqa: PLC0415

        blocking_artifact_names = frozenset(
            required_artifacts_for(step_id, mission_family, repo_root=repo_root)
        )

    return ArtifactPresenceSnapshot(
        present_artifacts=frozenset(present),
        status_facts=status_facts,
        mission_family=mission_family,
        step_id=step_id,
        legacy_step_id=legacy_step_id,
        blocking_artifact_names=blocking_artifact_names,
    )


# ---------------------------------------------------------------------------
# T019 — resolve_commit_target: the pure decision lifted out of
# _wrap_with_decision_git_log (data-model.md §Ports)
# ---------------------------------------------------------------------------


def resolve_commit_target(
    *,
    coord_routing_topology: bool,
    mission_slug: str,
    mission_id: str | None,
    coordination_branch: str,
    repo_root: Path,
) -> tuple[str, Path, CommitTarget]:
    """Pure decision lifted out of ``_wrap_with_decision_git_log`` (T019, #2531 WP05).

    Derives ``mid8`` (:func:`specify_cli.lanes.branch_naming.resolve_mid8`, a
    pure string derivation), enforces the fail-closed mid8-required invariant
    for a coordination-routing mission, and computes the ``CommitTarget`` plus
    the worktree_root CANDIDATE the caller should land decisions on.

    No disk I/O: ``CoordinationWorkspace.worktree_path`` is documented as
    "Pure; no filesystem touch" — it only composes the path string. The ONE
    still-I/O-bearing decision — whether ``CoordinationWorkspace.resolve()``'s
    verify-or-create side effects must run before trusting the candidate — is
    left to the caller (``_wrap_with_decision_git_log``, KEEP-IN-PLACE in the
    residual), which performs the ``.exists()`` stat itself: on success,
    ``CoordinationWorkspace.resolve()`` always returns the identical path this
    function already computed (its ``path = cls.worktree_path(...)`` is the
    first line of every one of its branches), so deciding the FINAL
    ``worktree_root`` value here is safe — the caller's ``.exists()``-gated
    call only decides whether verification/creation side effects must happen
    first, never a different resulting value on success.

    Returns ``(mid8, worktree_root_candidate, decision_target)``. Raises
    :class:`runtime_bridge.DecisionGitLogUnavailable` (deferred import — the
    residual defines it; a top-level import here would be circular) when
    ``coord_routing_topology`` is True and no ``mid8`` can be resolved,
    exactly as the pre-extraction inline code did (still caught by the
    enclosing ``try/except`` in ``_wrap_with_decision_git_log``, so the
    existing double-wrap-into-DecisionGitLogUnavailable behavior for that
    path is unchanged).
    """
    mid8 = resolve_mid8(mission_slug, mission_id=mission_id)
    if coord_routing_topology and not mid8:
        from runtime.next.runtime_bridge import DecisionGitLogUnavailable  # noqa: PLC0415

        raise DecisionGitLogUnavailable(
            f"Cannot resolve mid8 for coordination-topology mission "
            f"{mission_slug!r} (mission_id unresolvable); refusing to compose "
            "a malformed coordination branch without durable decision evidence."
        )

    decision_target = CommitTarget(ref=coordination_branch)

    if not coord_routing_topology:
        return mid8, repo_root, decision_target

    worktree_root_candidate = CoordinationWorkspace.worktree_path(repo_root, mission_slug, mid8)
    return mid8, worktree_root_candidate, decision_target
