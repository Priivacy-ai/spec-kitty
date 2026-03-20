"""Tests for post-init verification of agent skill installations."""

from __future__ import annotations

from pathlib import Path

from specify_cli.skills.manifest import ManagedFile, SkillsManifest
from specify_cli.skills.verification import VerificationResult, verify_installation


def _make_manifest(
    selected_agents: list[str] | None = None,
    installed_skill_roots: list[str] | None = None,
    managed_files: list[ManagedFile] | None = None,
) -> SkillsManifest:
    """Helper to build a manifest with sensible defaults."""
    return SkillsManifest(
        spec_kitty_version="2.1.0",
        created_at="2026-03-20T00:00:00Z",
        updated_at="2026-03-20T00:00:00Z",
        skills_mode="auto",
        selected_agents=selected_agents or [],
        installed_skill_roots=installed_skill_roots or [],
        managed_files=managed_files or [],
    )


# ---------------------------------------------------------------------------
# Pass case
# ---------------------------------------------------------------------------


class TestVerificationPasses:
    """Verify that a correct installation passes all checks."""

    def test_all_checks_pass(self, tmp_path: Path) -> None:
        """Mixed agents with correct roots and wrappers pass cleanly."""
        # Create skill roots on disk
        (tmp_path / ".agents" / "skills").mkdir(parents=True)
        (tmp_path / ".claude" / "skills").mkdir(parents=True)

        manifest = _make_manifest(
            selected_agents=["claude", "codex"],
            installed_skill_roots=[".agents/skills/", ".claude/skills/"],
            managed_files=[
                ManagedFile(
                    path=".codex/prompts/spec-kitty.specify.md",
                    sha256="abc123",
                    file_type="wrapper",
                ),
                ManagedFile(
                    path=".claude/commands/spec-kitty.specify.md",
                    sha256="def456",
                    file_type="wrapper",
                ),
            ],
        )

        result = verify_installation(tmp_path, ["claude", "codex"], manifest)

        assert result.passed
        assert result.errors == []

    def test_empty_result_defaults(self) -> None:
        """VerificationResult defaults to passed=True with empty lists."""
        r = VerificationResult()
        assert r.passed is True
        assert r.errors == []
        assert r.warnings == []


# ---------------------------------------------------------------------------
# Check 1: Agent coverage
# ---------------------------------------------------------------------------


class TestAgentCoverage:
    """Check 1: every selected agent has a skill root or wrapper files."""

    def test_agent_with_no_roots_or_wrappers_fails(self, tmp_path: Path) -> None:
        """An agent with neither a skill root nor wrappers is an error."""
        # claude has a root and wrappers; codex has nothing
        (tmp_path / ".claude" / "skills").mkdir(parents=True)

        manifest = _make_manifest(
            selected_agents=["claude", "codex"],
            installed_skill_roots=[".claude/skills/"],
            managed_files=[
                ManagedFile(
                    path=".claude/commands/x.md",
                    sha256="x",
                    file_type="wrapper",
                ),
                # No codex wrappers, no .agents/skills/
            ],
        )

        result = verify_installation(tmp_path, ["claude", "codex"], manifest)

        assert not result.passed
        assert any("codex" in e for e in result.errors)

    def test_agent_with_only_wrappers_passes(self, tmp_path: Path) -> None:
        """An agent that has wrappers but no dedicated skill root still passes."""
        manifest = _make_manifest(
            selected_agents=["codex"],
            installed_skill_roots=[],
            managed_files=[
                ManagedFile(
                    path=".codex/prompts/spec-kitty.specify.md",
                    sha256="abc",
                    file_type="wrapper",
                ),
            ],
        )

        result = verify_installation(tmp_path, ["codex"], manifest)

        assert result.passed
        assert result.errors == []

    def test_agent_with_only_skill_root_passes(self, tmp_path: Path) -> None:
        """An agent that has a skill root but no wrappers still passes coverage."""
        (tmp_path / ".claude" / "skills").mkdir(parents=True)

        manifest = _make_manifest(
            selected_agents=["claude"],
            installed_skill_roots=[".claude/skills/"],
            managed_files=[],
        )

        result = verify_installation(tmp_path, ["claude"], manifest)

        # Coverage passes (agent has a root), but wrapper warning fires
        assert result.passed
        assert any("claude" in e for e in result.errors) is False


