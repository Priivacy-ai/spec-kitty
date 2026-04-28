---
work_package_id: WP04
title: '#846 — specify/plan auto-commit gates on substantive content'
dependencies: []
requirement_refs:
- FR-012
- FR-013
- FR-014
- FR-015
- FR-016
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-e2e-827-followups-01KQAJA0
base_commit: b63e107acf869b30ccca53a3664d336738c2f988
created_at: '2026-04-28T20:36:36.295618+00:00'
subtasks:
- T014
- T015
- T016
- T017
- T018
agent: "claude:sonnet:python-pedro:reviewer"
shell_pid: "86584"
history:
- at: '2026-04-28T19:59:16Z'
  actor: planner
  note: Initial work package created from /spec-kitty.tasks.
- at: '2026-04-28T20:30:00Z'
  actor: planner
  note: Revised to target the actual create-time commit-boundary bug; dropped byte-length OR per planning review.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/mission.py
execution_mode: code_change
mission_id: 01KQAJA02YZ2Q7SH5WND713HKA
mission_slug: charter-e2e-827-followups-01KQAJA0
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/missions/_substantive.py
- src/specify_cli/cli/commands/agent/mission.py
- src/specify_cli/missions/*/command-templates/specify.md
- src/specify_cli/missions/*/command-templates/plan.md
- tests/integration/test_specify_plan_commit_boundary.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the assigned profile:

```
/ad-hoc-profile-load python-pedro
```

This sets `role=implementer`, scopes editing to the `owned_files` declared above, and applies Python-specialist standards.

## Objective

Close the specify/plan commit-boundary defect at the right place. There are **two** Python auto-commit paths that contribute to this bug; this WP fixes both:

1. **`mission create`** today auto-commits the empty `spec.md` scaffold. We observed this concretely while building this very mission. **Fix**: stop committing `spec.md` from `mission create`. Empty scaffolds remain untracked at create time; the agent commits the populated content from the `/spec-kitty.specify` slash-template (existing behavior).
2. **`setup-plan`** today writes `plan.md` and auto-commits it without checking that `spec.md` is committed-and-substantive, and without checking that `plan.md` itself is substantive. **Fix**: add an entry-time gate (spec must be committed AND substantive) and gate the existing `_commit_to_branch(plan_file, …)` call on `is_substantive(plan, "plan")`. On either failure, emit `phase_complete=False` with a `blocked_reason` and do not write or commit `plan.md`.

Per Constraint **C-007**, this WP MUST NOT silently delete or rewrite existing substantive content; it only changes the auto-commit decision boundary and the surfaced workflow state.

## Substantive-content definition (revised — section-presence only)

`is_substantive(file_path, kind)` returns True iff the file contains real, non-template-placeholder content for that artifact kind. **There is no byte-length OR fallback.** A file that is "empty scaffold + 300 bytes of arbitrary prose" is NOT substantive. Pure section-presence is the only signal.

| kind | Required signal |
|---|---|
| `spec` | At least one Functional Requirements row with an `FR-\d{3}` ID followed by non-empty description content. The row must NOT consist entirely of template placeholders (`[NEEDS CLARIFICATION …]`, `[e.g., …]`). |
| `plan` | A populated Technical Context section where `Language/Version` (and at least one peer field) contains a real value, NOT a placeholder. |

See [`contracts/specify-plan-commit-boundary.md`](../contracts/specify-plan-commit-boundary.md) and [`research.md`](../research.md) R7 (revised) for the rationale.

## Context (verified in source)

