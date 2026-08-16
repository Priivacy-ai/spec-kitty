# Contract: Missing-Charter Advisory Decision Matrix

**Governs**: `run_charter_preflight()` (`src/specify_cli/charter_runtime/preflight/runner.py`) when called with `allow_missing_charter=True`, and its two callers in `src/specify_cli/charter_runtime/preflight/hook.py` (`run_preflight_or_abort` — consumed by `spec-kitty next` and `spec-kitty implement WP##` — and `run_preflight_for_dashboard`).

**Purpose**: Pin the exact input→output mapping this mission changes, so implementation and review can check behavior against a single table instead of prose. Supersedes no prior contract — this is new.

## Inputs

- `checks`: the three `CharterPreflightCheck` states (`charter_source`, `synced_bundle`, `synthesized_drg`), each `fresh | stale | missing | built_in_only | invalid`.
- `charter_md_present`: whether display-only `.kittify/charter/charter.md` exists on disk. It is consulted only after canonical states qualify for advisory mode and selects warning copy, never pass/block behavior.

## Decision table

| # | charter_source | synced_bundle | synthesized_drg | charter.md present | `passed` | `blocked_reason` | `warnings` |
|---|-----------------|-----------------|---------------------|----------------------|----------|-------------------|------------|
| 1 | missing | missing | missing | absent | `True` | `None` | `[FRESH_PROJECT_WARNING]` |
| 2 | missing | missing | missing | present | `True` | `None` | `[LEGACY_BUNDLE_WARNING]` |
| 3 | missing | missing | built_in_only | absent | `True` | `None` | `[FRESH_PROJECT_WARNING]` |
| 4 | missing | missing | built_in_only | present | `True` | `None` | `[LEGACY_BUNDLE_WARNING]` |
| 5 | missing | stale/invalid/other | any | any | `False` (unchanged) | existing derived reason | `[]` |
| 6 | missing | any | stale/invalid/other | any | `False` (unchanged) | existing derived reason | `[]` |
| 7 | invalid/stale/fresh/other source combinations not already passing normally | any | any | any | `False` (unchanged) | existing derived reason | `[]` |

**Authority invariant**: rows 1/2 and 3/4 prove that changing only `charter.md` presence cannot change `passed` or `blocked_reason`; it changes warning text only. Rows 5–7 prove that `charter.md` cannot exempt stale, invalid, or partial canonical residue. The implementation must evaluate the canonical advisory predicate before the display-only wording selector.

## Consumer-level contract

| Consumer | Rows 1–4 (`passed=True`) | Rows 5–7 (`passed=False`) |
|----------|---------------------------|-----------------------------|
| `spec-kitty next` | every advancing/query and human/JSON mode emits advisories to stderr + continues; JSON stdout stays clean | advancing mode prints/encodes `blocked_reason`, exits 1, no state mutation; query stays read-only |
| `spec-kitty implement WP##` | emit each advisory warning to stderr + continue | abort before worktree alloc / `.kittify/` writes |
| dashboard serve/start | persist and render advisory warning; start server | persist and render `blocked_reason`; start server |

## Non-goals reaffirmed

This contract does **not** change rows 5–7 in any way. Any implementation or test change that alters their `blocked_reason`, `passed` value, or exit code is a regression. `charter.md` is behaviorally inert for every pass/block decision (doctrine C-001 / FR-016).
