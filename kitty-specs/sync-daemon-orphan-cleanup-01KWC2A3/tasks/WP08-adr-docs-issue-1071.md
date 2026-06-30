---
work_package_id: WP08
title: 'ADR, operator docs & #1071 reconfirmation'
dependencies:
- WP05
- WP06
- WP07
requirement_refs:
- C-005
- C-007
- FR-012
tracker_refs: []
planning_base_branch: fix/sync-daemon-orphan-cleanup
merge_target_branch: fix/sync-daemon-orphan-cleanup
branch_strategy: Planning artifacts for this mission were generated on fix/sync-daemon-orphan-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/sync-daemon-orphan-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T036
- T037
- T038
- T039
phase: Phase 5 - Decision record & closeout
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "97073"
history:
- at: '2026-06-30T11:18:31Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: docs/adr/3.x/
create_intent:
- docs/adr/3.x/2026-06-30-1-sync-daemon-identity-and-cleanup-classification.md
- docs/development/sync-daemon-orphan-cleanup.md
- tests/sync/test_issue_1071_singleton_reconfirmation.py
execution_mode: code_change
model: ''
owned_files:
- docs/adr/3.x/2026-06-30-1-sync-daemon-identity-and-cleanup-classification.md
- docs/development/sync-daemon-orphan-cleanup.md
- tests/sync/test_issue_1071_singleton_reconfirmation.py
role: curator
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – ADR, operator docs & #1071 reconfirmation

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile named in the frontmatter **before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is set, run `spec-kitty agent profile list` and pick the best match for `task_type: implement` on `authoritative_surface: docs/adr/3.x/`.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks (```python`, ```bash`).

---

## Objective

Record the daemon identity-contract change as an **ADR** (DIRECTIVE_003, C-005), document the **operator remediation runbook** (DIRECTIVE_037), and **reconfirm #1071** (same-`$HOME` singleton leak) with an automated live-subprocess test before it is closed or re-scoped (FR-012, SC-006, D-03).

## Context & Constraints

Read before editing:
- [spec.md](../spec.md) FR-012, C-005, SC-006; [research.md](../research.md) DD-05, D-03; [plan.md](../plan.md) IC-06; [quickstart.md](../quickstart.md) (operator path).
- ADR conventions: follow an existing file under `docs/adr/3.x/` for front-matter/structure (e.g. the doctrine-layer ADR referenced in CLAUDE.md). Use the `adr-drafting-workflow` tactic.
- Reuse the shared `tests/sync/_daemon_harness.py` (WP06) for the #1071 test.

**Negative scope**: do NOT edit `src/` (behavior is delivered in WP01–WP05). This WP is docs + one test. Do NOT perform the actual GitHub close/re-scope action automatically — record the recommendation; the operator closes #1071 (and #2261 follows DIR-012 at implementation start).

## Branch Strategy

- **Strategy**: lane-per-WP (from `lanes.json`)
- **Planning base branch**: `fix/sync-daemon-orphan-cleanup`
- **Merge target branch**: `fix/sync-daemon-orphan-cleanup`

> Depends on WP05/WP06/WP07 — the behavior and harness must exist before documenting/closing.

## Subtasks & Detailed Guidance

### Subtask T036 – ADR: daemon identity & cleanup classification

- **Purpose**: Make the decision discoverable (DIRECTIVE_003).
- **Files**: `docs/adr/3.x/2026-06-30-1-sync-daemon-identity-and-cleanup-classification.md` (new).
- **Steps**: Record Context (the 18-orphan leak + root cause), Decision (daemon-root scope marker is primary kill authority; `cleanup_class` model; explicit `daemon_family`; `owner.json` is reporting data, not kill authority; wedged → `operator_required`; `--reset --force` for `operator_required`), Consequences, and the three Decision Moments (DM IDs in `../decisions/`). Cross-link `kitty-specs/sync-daemon-orphan-cleanup-01KWC2A3/`.
- **Notes**: Match the front-matter/shape of an existing `docs/adr/3.x/` ADR.