- `mission.py` around line 333 has a `safe_commit(repo_path=..., files_to_commit=[file_path], commit_message=...)` call that happens during `mission create`. Today this call's `files_to_commit` includes `spec.md`. The fix removes `spec.md` from that list.
- `mission.py` around line 973 has `_commit_to_branch(plan_file, mission_slug, "plan", repo_root, target_branch, json_output)` — that's the `setup-plan` exit auto-commit for `plan.md`.
- `mission setup-plan --json` returns a structured payload that downstream tools and dashboards use to decide if the spec/plan phase is "ready". Today, the payload reports success even when the file is empty.
- Contract for this fix: [`contracts/specify-plan-commit-boundary.md`](../contracts/specify-plan-commit-boundary.md) and [`data-model.md`](../data-model.md) (INV-846-1, INV-846-2, INV-846-3, INV-846-4).
- Research decision: see [`research.md`](../research.md) R7 (revised: section-presence only) and R8 (gate placement at create + setup-plan entry + setup-plan exit).

## Detailed guidance per subtask

### Subtask T014 — Implement `_substantive` helpers

**Purpose**: Two pure helpers that the gate logic in T015/T016 calls.

**Steps**:

1. Create a new module `src/specify_cli/missions/_substantive.py`.
2. Module structure (section-presence only — no byte-length OR):
   ```python
   """Substantive-content gate for spec/plan auto-commit (#846)."""
   from __future__ import annotations
   import re
   import subprocess
   from pathlib import Path
   from typing import Literal

   Kind = Literal["spec", "plan"]

   _PLACEHOLDER_PATTERNS = (
       re.compile(r"\[NEEDS CLARIFICATION[^\]]*\]"),
       re.compile(r"\[e\.g\.,[^\]]*\]"),
       re.compile(r"\[FEATURE\]"),
       re.compile(r"\[###-feature[^\]]*\]"),
   )

   def _strip_placeholders(s: str) -> str:
       for p in _PLACEHOLDER_PATTERNS:
           s = p.sub("", s)
       return s

   def _has_substantive_fr_row(body: str) -> bool:
       """Return True iff body contains at least one FR-### row with real content."""
       # Look for table rows like: | FR-001 | <description> | ...
       # A row qualifies if there is at least one non-whitespace token in the
       # description column AFTER stripping known template placeholders.
       fr_row = re.compile(r"\|\s*FR-\d{3}\s*\|\s*(?P<desc>[^|]+)\|")
       for m in fr_row.finditer(body):
           desc = _strip_placeholders(m.group("desc")).strip()
           if desc:
               return True
       return False

   def _has_substantive_technical_context(body: str) -> bool:
       """Return True iff Technical Context section has real (non-placeholder) values."""
       # Find the "## Technical Context" section
       section = re.search(
           r"##\s+Technical Context\s*\n(?P<body>.*?)(?=\n##\s+|\Z)",
           body,
           flags=re.DOTALL,
       )
       if not section:
           return False
       sec_body = _strip_placeholders(section.group("body"))
       # A populated Technical Context has at least one bold field with a value
       # that survives placeholder stripping.
       # Heuristic: look for "**Language/Version**: <something non-empty>".
       lang = re.search(r"\*\*Language/Version\*\*\s*:\s*(?P<val>[^\n]+)", sec_body)
       if not lang or not lang.group("val").strip():
           return False
       return True

   def is_substantive(file_path: Path, kind: Kind) -> bool:
       """Section-presence-only substantive-content gate."""
       body = file_path.read_text(encoding="utf-8")
       if kind == "spec":
           return _has_substantive_fr_row(body)
       elif kind == "plan":
           return _has_substantive_technical_context(body)
       else:
           raise ValueError(f"Unknown kind: {kind!r}")

   def is_committed(file_path: Path, repo_root: Path) -> bool:
       """Return True iff file is git-tracked AND present at HEAD."""
       rel = file_path.relative_to(repo_root)
       try:
           subprocess.run(
               ["git", "-C", str(repo_root), "ls-files", "--error-unmatch", str(rel)],
               check=True, capture_output=True,
           )
           subprocess.run(
               ["git", "-C", str(repo_root), "cat-file", "-e", f"HEAD:{rel}"],
               check=True, capture_output=True,
           )
           return True
       except subprocess.CalledProcessError:
           return False
   ```
3. `mypy --strict` clean.

**Files**: `src/specify_cli/missions/_substantive.py` (new, ~100–140 lines including docstring).

