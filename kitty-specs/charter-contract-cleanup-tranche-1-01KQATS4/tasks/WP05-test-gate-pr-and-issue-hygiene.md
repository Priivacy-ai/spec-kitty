---
work_package_id: WP05
title: Local test gate + PR + GH issue hygiene (FR-011, FR-012, FR-013)
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- FR-011
- FR-012
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
created_at: '2026-04-28T20:35:00Z'
subtasks:
- T019
- T020
- T021
- T022
- T023
phase: Phase 3 - Release ops
agent: "claude:opus-4-7:implementer-ivan:implementer"
shell_pid: "57867"
history:
- timestamp: '2026-04-28T20:35:00Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/research/
execution_mode: planning_artifact
owned_files:
- kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/research/release-evidence.md
role: implementer
tags: []
---

# WP05 — Local test gate + PR + GH issue hygiene

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load the agent profile:

```
/ad-hoc-profile-load implementer-ivan
```

You are **implementer-ivan**: general-purpose implementation specialist. This WP is the release-ops phase: run gates, open the PR, manage GitHub issue hygiene. The deliverable is a single evidence file documenting the run.

---

## Branch Strategy

- **Planning/base branch:** `main`
- **Final merge target:** `main`
- Execution worktrees are allocated per computed lane in `lanes.json` after `finalize-tasks`. This WP runs in the lane that owns the mission's `kitty-specs/.../research/` directory and depends on WP01..WP04 having completed.
- Implementation command: `spec-kitty agent action implement WP05 --agent <name>`

## Objective

Land the mission. Run the five-command local test gate (NFR-001), dispose of the `Protect Main Branch` failure observed on the prior release merge, open the PR `fix/charter-827-contract-cleanup` → `Priivacy-ai/spec-kitty:main`, and after the PR merges apply post-merge GH issue hygiene to `#844`, `#827`, and `#848`. Document the entire run in `kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/research/release-evidence.md`.

This WP closes spec FR-011, FR-012, FR-013 and finalises the mission.

## Context

[`spec.md`](../spec.md) FR-011..FR-013 list the release-ops requirements. [`research.md`](../research.md) §R-008 (Protect-Main-Branch disposition) and §R-010 (issue-hygiene cadence) capture the resolved approach. [`quickstart.md`](../quickstart.md) §1 (the five-command test gate), §5 (CI verification), and §6 (post-merge issue hygiene) are the operational recipe.

`CLAUDE.md` in the repo root contains essential guidance for `gh` CLI org-repo authentication: when org-scope errors appear, `unset GITHUB_TOKEN` to fall back on the keyring token (which usually has full `repo` scope).

**FRs covered:** FR-011, FR-012, FR-013 · **NFRs:** NFR-001 (test gate), NFR-002 (no regressions), NFR-005 (SAAS env var rule), NFR-006 (single-PR scope) · **Constraints:** C-001, C-004, C-006

## Always-true rules

- WP01..WP04 must be merged into the feature branch before this WP starts running gates. Read the WP01 evidence file and confirm the verdict was GO; if NO-GO, escalate before opening the PR.
- The five NFR-001 commands must all exit 0 on the feature branch before pushing.
- The PR is opened against `Priivacy-ai/spec-kitty:main` from `fix/charter-827-contract-cleanup`. No other repo is touched (C-001).
- GH issue hygiene happens **after** the PR merges. Pre-merge updates are limited to the PR description naming the planned hygiene actions.
- `#827` and `#828` are NOT closed by this mission.
- `#844` is closed only after FR-006/FR-007 are merged (i.e. after WP03 lands in the merged PR).

---

## Subtask T019 — Run the five-command local test gate (NFR-001)

**Purpose:** Pre-push proof that the feature branch passes the contracts the mission promises.

**Steps:**

