"""Exhaustive parametrized tests for skill root resolution."""

from __future__ import annotations

import pytest

from specify_cli.core.agent_surface import AGENT_SURFACE_CONFIG
from specify_cli.skills.roots import resolve_skill_roots


# ---------------------------------------------------------------------------
# Auto mode tests
# ---------------------------------------------------------------------------


class TestAutoMode:
    """Tests for mode='auto' (default)."""

    def test_mixed_agents(self) -> None:
        """shared + native agents produce both root types."""
        roots = resolve_skill_roots(["claude", "codex", "opencode"], mode="auto")
        assert ".agents/skills/" in roots  # codex, opencode are shared-root-capable
        assert ".claude/skills/" in roots  # claude is native-root-required
        assert len(roots) == 2

    def test_wrapper_only_returns_empty(self) -> None:
        """Only wrapper-only agents produce no roots."""
        assert resolve_skill_roots(["q"], mode="auto") == []

    def test_native_only_no_shared_root(self) -> None:
        """Only native-required agents: no .agents/skills/."""
        roots = resolve_skill_roots(["claude", "qwen"], mode="auto")
        assert ".agents/skills/" not in roots
        assert ".claude/skills/" in roots
        assert ".qwen/skills/" in roots

    def test_all_agents(self) -> None:
        """All 12 agents produce shared root + all native roots."""
        all_agents = list(AGENT_SURFACE_CONFIG.keys())
        roots = resolve_skill_roots(all_agents, mode="auto")
        assert ".agents/skills/" in roots
        assert ".claude/skills/" in roots
        assert ".qwen/skills/" in roots
        assert ".kilocode/skills/" in roots

    def test_only_shared_root_capable(self) -> None:
        """Only shared-root-capable agents: just .agents/skills/."""
        roots = resolve_skill_roots(["codex", "opencode", "copilot"], mode="auto")
        assert roots == [".agents/skills/"]

    def test_default_mode_is_auto(self) -> None:
        """Calling without mode argument defaults to auto."""
        roots_default = resolve_skill_roots(["claude", "codex"])
        roots_auto = resolve_skill_roots(["claude", "codex"], mode="auto")
        assert roots_default == roots_auto


# ---------------------------------------------------------------------------
# Shared mode tests
# ---------------------------------------------------------------------------


class TestSharedMode:
    """Tests for mode='shared' (currently identical to auto)."""

    def test_shared_same_as_auto(self) -> None:
        """shared produces identical results to auto."""
        agents = ["claude", "codex", "copilot"]
        assert resolve_skill_roots(agents, "shared") == resolve_skill_roots(
            agents, "auto"
        )

    def test_shared_all_agents(self) -> None:
        """shared with all agents matches auto with all agents."""
        all_agents = list(AGENT_SURFACE_CONFIG.keys())
        assert resolve_skill_roots(all_agents, "shared") == resolve_skill_roots(
            all_agents, "auto"
        )


# ---------------------------------------------------------------------------
# Native mode tests
# ---------------------------------------------------------------------------


class TestNativeMode:
    """Tests for mode='native'."""

    def test_copilot_gets_github_root(self) -> None:
        """copilot in native mode uses .github/skills/ not .agents/skills/."""
        roots = resolve_skill_roots(["copilot"], mode="native")
        assert ".github/skills/" in roots
        assert ".agents/skills/" not in roots

    def test_codex_gets_agents_root(self) -> None:
        """codex in native mode uses .agents/skills/ (its only root)."""
        roots = resolve_skill_roots(["codex"], mode="native")
        assert ".agents/skills/" in roots
        assert len(roots) == 1

    def test_claude_gets_native_root(self) -> None:
        """claude in native mode uses .claude/skills/."""
        roots = resolve_skill_roots(["claude"], mode="native")
        assert ".claude/skills/" in roots
        assert len(roots) == 1

    def test_mixed_native(self) -> None:
        """Mixed agents in native mode: vendor roots preferred."""
        roots = resolve_skill_roots(["copilot", "codex", "claude"], mode="native")
        assert ".github/skills/" in roots  # copilot native
        assert ".agents/skills/" in roots  # codex only root
        assert ".claude/skills/" in roots  # claude native
        assert len(roots) == 3

    def test_native_wrapper_only_empty(self) -> None:
        """wrapper-only agent in native mode returns empty."""
        assert resolve_skill_roots(["q"], mode="native") == []

    def test_native_shared_capable_vendor_roots(self) -> None:
        """All shared-root-capable agents with two roots get vendor root."""
        # gemini, cursor, opencode, windsurf, auggie, roo all have vendor roots
        roots = resolve_skill_roots(["gemini", "cursor"], mode="native")
        assert ".gemini/skills/" in roots
        assert ".cursor/skills/" in roots
        assert ".agents/skills/" not in roots


