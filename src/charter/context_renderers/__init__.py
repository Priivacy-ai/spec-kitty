"""Sub-renderers for the resolved charter context payload.

This package hosts the helpers that compose the resolved context text
returned by :func:`charter.context.build_charter_context`.  Splitting the
helpers into a dedicated submodule keeps the ownership boundaries clean
between the WPs that extend ``src/charter/context.py``:

* WP03 owns the profile-cited renderers (still in ``context.py``).
* **WP04 owns this submodule**: ``authority_paths`` + ``section_bodies``.
* WP05 owns subsequent budget/governance composition.

Public surface (re-exported for convenience):

* :func:`render_authority_paths` — render the ``Project authority paths:``
  block (FR-003) from the on-disk default authority directories plus any
  charter-declared ``authority_paths`` entries.
* :func:`render_critical_section_bodies` — render the
  ``Action-Critical Charter Sections (<action>):`` block (FR-001) with
  verbatim section bodies (or fetch + when-doing stanzas when a section
  is missing from the charter).

Both helpers are pure functions: they do not touch global state and they
do not raise into the caller (best-effort rendering keeps the prompt
build hot path resilient — see NFR-004 / NFR-005).
"""

from __future__ import annotations

from charter.context_renderers.authority_paths import (
    AUTHORITY_PATHS_HEADER,
    DEFAULT_AUTHORITY_PATHS,
    DEFAULT_CHARTER_DECLARED_WHEN_CLAUSE,
    render_authority_paths,
)
from charter.context_renderers.fetch_stanza import (
    DEFAULT_WHEN_CLAUSE,
    fetch_stanza,
    fetch_stanza_lines,
    format_selector,
)
from charter.context_renderers.section_bodies import (
    ACTION_CRITICAL_SECTIONS,
    CRITICAL_SECTION_WHEN_CLAUSES,
    critical_section_header,
    render_critical_section_bodies,
    render_critical_section_include,
)
from charter.context_renderers.token_budget import (
    BUDGET_DEFAULT,
    RenderedSection,
    apply_token_budget,
    warning_line,
)

__all__ = [
    "ACTION_CRITICAL_SECTIONS",
    "AUTHORITY_PATHS_HEADER",
    "BUDGET_DEFAULT",
    "CRITICAL_SECTION_WHEN_CLAUSES",
    "DEFAULT_AUTHORITY_PATHS",
    "DEFAULT_CHARTER_DECLARED_WHEN_CLAUSE",
    "DEFAULT_WHEN_CLAUSE",
    "RenderedSection",
    "apply_token_budget",
    "critical_section_header",
    "fetch_stanza",
    "fetch_stanza_lines",
    "format_selector",
    "render_authority_paths",
    "render_critical_section_bodies",
    "render_critical_section_include",
    "warning_line",
]
