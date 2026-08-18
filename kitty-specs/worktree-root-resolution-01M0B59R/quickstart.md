# Quickstart: Reproducing & Verifying the Invariants

Red-first (NFR-001): each behavioral invariant has a regression **authored and shown failing on base** before the fix — not a `-k` glob over tests that don't exist yet (a glob matching nothing exits 0 and reads as success). Pin each to its issue with `@pytest.mark.regression`. For the fail-closed slices the red-on-base assertion is **refusal / absence-of-false-green** (per #3128), not "writes into invoking checkout".

## Setup

```bash
git rev-parse --show-toplevel        # confirm the intended checkout
pip install -e .                     # spec-kitty must shell out to THIS tree (stale-install gotcha)
# Fixtures: a primary, a linked lane worktree (foreign), and a nested clone.
```

## Reproducing each invariant (author the test, then show it red on base)

### SC-001 — Fail-closed on a foreign-checkout write (FR-002, FR-003)

- `doctor tool-surfaces --fix` from a lane worktree: **red on base** = it silently repairs the *primary's* `.claude/commands/*` manifest; **green after** = it refuses, naming the primary checkout. (Cleanest confirmed defect, #2613.)
- `intake <plan>` from a lane worktree that would clobber the primary's shared brief slot: **red on base** = silent clobber; **green after** = identity-checked refusal naming the slot. `--force` still identity-checks. (#3540)
- Owner-checkout invocation MUST stay green throughout (no new refusal).

### SC-002 — No false-green guard (FR-005, FR-006)

- `setup-plan` from a lane worktree on a lane branch: **red on base** = `branch_matches_target: true` (reflecting primary's HEAD); **green after** = reflects the invoking checkout / `meta.json`. (#3124)
- `migrate backfill-runtime-state` cutover guard from a lane: **red on base** = passes by verifying the same redirected path it wrote; **green after** = invoking-checkout-aware / refuses. (#3049)

### SC-003 — Deliberate anchors stay green (FR-004, FR-008)

- Characterization tests over `get_feature_target_branch` / `resolve_merge_target_branch` / `mission_runtime/resolution.py`: **green on base and green after** — the fix must not flip them (#2320/#3328). These are guards, not red-first.

### SC-004 — One review-verdict path, both surfaces (FR-010…FR-013)

```bash
spec-kitty agent status emit --wp WP01 --to for_review ...
spec-kitty agent status emit --wp WP01 --to in_review ...
spec-kitty agent status emit --wp WP01 --to approved --review-result-json '{"verdict":"approve"}'
spec-kitty agent status emit --help    # no non-functional in_review/--evidence-json verdict example
```
- **red on base** = `emit` has no `--review-result-json`; the walk cannot exit `in_review` via emit. **green after** = full emit-only walk to `done`.
- `for_review` gate: same verdict on both surfaces across {primary, worktree, clone}; **both** directions — clone with satisfied commits passes, clone with unsatisfied commits fails.

### SC-005 — Snapshots round-trip & audit clean (FR-014…FR-016, FR-018)

- Audit a `review_result`-carrying `status_event_row`: **red on base** = `UNKNOWN_SHAPE` (key verified absent from the frozenset); **green after** = registered, clean.
- Value round-trip: replay a snapshot carrying `review_result`; assert the replayed projection **equals** the snapshot by value; a corrupted-value replay MUST fail (guards the key-only fake); the generator MUST emit ≥1 `review_result` event (non-vacuous). (Internal-API level — marked as such under NFR-001.)

### NFR-004 — Green sentinels (already-fixed)

- `407ea376c4` projection and `bec7c25273` repair preservation: **green on base and green after** sentinels; no WP regresses them to manufacture a red.

## Full verification (post-fix)

```bash
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider
PWHEADLESS=1 pytest tests/sync/test_orphan_sweep.py -n0 -q
pytest tests/architectural/            # terminology + shared-package + single-channel-refusal gate
ruff check . && mypy src/
spec-kitty analyze --mission worktree-root-resolution-01M0B59R
```

## Baseline-red note

Classify every failure before treating it as yours: pre-existing known-P0 reds (leave red), CI-env failures (auth/sync toggles), stale-install false reds (reinstall). Only failures red on this branch **and** green on `upstream/main` are in scope.
