---
name: spk-start-command-map
description: "Map Spec Kitty slash commands and CLI entry points to spk skills. Use when choosing /spec-kitty.* commands or explaining command-skill boundaries."
---

# spk-start-command-map

Route command questions without conflating command wrappers and operating
skills.

## Flow

1. Read `references/command-map.md`.
2. Choose the command for execution and the `spk-*` skill for operating
   guidance.
3. If the user asks for discovery rather than a command, route to
   `spk-meta-skill-map`.

## Boundary

`spec-kitty.<command>` skills are generated command wrappers for slash-command
compatibility. `spk-*` skills are user-facing operating guides. Keep both names:
commands stay dotted; public operating skills stay short and hierarchical.
