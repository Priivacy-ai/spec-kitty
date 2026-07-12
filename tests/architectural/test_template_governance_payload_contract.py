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

FR-010 hardening (#2548 WS3 audit, WP01 of mission
content-address-ratchet-allowlists-01KX8M4D): the promised-surface set below
is DERIVED from the same Python-level constants/formatters
:func:`build_charter_context` itself reads — ``ACTION_CRITICAL_SECTIONS``,
``DEFAULT_AUTHORITY_PATHS``, the ``fetch_stanza`` formatter, and the shipped
``reviewer-renata`` profile's ``directive-references`` — instead of being
re-typed as independent literal strings in this test file. A legitimate
wording edit applied at the source (e.g. renaming a section) therefore stays
green here without a matching test-file edit; only a genuine
promise-vs-reality gap reds.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterable
from pathlib import Path

import pytest

from charter.context import build_charter_context
from charter.context_renderers.authority_paths import DEFAULT_AUTHORITY_PATHS
from charter.context_renderers.fetch_stanza import (
    DEFAULT_WHEN_CLAUSE,
    fetch_stanza_lines,
    format_selector,
)
from charter.context_renderers.section_bodies import ACTION_CRITICAL_SECTIONS
from doctrine.agent_profiles.repository import AgentProfileRepository


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


def _promised_but_absent(promised: Iterable[str], haystack: str) -> list[str]:
    """Return every ``promised`` surface not found verbatim in ``haystack``.

    Pure function of its inputs (FR-013) so the plant-and-catch negative
    test can drive it with synthetic promise/reality strings and prove
    non-vacuity without touching the real templates or resolver.
    """
    return [name for name in promised if name not in haystack]


def _fetch_command_form(kind: str, identifier: str) -> str:
    """Derive the literal ``spec-kitty charter context --include <selector>``
    command text from the resolver's own fetch-stanza formatter (FR-010) —
    the same formatter :func:`build_charter_context`'s renderers use to
    emit fetch stanzas — instead of hand-typing the command text.
    """
    # Explicit annotations pin the boundary type: charter.* is under a
    # documented mypy `follow_imports = "skip"` override (pyproject.toml),
    # so calls into it resolve to Any for external callers even though the
    # source is fully typed. Annotating here reflects the true contract
    # without suppressing a real check.
    selector: str = format_selector(kind, identifier)
    line: str = fetch_stanza_lines(selector, DEFAULT_WHEN_CLAUSE)[0]
    return line.removeprefix("Run: ")


def _fetch_command_prefix(kind: str) -> str:
    """Derive the bare ``<kind>:`` selector-prefix command form for ``kind``.

    The template promises the selector *kind* generically (e.g.
    ``tactic:``), not a specific identifier, so this strips the derived
    placeholder identifier back off :func:`_fetch_command_form`'s output.
    """
    placeholder_form = _fetch_command_form(kind, "_PLACEHOLDER_")
    return placeholder_form.rsplit(":", 1)[0] + ":"


