---
work_package_id: WP06
title: 'Charter fresh-project flow: generate auto-track + synthesize (#841 + #839)'
dependencies:
- WP01
requirement_refs:
- FR-013
- FR-014
- FR-015
planning_base_branch: release/3.2.0a6-tranche-2
merge_target_branch: release/3.2.0a6-tranche-2
branch_strategy: Planning artifacts for this feature were generated on release/3.2.0a6-tranche-2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into release/3.2.0a6-tranche-2 unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
- T032
- T033
- T034
- T035
agent: "claude:opus-4-7:default:implementer"
shell_pid: "48813"
history:
- at: '2026-04-28T09:30:00Z'
  by: spec-kitty.tasks
  note: Created as part of tranche-2 specify→plan→tasks pipeline
authoritative_surface: src/specify_cli/cli/commands/charter.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/charter.py
- src/specify_cli/cli/commands/charter_bundle.py
- tests/specify_cli/cli/commands/test_charter_generate_autotrack.py
- tests/integration/test_charter_synthesize_fresh.py
tags: []
---

# WP06 — Charter fresh-project flow: generate auto-track + synthesize (#841 + #839)

## Branch Strategy

- **Planning/base branch**: `release/3.2.0a6-tranche-2`
- **Final merge target**: `release/3.2.0a6-tranche-2`
- Lane A, position 2 (after WP01). Implementation command: `spec-kitty agent action implement WP06 --agent claude`.

## Objective

On a fresh project (post-WP01), `charter generate` produces an artifact set that `charter bundle validate` accepts without any intervening `git add`. On a fresh project with no hand-seeded `.kittify/doctrine/`, `charter synthesize` runs successfully via the public CLI path.

## Context

Combines GitHub issues #841 and #839 because both target the same fresh-project chain and share the `cli/commands/charter.py` editing surface.

- **#841** decision (Spec Assumption A1): `charter generate` auto-tracks (stages) the produced `charter.md` so `bundle validate` succeeds. In a non-git environment, `generate` fails fast with an actionable error.
- **#839** decision (Spec Assumption A2): `charter synthesize` runs via the public CLI path on a fresh project; no offline/test adapter; the existing public surface produces whatever doctrine artifacts the runtime needs from canonical inputs (`charter.md` + in-package canonical doctrine seed).

**FRs**: FR-013, FR-014, FR-015 · **NFRs**: covered via integration tests · **SC**: SC-006, SC-007, SC-001 (component) · **Spec sections**: Scenarios 6 and 7, Domain Language ("Charter bundle parity") · **Data shape**: [data-model.md §5, §6](../data-model.md)

## Always-true rules

- After `charter generate` on a fresh git repo, the produced `charter.md` is **tracked** (staged) so `bundle validate` accepts it without any operator command.
- `charter generate` outside a git repo exits non-zero with an actionable error string (per FR-014 fail-fast).
- `charter synthesize` on a fresh project completes via the public CLI without hand-seeded doctrine.
- `synthesize` is idempotent.

---

## Subtask T029 — `charter generate` auto-tracks `charter.md` on success in a git repo

**Purpose**: Close the parity gap with `charter bundle validate`.

**Steps**:

1. Open `src/specify_cli/cli/commands/charter.py`. Locate the `generate` command's success path — the moment after the artifact set is written to disk.
2. Use the existing git helper (likely `specify_cli.git.safe_commit` or a sibling `safe_add`; check the codebase) to **stage** the produced files. Stage, do not commit — staging is sufficient for `bundle validate`.
3. The staging set includes at minimum `.kittify/charter/charter.md` and any other files `generate` writes that `bundle validate` checks.
4. Use the existing tracked-files helper (or `git ls-files --stage`) for verification, not an ad-hoc subprocess call.

**Files to edit**:
- `src/specify_cli/cli/commands/charter.py`

**Acceptance**:
- After `generate`, `git ls-files --stage <produced files>` returns a non-empty stage entry for each.

