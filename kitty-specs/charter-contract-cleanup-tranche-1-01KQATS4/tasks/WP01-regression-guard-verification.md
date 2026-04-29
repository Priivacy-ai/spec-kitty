---
work_package_id: WP01
title: Regression-guard verification (verify-only baseline)
dependencies: []
requirement_refs:
- FR-009
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
created_at: '2026-04-28T20:35:00Z'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Verification baseline
agent: "claude:opus-4-7:researcher-robbie:researcher"
shell_pid: "27620"
history:
- timestamp: '2026-04-28T20:35:00Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: researcher-robbie
authoritative_surface: kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/research/
execution_mode: planning_artifact
owned_files:
- kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/research/verification-evidence.md
role: researcher
tags: []
---

# WP01 — Regression-guard verification (verify-only baseline)

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load the agent profile:

```
/ad-hoc-profile-load researcher-robbie
```

The profile assigns the **researcher** role: investigate, reproduce, document — do **not** modify production code. If the verification step you are about to run finds an actual regression, escalate it via the evidence file you author in T004; do not silently fix it as part of this WP.

---

## Branch Strategy

- **Planning/base branch:** `main`
- **Final merge target:** `main`
- Execution worktrees are allocated per computed lane in `lanes.json` after `finalize-tasks`. This WP runs in the lane that owns the mission's `kitty-specs/.../research/` directory.
- Implementation command: `spec-kitty agent action implement WP01 --agent <name>`

## Objective

Establish — *with evidence* — that the FR-009 and FR-010 verify-only items in [`spec.md`](../spec.md) are intact on this feature branch *before* any of the production-code work in WP02/WP03/WP04 lands. Per spec constraint **C-003**, none of those items are rewritten unless verification observes an actual regression.

The deliverable is a single evidence file:

`kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/research/verification-evidence.md`

## Context

[`spec.md`](../spec.md) FR-009 and FR-010 list a set of regression guards the brief explicitly classifies as "already fixed; verify, do not re-implement." They cover: the retrospective gate's pre-terminal placement (`runtime_bridge.py`); rollback-no-completion-event behaviour (real sync emitter); uppercase/mixed-case contract IDs in `retrospective/schema.py`; the real-bridge rollback test in `tests/next/test_retrospective_terminus_wiring.py`; the golden-path's call to `charter synthesize --json` against the real synthesizer (no hand-seeded `.kittify/doctrine`); the `_parse_first_json_object` strict-JSON parsing helper; and the `_run_next_and_assert_lifecycle` lifecycle-trail hard-fail.

[`research.md`](../research.md) §R-007 documents the verify-only protocol. [`quickstart.md`](../quickstart.md) §1 (block 3) names the test invocation.

**FRs covered:** FR-009, FR-010 · **NFRs:** NFR-002 (no regressions) · **Constraints:** C-003

## Always-true rules

- This WP authors **one evidence file**. It does not modify any production code, any test code, or any helper.
- If a verification step fails, the failing item is recorded in the evidence file with a Go/No-Go verdict; the failure is escalated as new in-scope work (per C-003) rather than silently fixed in this WP.
- All test runs that touch hosted auth/sync/tracker surfaces use `SPEC_KITTY_ENABLE_SAAS_SYNC=1` (machine rule). The regression-guard set listed below does **not** touch those surfaces, so the env var is not required for the runs in T001.

---

## Subtask T001 — Run regression-guard test suite + capture per-test evidence

**Purpose:** Get a green/red signal on every guard the spec enumerates.

**Steps:**

1. From the repo root checkout (or the implementation worktree if one exists for this WP), run:
   ```bash
   uv run pytest \
     tests/next/test_retrospective_terminus_wiring.py \
     tests/retrospective/test_gate_decision.py \
     tests/doctrine_synthesizer/test_path_traversal_rejection.py \
     -q --tb=short
   ```
