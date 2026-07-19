# Mission Specification: Charter-layer dead-code burndown + no-op-stability campsite

**Mission Branch**: `feat/charter-deadcode-noop-campsite`
**Created**: 2026-07-19
**Status**: Draft
**Input**: Low-risk sanitization slice continuing merged #2773 (charter.yaml authority
inversion). Under epics **#1797** (dead-code & LOC reduction) and **#1914** (governed/gate
operations must be no-op-stable). Delete two confirmed-dead charter modules and make the
governed charter read/preflight/synthesize surface no-op-stable. Scope decision (item 3
bundling) resolved by operator: **Bundle deep fix** — decision `01KXW0PN2KDS5M5GR9CMDPWV5F`.

## Context & Grounding *(evidence gathered by the pre-spec research squad)*

#2773 inverted the charter to an authoritative `charter.yaml`, leaving two dead surfaces
explicitly deferred-as-follow-up, and retired the render-path doctrine writer:

- **`src/charter/generator.py`** (`CharterDraft`, `build_charter_draft`, `write_charter`) —
  a WP03 wrapper over `compile_charter`, superseded by the `charter interview` + `charter
  generate` flow. **Zero live `src/` callers** (grep-confirmed). Only the
  `src/charter/__init__.py` reexport (lines 31, 108-110) and `tests/charter/test_generator.py`
  reference it. **Landmine CLEAR:** `charter generate` emits `charter.yaml` via
  `compile_charter`/`write_compiled_charter`; `charter.md` is a hand-authored companion; no
  live path bootstraps an initial `charter.md` from `generator.py`.

- **`src/charter/extractor.py`** (`Extractor` class + module) — the prose→triad scraper husk
  left after #2773 WP04 deleted `SECTION_MAPPING`/`write_extraction_result`/`extract_with_ai`.
  **Zero non-test `src/` callers.** Currently ALLOWLISTED as a deferred follow-up in three
  arch-gate locations that MUST be removed in the same change (else the gates go
  stale-red / dangling-red):
  1. `tests/architectural/_baselines.yaml:58` — `category_5_wp_in_flight_adapters: 1` (→ 0).
  2. `tests/architectural/test_no_dead_modules.py:339-344` — the `"charter.extractor"` entry
     in `_CATEGORY_5_WP_IN_FLIGHT_ADAPTERS`.
  3. `tests/architectural/test_no_dead_symbols.py:907-913` — the `Extractor` `SymbolKey`
     frozenset `_CATEGORY_C_WP_IN_FLIGHT_EXTRACTOR_RETIREMENT` **and** its `|` term in the
     `_SYMBOL_ALLOWLIST` union.

- **#2373 no-op-stability** — the *render-path* bug named in the issue ("`build_charter_context`
  regenerates tracked `.kittify/doctrine` as a side-effect") is **already fixed at HEAD by
  #2773**: `sync()` is inert and `build_charter_context` now writes only the gitignored
  `.kittify/charter/context-state.json`. The **residual** no-op churn lives in a *different*
  surface — the **preflight auto-refresh** (`src/specify_cli/charter_runtime/preflight/runner.py`
  `_attempt_auto_refresh`) which shells out to `spec-kitty charter synthesize` when the
  `synthesized_drg` freshness signal (`src/specify_cli/charter_runtime/freshness/computer.py`)
  reports stale. A freshness-misfire (judged stale on a genuine no-op) churns the tracked
  doctrine artifacts (`graph.yaml`, `directive/*`, `tactic/*`, `styleguide/*`).

- **⚠ MASKING LANDMINE:** this working checkout carries a *local, uncommitted*
  `.git/info/exclude` entry (`.kittify/doctrine/`) that HIDES the churn. The **committed**
  `.gitignore` tracks those artifacts (via negations). Red-first reproduction MUST run where
  doctrine is tracked (fresh clone, or the local exclude removed) — a green `git status` in
  this checkout is not evidence of a fix.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dead charter modules removed, arch baselines shrink downward (Priority: P1)

