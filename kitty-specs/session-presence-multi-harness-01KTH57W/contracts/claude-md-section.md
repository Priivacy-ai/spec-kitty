# Contract: CLAUDE.md Orientation Block Format

## Purpose

Specifies the exact structure of the Spec Kitty orientation block injected into `.claude/CLAUDE.md` (and into any other Markdown rules file via `MarkdownRulesWriter`).

## Format

```
<!-- spec-kitty:orientation -->
**Spec Kitty v{version}** — project: {project_slug} ({health})
[optional upgrade line]
[optional migration line]

Two usage patterns:
- **Full mission** (spec → plan → tasks → implement → review → merge):
  trigger: "spec out", "create a mission", "write a spec", "plan this"
  → run `/spec-kitty.specify`
- **Lightweight dispatch** (ad-hoc fix, question, or advice — no mission created):
  trigger: "hey spec kitty", "use spec kitty to", "spec kitty, fix/do/ask/advise"
  → run `spec-kitty do "<request verbatim>"`
<!-- /spec-kitty:orientation -->
```

## Optional Lines

- **Upgrade line** (present only when `health == "upgrade-available"`):
  `⚠ Upgrade available: {available_version} — run \`spec-kitty upgrade --cli\` to update.`

- **Migration line** (present only when `health == "migration-required"`):
  `⚠ Project migration required — run \`spec-kitty upgrade\` before using missions.`

## Idempotency

- `has_presence()`: returns `True` if and only if `<!-- spec-kitty:orientation -->` appears anywhere in the file content.
- On re-write: the block between `<!-- spec-kitty:orientation -->` and `<!-- /spec-kitty:orientation -->` (inclusive) is replaced in-place. Lines outside the markers are not touched.
- On first write (append_mode=True): the block is appended to the file with a preceding newline. The file is created if it does not exist.
- On first write (append_mode=False): the block is written as the entire file content.

## Removal

`remove()` strips the block between the markers (inclusive) from the file. If `append_mode=False`, the file is deleted entirely.
