"""Yaml-first retrospective policy resolution (FR-005c / SC-002 / C-003).

Mission: ``doctrine-charter-split-unification-01KZ0SRB``, WP06.

Before this WP the retrospective policy resolved *only* from ``charter.md``
YAML frontmatter — a **resolving** read of the display-only prose companion,
which is the invariant violation FR-005 closes.  After it, resolution is
yaml-first:

* ``charter.yaml`` ``governance.retrospective`` is the **authority** and takes
  precedence (SC-002);
* ``charter.md`` frontmatter survives as an **overridden secondary** so legacy
  ``charter.md``-only projects keep resolving (C-003);
* ``.kittify/config.yaml`` keeps its existing role beneath both.

Per NFR-001 the yaml-only presence fixture DELETES/omits ``charter.md``
entirely — it never seeds both files, which would make the presence proof
vacuous.

Test classes:
    TestYamlOnlyResolution        — case 1 (SC-002 presence, NFR-001)
    TestYamlWinsOverMarkdown      — case 2 (SC-002 precedence)
    TestLegacyMarkdownOnly        — case 3 (C-003 backward compat)
    TestYamlVsConfigPrecedence    — charter.yaml participates in config gating
    TestMalformedCharterYaml      — typed error, never a raw ValidationError
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]


from specify_cli.retrospective.policy import (
    PolicyResolutionError,
    resolve_policy,
)
from tests.retrospective.conftest import (
    write_charter_with_retrospective,
    write_config_with_retrospective,
)

_CHARTER_YAML_SOURCE = ".kittify/charter/charter.yaml"
_CHARTER_MD_SOURCE = ".kittify/charter/charter.md"


def write_charter_yaml(repo_root: Path, body: str) -> Path:
    """Write a raw ``.kittify/charter/charter.yaml`` document."""
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    charter_yaml_path = charter_dir / "charter.yaml"
    charter_yaml_path.write_text(body, encoding="utf-8")
    return charter_yaml_path


def write_charter_yaml_with_retrospective(repo_root: Path, block_yaml: str) -> Path:
    """Write a charter.yaml carrying a ``governance.retrospective:`` block.

    ``block_yaml`` is the block body, already indented four spaces (i.e. two
    levels below the ``governance:`` root key).
    """
    return write_charter_yaml(
        repo_root,
        "schema_version: 2.0.0\ngovernance:\n  retrospective:\n" + block_yaml,
    )


# =============================================================================
# Case 1 — yaml-only project resolves from charter.yaml (SC-002 / NFR-001)
# =============================================================================


class TestYamlOnlyResolution:
    """A compiled-only project (charter.yaml, NO charter.md) must resolve."""

    def test_yaml_only_project_resolves_policy(self, tmp_path: Path) -> None:
        write_charter_yaml_with_retrospective(
            tmp_path,
            "    enabled: false\n"
            "    timing: before_completion\n"
            "    failure_policy: block\n",
        )
        # NFR-001: the presence fixture seeds charter.yaml ONLY.
        assert not (tmp_path / ".kittify" / "charter" / "charter.md").exists()

        policy, source_map = resolve_policy(tmp_path, env={})

        assert policy.enabled is False
        assert policy.timing == "before_completion"
        assert policy.failure_policy == "block"
        assert source_map["enabled"].startswith(_CHARTER_YAML_SOURCE)
        assert source_map["timing"].startswith(_CHARTER_YAML_SOURCE)
        assert source_map["failure_policy"].startswith(_CHARTER_YAML_SOURCE)

    def test_yaml_only_permissions_block_resolves(self, tmp_path: Path) -> None:
        write_charter_yaml_with_retrospective(
            tmp_path,
            "    permissions:\n      apply_low_risk_changes: true\n",
        )

        policy, source_map = resolve_policy(tmp_path, env={})

        assert policy.permissions.apply_low_risk_changes is True
        # Unclaimed permission keys keep their built-in default (C-005).
        assert policy.permissions.apply_structural_changes is False
        assert source_map["permissions.apply_low_risk_changes"].startswith(
            _CHARTER_YAML_SOURCE
        )
        assert source_map["permissions.apply_structural_changes"] == "<default>"

    def test_charter_yaml_without_retrospective_block_is_silent(
        self, tmp_path: Path
    ) -> None:
        """A charter.yaml with no retrospective block falls through to defaults."""
        write_charter_yaml(tmp_path, "schema_version: 2.0.0\ngovernance:\n  quality: {}\n")

        policy, source_map = resolve_policy(tmp_path, env={})

        assert policy.failure_policy == "warn"
        assert source_map["failure_policy"] == "<default>"


# =============================================================================
# Case 2 — both present, divergent: charter.yaml WINS (SC-002 precedence)
# =============================================================================


class TestYamlWinsOverMarkdown:
    """charter.yaml is the authority; charter.md frontmatter is overridden."""

    def test_divergent_values_resolve_from_charter_yaml(self, tmp_path: Path) -> None:
        write_charter_with_retrospective(
            tmp_path,
            {
                "enabled": True,
                "timing": "post_completion",
                "failure_policy": "warn",
            },
        )
        write_charter_yaml_with_retrospective(
            tmp_path,
            "    enabled: false\n"
            "    timing: before_completion\n"
            "    failure_policy: block\n",
        )

        policy, source_map = resolve_policy(tmp_path, env={})

        assert policy.enabled is False
        assert policy.timing == "before_completion"
        assert policy.failure_policy == "block"
        assert source_map["enabled"].startswith(_CHARTER_YAML_SOURCE)
        assert source_map["timing"].startswith(_CHARTER_YAML_SOURCE)
        assert source_map["failure_policy"].startswith(_CHARTER_YAML_SOURCE)

    def test_markdown_remains_a_contributing_secondary(self, tmp_path: Path) -> None:
        """Keys the authority does NOT claim still resolve from frontmatter (C-003)."""
        write_charter_with_retrospective(
            tmp_path,
            {"failure_policy": "warn", "generate_proposals": False},
        )
        write_charter_yaml_with_retrospective(tmp_path, "    failure_policy: block\n")

        policy, source_map = resolve_policy(tmp_path, env={})

        # Claimed by the authority -> yaml wins.
        assert policy.failure_policy == "block"
        assert source_map["failure_policy"].startswith(_CHARTER_YAML_SOURCE)
        # Unclaimed by the authority -> the secondary still contributes.
        assert policy.generate_proposals is False
        assert source_map["generate_proposals"].startswith(_CHARTER_MD_SOURCE)

    def test_permissions_merge_with_yaml_winning_per_key(self, tmp_path: Path) -> None:
        write_charter_with_retrospective(
            tmp_path,
            {
                "permissions": {
                    "apply_low_risk_changes": True,
                    "propose_drg_changes": False,
                }
            },
        )
        write_charter_yaml_with_retrospective(
            tmp_path,
            "    permissions:\n      apply_low_risk_changes: false\n",
        )

        policy, source_map = resolve_policy(tmp_path, env={})

        assert policy.permissions.apply_low_risk_changes is False
        assert source_map["permissions.apply_low_risk_changes"].startswith(
            _CHARTER_YAML_SOURCE
        )
        assert policy.permissions.propose_drg_changes is False
        assert source_map["permissions.propose_drg_changes"].startswith(
            _CHARTER_MD_SOURCE
        )


# =============================================================================
# Case 3 — legacy charter.md-only still resolves (C-003 backward compat)
# =============================================================================


class TestLegacyMarkdownOnly:
    """No charter.yaml at all: the frontmatter secondary is the only source."""

    def test_legacy_markdown_only_project_resolves(self, tmp_path: Path) -> None:
        write_charter_with_retrospective(
            tmp_path,
            {
                "enabled": False,
                "timing": "before_completion",
                "failure_policy": "block",
                "permissions": {"apply_low_risk_changes": True},
            },
        )
        assert not (tmp_path / ".kittify" / "charter" / "charter.yaml").exists()

        policy, source_map = resolve_policy(tmp_path, env={})

        assert policy.enabled is False
        assert policy.timing == "before_completion"
        assert policy.failure_policy == "block"
        assert policy.permissions.apply_low_risk_changes is True
        assert source_map["enabled"].startswith(_CHARTER_MD_SOURCE)
        assert source_map["permissions.apply_low_risk_changes"].startswith(
            _CHARTER_MD_SOURCE
        )

    def test_no_charter_at_all_falls_back_to_defaults(self, tmp_path: Path) -> None:
        policy, source_map = resolve_policy(tmp_path, env={})

        assert policy.failure_policy == "warn"
        assert set(source_map.values()) == {"<default>"}


# =============================================================================
# charter.yaml participates in the config-precedence gating
# =============================================================================


class TestYamlVsConfigPrecedence:
    """The authority block gates `.kittify/config.yaml` like the md block does."""

    def test_config_cannot_override_a_key_claimed_by_charter_yaml(
        self, tmp_path: Path
    ) -> None:
        write_charter_yaml_with_retrospective(tmp_path, "    failure_policy: block\n")
        write_config_with_retrospective(tmp_path, {"failure_policy": "warn"})

        policy, source_map = resolve_policy(tmp_path, env={})

        assert policy.failure_policy == "block"
        assert source_map["failure_policy"].startswith(_CHARTER_YAML_SOURCE)

    def test_config_still_fills_keys_the_authority_does_not_claim(
        self, tmp_path: Path
    ) -> None:
        write_charter_yaml_with_retrospective(tmp_path, "    failure_policy: block\n")
        write_config_with_retrospective(tmp_path, {"timing": "before_completion"})

        policy, source_map = resolve_policy(tmp_path, env={})

        assert policy.failure_policy == "block"
        assert policy.timing == "before_completion"
        assert source_map["timing"].startswith(".kittify/config.yaml")

    def test_charter_yaml_precedence_config_delegates_to_config(
        self, tmp_path: Path
    ) -> None:
        """``precedence: config`` authored in the AUTHORITY is honoured."""
        write_charter_yaml_with_retrospective(
            tmp_path,
            "    precedence: config\n",
        )
        write_config_with_retrospective(tmp_path, {"failure_policy": "block"})

        policy, source_map = resolve_policy(tmp_path, env={})

        assert policy.precedence == "config"
        assert policy.failure_policy == "block"
        assert source_map["failure_policy"].startswith(".kittify/config.yaml")


# =============================================================================
# strict_keys follows yaml > md > config precedence, not an OR (#3163)
# =============================================================================


class TestStrictKeysPrecedence:
    """``strict_keys`` resolves as a precedence chain, never an OR-across-sources.

    Regression for #3163: the resolver used to compute
    ``any(block.get("strict_keys") is True for block in blocks)`` across
    charter.yaml / charter.md / config -- an OR that let a lower-precedence
    source's ``strict_keys: true`` win even when the authority explicitly set
    ``strict_keys: false``.  Effective ``strict_keys`` is observed indirectly
    here via an unknown key: strict mode turns an unknown key into a raised
    ``PolicyResolutionError``; lenient mode only warns.
    """

    def test_yaml_explicit_false_wins_over_md_true(self, tmp_path: Path) -> None:
        """yaml's explicit ``strict_keys: false`` suppresses md's ``true`` (#3163).

        The unknown key is planted in the **md** block deliberately: an
        unknown key authored in the yaml block would be silently dropped by
        ``RetrospectiveGovernance.model_validate`` (extra fields are ignored)
        before it ever reaches ``_apply_block_to_policy``, which would make
        this case vacuous for exercising strict-mode enforcement.
        """
        write_charter_with_retrospective(
            tmp_path,
            {
                "strict_keys": True,
                "unknown_field": "surprise",
                "failure_policy": "warn",
            },
        )
        write_charter_yaml_with_retrospective(
            tmp_path,
            "    strict_keys: false\n",
        )

        # Must NOT raise: yaml's explicit strict_keys: false is the winning
        # source, so md's unknown_field is only a warning, not a raise.
        policy, source_map = resolve_policy(tmp_path, env={})

        assert policy.failure_policy == "warn"
        assert source_map["failure_policy"].startswith(_CHARTER_MD_SOURCE)

    def test_both_sources_agree_strict_true_raises_on_unknown_key(
        self, tmp_path: Path
    ) -> None:
        """Both yaml and md set ``strict_keys: true`` -> unknown key still raises."""
        write_charter_with_retrospective(
            tmp_path,
            {"strict_keys": True, "unknown_field": "surprise"},
        )
        write_charter_yaml_with_retrospective(
            tmp_path,
            "    strict_keys: true\n",
        )

        with pytest.raises(PolicyResolutionError) as excinfo:
            resolve_policy(tmp_path, env={})

        assert excinfo.value.reason == "unknown_key"

    def test_only_md_sets_strict_keys_true_raises_on_unknown_key(
        self, tmp_path: Path
    ) -> None:
        """No yaml block at all -- md's ``strict_keys: true`` is the sole source."""
        write_charter_with_retrospective(
            tmp_path,
            {"strict_keys": True, "unknown_field": "surprise"},
        )

        with pytest.raises(PolicyResolutionError) as excinfo:
            resolve_policy(tmp_path, env={})

        assert excinfo.value.reason == "unknown_key"


# =============================================================================
# Malformed charter.yaml surfaces the typed resolver error, never pydantic's
# =============================================================================


class TestMalformedCharterYaml:
    """A bad authority block must not leak ``pydantic.ValidationError``."""

    def test_invalid_literal_raises_policy_resolution_error(
        self, tmp_path: Path
    ) -> None:
        write_charter_yaml_with_retrospective(tmp_path, "    failure_policy: explode\n")

        with pytest.raises(PolicyResolutionError) as excinfo:
            resolve_policy(tmp_path, env={})

        err = excinfo.value
        assert err.source == _CHARTER_YAML_SOURCE
        assert err.reason == "invalid_enum"
        assert "failure_policy" in err.detail

    def test_field_type_error_raises_different_reason_than_enum_error(
        self, tmp_path: Path
    ) -> None:
        """A structural type error (list where a bool is expected) must NOT
        be reported with the same reason code as a genuine bad-enum-value
        error (#3163) -- callers/UIs branch on ``reason``.
        """
        write_charter_yaml_with_retrospective(
            tmp_path,
            "    enabled:\n      - 1\n      - 2\n",
        )

        with pytest.raises(PolicyResolutionError) as excinfo:
            resolve_policy(tmp_path, env={})

        err = excinfo.value
        assert err.source == _CHARTER_YAML_SOURCE
        assert err.reason == "invalid_type"
        assert err.reason != "invalid_enum"
        assert "enabled" in err.detail

    def test_non_mapping_retrospective_block_raises_policy_resolution_error(
        self, tmp_path: Path
    ) -> None:
        write_charter_yaml(
            tmp_path,
            "schema_version: 2.0.0\ngovernance:\n  retrospective: not-a-mapping\n",
        )

        with pytest.raises(PolicyResolutionError) as excinfo:
            resolve_policy(tmp_path, env={})

        assert excinfo.value.source == _CHARTER_YAML_SOURCE
        assert excinfo.value.reason == "invalid_type_for_retrospective_block"

    def test_unparseable_charter_yaml_raises_policy_resolution_error(
        self, tmp_path: Path
    ) -> None:
        write_charter_yaml(tmp_path, "governance:\n  retrospective:\n   - [unclosed\n")

        with pytest.raises(PolicyResolutionError) as excinfo:
            resolve_policy(tmp_path, env={})

        assert excinfo.value.source == _CHARTER_YAML_SOURCE
        assert excinfo.value.reason == "invalid_yaml"

    def test_non_utf8_charter_yaml_raises_policy_resolution_error(
        self, tmp_path: Path
    ) -> None:
        """Invalid UTF-8 bytes must surface as PolicyResolutionError, not crash.

        Regression for #3163: ``load_charter_yaml`` opens ``charter.yaml``
        with ``encoding="utf-8"``, so non-UTF-8 bytes raise
        ``UnicodeDecodeError`` -- a ``ValueError`` subclass, NOT an
        ``OSError`` subclass -- which the original
        ``except (_YAMLError, OSError)`` tuple did not catch, letting it
        escape as a raw crash instead of this module's structured error.
        """
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True, exist_ok=True)
        (charter_dir / "charter.yaml").write_bytes(
            b"schema_version: 2.0.0\ngovernance:\n  retrospective:\n"
            b"    failure_policy: \xff\xfe warn\n"
        )

        with pytest.raises(PolicyResolutionError) as excinfo:
            resolve_policy(tmp_path, env={})

        assert excinfo.value.source == _CHARTER_YAML_SOURCE
        assert excinfo.value.reason == "invalid_yaml"
