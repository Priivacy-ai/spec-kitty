"""Tests for bootstrap integration in feature.py finalize-tasks command.

Verifies that finalize-tasks calls bootstrap_canonical_state() after
dependency parsing, respects --validate-only with dry_run=True, and
includes bootstrap stats in JSON output.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from specify_cli.status.bootstrap import BootstrapResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MODULE = "specify_cli.cli.commands.agent.feature"
CORE_MODULE = "specify_cli.core.feature_creation"


def _setup_feature(tmp_path: Path, feature_slug: str = "060-test-feature") -> Path:
    """Create a minimal feature directory with spec.md, tasks.md, and WP files."""
    feature_dir = tmp_path / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # spec.md with at least one requirement
    spec_md = feature_dir / "spec.md"
    spec_md.write_text(
        "---\ntitle: Test Feature\n---\n\n"
        "## Requirements\n\n"
        "- FR-001: First requirement\n",
        encoding="utf-8",
    )

    # tasks.md with dependency info
    tasks_md = feature_dir / "tasks.md"
    tasks_md.write_text(
        "# Tasks\n\n## WP01\n\nNo dependencies.\n\n## WP02\n\nDepends on WP01.\n",
        encoding="utf-8",
    )

    # WP files with frontmatter
    for wp_id, refs in [("WP01", ["FR-001"]), ("WP02", ["FR-001"])]:
        wp_file = tasks_dir / f"{wp_id}-test.md"
        refs_yaml = "\n".join(f"  - {r}" for r in refs)
        wp_file.write_text(
            f"---\nwork_package_id: \"{wp_id}\"\ntitle: \"Test {wp_id}\"\n"
            f"requirement_refs:\n{refs_yaml}\n"
            f"dependencies: []\n---\n\n# {wp_id}\n",
            encoding="utf-8",
        )

    # meta.json for event emission
    meta = feature_dir / "meta.json"
    meta.write_text(json.dumps({"feature_slug": feature_slug}), encoding="utf-8")

    return feature_dir


def _make_bootstrap_result(
    total: int = 2, seeded: int = 2, existing: int = 0,
) -> BootstrapResult:
    """Create a BootstrapResult with given counts."""
    return BootstrapResult(
        total_wps=total,
        already_initialized=existing,
        newly_seeded=seeded,
        skipped=0,
    )


# Common set of patches needed to run finalize_tasks without real git/filesystem
def _common_patches(tmp_path: Path, feature_slug: str = "060-test-feature"):
    """Return a dict of patch targets -> mock values for finalize_tasks."""
    feature_dir = tmp_path / "kitty-specs" / feature_slug
    return {
        f"{MODULE}.locate_project_root": MagicMock(return_value=tmp_path),
        f"{MODULE}._find_feature_directory": MagicMock(return_value=feature_dir),
        f"{MODULE}._resolve_planning_branch": MagicMock(return_value="main"),
        f"{MODULE}._ensure_branch_checked_out": MagicMock(),
        f"{MODULE}.safe_commit": MagicMock(return_value=True),
        f"{MODULE}.run_command": MagicMock(return_value=(0, "abc1234", "")),
        f"{CORE_MODULE}.emit_feature_created": MagicMock(),
        f"{MODULE}.emit_wp_created": MagicMock(),
        f"{MODULE}.get_emitter": MagicMock(
            return_value=MagicMock(generate_causation_id=MagicMock(return_value="test-id")),
        ),
        f"{MODULE}.validate_ownership": MagicMock(
            return_value=MagicMock(passed=True, warnings=[], errors=[]),
        ),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFinalizeTasksCallsBootstrap:
    """T005-a: finalize-tasks calls bootstrap_canonical_state after deps."""

    def test_bootstrap_called_after_dependency_parsing(self, tmp_path: Path) -> None:
        """Verify bootstrap_canonical_state is called during finalize-tasks."""
        feature_slug = "060-test-feature"
        _setup_feature(tmp_path, feature_slug)

        patches = _common_patches(tmp_path, feature_slug)
        mock_bootstrap = MagicMock(return_value=_make_bootstrap_result())
        patches[f"{MODULE}.bootstrap_canonical_state"] = mock_bootstrap

        from specify_cli.cli.commands.agent.feature import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        mocks = {}
        for k, p in ctx_patches.items():
            mocks[k] = p.start()

        try:
            finalize_tasks(
                feature=feature_slug,
                json_output=True,
                validate_only=False,
            )
        except (typer.Exit, SystemExit):
            pass  # finalize-tasks may exit
        finally:
            for p in ctx_patches.values():
                p.stop()

        mock_bootstrap.assert_called_once_with(
            tmp_path / "kitty-specs" / feature_slug,
            feature_slug,
            dry_run=False,
        )


class TestValidateOnlyDryRun:
    """T005-b: --validate-only calls bootstrap with dry_run=True."""

    def test_validate_only_uses_dry_run(self, tmp_path: Path) -> None:
        """Verify --validate-only passes dry_run=True to bootstrap."""
        feature_slug = "060-test-feature"
        _setup_feature(tmp_path, feature_slug)

        patches = _common_patches(tmp_path, feature_slug)
        mock_bootstrap = MagicMock(return_value=_make_bootstrap_result())
        patches[f"{MODULE}.bootstrap_canonical_state"] = mock_bootstrap

        from specify_cli.cli.commands.agent.feature import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        for p in ctx_patches.values():
            p.start()

        try:
            finalize_tasks(
                feature=feature_slug,
                json_output=True,
                validate_only=True,
            )
        except (typer.Exit, SystemExit):
            pass
        finally:
            for p in ctx_patches.values():
                p.stop()

        mock_bootstrap.assert_called_once_with(
            tmp_path / "kitty-specs" / feature_slug,
            feature_slug,
            dry_run=True,
        )

    def test_validate_only_console_output_reports_bootstrap_summary(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Non-JSON validate-only output should include bootstrap dry-run stats."""
        feature_slug = "060-test-feature"
        _setup_feature(tmp_path, feature_slug)

        patches = _common_patches(tmp_path, feature_slug)
        patches[f"{MODULE}.bootstrap_canonical_state"] = MagicMock(
            return_value=_make_bootstrap_result(total=2, seeded=1, existing=1)
        )

        from specify_cli.cli.commands.agent.feature import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        for p in ctx_patches.values():
            p.start()

        try:
            finalize_tasks(
                feature=feature_slug,
                json_output=False,
                validate_only=True,
            )
        except (typer.Exit, SystemExit):
            pass
        finally:
            for p in ctx_patches.values():
                p.stop()

        output = capsys.readouterr().out
        assert "Bootstrap:" in output
        assert "1 WPs would be seeded, 1 already initialized" in output