def _conceptual_alignment_directive_id() -> str:
    """Derive the ``DIRECTIVE_NNN`` id the reviewer-renata profile cites for
    "Conceptual Alignment" from the shipped profile data (FR-010), instead
    of hardcoding the literal ``"DIRECTIVE_032"`` string in this test.
    """
    profile = AgentProfileRepository().get("reviewer-renata")
    assert profile is not None, "expected the shipped reviewer-renata profile to load"
    conceptual_alignment = next(
        (ref for ref in profile.directive_references if ref.name == "Conceptual Alignment"),
        None,
    )
    assert conceptual_alignment is not None, (
        "reviewer-renata profile no longer cites 'Conceptual Alignment' — "
        "update this test's derivation, not the literal directive id."
    )
    return f"DIRECTIVE_{conceptual_alignment.code.zfill(3)}"


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
        promised = ACTION_CRITICAL_SECTIONS["implement"]
        missing_from_template = _promised_but_absent(promised, template_section)
        assert not missing_from_template, (
            "Template's Governance Payload Contract is missing guaranteed "
            f"bodies: {missing_from_template}."
        )
        missing_from_resolver = _promised_but_absent(promised, resolver_text)
        assert not missing_from_resolver, (
            "Resolver output is missing guaranteed bodies the implement "
            f"template promises: {missing_from_resolver}. Either the "
            "resolver dropped a section or the template overpromises."
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
        for path in DEFAULT_AUTHORITY_PATHS:
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
            _fetch_command_form("directive", "DIRECTIVE_NNN"),
            _fetch_command_prefix("tactic"),
            _fetch_command_prefix("section"),
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
        expected_directive_id = _conceptual_alignment_directive_id()
        assert expected_directive_id in template_section, (
            f"Review template's Governance Payload Contract MUST cite "
            f"{expected_directive_id} (Conceptual Alignment) per contract §5 — "
            f"this is the deterministic anchor for the reviewer's terminology check."
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
        promised = ACTION_CRITICAL_SECTIONS["review"]
        missing_from_template = _promised_but_absent(promised, template_section)
        assert not missing_from_template, (
            "Review template Governance Payload Contract is missing "
            f"guaranteed bodies: {missing_from_template}."
        )
        missing_from_resolver = _promised_but_absent(promised, resolver_text)
        assert not missing_from_resolver, (
            "Resolver output is missing guaranteed bodies the review "
            f"template promises: {missing_from_resolver}."
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
        for path in DEFAULT_AUTHORITY_PATHS:
            assert path in template_section, (
                f"Review template Governance Payload Contract is missing authority pointer '{path}'."
            )
            assert path in resolver_text or path.rstrip("/") in resolver_text, (
                f"Resolver output is missing the guaranteed authority pointer '{path}' "
                f"the review template promises."
            )


class TestGovernancePayloadPlantAndCatch:
    """Non-vacuity + wording-drift proof for the FR-010 hardening (T002/T004).

    ``_promised_but_absent`` is the pure matcher the real
    ``test_guaranteed_bodies_listed_in_template_appear_in_resolver`` tests
    (both classes above) exercise against real template/resolver text. Here
    it is driven directly with synthetic inputs to prove the two things the
    FR-010 derivation change depends on:

    1. A promised surface genuinely missing from the resolver output MUST
       still red (the behavioural contract has not been weakened).
    2. A pure wording change applied identically to the promised-surface
       *source* and to both template/resolver text MUST NOT red — proving
       the hardened test derives its expectations rather than re-pinning a
       literal string (the whole point of FR-010).
    """

    def test_missing_promised_surface_is_flagged(self) -> None:
        offenders = _promised_but_absent(
            ["Terminology Canon", "Totally-Fake-Promised-Surface"],
            "... body containing only Terminology Canon ...",
        )
        assert offenders == ["Totally-Fake-Promised-Surface"], (
            "expected the matcher to flag a promised surface genuinely "
            "missing from resolver reality — the plant-and-catch self-test "
            "has lost its teeth"
        )

    def test_consistent_wording_rename_does_not_red(self) -> None:
        # Simulate a legitimate wording-only rename applied at the SOURCE
        # (ACTION_CRITICAL_SECTIONS) and propagated consistently to both the
        # template promise and the resolver reality in the same change —
        # the scenario FR-010's derivation is meant to survive without a
        # separate edit to this test file's literals.
        renamed_sections = [
            "Regression Awareness" if name == "Regression Vigilance" else name
            for name in ACTION_CRITICAL_SECTIONS["implement"]
        ]
        synthetic_template = " | ".join(renamed_sections)
        synthetic_resolver = " | ".join(renamed_sections)

        offenders = _promised_but_absent(renamed_sections, synthetic_template)
        offenders += _promised_but_absent(renamed_sections, synthetic_resolver)
        assert not offenders, (
            "a wording change applied consistently to the promised-surface "
            "source and to both template/resolver text must not red — a "
            "hardened (derived) test must not re-pin the old literal wording"
        )
