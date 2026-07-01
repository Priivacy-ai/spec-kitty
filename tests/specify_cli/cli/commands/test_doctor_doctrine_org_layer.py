"""Unit tests for ``doctor doctrine`` org-layer section (WP07 / FR-007).

Verifies:
- ``_render_org_layer_section`` prints pack name + node/edge counts for fetched packs.
- ``_render_org_layer_section`` handles OrgPackMissingError gracefully (no crash).
- ``_collect_org_layer_data`` returns structured dict for JSON output.
- ``doctor doctrine`` command includes ``org_drg`` key in ``--json`` output
  when org packs are configured.
- ``doctor doctrine`` does not crash when no org packs are configured.

Per WP07: diagnostic commands are READ-ONLY and must never crash on operator
misconfiguration. All exception paths must produce a usable (non-crashing)
diagnostic output.
"""

from __future__ import annotations

import json
import shutil
from io import StringIO
from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import pytest
from rich.console import Console
from typer.testing import CliRunner

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_REPO_ROOT: Path = Path(__file__).resolve().parents[4]
_FIXTURE_ORG_PACK: Path = (
    _REPO_ROOT
    / "tests"
    / "architectural"
    / "_fixtures"
    / "org_packs"
    / "example_org"
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_repo_with_org_pack(tmp_path: Path) -> Path:
    """Minimal repo with the example_org fixture pack configured (WP06 loader format)."""
    pack_dest = tmp_path / "example_org"
    shutil.copytree(_FIXTURE_ORG_PACK, pack_dest)
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text(
        dedent(
            f"""\
            organisation_packs:
              - name: example-org
                source: local_path
                path: {pack_dest}
            """
        )
    )
    return tmp_path


@pytest.fixture
def tmp_repo_without_org_pack(tmp_path: Path) -> Path:
    """Minimal repo with no org packs configured."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text(
        dedent(
            """\
            agents:
              available:
                - claude
            """
        )
    )
    return tmp_path


# ---------------------------------------------------------------------------
# _render_org_layer_section tests
# ---------------------------------------------------------------------------


def test_render_org_layer_section_shows_pack_counts(
    tmp_repo_with_org_pack: Path,
) -> None:
    """When org pack is configured and fetched, section shows pack name and counts."""
    from specify_cli.cli.commands.doctor import _render_org_layer_section

    buf = StringIO()
    console = Console(file=buf, highlight=False, markup=False)
    _render_org_layer_section(tmp_repo_with_org_pack, console)
    output = buf.getvalue()

    assert "example-org" in output, (
        f"pack name 'example-org' must appear in output: {output!r}"
    )
    # Must show node/edge counts
    assert "nodes" in output or "edges" in output, (
        f"output must show node/edge counts: {output!r}"
    )


def test_render_org_layer_section_no_crash_on_missing_pack(
    tmp_path: Path,
) -> None:
    """When pack path doesn't exist, section renders error message without crashing."""
    from specify_cli.cli.commands.doctor import _render_org_layer_section

    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text(
        dedent(
            """\
            organisation_packs:
              - name: missing-pack
                source: local_path
                path: /nonexistent/path/to/pack
            """
        )
    )

    buf = StringIO()
    console = Console(file=buf, highlight=False, markup=False)
    # Must not raise an exception
    _render_org_layer_section(tmp_path, console)
    output = buf.getvalue()
    # Should mention the error or missing pack
    assert "missing" in output.lower() or "error" in output.lower() or "pack" in output.lower(), (
        f"expected error/missing indication in output: {output!r}"
    )


def test_render_org_layer_section_no_packs_configured(
    tmp_repo_without_org_pack: Path,
) -> None:
    """When no org packs configured, section indicates none configured."""
    from specify_cli.cli.commands.doctor import _render_org_layer_section

    buf = StringIO()
    console = Console(file=buf, highlight=False, markup=False)
    _render_org_layer_section(tmp_repo_without_org_pack, console)
    output = buf.getvalue()

    assert "no organisation packs" in output.lower() or "no packs" in output.lower() or "(no" in output, (
        f"expected 'no packs configured' indication: {output!r}"
    )


# ---------------------------------------------------------------------------
# _collect_org_layer_data tests
# ---------------------------------------------------------------------------


def test_collect_org_layer_data_returns_configured_packs(
    tmp_repo_with_org_pack: Path,
) -> None:
    """Returns structured dict with configured_packs list when packs exist."""
    from specify_cli.cli.commands.doctor import _collect_org_layer_data

    result = _collect_org_layer_data(tmp_repo_with_org_pack)

    assert "configured_packs" in result
    packs = result["configured_packs"]
    assert isinstance(packs, list)
    assert len(packs) == 1
    pack = packs[0]
    assert pack.get("name") == "example-org"
    assert pack.get("fetched") is True
    assert isinstance(pack.get("node_count"), int)
    assert isinstance(pack.get("edge_count"), int)


def test_collect_org_layer_data_empty_packs_when_none_configured(
    tmp_repo_without_org_pack: Path,
) -> None:
    """Returns empty configured_packs when no org packs are in config."""
    from specify_cli.cli.commands.doctor import _collect_org_layer_data

    result = _collect_org_layer_data(tmp_repo_without_org_pack)
    packs = result.get("configured_packs", [])
    assert packs == [], f"expected empty packs list, got: {packs}"


def test_collect_org_layer_data_error_on_missing_pack(
    tmp_path: Path,
) -> None:
    """Returns errors list when pack path doesn't exist."""
    from specify_cli.cli.commands.doctor import _collect_org_layer_data

    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text(
        dedent(
            """\
            organisation_packs:
              - name: ghost-pack
                source: local_path
                path: /nonexistent/path/to/ghost-pack
            """
        )
    )

    result = _collect_org_layer_data(tmp_path)
    errors = result.get("errors", [])
    assert errors, f"expected errors list when pack is missing, got: {result}"


# ---------------------------------------------------------------------------
# CLI integration: doctor doctrine --json includes org_drg key
# ---------------------------------------------------------------------------


def _build_kittify_config_for_test(
    repo_root: Path, pack_path: Path, pack_name: str = "test-pack"
) -> None:
    """Write a minimal .kittify/config.yaml for the doctrine.org.packs schema."""
    config_dir = repo_root / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.yaml").write_text(
        dedent(
            f"""
            doctrine:
              org:
                packs:
                  - name: {pack_name}
                    local_path: {pack_path}
            """
        ).lstrip()
    )


