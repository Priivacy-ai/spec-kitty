"""Project authority must be effectively activated, including its verification procedure."""

from pathlib import Path
from shutil import copytree

import pytest
from ruamel.yaml import YAML

from charter.activation.doctrine_service_builder import build_activation_aware_doctrine_service

ROOT = Path(__file__).resolve().parents[2]
DIRECTIVE = "CLI_HOSTED_BINDING_COMPATIBILITY"
PROCEDURE = "cli-hosted-binding-verification"


def resolved(root):
    service = build_activation_aware_doctrine_service(root)
    directive = service.directives.get(DIRECTIVE)
    procedure = service.procedures.get(PROCEDURE)
    if directive is None or procedure is None:
        raise ValueError("hosted_binding_authority_unavailable")
    return directive, procedure


def test_real_project_resolves_required_binding_authority():
    directive, procedure = resolved(ROOT)
    assert str(directive.enforcement) == "required"
    assert any(reference.id == PROCEDURE for reference in directive.references)
    assert len(procedure.steps) >= 4
    assert "native provider repository ID" in " ".join(directive.integrity_rules)


@pytest.mark.parametrize("mutation", ["inactive_directive", "inactive_procedure", "missing_source"])
def test_actual_activation_consumer_rejects_removed_authority(tmp_path, mutation):
    copytree(ROOT / ".kittify", tmp_path / ".kittify")
    # The org pack is part of this project's real source chain.
    copytree(ROOT / "packs/internal", tmp_path / "packs/internal")
    if mutation == "missing_source":
        (tmp_path / f".kittify/doctrine/directive/{DIRECTIVE}.directive.yaml").unlink()
    else:
        path = tmp_path / ".kittify/charter/charter.yaml"
        yaml = YAML()
        data = yaml.load(path.read_text())
        key, artifact = ("activated_directives", DIRECTIVE) if mutation == "inactive_directive" else ("activated_procedures", PROCEDURE)
        data[key] = [value for value in data[key] if value != artifact]
        with path.open("w") as stream:
            yaml.dump(data, stream)
    with pytest.raises(ValueError, match="hosted_binding_authority_unavailable"):
        resolved(tmp_path)


def test_canonical_owned_context_delivers_hosted_binding_authority():
    import json
    from typer.testing import CliRunner
    from specify_cli.cli.commands.charter import app

    result = CliRunner().invoke(
        app, ["context", "--owned-checkout", str(ROOT), "--action", "implement", "--mission-type", "software-dev", "--json", "--no-mark-loaded"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert DIRECTIVE in {item["id"] for item in payload["all_directives"]}
    assert "governance unresolved" not in payload["context"]
