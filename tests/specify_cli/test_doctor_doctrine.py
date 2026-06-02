"""WP08 — ``doctor doctrine`` health report tests (FR-008/009/010, NFR-001).

Covers:
- ``PackHealth`` / ``DoctrineHealthReport`` derived health (I-H1 / FR-010):
  ``healthy = (valid_count == discovered_count) and not invalid_profiles``.
- ``to_dict()`` emits stable invalid-profile fields
  (layer/path/profile_id/error_summary) as a passthrough of ``SkippedProfile``.
- A pack with an invalid profile reports ``healthy=false`` even when DRG counts
  are valid (the old false-healthy snapshot-presence bug).
- Human + JSON surfaces both derive from one report (no parallel assembly).
- ≤2s wall-clock budget on built-in + one project-layer profile (NFR-001).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from doctrine.agent_profiles.diagnostics import SkippedProfile
from specify_cli.cli.commands._doctrine_health import (
    DoctrineHealthReport,
    PackHealth,
    build_pack_health_by_layer,
)

pytestmark = [pytest.mark.unit]

runner = CliRunner()


# ---------------------------------------------------------------------------
# T034 — PackHealth / DoctrineHealthReport derived health + stable fields
# ---------------------------------------------------------------------------


def test_pack_health_healthy_when_all_valid() -> None:
    pack = PackHealth(
        pack_id="builtin", layer="builtin", discovered_count=3, valid_count=3
    )
    assert pack.healthy is True


def test_pack_health_degraded_when_counts_mismatch() -> None:
    pack = PackHealth(
        pack_id="org", layer="org", discovered_count=2, valid_count=1
    )
    assert pack.healthy is False


def test_pack_health_degraded_when_invalid_profiles_present() -> None:
    """I-H1: invalid profiles force degraded even if counts happened to match."""
    skipped = SkippedProfile(
        layer="org",
        path="/packs/org/agent_profiles/bad.yaml",
        profile_id="broken-bart",
        error_summary="schema invalid",
    )
    # Construct an inconsistent-but-defensive case: counts equal yet an invalid
    # profile is attached. Health must still be False.
    pack = PackHealth(
        pack_id="org",
        layer="org",
        discovered_count=1,
        valid_count=1,
        invalid_profiles=[skipped],
    )
    assert pack.healthy is False


def test_pack_health_to_dict_emits_stable_invalid_profile_fields() -> None:
    skipped = SkippedProfile(
        layer="project",
        path="/repo/.kittify/doctrine/agent_profiles/bad.yaml",
        profile_id="broken-bart",
        error_summary="Missing required field 'identity'",
    )
    pack = PackHealth(
        pack_id="project",
        layer="project",
        discovered_count=2,
        valid_count=1,
        invalid_profiles=[skipped],
    )
    out = pack.to_dict()
    assert out["layer"] == "project"
    assert out["discovered_count"] == 2
    assert out["valid_count"] == 1
    assert out["healthy"] is False
    assert out["invalid_profiles"] == [
        {
            "layer": "project",
            "path": "/repo/.kittify/doctrine/agent_profiles/bad.yaml",
            "profile_id": "broken-bart",
            "error_summary": "Missing required field 'identity'",
        }
    ]


def test_report_healthy_only_when_every_pack_healthy() -> None:
    healthy = PackHealth("builtin", "builtin", 2, 2)
    degraded = PackHealth(
        "org",
        "org",
        2,
        1,
        invalid_profiles=[
            SkippedProfile("org", "/p/bad.yaml", None, "YAML error")
        ],
    )
    assert DoctrineHealthReport(packs=[healthy]).healthy is True
    assert DoctrineHealthReport(packs=[healthy, degraded]).healthy is False


def test_report_to_dict_is_single_json_shape() -> None:
    skipped = SkippedProfile("org", "/p/bad.yaml", "x", "boom")
    report = DoctrineHealthReport(
        packs=[PackHealth("org", "org", 2, 1, invalid_profiles=[skipped])],
        org_drg={"configured_packs": [], "errors": []},
    )
    out = report.to_dict()
    assert out["healthy"] is False
    assert out["org_drg"] == {"configured_packs": [], "errors": []}
    assert out["packs"][0]["invalid_profiles"][0]["error_summary"] == "boom"
    # JSON-serialisable end to end.
    assert json.loads(json.dumps(out))["packs"][0]["healthy"] is False


def test_build_pack_health_groups_by_layer() -> None:
    skipped = [
        SkippedProfile("org", "/p/org/bad.yaml", "broken", "schema invalid"),
        SkippedProfile("project", "/p/proj/empty.yaml", None, "empty file"),
    ]
    packs = build_pack_health_by_layer(
        provenance_by_layer={"builtin": 5, "org": 2},
        skipped_profiles=skipped,
    )
    by_layer = {p.layer: p for p in packs}
    # builtin: 5 valid, 0 invalid → healthy
    assert by_layer["builtin"].discovered_count == 5
    assert by_layer["builtin"].healthy is True
    # org: 2 valid + 1 invalid = 3 discovered → degraded
    assert by_layer["org"].discovered_count == 3
    assert by_layer["org"].valid_count == 2
    assert by_layer["org"].healthy is False
    # project: 0 valid + 1 invalid → degraded, surfaced even with no valid load
    assert by_layer["project"].discovered_count == 1
    assert by_layer["project"].healthy is False
    # Layer ordering is builtin, org, project.
    assert [p.layer for p in packs] == ["builtin", "org", "project"]


def test_build_pack_health_omits_empty_layers() -> None:
    packs = build_pack_health_by_layer(
        provenance_by_layer={"builtin": 4},
        skipped_profiles=[],
    )
    assert [p.layer for p in packs] == ["builtin"]


# ---------------------------------------------------------------------------
# Integration fixtures: project-layer doctrine with a valid + invalid profile
# ---------------------------------------------------------------------------


_VALID_PROFILE = dedent(
    """\
    profile-id: tester-tina
    name: Tester Tina
    roles:
      - reviewer
    purpose: A test specialist profile used by the WP08 doctor-doctrine suite.
    specialization:
      primary-focus: Testing the doctrine health report.
      secondary-awareness: Diagnostics.
      avoidance-boundary: Production code.
      success-definition: The health report renders.
    """
)

# A profile file that declares a profile-id but is missing required fields and
# uses the wrong type for ``roles``, so the repository skips it as a
# ValidationError (FR-008/009 invalid profile).
_INVALID_PROFILE = dedent(
    """\
    profile-id: broken-bart
    roles: "not-a-list-but-a-string"
    """
)


@pytest.fixture
def repo_with_invalid_project_profile(tmp_path: Path) -> Path:
    """Repo whose project doctrine layer contains one invalid agent profile."""
    profiles_dir = tmp_path / ".kittify" / "doctrine" / "agent_profiles"
    profiles_dir.mkdir(parents=True)
    (profiles_dir / "tester-tina.agent.yaml").write_text(
        _VALID_PROFILE, encoding="utf-8"
    )
    (profiles_dir / "broken-bart.agent.yaml").write_text(
        _INVALID_PROFILE, encoding="utf-8"
    )
    kittify = tmp_path / ".kittify"
    (kittify / "config.yaml").write_text(
        "agents:\n  available:\n    - claude\n", encoding="utf-8"
    )
    return tmp_path


def test_collect_profile_health_surfaces_invalid_project_profile(
    repo_with_invalid_project_profile: Path,
) -> None:
    """``_collect_profile_health`` reads ``skipped_profiles()`` (no regex scrape)."""
    from specify_cli.cli.commands.doctor import _collect_profile_health

    report = _collect_profile_health(repo_with_invalid_project_profile)
    project_packs = [p for p in report.packs if p.layer == "project"]
    assert project_packs, "expected a project-layer PackHealth"
    project = project_packs[0]
    assert project.invalid_profiles, "broken-bart must be surfaced as invalid"
    bad = project.invalid_profiles[0]
    assert bad.layer == "project"
    assert bad.path.endswith("broken-bart.agent.yaml")
    # FR-010: present-but-broken layer is NOT healthy.
    assert project.healthy is False
    assert report.healthy is False


def test_doctor_doctrine_json_reports_false_healthy_fixed(
    repo_with_invalid_project_profile: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-010: ``--json`` reports ``healthy=false`` for an invalid profile.

    Even though no org pack is configured (valid DRG counts), the presence of
    an invalid project profile must degrade the report — the old code greened
    on snapshot presence.
    """
    from specify_cli.cli.commands.doctor import app as doctor_app

    monkeypatch.chdir(repo_with_invalid_project_profile)
    with patch(
        "specify_cli.cli.commands.doctor.locate_project_root",
        return_value=repo_with_invalid_project_profile,
    ):
        result = runner.invoke(doctor_app, ["doctrine", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert "profile_health" in payload
    health = payload["profile_health"]
    assert health["healthy"] is False
    project_packs = [p for p in health["packs"] if p["layer"] == "project"]
    assert project_packs and project_packs[0]["healthy"] is False
    invalid = project_packs[0]["invalid_profiles"]
    assert invalid, "invalid_profiles must be populated"
    # Stable fields present.
    assert set(invalid[0]) == {"layer", "path", "profile_id", "error_summary"}
    assert invalid[0]["profile_id"] == "broken-bart"


def test_doctor_doctrine_human_renders_degraded_pack_and_invalid_profiles(
    repo_with_invalid_project_profile: Path,
) -> None:
    """Human render shows a degraded pack header + invalid profiles by layer/path/error.

    Drives the human renderer (``_render_doctrine_pack``) from the same
    ``DoctrineHealthReport`` the JSON surface uses (T035/T036 validation): a
    present snapshot whose profiles failed to load renders *degraded*, not green.
    """
    from io import StringIO

    from rich.console import Console
    from specify_cli.cli.commands import doctor as doctor_mod

    report = doctor_mod._collect_profile_health(repo_with_invalid_project_profile)
    assert report.healthy is False
    project_pack = next(p for p in report.packs if p.layer == "project")

    # Simulate a present org snapshot annotated with the degraded layer health,
    # exactly as ``_attach_pack_health`` does for the live command.
    entry: dict[str, object] = {
        "name": "example-org",
        "local_path": "/packs/example-org",
        "snapshot_present": True,
        "pack_version": "1.0",
        "is_git_pack": False,
        "artifact_counts": {"agent_profiles": 2},
        "pack_health": project_pack.to_dict(),
    }

    buf = StringIO()
    original = doctor_mod.console
    doctor_mod.console = Console(file=buf, highlight=False, markup=True)
    try:
        doctor_mod._render_doctrine_pack(entry, 0)
    finally:
        doctor_mod.console = original
    output = buf.getvalue()

    assert "degraded" in output, output
    assert "invalid profiles" in output, output
    assert "broken-bart.agent.yaml" in output, output
    assert "(project)" in output, output


def test_doctor_doctrine_human_and_json_share_one_report(
    repo_with_invalid_project_profile: Path,
) -> None:
    """Human + JSON derive from the same DoctrineHealthReport (no parallel assembly)."""
    from specify_cli.cli.commands import doctor as doctor_mod

    calls: list[int] = []
    real = doctor_mod._collect_profile_health

    def _counting(repo_root: Path) -> DoctrineHealthReport:
        calls.append(1)
        return real(repo_root)

    with patch.object(doctor_mod, "_collect_profile_health", _counting), patch.object(
        doctor_mod, "locate_project_root", return_value=repo_with_invalid_project_profile
    ):
        result = runner.invoke(doctor_mod.app, ["doctrine", "--json"])
    assert result.exit_code == 0, result.output
    # The report is built exactly once per invocation (single source).
    assert calls == [1]


# ---------------------------------------------------------------------------
# T038 — NFR-001: ≤2s on built-in + one project-layer profile
# ---------------------------------------------------------------------------


def test_doctor_doctrine_within_two_second_budget(
    repo_with_invalid_project_profile: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NFR-001: report build stays well under the 2s budget (generous margin)."""
    from specify_cli.cli.commands.doctor import _collect_profile_health

    monkeypatch.chdir(repo_with_invalid_project_profile)
    start = time.perf_counter()
    _collect_profile_health(repo_with_invalid_project_profile)
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0, f"report build exceeded 2s budget: {elapsed:.3f}s"
