"""Pinned versions for rendering the committed generated fixtures (#3447, FR-005).

The committed generated assets are rendered with a *fixed* version marker so the
fixtures stay stable across CLI version bumps:

- the twelve-agent command baselines under
  ``tests/specify_cli/regression/_twelve_agent_baseline/`` use
  :data:`FIXTURE_COMMAND_RENDER_VERSION`;
- the codex/vibe skill snapshots under
  ``tests/specify_cli/skills/__snapshots__/`` use
  :data:`FIXTURE_SKILL_RENDER_VERSION`.

This module is the SINGLE SOURCE OF TRUTH for those two pins. Both the
fixture-parity tests and the ``spec-kitty regen`` command import them, so the
regeneration tool and the gate that checks its output can never silently
diverge (previously the two versions were hard-coded independently in the two
test modules).
"""

from __future__ import annotations

# Version marker baked into the twelve non-migrated agents' command files.
FIXTURE_COMMAND_RENDER_VERSION = "3.1.2a3"

# Version passed to the Agent Skills renderer for codex/vibe snapshots.
FIXTURE_SKILL_RENDER_VERSION = "3.0.0"

__all__ = [
    "FIXTURE_COMMAND_RENDER_VERSION",
    "FIXTURE_SKILL_RENDER_VERSION",
]
