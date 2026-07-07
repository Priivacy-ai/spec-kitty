"""The ONE Playwright kanban->modal e2e regression guard (issue #1008).

Makes the CLAUDE.md "Never claim the frontend works without Playwright
proof" rule real: this is the exact click-through render PR #970 broke
(the dashboard's WP-card click opened a modal missing the agent identity)
while 338 backend tests + all architectural tests stayed green, because no
layer exercised the browser render.

Every identity assertion below is scoped to the modal container
(`#prompt-modal` / `.agent-identity-section`), never page-global and never
`.card .badge` — `agent`/`agent_profile`/`role` also render as card badges
*before* any click (`dashboard/static/dashboard/dashboard.js:514-516`), so a
page-global assertion would still pass even if the modal itself dropped the
identity (the #970 class of bug); only `model` is modal-exclusive.

Non-vacuity proof (FR-006, render-path): temporarily deleting the identity
block in `showPromptModal` (`dashboard/static/dashboard/dashboard.js:628-631`)
with this fixture's data left intact makes
`test_kanban_card_click_opens_modal_with_agent_identity` fail cleanly;
reverting the deletion makes it pass again (see the WP01 implementation
report for the pasted red/green run). That mutation is a throwaway
demonstration only — never committed.

See docs/development/ui-e2e.md (WP02) for how to extend this suite.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e

MODAL_SELECTOR = "#prompt-modal"
IDENTITY_SECTION_SELECTOR = f"{MODAL_SELECTOR} .agent-identity-section"
PROMPT_CONTENT_SELECTOR = f"{MODAL_SELECTOR} #modal-prompt-content"
_DISABLED_CLASS_RE = re.compile(r"(?:^|\s)disabled(?:\s|$)")


def test_kanban_card_click_opens_modal_with_agent_identity(
    page: Page, dashboard: dict[str, str]
) -> None:
    """Click a WP card; the modal renders agent/model/agent_profile/role + prompt.

    Steps mirror FR-002 exactly: load the page, assert the modal is hidden,
    click the WP card, wait for the modal, then assert — scoped to the
    modal container only — that it renders the canonical identity fields
    (populated, matching the fixture) plus the prompt markdown.
    """
    page.goto(dashboard["base_url"])

    modal = page.locator(MODAL_SELECTOR)

    # Pre-click baseline: the modal starts hidden. Asserting this first makes
    # the later "populated" assertions prove a real hidden->visible
    # transition happened, not an artifact of the modal always being shown.
    expect(modal).to_be_hidden()

    # Navigate to the kanban ("Implement") page. `fetchData()` polls
    # `/api/features` every second and only then flips this button out of
    # its disabled state, so wait for that rather than clicking blind.
    kanban_nav = page.locator('.sidebar-item[data-page="kanban"]')
    expect(kanban_nav).not_to_have_class(_DISABLED_CLASS_RE)
    kanban_nav.click()

    # Click the WP card seeded by the `dashboard` fixture into the
    # "planned" lane (see tests/ui/conftest.py::_seed_event_log).
    card = page.locator(".lane.planned .card").first
    expect(card).to_be_visible()
    card.click()

    expect(modal).to_be_visible()

    # Every assertion below is scoped to the modal's own identity section —
    # never `.card .badge` (populated pre-click regardless of the modal
    # render path) and never a page-global locator.
    identity_section = page.locator(IDENTITY_SECTION_SELECTOR)
    expect(identity_section).to_be_visible()
    expect(identity_section.locator(".badge.agent")).to_have_text(dashboard["agent"])
    expect(identity_section.locator(".badge.model")).to_have_text(dashboard["model"])
    expect(identity_section.locator(".badge.profile")).to_have_text(dashboard["agent_profile"])
    expect(identity_section.locator(".badge.role")).to_have_text(dashboard["role"])

    expect(page.locator(PROMPT_CONTENT_SELECTOR)).to_contain_text(dashboard["prompt_body"])
