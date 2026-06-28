"""Architectural test: runtime template Governance Payload Contract matches resolver.

The runtime ``implement.md`` and ``review.md`` templates carry a
``## Governance Payload Contract`` section listing the governance surfaces the
prompt is guaranteed to expose. This test pins **template-promise ↔
resolver-reality** consistency: every surface the template promises MUST be
present in :func:`build_charter_context`'s output for a fixture mission whose
WP frontmatter selects an agent profile.

The reverse direction is intentionally NOT enforced — the resolver may emit
additional surfaces (e.g. extra action-doctrine entries) without forcing a
template update.

See `kitty-specs/wp-prompt-governance-payload-01KRR8HS/contracts/`
`runtime-template-governance-payload-contract.md` §7.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from charter.context import build_charter_context


pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_IMPLEMENT_TEMPLATE = (
    _REPO_ROOT
    / "src"
    / "doctrine"
    / "missions"
    / "mission-steps"
    / "software-dev"
    / "implement"
    / "prompt.md"
)
_REVIEW_TEMPLATE = (
    _REPO_ROOT
    / "src"
    / "doctrine"
    / "missions"
    / "mission-steps"
    / "software-dev"
    / "review"
    / "prompt.md"
)

_SECTION_HEADING_RE = re.compile(
    r"##\s+Governance\s+Payload\s+Contract\b",
    re.IGNORECASE,
)


_FIXTURE_CHARTER_MD = """\
# Fixture Charter

> Version: 1.0.0

## Purpose

Fixture charter used by the architectural template-contract test. The body
declares both a ``template_set`` and ``available_tools`` so the resolver
emits no fallback diagnostics.

## Terminology Canon

- The canonical term for a unit of governed work is **Mission**.
- Legacy aliases such as ``feature`` and ``features`` are prohibited in
  canonical and operator-facing language.

## Code Review Checklist

- The WP diff respects the agent profile's directive-references.
- Terminology in code and docs aligns with the project glossary
  (DIRECTIVE_032 — Conceptual Alignment).

## Regression Vigilance (2026-04-06)

When renaming identifier-bearing terms, the reviewer MUST grep the diff for
the old term and MUST consult the project glossary at ``docs/context/``.

## Charter Resolution Hints

```yaml
template_set: software-dev-default
available_tools: [git, spec-kitty, pytest, mypy, ruff]
```
"""


def _git_init(tmp_path: Path) -> None:
    subprocess.run(
        ["git", "init", "--initial-branch=main"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "atdd@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "ATDD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def fixture_project(tmp_path: Path) -> Path:
    _git_init(tmp_path)
    charter_dir = tmp_path / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    (charter_dir / "charter.md").write_text(_FIXTURE_CHARTER_MD, encoding="utf-8")
    # The authority-paths renderer is existence-gated: it only emits
    # ``docs/context/`` and ``docs/adr/3.x/`` when those
    # directories exist on disk. The template promises both unconditionally,
    # so the fixture stages both so the resolver can deliver them.
    (tmp_path / "docs" / "context").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "adr" / "3.x").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _slice_contract_section(template_text: str) -> str:
    """Return the body of the ``## Governance Payload Contract`` section."""
    match = _SECTION_HEADING_RE.search(template_text)
    assert match is not None, (
        "Template is missing the ``## Governance Payload Contract`` heading. "
        "Re-add the section per the runtime-template-governance-payload-contract.md schema."
    )
    start = match.end()
    # Stop at the next top-level (``## ``) or third-level (``### ``) heading.
    next_heading = re.search(r"\n(##\s|###\s)", template_text[start:])
    end = start + next_heading.start() if next_heading else len(template_text)
    return template_text[start:end]


def _resolver_text(repo_root: Path, profile: str, action: str) -> str:
    result = build_charter_context(
        repo_root,
        action=action,
        profile=profile,
        mark_loaded=False,
    )
    return result.text


