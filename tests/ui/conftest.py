"""Hermetic fixtures for the Playwright kanban->modal e2e (issue #1008).

This is the framework-bootstrap fixture for `tests/ui/` (mission
playwright-ui-e2e-bootstrap-01KWX72W, WP01): a deterministic, synthetic
mission/WP the dashboard scanner can read, plus an in-thread dashboard boot
on an ephemeral port. No real `~/.spec-kitty`, no network, no git repo.

See docs/development/ui-e2e.md (added in WP02) for how to extend this
suite with additional dashboard e2e coverage.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
import ulid

from specify_cli.dashboard.server import find_free_port, start_dashboard
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event

# ---------------------------------------------------------------------------
# Playwright browser cache vs. per-worker HOME isolation (WP04, tests/conftest.py)
# ---------------------------------------------------------------------------
# The suite's root conftest repoints HOME/XDG_CACHE_HOME at a per-worker
# throwaway directory (`_apply_home_env`, called from its `pytest_configure`)
# so no test ever touches the developer's real `~/.spec-kitty`. Playwright's
# Python client resolves its browser cache from `$HOME/.cache/ms-playwright`
# unless `PLAYWRIGHT_BROWSERS_PATH` is set explicitly — so under the isolated
# HOME it looks in an empty throwaway directory and reports "Executable
# doesn't exist", even though `playwright install chromium` cached the
# browser under the real home.
#
# The root conftest publishes the pre-isolation home via
# `SPEC_KITTY_REAL_HOME_FOR_TESTS` for exactly this kind of case
# (tests/conftest.py:63); this module's own `pytest_configure` reads it back
# and points Playwright's browser cache at it. `trylast=True` forces this
# hookimpl to run after every plain-priority `pytest_configure` (the root
# conftest's included) regardless of conftest.py registration/collection
# order, so `SPEC_KITTY_REAL_HOME_FOR_TESTS` is guaranteed populated by the
# time this reads it. All `pytest_configure` hooks (across every plugin)
# complete before collection begins, which is itself before any fixture —
# including pytest-playwright's session-scoped `browser` fixture — is ever
# instantiated, so this always wins the race against the first browser
# launch. A no-op outside this repo's isolated-home pytest setup (the real
# app's normal `spec-kitty dashboard` boot path never sets this env var).
@pytest.hookimpl(trylast=True)
def pytest_configure(config: pytest.Config) -> None:
    del config
    real_home = os.environ.get("SPEC_KITTY_REAL_HOME_FOR_TESTS")
    if real_home and "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(Path(real_home) / ".cache" / "ms-playwright")


def _chromium_is_installed() -> bool:
    """True if a Playwright Chromium build is present on disk.

    A bare full-suite ``pytest tests/`` from a dev who ran ``uv sync`` but not
    ``playwright install chromium`` would otherwise HARD-ERROR on the ``page``
    fixture's browser launch. We skip these e2e tests gracefully instead. CI is
    unaffected — the dedicated ``ui-e2e.yml`` job always installs Chromium first.
    """
    browsers_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or str(
        Path.home() / ".cache" / "ms-playwright"
    )
    return any(Path(browsers_path).glob("chromium-*"))


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip the ``tests/ui/`` e2e tests (only) when Chromium isn't installed."""
    del config
    if _chromium_is_installed():
        return
    ui_dir = Path(__file__).parent
    skip = pytest.mark.skip(
        reason="Playwright Chromium not installed — run `playwright install chromium` "
        "(or exclude with `-m 'not e2e'`). CI's ui-e2e job installs it."
    )
    for item in items:
        try:
            item.path.relative_to(ui_dir)
        except ValueError:
            continue  # not a tests/ui/ item — leave it alone
        item.add_marker(skip)

# ---------------------------------------------------------------------------
# Synthetic WP identity — the exact values the e2e test asserts against.
# Single source of truth: the `dashboard` fixture below hands these back to
# the test as a plain dict so both files stay in sync without a cross-file
# type import (tests/ui/ intentionally carries no __init__.py; see WP01 spec).
# ---------------------------------------------------------------------------
MISSION_SLUG = "001-synthetic-ui-mission"
WP_ID = "WP01"
WP_TITLE = "Sample Work Package"
WP_AGENT_TOOL = "claude"
WP_AGENT_MODEL = "claude-opus-4-6"
WP_AGENT_PROFILE = "implementer-ivan"
WP_AGENT_ROLE = "implementer"
WP_PROMPT_BODY = (
    "This is the synthetic prompt body used by the Playwright "
    "kanban-to-modal regression test (mission "
    "playwright-ui-e2e-bootstrap-01KWX72W, issue #1008)."
)


