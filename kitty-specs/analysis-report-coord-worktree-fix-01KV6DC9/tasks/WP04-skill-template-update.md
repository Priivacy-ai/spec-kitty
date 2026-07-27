---
work_package_id: WP04
title: spec-kitty.analyze Skill Source Template Update
dependencies: []
requirement_refs:
- FR-006
tracker_refs: []
planning_base_branch: fix/analysis-report-coord-worktree-fix
merge_target_branch: fix/analysis-report-coord-worktree-fix
branch_strategy: Planning artifacts for this mission were generated on fix/analysis-report-coord-worktree-fix. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/analysis-report-coord-worktree-fix unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-analysis-report-coord-worktree-fix-01KV6DC9
base_commit: 2c350ed220b107a1890e6b22a9b24d4e63b685df
created_at: '2026-06-15T20:56:28.286974+00:00'
subtasks:
- T016
- T017
- T018
- T019
agent: claude
shell_pid: '6829'
history:
- event: created
  at: '2026-06-15T19:57:30Z'
  actor: architect-alphonso
agent_profile: curator-carla
authoritative_surface: src/doctrine/missions/mission-steps/software-dev/analyze/
create_intent: []
execution_mode: code_change
owned_files:
- src/doctrine/missions/mission-steps/software-dev/analyze/prompt.md
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load curator-carla
```

---

## Objective

Add a caution block to step 7 ("Persist Report Artifact") in the `spec-kitty.analyze`
skill **source template** at
`src/doctrine/missions/mission-steps/software-dev/analyze/prompt.md`.

This closes the documentation gap that led agents to write `analysis-report.md` directly
in carrier format — the manual-write workaround that issue #1989 describes.

**Canonical-source scope**: Edit ONLY the source template. Agent-directory copies
(`.claude/`, `.agents/skills/`, etc.) are generated downstream in consumer projects via
`spec-kitty upgrade`. This source repo does not carry per-agent analyze copies, so this WP
does not run `spec-kitty upgrade` and does not own or modify any agent directory.

**This WP is independent of WP01–WP03 and can be developed in parallel.**

## Branch Strategy

- **Planning/execution branch**: `fix/analysis-report-coord-worktree-fix`
- **Merge target**: `fix/analysis-report-coord-worktree-fix`
- Run: `spec-kitty agent action implement WP04 --agent claude`

## Context

### Source file location

`src/doctrine/missions/mission-steps/software-dev/analyze/prompt.md`

This is the **canonical source**. Agent-directory copies are generated from it.
Do NOT edit `.claude/commands/`, `.agents/skills/`, or any other generated copy directly.

### Current step 7 (relevant excerpt)

```markdown
### 7. Persist Report Artifact

Save the Markdown report body to `kitty-specs/<mission>/analysis-report.md` by running
the recorder with a temp report file outside the repository checkout:

```bash
spec-kitty agent mission record-analysis --mission <mission-slug> --input-file <path-to-temp-report.md> --json
```

If your host supports piping reliable multiline stdin, this equivalent form is acceptable:

```bash
spec-kitty agent mission record-analysis --mission <mission-slug> --input-file - --json
```

The report file you pass MUST start with the `analysis-findings/v1` carrier from step 6. ...

Treat persistence failure as command failure. The command is not complete until the JSON
response reports success and names `analysis-report.md`.
```

### What to add

Append a caution block **after** the last paragraph of step 7 and **before** the next
section heading (### 8. ...). The caution block should be:

```markdown
> **⚠️ Caution — Do not write `analysis-report.md` directly**
>
> The `analysis-findings/v1` carrier (step 6) is the **input format** for `record-analysis`,
> not the **persisted format**. `record-analysis` wraps the carrier in the outer-wrapper
> format (`artifact_type: spec-kitty.analysis-report`) that the implement gate accepts.
>
> Writing `analysis-report.md` directly — without piping through `record-analysis` — leaves
> the file in carrier format, which the implement gate rejects with `carrier_format_not_wrapped`.
> If this happens, recover by running:
> ```bash
> spec-kitty agent mission record-analysis --mission <mission-slug> --input-file analysis-report.md --json
> ```
```

### Terminology constraint

Do NOT use the word `feature` in the caution block. Use `mission` consistently.
Run `pytest tests/architectural/test_no_legacy_terminology.py` to verify.

## Subtask Guidance

### T016 — Append caution block to step 7 of `analyze/prompt.md`

**Purpose**: Document the carrier-vs-wrapper distinction at the point where agents
are instructed to persist the report.

**Steps**:

1. Open `src/doctrine/missions/mission-steps/software-dev/analyze/prompt.md`.

2. Locate step 7's closing paragraph ("Treat persistence failure as command failure...").

3. After that paragraph, before the next `###` heading, insert the caution block
   shown above in the Context section (verbatim, including the warning emoji and
   the `> **⚠️ Caution...` blockquote formatting).

