---
work_package_id: WP10
title: External Workflow Filters and Validation
dependencies:
- WP09
requirement_refs:
- FR-014
- FR-015
planning_base_branch: feat/080-ci-hardening-and-lint-cleanup
merge_target_branch: feat/080-ci-hardening-and-lint-cleanup
branch_strategy: Planning artifacts for this feature were generated on feat/080-ci-hardening-and-lint-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/080-ci-hardening-and-lint-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T051
- T052
- T053
- T054
- T055
history:
- date: '2026-04-09'
  action: created
  actor: claude-sonnet-4-6
authoritative_surface: .github/workflows/orchestrator-boundary.yml
execution_mode: code_change
owned_files:
- .github/workflows/orchestrator-boundary.yml
- .github/workflows/check-spec-kitty-events-alignment.yml
tags: []
---

# WP10 — External Workflow Filters and Validation

## Objective

Add path filters to `orchestrator-boundary.yml` and `check-spec-kitty-events-alignment.yml`
so these workflows only run when their relevant source files change. Coordinate the branch
protection required-checks update with the repository owner. Validate the full migration
end-to-end.

After this WP, all FR-010–FR-015 acceptance criteria are satisfied and `quality-gate` passes
on `main`.

## Context

**Why this WP exists (FR-014, FR-015):** Two secondary workflow files run unconditionally on
every PR. They are expensive for unrelated changes. Path filters will scope them correctly.

**Pre-condition (C-001 — highest risk item):** Branch protection required checks must remain
satisfied throughout the migration. Before making any changes in this WP, confirm with the
repository owner which jobs are in the required checks list and coordinate the transition.
This is a human coordination step, not a code change.

**Doctrine:** DIRECTIVE_001 (architectural integrity — workflow structure must match
architectural boundaries).

**This WP is part of Batch 3 (sequential after WP09).**

## Subtask Guidance

### T051 — Confirm current required-checks list with repo owner (pre-merge gate)

**This is a coordination task, not a code change.**

Before implementing T052–T053, you need to know:
1. Which CI job names are currently required branch-protection checks?
2. Are the old monolithic `fast-tests-core` and `integration-tests-core` listed as required?
3. Are any of the new per-module job names listed as required (they should NOT be yet —
   WP09 added shim jobs for all of them as a safety measure)?

**Process:**
```bash
# List current branch protection settings (requires repo write access):
gh api repos/{owner}/{repo}/branches/main/protection \
  --jq '.required_status_checks.contexts[]'
```

If you have access, review the list and:
- Identify which check names correspond to the old monolithic jobs
- Note which check names will need to be updated or added for the new per-module jobs

**Output of this task:** A list of required-check job names, recorded as a comment in the
commit message for T052/T053. If the required-checks list cannot be confirmed (e.g., access
denied), document the blocker and proceed with a conservative approach: assume ALL jobs
that existed before are required, ensure WP09 shim jobs cover all of them.

---

### T052 — Add path filter to `orchestrator-boundary.yml` (FR-014)

**File:** `.github/workflows/orchestrator-boundary.yml`

Read the current `on:` trigger section. Add `paths:` to scope it to only run when the
orchestrator_api source or tests change:

```yaml
on:
  pull_request:
    branches: [main, develop, "2.x"]
    paths:
      - 'src/specify_cli/orchestrator_api/**'
      - 'src/specify_cli/core/**'   # if orchestrator_api depends on core
      - 'tests/orchestrator_api/**'
      - '.github/workflows/orchestrator-boundary.yml'
  push:
    branches: [main, develop, "2.x"]
    paths:
      - 'src/specify_cli/orchestrator_api/**'
      - 'src/specify_cli/core/**'
      - 'tests/orchestrator_api/**'
      - '.github/workflows/orchestrator-boundary.yml'
```

Read the current workflow to understand what it tests before adding the paths filter.
The paths list should include all source directories whose changes would require this workflow
to run.

**Validation:**
```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/orchestrator-boundary.yml'))"
```
YAML must parse without error.

---

### T053 — Add path filter to `check-spec-kitty-events-alignment.yml` (FR-015)

**File:** `.github/workflows/check-spec-kitty-events-alignment.yml`

This workflow verifies alignment between the spec-kitty event schema and the `sync` module's
event handling. It should run only when `sync/**`, `pyproject.toml` (event package version
changes), or the workflow file itself changes:

