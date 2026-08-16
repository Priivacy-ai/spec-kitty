# Phase 1 Data Model: Charter Preflight Missing-Charter Advisory Mode

This mission introduces no persistent data, no schema change, and no new dataclass fields. It composes entirely with the existing `charter_runtime/preflight` value objects. This document exists to make that composition explicit for `/spec-kitty.tasks`.

## Existing entities consumed (unchanged shape)

### `CharterPreflightCheck` (`result.py`)
- `name`: one of `charter_source`, `synced_bundle`, `synthesized_drg`
- `state`: `fresh` | `stale` | `missing` | `built_in_only` | `invalid`
- `detail`, `remediation`: str | None

No fields added. The canonical predicate reads this structure; the display-only selector reads only `charter.md` after the canonical decision. Neither writes to it.

### `CharterPreflightResult` (`result.py`)
- `passed: bool`
- `checks: list[CharterPreflightCheck]`
- `auto_refresh_applied: bool`, `auto_refresh_actions: list[str]`
- `blocked_reason: str | None`
- `warnings: list[str]` — populated with exactly one fresh or legacy advisory. Mutation hooks emit it to stderr; dashboard persists it through the existing warning channel.

No fields added.

## New logical concept: canonical missing-charter exemption + warning presentation

The first three columns alone decide whether the exemption applies. `charter.md` presence selects warning presentation only:

| Shape | `charter_source` | `synced_bundle` | `synthesized_drg` | `.kittify/charter/charter.md` on disk | Result |
|-------|-------------------|------------------|---------------------|------------------------------------------|--------|
| Canonically missing, fresh presentation | `missing` | `missing` | `missing` or `built_in_only` | absent | `passed=True`, fresh-project warning |
| Canonically missing, legacy presentation | `missing` | `missing` | `missing` or `built_in_only` | present | `passed=True`, legacy-bundle warning |
| Stale/invalid/other partial state | any non-qualifying combination | — | — | absent or present | unchanged blocking logic |

Changing only `charter.md` can never change `passed` or `blocked_reason`. The complete executable contract is in `contracts/missing-charter-advisory-matrix.md`.

## State transitions

None. Charter preflight is a stateless, read-only computation per invocation — it has no persisted state machine of its own (distinct from the mission `status.events.jsonl` model elsewhere in this codebase). Each `next`/`implement`/dashboard call independently recomputes `CharterFreshness` from the current filesystem contents.
