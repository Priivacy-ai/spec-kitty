# Research: LOC-insensitive census freshness gate

## Reproduction (live evidence, red-first witness)

On `main` @ `8d4d03197` (census present):

- Baseline: `test_census_worklist_matches_live_derivation` → **PASS**.
- Add 3 lines to a worklist dir (`src/specify_cli/bulk_edit/_zzz_probe.py`) → **FAIL**:
  ```
  {'dir': 'bulk_edit', 'loc': 1276, 'cone_roots': [...], 'target_group': 'agent_surface', 'target_shard': 'specify-cli-rest'}
  != {'dir': 'bulk_edit', 'loc': 1279, ...same...}
  ```
  Only `loc` differs; membership + routing identical.
- Revert → **PASS**.

This isolates the tax to (a) the exact `loc` field carried on each worklist entry and
(b) the `sort by -loc` ordering used by list-equality. Neither adds protection beyond
membership + routing.

## Decision

**Chosen: membership + live-floor (ticket options (c)+(e)).** Narrow the freshness
comparison to a dir-keyed routing index (`dir -> {cone_roots, target_group,
target_shard}`), order- and LOC-insensitive; drop `loc` at the shared derivation
(`live_derived_worklist`); re-verify the LOC floor against the live tree.

### Rationale

The gate's stated job is a **routing-completeness invariant** (every worklist dir
routes to a named src-backed group; none falls to `unmatched -> run_all`). Its three
documented "teeth" — hand-trim reds, floor-crossing reds, new-hot-dir reds — are all
**membership** changes, which the dir-keyed index catches. The exact `loc` value and
the LOC sort order carry the entire false-positive cost while adding nothing the teeth
need. Applying the fix at the shared derivation also fixes the `--verify-census` CLI by
construction (it consumes the same `build_census`/`live_derived_worklist`), so no second
authority is introduced (charter single-canonical-source).

### Alternatives considered (from ticket #2416)

| Option | Verdict |
|--------|---------|
| (a) LOC tolerance/percentage-drift band | Rejected: keeps a stored number that drifts within-band (a committed lie) and still reds at band boundaries; adds a fuzzy concept. |
| (b) Auto-regenerate-and-commit census in CI (bot commit) | Rejected: heavy infra, bot-write permissions on a fork workflow, unnecessary once exact LOC is off the comparison surface. |
| (c) Coarser signal — membership + LOC floor only | **Chosen** (merged with (e)). |
| (d) Demote freshness to soft/warn | Rejected: throws away the anti-vacuous-pass teeth (a hand-trim would no longer red). |
| (e) Narrow / drop the freshness-equality test | **Chosen** (merged with (c)): narrowed to membership + routing, not dropped. |

## Post-spec adversarial gate outcomes folded

- FR-007 (order-insensitivity) had no binding success criterion → added SC-007 and made
  the red-first reproduction a **rank-altering** churn so both loc-drop and
  order-insensitivity are forced by one failing test.
- `arch_blind_groups` de-LOC is unfalsifiable on the empty, structurally-pinned-empty
  surface → deferred to Out of Scope.
- Refuted `--verify-census` finding confirmed the derivation-level fix (both surfaces
  fixed by construction) → encoded in C-001.