1. From the feature branch checkout (or the implementation worktree), run each command and capture output. If any command path touches hosted auth/sync/tracker, prefix with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` (none of the five below do, but the rule applies if you add ad-hoc commands):
   ```bash
   uv run pytest tests/e2e/test_charter_epic_golden_path.py -q
   uv run pytest \
     tests/agent/cli/commands/test_charter_synthesize_cli.py \
     tests/integration/test_json_envelope_strict.py \
     tests/integration/test_charter_synthesize_fresh.py -q
   uv run pytest \
     tests/next/test_retrospective_terminus_wiring.py \
     tests/retrospective/test_gate_decision.py \
     tests/doctrine_synthesizer/test_path_traversal_rejection.py -q
   uv run --extra test --extra lint pytest \
     tests/cross_cutting/test_mypy_strict_mission_step_contracts.py -q
   uv run ruff check src tests
   ```
2. Each command must exit 0. Capture full stdout/stderr per command into `kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/research/_artifacts/test-gate-<short-cmd>.txt`. (Create `_artifacts/` if it does not exist.)
3. If any command fails, do **not** push. Triage: read the failure → identify whether it is a regression in WP02/WP03/WP04's work or an unrelated environment issue → escalate appropriately. Do not weaken the test gate.

**Files to edit:** none (this writes captured output, plus updates `release-evidence.md` later in T023).

**Validation:**
- All five commands exit 0.
- Captured output saved.

---

## Subtask T020 — Diagnose the `Protect Main Branch` failure (fix or file issue)

**Purpose:** FR-013 disposition. The failure was observed on release PR #864 and the brief explicitly leaves the choice between fixing-here and filing-an-issue to engineering judgement.

**Steps:**

1. Inspect the failure. Use `gh` (with `unset GITHUB_TOKEN` if scope errors appear):
   ```bash
   unset GITHUB_TOKEN
   gh run list --repo Priivacy-ai/spec-kitty --workflow protect-main.yml --limit 10
   gh run view <run-id-of-failure> --log
   ```
2. Read the workflow file `.github/workflows/protect-main.yml`. Determine whether the failure is:
   - **(A) Reproducible from product code in `src/`.** Example: the workflow runs a check that imports from `src/` and that import has broken. → Fix it in this PR. Add a brief subtask note inline in `release-evidence.md` describing the fix.
   - **(B) A release-process artefact** (e.g. the workflow asserts that PRs into `main` come via the lane pipeline, and the prior release PR merged directly). → Do not fix it in this PR. File or update a GitHub issue describing the situation.
3. If branching to (B): create a new GitHub issue or update an existing one (search for "Protect Main" or related). Body should include:
   - The failing run URL.
   - One-paragraph diagnosis (release-process hygiene, not product code).
   - Proposed disposition (e.g. "tighten the workflow to exempt release PRs from the lane-pipeline check, or change the release process to go through a lane").
   - Cross-link to this mission's PR.
4. Whichever branch you take, document the disposition in `release-evidence.md` (T023).

**Files to edit:**
- `.github/workflows/protect-main.yml` if branching to (A) — but only with permission of the WP05 ownership scope. If the fix is non-trivial, escalate.
- No files modified if branching to (B).

**Validation:**
- A clear, written disposition exists.
- If (B), a GH issue URL is captured for `release-evidence.md`.

---

## Subtask T021 — Open the PR `fix/charter-827-contract-cleanup` → `main`

**Purpose:** FR-012. Land the mission.

**Steps:**

1. Confirm the feature branch is named `fix/charter-827-contract-cleanup` and tracks the mission's lane branch correctly.
2. Push the branch:
   ```bash
   git push -u origin fix/charter-827-contract-cleanup
   ```
3. Open the PR via `gh pr create` (with `unset GITHUB_TOKEN` if scope errors appear). Use a HEREDOC to format the body. Required body sections:
   - **Summary** — 2-3 bullets covering the contract fixes (FR-001..FR-005), the E2E hardening (FR-006/FR-007 / closes #844), and the CI mypy hygiene (FR-008).
   - **Evidence** — paste the terminal blocks captured in T019 (the five-command test gate). If they are large, attach as a comment after PR creation.
   - **Issues this PR closes** — `#844`. (Do NOT use "Closes #827" — #827 only gets a comment, see T022.)
   - **Issues this PR comments on** — `#827`, `#848`.
   - **Out of scope** — list the four explicit later tranches.
   - **`Protect Main Branch` disposition** — fix-here or file-issue link, per T020.
