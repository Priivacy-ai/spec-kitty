"""Default-on policy detection for retrospective lifecycle wiring.

Covers ``specify_cli.retrospective.config.is_retrospective_enabled``:
the compatibility shim delegates to durable retrospective policy. The default
is enabled; durable config/charter policy can opt out.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.retrospective.config import is_retrospective_enabled
from specify_cli.retrospective.policy import PolicyResolutionError

pytestmark = pytest.mark.fast


def _write_charter(repo_root: Path, frontmatter: str) -> None:
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    (charter_dir / "charter.md").write_text(frontmatter, encoding="utf-8")


def test_no_charter_no_env_returns_true(tmp_path: Path) -> None:
    assert is_retrospective_enabled(tmp_path, env={}) is True


def test_charter_with_autonomous_mode_enables(tmp_path: Path) -> None:
    _write_charter(tmp_path, "---\nmode: autonomous\n---\n# Charter\n")
    assert is_retrospective_enabled(tmp_path, env={}) is True


def test_charter_with_human_in_command_mode_enables(tmp_path: Path) -> None:
    _write_charter(tmp_path, "---\nmode: human_in_command\n---\n# Charter\n")
    assert is_retrospective_enabled(tmp_path, env={}) is True


def test_charter_without_mode_clause_still_uses_default_enabled(tmp_path: Path) -> None:
    _write_charter(tmp_path, "---\nproject: spec-kitty\n---\n# Charter\n")
    assert is_retrospective_enabled(tmp_path, env={}) is True


def test_config_policy_can_opt_out(tmp_path: Path) -> None:
    config = tmp_path / ".kittify" / "config.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text("retrospective:\n  enabled: false\n", encoding="utf-8")
    assert is_retrospective_enabled(tmp_path, env={}) is False


def test_env_truthy_enables(tmp_path: Path) -> None:
    assert is_retrospective_enabled(tmp_path, env={"SPEC_KITTY_RETROSPECTIVE": "1"}) is True
    assert is_retrospective_enabled(tmp_path, env={"SPEC_KITTY_RETROSPECTIVE": "true"}) is True
    assert is_retrospective_enabled(tmp_path, env={"SPEC_KITTY_RETROSPECTIVE": "yes"}) is True


def test_env_falsy_does_not_opt_out(tmp_path: Path) -> None:
    assert is_retrospective_enabled(tmp_path, env={"SPEC_KITTY_RETROSPECTIVE": "0"}) is True
    assert is_retrospective_enabled(tmp_path, env={"SPEC_KITTY_RETROSPECTIVE": "false"}) is True
    assert is_retrospective_enabled(tmp_path, env={"SPEC_KITTY_RETROSPECTIVE": ""}) is True


def test_malformed_charter_raises(tmp_path: Path) -> None:
    """Malformed charter frontmatter is fail-closed: the runtime should not
    silently bypass governance because the charter is broken."""
    _write_charter(tmp_path, "---\nmode: autonomous\n# missing closing fence\n")
    with pytest.raises(PolicyResolutionError):
        is_retrospective_enabled(tmp_path, env={})