2. Capture the full terminal output (a copy under `kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/research/_artifacts/regression-guard-output.txt` is fine; create the `_artifacts/` directory if needed — it is allowed under this WP's authoritative surface).
3. Record per-test PASS/FAIL.

**Acceptance:**

- Terminal output captured and reproducible.
- Per-test PASS/FAIL list authored.

---

## Subtask T002 — Inspect `runtime_bridge.py` and `retrospective/schema.py` invariants  [P]

**Purpose:** Confirm the source-level invariants the spec calls out are still present in current code.

**Steps:**

1. Read `src/specify_cli/next/runtime_bridge.py`. Confirm the retrospective gate runs *before* terminal completion (or via a buffered emitter that cannot retract). Cite line numbers.
2. Read `src/charter/retrospective/schema.py`. Confirm:
   - It accepts uppercase/mixed-case contract IDs such as `DIRECTIVE_NEW_EXAMPLE` and `PROJECT_001`.
   - It still rejects path-traversal patterns (e.g. `../etc/passwd`, embedded `..`).
   - Cite the regex / validator and line numbers.
3. If the file structure has shifted since the brief was written and the location is different, search via `rg -n "schema|validator|retrospective" src/charter/` and reconcile.

**Acceptance:**

- Evidence file lists the file paths, line numbers, and a one-sentence quote per invariant confirming presence.

---

## Subtask T003 — Inspect golden-path helpers + synthesizer-call path  [P]

**Purpose:** Confirm three FR-010 invariants visible only in test code.

**Steps:**

1. Read `tests/e2e/test_charter_epic_golden_path.py`. Cite line numbers for:
   - `_parse_first_json_object`: it must call `json.loads(stdout)` over the full stdout (no regex pre-extraction; no first-`{` slicing).
   - `_run_next_and_assert_lifecycle`: it must hard-fail when the lifecycle log file is absent (no permissive return / no warning-only branch).
   - The `charter synthesize --json` invocation in the golden-path setup: it must run against the real synthesizer (not seed `.kittify/doctrine` from a fixture).
2. If any invariant is **not** present (e.g. someone weakened it in a recent commit), record the discrepancy with the offending lines and proposed disposition (escalate to mission-scope per C-003).

**Acceptance:**

- Evidence file documents PASS or FAIL for each of the three FR-010 invariants with file path + line number + short quote.

---

## Subtask T004 — Author `verification-evidence.md` with results and disposition

**Purpose:** Single deliverable for this WP. Reviewers and downstream WPs read it before starting their work.

**Steps:**

1. Create `kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/research/verification-evidence.md` with these sections:

   ```markdown
   # WP01 — Verification Evidence

   **Run on branch:** <branch-name>
   **Run at (UTC):** <iso-timestamp>
   **Operator:** <agent / human label>

   ## T001 — Regression-guard test results

   | Test file | Outcome | Notes |
   |---|---|---|
   | tests/next/test_retrospective_terminus_wiring.py | PASS / FAIL | … |
   | tests/retrospective/test_gate_decision.py | PASS / FAIL | … |
   | tests/doctrine_synthesizer/test_path_traversal_rejection.py | PASS / FAIL | … |

   Terminal evidence at `_artifacts/regression-guard-output.txt`.

   ## T002 — `runtime_bridge.py` + `retrospective/schema.py` invariants

   - Retrospective gate placement: PASS — `src/specify_cli/next/runtime_bridge.py:<line>` …
   - Mixed-case ID acceptance: PASS — `src/charter/retrospective/schema.py:<line>` …
   - Path-traversal rejection: PASS — `src/charter/retrospective/schema.py:<line>` …

   ## T003 — Golden-path helper invariants

   - `_parse_first_json_object` uses `json.loads(stdout)`: PASS — `tests/e2e/test_charter_epic_golden_path.py:<line>` …
   - `_run_next_and_assert_lifecycle` hard-fails on missing trail: PASS — `tests/e2e/test_charter_epic_golden_path.py:<line>` …
   - Real-synthesizer call (no `.kittify/doctrine` seeding): PASS — `tests/e2e/test_charter_epic_golden_path.py:<line>` …

   ## Disposition

   **Verdict:** GO  (or NO-GO, with a list of escalated items)

   FR-009: VERIFIED INTACT
   FR-010: VERIFIED INTACT

   No production-code changes made by this WP.
   ```

2. If any subtask returned a FAIL, the **Verdict** is `NO-GO`, the failing items are listed under "Escalations," and a one-paragraph proposal is written for how WP02/WP03 should absorb the regression fix (e.g. "FR-009 retrospective gate has regressed — propose adding subtask T011a to WP02 to restore the pre-terminal gate before the synthesize work proceeds").

**Acceptance:**

- File exists at the specified path.
- Per-subtask outcomes are recorded.
- A clear GO / NO-GO verdict is present.
- If NO-GO, escalation paragraph is present.

---

## Definition of Done

- [ ] T001 evidence captured.
- [ ] T002 invariant inspection complete with line numbers.
- [ ] T003 invariant inspection complete with line numbers.
- [ ] `kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/research/verification-evidence.md` exists, lists per-task results, and carries a GO or NO-GO verdict.
- [ ] No production-code or non-evidence test code modified by this WP.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| The regression-guard tests fail due to environment drift (e.g. missing extra) rather than a real product regression | Re-run with `uv run --extra test ...` and document in the evidence file; do not classify as a regression until reproduced cleanly |
| One of the FR-010 invariants is genuinely missing on current `main` | Record as escalation; downstream WPs absorb the fix per C-003 |
| File paths cited in this WP have shifted since the brief was written | Use `rg` to find the modern path and document the resolved path in the evidence file |

## Reviewer Guidance

- Confirm the evidence file exists and is well-formed.
- Confirm no source files outside `kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/research/` were modified by this WP.
- If the verdict is NO-GO, confirm the escalation paragraph names a concrete WP and proposed subtask.

## Implementation Command

```bash
spec-kitty agent action implement WP01 --agent <name>
```

## Activity Log

- 2026-04-29T05:14:53Z – claude:opus-4-7:researcher-robbie:researcher – shell_pid=27620 – Started implementation via action command
