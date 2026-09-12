# Implementation Plan: kernel.clock — the single door to time

**Mission**: `kernel-clock-single-door` · **Spec**: [spec.md](./spec.md) (rev 1) · **Plan**: rev 2 (post-plan squad)
**Approach**: one mission. Door surface + **gate stood up fail-closed on day one** → parallel per-package remediation that ratchets its own exemption file to empty → terminal hardening. Stacked PRs.

## 1. Architecture

### 1.1 The door module (`src/kernel/clock.py`)

Stdlib-only kernel module (the zero-first-party-dependency floor), modelled on `kernel/atomic.py`.
Primary sanctioned holder of raw `datetime`/`time.time()`.

**Producer family** (one per distinct serialization contract; C-003):

| Producer | Returns | Replaces |
|----------|---------|----------|
| `now_utc_iso() -> str` | aware-UTC ISO (`…+00:00`, native precision) | `datetime.now(UTC).isoformat()` |
| `now_utc_stamp() -> str` | `%Y-%m-%dT%H:%M:%SZ` | the 4 duplicate `TIMESTAMP_FORMAT` constants |
| `now_utc_compact_stamp() -> str` | `%Y%m%dT%H%M%SZ` | compact stamp sites |
| `now_utc_seconds() -> str` | `isoformat(timespec="seconds")` | the timespec sites |
| `now_utc() -> datetime` | aware `datetime` | datetime-returning helpers |
| `now_epoch() -> float` | Unix epoch seconds | wall-clock `time.time()` |
| `now_naive_local() -> datetime` | naive local (**only if** census shows a legitimate consumer — MINOR-1) | conditional |

**Parse/format helpers** (C-007): `parse_iso`, `parse_stamp` (wraps `strptime`), `format_stamp` (wraps
`strftime`), and `from_epoch(x) -> datetime` (wraps `datetime.fromtimestamp(x, tz=UTC)` — the inverse of
`now_epoch`; 11+ sites otherwise keep a raw `datetime` import solely to call `.fromtimestamp`, eroding
C-007). `date.today()` (1 site, `scripts/`) has no date-only producer; adjudicate it at census as a naive
fix (`now_utc().date()` flips local→UTC date — a byte-changing FR-011 case needing a migration note).
**Type re-exports** (FR-002): `__all__` = exact AST closure of datetime names used outside the door
(baseline `datetime,date,timedelta,UTC`; add others only if the census shows a referencing site).
Re-exporting a type never yields a sanctioned `.now()` path — the call-ban (§1.3) catches it.
**Format constants**: one canonical definition each (home of the 4 collapsed duplicates).

### 1.2 The injectable clock (FR-008/009) — landed in WP02, before the families

`Clock` Protocol + `SystemClock` (the one real boundary; producers delegate to it) + `FrozenClock`
(test double) + `DEFAULT_CLOCK` (in the door, so it never trips the gate), modelled 1:1 on `GitPort`
(`implement_cores.py:70-124`). Call sites with a `now=` seam accept `*, clock: Clock = DEFAULT_CLOCK`.
Landing the seam in WP02 (immediately after the skeleton, **before** the producer families) means every
byte-identity golden uses `FrozenClock` uniformly — the `_FixedDatetime`+monkeypatch workaround is
avoided (resolves the phasing inversion; Priti MINOR-2 / Renata).

### 1.3 The dual gate (FR-012) — stood up fail-closed in WP01, hardened terminally