# ---------------------------------------------------------------------------
# Check 2: Skill root existence
# ---------------------------------------------------------------------------


class TestSkillRootExistence:
    """Check 2: every installed skill root must exist on disk."""

    def test_missing_skill_root_directory(self, tmp_path: Path) -> None:
        """A root listed in the manifest but absent on disk is an error."""
        # Don't create .claude/skills/ on disk
        manifest = _make_manifest(
            selected_agents=["claude"],
            installed_skill_roots=[".claude/skills/"],
            managed_files=[
                ManagedFile(
                    path=".claude/commands/x.md",
                    sha256="x",
                    file_type="wrapper",
                ),
            ],
        )

        result = verify_installation(tmp_path, ["claude"], manifest)

        assert not result.passed
        assert any(".claude/skills/" in e for e in result.errors)

    def test_all_roots_present_passes(self, tmp_path: Path) -> None:
        """All listed roots existing on disk produces no errors for this check."""
        (tmp_path / ".agents" / "skills").mkdir(parents=True)
        (tmp_path / ".claude" / "skills").mkdir(parents=True)

        manifest = _make_manifest(
            selected_agents=["claude", "codex"],
            installed_skill_roots=[".agents/skills/", ".claude/skills/"],
            managed_files=[
                ManagedFile(
                    path=".claude/commands/x.md",
                    sha256="x",
                    file_type="wrapper",
                ),
                ManagedFile(
                    path=".codex/prompts/x.md",
                    sha256="x",
                    file_type="wrapper",
                ),
            ],
        )

        result = verify_installation(tmp_path, ["claude", "codex"], manifest)

        assert result.passed
        assert result.errors == []


# ---------------------------------------------------------------------------
# Check 3: Wrapper counts
# ---------------------------------------------------------------------------


