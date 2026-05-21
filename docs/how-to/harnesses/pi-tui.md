# Use Spec Kitty in Pi TUI

> **Tier:** **partial** — no on-disk installer surface located in 3.2, and no current canonical public documentation could be confirmed at the access date.
> **Citation (accessed 2026-05-21):** *(none located 2026-05-21 — see [supported-harnesses matrix](../../reference/supported-harnesses.md))*

## Partial-tier note

Pi TUI is classified `partial` in the 3.2 [support matrix](../../reference/supported-harnesses.md) because:

1. The Spec Kitty installer does **not** currently produce an on-disk command surface for Pi TUI (no `.pi/` or equivalent directory is created by `spec-kitty init`).
2. No current canonical public documentation URL could be located at the access date 2026-05-21.

Until a stable installer target and external citation land, this page intentionally does **not** prescribe an invocation syntax. Promotion to `supported` requires (a) an installer that produces a complete `/spec-kitty.*` set, (b) a current external citation, and (c) at least one documented smoke test (see [`docs/development/3-2-harness-research-method.md`](../../development/3-2-harness-research-method.md) §6).

## Prerequisites

- **Spec Kitty CLI installed.** See [Install Spec Kitty](../install-spec-kitty.md).
- **Project initialized.** Note that `spec-kitty init --agent pi` is **not** a supported configuration in 3.2 — initialize with a configured harness instead (Claude Code, Codex, OpenCode, etc.), then dogfood Pi TUI against the resulting `kitty-specs/` artifacts manually.

## Where Spec Kitty installs files

**None.** Per the [supported-harnesses matrix](../../reference/supported-harnesses.md), Pi TUI has no installed surface in 3.2.

## Canonical invocation

**Not yet defined.** Do not fabricate a slash-command or skill syntax for Pi TUI; consult the Pi TUI project directly when a stable public reference becomes available.

## Worked example

Until installer support lands, use Pi TUI as a **read-only** view onto Spec Kitty artifacts:

1. From your project root, drive a normal mission lifecycle through any configured harness (for example, Claude Code: `/spec-kitty.specify "a hello world page"`).
2. The mission spec lands at `kitty-specs/hello-world-page-<mid8>/spec.md` on disk.
3. Open Pi TUI against the same project directory and inspect the `kitty-specs/` tree as plain files.

This is the only flow we can confirm at 2026-05-21.

## Troubleshooting

- **No `/spec-kitty.*` commands inside Pi TUI.**
  Expected — Pi TUI is `partial` in 3.2 with no installer surface. Drive Spec Kitty from a supported harness (Claude Code, Codex, OpenCode, Cursor, Gemini, Qwen, Amazon Q, Copilot, Augment, Roo, Kilo, Kiro, Windsurf) and read the artifacts back from disk in Pi TUI.

- **Profile not loading.**
  The `/ad-hoc-profile-load` workflow assumes a slash-command host. Until Pi TUI has an installer surface, use the helper from your other configured harness and reuse the same `kitty-specs/<mission>/` tree.

## Where to learn more about Pi TUI

No current canonical public documentation could be located at 2026-05-21. The matrix row in [`docs/reference/supported-harnesses.md`](../../reference/supported-harnesses.md) is the authoritative tracker — promotion (and a citation) will land here when evidence is recorded.
