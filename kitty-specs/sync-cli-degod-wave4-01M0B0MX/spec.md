# Mission Specification: Sync CLI Degod — Wave 4

**Mission Branch**: `refactor/wave4-sync-degod`
**Created**: 2026-08-18
**Status**: Draft
**Input**: Wave-4 (CLI-split half) of the degod/unshim program. Decompose `cli/commands/sync.py` (6,332 LOC) into ports + pure cores + thin command shells and tidy `calibration/walker.py`, retiring the three `# noqa: C901` and clearing walker's `S1192` cluster — **with zero behavior change**, under the program's architectural invariants. Grounding: `research/mission-brief.md`. Tracked under the degod-delivery epic (`#1797` — "where god-objects get extracted") advancing program parent `#1619`; a tracking child is filed at merge (FR-008). PR to upstream/main; coord topology.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Decompose the sync god-module behind a frozen CLI contract (Priority: P1)

A maintainer needs `cli/commands/sync.py` — the single largest, worst-rated source file in the repository — to become a set of small, focused, individually-testable modules (ports + pure decision cores + thin Typer command shells), so future sync work is reviewable and the pure cores are stub-testable. Before touching structure, they freeze the observable behavior of all 22 `spec-kitty sync` subcommands with a golden-CLI-characterization test; every extraction is then a refactor that keeps that characterization green.

**Why this priority**: This is the mission. The file blocks reviewability and carries three complexity suppressions the charter says to retire. The golden test is the safety net that makes the decomposition safe; without it, extraction risks silent behavior drift.

