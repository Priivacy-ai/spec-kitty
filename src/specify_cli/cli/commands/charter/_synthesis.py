"""Synthesis helpers shared by ``charter synthesize`` and ``charter resynthesize``.

Lifted from the legacy ``charter.py`` during the WP06 MS-1 split. Module is
behaviour-preserving; only import paths changed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from specify_cli.task_utils import TaskCliError

# ``_interview_path`` is part of the legacy charter test-patch surface. We must
# look it up on the package module at call time (not bind it at import time) so
# ``patch("specify_cli.cli.commands.charter._interview_path", …)`` propagates
# here after the WP06 split. ``_synthesis`` is imported from the package
# ``__init__`` itself, so the package import is performed lazily inside
# functions to avoid a circular import at module-load time.


def _build_synthesis_request(
    repo_root: Path,
    adapter_name: str,
    evidence: Any = None,
) -> tuple[Any, Any]:
    """Build a SynthesisRequest + adapter from the project's current interview state.

    Returns ``(SynthesisRequest, adapter)`` ready for synthesize() / resynthesize().
    Raises ``TaskCliError`` if the interview answers file does not exist.
    """
    import uuid

    from charter.interview import read_interview_answers
    from charter.synthesizer.fixture_adapter import FixtureAdapter
    from charter.synthesizer.generated_artifact_adapter import GeneratedArtifactAdapter
    from charter.synthesizer.request import SynthesisRequest, SynthesisTarget

    import specify_cli.cli.commands.charter as _charter_pkg

    answers_path = _charter_pkg._interview_path(repo_root)
    interview_data = read_interview_answers(answers_path)
    if interview_data is None:
        raise TaskCliError(
            "No interview answers found. "
            "Run 'spec-kitty charter interview' first."
        )

    # Build a minimal interview snapshot from the interview data
    interview_snapshot: dict[str, Any] = {
        "mission_id": interview_data.mission,
        "selected_directives": interview_data.selected_directives,
        "selected_paradigms": interview_data.selected_paradigms,
    }
    interview_snapshot.update(dict(interview_data.answers))

    # Build a minimal doctrine snapshot (directives only for now)
    doctrine_snapshot: dict[str, Any] = {
        "directives": {},
        "tactics": {},
        "styleguides": {},
    }

    # Build a minimal DRG snapshot with built-in directives as nodes
    drg_nodes = []
    for directive_id in interview_data.selected_directives:
        drg_nodes.append({
            "urn": f"directive:{directive_id}",
            "kind": "directive",
            "id": directive_id,
        })
    drg_snapshot: dict[str, Any] = {
        "nodes": drg_nodes,
        "edges": [],
        "schema_version": "1",
    }

    # Internal placeholder target. ``synthesize()`` derives the actual
    # target list from the interview, so this token is never the artifact
    # the synthesizer actually produces — it just satisfies the Pydantic
    # constructor that requires a non-None ``target``.
    #
    # FR-005 (WP02): ``PROJECT_000`` is INTERNAL ONLY here. The CLI
    # surface MUST NOT expose it. The four user-visible code paths
    # (``--json`` success, ``--json`` dry-run, ``--json`` failure, and
    # the human-readable text branch) all derive their displayed
    # artifact_id from ``ProvenanceEntry.artifact_urn`` produced by the
    # synthesizer (see ``_load_written_artifacts_from_manifest`` and
    # ``compute_written_artifacts``), never from this constructor
    # placeholder. The path-parity test in
    # ``tests/charter/synthesizer/test_synthesize_path_parity.py``
    # guards against regression.
    target = SynthesisTarget(
        kind="directive",
        slug="synthesize-placeholder",
        title="Synthesize Placeholder",
        artifact_id="PROJECT_000",
        source_section="mission_type",
    )

    run_id = str(uuid.uuid4()).replace("-", "").upper()[:26]

    request = SynthesisRequest(
        target=target,
        interview_snapshot=interview_snapshot,
        doctrine_snapshot=doctrine_snapshot,
        drg_snapshot=drg_snapshot,
        run_id=run_id,
        evidence=evidence,
    )

    adapter_obj: Any
    if adapter_name == "generated":
        adapter_obj = GeneratedArtifactAdapter(repo_root=repo_root)
    elif adapter_name == "fixture":
        adapter_obj = FixtureAdapter()
    else:
        raise TaskCliError(
            f"Unknown adapter '{adapter_name}'. "
            "Supported adapters are '--adapter generated' and '--adapter fixture'. "
            "Doctrine generation is performed by the LLM harness (Claude Code, Codex, "
            "Cursor, etc.) via the spec-kitty-charter-doctrine skill. "
            "spec-kitty never calls an LLM itself."
        )

    return request, adapter_obj


def _collect_evidence_result(
    repo_root: Path,
    *,
    skip_code_evidence: bool,
    skip_corpus: bool,
) -> Any:
    from charter.evidence.orchestrator import EvidenceOrchestrator, load_url_list_from_config

    url_list = load_url_list_from_config(repo_root)
    orchestrator = EvidenceOrchestrator(
        repo_root=repo_root,
        url_list=url_list,
        skip_code=skip_code_evidence,
        skip_corpus=skip_corpus,
    )
    return orchestrator.collect()


def _build_synthesis_validation_callback(request: Any) -> Any:
    from doctrine.drg.models import DRGGraph
    from importlib.metadata import version as pkg_version

    from charter.synthesizer.interview_mapping import normalize_interview_snapshot, resolve_sections
    from charter.synthesizer.orchestrator import _built_in_drg_from_snapshot
    from charter.synthesizer.project_drg import emit_project_layer, persist as persist_project_graph
    from charter.synthesizer.targets import build_targets, detect_duplicates, order_targets
    from charter.synthesizer.validation_gate import validate as validate_project_graph

    spec_kitty_version = pkg_version("spec-kitty-cli")
    built_in_drg = DRGGraph.model_validate(_built_in_drg_from_snapshot(request.drg_snapshot))
    interview_snapshot = normalize_interview_snapshot(dict(request.interview_snapshot))
    sections = resolve_sections(interview_snapshot)
    targets = build_targets(
        interview_snapshot=interview_snapshot,
        mappings=sections,
        drg_snapshot=dict(request.drg_snapshot),
    )
    targets = order_targets(targets)
    detect_duplicates(targets)
    if not targets:
        targets = [request.target]

    def _validation_callback(staged_dir: Any) -> None:
        project_graph = emit_project_layer(
            targets=targets,
            spec_kitty_version=spec_kitty_version,
            built_in_drg=built_in_drg,
        )
        persist_project_graph(project_graph, staged_dir.root, staged_dir.guard)
        validate_project_graph(staged_dir.root, built_in_drg)

    return _validation_callback


def _read_written_artifacts_from_manifest(repo_root: Path) -> list[dict[str, str]]:
    """Read manifest entries for the strict synthesize success envelope."""
    try:
        from charter.synthesizer.manifest import MANIFEST_PATH, load_yaml as _load_manifest
    except Exception:
        return []
    manifest_path = repo_root / MANIFEST_PATH
    if not manifest_path.exists():
        return []
    try:
        manifest = _load_manifest(manifest_path)
    except Exception:
        return []
    return [{"path": entry.path, "kind": entry.kind} for entry in manifest.artifacts]


def _provenance_to_planned_artifacts(
    results: list[tuple[Any, Any]],
) -> list[dict[str, str]]:
    """Convert synthesis provenance entries into planned doctrine paths."""
    from charter.synthesizer.artifact_naming import (
        artifact_filename,
        doctrine_kind_subdir,
    )

    planned: list[dict[str, str]] = []
    for _body, prov in results:
        kind = prov.artifact_kind
        slug = prov.artifact_slug
        artifact_id: str | None = None
        if kind == "directive":
            artifact_id = prov.artifact_urn.split(":", 1)[1]
        try:
            filename = artifact_filename(kind, slug, artifact_id)
            subdir = doctrine_kind_subdir(kind)
        except Exception:  # noqa: S112
            continue
        planned.append(
            {
                "path": f".kittify/doctrine/{subdir}/{filename}",
                "kind": kind,
            }
        )
    return planned


def _staged_to_planned_artifacts(staged_files: list[str]) -> list[dict[str, str]]:
    """Convert legacy staged ``kind:slug`` selectors to planned artifacts."""
    from charter.synthesizer.artifact_naming import (
        artifact_filename,
        doctrine_kind_subdir,
    )

    planned: list[dict[str, str]] = []
    for selector in staged_files:
        if ":" not in selector:
            continue
        kind, slug = selector.split(":", 1)
        artifact_id: str | None = None
        if kind == "directive":
            artifact_id = "PROJECT_000"
        try:
            filename = artifact_filename(kind, slug, artifact_id)
            subdir = doctrine_kind_subdir(kind)
        except Exception:  # noqa: S112
            continue
        planned.append(
            {
                "path": f".kittify/doctrine/{subdir}/{filename}",
                "kind": kind,
            }
        )
    return planned


def _run_synthesis_dry_run(
    request: Any,
    syn_adapter: Any,
    repo_root: Path,
) -> list[str]:
    """Stage + validate without promoting; return ``kind:slug`` selectors.

    Legacy ``staged_artifacts`` field on the dry-run JSON envelope is sourced
    from this list. The strict ``written_artifacts`` field (FR-003) is built
    separately in :func:`_run_synthesis_dry_run_with_artifacts`, which calls
    this function and additionally projects the typed staged-artifact entries
    via :func:`charter.synthesizer.write_pipeline.compute_written_artifacts`.
    """
    from charter.synthesizer.staging import StagingDir
    from charter.synthesizer.synthesize_pipeline import run_all
    from charter.synthesizer.write_pipeline import stage_and_validate

    results = run_all(request, adapter=syn_adapter)
    validation_callback = _build_synthesis_validation_callback(request)

    with StagingDir.create(repo_root, request.run_id) as staging_dir:
        staged_artifacts: list[str] = stage_and_validate(
            request,
            staging_dir,
            results,
            validation_callback,
        )
        staging_dir.wipe()

    return staged_artifacts


def _run_synthesis_dry_run_with_artifacts(
    request: Any,
    syn_adapter: Any,
    repo_root: Path,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Stage + validate; return both legacy selectors and typed written-artifact entries.

    The typed ``written_artifacts`` list is sourced from the SAME
    ``compute_written_artifacts`` helper used by the real-run branch — this is
    the FR-004 byte-equal-path guarantee. ``run_all`` is invoked once; the
    same ``results`` feed both ``stage_and_validate`` (which exercises the
    write-time validation gate) and ``compute_written_artifacts`` (which
    projects per-artifact provenance).
    """
    from charter.synthesizer.staging import StagingDir
    from charter.synthesizer.synthesize_pipeline import run_all
    from charter.synthesizer.write_pipeline import (
        compute_written_artifacts,
        stage_and_validate,
    )

    results = run_all(request, adapter=syn_adapter)
    validation_callback = _build_synthesis_validation_callback(request)

    with StagingDir.create(repo_root, request.run_id) as staging_dir:
        staged_artifacts = stage_and_validate(
            request,
            staging_dir,
            results,
            validation_callback,
        )
        staging_dir.wipe()

    # FR-003 / FR-004: typed staged-artifact entries — never reconstructed
    # from kind:slug selectors. Same source of truth as the real-run path.
    typed = compute_written_artifacts(results, repo_root)
    written_artifacts = [
        {
            "path": entry.path,
            "kind": entry.kind,
            "slug": entry.slug,
            "artifact_id": entry.artifact_id,
        }
        for entry in typed
    ]
    return staged_artifacts, written_artifacts