---

## Subtask T030 — `charter generate` fails fast in a non-git environment

**Purpose**: Avoid silent inconsistency with `bundle validate`.

**Steps**:

1. In the same `generate` command, before performing any side effect, check whether the cwd is inside a git working tree (existing helper or `subprocess.run(["git", "rev-parse", "--is-inside-work-tree"])`).
2. If not, exit non-zero with a clear, actionable error message such as:
   ```
   Error: charter generate requires a git repository. Initialize one with `git init`,
   or follow the documented offline charter setup at <path or doc link>.
   ```
3. The error string MUST contain the words `git` and `init` (verifiable in the test).

**Files to edit**:
- `src/specify_cli/cli/commands/charter.py`

---

## Subtask T031 — `charter synthesize`: identify minimal doctrine artifact set

**Purpose**: Bound the scope of T032 before changing code.

**Steps**:

1. Read the existing `charter synthesize` implementation in `src/specify_cli/cli/commands/charter.py`. List every artifact it currently writes when the inputs are present (procedures, tactics, directives, guidelines, action index, etc.).
2. Read `DoctrineService` (per CLAUDE.md governance section). List every artifact the runtime expects to exist after synthesize.
3. Cross-reference: the **minimal artifact set** is the intersection — things synthesize must write so the runtime stops failing on a fresh project.
4. Document this set in a comment at the top of the synthesize implementation, citing #839.

**Output**: an explicit minimal artifact list (4–8 files probably). This is a **boundary** for T032 — changes outside this set are out of scope.

---

## Subtask T032 — `charter synthesize`: produce artifacts from canonical inputs on a fresh project

**Purpose**: Make the public CLI work without hand-seeded doctrine.

**Steps**:

1. Modify the synthesize implementation to accept the fresh-project case:
   - Inputs available: `charter.md` (post-WP01 + post-T029) and the in-package canonical doctrine seed (already shipped with `spec-kitty`).
   - Required outputs: the minimal artifact set from T031.
2. If today the implementation requires pre-seeded `.kittify/doctrine/`, replace that requirement with a path that pulls the canonical seed from the package data (use `importlib.resources` for type safety; do not read files outside the package).
3. **Boundary**: do not introduce any new doctrine subsystem, new charter product features, or new public CLI subcommands. The change is bounded to "make the existing public surface succeed on a fresh project".
4. If the change feels like it requires more than a localized fix, **escalate** before merging — Risk Map "scope expansion" mitigation applies.

**Files to edit**:
- `src/specify_cli/cli/commands/charter.py`

---

## Subtask T033 — Idempotency: synthesize twice yields identical output set

**Purpose**: Lock in stable behavior.

**Steps**:

1. After T032 lands, run `synthesize` twice in the unit test setup; collect file lists and contents.
2. Add an assertion that all output files are bytewise-equal between runs (modulo any timestamps already in pre-existing artifacts).
3. If a timestamp leak is found, isolate it (e.g., a "generated_at" field) and use a stable value (e.g., a git-derived hash or omit) so idempotency holds in tests.

**Files to edit**:
- `src/specify_cli/cli/commands/charter.py` (only if a stability fix is required)
- The test added in T035

---

## Subtask T034 — Integration test: fresh repo, `generate → bundle validate` succeeds  [P]

**Purpose**: Lock in the #841 parity contract.

**Steps**:

1. Create `tests/specify_cli/cli/commands/test_charter_generate_autotrack.py`.
2. Tests:
   - `test_generate_then_bundle_validate_succeeds_in_fresh_git_repo`: in `tmp_path` initialised as a git repo, run `init` (relies on WP01) → `charter setup` → `charter generate` → `charter bundle validate`. Assert all exit 0 with no manual `git add` between the latter two.
   - `test_generate_in_non_git_dir_fails_fast`: in a `tmp_path` that is NOT a git repo, run `charter generate`. Assert non-zero exit, stderr (or stdout for non-`--json` mode) contains both `git` and `init`.
   - `test_generate_stages_produced_files`: after success, assert `git ls-files --stage` includes `.kittify/charter/charter.md`.

