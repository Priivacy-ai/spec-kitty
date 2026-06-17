---
work_package_id: WP05
title: 'implement single-resolution + #1993 lanes-dir seam'
dependencies:
- WP01
requirement_refs:
- FR-008
- FR-011
tracker_refs: []
planning_base_branch: feat/read-path-error-fidelity
merge_target_branch: feat/read-path-error-fidelity
branch_strategy: Planning artifacts for this mission were generated on feat/read-path-error-fidelity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/read-path-error-fidelity unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
- T027
- T028
- T044
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2564771"
history:
- 2026-06-16 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/workflow.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_implement_single_resolution.py
- tests/specify_cli/lanes/test_resolve_lanes_dir.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/lanes/persistence.py
- src/specify_cli/workspace/context.py
- tests/specify_cli/cli/commands/agent/test_implement_single_resolution.py
- tests/specify_cli/lanes/test_resolve_lanes_dir.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before any code, load the implementer profile so your identity, governance scope, and
boundaries are active for this session:

```
/ad-hoc-profile-load python-pedro
```

Then read, in this order, so the behavior you implement matches the canonical intent:

- `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/spec.md` — FR-008, FR-011; the issue-matrix
  rows for **#1832** and the **#1993** co-dependency note ("MUST NOT land alone").
- `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/plan.md` — IC-05 (purpose, affected
  surfaces, risks), decision **D-1** (#1993 CARRY-minimal, #1716 DEFER), and the sequencing note
  (WP05 depends on WP01).
- `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/contracts/behavioral-contracts.md` —
  **C-IC05** (implement single resolution + #1993) is your acceptance contract.
- `research/live-repro.md` — context for the `agent action implement` "no workspace resolved" class
  (#1832).
- `research/call-site-inventory.md` — call-site **C14**, §8 "#1993 / #1716 sizing", and the §6
  line-number drift table (treat §6 as authoritative over any earlier cite).

## Objective

Two-part WP, both on the implement/workspace surface:

1. **FR-008 (#1832) — single resolution path.** `agent action implement WP##` MUST consume the
   claim's **already-resolved** context (the single resolution path) instead of re-resolving the
   workspace, eliminating the "no workspace could be resolved" failure on a verified read-path.
   Today `workflow.py:1341` and `:1377-1381` re-call `resolve_workspace_for_wp` after the claim
   (instead of consuming the claim's context), and `:1380` raises "no workspace could be resolved".
2. **#1993 (D-1 CARRY-minimal) — `resolve_lanes_dir` pure seam.** Extract a single pure seam
   `resolve_lanes_dir(feature_dir) -> Path` (≈6–10 LOC incl. docstring) in `lanes/persistence.py`
   and **route the 2–3 ad-hoc `feature_dir/lanes.json` derivations** (`lanes/persistence.py:43,:78`;
   `workspace/context.py:798`) through it. **#1993 MUST NOT land alone** — it rides here with #1832.

## Context

**C-001: adopt, do not build.** No new resolver/authority. #1832 is a **fragment-adopt** fix
(call-site-inventory C14): the workspace was already resolved when the claim created/reused it; the
implement path must **consume** that resolved context, not re-run resolution. The target branch is
already routed through the resolver at `workflow.py:969` — the residual is the post-claim
re-resolution at `:1341`/`:1377-1381`.

**#1993 is pure path composition (D-1, LOW risk).** No `resolve_lanes_dir` exists today (`grep` = 0
hits); the lanes dir is derived ad-hoc as `feature_dir / LANES_FILENAME` in `lanes/persistence.py`
(`:43`, `:78`) and `workspace/context.py` (`:798`). Extracting one named seam and routing all
derivations through it is the entire #1993 carry — **no topology semantics, no write-side change**
(#1716 is DEFERRED entirely per D-1). Owned by this WP alongside #1832 to satisfy the co-dependency
and keep the surface co-located (call-site-inventory §9 IC-E).

**Function-over-form + verification-by-deletion.** The proof of #1832 is that **removing the
re-resolution call** keeps implement green (C-IC05 deletion proof). The proof of #1993 is that the
ad-hoc joins are gone and exactly one derivation remains; deleting the inline joins keeps the suite
green.

**TDD-first (C-002).** Write the failing "no workspace could be resolved" test first (a verified
claim followed by implement), watch it fail for the real symptom, then make it pass by consuming the
claim's context. The seam gets a focused unit test.

**Topology-true fixtures (NFR-002 — binding).** Use production-shaped data only: full **26-char ULID**
`mission_id`, a **real coord worktree** and (where the resolution path is exercised) a real
`lanes.json`. No fabricated short ids, no synthetic single-repo stand-in for the workspace-resolution
path.

**Quality gates (NFR-004).** New/changed code passes `ruff` and `mypy` with zero issues, complexity
≤ 15, **no suppressions** (`workflow.py` is a 2737-LOC module — keep edits surgical). No
`# noqa`/`# type: ignore` additions.

## Subtasks

### T024 — TDD: implement consumes claim's resolved context (no "no workspace")
- Write `tests/specify_cli/cli/commands/agent/test_implement_single_resolution.py` (NEW).
- Build a topology-true fixture (full ULID, real coord worktree, `lanes.json` present): perform a
  successful **claim** of a WP, then invoke `agent action implement WP##`. Assert it succeeds and does
  **NOT** raise "no workspace could be resolved" (`workflow.py:1380`).
- Include a verified-read-path case (the claim resolved the workspace) so the test proves the
  single-resolution consumption, not a re-resolution that happens to succeed.
- **Validation:** test FAILS first on HEAD (re-resolution at `:1341`/`:1377-1381` raises "no workspace
  could be resolved" on a verified read-path).

### T025 — Route implement to single resolution path (workflow.py)
- In `agent action implement` (`workflow.py`): consume the **claim's already-resolved context**
  instead of re-calling `resolve_workspace_for_wp` at `:1341` and `:1377-1381`. The target branch is
  already routed via the resolver at `:969` — thread the resolved workspace/context from the claim
  through to implement (single resolution path).
- Remove the redundant re-resolution call that raises "no workspace could be resolved" at `:1380`
  (verification-by-deletion — the claim's context is the single authority).
- **Validation:** T024 passes; existing implement/review tests stay green.

### T026 — Extract resolve_lanes_dir(feature_dir) pure seam
- Add `resolve_lanes_dir(feature_dir: Path) -> Path` to `lanes/persistence.py` (≈6–10 LOC incl.
  docstring) — a **pure** composition returning the lanes dir/file path; no I/O, no topology logic.
- Use the existing `LANES_FILENAME` constant so the seam is the single place that knows the join.
- **Validation:** the function imports cleanly; `ruff`/`mypy` clean.

### T027 — Route ad-hoc lanes.json derivations through the seam
- Replace the 2–3 ad-hoc `feature_dir / LANES_FILENAME` (or `feature_dir / "lanes.json"`) derivations
  with calls to `resolve_lanes_dir(feature_dir)`:
  - `lanes/persistence.py:43`
  - `lanes/persistence.py:78`
  - `workspace/context.py:798`
- After this, **exactly one** derivation of the lanes dir remains (the seam) — verification-by-deletion
  of the ad-hoc joins.
- **Validation:** no remaining ad-hoc `feature_dir / ... lanes.json` join outside the seam (grep);
  existing lanes/workspace tests stay green.

### T028 — Unit test the seam + verification-by-deletion
- Write `tests/specify_cli/lanes/test_resolve_lanes_dir.py` (NEW): a focused unit test on
  `resolve_lanes_dir` (≈20 LOC) — given a `feature_dir`, it returns the expected lanes path; pure,
  deterministic, no fixtures beyond a `tmp_path` feature dir.
- Confirm (grep assertion or a code-shape test) that the ad-hoc joins are gone and all call-sites route
  through the seam.
- **Validation:** the seam test passes; the full lanes + implement suite is green.

### T044 — M4: decide explicitly on the `_find_first_for_review_wp` parent-walk re-deriver (IC-E)
- **M4 (SHOULD-FIX — do NOT silently drop; WP05 owns `workflow.py`).** `_find_first_for_review_wp`
  (`workflow.py:2030-2054`) re-derives `candidate_feature_dir_for_mission` by hand via a manual
  `current`-walk (`:2047-2054`) — a second authority on the review surface, distinct from the C14
  re-resolution at `:1341`/`:1377-1381`. WP05 MUST decide explicitly:
  - **Either** route `_find_first_for_review_wp` through the **resolved workspace/context** (consume the
    canonical surface instead of the manual parent-walk), so FR-011 "no per-command second authority"
    holds on the review surface too;
  - **OR** record a **CONSCIOUS DEFERRAL** note (here and in tasks.md) with rationale — lower blast
    radius (review-mode helper, not operator-facing fidelity) — so the disposition drift is intentional,
    not silent.
- **Validation:** whichever path is chosen is recorded explicitly; if routed, the review surface no
  longer re-derives the feature dir by manual walk and the implement/review suite stays green.

## Branch Strategy

Planning artifacts were generated on `feat/read-path-error-fidelity`. During
`/spec-kitty.implement` this WP may branch from a dependency-specific base (it depends on WP01), but
completed changes merge back into `feat/read-path-error-fidelity` unless the human explicitly
redirects the landing branch. Do not push to `origin/main`; the mission lands via PR.

## Definition of Done

- [ ] `/ad-hoc-profile-load python-pedro` invoked; spec/plan/contracts/research read.
- [ ] **T024–T025 (FR-008/#1832):** `agent action implement` consumes the claim's already-resolved
      context (single resolution path); the post-claim re-resolution at `workflow.py:1341`/`:1377-1381`
      is removed; "no workspace could be resolved" no longer fires on a verified read-path.
- [ ] **T026–T027 (#1993, D-1):** `resolve_lanes_dir(feature_dir)` extracted in `lanes/persistence.py`;
      the 2–3 ad-hoc `feature_dir/lanes.json` derivations (`persistence.py:43,:78`,
      `workspace/context.py:798`) routed through it; exactly one derivation remains.
- [ ] **T028:** focused unit test on the seam; grep/shape check confirms no ad-hoc join remains.
- [ ] **T044 (M4):** `_find_first_for_review_wp`'s parent-walk re-deriver (`workflow.py:2030-2054`,
      IC-E) is explicitly **either** routed through the resolved workspace/context **or** recorded as a
      conscious deferral with rationale — never silently left undecided.
- [ ] **#1993 does NOT land alone** — it rides with #1832 in this same WP (D-1 co-dependency satisfied).
- [ ] All new tests use topology-true fixtures (full 26-char ULID, real coord worktree, real `lanes.json`).
- [ ] The #1832 fix landed **test-first** and the test failed for the real symptom before the fix.
- [ ] **Verification-by-deletion:** removing the re-resolution call and the ad-hoc lanes joins keeps the
      suite green.
- [ ] `ruff` and `mypy` clean on changed code; complexity ≤ 15; no `# noqa`/`# type: ignore` added.
- [ ] Suite green (`PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_implement_single_resolution.py tests/specify_cli/lanes/ -n0 -q`).

## Risks / reviewer guidance

- **#1993 MUST NOT land alone** (the #2007 binding co-dependency). A reviewer must confirm both #1832
  and the lanes seam land in this one WP — splitting them violates D-1.
- **#1716 is DEFERRED entirely** (D-1). If any change reaches into write-side coord topology
  (`coordination/transaction.py`, `surface_resolver.py`, `workspace.py` write paths), that is scope
  creep — #1993 is **pure path composition only**.
- **#1832 is fragment-adopt, not re-resolution.** A reviewer should see the claim's context *consumed*,
  not a second `resolve_workspace_for_wp` call that happens to succeed — the deletion of the
  re-resolution is the proof (C-IC05).
- **Re-invoking implement on an `in_progress` WP is a no-op resume** (not re-gated) — do not regress
  that behavior when consolidating the resolution path.
- **Line numbers** are from HEAD `87697e5e4` per §6 (authoritative); re-locate by symbol after WP01.
- Consume WP01's frozen context; never re-derive `mission_id`/`mid8`/`target_branch` here (D-6).

## Activity Log

- 2026-06-16 — Prompt generated via /spec-kitty.tasks (IC-05; FR-008/FR-011; #1832 + #1993 carry-minimal; C14).
- 2026-06-16T21:03:49Z – claude:opus:python-pedro:implementer – shell_pid=2432976 – Assigned agent via action command
- 2026-06-16T21:24:05Z – claude:opus:python-pedro:implementer – shell_pid=2432976 – Ready: single-resolution + #1993 seam + M4 deferral; gates green
- 2026-06-16T21:24:57Z – claude:opus:reviewer-renata:reviewer – shell_pid=2564771 – Started review via action command
- 2026-06-16T21:37:04Z – user – shell_pid=2564771 – Single-resolution (FR-008/#1832): resolve_workspace_for_wp called once; consumed via _ensure_workspace_materialized; post-create/review re-resolution + 'no workspace could be resolved' removed; captured-red verified (lane-e path pinned). #1993 (D-1): resolve_lanes_dir pure seam; 3 owned joins routed, exactly one derivation remains; resolver.py:203 (not owned) untouched; #1716 deferred. M4/T044 conscious deferral recorded in-code + tasks.md:77. Stash integrity: commit 4f6fde52a = ONLY 5 owned files, NO decision.py leak, complete. Topology-true; ruff/mypy/C901 clean, no suppressions; 57 gate tests pass. test_wrapper_delegation 2 fails are PRE-EXISTING worktree-cwd artifact (identical on parent code), not WP05.
