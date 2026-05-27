---
work_package_id: WP11
title: Full-suite re-baseline + issue closeout
dependencies:
- WP10
requirement_refs:
- FR-013
tracker_refs: []
planning_base_branch: feat/pre-doctrine-stabilization-remediation
merge_target_branch: feat/pre-doctrine-stabilization-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/pre-doctrine-stabilization-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/pre-doctrine-stabilization-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T046
- T047
- T048
- T049

model: claude-sonnet-4-6
history:
- date: '2026-05-27'
  event: created
agent_profile: human-in-charge
authoritative_surface: docs/01KSMG8Y-closeout/
execution_mode: planning_artifact
owned_files:
- docs/01KSMG8Y-closeout/baseline.md
role: human-in-charge
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load human-in-charge
```

---

## Objective

Run the full test suite on the merged feature branch, record the output, commit the baseline document, and close all ten GitHub sub-issues (#1301–#1310). This is a planning-lane WP — no worktree is needed; run in the main checkout after all earlier lanes have been merged.

**Closes**: FR-013. Contributes to closing #1298.

---

## Context

This WP is the mission's success gate. The ≤75-failure threshold (NFR-001) determines whether the mission is complete or whether additional follow-up issues must be filed.

**Pre-condition**: WP01–WP10 must all be merged into `feat/pre-doctrine-stabilization-remediation` before this WP begins. The feature branch must be up to date with all lane merges.

---

## Subtask T046 — Run full test suite and record output

**Purpose**: Establish the post-mission baseline failure count.

**Steps**:

1. Ensure all lanes are merged:
   ```bash
   git log --oneline -20
   ```
   Confirm commits from all WP lanes are present.

2. Run the full suite in headless mode:
   ```bash
   PWHEADLESS=1 pytest tests/ -q --tb=no 2>&1 | tee /tmp/baseline_run.txt
   ```
   This may take ~15–20 minutes. Let it complete.

3. Extract summary statistics:
   ```bash
   tail -5 /tmp/baseline_run.txt
   grep "FAILED\|ERROR" /tmp/baseline_run.txt | wc -l
   grep "FAILED\|ERROR" /tmp/baseline_run.txt > /tmp/failures.txt
   ```

4. Record:
   - Total test count
   - Pass count
   - Failure count
   - Error count
   - Run time (seconds)

5. Check against the gate:
   - ≤75 failures: mission SUCCESS — proceed to T047
   - >75 failures: file DIR-013 issues for each unexpected failure cluster; document in baseline.md; declare mission complete with known gap

**Validation**:
- [ ] Full suite completed (no timeout)
- [ ] Failure count recorded
- [ ] Result assessed against the ≤75 gate

---

## Subtask T047 — Commit baseline.md to docs/01KSMG8Y-closeout/

**Purpose**: Create a permanent record of the post-mission test baseline.

**Steps**:

1. Create the closeout directory if it doesn't exist:
   ```bash
   mkdir -p docs/01KSMG8Y-closeout/
   ```

2. Write `docs/01KSMG8Y-closeout/baseline.md` with the following content:

   ```markdown
   # Post-Mission Test Baseline: 01KSMG8Y

   **Mission**: Pre-Doctrine Test Stabilization  
   **Date**: YYYY-MM-DD  
   **Branch**: feat/pre-doctrine-stabilization-remediation  
   **Gate**: ≤75 failures (NFR-001)

   ## Summary

   | Metric | Value |
   |--------|-------|
   | Total tests | NNN |
   | Passed | NNN |
   | Failed | NNN |
   | Errors | NNN |
   | Run time | NNN s |
   | **Gate met** | ✅ YES / ❌ NO |

   ## Failure List

   <paste full FAILED/ERROR lines from pytest output>

   ## Sub-issue Resolution

   | Issue | Status | Notes |
   |-------|--------|-------|
   | #1301 | closed / re-deferred | [linking commit or new issue] |
   | #1302 | closed | [linking commit] |
   | #1303 | closed | [linking commit] |
   | #1304 | closed | [linking commit] |
   | #1305 | closed | [linking commit] |
   | #1306 | closed | [linking commit] |
   | #1307 | closed | [linking commit] |
   | #1308 | closed | [linking commit] |
   | #1309 | closed | [linking commit] |
   | #1310 | closed / re-deferred | [linking commit + new issue numbers] |

   ## Notes

   [Any outstanding items, follow-on issues, or observations]
   ```

3. Fill in all values from T046 output.

4. Commit:
   ```bash
   git add docs/01KSMG8Y-closeout/baseline.md
   git commit -m "docs(01KSMG8Y): add post-mission test baseline"
   ```

**Files**: `docs/01KSMG8Y-closeout/baseline.md`

**Validation**:
- [ ] File committed with full failure list
- [ ] Gate result (pass/fail) clearly stated

---

## Subtask T048 — Close or re-defer GitHub issues #1301–#1310

**Purpose**: Each sub-issue must be either closed with a linking commit or re-deferred with a new filed follow-on issue.

**Steps**:

```bash
unset GITHUB_TOKEN  # use keyring auth