def _load_written_artifacts_from_manifest(repo_root: Path) -> list[dict[str, Any]]:
    """Project the on-disk synthesis manifest into ``WrittenArtifact`` dicts.

    Single source of truth for the real-run JSON envelope (FR-003): we read
    the manifest the write pipeline wrote last (KD-2 commit marker) and
    project each ``ManifestArtifactEntry`` plus its sibling provenance
    sidecar into the four-field ``WrittenArtifact`` shape.

    The provenance sidecar is consulted because the manifest does not carry
    ``artifact_id`` directly; the URN segment after ``directive:`` is the
    canonical id (e.g. ``directive:PROJECT_001`` → ``PROJECT_001``). For
    non-directive kinds (tactic, styleguide), ``artifact_id`` is ``None``
    per the ``WrittenArtifact`` schema.

    Returns ``[]`` when the manifest is absent — this happens when the
    real-run code path is mocked out by tests, so the JSON envelope still
    carries a valid empty ``written_artifacts`` list (FR-002 / INV-E-2).

    All fields are pure data; the function never raises (a corrupt manifest
    yields an empty list rather than blowing up the strict-JSON contract).
    """
    try:
        from charter.synthesizer.manifest import MANIFEST_PATH, load_yaml
    except Exception:
        return []

    manifest_path = repo_root / MANIFEST_PATH
    if not manifest_path.is_file():
        return []

    try:
        manifest = load_yaml(manifest_path)
    except Exception:
        return []

    entries: list[dict[str, Any]] = []
    for entry in manifest.artifacts:
        artifact_id: str | None = None
        if entry.kind == "directive":
            # Provenance sidecar at .kittify/charter/provenance/<kind>-<slug>.yaml
            # carries the URN; that is the only on-disk surface that records
            # the symbolic artifact_id without lossy reconstruction.
            prov_path = repo_root / entry.provenance_path
            artifact_id = _extract_artifact_id_from_provenance(prov_path)

        entries.append(
            {
                "path": entry.path,
                "kind": entry.kind,
                "slug": entry.slug,
                "artifact_id": artifact_id,
            }
        )
    return entries


