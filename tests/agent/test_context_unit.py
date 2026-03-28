"""Unit tests for agent context CLI commands.

The agent_context module (parse_plan_for_tech_stack, update_agent_context, etc.)
was deleted in WP10.  The update-context CLI command was removed at the same time.
Only the 'resolve' command remains, which delegates to execution_context.
"""

from __future__ import annotations