# For each issue that has been fixed:
gh issue close 1302 --comment "Fixed by commit <hash> in feat/pre-doctrine-stabilization-remediation (WP01 — TOML escape fix)"
gh issue close 1308 --comment "Fixed by commit <hash> in feat/pre-doctrine-stabilization-remediation (WP02 — README Governance section)"
gh issue close 1309 --comment "Fixed by commit <hash> in feat/pre-doctrine-stabilization-remediation (WP02 — wp_files.py frontmatter lane guard)"
gh issue close 1310 --comment "Partially fixed by feat/pre-doctrine-stabilization-remediation. Re-deferred items tracked in issues #XXXX and #XXXX (filed by WP09)."
gh issue close 1304 --comment "Fixed by commit <hash> in feat/pre-doctrine-stabilization-remediation (WP03 — doctrine glossary anchors)"
gh issue close 1306 --comment "Fixed by commit <hash> in feat/pre-doctrine-stabilization-remediation (WP04 — status/lifecycle event drift)"
gh issue close 1307 --comment "Fixed by commit <hash> in feat/pre-doctrine-stabilization-remediation (WP05 — charter integration regressions)"
gh issue close 1305 --comment "Fixed by commit <hash> in feat/pre-doctrine-stabilization-remediation (WP06 — next CLI exit-code)"
gh issue close 1301 --comment "Fixed by commit <hash> in feat/pre-doctrine-stabilization-remediation (WP07 — shared-package events drift)"
gh issue close 1303 --comment "Fixed by commit <hash> in feat/pre-doctrine-stabilization-remediation (WP08 — charter synthesizer determinism)"
```

Replace `<hash>` with the actual commit hash from each WP's merge commit.

For re-deferred items: do NOT close the original issue — instead comment with the new issue number and mark as "deferred" if the label is available.

**Validation**:
- [ ] All 10 issues (#1301–#1310) are either closed or have a re-defer comment with new issue number
- [ ] No issue closed without a linking commit hash

---

## Subtask T049 — Post closing comment on #1298

**Purpose**: Close the parent triage issue with the final delta (before vs. after failure count).

**Steps**:

1. Compose the closing comment with:
   - Pre-mission failure count (249 per original triage)
   - Post-mission failure count (from T046)
   - Delta (failures resolved)
   - List of linked closing commits
   - Links to re-deferred issues (if any)

2. Post the comment:
   ```bash
   unset GITHUB_TOKEN
   gh issue comment 1298 --body "$(cat <<'EOF'
   ## Mission 01KSMG8Y — Pre-Doctrine Test Stabilization — Closeout

   **Result**: [GATE MET / GATE MISSED]

   | Metric | Before | After | Delta |
   |--------|--------|-------|-------|
   | Failures | ~249 | NNN | -NNN |

   All 10 sub-issues resolved:
   - #1301 closed (WP07)
   - #1302 closed (WP01)
   - #1303 closed (WP08)
   - #1304 closed (WP03)
   - #1305 closed (WP06)
   - #1306 closed (WP04)
   - #1307 closed (WP05)
   - #1308 closed (WP02)
   - #1309 closed (WP02)
   - #1310 partially closed (WP02 + WP09); re-deferred items: #XXXX, #XXXX

   Baseline committed to `docs/01KSMG8Y-closeout/baseline.md` on branch `feat/pre-doctrine-stabilization-remediation`.
   EOF
   )"
   ```

3. If the gate was NOT met (>75 failures): close #1298 anyway but note that follow-on issues have been filed for remaining clusters (DIR-013 compliance).

**Validation**:
- [ ] #1298 has a closing comment with before/after failure counts
- [ ] All 10 sub-issues are referenced in the comment

---

## Branch Strategy

- **Planning/base branch**: `feat/pre-doctrine-stabilization-remediation`
- **Final merge target**: `feat/pre-doctrine-stabilization-remediation`
- **Execution mode**: `planning_artifact` — runs in the main checkout, no worktree needed

To start implementation:
```bash
spec-kitty agent action implement WP11 --agent claude
```

---

## Definition of Done

- [ ] Full `PWHEADLESS=1 pytest tests/ -q --tb=no` run completed
- [ ] Failure count ≤75 (or follow-on issues filed for remaining clusters)
- [ ] `docs/01KSMG8Y-closeout/baseline.md` committed with full failure list
- [ ] All ten issues (#1301–#1310) closed or re-deferred with new issue numbers
- [ ] #1298 has a closing comment with the final failure delta

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Failure count >75 | Medium | File DIR-013 issues for remaining clusters; declare mission complete with gap |
| GitHub auth fails | Medium | `unset GITHUB_TOKEN`; use keyring auth |
| Test suite times out on CI | Low | Run locally first; note any slowdown vs. ~924s baseline |

---

## Reviewer Guidance

This WP is human-reviewed. The reviewer confirms:
1. `baseline.md` was committed with real pytest output (not fabricated)
2. Failure count is accurate and assessed against the ≤75 gate
3. All 10 sub-issues have resolution comments
4. #1298 has the closing comment
</content>