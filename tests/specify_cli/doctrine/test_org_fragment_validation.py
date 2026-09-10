"""Public CLI contract: authored org fragments use the runtime loader's schema."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.doctrine import app

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_pack_cli_rejects_graph_node_in_org_fragment(tmp_path: Path) -> None:
    fragment = tmp_path / "drg" / "fragment.yaml"
    fragment.parent.mkdir()
    fragment.write_text(
        "nodes:\n  - urn: directive:ACME-001-FOO\n    kind: directive\nedges: []\n",
        encoding="utf-8",
    )
    result = CliRunner().invoke(app, ["pack", "validate", str(tmp_path), "--json"])
    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert len(payload["errors"]) == 1
    finding = payload["errors"][0]
    assert finding["category"] == "schema_invalid"
    assert finding["artifact_type"] == "drg"
    assert finding["file"] == str(fragment)
    assert "nodes.0.id" in finding["message"]
    assert "unknown kind 'directive'" in finding["message"]


@pytest.mark.parametrize("command", ["pack", "org"])
def test_cli_accepts_minimal_authored_fragment(tmp_path: Path, command: str) -> None:
    fragment = tmp_path / "drg" / "fragment.yaml"
    fragment.parent.mkdir()
    fragment.write_text("nodes:\n  - id: ACME-001-FOO\n    kind: directives\nedges: []\n", encoding="utf-8")
    result = CliRunner().invoke(app, [command, "validate", str(tmp_path)])
    assert result.exit_code == 0, result.output
    from charter.offering.drg.org_pack_loader import load_org_pack

    loaded = load_org_pack(pack_name="test", pack_root=tmp_path, layer_index=1)
    assert [(node.id, node.kind) for node in loaded.nodes] == [("ACME-001-FOO", "directives")]


@pytest.mark.parametrize(
    ("content", "category", "diagnostic"),
    [
        ("nodes: [", "parse_error", "YAML parse error"),
        ("a scalar", "schema_invalid", "mapping"),
        ("[a, list]", "schema_invalid", "mapping"),
        ("[]", "schema_invalid", "mapping"),
        ("false", "schema_invalid", "mapping"),
        ("nodes: null", "schema_invalid", "nodes"),
        ("surprise: true", "schema_invalid", "surprise"),
        ("nodes: [{id: foo, kind: directives, surprise: true}]", "schema_invalid", "surprise"),
        ("nodes: [{id: foo, kind: unknown}]", "schema_invalid", "unknown kind"),
        ("edges: 3", "schema_invalid", "edges"),
        ("edges: {}", "schema_invalid", "edges"),
        ("edges: false", "schema_invalid", "edges"),
        ("edges: ''", "schema_invalid", "edges"),
        ("edges: [{source: foo, target: bar, relation: requires, surprise: true}]", "schema_invalid", "surprise"),
        ("edges: [{source: foo, target: bar, relation: invalid}]", "schema_invalid", "relation"),
    ],
)
def test_malformed_fragments_have_actionable_findings(tmp_path: Path, content: str, category: str, diagnostic: str) -> None:
    from charter.offering.drg.org_pack_loader import OrgPackParseError, OrgPackSchemaError, load_org_pack
    from specify_cli.doctrine.pack_validator import validate_pack

    fragment = tmp_path / "drg" / "fragment.yaml"
    fragment.parent.mkdir()
    fragment.write_text(content, encoding="utf-8")
    expected_error = OrgPackParseError if category == "parse_error" else OrgPackSchemaError
    with pytest.raises(expected_error, match=diagnostic):
        load_org_pack(pack_name="test", pack_root=tmp_path, layer_index=1)
    result = validate_pack(tmp_path, check_drg_root=False)
    assert not result.ok
    assert len(result.errors) == 1
    finding = result.errors[0]
    assert finding.category == category
    assert finding.file == str(fragment)
    assert diagnostic in finding.message
    for command in ("pack", "org"):
        cli = CliRunner().invoke(app, [command, "validate", str(tmp_path)])
        assert cli.exit_code == 1, cli.output
        assert "1 error" in cli.output
        assert diagnostic in cli.output


@pytest.mark.parametrize(
    "content", ["", "{}", "edges: null", "nodes: []\nedges: []", "pack_name: []\nsource_kind: invalid\nsource_ref: null\nlayer_index: invalid"]
)
def test_runtime_normalization_matches_pack_validation(tmp_path: Path, content: str) -> None:
    from charter.offering.drg.org_pack_loader import load_org_pack
    from specify_cli.doctrine.pack_validator import validate_pack

    fragment = tmp_path / "drg" / "fragment.yaml"
    fragment.parent.mkdir()
    fragment.write_text(content, encoding="utf-8")
    loaded = load_org_pack(pack_name="authoritative", pack_root=tmp_path, layer_index=2)
    assert loaded.pack_name == "authoritative"
    assert loaded.layer_index == 2
    assert loaded.source_ref == str(tmp_path)
    assert loaded.source_kind == "local_path"
    assert loaded.nodes == []
    assert loaded.edges == []
    assert validate_pack(tmp_path).ok
    for command in ("pack", "org"):
        cli = CliRunner().invoke(app, [command, "validate", str(tmp_path)])
        assert cli.exit_code == 0, cli.output


def test_fragment_is_optional(tmp_path: Path) -> None:
    from specify_cli.doctrine.pack_validator import validate_pack

    assert validate_pack(tmp_path).ok
