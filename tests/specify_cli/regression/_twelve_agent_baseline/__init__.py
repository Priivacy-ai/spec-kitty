"""Fixture tree: post-mission-083 command-file baseline for twelve agents.

Each subdirectory holds the expected command-file content for one agent key
from ``AGENT_COMMAND_CONFIG``.  Files are named ``<command>.<ext>`` where
``<ext>`` is the agent-specific extension (``md``, ``toml``, or
``prompt.md``).

This baseline was captured at mission 083 completion (after WP01–WP06 merged
but before WP07).  It is NOT a pre-mission byte-identity check — pre-vs-post
identity is infeasible because WP02 edited source templates, changing rendered
output for all agents.  Instead, it locks in post-mission behavior so any
future unintended drift for the twelve non-migrated agents is caught.

Regenerate after intentional template changes with::

    PYTEST_UPDATE_SNAPSHOTS=1 pytest tests/specify_cli/regression/ -v
"""
