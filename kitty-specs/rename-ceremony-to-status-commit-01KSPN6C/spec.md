# Spec: Rename Ceremony Commit to Status Commit

**Mission**: `rename-ceremony-to-status-commit-01KSPN6C`
**Friendly Name**: Rename Ceremony Commit to Status Commit
**Mission Type**: software-dev
**Source**: [GitHub Issue #1325](https://github.com/Priivacy-ai/spec-kitty/issues/1325)
**Created**: 2026-05-28

---

## Purpose

### TLDR

Replace the opaque term "ceremony commit" with "status commit" across spec-kitty source, tests, doctrine, docs, and glossary. Reconcile the partially-landed alternative term "status-writing" to the same canonical "status commit" phrasing so the codebase converges on a single term.

### Context

The codebase uses "ceremony" and "ceremony commit" to describe auto-commits spec-kitty creates for workflow state changes (status transitions, task metadata, lane claims). This terminology obscures intent for new contributors who must guess what a "ceremony" is. A prior partial rename inside `src/specify_cli/git/commit_helpers.py` replaced "ceremony" with "status-writing" in the user-facing error message and surrounding docstrings, but the issue's prescribed canonical term is "status commit". This mission therefore has two reconciliation surfaces: (1) replace remaining "ceremony" occurrences outside `commit_helpers.py`, and (2) bring `commit_helpers.py`'s "status-writing" phrasings into alignment with the canonical "status commit" term. The work is a pure terminology rename: no commands, flags, file formats, or commit policies change semantically.

### Live-state findings (recorded at spec time, 2026-05-28)

A repo-wide grep at spec time established the following live state. The plan phase will re-grep to produce the authoritative `occurrence_map.yaml`.

- `src/specify_cli/git/commit_helpers.py` no longer contains "ceremony" — it was partially renamed to "status-writing operations" / "status commits" / "status-writing commands" in a recent commit. The user-facing error string reads `"Run status-writing operations from the mission lane branch/worktree."` and must be reconciled to use the canonical "status commit" phrasing.
- The config flag `vcs.allow_ceremony_commits_on_target_branch` was **not found in live code**; it exists only as a proposal in the F-09 findings doc. The rename therefore touches only that doc, with no compat-alias work needed.
- Remaining "ceremony" occurrences in the active surface are in 11 files: 3 doctrine docs (`src/doctrine/procedures/README.md`, `src/doctrine/missions/software-dev/actions/tasks/guidelines.md`, `src/doctrine/skills/spec-kitty-program-orchestrate/SKILL.md`), 3 test files (`tests/doctrine/procedures/conftest.py`, `tests/doctrine/procedures/test_models.py`, `tests/e2e/conftest.py`), 4 documentation files (`docs/development/org-doctrine-layer-architecture-review.md`, `docs/development/3-2-publication-checklist.md`, `docs/engineering_notes/reflections/README.md`, `docs/engineering_notes/finding/2026-05-24-mission-01KSAF14-orchestration-findings.md`), and the architectural baseline (`tests/architectural/_baselines.yaml`).

---

## User Scenarios & Testing

### Primary Scenario: New contributor reads an error

**Actor**: A new contributor running `spec-kitty` for the first time.
**Trigger**: They attempt a workflow-state-changing command (status transition, task update, lane claim) while checked out on a protected branch.
**Current outcome**: Error reads "Run ceremony write operations from the mission lane branch/worktree." The contributor must ask in chat or grep the repo to learn what a "ceremony" is.
**Desired outcome**: Error reads "Run status commit operations from the mission lane branch/worktree." The contributor immediately understands the message refers to spec-kitty's auto-commits for workflow state.

### Secondary Scenario: Contributor reads a doctrine or skill document

**Actor**: A contributor reading `src/doctrine/skills/spec-kitty-program-orchestrate/SKILL.md` or related doctrine.
**Trigger**: They encounter the phrase "full ceremony" or "specify/plan/tasks ceremony" while learning the system.
**Desired outcome**: The phrase has been replaced with "status commit" (or, where the prose meant "the full multi-phase workflow", a non-ceremony rewording), and the term resolves cleanly against the canonical glossary entry.

### Tertiary Scenario: Term-checker / linter run

**Actor**: A linter or term-checker run by CI or a contributor before push.
**Trigger**: A new patch reintroduces the word "ceremony" in `src/`, `tests/`, or `docs/`.
**Desired outcome**: The glossary lists "ceremony commit" as a deprecated synonym, so any future term-checker that consumes the glossary can flag the regression with a useful pointer to the canonical term "status commit".

### Acceptance Scenarios

1. Running `grep -rn 'ceremony' src/ tests/ docs/ --include='*.py' --include='*.md' --include='*.yaml'` against the merged branch returns **zero hits** (artifacts under `kitty-specs/` are explicitly out of scope and excluded from this grep).
2. Running `grep -rn 'status-writing' src/ tests/ docs/ --include='*.py' --include='*.md' --include='*.yaml'` against the merged branch returns **zero hits** (the partially-landed alternative term is reconciled to "status commit").
3. The protected-branch error message produced by `assert_not_protected_branch()` reads exactly: `"Run status commit operations from the mission lane branch/worktree."`
4. The glossary file `.kittify/glossaries/spec_kitty_core.yaml` contains an active canonical entry for `status commit` and deprecation entries that pair both `ceremony commit` and `status-writing operation` with the canonical replacement.
5. The full test suite (`pytest`) passes against the rename, including renamed fixture IDs, function names, and branch-name constants.
6. `mypy --strict` passes against the rename (no signature drift).
7. The F-09 findings doc references the corrected proposed flag name `vcs.allow_status_commits_on_target_branch`. No code-level config-flag rename is required because the flag does not exist in live code (confirmed at spec time, 2026-05-28).

### Edge Cases

- **Path-only occurrences**: The user's local checkout path `spec-kitty-dev/ceremony/spec-kitty` contains the word but is a local directory naming choice, not a source artifact. Out of scope.
- **Historical mission artifacts**: Files under `kitty-specs/<past-mission>/` may reference "ceremony" in past planning documents. These are immutable history and are out of scope.
- **This mission's own artifacts**: This `spec.md`, the forthcoming `plan.md`, `tasks.md`, and `occurrence_map.yaml` legitimately mention "ceremony" while describing the rename itself. The acceptance grep excludes `kitty-specs/` so these do not block the gate.
- **Commit messages in git history**: Past commit messages contain "ceremony". Not rewriteable; out of scope.
- **Engineering notes referencing dated findings**: `docs/engineering_notes/finding/2026-05-24-mission-01KSAF14-orchestration-findings.md` contains 5 occurrences including a proposed config flag name. The proposed name `vcs.allow_ceremony_commits_on_target_branch` must be updated to `vcs.allow_status_commits_on_target_branch` in this note even if the flag itself does not yet exist in code.

---

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | Replace every active-source occurrence of "ceremony" / "ceremony commit" / "ceremony commands" / "ceremony write operations" with the corresponding "status commit" phrasing, across `src/`, `tests/`, `docs/`, `src/doctrine/`, and architectural baselines. | Active |
| FR-002 | Reconcile every active-source occurrence of the partially-landed alternative phrasing "status-writing" (operations / commands / commits) in `src/specify_cli/git/commit_helpers.py` (and any other file the plan-phase grep surfaces) to the canonical "status commit" phrasing. | Active |
| FR-003 | The error string raised by `assert_not_protected_branch()` in `src/specify_cli/git/commit_helpers.py` reads exactly: `Run status commit operations from the mission lane branch/worktree.` (currently reads `Run status-writing operations from the mission lane branch/worktree.`) | Active |
| FR-004 | Docstrings on `ProtectedBranchCommitError`, `protected_branches()`, and `assert_not_protected_branch()` in `src/specify_cli/git/commit_helpers.py`, plus the test-mode bypass comment, reference "status commit" consistently (no "status-writing", no "ceremony"). | Active |
| FR-005 | Test fixture identifiers and function names that currently embed `ceremony` (e.g., `E2E_CEREMONY_BRANCH`, `_checkout_e2e_ceremony_branch`, `mission-merge-ceremony`) are renamed to their `status-commit` / `status_commit` equivalents. All callers and assertions are updated together. | Active |
| FR-006 | `.kittify/glossaries/spec_kitty_core.yaml` gains a canonical entry for `status commit` with the definition: "An auto-commit created by spec-kitty to record workflow state changes (task status transitions, lane metadata, WP claims). Status commits target lane branches, not protected branches." | Active |
| FR-007 | The glossary marks both `ceremony commit` and `status-writing operation` as deprecated synonyms that resolve to `status commit`, so future linters and term-checkers can flag regressions on either old term. | Active |
| FR-008 | Doctrine and skill documents (`src/doctrine/procedures/README.md`, `src/doctrine/missions/software-dev/actions/tasks/guidelines.md`, `src/doctrine/skills/spec-kitty-program-orchestrate/SKILL.md`) replace ceremony phrasing with status-commit phrasing or, where the prose described a multi-phase workflow rather than a commit class, a clear non-ceremony rewording. | Active |
| FR-009 | Engineering-notes and development docs (`docs/development/org-doctrine-layer-architecture-review.md`, `docs/development/3-2-publication-checklist.md`, `docs/engineering_notes/reflections/README.md`, `docs/engineering_notes/finding/2026-05-24-mission-01KSAF14-orchestration-findings.md`) replace ceremony phrasing with status-commit phrasing. | Active |
| FR-010 | The proposed config-flag name `vcs.allow_ceremony_commits_on_target_branch` is rewritten to `vcs.allow_status_commits_on_target_branch` in the F-09 findings document only. The flag does not exist in live code (confirmed at spec time, 2026-05-28), so no compat alias and no code-side rename are required. | Active |
| FR-011 | The architectural baseline comment in `tests/architectural/_baselines.yaml` (line 17) referencing "ceremony" is rewritten in terms of "status commit". | Active |
| FR-012 | The mission produces an `occurrence_map.yaml` enumerating every active-source occurrence of "ceremony" and "status-writing" with its file, line, surrounding context, and the exact replacement text, classified per the bulk-edit guardrail. | Active |
| FR-013 | After the rename lands, running `grep -rn 'ceremony' src/ tests/ docs/ --include='*.py' --include='*.md' --include='*.yaml'` from the repo root returns zero hits. | Active |
| FR-014 | After the rename lands, running `grep -rn 'status-writing' src/ tests/ docs/ --include='*.py' --include='*.md' --include='*.yaml'` from the repo root returns zero hits. | Active |

---

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Behavioral fidelity: the rename does not alter runtime behavior of any command, hook, helper, or test assertion beyond the literal string substitution. | 100% of pre-rename functional tests pass post-rename without behavioral edits. | Active |
| NFR-002 | Type-check cleanliness: signature and identifier renames keep the codebase type-safe. | `mypy --strict` passes with zero new errors. | Active |
| NFR-003 | Lint cleanliness: no new lint findings introduced by the rename. | `ruff check .` passes with zero new findings. | Active |
| NFR-004 | Bulk-edit guardrail compliance: every occurrence in the active-source surface appears in `occurrence_map.yaml` and is reviewed against the diff before merge. | 100% of diff lines that touch a ceremony→status-commit occurrence are represented in `occurrence_map.yaml`. | Active |
| NFR-005 | Test runtime regression budget: the test suite running time after rename does not grow more than 5% versus pre-rename baseline (no accidental new I/O or slow setup). | ≤5% wall-clock delta on the same machine. | Active |

---

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | Files under `kitty-specs/` (historical mission artifacts) are out of scope and must not be modified by this mission. This includes prior plans, specs, and tasks documents that reference "ceremony". | Active |
| C-002 | The user's local working-directory path (`spec-kitty-dev/ceremony/spec-kitty`) is out of scope; it is a local checkout naming choice, not a repository artifact. | Active |
| C-003 | Git history (past commit messages, tags, release notes for past releases) is not rewritten. Only files-at-HEAD are in scope. | Active |
| C-004 | Behavior, command surface, file formats, and commit policy must not change. This is a terminology rename only. If a config key with the old name exists in live code, the plan phase decides between hard-rename and compat-alias before any code is touched. | Active |
| C-005 | The mission is classified as a bulk edit (`change_mode: bulk_edit`). An `occurrence_map.yaml` must be produced and approved during the plan phase before implementation begins; the implement-review loop verifies diff coverage against that map. | Active |
| C-006 | The canonical replacement is "status commit" (two words, lowercase) in prose; identifier renames use the conventional case for the surrounding code (`status_commit` in Python identifiers, `STATUS_COMMIT` in constants, `status-commit` in branch names and fixture IDs). | Active |

---

## Success Criteria

1. A new contributor reading the protected-branch error message understands within one sentence what kind of write operation triggered it (no need to search the repo for "ceremony").
2. A `grep -rn 'ceremony' src/ tests/ docs/ --include='*.py' --include='*.md' --include='*.yaml'` performed against the merged branch returns zero hits.
3. The glossary contains exactly one canonical entry for "status commit" and one deprecation entry mapping "ceremony commit" → "status commit"; any future term-checker that consumes the glossary can detect a regression on the old term.
4. The full test suite passes after the rename with no behavioral test edits beyond identifier renames.
5. `mypy --strict` and `ruff check .` both pass against the merged branch with no new findings attributable to the rename.

---

## Domain Language

**Canonical terms used in this spec:**

| Canonical term | Definition | Synonyms to avoid |
|----------------|------------|-------------------|
| status commit | An auto-commit created by spec-kitty to record workflow state changes (task status transitions, lane metadata, WP claims). Status commits target lane branches, not protected branches. | ceremony commit, ceremony write, ceremony, status-writing operation, status-writing command |
| protected branch | A branch (typically `main`) on which status commits are rejected; spec-kitty enforces that workflow auto-commits land on the mission lane branch/worktree instead. | — |
| occurrence map | A YAML artifact produced during the plan phase of a bulk-edit mission. Enumerates every active-source occurrence of the renamed term with its file, line, context, and replacement text. Used by the implement-review loop to verify diff coverage. | — |

---

## Key Entities

- **Glossary file**: `.kittify/glossaries/spec_kitty_core.yaml`. Contains canonical-term entries and deprecation entries. Single source of truth for project terminology.
- **Protected-branch helper module**: `src/specify_cli/git/commit_helpers.py`. Owns the `ProtectedBranchCommitError`, `protected_branches()`, and `assert_not_protected_branch()` surface; the error string here is the user-facing anchor for the rename.
- **Engineering finding F-09**: `docs/engineering_notes/finding/2026-05-24-mission-01KSAF14-orchestration-findings.md`. Proposed the config-flag name that this mission must rewrite from `vcs.allow_ceremony_commits_on_target_branch` to `vcs.allow_status_commits_on_target_branch`.
- **Architectural baseline**: `tests/architectural/_baselines.yaml`. Referenced in the issue's acceptance list; comment near line 17 needs a wording update.
- **Occurrence map (planning artifact)**: `kitty-specs/rename-ceremony-to-status-commit-01KSPN6C/occurrence_map.yaml` (to be produced during the plan phase).

---

## Assumptions

1. The issue's enumerated file list is comprehensive but not authoritative: a fresh repo-wide grep during the plan phase will be used to build `occurrence_map.yaml` for both "ceremony" and "status-writing" and may surface additional active-source occurrences not listed in the issue body.
2. The config-flag check has been performed at spec time: `vcs.allow_ceremony_commits_on_target_branch` does not exist in live code, only in the F-09 findings doc. The plan phase will re-confirm with a fresh grep; expected outcome is that only the F-09 doc is updated.
3. Doctrine prose that uses "ceremony" to mean "the full multi-phase workflow" (rather than the commit class) is reworded to a non-ceremony phrasing during the rename rather than mechanically substituted with "status commit". Examples: `src/doctrine/skills/spec-kitty-program-orchestrate/SKILL.md` "full ceremony" likely becomes "the full mission workflow" or similar.
4. Renaming Python identifiers (constants, fixtures, helper functions) is acceptable because they are internal to spec-kitty's own codebase; no external consumers import these symbols.
5. The mission lands as a single PR against `main`; bulk-edit guardrail review applies to the consolidated diff.

---

## Out of Scope

- Rewriting git history (past commits, tags).
- Modifying historical mission artifacts under `kitty-specs/`.
- Changing any runtime behavior, command surface, file format, or commit policy.
- Renaming the user's local checkout directory path.
- Introducing new linters or term-checkers as part of this mission (the glossary deprecation entry is the hook future tooling can build on, but the tooling itself is a separate mission).
