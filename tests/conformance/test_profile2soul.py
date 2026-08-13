"""Unit tests for ``conformance/tools/profile2soul.py`` (M7 / WP01, HIGH-2 remediation).

``conformance/tools`` is not an importable package (no ``pyproject.toml``
entry, and ``pytest.ini``'s ``pythonpath = src`` deliberately does not add
it), so the module under test is loaded by file path, mirroring
``tests/ci/test_sonar_project_version.py``.

Coverage (per the HIGH-2 remediation instructions):

- determinism: two ``project()`` calls against the same source file are
  byte-identical (FR-001's own determinism contract);
- the field mapping: every FR-001-carried field lands in its documented
  body section, verbatim;
- ``_require`` raises loudly (never defaults silently) on a missing field;
- the module's ``FABRICATED_*`` constants match ``PROJECTION.md``'s
  Fabricated Defaults table byte-for-byte, so the two hand-synced tables
  this script's own docstring warns about cannot silently drift apart;
- the generated-header shape (``^#.*generated:\\s*true``) that C-003's
  audit anchor depends on.

Note on ATDD ordering (C-011): this module is a **documented one-time
deviation** from red-green-refactor — it was authored after WP01's
implementation commit landed, not before, as part of a post-review
remediation. See this WP's Activity Log for the full explanation and the
red/green demonstration performed against a throwaway clone in lieu of a
reconstructed commit history.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "conformance" / "tools" / "profile2soul.py"
_PROJECTION_MD = _REPO_ROOT / "conformance" / "tools" / "PROJECTION.md"
#: Built-in agent profiles live under ``packs/built-in/`` since the doctrine-pack
#: layout move; the old ``src/doctrine/agent_profiles/built-in/`` path no longer
#: exists. This mission's own final commit repointed the PROJECTION.md path
#: labels at ``packs/built-in`` but missed this constant, so the test read a
#: path that is simply absent and died on FileNotFoundError rather than on
#: anything about the projection it exists to check.
_ARCHITECT_PROFILE = _REPO_ROOT / "packs" / "built-in" / "agent_profiles" / "architect-alphonso.agent.yaml"

_GENERATED_HEADER_PATTERN = re.compile(r"^#.*generated:\s*true")


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("profile2soul", _SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot build an import spec for {_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def module() -> ModuleType:
    return _load_module()


def _write_profile(tmp_path: Path, body: str, *, name: str = "profile.agent.yaml") -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


_FULL_PROFILE_YAML = """\
profile-id: test-persona
name: Test Persona
description: A test persona for unit coverage.
purpose: >
  Exercise every carried field of the projector.
specialization:
  primary-focus: Testing the projector's field mapping
  avoidance-boundary: Anything not related to this test
initialization-declaration: >
  I am Test Persona. I exist only to exercise profile2soul.py.
"""


# ---------------------------------------------------------------------------
# Determinism (FR-001)
# ---------------------------------------------------------------------------


def test_project_is_byte_identical_across_repeated_calls(module: ModuleType, tmp_path: Path) -> None:
    source = _write_profile(tmp_path, _FULL_PROFILE_YAML)
    first = module.project(source)
    second = module.project(source)
    assert first == second


def test_project_is_byte_identical_against_real_builtin_profile(module: ModuleType) -> None:
    first = module.project(_ARCHITECT_PROFILE)
    second = module.project(_ARCHITECT_PROFILE)
    assert first == second


# ---------------------------------------------------------------------------
# Field mapping (FR-001 step 1 / PROJECTION.md's "Field Mapping" table)
# ---------------------------------------------------------------------------


def test_carried_fields_land_in_their_documented_body_sections(module: ModuleType, tmp_path: Path) -> None:
    source = _write_profile(tmp_path, _FULL_PROFILE_YAML)
    output = module.project(source)

    # Front matter: profile-id -> id, name -> name.
    assert "id: test-persona" in output
    assert "name: Test Persona" in output

    # Body: top-level heading is the profile's name.
    assert "\n# Test Persona\n" in output

    # Body sections, each carried verbatim (whitespace-stripped).
    assert "## Identity Declaration\n\nI am Test Persona. I exist only to exercise profile2soul.py." in output
    assert "## Purpose\n\nExercise every carried field of the projector." in output
    assert "## Description\n\nA test persona for unit coverage." in output
    assert "### Primary Focus\n\nTesting the projector's field mapping" in output
    assert "### Avoidance Boundary\n\nAnything not related to this test" in output


def test_carried_fields_never_appear_fabricated(module: ModuleType, tmp_path: Path) -> None:
    """The six carried fields must never be silently replaced by a fabricated default."""
    source = _write_profile(tmp_path, _FULL_PROFILE_YAML)
    output = module.project(source)
    assert "test-persona" in output  # the real id, not a placeholder
    assert module.FABRICATED_LOCALE == "en-US"  # sanity: fabrication is a separate path
    assert "locale: en-US" in output  # locale IS fabricated -- expected, distinct from carried fields


# ---------------------------------------------------------------------------
# ``_require`` raises loudly on a missing field
# ---------------------------------------------------------------------------


def test_require_raises_keyerror_on_missing_field(module: ModuleType, tmp_path: Path) -> None:
    profile = {"name": "Incomplete Persona"}
    with pytest.raises(KeyError, match="profile-id"):
        module._require(profile, "profile-id", tmp_path / "incomplete.agent.yaml")


def test_require_raises_keyerror_on_none_value(module: ModuleType, tmp_path: Path) -> None:
    profile = {"profile-id": None}
    with pytest.raises(KeyError, match="profile-id"):
        module._require(profile, "profile-id", tmp_path / "incomplete.agent.yaml")


def test_require_raises_typeerror_on_non_string_value(module: ModuleType, tmp_path: Path) -> None:
    profile = {"profile-id": 12345}
    with pytest.raises(TypeError, match="profile-id"):
        module._require(profile, "profile-id", tmp_path / "wrong-type.agent.yaml")


def test_require_nested_raises_keyerror_when_parent_section_missing(module: ModuleType, tmp_path: Path) -> None:
    profile: dict[str, object] = {"name": "Incomplete Persona"}
    with pytest.raises(KeyError, match="specialization"):
        module._require_nested(profile, "specialization", "primary-focus", tmp_path / "incomplete.agent.yaml")


def test_project_raises_on_source_profile_missing_a_required_field(module: ModuleType, tmp_path: Path) -> None:
    incomplete_yaml = """\
