"""Direct-written doctrine registration through the charter domain seam."""
from pathlib import Path

import pytest

from charter.activation.synthesizer.manifest import load_yaml, verify
from charter.offering.artifact_kinds import ArtifactKind, PROJECT_KIND_DIRS
from specify_cli.cli.commands.doctrine import _STUB_TEMPLATES

pytestmark = pytest.mark.unit


def author_guidance(root: Path) -> dict[str, Path]:
    paths = {}
    for token, identifier in {
        "procedure": "incident-runbook", "agent_profile": "ops-responder",
        "directive": "CHANGE_FREEZE", "tactic": "verify-rollback",
        "styleguide": "incident-notes",
    }.items():
        kind = ArtifactKind(token)
        directory = root / ".kittify/doctrine" / PROJECT_KIND_DIRS[kind]
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / kind.glob_pattern.replace("*", identifier)
        content = _STUB_TEMPLATES[kind].format(artifact_id=identifier).replace("TODO", "Operational")
        if token == "agent_profile":
            content += ("collaboration:\n  operating-procedures: [incident-runbook]\n"
                        "directive-references:\n  - code: CHANGE_FREEZE\n    name: Freeze\n    rationale: Safety\n"
                        "tactic-references:\n  - id: verify-rollback\n    rationale: Safety\n"
                        "styleguide-references:\n  - id: incident-notes\n    rationale: Clarity\n")
        path.write_text(content)
        paths[token] = path
    return paths


def test_direct_written_guidance_registers_five_artifacts_without_synthesis(tmp_path):
    from charter.activation.project_registration import plan_project_registration, commit_project_registration
    paths = author_guidance(tmp_path)
    before = {key: path.read_bytes() for key, path in paths.items()}
    plan = plan_project_registration(tmp_path)
    assert not (tmp_path / ".kittify/doctrine/graph.yaml").exists()
    assert sorted((a.node.kind.value, a.path) for a in plan.artifacts) == sorted(paths.items())
    assert {e.target for e in plan.graph.edges if e.source == "agent_profile:ops-responder"} == {
        "procedure:incident-runbook", "directive:CHANGE_FREEZE", "tactic:verify-rollback", "styleguide:incident-notes",
    }
    commit_project_registration(plan)
    manifest = load_yaml(tmp_path / ".kittify/charter/synthesis-manifest.yaml")
    verify(manifest, tmp_path)
    assert sorted((a.kind, tmp_path / a.path) for a in manifest.artifacts) == sorted(paths.items())
    assert {key: path.read_bytes() for key, path in paths.items()} == before
    snapshot = {p: p.read_bytes() for p in (tmp_path / ".kittify").rglob("*.yaml")}
    commit_project_registration(plan_project_registration(tmp_path))
    assert {p: p.read_bytes() for p in snapshot} == snapshot


def test_unresolved_profile_reference_is_reported_without_phantom_node(tmp_path):
    from charter.activation.project_registration import plan_project_registration
    paths = author_guidance(tmp_path)
    paths["procedure"].unlink()
    plan = plan_project_registration(tmp_path)
    assert any("procedure:incident-runbook" in warning for warning in plan.warnings)
    assert plan.graph.get_node("procedure:incident-runbook") is None
    assert all(e.target != "procedure:incident-runbook" for e in plan.graph.edges)


def test_invalid_artifact_preflight_does_not_write_registration(tmp_path):
    from charter.activation.project_registration import plan_project_registration
    paths = author_guidance(tmp_path)
    paths["procedure"].write_text("id: incident-runbook\n")
    with pytest.raises(ValueError, match="incident-runbook"):
        plan_project_registration(tmp_path)
    assert not (tmp_path / ".kittify/charter/synthesis-manifest.yaml").exists()


