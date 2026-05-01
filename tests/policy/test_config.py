"""Tests for policy configuration loading."""

from specify_cli.policy.config import (
    CommitGuardConfig,
    MergeGateConfig,
    PolicyConfig,
    RiskPolicyConfig,
    load_policy_config,
)


class TestDefaults:
    def test_all_defaults(self):
        config = PolicyConfig()
        assert config.risk.enabled is True
        assert config.risk.mode == "warn"
        assert config.risk.threshold == 0.6
        assert config.commit_guard.enabled is True
        assert config.commit_guard.mode == "warn"
        assert config.merge_gates.enabled is True
        assert config.merge_gates.mode == "warn"

    def test_invalid_mode_defaults_to_warn(self):
        r = RiskPolicyConfig(mode="invalid")
        assert r.mode == "warn"
        c = CommitGuardConfig(mode="bogus")
        assert c.mode == "warn"
        m = MergeGateConfig(mode="")
        assert m.mode == "warn"


class TestLoadFromYaml:
    def test_missing_file_returns_defaults(self, tmp_path):
        config = load_policy_config(tmp_path)
        assert config.risk.mode == "warn"
        assert config.commit_guard.mode == "warn"
        assert config.merge_gates.mode == "warn"

    def test_missing_policy_section_returns_defaults(self, tmp_path):
        (tmp_path / ".kittify").mkdir()
        (tmp_path / ".kittify" / "config.yaml").write_text("agents:\n  available: [claude]\n")
        config = load_policy_config(tmp_path)
        assert config.risk.mode == "warn"

    def test_full_policy_section(self, tmp_path):
        (tmp_path / ".kittify").mkdir()
        (tmp_path / ".kittify" / "config.yaml").write_text(
            "policy:\n"
            "  risk:\n"
            "    enabled: true\n"
            "    mode: block\n"
            "    threshold: 0.8\n"
            "  commit_guard:\n"
            "    enabled: false\n"
            "    mode: off\n"
            "  merge_gates:\n"
            "    mode: block\n"
            "    require_review_approval: false\n"
        )
        config = load_policy_config(tmp_path)
        assert config.risk.mode == "block"
        assert config.risk.threshold == 0.8
        assert config.commit_guard.enabled is False
        assert config.commit_guard.mode == "off"
        assert config.merge_gates.mode == "block"
        assert config.merge_gates.require_review_approval is False

    def test_partial_policy_section(self, tmp_path):
        (tmp_path / ".kittify").mkdir()
        (tmp_path / ".kittify" / "config.yaml").write_text("policy:\n  risk:\n    mode: block\n")
        config = load_policy_config(tmp_path)
        assert config.risk.mode == "block"
        # Unspecified sections get defaults
        assert config.commit_guard.mode == "warn"
        assert config.merge_gates.mode == "warn"