Two AST detectors over `src/`, `tests/`, `scripts/` (C-008), each excluding the sanctioned allow-list:
- **Import-ban** (template `test_kernel_no_doctrine_import.py`): fail on stdlib `datetime` import outside sanctioned modules.
- **Call-ban** (reuses `wall_clock_assertions.py` alias machinery + `_BANNED_CALLS`): landed and proven non-vacuous in WP01b (not deferred). **Add a NEW whole-module entry point** that reuses the shared alias/`_BANNED_CALLS` machinery — do NOT widen the existing assert-scoped `find_wall_clock_assertion_violations` (that would turn the legitimate freshness-bounds idiom `before/after = datetime.now(UTC)` into violations and red-flag its 124-test support suite). The existing assert-gate and its tests stay intact. The new entry point (i) records banned calls across the whole module, and (ii) **anchors module-name resolution per source root** — the engine currently derives module keys from the scan's `os.path.commonpath`, so widening the scan to `src/`+`tests/`+`scripts/` collapses the root and resolves the door as `src.kernel.clock`, never `kernel.clock` — the re-export bypass would slip through (verified). Fix: resolve `src/**` names anchored at `src/` (→ `kernel.clock`) while keeping `tests/**` anchored at the repo root. Then fail on `.now`/`.utcnow`/`.today`/`time.time()` calls whose receiver resolves — via the per-file alias map covering stdlib import, `import datetime as _dt`, **and the door re-export** — to datetime/time. Flags the `.now(<aware-UTC>)` call itself so the **variable-split** form is caught (no type inference needed). **Honest limits (documented in the gate docstring)**: cross-statement receiver binding is resolved only within a function's local alias/assignment map; a `getattr(kernel.clock,'datetime').now()` receiver yields no attribute chain and is an accepted, disclosed residual (contrived, and it carries no datetime import for the import-ban either).
- **Both detectors carry their own `scanned > N` floor** (NOTE-3): a detector silently scanning zero files must go red, not green.
- **Allow-list = per-package files** (`tests/architectural/_exemptions/<package>.txt`), unioned by the gate (MAJOR-2). Each remediation WP edits only its own file → lanes are physically disjoint. A stale-exemption check fails once an allowlisted path is clean. Terminal acceptance: the union is empty (SC-003).
- **Non-vacuity plant matrix** (Renata MAJOR-3; all planted in-memory / `tmp_path`, NEVER as committed `.py` under the scanned tree — NOTE-2): every banned spelling — `import datetime`; `from datetime import datetime`; positional `datetime.now(UTC)`; `tz=` keyword `datetime.now(tz=UTC)`; module-alias `dt.now()`; double-attr `datetime.datetime.now()`; re-export bypass `from kernel.clock import datetime; datetime.now()`; variable-split; `utcnow()`; `date.today()`; `time.time()` — each asserted to FIRE. Paired allowed-form negatives asserted NOT to fire: producers, `timedelta`, type annotations, `parse_iso`, and — critically — `import time; time.monotonic()/perf_counter()` (the over-fire boundary NFR-006 depends on).
- `import time` is NOT banned; only `time.time()` calls.
- **Message mapping** (SC-001; Renata MAJOR-4): the gate's rendered failure names file, line, AND the producer to use (`…isoformat()`→`now_utc_iso`, `%Y-%m-%dT%H:%M:%SZ`→`now_utc_stamp`, `time.time()`→`now_epoch`, …); a test asserts the suggestion is present and correct for ≥3 representative spellings.

## 2. Decisions resolved

- **D-1 → route through the door.** Verified sound: `test_layer_rules.py` places `runtime` above `kernel`
  (a legal downward edge); `test_shared_package_boundary.py` bans only `spec_kitty_runtime`/vendored-events
  (kernel is a permitted production layer); `test_no_runtime_pypi_dep.py` is unaffected (the door is
  stdlib-only, no new dep/cycle). The `_internal_runtime` no-kernel docstring's real purpose is runtime
  **re-extractability**, not general purity — and it is already porous (`retrospective_terminus.py` and
  `planner.py` import `specify_cli.*`), while `spec_kitty_runtime`'s retirement (shared-package-boundary ADR)
  moots re-extraction. So route `engine.py`/`retrospective_terminus.py` through the door, keep the allow-list
  at **one**, and update the `_internal_runtime` docstring to state that rationale (code/doctrine agree).
  Fallback to a second sanctioned module only if an enforced isolation test surfaces.
- **D-2 → `kernel.clock`.** Keep the name; minimal `__all__`; C-005 documents the Lamport distinction.

## 3. Census (WP00 — hard prerequisite)

Re-baseline against branch HEAD into `research/census.yaml`: per package AND per contract, the datetime
importers, each contract's call sites **with their prior serialization signature** (precision/sep/suffix —
needed for the SC-004 per-site mapping proof), naive sites, `time.time()` sites, parse/format sites, and
`_internal_runtime` wall-clock sites. Decide FR-011(b): if no legitimately-naive consumer exists, record
`(b)=∅` and drop `now_naive_local()`; else specify it. Generate the per-package exemption files from the
census. Run the **duplicate-application guard** (C-006): confirm none of the base's #3288 commits already
reached `origin/main` by another route.