profile-id: incomplete-persona
name: Incomplete Persona
description: Missing purpose and specialization.
"""
    source = _write_profile(tmp_path, incomplete_yaml, name="incomplete.agent.yaml")
    with pytest.raises(KeyError):
        module.project(source)


def test_main_reports_exit_1_on_malformed_source(module: ModuleType, tmp_path: Path) -> None:
    incomplete_yaml = "profile-id: incomplete-persona\nname: Incomplete Persona\n"
    source = _write_profile(tmp_path, incomplete_yaml, name="incomplete.agent.yaml")
    exit_code = module.main([str(_SCRIPT_PATH), str(source)])
    assert exit_code == 1


def test_main_reports_exit_2_on_usage_error(module: ModuleType) -> None:
    assert module.main([str(_SCRIPT_PATH)]) == 2


def test_main_reports_exit_2_when_source_path_is_not_a_file(module: ModuleType, tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.agent.yaml"
    assert module.main([str(_SCRIPT_PATH), str(missing)]) == 2


# ---------------------------------------------------------------------------
# Fabricated defaults must match PROJECTION.md's own table (drift guard)
# ---------------------------------------------------------------------------


def _extract_fabricated_defaults_table(projection_md: Path) -> dict[str, str]:
    """Parse PROJECTION.md's ``## Fabricated Defaults`` markdown table into a
    ``{field: frozen_value}`` mapping, keyed by the field's exact `code`-span
    text (e.g. ``voice.formality``) and valued by its `code`-span frozen
    value (e.g. ``50`` or ``en-US``).
    """
    text = projection_md.read_text(encoding="utf-8")
    match = re.search(r"^## Fabricated Defaults\b(.*?)(?=^## )", text, re.MULTILINE | re.DOTALL)
    assert match is not None, "PROJECTION.md must have a '## Fabricated Defaults' section"
    section = match.group(1)

    row_pattern = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`", re.MULTILINE)
    rows = row_pattern.findall(section)
    assert rows, "expected at least one fabricated-defaults table row"
    return dict(rows)


def test_fabricated_defaults_table_matches_projection_md(module: ModuleType) -> None:
    documented = _extract_fabricated_defaults_table(_PROJECTION_MD)

    # PROJECTION.md documents this field with its literal quoting (`"1.0"`),
    # matching the YAML front matter's rendered form; strip the quotes to
    # compare against the module's bare constant.
    assert documented["soul_spec"].strip('"') == module.FABRICATED_SOUL_SPEC
    assert documented["locale"] == module.FABRICATED_LOCALE
    assert documented["composition.merge_policy"] == module.FABRICATED_COMPOSITION_MERGE_POLICY
    assert documented["voice.formatting"] == module.FABRICATED_VOICE_FORMATTING

    for key, expected in module.FABRICATED_VOICE.items():
        assert documented[f"voice.{key}"] == str(expected)

    for key, expected in module.FABRICATED_INTERACTION.items():
        assert documented[f"interaction.{key}"] == expected

    for key, expected in module.FABRICATED_SAFETY.items():
        assert documented[f"safety.{key}"] == expected

    quoted_profiles = ", ".join(f'"{name}"' for name in module.FABRICATED_PROFILES)
    assert documented["profiles"] == f"[{quoted_profiles}]"


def test_fabricated_defaults_table_key_set_matches_constants(module: ModuleType) -> None:
    """LOW-2 (M7 WP01 review round 2): the assertions above only look up each
    known constant *inside* the parsed table (one-directional) -- a brand
    new row added to ``PROJECTION.md`` with no matching constant would pass
    every assertion above silently. Assert the two key sets are equal so an
    addition with no backing constant (or hardcoded literal, for the fields
    that intentionally have none -- ``composition.extends``/``.mixins``,
    ``profile_overrides``, ``values.priorities``, ``extensions``) fails
    loudly, the same way a rename/value-change/deletion already does.
    """
    documented = _extract_fabricated_defaults_table(_PROJECTION_MD)
    expected_keys = (
        {"soul_spec", "locale"}
        | {"composition.extends", "composition.mixins", "composition.merge_policy"}
        | {"profiles", "profile_overrides"}
        | {"values.priorities"}
        | {f"voice.{key}" for key in module.FABRICATED_VOICE}
        | {"voice.formatting"}
        | {f"interaction.{key}" for key in module.FABRICATED_INTERACTION}
        | {f"safety.{key}" for key in module.FABRICATED_SAFETY}
        | {"extensions"}
    )
    assert set(documented.keys()) == expected_keys


def test_fabricated_output_matches_frozen_constants(module: ModuleType, tmp_path: Path) -> None:
    source = _write_profile(tmp_path, _FULL_PROFILE_YAML)
    output = module.project(source)
    assert f'soul_spec: "{module.FABRICATED_SOUL_SPEC}"' in output
    assert f"locale: {module.FABRICATED_LOCALE}" in output
    assert f"  merge_policy: {module.FABRICATED_COMPOSITION_MERGE_POLICY}" in output
    quoted_profiles = ", ".join(f'"{name}"' for name in module.FABRICATED_PROFILES)
    assert f"profiles: [{quoted_profiles}]" in output
    for key, value in module.FABRICATED_VOICE.items():
        assert f"  {key}: {value}" in output
    assert f"  formatting: {module.FABRICATED_VOICE_FORMATTING}" in output
    for key, value in module.FABRICATED_INTERACTION.items():
        assert f"  {key}: {value}" in output
    for key, value in module.FABRICATED_SAFETY.items():
        assert f"  {key}: {value}" in output
    for field in module.FABRICATED_EMPTY_OBJECT_FIELDS:
        assert f"{field}: {{}}" in output


# ---------------------------------------------------------------------------
# Generated-header shape (C-003's textual-audit anchor) and RFC-1 Section
# 3.1.1's opening-delimiter requirement (the WP01 remediation
# tests/cross_cutting/test_crosslayer_wp01_persona_rfc1_conformance.py
# exists to guard end-to-end against muster's real parser — relocated there
# from tests/conformance/ so it is actually selected by a CI gate; see that
# module's own docstring).
# ---------------------------------------------------------------------------


def test_document_opens_with_a_bare_delimiter_line(module: ModuleType, tmp_path: Path) -> None:
    """RFC-1 Section 3.1.1: the document's literal first line must be
    exactly ``---`` -- no leading comment tolerated. This was WP01's actual
    defect: the generated-header comment used to precede this line.
    """
    source = _write_profile(tmp_path, _FULL_PROFILE_YAML)
    output = module.project(source)
    assert output.splitlines()[0] == "---"


def test_generated_header_matches_audit_anchor_pattern(module: ModuleType, tmp_path: Path) -> None:
    source = _write_profile(tmp_path, _FULL_PROFILE_YAML)
    output = module.project(source)
    # Line 0 is the bare opening delimiter (Section 3.1.1); the generated
    # marker is the front-matter block's own first line, immediately after.
    second_line = output.splitlines()[1]
    assert _GENERATED_HEADER_PATTERN.match(second_line)


def test_generated_header_is_the_first_line_inside_front_matter(module: ModuleType, tmp_path: Path) -> None:
    source = _write_profile(tmp_path, _FULL_PROFILE_YAML)
    output = module.project(source)
    assert output.startswith("---\n# generated: true, source-hash: sha256:")


def test_generated_header_hash_is_pure_function_of_source_bytes(module: ModuleType, tmp_path: Path) -> None:
    """The header's hash must depend only on source file content, never on
    wall-clock time or run count -- the property the determinism check
    (T006) falsifies by injecting a ``time.time_ns()`` source.
    """
    source_a = _write_profile(tmp_path, _FULL_PROFILE_YAML, name="a.agent.yaml")
    source_b = _write_profile(tmp_path, _FULL_PROFILE_YAML, name="b.agent.yaml")
    output_a = module.project(source_a)
    output_b = module.project(source_b)
    header_a = output_a.splitlines()[1]
    header_b = output_b.splitlines()[1]
    assert header_a == header_b  # identical bytes -> identical hash, regardless of filename/run


def test_generated_header_committed_personas_match_pattern(module: ModuleType) -> None:
    """Guards the two personas T004 actually committed, not just synthetic fixtures."""
    for persona_path in (
        _REPO_ROOT / "conformance" / "crosslayer" / "personas" / "architect-alphonso.Soul.md",
        _REPO_ROOT / "conformance" / "crosslayer" / "personas" / "reviewer-renata.Soul.md",
    ):
        lines = persona_path.read_text(encoding="utf-8").splitlines()
        assert lines[0] == "---", persona_path
        assert _GENERATED_HEADER_PATTERN.match(lines[1]), persona_path
