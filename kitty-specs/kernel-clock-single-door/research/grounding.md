# Grounding + Decision Record — "kernel.clock single door to time" mission

Stacks on PR #3288 (clock consolidation inside specify_cli). Base branch: `pr/2611-clock-now-utc-iso`.

## Operator decisions (2026-08-10)
1. **Enforcement strictness: FULL ban, NO whitelist → remediate.** Forbid stdlib
   `datetime` / `time.time` access everywhere except the sanctioned kernel time module.
   Do NOT accumulate a parse/format whitelist — route every consumer (parsing, formatting,
   arithmetic, type use) through the single kernel door instead.
2. **Convergence scope: unify ALL clock families** into the kernel door — aware-ISO
   (`now_utc_iso`), second-precision stamp (`%Y-%m-%dT%H:%M:%SZ`, dedup the 4 duplicate
   constants), compact stamp, `timespec=seconds`, and the datetime-returning family. Plus
   fix the ~21 naive `now()` latent local-time bugs (aware-UTC; on-disk byte changes need
   per-site proof / migration).
3. **Injectable Clock: INCLUDE now.** `Clock` protocol + `SystemClock` default +
   `FrozenClock` test double (GitPort template), standardizing the ~5 existing `now=` seams;
   `DEFAULT_CLOCK` wraps the kernel producer. Freeze-everywhere in tests.

## The design (single door to time)
`src/kernel/clock.py` (name TBD; avoid collision with `specify_cli/sync/clock.py` = Lamport
logical clock) becomes the SOLE door to time:
- Re-exports the datetime types callers still need (`datetime`, `date`, `timedelta`, `UTC`)
  so no module imports stdlib `datetime` directly.
- Owns every producer: `now_utc_iso()`, `now_utc_stamp()` (`%Y-%m-%dT%H:%M:%SZ`),
  compact stamp, `now_utc()` (datetime-returning), parse helpers (wrapping `fromisoformat`),
  format helpers.
- Hosts the `Clock` protocol + `SystemClock`/`FrozenClock` + `DEFAULT_CLOCK`.
- Repo-wide AST gate bans `import datetime` / `from datetime import` / `time.time()` outside
  the door (+ the door's own module). Template: `tests/architectural/test_kernel_no_doctrine_import.py`.

## Ground truth (from 3-lens grounding squad)
- Kernel = `src/kernel/` (zero-dep root: `kernel<-doctrine<-charter<-glossary/runtime<-specify_cli`),
  already ships in the single `spec-kitty-cli` wheel; relocation is intra-wheel (no packaging churn,
  no cycle). Template: `kernel.atomic` (relocation), `implement_cores.py:70-124 GitPort` (port/DI).
- Layer gate forces the move: `charter`/`glossary` ↛ `specify_cli` (hard-enforced in
  `tests/architectural/test_layer_rules.py`), so today's `specify_cli.core.time_utils.now_utc_iso`
  is unreachable by lower layers → duplicate copies. Kernel is the only shared floor.
- Blast radius: 132 src files import `datetime` (specify_cli 101, charter 16, runtime 7, glossary 6,
  doctrine 2; kernel 0, mission_runtime 0). `fromisoformat` in 41 files. Distinct contracts:
  aware-ISO (0 live in specify_cli, 9 live siblings), stamp `%Y-%m-%dT%H:%M:%SZ` (25, 4 dup constants),
  compact/other stamps, datetime-returning (81), naive `now()` (21, some latent bugs), `utcnow` (1),
  `time.monotonic/perf_counter` (41 — OUT of scope, duration not wall-clock), `time.time()` (9),
  parsing `fromisoformat` (64/41 files).
- Existing seed: `tests/specify_cli/test_clock_consolidation.py` full-tree ratchet (specify_cli-only,
  fluent idiom, alias-resolved, self-mutant non-vacuity). Widen scope to all 7 packages.
- Enforcement templates: `test_kernel_no_doctrine_import.py` (scoped AST import ban + exemption
  registry + self-mutation), `tests/_support/wall_clock_assertions.py` (call-ban alias machinery),
  ruff `TID251` (global banned-api, can't do scoped), `flake8-datetimez`/DTZ (NOT enabled — off-the-shelf
  naive lever), `canonical-producer-lint.yml` + `scripts/lint_*.py` + baseline (cross-repo portable lint).
- **HARD CONSTRAINT:** `runtime/next/_internal_runtime/{planner,workflow_registry,workflow_schema}.py`
  declare a no-kernel-imports invariant, yet siblings (`engine.py:115`, `retrospective_terminus.py:65`)
  use `datetime`. Options: (a) `_internal_runtime` gets its own sanctioned local producer;
  (b) narrowly relax the invariant to allow only the clock door; (c) exempt it. Spec must pick.
- Naming collision: `src/specify_cli/sync/clock.py` = Lamport logical clock (consumes `now_utc_iso`).
- Dormant kernel wheel `src/kernel/pyproject.toml` (#3101 / ADR 2026-08-02-1): adding a module is fine
  intra-single-wheel; do NOT build/publish the kernel wheel separately.

## Known non-mechanical risks the spec must handle
- Naive→aware conversions (Group D) change persisted bytes → per-site NFR-004 byte-identity proof /
  data migration decision.
- On-disk stamp formats (charter compiler/context_state/pack_manager) → same proof discipline.
- `_internal_runtime` no-kernel invariant (above).
- Single-door re-export must not create a "second resolver" smell; must be the ONLY door.
- `DEFAULT_CLOCK`/injected default must itself live in the sanctioned module so it doesn't trip the ban.