def test_synthesis_reemits_all_registered_nodes_and_profile_edges(tmp_path):
    from charter.activation.project_registration import plan_project_registration, commit_project_registration
    from charter.activation.synthesizer.project_drg import emit_project_layer
    from charter.offering.drg.loader import load_built_in_graph
    from charter.activation.synthesizer.reconcile import merge_project_overlay
    author_guidance(tmp_path)
    plan = plan_project_registration(tmp_path)
    commit_project_registration(plan)
    overlay = emit_project_layer([], "test", load_built_in_graph(), project_root=tmp_path)
    assert {node.urn for node in overlay.nodes} == {artifact.node.urn for artifact in plan.artifacts}
    assert sorted((e.target, e.relation.value) for e in overlay.edges) == [
        ("directive:CHANGE_FREEZE", "requires"), ("procedure:incident-runbook", "requires"),
        ("styleguide:incident-notes", "suggests"), ("tactic:verify-rollback", "requires"),
    ]
    merged = merge_project_overlay(existing_overlay=overlay, updated_overlay=overlay)
    assert merged.edges == overlay.edges


def test_editing_references_removes_previous_projected_edges(tmp_path):
    from charter.activation.project_registration import plan_project_registration, commit_project_registration
    paths = author_guidance(tmp_path)
    commit_project_registration(plan_project_registration(tmp_path))
    profile = paths["agent_profile"]
    profile.write_text(profile.read_text().replace("operating-procedures: [incident-runbook]", "operating-procedures: []"))
    plan = plan_project_registration(tmp_path)
    assert all(e.target != "procedure:incident-runbook" for e in plan.graph.edges if e.source == "agent_profile:ops-responder")
    commit_project_registration(plan)
    verify(load_yaml(tmp_path / ".kittify/charter/synthesis-manifest.yaml"), tmp_path)


def test_duplicate_identity_fails_before_bookkeeping_mutation(tmp_path):
    from charter.activation.project_registration import plan_project_registration
    paths = author_guidance(tmp_path)
    duplicate = paths["procedure"].with_name("other.procedure.yaml")
    duplicate.write_bytes(paths["procedure"].read_bytes())
    with pytest.raises(ValueError, match="Duplicate project artifact procedure:incident-runbook"):
        plan_project_registration(tmp_path)
    assert not (tmp_path / ".kittify/charter").exists()


def test_existing_manifest_identity_and_provenance_are_preserved(tmp_path):
    from charter.activation.project_registration import plan_project_registration, commit_project_registration
    from charter.activation.synthesizer.manifest import dump_yaml, finalize_manifest
    from charter.activation.synthesizer.path_guard import PathGuard
    paths = author_guidance(tmp_path)
    commit_project_registration(plan_project_registration(tmp_path))
    manifest_path = tmp_path / ".kittify/charter/synthesis-manifest.yaml"
    manifest = load_yaml(manifest_path)
    original = manifest.artifacts[0]
    renamed = original.model_copy(update={"slug": "original-synthesis-slug"})
    manifest = finalize_manifest(manifest.model_copy(update={"artifacts": [renamed, *manifest.artifacts[1:]]}))
    dump_yaml(manifest, manifest_path, PathGuard(tmp_path))
    sidecar = tmp_path / original.provenance_path
    before = sidecar.read_bytes()
    commit_project_registration(plan_project_registration(tmp_path))
    after = load_yaml(manifest_path)
    assert sorted((a.kind, tmp_path / a.path) for a in after.artifacts) == sorted(paths.items())
    assert after.artifacts[0] == renamed
    assert sidecar.read_bytes() == before
    verify(after, tmp_path)


def test_namespaced_profile_identity_cannot_escape_provenance_directory(tmp_path):
    from charter.activation.project_registration import plan_project_registration, commit_project_registration
    paths = author_guidance(tmp_path)
    profile = paths["agent_profile"]
    profile.write_text(profile.read_text().replace("profile-id: ops-responder", "profile-id: team/ops-responder"))
    plan = plan_project_registration(tmp_path)
    commit_project_registration(plan)
    manifest = load_yaml(tmp_path / ".kittify/charter/synthesis-manifest.yaml")
    entry = next(entry for entry in manifest.artifacts if entry.kind == "agent_profile")
    assert Path(entry.provenance_path).parent == Path(".kittify/charter/provenance")
    assert "team%2Fops-responder" in entry.provenance_path
    verify(manifest, tmp_path)
