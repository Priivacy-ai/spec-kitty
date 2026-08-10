# Work Packages: kernel.clock — the single door to time

**Mission**: `kernel-clock-single-door` · **Spec**: [spec.md](./spec.md) (rev 1) · **Plan**: [plan.md](./plan.md) (rev 3) · **Tasks**: rev 2 (post-tasks squad)

Critical path is a serial chain on `clock.py`/the gate (WP00→WP01a→WP01b→WP02→WP03→WP04); then a parallel
per-package remediation lane where each WP ratchets **its own** `_exemptions/<owner>.txt` to empty; then
terminal gate hardening. Delivered as stacked PRs; the gate is fail-closed from WP01b, so every intermediate
PR is green and monotonically more-enforced. The `specify_cli` subpackage split (WP09–WP13) is confirmed
against the WP00 census (census-measured: sync 7, status+merge 5, core 7, cli 13, auth+compat 12 files — all
≤~15); any lane exceeding ~15 owned files splits and triggers a `finalize-tasks` re-run before the fan-out.

## Dependency graph

```
WP00 ─► WP01a ─► WP01b ─► WP02 ─► WP03 ─► WP04 ─┬─► WP05 doctrine ─────────┐
(census+ (relocate (engine+  (clock)(family)(helpers)│  WP06 glossary          │
 owner-  +91-file  gate                              │  WP07 charter           │
 map)    repoint)  fail-closed)                      │  WP08 runtime (+D-1)    ├─► WP15 ─► WP16 (opt)
                                                     │  WP09 specify_cli/sync  │  (terminal
                                                     │  WP10 status+merge      │   gate harden)
                                                     │  WP11 core              │
                                                     │  WP12 cli               │
                                                     │  WP13 auth+compat       │
                                                     │  WP14 scripts/ + tests/-shared + pyproject │
                                                     └─────────────────────────┘
```

## Package-WP `Done` template (applies to WP05–WP14 and any census-split WP)

Every per-package remediation WP's `Done` = its package-specific line **plus all of**:
1. **Exemption emptied**: `tests/architectural/_exemptions/<owner>.txt` → empty; ruff+mypy clean; gate green.
2. **Byte-identity registered**: every site this WP migrates is registered in the per-site mapping harness
   (WP03) with its WP00 census prior-signature (precision/sep/suffix); the harness is green for those sites.
   A site whose prior contract has no exact producer match is **flagged for adjudication, not auto-migrated**.
3. **Persisted goldens from pre-mission bytes**: goldens for writers this WP owns use the **WP00-captured
   pre-mission bytes**, not a re-capture of the new producer (fails if the producer diverges from them).
4. **Naive adjudicated with evidence**: every naive site in this owner (per census) is enumerated in
   `research/migration-notes.md` with a behaviour test (aware value) or a pinning test (justified-naive);
   if the census shows none, `Done` records `naive=∅` for this owner.
5. **Test-file hygiene + C-009**: new `test_*.py` declare a pytest marker and join the
   `test_pytest_marker_convention` + arch shard/module-inventory baselines in this WP
   (`pytest tests/architectural/test_pytest_marker_convention.py` green); each added test records its
   non-vacuity mutation (symbol-deletion/`raise` for fires-tests; over-fire for negatives;
   flip-a-literal-vs-captured-baseline for no-drift) and the reviewer verifies it reproduces red.

## Work packages

### WP00 — Census, ownership map & guards (hard prerequisite)
- **Deps**: none · **Lane**: critical · **Discharges**: C-006; feeds all.
- **Do**: write `research/census.yaml` — per package AND per contract: datetime importers; each contract's
  call sites **with prior serialization signature** (precision/sep/suffix) **and captured pre-mission bytes**
  for persisted writers; naive sites; `time.time()` sites; `datetime.fromtimestamp` sites (→ `from_epoch`);
  `date.today()` sites; parse/format sites; `_internal_runtime` wall-clock sites; the freshness-bounds test
  idiom sites (`before/after = datetime.now(UTC)` — migrate to `now_utc()`). **Emit a disjoint `path → owning
  WP` map covering every gate-scoped path in `src/`+`tests/`+`scripts/` — including `tests/architectural/`,
  `tests/_support/`, conftests, and `pyproject.toml`; every path owned by exactly one WP, none double-claimed.**
  Confirm each `specify_cli` lane ≤~15 owned files (split + re-run `finalize-tasks` if not). Decide FR-011(b)
  (`(b)=∅` or specify `now_naive_local()`). Emit **draft** `_exemptions/<owner>.txt` seeds (WP01b regenerates
  them from the real engine). Run the C-006 duplicate-application guard (base's #3288 commits vs `origin/main`).
- **Done**: census.yaml + ownership map reviewed (no orphan/double-claimed path); lane sizes confirmed;
  FR-011(b) decided; guard result recorded.

### WP01a — Door skeleton + relocation + mechanical repoint
- **Deps**: WP00 · **Lane**: critical · **FR/NFR**: FR-001/002/003, NFR-003/007.
- **Do**: create `src/kernel/clock.py` (skeleton, `now_utc_iso` relocated, type re-exports via `__all__`,
  canonical format constants); **repoint all ~91 `now_utc_iso` importers** (pure mechanical, no logic change);
  delete sibling ISO duplicates; **retire/repoint the seed gate** `tests/specify_cli/test_clock_consolidation.py`
  and update the `time_utils.py`/door docstring. (Large-but-trivial diff, reviewed as a mechanical repoint.)
- **Done**: `now_utc_iso` byte-identity golden green; clean-install-verification green; `test_layer_rules` +
  `test_shared_package_boundary` green; seed gate retired; ruff+mypy clean.

### WP01b — Dual gate stood up fail-closed
- **Deps**: WP01a · **Lane**: critical · **FR/NFR/SC**: FR-012 (stand-up), SC-001, NFR-004.
- **Do**: import-ban (template `test_kernel_no_doctrine_import.py`); **new whole-module call-ban entry point**
  reusing the shared alias/`_BANNED_CALLS` machinery (do NOT widen the assert-scoped
  `find_wall_clock_assertion_violations` — keep its 124 tests intact), with **per-source-root module-name
  anchoring** so the door resolves as `kernel.clock` under a `src/`+`tests/`+`scripts/` scan; prove the
  **re-export-bypass plant** fires (`from kernel.clock import datetime; datetime.now()`), else SC-001 unmet;
  document the `getattr` residual limit. Decide + record the **deployment surface** (a `tests/architectural/`
  test alongside the existing conftest assert-gate, which survives). **Regenerate `_exemptions/<owner>.txt`
  from this engine's own output** (WP00's grep seed was a draft); stand the gate up **fail-closed, green day
  one** with the full regenerated allow-list. Per-detector `scanned>N` floors.
