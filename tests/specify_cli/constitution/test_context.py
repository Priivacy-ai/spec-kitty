"""Tests for constitution context bootstrap rendering."""

from pathlib import Path

from specify_cli.constitution.context import build_constitution_context


def _write_constitution_bundle(root: Path) -> None:
    constitution_dir = root / ".kittify" / "constitution"
    constitution_dir.mkdir(parents=True)
    (constitution_dir / "constitution.md").write_text(
        """# Project Constitution

## Policy Summary

- Intent: deterministic delivery
- Testing: pytest + coverage

## Project Directives

1. Keep tests strict
""",
        encoding="utf-8",
    )
    (constitution_dir / "references.yaml").write_text(
        """schema_version: "1.0.0"
references:
  - id: "USER:PROJECT_PROFILE"
    kind: user_profile
    title: User Project Profile
    local_path: library/user-project-profile.md
""",
        encoding="utf-8",
    )


def test_context_bootstrap_then_compact(tmp_path: Path) -> None:
    _write_constitution_bundle(tmp_path)

    first = build_constitution_context(tmp_path, action="specify", mark_loaded=True)
    second = build_constitution_context(tmp_path, action="specify", mark_loaded=True)

    assert first.mode == "bootstrap"
    assert first.first_load is True
    assert "Policy Summary" in first.text
    assert first.references_count == 1

    assert second.mode == "compact"
    assert second.first_load is False
    assert "Governance:" in second.text or "Governance: unresolved" in second.text


def test_context_missing_constitution_reports_missing(tmp_path: Path) -> None:
    result = build_constitution_context(tmp_path, action="plan", mark_loaded=True)

    assert result.mode == "missing"
    assert "Constitution file not found" in result.text


def test_non_bootstrap_action_uses_compact_context(tmp_path: Path) -> None:
    _write_constitution_bundle(tmp_path)

    result = build_constitution_context(tmp_path, action="tasks", mark_loaded=True)

    assert result.mode == "compact"
    assert result.first_load is False