A maintainer deletes `charter.generator` and `charter.extractor` — both proven dead — and
retires their deferred arch-gate allowlist entries. The dead-code baselines move **downward**,
never green-washed upward, and the removal leaves no functional gap.

**Why this priority**: Pure debt burndown under #1797; the confirmed-dead surfaces were
explicitly deferred by #2773 and are ready to retire. Lowest risk, highest campsite value.

**Independent Test**: Delete both modules + their `__init__`/allowlist references; run
`pytest tests/architectural/{test_no_dead_modules,test_no_dead_symbols,test_ratchet_baselines}.py`
and `tests/charter/` — all green, `category_5` baseline = 0, and the live
`write_compiled_charter` symlink-guard tests still pass.

**Acceptance Scenarios**:

1. **Given** `src/charter/generator.py` exists with zero live callers, **When** the module and
   its `__init__.py` import + `__all__` entries are deleted, **Then** `git grep` finds zero
   live `src/` references and the package still imports cleanly.
2. **Given** `tests/charter/test_generator.py` mixes dead-API tests with live
   `write_compiled_charter` symlink-guard tests, **When** the generator import + the 4
   generator-API tests are removed, **Then** the 4 `write_compiled_charter` symlink-guard
   tests remain and pass.
3. **Given** `charter.extractor` is allowlisted in three arch-gate locations, **When** the
   module is deleted, **Then** the three allowlist entries are removed in the same change and
   `test_no_dead_modules`/`test_no_dead_symbols` do not report stale/dangling entries.
4. **Given** the `category_5_wp_in_flight_adapters` baseline is `1`, **When** the extractor is
   removed, **Then** the baseline is `0` (a downward edit) and `test_ratchet_baselines` is green.

---

### User Story 2 - Governed charter operations are no-op-stable (Priority: P1)

A developer (or a gate) runs a governed charter operation — `charter context`, `doctor
doctrine`, or any preflight-gated command — on a clean tree, twice, and the git working tree
stays clean. No governed read self-writes tracked doctrine artifacts.

**Why this priority**: The #1914 invariant. A read that dirties the tree corrupts every
downstream diff, gate, and auto-commit; #2373 is the enumerated charter-layer instance.

**Independent Test**: In a doctrine-**tracked** checkout (fresh clone or local exclude
removed), run each governed operation twice from a clean tree and assert `git status --porcelain`
is empty after each run. The red-first version of this test fails before the freshness fix.

**Acceptance Scenarios**:

1. **Given** a clean, doctrine-tracked tree, **When** `spec-kitty charter context` renders,
   **Then** no git-tracked artifact is modified (only untracked runtime state may change).
2. **Given** a clean tree whose `synthesized_drg` is genuinely fresh, **When** a preflight-gated
   command runs, **Then** `charter synthesize` is NOT triggered and no doctrine artifact churns.
3. **Given** the freshness signal previously misfired on a no-op, **When** the same operation
   runs twice, **Then** the second run detects no change and leaves the tree clean.
4. **Given** `charter.yaml` is *genuinely* edited, **When** a preflight-gated command runs,
   **Then** synthesize DOES run and refreshes the doctrine artifacts — the fix suppresses
   *no-op churn only*, never genuine staleness.

---

### User Story 3 - No-op-stability is regression-guarded and #2373 is closed honestly (Priority: P2)

The fixes are locked in by red-first tests so they cannot silently regress, and #2373 receives
a terminal issue-matrix verdict backed by evidence (render path verified-already-fixed-by-#2773;
residual churn fixed).

**Why this priority**: Prevents the "static-fixed" trap — a bug is not fixed because the code
looks fixed; it is fixed when a live reproduction goes from red to green and a guard holds it.

**Independent Test**: The committed guard tests fail if `build_charter_context` writes a tracked
artifact, or if `synthesize` churns an unchanged tree; `issue-matrix.md` shows #2373 with a
terminal verdict.

**Acceptance Scenarios**:

