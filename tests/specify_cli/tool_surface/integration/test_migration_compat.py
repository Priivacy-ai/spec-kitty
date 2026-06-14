"""Migration compatibility gate for ``spec-kitty doctor skills --json``.

These tests freeze the ``doctor skills --json`` output **schema** (keys + value
types, not content) as a backward-compatibility baseline for the entire
ToolSurfaceContract epic. Any subsequent WP (WP03-WP09) that changes the schema
breaks these tests and therefore cannot merge.

The tests are deterministic: they run the checkout-local ``specify_cli`` package
against a controlled ``.kittify`` fixture in ``tmp_path``, so the result never
depends on what tools the developer has configured.
"""

from __future__ import annotations

import json
from pathlib import Path

from ._compat_support import (
    project_root,
    run_spec_kitty,
    schema_shape,
    write_controlled_project,
)

_FIXTURES = Path(__file__).parent / "fixtures"
_BASELINE = _FIXTURES / "doctor_skills_baseline.json"


def _load_baseline() -> dict[str, object]:
    data: dict[str, object] = json.loads(_BASELINE.read_text(encoding="utf-8"))
    return data


def test_doctor_skills_json_is_valid_json(tmp_path: Path) -> None:
    project = write_controlled_project(tmp_path)
    result = run_spec_kitty("doctor", "skills", "--json", cwd=project)
    # Exit code may be 0 or 1 (1 = healthy schema but agents need install);
    # both produce valid JSON. Anything >=2 is an unexpected error.
    assert result.returncode in (0, 1), result.stderr
    parsed = result.json()  # raises if stdout is not valid JSON
    assert isinstance(parsed, dict)


def test_doctor_skills_json_schema_matches_baseline(tmp_path: Path) -> None:
    """The success-path schema shape must equal the committed baseline."""
    project = write_controlled_project(tmp_path)
    result = run_spec_kitty("doctor", "skills", "--json", cwd=project)
    assert result.returncode in (0, 1), result.stderr
    actual_shape = schema_shape(result.json())
    assert actual_shape == _load_baseline(), (
        "doctor skills --json schema drifted from the frozen baseline. "
        "If this change is intentional and additive, regenerate "
        "doctor_skills_baseline.json and document it per "
        "src/specify_cli/tool_surface/contracts/migration-compatibility.md."
    )


def test_doctor_skills_json_has_frozen_top_level_keys(tmp_path: Path) -> None:
    """Explicit assertions on the frozen field set (not just shape equality)."""
    project = write_controlled_project(tmp_path)
    output = run_spec_kitty("doctor", "skills", "--json", cwd=project).json()
    frozen_keys = {
        "ok",
        "configured_agents",
        "manifest_agents",
        "entries",
        "drift",
        "gaps",
        "orphans",
        "stale",
        "unsafe",
        "slash_commands",
    }
    assert frozen_keys.issubset(output.keys()), (
        f"Missing frozen keys: {frozen_keys - set(output.keys())}"
    )
    assert isinstance(output["ok"], bool)
    for list_key in ("configured_agents", "drift", "gaps", "orphans", "stale", "unsafe"):
        assert isinstance(output[list_key], list), f"{list_key} must be a list"
    assert isinstance(output["slash_commands"], dict)


def test_doctor_skills_json_is_deterministic(tmp_path: Path) -> None:
    """Same controlled fixture => identical output across runs (no ambient state)."""
    project = write_controlled_project(tmp_path)
    first = run_spec_kitty("doctor", "skills", "--json", cwd=project)
    second = run_spec_kitty("doctor", "skills", "--json", cwd=project)
    assert first.returncode == second.returncode
    assert first.json() == second.json()


def test_doctor_skills_json_error_schema_stable(tmp_path: Path) -> None:
    """The structured error envelope is frozen too: {ok, error:{code, message}}."""
    # No .kittify project here => 'not_in_project' error path. Point the repo-root
    # override at an empty dir so resolution genuinely fails.
    empty = tmp_path / "empty"
    empty.mkdir()
    result = run_spec_kitty("doctor", "skills", "--json", cwd=empty)
    assert result.returncode == 2, result.stdout
    payload = result.json()
    assert payload["ok"] is False
    assert isinstance(payload["error"], dict)
    assert "code" in payload["error"]
    assert "message" in payload["error"]
    assert isinstance(payload["error"]["code"], str)
    assert isinstance(payload["error"]["message"], str)


def test_baseline_fixture_is_machine_independent() -> None:
    """The baseline must not leak machine-specific paths or ambient config."""
    raw = _BASELINE.read_text(encoding="utf-8")
    assert str(Path.home()) not in raw
    assert str(project_root()) not in raw
    # Shape-only: leaf values are type names or empty containers, never content.
    baseline = _load_baseline()
    assert baseline["configured_agents"] == ["str"]
    assert baseline["ok"] == "bool"
