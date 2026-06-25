"""Doctrine-health DATA COLLECTORS for the ``doctor doctrine`` command (WP03, #2059).

This module completes the doctrine-health seam that #1623 left behind. #1623
scoped its extraction to the RENDER layer only (``_profile_health_render``) and
left the collectors in ``doctor.py``. This module moves Cluster J — the data
collectors — beside the existing MODEL (:mod:`._doctrine_health`) and RENDER
(:mod:`._profile_health_render`) modules, finishing the MODEL/RENDER/COLLECT
triad.

Import discipline (one-way graph, I-2): collect → model / render / shared. This
module imports from :mod:`._doctrine_health` (MODEL types), from
:mod:`._profile_health_render` (the ``_SELECTION_KIND_PLURALS`` constant), and
from :mod:`._doctor_shared` if shared infra is needed. It must NEVER import
``doctor.py`` (the orchestrator re-exports FROM here).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ._profile_health_render import _SELECTION_KIND_PLURALS

if TYPE_CHECKING:
    from ._doctrine_health import DoctrineHealthReport

# ``__all__`` lists the collectors re-exported through the ``doctor`` shim
# (FR-006) plus the collectors ``doctor.py`` delegates to. The remaining
# helpers are intra-module (used here + by this module's own unit tests) and
# are deliberately NOT exported — listing them would register orphan public
# symbols under the dead-symbol gate (tests/architectural/test_no_dead_symbols).
__all__ = [
    "_resolve_pack_version",
    "_count_pack_artifacts",
    "_collect_profile_health",
    "_attach_pack_health",
    "_build_pack_entries",
    "_collect_doctrine_collisions",
    "_collect_org_layer_data",
    "_build_selection_block",
]


_ORG_ARTIFACT_DIRS: tuple[str, ...] = (
    "directives",
    "tactics",
    "styleguides",
    "toolguides",
    "paradigms",
    "procedures",
    "agent_profiles",
    "mission_step_contracts",
)


def _resolve_pack_version(snapshot_path: Path) -> tuple[str, str | None, bool]:
    """Return ``(pack_version, fetched_at, is_git_pack)`` for an org snapshot.

    For git-managed snapshots, ``pack_version`` is the ``git describe --tags
    --always`` output; ``fetched_at`` is ``None``.  For non-git snapshots, the
    version + timestamp are read from ``pack-manifest.yaml`` when present.
    Falls back to ``"unknown"`` if neither source yields a value.
    """
    import subprocess as _sp

    is_git_pack = (snapshot_path / ".git").exists()
    if is_git_pack:
        try:
            version = _sp.check_output(
                ["git", "-C", str(snapshot_path), "describe", "--tags", "--always"],
                stderr=_sp.DEVNULL,
                text=True,
            ).strip()
            return version or "git (version unavailable)", None, True
        except (_sp.CalledProcessError, OSError):
            return "git (version unavailable)", None, True

    manifest_path = snapshot_path / "pack-manifest.yaml"
    if manifest_path.exists():
        try:
            from ruamel.yaml import YAML

            yaml = YAML(typ="safe")
            data = yaml.load(manifest_path.read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001
            return "unknown", None, False
        if isinstance(data, dict):
            version = str(data.get("pack_version") or "unknown")
            fetched_at = data.get("fetched_at")
            return version, str(fetched_at) if fetched_at else None, False
    return "unknown", None, False


def _count_pack_artifacts(snapshot_path: Path) -> dict[str, int]:
    """Return per-artifact YAML counts for an org snapshot directory."""
    counts: dict[str, int] = {}
    for artifact_type in _ORG_ARTIFACT_DIRS:
        adir = snapshot_path / artifact_type
        if adir.exists():
            counts[artifact_type] = len(list(adir.glob("*.yaml")))
    return counts


def _summarize_org_charter(snapshot_path: Path) -> dict[str, object]:
    """Inspect ``org-charter.yaml`` in *snapshot_path* and return a JSON-able summary.

    Gracefully degrades when the optional
    ``specify_cli.doctrine.org_charter`` module is not yet shipped (WP09).
    """
    charter_path = snapshot_path / "org-charter.yaml"
    if not charter_path.exists():
        return {"present": False}

    try:
        from specify_cli.doctrine.org_charter import load_org_charter_policy
    except ImportError:
        # Module not yet shipped — surface presence without policy details.
        return {"present": True, "module_available": False}

    try:
        policy = load_org_charter_policy(snapshot_path)
    except Exception:  # noqa: BLE001
        return {"present": True, "module_available": True, "load_error": True}
    if policy is None:
        return {"present": False}

    return {
        "present": True,
        "module_available": True,
        "interview_defaults_count": len(getattr(policy, "interview_defaults", {}) or {}),
        "required_directives_count": len(getattr(policy, "required_directives", []) or []),
        "governance_policies_count": len(getattr(policy, "governance_policies", []) or []),
    }


def _collect_profile_health(repo_root: Path) -> DoctrineHealthReport:
    """Build the agent-profile + org-DRG health report once (WP08, NFR-001).

    Instantiates a single :class:`~doctrine.service.DoctrineService` rooted at
    the configured org packs, reads the WP05
    ``AgentProfileRepository.skipped_profiles()`` diagnostics (no regex
    scraping), and groups valid + skipped counts into one ``PackHealth`` per
    layer.  The org-DRG state is collected here too so the human and JSON
    surfaces share a single DRG load (the old double-load was the main
    NFR-001 cost).

    Diagnostics are READ-ONLY and must never crash on operator
    misconfiguration. A profile-load failure no longer degrades to a silent,
    vacuously-green empty report (the #1584 false-healthy class): the crash is
    *recorded* (into ``org_drg["errors"]``) so the report is honestly unhealthy
    and "collector crashed" is distinguishable from "genuinely zero profiles".
    """
    from ._doctrine_health import DoctrineHealthReport, build_pack_health_by_layer

    from doctrine.agent_profiles.diagnostics import SkippedProfile

    provenance_by_layer: dict[str, int] = {}
    skipped: list[SkippedProfile] = []
    load_error: str | None = None
    try:
        from doctrine.service import DoctrineService
        from specify_cli.doctrine.config import resolve_org_roots

        org_roots = resolve_org_roots(repo_root)
        project_doctrine = repo_root / ".kittify" / "doctrine"
        project_root = project_doctrine if project_doctrine.exists() else None
        service = DoctrineService(
            org_roots=list(org_roots),
            project_root=project_root,
        )
        repo = service.agent_profiles
        for profile in repo.list_all():
            layer = repo.get_provenance(profile.profile_id) or "unknown"
            provenance_by_layer[layer] = provenance_by_layer.get(layer, 0) + 1
        skipped = list(repo.skipped_profiles())
    except Exception as exc:  # noqa: BLE001 — diagnostics must never crash
        provenance_by_layer = {}
        skipped = []
        load_error = f"profile-health load error: {exc}"

    packs = build_pack_health_by_layer(
        provenance_by_layer=provenance_by_layer,
        skipped_profiles=skipped,
    )
    org_drg = _collect_org_layer_data(repo_root)
    if load_error is not None:
        # Record the crash so the honest ``healthy`` flag (which checks
        # ``org_drg['errors']``) reports unhealthy rather than vacuously green.
        if isinstance(org_drg, dict):
            existing = org_drg.get("errors")
            errors = list(existing) if isinstance(existing, list) else []
            errors.append(load_error)
            org_drg["errors"] = errors
        else:  # pragma: no cover — _collect_org_layer_data always returns a dict
            org_drg = {"errors": [load_error]}
    return DoctrineHealthReport(packs=packs, org_drg=org_drg)


def _attach_pack_health(
    pack_entries: list[dict[str, object]], report: DoctrineHealthReport
) -> None:
    """Attach per-layer ``PackHealth`` to registry pack entries for FR-010 rendering.

    Org-pack registry entries are org-layer snapshots, so each present pack is
    annotated with the report's ``org`` layer health (if any).  This is what
    makes the human renderer color the pack header from derived health rather
    than snapshot presence.
    """
    org_pack = next((p for p in report.packs if p.layer == "org"), None)
    if org_pack is None:
        return
    health_dict = org_pack.to_dict()
    for entry in pack_entries:
        if entry.get("snapshot_present"):
            entry["pack_health"] = health_dict


def _build_pack_entries(registry: object, repo_root: Path) -> list[dict[str, object]]:
    """Build per-pack registry entries (name/version/counts/charter) for rendering."""
    pack_entries: list[dict[str, object]] = []
    for pack in registry.packs:  # type: ignore[attr-defined]
        snapshot_path = pack.effective_root(repo_root)
        entry: dict[str, object] = {
            "name": pack.name,
            "local_path": str(snapshot_path),
            "source_type": pack.source_type,
            "url": pack.url,
            "ref": pack.ref,
            "snapshot_present": snapshot_path.exists(),
        }
        if snapshot_path.exists():
            version, fetched_at, is_git = _resolve_pack_version(snapshot_path)
            entry["pack_version"] = version
            entry["fetched_at"] = fetched_at
            entry["is_git_pack"] = is_git
            entry["artifact_counts"] = _count_pack_artifacts(snapshot_path)
            entry["org_charter"] = _summarize_org_charter(snapshot_path)
        pack_entries.append(entry)
    return pack_entries


def _collect_doctrine_collisions(repo_root: Path) -> list[dict[str, object]]:
    """Run the doctrine resolver and collect any layer-collision warnings.

    Returns a list of structured collision descriptors (kind, item_id,
    higher_layer, lower_layer, replaced, inherited) for surfacing via
    ``doctor doctrine`` (FR-003 wording per ADR 2026-05-16-1).
    """
    import re
    import warnings as _warnings

    from doctrine.base import DoctrineLayerCollisionWarning
    from doctrine.service import DoctrineService
    from specify_cli.doctrine.config import resolve_org_roots

    org_roots = resolve_org_roots(repo_root)
    project_doctrine = repo_root / ".kittify" / "doctrine"
    project_root = project_doctrine if project_doctrine.exists() else None

    service = DoctrineService(
        org_roots=list(org_roots),
        project_root=project_root,
    )

    # Touch every repository so each one runs through its loader and emits
    # any collision warnings.
    accessors = (
        "directives",
        "tactics",
        "styleguides",
        "toolguides",
        "paradigms",
        "procedures",
        "mission_step_contracts",
        "agent_profiles",
    )

    collisions: list[dict[str, object]] = []
    pattern = re.compile(
        r"Doctrine override: (?P<kind>\S+) (?P<item_id>\S+) "
        r"from (?P<higher>\S+) shadowed (?P<lower>\S+) "
        r"\((?P<replaced>\d+) field\(s\) replaced; "
        r"(?P<inherited>\d+) field\(s\) inherited\)\."
    )

    with _warnings.catch_warnings(record=True) as captured:
        _warnings.simplefilter("always")
        for name in accessors:
            try:
                getattr(service, name)
            except Exception:  # noqa: BLE001, S112 — doctor must not fail on a single repo's load error
                continue
    for w in captured:
        if not isinstance(w.message, DoctrineLayerCollisionWarning):
            continue
        m = pattern.match(str(w.message))
        if not m:
            continue
        collisions.append(
            {
                "kind": m.group("kind"),
                "item_id": m.group("item_id"),
                "higher_layer": m.group("higher"),
                "lower_layer": m.group("lower"),
                "replaced": int(m.group("replaced")),
                "inherited": int(m.group("inherited")),
            }
        )
    return collisions


def _collect_org_layer_data(repo_root: Path) -> dict[str, object]:
    """Return structured org-layer data for ``doctor doctrine --json`` (FR-007).

    Mirrors the human-readable output of :func:`_render_org_layer_section`
    but as a dict suitable for JSON serialisation.  Always returns a dict
    with an ``"org_drg"`` key so callers can rely on its presence.
    """
    from charter.drg import (  # noqa: PLC0415
        OrgDRGConflictError,
        OrgPackMissingError,
        load_org_drg,
        merge_three_layers,
    )
    from charter.catalog import resolve_doctrine_root  # noqa: PLC0415
    from doctrine.drg.loader import load_graph_or_dir  # noqa: PLC0415

    result: dict[str, object] = {
        "configured_packs": [],
        "collision_warnings": [],
        "errors": [],
    }

    try:
        fragments = load_org_drg(repo_root)
    except OrgPackMissingError as exc:
        result["errors"] = [str(exc)]
        return result
    except Exception as exc:  # noqa: BLE001
        result["errors"] = [f"org-DRG load error: {exc}"]
        return result

    packs = []
    for frag in fragments:
        packs.append(
            {
                "name": frag.pack_name,
                "source_kind": frag.source_kind,
                "source_ref": frag.source_ref,
                "layer_index": frag.layer_index,
                "node_count": len(frag.nodes),
                "edge_count": len(frag.edges),
                "fetched": True,
            }
        )
    result["configured_packs"] = packs

    if not fragments:
        return result

    try:
        built_in = load_graph_or_dir(resolve_doctrine_root())
        merge_three_layers(built_in=built_in, org_fragments=fragments, project=None)
    except OrgDRGConflictError as exc:
        result["collision_warnings"] = [
            {
                "kind": c.kind,
                "target_id": c.target_id,
                "conflicting_layers": c.conflicting_layers,
                "resolution": c.resolution_applied,
            }
            for c in exc.conflicts
        ]
    except Exception:  # noqa: BLE001
        pass

    return result


def _resolve_artifact_source(
    item_id: str,
    plural: str,
    service: object,
    org_required: dict[str, list[str]],
    project_selected: set[str],
) -> str:
    """Return a stable ``source: <token>`` annotation for *item_id*.

    The annotation tokens are deliberately compact so the snapshot test
    can pin them byte-for-byte:

    * ``built-in`` — artifact comes from the built-in doctrine layer
    * ``project`` — artifact lives under ``.kittify/doctrine/``
    * ``org`` — artifact lives in an org pack (per-pack attribution is
      not yet tracked at the repository layer; see ``_collect_org_source_map``
      in charter.context for the same limitation)
    * ``charter`` — declared selected in the project charter but the
      DoctrineService does not (yet) know about it (e.g. typo or
      missing snapshot)
    * ``org-required`` — required by an org pack's ``org-charter.yaml``
      but not present in the resolved catalog
    """
    repo = getattr(service, plural, None)
    if repo is not None:
        try:
            provenance = repo.get_provenance(item_id)
        except (AttributeError, KeyError):
            provenance = None
        if provenance == "builtin":
            return "built-in"
        if provenance == "project":
            return "project"
        if provenance == "org":
            return "org"
    # Not loaded — distinguish "project charter declared it" vs "org pack
    # required it" so the operator can find the right config file.
    if item_id in project_selected:
        return "charter"
    if item_id in (org_required.get(plural) or []):
        return "org-required"
    return "unknown"


def _read_project_selections(repo_root: Path) -> dict[str, list[str]]:
    """Read project-charter ``selected_<kind>`` lists (best-effort, FR-018).

    We intentionally bypass ``charter.sync.load_governance_config`` here: that
    loader runs the charter auto-sync pipeline (and requires a git repository).
    The Selections section is a diagnostic — it MUST work in any working tree,
    including freshly-bootstrapped tmp fixtures and non-git operator
    workspaces.  Reading the YAML directly preserves accuracy while keeping the
    diagnostic side-effect-free.  Missing/malformed YAML degrades to empty lists.
    """
    selections: dict[str, list[str]] = {kind: [] for kind in _SELECTION_KIND_PLURALS}
    governance_yaml = repo_root / ".kittify" / "charter" / "governance.yaml"
    if not governance_yaml.exists():
        return selections
    try:
        from ruamel.yaml import YAML as _YAML

        data = _YAML(typ="safe").load(governance_yaml.read_text(encoding="utf-8"))
        doctrine_block = (data or {}).get("doctrine") or {}
        for kind in _SELECTION_KIND_PLURALS:
            value = doctrine_block.get(f"selected_{kind}")
            if isinstance(value, list):
                selections[kind] = [str(v) for v in value]
    except Exception:  # noqa: BLE001 — diagnostics must never crash on malformed yaml
        pass
    return selections


def _read_org_required(repo_root: Path) -> dict[str, list[str]]:
    """Read merged org-charter ``required_<kind>`` lists (best-effort, FR-018).

    Missing or invalid org config degrades to empty lists; diagnostics must
    never crash.
    """
    org_required: dict[str, list[str]] = {kind: [] for kind in _SELECTION_KIND_PLURALS}
    try:
        from charter.invocation_context import ProjectContext
        from specify_cli.doctrine.org_charter import load_org_charter_policies

        _pack_ctx = None
        try:
            _ctx = ProjectContext.from_repo(repo_root)
            _pack_ctx = _ctx.require_pack_context()
        except Exception:  # noqa: BLE001 — pack_context is best-effort
            pass

        policy = load_org_charter_policies(repo_root, pack_context=_pack_ctx)
        for kind in _SELECTION_KIND_PLURALS:
            org_required[kind] = list(getattr(policy, f"required_{kind}", []) or [])
    except Exception:  # noqa: BLE001 — diagnostics must never crash on missing/invalid org
        pass
    return org_required


def _build_selection_block(repo_root: Path) -> dict[str, list[dict[str, str]]]:
    """Return ``{plural: [{"id": ..., "source": ...}, ...]}`` for FR-018.

    Composes the union of project charter ``selected_<kind>`` and merged
    org ``required_<kind>`` lists, dedupes per-kind (preserving order:
    project-charter ids first, org-required ids appended), and tags each
    entry with the resolved source layer.

    Mission-type-profile selections are intentionally excluded here:
    profiles apply per-mission (gated by ``meta.json mission_type``)
    while ``doctor doctrine`` is a project-wide diagnostic.  The
    selections block reflects the *globally* active set so the operator
    can audit charter intent without picking a specific mission.
    """
    from doctrine.service import DoctrineService
    from specify_cli.doctrine.config import resolve_org_roots

    project_selections = _read_project_selections(repo_root)
    org_required = _read_org_required(repo_root)

    # DoctrineService instance for provenance lookup.
    org_roots = resolve_org_roots(repo_root)
    project_doctrine = repo_root / ".kittify" / "doctrine"
    project_root = project_doctrine if project_doctrine.exists() else None
    service = DoctrineService(
        org_roots=list(org_roots),
        project_root=project_root,
    )

    result: dict[str, list[dict[str, str]]] = {}
    for kind in _SELECTION_KIND_PLURALS:
        seen: set[str] = set()
        ordered: list[str] = []
        for item_id in project_selections[kind] + org_required[kind]:
            if item_id in seen:
                continue
            seen.add(item_id)
            ordered.append(item_id)
        project_set = set(project_selections[kind])
        entries: list[dict[str, str]] = []
        for item_id in ordered:
            entries.append({
                "id": item_id,
                "source": _resolve_artifact_source(
                    item_id, kind, service, org_required, project_set
                ),
            })
        result[kind] = entries
    return result
