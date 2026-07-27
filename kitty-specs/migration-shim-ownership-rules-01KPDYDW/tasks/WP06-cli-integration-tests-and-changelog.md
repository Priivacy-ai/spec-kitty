---
work_package_id: WP06
title: CLI Integration Tests and Changelog
dependencies:
- WP03
- WP04
requirement_refs:
- FR-009
- FR-015
- NFR-001
- NFR-004
- NFR-005
planning_base_branch: kitty/mission-migration-shim-ownership-rules-01KPDYDW
merge_target_branch: kitty/mission-migration-shim-ownership-rules-01KPDYDW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-migration-shim-ownership-rules-01KPDYDW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-migration-shim-ownership-rules-01KPDYDW unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
agent: "claude"
shell_pid: "1350803"
history:
- date: '2026-04-19'
  event: created
agent_profile: python-implementer
authoritative_surface: tests/doctor/
execution_mode: code_change
mission_id: 01KPDYDWVF8W838HNJK7FC3S7T
mission_slug: migration-shim-ownership-rules-01KPDYDW
owned_files:
- tests/doctor/test_shim_registry.py
- CHANGELOG.md
tags: []
---

# WP06 — CLI Integration Tests and Changelog

## Objective

Cover the `spec-kitty doctor shim-registry` CLI surface with integration tests using `typer.testing.CliRunner`, covering all exit code paths (0/1/2), status variants (pending/overdue/grandfathered/removed), and the `--json` flag. Also add the CHANGELOG entry (FR-015).

## Context

`tests/doctor/test_identity_audit.py` shows the established pattern: use `typer.testing.CliRunner` against the top-level `app` from `specify_cli.cli.main` (or the doctor app directly). Tests write synthetic files to `tmp_path` to avoid coupling to the live project version.

## Branch Strategy

- **Working branch**: `kitty/mission-migration-shim-ownership-rules-01KPDYDW`
- **Merge target**: `main`
- Run: `spec-kitty agent action implement WP06 --agent <name>`

> **Agent guideline**: Load the assigned agent profile (`agent_profile: python-implementer`) from
> `src/doctrine/agent_profiles/shipped/python-implementer.agent.yaml` before starting work.
> Apply the profile's `initialization-declaration`, `success-definition`, and `self-review-protocol`
> (pytest, mypy --strict, ruff check) before moving to for_review.

---

## Subtask T011 — Write `tests/doctor/test_shim_registry.py`

**Purpose**: FR-009 — integration-test every execution path of `spec-kitty doctor shim-registry`.

**Setup approach**: Each test builds a `tmp_path` repo with a synthetic `pyproject.toml` and `architecture/2.x/shim-registry.yaml`. The version in `pyproject.toml` is pinned to `"3.2.0"` in tests so semver comparisons are deterministic.