```yaml
on:
  pull_request:
    branches: [main, develop, "2.x"]
    paths:
      - 'src/specify_cli/sync/**'
      - 'pyproject.toml'
      - '.github/workflows/check-spec-kitty-events-alignment.yml'
  push:
    branches: [main, develop, "2.x"]
    paths:
      - 'src/specify_cli/sync/**'
      - 'pyproject.toml'
      - '.github/workflows/check-spec-kitty-events-alignment.yml'
```

Read the workflow before editing to verify the path assumptions above are correct.

**Validation:**
```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/check-spec-kitty-events-alignment.yml'))"
```

---

### T054 — Validate docs-only PR behavior via draft PR

**Validation scenario (FR-010, FR-011, NFR-001):**

Open a draft PR with ONLY documentation changes to verify path filtering works end-to-end.

**How to validate:**
1. Create a test branch with only a markdown change:
   ```bash
   git checkout -b test/docs-only-validation
   echo "<!-- validation test -->" >> docs/some-doc.md
   git add docs/some-doc.md
   git commit -m "test: docs-only CI validation"
   git push origin test/docs-only-validation
   ```
2. Open a draft PR against `main`.
3. Observe the CI checks:
   - Python test jobs (`fast-tests-*`, `integration-tests-*`) should be SKIPPED or not triggered
   - markdownlint and commitlint should run
   - `quality-gate` should pass (either via shim jobs or because all tests are skipped)
4. Record the CI wall-clock time — target is ≤ 2 minutes (NFR-001).

**If Python test jobs are triggering on the docs PR:**
- Review the `paths:` filter in the workflow — confirm `docs/**` is not in the paths list
- Check whether the `push` trigger is also filtered (not just `pull_request`)

**Close the draft PR and delete the test branch** after validation.

---

### T055 — Confirm `quality-gate` passes on `main` with full migration applied

**Final validation gate:**

Push the completed WP10 changes to the feature branch and confirm:

```bash
# Local syntax validation for all modified workflows
python3 -c "
import yaml, pathlib
for wf in pathlib.Path('.github/workflows').glob('*.yml'):
    try:
        yaml.safe_load(wf.read_text())
        print(f'OK: {wf.name}')
    except yaml.YAMLError as e:
        print(f'ERROR: {wf.name}: {e}')
"
```

For the full CI validation, open a non-draft PR (or push to a branch with a PR open) and
verify:
1. `quality-gate` job passes
2. `report` job shows all per-module job results (not the old monolithic jobs)
3. At least one per-module job ran (the PR touched some source file)
4. No job appears twice in the output (verifying `no-parallel-duplicate-test-runs`)

**If `quality-gate` fails:**
- Check the `needs:` list in `quality-gate` — is it referencing old job names that no
  longer exist?
- Check whether any required checks in branch protection reference old job names — if so,
  coordinate with the repo owner to update them

**Commit** and request reviewer confirmation that branch protection is satisfied.

## Definition of Done

- [ ] `orchestrator-boundary.yml` has path filter scoped to `orchestrator_api/**` changes
- [ ] `check-spec-kitty-events-alignment.yml` has path filter scoped to `sync/**` and `pyproject.toml`
- [ ] Required-checks list confirmed with repo owner (documented in commit message or PR description)
- [ ] Docs-only PR validation: Python test jobs not triggered; markdownlint/commitlint run; CI completes in ≤ 2 minutes
- [ ] `quality-gate` passes on `main` after full migration
- [ ] All YAML files parse without error
- [ ] Changes committed to `feat/080-ci-hardening-and-lint-cleanup`

## Risks

- **Branch protection blocks the PR itself (highest risk):** If WP09 removed a required
  check that WP09 shim jobs do not cover, this WP's PR cannot merge. Verify shim coverage
  before merging WP09. This is why T051 (confirm required checks) is the first subtask.
- **`paths:` filter too narrow:** If the paths filter for `check-spec-kitty-events-alignment.yml`
  is too narrow, the workflow won't run when it should. Read the workflow's actual trigger
  conditions and the spec (FR-015) together before writing the filter.
- **Docs-only PR test takes >2 minutes (NFR-001):** If markdownlint or commitlint is slow,
  investigate — they should be the only things running on docs PRs and should complete in
  under 2 minutes on GitHub-hosted runners.
- **YAML syntax errors in edited workflows:** Always validate YAML syntax after editing.
  GitHub Actions YAML has strict schema requirements that `yaml.safe_load` alone won't catch —
  consider also running `actionlint` if available.

## Reviewer Guidance

The diff should show only `on:` section additions (path filters) in the two workflow files.
No job logic should change in this WP — that is WP09's territory. Any change to job steps,
environment variables, or test commands in this PR is out of scope and must be moved to WP09.
