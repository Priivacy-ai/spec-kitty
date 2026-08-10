# Mission Specification: kernel.clock — the single door to time

**Mission**: `kernel-clock-single-door` · **Type**: software-dev
**Status**: Draft (spec, post-squad revision 1) · **Owns**: the clock consolidation formerly on PR #3288 (closed)
**Grounded by**: 3-lens research squad (researcher-robbie · architect-alphonso · paula-patterns), 2026-08-10
**Reviewed by**: post-spec adversarial squad (architect-alphonso · planner-priti · reviewer-renata), 2026-08-10 — findings folded into this revision.

## Overview

Wall-clock time is currently produced in many places, in many spellings, with
enforcement covering only one of seven packages. This mission makes **one kernel
module the sole door to time for the entire codebase**: it owns every timestamp
producer and parse/format helper, provides an injectable clock for deterministic
testing, and is protected by a repo-wide, alias-aware gate that bans the raw
alternative so the wrong way can no longer be written — even through the door's
own re-exported types.

The value is correctness and legibility: a developer can no longer accidentally
read the wall clock the wrong way (naive local time, a drifted format, a bypass
of a frozen-clock test), because the only reachable way to get the time is the
one sanctioned door — and CI proves it.

The counts in this spec (≈122 datetime-importing files, ≈41 `fromisoformat`, ≈21
naive `now()`, 9 `time.time()`) are the grounding census; **plan re-baselines all
counts against branch HEAD into a census artifact** the WPs consume (they drift as
the tree changes and as this mission's own base already carries the #3288 work).

## Actors

- **Developer** writing or changing code that needs the current time or a timestamp.
- **Maintainer / reviewer** relying on CI to catch time-handling drift.
- **CI** enforcing the single-door invariant repo-wide.
- **Test author** needing to freeze time deterministically across packages.
- **Downstream consumer** of the shipped `spec-kitty-cli` wheel (must see no behaviour change).

## Domain Language (canonical terms)

- **The door** — the single sanctioned kernel module (`src/kernel/clock.py`) through
  which all wall-clock access flows. The primary module permitted to import stdlib
  `datetime` and call `time.time()`.
- **Sanctioned module** — a member of the enumerated allow-list of modules permitted
  raw stdlib clock access. Normally just the door; the allow-list has ≤ 2 entries,
  each with a one-line rationale (see D-1).
- **Producer** — a named function on the door returning a specific serialization
  (`now_utc_iso`, `now_utc_stamp`, `now_utc`, `now_epoch`, …).
- **Serialization contract** — a distinct on-disk/on-wire timestamp format. Distinct
  contracts are preserved as distinct producers; they are NOT folded together.
- **Dual gate** — the two enforcement mechanisms together: an **import-ban** (no stdlib
  `datetime` import outside sanctioned modules) and an **attribute-call-ban** (no
  `.now`/`.utcnow`/`.today` / `time.time()` call outside sanctioned modules), the
  latter **alias-aware** so it catches the call regardless of whether the receiver
  traces to stdlib or to the door's re-exported type.
- **Wall-clock time** — the current civil time (what this mission governs).
- **Logical clock** — the Lamport clock in `specify_cli/sync/clock.py`. Different concept,
  **out of scope**; must not be conflated with the door.
- **Duration clock** — `time.monotonic()` / `time.perf_counter()` for elapsed-time
  measurement. Not wall-clock; **out of scope** — and `import time` is NOT banned
  (these consumers need it); only the `time.time()` *call* is banned.

## User Scenarios & Testing

### Primary scenario — a developer needs the current timestamp
The developer imports the producer they need from the door and calls it. If they try
to write `datetime.now(UTC).isoformat()` in any spelling — stdlib import, a module
alias (`dt.now()`), a variable split (`d = datetime.now(UTC); d.isoformat()`), or even
via the door's own re-exported type (`from kernel.clock import datetime; datetime.now()`)
— CI fails, naming the file, line, and the producer to use instead.

### Scenario — a lower-layer package needs the time
A developer in `charter`/`glossary`/`runtime` (which cannot import `specify_cli`) uses
the same producer as everyone else, because the door lives in the kernel — the layer
every package may import. The duplicate local copies are removed.

### Scenario — a test needs deterministic time
A test author injects one `FrozenClock`; every producer across every package returns
the frozen instant with no per-module monkeypatching. A companion assertion proves the
determinism test goes red when the freeze is removed.

### Scenario — an epoch timestamp
A site needs a float Unix epoch (e.g. a persisted `created_at` in SQLite). It uses the
door's `now_epoch()`; no `time.time()` call survives outside the door.

### Scenario — a naive local-time bug is fixed
Each naive `datetime.now()` site is adjudicated: converted to an aware-UTC door producer,
or explicitly justified as intentionally naive with an inline rationale and a test pinning
the naive behaviour. Where persisted bytes change, a migration note is recorded.

### Edge cases
- **Parsing/formatting** (`fromisoformat`, `strftime`, `strptime`) routes through door helpers.
- **Type annotations / `timedelta` arithmetic** import the types from the door (re-exported),
  not stdlib — but importing a type from the door never yields a sanctioned `.now()` path
  (the call-ban catches it).
- **`runtime/next/_internal_runtime`** — the wall-clock users (`engine.py`,
  `retrospective_terminus.py`) do not declare the no-kernel invariant; see D-1.
- **`DEFAULT_CLOCK`** and the injected default live in the door so they do not trip the gate.
- **Duration measurement** (`time.monotonic`) and `import time` are untouched and unflagged.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | A single sanctioned kernel module (`src/kernel/clock.py`) exists and is the door to wall-clock time for all packages. | Draft |
| FR-002 | The door re-exports exactly the datetime names consumers need for annotations/arithmetic/parsing (verified by AST to be the exact closure of datetime names referenced outside the door — at least `datetime`, `date`, `timedelta`, `UTC`; add `timezone`/`tzinfo` iff referenced). The re-export surface is declared via `__all__` and kept minimal; re-exporting a type never creates a sanctioned wall-clock-read path (enforced by FR-012's call-ban). | Draft |
| FR-003 | The aware-UTC ISO producer `now_utc_iso()` is relocated from `specify_cli/core/time_utils.py` to the door; all its importers are repointed with no compatibility shim (a shim would be a second door). Acceptance is the invariant "0 stdlib-`datetime` importers remain outside sanctioned modules", not a fixed repoint count. | Draft |
| FR-004 | The door owns the second-precision stamp producer (`%Y-%m-%dT%H:%M:%SZ`); the four duplicate `TIMESTAMP_FORMAT`/`UTC_SECOND_TIMESTAMP_FORMAT` constants collapse into one canonical definition on the door. | Draft |
| FR-005 | The door owns the remaining distinct producers: compact stamp (`%Y%m%dT%H%M%SZ`), the `timespec="seconds"` variant, the datetime-returning `now_utc()`, and a **float epoch producer `now_epoch()`** replacing `time.time()` wall-clock reads. | Draft |
| FR-006 | Datetime-returning helpers (`decisions/*` and peers) route onto `now_utc()`. | Draft |
| FR-007 | The door provides sanctioned parse/format helpers wrapping `fromisoformat`, `strftime`, and `strptime` so consumers parse/format without importing stdlib `datetime`. | Draft |
| FR-008 | The door defines an injectable `Clock` protocol with a `SystemClock` default (`DEFAULT_CLOCK`) and a `FrozenClock` test double. A cross-package test asserts two independent code paths yield identical instants under one injected `FrozenClock`, and a companion assertion proves that test goes red when the freeze is removed. | Draft |
| FR-009 | The existing ad-hoc `now=` injection seams are standardized onto the `Clock` protocol. | Draft |
| FR-010 | Every consumer across all seven packages (and `scripts/`, C-008) is remediated to obtain time via the door; no stdlib `datetime` import or banned wall-clock call remains outside the enumerated sanctioned modules. | Draft |
| FR-011 | Each naive `datetime.now()`/`datetime.utcnow()` site is **adjudicated**: either (a) converted to an aware-UTC door producer, or (b) if a legitimately-naive consumer exists, routed through a **sanctioned door producer `now_naive_local()`** with an inline rationale and a pinning test (so it does not bypass the gate). The `(b)` set is decided at census (WP00): if no legitimately-naive consumer exists, `(b)=∅` and `now_naive_local()` is not added. No site is left un-adjudicated; the `(b)` set is enumerated in the migration note. | Draft |
| FR-012 | A repo-wide **dual gate** enforces the door: (a) an **import-ban** (AST) failing on any stdlib `datetime` import outside sanctioned modules; (b) an **alias-aware attribute-call-ban** (AST) failing on any `.now`/`.utcnow`/`.today` call or `time.time()` call outside sanctioned modules — resolving door-alias and module-alias receivers and covering the variable-split form, not only the fluent idiom. It does NOT ban `import time`. It carries self-mutation non-vacuity tests (including a planted `from kernel.clock import datetime; datetime.now()` bypass) and a stale-exemption check. Enforcement is a **per-package ratchet**: a per-path allow-list that each remediation WP shrinks to empty for its package; "allow-list empty" is the terminal acceptance. | Draft |
| FR-013 | (Droppable / last WP; defer candidate) A standalone, repo-portable lint script + config template exists with a smoke test that runs it against a fixture dir holding one compliant and one violating file, asserting exit 0 and non-zero respectively. Deferred to a follow-on unless a sibling-repo consumer is named. | Draft |
| FR-014 | The wall-clock sites in `runtime/next/_internal_runtime` (`engine.py`, `retrospective_terminus.py`) are routed through the door; the plan first verifies the no-kernel invariant's true scope (see D-1) and updates the `_internal_runtime` docstring so code and doctrine agree. | Draft |

## Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | Serialization-preserving migration, measured **per serialization contract** (the producers in C-003), each with a golden-fixture byte comparison under a fixed clock. | 100% of contracts have a golden byte-identity fixture; all pass. | Draft |
| NFR-002 | Naive-fix adjudication (FR-011). | 100% of naive sites adjudicated (converted or justified-naive-with-test); each byte-changing conversion carries a migration note. | Draft |
| NFR-003 | Kernel stays a zero-first-party-dependency leaf; no new layer violations. | `tests/architectural/test_layer_rules.py` + `test_shared_package_boundary.py` green; door imports stdlib only. | Draft |
| NFR-004 | Wall-clock stdlib access is confined to an enumerated allow-list of sanctioned modules (the door + any D-1 module). | Gate asserts the allow-list is exhaustive: forbidden `datetime` imports = 0 and forbidden wall-clock calls = 0 outside it; allow-list ≤ 2 entries, each with a rationale. | Draft |
| NFR-005 | Code quality holds. | `ruff` + `mypy` zero issues; per-function complexity ≤ 15; no new `# noqa`/`# type: ignore`. | Draft |
| NFR-006 | Duration measurement untouched. | `time.monotonic`/`perf_counter` sites unchanged and unflagged; `import time` not banned. | Draft |
| NFR-007 | No downstream/consumer behaviour change from the relocation. | Relocation stays intra-single-wheel; clean-install verification green. | Draft |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Do NOT activate or publish the dormant `spec-kitty-kernel` wheel (#3101 / ADR 2026-08-02-1). Relocation stays inside the single `spec-kitty-cli` wheel. | Draft |
| C-002 | The kernel must remain free of imports from any other spec-kitty package (layer floor). | Draft |
| C-003 | Distinct serialization contracts (ISO / second-stamp / compact / `timespec=seconds` / datetime-returning / **float epoch**) MUST be preserved as named producers. Folding that changes on-disk bytes is forbidden, except the deliberate naive→aware fixes (FR-011), each with a migration decision. | Draft |
| C-004 | The `runtime/next/_internal_runtime` no-kernel-imports invariant must be verified and reconciled explicitly (D-1), not silently violated; code and docstring must agree afterward. | Draft |
| C-005 | Naming: the door governs wall-clock time. The Lamport logical clock (`specify_cli/sync/clock.py`) and duration clocks (`time.monotonic`) are distinct and out of scope; spec/impl must not conflate them. | Draft |
| C-006 | This mission **owns and includes** the specify_cli-scoped clock consolidation formerly on the now-closed PR #3288 (those commits ride this branch's base). It does not "rebase onto #3288"; instead the plan (a) bases the mission on current `origin/main`, and (b) runs a duplicate-application guard confirming none of the #3288 diff already reached `origin/main` by another route before re-applying it. | Draft |
| C-007 | Parsing/formatting (`fromisoformat`, `strftime`, `strptime`) must route through sanctioned door helpers, not raw stdlib imports (full-ban decision, no whitelist). | Draft |
| C-008 | Gate scope is pinned to `src/`, `tests/`, and `scripts/`. Tests import datetime types/producers from the door too (single-door thesis). `scripts/`'s blanket TID251 ignore is revisited; its datetime usage is in-scope unless explicitly exempted with rationale. | Draft |
| C-009 | Every test this mission adds MUST verify real, shipped behaviour. A test is **scaffold-only** if ANY of: (1) it passes unchanged against the pre-mission tree; (2) it still passes when the production symbol under test is deleted or its body replaced with `raise`/a wrong constant (fails the mutation/non-vacuity check); (3) it asserts only on existence, importability, naming, or file structure rather than an observable return value, on-disk byte, or gate verdict. Every added test must fail under at least one such mutation of the behaviour it claims to cover; the reviewer records the mutation used. Scaffold-only tests are removed before mission close; new real test files join the completeness baselines in the same WP. | Draft |

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | A developer cannot introduce a raw wall-clock read outside the door in ANY spelling — stdlib import, module alias, variable split, or the door's re-exported type — CI fails naming file, line, and the producer to use. |
| SC-002 | One `FrozenClock` fixture freezes time across all seven packages in tests with no per-module monkeypatching; removing it makes a determinism assertion fail. |
| SC-003 | Wall-clock stdlib access is confined to the enumerated sanctioned allow-list (≤ 2 modules); the gate proves the allow-list exhaustive (0 forbidden imports, 0 forbidden calls elsewhere). |
| SC-004 | Every pre-existing on-disk timestamp format is byte-identical after the mission — proven by (a) an AST/grep assertion that no format string or `timespec` literal changed for any migrated contract, and (b) golden fixtures for the persisted artifacts named in grounding (charter compiler / context_state / pack_manager) — except the naive→aware fixes enumerated under SC-006. |
| SC-005 | No architectural/layer regression; the kernel remains a clean zero-dependency leaf and the shipped wheel behaviour is unchanged. |
| SC-006 | 100% of the naive `now()`/`utcnow` sites are adjudicated (converted or justified-naive-with-rationale-and-test), each with evidence; byte-changing conversions carry a migration note. |

## Key Entities

- **The door** (`src/kernel/clock.py`) — owns all producers, the minimal type re-exports (`__all__`),
  parse/format helpers, and the `Clock` protocol + defaults.
- **Producer family** — `now_utc_iso`, `now_utc_stamp`, `now_utc_compact_stamp`, `now_utc_seconds`,
  `now_utc` (datetime-returning), `now_epoch` (float), plus parse/format helpers.
- **`Clock` / `SystemClock` / `FrozenClock` / `DEFAULT_CLOCK`** — the injection seam.
- **The dual gate** — import-ban + alias-aware call-ban, per-package ratchet, self-mutation + stale-exemption.

## Assumptions

- Python ≥ 3.11 (`datetime.UTC is timezone.utc`), so ISO substitutions are byte-identical.
- `src/kernel/` already ships inside the single `spec-kitty-cli` wheel; relocation needs no packaging change.
- The mission owns the #3288 clock diff (PR #3288 closed, unmerged); the plan bases on current `origin/main` and guards against duplicate application.
- Templates: `kernel.atomic` (relocation); `implement_cores.py` `GitPort` (injection); `test_kernel_no_doctrine_import.py` (import-ban); `tests/_support/wall_clock_assertions.py` (alias-aware call-ban machinery).

## Out of Scope

- The Lamport logical clock (`specify_cli/sync/clock.py`).
- Duration clocks (`time.monotonic`/`perf_counter`); `import time` is not banned.
- Building or publishing the standalone `spec-kitty-kernel` wheel (#3101).
- Any re-design beyond a single door + injectable clock.
- FR-013 cross-repo portable lint if no sibling consumer is named (defer to follow-on).

## Open Decisions (recommended defaults; confirm in plan)

- **D-1 — `_internal_runtime` wall-clock sites.** The no-kernel-imports invariant is
  **documentary (unenforced) and module-scoped** to `planner.py`/`workflow_registry.py`/
  `workflow_schema.py` — none of which read the wall clock. The wall-clock users
  (`engine.py`, `retrospective_terminus.py`) do not declare it. **Recommended default (revised
  from the pre-squad "second sanctioned module"): route `engine.py`/`retrospective_terminus.py`
  through the door directly** (keeps the allow-list at one, honours the single-door thesis),
  update the `_internal_runtime` docstring, and confirm no `shared-package-boundary` test
  regresses. Fall back to a local sanctioned producer only if a real *enforced* isolation
  requirement surfaces.
- **D-2 — Door module name.** Keep `kernel.clock` (operator's choice); document the distinction
  from the Lamport `sync/clock.py` (C-005). Minimize the re-export surface to reduce the
  `.now()` footgun (the call-ban still covers it).

## Dependencies

- The specify_cli clock consolidation formerly on PR #3288 (now owned by this mission).
- ADR `docs/adr/3.x/2026-08-02-1-charter-wheel-assessment.md` (kernel/#3101 groundwork — do not activate).

## Note on scope & phasing (for plan/tasks) — ONE mission (squad-confirmed; a split ships an inert door + a warn-only gate)

1. **Door surface (critical path):** create `kernel/clock.py`, relocate `now_utc_iso` (FR-003),
   type re-exports (FR-002), the producer family incl. `now_epoch` (FR-004/005/006), parse/format
   helpers (FR-007), and the injectable `Clock` (FR-008/009). Land the `Clock` seam early (or
   explicitly sanction the `_FixedDatetime`+monkeypatch idiom) so family byte-identity proofs
   (NFR-001) have a fixed clock available — avoid the phasing inversion.
2. **Per-package remediation lane (parallel fan-out):** one WP per package — `doctrine`, `glossary`,
   `charter`, `runtime` (includes FR-014 / D-1), remaining `specify_cli`, `scripts/`. Each WP folds
   **route + naive-fix for the files it touches** (single touch per file), but the naive fixes are
   individually adjudicated (FR-011) and **enumerated in the WP's review notes** so byte-changing
   diffs are never hidden inside the mechanical sweep. Each WP **ratchets its package's allow-list
   segment to zero**; partition the ratchet baseline by package so parallel WPs don't collide.
3. **Terminal gate hardening:** self-mutation + stale-exemption (FR-012), allow-list empty, optional
   FR-013. The gate is fail-closed *per package as it lands*, so the terminal WP only removes residue.

Delivery: **stacked origin PRs** (door surface → per-package remediation → gate), each CI-gated and
independently reviewable, the ratchet guaranteeing every intermediate PR leaves the tree green and
monotonically more-enforced. Never a single 120-file PR.
