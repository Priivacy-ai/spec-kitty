# Mission Specification: Post-Consolidation Write Surface and Authoring Finish

**Mission Branch**: `feat/post-merge-write-authoring-finish`
**Created**: 2026-07-30
**Status**: Draft
**Input**: Finish the write-side placement seam pieces PR #3076 deferred — wire the CONSOLIDATED surface so artifact writes succeed after a mission is consolidated/published even once its Target Ref is deleted (#3033), with no staging residue on refusal (#3073); plus deterministic authoring finish-work (#2318 negative invariants + stale-verdict persist; #1738 same-repo URL issue references).

## Terminology (binding for this spec — the `merge` footgun)

`merge` is a three-sense overloaded term (Terminology Canon; ADR 2026-07-23-2). This spec **always names the sense**:

- **Lane consolidation (E1)** — `spec-kitty merge` folds lane branches into the **Target Ref**. Local. Deletes only *lane* branches; the Target Ref **survives**. The integrated tree now lives on the Target Ref; `baseline_merge_commit` is landed there. This is `LifecyclePhase.POST_CONSOLIDATION`.
- **Publish to trunk (E2)** — the Target Ref branch is integrated into the **Primary Branch** (trunk / `main`) via PR and then deleted. The integrated tree now lives on the Primary Branch, in the **repository-root checkout**. The Target Ref is **gone**.
- **Target Ref** = `target_branch` = the mission's **feature branch** (NOT trunk).
- **Primary Branch** = trunk (`main`).
- **CONSOLIDATED surface** (`TopologySurface.CONSOLIDATED`) = the abstraction for *the consolidated/integrated tree, wherever it currently lives* — the Target Ref tree in E1, the repository-root checkout on the Primary Branch in E2. It exists precisely to name this independently of any one branch.

#3033's symptom — a **deleted `target_branch`** — is **E2**, not E1. The fix is to **wire the CONSOLIDATED surface** (its intended, so-far-dormant first production wiring), not to route around it.

