"""Validate and register direct-written project doctrine without rewriting its source.

Planning performs all schema, graph and provenance work before activation may
mutate its store. Committing writes only derived state, with the manifest last.
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from urllib.parse import quote

from ulid import ULID

from charter.activation._drg_helpers import load_validated_graph
from charter.activation.drg_activation import load_org_drg
from charter.activation.synthesizer.manifest import (
    MANIFEST_PATH, ManifestArtifactEntry, SynthesisManifest, finalize_manifest,
    hash_content_bytes, load_yaml as load_manifest, verify_manifest_hash,
)
from charter.activation.synthesizer.path_guard import PathGuard
from charter.activation.synthesizer.provenance import ProvenanceEntry, provenance_path_for
from charter.activation.synthesizer.synthesize_pipeline import canonical_yaml
from charter.offering.drg.loader import has_graph_files, load_graph_or_dir, merge_layers
from charter.offering.drg.migration.extractor import graph_document_to_dict
from charter.offering.drg.models import DRGGraph
from charter.offering.drg.org_pack_config import resolve_existing_org_roots
from charter.offering.drg.project_scan import ProjectArtifact, project_reference_edges, scan_project_artifacts
from charter.offering.drg.validator import assert_valid
from kernel.clock import now_utc_seconds

__all__ = ["plan_project_registration", "commit_project_registration"]


@dataclass(frozen=True)
class ProjectRegistrationPlan:
    """Validated merged graph for cascade and prepared derived-state writes."""

    repo_root: Path
    graph: DRGGraph
    artifacts: tuple[ProjectArtifact, ...]
    warnings: tuple[str, ...]
    writes: tuple[tuple[Path, str], ...]


def _project_graph(root: Path, artifacts: tuple[ProjectArtifact, ...], base: DRGGraph) -> tuple[DRGGraph, tuple[str, ...]]:
    directory = root / ".kittify/doctrine"
    existing = load_graph_or_dir(directory) if has_graph_files(directory) else None
    nodes = {node.urn: node for node in existing.nodes} if existing else {}
    nodes.update({artifact.node.urn: artifact.node for artifact in artifacts})
    projected, warnings = project_reference_edges(artifacts, [*base.nodes, *nodes.values()])
    profile_urns = {a.node.urn for a in artifacts if a.node.kind.value == "agent_profile"}
    # Only previously projected reference edges are replaced. Explicit lineage,
    # tension and synthesis provenance edges remain owned by their authors.
    reference_relations = {"requires", "suggests"}
    edges = [e for e in existing.edges if not (
        e.source in profile_urns and e.relation.value in reference_relations
    )] if existing else []
    triples = {(e.source, e.target, e.relation): e for e in edges}
    triples.update({(e.source, e.target, e.relation): e for e in projected})
    graph = DRGGraph(schema_version="1.0", generated_at=existing.generated_at if existing else now_utc_seconds(),
                     generated_by="spec-kitty project registration", nodes=list(nodes.values()), edges=list(triples.values()))
    return graph, warnings


def _registration_records(root: Path, artifacts: tuple[ProjectArtifact, ...]) -> list[tuple[Path, str]]:
    manifest_path = root / MANIFEST_PATH
    existing = load_manifest(manifest_path) if manifest_path.exists() else None
    if existing:
        verify_manifest_hash(existing)
    entries = {(entry.kind, entry.slug): entry for entry in existing.artifacts} if existing else {}
    writes: list[tuple[Path, str]] = []
    timestamp = now_utc_seconds()
    run_id = str(ULID())
    package_version = version("spec-kitty-cli")
    for artifact in artifacts:
        kind, identifier = artifact.node.urn.split(":", 1)
        # URNs admit slash-separated identities. Encode them as one filename
        # component; preserve case except for canonical uppercase directive IDs.
        slug = quote(identifier.lower().replace("_", "-") if kind == "directive" else identifier, safe="")
        content_hash = hash_content_bytes(artifact.path.read_bytes())
        source_path = artifact.path.relative_to(root).as_posix()
        previous = next((entry for entry in entries.values() if entry.path == source_path), None)
        if previous:
            slug = previous.slug
        key = (kind, slug)
        previous = previous or entries.get(key)
        sidecar = provenance_path_for(kind, slug)
        if previous and previous.content_hash == content_hash and (root / previous.provenance_path).is_file():
            continue
        record = ProvenanceEntry(
            artifact_urn=artifact.node.urn, artifact_kind=kind, artifact_slug=slug,
            artifact_content_hash=content_hash, inputs_hash=content_hash,
            adapter_id="project-direct-write", adapter_version="1", synthesizer_version=package_version,
            source_section=source_path, source_urns=[], source_input_ids=[source_path],
            generated_at=timestamp, produced_at=timestamp, corpus_snapshot_id="(none)",
            synthesis_run_id=run_id,
            adapter_notes="Registered authored project content; no generation or source rewrite performed.",
        )
        writes.append((root / sidecar, canonical_yaml(record.model_dump(mode="python")).decode()))
        entries[key] = ManifestArtifactEntry(kind=kind, slug=slug, path=source_path,
                                             provenance_path=sidecar, content_hash=content_hash)
    if existing:
        manifest = existing.model_copy(update={"artifacts": list(entries.values()), "built_in_only": False})
    else:
        manifest = SynthesisManifest(created_at=timestamp, run_id=run_id,
                                     adapter_id="project-direct-write", adapter_version="1",
                                     synthesizer_version=package_version, manifest_hash="0" * 64,
                                     artifacts=list(entries.values()), built_in_only=False)
    manifest = finalize_manifest(manifest)
    writes.append((manifest_path, canonical_yaml(manifest.model_dump(mode="python")).decode()))
    return writes


def plan_project_registration(repo_root: Path, *, base_graph: DRGGraph | None = None) -> ProjectRegistrationPlan:
    """Return validated project registration and its merged graph without writes."""
    root = repo_root.resolve()
    artifacts = scan_project_artifacts(root)
    base = base_graph if base_graph is not None else load_validated_graph(
        root, org_roots=resolve_existing_org_roots(root), org_fragments=load_org_drg(root, strict=False),
    )
    if not artifacts:
        return ProjectRegistrationPlan(root, base, (), (), ())
    project, warnings = _project_graph(root, artifacts, base)
    project_triples = {(e.source, e.target, e.relation) for e in project.edges}
    profile_urns = {a.node.urn for a in artifacts if a.node.kind.value == "agent_profile"}
    retained_edges = [e for e in base.edges if (e.source, e.target, e.relation) not in project_triples
                      and not (e.source in profile_urns and e.relation.value in {"requires", "suggests"})]
    merged = merge_layers(base.model_copy(update={"edges": retained_edges}), project)
    assert_valid(merged)
    writes = [(root / ".kittify/doctrine/graph.yaml", canonical_yaml(graph_document_to_dict(project)).decode())]
    writes.extend(_registration_records(root, artifacts))
    changed = tuple((path, text) for path, text in writes if not path.exists() or path.read_text() != text)
    return ProjectRegistrationPlan(root, merged, artifacts, warnings, changed)


def commit_project_registration(plan: ProjectRegistrationPlan) -> None:
    """Write a validated registration plan, preserving every authored source file."""
    guard = PathGuard(plan.repo_root)
    for path, text in plan.writes:
        guard.mkdir(path.parent, caller="project_registration.commit")
        guard.write_text(path, text, caller="project_registration.commit")
