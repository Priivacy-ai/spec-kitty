# Contract: Cutover CLI + Upgrade Migration (FR-001..FR-003, FR-010)

The behavioural contract for the two callers of the shared cutover orchestration helper. This is the
acceptance surface for IC-01 and IC-02.

## Shared orchestration helper — `migration/runtime_state_cutover.py`

```
cutover_mission(feature_dir, *, dry_run=False) -> CutoverResult
    1. backfill  = backfill_runtime_state(feature_dir, dry_run=dry_run)   # idempotent seeds
    2. verify    = verify_backfill(feature_dir)                           # count+value, fail-closed
    3. if not verify.ok:  return CutoverResult(flipped=False, verify=verify)   # NEVER flip
    4. if dry_run:        return CutoverResult(flipped=False, would_flip=True, verify=verify)
    5. write meta.json status_phase = "1"   (sole writer; only reached on ok verify)
    6. return CutoverResult(flipped=True, verify=verify)
```

- **Ordering is by construction** — verify is called on the un-stripped frontmatter (never strip before
  verify; `MigrationOrderingError` guards it).
- **Sole writer of `status_phase`** — no other code path writes it; step 5 is unreachable on a failed verify.
- **Write target** — resolved via `canonicalize_feature_dir` inside the library; the helper adds no
  `Path.cwd()` path (INV-5 / #2815).

`CutoverResult` fields: `slug`, `flipped: bool`, `would_flip: bool` (dry-run), `seeded_count: int`,
`verify: VerifyResult`, `error: str | None`.

## Operator CLI — `spec-kitty migrate backfill-runtime-state`

Registered as `@app.command(name="backfill-runtime-state")` in `cli/commands/migrate_cmd.py`.

| Option | Behaviour |
|--------|-----------|
| `--dry-run` | Seed nothing, flip nothing; report per-mission would-seed counts and would-flip. |
| `--mission <handle>` | Scope to one mission (mission_id / mid8 / slug); default = whole corpus. |
| (default) | Walk `kitty-specs/`, run `cutover_mission` per mission. |

**Exit semantics (per-mission best-effort — research D-03):**
- Runs every mission independently; flips each that verifies; records failures.
- **Exit 0** iff every visited mission either flipped or was already migrated (idempotent skip).
- **Exit non-zero** if any mission's verify failed; prints each mismatch. **No** unverified mission is
  ever flipped.
- Idempotent: a second run seeds nothing and re-flips nothing.

**Acceptance (maps to spec scenarios US1):**
1. `--dry-run` on a corpus with legacy runtime state → reports counts, writes 0 events, 0 flips.
2. real run → snapshot == old reader (count+value) for every WP; `status_phase="1"` only for passed missions.
3. fault-injected corrupt deterministic seed row → run aborts that mission's flip, exits non-zero, names the mismatch; `status_phase` untouched for it.
4. re-run → 0 new seeds, 0 flips (idempotent).

## Upgrade migration — `upgrade/migrations/m_<version>_runtime_state_backfill.py`

- Self-registers via `@MigrationRegistry.register`; discovered by `auto_discover_migrations()`.
- Version-key prefix sorts **after** the charter-fold migrations.
- Calls the same `cutover_mission` per mission over the project corpus.

**Fail-closed abort semantics (stricter than CLI — research D-03, NFR-005):**
- **Any** mission's verify failure **aborts the migration step** with an operator-actionable message
  naming the mission + mismatch; leaves **no** mission half-flipped (each mission's flip is atomic).
- **No-op** when there is no `kitty-specs/` or no mission carries legacy runtime state (fresh install).
- **Idempotent** — a re-run (already-migrated corpus) seeds nothing and completes clean.

**Acceptance (maps to spec scenarios US3):**
1. legacy deployment → migration runs, corpus backfilled+verified+flipped.
2. fresh install → migration no-ops.
3. a mission fails verify → migration step aborts fail-closed with an actionable message; no partial flip.

## Cross-cutting guards

- **INV-5 regression test**: after backfill (CLI and migration), assert no `status.events.jsonl` (or any
  event file) is created at repo root (#2815 co-constraint).
- **Dead-symbol un-pin (C-006)**: IC-01 removes the 15-symbol
  `_CATEGORY_C_DEFERRED_RUNTIME_STATE_BACKFILL_CUTOVER` frozenset in the same WP that first wires a caller.
- **No suppression (NFR-004)**: `ruff` + `mypy` clean; complexity ≤15 (helper split into seed/verify/flip phases).
