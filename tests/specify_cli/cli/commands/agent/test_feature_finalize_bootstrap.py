"""Tests for bootstrap integration in feature.py finalize-tasks command.

Verifies that finalize-tasks calls bootstrap_canonical_state() after
dependency parsing, respects --validate-only with dry_run=True, and
includes bootstrap stats in JSON output.

WP01 additions (T009):
- test_validate_only_no_file_writes: --validate-only must not modify WP files
- test_validate_only_reports_would_modify: JSON output includes would_modify
- test_non_empty_disagreement_fails: conflicting deps → exit code 1 + diagnostic
- test_empty_parse_preserves_existing_deps: existing deps survive empty parse
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

MODULE = "specify_cli.cli.commands.agent.mission"
CORE_MODULE = "specify_cli.core.mission_creation"


def _setup_feature(tmp_path: Path, mission_slug: str = "060-test-feature") -> Path:
    """Create a minimal feature directory with spec.md, tasks.md, and WP files."""
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # spec.md with at least one requirement
    spec_md = feature_dir / "spec.md"
    spec_md.write_text(
        "---\ntitle: Test Feature\n---\n\n## Requirements\n\n- FR-001: First requirement\n",
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
            f'---\nwork_package_id: "{wp_id}"\ntitle: "Test {wp_id}"\nrequirement_refs:\n{refs_yaml}\ndependencies: []\n---\n\n# {wp_id}\n',
            encoding="utf-8",
        )

    # meta.json for event emission
    meta = feature_dir / "meta.json"
    meta.write_text(json.dumps({"mission_slug": mission_slug}), encoding="utf-8")

    return feature_dir


def _make_bootstrap_result(
    total: int = 2,
    seeded: int = 2,
    existing: int = 0,
) -> BootstrapResult:
    """Create a BootstrapResult with given counts."""
    return BootstrapResult(
        total_wps=total,
        already_initialized=existing,
        newly_seeded=seeded,
        skipped=0,
    )


# Common set of patches needed to run finalize_tasks without real git/filesystem
def _common_patches(tmp_path: Path, mission_slug: str = "060-test-feature"):
    """Return a dict of patch targets -> mock values for finalize_tasks."""
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    return {
        f"{MODULE}.locate_project_root": MagicMock(return_value=tmp_path),
        f"{MODULE}._find_feature_directory": MagicMock(return_value=feature_dir),
        f"{MODULE}._resolve_planning_branch": MagicMock(return_value="main"),
        f"{MODULE}._ensure_branch_checked_out": MagicMock(),
        f"{MODULE}.safe_commit": MagicMock(return_value=True),
        f"{MODULE}.run_command": MagicMock(return_value=(0, "abc1234", "")),
        f"{CORE_MODULE}.emit_mission_created": MagicMock(),
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
        mission_slug = "060-test-feature"
        _setup_feature(tmp_path, mission_slug)

        patches = _common_patches(tmp_path, mission_slug)
        mock_bootstrap = MagicMock(return_value=_make_bootstrap_result())
        patches[f"{MODULE}.bootstrap_canonical_state"] = mock_bootstrap

        from specify_cli.cli.commands.agent.mission import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        mocks = {}
        for k, p in ctx_patches.items():
            mocks[k] = p.start()

        try:
            finalize_tasks(
                feature=mission_slug,
                json_output=True,
                validate_only=False,
            )
        except (typer.Exit, SystemExit):
            pass  # finalize-tasks may exit
        finally:
            for p in ctx_patches.values():
                p.stop()

        mock_bootstrap.assert_called_once_with(
            tmp_path / "kitty-specs" / mission_slug,
            mission_slug,
            dry_run=False,
        )


class TestValidateOnlyDryRun:
    """T005-b: --validate-only calls bootstrap with dry_run=True."""

    def test_validate_only_uses_dry_run(self, tmp_path: Path) -> None:
        """Verify --validate-only passes dry_run=True to bootstrap."""
        mission_slug = "060-test-feature"
        _setup_feature(tmp_path, mission_slug)

        patches = _common_patches(tmp_path, mission_slug)
        mock_bootstrap = MagicMock(return_value=_make_bootstrap_result())
        patches[f"{MODULE}.bootstrap_canonical_state"] = mock_bootstrap

        from specify_cli.cli.commands.agent.mission import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        for p in ctx_patches.values():
            p.start()

        try:
            finalize_tasks(
                feature=mission_slug,
                json_output=True,
                validate_only=True,
            )
        except (typer.Exit, SystemExit):
            pass
        finally:
            for p in ctx_patches.values():
                p.stop()

        mock_bootstrap.assert_called_once_with(
            tmp_path / "kitty-specs" / mission_slug,
            mission_slug,
            dry_run=True,
        )

    def test_validate_only_console_output_reports_bootstrap_summary(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Non-JSON validate-only output should include bootstrap dry-run stats."""
        mission_slug = "060-test-feature"
        _setup_feature(tmp_path, mission_slug)

        patches = _common_patches(tmp_path, mission_slug)
        patches[f"{MODULE}.bootstrap_canonical_state"] = MagicMock(return_value=_make_bootstrap_result(total=2, seeded=1, existing=1))

        from specify_cli.cli.commands.agent.mission import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        for p in ctx_patches.values():
            p.start()

        try:
            finalize_tasks(
                feature=mission_slug,
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
        mission_slug = "060-test-feature"
        _setup_feature(tmp_path, mission_slug)

        patches = _common_patches(tmp_path, mission_slug)
        mock_bootstrap = MagicMock(return_value=_make_bootstrap_result(total=2, seeded=1, existing=1))
        patches[f"{MODULE}.bootstrap_canonical_state"] = mock_bootstrap

        from specify_cli.cli.commands.agent.mission import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        for p in ctx_patches.values():
            p.start()

        try:
            finalize_tasks(
                feature=mission_slug,
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

    def test_validate_only_json_includes_validation_preview(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Verify --validate-only JSON output contains validation.bootstrap_preview."""
        mission_slug = "060-test-feature"
        _setup_feature(tmp_path, mission_slug)

        patches = _common_patches(tmp_path, mission_slug)
        mock_bootstrap = MagicMock(return_value=_make_bootstrap_result(total=3, seeded=3, existing=0))
        patches[f"{MODULE}.bootstrap_canonical_state"] = mock_bootstrap

        from specify_cli.cli.commands.agent.mission import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        for p in ctx_patches.values():
            p.start()

        try:
            finalize_tasks(
                feature=mission_slug,
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
                    assert "bootstrap" not in data
                    assert "validation" in data
                    preview = data["validation"]["bootstrap_preview"]
                    assert preview["total_wps"] == 3
                    assert preview["newly_seeded"] == 3
                    assert preview["already_initialized"] == 0
                    assert data["validate_only"] is True
                    return
            except json.JSONDecodeError:
                continue

        pytest.fail("No JSON output with 'result': 'validation_passed' found")


# ---------------------------------------------------------------------------
# WP01 regression tests (T009)
# ---------------------------------------------------------------------------


def _setup_feature_with_existing_deps(
    tmp_path: Path,
    mission_slug: str = "060-test-feature",
    wp02_existing_deps: list[str] | None = None,
) -> Path:
    """Create feature where WP02 already has frontmatter dependencies."""
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    (feature_dir / "spec.md").write_text(
        "---\ntitle: Test Feature\n---\n\n## Requirements\n\n- FR-001: First requirement\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n## WP01\n\nNo dependencies.\n\n## WP02\n\nDepends on WP01.\n",
        encoding="utf-8",
    )
    (feature_dir / "meta.json").write_text(json.dumps({"mission_slug": mission_slug}), encoding="utf-8")

    for wp_id, refs in [("WP01", ["FR-001"]), ("WP02", ["FR-001"])]:
        dep_lines = ""
        if wp_id == "WP02" and wp02_existing_deps is not None:
            dep_items = "\n".join(f"  - {d}" for d in wp02_existing_deps)
            dep_lines = f"dependencies:\n{dep_items}\n" if dep_items else "dependencies: []\n"
        else:
            dep_lines = "dependencies: []\n"
        refs_yaml = "\n".join(f"  - {r}" for r in refs)
        (tasks_dir / f"{wp_id}-test.md").write_text(
            f'---\nwork_package_id: "{wp_id}"\ntitle: "Test {wp_id}"\nrequirement_refs:\n{refs_yaml}\n{dep_lines}---\n\n# {wp_id}\n',
            encoding="utf-8",
        )

    return feature_dir


class TestWP01Regressions:
    """WP01 regression tests (T009)."""

    def test_validate_only_no_file_writes(self, tmp_path: Path) -> None:
        """--validate-only must not modify WP files (files byte-identical before/after)."""
        mission_slug = "060-test-feature"
        feature_dir = _setup_feature(tmp_path, mission_slug)
        tasks_dir = feature_dir / "tasks"

        # Capture checksums before
        checksums_before = {f.name: f.read_bytes() for f in tasks_dir.glob("WP*.md")}

        patches = _common_patches(tmp_path, mission_slug)
        mock_bootstrap = MagicMock(return_value=_make_bootstrap_result())
        patches[f"{MODULE}.bootstrap_canonical_state"] = mock_bootstrap

        from specify_cli.cli.commands.agent.mission import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        for p in ctx_patches.values():
            p.start()
        try:
            finalize_tasks(feature=mission_slug, json_output=True, validate_only=True)
        except (typer.Exit, SystemExit):
            pass
        finally:
            for p in ctx_patches.values():
                p.stop()

        # Capture checksums after — must be identical
        checksums_after = {f.name: f.read_bytes() for f in tasks_dir.glob("WP*.md")}
        assert checksums_before == checksums_after, "validate_only=True must not modify any WP files on disk"

    def test_validate_only_reports_would_modify(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """--validate-only JSON output must include would_modify field."""
        mission_slug = "060-test-feature"
        _setup_feature(tmp_path, mission_slug)

        patches = _common_patches(tmp_path, mission_slug)
        patches[f"{MODULE}.bootstrap_canonical_state"] = MagicMock(return_value=_make_bootstrap_result())

        from specify_cli.cli.commands.agent.mission import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        for p in ctx_patches.values():
            p.start()
        try:
            finalize_tasks(feature=mission_slug, json_output=True, validate_only=True)
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
                    assert "would_modify" in data, "JSON must include would_modify"
                    assert "would_preserve" in data, "JSON must include would_preserve"
                    assert "unchanged" in data, "JSON must include unchanged"
                    assert "bootstrap" not in data
                    assert "validation" in data
                    assert "bootstrap_preview" in data["validation"]
                    assert data["validate_only"] is True
                    return
            except json.JSONDecodeError:
                continue
        pytest.fail("No JSON output with 'result': 'validation_passed' found")

    def test_non_empty_disagreement_fails(self, tmp_path: Path) -> None:
        """Non-empty dep disagreement between tasks.md and frontmatter → exit 1."""
        mission_slug = "060-test-feature"
        # WP02 frontmatter says [WP99] but tasks.md says "Depends on WP01"
        _setup_feature_with_existing_deps(tmp_path, mission_slug, wp02_existing_deps=["WP99"])

        patches = _common_patches(tmp_path, mission_slug)
        patches[f"{MODULE}.bootstrap_canonical_state"] = MagicMock(return_value=_make_bootstrap_result())

        from specify_cli.cli.commands.agent.mission import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        for p in ctx_patches.values():
            p.start()
        exit_code = None
        try:
            finalize_tasks(feature=mission_slug, json_output=False, validate_only=False)
        except (typer.Exit, SystemExit) as exc:
            exit_code = getattr(exc, "code", 1) or 1
        finally:
            for p in ctx_patches.values():
                p.stop()

        assert exit_code == 1, "Dependency disagreement must exit with code 1"

    def test_empty_parse_preserves_existing_deps(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """When parser finds no deps but frontmatter has deps, preserve existing."""
        mission_slug = "060-test-feature"
        # tasks.md declares no dependencies for WP02; frontmatter has [WP01]
        feature_dir = tmp_path / "kitty-specs" / mission_slug
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        (feature_dir / "spec.md").write_text(
            "---\ntitle: Test Feature\n---\n\n## Requirements\n\n- FR-001: First requirement\n",
            encoding="utf-8",
        )
        # tasks.md has no dependency declaration for WP02
        (feature_dir / "tasks.md").write_text(
            "# Tasks\n\n## WP01\n\nNo dependencies.\n\n## WP02\n\nSome content, no dep line.\n",
            encoding="utf-8",
        )
        (feature_dir / "meta.json").write_text(json.dumps({"mission_slug": mission_slug}), encoding="utf-8")

        for wp_id, refs in [("WP01", ["FR-001"]), ("WP02", ["FR-001"])]:
            dep_line = "dependencies: []\n" if wp_id == "WP01" else "dependencies:\n  - WP01\n"
            refs_yaml = "\n".join(f"  - {r}" for r in refs)
            (tasks_dir / f"{wp_id}-test.md").write_text(
                f'---\nwork_package_id: "{wp_id}"\ntitle: "Test {wp_id}"\nrequirement_refs:\n{refs_yaml}\n{dep_line}---\n\n# {wp_id}\n',
                encoding="utf-8",
            )

        patches = _common_patches(tmp_path, mission_slug)
        patches[f"{MODULE}.bootstrap_canonical_state"] = MagicMock(return_value=_make_bootstrap_result())

        from specify_cli.cli.commands.agent.mission import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        for p in ctx_patches.values():
            p.start()
        try:
            finalize_tasks(feature=mission_slug, json_output=True, validate_only=False)
        except (typer.Exit, SystemExit):
            pass
        finally:
            for p in ctx_patches.values():
                p.stop()

        # WP02 file should still have WP01 in its dependencies
        wp02_file = tasks_dir / "WP02-test.md"
        assert wp02_file.exists()
        content = wp02_file.read_text(encoding="utf-8")
        assert "WP01" in content, "Existing WP01 dependency must be preserved when parser finds nothing"

    def test_json_reports_modified_unchanged_preserved(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Success JSON output must include modified_wps, unchanged_wps, preserved_wps."""
        mission_slug = "060-test-feature"
        _setup_feature(tmp_path, mission_slug)

        patches = _common_patches(tmp_path, mission_slug)
        patches[f"{MODULE}.bootstrap_canonical_state"] = MagicMock(return_value=_make_bootstrap_result())

        from specify_cli.cli.commands.agent.mission import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        for p in ctx_patches.values():
            p.start()
        try:
            finalize_tasks(feature=mission_slug, json_output=True, validate_only=False)
        except (typer.Exit, SystemExit):
            pass
        finally:
            for p in ctx_patches.values():
                p.stop()

        captured = capsys.readouterr()
        for line in captured.out.strip().splitlines():
            try:
                data = json.loads(line)
                if data.get("result") == "success":
                    assert "modified_wps" in data, "JSON must include modified_wps"
                    assert "unchanged_wps" in data, "JSON must include unchanged_wps"
                    assert "preserved_wps" in data, "JSON must include preserved_wps"
                    assert isinstance(data["modified_wps"], list)
                    assert isinstance(data["unchanged_wps"], list)
                    assert isinstance(data["preserved_wps"], list)
                    return
            except json.JSONDecodeError:
                continue
        pytest.fail("No JSON output with 'result': 'success' found")


class TestValidateOnlyUsesInMemoryOwnership:
    """Regression test for validate-only ownership inference and manifest reuse."""

    def _setup_feature_no_ownership(self, tmp_path: Path, mission_slug: str = "060-test-feature") -> Path:
        """Create WP files WITHOUT ownership fields."""
        feature_dir = tmp_path / "kitty-specs" / mission_slug
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        spec_md = feature_dir / "spec.md"
        spec_md.write_text(
            "---\ntitle: Test Feature\n---\n\n## Requirements\n\n- FR-001: First\n",
            encoding="utf-8",
        )

        tasks_md = feature_dir / "tasks.md"
        tasks_md.write_text(
            "# Tasks\n\n## WP01\n\nNo dependencies.\n\n## WP02\n\nDepends on WP01.\n",
            encoding="utf-8",
        )

        for wp_id, refs in [("WP01", ["FR-001"]), ("WP02", ["FR-001"])]:
            wp_file = tasks_dir / f"{wp_id}-test.md"
            refs_yaml = "\n".join(f"  - {r}" for r in refs)
            wp_file.write_text(
                f'---\nwork_package_id: "{wp_id}"\ntitle: "Test {wp_id}"\n'
                f"requirement_refs:\n{refs_yaml}\ndependencies: []\n---\n\n# {wp_id}\n"
                f"\n## Files\n\n- src/specify_cli/foo.py\n",
                encoding="utf-8",
            )

        meta = feature_dir / "meta.json"
        meta.write_text(json.dumps({"mission_slug": mission_slug}), encoding="utf-8")

        return feature_dir

    def test_validate_only_infers_ownership_in_memory(self, tmp_path: Path) -> None:
        """validate_ownership must receive non-empty manifests in validate-only mode."""
        mission_slug = "060-test-feature"
        self._setup_feature_no_ownership(tmp_path, mission_slug)

        patches = _common_patches(tmp_path, mission_slug)
        patches[f"{MODULE}.bootstrap_canonical_state"] = MagicMock(return_value=_make_bootstrap_result(total=2, seeded=0, existing=2))
        mock_validate = MagicMock(return_value=MagicMock(passed=True, warnings=[], errors=[]))
        patches[f"{MODULE}.validate_ownership"] = mock_validate

        from specify_cli.cli.commands.agent.mission import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        for p in ctx_patches.values():
            p.start()

        try:
            finalize_tasks(
                feature=mission_slug,
                json_output=True,
                validate_only=True,
            )
        except (typer.Exit, SystemExit):
            pass
        finally:
            for p in ctx_patches.values():
                p.stop()

        mock_validate.assert_called_once()
        actual_manifests = mock_validate.call_args[0][0]
        assert len(actual_manifests) > 0, "validate_ownership received empty wp_manifests in validate-only mode"

    def test_validate_only_no_disk_mutation_even_with_ownership_inference(self, tmp_path: Path) -> None:
        """Ownership inference in validate-only mode must not mutate WP files."""
        mission_slug = "060-test-feature"
        self._setup_feature_no_ownership(tmp_path, mission_slug)
        tasks_dir = tmp_path / "kitty-specs" / mission_slug / "tasks"

        wp_snapshots: dict[str, bytes] = {}
        for wp_file in sorted(tasks_dir.glob("WP*.md")):
            wp_snapshots[wp_file.name] = wp_file.read_bytes()

        patches = _common_patches(tmp_path, mission_slug)
        patches[f"{MODULE}.bootstrap_canonical_state"] = MagicMock(return_value=_make_bootstrap_result(total=2, seeded=0, existing=2))

        from specify_cli.cli.commands.agent.mission import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        for p in ctx_patches.values():
            p.start()

        try:
            finalize_tasks(
                feature=mission_slug,
                json_output=True,
                validate_only=True,
            )
        except (typer.Exit, SystemExit):
            pass
        finally:
            for p in ctx_patches.values():
                p.stop()

        for wp_name, before_bytes in wp_snapshots.items():
            after_bytes = (tasks_dir / wp_name).read_bytes()
            assert after_bytes == before_bytes, f"{wp_name} was modified by --validate-only even though ownership inference should only operate in memory"


# ---------------------------------------------------------------------------
# Unit B: Typed frontmatter migration tests for finalize_tasks()
# ---------------------------------------------------------------------------


class TestTypedFrontmatterMigration:
    """Verify finalize_tasks() uses WPMetadata typed reads instead of raw dicts.

    These tests validate the consumer migration from raw ``read_frontmatter()``
    to ``read_wp_frontmatter()`` and the builder pattern for mutations.
    """

    def test_finalize_reads_wp_via_typed_reader(self, tmp_path: Path) -> None:
        """finalize_tasks() must use read_wp_frontmatter, not raw read_frontmatter."""
        mission_slug = "060-test-feature"
        _setup_feature(tmp_path, mission_slug)

        patches = _common_patches(tmp_path, mission_slug)
        patches[f"{MODULE}.bootstrap_canonical_state"] = MagicMock(return_value=_make_bootstrap_result())

        from specify_cli.cli.commands.agent.mission import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        for p in ctx_patches.values():
            p.start()

        # Spy on read_wp_frontmatter to verify it is called
        with patch(
            f"{MODULE}.read_wp_frontmatter",
            wraps=__import__("specify_cli.status.wp_metadata", fromlist=["read_wp_frontmatter"]).read_wp_frontmatter,
        ) as spy_typed:
            try:
                finalize_tasks(
                    feature=mission_slug,
                    json_output=True,
                    validate_only=False,
                )
            except (typer.Exit, SystemExit):
                pass
            finally:
                for p in ctx_patches.values():
                    p.stop()

            assert spy_typed.call_count >= 2, f"Expected read_wp_frontmatter to be called at least twice (pre-loop + main loop), got {spy_typed.call_count}"

    def test_finalize_does_not_call_raw_read_frontmatter(self, tmp_path: Path) -> None:
        """After migration, finalize_tasks must NOT use raw read_frontmatter for WP files."""
        mission_slug = "060-test-feature"
        _setup_feature(tmp_path, mission_slug)

        patches = _common_patches(tmp_path, mission_slug)
        patches[f"{MODULE}.bootstrap_canonical_state"] = MagicMock(return_value=_make_bootstrap_result())

        from specify_cli.cli.commands.agent.mission import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        for p in ctx_patches.values():
            p.start()

        # Spy on the frontmatter module's read_frontmatter to verify it is NOT called
        # by finalize_tasks (which should use read_wp_frontmatter instead)
        import specify_cli.frontmatter as _fm_mod

        with patch.object(_fm_mod, "read_frontmatter", wraps=_fm_mod.read_frontmatter) as spy_raw:
            try:
                finalize_tasks(
                    feature=mission_slug,
                    json_output=True,
                    validate_only=False,
                )
            except (typer.Exit, SystemExit):
                pass
            finally:
                for p in ctx_patches.values():
                    p.stop()

            # read_wp_frontmatter internally calls FrontmatterManager.read(), not
            # the module-level read_frontmatter function.  So spy_raw should be 0.
            assert spy_raw.call_count == 0, f"Expected read_frontmatter to not be called after migration, but it was called {spy_raw.call_count} time(s)"

    def test_written_frontmatter_validates_as_wp_metadata(self, tmp_path: Path) -> None:
        """Frontmatter written by finalize_tasks must round-trip through WPMetadata."""
        mission_slug = "060-test-feature"
        _setup_feature(tmp_path, mission_slug)

        patches = _common_patches(tmp_path, mission_slug)
        patches[f"{MODULE}.bootstrap_canonical_state"] = MagicMock(return_value=_make_bootstrap_result())

        from specify_cli.cli.commands.agent.mission import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        for p in ctx_patches.values():
            p.start()

        try:
            finalize_tasks(
                feature=mission_slug,
                json_output=True,
                validate_only=False,
            )
        except (typer.Exit, SystemExit):
            pass
        finally:
            for p in ctx_patches.values():
                p.stop()

        # After finalize, every WP file's frontmatter must be valid WPMetadata
        from specify_cli.status.wp_metadata import read_wp_frontmatter

        tasks_dir = tmp_path / "kitty-specs" / mission_slug / "tasks"
        for wp_file in sorted(tasks_dir.glob("WP*.md")):
            wp_meta, _body = read_wp_frontmatter(wp_file)
            assert wp_meta.work_package_id is not None
            assert wp_meta.title.strip() != ""

    def test_finalize_updates_branch_fields_via_typed_api(self, tmp_path: Path) -> None:
        """Branch contract fields must be set correctly after finalize_tasks."""
        mission_slug = "060-test-feature"
        _setup_feature(tmp_path, mission_slug)

        patches = _common_patches(tmp_path, mission_slug)
        patches[f"{MODULE}.bootstrap_canonical_state"] = MagicMock(return_value=_make_bootstrap_result())

        from specify_cli.cli.commands.agent.mission import finalize_tasks

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        for p in ctx_patches.values():
            p.start()

        try:
            finalize_tasks(
                feature=mission_slug,
                json_output=True,
                validate_only=False,
            )
        except (typer.Exit, SystemExit):
            pass
        finally:
            for p in ctx_patches.values():
                p.stop()

        from specify_cli.status.wp_metadata import read_wp_frontmatter

        tasks_dir = tmp_path / "kitty-specs" / mission_slug / "tasks"
        for wp_file in sorted(tasks_dir.glob("WP*.md")):
            wp_meta, _ = read_wp_frontmatter(wp_file)
            # finalize_tasks sets these branch fields
            assert wp_meta.planning_base_branch == "main"
            assert wp_meta.merge_target_branch == "main"
            assert wp_meta.branch_strategy is not None
            assert "Planning artifacts" in wp_meta.branch_strategy

    def test_ownership_manifest_receives_typed_metadata(self, tmp_path: Path) -> None:
        """OwnershipManifest.from_frontmatter() must receive WPMetadata, not raw dict."""
        mission_slug = "060-test-feature"
        _setup_feature(tmp_path, mission_slug)

        # Add ownership fields so the post-loop validation path is exercised
        tasks_dir = tmp_path / "kitty-specs" / mission_slug / "tasks"
        for wp_file in sorted(tasks_dir.glob("WP*.md")):
            content = wp_file.read_text(encoding="utf-8")
            # Insert ownership fields before the closing ---
            content = content.replace(
                "dependencies: []",
                'dependencies: []\nexecution_mode: "code_change"\nowned_files:\n  - "src/**"',
            )
            wp_file.write_text(content, encoding="utf-8")

        patches = _common_patches(tmp_path, mission_slug)
        patches[f"{MODULE}.bootstrap_canonical_state"] = MagicMock(return_value=_make_bootstrap_result())

        from specify_cli.cli.commands.agent.mission import finalize_tasks
        from specify_cli.ownership.models import OwnershipManifest
        from specify_cli.status.wp_metadata import WPMetadata

        ctx_patches = {k: patch(k, v) for k, v in patches.items()}
        for p in ctx_patches.values():
            p.start()

        # Spy on OwnershipManifest.from_frontmatter to check arg types
        original_from_fm = OwnershipManifest.from_frontmatter
        received_args: list[object] = []

        def spy_from_frontmatter(data: object) -> object:
            received_args.append(data)
            return original_from_fm(data)

        with patch.object(OwnershipManifest, "from_frontmatter", staticmethod(spy_from_frontmatter)):
            try:
                finalize_tasks(
                    feature=mission_slug,
                    json_output=True,
                    validate_only=False,
                )
            except (typer.Exit, SystemExit):
                pass
            finally:
                for p in ctx_patches.values():
                    p.stop()

        assert len(received_args) >= 1, "OwnershipManifest.from_frontmatter was never called"
        for arg in received_args:
            assert isinstance(arg, WPMetadata), f"Expected WPMetadata instance, got {type(arg).__name__}"
