# Contract: Host-Surface Inventory Matrix

**Mission**: `phase-4-closeout-host-surfaces-and-trail-01KPWA5X`
**Covers**: FR-001 (inventory), FR-002 (parity), FR-006 (guidance-gap coverage), NFR-003 (100% surface coverage)
**Living location**: `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/artifacts/host-surface-inventory.md`
**Promoted location**: `docs/host-surface-parity.md` (created by WP05 on mission close)

## Purpose

One authoritative matrix, per mission, that lists every supported host surface and its parity status against the advise/ask/do governance-injection contract. Drives WP02–WP04 scope during Tranche A; becomes the durable operator-facing reference at closeout.

## Row schema

Columns in this exact order:

| # | Column | Type | Allowed values | Notes |
|---|--------|------|----------------|-------|
| 1 | `surface_key` | str | One of the keys in `AGENT_DIRS` from `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py` | Canonical host key. |
| 2 | `directory` | str | e.g. `.claude/commands/`, `.agents/skills/spec-kitty.advise/` | Relative to repo root. |
| 3 | `kind` | str | `slash_command` or `agent_skill` | Derived from the surface category. |
| 4 | `has_advise_guidance` | bool | `yes` / `no` | Does the surface teach when to call `advise`/`ask`/`do`? |
| 5 | `has_governance_injection` | bool | `yes` / `no` | Does the surface teach how to inject `governance_context_text`? |
| 6 | `has_completion_guidance` | bool | `yes` / `no` | Does the surface teach how to call `profile-invocation complete`? |
| 7 | `guidance_style` | str | `inline` or `pointer` | `inline` hosts the content; `pointer` links to the canonical skill pack. |
| 8 | `parity_status` | str | `at_parity`, `partial`, or `missing` | Composite judgement from columns 4–7. |
| 9 | `notes` | str | free text | Captures per-surface rationale — especially required for `pointer` style per FR-006. |

## Canonical host surface list

The 15 supported surfaces are:

### Slash-command surfaces (13)

| surface_key | directory | subdir |
|-------------|-----------|--------|
| `claude` | `.claude/` | `commands/` |
| `copilot` | `.github/` | `prompts/` |
| `gemini` | `.gemini/` | `commands/` |
| `cursor` | `.cursor/` | `commands/` |
| `qwen` | `.qwen/` | `commands/` |
| `opencode` | `.opencode/` | `command/` |
| `windsurf` | `.windsurf/` | `workflows/` |
| `kilocode` | `.kilocode/` | `workflows/` |
| `auggie` | `.augment/` | `commands/` |
| `roo` | `.roo/` | `commands/` |
| `q` | `.amazonq/` | `prompts/` |
| `kiro` | `.kiro/` | `prompts/` |
| `agent` | `.agent/` | `workflows/` |

### Agent Skills surfaces (2)

| surface_key | directory |
|-------------|-----------|
| `codex` | `.agents/skills/` (reads from tree directly) |
| `vibe` | `.agents/skills/` (via `.vibe/config.toml::skill_paths`) |

## Parity judgement rubric

| parity_status | Condition |
|---------------|-----------|
| `at_parity` | All three guidance flags `yes` **and** the surface matches the content shape shipped in `.agents/skills/spec-kitty.advise/SKILL.md` and `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`. |
| `partial` | Some guidance flags `yes`, some `no`, or guidance is present but not aligned with the reference content shape. |
| `missing` | All three guidance flags `no`. |

## Example row (worked)

```markdown
| claude | .claude/commands/ | slash_command | yes | yes | yes | inline | at_parity | Priority slice shipped in 3.2.0a5. Uses src/doctrine/skills/spec-kitty-runtime-next/SKILL.md content. |
```

```markdown
| copilot | .github/prompts/ | slash_command | no | no | no | pointer | missing | No governance-injection block present. WP04 will add a pointer to the canonical skill pack; .github/prompts/ is read into Copilot context via workspace-level prompts only. |
```

## Promotion rules (WP05)

When Tranche A closes:

1. Copy the matrix verbatim to `docs/host-surface-parity.md`.
2. Add a short preamble to the promoted doc explaining what the matrix is and how it is kept up to date (any new host integration MUST add a row).
3. Link the promoted doc from:
   - `docs/trail-model.md` (under "Host surfaces that teach the trail" subsection).
   - README governance section (one-line pointer).

## Acceptance

- **Mechanical**: `tests/specify_cli/docs/test_host_surface_inventory.py` parses `docs/host-surface-parity.md` after WP05, asserts every `surface_key` from `AGENT_DIRS` has exactly one row, and asserts each row's `parity_status` is one of the three allowed values. Covers FR-001 / NFR-003.
- **Textual**: Each row with `parity_status != "at_parity"` must have a non-empty `notes` column explaining the gap and the remediation plan. Covers FR-006.