**Tidy-first (#3080).** This mission also lands the *"do not make it worse"* foundation of the `consolidate`-canonicalization effort (#3080): it canonicalizes **`consolidate`/`consolidation`** for the lane-consolidation (E1) sense via an ADR decision, a glossary update, and a CI drift-ratchet guard — sequenced **before** the Lane A functional work. The full command/code/docs rename (renaming `spec-kitty merge`, `MergeState`, `baseline_merge_commit`, etc.) stays #3080; doing it here would explode scope. See FR-014/015/016, C-012.

## Context

PR #3076 shipped the write-side placement seam but deferred:

- **CONSOLIDATED write routing (#3033, P0):** `resolve_placement_only` resolves PRIMARY-kind writes to the Target Ref unconditionally. In E2 the Target Ref is deleted, so `safe-commit`'s HEAD-vs-ref guard can never be satisfied and evidence writes fail; #3076 shipped only a graceful *refusal* naming #3033. The composed writers also stage a file to disk *before* the routability probe, leaving residue on a refused write (#3073).
- **Authoring finish-work (#2318, #1738):** the acceptance CLI cannot register/execute a *negative invariant* (a malformed one crashes `--diagnose`); an all-pass matrix persists a stale `overall_verdict: pending` (samuelgoff, v3.2.6); and issue-reference discovery recognizes only `#NNN`, missing same-repo GitHub-URL references and recording no source-file provenance.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Evidence writes succeed on a consolidated mission whose Target Ref is deleted (Priority: P1)

After a mission is consolidated (E1) and then published to trunk (E2) — Target Ref deleted, content on the Primary Branch — an operator/agent records post-consolidation evidence (acceptance-matrix verdict, tracer finding, issue-matrix update, retrospective). Today the write fails or is refused because placement still targets the deleted Target Ref. After this mission, the CONSOLIDATED surface resolves to the integrated tree's current home and the write succeeds; an genuinely-unroutable write refuses cleanly with no residue.

**Why this priority**: The escalated P0 (#3033). Post-consolidation evidence capture is a core lifecycle guarantee, today broken on the E2 (deleted-Target-Ref) configuration.

**Independent Test**: On a mission consolidated then with its Target Ref deleted, from the repository-root checkout on the Primary Branch, run `spec-kitty safe-commit` on a classified PRIMARY artifact; the commit succeeds and the tree is clean.

**Acceptance Scenarios**:

1. **Given** an E2 mission (consolidated, Target Ref deleted, integrated content on the Primary Branch), **When** an agent runs `spec-kitty safe-commit` on a classified PRIMARY artifact from the repository-root checkout, **Then** the artifact commits to the CONSOLIDATED surface and the command exits 0.
2. **Given** the same E2 mission, **When** a composed writer records a coord-partitioned artifact (issue-matrix / tracer / acceptance-matrix) via the write seam, **Then** the write returns a committed result on the CONSOLIDATED surface instead of `refused`.
3. **Given** a write that genuinely cannot be routed (no resolvable consolidated location), **When** the composed writer runs, **Then** it refuses with a structured, recoverable result **and leaves zero untracked staging files** (#3073).
4. **Given** an operator on a checkout that does not carry the mission's consolidated content (ancestry check fails), **When** they attempt a post-consolidation write, **Then** the command refuses with a recovery instruction naming what to check out; it does not force a checkout.

---

### User Story 2 - Agent drives a full accept pass with zero hand-edited JSON (Priority: P2)

An agent finishing a mission records acceptance results — including a *negative invariant* (a condition that must NOT hold) — and preflights the gate. Today only per-criterion marking exists; a negative invariant must be hand-edited into JSON with the exact dataclass shape, a malformed one crashes `--diagnose`, and an all-pass matrix persists a stale `pending` verdict. After this mission the agent registers/executes negative invariants through the deterministic command, a malformed shape is *reported* not crashed, and canonical acceptance persists a fresh verdict.

**Why this priority**: #2318 residual (three sub-bugs: negative-invariant handling, `--diagnose` crash, stale-verdict persist).

**Independent Test**: Register a negative invariant via the CLI, run the accept diagnostics on a malformed one (reported, not crashed), and confirm an all-pass matrix persists `overall_verdict: pass`.

**Acceptance Scenarios**:

1. **Given** a mission with acceptance criteria, **When** an agent registers and executes a negative invariant through the deterministic command, **Then** it is persisted with the correct shape (zero hand-edited JSON) and its result recorded.
2. **Given** a malformed negative invariant, **When** the agent runs the accept diagnostics, **Then** the malformed invariant is reported with its reason and the command exits non-zero without an unhandled exception.
3. **Given** an all-pass acceptance matrix with no negative invariants, **When** canonical acceptance runs, **Then** the persisted `overall_verdict` is a fresh `pass`, not a stale `pending` (#2318, samuelgoff fixture).
4. **Given** a fully-marked matrix, **When** the accept mission-step prompt runs, **Then** it drives the pass by calling the acceptance CLI (no instruction to hand-edit JSON).

---

### User Story 3 - Same-repo GitHub-URL issue references are recognized with provenance (Priority: P3)

An author cites an issue by full GitHub URL to **this repository** (`https://github.com/Priivacy-ai/spec-kitty/issues/320`) rather than `#320`. Today the completeness gate can't see URL-form references, so a referenced issue is silently invisible, and discovery records no provenance. After this mission, same-repo URL references are recognized (cross-repo/prior-art URLs are ignored, so currently-green missions don't newly redden) and each reference carries its source file.

**Why this priority**: #1738 residual (URL-form + provenance). The multi-file scan shipped in #3076.

**Independent Test**: Put a same-repo GitHub issue URL in `spec.md`'s `**Input**` field (samuelgoff's exact v3.2.6 case, PDB #320) and run discovery; the reference is discovered, produces a matrix row, and records its source file.

**Acceptance Scenarios**:

1. **Given** a mission document citing a same-repo issue by full GitHub URL, **When** issue-reference discovery runs, **Then** the referenced issue is discovered exactly as a `#NNN` literal would be, and flows through the already-wired scaffold + completeness gate.
2. **Given** an unrelated / cross-repo / prior-art GitHub issue URL in prose, **When** discovery runs, **Then** it does **not** newly require an issue-matrix row (no false-positive gate regression).
3. **Given** references discovered across multiple documents, **When** results are inspected, **Then** each records the source file it was found in (a number appearing in N files yields provenance per the defined dedup rule).

### Edge Cases

- **Never-created vs deleted Target Ref (E2 disambiguation):** a *pre-consolidation* mission whose Target Ref was never materialized also has an absent branch; "branch absent" alone must NOT classify it as consolidated/published. Conjoin with terminal-completion evidence (see C-003).
- **Squash publish to trunk:** if E2 squash-merges, the E1 consolidation commit is not a commit-ancestor of the Primary Branch; the CONSOLIDATED E2 resolution must key on the mission's consolidated *content* being present on the checkout, not naive commit ancestry (design detail for the ADR/plan).
- **Pre-consolidation happy path:** an in-flight mission (Target Ref present, not yet consolidated) resolves as pre-consolidation and routing is unchanged from #3076 — no regression.
- **Well-formed-but-failing negative invariant:** reported as a failed invariant (verdict fail), distinct from a *malformed* one reported by the accept diagnostics.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Lifecycle-phase resolution (internal) | As an agent, I want the resolver to derive a mission's phase (pre-consolidation / consolidated / published-Target-Ref-deleted) internally from durable meta so writes route correctly without callers threading phase. | High | Open |
| FR-002 | CONSOLIDATED surface location wiring | As an agent, I want `SurfaceLocations.consolidated` populated so `TopologySurface.CONSOLIDATED` resolves to the integrated tree — the Target Ref tree while it exists (E1), the repository-root checkout on the Primary Branch once the Target Ref is deleted and the consolidated content is present (E2). | High | Open |
| FR-003 | Post-consolidation PRIMARY-kind write routing | As an agent, I want post-consolidation PRIMARY-kind writes to resolve through the CONSOLIDATED surface so `safe-commit` succeeds in E2 instead of failing against the deleted Target Ref (#3033 P0). | High | Open |
| FR-004 | Post-consolidation coord-kind write routing | As an agent, I want coord-partitioned writes (issue-matrix / tracer / acceptance-matrix) via the write seam to route through CONSOLIDATED in E2 and return committed instead of refused (#3033). | High | Open |
| FR-005 | No residue on refused write (seam thunk) | As an agent, I want the write seam to materialize a composed writer's staging file only after the routability probe passes, at a single seam-level locus, so a refused write leaves no untracked residue (#3073). | High | Open |
| FR-006 | Off-checkout refuse-with-recovery | As an operator, I want a post-consolidation write from a checkout that does not carry the mission's consolidated content to refuse with a recovery instruction naming what to check out, rather than force a checkout or write to the wrong place. | Medium | Open |
| FR-007 | Negative-invariant register | As an agent, I want to register an acceptance negative invariant through the deterministic `acceptance-verdict` command with the correct persisted shape, so I never hand-edit its JSON (#2318). | High | Open |
| FR-008 | Negative-invariant execute | As an agent, I want the registered negative invariant executed (its verification run) and its result recorded via the existing enforcement engine (#2318). | Medium | Open |
| FR-009 | Accept diagnostics hardening | As an agent, I want the accept diagnostics to report a malformed negative-invariant/criterion shape with its reason instead of crashing at load time (#2318, mgifford). | High | Open |
| FR-010 | Fresh persisted acceptance verdict | As an agent, I want canonical acceptance to persist a fresh `overall_verdict` (e.g. `pass` for an all-pass / no-negative-invariant matrix) rather than a stale `pending` (#2318, samuelgoff). | High | Open |
| FR-011 | Accept mission-step prompt drives the CLI | As an agent, I want the accept mission-step prompt to drive the accept pass through the acceptance CLI so the "zero hand-edited JSON" guarantee is operationalized (#2318). | Medium | Open |
| FR-012 | Same-repo GitHub-URL issue-reference recognition | As an author, I want issue-reference discovery to recognize full GitHub issue URLs pointing at **this repository** (not only `#NNN`), while ignoring cross-repo/prior-art URLs, so URL-cited issues are visible without reddening currently-green missions (#1738). | High | Open |
| FR-013 | Issue-reference source-file provenance | As an author, I want each discovered issue reference to record its source file (with a defined dedup rule that preserves provenance), inspectable via the persisted round-trip (#1738). | Medium | Open |
| FR-014 | Consolidate-terminology decision record | As a maintainer, I want the mission's ADR to establish `consolidate`/`consolidation` as the canonical term for the lane-consolidation (E1) sense (extending the CONSOLIDATED-wiring ADR), recording the "foundation now / full swap in #3080" split, so future work has a citable decision (#3080 foundation). | High | Open |
| FR-015 | Glossary canonicalization | As a maintainer, I want the glossary (`docs/context/orchestration.md`) to mark `consolidate` canonical for the lane-consolidation sense and the lane-consolidation sense of "merge" as a legacy alias with "do NOT use when" guards, so the canonical term is discoverable (#3080 foundation). | High | Open |
| FR-016 | Terminology drift-ratchet guard | As a maintainer, I want `tests/architectural/test_no_legacy_terminology.py` to fail on NEW lane-consolidation-sense uses of "merge" (a curated forbidden-phrasing ratchet scoped to not flag legitimate git-merge/publish uses), so the overload cannot get worse while the full rename (#3080) is pending. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Single write resolver preserved | Phase is derived **inside** `resolve_placement_only`, not threaded as a caller parameter and not a parallel/second resolver; the probe (`write_target`) and the materializer (`commit_for_mission`) derive the identical phase from the same durable signal (no split-brain). Coord-authority non-vacuity + write-side rederivation gates stay green. | Maintainability | High | Open |
| NFR-002 | Red-first regressions | Every behavioural change lands a failing-first regression through the pre-existing entry point; the #3033 P0 `safe-commit` test is authored and independently mergeable ahead of the fix. | Reliability | High | Open |
| NFR-003 | Clean gates | New code passes `ruff` and `mypy --strict` with zero issues; `tests/architectural/` stays green; no suppressions added. | Quality | High | Open |
| NFR-004 | Resolution overhead | Phase resolution adds only durable-meta reads on the write path and introduces **no** new git subprocess on the pre-consolidation happy path; the E2 content/ancestry probe runs only when the Target Ref is absent. | Performance | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Phase derived internally | Lifecycle-phase is derived inside the single write authority `resolve_placement_only`; no phase parameter threads through `PlacementSeam.write_target` or `commit_for_mission`; no second resolver (ADR 2026-06-24-1 C-006). | Technical | High | Open |
| C-002 | CONSOLIDATED is the vehicle | The fix WIRES `TopologySurface.CONSOLIDATED` (its first production wiring; `translate_surface` already has the total arm — populate `SurfaceLocations.consolidated`). It resolves the integrated tree by phase: Target Ref tree in E1, repository-root checkout on the Primary Branch in E2. It is NOT a ref-swap around CONSOLIDATED and introduces NO new `merge_target_branch` field. A new ADR documents this wiring, extends 2026-07-23-2, re-affirms C-006, and (FR-014) canonicalizes `consolidate` for the lane-consolidation sense. | Technical | High | Open |
| C-003 | E2 signal disambiguation | The "published / Target-Ref-deleted" (E2) signal is NOT "Target Ref absent" alone (cannot distinguish never-created from deleted). It conjoins Target-Ref-absence with terminal-completion evidence a consolidation produces (all WPs `done` in the status event log, and/or `mission_number` assigned) plus `baseline_merge_commit` present. The foundation reader `get_feature_target_branch` stays unrouted (no existence check added). | Technical | High | Open |
| C-004 | Off-checkout = refuse, not force | When the current checkout does not carry the mission's consolidated content, post-consolidation writes refuse-with-recovery; the mission never forces a git checkout. | Technical | Medium | Open |
| C-005 | Scope boundary + shared-resolver reconciliation | OUT of scope and code-untouched: emit.py placement-routing (#3071), move-task guard-unification (#2980/#2549), status-writer/reducer cluster (#2960/#3029). BUT `STATUS_STATE`/`DECISION_LOG` share `resolve_placement_only`, so their post-consolidation *resolution* shifts as a shared-resolver consequence (their writer code is unmodified). This is intended and must be verified non-regressive — NOT worked around with per-kind branching in the resolver (which would reintroduce the call-site kind-conditioning C-006 forbids). `DECISION_LOG` is in-mission and is intentionally not an E2 write target. | Business | High | Open |
| C-006 | Canonical P0 repro | The #3033 red-first repro is `spec-kitty safe-commit` on a classified PRIMARY artifact with a deleted Target Ref (E2), from the repository-root checkout; `spec-kitty review --mode post-merge` is the operator-facing *symptom* (it performs no commit). | Technical | Medium | Open |
| C-007 | Terminology discipline | The spec, ADR, and WP prompts name the `merge` sense everywhere (lane consolidation E1 / publish-to-trunk E2 / Target Ref = feature branch / Primary Branch = trunk / CONSOLIDATED surface). No bare "merge"/"target"/"post-merge". | Technical | High | Open |
| C-008 | Additive authoring; canonical surfaces | The negative-invariant work extends the existing `agent mission acceptance-verdict` command (no new command); the `NegativeInvariant` dataclass already carries the needed fields (NO acceptance-matrix schema migration). Accept diagnostics are hardened on the existing `accept --diagnose` load path. The accept-prompt edit lands in the doctrine SOURCE `src/doctrine/missions/mission-steps/` only (never the 12 generated agent copies; propagation is via `spec-kitty upgrade`). | Technical | Medium | Open |
| C-009 | Retrospective terminus stays fail-open | The retrospective terminus (`retrospective_terminus.py`, both `merge.py` and `teardown.py` call sites) fires at **E1** (lane consolidation — Target Ref still exists) and MUST stay fail-open (converting it to fail-closed after the merge already mutated state and deleted lane branches would produce a torn, unrecoverable merge). It is NOT changed by this mission; any genuine E2 retrospective write is covered by FR-003 as an ordinary PRIMARY-kind CONSOLIDATED write. | Technical | High | Open |
| C-010 | Hard sequencing | The terminology foundation (FR-014/015/016) is the **tidy-first enabler**, landed first — before Lane A functional work. Then: FR-001 (phase + CONSOLIDATED resolution) gates FR-003/004/006; FR-005 (no-residue seam thunk) lands with-or-before FR-003/004; the NFR-002 #3033 red test is the first *functional* WP, mergeable ahead of any fix WP. | Technical | High | Open |
| C-011 | Same-repo URL only; single regex | FR-012 widens the SINGLE canonical `detect_issue_references` pattern in place (no second matcher; there are already three issue-ref parsers) and recognizes only same-repo issue URLs; FR-013 adds `source_file` to the single `IssueReference` type and its `to_dict`/`from_dict` round-trip with a defined dedup rule. | Technical | Medium | Open |
| C-012 | Tidy-first #3080 foundation + boyscouting | This mission lands only the "do not make it worse" FOUNDATION of #3080 (ADR decision FR-014, glossary canonicalization FR-015, drift-ratchet guard FR-016) as a tidy-first enabler; the full command/code/docs rename stays #3080 (renaming `spec-kitty merge` / `MergeState` / `baseline_merge_commit` here would explode scope). BOYSCOUTING: when this mission touches code or docs that use "merge" in the lane-consolidation sense, disambiguate to the canonical term in NEW symbols, touched prose, and comments; leave existing public merge-named symbols (→ #3080) and the git-merge/publish senses unchanged. | Business | High | Open |

### Key Entities

- **LifecyclePhase**: pre-consolidation / consolidated (E1) / published-Target-Ref-deleted (E2); derived inside the resolver.
- **CONSOLIDATED surface / `SurfaceLocations.consolidated`**: the integrated-tree location this mission wires — Target Ref tree (E1) or repository-root checkout on the Primary Branch (E2).
- **baseline_merge_commit**: durable primary-meta field landed on the Target Ref at E1; anchors the E2 content/ancestry resolution and the phase signal.
- **WriteSeamResult**: committed / refused-with-recovery; extended to no-residue-on-refusal.
- **NegativeInvariant**: acceptance condition that must not hold; registered/executed via `acceptance-verdict` (dataclass fields already exist).
- **IssueReference**: discovered reference; extended with `source_file`; single canonical detector widened for same-repo URLs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On an E2 mission (consolidated, Target Ref deleted), `spec-kitty safe-commit` on a PRIMARY artifact from the repository-root checkout exits 0 with a clean tree — the #3033 red-first test flips from failing to passing.
- **SC-002**: E2 write-seam writes for issue-matrix, tracer, and acceptance-matrix kinds return a committed result on the CONSOLIDATED surface (0 `refused`) when the consolidated content is present.
- **SC-003**: A genuinely-unroutable refused write leaves 0 untracked files (clean `git status` in the regression).
- **SC-004**: A post-consolidation write from a checkout lacking the mission's consolidated content refuses with a branch-named recovery message, exits non-zero, and performs no checkout.
- **SC-005**: `STATUS_STATE`/`DECISION_LOG` post-consolidation resolution is verified non-regressive for the pre-consolidation happy path (shared-resolver consequence introduces 0 behaviour regressions).
- **SC-006**: An agent completes a full accept pass including a negative invariant with 0 hand-edited JSON files; a malformed invariant is reported by the accept diagnostics with 0 unhandled exceptions.
- **SC-007**: An all-pass / no-negative-invariant acceptance matrix persists `overall_verdict: pass` (not stale `pending`) — samuelgoff's fixture.
- **SC-008**: A same-repo GitHub issue URL in `spec.md`'s `**Input**` field (samuelgoff #320 fixture) is discovered and produces an issue-matrix row; an unrelated cross-repo GitHub URL in prose does NOT newly block the completeness gate; every discovered reference reports a non-empty source file.
- **SC-009**: `spec-kitty review --mode post-merge` on an E2 mission exits 0 end-to-end (the operator-facing symptom clears).
- **SC-010**: The glossary names `consolidate` as canonical for the lane-consolidation sense with a "do NOT use when" guard, and a new ADR records the decision plus the #3080 foundation/full-swap split.
- **SC-011**: The terminology drift-ratchet guard **fails** when a new lane-consolidation-sense "merge" phrasing is introduced (bite proven by a red-first fixture) and stays **green** on the existing grandfathered uses and on legitimate git-merge / publish-to-origin "merge" uses (no false-positive flood).

## Referenced Issues

- **#3033** (P0) — post-consolidation (E2) writes fail against a deleted Target Ref (FR-001/002/003/004/006; C-002/003/006).
- **#3073** — composed writers stage before the routability probe, leaving residue on refusal (FR-005).
- **#2318** — deterministic accept: negative-invariant register/execute (FR-007/008), diagnostics hardening (FR-009), fresh persisted verdict (FR-010), prompt wiring (FR-011); C-008.
- **#1738** — completeness gate misses same-repo URL references; no source-file provenance (FR-012/013; C-011).
- **#3080** (P0 feature) — make `consolidate` canonical for the lane-consolidation sense. This mission lands only the tidy-first FOUNDATION (ADR FR-014 + glossary FR-015 + drift-ratchet guard FR-016 + boyscouting C-012); the full command/code/docs rename remains #3080.
- Epics (do not close here): **#2160** coord-authority, **#1676** deterministic-authoring, **#3044** review-integrity.