4. Watch checks:
   ```bash
   gh pr checks --watch
   ```
   - All required checks must go green. The `e2e-cross-cutting` job specifically must report a passing strict-typing executor test (this is the validation for WP04).
   - If a previously-green check fails, triage with the same rules as T019.
5. Once green and approved, merge per the project's standard process. (Lane-based merge if applicable; otherwise the standard merge-commit flow. The agent does **not** force-push to `main` and does **not** bypass branch protection.)

**Files to edit:** none.

**Validation:**
- PR exists at `https://github.com/Priivacy-ai/spec-kitty/pull/<n>`.
- `gh pr checks` shows all required checks green.
- Merge commit hash captured for `release-evidence.md`.

---

## Subtask T022 — Apply post-merge GH issue hygiene

**Purpose:** FR-011. Close out the issues this mission affects, with evidence.

**Steps:**

1. Wait for the PR to actually merge into `main`. Confirm:
   ```bash
   unset GITHUB_TOKEN
   gh pr view <pr-number> --json state,mergedAt,mergeCommit
   ```
2. `#844` — close with evidence:
   ```bash
   gh issue close 844 --comment "Closed by PR #<merged-pr>: golden-path E2E (\`tests/e2e/test_charter_epic_golden_path.py\`) now asserts non-null/non-empty/resolvable \`prompt_file\` for \`kind=step\` envelopes (FR-006), and a non-empty \`reason\` for blocked decisions (FR-007). See merge commit <sha>."
   ```
3. `#827` — comment, do **not** close:
   ```bash
   gh issue comment 827 --body "Tranche 1 (product-repo cleanup) merged in PR #<merged-pr>:
   - Charter \`charter synthesize --json\` strict-stdout + contracted envelope (\`result\`/\`adapter\`/\`written_artifacts\`/\`warnings\`)
   - Dry-run/non-dry-run path parity; no user-visible \`PROJECT_000\`
   - Golden-path E2E prompt-file resolvability assertion (closes #844)
   - CI \`e2e-cross-cutting\` job now installs the \`lint\` extra; mypy strict test runs and passes
   - Regression guards verified intact (verify-only)

   Remaining for #827:
   - Tranche 3 external E2E in \`spec-kitty-end-to-end-testing\`
   - Tranche 3 plain-English acceptance scenarios in \`spec-kitty-plain-english-tests\`"
   ```
4. `#848` — update with evidence:
   ```bash
   gh issue comment 848 --body "Resolved by PR #<merged-pr>: \`.github/workflows/ci-quality.yml\` \`e2e-cross-cutting\` job now installs \`pip install -e .[test,lint]\`. \`tests/cross_cutting/test_mypy_strict_mission_step_contracts.py\` runs and passes there. The \`uv.lock\` vs installed \`spec-kitty-events\` pin drift component of #848 is unaffected by this mission and remains tracked there."
   ```
   - If `#848` covers a different concern primarily and the mypy/uv-lock issue is a sub-aspect, adapt the comment text but keep the resolution scope explicit.
5. `#828` — leave open. Do not comment unless someone asks; #828 is the docs mission and lives in a separate later tranche.
6. `#469` — leave open. Phase 7, out of scope.

**Files to edit:** none.

**Validation:**
- `gh issue view 844 --json state` returns `closed`.
- `gh issue view 827 --json comments` shows the new comment.
- `gh issue view 848 --json comments` shows the new comment.

---

## Subtask T023 — Update `release-evidence.md` with the final state

**Purpose:** Single-file evidence artefact for the mission's release ops.

**Steps:**