1. **Given** the render-cleanliness guard, **When** a future change reintroduces a tracked-doctrine
   write into the render path, **Then** the guard test fails.
2. **Given** the synthesize no-op ratchet, **When** `synthesize` is run twice on an unchanged tree,
   **Then** the second run produces zero tracked-file diffs.
3. **Given** `spec.md` references #2373 (+ epic refs #1797/#1914), **When** the mission reaches
   review, **Then** `issue-matrix.md` carries a terminal verdict for each referenced issue.

---

### Edge Cases

- **Stale/dangling allowlist after deletion**: deleting the extractor module/class WITHOUT
  removing the three allowlist entries turns `test_no_dead_modules` (stale-entry assert) and
  `test_no_dead_symbols` (dangling-key assert) RED. Both edits ship in the same change.
- **Masked reproduction**: a green `git status` in this checkout is a false negative for #2373
  (local `.git/info/exclude` hides doctrine churn). Reproduce where doctrine is tracked.
- **Already-broken fallout test**: `tests/charter/test_sync_references.py:156` already calls the
  removed `Extractor(tactic_registry=...)` under `# type: ignore` — it retires with the file.
- **Genuine staleness must survive**: the freshness fix must not suppress a real
  `charter.yaml`/pack change; only a genuine no-op may skip synthesize.
- **Doctrine readers require materialized artifacts**: many consumers load
  `.kittify/doctrine/**` from disk, so the fix confines regeneration to explicit write commands /
  genuine-change gating — it must NOT make artifacts on-demand-only (that would touch every reader).
- **`test_generator.py` cannot be deleted wholesale**: it hosts the surviving compiler tests;
  only the generator import line + the 4 generator-API tests are removed.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Delete `charter.generator` module + reexports | As a maintainer, I want `src/charter/generator.py` (`CharterDraft`/`build_charter_draft`/`write_charter`) and its `src/charter/__init__.py` import + `__all__` entries removed so the dead wrapper is gone. | High | Open |