```python
"""FR-009: Integration tests for spec-kitty doctor shim-registry."""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

# Import the doctor app — adjust import path to match how other doctor tests do it
from specify_cli.cli.commands.doctor import app

runner = CliRunner()

PYPROJECT_CONTENT = '[project]\nname = "spec-kitty-cli"\nversion = "3.2.0"\n'
REGISTRY_TEMPLATE = "shims:\n{entries}\n"


def _write_project(tmp_path: Path, registry_content: str, version: str = "3.2.0") -> None:
    """Write a minimal pyproject.toml and shim-registry.yaml to tmp_path."""
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "spec-kitty-cli"\nversion = "{version}"\n'
    )
    arch = tmp_path / "architecture" / "2.x"
    arch.mkdir(parents=True)
    (arch / "shim-registry.yaml").write_text(registry_content)


def _make_entry(
    legacy_path: str = "specify_cli.example",
    canonical: str = "example",
    introduced: str = "3.2.0",
    removal: str = "3.3.0",
    issue: str = "#615",
    grandfathered: bool = False,
    notes: str | None = None,
) -> str:
    lines = [
        f"  - legacy_path: {legacy_path}",
        f"    canonical_import: {canonical}",
        f"    introduced_in_release: \"{introduced}\"",
        f"    removal_target_release: \"{removal}\"",
        f"    tracker_issue: \"{issue}\"",
        f"    grandfathered: {'true' if grandfathered else 'false'}",
    ]
    if notes:
        lines.append(f"    notes: \"{notes}\"")
    return "\n".join(lines)


class TestEmptyRegistry:
    def test_empty_registry_exits_0(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _write_project(tmp_path, "shims: []\n")
        monkeypatch.chdir(tmp_path)
        # Patch locate_project_root to return tmp_path
        import specify_cli.core.paths as paths_mod
        monkeypatch.setattr(paths_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry"])
        assert result.exit_code == 0
        assert "empty" in result.output.lower()

    def test_empty_registry_json_exits_0(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _write_project(tmp_path, "shims: []\n")
        import specify_cli.core.paths as paths_mod
        monkeypatch.setattr(paths_mod, "locate_project_root", lambda: tmp_path)
        import json
        result = runner.invoke(app, ["shim-registry", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["entries"] == []
        assert data["has_overdue"] is False


class TestPendingEntry:
    def test_pending_entry_exits_0(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # removal 3.3.0, current 3.2.0 → pending
        entry = _make_entry(removal="3.3.0")
        _write_project(tmp_path, f"shims:\n{entry}\n", version="3.2.0")
        import specify_cli.core.paths as paths_mod
        monkeypatch.setattr(paths_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry"])
        assert result.exit_code == 0
        assert "pending" in result.output


class TestOverdueEntry:
    def test_overdue_entry_exits_1(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # removal 3.2.0 == current 3.2.0 → overdue (when shim file exists)
        entry = _make_entry(removal="3.2.0")
        _write_project(tmp_path, f"shims:\n{entry}\n", version="3.2.0")
        # create the shim file so it counts as "exists"
        shim_dir = tmp_path / "src" / "specify_cli"
        shim_dir.mkdir(parents=True)
        (shim_dir / "example.py").write_text("__deprecated__ = True\n")
        import specify_cli.core.paths as paths_mod
        monkeypatch.setattr(paths_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry"])
        assert result.exit_code == 1
        assert "OVERDUE" in result.output or "overdue" in result.output.lower()

    def test_overdue_shows_remediation_block(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        entry = _make_entry(removal="3.2.0")
        _write_project(tmp_path, f"shims:\n{entry}\n", version="3.2.0")
        shim_dir = tmp_path / "src" / "specify_cli"
        shim_dir.mkdir(parents=True)
        (shim_dir / "example.py").write_text("__deprecated__ = True\n")
        import specify_cli.core.paths as paths_mod
        monkeypatch.setattr(paths_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry"])
        assert "Option A" in result.output or "Delete" in result.output


class TestGrandfatheredEntry:
    def test_grandfathered_exits_0(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # grandfathered=true → never overdue even if removal target passed
        entry = _make_entry(removal="3.1.0", grandfathered=True)
        _write_project(tmp_path, f"shims:\n{entry}\n", version="3.2.0")
        import specify_cli.core.paths as paths_mod
        monkeypatch.setattr(paths_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry"])
        assert result.exit_code == 0
        assert "grandfathered" in result.output.lower()


class TestRemovedEntry:
    def test_removed_entry_exits_0(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # removal target passed but shim file absent → "removed"
        entry = _make_entry(removal="3.2.0")
        _write_project(tmp_path, f"shims:\n{entry}\n", version="3.2.0")
        # do NOT create the shim file
        import specify_cli.core.paths as paths_mod
        monkeypatch.setattr(paths_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry"])
        assert result.exit_code == 0
        assert "removed" in result.output.lower()


class TestConfigErrors:
    def test_missing_pyproject_exits_2(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        arch = tmp_path / "architecture" / "2.x"
        arch.mkdir(parents=True)
        (arch / "shim-registry.yaml").write_text("shims: []\n")
        import specify_cli.core.paths as paths_mod
        monkeypatch.setattr(paths_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry"])
        assert result.exit_code == 2

    def test_missing_registry_exits_2(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        (tmp_path / "pyproject.toml").write_text(PYPROJECT_CONTENT)
        import specify_cli.core.paths as paths_mod
        monkeypatch.setattr(paths_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry"])
        assert result.exit_code == 2

    def test_invalid_registry_yaml_exits_2(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _write_project(tmp_path, "shims:\n  - legacy_path: bad path!\n    grandfathered: not-a-bool\n")
        import specify_cli.core.paths as paths_mod
        monkeypatch.setattr(paths_mod, "locate_project_root", lambda: tmp_path)
        result = runner.invoke(app, ["shim-registry"])
        assert result.exit_code == 2


class TestJsonOutput:
    def test_json_has_required_keys(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _write_project(tmp_path, "shims: []\n")
        import specify_cli.core.paths as paths_mod
        monkeypatch.setattr(paths_mod, "locate_project_root", lambda: tmp_path)
        import json
        result = runner.invoke(app, ["shim-registry", "--json"])
        data = json.loads(result.output)
        assert set(data.keys()) >= {"entries", "has_overdue", "exit_code", "project_version", "registry_path"}
```

