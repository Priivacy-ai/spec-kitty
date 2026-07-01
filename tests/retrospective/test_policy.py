"""Tests for RetrospectivePolicy resolver, models, and malformed-input handling.

Coverage target: ≥ 90% of src/specify_cli/retrospective/policy.py

Test classes:
    TestPolicyDefaults       — T001: model construction, defaults, invariants
    TestResolver             — T002: resolve_policy with charter / config / defaults
    TestPrecedenceDelegation — T003: charter retrospective.precedence: config
    TestMalformedInput       — T004: PolicyResolutionError shapes for all failure modes
    TestEnvObservation       — T005: env-var observation in source_map (env never wins)

FR refs: FR-001, FR-002, FR-003, FR-004, FR-015, FR-024
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]


from specify_cli.retrospective.policy import (
    PolicyResolutionError,
    RetrospectivePermissions,
    RetrospectivePolicy,
    _default_source_map,
    default_policy,
    resolve_policy,
)
from tests.retrospective.conftest import (
    write_charter,
    write_charter_with_retrospective,
    write_config,
    write_config_with_retrospective,
)


# =============================================================================
# TestPolicyDefaults (T001)
# =============================================================================


class TestPolicyDefaults:
    """Verify built-in model defaults, invariants, and the default_policy() factory."""

    def test_default_policy_returns_correct_fields(self) -> None:
        """default_policy() returns all expected fields per FR-002."""
        p = default_policy()
        assert p.enabled is True
        assert p.timing == "post_completion"
        assert p.failure_policy == "warn"
        assert p.write_record is True
        assert p.generate_proposals is True
        assert p.apply_proposals == "require_human"
        assert p.generator == "python"
        assert p.precedence is None

    def test_default_permissions_all_correct(self) -> None:
        """All permission defaults match spec (C-005 invariant: structural stays False)."""
        p = default_policy()
        perms = p.permissions
        assert perms.write_record is True
        assert perms.inspect_mission_artifacts is True
        assert perms.propose_glossary_changes is True
        assert perms.propose_drg_changes is True
        assert perms.propose_doctrine_changes is True
        assert perms.apply_low_risk_changes is False
        assert perms.apply_structural_changes is False

    def test_apply_structural_changes_c005_invariant(self) -> None:
        """default_policy() NEVER sets apply_structural_changes=True (C-005)."""
        p = default_policy()
        assert p.permissions.apply_structural_changes is False

    def test_permissions_can_opt_in_structural(self) -> None:
        """Operators CAN explicitly construct permissions with apply_structural_changes=True."""
        perms = RetrospectivePermissions(apply_structural_changes=True)
        assert perms.apply_structural_changes is True

    def test_two_default_policies_are_independent(self) -> None:
        """Each call to default_policy() produces independent objects."""
        p1 = default_policy()
        p2 = default_policy()
        p1.enabled = False
        assert p2.enabled is True

    def test_permissions_independence(self) -> None:
        """Mutations to one default policy's permissions don't affect another."""
        p1 = default_policy()
        p2 = default_policy()
        p1.permissions.apply_low_risk_changes = True
        assert p2.permissions.apply_low_risk_changes is False

    def test_default_source_map_has_all_leaf_keys(self) -> None:
        """_default_source_map() covers every leaf key of RetrospectivePolicy."""
        sm = _default_source_map()
        expected = {
            "enabled", "timing", "failure_policy", "write_record",
            "generate_proposals", "apply_proposals",
            "permissions.write_record", "permissions.inspect_mission_artifacts",
            "permissions.propose_glossary_changes", "permissions.propose_drg_changes",
            "permissions.propose_doctrine_changes", "permissions.apply_low_risk_changes",
            "permissions.apply_structural_changes",
            "precedence", "generator",
        }
        assert set(sm.keys()) == expected

    def test_default_source_map_all_default_sentinels(self) -> None:
        """Every entry in the default source_map is '<default>'."""
        sm = _default_source_map()
        for key, val in sm.items():
            assert val == "<default>", f"Expected '<default>' for {key!r}, got {val!r}"

    def test_retrospective_permissions_dataclass_defaults(self) -> None:
        """RetrospectivePermissions() without args uses all defaults."""
        perms = RetrospectivePermissions()
        assert perms.write_record is True
        assert perms.apply_structural_changes is False

    def test_retrospective_policy_dataclass_defaults(self) -> None:
        """RetrospectivePolicy() without args uses all defaults."""
        pol = RetrospectivePolicy()
        assert pol.enabled is True
        assert pol.permissions.apply_structural_changes is False


# =============================================================================
# TestResolver (T002)
# =============================================================================


class TestResolver:
    """Verify resolve_policy() with various charter / config / default combinations."""

    def test_empty_project_returns_defaults(self, tmp_path: Path) -> None:
        """No charter, no config → all fields from built-in defaults."""
        policy, source_map = resolve_policy(tmp_path)
        expected = default_policy()
        assert policy.enabled == expected.enabled
        assert policy.timing == expected.timing
        assert policy.failure_policy == expected.failure_policy
        for key, val in source_map.items():
            assert val == "<default>", f"{key!r} should be '<default>', got {val!r}"

    def test_charter_only_overrides_enabled(self, tmp_path: Path) -> None:
        """Charter sets enabled=false; source_map cites charter; config absent."""
        write_charter_with_retrospective(tmp_path, {"enabled": False})
        policy, source_map = resolve_policy(tmp_path)
        assert policy.enabled is False
        charter_path = ".kittify/charter/charter.md"
        assert source_map["enabled"].startswith(charter_path)
        # Other fields stay at default
        assert source_map["timing"] == "<default>"

    def test_charter_only_overrides_timing(self, tmp_path: Path) -> None:
        """Charter sets timing=before_completion; other fields default."""
        write_charter_with_retrospective(tmp_path, {"timing": "before_completion"})
        policy, source_map = resolve_policy(tmp_path)
        assert policy.timing == "before_completion"
        assert ".kittify/charter/charter.md" in source_map["timing"]
        assert source_map["enabled"] == "<default>"

    def test_config_only_overrides_failure_policy(self, tmp_path: Path) -> None:
        """Config sets failure_policy=block; no charter; source_map cites config."""
        write_config_with_retrospective(tmp_path, {"failure_policy": "block"})
        policy, source_map = resolve_policy(tmp_path)
        assert policy.failure_policy == "block"
        assert source_map["failure_policy"] == ".kittify/config.yaml#retrospective.failure_policy"
        assert source_map["enabled"] == "<default>"

    def test_config_only_overrides_permissions(self, tmp_path: Path) -> None:
        """Config sets a permission sub-field; source_map reflects it."""
        write_config_with_retrospective(
            tmp_path, {"permissions": {"apply_low_risk_changes": True}}
        )
        policy, source_map = resolve_policy(tmp_path)
        assert policy.permissions.apply_low_risk_changes is True
        assert "permissions.apply_low_risk_changes" in source_map
        assert ".kittify/config.yaml" in source_map["permissions.apply_low_risk_changes"]

    def test_charter_wins_over_config_default_precedence(self, tmp_path: Path) -> None:
        """Charter says enabled=false; config says enabled=true; charter wins."""
        write_charter_with_retrospective(tmp_path, {"enabled": False})
        write_config_with_retrospective(tmp_path, {"enabled": True})
        policy, source_map = resolve_policy(tmp_path)
        assert policy.enabled is False
        assert ".kittify/charter/charter.md" in source_map["enabled"]

    def test_config_fills_charter_gap(self, tmp_path: Path) -> None:
        """Charter sets timing; config sets failure_policy; both sources respected."""
        write_charter_with_retrospective(tmp_path, {"timing": "before_completion"})
        write_config_with_retrospective(tmp_path, {"failure_policy": "block"})
        policy, source_map = resolve_policy(tmp_path)
        assert policy.timing == "before_completion"
        assert policy.failure_policy == "block"
        assert ".kittify/charter/charter.md" in source_map["timing"]
        assert ".kittify/config.yaml" in source_map["failure_policy"]

    def test_resolve_policy_is_deterministic(self, tmp_path: Path) -> None:
        """resolve_policy() is byte-deterministic given the same input (golden snapshot)."""
        write_charter_with_retrospective(tmp_path, {"timing": "before_completion"})
        write_config_with_retrospective(tmp_path, {"failure_policy": "block"})
        policy1, sm1 = resolve_policy(tmp_path)
        policy2, sm2 = resolve_policy(tmp_path)
        assert policy1.timing == policy2.timing
        assert policy1.failure_policy == policy2.failure_policy
        assert sm1 == sm2

    def test_charter_no_retrospective_block_uses_defaults(self, tmp_path: Path) -> None:
        """Charter exists but has no retrospective: key → falls through to defaults."""
        write_charter(tmp_path, frontmatter={"mode": "autonomous"})
        policy, source_map = resolve_policy(tmp_path)
        assert policy.enabled is True
        assert all(v == "<default>" for v in source_map.values())

    def test_source_map_covers_all_leaf_keys(self, tmp_path: Path) -> None:
        """Resolved source_map always contains all expected leaf keys."""
        write_charter_with_retrospective(tmp_path, {"enabled": False})
        _, source_map = resolve_policy(tmp_path)
        required_keys = {
            "enabled", "timing", "failure_policy", "write_record",
            "generate_proposals", "apply_proposals",
            "permissions.write_record", "permissions.inspect_mission_artifacts",
            "permissions.propose_glossary_changes", "permissions.propose_drg_changes",
            "permissions.propose_doctrine_changes", "permissions.apply_low_risk_changes",
            "permissions.apply_structural_changes",
            "precedence", "generator",
        }
        missing = required_keys - set(source_map.keys())
        assert not missing, f"source_map missing keys: {missing}"

    def test_charter_sets_generator_field(self, tmp_path: Path) -> None:
        """Charter can set the generator field; source_map reflects it."""
        write_charter_with_retrospective(tmp_path, {"generator": "python"})
        policy, source_map = resolve_policy(tmp_path)
        assert policy.generator == "python"
        assert ".kittify/charter/charter.md" in source_map["generator"]


# =============================================================================
# TestPrecedenceDelegation (T003)
# =============================================================================


class TestPrecedenceDelegation:
    """Verify charter retrospective.precedence: config delegation semantics."""

    def test_charter_explicit_field_preserved_under_config_precedence(
        self, tmp_path: Path
    ) -> None:
        """Charter says enabled=false + precedence=config; config says enabled=true.
        Charter's explicit enabled=false is preserved.
        """
        write_charter_with_retrospective(
            tmp_path, {"enabled": False, "precedence": "config"}
        )
        write_config_with_retrospective(tmp_path, {"enabled": True})
        policy, source_map = resolve_policy(tmp_path)
        assert policy.enabled is False
        assert ".kittify/charter/charter.md" in source_map["enabled"]

    def test_config_wins_for_unset_charter_field_under_config_precedence(
        self, tmp_path: Path
    ) -> None:
        """Charter sets precedence=config but not failure_policy; config sets block.
        Config wins for the gap field.
        """
        write_charter_with_retrospective(tmp_path, {"precedence": "config"})
        write_config_with_retrospective(tmp_path, {"failure_policy": "block"})
        policy, source_map = resolve_policy(tmp_path)
        assert policy.failure_policy == "block"
        assert ".kittify/config.yaml" in source_map["failure_policy"]

    def test_no_precedence_key_config_only_fills_gaps(self, tmp_path: Path) -> None:
        """Charter sets enabled=false without precedence=config.
        Config sets failure_policy but NOT enabled.
        Charter keeps enabled; config fills failure_policy.
        """
        write_charter_with_retrospective(tmp_path, {"enabled": False})
        write_config_with_retrospective(tmp_path, {"failure_policy": "block"})
        policy, source_map = resolve_policy(tmp_path)
        assert policy.enabled is False
        assert policy.failure_policy == "block"
        assert ".kittify/charter/charter.md" in source_map["enabled"]
        assert ".kittify/config.yaml" in source_map["failure_policy"]

    def test_precedence_field_threaded_onto_policy(self, tmp_path: Path) -> None:
        """When charter sets precedence=config, resolved policy.precedence == 'config'."""
        write_charter_with_retrospective(tmp_path, {"precedence": "config"})
        policy, _ = resolve_policy(tmp_path)
        assert policy.precedence == "config"

    def test_config_fills_all_defaults_when_charter_sets_only_precedence(
        self, tmp_path: Path
    ) -> None:
        """Charter only sets precedence=config; config sets timing and failure_policy.
        Both config fields should win over defaults.
        """
        write_charter_with_retrospective(tmp_path, {"precedence": "config"})
        write_config_with_retrospective(
            tmp_path, {"timing": "before_completion", "failure_policy": "block"}
        )
        policy, source_map = resolve_policy(tmp_path)
        assert policy.timing == "before_completion"
        assert policy.failure_policy == "block"
        assert ".kittify/config.yaml" in source_map["timing"]
        assert ".kittify/config.yaml" in source_map["failure_policy"]

    def test_source_map_reflects_winning_source_per_field_under_delegation(
        self, tmp_path: Path
    ) -> None:
        """Under precedence=config, source_map accurately reflects winner per field."""
        write_charter_with_retrospective(
            tmp_path, {"enabled": False, "timing": "before_completion", "precedence": "config"}
        )
        write_config_with_retrospective(
            tmp_path, {"failure_policy": "block", "timing": "post_completion"}
        )
        policy, source_map = resolve_policy(tmp_path)
        # Charter set timing explicitly → charter wins
        assert policy.timing == "before_completion"
        assert ".kittify/charter/charter.md" in source_map["timing"]
        # Config set failure_policy; charter did not → config wins
        assert policy.failure_policy == "block"
        assert ".kittify/config.yaml" in source_map["failure_policy"]


# =============================================================================
# TestMalformedInput (T004)
# =============================================================================


class TestMalformedInput:
    """Verify PolicyResolutionError shapes for every malformed-input mode (FR-024)."""

    # --- Invalid YAML ---

    def test_invalid_yaml_config_raises_policy_resolution_error(
        self, tmp_path: Path
    ) -> None:
        """Config with invalid YAML raises PolicyResolutionError(reason='invalid_yaml')."""
        write_config(tmp_path, "retrospective:\n  timing: [\nunot closed")
        with pytest.raises(PolicyResolutionError) as exc_info:
            resolve_policy(tmp_path)
        err = exc_info.value
        assert err.reason == "invalid_yaml"
        assert ".kittify/config.yaml" in err.source

    def test_invalid_yaml_config_error_has_detail(self, tmp_path: Path) -> None:
        """PolicyResolutionError for invalid YAML includes parser message in detail."""
        # A tab character inside a YAML mapping block triggers a parse error
        write_config(tmp_path, "retrospective:\n\ttiming: post_completion\n")
        with pytest.raises(PolicyResolutionError) as exc_info:
            resolve_policy(tmp_path)
        assert exc_info.value.detail  # non-empty

    def test_invalid_yaml_charter_raises_policy_resolution_error(
        self, tmp_path: Path
    ) -> None:
        """Charter with invalid YAML frontmatter raises PolicyResolutionError."""
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        (charter_dir / "charter.md").write_text(
            "---\nretrospective:\n  timing: [\n  unclosed\n---\n# body\n",
            encoding="utf-8",
        )
        with pytest.raises(PolicyResolutionError) as exc_info:
            resolve_policy(tmp_path)
        err = exc_info.value
        assert err.reason == "invalid_yaml"

    # --- Wrong type for retrospective block ---

    def test_config_retrospective_not_dict_raises_invalid_type(
        self, tmp_path: Path
    ) -> None:
        """retrospective: 'not_a_dict' → reason='invalid_type_for_retrospective_block'."""
        write_config(tmp_path, "retrospective: not_a_dict\n")
        with pytest.raises(PolicyResolutionError) as exc_info:
            resolve_policy(tmp_path)
        assert exc_info.value.reason == "invalid_type_for_retrospective_block"

    def test_config_retrospective_list_raises_invalid_type(
        self, tmp_path: Path
    ) -> None:
        """retrospective: [list] → reason='invalid_type_for_retrospective_block'."""
        write_config(tmp_path, "retrospective:\n  - item\n  - item2\n")
        with pytest.raises(PolicyResolutionError) as exc_info:
            resolve_policy(tmp_path)
        assert exc_info.value.reason == "invalid_type_for_retrospective_block"

    def test_charter_retrospective_not_dict_raises_invalid_type(
        self, tmp_path: Path
    ) -> None:
        """Charter retrospective: 42 → reason='invalid_type_for_retrospective_block'."""
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        (charter_dir / "charter.md").write_text(
            "---\nretrospective: 42\n---\n# body\n",
            encoding="utf-8",
        )
        with pytest.raises(PolicyResolutionError) as exc_info:
            resolve_policy(tmp_path)
        assert exc_info.value.reason == "invalid_type_for_retrospective_block"

    # --- Invalid enum value ---

    def test_invalid_enum_timing_raises_policy_resolution_error(
        self, tmp_path: Path
    ) -> None:
        """retrospective.timing: foo → reason='invalid_enum' with helpful detail."""
        write_config_with_retrospective(tmp_path, {"timing": "foo"})
        with pytest.raises(PolicyResolutionError) as exc_info:
            resolve_policy(tmp_path)
        err = exc_info.value
        assert err.reason == "invalid_enum"
        assert "timing" in err.detail
        assert "foo" in err.detail

    def test_invalid_enum_failure_policy(self, tmp_path: Path) -> None:
        """retrospective.failure_policy: bad → reason='invalid_enum'."""
        write_config_with_retrospective(tmp_path, {"failure_policy": "explode"})
        with pytest.raises(PolicyResolutionError) as exc_info:
            resolve_policy(tmp_path)
        assert exc_info.value.reason == "invalid_enum"
        assert "failure_policy" in exc_info.value.detail

    def test_invalid_enum_apply_proposals(self, tmp_path: Path) -> None:
        """retrospective.apply_proposals: bad → reason='invalid_enum'."""
        write_config_with_retrospective(tmp_path, {"apply_proposals": "auto"})
        with pytest.raises(PolicyResolutionError) as exc_info:
            resolve_policy(tmp_path)
        assert exc_info.value.reason == "invalid_enum"

    # --- Unknown keys ---

    def test_unknown_key_strict_mode_raises_policy_resolution_error(
        self, tmp_path: Path
    ) -> None:
        """Unknown key with strict_keys=true → reason='unknown_key'."""
        write_config(
            tmp_path,
            "retrospective:\n  strict_keys: true\n  unknown_field: value\n",
        )
        with pytest.raises(PolicyResolutionError) as exc_info:
            resolve_policy(tmp_path)
        err = exc_info.value
        assert err.reason == "unknown_key"
        assert "unknown_field" in err.detail

    def test_unknown_key_lenient_mode_no_error(self, tmp_path: Path) -> None:
        """Unknown key with default strict_keys (false) → warning, no error."""
        write_config(
            tmp_path,
            "retrospective:\n  totally_unknown: value\n  timing: post_completion\n",
        )
        policy, source_map = resolve_policy(tmp_path)  # must NOT raise
        assert policy.timing == "post_completion"

    def test_unknown_key_lenient_mode_known_fields_still_apply(
        self, tmp_path: Path
    ) -> None:
        """Lenient mode: unknown keys are skipped but known keys are applied."""
        write_config(
            tmp_path,
            "retrospective:\n  unknown_key: garbage\n  failure_policy: block\n",
        )
        policy, _ = resolve_policy(tmp_path)
        assert policy.failure_policy == "block"

    # --- PolicyResolutionError structure ---

    def test_policy_resolution_error_fields(self, tmp_path: Path) -> None:
        """PolicyResolutionError carries source, reason, and detail attributes."""
        write_config(tmp_path, "retrospective: not_a_dict\n")
        with pytest.raises(PolicyResolutionError) as exc_info:
            resolve_policy(tmp_path)
        err = exc_info.value
        assert hasattr(err, "source")
        assert hasattr(err, "reason")
        assert hasattr(err, "detail")
        assert isinstance(err.source, str)
        assert isinstance(err.reason, str)
        assert isinstance(err.detail, str)

    def test_policy_resolution_error_is_exception(self) -> None:
        """PolicyResolutionError is a subclass of Exception."""
        err = PolicyResolutionError(source="x", reason="invalid_yaml", detail="msg")
        assert isinstance(err, Exception)

    def test_resolver_does_not_raise_non_policy_resolution_errors(
        self, tmp_path: Path
    ) -> None:
        """Resolver never raises non-PolicyResolutionError exceptions."""
        # Valid config — should work without any error
        write_config_with_retrospective(tmp_path, {"enabled": True})
        try:
            resolve_policy(tmp_path)
        except PolicyResolutionError:
            pass  # OK if it raises PolicyResolutionError
        except Exception as exc:
            pytest.fail(f"Raised non-PolicyResolutionError: {type(exc).__name__}: {exc}")

    def test_unclosed_charter_frontmatter(self, tmp_path: Path) -> None:
        """Charter with unclosed --- block → PolicyResolutionError reason=invalid_yaml."""
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        (charter_dir / "charter.md").write_text(
            "---\nretrospective:\n  enabled: false\n# no closing ---\n",
            encoding="utf-8",
        )
        with pytest.raises(PolicyResolutionError) as exc_info:
            resolve_policy(tmp_path)
        assert exc_info.value.reason == "invalid_yaml"


# =============================================================================
# TestEnvObservation (T005)
# =============================================================================


class TestEnvObservation:
    """Verify env-var observation in source_map (FR-015 deprecation cycle).

    Env vars are NEVER applied to the policy. They only appear in source_map
    for observability when the field came from '<default>' (no charter/config opinion).

    NOTE: These tests mutate os.environ via the ``env`` injection parameter.
    No ``monkeypatch.setenv`` or direct os.environ mutation is used here.
    """

    def test_retro_env_set_and_no_charter_config_records_in_source_map(
        self, tmp_path: Path
    ) -> None:
        """SPEC_KITTY_RETROSPECTIVE=1 with no charter/config → source_map records env."""
        policy, source_map = resolve_policy(
            tmp_path, env={"SPEC_KITTY_RETROSPECTIVE": "1"}
        )
        assert source_map["enabled"] == "<env:SPEC_KITTY_RETROSPECTIVE>"
        # Policy is NOT changed — built-in default is already True
        assert policy.enabled is True

    def test_retro_env_zero_records_in_source_map_policy_unchanged(
        self, tmp_path: Path
    ) -> None:
        """SPEC_KITTY_RETROSPECTIVE=0 with no charter/config → source_map records env.
        Resolved enabled stays True (env never wins; default is True).
        """
        policy, source_map = resolve_policy(
            tmp_path, env={"SPEC_KITTY_RETROSPECTIVE": "0"}
        )
        assert source_map["enabled"] == "<env:SPEC_KITTY_RETROSPECTIVE>"
        assert policy.enabled is True  # env never wins

    def test_charter_enabled_false_env_retro_set_charter_wins(
        self, tmp_path: Path
    ) -> None:
        """Charter enabled=false + SPEC_KITTY_RETROSPECTIVE=1 → charter wins.
        source_map shows charter, not env.
        """
        write_charter_with_retrospective(tmp_path, {"enabled": False})
        policy, source_map = resolve_policy(
            tmp_path, env={"SPEC_KITTY_RETROSPECTIVE": "1"}
        )
        assert policy.enabled is False
        assert ".kittify/charter/charter.md" in source_map["enabled"]
        # Env observation does NOT appear — charter is authoritative
        assert "<env:" not in source_map["enabled"]

    def test_mode_env_set_records_in_source_map(self, tmp_path: Path) -> None:
        """SPEC_KITTY_MODE set with no charter/config → timing + failure_policy observe env."""
        policy, source_map = resolve_policy(
            tmp_path, env={"SPEC_KITTY_MODE": "autonomous"}
        )
        assert source_map["timing"] == "<env:SPEC_KITTY_MODE>"
        assert source_map["failure_policy"] == "<env:SPEC_KITTY_MODE>"
        # Policy fields still at defaults
        assert policy.timing == "post_completion"
        assert policy.failure_policy == "warn"

    def test_charter_timing_set_env_mode_no_observation(self, tmp_path: Path) -> None:
        """Charter sets timing; SPEC_KITTY_MODE set → charter wins; no env in source_map for timing."""
        write_charter_with_retrospective(tmp_path, {"timing": "before_completion"})
        policy, source_map = resolve_policy(
            tmp_path, env={"SPEC_KITTY_MODE": "autonomous"}
        )
        assert policy.timing == "before_completion"
        assert "<env:" not in source_map["timing"]
        # failure_policy was not set by charter → env observation appears
        assert source_map["failure_policy"] == "<env:SPEC_KITTY_MODE>"

    def test_no_env_vars_all_source_map_defaults(self, tmp_path: Path) -> None:
        """No charter, no config, no env vars → all source_map entries are '<default>'."""
        policy, source_map = resolve_policy(tmp_path, env={})
        for key, val in source_map.items():
            assert val == "<default>", f"{key!r}: expected '<default>', got {val!r}"

    def test_env_observation_does_not_mutate_policy_values(
        self, tmp_path: Path
    ) -> None:
        """Env vars never change the resolved policy field values."""
        policy_no_env, _ = resolve_policy(tmp_path, env={})
        policy_with_env, _ = resolve_policy(
            tmp_path, env={"SPEC_KITTY_RETROSPECTIVE": "0", "SPEC_KITTY_MODE": "autonomous"}
        )
        assert policy_no_env.enabled == policy_with_env.enabled
        assert policy_no_env.timing == policy_with_env.timing
        assert policy_no_env.failure_policy == policy_with_env.failure_policy

    def test_config_field_set_env_no_observation_for_that_field(
        self, tmp_path: Path
    ) -> None:
        """Config sets enabled=false; SPEC_KITTY_RETROSPECTIVE set → config wins, no env in source_map."""
        write_config_with_retrospective(tmp_path, {"enabled": False})
        policy, source_map = resolve_policy(
            tmp_path, env={"SPEC_KITTY_RETROSPECTIVE": "1"}
        )
        assert policy.enabled is False
        assert ".kittify/config.yaml" in source_map["enabled"]
        assert "<env:" not in source_map["enabled"]