## 4. Behaviour preservation (NFR-001 / SC-004)

- **Per-contract golden fixtures** under `FrozenClock`: producer bytes identical to the pre-mission form.
- **Per-site mapping assertion (closes the SC-004 hole — Renata MAJOR-1):** the census records each
  migrated site's prior contract signature; a test asserts the chosen target producer's golden bytes equal
  that site's pre-mission bytes for a shared fixed instant. This catches the silent case where a site's
  `timespec=`/`sep=` is *deleted* on swap-to-producer (invisible to a "no literal changed value" check).
  Where a site's prior contract has no exact producer match, it is flagged for adjudication, not auto-migrated.
- **No-format-drift AST check**: no surviving format/`timespec` literal changed value (complements, not
  replaces, the mapping assertion).
- **Persisted-artifact goldens** homed on the owning package WP (charter compiler/context_state/pack_manager
  → charter WP; `sync/body_queue` SQLite epoch → sync WP; …) — MAJOR-5.
- **Naive fixes (FR-011)** are the only sanctioned byte changes; each adjudicated, tested, enumerated in
  `research/migration-notes.md`. `time.time()` sites that are elapsed-duration in disguise are adjudicated
  `now_epoch` vs `monotonic` (out of scope) per site, within the owning package WP.

## 5. Work-package decomposition (post-squad)

True critical path is five sequential merges on `clock.py` (WP00→WP01→WP02→WP03→WP04) before fan-out
(Priti MINOR-1: WP02/03/04 serialize on the door file — declared, not parallel). Then a parallel
per-package lane where each WP ratchets **its own** exemption file. Each package WP folds route + its own
`time.time` sites + its naive-fixes + its persisted goldens (single touch per file).

| WP | Scope | Deps | Lane | Done-ness |
|----|-------|------|------|-----------|
| **WP00** | Census (per-package + per-contract + prior signatures) + C-006 guard + FR-011(b) decision; generate per-package exemption files. | — | critical | `census.yaml` written; guard recorded; exemption files seeded. |
| **WP01** | Door skeleton; relocate `now_utc_iso` (FR-003); type re-exports (FR-002); format constants; **stand up the dual gate fail-closed, seeded with the full census allow-list (green day one)** (MAJOR-1); **retire/repoint the seed gate `test_clock_consolidation.py` + update `time_utils.py` docstring** (NOTE-1); NFR-007 clean-install acceptance (MAJOR-5). | WP00 | critical | Gate green with full exemptions; clean-install green; layer tests green; seed gate retired. |
| **WP02** | Injectable `Clock`/`SystemClock`/`FrozenClock`/`DEFAULT_CLOCK` + standardize `now=` seams (FR-008/009); **per-package** cross-package freeze test (7 cases, SC-002; Renata MAJOR-2) + non-vacuity companion. | WP01 | door-surface (serial on clock.py) | 7-package freeze green; freeze-removal → red. |
| **WP03** | Producer family: collapse 4 dup constants (FR-004); compact + `seconds` + `now_utc()` + `now_epoch()` (FR-005/006, **producer-only** — MAJOR-3); per-contract goldens + per-site mapping harness (NFR-001/§4). | WP02 | door-surface (serial) | Every contract golden passes; mapping harness runs. |
| **WP04** | Parse/format helpers (FR-007, C-007). | WP03 | door-surface (serial) | Helpers present + tested. |
| **WP05** `doctrine` | Route + naive + `time.time` + goldens for its writers. | WP04 | parallel | `_exemptions/doctrine.txt` → empty; naive enumerated+tested. |
| **WP06** `glossary` | " | WP04 | parallel | `_exemptions/glossary.txt` → empty. |
| **WP07** `charter` | " incl. compiler/context_state/pack_manager persisted goldens (MAJOR-5). | WP04 | parallel | `_exemptions/charter.txt` → empty; persisted goldens pass. |
| **WP08** `runtime` | " incl. FR-014/D-1 (route engine.py/retrospective_terminus.py; docstring update; boundary tests green). | WP04 | parallel | `_exemptions/runtime.txt` → empty; boundary tests green. |
| **WP09–WP0n** `specify_cli` **split by subpackage** (MAJOR-4) | one WP each for `sync` (incl. body_queue epoch golden), `status`/`merge`, `core`, `cli`, `auth`/`compat` (both `time.time`+datetime), … — any lane >~15 files splits further. | WP04 | parallel | each subpackage `_exemptions/*.txt` → empty. |
| **WP(scripts)** | `scripts/` remediation + revisit TID251 blanket ignore (C-008). | WP04 | parallel | `_exemptions/scripts.txt` → empty. |
| **WP(terminal)** | Gate hardening: full plant matrix + message-mapping + per-detector floors + stale-exemption (FR-012); assert union allow-list empty (SC-003); re-confirm NFR-007. | all remediation | terminal | Plant matrix green; union empty. |
| **WP(optional)** | FR-013 portable lint + smoke test — only if a sibling consumer is named (record the decision — NOTE-3). | terminal | optional | Smoke test 0/non-zero, or documented deferral. |