**Files**:
- `tests/doctor/test_shim_registry.py` (new, ~160 lines)

**Validation**:
- [ ] All 8 test classes pass
- [ ] `pytest tests/doctor/test_shim_registry.py -v` exits 0
- [ ] `mypy --strict tests/doctor/test_shim_registry.py` passes (or with `--ignore-missing-imports` for typer internals)
- [ ] NFR-005: DeprecationWarning from monkeypatched shims does not cause test failures

> **Note on `monkeypatch.setattr`**: Adjust the `locate_project_root` patch target to match the actual import path in `doctor.py`. If `doctor.py` imports as `from specify_cli.core.paths import locate_project_root` and uses it by name, patch `specify_cli.cli.commands.doctor.locate_project_root` directly.

---

## Subtask T012 — Update `CHANGELOG.md`

**Purpose**: FR-015 — add an entry under `## [Unreleased]` → `### Added` for the three new artifacts.

**Steps**:
1. Open `CHANGELOG.md` and locate the `## [Unreleased]` section (create it if absent, above the most recent versioned section).
2. Under `### Added` (create if absent within Unreleased), add:

```markdown
### Added

- `architecture/2.x/06_migration_and_shim_rules.md` — compatibility shim lifecycle rulebook covering schema/version gating, migration authoring contract, shim lifecycle, and removal plans. Cite this rulebook in any future extraction PR (#615).
- `architecture/2.x/shim-registry.yaml` — machine-readable registry of all active and grandfathered compatibility shims. New shims must be registered here per the rulebook.
- `spec-kitty doctor shim-registry` — CI enforcement check that fails (exit 1) when a registered shim's `removal_target_release` has shipped but the shim file still exists on disk.
```

**Files**:
- `CHANGELOG.md`

**Validation**:
- [ ] `CHANGELOG.md` has an `## [Unreleased]` section with the three Added entries
- [ ] Existing changelog entries are untouched

---

## Definition of Done

- [ ] `tests/doctor/test_shim_registry.py` written with all exit-code paths covered
- [ ] All test classes pass: empty/pending/overdue/grandfathered/removed/config-errors/json
- [ ] `CHANGELOG.md` updated with Unreleased/Added entry
- [ ] `pytest tests/doctor/ -v` exits 0 (including existing `test_identity_audit.py`)
- [ ] mypy passes on the new test file

## Risks

- The `locate_project_root` patch path may differ from `specify_cli.core.paths` — check the actual import in `doctor.py` and patch the name as seen by the module under test.
- `typer.testing.CliRunner` captures stdout but not stderr by default; set `mix_stderr=False` if error messages go to stderr.
- Existing `test_identity_audit.py` imports from the doctor app — verify the addition of `shim-registry` doesn't change the app object's import path.

## Activity Log

- 2026-04-19T13:31:15Z – claude – shell_pid=1349267 – Started implementation via action command
- 2026-04-19T13:34:07Z – claude – shell_pid=1349267 – 16 integration tests pass, CHANGELOG updated, ruff clean.
- 2026-04-19T13:36:33Z – claude – shell_pid=1350803 – Started review via action command
- 2026-04-19T13:36:51Z – claude – shell_pid=1350803 – Review passed: 16 integration tests pass (all exit codes 0/1/2, all statuses pending/overdue/grandfathered/removed, --json flag); full doctor suite 49 tests green; CHANGELOG has 3 Unreleased/Added entries.
