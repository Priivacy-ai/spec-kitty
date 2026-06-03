---
title: "Use Spec Kitty in Roo Cline"
description: "Configure the Use Spec Kitty in Roo Cline harness for Spec Kitty 3.2 commands, generated skills, and agent workflow integration."
---

# Use Spec Kitty in Roo Cline

> **Tier:** supported.
> **Citation (accessed 2026-05-21):** <https://docs.roocode.com/>

## Prerequisites

- **Spec Kitty CLI installed.** See [Install Spec Kitty](../install-spec-kitty.md).
- **Project initialized for this harness:**
  ```bash
  spec-kitty init --ai roo
  ```
- **Roo Cline installed and configured** in your editor. Follow the [Roo Code documentation](https://docs.roocode.com/) for installation and authentication.

## Where Spec Kitty installs files

Per the [supported-harnesses matrix](../../reference/supported-harnesses.md), Roo Cline uses the slash-command mechanism. Spec Kitty installs:

- **Directory:** `.roo/commands/`
- **Files:** `spec-kitty.specify.md`, `spec-kitty.plan.md`, `spec-kitty.tasks.md`, `spec-kitty.implement.md`, `spec-kitty.review.md`, `spec-kitty.accept.md`, `spec-kitty.merge.md`, `spec-kitty.dashboard.md`, `spec-kitty.status.md`, `spec-kitty.charter.md`, `spec-kitty.analyze.md`, `spec-kitty.research.md`.

## Canonical invocation

Inside Roo Cline's chat, slash commands are invoked as:

```
/spec-kitty.specify "<one-line mission description>"
/spec-kitty.plan
/spec-kitty.tasks
/spec-kitty.implement WP01
```

## Worked example

1. Open your project in an editor with Roo Cline enabled.
2. In the Roo chat panel, type:
   ```
   /spec-kitty.specify "a hello world page"
   ```
3. Spec Kitty's interview prompts appear — answer them inline.
4. When asked for a kebab-case slug, supply something short, e.g. `hello-world-page`.
5. The mission spec lands at `kitty-specs/hello-world-page-<mid8>/spec.md`.

## Troubleshooting

- **`/spec-kitty.*` commands do not appear.**
  Run `spec-kitty agent config sync` from the repo root. This rewrites `.roo/commands/` from the canonical source templates. Reload your editor.

- **Profile not loading.**
  Run inside Roo:
  ```
  /ad-hoc-profile-load researcher-robbie
  ```
  Use the profile id from the work-package frontmatter.

## Where to learn more about Roo Cline

Authoritative documentation: <https://docs.roocode.com/> (accessed 2026-05-21).
