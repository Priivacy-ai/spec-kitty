---
name: spk-doctrine-profile-load
description: "Load a Spec Kitty agent profile on demand for interactive sessions, including identity, governance scope, boundaries, and initialization."
---

# spk-doctrine-profile-load

Use this skill when the agent needs a profile outside the runtime loop or the
user asks to adopt a specific role.

## Flow

1. Identify the requested profile and active mission context.
2. Load only the profile's initialization declaration and relevant boundaries.
3. Apply the role for the current session or routed task.
4. Return to `spk-run-next` for mission advancement.

## Legacy Alias

For detailed ad hoc profile mechanics, use `ad-hoc-profile-load` when
available.