1. Create `kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/research/release-evidence.md` with these sections:

   ```markdown
   # WP05 — Release Evidence

   **PR:** https://github.com/Priivacy-ai/spec-kitty/pull/<n>
   **Merge commit:** <sha>
   **Merged at (UTC):** <iso-timestamp>

   ## T019 — Local test gate (NFR-001)

   | Command | Outcome | Evidence |
   |---|---|---|
   | `uv run pytest tests/e2e/test_charter_epic_golden_path.py -q` | PASS | `_artifacts/test-gate-e2e.txt` |
   | `uv run pytest tests/agent/cli/commands/test_charter_synthesize_cli.py tests/integration/test_json_envelope_strict.py tests/integration/test_charter_synthesize_fresh.py -q` | PASS | `_artifacts/test-gate-synthesize.txt` |
   | `uv run pytest tests/next/test_retrospective_terminus_wiring.py tests/retrospective/test_gate_decision.py tests/doctrine_synthesizer/test_path_traversal_rejection.py -q` | PASS | `_artifacts/test-gate-regression.txt` |
   | `uv run --extra test --extra lint pytest tests/cross_cutting/test_mypy_strict_mission_step_contracts.py -q` | PASS | `_artifacts/test-gate-mypy.txt` |
   | `uv run ruff check src tests` | PASS | `_artifacts/test-gate-ruff.txt` |

   ## T020 — `Protect Main Branch` disposition

   **Outcome:** FIX-HERE  /  FILE-ISSUE  (pick one)

   <one paragraph diagnosis>

   <if FILE-ISSUE: GitHub issue URL>
   <if FIX-HERE: brief description of the change>

   ## T021 — PR

   - Branch: `fix/charter-827-contract-cleanup` → `main`
   - All required CI checks green at merge time: yes / no
   - `e2e-cross-cutting` strict-typing executor test passed: yes / no
   - Merge commit: <sha>

   ## T022 — Issue hygiene

   - #844 — CLOSED with comment referencing PR #<n>
   - #827 — COMMENTED with Tranche 1 closure summary; not closed
   - #848 — COMMENTED with mypy resolution; sub-aspects (uv.lock) remain tracked there
   - #828 — left open (docs mission, later tranche)
   - #469 — left untouched (Phase 7, out of scope)

   ## Verdict

   **Mission complete.** All FRs and NFRs in spec.md verified.
   ```

2. Commit `release-evidence.md` (and any `_artifacts/` files captured) on the feature branch *after* the PR is merged. If the merge is already complete, push the evidence as a follow-up commit on a small post-merge branch or attach as a comment on the merged PR — choose whichever the project's house style prefers.

**Files to edit:**
- `kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/research/release-evidence.md` (new)

**Validation:**
- File exists.
- Per-task outcomes recorded.
- "Mission complete" verdict present.

---

## Definition of Done

- [ ] T019 — All five NFR-001 commands exit 0 on the feature branch.
- [ ] T020 — `Protect Main Branch` disposition documented (fix-here or file-issue).
- [ ] T021 — PR opened from `fix/charter-827-contract-cleanup` to `Priivacy-ai/spec-kitty:main`; all required checks green; merged.
- [ ] T022 — `#844` closed; `#827` and `#848` commented; `#828` and `#469` untouched.
- [ ] T023 — `release-evidence.md` exists with the final-state summary and a "Mission complete" verdict.
- [ ] No files modified outside the WP's authoritative surface unless covered by T020(A).

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Local test gate fails after WP02..WP04 land | Triage as a regression in those WPs and escalate; do not weaken the gate |
| `gh pr create` fails with org-scope errors | `unset GITHUB_TOKEN` per CLAUDE.md guidance |
| The `Protect Main Branch` workflow can't be diagnosed without merging this PR (chicken-and-egg) | Diagnose by reading `.github/workflows/protect-main.yml` and the failure logs from the prior release PR; the diagnosis does not require this PR to be merged |
| Issue hygiene runs before the merge actually completes | Gate on `gh pr view --json state,mergedAt,mergeCommit` returning `state == MERGED` and a non-null `mergedAt` |
| `#848` covers a different primary issue and the mypy comment is off-topic | Read `#848` first, scope the comment to the mypy/uv-lock aspect, and call out the rest as still-tracked |

## Reviewer Guidance

- Confirm `release-evidence.md` exists and is well-formed.
- Spot-check at least two of the captured `_artifacts/test-gate-*.txt` files.
- Confirm `#844` is closed with a comment that links the merge commit.
- Confirm `#827` is commented but **not** closed.
- Confirm no files outside the authoritative surface were modified (other than the FIX-HERE branch of T020, if taken).

## Implementation Command

```bash
spec-kitty agent action implement WP05 --agent <name>
```

## Activity Log

- 2026-04-29T05:51:58Z – claude:opus-4-7:implementer-ivan:implementer – shell_pid=57867 – Started implementation via action command
