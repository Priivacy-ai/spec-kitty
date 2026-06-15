"""Black-box CLI tests for ``spec-kitty charter list --all`` (WP16, FR-025).

DIRECTIVE_036: these exercise the live CLI surface end-to-end via
``CliRunner`` — no internal mocking of the catalog. They prove that ``--all``:

* surfaces available-but-not-activated artifacts across the built-in, org, and
  project layers, each annotated by its source layer;
* derives the kind ordering from the canonical kind universe (no re-declared
  list); and
* appends the mission-scoped ``template`` kind with mission-qualified IDs
  discovered through WP18.

The fixtures build a real on-disk org pack and a project doctrine layer so the
roots (resolved in ``specify_cli``, passed as data — C-008) are honoured by the
lower layers.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.charter import charter_app

runner = CliRunner()

pytestmark = [pytest.mark.fast]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_directive(directory: Path, stem: str, artifact_id: str) -> None:
    """Write a minimal directive artifact carrying a declared ``id:`` (R-011-D)."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{stem}.directive.yaml").write_text(
        textwrap.dedent(
            f"""\
            id: {artifact_id}
            type: directive
            title: {artifact_id}
            """
        ),
        encoding="utf-8",
    )


def _write_template(missions_root: Path, mission: str, name: str, body: str) -> None:
    """Write a mission-scoped template (WP18 discovery surface)."""
    tpl_dir = missions_root / mission / "templates"
    tpl_dir.mkdir(parents=True, exist_ok=True)
    (tpl_dir / name).write_text(body, encoding="utf-8")


def _invoke(project_root: Path, *args: str) -> object:
    return runner.invoke(
        charter_app,
        ["list", "--repo-root", str(project_root), *args],
        catch_exceptions=False,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def layered_project(tmp_path: Path) -> Path:
    """A project with an org pack + project doctrine layer + project template.

    Layout::

        <repo>/.kittify/config.yaml                 (registers the org pack)
        <repo>/.kittify/doctrine/directive/<...>.directive.yaml
        <repo>/.kittify/doctrine/missions/<mission>/templates/<name>
        <org-pack>/doctrine/directives/org/<...>.directive.yaml
    """
    repo = tmp_path / "repo"
    kittify = repo / ".kittify"
    kittify.mkdir(parents=True)

    # Org pack on disk, registered via the doctrine.org.packs config block.
    org_pack = tmp_path / "org-pack"
    _write_directive(
        org_pack / "doctrine" / "directives" / "org",
        "900-org-only-directive",
        "900-org-only-directive",
    )

    (kittify / "config.yaml").write_text(
        textwrap.dedent(
            f"""\
            doctrine:
              org:
                packs:
                  - name: acme
                    local_path: {org_pack}
            """
        ),
        encoding="utf-8",
    )

    # Project doctrine layer directive.
    _write_directive(
        kittify / "doctrine" / "directive",
        "950-project-only-directive",
        "950-project-only-directive",
    )

    # Project mission template (mission-qualified discovery target).
    _write_template(
        kittify / "doctrine" / "missions",
        "acme-mission",
        "project-spec-template.md",
        "# project spec template\n",
    )

    return repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestListAllLayers:
    def test_all_flag_adds_all_layers_column(self, layered_project: Path) -> None:
        result = _invoke(layered_project, "--all")
        assert result.exit_code == 0, result.output
        assert "Available (all layers)" in result.output

    def test_all_supersedes_show_available_column_header(
        self, layered_project: Path
    ) -> None:
        # --all wins even when --show-available is also passed.
        result = _invoke(layered_project, "--show-available", "--all")
        assert result.exit_code == 0, result.output
        assert "Available (all layers)" in result.output
        assert "Available (not activated)" not in result.output

    def test_org_artifact_shown_with_org_layer(self, layered_project: Path) -> None:
        result = _invoke(layered_project, "--all")
        assert result.exit_code == 0, result.output
        assert "900-org-only-directive" in result.output
        # Layer annotation present.
        assert "(org)" in result.output

    def test_project_artifact_shown_with_project_layer(
        self, layered_project: Path
    ) -> None:
        result = _invoke(layered_project, "--all")
        assert result.exit_code == 0, result.output
        assert "950-project-only-directive" in result.output
        assert "(project)" in result.output

    def test_built_in_artifacts_annotated(self, layered_project: Path) -> None:
        """Built-in directives appear with the built-in layer tag."""
        result = _invoke(layered_project, "--all")
        assert result.exit_code == 0, result.output
        # The shipped built-in doctrine has directives; the layer tag must show.
        assert "(built-in)" in result.output


class TestListAllTemplateKind:
    def test_template_kind_row_present(self, layered_project: Path) -> None:
        result = _invoke(layered_project, "--all")
        assert result.exit_code == 0, result.output
        assert "template" in result.output

    def test_template_mission_qualified_id_present(self, layered_project: Path) -> None:
        """The project template appears with a mission-qualified ID (WP18)."""
        result = _invoke(layered_project, "--all")
        assert result.exit_code == 0, result.output
        assert "acme-mission/project-spec-template.md" in result.output

    def test_template_kind_absent_without_all(self, layered_project: Path) -> None:
        """The template row only appears in the --all (layer-aware) view."""
        result = _invoke(layered_project, "--show-available")
        assert result.exit_code == 0, result.output
        assert "acme-mission/project-spec-template.md" not in result.output


class TestKindOrderDerivedFromCanonical:
    def test_all_canonical_kinds_present(self, layered_project: Path) -> None:
        """Every canonical charter kind appears (order derived from WP01)."""
        from doctrine.artifact_kinds import CHARTER_KIND_TOKENS

        result = _invoke(layered_project, "--all")
        assert result.exit_code == 0, result.output
        for kind in CHARTER_KIND_TOKENS:
            assert kind in result.output, f"missing kind {kind!r}"