# ---------------------------------------------------------------------------
# Wrappers-only mode tests
# ---------------------------------------------------------------------------


class TestWrappersOnlyMode:
    """Tests for mode='wrappers-only'."""

    @pytest.mark.parametrize(
        "agents",
        [
            ["claude"],
            ["codex"],
            ["claude", "codex", "q"],
            list(AGENT_SURFACE_CONFIG.keys()),
            [],
        ],
    )
    def test_always_empty(self, agents: list[str]) -> None:
        """wrappers-only always returns empty list regardless of agents."""
        assert resolve_skill_roots(agents, mode="wrappers-only") == []


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases and invariants."""

    def test_empty_agents(self) -> None:
        """Empty agent list produces empty roots."""
        assert resolve_skill_roots([], mode="auto") == []

    def test_invalid_mode_raises(self) -> None:
        """Invalid mode raises ValueError with descriptive message."""
        with pytest.raises(ValueError, match="Invalid skills mode"):
            resolve_skill_roots(["claude"], mode="invalid")

    def test_invalid_mode_message_content(self) -> None:
        """ValueError message includes the bad mode and valid options."""
        with pytest.raises(ValueError, match="invalid") as exc_info:
            resolve_skill_roots(["claude"], mode="invalid")
        msg = str(exc_info.value)
        assert "auto" in msg
        assert "native" in msg
        assert "shared" in msg
        assert "wrappers-only" in msg

    def test_results_sorted(self) -> None:
        """Results are always sorted alphabetically."""
        roots = resolve_skill_roots(["qwen", "claude", "codex"], mode="auto")
        assert roots == sorted(roots)

    def test_no_duplicates(self) -> None:
        """No duplicate entries in results."""
        roots = resolve_skill_roots(
            ["codex", "copilot", "opencode"], mode="auto"
        )
        assert len(roots) == len(set(roots))
        # All three are shared-root-capable → only .agents/skills/ once
        assert roots.count(".agents/skills/") == 1

    def test_unknown_agent_key_ignored(self) -> None:
        """Unknown agent keys are silently ignored."""
        roots = resolve_skill_roots(["nonexistent", "claude"], mode="auto")
        assert roots == [".claude/skills/"]

    def test_all_unknown_agents_empty(self) -> None:
        """All unknown agent keys produce empty list."""
        assert resolve_skill_roots(["fake1", "fake2"], mode="auto") == []

    def test_native_all_agents_no_shared_root_for_dual_agents(self) -> None:
        """In native mode, agents with two roots never get .agents/skills/."""
        # copilot, gemini, cursor, opencode, windsurf, auggie, roo
        # all have (.agents/skills/, .<vendor>/skills/) → should get vendor root
        dual_root_agents = [
            "copilot",
            "gemini",
            "cursor",
            "opencode",
            "windsurf",
            "auggie",
            "roo",
        ]
        roots = resolve_skill_roots(dual_root_agents, mode="native")
        # .agents/skills/ should NOT appear since all have vendor alternatives
        assert ".agents/skills/" not in roots
        assert ".github/skills/" in roots  # copilot
        assert ".gemini/skills/" in roots
        assert ".cursor/skills/" in roots
        assert ".opencode/skills/" in roots
        assert ".windsurf/skills/" in roots
        assert ".augment/skills/" in roots  # auggie
        assert ".roo/skills/" in roots

    def test_auto_does_not_include_vendor_roots_for_shared_capable(self) -> None:
        """In auto mode, shared-root-capable agents only get .agents/skills/."""
        roots = resolve_skill_roots(
            ["copilot", "gemini", "cursor"], mode="auto"
        )
        assert roots == [".agents/skills/"]
        # No vendor roots like .github/skills/ in auto mode
        assert ".github/skills/" not in roots
        assert ".gemini/skills/" not in roots
        assert ".cursor/skills/" not in roots
