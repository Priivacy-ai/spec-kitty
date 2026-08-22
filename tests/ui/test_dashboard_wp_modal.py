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

# `pytest-playwright` is an optional dependency (`[project.optional-dependencies].test`
# in pyproject.toml) — a dev who ran `uv sync` without the `test` extra won't have
# it installed. Without this guard, `from playwright.sync_api import ...` raises
# `ModuleNotFoundError` at COLLECTION time, which fails the full-suite
# `pytest --collect-only` the architectural gate tests
# (tests/architectural/test_ci_collection_completeness.py et al.) run to build their test
# universe — turning a missing optional dep into a hard RuntimeError across a
# dozen unrelated gate tests. `importorskip` degrades that to a clean SKIP of
# just this module; it is a no-op when playwright IS installed (CI's
# `ui-e2e.yml` always installs it), so the real e2e regression guard still
# collects and runs unchanged there.
pytest.importorskip(
    "playwright",
    reason="pytest-playwright optional dep; run `uv sync --extra test` / "
    "`playwright install chromium` to exercise tests/ui/",
)
from playwright.sync_api import Page, Route, expect  # noqa: E402  (after importorskip)

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
    identity_section = page.locator(IDENTITY_SECTION_SELECTOR).filter(has_text="Agent:")
    expect(identity_section).to_be_visible()
    expect(identity_section.locator(".badge.agent")).to_have_text(dashboard["agent"])
    expect(identity_section.locator(".badge.model")).to_have_text(dashboard["model"])
    expect(identity_section.locator(".badge.profile")).to_have_text(dashboard["agent_profile"])
    expect(identity_section.locator(".badge.role")).to_have_text(dashboard["role"])

    expect(page.locator(PROMPT_CONTENT_SELECTOR)).to_contain_text(dashboard["prompt_body"])


def test_kanban_card_shows_assigned_profile_avatar(page: Page, dashboard: dict[str, str]) -> None:
    """The WP card itself (pre-click) renders a profile avatar (issue #647).

    Deliberately card-scoped (`.lane.planned .card .card-avatar`), the mirror
    image of the module docstring's warning about the modal test above: this
    one is *only* about the card, so it must never assert against
    `#prompt-modal` — that would make it pass even if `createCard()` dropped
    the avatar but the modal still built one independently.
    """
    page.goto(dashboard["base_url"])

    kanban_nav = page.locator('.sidebar-item[data-page="kanban"]')
    expect(kanban_nav).not_to_have_class(_DISABLED_CLASS_RE)
    kanban_nav.click()

    card = page.locator(".lane.planned .card").first
    expect(card).to_be_visible()

    avatar = card.locator(".card-avatar")
    expect(avatar).to_be_visible()
    # dashboard["agent_profile"] is "implementer-ivan" (tests/ui/conftest.py);
    # profileAvatarHtml() takes the first letter of each of the first two
    # hyphen-separated words, uppercased.
    expect(avatar).to_have_text("II")
    expect(avatar).to_have_attribute("title", dashboard["agent_profile"])


def test_kanban_card_treats_identity_and_card_copy_as_text(
    page: Page, dashboard: dict[str, str]
) -> None:
    """Hostile card copy cannot become markup; blank profile falls through."""
    hostile_id = 'WP01<img src=x onerror="globalThis.__cardPwned=true">'
    hostile_title = 'Unsafe <svg onload="globalThis.__cardPwned=true"> title'
    hostile_role = 'reviewer" onmouseover="globalThis.__avatarPwned=true'

    def _rewrite_kanban(route: Route) -> None:
        response = route.fetch()
        payload = response.json()
        lanes = payload.get("lanes", payload)
        task = lanes["planned"][0]
        task.update(
            {
                "id": hostile_id,
                "title": hostile_title,
                "agent_profile": "   ",
                "role": hostile_role,
            }
        )
        route.fulfill(response=response, json=payload)

    page.route("**/api/kanban/*", _rewrite_kanban)
    page.goto(dashboard["base_url"])
    kanban_nav = page.locator('.sidebar-item[data-page="kanban"]')
    expect(kanban_nav).not_to_have_class(_DISABLED_CLASS_RE)
    kanban_nav.click()

    card = page.locator(".lane.planned .card").first
    expect(card.locator(".card-id")).to_have_text(hostile_id)
    expect(card.locator(".card-title")).to_have_text(hostile_title)
    expect(card.locator("img")).to_have_count(0)
    expect(card.locator("svg")).to_have_count(0)

    avatar = card.locator(".card-avatar")
    expect(avatar).to_have_attribute("title", hostile_role)
    expect(avatar).not_to_have_attribute("onmouseover", re.compile(".+"))
    assert page.evaluate("globalThis.__cardPwned === true") is False
    assert page.evaluate("globalThis.__avatarPwned === true") is False
    assert page.evaluate("profileAvatarHtml({})") == ""


def test_print_media_allows_below_fold_content_to_flow(
    page: Page, dashboard: dict[str, str]
) -> None:
    """Chromium computed layout must expand the SPA shell under print media."""
    page.set_viewport_size({"width": 1000, "height": 600})
    page.goto(dashboard["base_url"])
    page.evaluate(
        """
        () => {
          const sentinel = document.createElement('div');
          sentinel.id = 'print-below-fold-sentinel';
          sentinel.style.height = '1800px';
          sentinel.textContent = 'PRINT-END-SENTINEL';
          document.querySelector('.main-content').appendChild(sentinel);
        }
        """
    )

    screen = page.evaluate(
        """
        () => {
          const main = document.querySelector('.main-content');
          const style = getComputedStyle(main);
          return {height: main.getBoundingClientRect().height, overflowY: style.overflowY};
        }
        """
    )
    assert screen["height"] <= 600
    assert screen["overflowY"] == "auto"

    page.emulate_media(media="print")
    printed = page.evaluate(
        """
        () => {
          const main = document.querySelector('.main-content');
          const sentinel = document.querySelector('#print-below-fold-sentinel');
          const style = getComputedStyle(main);
          return {
            height: main.getBoundingClientRect().height,
            overflowY: style.overflowY,
            sentinelBottom: sentinel.getBoundingClientRect().bottom,
            documentHeight: document.documentElement.scrollHeight,
          };
        }
        """
    )
    assert printed["overflowY"] == "visible"
    assert printed["height"] > 1600
    assert printed["sentinelBottom"] <= printed["documentHeight"]
