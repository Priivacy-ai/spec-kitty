---
work_package_id: WP01
title: Excise curation surface
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-012
- FR-013
- FR-015
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-excise-doctrine-curation-and-inline-references-01KP54J6
base_commit: e34db6c821f8cdc59e27e6dc0a6f0739fc98b2dc
created_at: '2026-04-14T05:42:21.868672+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
shell_pid: "43987"
agent: "claude:opus-4.6:python-implementer:implementer"
history:
- at: '2026-04-14T05:02:32Z'
  actor: claude
  event: created
authoritative_surface: src/doctrine/curation/
execution_mode: code_change
owned_files:
- src/doctrine/curation/**
- src/doctrine/directives/_proposed/**
- src/doctrine/tactics/_proposed/**
- src/doctrine/procedures/_proposed/**
- src/doctrine/styleguides/_proposed/**
- src/doctrine/toolguides/_proposed/**
- src/doctrine/paradigms/_proposed/**
- src/specify_cli/cli/commands/doctrine.py
- src/specify_cli/cli/commands/__init__.py
- src/specify_cli/validators/doctrine_curation.py
- tests/doctrine/curation/**
- tests/cross_cutting/test_doctrine_curation_unit.py
- tests/specify_cli/cli/test_doctrine_cli_removed.py
- scripts/verify_occurrences.py
- kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/occurrences/**
tags: []
---

# WP01 — Excise curation surface

**Tracks**: [Priivacy-ai/spec-kitty#476](https://github.com/Priivacy-ai/spec-kitty/issues/476)
**Depends on**: — (first WP in the Phase 1 tranche)
**Merges to**: `main`

## Branch Strategy

- **Planning/base branch**: `main`
- **Merge target**: `main`
- **Execution mode**: lane-based worktree allocated by `finalize-tasks`. Run `spec-kitty agent action implement WP01 --agent <name> --mission excise-doctrine-curation-and-inline-references-01KP54J6` to resolve the actual workspace path and branch. Do NOT reconstruct the path by hand.

---

## Objective

Delete every file, package, CLI surface, validator, and test that implements the legacy `_proposed/` → `shipped/` doctrine curation workflow. After this WP merges, `src/doctrine/curation/` is gone, the `spec-kitty doctrine` Typer app is unregistered, all six `_proposed/` directories are gone, and a permanent regression test (`tests/specify_cli/cli/test_doctrine_cli_removed.py`) prevents reintroduction.

No fallback. No deprecation shim. No compatibility alias. Per spec C-001.

## Context

- EPIC: [#461](https://github.com/Priivacy-ai/spec-kitty/issues/461)
- Phase 1 tracking: [#463](https://github.com/Priivacy-ai/spec-kitty/issues/463)
- Guardrail reference: [#393](https://github.com/Priivacy-ai/spec-kitty/issues/393) — occurrence-classification pattern
- Current state of `_proposed/` on `main`: 5 directive YAMLs + 5 tactic YAMLs + empty `.gitkeep` placeholders across six kind-subtrees
- Current curation package: 3 modules (`engine.py`, `state.py`, `workflow.py`) + README + `imports/` examples
- Current CLI: `src/specify_cli/cli/commands/doctrine.py` (210 LOC) registered as `app.add_typer(doctrine_module.app, name="doctrine")` in `src/specify_cli/cli/commands/__init__.py`

## Authoritative files (read before starting)

- [spec.md](../spec.md) — FR-001, FR-002, FR-003, FR-004, FR-012, FR-013, FR-015; C-001, C-002, C-005, C-007
- [plan.md](../plan.md) — WP1.1 section + D-5 (occurrence artifact shape)
- [data-model.md](../data-model.md) — E-1 (Occurrence-Classification Artifact), E-2 (Mission-Level Index)
- [quickstart.md](../quickstart.md) — step-by-step workflow for this WP
- [contracts/occurrence-artifact.schema.yaml](../contracts/occurrence-artifact.schema.yaml) — artifact schema
- [contracts/removed-cli-surface.md](../contracts/removed-cli-surface.md) — CLI removal contract + regression test skeleton

---

## Subtask details

### T001 — Add verifier script + author `occurrences/WP01.yaml`

**Purpose**: Produce the mission-level tooling (`scripts/verify_occurrences.py`) and the WP01 occurrence-classification artifact BEFORE any deletion. The artifact is the spec for what the WP deletes; the verifier proves the WP is done.

**Steps**:

1. Create `scripts/verify_occurrences.py` per the sketch in [quickstart.md](../quickstart.md) "Verifier" section. It must:
   - Load an occurrence-classification YAML artifact.
   - For each category: iterate `strings`, grep `include_globs` respecting `exclude_globs` and `permitted_exceptions`.
   - Fail if the hit count does not equal `expected_final_count`.
   - Support both per-WP artifact shape and the mission-level `index.yaml` shape (detected by presence of `wps` key).
   - Emit a clear `VERIFIER GREEN` / `VERIFIER FAILED` message with hit details on failure.
   - Exit 0 on success, 1 on failure, 2 on usage error.

2. Create `kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/occurrences/` directory.

3. Author `kitty-specs/.../occurrences/WP01.yaml` per [contracts/occurrence-artifact.schema.yaml](../contracts/occurrence-artifact.schema.yaml).

   Mandatory categories for WP01:
   - `import_path`: the `from doctrine.curation import ...` and `from specify_cli.validators.doctrine_curation import ...` imports anywhere in `src/` or `tests/`
   - `symbol_name`: `ProposedArtifact`, `discover_proposed`, `promote_artifact_to_shipped`, `CurationSession`, `load_session`, `clear_session`, `run_curate_session`, `promote_single`, `get_status_counts`, `doctrine_module` (as Typer app alias)
   - `filesystem_path_literal`: `src/doctrine/curation`, `_proposed`
   - `cli_command_name`: `doctrine curate`, `doctrine promote`, `doctrine reset`, `doctrine status`
   - `template_reference`: prose references to the doctrine CLI subcommands in SOURCE templates (`src/specify_cli/missions/*/command-templates/`, `src/doctrine/*/README.md`, `src/charter/README.md`)
   - `test_identifier`: `tests/doctrine/curation/**`, `tests/cross_cutting/test_doctrine_curation_unit.py`

   Populate `to_change` entries by greping the live tree. Use the verifier script itself to confirm the pre-edit counts match what you put in `to_change`.

   `requires_merged: []` (WP01 is the first).

4. Also seed `kitty-specs/.../occurrences/index.yaml` as a placeholder with `wps: [WP01]` and the mission-level `must_be_zero` set per [data-model.md](../data-model.md) E-2. WP02 and WP03 will extend it.

**Files**:
- `scripts/verify_occurrences.py` (new, ~120 lines)
- `kitty-specs/.../occurrences/WP01.yaml` (new)
- `kitty-specs/.../occurrences/index.yaml` (new, placeholder-state)

**Validation**:
- [ ] `python scripts/verify_occurrences.py kitty-specs/.../occurrences/WP01.yaml` reports the pre-edit hits (VERIFIER FAILED expected — that's the "to-change" set).
- [ ] Artifact YAML conforms to `contracts/occurrence-artifact.schema.yaml` (optionally: validate by hand or with a ruamel.yaml round-trip + `jsonschema` check).

---

### T002 — Delete `src/doctrine/curation/`, `_proposed/` trees, and the curation candidate validator

**Purpose**: Remove the Python packages and doctrine directories that implement the curation workflow. This is the largest LOC reduction in the mission.

**Steps**:

1. Delete the entire curation package:
   ```bash
   rm -rf src/doctrine/curation/
   ```
   Removes: `engine.py` (~272 LOC), `state.py` (~161 LOC), `workflow.py` (~220 LOC), `README.md`, `imports/` (example import manifests).

2. Delete the curation candidate validator:
   ```bash
   rm -f src/specify_cli/validators/doctrine_curation.py
   ```
   Removes: ~165 LOC, one module.

3. Delete all six `_proposed/` trees:
   ```bash
   for kind in directives tactics procedures styleguides toolguides paradigms; do
     rm -rf "src/doctrine/${kind}/_proposed"
   done
   ```
   Removes: 5 populated directive proposals + 5 populated tactic proposals + 4 empty dirs with `.gitkeep` placeholders.

**Files affected**:
- Deleted: `src/doctrine/curation/` entire tree (5 files + imports subtree)
- Deleted: `src/specify_cli/validators/doctrine_curation.py`
- Deleted: 6 `_proposed/` directories with ~16 files total (including `.gitkeep`)

**Validation**:
- [ ] `test -d src/doctrine/curation` returns non-zero
- [ ] `test -f src/specify_cli/validators/doctrine_curation.py` returns non-zero
- [ ] `find src/doctrine -type d -name _proposed` returns no rows
- [ ] `mypy --strict src/` passes (failures here indicate a stale import — fix in T003 or T004)

---

### T003 — Delete `src/specify_cli/cli/commands/doctrine.py`, unregister Typer app, add regression test

**Purpose**: Remove the CLI adapter and prevent it from being re-registered in the future.

**Steps**:

1. Delete the CLI adapter:
   ```bash
   rm -f src/specify_cli/cli/commands/doctrine.py
   ```
   Removes: ~210 LOC, one Typer app definition with 4 subcommands (curate/status/promote/reset).

2. Edit `src/specify_cli/cli/commands/__init__.py`:
   - Remove the `from . import doctrine as doctrine_module` import line (or equivalent)
   - Remove the `app.add_typer(doctrine_module.app, name="doctrine")` registration line (line 53 in current `main`)
   - Do NOT touch any other registration — this file has many; only the `doctrine` one is targeted

3. Create `tests/specify_cli/cli/test_doctrine_cli_removed.py` per [contracts/removed-cli-surface.md](../contracts/removed-cli-surface.md):

   ```python
   """Regression test: `spec-kitty doctrine ...` must be an unknown command.

   This test prevents reintroduction of the curation CLI surface deleted in Phase 1.
   See EPIC #461 / Phase 1 issue #463.
   """
   from typer.testing import CliRunner
   from specify_cli.cli.app import app


   def test_doctrine_curate_is_unknown_command() -> None:
       runner = CliRunner()
       result = runner.invoke(app, ["doctrine", "curate"])
       assert result.exit_code != 0


   def test_doctrine_parent_group_is_unregistered() -> None:
       runner = CliRunner()
       result = runner.invoke(app, ["doctrine", "--help"])
       assert result.exit_code != 0


   def test_doctrine_promote_is_unknown_command() -> None:
       runner = CliRunner()
       result = runner.invoke(app, ["doctrine", "promote"])
       assert result.exit_code != 0
   ```

   Note: the import path `specify_cli.cli.app` matches the current project layout; verify with `grep -r "^app = typer.Typer" src/specify_cli/` before writing.

**Files affected**:
- Deleted: `src/specify_cli/cli/commands/doctrine.py`
- Modified: `src/specify_cli/cli/commands/__init__.py` (remove 2 lines)
- Created: `tests/specify_cli/cli/test_doctrine_cli_removed.py`

**Validation**:
- [ ] `grep -n "doctrine_module" src/specify_cli/cli/commands/__init__.py` returns no rows
- [ ] `grep -n "doctrine" src/specify_cli/cli/commands/__init__.py` returns no rows related to the command registration (other `doctrine` strings in comments must also be removed per R-3 audit)
- [ ] `pytest tests/specify_cli/cli/test_doctrine_cli_removed.py` passes
- [ ] `spec-kitty doctrine curate` on a dev-install (`pip install -e .` or `uv pip install -e .`) fails with unknown-command

---

### T004 — Delete curation test files

**Purpose**: Remove tests that exercise the deleted curation code. These tests are pure coverage of removed surfaces — no behavioral coverage is lost.

**Steps**:

1. Delete the curation test tree:
   ```bash
   rm -rf tests/doctrine/curation/
   ```
   Removes: `test_engine.py`, `conftest.py`, any other files under that subtree.

2. Delete the cross-cutting curation unit test:
   ```bash
   rm -f tests/cross_cutting/test_doctrine_curation_unit.py
   ```

**Files affected**:
- Deleted: `tests/doctrine/curation/` entire tree
- Deleted: `tests/cross_cutting/test_doctrine_curation_unit.py`

**Validation**:
- [ ] `find tests -path "*/curation/*"` returns no rows (except the mission-scoped occurrence artifacts, which are under `kitty-specs/`)
- [ ] `test -f tests/cross_cutting/test_doctrine_curation_unit.py` returns non-zero
- [ ] `pytest tests/` still runs to completion (green or with OTHER failures; the curation deletions themselves must not cause import errors)

**Parallel opportunity**: T004 is safe to run concurrently with T002/T003. Both just delete files.

---

### T005 — Update SOURCE templates + doctrine READMEs referencing removed surfaces

**Purpose**: Scrub SOURCE prose of references to deleted commands and paths so new projects instantiating spec-kitty don't see stale doctrine guidance.

**Steps**:

1. Grep SOURCE directories for removed surfaces:
   ```bash
   # Repo-root-relative
   grep -rn "doctrine curate\|doctrine promote\|doctrine reset\|doctrine status\|_proposed\|curation" \
     src/specify_cli/missions src/specify_cli/skills src/doctrine/*/README.md \
     2>/dev/null | grep -v 'kitty-specs/' | grep -v 'scripts/verify_occurrences.py'
   ```

2. For each hit, rewrite or remove the prose. Specific targets expected (not exhaustive):
   - `src/doctrine/*/README.md` — these may describe the `_proposed/` → shipped workflow; rewrite to say artifacts are authored directly in the shipped tree and cross-references live in `graph.yaml`
   - `src/charter/README.md` — the table at the top lists `compiler.py :: compile_charter()` and `resolver.py :: resolve_governance()`; these entries are correct now but will need a follow-up in WP03 when the resolver implementation changes. For WP01: touch only if it mentions the curation workflow or `_proposed/`.
   - `src/specify_cli/missions/software-dev/command-templates/*.md` and other mission command-templates — grep for mention of `doctrine` CLI commands; there should be few or none, but verify

3. **DO NOT EDIT** any file under these agent-copy directories:
   - `.claude/`, `.amazonq/`, `.augment/`, `.codex/`, `.cursor/`, `.gemini/`, `.github/prompts/`, `.kilocode/`, `.opencode/`, `.qwen/`, `.roo/`, `.windsurf/`

   These are generated copies; they re-flow from the SOURCE on the next `spec-kitty upgrade`.

**Files affected**:
- Modified: zero-to-many SOURCE prose files, depending on grep results. Most likely hits: 2-3 `README.md` files under `src/doctrine/`. No mission command-templates expected to reference doctrine CLI per specify-phase discovery.

**Validation**:
- [ ] Re-run the grep from step 1 — zero hits outside `kitty-specs/` and the verifier script
- [ ] `mypy --strict src/` still passes (no code change expected here, but sanity)
- [ ] Prose changes are cohesive — don't leave hanging references like "see the `_proposed` workflow"

**Parallel opportunity**: Independent of T002-T004.

---

### T006 — Run gates + seed `occurrences/index.yaml` with WP01 segment

**Purpose**: Verify all WP01 changes are coherent and the occurrence artifact accurately reflects the post-edit state, before opening the PR.

**Steps**:

1. Run the full test suite:
   ```bash
   pytest tests/
   ```
   All tests must pass. Expected new passing test: `tests/specify_cli/cli/test_doctrine_cli_removed.py`.

2. Run type checker:
   ```bash
   mypy --strict src/
   ```
   Must pass with zero errors.

3. Run the verifier:
   ```bash
   python scripts/verify_occurrences.py kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/occurrences/WP01.yaml
   ```
   Must output `VERIFIER GREEN for .../WP01.yaml`. If RED: the `to_change` list has un-addressed hits — go back and finish the deletion, or add a `permitted_exceptions` entry with a rationale if the hit is in fact intentional.

4. Update `kitty-specs/.../occurrences/index.yaml`:
   - Ensure `wps: [WP01]` is present
   - Ensure `must_be_zero` lists the WP01-scoped strings: `curation`, `_proposed`
   - Record any `permitted_exceptions` you added during T005 (e.g. the `m_3_1_1_charter_rename.py` migration is ALREADY a carve-out per spec C-006 — restate it here)

5. Run the verifier against the index too (it should pass for the WP01 subset):
   ```bash
   python scripts/verify_occurrences.py kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/occurrences/index.yaml
   ```
   Must output `VERIFIER GREEN`.

6. Prepare the PR body — paste the verifier output, mypy output, and pytest summary. Reference [#476](https://github.com/Priivacy-ai/spec-kitty/issues/476).

**Validation**:
- [ ] All three commands (pytest, mypy, verifier WP01.yaml, verifier index.yaml) are green
- [ ] `spec-kitty doctrine curate` on a dev-install returns unknown-command
- [ ] `find src/doctrine -type d -name _proposed` returns no rows
- [ ] `test -d src/doctrine/curation` returns non-zero

---

## Definition of Done

- All six subtasks (T001-T006) are marked complete in tasks.md
- `scripts/verify_occurrences.py` exists and is callable
- `kitty-specs/.../occurrences/WP01.yaml` exists and verifier reports `VERIFIER GREEN`
- `kitty-specs/.../occurrences/index.yaml` exists with `wps: [WP01]` + `must_be_zero` + WP01 permitted exceptions
- `src/doctrine/curation/` is fully deleted
- `src/specify_cli/cli/commands/doctrine.py` is deleted
- `src/specify_cli/validators/doctrine_curation.py` is deleted
- All six `_proposed/` directories under `src/doctrine/` are deleted
- `app.add_typer(doctrine_module.app, name="doctrine")` is gone from `src/specify_cli/cli/commands/__init__.py`
- `tests/specify_cli/cli/test_doctrine_cli_removed.py` exists and passes
- `tests/doctrine/curation/` is deleted
- `tests/cross_cutting/test_doctrine_curation_unit.py` is deleted
- Full pytest suite is green
- `mypy --strict src/` is clean
- SOURCE prose no longer references removed surfaces (verified by grep in T005)
- PR opened against `main`, body references #476, includes verifier + pytest output

## Risks & Reviewer Guidance

**Reviewer must check**:

1. **No agent-copy dirs edited**: `git diff --stat main...HEAD | grep -E '^\.(claude|amazonq|augment|codex|cursor|gemini|github|kilocode|opencode|qwen|roo|windsurf)/'` returns nothing. Any hit is a spec C-005 violation.

2. **Typer registration line cleanly removed**: only the `doctrine` registration line is deleted from `src/specify_cli/cli/commands/__init__.py`; other lines untouched.

3. **Occurrence artifact completeness**: the `to_change` list in WP01.yaml was empty when the verifier ran at T006 — but it is NOT empty at the start of T001. This confirms every planned deletion was actually executed.

4. **Regression test is durable**: `tests/specify_cli/cli/test_doctrine_cli_removed.py` imports the CLI via the canonical `specify_cli.cli.app.app` path so it survives future CLI restructures.

5. **No unrelated file modifications**: scope is tight. PR diff should be: deletions (curation package, CLI module, tests, `_proposed/`), one-line deletions in `__init__.py`, one new test file, one new verifier script, two new YAML artifacts under `kitty-specs/`.

**Common mistakes to avoid**:

- Editing agent-copy directories (C-005)
- Leaving a stale import in `__init__.py` after deleting `doctrine.py` (mypy catches this)
- Over-scoping by starting to edit schemas or models (that's WP02)
- Deleting `src/doctrine/graph.yaml` or `src/doctrine/drg/` — out of scope for this WP

## Escalation criteria

Stop and comment on [#476](https://github.com/Priivacy-ai/spec-kitty/issues/476) if:
- Typer command re-registration is discovered (string-based dispatch somewhere)
- A curation-import is found in a module outside `src/doctrine/` or `src/specify_cli/` (suggests wider blast radius than the specify-phase inventory captured)
- A test outside `tests/doctrine/curation/` or `tests/cross_cutting/test_doctrine_curation_unit.py` fails in a way that references curation APIs
- A SOURCE template references the curation workflow in a way that needs product-level rewriting, not just deletion (escalate for guidance rather than ad-lib rewriting)

## Activity Log

- 2026-04-14T05:42:22Z – claude:opus-4.6:python-implementer:implementer – shell_pid=43987 – Assigned agent via action command
- 2026-04-14T06:22:20Z – claude:opus-4.6:python-implementer:implementer – shell_pid=43987 – WP01 complete: curation package, _proposed/ trees, doctrine CLI, and curation tests deleted. Verifier green. Regression test added. Pytest and mypy clean.