**Files to create**:
- `tests/specify_cli/cli/commands/test_charter_generate_autotrack.py` (~140 lines)

---

## Subtask T035 — Integration test: synthesize on fresh project produces expected set  [P]

**Purpose**: Lock in the #839 contract.

**Steps**:

1. Create `tests/integration/test_charter_synthesize_fresh.py`.
2. Tests:
   - `test_synthesize_on_fresh_project_via_public_cli`: in `tmp_path` initialised as a git repo with `init` → `charter setup` → `charter generate` (no hand seeding of `.kittify/doctrine/`), run `charter synthesize`. Assert exit 0 and the minimal artifact set from T031 is present under `.kittify/doctrine/`.
   - `test_synthesize_is_idempotent`: run `synthesize` twice; assert directory listings and file contents are equal.
   - `test_synthesize_without_charter_md_fails_actionably`: pre-condition: no `charter.md`. Assert non-zero exit with an actionable error string.

**Files to create**:
- `tests/integration/test_charter_synthesize_fresh.py` (~150 lines)

---

## Test Strategy

- **Integration**: T034 + T035 cover the user-visible contracts end-to-end.
- **Coverage**: ≥ 90% on changed code in `charter.py` (NFR-002).
- **Type safety**: `mypy --strict` clean.
- **No SaaS**: tests gate any SaaS-touching subcommand with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` (per C-003) — though `charter` flow itself should be local.

## Definition of Done

- [ ] T029 — `charter generate` auto-tracks `charter.md`.
- [ ] T030 — non-git environment exits non-zero with actionable error.
- [ ] T031 — minimal doctrine artifact set documented inline.
- [ ] T032 — synthesize works on a fresh project via public CLI.
- [ ] T033 — synthesize is idempotent.
- [ ] T034 — auto-track integration tests pass.
- [ ] T035 — fresh-project synthesize integration tests pass.
- [ ] `mypy --strict` clean.
- [ ] No new public CLI subcommand (SC-008).

## Risks

- **Risk**: Auto-staging `charter.md` surprises operators who deliberately keep it untracked.
  **Mitigation**: Document the new behavior in CHANGELOG (WP07's job) + governance setup docs (WP07).
- **Risk**: `synthesize` change cascades into a doctrine-subsystem refactor.
  **Mitigation**: T031 sets a bounded artifact list; T032 explicitly forbids new doctrine subsystems. **Escalate** if scope expands.
- **Risk**: Idempotency violation due to a timestamp in synthesized output.
  **Mitigation**: T033 surfaces and fixes any such leak.
- **Risk**: `bundle validate` checks something beyond `charter.md` (e.g., a manifest); auto-track misses it.
  **Mitigation**: T029 stages every file `generate` produces; T034 asserts via real `bundle validate` call.

## Reviewer guidance

- Read `bundle validate` carefully — does it check anything besides `charter.md`? If so, those files MUST also be auto-tracked.
- Verify the non-git error string is **actionable** (names the remediation).
- Verify the minimal artifact set in T031 is documented in code; future maintainers must know the boundary.
- Confirm idempotency test runs synthesize twice and diffs output bytewise.

## Out of scope

- New charter product features.
- A test-only adapter for synthesize (Spec Assumption A2 forbids it).
- Auto-commit (we auto-track / stage, not commit).
- Migration for projects whose `charter.md` is already untracked but valid.

## Activity Log

- 2026-04-28T10:26:38Z – claude:opus-4-7:default:implementer – shell_pid=48813 – Started implementation via action command
- 2026-04-28T10:41:29Z – claude:opus-4-7:default:implementer – shell_pid=48813 – WP06 ready: charter generate auto-tracks + non-git fail-fast + synthesize on fresh project + idempotency + tests
