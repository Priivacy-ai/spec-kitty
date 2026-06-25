"""Direct unit tests for the parsing/validation/emit seam (#2056 WP03, Seam C).

These tests exercise the extracted helpers in
``specify_cli.cli.commands.agent.mission_parsing`` directly, closing the
research §5 gap (the parsers were previously only exercised indirectly via
finalize-tasks). They pin: per-parser well-formed/empty/malformed behavior, the
owned-files validators (incl. explicit-empty-list intent), and the JSON-emit
shims' envelope-key injection (INV-2). Behavior preserved from mission.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.cli.commands.agent import mission_parsing as seam
from specify_cli.status import WPMetadata

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# _extract_wp_ids_from_task_files
# ---------------------------------------------------------------------------


def test_extract_wp_ids_sorted_and_deduped(tmp_path: Path) -> None:
    files = [
        tmp_path / "WP03-foo.md",
        tmp_path / "WP01-bar.md",
        tmp_path / "WP01_baz.md",
        tmp_path / "README.md",
    ]
    assert seam._extract_wp_ids_from_task_files(files) == ["WP01", "WP03"]


def test_extract_wp_ids_empty() -> None:
    assert seam._extract_wp_ids_from_task_files([]) == []


# ---------------------------------------------------------------------------
# _parse_wp_sections_from_tasks_md
# ---------------------------------------------------------------------------


def test_parse_wp_sections_splits_by_heading() -> None:
    content = (
        "# Tasks\n"
        "## WP01: First\nalpha body\n"
        "## WP02 Second\nbeta body\n"
    )
    sections = seam._parse_wp_sections_from_tasks_md(content)
    assert set(sections) == {"WP01", "WP02"}
    assert "alpha body" in sections["WP01"]
    assert "beta body" in sections["WP02"]


def test_parse_wp_sections_empty_when_no_headings() -> None:
    assert seam._parse_wp_sections_from_tasks_md("no work packages here") == {}


# ---------------------------------------------------------------------------
# _parse_dependencies_from_tasks_md
# ---------------------------------------------------------------------------


def test_parse_dependencies_depends_on_phrase() -> None:
    content = "## WP02\nDepends on WP01\n## WP03\nDepends on WP01, WP02\n"
    deps = seam._parse_dependencies_from_tasks_md(content)
    assert deps["WP02"] == ["WP01"]
    assert deps["WP03"] == ["WP01", "WP02"]


def test_parse_dependencies_dependencies_line() -> None:
    content = "## WP02\n**Dependencies**: WP01\n"
    assert seam._parse_dependencies_from_tasks_md(content)["WP02"] == ["WP01"]


def test_parse_dependencies_empty_section() -> None:
    content = "## WP01\nno deps here\n"
    assert seam._parse_dependencies_from_tasks_md(content)["WP01"] == []


# ---------------------------------------------------------------------------
# _parse_requirement_refs_from_tasks_md
# ---------------------------------------------------------------------------


def test_parse_requirement_refs_uppercases_and_dedupes() -> None:
    content = "## WP01\nRequirements: fr-001, NFR-002, FR-001, C-003\n"
    refs = seam._parse_requirement_refs_from_tasks_md(content)
    assert refs["WP01"] == ["FR-001", "NFR-002", "C-003"]


def test_parse_requirement_refs_empty_when_none() -> None:
    content = "## WP01\njust prose\n"
    assert seam._parse_requirement_refs_from_tasks_md(content)["WP01"] == []


# ---------------------------------------------------------------------------
# _parse_requirement_refs_from_wp_files
# ---------------------------------------------------------------------------


def test_parse_requirement_refs_from_wp_files(tmp_path: Path) -> None:
    wp = tmp_path / "WP01-thing.md"
    wp.write_text(
        "---\nwork_package_id: WP01\nrequirement_refs:\n- FR-001\n- C-002\n---\nbody\n",
        encoding="utf-8",
    )
    parsed = seam._parse_requirement_refs_from_wp_files([wp])
    assert parsed["WP01"] == ["FR-001", "C-002"]


def test_parse_requirement_refs_from_wp_files_skips_non_wp(tmp_path: Path) -> None:
    other = tmp_path / "notes.md"
    other.write_text("nothing", encoding="utf-8")
    assert seam._parse_requirement_refs_from_wp_files([other]) == {}


def test_parse_requirement_refs_from_wp_files_malformed_yields_empty(tmp_path: Path) -> None:
    wp = tmp_path / "WP01-broken.md"
    wp.write_text("not even frontmatter", encoding="utf-8")
    parsed = seam._parse_requirement_refs_from_wp_files([wp])
    assert parsed.get("WP01") == []


# ---------------------------------------------------------------------------
# _parse_requirement_ids_from_spec_md
# ---------------------------------------------------------------------------


def test_parse_requirement_ids_from_spec_md_delegates() -> None:
    spec = "- **FR-001**: do a thing\n- **NFR-002**: be fast\n"
    result = seam._parse_requirement_ids_from_spec_md(spec)
    assert isinstance(result, dict)
    # The pure delegate groups requirement IDs; FR-001 must surface somewhere.
    flat = {ref for refs in result.values() for ref in refs} | set(result)
    assert any("FR-001" in str(v) for v in [*flat, *result])


# ---------------------------------------------------------------------------
# Owned-files validators
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  ./src/a.py  ", "src/a.py"),
        ("src\\b.py", "src/b.py"),
        ("././x", "x"),
    ],
)
def test_normalize_owned_file_path(raw: str, expected: str) -> None:
    assert seam._normalize_owned_file_path(raw) == expected


def test_is_mission_specs_owned_file_true() -> None:
    assert seam._is_mission_specs_owned_file("kitty-specs/foo/spec.md") is True
    assert seam._is_mission_specs_owned_file("kitty-specs") is True


def test_is_mission_specs_owned_file_false() -> None:
    assert seam._is_mission_specs_owned_file("src/a.py") is False


def test_owned_files_explicit_empty_list_true() -> None:
    raw = "---\nwork_package_id: WP01\nowned_files: []\n---\nbody\n"
    assert seam._owned_files_yaml_is_explicit_empty_list(raw) is True


def test_owned_files_explicit_empty_list_false_when_populated() -> None:
    raw = "---\nwork_package_id: WP01\nowned_files:\n- src/a.py\n---\nbody\n"
    assert seam._owned_files_yaml_is_explicit_empty_list(raw) is False


def test_owned_files_explicit_empty_list_false_no_frontmatter() -> None:
    assert seam._owned_files_yaml_is_explicit_empty_list("no frontmatter") is False


def test_raw_frontmatter_has_field_true_false() -> None:
    raw = "---\nwork_package_id: WP01\nassignee: bob\n---\nbody\n"
    assert seam._raw_frontmatter_has_field(raw, "assignee") is True
    assert seam._raw_frontmatter_has_field(raw, "missing_field") is False


def test_raw_frontmatter_has_field_no_frontmatter() -> None:
    assert seam._raw_frontmatter_has_field("plain text", "anything") is False


def test_invalid_mission_specs_owned_files_flags_planning_paths() -> None:
    by_wp = {
        "WP01": WPMetadata(
            work_package_id="WP01",
            owned_files=["kitty-specs/foo/spec.md", "src/ok.py"],
        ),
        "WP02": WPMetadata(work_package_id="WP02", owned_files=["src/clean.py"]),
    }
    invalid = seam._invalid_mission_specs_owned_files(by_wp)
    assert invalid == [{"wp_id": "WP01", "path": "kitty-specs/foo/spec.md"}]


def test_invalid_owned_files_dynamic_alias_is_same_callable() -> None:
    """The ``_invalid_kitty_specs_owned_files`` alias preserves the patch target."""
    # The alias is created dynamically (globals()[...]), so resolve it via the
    # module namespace rather than static attribute access.
    alias = vars(seam)["_invalid_kitty_specs_owned_files"]
    assert alias is seam._invalid_mission_specs_owned_files


# ---------------------------------------------------------------------------
# JSON-emit shims
# ---------------------------------------------------------------------------


def test_with_cli_version_injects_when_absent() -> None:
    enriched = seam._with_cli_version({"result": "ok"})
    assert "spec_kitty_version" in enriched
    assert enriched["result"] == "ok"


def test_with_cli_version_idempotent_when_present() -> None:
    payload = {"result": "ok", "spec_kitty_version": "custom"}
    assert seam._with_cli_version(payload) is payload
    assert payload["spec_kitty_version"] == "custom"


def test_with_mission_aliases_returns_copy() -> None:
    payload = {"a": 1}
    out = seam._with_mission_aliases(payload)
    assert out == payload
    assert out is not payload


def test_emit_json_emits_single_object_with_version(capsys: pytest.CaptureFixture[str]) -> None:
    seam._emit_json({"result": "success"})
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["result"] == "success"
    assert "spec_kitty_version" in parsed


def test_emit_console_or_json_error_json_mode(capsys: pytest.CaptureFixture[str]) -> None:
    seam._emit_console_or_json_error(json_output=True, message="boom")
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["error"] == "boom"


def test_emit_console_or_json_error_human_mode(capsys: pytest.CaptureFixture[str]) -> None:
    seam._emit_console_or_json_error(json_output=False, message="boom-human")
    captured = capsys.readouterr()
    assert "boom-human" in captured.out
    # Human mode is NOT valid JSON (it is a Rich-rendered line).
    with pytest.raises(json.JSONDecodeError):
        json.loads(captured.out)


# ---------------------------------------------------------------------------
# _utc_now_iso
# ---------------------------------------------------------------------------


def test_utc_now_iso_format() -> None:
    value = seam._utc_now_iso()
    # Deterministic shape: YYYY-MM-DDTHH:MM:SSZ
    assert len(value) == 20
    assert value.endswith("Z")
    assert value[4] == "-" and value[10] == "T"