def _extract_artifact_id_from_provenance(prov_path: Path) -> str | None:
    """Read ``artifact_urn`` from a provenance sidecar; return the id segment.

    The sidecar is YAML with a top-level ``artifact_urn`` key shaped like
    ``directive:PROJECT_001``. Return ``None`` on any parse failure or if
    the URN does not carry a non-empty id segment.
    """
    if not prov_path.is_file():
        return None
    try:
        from ruamel.yaml import YAML

        y = YAML(typ="safe")
        with prov_path.open("r", encoding="utf-8") as f:
            data = y.load(f)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    urn = data.get("artifact_urn")
    if not isinstance(urn, str):
        return None
    parts = urn.split(":", 1)
    if len(parts) != 2 or not parts[1]:
        return None
    return parts[1]


def _list_resynthesis_topics(
    request: Any,
    repo_root: Path,
) -> dict[str, list[str]]:
    from charter.synthesizer.resynthesize_pipeline import (
        _load_merged_drg,
        _load_project_artifacts_from_provenance,
    )

    project_artifacts = _load_project_artifacts_from_provenance(repo_root)
    merged_drg = _load_merged_drg(repo_root, request)
    interview_sections = sorted(str(section) for section in request.interview_snapshot)

    artifact_topics = []
    for artifact in project_artifacts:
        selector = artifact.urn if artifact.kind == "directive" else f"{artifact.kind}:{artifact.slug}"
        artifact_topics.append(selector)

    drg_topics: list[str] = []
    for node in merged_drg.get("nodes", []):
        if isinstance(node, dict):
            urn = node.get("urn")
            if isinstance(urn, str) and urn:
                drg_topics.append(urn)

    return {
        "project_artifacts": sorted(dict.fromkeys(artifact_topics)),
        "drg_urns": sorted(dict.fromkeys(drg_topics)),
        "interview_sections": interview_sections,
        "interview_section_aliases": sorted(section.replace("_", "-") for section in interview_sections),
    }


