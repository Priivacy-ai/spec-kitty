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
import os
import re
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict

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
    from charter.invocation_context import OperationalContext as OperationalContextT

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


def _build_run_ref(*, run_id: str, run_dir: str, mission_type: str) -> MissionRunRef:
    """Construct MissionRunRef across runtime versions."""
    try:
        return MissionRunRef(
            run_id=run_id,
            run_dir=run_dir,
            mission_key=mission_type,
        )
    except TypeError:
        return MissionRunRef(
            run_id=run_id,
            run_dir=run_dir,
            mission_type=mission_type,  # type: ignore[call-arg]  # pre-existing cross-version defensive fallback (unmodified by this move): the current pydantic MissionRunRef only has `mission_key`, but this branch guards against an older runtime-package shape (pre-internalization) that used `mission_type` — mypy can only see the one concrete model, not the hypothetical alternate shape this except clause defends against.
        )


# ---------------------------------------------------------------------------
# Template / pack discovery (T017)
# ---------------------------------------------------------------------------


def _build_discovery_context(repo_root: Path) -> DiscoveryContext:
    """Build a DiscoveryContext that finds the runtime mission template."""
    import specify_cli  # noqa: PLC0415

    # Runtime bridge uses the legacy runtime templates under specify_cli/missions.
    # The doctrine mission catalog is not behaviorally equivalent yet.
    package_root = Path(specify_cli.__file__).resolve().parent / "missions"
    return DiscoveryContext(
        project_dir=repo_root,
        builtin_roots=[package_root],
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


def _template_key_for_file(path: Path) -> str | None:
    try:
        template = load_mission_template_file(path)
        return template.mission.key
    except Exception:
        return None


def _resolve_runtime_template_in_root(root: Path, mission_type: str) -> Path | None:
    for candidate in _candidate_templates_for_root(root, mission_type):
        if not candidate.exists() or not candidate.is_file():
            continue

        paths_to_try = [candidate]
        # Prefer mission-runtime.yaml sidecar when candidate is mission.yaml.
        if candidate.name == MISSION_YAML:
            runtime_sidecar = candidate.with_name(MISSION_RUNTIME_YAML)
            if runtime_sidecar.exists() and runtime_sidecar.is_file():
                paths_to_try = [runtime_sidecar, candidate]

        for path in paths_to_try:
            template_key = _template_key_for_file(path)
            if template_key == mission_type:
                return path.resolve()

    return None


def _runtime_template_key(mission_type: str, repo_root: Path) -> str:
    """Resolve the runtime template path for a mission key.

    Uses deterministic runtime discovery precedence for mission-runtime YAML:
    explicit -> env -> project override -> project legacy -> project config
    -> user global -> built-in.

    For the built-in ``software-dev`` mission, the packaged runtime template is
    canonical after this composition rewrite. Stale user-global mission packs
    from earlier installs must not reintroduce the legacy tasks_* DAG, while
    explicit, env, and project-scoped overrides remain honored.
    """
    from runtime.next import runtime_bridge as _rb  # noqa: PLC0415

    context = _rb._build_discovery_context(repo_root)
    env_value = os.environ.get(context.env_var_name, "")
    project_tiers: list[list[Path]] = [
        list(context.explicit_paths),
        _split_env_paths(env_value),
        [repo_root / KITTIFY_DIR / "overrides" / "missions"],
        [repo_root / KITTIFY_DIR / "missions"],
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
    :class:`~charter.invocation_context.OperationalContext` never blocks a
    claim or decision. The lookup is read-only and creates no worktree or
    status side effects (NFR-004).
    """
    if not profile_id:
        return frozenset()
    try:
        from doctrine.agent_profiles import AgentProfileRepository  # noqa: PLC0415

        repo = AgentProfileRepository(project_dir=repo_root / KITTIFY_DIR / "doctrine")
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
        A populated :class:`~charter.invocation_context.OperationalContext`.
    """
    from charter.invocation_context import build_operational_context  # noqa: PLC0415
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
    from charter.invocation_context import build_operational_context  # noqa: PLC0415
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


_PRESENCE_FILE_TAGS: tuple[str, ...] = (
    "spec.md",
    "plan.md",
    "tasks.md",
    "source-register.csv",
    "findings.md",
    "report.md",
    "gap-analysis.md",
    "audit-report.md",
    "release.md",
)


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
    """

    present_artifacts: frozenset[str]
    status_facts: Mapping[str, Any]
    mission_family: str
    step_id: str
    legacy_step_id: str | None = None
    wp_advance_ready: bool | None = None


def gather_artifact_presence(
    feature_dir: Path,
    *,
    mission_family: str,
    step_id: str,
    legacy_step_id: str | None = None,
) -> ArtifactPresenceSnapshot:
    """Gather (never decide) the facts the two CLI-level guards read today.

    Mirrors the exact set of filesystem/status/bulk-edit/requirement-mapping
    reads ``_check_cli_guards`` / ``_check_composed_action_guard`` perform
    across all three mission families (software-dev / research /
    documentation), so a downstream pure ``evaluate_guards(snapshot)`` can
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
    """
    from runtime.next import runtime_bridge as _rb  # noqa: PLC0415

    present: set[str] = set()
    for tag in _PRESENCE_FILE_TAGS:
        if (feature_dir / tag).is_file():
            present.add(tag)

    tasks_dir = feature_dir / "tasks"
    tasks_dir_is_dir = tasks_dir.is_dir()
    wp_files = sorted(tasks_dir.glob("WP*.md")) if tasks_dir_is_dir else []
    if wp_files:
        present.add("tasks_wp_files")

    has_generated_docs = bool(_rb._has_generated_docs(feature_dir))
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
        "occurrence_gate_failures": tuple(_rb._occurrence_gate_failures(feature_dir)),
        "source_documented_count": _rb._count_source_documented_events(feature_dir),
        "publication_approved": bool(_rb._publication_approved(feature_dir)),
        "has_generated_docs": has_generated_docs,
    }

    return ArtifactPresenceSnapshot(
        present_artifacts=frozenset(present),
        status_facts=status_facts,
        mission_family=mission_family,
        step_id=step_id,
        legacy_step_id=legacy_step_id,
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
