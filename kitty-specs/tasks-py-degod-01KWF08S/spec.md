# Mission Specification: Degod tasks.py — thin CLI over pure cores (Wave 1)

**Mission**: `tasks-py-degod-01KWF08S` · **Type**: software-dev · **Closes**: #2116 (under #2173)
**Status**: Draft (hardened after two pre-plan squads — sizing/arch/parity, then coherence/doctrine/program-alignment)

## Overview & Context

`agent tasks` (`src/specify_cli/cli/commands/agent/tasks.py`, ~3,617 LOC, **9 subcommands / 53
CLI params**) is the codebase's #1 change-magnet: 79% of its commits are fixes across ~100
distinct issues — a recurring defect class under many symptoms, whose root is structural, so per
**DIRECTIVE_040** the sanctioned response is a structural intervention, not a 101st point-fix.
Decision logic, filesystem/git I/O, status emission, and output rendering are interleaved
line-by-line inside four mega-command bodies (`move_task` ~831 LOC / 19 params, `status` ~488,
`map_requirements` ~426, `mark_status` ~280) plus `finalize_tasks` (~172, already near the ≤150
ceiling — it thins cheaply), so **every coordination-contract change edits the whole file**, and
the fragile helper tests that guard it are re-pinned nearly every mission.

This mission thins the command into a **thin CLI shell over pure decision cores behind injected
ports**. `tasks.py` was already *seam-extracted* once (#2058/#2114 — `tasks_outline`,
`tasks_materialization`, `tasks_parsing_validation`, `tasks_finalize_validation`,
`tasks_dependency_graph` exist and are imported); this is the **open #2116** body-thinning
second pass. It is **behavior-preserving (pure parity)** — the pre-existing skip-vs-refuse
inconsistency between commands (see §Deferred, #2300) is NOT changed here. It is Wave 1 of the
degod/unshim program and the first structural cure for the measured test-friction. Template: the
*completed* `agent/mission.py` decomposition (#2056,
`kitty-specs/decompose-mission-god-module-01KVXHF8`, 9 WPs, golden-CLI-characterization-first,
strictly-linear lanes, thin-shell delegation) — used for its *pattern*, not its injection idiom.

## User Scenarios & Testing

**Primary actor**: a spec-kitty contributor (human or agent) changing mission-lifecycle logic.

- **Primary scenario (why):** A contributor changes a coordination-authority rule — e.g. how the
  coord-vs-primary *write* surface is chosen. *Today* they must edit that rule across the
  interleaved 3,617-line command. *After*, they edit **one pure decision core** (or one port
  adapter); the CLI shell and other subcommands are untouched — the change stops rippling.

- **Behavior-parity guard (the crown jewel):** `move_task` on a coord-topology + protected-primary
  tree *skips the primary commit and exits 0* (the "coord skip-exit-0 arm", `tasks.py:1083 →
  1648/1783`, a normal fall-through return driven by `skip_target_branch_commit`, not a
  `typer.Exit(0)`) — while still emitting the transition to the coord branch. This behavior, its
  polymorphic `--json` envelope (extra `wp_file_update`/`status_events_path` keys only in the skip
  arm), and the side effects with no stdout signature (coord-vs-primary event emission, WP-file
  writes, tracker-ref frontmatter, review-artifact override to *both* dirs) **must be frozen by the
  golden characterization before any extraction and reproduced exactly after.**

- **Deferred exception (out of scope, #2300):** the *inconsistency* — `move_task` skips where
  `mark_status` (`:1944`) and `map_requirements` (`:2621`) *refuse-exit-1* on the same condition —
  is a real divergence but a behavior change to reconcile; this mission preserves it.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | A golden CLI-characterization harness freezes the full `agent tasks` surface (9 subcommands, 53 params, each × {human, `--json`} × exit {0,1,2}) **before** any body extraction, and — extending the #2114 harness which explicitly punts it — adds a **coord-topology + protected-branch fixture class** that constructs real on-disk coord-worktree state and drives the *mutating* commands (`move_task`/`mark_status`/`map_requirements`) so the **coord skip-exit-0 arm and the exit-1 refuse arms** (with their conditional `--json` keys) are frozen. **The freeze is not limited to the skip/refuse arms**: it MUST cover every named `move_task` decision branch that WP03 extracts — arbiter-override, rejected-verdict, the planning-artifact-WP arm, review-currency, and the for_review→in_progress force paths — each pinned as an explicit case, gated by a **from-harness branch-coverage measurement** of `move_task`/`status`/`map_requirements` (branch coverage on those functions ≥ a stated threshold, driven by the harness) so no decision branch is extracted unguarded. For the skip arm the distinguishing evidence is asserted (primary-branch HEAD **unchanged** + coord event emitted), not merely exit-0 + key presence. | Draft |
| FR-002 | Decision logic is expressed as **pure functions** — no filesystem, git, status-emission, or rendering side effects — callable and testable independently of the CLI. Wiring a core into a command **replaces** the inline decision block (the old inline logic is deleted, not shadowed): a "called-but-result-discarded" core is a defect, so the wiring WP must prove the core's return value **drives observable behavior** (a fake-core/sentinel test whose perturbed outcome flips the command's observable result), not merely that a caller exists. | Draft |
| FR-003 | Capabilities are supplied through **injected ports** (typed interfaces, Real + Fake), injected at the **extracted-orchestrator boundary** (`_do_<command>(..., *, ports=None)`), **never** on the Typer `@app.command` signature. The set is stratified (per the #2173 candidate-ports adjudication): **program-reference ports** — `FsReader` (coord **READ** authority) and `CoordCommitRouter` (coord **WRITE** authority) — which follower waves reuse. The coord WRITE port exposes **two distinct capability methods over two structurally disjoint real seams** (do NOT fuse them into one `commit()`): **`commit_status(event, *, capability)`** over `emit_status_transition_transactional` (keyed on `GuardCapability`; self-atomic via `BookkeepingTransaction`), and **`commit_artifact(paths, message, *, kind, policy)`** over `commit_for_mission` (keyed on `MissionArtifactKind` + `ProtectionPolicy`). The two-method shape is load-bearing: the Wave-2 consumers use **disjoint halves** — `implement.py` uses only `commit_status`, `acceptance` uses only `commit_artifact` (event-less), `move_task` uses both — so a single `commit()` would be re-cut in Wave 2 (the C-006 failure). StatusEmit atomicity is a property of the transactional emitter (`BookkeepingTransaction`), **not** of port packaging — a `commit_status` method routing through it is equally atomic, so it is a co-equal capability, not a hidden sub-step. **Mission-local seams** — `GitOps` and `Render` — are isolated for tasks.py testability only, explicitly **not** advertised as program-reference ports (#2173 DROPs both). | Draft |
| FR-004 | `move_task`'s transition decision (arbiter-override, the planning-artifact-WP arm, for_review→in_progress force paths, review-currency, the coord skip arm) is extracted into **one pure decision core that reproduces move_task's exact current behavior** — no cross-command change. | Draft |
| FR-005 | The requirement-mapping validation and FR↔WP mapping logic is extracted into a **pure decision** consuming injected reads, separated from frontmatter-write side effects. | Draft |
| FR-006 | The `status` command's compute/aggregation logic (~49 aggregation calls — stale-fallback, `dependency_readiness`, kanban rollup) is extracted into a **pure aggregation core**, separated from rendering. | Draft |
| FR-007 | The five fat command bodies become **thin orchestrators** over the cores and ports. `mark_status` and `finalize_tasks` thin via ports + the pre-existing `tasks_finalize_validation`/parsing seam modules (they carry no new decision core — borrowing move_task's core would be the deferred cross-command unification). | Draft |
| FR-009 | Coordination **READ**-authority and **WRITE**-authority are supplied as **two distinct ports** (`FsReader` vs `CoordCommitRouter`); no single port, function, or path conflates them. | Draft |
| FR-010 | The pre-3.0-layout boundary read is unified onto the **kind-aware coord READ authority** (`resolve_planning_read_dir`) at the 3 sites currently resolving it kind-blind via `resolve_feature_dir_for_mission` (resolver calls at **`move_task:1138`, `finalize_tasks:2373`, `list_dependents:3568`** — re-census at WP-start). **Parity is *guard-outcome* equivalence, NOT dir equivalence** (WP02-proven): the reads feed `check_pre30_layout`, a confirmed byte-identical **no-op on modern layout**, so on a coord topology `resolve_feature_dir_for_mission` (→ `-coord` husk) and `resolve_planning_read_dir(primary kind)` (→ primary) resolve **different dirs** yet the CLI output is identical — that divergence *is* the split-brain this closes. **Per-site pinning is therefore not one-size** (WP02 pin table): `finalize_tasks:2373` + `list_dependents:3568` are **guard-only** (the var is reassigned right after) → migrate to `WORK_PACKAGE_TASK`→primary (WP08). `move_task:1138` is the **SHARED-VAR exception** — its `_mt_feature_dir` also feeds real coord-authority status reads (`_read_transactional_wp_lane:1149`, review-artifact-override:1216) that MUST read the coord husk → it **stays on `resolve_feature_dir_for_mission`**; if the guard is routed, use `STATUS_STATE` (path-equal) or a separate guard-only variable (WP06). The **WP02 proof artifact** establishes the per-site guard-outcome equivalence + the pin table before any rewire. Holds under NFR-001 pure parity. | Draft |
| FR-011 | The cross-cutting **resolution-authority census** is honestly managed as the bodies thin: sites reclassified WRITE→READ (once body-thinning removes their write indicators) **drain** (are removed from the census), and `COORD_AUTHORITY_WRITE_FLOOR`/`CANONICALIZER_FLOOR` are re-measured and **lowered shrink-only** (DIRECTIVE_043). #2072 has **already landed** (the allowlist is composite-keyed qualname+line), so the entries survive the rewire with **no file:line re-key**. Because the floor gate is a lower-bound (`count >= FLOOR`), lowering a floor is **self-attestable by the same WP that owns the gate file** — so the drain MUST ship with **(a)** an enumerated 1:1 cross-base drain artifact (each drained `qualname` mapped to the `git log lane-base..mission-base` hunk that removed its write indicator), **(b)** reviewer (not author) sign-off on that artifact, and **(c)** a **margin gate** (`ROUTED_CANONICALIZER_FLOOR_MARGIN`-style) so a floor set materially below the live count itself fails. Also correct the stale `coord_authority_baseline: 13` scalar → `12` (12 live entries; 1 spurious shrink-only slot today). | Draft |

## Non-Functional Requirements

| ID | Requirement | Measurable threshold | Status |
|----|-------------|----------------------|--------|
| NFR-001 | **Behavior parity** — the golden characterization passes identically before and after **every** WP. | 100% of frozen cases (incl. the coord skip-exit-0 arm + all conditional `--json` keys) pass byte-identically pre- and post-each-WP. Pure parity — no intentional deltas (the deferred unification is out of scope). | Draft |
| NFR-002 | Each extracted core is covered by focused unit tests that run in CI. | **≥ branch-coverage on each core module** (`--cov-branch` ≥ a stated threshold on `tasks_transition_core.py`/`tasks_mapping_core.py`/`tasks_status_view.py`) — "one test per outcome type" is insufficient; every named guard sub-branch in `data-model.md`'s decision entities maps to a specific test (reviewer-verified checklist). Branch set enumerated **from the WP01 golden harness** (not implementer-selected); selected by a CI gate (Wave-0 marker binding, #2294 merged) and fails if the extraction is reverted. **This per-core unit test is the failing-first (red-on-base) artifact satisfying charter C-011 for these pure-parity WPs; the golden harness is the green parity guard.** | Draft |
| NFR-003 | New/changed code passes lint + type checks with no new suppressions. | ruff + mypy clean; CC ≤ 15 per function; 0 new `# noqa`/`# type: ignore`. | Draft |
| NFR-004 | Command bodies **and** extracted orchestrator helpers are bounded. | Each of the 5 fat command bodies ≤ **150 LOC** post-rewire (met: move_task 88, map_requirements 56, status 24, mark_status 39, finalize_tasks 25); each extracted orchestrator/glue helper ≤ **150 LOC** and CC ≤ 15 (so glue can't absorb un-tested decision logic); the extracted cores carry the logic. **The whole-file `tasks.py` ≤1400 LOC shim ceiling + the automated LOC gate are DEFERRED to the follow-up "shim relocation" mission** (see Deferred): thinning the bodies left the orchestrators/glue/port-seam adapters in `tasks.py` (≈4547 LOC), and relocating ~3150 LOC to sibling modules is a large structural move better done as its own reviewed mission. This mission meets the per-body/per-helper bound; the whole-file shim is out of scope. | Draft |
| NFR-005 | Ratchet debt is honestly managed, not hidden. | The **command's own** file:line ratchets are replaced by the golden characterization (DIRECTIVE_041). The cross-cutting **resolution-authority AST census** is composite-keyed (via #2072) and **shrink-only** (DIRECTIVE_043): reclassified sites drain, floors lower, **net-zero new entries**. WP08 + the mission-merge run the full `tests/architectural/` sweep with mission-base-vs-lane-base cross-diff (`post-merge-arch-gate-adjudication` procedure). | Draft |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | **CoordRead-authority ≠ CoordWrite-authority** — two distinct ports, never unified (the #2160 structural form; re-unifying is a regression). The split is proven by the Wave-2 consumers exercising **disjoint write capabilities**: `acceptance` **is a writer** (it routes `commit_for_mission` on protected primaries and commits directly otherwise) but uses **only the `commit_artifact` (event-less) leg** — never `commit_status` — while `implement.py` uses only `commit_status`. (The earlier "acceptance does zero writes" framing was factually inverted; the real proof is capability-disjointness, which is exactly why the WRITE port needs two methods — FR-003.) | Binding |
| C-002 | Stay **out of the blind primitive** `primary_feature_dir_for_mission` (FR-011 recursion hazard). Keep the `_canonicalize_primary_read_handle` fold and the primitive call **co-located inside the adapter method** — the canonicalizer gate's def-use check is strictly intra-function, so splitting the fold across the port boundary turns the gate RED. | Binding |
| C-003 | Selector/handle ambiguity raises `MissionSelectorAmbiguous` (or the established structured error) — **never** a silent fallback. | Binding |
| C-004 | The golden characterization test (incl. the coord skip-exit-0 topology fixture) lands **first** (WP01), before any body extraction. | Binding |
| C-005 | Ports are **co-designed** here (no prior codebase precedent for protocol-capability injection). A `*, ports=None`-style keyword param on the **extracted orchestrator helper**, **not** the Typer `@app.command` signature (a Protocol param on a decorated command collides with Typer introspection → an unwanted `--port` flag / registration failure). | Binding |
| C-006 | Scope is the `agent tasks` surface **only** — no changes to `workflow`/`implement`/`acceptance` (Wave 2), the `#2173` MissionResolver generalization, `#2164` Phase-1 gate, or `#2297`. The cross-command skip-vs-refuse unification is deferred (#2300). | Binding |

## Success Criteria

- **SC-001** — A representative coordination-contract change touches **one** decision unit (or one port adapter), not the whole command file.
- **SC-002** — The `agent tasks` CLI behaves **identically** before and after: 100% of the frozen characterization cases (incl. the coord skip-exit-0 arm) pass unchanged.
- **SC-003** — Each extracted **decision/aggregation** core reproduces its command's exact current behavior, verified by driving the command through the core against the golden harness (not a stubbed cross-command test).
- **SC-004** — Every new decision/aggregation core is covered by unit tests that run in CI and fail on a reverted extraction.
- **SC-005** — The five command bodies are each reduced to ≤ 150 LOC thin orchestrators, with the logic in tested cores. *(The full "shim state" — 0 inline `json.dumps` + whole-file ≤1400 LOC — is DEFERRED to the follow-up shim-relocation mission; see Deferred.)*

## Work Package Shape (post-squad: resized to 9; strictly linear)

1. **WP01** — Golden CLI-characterization harness (FR-001, C-004): the 9-command/53-param surface **plus a coord-topology + protected-branch fixture** freezing the skip-exit-0 arm (distinguishing evidence: primary HEAD unchanged + coord event) + exit-1 refuse arms + conditional `--json` keys + **every named `move_task` decision branch** (arbiter-override, rejected-verdict, planning-artifact-WP, review-currency, force paths), gated by a **from-harness branch-coverage measurement** of the mutating commands.
2. **WP02** — `TasksPorts` co-design (FR-003, FR-009, C-002, C-005): the stratified set — **program-reference** `FsReader` (coord READ) + `CoordCommitRouter` exposing **two capabilities** `commit_status` (over the transactional emitter) + `commit_artifact` (over `commit_for_mission`, event-less leg), **mission-local** `GitOps`/`Render` — Real/Fake adapters; the canonicalizer fold co-located in the adapter; injection at the orchestrator boundary; **plus the FR-010 dir-equivalence proof artifact** (per-kind coord-fixture equivalence). *(Prereq: #2072 landed — see Dependencies.)*
3. **WP03** — `move_task` transition decision core, pure, behavior-preserving (FR-004, FR-002); wiring **deletes** the inline decision block + a fake-core sentinel test proves the core drives behavior.
4. **WP04** — Requirement-mapping decision core, pure (FR-005, FR-002); same delete-and-sentinel wiring discipline.
5. **WP05** — `status` aggregation core, pure (FR-006, FR-002); same.
6. **WP06** — `move_task` rewire to a thin orchestrator (FR-007, NFR-004) + FR-010 read-authority migration for its site (`move_task:1138`, pinned `kind`).
7. **WP07** — Rewire the **core-backed** bodies: `map_requirements` (over the WP04 core) + `status` (over the WP05 core + `Render`) to thin orchestrators (FR-007, NFR-004).
8. **WP08** — Rewire the **coreless** bodies: `mark_status` + `finalize_tasks` via ports + existing `tasks_finalize_validation`/parsing seams (FR-007, NFR-004) + FR-010's `finalize_tasks:2373`/`list_dependents:3568` folds (pinned `kind`) + a **structural non-import AST gate** asserting `tasks_transition_core` is NOT reachable from `mark_status`/`finalize_tasks` (guards the deferred-unification boundary structurally, not just behaviorally).
9. **WP09** — *(slimmed — census cleanup ONLY; Render seam + shim relocation deferred to the follow-up mission)* The resolution-authority census drain: lower `COORD_AUTHORITY_WRITE_FLOOR` 12→9 (shrink-only) + drain the 5 stale allowlist entries the WP01–WP08 rewires left (`list_dependents:3568`, `list_tasks:2198`, `move_task:1138/1396`, `validate_workflow:2995`), with an **enumerated cross-base drain artifact + reviewer sign-off + margin gate** (FR-011, NFR-005) + the full `tests/architectural/` cross-base sweep confirming green. This unblocks the 4 currently-red arch gates that this mission's own drains caused.

## Key Entities

- **TasksPorts** — program-reference: `FsReader` (coord READ) and `CoordCommitRouter` (coord WRITE, two capabilities `commit_status` over the transactional emitter + `commit_artifact` over `commit_for_mission`); mission-local: `GitOps`, `Render` (dual-arm). Each with Real + Fake adapters.
- **Decision/aggregation cores** — pure: `move_task` transition decision, requirement-mapping decision, `status` aggregation.
- **Golden characterization contract** — the frozen behavioral snapshot incl. the coord-topology fixture.

## Assumptions

- **Wave 0 (#2294) is merged** — the CI-marker gate binding is in place, so NFR-002's "tests run in CI and fail on reverted extraction" enabler is satisfied (not speculative).
- The `#2173` DI mechanism (keyword port injection at the orchestrator boundary) is co-designed here; WP02 delivers the reference set (FsReader + CoordCommitRouter) the epic's Phase 2 generalizes into `MissionResolver`.

## Dependencies

- **Base:** rebased onto `upstream/main` (Priivacy-ai, `956a328f4`) 2026-07-01 — **decoupled** from PR #2299 (doctrine-catfooding), which lands as its own PR. The cited directives (040/041/043/044) + the `post-merge-arch-gate-adjudication` procedure are present in upstream/main's `src/doctrine/`, so the decoupling dangles no references. degod lands to `main` via its own PR.
- **Hard predecessor:** **#2072 Obligation-A** (composite-key re-key of the tasks.py `coord_authority` census entries) must **land before WP03**, not merely run in parallel — the body-thinning shifts every line, so file:line-keyed entries would force a manual re-key on every WP (the exact friction #2072 removes). Under composite-key the entries are line-independent and survive the rewire (FR-011). This is the DIRECTIVE_041 stable-anchoring remediation, not an optional enabler.

## Deferred (explicit, with follow-up)

- **#2300** — the skip-vs-refuse cross-command inconsistency (`move_task` skips-exit-0 where `mark_status`/`map_requirements` refuse-exit-1 on coord+protected). Reconciling it is a behavior change (violates this mission's pure parity); deferred to a follow-up that will characterize-then-intentionally-diff the chosen unified behavior.
- **Render seam + shim relocation (→ follow-up mission)** — the former **Render-seam requirement** (dual-arm Render seam: the 13 inline `json.dumps` → a Render port + AST "0 remaining" gate + status-`indent` unification) and the whole-file **SC-005/NFR-004 ≤1400 shim ceiling** (relocating ~3150 LOC of orchestrators/glue/port-seam adapters out of `tasks.py` to sibling modules) are **descoped from this mission** and moved to a focused follow-up. Rationale: this mission's core value (decomposing the change-magnet decision logic into pure, tested cores with all command bodies thinned ≤150 LOC and byte-identical behavior) is complete at 8 WPs; the render-seam unification and the large "make `tasks.py` a true registration shim" relocation are lower-risk-per-move but large and orthogonal, and are better specced + reviewed as their own mission. The 13 `json.dumps` are pre-existing (not debt this mission created), so deferring them is clean. **NOT deferred: the census cleanup** (WP09) — the rewires drained the coord-authority census below its floor, which is debt *this* mission created and must land here so the arch gates are green.

## Non-Goals

- The coord-authority trio degod — `workflow.py` / `implement.py` / `acceptance/__init__.py` (Wave 2).
- The full `#2173` `MissionResolver` generalization; the `#2164` Phase-1 canonicalizer gate (Wave 2); the `#2297` suite-map generator (its "FR-two" work).