4. Verify the inserted text:
   - Uses `mission` (not `feature`)
   - References `carrier_format_not_wrapped` as the error code agents will see
   - Provides the exact recovery command with `--input-file analysis-report.md`
   - Does not introduce any lines that would trigger the terminology guard

**Files**: `src/doctrine/missions/mission-steps/software-dev/analyze/prompt.md`

**Validation**:
- [ ] Caution block is present immediately after "Treat persistence failure..." paragraph
- [ ] No use of forbidden term `feature` in the added text
- [ ] Markdown blockquote formatting (`>`) is correct (renders as a callout)
- [ ] `grep -n "feature" src/doctrine/missions/mission-steps/software-dev/analyze/prompt.md` returns only pre-existing occurrences (not the new block)

---

### T017 — Verify the rendered source edit

**Purpose**: Confirm the caution block is correctly placed and well-formed in the
source template. **Scope note**: In this (the spec-kitty source) repository, only the
source template is edited and committed. Agent-directory copies are generated downstream
in consumer projects when they run `spec-kitty upgrade` — do NOT run `spec-kitty upgrade`
here or commit agent-directory copies, as that is outside this WP's ownership and the
source repo does not carry per-agent analyze copies.

**Steps**:

1. Confirm the caution block lands in step 7, after the persistence-failure paragraph
   and before the next `###` heading:
   ```bash
   grep -n "Caution" src/doctrine/missions/mission-steps/software-dev/analyze/prompt.md
   grep -n "carrier_format_not_wrapped" src/doctrine/missions/mission-steps/software-dev/analyze/prompt.md
   ```

2. Confirm the blockquote formatting is intact (lines start with `>`):
   ```bash
   sed -n '/Caution — Do not write/,/^$/p' src/doctrine/missions/mission-steps/software-dev/analyze/prompt.md
   ```

**Files**: `src/doctrine/missions/mission-steps/software-dev/analyze/prompt.md` (read-only verification)

**Validation**:
- [ ] `grep` finds the caution block in the source template
- [ ] `grep` finds `carrier_format_not_wrapped` referenced in the recovery guidance
- [ ] The block renders as a blockquote (every line of the callout starts with `>`)

---

### T018 — Confirm no agent-directory copies were edited

**Purpose**: Enforce the canonical-source rule — the only file changed by this WP is the
source template. Agent copies must NOT be hand-edited.

**Steps**:

1. Verify the working tree shows exactly one changed source file for this WP:
   ```bash
   git status --short src/doctrine/missions/mission-steps/software-dev/analyze/prompt.md
   git status --short .cursor .github .opencode
   ```

2. The agent directories (`.cursor`, `.github`, `.opencode`) must show NO modifications
   attributable to this WP. If they do, revert them — they are generated artifacts.

**Files**: Read-only verification

**Validation**:
- [ ] Only `src/doctrine/.../analyze/prompt.md` is modified for this WP
- [ ] No agent-directory files are hand-edited

---

### T019 — Run architectural and template-cleanliness tests

**Purpose**: Verify the template change does not introduce terminology violations
or break the command-template cleanliness gate.

**Steps**:

1. Run the terminology guard:
   ```bash
   pytest tests/architectural/test_no_legacy_terminology.py -v
   ```

2. Run the command-template cleanliness test:
   ```bash
   pytest tests/specify_cli/test_command_template_cleanliness.py -v
   ```

3. If either test fails:
   - For terminology violations: remove the offending word from the caution block
     (most likely `feature` — replace with `mission`)
   - For cleanliness failures: check the test output for the specific assertion that
     failed; it usually points to a formatting or structure issue in the template

**Files**: Read-only test runs

**Validation**:
- [ ] `pytest tests/architectural/test_no_legacy_terminology.py -v` exits 0
- [ ] `pytest tests/specify_cli/test_command_template_cleanliness.py -v` exits 0

---

## Definition of Done

- [ ] T016: Caution block appended to step 7 of `analyze/prompt.md` (correct format, no terminology violations)
- [ ] T017: Source edit verified — caution block present, well-formed blockquote, references `carrier_format_not_wrapped`
- [ ] T018: No agent-directory copies hand-edited (canonical-source rule upheld)
- [ ] T019: `test_no_legacy_terminology.py` and `test_command_template_cleanliness.py` pass

## Risks

- **Terminology guard**: The word `feature` must not appear in the new caution block. Always use `mission`.
- **Canonical source only**: Edit ONLY the source template. Agent-directory copies are generated downstream in consumer projects via `spec-kitty upgrade`; this source repo does not carry per-agent analyze copies, so never run `spec-kitty upgrade` as part of this WP nor commit agent-directory changes.

## Reviewer Guidance

- Verify the source template edit is the ONLY change (no edits to `.cursor`, `.github`, `.opencode`, or any agent copy).
- Check the caution block appears as a blockquote (`>`) in the rendered Markdown, not as plain prose.
- Confirm `test_no_legacy_terminology.py` passes in CI.
