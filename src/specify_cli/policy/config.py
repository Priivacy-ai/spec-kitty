"""Policy configuration schema and loader.

Reads the ``policy`` section from ``.kittify/config.yaml``.
Returns all-defaults when the section is absent, so existing
projects are never broken on upgrade.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

VALID_MODES = frozenset({"warn", "block", "off"})


@dataclass(frozen=True)
class RiskPolicyConfig:
    """Parallelization risk scoring policy."""

    enabled: bool = True
    mode: str = "warn"
    threshold: float = 0.6

    def __post_init__(self) -> None:
        if self.mode not in VALID_MODES:
            object.__setattr__(self, "mode", "warn")


@dataclass(frozen=True)
class CommitGuardConfig:
    """Pre-commit ownership guard policy."""

    enabled: bool = True
    mode: str = "warn"
    block_kitty_specs: bool = True
    enforce_ownership: bool = True

    def __post_init__(self) -> None:
        if self.mode not in VALID_MODES:
            object.__setattr__(self, "mode", "warn")


@dataclass(frozen=True)
class MergeGateConfig:
    """Evidence-based merge gate policy."""

    enabled: bool = True
    mode: str = "warn"
    require_review_approval: bool = True
    require_risk_check: bool = True
    require_deps_complete: bool = True

    def __post_init__(self) -> None:
        if self.mode not in VALID_MODES:
            object.__setattr__(self, "mode", "warn")


@dataclass(frozen=True)
class PolicyConfig:
    """Top-level policy configuration."""

    risk: RiskPolicyConfig = field(default_factory=RiskPolicyConfig)
    commit_guard: CommitGuardConfig = field(default_factory=CommitGuardConfig)
    merge_gates: MergeGateConfig = field(default_factory=MergeGateConfig)


def load_policy_config(repo_root: Path) -> PolicyConfig:
    """Load policy configuration from .kittify/config.yaml.

    Returns all-defaults when the file or ``policy`` section is absent.
    """
    config_file = repo_root / ".kittify" / "config.yaml"

    if not config_file.exists():
        return PolicyConfig()

    try:
        from ruamel.yaml import YAML

        yaml = YAML()
        yaml.preserve_quotes = True
        with open(config_file) as f:
            data = yaml.load(f) or {}
    except Exception as exc:
        logger.warning("Failed to read config.yaml for policy: %s", exc)
        return PolicyConfig()

    policy_data = data.get("policy")
    if not isinstance(policy_data, dict):
        return PolicyConfig()

    return _parse_policy(policy_data)


def _parse_policy(data: dict[str, Any]) -> PolicyConfig:
    """Parse the ``policy`` dict from config.yaml."""
    return PolicyConfig(
        risk=_parse_risk(data.get("risk", {})),
        commit_guard=_parse_commit_guard(data.get("commit_guard", {})),
        merge_gates=_parse_merge_gates(data.get("merge_gates", {})),
    )


def _parse_risk(data: Any) -> RiskPolicyConfig:
    if not isinstance(data, dict):
        return RiskPolicyConfig()
    return RiskPolicyConfig(
        enabled=bool(data.get("enabled", True)),
        mode=str(data.get("mode", "warn")),
        threshold=float(data.get("threshold", 0.6)),
    )


def _parse_commit_guard(data: Any) -> CommitGuardConfig:
    if not isinstance(data, dict):
        return CommitGuardConfig()
    return CommitGuardConfig(
        enabled=bool(data.get("enabled", True)),
        mode=str(data.get("mode", "warn")),
        block_kitty_specs=bool(data.get("block_kitty_specs", True)),
        enforce_ownership=bool(data.get("enforce_ownership", True)),
    )


def _parse_merge_gates(data: Any) -> MergeGateConfig:
    if not isinstance(data, dict):
        return MergeGateConfig()
    return MergeGateConfig(
        enabled=bool(data.get("enabled", True)),
        mode=str(data.get("mode", "warn")),
        require_review_approval=bool(data.get("require_review_approval", True)),
        require_risk_check=bool(data.get("require_risk_check", True)),
        require_deps_complete=bool(data.get("require_deps_complete", True)),
    )
