---
work_package_id: WP05
title: 'Mission closure: evidence + PR body update draft'
dependencies:
- WP02
- WP03
- WP04
requirement_refs:
- FR-010
planning_base_branch: kitty/pr/mvp-sync-boundary-cli-01KRVCQS
merge_target_branch: kitty/pr/mvp-sync-boundary-cli-01KRVCQS
branch_strategy: Planning artifacts for this mission were generated on kitty/pr/mvp-sync-boundary-cli-01KRVCQS. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/pr/mvp-sync-boundary-cli-01KRVCQS unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
agent: "claude:opus-4.7:reviewer-rita:reviewer"
shell_pid: "19931"
history:
- at: '2026-05-18T08:00:00Z'
  actor: planner
  note: Initial generation
agent_profile: curator-carla
authoritative_surface: kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/
execution_mode: planning_artifact
mission_id: 01KRX11MCY70M5NFBBHT4DQHJ2
mission_slug: mvp-cli-sync-boundary-completion-01KRX11M
owned_files:
- kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/**
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, run the `ad-hoc-profile-load` skill to adopt the assigned profile (`curator-carla`, role: `curator`). The profile sets the identity, governance scope, and boundaries for the work in this WP.

## Objective

Capture verification evidence proving WP01-WP04 satisfy the spec's strict acceptance, draft the four sub-issue close comments (#1090, #1088, #1087, #1089) the operator will paste at close time, and prepare the replacement PR #1107 body that removes the "post-merge follow-up" claim now that the daemon-owner preflight is in-MVP.

This WP touches no source code; it only writes to `evidence/` inside the mission directory.

## Context

- The mission is complete (per spec) once Phase 2 work lands on PR #1107 with verification evidence.
- The operator is responsible for actually posting issue comments and running `gh pr edit`; this WP prepares the artifacts they will paste.
- All four sub-issues are tracked in `start-here.md` and remain open during the mission run.

## Branch strategy

- Planning/base branch: `kitty/pr/mvp-sync-boundary-cli-01KRVCQS`.
- Final merge target: `kitty/pr/mvp-sync-boundary-cli-01KRVCQS`.
- Execution worktree: allocated by `finalize-tasks` (planning_artifact mode; runs in the planning workspace).

## Subtasks

### T021 — Run full verification suite and capture transcripts

**Purpose**: Produce evidence files showing green test runs and clean live `sync status --check`.

**Steps**:

1. Create `evidence/test-transcripts/` inside the mission directory.
2. Run and tee output for each command, capturing both stdout and stderr:
   - `uv run pytest tests/sync/test_queue_row_level_migration.py tests/sync/test_daemon_owner_record.py tests/sync/test_sync_status_boundary_check.py tests/sync/test_sync_boundary_preflight.py tests/runtime/test_setup_plan_sync_evidence.py -q | tee evidence/test-transcripts/targeted.txt`
   - `uv run pytest tests/sync tests/status tests/runtime -q | tee evidence/test-transcripts/broad.txt`
   - `uv run mypy --strict src/specify_cli/sync/ | tee evidence/test-transcripts/mypy-strict.txt`
   - `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty sync status --check | tee evidence/test-transcripts/sync-status-check-coherent.txt` (skip if no hosted auth on this machine; record SKIP reason in a file)
   - `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty sync status --check --json | jq . | tee evidence/test-transcripts/sync-status-check-json.txt` (same skip caveat)
3. If any test fails, **stop**. Reopen the failing WP via the runtime review loop instead of papering over the failure here.

**Files**:
- `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/test-transcripts/*.txt` (new)

**Validation**:
- All targeted commands exit 0; transcripts saved verbatim.

### T022 — Draft sub-issue evidence comments

**Purpose**: Give the operator paste-ready close comments for #1090, #1088, #1087, #1089.

**Steps**:

1. For each sub-issue, write a markdown file under `evidence/`:
   - `evidence/close-1090.md` — row-level migration
   - `evidence/close-1088.md` — daemon owner coherence
   - `evidence/close-1087.md` — truthful `sync status --check` / `sync doctor`
   - `evidence/close-1089.md` — `setup-plan` refuse-loudly
2. Each file follows this template (adapt content to the specific issue):

   ```markdown
   ## Resolution: PR #1107

   This issue is fixed by PR #1107 (`mvp-cli-sync-boundary-completion-01KRX11M`).

   ### What changed (this issue's scope)
   - <bullet 1>
   - <bullet 2>

   ### Verification

   ```
   $ <command from quickstart.md §5>
   <captured output excerpt>
   ```

   Full transcripts: `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/test-transcripts/`.

   ### Code references
   - <file>:<line> — <what it does>
   - ...

   Closing per the mission's Definition of Done.
   ```

3. Source the verification command and code references from `quickstart.md §5` and `plan.md`'s wiring-points list. Source the captured output excerpts from T021's transcripts.

**Files**:
- `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/close-1090.md` (new)
- `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/close-1088.md` (new)
- `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/close-1087.md` (new)
- `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/close-1089.md` (new)

**Validation**:
- Each file exists, has a non-empty verification block, and links to a real transcript file in `test-transcripts/`.

### T023 — Draft replacement PR #1107 body

**Purpose**: Prepare the new PR body the operator will apply via `gh pr edit`. Remove the "post-merge follow-up" claim for daemon-owner gating (it is now in-MVP).

**Steps**:

1. Fetch the current PR #1107 body for reference:
   ```bash
   gh pr view 1107 --repo Priivacy-ai/spec-kitty --json body | jq -r .body > evidence/pr-1107-body-current.md
   ```
2. Draft the replacement body at `evidence/pr-1107-body-update.md`:
   - Preserve all sections of the current body that are still accurate.
   - Remove or rewrite the "post-merge follow-up" line that mentions `check_daemon_owner_match()` not being wired into per-action gates.
   - Add a new "Boundary preflight (shipped in this PR)" section summarizing WP01-WP04: reusable `SyncBoundaryPreflight`, wired into `sync now` and `setup-plan`, `sync status --check` expanded with `--json` mode, row-level migration covers body uploads with idempotent retries.
   - Link to mission directory `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/` and to `quickstart.md` for the operator runbook.
3. Add the exact `gh` command the operator will run, at the top of the file:
   ```bash
   gh pr edit 1107 --repo Priivacy-ai/spec-kitty --body-file kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/pr-1107-body-update.md
   ```

**Files**:
- `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/pr-1107-body-current.md` (snapshot)
- `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/pr-1107-body-update.md` (replacement draft)

**Validation**:
- Replacement draft does not contain any stale "post-merge follow-up" language for daemon-owner gating.
- `gh` command is correct and runnable.

### T024 — Update mission status events and verify decisions

**Purpose**: Close the mission cleanly so the spec-kitty runtime reflects completion.

**Steps**:

1. Run `spec-kitty agent decision verify --mission mvp-cli-sync-boundary-completion-01KRX11M --json`. Output MUST be `{"status": "clean", ...}`. If not, address findings before continuing.
2. Update or add `evidence/definition-of-done.md` enumerating the spec's DoD checklist with a ✓ / ✗ per item, citing transcript file references for each ✓.
3. Optional: emit a mission-level status event marking the mission ready for merge via the runtime CLI if a suitable command exists; otherwise, leave the artifact-based evidence as the canonical proof and let the operator drive merge.

**Files**:
- `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/definition-of-done.md` (new)

**Validation**:
- `spec-kitty agent decision verify --mission mvp-cli-sync-boundary-completion-01KRX11M` returns `{"status": "clean", ...}`.
- `evidence/definition-of-done.md` exists and every spec DoD item has a verdict + transcript reference.

## Definition of Done

- [ ] `evidence/test-transcripts/` contains transcripts for the targeted, broad, mypy, and (if applicable) live `sync status --check` runs.
- [ ] All four `evidence/close-NNNN.md` files exist with verification blocks linked to real transcripts.
- [ ] `evidence/pr-1107-body-update.md` exists and is operator-ready.
- [ ] `evidence/definition-of-done.md` exists with all spec DoD items checked or explicitly justified.
- [ ] Decision verifier is clean.

## Risks

- **Tests fail and this WP can't proceed**: Correct response is to bounce back to the failing WP, not to fake the evidence. Reopen via the runtime review loop.
- **Live `sync status --check` skipped on this machine for lack of hosted auth**: Acceptable; record the SKIP reason in `evidence/test-transcripts/sync-status-check-coherent.txt`. The CI run on the PR will provide the live evidence path.

## Reviewer guidance

- Spot-check one transcript per WP to confirm it really exits 0.
- Spot-check one close comment to confirm verification block links to a transcript that exists in `evidence/test-transcripts/`.
- Verify the PR body replacement removes the stale "post-merge follow-up" claim, not just renames it.

## Implementation command

```bash
spec-kitty agent action implement WP05 --agent <name> --mission mvp-cli-sync-boundary-completion-01KRX11M
```

## Activity Log

- 2026-05-18T12:04:26Z – claude:opus-4.7:curator-carla:curator – shell_pid=15262 – Started implementation via action command
- 2026-05-18T12:12:59Z – claude:opus-4.7:curator-carla:curator – shell_pid=15262 – Closure evidence + sub-issue drafts + PR body update + DoD checklist ready
- 2026-05-18T12:13:35Z – claude:opus-4.7:reviewer-rita:reviewer – shell_pid=19931 – Started review via action command
- 2026-05-18T12:16:28Z – claude:opus-4.7:reviewer-rita:reviewer – shell_pid=19931 – Review passed: transcripts honest (92/92 targeted; mypy errors all pre-existing in non-mission files); close-NNNN drafts cite real commits + plausible line numbers; PR body update removes the stale post-merge follow-up; DoD documents the mypy carve-out; decision verifier clean.