def _new_event_id() -> str:
    """Return a fresh ULID string.

    Tolerates both `python-ulid` API shapes (module-level `new()` on newer
    releases, bare `ULID()` constructor on the version pinned today) the
    same way `specify_cli.status.emit._generate_ulid` does, without
    importing that private helper across a package boundary.
    """
    if hasattr(ulid, "new"):
        return str(ulid.new().str)
    return str(ulid.ULID())


def _write_wp_frontmatter(tasks_dir: Path) -> None:
    """Materialize one synthetic WP using the frontmatter shape the scanner decomposes.

    Uses the **dict** `agent: {tool, model}` form (+ top-level
    `agent_profile`/`role` keys) that
    `dashboard/scanner.py::_process_wp_file` (:851-869) reads directly:

        agent_raw = wp_meta_dict.agent
        if isinstance(agent_raw, dict):
            agent_str = agent_raw.get("tool", "")
            model_str = agent_raw.get("model", "")

    The dominant colon-string form (`agent: 'tool:model:profile:role'`) is
    deliberately NOT used: the scanner assigns that whole string to `agent`
    verbatim and leaves `model` blank, which would make the modal-scoped
    `model` assertion vacuous (FR-003).
    """
    wp_path = tasks_dir / f"{WP_ID}.md"
    wp_path.write_text(
        f"""---
work_package_id: {WP_ID}
title: {WP_TITLE}
dependencies: []
subtasks: []
phase: "1"
assignee: ""
agent:
  tool: {WP_AGENT_TOOL}
  model: {WP_AGENT_MODEL}
agent_profile: {WP_AGENT_PROFILE}
role: {WP_AGENT_ROLE}
---
# Work Package Prompt: {WP_TITLE}

{WP_PROMPT_BODY}
""",
        encoding="utf-8",
    )


def _seed_event_log(feature_dir: Path) -> None:
    """Seed one genesis->planned event so the WP resolves off the canonical log.

    `dashboard/scanner.py::_process_wp_file` resolves a WP's lane either via
    the legacy `tasks/<lane>/*.md` directory layout or via the canonical
    event log (`has_event_log`). A flat `tasks/WP01.md` with no lane
    subdirectories is NOT legacy format, so the event log is the only path
    that yields a populated kanban card — an absent log raises
    `CanonicalStatusNotFoundError` inside `scan_feature_kanban`, which is
    swallowed into an empty board (no card to click at all).
    """
    event = StatusEvent(
        event_id=_new_event_id(),
        mission_slug=MISSION_SLUG,
        wp_id=WP_ID,
        from_lane=Lane.GENESIS,
        to_lane=Lane.PLANNED,
        at=datetime.now(UTC).isoformat(),
        actor="fixture",
        force=False,
        execution_mode="worktree",
    )
    append_event(feature_dir, event)


@pytest.fixture
def synthetic_project_root(tmp_path: Path) -> Path:
    """A temp project root with one synthetic mission/WP the scanner can read.

    Hermetic: no real `~/.spec-kitty`, no network, no git repository — just
    the `kitty-specs/<mission>/tasks/WP01.md` + `status.events.jsonl` layout
    `dashboard/scanner.py` needs to list the mission and populate its kanban.
    """
    feature_dir = tmp_path / "kitty-specs" / MISSION_SLUG
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    _write_wp_frontmatter(tasks_dir)
    _seed_event_log(feature_dir)
    return tmp_path


@pytest.fixture
def dashboard(synthetic_project_root: Path) -> dict[str, str]:
    """Boot the dashboard in-thread against the synthetic project root.

    Uses `start_dashboard(project_dir, port, background_process=False)`
    (`dashboard/server.py:110`) — the hermetic seam that runs the real
    stdlib HTTP server on a daemon thread inside THIS process. Deliberately
    NOT `cli/commands/dashboard.py`'s `ensure_dashboard_running` singleton,
    which detaches a PID'd child process and kills siblings on the shared
    port range (xdist flake risk per FR-002).

    No explicit teardown call is exposed by `start_dashboard` for
    `background_process=False` — the server thread is a daemon thread
    (`server.py:150`, `daemon=True`) bound to an ephemeral `find_free_port()`
    port, so it dies with the pytest process rather than needing an
    early stop.
    """
    port = find_free_port()
    actual_port, _pid = start_dashboard(
        synthetic_project_root, port=port, background_process=False
    )
    return {
        "base_url": f"http://127.0.0.1:{actual_port}",
        "agent": WP_AGENT_TOOL,
        "model": WP_AGENT_MODEL,
        "agent_profile": WP_AGENT_PROFILE,
        "role": WP_AGENT_ROLE,
        "prompt_body": WP_PROMPT_BODY,
    }