**Validation**:
- [ ] `is_substantive(<empty-scaffold spec.md>, "spec")` returns False.
- [ ] `is_substantive(<scaffold with only `[NEEDS CLARIFICATION …]` filler>, "spec")` returns False.
- [ ] `is_substantive(<spec with one populated FR-001 row>, "spec")` returns True.
- [ ] `is_substantive(<scaffold with 300 bytes of arbitrary prose but NO FR row>, "spec")` returns **False** (no byte-length escape hatch).
- [ ] `is_substantive(<plan with placeholder Technical Context>, "plan")` returns False.
- [ ] `is_substantive(<plan with populated Language/Version>, "plan")` returns True.
- [ ] `is_committed(<tracked file at HEAD>, repo_root)` returns True.
- [ ] `is_committed(<untracked file>, repo_root)` returns False.
- [ ] `is_committed(<staged-but-not-committed file>, repo_root)` returns False.

### Subtask T015 — `mission create` boundary fix

**Purpose**: Stop `mission create` from auto-committing the empty `spec.md` scaffold.

**Steps**:

1. Open `src/specify_cli/cli/commands/agent/mission.py`.
2. Locate the `mission create` command's `safe_commit(...)` call (around line 333). Inspect `files_to_commit` — today it likely includes both `meta.json` and `spec.md` (and possibly other scaffolding).
3. Modify the call so `spec.md` is **excluded** from `files_to_commit`. Keep `meta.json` and any other genuinely-scaffolding files. Update the commit message to reflect the change (e.g. "Add meta and scaffolding for feature ...").
4. Document the change with a short comment:
   ```python
   # spec.md is intentionally NOT committed here. The agent commits the populated
   # spec.md from the /spec-kitty.specify slash-template after writing substantive
   # content. See kitty-specs/charter-e2e-827-followups-01KQAJA0/contracts/specify-plan-commit-boundary.md
   ```
5. Verify the empty scaffold remains on disk (the file is still written; only the commit changes).
6. Per Constraint C-007: do not delete or rewrite existing files; only adjust the commit list.

**Files**: `src/specify_cli/cli/commands/agent/mission.py` (modified, small surgical change ~5–10 lines).

**Validation**:
- [ ] After `spec-kitty agent mission create "test-mission"`, `git log --oneline -1` shows a commit that includes `meta.json` but NOT `spec.md`.
- [ ] `spec.md` exists on disk (untracked).
- [ ] No regression in existing mission-create tests; if any test asserts "spec.md is committed at create time", update its expectation (the new behavior is correct).

### Subtask T016 — `setup-plan` entry + exit gates

**Purpose**: Apply the substantive-and-committed check at the start of `setup-plan` and gate the existing plan auto-commit at the end.

**Steps**:

1. Open `src/specify_cli/cli/commands/agent/mission.py` and locate the `setup-plan` command.
2. **Entry gate** — at the top of `setup-plan`, before any plan.md write or commit:
   ```python
   from specify_cli.missions._substantive import is_substantive, is_committed

   spec_path = feature_dir / "spec.md"
   if not is_committed(spec_path, repo_root) or not is_substantive(spec_path, "spec"):
       payload = {
           "result": "blocked",
           "phase_complete": False,
           "blocked_reason": (
               "spec.md must be committed AND substantive before setup-plan can run. "
               "Populate the Functional Requirements (at least one FR-### row), "
               "commit spec.md, then re-run setup-plan."
           ),
           # ... include any other already-populated fields ...
       }
       return payload  # do NOT write or commit plan.md
   ```
3. **Exit gate** — replace the existing `_commit_to_branch(plan_file, mission_slug, "plan", repo_root, target_branch, json_output)` call (around line 973) with:
   ```python
   if is_substantive(plan_file, "plan"):
       _commit_to_branch(plan_file, mission_slug, "plan", repo_root, target_branch, json_output)
       payload["phase_complete"] = True
   else:
       payload["phase_complete"] = False
       payload["blocked_reason"] = (
           "plan.md content is not substantive yet; populate Technical Context with real values "
           "(not template placeholders) and re-run setup-plan to commit."
       )
       # do NOT commit
   ```
