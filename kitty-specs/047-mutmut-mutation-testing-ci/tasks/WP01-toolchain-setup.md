---
work_package_id: WP01
title: Toolchain Setup
dependencies: []
requirement_refs:
- FR-001
- FR-002
- NFR-002
- C-001
- C-002
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Foundation
history:
- timestamp: '2026-03-01T16:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: ''
execution_mode: code_change
mission_id: 01KN2371WTANS0Z2M6JEHAJS3E
owned_files:
- kitty-specs/047-mutmut-mutation-testing-ci/plan.md
- kitty-specs/047-mutmut-mutation-testing-ci/quickstart.md
- kitty-specs/047-mutmut-mutation-testing-ci/research.md
- kitty-specs/047-mutmut-mutation-testing-ci/spec.md
- src/specify_cli/**
wp_code: WP01
---

# Work Package Prompt: WP01 – Toolchain Setup

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check `review_status`. If it says `has_feedback`, read `review_feedback` first.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*No feedback yet — this is a fresh work package.*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ` ```python `, ` ```bash `

---

## Objectives & Success Criteria

- `mutmut>=3.5.0` is listed in `[project.optional-dependencies].test` in `pyproject.toml`.
- A `[tool.mutmut]` section configures mutmut to target `src/specify_cli/` using the existing pytest runner.
- `mutmut.db` and related artifacts are excluded from version control.
- Running `mutmut run --paths-to-mutate src/specify_cli/status/` locally completes without configuration errors.
- `mutmut results` shows a summary with killed/surviving/timeout counts.

## Context & Constraints

- **Branch**: `architecture/restructure_and_proposals` (no worktree — work directly on this branch)
- **Spec**: `kitty-specs/047-mutmut-mutation-testing-ci/spec.md`
- **Plan**: `kitty-specs/047-mutmut-mutation-testing-ci/plan.md`
- **Research**: `kitty-specs/047-mutmut-mutation-testing-ci/research.md` — contains the confirmed pyproject.toml config format and CLI command sequence
- **Quickstart**: `kitty-specs/047-mutmut-mutation-testing-ci/quickstart.md` — local developer guide
- **Constraint C-001**: Must use `mutmut>=3.5.0` (3.x CLI; 2.x config is incompatible)
- **Constraint C-002**: Must use the existing pytest suite — no second test framework
- This WP is the foundation for all subsequent WPs. CI integration (WP02) depends on this being correct.

## Subtasks & Detailed Guidance

### Subtask T001 – Add mutmut to test dependencies

**Purpose**: Make mutmut installable via `pip install -e ".[test]"` so both CI and
local environments get the same version.

**Steps**:
1. Open `pyproject.toml`.
2. Locate the `[project.optional-dependencies]` section (around line 79).
3. Add `"mutmut>=3.5.0",` to the `test` array, alongside the existing pytest dependencies.
4. Keep the list sorted or grouped logically (mutation testing near the bottom of the test deps).

**Files**: `pyproject.toml`

**Validation**:
```bash
pip install -e ".[test]"
mutmut --version
# Should print: mutmut 3.x.x
```

---

### Subtask T002 – Add [tool.mutmut] configuration section

**Purpose**: Configure mutmut scope, runner, and exclusions declaratively in
`pyproject.toml` so local and CI runs use identical settings.

**Steps**:
1. Add the following section to `pyproject.toml` (after the existing tool sections):

```toml
[tool.mutmut]
paths_to_mutate = ["src/specify_cli/"]
runner = "python -m pytest -x --timeout=30 -q"
tests_dir = "tests/"
# Exclude migrations (idempotent, hard to unit-test meaningfully via mutation)
# and any generated/vendored files
exclude_patterns = [
    "src/specify_cli/upgrade/migrations/",
]
```

2. Verify the exact key names by running `mutmut --help` — if the toml key is
   different from `paths_to_mutate` or `exclude_patterns` in your installed
   version, use the actual keys reported by the CLI.
3. The runner uses `-x` (stop after first failure per mutant) and `--timeout=30`
   (per-test timeout) to keep mutant runs fast.

**Files**: `pyproject.toml`

**Notes**:
- `runner` is a shell command string. Mutmut passes a `--` separator and the test
  file paths automatically.
- If the `[tool.mutmut]` config section is not recognised by your mutmut version,
  fall back to a `setup.cfg` `[mutmut]` section (same keys, ini format). Document
  which approach you used in a comment.

---

### Subtask T003 – Update .gitignore for mutmut artifacts

**Purpose**: Keep mutmut's SQLite cache and generated files out of version control.

**Steps**:
1. Open `.gitignore`.
2. Find an appropriate section (near other tool caches) and add:

```gitignore
# mutmut mutation testing
mutmut.db
mutmut-cache/
.mutmut-cache
```

**Files**: `.gitignore`

**Validation**: After running `mutmut run` locally, confirm `git status` does not show
`mutmut.db` as an untracked file.

---

### Subtask T004 – Local verification run

**Purpose**: Confirm the configuration works end-to-end before CI is wired up.

**Steps**:
1. Install the updated dependencies:
   ```bash
   pip install -e ".[test]"
   ```
2. Run mutmut against a small, fast module to bound the verification time:
   ```bash
   mutmut run --paths-to-mutate src/specify_cli/status/transitions.py
   ```
3. Observe the output. It should show progress (mutant count, killed/survived).
4. If mutmut exits with a configuration error (e.g., "unknown key"), inspect the
   error and adjust `[tool.mutmut]` keys accordingly (see T002 notes).
5. If the run completes but takes >5 minutes for a single file, narrow scope to
   a smaller file for the verification step.

**Files**: None (runtime verification step)

**Notes**: This step is intentionally scoped to one file to keep it fast. The full
codebase run happens in CI (WP02).

---

### Subtask T005 – Confirm mutmut results output

**Purpose**: Verify that the results command works and its output is human-readable.

**Steps**:
1. After T004 completes, run:
   ```bash
   mutmut results
   ```
2. Confirm output lists mutant IDs with statuses (killed, survived, timeout).
3. Pick one surviving mutant ID and run:
   ```bash
   mutmut show <id>
   ```
4. Confirm the output shows a source diff (the mutated line vs. the original).

**Files**: None (verification step)

**Validation**:
- [ ] `mutmut results` shows at least one result line
- [ ] `mutmut show <id>` shows a readable diff
- [ ] No Python tracebacks or "command not found" errors

## Risks & Mitigations

- **mutmut 3.x config key mismatch**: If `[tool.mutmut]` is ignored, check `mutmut --help` for the config file format and adjust. Fallback: use `setup.cfg` `[mutmut]` section.
- **Very slow verification run**: Scope T004 to a single file (e.g., `status/transitions.py` — ~200 lines) to keep verification under 5 minutes.
- **pytest import errors during mutmut run**: If mutmut's subprocess can't find the package, ensure `pip install -e ".[test]"` ran before mutmut (editable install is required).

## Review Guidance

- Check that `pyproject.toml` has `mutmut>=3.5.0` in the test deps.
- Check that `[tool.mutmut]` section targets `src/specify_cli/` and uses `python -m pytest`.
- Check that `.gitignore` includes `mutmut.db`.
- Ask the implementer to paste the output of `mutmut results` as evidence of a successful run.

## Activity Log

- 2026-03-01T16:00:00Z – system – lane=planned – Prompt created.
- 2026-03-01T06:40:44Z – unknown – lane=in_progress – Starting WP01 implementation
- 2026-03-01T06:52:10Z – unknown – lane=done – T001-T005 complete, review fix applied. | Done override: No worktree model: all work committed directly to architecture/restructure_and_proposals per feature design decision
