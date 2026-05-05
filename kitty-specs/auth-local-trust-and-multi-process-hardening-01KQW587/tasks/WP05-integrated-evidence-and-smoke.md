---
work_package_id: WP05
title: Integrated Evidence And Smoke
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- C-001
- C-002
- C-003
- C-004
- C-005
- C-006
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- NFR-001
- NFR-002
- NFR-003
- NFR-004
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
phase: Phase 3 - Evidence
assignee: ''
agent: "codex:gpt-5:python-pedro:reviewer"
shell_pid: "25495"
history:
- at: '2026-05-05T13:41:33Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/
execution_mode: planning_artifact
model: ''
owned_files:
- kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/evidence.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 - Integrated Evidence And Smoke

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Collect final acceptance evidence for the mission after WP01-WP04 land. This WP should create `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/evidence.md` and should not change production code unless a narrow integration gap is discovered and explicitly justified.

Implementation command: `spec-kitty agent action implement WP05 --agent <name>`

## Dependencies

Depends on WP01, WP02, WP03, and WP04.

## Context & Constraints

Read:

- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/quickstart.md`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/spec.md`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/plan.md`

On this computer, hosted auth/tracker/sync CLI smoke commands must use `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. Default unit and concurrency tests should remain hermetic.

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`
- **Actual execution workspace is resolved later**: `/spec-kitty.implement` decides the lane workspace path and records the lane branch in `base_branch`.

## Subtasks & Detailed Guidance

### Subtask T020 - Run focused evidence suite

- **Purpose**: Verify the acceptance checks after all implementation WPs land.
- **Steps**:
  1. Run focused WP01 diagnostic tests.
  2. Run WP02 hosted-URL-set and hosted-URL-unset refresh-lock tests.
  3. Run WP03 review guardrail tests.
  4. Run WP04 auth hot-path/secure-storage/packaging tests.
  5. Summarize commands and outcomes in `evidence.md`.
- **Files**: `evidence.md`.
- **Parallel?**: No; depends on all prior WPs.
- **Notes**: Do not paste huge logs. Summarize command, result, and key assertion.

### Subtask T021 - Record hosted smoke commands with required environment

- **Purpose**: Keep hosted dev smoke explicit and separate from hermetic tests.
- **Steps**:
  1. Identify any hosted auth/tracker/sync smoke command run for this mission.
  2. Prefix such commands with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.
  3. Record whether the command touched `https://spec-kitty-dev.fly.dev`.
- **Files**: `evidence.md`.
- **Parallel?**: No.
- **Notes**: Do not turn hosted smoke into default test requirements.

### Subtask T022 - Compile acceptance evidence

- **Purpose**: Tie results to issues and requirements.
- **Steps**:
  1. Add sections for #829, #907, #889, #977, and CLI-side #77.
  2. Include the exact evidence that satisfies each acceptance check.
  3. Note any deferred or out-of-scope tracker/SaaS work.
- **Files**: `evidence.md`.
- **Parallel?**: No.
- **Notes**: Keep the evidence actionable for review and future issue closure.

### Subtask T023 - Record pre-existing failure issue links

- **Purpose**: Follow the charter rule for pre-existing failures.
- **Steps**:
  1. If a verification command fails, decide whether the failure is introduced by this mission or pre-existing.
  2. For pre-existing failures, open/report a GitHub issue before accepting them as baseline.
  3. Link the issue and include command/failure summary in `evidence.md`.
- **Files**: `evidence.md`.
- **Parallel?**: No.
- **Notes**: Do not silently wave through failing tests.

## Test Strategy

Use the commands from `quickstart.md`, adjusted to the final changed files. At minimum, evidence should cover:

```bash
SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev \
  uv run pytest tests/auth/concurrency/test_machine_refresh_lock.py -q --timeout=60

env -u SPEC_KITTY_SAAS_URL \
  uv run pytest tests/auth/concurrency/test_machine_refresh_lock.py -q --timeout=60
```

Run hosted smoke only with:

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 <hosted-auth-or-sync-command>
```

## Definition of Done

- `evidence.md` exists and maps evidence to all targeted issues.
- Commands are summarized with pass/fail status.
- Hosted smoke use of `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is explicit.
- Any pre-existing failures have issue links.

## Risks & Mitigations

- **Risk**: Evidence becomes noisy. **Mitigation**: summarize, do not dump full logs.
- **Risk**: Hosted smoke contaminates hermetic tests. **Mitigation**: keep hosted commands separate and env-prefixed.

## Review Guidance

Reviewers should verify that evidence maps directly to the spec success criteria and that no pre-existing failures were accepted without issue tracking.

## Evidence File Structure

Create `evidence.md` with these sections:

1. Mission summary and commit range under review.
2. Focused command results.
3. Issue #829 evidence.
4. Issue #907 evidence.
5. Issue #889 evidence.
6. Issue #977 evidence.
7. CLI-side SaaS #77 evidence.
8. Hosted smoke commands and environment.
9. Pre-existing failures and issue links, if any.
10. Final acceptance checklist.

## Integration Verification

Before moving this WP to `for_review`, verify:

- [ ] Every success criterion in `spec.md` has evidence or an explicit deferral.
- [ ] Hosted smoke commands that touch SaaS/tracker/sync use `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.
- [ ] Hermetic tests are not rewritten as hosted smoke.
- [ ] Any failing command is triaged as introduced failure or pre-existing failure.
- [ ] Any pre-existing failure has a linked issue before acceptance.

## Out Of Scope

- Do not implement broad production fixes in this WP.
- Do not rerun `/spec-kitty.tasks` or change WP ownership.
- Do not push or deploy from this WP unless the human explicitly asks.
- Do not include raw token material or sensitive audit metadata in `evidence.md`.

## Implementation Handoff Notes

This WP is the release/evidence closure. It should read the final changed code and run the focused commands that prove the mission, but it should not reopen design. If a late integration gap appears, make the smallest possible fix only when it is clearly inside the owned evidence artifact; otherwise send the relevant WP back through implementation/review.

The evidence file should be concise enough to support issue closure comments without requiring reviewers to inspect raw terminal logs.
Prefer stable command summaries over copied stack traces unless a failure needs issue filing.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-05-05T13:41:33Z – system – Prompt created.
- 2026-05-05T15:15:55Z – codex:gpt-5:python-pedro:implementer – shell_pid=13415 – Started implementation via action command
- 2026-05-05T15:27:37Z – codex:gpt-5:python-pedro:implementer – shell_pid=13415 – Ready for review: integrated evidence recorded; required quickstart gates pass; supplemental FR-011 lane regression noted.
- 2026-05-05T15:28:44Z – codex:gpt-5:python-pedro:reviewer – shell_pid=16423 – Started review via action command
- 2026-05-05T15:34:44Z – codex:gpt-5:python-pedro:reviewer – shell_pid=16423 – Moved to planned
- 2026-05-05T15:44:12Z – codex:gpt-5:python-pedro:implementer – shell_pid=22300 – Started implementation via action command
- 2026-05-05T15:49:02Z – codex:gpt-5:python-pedro:implementer – shell_pid=23993 – Ready for review: integrated evidence refreshed with lane A 9099a032 and lane B 306bc815; FR-011 146 passed.
- 2026-05-05T15:50:36Z – codex:gpt-5:python-pedro:reviewer – shell_pid=25495 – Started review via action command
- 2026-05-05T15:54:25Z – codex:gpt-5:python-pedro:reviewer – shell_pid=25495 – Review passed: evidence uses lane A 9099a032 and lane B 306bc815; focused suites pass including FR-011 146 passed