4. Ensure the `mission setup-plan --json` output reflects `phase_complete` consistently in both branches. If existing payload keys conflict with the new `phase_complete` shape, align — the gate's contract is the new authority.
5. Per Constraint C-007: do not delete or rewrite existing populated content. Only the COMMIT decision and the returned payload change.

**Files**: `src/specify_cli/cli/commands/agent/mission.py` (modified, ~30–50 changed lines).

**Validation**:
- [ ] After `mission create` (which no longer commits spec.md), `setup-plan` returns `phase_complete=False` with a blocked_reason naming "committed AND substantive".
- [ ] After the agent populates spec.md but does NOT commit it, `setup-plan` still returns `phase_complete=False` (uncommitted leg).
- [ ] After the agent commits a substantive spec.md, `setup-plan` writes `plan.md` from template. If `plan.md` is left as template, the exit gate returns `phase_complete=False` (unsubstantive-plan leg).
- [ ] After the agent populates plan.md with real Technical Context, re-running `setup-plan` commits plan.md and returns `phase_complete=True`.
- [ ] No silent overwrite or deletion of existing content.

### Subtask T017 — Mission templates + regression test

**Purpose**: Document the commit boundary in templates and lock the gate in with integration coverage.

**Steps**:

1. **Templates** — locate command templates under `src/specify_cli/missions/<mission-type>/command-templates/`. There are templates for both `specify.md` and `plan.md` per supported mission type (e.g., `software-dev`, `research`).
2. To each touched template, add a short "Commit Boundary" subsection (~10–15 lines) explaining:
   - Why the workflow may refuse to commit `spec.md`/`plan.md` at certain points.
   - What "substantive content" means operationally for this artifact (FR rows for spec; populated Technical Context for plan).
   - How to advance: populate substantive content; for spec, commit it (the slash-template instructs the agent); for plan, the workflow auto-commits once substantive.
   - Cross-reference [`contracts/specify-plan-commit-boundary.md`](../contracts/specify-plan-commit-boundary.md).
3. **Important**: per CLAUDE.md, edit the SOURCE templates under `src/specify_cli/missions/`, NOT the agent copies under `.claude/`, `.amazonq/`, etc.
4. **Regression test** — create `tests/integration/test_specify_plan_commit_boundary.py` with five scenarios from the contract:
   - (a) `mission create` does NOT commit spec.md (meta.json IS committed).
   - (b) Uncommitted populated spec.md → setup-plan blocks with "committed AND substantive".
   - (c) Committed but scaffold-only spec.md → setup-plan blocks with substantive-spec reason.
   - (d) Committed substantive spec + populated plan → setup-plan commits plan.md and returns phase_complete=True.
   - (e) Same as (d) but plan left as template → setup-plan returns phase_complete=False with substantive-plan reason.
5. Use isolated temp git repos / temp mission scaffolds. Do NOT pollute the real `kitty-specs/` tree during tests.
6. Mirror existing integration-test patterns for spec-kitty CLI invocation.

**Files**: `src/specify_cli/missions/<mission-type>/command-templates/specify.md` and `plan.md` (modified, multiple files; ~10–15 lines added per file). `tests/integration/test_specify_plan_commit_boundary.py` (new, ~250–320 lines).

**Validation**:
- [ ] All five regression-test scenarios pass.
- [ ] Reverting T015 (mission-create change) makes scenario (a) fail.
- [ ] Reverting T016 entry gate makes scenarios (b)/(c) fail.
- [ ] Reverting T016 exit gate makes scenario (e) fail.
- [ ] No agent-copy directory was modified.

### Subtask T018 — Verify integration filter

**Purpose**: Confirm no collateral regressions in adjacent tests.

**Steps**:

1. Run:
   ```bash
   uv run pytest tests/integration -k 'specify or plan or auto_commit or mission' -q
   ```
