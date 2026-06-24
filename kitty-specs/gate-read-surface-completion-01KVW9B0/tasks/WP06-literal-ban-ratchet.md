---
work_package_id: WP06
title: Literal-ban architectural ratchet for gate-command planning reads
dependencies:
- WP00
- WP01
- WP02
- WP03
- WP04
- WP05
requirement_refs:
- FR-009
- FR-010
tracker_refs:
- '#2107'
planning_base_branch: feat/gate-read-surface-completion
merge_target_branch: feat/gate-read-surface-completion
branch_strategy: Planning artifacts for this mission were generated on feat/gate-read-surface-completion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/gate-read-surface-completion unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
phase: Phase 1 - Gate-read spine (Lane A) - ratchet
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "4136073"
history:
- at: '2026-06-24T08:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_gate_read_literal_ban.py
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_gate_read_literal_ban.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Literal-ban architectural ratchet

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: tests/architectural/`.

---

## Objective

Add an **architectural literal-ban ratchet** (FR-010) that makes FR-004 enforceable on BOTH
arms:
1. **Read arm:** no gate-command entry function may directly join
   `<feature_dir>/{spec,plan,tasks,research,data-model}.md` or resolve a planning-artifact
   read through a topology-routed resolver.
2. **Write arm (paula post-tasks remediation):** no gate command may resolve a
   planning-artifact **COMMIT / branch** to the repo primary `main` outside the kind-aware
   write seam — i.e. a write-branch resolution anchored to `candidate_feature_dir_for_mission`
   (→ coord → fallback `main`) instead of `primary_feature_dir_for_mission`. This covers
   **WP00's territory** so the write twin (FR-009(e), the finalize-tasks commit) cannot
   silently regress. Without it, FR-009(e) is documentation, not a gate.

Without this ratchet, FR-004/FR-009(e) are documentation and a future command silently
re-reads coord or re-commits to `main` (research Decision 5 — the highest-leverage item).

This WP **ratchets the consolidated state** WP00–WP05 produced — it runs LAST in Lane A.

## Context & Constraints

Ground truth — read before editing:
- [spec.md](../spec.md) FR-010; C-005.
- [plan.md](../plan.md) IC-07.
- [contracts/gate-read-seam.md](../contracts/gate-read-seam.md) the Ratchet contract — it
  defines exactly what MUST fail and what is allowed.
- [research.md](../research.md) Decision 5 (the ratchet makes FR-004 enforceable).

**The ratchet MUST fail if any gate-command entry function:**
- (read arm) directly joins `<feature_dir>/{spec,plan,tasks,research,data-model}.md`, OR
- (read arm) resolves a planning-artifact read through `resolve_handle_to_read_path` /
  `_find_feature_directory` / `resolve_feature_dir_for_mission` (topology-routed), OR
- (**write arm**) resolves a planning-artifact **COMMIT / branch** by anchoring its
  `meta.json` lookup to `candidate_feature_dir_for_mission` (→ coord → fallback repo primary
  `main`) instead of `primary_feature_dir_for_mission` / the kind-aware write seam. Scope the
  write-arm scan to the write-branch resolvers `get_feature_target_branch` (`paths.py`),
  `resolve_target_branch` (`git_ops.py`), and the finalize-tasks commit-branch resolution
  (`mission.py`) — the sites WP00 fixes.

**Allowed (NOT flagged):**
- the seam itself (`resolve_planning_read_dir`, `_planning_read_dir` chokepoint),
- the write seam (`primary_feature_dir_for_mission` / `resolve_merge_target_branch`),
- STATUS reads off `status_feature_dir` (`status.events.jsonl`, acceptance-matrix),
- STATUS/coord commit destinations (status events emit to coord — C-002/C-003),
- the self-bookkeeping allowlist (`meta.json`, provenance),
- already-primary KEEP sites (`check-prerequisites`, `finalize-tasks` verify,
  record-analysis WRITE),
- genuine topology-aware reads that legitimately need `candidate_feature_dir_for_mission`
  (status surfaces) — the write-arm scan flags ONLY a write-BRANCH resolution.

Reference for an existing architectural ratchet pattern: look at the
write-side mission's literal-ban / partition ratchet (mission write-surface-coherence,
`tests/architectural/`) and the existing `tests/architectural/` AST-scan helpers — REUSE the
canonical AST-scan utility, do NOT hand-roll a regex if a shared helper exists.

## Branch Strategy

- **Strategy**: `shared-lane` (Lane A; `tests/architectural/` exclusive)
- **Planning base branch**: `feat/gate-read-surface-completion`
- **Merge target branch**: `feat/gate-read-surface-completion`

> WP06 OWNS `tests/architectural/test_gate_read_literal_ban.py` exclusively. It depends on
> **WP00** (write arm — the write-branch re-point) and ALL Lane-A WPs (WP01–05, read arm) so
> the ratchet asserts the fully consolidated read+write state — it would fail if run before
> the re-points land.

## Subtasks & Detailed Guidance

### Subtask T022 – Build the literal-ban AST/source scan

- **Purpose**: Detect direct planning-artifact path joins in gate-command entry functions.
- **Files**: new `tests/architectural/test_gate_read_literal_ban.py`.
- **Steps**:
  1. Enumerate the gate-command entry modules/functions: `setup_plan`, the accept cluster
     (`acceptance/__init__.py`), `map_requirements`, `record_analysis`, plus the chokepoint
     module. Scope the scan to these (a precise allowlist of files/functions), NOT the whole
     codebase (avoids false positives on status paths).
  2. Use an AST scan (reuse the canonical `tests/architectural/` AST helper if present):
     flag a `BinOp`/`Call` that joins a `feature_dir`-like path with a literal
     `"spec.md"`/`"plan.md"`/`"tasks.md"`/`"research.md"`/`"data-model.md"` outside the seam.
  3. Flag a call to `resolve_handle_to_read_path` / `_find_feature_directory` /
     `resolve_feature_dir_for_mission` whose result feeds a planning-artifact read in a gate
     entry function.
  4. **Write arm (paula remediation):** add a scan over the write-branch resolvers
     (`get_feature_target_branch` in `paths.py`, `resolve_target_branch` in `git_ops.py`,
     the finalize-tasks commit-branch resolution in `mission.py`) that FLAGS a `meta.json`
     lookup anchored to `candidate_feature_dir_for_mission` (the WP00 bug shape). Assert
     these resolve via `primary_feature_dir_for_mission` / the kind-aware write seam. This
     fences WP00's fix so the finalize-tasks commit twin cannot regress to `main`.
- **Notes**: Precision over recall here — a false positive on a STATUS path would block
  legitimate code. Explicitly allow `status_feature_dir` joins, the read seam, the write seam
  (`primary_feature_dir_for_mission`), and genuine topology-aware STATUS reads. The write-arm
  scan flags ONLY a write-BRANCH resolution anchored to the candidate dir, not every
  `candidate_feature_dir_for_mission` use.

### Subtask T023 – Assert the consolidated state is clean (GREEN) + allow-list the KEEPs

- **Purpose**: The ratchet passes on the post-WP01-05 tree and explicitly permits the KEEPs.
- **Files**: `tests/architectural/test_gate_read_literal_ban.py`.
- **Steps**:
  1. Run BOTH scans (read arm + write arm) over the enumerated surfaces; assert ZERO
     violations (the consolidated post-WP00–WP05 state — the write arm passes because WP00
     re-pointed the write-branch resolvers).
  2. Encode the allowed set: the read seam, the write seam (`primary_feature_dir_for_mission`),
     `status_feature_dir` STATUS reads, STATUS/coord commit destinations, the self-bookkeeping
     allowlist, and the already-primary KEEP sites — each with a comment citing
     data-model.md / contract so a future maintainer understands why it is exempt.
  3. If the scan finds a residual, FAIL with a message naming the file:function:line and the
     seam to route through (anti-"fixed N of M" — the ratchet itself enumerates).

### Subtask T024 – Anti-mutant proof: MANDATORY synthetic-AST self-test → RED

> **Remediation (reviewer-renata post-tasks):** a manual recorded mutation proof is NOT a
> gate — it rots and cannot be re-run, which is exactly the friction-test smell
> DIRECTIVE_041 rejects. The synthetic-AST self-test is **MANDATORY, not "if feasible"** —
> the ratchet's non-vacuity MUST be a runnable assertion, not a log entry.

- **Purpose**: Prove the ratchet (both arms) is non-vacuous via a runnable self-test.
- **Files**: `tests/architectural/test_gate_read_literal_ban.py`.
- **Steps**:
  1. **MANDATORY — read arm self-test:** feed the scanner a synthetic violating AST snippet
     (a `feature_dir / "spec.md"` join AND a topology-routed planning read) as a string;
     assert the scanner FLAGS each. Feed a clean snippet (via the seam); assert it PASSES.
  2. **MANDATORY — write arm self-test:** feed the scanner a synthetic snippet that resolves
     a write-branch `meta.json` via `candidate_feature_dir_for_mission`; assert it FLAGS.
     Feed a snippet anchored to `primary_feature_dir_for_mission`; assert it PASSES.
  3. **Pin the enumerated file/function set** in the test (read-arm gate surfaces + the three
     write-branch resolvers) so adding a NEW gate command (or write-branch resolver) without
     adding it to the scan set FAILS the test. (A ratchet that silently skips a new surface is
     vacuous.)
  4. (Belt-and-braces, optional) also record a one-off production-mutation proof in the log —
     but the runnable synthetic self-tests above are the gate, not the log entry.

## Test Strategy

- `pytest tests/architectural/test_gate_read_literal_ban.py -q`.
- The mutation proof (re-introduce a violation → RED) recorded as evidence.
- `ruff check tests/architectural/test_gate_read_literal_ban.py` + `mypy` — zero issues,
  no suppressions.

## Definition of Done

- [ ] **Read arm**: ratchet scans the enumerated gate-command surfaces for direct
  `<dir>/{spec,plan,tasks,research,data-model}.md` joins and topology-routed planning reads.
- [ ] **Write arm**: ratchet flags a write-branch `meta.json` resolution anchored to
  `candidate_feature_dir_for_mission` (→ `main`) in `get_feature_target_branch` /
  `resolve_target_branch` / the finalize-tasks commit — covering WP00's territory so the
  write twin (FR-009(e)) cannot regress.
- [ ] Ratchet GREEN on the consolidated post-WP00–WP05 tree (both arms).
- [ ] KEEP sites (read seam, write seam, status reads, status/coord commit destinations,
  self-bookkeeping allowlist, already-primary verify) explicitly allowed with cited rationale.
- [ ] **MANDATORY synthetic-AST self-test** (NOT "if feasible"): read-arm AND write-arm
  violating snippets are FLAGGED, clean snippets PASS, and the enumerated surface/resolver set
  is pinned so a new un-scanned surface FAILS. Non-vacuity is a runnable assertion, not a log.
- [ ] Scan scoped precisely (no false positives on STATUS paths or genuine topology reads).
- [ ] ruff + mypy clean; no suppressions.

## Risks & Mitigations

- **False positives on STATUS paths**: Mitigation: scope to gate-command entry functions;
  explicitly allow `status_feature_dir` and the seam.
- **Vacuous ratchet**: Mitigation: T024 mutation proof.
- **Hand-rolled brittle regex**: Mitigation: reuse the canonical `tests/architectural/` AST
  helper.

## Review Guidance

- Confirm the ratchet is non-vacuous via the **MANDATORY runnable synthetic-AST self-test**
  (read arm AND write arm) — reject a "recorded manual proof" as the sole non-vacuity
  evidence (it rots; DIRECTIVE_041).
- Confirm the **write arm** flags a `candidate_feature_dir_for_mission` write-branch
  resolution (the WP00 bug shape) and passes the `primary_feature_dir_for_mission` form —
  so the finalize-tasks commit twin (FR-009(e)) cannot regress to `main`.
- Confirm the allowed set explicitly permits STATUS reads + the read/write seams +
  self-bookkeeping + already-primary KEEPs + status/coord commit destinations (a ratchet
  that flags those is wrong).
- Confirm the enumerated surface/resolver set is pinned (a new un-scanned gate command or
  write-branch resolver FAILS the test).
- Confirm the scan is scoped to gate-command + write-branch surfaces, not the whole codebase.

## Activity Log

- 2026-06-24T08:00:00Z – system – Prompt created.
- 2026-06-24T16:28:54Z – user – Direct-on-feat (allocator bypassed)
- 2026-06-24T16:28:56Z – user – Implementing ratchet directly on feat
- 2026-06-24T16:40:59Z – claude – WP06 ratchet 09257ce45 on feat; caught+restored dropped WP02; status from main
- 2026-06-24T16:41:00Z – claude:opus:reviewer-renata:reviewer – shell_pid=4136073 – Started review via action command
- 2026-06-24T16:44:53Z – user – shell_pid=4136073 – Review passed: FR-010 literal-ban ratchet approved. Both arms verified non-vacuous via INDEPENDENT mutation run (reviewer-renata): READ arm flags topology-routed planning joins (handle/find/resolve_feature_dir) + WRITE arm flags candidate-anchored meta.json (one-hop+two-hop), clean seam/primary snippets PASS. Precision confirmed: coord/candidate dir used only for STATUS join is NOT flagged; named-const joins not flagged. Green is EARNED not vacuous: setup_plan/record_analysis/collect_feature_summary DO bind topology-routed dirs but route planning reads through the seam; all 3 write resolvers anchor primary. Pin test live. 8/8 ratchet tests + 4/4 WP02 behavioral tests pass. WP02 restoration byte-faithful to approved lane-c form (product code identical bar 2 explanatory comment lines; test byte-identical). ruff clean; mypy 3 pre-existing baseline (lines 1033/2671/4210, outside diff, present on parent).
