---
name: spk-integrate-ci
description: "Integrate Spec Kitty with CI checks, release gates, automation, and machine-readable status without replacing runtime decisions."
---

# spk-integrate-ci

Use this skill when CI, automation, release tooling, or machine-facing status
needs to interact with Spec Kitty.

## Flow

1. Identify which gate CI should observe: status, review, accept, merge, sync,
   or mission review.
2. Prefer machine-readable command output where available.
3. Keep CI as an observer/enforcer, not an alternate mission runtime.
4. Link failures to a concrete recovery skill.

## Rule

CI may block unsafe work, but it should not invent mission state transitions.