2. All filtered tests pass.
3. If any unrelated test fails because it depended on `mission create` auto-committing spec.md, fix the test's expectations — the new behavior is correct.
4. Run `uv run pytest tests/specify_cli/cli/commands/agent -q` and confirm.

**Validation**:
- [ ] Filtered integration suite is green.
- [ ] `tests/specify_cli/cli/commands/agent` is green.

## Branch strategy

- **Planning/base branch**: `main`.
- **Final merge target**: `main`.
- **Execution worktree**: lane D per the tasks.md plan; assigned by `finalize-tasks`.

## Definition of Done

- [ ] `src/specify_cli/missions/_substantive.py` exists with `is_substantive()` (section-presence only — no byte-length OR) and `is_committed()`.
- [ ] `mission create` no longer commits `spec.md`. Only `meta.json` and other genuine scaffolding files are committed at create time. The empty `spec.md` remains on disk untracked.
- [ ] `setup-plan` has an entry gate enforcing committed-AND-substantive `spec.md`, and an exit gate enforcing substantive `plan.md`. Both emit `phase_complete=False / blocked_reason` on failure and skip the relevant commit.
- [ ] `mission setup-plan --json` payload reflects the gate state accurately.
- [ ] Mission templates under `src/specify_cli/missions/<mission-type>/command-templates/` document the commit boundary.
- [ ] `tests/integration/test_specify_plan_commit_boundary.py` covers all five scenarios above, including the "scaffold + arbitrary prose stays NON-substantive" case.
- [ ] `uv run pytest tests/integration -k 'specify or plan or auto_commit or mission' -q` passes.
- [ ] `uv run pytest tests/specify_cli/cli/commands/agent -q` passes.
- [ ] No edits to agent-copy directories (`.claude/`, `.amazonq/`, etc.).
- [ ] `mypy --strict` clean.
- [ ] Only files in this WP's `owned_files` list were modified.

## Implementation command

```bash
spec-kitty agent action implement WP04 --agent claude --mission charter-e2e-827-followups-01KQAJA0
```

## Reviewer guidance

- **Section-presence only**. If the implementer adds a byte-length OR (or any other "if file is large enough, commit" branch), reject — that is the rejected design (research R7 revised).
- **Both gates**. The fix is at THREE places: `mission create` (no spec.md commit), `setup-plan` entry (spec must be committed AND substantive), `setup-plan` exit (plan must be substantive). Missing any of the three is incomplete.
- **No agent-copy edits**. `.claude/`, `.amazonq/`, etc. are generated. Source templates only.
- **Legacy missions**. After this fix lands, missions whose `spec.md` was already committed empty by the pre-fix `mission create` will be reported as incomplete by the new entry gate until the agent populates and re-commits them. That is correct behavior — surface this in the PR description.

## Requirement references

- **FR-012** (auto-commit only when substantive — applies at create-time and setup-plan-exit).
- **FR-013** (block clearly when not substantive; do not silently auto-commit).
- **FR-014** (workflow state does not falsely advance — entry gate at setup-plan reads committed-AND-substantive).
- **FR-015** (regression coverage defines the boundary).
- **FR-016** (PR closeout language — informational; the implementer ensures commit messages match the FR-016 closeout style).
- **C-007** (no silent deletion/rewrite of existing content).
- Contributes to **NFR-003** (verification matrix).

## Activity Log

- 2026-04-28T20:50:48Z – claude – shell_pid=73767 – WP04 ready for review: mission-create no-empty-spec + setup-plan entry/exit gates + templates + 5 regression scenarios
- 2026-04-28T20:51:30Z – claude:sonnet:python-pedro:reviewer – shell_pid=86584 – Started review via action command
- 2026-04-28T20:55:23Z – claude:sonnet:python-pedro:reviewer – shell_pid=86584 – Review passed: section-presence-only is_substantive; three gates wired (create + setup-plan entry + exit); 5 regression scenarios + 300-byte-prose negative; templates documented; mission_creation.py scope deviation justified by inaccurate prompt pointer; FR-012/013/014/015/016 met; C-007 honored.