class TestImplementTemplateGovernancePayloadContract:
    def test_section_is_present_in_implement_template(self) -> None:
        text = _IMPLEMENT_TEMPLATE.read_text(encoding="utf-8")
        assert _SECTION_HEADING_RE.search(text), (
            "``## Governance Payload Contract`` section is missing from "
            f"{_IMPLEMENT_TEMPLATE}. The runtime template MUST carry this section "
            "so the forbid clause remains honest (see contract §1)."
        )

    def test_guaranteed_bodies_listed_in_template_appear_in_resolver(
        self, fixture_project: Path
    ) -> None:
        template_section = _slice_contract_section(
            _IMPLEMENT_TEMPLATE.read_text(encoding="utf-8")
        )
        resolver_text = _resolver_text(
            fixture_project, profile="python-pedro", action="implement"
        )
        for name in ("Terminology Canon", "Code Review Checklist", "Regression Vigilance"):
            assert name in template_section, (
                f"Template's Governance Payload Contract is missing guaranteed body '{name}'."
            )
            assert name in resolver_text, (
                f"Resolver output is missing the guaranteed body '{name}' that the "
                f"implement template promises. Either the resolver dropped a "
                f"section or the template overpromises."
            )

    def test_guaranteed_authority_pointers_appear_in_resolver(
        self, fixture_project: Path
    ) -> None:
        template_section = _slice_contract_section(
            _IMPLEMENT_TEMPLATE.read_text(encoding="utf-8")
        )
        resolver_text = _resolver_text(
            fixture_project, profile="python-pedro", action="implement"
        )
        for path in ("docs/context/", "docs/adr/3.x/"):
            assert path in template_section, (
                f"Template's Governance Payload Contract is missing authority pointer '{path}'."
            )
            assert path in resolver_text or path.rstrip("/") in resolver_text, (
                f"Resolver output is missing the guaranteed authority pointer "
                f"'{path}' the template promises."
            )

    def test_fetch_command_forms_are_listed_in_template(self) -> None:
        template_section = _slice_contract_section(
            _IMPLEMENT_TEMPLATE.read_text(encoding="utf-8")
        )
        for fetch in (
            "spec-kitty charter context --include directive:DIRECTIVE_NNN",
            "spec-kitty charter context --include tactic:",
            "spec-kitty charter context --include section:",
        ):
            assert fetch in template_section, (
                f"Template's Governance Payload Contract is missing canonical "
                f"fetch command form '{fetch}'."
            )


class TestReviewTemplateGovernancePayloadContract:
    def test_section_is_present_in_review_template(self) -> None:
        text = _REVIEW_TEMPLATE.read_text(encoding="utf-8")
        assert _SECTION_HEADING_RE.search(text), (
            "``## Governance Payload Contract`` section is missing from "
            f"{_REVIEW_TEMPLATE}."
        )

    def test_review_contract_cites_directive_032(self) -> None:
        template_section = _slice_contract_section(
            _REVIEW_TEMPLATE.read_text(encoding="utf-8")
        )
        assert "DIRECTIVE_032" in template_section, (
            "Review template's Governance Payload Contract MUST cite "
            "DIRECTIVE_032 (Conceptual Alignment) per contract §5 — this is "
            "the deterministic anchor for the reviewer's terminology check."
        )

    def test_guaranteed_bodies_listed_in_template_appear_in_resolver(
        self, fixture_project: Path
    ) -> None:
        template_section = _slice_contract_section(
            _REVIEW_TEMPLATE.read_text(encoding="utf-8")
        )
        resolver_text = _resolver_text(
            fixture_project, profile="reviewer-renata", action="review"
        )
        for name in ("Terminology Canon", "Code Review Checklist", "Regression Vigilance"):
            assert name in template_section, (
                f"Review template Governance Payload Contract is missing guaranteed body '{name}'."
            )
            assert name in resolver_text, (
                f"Resolver output is missing the guaranteed body '{name}' that the "
                f"review template promises."
            )

    def test_guaranteed_authority_pointers_appear_in_resolver(
        self, fixture_project: Path
    ) -> None:
        template_section = _slice_contract_section(
            _REVIEW_TEMPLATE.read_text(encoding="utf-8")
        )
        resolver_text = _resolver_text(
            fixture_project, profile="reviewer-renata", action="review"
        )
        for path in ("docs/context/", "docs/adr/3.x/"):
            assert path in template_section, (
                f"Review template Governance Payload Contract is missing authority pointer '{path}'."
            )
            assert path in resolver_text or path.rstrip("/") in resolver_text, (
                f"Resolver output is missing the guaranteed authority pointer '{path}' "
                f"the review template promises."
            )
