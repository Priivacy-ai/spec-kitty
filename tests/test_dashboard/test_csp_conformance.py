"""CSP-conformance guard for the dashboard shell (issue #66).

The dashboard sends ``Content-Security-Policy: script-src 'self';
style-src 'self'`` (:mod:`specify_cli.dashboard.csp`) on every response.
Under that policy the browser silently refuses to run:

- inline event handlers (``onclick="…"`` / ``onchange="…"`` attributes),
- executable inline ``<script>`` blocks,
- scripts from any non-self origin.

PR #970-era markup relied on all three, so wiring the CSP in (D2) left the
dashboard shell unable to navigate at all — the deterministic
``tests/ui/test_kanban_card_click…`` red on main that issue #66 tracks. These
tests pin the shell to the CSP-conformant shape so a future edit cannot
quietly reintroduce an inline handler or a remote script tag: under CSP those
failures are *silent* (a console message, not an error), so no Python-level
test except this source inspection can catch them.

Covers ``templates/index.html`` only; ``templates/glossary.html`` still
carries blocked inline style/script blocks and is tracked in #71.
"""

from __future__ import annotations

import re

from specify_cli.dashboard.csp import DASHBOARD_CSP
from specify_cli.dashboard.templates import get_dashboard_html

import pytest

pytestmark = [pytest.mark.integration]

_INLINE_HANDLER_RE = re.compile(r"\son[a-z]+\s*=")
# An executable script is any <script> without a src and without a
# non-executing type (JSON data islands are inert and CSP-safe).
_EXECUTABLE_INLINE_SCRIPT_RE = re.compile(r"<script(?![^>]*\bsrc=)(?![^>]*type=\"application/json\")[^>]*>", re.IGNORECASE)
# Accepts double- or single-quoted, unquoted, and protocol-relative (`//host`)
# forms — a bare `https?://` + double-quote match missed all three (#83).
_REMOTE_ASSET_RE = re.compile(r"<(?:script|link)[^>]+(?:src|href)\s*=\s*['\"]?(?:https?:)?//", re.IGNORECASE)


def test_shell_policy_is_the_strict_self_only_csp() -> None:
    """Guard the premise: if DASHBOARD_CSP loosens, these tests need revisiting."""
    assert "script-src 'self'" in DASHBOARD_CSP
    assert "'unsafe-inline'" not in DASHBOARD_CSP


def test_shell_has_no_inline_event_handlers() -> None:
    html = get_dashboard_html()

    offenders = _INLINE_HANDLER_RE.findall(html)
    assert not offenders, (
        f"index.html carries inline event handlers {offenders} — the dashboard CSP blocks them, so the control is dead; attach the listener in dashboard.js instead"
    )


def test_shell_has_no_executable_inline_script_blocks() -> None:
    html = get_dashboard_html()

    offenders = _EXECUTABLE_INLINE_SCRIPT_RE.findall(html)
    assert not offenders, (
        "index.html carries executable inline <script> blocks {offenders} — "
        "the dashboard CSP blocks them; move the code into dashboard.js (or a "
        'type="application/json" data island for data)'
    )


def test_shell_loads_no_remote_scripts_or_styles() -> None:
    html = get_dashboard_html()

    offenders = _REMOTE_ASSET_RE.findall(html)
    assert not offenders, (
        f"index.html references remote assets {offenders} — the dashboard CSP (`script-src 'self'`) blocks them; vendor the asset under static/dashboard/ instead"
    )


def test_shell_still_wires_marked_and_behaviors_from_self() -> None:
    """The conformance rules above must not drift into stripping behavior."""
    html = get_dashboard_html()
    assert '<script src="/static/dashboard/vendor/marked.min.js"></script>' in html
    assert '<script src="/static/dashboard/dashboard.js"></script>' in html


@pytest.mark.parametrize(
    ("pattern", "description"),
    [
        (_INLINE_HANDLER_RE, "inline event handler"),
        (_EXECUTABLE_INLINE_SCRIPT_RE, "executable inline script"),
        (_REMOTE_ASSET_RE, "remote asset reference"),
    ],
)
def test_offender_patterns_detect_real_violations(pattern: re.Pattern[str], description: str) -> None:
    """Non-vacuity: each guard regex must flag a known-bad snippet."""
    samples = {
        "inline event handler": "<button onclick=\"switchPage('kanban')\">go</button>",
        "executable inline script": "<script>switchPage('kanban');</script>",
        "remote asset reference": '<script src="https://cdn.example.com/x.js"></script>',
    }
    assert pattern.search(samples[description]), f"{description} pattern failed to detect its sample"


@pytest.mark.parametrize(
    "snippet",
    [
        "<script src='https://host/x.js'></script>",
        "<script src=//host/x.js></script>",
        "<script src=https://host/x.js></script>",
    ],
)
def test_remote_asset_pattern_detects_quoting_variants(snippet: str) -> None:
    """Non-vacuity for the #83 widening: each form was previously missed by every guard."""
    assert _REMOTE_ASSET_RE.search(snippet), f"remote asset pattern failed to detect: {snippet}"