def _has_generated_artifacts(repo_root: Path) -> bool:
    """Return True iff ``.kittify/charter/generated/`` contains agent-authored YAMLs.

    The ``generated`` adapter (production default) reads YAML files written by
    the LLM harness under ``.kittify/charter/generated/{directives,tactics,
    styleguides}/``. On a fresh project the harness has not run yet, so this
    directory is either missing or empty. The fresh-project synthesize path
    (T032 / #839) keys on this signal.
    """
    generated_root = repo_root / ".kittify" / "charter" / "generated"
    if not generated_root.is_dir():
        return False
    for sub in ("directives", "tactics", "styleguides"):
        sub_dir = generated_root / sub
        if sub_dir.is_dir() and any(sub_dir.glob("*.yaml")):
            return True
    return False


# Fresh-project doctrine seed helpers were carved out into ``_fresh_doctrine``
# so this module stays comfortably under the WP06 line budget. Re-exported so
# legacy ``from specify_cli.cli.commands.charter._synthesis import …`` consumers
# (and the package ``__init__``) keep working unchanged.
from specify_cli.cli.commands.charter._fresh_doctrine import (  # noqa: E402,F401
    _MINIMAL_FRESH_DOCTRINE_PROVENANCE_TEMPLATE,
    _materialize_fresh_doctrine,
    _planned_fresh_doctrine_deletes,
    _planned_fresh_doctrine_paths,
)

__all__ = [
    "_MINIMAL_FRESH_DOCTRINE_PROVENANCE_TEMPLATE",
    "_build_synthesis_request",
    "_build_synthesis_validation_callback",
    "_collect_evidence_result",
    "_extract_artifact_id_from_provenance",
    "_has_generated_artifacts",
    "_list_resynthesis_topics",
    "_load_written_artifacts_from_manifest",
    "_materialize_fresh_doctrine",
    "_planned_fresh_doctrine_deletes",
    "_planned_fresh_doctrine_paths",
    "_provenance_to_planned_artifacts",
    "_read_written_artifacts_from_manifest",
    "_run_synthesis_dry_run",
    "_run_synthesis_dry_run_with_artifacts",
    "_staged_to_planned_artifacts",
]
