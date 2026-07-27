# Data Model — refactor-stable-gate-substrate-01KWK3FY

The entities are gate keys, inventory rows, and the theater contract.

## GateAllowlistKey (converted, IC-01)

| Field | Before | After | Role |
|---|---|---|---|
| `rel_path` | — (absent) | `str` (NEW) | Disambiguates qualname collisions (`implement`/`review` ×2) |
| `enclosing_qualname` | `str` | `str` | Function scope of the allowlisted site |
| `token_line` | `int` (raw AST lineno — THE fragility) | `str` (frozen `code_tokens_by_line` token) | The authoritative content comparand |

YAML entry shape (after):

```yaml
- file: specify_cli/cli/commands/agent/workflow.py   # NEW — part of the key
  qualname: implement                                # part of the key
  token: "feature_dir = primary_feature_dir_for_mission ( repo_root , handle )"  # FROZEN comparand
  line: 453        # NON-authoritative locator (diagnostics/jump-to only)
  reason: "..."    # unchanged
```

- The scanner emits `(rel_path, qualname, token)` from live source; comparison is set
  membership. `node.lineno` feeds NO key anywhere (SC-001 grep evidence).
- **Collision rule** (within one function, identical tokens): an entry covers all
  occurrences of that token in that function — if the gate must distinguish
  occurrences, the entry carries an explicit `count:` (default 1) and the scanner
  compares occurrence counts (mirrors the reference implementation's two-doctor-sites
  handling).
- Violation message format keeps `{file}:{line-locator} ({qualname})` for ergonomics;
  the locator is refreshed opportunistically, never compared.

## Audit row identity (converted, IC-02/IC-03)

| Row type | Before key | After key |
|---|---|---|
| `SinkRow` (untrusted) | `f"{rel_path}:{line}"` | `(rel_path, enclosing_qualname, token)` via `composite_key_from_file` |
| `ResolutionRow` (surface) | same | same |
| `SelectionRow` (surface) | same | same |

Inventory markdown rows keep their human columns; the `line` column becomes a
locator. Tagged rows: a row may carry `[inventory-only]` in its notes column to be
exempt from the overcount guard (narrow, documented use: retained documentation of an
intentionally-removed sink — each such row must reference the removing change).

## Tripwire directions (per audit, after IC-02/03)

1. **Undercount** (exists today, re-keyed): every DISCOVERED sink must match an
   inventory row by composite identity → RED naming the missing row otherwise.
2. **Overcount/ghost (NEW)**: every inventory row (minus `[inventory-only]`) must match
   a live discovered sink → RED naming the ghost row otherwise.
3. Check-3 (`KNOWN_CANDIDATE_FILES`) — path-level, already drift-immune, untouched.

## Theater triad (per converted gate — the acceptance instrument)

| Leg | Drives | Must |
|---|---|---|
| Drift-immunity | top-level `check_*_gate` / audit `main()`-equivalent with synthetic source shifted +1 line, allowlist/inventory untouched | stay GREEN |
| Content-detection | same entry point with an allowlisted/documented site's token edited | go RED (staleness/mismatch) |
| Non-vacuity | same entry point with a synthetic NEW offending site | go RED with actionable message |

All legs drive the exact entry points CI runs (T005 model) — helper-only theater is a
review reject.

## Quarantine set (IC-05)

- 31 marked nodes → 16 after CT9 (15 markers removed across ~5 files).
- Stay-behind reason format: `@pytest.mark.quarantine  # <honest diagnosis> — <issue ref>`.

## Doctrine styleguide delta (IC-04)

- +6 principles (research.md D7 outline), +patterns/anti_patterns with PR #2308-cited
  examples; `graph.yaml` regenerated (byte-freshness).

## Invariants

1. **Frozen-comparand invariant**: no stored/compared gate or audit key contains a raw
   line number after this mission (locators excepted, never compared).
2. **Tool-derivation invariant**: every frozen token was produced by
   `composite_key`/`composite_key_from_file` — hand-typed tokens are a review reject.
3. **Zero-production invariant** (NFR-002): no diff under `src/specify_cli/` or
   `src/runtime/`.
4. **Reference-implementation invariant**: `test_no_worktree_name_guess.py` keys are
   NOT modified (FR-005 is documentation only).
