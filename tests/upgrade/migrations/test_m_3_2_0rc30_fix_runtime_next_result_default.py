from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_3_2_0rc30_fix_runtime_next_result_default import (
    FixRuntimeNextResultDefaultMigration,
)
from specify_cli.upgrade.registry import MigrationRegistry

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _write_runtime_next_skill(project: Path, content: str) -> Path:
    skill_path = project / ".claude" / "skills" / "spec-kitty-runtime-next" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(content, encoding="utf-8")
    return skill_path


def test_migration_detects_stale_success_default_doc(tmp_path: Path) -> None:
    _write_runtime_next_skill(
        tmp_path,
        "The `--result` flag tells the runtime the outcome of the previous step.\n"
        "Defaults to `success` if omitted.\n",
    )

    assert FixRuntimeNextResultDefaultMigration().detect(tmp_path) is True


def test_migration_refreshes_runtime_next_skill_doc(tmp_path: Path) -> None:
    skill_path = _write_runtime_next_skill(
        tmp_path,
        "The `--result` flag tells the runtime the outcome of the previous step.\n"
        "Defaults to `success` if omitted.\n",
    )

    result = FixRuntimeNextResultDefaultMigration().apply(tmp_path)

    assert result.success is True
    assert result.changes_made == [
        "Replaced .claude/skills/spec-kitty-runtime-next/SKILL.md"
    ]
    content = skill_path.read_text(encoding="utf-8")
    assert "Defaults to `success` if omitted." not in content
    assert (
        "If omitted, `spec-kitty next` returns current state without advancing "
        "(query mode)."
    ) in content


def test_migration_applies_to_same_version_when_stale_doc_detected(
    tmp_path: Path,
) -> None:
    _write_runtime_next_skill(
        tmp_path,
        "The `--result` flag tells the runtime the outcome of the previous step.\n"
        "Defaults to `success` if omitted.\n",
    )

    applicable = MigrationRegistry.get_applicable(
        "3.2.0rc30",
        "3.2.0rc30",
        project_path=tmp_path,
    )

    assert any(
        migration.migration_id == "3.2.0rc30_fix_runtime_next_result_default"
        for migration in applicable
    )
