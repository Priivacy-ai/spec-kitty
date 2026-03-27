"""Skill allowlist — consumer-facing vs internal-only skills.

Only skills in ``CONSUMER_SKILLS`` are written to agent shim directories
during ``generate_all_shims()``.  Skills in ``INTERNAL_SKILLS`` are
reserved for operator/developer use and must never appear in generated
command directories.
"""

from __future__ import annotations

# Skills that project teams interact with directly via their AI agent's
# slash-command interface.
CONSUMER_SKILLS: frozenset[str] = frozenset(
    {
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
    }
)

# Skills reserved for spec-kitty operators and developers.
# These are NEVER written to consumer agent directories.
INTERNAL_SKILLS: frozenset[str] = frozenset(
    {
        "doctor",
        "materialize",
        "debug",
    }
)


def is_consumer_skill(skill_name: str) -> bool:
    """Return True if *skill_name* is a consumer-facing skill.

    Args:
        skill_name: Skill identifier (e.g. ``"implement"``).

    Returns:
        True when the skill appears in :data:`CONSUMER_SKILLS`.
    """
    return skill_name in CONSUMER_SKILLS


def get_consumer_skills() -> frozenset[str]:
    """Return the frozen set of consumer-facing skill names."""
    return CONSUMER_SKILLS


def get_all_skills() -> frozenset[str]:
    """Return the union of consumer and internal skill names."""
    return CONSUMER_SKILLS | INTERNAL_SKILLS