| FR-002 | Retire generator dead-API tests, keep compiler tests | As a maintainer, I want the `build_charter_draft`/`write_charter` tests + the generator import line in `tests/charter/test_generator.py` removed while the 4 `write_compiled_charter` symlink-guard tests are preserved. | High | Open |
| FR-003 | Delete `charter.extractor` module + test-only refs | As a maintainer, I want `src/charter/extractor.py` (`Extractor`) and the `test_extractor*`/`test_sync*` files that import it retired, since it has zero non-test `src/` callers. | High | Open |
| FR-004 | Remove the three deferred extractor allowlist entries | As a maintainer, I want the `_baselines.yaml` `category_5` count (1→0), the `test_no_dead_modules.py` `"charter.extractor"` entry, and the `test_no_dead_symbols.py` `Extractor` SymbolKey frozenset + its union term removed so the gates stay green (no stale/dangling) and baselines shrink downward. | High | Open |
| FR-005 | Render path stays no-op-stable | As a developer, I want `build_charter_context` and the `charter context` CLI to write no git-tracked artifact (only untracked runtime state), locking in the #2773 render-path fix. | High | Open |
| FR-006 | Preflight/synthesize surface is no-op-stable (guarded) | As a gate, I want the preflight auto-refresh → `charter synthesize` path to not churn tracked doctrine on an unchanged tree, and a regression guard pinning it. **Post-tasks finding:** already ensured at HEAD by #2732 (charter.yaml content-hash freshness) + #1912 (promote `_substantively_equal` guards); this mission adds the guard only — no behavioral change. | High | Open |
| FR-007 | No-op-stability guards use a doctrine-tracked fixture | As an implementer, I want the no-op-stability guards asserted against a real-synthesized, doctrine-tracked fixture (not the masked working checkout, whose `.git/info/exclude` hides doctrine and whose `built_in_only` state can't reproduce), so the assertion is meaningful. | Medium | Open |
| FR-008 | Close #2373 with a terminal verdict + guard | As an operator, I want #2373 resolved in `issue-matrix.md` with a terminal verdict (render path verified-already-fixed-by-#2773; residual churn fixed) backed by a committed regression guard. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Run-twice tree cleanliness | Any governed charter read/gate run twice on an unchanged, doctrine-tracked tree leaves `git status --porcelain` empty (0 modified tracked files). | Reliability | High | Open |
| NFR-002 | Debt shrinks, gates unrelaxed | Net tracked-source LOC delta is negative; arch dead-code baselines move only downward; zero new `# noqa`/`# type: ignore`/allowlist additions; ruff + mypy --strict clean; cyclomatic complexity ≤ 15 on touched functions. | Maintainability | High | Open |
| NFR-003 | No new hot-path subprocess | The no-op-stability fix adds no subprocess to a pure render/read path; a no-op must be cheaper, not costlier. | Performance | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Do not reopen #2773 invariants | `charter.yaml` remains authoritative; activation FLAT at `charter.yaml` root; `config.yaml` one-line `charter:` pointer; manifest v2; fail-loud with no None→default fallback. | Technical | High | Open |
| C-002 | Preserve the layer boundary | `src/charter/` must not import `specify_cli` (`test_shared_package_boundary`); the preflight/freshness fixes live in `specify_cli.charter_runtime`. | Technical | High | Open |
| C-003 | Never delete a test to go green | Retire a test ONLY because the code it covers is removed (dead-API tests); split survivors (keep the `write_compiled_charter` tests); never green-wash a baseline upward. | Technical | High | Open |
| C-004 | Charter-layer-scoped | Do not chase non-charter #1797 dead-code targets, pack-split #2467, governance tiers #2216, or pack-trust #2539 in this slice. | Technical | Medium | Open |
| C-005 | Doctrine artifacts stay materialized | The fix confines regeneration to explicit write commands / genuine-change gating; it must NOT make `.kittify/doctrine/**` on-demand-only (many readers load from disk). | Technical | Medium | Open |

### Key Entities

- **`charter.generator` module**: dead WP03 wrapper (`CharterDraft`, `build_charter_draft`,
  `write_charter`) over `compile_charter`; to be deleted.
- **`charter.extractor` module**: dead prose→triad scraper husk (`Extractor`); to be deleted
  with its three arch-gate allowlist entries.
- **`synthesized_drg` freshness signal** (`charter_runtime/freshness/computer.py`): the staleness
  input that gates the preflight auto-refresh; its misfire is the residual no-op-churn root.
- **Preflight auto-refresh** (`charter_runtime/preflight/runner.py` `_attempt_auto_refresh`):
  shells out to `charter synthesize`; must not churn on a no-op.
- **Doctrine artifacts** (`.kittify/doctrine/**`: `graph.yaml`, `directive/*`, `tactic/*`,
  `styleguide/*`): git-tracked (committed `.gitignore` negations); the churn target.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `src/charter/generator.py` and `src/charter/extractor.py` no longer exist;
  `git grep` finds zero live `src/` references to their symbols.
- **SC-002**: `pytest tests/architectural/test_no_dead_modules.py tests/architectural/test_no_dead_symbols.py tests/architectural/test_ratchet_baselines.py`
  is green with `category_5_wp_in_flight_adapters = 0` (down from 1) and no stale/dangling entries.
- **SC-003**: In a doctrine-tracked checkout, `spec-kitty charter context`, `spec-kitty doctor
  doctrine`, and one preflight-gated command each run twice leave `git status --porcelain` empty.
- **SC-004**: `pytest tests/charter/` is green; the 4 `write_compiled_charter` symlink-guard
  tests are present and passing.
- **SC-005**: `issue-matrix.md` shows #2373 with a terminal verdict, a committed red-first
  regression guard exists for the no-op-stability fix, and the net tracked-source LOC delta is
  negative.
- **SC-006**: `ruff check .` and `mypy --strict` on touched files pass with zero new suppressions.
