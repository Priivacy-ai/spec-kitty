---
work_package_id: WP07
title: CONTRACT_VERSION bump to 1.4.0
dependencies:
- WP03
- WP04
- WP05
- WP06
- WP08
requirement_refs:
- FR-011
- NFR-001
planning_base_branch: feat/design-phase-orchestrator-api-3837
merge_target_branch: feat/design-phase-orchestrator-api-3837
branch_strategy: Planning artifacts for this mission were generated on feat/design-phase-orchestrator-api-3837. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/design-phase-orchestrator-api-3837 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-design-phase-orchestrator-api-01M1HE6M
base_commit: 7a996ce7b78df18df59375982d4494e13ac280fc
created_at: '2026-09-03T08:04:27.954830+00:00'
subtasks:
- T033
- T034
- T035
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/orchestrator_api/envelope.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/orchestrator_api/envelope.py
- tests/specify_cli/orchestrator_api/test_contract_version.py
role: implementer
tags: []
tracker_refs: []
---

# WP07 — CONTRACT_VERSION bump to 1.4.0

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: (unset — select at implementation time)

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Bump `CONTRACT_VERSION` `"1.3.0"` → `"1.4.0"` in
`src/specify_cli/orchestrator_api/envelope.py:28`, with an inline
changelog comment naming all 11 new verbs, following the exact 1.2.0/1.3.0
precedent format already in this file.

## Context

This WP intentionally depends on WP03, WP04, WP05, WP06, and WP08 (every
verb-adding WP) — NOT just "runs after them chronologically," but
FUNCTIONALLY: it must name every verb's FINAL landed name in the
changelog comment, so it cannot be written correctly until all five are
known-complete. It does not depend on WP02 directly (WP02 adds no verb of
its own) or WP09 (docs land after this WP, documenting the bumped
version).

**MIN_PROVIDER_VERSION is UNCHANGED** (`envelope.py:29`, stays `"0.1.0"`)
— already ruled on in spec Clarification 4: this is a routine additive
minor bump, not a breaking provider-compatibility change.

**Precedent format** (`envelope.py:19-27`, do not deviate from this
style):
```python
# 1.1.0: start-implementation now allocates the real lane worktree...
# 1.2.0: added read-only ``resolve-workspace`` (#2337)... Purely additive.
# 1.3.0: ``transition`` accepts structured ``--review-result-json``...
CONTRACT_VERSION = "1.3.0"
```

## Subtask T033: RED — version/verb-list assertion test

**Purpose**: A genuine, non-vacuous ATDD test — `CONTRACT_VERSION` is
currently `"1.3.0"`, so a test pinning the new value and the new verb
names is authentically RED before this WP's change.

**Steps**:
1. Add (or extend, if `tests/specify_cli/orchestrator_api/` already has a
   `test_contract_version.py`-style file covering `contract-version` — grep
   first) a test asserting `contract-version --json`'s response `data`
   reports `"1.4.0"` AND that a fresh grep of `envelope.py`'s changelog
   comment block contains all 11 new verb names by their literal Typer
   command names (`specify`, `plan`, `tasks`, `check-prerequisites`,
   `record-analysis`, `open-decision`, `resolve-decision`,
   `defer-decision`, `cancel-decision`, `design-status`,
   `answer-decision`).
2. Since this test only inspects an in-memory Typer response
   (`contract-version --json`) and re-reads `envelope.py`'s own changelog
   comment text — no fixture-mission, no real git operations — mark it
   `pytestmark = [pytest.mark.fast]`, matching `test_commands_fail_closed.py`'s
   convention (`pytest.ini:25`). This is what makes `fast-tests-core-misc`'s
   specify-cli-rest shard (`-m "fast and not windows_ci and not
   regression"`) collect it; without a marker, neither `fast-tests-core-misc`
   nor `integration-tests-core-misc` (`-m 'not windows_ci and (git_repo or
   integration or architectural) and not timing and not regression'`) will
   collect the file. If extending an existing file rather than creating a
   new one, PRESERVE that file's existing `pytestmark` — do not re-derive
   or overwrite it.