class TestBootstrapStatsInJson:
    """T005-c: Bootstrap stats appear in JSON output."""

    def test_json_output_includes_bootstrap_stats(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Verify JSON output contains bootstrap key with correct counts."""
        feature_slug = "060-test-feature"
        _setup_feature(tmp_path, feature_slug)

        patches = _common_patches(tmp_path, feature_slug)
        mock_bootstrap = MagicMock(return_value=_make_bootstrap_result(total=2, seeded=1, existing=1))
        patches[f"{MODULE}.bootstrap_canonical_state"] = mock_bootstrap

        from specify_cli.cli.commands.agent.feature import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        for p in ctx_patches.values():
            p.start()

        try:
            finalize_tasks(
                feature=feature_slug,
                json_output=True,
                validate_only=False,
            )
        except (typer.Exit, SystemExit):
            pass
        finally:
            for p in ctx_patches.values():
                p.stop()

        captured = capsys.readouterr()
        # Find the JSON line that contains "result"
        for line in captured.out.strip().splitlines():
            try:
                data = json.loads(line)
                if data.get("result") == "success":
                    assert "bootstrap" in data
                    assert data["bootstrap"]["total_wps"] == 2
                    assert data["bootstrap"]["newly_seeded"] == 1
                    assert data["bootstrap"]["already_initialized"] == 1
                    return
            except json.JSONDecodeError:
                continue

        pytest.fail("No JSON output with 'result': 'success' found in captured output")

    def test_validate_only_json_includes_bootstrap(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Verify --validate-only JSON output also contains bootstrap stats."""
        feature_slug = "060-test-feature"
        _setup_feature(tmp_path, feature_slug)

        patches = _common_patches(tmp_path, feature_slug)
        mock_bootstrap = MagicMock(return_value=_make_bootstrap_result(total=3, seeded=3, existing=0))
        patches[f"{MODULE}.bootstrap_canonical_state"] = mock_bootstrap

        from specify_cli.cli.commands.agent.feature import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        for p in ctx_patches.values():
            p.start()

        try:
            finalize_tasks(
                feature=feature_slug,
                json_output=True,
                validate_only=True,
            )
        except (typer.Exit, SystemExit):
            pass
        finally:
            for p in ctx_patches.values():
                p.stop()

        captured = capsys.readouterr()
        for line in captured.out.strip().splitlines():
            try:
                data = json.loads(line)
                if data.get("result") == "validation_passed":
                    assert "bootstrap" in data
                    assert data["bootstrap"]["total_wps"] == 3
                    assert data["bootstrap"]["newly_seeded"] == 3
                    assert data["bootstrap"]["already_initialized"] == 0
                    assert data["validate_only"] is True
                    return
            except json.JSONDecodeError:
                continue

        pytest.fail("No JSON output with 'result': 'validation_passed' found")