New test files in any WP join the completeness baselines **in that WP**: the marker-convention gate
(`test_pytest_marker_convention` — a new `test_*.py` needs a marker), and the arch shard/module-inventory
maps. Otherwise the WP ships baseline-red.

## 6. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| Ratchet inert until the end | Gate stood up fail-closed in WP01 (MAJOR-1). |
| Parallel lanes collide on the allow-list / shared files | Per-package exemption files (MAJOR-2); `time.time` folded into owning package (MAJOR-3). |
| Silent byte change on producer swap | Per-site mapping assertion (§4, MAJOR-1). |
| Re-export bypass | Alias-aware call-ban + planted self-mutation; minimal `__all__`. |
| Mega-PR | Stacked PRs; specify_cli split by subpackage (MAJOR-4). |
| Orphaned NFR-007 / persisted goldens | Homed on WP01/terminal and owning package WPs (MAJOR-5). |
| Seed gate breaks on relocation | Retired/repointed in WP01 (NOTE-1). |
| C-009 self-application vacuity | Negatives/no-drift record the **over-fire / flip-a-literal** mutation, not `return []` (MINOR-2). |
| FR-011(b) untestable (no naive producer) | Census decides `(b)=∅` (drop branch) or add sanctioned `now_naive_local()` (MINOR-1). |

## 7. Test strategy (real behaviour only — C-009) — named vehicles

| SC / requirement | Vehicle |
|---|---|
| SC-001 (raw read banned, all spellings + message) | Dual-gate plant matrix (§1.3) + message-mapping assertion (≥3 spellings). |
| SC-002 (freeze across 7 packages) | WP02 per-package parametrized freeze test (7 cases) + freeze-removal-goes-red companion. |
| SC-003 (allow-list exhaustive/empty) | Union-empty assertion + per-detector `scanned>N` floor + stale-exemption check. |
| SC-004 (on-disk byte-identity) | Per-contract goldens + **per-site mapping assertion** + no-format-drift AST check + persisted-artifact goldens. |
| SC-005 (no layer/wheel regression) | `test_layer_rules`/`test_shared_package_boundary` green; clean-install-verification on WP01+terminal. |
| SC-006 (naive adjudication) | Per-site behaviour test (aware value) or pinned-naive test; `migration-notes.md` enumerates all. |
| C-009 (no scaffold-only tests) | Each added test records its mutation: fires-tests use symbol-deletion/`raise`; **negatives use over-fire**; no-drift uses flip-a-literal-vs-captured-baseline. Reviewer records the mutation per test. |

Planted violations live in-memory/`tmp_path` only (NOTE-2). Both detectors have independent non-vacuity floors.

## 8. Delivery & branch

Base on current `origin/main` (owns the #3288 diff; duplicate-application guard first). Stacked origin PRs
in WP order; operator merges each; rebase forward as earlier ones land. Never a single 120-file PR. The
ratchet keeps every intermediate PR green and monotonically more-enforced from WP01 onward.