3. Confirm RED on `planning_base_branch` (fails: version string is still
   `"1.3.0"`, changelog comment does not yet mention the new verbs).

**Files**: `tests/specify_cli/orchestrator_api/test_contract_version.py`
(new, ~20-40 lines) — grep `tests/specify_cli/orchestrator_api/` first for
an existing `test_contract_version.py`-style file covering
`contract-version`; reuse and extend it (preserving its `pytestmark`)
instead of creating a new file if one already exists. Either way this path
is WP07's declared test-file ownership — enforced via this WP's own
frontmatter `owned_files` (the field the commit-guard ownership check
reads at implementation time), also mirrored in `wps.yaml`'s
`owned_files` for consistency.

**Validation**: fails on `planning_base_branch`.

## Subtask T034: Bump version + changelog comment

**Purpose**: The actual bump.

**Steps**:
1. Change `CONTRACT_VERSION = "1.3.0"` to `CONTRACT_VERSION = "1.4.0"`.
2. Add a `# 1.4.0: ...` comment line above it, in the same style as the
   three existing entries, naming ALL 11 new verbs by their literal Typer
   command names and summarizing the two categories (design-phase
   scaffolding verbs `specify`/`plan`/`tasks`/`check-prerequisites`/
   `record-analysis`; decision-resolution verbs
   `open-decision`/`resolve-decision`/`defer-decision`/`cancel-decision`/
   `answer-decision`; plus the read-only `design-status` query verb) —
   "Purely additive", matching 1.2.0's own phrasing, since NFR-001
   guarantees zero change to the 10 existing verbs.
3. Do NOT touch `MIN_PROVIDER_VERSION`.

**Files**: `src/specify_cli/orchestrator_api/envelope.py` (~5-8 line diff).

**Validation**: T033's test passes.

## Subtask T035: Confirm unchanged provider version + re-run existing envelope/contract tests

**Purpose**: NFR-001 confirmation for the one file this mission bumps.

**Steps**:
1. Confirm `MIN_PROVIDER_VERSION == "0.1.0"` unchanged via the T033 test
   or a dedicated assertion.
2. Re-run any existing `envelope.py`/`contract-version` test coverage to
   confirm zero regression.

**Files**: none new — verification only.

**Validation**: green.

## Write-Scope / Adjacent Open PRs

`envelope.py` is touched by no other WP in this mission and by none of the
three adjacent open PRs (#3842, #3826, #3836) — no same-file overlap or
rebase-risk note applies to this WP.

## Definition of Done

- [ ] RED commit: version/verb-list test fails on `planning_base_branch`.
- [ ] `pytestmark = pytest.mark.fast` on the test file (new or extended;
      preserved, not re-derived, if the file already existed).
- [ ] `CONTRACT_VERSION` = `"1.4.0"`, changelog comment names all 11 new verbs.
- [ ] `MIN_PROVIDER_VERSION` unchanged (`"0.1.0"`).
- [ ] Existing envelope/contract-version test coverage green.
- [ ] `mypy --strict` / `ruff check` clean.

Run: `spec-kitty agent action implement WP07 --agent <name>`

## Risks

- **Premature authoring**: if this WP starts before WP03/04/05/06/08 have
  settled their FINAL verb names, the changelog comment risks naming a
  verb inconsistently with what actually landed — do not start T034 until
  all five dependency WPs report complete.

## Reviewer Guidance

- Confirm all 11 new verb names in the changelog comment exactly match the
  literal `@app.command(name=...)` strings landed in WP03-WP06/WP08 — a
  mismatched name here is a documentation-vs-code drift, easy to miss on a
  quick skim.
- Confirm `MIN_PROVIDER_VERSION` is untouched.
