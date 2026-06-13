"""NFR-005 regression pin for FR-006: dispatch presence in the advise skill.

WP04 cycle-1 — pins that `spec-kitty dispatch` (FR-006) and its three
retained first-class aliases (`do`, `ask`, `advise`) remain documented in the
SOURCE SKILL.md.  This test must fail if any of those terms is accidentally
removed from the canonical skill file.

Rationale for new test file (NFR-005 required):
  The SKILL.md is a doctrine source artefact, not a Python module.  The
  existing spk_skill_pack tests only check structural metadata (frontmatter
  fields, body line count, skill-map membership) for the spk-* namespace.
  The spec-kitty.advise skill lives in a different namespace and needs
  content-level assertions that the structural tests do not provide.
  A dedicated test file keeps the concern isolated and the failure message
  precise.
"""

from __future__ import annotations

import pytest

from tests.doctrine.conftest import DOCTRINE_SOURCE_ROOT

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]

_ADVISE_SKILL = DOCTRINE_SOURCE_ROOT / "skills" / "spec-kitty.advise" / "SKILL.md"


@pytest.fixture(scope="module")
def skill_text() -> str:
    assert _ADVISE_SKILL.is_file(), (
        f"SOURCE skill not found: {_ADVISE_SKILL!s}. "
        "If the file was moved, update the path in this test."
    )
    return _ADVISE_SKILL.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# FR-006 pin: dispatch must be present as the canonical command
# ---------------------------------------------------------------------------


def test_fr006_dispatch_is_documented_as_canonical_command(skill_text: str) -> None:
    """FR-006: spec-kitty dispatch is the canonical command in the advise skill."""
    assert "spec-kitty dispatch" in skill_text, (
        "FR-006 regression: 'spec-kitty dispatch' was removed from "
        "src/doctrine/skills/spec-kitty.advise/SKILL.md. "
        "Restore it as the canonical command."
    )


def test_fr006_dispatch_canonical_label_present(skill_text: str) -> None:
    """FR-006: skill explicitly labels dispatch as canonical (not merely mentions it)."""
    # The skill must say dispatch is canonical — a bare mention is insufficient.
    assert "`dispatch` is the canonical" in skill_text or (
        "dispatch` is the canonical" in skill_text
    ), (
        "FR-006 regression: the advise skill no longer labels 'dispatch' as canonical. "
        "The skill must state that dispatch is the canonical mechanism."
    )


# ---------------------------------------------------------------------------
# FR-006 alias pin: do / ask / advise must remain documented as retained aliases
# ---------------------------------------------------------------------------


def test_fr006_alias_do_is_documented(skill_text: str) -> None:
    """FR-006: `do` is a retained first-class alias documented in the advise skill."""
    assert "spec-kitty do" in skill_text, (
        "FR-006 regression: 'spec-kitty do' alias was removed from "
        "src/doctrine/skills/spec-kitty.advise/SKILL.md."
    )


def test_fr006_alias_ask_is_documented(skill_text: str) -> None:
    """FR-006: `ask` is a retained first-class alias documented in the advise skill."""
    assert "spec-kitty ask" in skill_text, (
        "FR-006 regression: 'spec-kitty ask' alias was removed from "
        "src/doctrine/skills/spec-kitty.advise/SKILL.md."
    )


def test_fr006_alias_advise_is_documented(skill_text: str) -> None:
    """FR-006: `advise` is a retained first-class alias documented in the advise skill."""
    assert "spec-kitty advise" in skill_text, (
        "FR-006 regression: 'spec-kitty advise' alias was removed from "
        "src/doctrine/skills/spec-kitty.advise/SKILL.md."
    )


def test_fr006_aliases_not_deprecated(skill_text: str) -> None:
    """FR-006: the retained aliases must NOT be marked as deprecated in the skill."""
    # The skill invariants section explicitly states they are not deprecated.
    assert "not** deprecated" in skill_text or "not deprecated" in skill_text, (
        "FR-006 regression: the advise skill must assert that the aliases "
        "(do/ask/advise) are not deprecated."
    )
