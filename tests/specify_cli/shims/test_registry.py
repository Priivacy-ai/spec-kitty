"""Tests for shims/registry.py — skill allowlist."""

from __future__ import annotations

import pytest

from specify_cli.shims.registry import (
    CONSUMER_SKILLS,
    INTERNAL_SKILLS,
    get_all_skills,
    get_consumer_skills,
    is_consumer_skill,
)


class TestConsumerSkills:
    @pytest.mark.parametrize(
        "skill",
        [
            "specify",
            "plan",
            "tasks",
            "tasks-outline",
            "tasks-packages",
            "tasks-finalize",
            "implement",
            "review",
            "accept",
            "merge",
            "status",
            "dashboard",
            "checklist",
            "analyze",
            "research",
            "constitution",
        ],
    )
    def test_known_consumer_skills_present(self, skill: str) -> None:
        assert skill in CONSUMER_SKILLS

    def test_consumer_skills_is_frozenset(self) -> None:
        assert isinstance(CONSUMER_SKILLS, frozenset)

    def test_internal_skills_not_in_consumer(self) -> None:
        for skill in INTERNAL_SKILLS:
            assert skill not in CONSUMER_SKILLS, f"{skill} should not be consumer-facing"


class TestInternalSkills:
    @pytest.mark.parametrize("skill", ["doctor", "materialize", "debug"])
    def test_known_internal_skills_present(self, skill: str) -> None:
        assert skill in INTERNAL_SKILLS

    def test_internal_skills_is_frozenset(self) -> None:
        assert isinstance(INTERNAL_SKILLS, frozenset)


class TestIsConsumerSkill:
    def test_returns_true_for_consumer(self) -> None:
        assert is_consumer_skill("implement") is True

    def test_returns_false_for_internal(self) -> None:
        assert is_consumer_skill("doctor") is False

    def test_returns_false_for_unknown(self) -> None:
        assert is_consumer_skill("nonexistent-skill-xyz") is False

    @pytest.mark.parametrize("skill", list(CONSUMER_SKILLS))
    def test_all_consumer_skills_return_true(self, skill: str) -> None:
        assert is_consumer_skill(skill) is True

    @pytest.mark.parametrize("skill", list(INTERNAL_SKILLS))
    def test_all_internal_skills_return_false(self, skill: str) -> None:
        assert is_consumer_skill(skill) is False


class TestGetConsumerSkills:
    def test_returns_frozenset(self) -> None:
        result = get_consumer_skills()
        assert isinstance(result, frozenset)

    def test_same_as_constant(self) -> None:
        assert get_consumer_skills() == CONSUMER_SKILLS


class TestGetAllSkills:
    def test_contains_consumer_skills(self) -> None:
        all_skills = get_all_skills()
        assert CONSUMER_SKILLS.issubset(all_skills)

    def test_contains_internal_skills(self) -> None:
        all_skills = get_all_skills()
        assert INTERNAL_SKILLS.issubset(all_skills)

    def test_is_union(self) -> None:
        assert get_all_skills() == CONSUMER_SKILLS | INTERNAL_SKILLS

    def test_returns_frozenset(self) -> None:
        assert isinstance(get_all_skills(), frozenset)
