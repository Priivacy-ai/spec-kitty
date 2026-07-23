# Implementation Plan: Trusted mission-artifact commit path

**Branch**: `remediation/coord-trust-2841` (coord topology) | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)
**Input**: Re-grounded spec (C-006) + pre-plan squad (paula/alphonso/pedro, convergent, code-cited on current main).

## Summary

Remediate the coordination-branch split-brain (#2841) and the review-claim actor leak (#2861) — one
commit/actor seam. The load-bearing prevention is write-in-home + the `safe_commit` HEAD==destination_ref
guard, making a wrong-partition write unrepresentable at commit. The pre-plan squad re-grounded the
stale-branch notes against current main and materially sharpened scope: the **modern** coord-commit path
is already correct; the real #2861 blocker is the **misroute-to-legacy** (`SafeCommitHeadMismatch`), not
the actor bug; the analysis-report sibling-coupling is dissolved by **re-homing `ANALYSIS_REPORT` →
PRIMARY** (operator decision); FR-004 is topology-conditional, not a delete.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: existing only — `typer`/`click` (CLI), `ruamel.yaml`, `spec_kitty_events` (event schema), the `safe_commit` git plumbing. No new third-party dependency.
**Storage**: git — coordination branch + primary/target branch, coord sub-worktree under `.worktrees/`, append-only `status.events.jsonl`, mission artifacts under `kitty-specs/<mission>/`.
**Testing**: `pytest`. Real-repo e2e via the existing un-stubbed harnesses (`tests/regression/test_issue_2508.py`, `tests/integration/coord_topology_fixture.py` — real `git worktree add`, `CliRunner` on `agent action`); unit tests per helper; a live red-first #2861 repro.
**Target Platform**: Linux / dev CLI (`spec-kitty`).
**Project Type**: single (CLI / mission toolchain).
**Performance Goals**: N/A — correctness/reliability mission, not latency.
**Constraints**: C-001 (partition structure unchanged; one authorized `ANALYSIS_REPORT` re-home), C-002 (C-007 provenance — no synthesized binding), C-003 (keep `doctor --fix` minimized), C-004 (own-`feature_dir` named allowlist), C-005 (staleness warn-first, FF-when-safe), C-006 (re-grounded — line numbers are current-main approximations, re-confirm at campsite), C-007 (#2803/#2853 out).
**Scale/Scope**: ~6 implementation concerns; touches `src/specify_cli/coordination/`, `src/specify_cli/cli/commands/agent/`, `src/specify_cli/status/`, `src/specify_cli/sync/`, `src/mission_runtime/artifacts.py`, `src/specify_cli/review/cycle.py`, `src/specify_cli/bulk_edit/`, `src/specify_cli/git/` (read-only guard), + tests.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority**: PASS — the placement port + coord-commit targeting collapse many ad-hoc write/copy sites into one write-in-home authority; `ANALYSIS_REPORT` gets one home (PRIMARY) that writer+gate+SSOT agree on.
- **Close defect classes by construction (DIRECTIVE_043)**: PASS — `safe_commit`'s worktree-HEAD==destination_ref + `.worktrees/` path-policy make a wrong-partition/misrouted write *unrepresentable* at commit, not discipline-reliant; the misroute-to-legacy fail-loud guard removes the last hole.
- **DDD + tiered rigour**: PASS — coordination/commit machinery is core (higher rigour: real-repo e2e, no stubbed `safe_commit`); the gate exemption + staleness detector are glue with focused tests.
- **ATDD-first**: PASS — NFR-001 real-repo e2e + NFR-002 live red-first #2861 repro precede the fixes; each FR maps to acceptance scenarios.
- **Canonical sources / no improvisation (DIRECTIVE_044)**: PASS — reuse `resolve_placement_only`/`kind_for_mission_file`/`CoordinationWorkspace.resolve`/`safe_commit`; reuse existing real-git test harnesses; do not fork parsers or partition logic.
- **Terminology adherence**: PASS — COORD/PRIMARY partition, coord worktree, Mission, placement port; no `feature*` aliases.
- **Complexity ceiling (≤15)**: enforced per touched function; the commit paths are already near the ceiling — extract helpers, do not inflate.

No unjustified charter violations. The one contract-membership change (`ANALYSIS_REPORT` re-home) is operator-authorized and keeps `assert_partition_invariant` green — recorded in Complexity Tracking as a deliberate, bounded exception.

## Project Structure

### Documentation (this mission)

```
kitty-specs/coord-commit-integrity-01KY5JS8/
├── plan.md              # This file
├── research.md          # Phase 0 — the re-grounded decisions (D-A..D-G)
├── data-model.md        # Phase 1 — artifact-kind partition table + actor payload shape
├── quickstart.md        # Phase 1 — how to run the real-repo e2e + the live #2861 repro
├── contracts/           # Phase 1 — commit-path contract + gate-exemption contract + doctor-staleness contract
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT here)
```

### Source Code (repository root)

```
src/mission_runtime/
└── artifacts.py                     # EDIT (D-C) — move ANALYSIS_REPORT COORD→PRIMARY (_PLACEMENT→_PRIMARY);
                                     #   assert_partition_invariant stays green.

src/specify_cli/coordination/
├── commit_router.py                 # EDIT (D-C/FR-003) — drop the shutil.copy2 residue factory (~:703)
│                                    #   for coord kinds; write-in-home.
├── transaction.py                   # READ/verify (D-A) — the modern path already threads the coord
│                                    #   worktree root; add regression coverage, no code change expected.
└── status_transition.py            # EDIT (D-E/FR-004) — conditionalize the primary-uncommitted fallback
                                     #   (~:924): coord topology → materialize/target coord worktree;
                                     #   PRESERVE the fallback for coord-less topologies.

src/specify_cli/cli/commands/agent/
├── workflow_executor.py             # EDIT (D-A/FR-002) — misroute-to-legacy fail-loud guard (~:217);
│                                    #   (D-F/FR-005) normalize --agent at the 3 build_resolved_actor seams.
├── workflow.py                      # EDIT (D-A/FR-002) — legacy-leaf porcelain pre-check (~:599, #2684)
│                                    #   run against the resolved worktree root, not repo_root.
├── tasks_move_task.py               # EDIT (D-F/FR-005) — normalize --agent at the move-task actor seam.
└── mission_record_analysis.py       # EDIT (D-C) — write analysis-report to its (now PRIMARY) home; drop
                                     #   the suppress-copy to coord.

src/specify_cli/status/
└── emit.py                          # EDIT (D-F/FR-005) — widen build_resolved_actor with self-asserted
                                     #   profile/model kwargs (no synthetic defaults, no fake binding).

src/specify_cli/sync/
└── emitter.py                       # EDIT (D-F/FR-006) — widen WPStatusChanged(:434)+WPCreated(:452)
                                     #   actor validators to Union[str,Dict] (SaaS-fanout fidelity).

src/specify_cli/review/
└── cycle.py                         # EDIT (D-D/FR-001) — retire kind-blind candidate_feature_dir_for_mission
                                     #   (~:272); write review-cycle into its PRIMARY home.

src/specify_cli/bulk_edit/
├── diff_check.py                    # EDIT (FR-007) — runtime-state exemption branch before the classifier.
└── gate.py                          # EDIT (FR-007) — thread the mission's own feature_dir + named allowlist.

src/specify_cli/cli/commands/_coordination_doctor.py  # EDIT (FR-008/009) — coord-vs-target staleness
                                     #   finding + `--check-staleness` mode + safe `--fix` fast-forward.

tests/                               # NEW — real-repo e2e (NFR-001), live #2861 repro (NFR-002),
                                     #   per-helper units, partition-invariant + gate-exemption regressions.
```

**Structure Decision**: single-project toolchain remediation. The commit/actor machinery
(`coordination/`, `agent/workflow*.py`, `status/emit.py`, `sync/emitter.py`) is the core high-rigour
surface; `bulk_edit/` and `_coordination_doctor.py` are lower-coupling glue. `git/commit_helpers.py`
(`safe_commit`) is the enforcement primitive — READ-ONLY here (it is already correct; we feed it the
right worktree root).

## Complexity Tracking

| Deviation | Why needed | Bounded by |
|-----------|------------|------------|
| `ANALYSIS_REPORT` partition-membership move (COORD→PRIMARY) — a contract-membership change under C-001 | The kind was mis-classified: its writer, freshness gate, and spec/plan/tasks siblings all live on PRIMARY, so "write-in-home" on COORD is structurally impossible (the coord worktree lacks the siblings the freshness hash needs). Re-homing makes writer+gate+SSOT agree and dissolves the FR-003 blocker. | Operator-signed-off; ONE kind only; `assert_partition_invariant` must stay green (disjoint-and-total); no read-surface asymmetry introduced. |

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Coord-commit correctness + the #2861 causation repro (URGENT-FIRST)

- **Purpose**: Close the real manual-review blocker. Establish (live) that the "commit refused" is the misroute-to-legacy, then make it unrepresentable.
- **Requirements**: FR-002, NFR-001, NFR-002; constraint C-006.
- **Affected surfaces**: `agent/workflow_executor.py` (misroute guard ~:217), `agent/workflow.py` (legacy porcelain pre-check ~:599 → resolved worktree root), `coordination/transaction.py` (modern path — regression only), the real-repo e2e + live-repro tests.
- **Sequencing/depends-on**: none (first). The NFR-002 live repro runs BEFORE finalizing FR-005/006 (D-B) — its verdict decides whether the actor work is on the blocker's path.
- **Risks**: a blanket "route everything to modern" could regress legitimately-legacy paths — prefer a fail-loud guard + fix the leaf. Real-repo e2e must not stub `safe_commit` (NFR-001).

### IC-02 — Write-in-home placement + analysis-report re-home

- **Purpose**: Retire wrong-partition authorship and the second-copy residue so no divergent copy exists.
- **Requirements**: FR-001, FR-003; constraints C-001 (the one re-home), C-006. References #2646/#2697/#2275 (review-cycle partition family), #2198 (arch-gate).
- **The re-home = ONE frozenset move (paula/randy CRITICAL)**: move `ANALYSIS_REPORT` `_PLACEMENT→_PRIMARY` in `mission_runtime/artifacts.py` ONLY. **KEEP `_COORD_RESIDUE_FILENAMES["analysis-report.md"]`** — it is the file→kind classifier (`kind_for_mission_file`), not a residue-only entry; deleting it mis-routes via the unrecognized-path fallback. ~9 residue delegators + `is_primary_artifact_kind` flip atomically. (Recommend renaming `_COORD_RESIDUE_FILENAMES`→`_MISSION_FILENAME_KINDS` to kill the naming-lie — randy.)
- **Mandatory co-changes (else CI red / silent reversal)**: (a) update `tests/architectural/test_write_surface_placement_guard.py` `PARTITION_RATIONALE[ANALYSIS_REPORT]` (partition + rationale text + anti-mutant expected ref, #2198); (b) INVERT — never run-to-green — the ~8 coord-pinning tests (`tests/coordination/test_commit_router.py:502` asserts "STILL routes to coordination" = a #2463 flip-test landmine; `test_partition_authority_characterization.py:61`, `test_merge_residue_gate_single_authority_wp13.py:307`, `test_record_analysis_placement.py:80`, `test_acceptance.py:179` → invert; `test_wp05_mission_coordination_routing.py:96`, `test_protected_primary_spec_commit.py:205/368/414` → swap the coord-exemplar to `ACCEPTANCE_MATRIX`/`ISSUE_MATRIX`, don't delete); (c) rewrite the now-false comment at `mission_record_analysis.py:~336-340`.
- **FR-001 review-cycle — enumerate ALL write sites (priti)**: `review/cycle.py:~272` is only ONE; also cover the move-task `--review-feedback-file` rejection path (#2697) and verify `post_merge/review_artifact_consistency.py`'s caller-supplied `feature_dir` resolves PRIMARY post-re-home (#2275/#2646). Extract one `_review_cycle_wp_dir` so read (`cycle.py:~193`) + write converge (randy). Contingent-close #2646/#2697/#2275 only if each repro retests green.
- **FR-003 residue-drop — narrow scope (paula)**: drop ONLY the analysis-report path of the `shutil.copy2` at `coordination/commit_router.py:~703` (`:700-705`); KEEP the `.worktrees` bypass (`:691-699`) and status-skip (`:688`). Acceptance-matrix + issue-matrix stay COORD (verified: they write-in-coord-home via the bypass, no sibling coupling). Add a regression enumerating every `commit_for_mission` coord-kind caller proving write-in-coord-home BEFORE removing the copy (else "silently copied" → "silently missing").
- **Verify at campsite**: 3 direct-path analysis-report readers (`retrospective/generator.py`, `dossier/indexer.py`, `sync/body_upload.py`) receive the PRIMARY dir post-re-home.
- **Sequencing/depends-on**: independent of IC-01 (ref-projection vs worktree-root-projection); co-land.
- **Risks**: `assert_partition_invariant` must stay green; the flip-test landmine (run-to-green reverses the re-home) is the biggest trap — invert deliberately.

### IC-03 — Single status write-authority (topology-conditional)

- **Purpose**: For coord topology, a status event commits to the coord worktree; preserve the correct primary write for coord-less topologies.
- **Requirements**: FR-004; constraint C-006.
- **Affected surfaces**: `coordination/status_transition.py` (~:924 conditionalize the `_transaction_topology_available` False arm).
- **Sequencing/depends-on**: same commit machinery as IC-01 — co-land; verify no double-fix overlap with IC-01's targeting.
- **Risks**: a blanket delete regresses SINGLE_BRANCH/LANES/flat missions — MUST preserve the fallback for coord-less topologies (regression test both).

### IC-04 — Actor identity on the emit seam (#2861 correctness + fidelity)

- **Purpose**: A manually-orchestrated claim records a valid, parsed actor; the SaaS fanout stops rejecting dict actors.
- **Requirements**: FR-005, FR-006; constraints C-002/C-007.
- **Affected surfaces**: `status/emit.py` (widen `build_resolved_actor` with self-asserted profile/model), `agent/workflow_executor.py` + `tasks_move_task.py` (normalize `--agent` at the 3 seams, no synthetic defaults), `sync/emitter.py` (WPStatusChanged/WPCreated dict validators).
- **Sequencing/depends-on**: after IC-01's NFR-002 verdict (D-B) — this is actor correctness + fanout fidelity, NOT the commit blocker; do not over-claim it unblocks US2 AC-3 unless the repro says so.
- **Risks**: reusing the frontmatter parser's synthetic defaults would fabricate `unknown-model`/`{tool}-default` on the actor — must NOT; keep existing `test_resolved_binding_linkage` / `test_saas_resolved_binding_fanout` green.

### IC-05 — Runtime-state gate exemption (Symptom B)

- **Purpose**: The diff-compliance gate never blocks the mission's own runtime state; no `occurrence_map` exception.
- **Requirements**: FR-007; constraint C-004.
- **Affected surfaces**: `bulk_edit/diff_check.py` (exemption branch before the classifier), `bulk_edit/gate.py` (thread own `feature_dir` + named allowlist).
- **Sequencing/depends-on**: independent — parallel.
- **Risks**: over-broad exemption slips real surface past review — anchor to the running mission's OWN feature_dir + NAMED allowlist; regression: a non-runtime file (and another mission's runtime file) under the same tree still classifies.

### IC-06 — Coord staleness signal + safe resync

- **Purpose**: Surface coord-vs-target staleness non-blockingly; fast-forward only when unambiguously safe.
- **Requirements**: FR-008, FR-009; constraints C-003 (keep `--fix` minimized), C-005.
- **Affected surfaces**: `cli/commands/_coordination_doctor.py` (staleness finding + `--check-staleness` + safe `--fix` FF — extract `_fast_forward_finding`/`_is_ff_candidate` from the near-dup `_coord_worktree_stale_finding:~312-359`; C-005 warn-first falls out for free), the `finalize-tasks` seam (non-blocking WARN).
- **Sequencing/depends-on**: independent — parallel.
- **Risks**: growing `--fix` into a general repair command (C-003 forbids); auto-mutation on divergence (C-005 forbids — fail loud with diff).

## Lane ownership & sequencing (post-plan squad)

- **IC-01 + IC-04 share `agent/workflow_executor.py`** (disjoint functions: commit routing vs actor seams). They MUST be the **same lane, sequential WPs (IC-01 → IC-04)** — never parallel lanes (a parallel edit collides at merge). D-B already sequences IC-04 after IC-01's NFR-002 verdict.
- **IC-01 (misroute guard) and IC-03 (`status_transition.py`) share the "resolve+target the coord worktree" operation** — both MUST draw from the ONE existing authority `CoordinationWorkspace.resolve` (already used at `commit_router.py:~620`); one WP owns any shared helper. Do NOT merge IC-01/03/04 into a single WP (three files, three concerns) — co-lane and sequence.
- IC-02, IC-05, IC-06 are independent seams → parallel lanes.

## Campsite (per-IC, in-diff — randy, extreme-boyscout)

Fold these into the owning IC's WP (SAFE/ADJACENT); they also buy complexity headroom before the edits push functions over the ≤15 ceiling:

- **IC-04**: collapse the `sync/emitter.py` actor validators (`:434`+`:452`) + the `_is_proof_actor`↔`_is_actor_payload` clone into one `_is_actor_field`; dedup the 3 `try/materialize/except` blocks in `emit.py`. `build_resolved_actor:1077` stays trivial (no fabricated defaults).
- **IC-01**: extract `_handle_commit_failure` from the two copy-paste rollback+`_record_receipt("refused")` arms in `workflow_executor.py:~140` before adding the misroute guard; delete the dead triplicate `workflow.py:672 _resolve_git_common_dir` + its stale test; add a workspace preflight helper before the guard tips `implement`/`review` over 15.
- **IC-02**: dedup the 5 json/console error branches + narrow the two blanket `suppress(Exception)` (`mission_record_analysis.py:324/344`) — keeps `record_analysis:206` (C14) under 15 and removes paula's error-masking.
- **IC-03**: extract one `_emit_via_non_transactional_fallback` so both `emit_status_transition_transactional:924` AND `emit_status_transition_batch_transactional:1028` (C25) conditionalize once — do NOT branch-in-place.
- **IC-05**: extract `_glob_match` (dup `_path_matches`/`_exception_for`) + `_is_bulk_edit_mission`; keep the named-allowlist filter a pure testable `_filter_allowlisted`.
- **IC-06**: hoist the 7× function-local `import subprocess`; extract `_resolve_coord_short`.

**Complexity ceiling — do NOT inflate (OUT / separate degod)**: `emit.py:495` (C32) / `:789` (C44), `commit_router.py:210` (C18), `workflow_executor.py:845` (C18). The dead near-dup `commit_router.py:765 _resolve_commit_worktree_for_kind` is the biggest structural prize but is **WP09-shim-sweep-owned** — OUT (collapsing it here would trade an arch-invariant test for a reduction).

## Deferrals (file/track, do NOT scope-creep)

- `traces/` partition classification — no GitHub issue exists yet; file one at `/tasks` time (the placement port safely ignores it — no crash — so it is a genuine follow-up, not a blocker).
- If the issue-matrix/acceptance-matrix "verify no sibling coupling" surfaces a real coupling needing code beyond the analysis-report pattern, spin a new deferred issue rather than growing IC-02.
