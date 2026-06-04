"""Agent-facing Spec Kitty upgrade prompt instructions."""

from __future__ import annotations


AGENT_UPGRADE_CHECK_BLOCK = """## Startup Upgrade Check

Before continuing, run:

```bash
spec-kitty upgrade --agent-check --json
```

If JSON `action` is `none`, continue.
If `action` is `auto_upgrade`, run `upgrade_command` before continuing. If it fails, tell the user and continue with the current Spec Kitty version.
If `action` is `guidance`, show `upgrade_note` briefly, then continue.
If `action` is `prompt`, ask the user with the host-native question UI when available:

`Spec Kitty {latest_version} is available. You are on {installed_version}. Upgrade now?`

Use these choices:

1. Upgrade now (recommended) - record `upgrade_now`, run `upgrade_command`, then continue.
2. Always keep me up to date - record `always`, run `upgrade_command`, then continue.
3. Not now - record `not_now`, then continue.
4. Never ask again - record `never_ask`, then continue.

Record the selected choice before continuing:

```bash
spec-kitty upgrade --agent-choice <upgrade_now|always|not_now|never_ask> --agent-latest <latest_version> --json
```

If no host-native question UI is available, present the same four choices in plain text and wait for the user.
In non-interactive hosts, choose `not_now` and continue.
"""


def prepend_agent_upgrade_check(body: str) -> str:
    """Prepend the agent upgrade-check block unless already present."""
    if "spec-kitty upgrade --agent-check --json" in body:
        return body
    if not body:
        return AGENT_UPGRADE_CHECK_BLOCK
    separator = "\n\n" if not body.startswith("\n") else "\n"
    return f"{AGENT_UPGRADE_CHECK_BLOCK}{separator}{body}"


__all__ = ["prepend_agent_upgrade_check"]