### Subtask T037 – Operator remediation runbook

- **Purpose**: DIRECTIVE_037 living docs.
- **Files**: `docs/development/sync-daemon-orphan-cleanup.md` (new).
- **Steps**: Document the two-command path (`spec-kitty auth doctor` → `spec-kitty auth doctor --reset [--force]`), what each `cleanup_class` means, what is never touched (dashboard/third-party/out-of-range), and the JSON fields for scripting. Adapt from `../quickstart.md`. Note the `SPEC_KITTY_ENABLE_SAAS_SYNC=1` requirement for hosted auth/sync tests (C-006).
- **Notes**: Link it from the relevant docs index if one exists (check `docs/` for a development index).

### Subtask T038 – Automated #1071 reconfirmation test (FR-012)

- **Purpose**: Durable evidence #1071 is handled (D-03).
- **Files**: `tests/sync/test_issue_1071_singleton_reconfirmation.py` (new).
- **Steps**: Using the WP06 harness, reproduce the same-`$HOME` singleton scenario from #1071 (multiple same-scope daemons under one `$HOME`/runtime root) and assert the new authority resolves it: stale same-scope daemons are reaped and exactly one singleton remains — no leak. Mark `@pytest.mark.integration`, serial (`-n0`), `skipif` win32.
- **Notes**: This is the evidence cited when closing #1071.

### Subtask T039 – Close/re-scope recommendation

- **Purpose**: Complete FR-012/SC-006.
- **Files**: `docs/development/sync-daemon-orphan-cleanup.md` (a short "#1071 status" section).
- **Steps**: State that #1071 is reconfirmed by `test_issue_1071_singleton_reconfirmation.py` and recommend closing it (or, if any residual is found, the precise re-scope). The human performs the GitHub action (unset `GITHUB_TOKEN` keyring auth per CLAUDE.md if needed).
- **Notes**: Do not auto-close the issue.

## Test Strategy

- `PWHEADLESS=1 .venv/bin/pytest tests/sync/test_issue_1071_singleton_reconfirmation.py -n0 -q`.
- Run the terminology guard since this WP adds prose: `.venv/bin/pytest tests/architectural/test_no_legacy_terminology.py -q` (CLAUDE.md pre-push rule for `docs/` changes).
- `.venv/bin/ruff check tests/sync/test_issue_1071_singleton_reconfirmation.py` — zero issues.

## Risks & Mitigations

- **#1071 not fully reproduced**: model the exact same-`$HOME` multi-daemon shape; if a residual leak remains, re-scope rather than force-close.
- **Terminology regression in docs**: run the terminology guard (some gates only fire in CI's integration job).
- **ADR drift**: write the ADR against the shipped contract (after WP01–05), not the original issue text.

## Review Guidance

- Verify the ADR captures the identity-contract decision + the 3 DMs (DIRECTIVE_003).
- Verify the operator runbook matches the shipped `auth doctor`/`--reset --force` behavior (DIRECTIVE_037).
- Verify the #1071 test reproduces the same-`$HOME` scenario and proves no leak (FR-012); confirm the close/re-scope recommendation is recorded (SC-006).
- Verify the terminology guard passes.

## Activity Log

- 2026-06-30T11:18:31Z – system – Prompt created.
- 2026-06-30T14:05:14Z – claude:sonnet:curator-carla:implementer – shell_pid=29988 – Assigned agent via action command
- 2026-06-30T14:16:32Z – claude:sonnet:curator-carla:implementer – shell_pid=29988 – ADR (identity contract + 3 DMs), operator runbook, automated #1071 same-HOME reconfirmation test (green); terminology guard passes; ruff+mypy clean; no leaks
- 2026-06-30T14:17:21Z – claude:opus:reviewer-renata:reviewer – shell_pid=97073 – Started review via action command
