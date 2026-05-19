"""Unit tests for org-charter policy composition (WP09, T050).

Covers:
- OrgCharterPolicy model + loader
- load_org_charter_policies merge semantics
- apply_org_charter_pre_fill non-destructive behaviour
- org_charter JSON block presence/absence via org_charter_loader
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from charter.interview import apply_org_charter_pre_fill_to_answers
from specify_cli.doctrine.org_charter import (
    GovernancePolicy,
    OrgCharterPolicy,
    apply_org_charter_pre_fill,
    load_org_charter_policies,
    load_org_charter_policy,
)
from specify_cli.doctrine.org_charter_loader import load_org_charter_json_block


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_org_charter(pack_dir: Path, body: str) -> Path:
    """Write a YAML org-charter file at ``pack_dir/org-charter.yaml``."""
    pack_dir.mkdir(parents=True, exist_ok=True)
    path = pack_dir / "org-charter.yaml"
    path.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
    return path


def _write_kittify_config(repo_root: Path, packs: list[dict]) -> None:
    """Write ``.kittify/config.yaml`` with ``doctrine.org.packs``."""
    config_dir = repo_root / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    pack_yaml_lines = ["doctrine:", "  org:", "    packs:"]
    for pack in packs:
        pack_yaml_lines.append(f"      - name: {pack['name']}")
        pack_yaml_lines.append(f"        local_path: {pack['local_path']}")
    config_path = config_dir / "config.yaml"
    config_path.write_text("\n".join(pack_yaml_lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# T050: load_org_charter_policy (single pack)
# ---------------------------------------------------------------------------


class TestLoadOrgCharterPolicy:
    def test_load_single_pack_policy(self, tmp_path: Path) -> None:
        pack = tmp_path / "pack"
        _write_org_charter(
            pack,
            """
            schema_version: "1"
            org_name: "Acme"
            interview_defaults:
              human_in_command: true
              security_review: "Required"
            required_directives:
              - sec-001
              - sec-002
            governance_policies:
              - field: "autonomous_mode"
                value: "disallowed"
                enforcement: advisory
            """,
        )

        policy = load_org_charter_policy(pack)

        assert policy is not None
        assert policy.schema_version == "1"
        assert policy.org_name == "Acme"
        assert policy.interview_defaults == {
            "human_in_command": True,
            "security_review": "Required",
        }
        assert policy.required_directives == ["sec-001", "sec-002"]
        assert len(policy.governance_policies) == 1
        gp = policy.governance_policies[0]
        assert gp.field == "autonomous_mode"
        assert gp.value == "disallowed"
        assert gp.enforcement == "advisory"

    def test_load_missing_charter(self, tmp_path: Path) -> None:
        pack = tmp_path / "pack"
        pack.mkdir()

        assert load_org_charter_policy(pack) is None

    def test_load_empty_file(self, tmp_path: Path) -> None:
        pack = tmp_path / "pack"
        _write_org_charter(pack, "")

        assert load_org_charter_policy(pack) is None

    def test_load_malformed_yaml_returns_none(self, tmp_path: Path) -> None:
        pack = tmp_path / "pack"
        pack.mkdir()
        (pack / "org-charter.yaml").write_text("::: not valid yaml :::", encoding="utf-8")

        assert load_org_charter_policy(pack) is None


# ---------------------------------------------------------------------------
# T050: load_org_charter_policies (multi-pack merge)
# ---------------------------------------------------------------------------


class TestLoadOrgCharterPolicies:
    def test_load_org_charter_policies_empty(self, tmp_path: Path) -> None:
        """Zero configured packs -> empty policy, not None, no error."""
        policy = load_org_charter_policies(tmp_path)

        assert isinstance(policy, OrgCharterPolicy)
        assert policy.interview_defaults == {}
        assert policy.required_directives == []
        assert policy.governance_policies == []

    def test_load_packs_without_charter_returns_empty(self, tmp_path: Path) -> None:
        """Packs configured but none ship org-charter.yaml -> empty policy."""
        pack_a = tmp_path / "packs" / "a"
        pack_a.mkdir(parents=True)
        _write_kittify_config(
            tmp_path,
            [{"name": "a", "local_path": str(pack_a)}],
        )

        policy = load_org_charter_policies(tmp_path)

        assert isinstance(policy, OrgCharterPolicy)
        assert policy.interview_defaults == {}
        assert policy.required_directives == []

    def test_merge_interview_defaults_precedence(self, tmp_path: Path) -> None:
        """Two packs with overlapping interview_defaults: last pack wins."""
        pack_a = tmp_path / "packs" / "a"
        pack_b = tmp_path / "packs" / "b"
        _write_org_charter(
            pack_a,
            """
            interview_defaults:
              human_in_command: true
              shared_key: "from-a"
            """,
        )
        _write_org_charter(
            pack_b,
            """
            interview_defaults:
              shared_key: "from-b"
              new_key: "only-in-b"
            """,
        )
        _write_kittify_config(
            tmp_path,
            [
                {"name": "a", "local_path": str(pack_a)},
                {"name": "b", "local_path": str(pack_b)},
            ],
        )

        policy = load_org_charter_policies(tmp_path)

        assert policy.interview_defaults["human_in_command"] is True
        assert policy.interview_defaults["shared_key"] == "from-b"  # b wins
        assert policy.interview_defaults["new_key"] == "only-in-b"

    def test_merge_required_directives_union(self, tmp_path: Path) -> None:
        """Two packs with overlapping required_directives: union, no dupes."""
        pack_a = tmp_path / "packs" / "a"
        pack_b = tmp_path / "packs" / "b"
        _write_org_charter(
            pack_a,
            """
            required_directives:
              - dir-1
              - shared
            """,
        )
        _write_org_charter(
            pack_b,
            """
            required_directives:
              - shared
              - dir-2
            """,
        )
        _write_kittify_config(
            tmp_path,
            [
                {"name": "a", "local_path": str(pack_a)},
                {"name": "b", "local_path": str(pack_b)},
            ],
        )

        policy = load_org_charter_policies(tmp_path)

        assert policy.required_directives == ["dir-1", "shared", "dir-2"]

    def test_merge_governance_policies_dedup(self, tmp_path: Path) -> None:
        """Identical (field, value) policies are deduplicated to one."""
        pack_a = tmp_path / "packs" / "a"
        pack_b = tmp_path / "packs" / "b"
        _write_org_charter(
            pack_a,
            """
            governance_policies:
              - field: "autonomous_mode"
                value: "disallowed"
                enforcement: advisory
              - field: "another_field"
                value: "alpha"
                enforcement: advisory
            """,
        )
        _write_org_charter(
            pack_b,
            """
            governance_policies:
              - field: "autonomous_mode"
                value: "disallowed"
                enforcement: advisory
            """,
        )
        _write_kittify_config(
            tmp_path,
            [
                {"name": "a", "local_path": str(pack_a)},
                {"name": "b", "local_path": str(pack_b)},
            ],
        )

        policy = load_org_charter_policies(tmp_path)

        # autonomous_mode appears once even though both packs declare it.
        autonomous_entries = [
            gp for gp in policy.governance_policies if gp.field == "autonomous_mode"
        ]
        assert len(autonomous_entries) == 1
        # The non-overlapping policy from pack-a survives.
        assert any(gp.field == "another_field" for gp in policy.governance_policies)


# ---------------------------------------------------------------------------
# T050: pre-fill behaviour
# ---------------------------------------------------------------------------


class TestApplyOrgCharterPreFill:
    def test_pre_fill_sets_missing_keys(self, tmp_path: Path) -> None:
        answers_path = tmp_path / "answers.yaml"

        messages = apply_org_charter_pre_fill_to_answers(
            answers_path=answers_path,
            interview_defaults={"human_in_command": True},
            required_directives=[],
        )

        assert messages, "Expected at least one pre-fill message"
        yaml = YAML(typ="safe")
        loaded = yaml.load(answers_path.read_text(encoding="utf-8"))
        assert loaded["human_in_command"] is True

    def test_pre_fill_does_not_overwrite(self, tmp_path: Path) -> None:
        """Existing project answer is preserved when org default differs."""
        answers_path = tmp_path / "answers.yaml"
        answers_path.write_text("human_in_command: false\n", encoding="utf-8")

        messages = apply_org_charter_pre_fill_to_answers(
            answers_path=answers_path,
            interview_defaults={"human_in_command": True},
            required_directives=[],
        )

        assert messages == []  # nothing changed -> no message
        yaml = YAML(typ="safe")
        loaded = yaml.load(answers_path.read_text(encoding="utf-8"))
        assert loaded["human_in_command"] is False  # project value preserved

    def test_pre_fill_required_directives_union(self, tmp_path: Path) -> None:
        """Existing selected_directives are augmented, not replaced."""
        answers_path = tmp_path / "answers.yaml"
        answers_path.write_text(
            "selected_directives:\n  - dir-a\n",
            encoding="utf-8",
        )

        messages = apply_org_charter_pre_fill_to_answers(
            answers_path=answers_path,
            interview_defaults={},
            required_directives=["dir-b"],
        )

        assert messages, "Expected pre-selection message"
        yaml = YAML(typ="safe")
        loaded = yaml.load(answers_path.read_text(encoding="utf-8"))
        assert loaded["selected_directives"] == ["dir-a", "dir-b"]

    def test_pre_fill_required_directives_no_duplicate(self, tmp_path: Path) -> None:
        """When org directive already present, no change occurs."""
        answers_path = tmp_path / "answers.yaml"
        answers_path.write_text(
            "selected_directives:\n  - dir-a\n",
            encoding="utf-8",
        )

        messages = apply_org_charter_pre_fill_to_answers(
            answers_path=answers_path,
            interview_defaults={},
            required_directives=["dir-a"],
        )

        assert messages == []
        yaml = YAML(typ="safe")
        loaded = yaml.load(answers_path.read_text(encoding="utf-8"))
        assert loaded["selected_directives"] == ["dir-a"]

    def test_pre_fill_idempotent_rerun(self, tmp_path: Path) -> None:
        """Second run is a no-op (no further writes, no further messages)."""
        answers_path = tmp_path / "answers.yaml"
        interview_defaults: dict[str, str | bool] = {"human_in_command": True}
        required_directives = ["dir-a"]

        first = apply_org_charter_pre_fill_to_answers(
            answers_path=answers_path,
            interview_defaults=interview_defaults,
            required_directives=required_directives,
        )
        second = apply_org_charter_pre_fill_to_answers(
            answers_path=answers_path,
            interview_defaults=interview_defaults,
            required_directives=required_directives,
        )

        assert first, "First call should apply pre-fill"
        assert second == [], "Second call should be a no-op"

    def test_apply_org_charter_pre_fill_no_packs_is_noop(self, tmp_path: Path) -> None:
        """No packs configured -> empty list, no answers file created."""
        messages = apply_org_charter_pre_fill(tmp_path)

        assert messages == []
        assert not (
            tmp_path / ".kittify" / "charter" / "interview" / "answers.yaml"
        ).exists()

    def test_apply_org_charter_pre_fill_with_pack(self, tmp_path: Path) -> None:
        """End-to-end: configured pack with charter -> answers.yaml written."""
        pack = tmp_path / "packs" / "security"
        _write_org_charter(
            pack,
            """
            interview_defaults:
              human_in_command: true
            required_directives:
              - sec-001
            """,
        )
        _write_kittify_config(
            tmp_path, [{"name": "security", "local_path": str(pack)}]
        )

        messages = apply_org_charter_pre_fill(tmp_path)

        assert messages
        answers_path = (
            tmp_path / ".kittify" / "charter" / "interview" / "answers.yaml"
        )
        assert answers_path.exists()
        yaml = YAML(typ="safe")
        loaded = yaml.load(answers_path.read_text(encoding="utf-8"))
        assert loaded["human_in_command"] is True
        assert "sec-001" in loaded["selected_directives"]


# ---------------------------------------------------------------------------
# T050: charter context JSON block
# ---------------------------------------------------------------------------


class TestContextJsonOrgCharter:
    def test_context_json_org_charter_absent(self, tmp_path: Path) -> None:
        """No org roots -> {present: false, packs: []}."""
        block = load_org_charter_json_block(None)

        assert block == {"present": False, "packs": []}

        block_empty = load_org_charter_json_block([])
        assert block_empty == {"present": False, "packs": []}

    def test_context_json_org_charter_present(self, tmp_path: Path) -> None:
        """Org root with org-charter.yaml -> present=true with pack entry."""
        pack = tmp_path / "pack"
        _write_org_charter(
            pack,
            """
            org_name: "Acme Security"
            required_directives:
              - sec-001
            governance_policies:
              - field: "autonomous_mode"
                value: "disallowed"
                enforcement: advisory
            """,
        )

        block = load_org_charter_json_block([pack])

        assert block["present"] is True
        assert len(block["packs"]) == 1
        entry = block["packs"][0]
        assert entry["pack_name"] == "Acme Security"
        assert "sec-001" in entry["required_directives"]
        assert entry["governance_policies"]
        assert entry["governance_policies"][0]["source"] == "org"


# ---------------------------------------------------------------------------
# Schema model surface
# ---------------------------------------------------------------------------


class TestOrgCharterPolicyModel:
    def test_empty_policy_is_valid(self) -> None:
        policy = OrgCharterPolicy()
        assert policy.schema_version == "1"
        assert policy.org_name is None
        assert policy.interview_defaults == {}
        assert policy.required_directives == []
        assert policy.governance_policies == []

    def test_governance_policy_defaults_to_advisory(self) -> None:
        gp = GovernancePolicy(field="x", value=True)
        assert gp.enforcement == "advisory"

    def test_governance_policy_accepts_bool_value(self) -> None:
        gp = GovernancePolicy(field="human_in_command", value=True)
        assert gp.value is True

    def test_unknown_field_rejected(self) -> None:
        """extra='forbid' on the model — unknown keys raise ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            OrgCharterPolicy.model_validate({"unknown_field": "x"})