class TestWrapperCounts:
    """Check 3: warn when an agent has zero managed wrapper files."""

    def test_zero_wrappers_generates_warning(self, tmp_path: Path) -> None:
        """An agent with no wrappers should produce a warning, not an error."""
        (tmp_path / ".claude" / "skills").mkdir(parents=True)

        manifest = _make_manifest(
            selected_agents=["claude"],
            installed_skill_roots=[".claude/skills/"],
            managed_files=[],  # No wrappers at all
        )

        result = verify_installation(tmp_path, ["claude"], manifest)

        # Warnings don't cause failure
        assert result.passed
        assert any("claude" in w and "0 managed wrapper" in w for w in result.warnings)

    def test_agent_with_wrappers_no_warning(self, tmp_path: Path) -> None:
        """An agent with wrappers should not produce a wrapper-count warning."""
        (tmp_path / ".claude" / "skills").mkdir(parents=True)

        manifest = _make_manifest(
            selected_agents=["claude"],
            installed_skill_roots=[".claude/skills/"],
            managed_files=[
                ManagedFile(
                    path=".claude/commands/spec-kitty.specify.md",
                    sha256="abc",
                    file_type="wrapper",
                ),
            ],
        )

        result = verify_installation(tmp_path, ["claude"], manifest)

        assert not any("0 managed wrapper" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Check 4: Duplicate skill names
# ---------------------------------------------------------------------------


class TestDuplicateSkillNames:
    """Check 4: no duplicate skill names in overlapping roots."""

    def test_empty_roots_always_passes(self, tmp_path: Path) -> None:
        """Phase 0 scenario: roots exist but are empty, so no duplicates."""
        (tmp_path / ".agents" / "skills").mkdir(parents=True)
        (tmp_path / ".github" / "skills").mkdir(parents=True)

        # copilot scans both .agents/skills/ and .github/skills/
        manifest = _make_manifest(
            selected_agents=["copilot"],
            installed_skill_roots=[".agents/skills/", ".github/skills/"],
            managed_files=[
                ManagedFile(
                    path=".github/prompts/x.prompt.md",
                    sha256="x",
                    file_type="wrapper",
                ),
            ],
        )

        result = verify_installation(tmp_path, ["copilot"], manifest)

        assert result.passed

    def test_duplicate_skill_file_detected(self, tmp_path: Path) -> None:
        """Same filename in two roots scanned by the same agent is an error."""
        (tmp_path / ".agents" / "skills").mkdir(parents=True)
        (tmp_path / ".github" / "skills").mkdir(parents=True)

        # Create duplicate-named skill file in both roots
        (tmp_path / ".agents" / "skills" / "deploy.md").write_text("v1")
        (tmp_path / ".github" / "skills" / "deploy.md").write_text("v2")

        # copilot scans both roots
        manifest = _make_manifest(
            selected_agents=["copilot"],
            installed_skill_roots=[".agents/skills/", ".github/skills/"],
            managed_files=[
                ManagedFile(
                    path=".github/prompts/x.prompt.md",
                    sha256="x",
                    file_type="wrapper",
                ),
            ],
        )

        result = verify_installation(tmp_path, ["copilot"], manifest)

        assert not result.passed
        assert any("Duplicate skill 'deploy.md'" in e for e in result.errors)
        assert any("copilot" in e for e in result.errors)

    def test_same_name_different_agents_no_error(self, tmp_path: Path) -> None:
        """Same filename in roots scanned by *different* agents is fine."""
        (tmp_path / ".claude" / "skills").mkdir(parents=True)
        (tmp_path / ".qwen" / "skills").mkdir(parents=True)

        (tmp_path / ".claude" / "skills" / "deploy.md").write_text("v1")
        (tmp_path / ".qwen" / "skills" / "deploy.md").write_text("v2")

        manifest = _make_manifest(
            selected_agents=["claude", "qwen"],
            installed_skill_roots=[".claude/skills/", ".qwen/skills/"],
            managed_files=[
                ManagedFile(
                    path=".claude/commands/x.md",
                    sha256="x",
                    file_type="wrapper",
                ),
                ManagedFile(
                    path=".qwen/commands/x.toml",
                    sha256="x",
                    file_type="wrapper",
                ),
            ],
        )

        result = verify_installation(tmp_path, ["claude", "qwen"], manifest)

        # claude and qwen each only scan their own root (NATIVE_ROOT_REQUIRED),
        # so there's no overlap and no duplicate error.
        assert result.passed


# ---------------------------------------------------------------------------
# Wrapper-only agent
# ---------------------------------------------------------------------------


class TestWrapperOnlyAgent:
    """Wrapper-only agents (e.g. q/Amazon Q) should not require skill roots."""

    def test_wrapper_only_passes_without_skill_root(self, tmp_path: Path) -> None:
        """A wrapper-only agent with wrappers but no skill roots passes."""
        manifest = _make_manifest(
            selected_agents=["q"],
            installed_skill_roots=[],
            managed_files=[
                ManagedFile(
                    path=".amazonq/prompts/spec-kitty.specify.md",
                    sha256="abc",
                    file_type="wrapper",
                ),
            ],
        )

        result = verify_installation(tmp_path, ["q"], manifest)

        assert result.passed
        assert result.errors == []

    def test_wrapper_only_no_wrappers_fails_coverage(self, tmp_path: Path) -> None:
        """A wrapper-only agent with no wrappers at all fails coverage."""
        manifest = _make_manifest(
            selected_agents=["q"],
            installed_skill_roots=[],
            managed_files=[],
        )

        result = verify_installation(tmp_path, ["q"], manifest)

        assert not result.passed
        assert any("q" in e and "no managed skill root or wrapper root" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases and combined scenarios."""

    def test_no_agents_passes(self, tmp_path: Path) -> None:
        """No selected agents means nothing to verify -- passes trivially."""
        manifest = _make_manifest()

        result = verify_installation(tmp_path, [], manifest)

        assert result.passed
        assert result.errors == []
        assert result.warnings == []

    def test_multiple_errors_collected(self, tmp_path: Path) -> None:
        """Multiple failures accumulate in the errors list."""
        # No roots created on disk; codex has no wrappers
        manifest = _make_manifest(
            selected_agents=["claude", "codex"],
            installed_skill_roots=[".claude/skills/"],
            managed_files=[
                ManagedFile(
                    path=".claude/commands/x.md",
                    sha256="x",
                    file_type="wrapper",
                ),
            ],
        )

        result = verify_installation(tmp_path, ["claude", "codex"], manifest)

        assert not result.passed
        # At least 2 errors: missing root on disk + codex no coverage
        assert len(result.errors) >= 2