**Independent Test**: Land the golden-CLI-characterization test (all 22 subcommands' flags/exit-codes/`--json`); confirm it passes on the pre-decomposition code, then passes unchanged after each extraction — the observable CLI contract is byte-stable.

**Acceptance Scenarios**:

1. **Given** the pre-decomposition `sync.py`, **When** the golden-CLI-characterization test runs, **Then** it passes and records the exact flags, exit codes, and `--json` envelopes for all 22 subcommands (including the coord exit-0 silent-skip arm and `status --check` exit-2).
2. **Given** any extraction commit (a port, a pure core, a command-shell move), **When** the golden test re-runs, **Then** it passes **unchanged** — no observable CLI behavior differs.
3. **Given** the completed decomposition, **When** `ruff`/Sonar complexity is measured, **Then** `sync_workspace`, `status`, and `doctor` no longer carry `# noqa: C901` and each function is at or below the complexity ceiling.
4. **Given** an about-to-be-extracted command among `{status, doctor, sync_workspace, diagnose}`, **When** its extraction WP begins, **Then** a snapshot of its **non-`--json` human-render output AND every `--json` branch** already exists and is green — a `--json`-happy-path-only freeze does not satisfy the gate.

---

### User Story 2 - Preserve the architectural invariants during the split (Priority: P1)

A reviewer needs assurance the decomposition honors the degod program's non-negotiable invariants and the repository's architectural gates — a careless split (e.g. unifying the read/write authority, placing cores in the wrong layer, mutating a positional-anchor ratchet) is a regression even if the CLI still works.

**Why this priority**: The operator's explicit constraint is architectural-design compatibility. These invariants are what separate a safe degod from a structural regression; they are as load-bearing as behavior preservation.

**Independent Test**: Run the architectural-gate suite (layer rules, shared-package boundary, dead-symbol/module baselines, ratchet + positional-anchor + golden-count guards, sync-writer census, terminology) after the decomposition and confirm all remain green with no ratchet allowlist growth used to accommodate the refactor.

**Acceptance Scenarios**:

1. **Given** the extracted cores and ports, **When** the layer-rule, shared-package-boundary, and `status`/`dossier`→sync boundary gates run, **Then** every new module lives under `specify_cli.sync.*`/`cli.commands.*` (never `runtime` or a new top-level package), introduces no cross-boundary or SDK-internal import, and adds no new `status`/`dossier`→sync edge.
2. **Given** the sync authority logic, **When** it is split, **Then** a dedicated architectural test asserts the read authority and write authority are distinct port symbols with **no shared authority class** — proving non-unification mechanically, not by diff inspection.
3. **Given** the golden test, **When** it is added, **Then** it does not rely on mutating the DIR-041 positional-anchor ratchet allowlists.
4. **Given** the ~60 tests that monkeypatch `sync` internals, **When** the decomposition completes, **Then** they pass green as a co-gate (the seam is preserved), and any patched callee invoked by a relocated core is reached through the shell.

---

### User Story 3 - Clear the mechanical smell debt (Priority: P2)

A maintainer completes the two behavior-preserving mechanical sweeps that ride alongside the degod: `calibration/walker.py`'s duplicated-URN-literal cluster and `sync.py`'s Tier-1 smells (nested ternaries, re-inlined literals, malformed suppression comments).

**Why this priority**: High signal-to-risk, independently landable, and it clears the litter on the surfaces the degod touches. `walker.py` is a distinct file with its own regression guard.

**Independent Test**: `walker.py`'s `S1192` count goes to zero by completing its named-constant set, with the calibration suite (frozenset-equality) proving byte-identical behavior; `sync.py` Tier-1 findings are resolved and re-verified against a fresh Sonar run.

**Acceptance Scenarios**:

1. **Given** `walker.py`, **When** the named-constant set is completed and raw URN literals are replaced (landing first, as a standalone campsite slice), **Then** the calibration inequality tests pass unchanged (frozensets resolve identically) and the `S1192` count reaches 0.
2. **Given** `sync.py` Tier-1 findings, **When** the nested ternaries are extracted, literals referenced, and malformed suppression *formats* corrected, **Then** behavior is unchanged, no guarded `except` is removed, and no live `S3358`/`S1192` remains on the changed functions.
3. **Given** the sync surface, **When** the env-var census runs, **Then** `docs/plans/code-quality/sync-env-census.md` lists every `SPEC_KITTY_*` reference with a live/retire-candidate verdict, and a guard confirms the **set** of `SPEC_KITTY_*` references is unchanged by the mission (nothing deleted).
4. **Given** the deferred adapter-consolidation and env retirement-candidates, **When** the mission merges, **Then** tracked follow-on issue(s) are filed under the degod-delivery epic (`#1797`, advancing `#1619`) and referenced in the PR body.

### Edge Cases

- **Monkeypatch seams**: ~60 tests monkeypatch `sync.py` `_*` privates (e.g. `get_vcs`, `_check_server_connection`, `_run_event_sync_dispatch`, `_run_dispatch_batches`), and they work today only because those callees resolve as bare module-globals at call time. The husk re-export preserves import/attribute resolution but **not** call-time patch dispatch for a relocated caller that re-binds the name via its own local import — so a moved core must reach a patched callee through the shell (bare-name in the husk shell, or port-injected). Re-export alone is necessary-not-sufficient (C-005); the patch-tests are the seam gate (NFR-001).
- **The coord exit-0 silent-skip arm** (SaaS-disabled guard) is a *documented behavior to freeze*, not an ambiguity swallow — it must be preserved exactly, not "cleaned up" into an error.
- **Golden-test coverage gaps**: `workspace` (no CLI golden today), `status` full human-render (the cc-90 path), `doctor` non-json render + each `--json` branch, and `diagnose --json` are under-characterized and must be frozen *before* their extraction.
- **Deferred behavior**: daemon reuse/kill/lifecycle semantics and env-var deletion are explicitly frozen/deferred; a change to either is out of scope and would be a scope breach.
- **Baseline drift**: arch-gate count baselines must be re-pinned against `upstream/main` (the true merge-base), not the stale fork `origin/main`.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Golden CLI contract frozen first | As a maintainer, I want a golden-CLI-characterization test freezing all 22 `spec-kitty sync` subcommands' flags/exit-codes/`--json` landed before any extraction — and, for the under-characterized commands (`status`, `doctor`, `sync_workspace`, `diagnose`), a snapshot of the **non-`--json` human-render path AND every `--json` branch** frozen before that specific function is extracted — so the decomposition is provably behavior-preserving and cannot be satisfied by `--json`-happy-path coverage alone. | High | Draft |
| FR-002 | Decompose sync.py into ports + cores + shells | As a maintainer, I want `cli/commands/sync.py` split into injectable ports, pure decision cores, and thin command shells, so the god-module becomes small, focused, reviewable modules. | High | Draft |
| FR-003 | Retire the three C901 suppressions | As a maintainer, I want `sync_workspace`, `status`, and `doctor` decomposed so their `# noqa: C901` come off and each function is within the complexity ceiling. | High | Draft |
| FR-004 | Preserve the read/write authority split, guarded | As a reviewer, I want the sync read authority and write authority kept as two separate ports/adapters (never unified), **backed by an architectural test asserting distinct read-port and write-port symbols with no shared authority class** — so the #2160-class invariant is provable, not diff-eyeballed. | High | Draft |
| FR-005 | Complete walker.py's constant set (standalone-first) | As a maintainer, I want `calibration/walker.py`'s duplicated URN literals replaced by a completed named-constant set — shipped as a **standalone campsite slice that lands first**, independent of the sync degod (no dependency on the golden test, ports, or husk) — so its `S1192` cluster is cleared with byte-identical behavior. | Medium | Draft |
| FR-006 | Clean sync.py Tier-1 smells | As a maintainer, I want `sync.py`'s Tier-1 mechanical smells cleaned behavior-preserving: extract the nested ternaries (`S3358`), reference/hoist the re-inlined literals (`S1192`), and correct the malformed suppression-comment **format** (`S7632`). Fixing a malformed suppression means correcting the `# noqa … — …` em-dash format, **never removing the suppression or its guarded `except`**. | Medium | Draft |
| FR-007 | Produce an env-var census (inventory only, anti-deletion proof) | As a maintainer, I want a `SPEC_KITTY_*` env-var census for the sync surface written to a named artifact (`docs/plans/code-quality/sync-env-census.md`), listing every `SPEC_KITTY_*` reference under the sync surface with a live/retire-candidate verdict — and a guard proving the **set** of `SPEC_KITTY_*` references is unchanged by the mission (deletion defers to WS6). | Low | Draft |
| FR-008 | File the deferred follow-on(s) as tracked children | As a maintainer, I want the deferred work filed as tracked issues at merge — the Wave-4 adapter-consolidation follow-on (`emitter`/`transport_attempts`/`queue`/`daemon`, WS4/WS6-gated) and the census-derived env retirement candidates — under the degod-delivery epic (`#1797`, advancing `#1619`), so the deferral leaves durable pointers. | Low | Draft |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No behavioral regression, patch-tests co-gate | The pre-existing sync + calibration suites (`tests/sync/`, `tests/cli/commands/test_sync_*`, `tests/calibration/`) pass at 100%; the golden-CLI-characterization test passes identically pre- and post-extraction; **and the ~60 existing tests that monkeypatch `sync` internals pass green as an explicit co-gate** (the golden test proves production behavior; the patch-tests prove the seam is preserved). | Reliability | High | Draft |
| NFR-002 | Complexity ceiling met, zero net-new suppressions | The three `# noqa: C901` are removed; every extracted/changed function passes `ruff` C901 / Sonar S3776 at ≤ 15; **zero net-new `C901`/`S3776` suppressions anywhere on the sync surface** (per-line included) — the net `# noqa` count on the changed files does not increase, and the pre-existing justified `BLE001`/`S105`/`S608`/`PLC0415` suppressions are preserved unchanged; `ruff` + `mypy --strict` clean on changed files. | Maintainability | High | Draft |
| NFR-003 | Smell reduction, class-bound | `walker.py` `S1192` count → 0; **zero remaining live `S3358` or `S1192` findings on the changed `sync.py` functions** (bound to the FR-006 rule classes, not a net "decrease by 1"); the target set is re-verified against a fresh Sonar run (the file has drifted from the 2026-08-12 snapshot) and the before/after Sonar issue list for the two files is committed as a mission artifact. | Maintainability | Medium | Draft |
| NFR-004 | Arch-gates stay green | The architectural-gate suite remains green — layer rules, shared-package boundary, `test_status_sync_boundary.py`, `test_dossier_sync_boundary.py`, dead-symbol/module baselines, ratchet + positional-anchor + golden-count guards, sync-writer census, no-legacy-terminology — with count baselines re-pinned against `upstream/main` (not the stale fork `origin/main`; if the merge-base surfaces pre-existing red, a tracking issue is opened per DIR-013 before treating it as baseline). | Reliability | High | Draft |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Layer + boundary placement | New cores/ports live under `specify_cli.sync.*` / `cli.commands.*` — never `runtime`, never a new top-level `src/` package; zero import of the `runtime`/`spec_kitty_runtime` **package**; events/tracker consumed only via the existing public adapter seam (no `_internal`, no SDK re-export). The extraction introduces **no new `status`→sync or `dossier`→sync edge** — a symbol relocated into `specify_cli.sync.*` must not be one `status`/`dossier` currently reaches (`test_status_sync_boundary.py`, `test_dossier_sync_boundary.py`, #862). | Technical | High | Draft |
| C-002 | Port discipline | Ports are injected on the command shell (default-param), not the frozen `MissionExecutionContext`; exactly one adapter per port; extracted consent/grant writers stay within the sync-writer-census roots. | Technical | High | Draft |
| C-003 | Golden-test-first, no ratchet mutation | The golden-CLI-characterization test lands before any extraction and must not be satisfied by mutating the DIR-041 positional-anchor ratchet allowlists. | Technical | High | Draft |
| C-004 | Deferred scope frozen | Daemon reuse/kill/lifecycle **behavior** is frozen (deferred to WS4); the daemon-owner read/guard code (`_require_daemon_owner_coherence`, owner-record reads) **may be relocated intact** — its behavior is pinned by the golden test, not changed. Env-var deletion is deferred to WS6 (census only). The `emitter`/`transport_attempts`/`queue`/`daemon` adapter-consolidation is out of scope (sequenced follow-on). | Business | High | Draft |
| C-005 | Import/monkeypatch compat (caller-side binding) | The husk keeps `sync.<name>` import/attribute seams resolvable via a guarded re-export block (the `runtime_bridge` #2531 pattern). Re-export is **necessary but not sufficient** for the ~60 patch-tests: any monkeypatched callee invoked by a relocated core must be reached **at call time through the shell** — kept as a bare-name call inside the husk-module shell, or injected as a shell-resolved port — so `monkeypatch.setattr("…commands.sync.<name>", …)` still intercepts. The patch-tests are the seam gate (NFR-001). | Technical | High | Draft |
| C-006 | Blind-primitive avoidance | No extracted module introduces a `primary_feature_dir_for_mission` reference; any mission-dir composition routes through the sanctioned resolver seam. No arch-gate guards this — discipline + review + the golden test are the only defense, so it is a fail-closed constraint, not an assumption. | Technical | High | Draft |
| C-007 | Freeze-over-improve on ambiguity | The roadmap's "ambiguity → typed error, never silent" invariant is **subordinated to SC-004 zero-behavior-change**: extracted resolvers are frozen exactly as-is — they neither newly-swallow an ambiguity into a fallback nor newly-raise a typed error. (The coord exit-0 silent-skip arm is a documented behavior to preserve, not an ambiguity swallow.) | Technical | Medium | Draft |

### Key Entities *(include if feature involves data)*

- **`spec-kitty sync` subcommands (22)**: the Typer command surface whose observable contract (flags, exit codes, `--json` envelopes) is the thing being frozen and preserved.
- **Ports**: injectable adapter interfaces — `Render`, `GitOps`, `Clock`, `FsReader` (reused), plus sync-specific `DeliveryQueue` and a two-part `AuthorityGate` (read vs write).
- **Pure cores**: stub-testable decision logic with no I/O — status row/coherence build, doctor report build, dispatch/exit-code decisions, purge census differentials, per-project-store summaries.
- **Golden-CLI-characterization contract**: the frozen behavior spec (extends `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/contracts/sync-status-output.md`).
- **`_REQUIRED_SCOPE` calibration table**: the `walker.py` lookup whose raw URN literals become named constants.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `cli/commands/sync.py` is reduced to thin command shells (each shell = parse args → open ports → call core → render, **no decision logic**) plus focused modules **each ≤ 800 LOC** (well under the 6,332-LOC god-module), and the **three `# noqa: C901` are gone** (`sync_workspace`, `status`, `doctor` each ≤ 15 complexity).
- **SC-002**: **100%** of the pre-existing sync + calibration suites remain green, and the golden-CLI-characterization test freezes all **22** subcommands' contract and passes identically before and after every extraction.
- **SC-003**: `walker.py`'s `S1192` count reaches **0**; the net Sonar smell count on the two target files strictly decreases and is reported.
- **SC-004**: **Zero** behavior change — no env var deleted, no daemon-lifecycle semantics changed, the CoordRead≠CoordWrite split preserved — verifiable from the diff and the green golden test.

## Assumptions

- The decomposition follows the established degod template — `runtime_bridge` (#2531) six-seam split (closest analogue) and the coord-authority trio (#2464/#2465/#2508) shell+core+executor pattern, reusing the `agent_tasks_ports.py` port set.
- `sync.py` currently imports no `runtime`/`spec_kitty_runtime` **package** (its `get_runtime_root` comes from `specify_cli.paths`, which is legal) and does not reach `primary_feature_dir_for_mission` (now C-006). The decomposition keeps both true.
- The 2026-08-12 Sonar line numbers have drifted; the exact Tier-1 findings are re-verified against a fresh run at implementation time.
- Grounding: the 4-lens research squad brief is persisted at `research/mission-brief.md`; the post-spec adversarial squad findings at `research/squad-findings-post-spec.md`.

## Out of Scope

- The `emitter`/`transport_attempts`/`queue`/`daemon` **adapter-consolidation** (a different refactor shape gated on #2173 Phase-2 / WS4 / WS6) — a sequenced Wave-4 follow-on.
- **Deleting** any `SPEC_KITTY_*` env var (defers to the WS6 versioned-contract policy ADR) — this mission produces the census only.
- Any **behavioral** change to daemon reuse/kill/lifecycle (defers to WS4 daemon-identity).