def test_doctor_doctrine_json_includes_org_drg_key_when_packs_configured(
    tmp_repo_with_org_pack: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``doctor doctrine --json`` includes ``org_drg`` key when org packs configured.

    Uses the WP06 ``organisation_packs`` config format (which ``load_org_drg`` reads),
    distinct from the ``doctrine.org.packs`` format (which ``load_pack_registry`` reads).
    The ``org_drg`` key is populated from ``_collect_org_layer_data`` regardless
    of whether ``load_pack_registry`` finds packs.
    """
    from specify_cli.cli.commands.doctor import app as doctor_app

    monkeypatch.chdir(tmp_repo_with_org_pack)

    with patch(
        "specify_cli.cli.commands.doctor.locate_project_root",
        return_value=tmp_repo_with_org_pack,
    ):
        result = runner.invoke(doctor_app, ["doctrine", "--json"])

    # Exit code is always 0 for doctor doctrine (diagnostic only)
    assert result.exit_code == 0, (
        f"doctor doctrine exited with code {result.exit_code}: {result.output}"
    )

    try:
        payload = json.loads(result.output)
    except json.JSONDecodeError as exc:
        pytest.fail(
            f"doctor doctrine --json did not produce valid JSON: {exc}\n"
            f"output: {result.output!r}"
        )

    assert "org_drg" in payload, (
        f"doctor doctrine JSON must include 'org_drg' key. Got keys: {list(payload.keys())}"
    )


def test_doctor_doctrine_json_includes_org_drg_key_when_no_packs(
    tmp_repo_without_org_pack: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``doctor doctrine --json`` includes ``org_drg`` key even when no packs configured."""
    from specify_cli.cli.commands.doctor import app as doctor_app

    monkeypatch.chdir(tmp_repo_without_org_pack)

    with patch(
        "specify_cli.cli.commands.doctor.locate_project_root",
        return_value=tmp_repo_without_org_pack,
    ):
        result = runner.invoke(doctor_app, ["doctrine", "--json"])

    assert result.exit_code == 0, (
        f"doctor doctrine exited with code {result.exit_code}: {result.output}"
    )

    try:
        payload = json.loads(result.output)
    except json.JSONDecodeError as exc:
        pytest.fail(
            f"doctor doctrine --json did not produce valid JSON: {exc}\n"
            f"output: {result.output!r}"
        )

    assert "org_drg" in payload, (
        f"doctor doctrine JSON must always include 'org_drg' key. Got: {list(payload.keys())}"
    )
    org_drg = payload["org_drg"]
    packs = org_drg.get("configured_packs", [])
    assert packs == [], f"expected empty packs when none configured, got: {packs}"