- **Done**: gate green with full (engine-regenerated) exemptions; re-export-bypass plant reds without its fix;
  124 assert-gate tests still green; ruff+mypy clean.

### WP02 — Injectable Clock (before the families)
- **Deps**: WP01b · **Lane**: door-surface (serial on clock.py) · **FR/SC**: FR-008/009, SC-002.
- **Do**: `Clock` Protocol + `SystemClock` + `FrozenClock` + `DEFAULT_CLOCK` (in the door); producers delegate
  to `DEFAULT_CLOCK`; standardize existing `now=` seams.
- **Done**: a per-package parametrized (7-case) freeze test asserts two door consumers **per package** yield
  identical instants under one `FrozenClock`; a non-vacuity companion proves the determinism assertion goes
  **red** when the freeze is removed (freeze/symbol-deletion mutation, not `return []`).

### WP03 — Producer family + byte-identity harness
- **Deps**: WP02 · **Lane**: door-surface (serial) · **FR/NFR**: FR-004/005/006, NFR-001.
- **Do**: collapse the 4 duplicate second-stamp constants into one door constant; add `now_utc_stamp`,
  `now_utc_compact_stamp`, `now_utc_seconds`, `now_utc()` (datetime-returning), `now_epoch()` (producer-only).
- **Done**: every contract has a passing golden under `FrozenClock`; the per-site mapping harness runs and
  fires on a planted precision/sep/suffix mismatch (non-vacuous).

### WP04 — Parse/format helpers
- **Deps**: WP03 · **Lane**: door-surface (serial) · **FR/C**: FR-007, C-007.
- **Do**: `parse_iso` (fromisoformat), `parse_stamp` (strptime), `format_stamp` (strftime), `from_epoch(x)->datetime` (fromtimestamp, tz=UTC).
- **Done**: helpers present + unit-tested against round-trip fixtures (each records its C-009 mutation).

### WP05–WP14 — Per-package remediation (parallel fan-out; each ratchets its own exemption file)
Each WP routes every datetime import + wall-clock call in **the paths the WP00 ownership map assigns it**
through the door; folds its `time.time()` sites (adjudicate `now_epoch` vs monotonic per site) and its naive
sites. **`Done` = the package-specific line below + the Package-WP `Done` template (all 5 clauses).**

- **WP05 doctrine** (deps WP04).
- **WP06 glossary** (deps WP04).
- **WP07 charter** (deps WP04) — persisted goldens for compiler/context_state/pack_manager (pre-mission bytes, SC-004b).
- **WP08 runtime** (deps WP04) — **FR-014/D-1**: route `engine.py` + `retrospective_terminus.py` through the door; update the `_internal_runtime` docstring with the re-extractability rationale; `test_shared_package_boundary`/`test_no_runtime_pypi_dep` green.
- **WP09 specify_cli/sync** (deps WP04) — `body_queue` SQLite epoch golden (pre-mission bytes); **repoint the Lamport `sync/clock.py`'s `now_utc_iso` import to `kernel.clock` (import-only; do not touch Lamport logic — C-005)**.
- **WP10 specify_cli/status+merge** (deps WP04).
- **WP11 specify_cli/core** (deps WP04) — owns FR-006's `decisions/*` datetime-returning callers.
- **WP12 specify_cli/cli** (deps WP04).
- **WP13 specify_cli/auth+compat** (deps WP04) — the `time.time`+datetime files (`session_hot_path.py`, `compat/history.py`).
- **WP14 scripts/ + shared-test paths + pyproject** (deps WP04) — `scripts/` incl. `date.today()` adjudication (`seo_postprocess.py`, local→UTC date is byte-changing → migration note); the cross-cutting `tests/architectural/`+`tests/_support/`+conftest datetime sites and the freshness-bounds idiom migration to `now_utc()`; **the sole `pyproject.toml` touch** — revisit the TID251 blanket ignore (C-008). (The ratchet runs through per-owner `_exemptions/*.txt` + the AST gate only, never per-path TID251 ignores.)

Any WP split off at census inherits the full Package-WP `Done` template verbatim.

### WP15 — Terminal gate hardening
- **Deps**: WP05–WP14 · **Lane**: terminal · **FR/NFR/SC**: FR-012, SC-001/003, NFR-007 re-confirm.
- **Do**: full plant matrix (every banned spelling: `import datetime`; `from datetime import datetime`;
  positional `now(UTC)`; `tz=` keyword; module-alias `dt.now()`; double-attr `datetime.datetime.now()`;
  re-export bypass; variable-split; `utcnow()`; `date.today()`; `time.time()` — each FIRES) + paired
  allowed-form negatives (producers, `timedelta`, annotations, `parse_iso`, `from_epoch`, **`import time` +
  `time.monotonic()`/`perf_counter()` do NOT fire**); message-mapping assertion (≥3 spellings → correct
  producer); per-detector `scanned>N` floors; stale-exemption check; assert union allow-list empty.
- **Done**: plant matrix green; union empty; clean-install re-confirmed; ruff+mypy clean; each test records its C-009 mutation.

### WP16 — (Optional / deferred) portable lint (FR-013)
- **Deps**: WP15 · **Lane**: optional. Only if a sibling-repo consumer is named (record the decision).
- **Do**: standalone lint script + config template + smoke test (compliant + violating fixture → exit 0/non-zero).

## Requirement coverage matrix (no orphans)

| Req | WP(s) |
|-----|-------|
| FR-001 door exists | WP01a |
| FR-002 type re-exports | WP01a |
| FR-003 relocate now_utc_iso + repoint | WP01a |
| FR-004 stamp family + dedup constants | WP03 |
| FR-005 compact/seconds/now_utc/now_epoch | WP03 |
| FR-006 datetime-returning routed | WP03 (door) + WP11 (decisions/* callers) |
| FR-007 parse/format helpers (+from_epoch) | WP04 |
| FR-008 injectable Clock + freeze test | WP02 |
| FR-009 standardize now= seams | WP02 |
| FR-010 all consumers remediated | WP05–WP14 (per ownership map) |
| FR-011 naive adjudication | WP00 (decision) + package WPs (template clause 4) |
| FR-012 dual gate + ratchet | WP01b (stand-up) + WP15 (harden) |
| FR-013 portable lint | WP16 (deferred) |
| FR-014 _internal_runtime routing (D-1) | WP08 |
| NFR-001 byte-identity per contract + per-site | WP03 (harness) + package WPs (template clause 2) |
| NFR-002 naive-fix adjudication | package WPs (template clause 4) + migration-notes |
| NFR-003 kernel leaf / no layer violation | WP01a (+ all) |
| NFR-004 allow-list exhaustive | WP01b (fail-closed) + WP15 (union empty) |
| NFR-005 ruff/mypy/complexity | every WP |
| NFR-006 duration untouched | WP15 negative (time.monotonic) + all WPs |
| NFR-007 clean-install | WP01a + WP15 |
| C-001 no kernel-wheel activation | WP01a (honoured) |
| C-002 kernel leaf | WP01a |
| C-003 preserve distinct contracts | WP03 |
| C-004 _internal_runtime reconciled | WP08 |
| C-005 naming distinction | WP01a (docstring) + WP09 (Lamport repoint) |
| C-006 own #3288 diff + guard | WP00 |
| C-007 parse/format via door | WP04 + package WPs |
| C-008 scope src/tests/scripts | WP01b (gate scope) + WP14 (scripts/tests-shared/pyproject) |
| C-009 no scaffold-only tests | every test-adding WP (template clause 5 / WP15 / WP01b) |
| SC-001 raw read banned + message | WP01b + WP15 |
| SC-002 7-package freeze | WP02 |
| SC-003 allow-list empty | WP15 |
| SC-004 on-disk byte-identity | WP03 (harness) + package WPs (template clauses 2/3) |
| SC-005 no layer/wheel regression | WP01a + WP15 |
| SC-006 naive adjudicated | package WPs (template clause 4) + migration-notes |

## Notes
- Per-WP detail files (`tasks/WP##.md`) are materialized at implement time; each carries its census-derived
  owned-path list, exemption segment, and the C-009 mutation recorded per test. The WP00 ownership map is the
  authority for which paths each WP touches (prevents parallel-lane collisions).
- No task in this mission adds a scaffold-only test (C-009); gate/freeze/golden/mapping tests are all
  behaviour-verifying and each records its non-vacuity mutation.
