# Work Packages: Lightweight PyPI Release Workflow

**Inputs**: Design artifacts in `/kitty-specs/002-lightweight-pypi-release/`
**Prerequisites**: plan.md (required), spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Only include explicit testing work when stakeholders request it.

**Organization**: Fine-grained subtasks (`Txxx`) roll into work packages (`WPxx`). Each work package is independently deliverable and testable.

**Prompt Files**: Prompts live under `/kitty-specs/002-lightweight-pypi-release/tasks/planned/` by ID.

---

## Work Package WP01: Release Validation Tooling (Priority: P0) 🎯 MVP

**Goal**: Ship a deterministic CLI (`scripts/release/validate_release.py`) that verifies version, changelog, and tag alignment for both branch and tag contexts.  
**Independent Test**: `python -m pytest tests/release/test_validate_release.py` passes and `python scripts/release/validate_release.py --tag vX.Y.Z --changelog CHANGELOG.md` exits 0 on a prepared release branch.  
**Prompt**: `/kitty-specs/002-lightweight-pypi-release/tasks/planned/WP01-release-validation-tooling.md`

### Included Subtasks
- [X] T001 Implement `scripts/release/validate_release.py` with branch/tag modes, changelog parsing, semantic version comparisons, and actionable errors. ✅ (See: `kitty-specs/002-lightweight-pypi-release/tasks/done/WP01-release-validation-tooling.md`)
- [X] T002 Add pytest coverage for validator success, mismatch, missing changelog, and regression scenarios in `tests/release/test_validate_release.py`. ✅ (See: `kitty-specs/002-lightweight-pypi-release/tasks/done/WP01-release-validation-tooling.md`)

### Implementation Notes
- Use `tomllib`/`tomli` for `pyproject.toml` parsing and support manual tag overrides plus auto-detection from environment variables (`GITHUB_REF`, etc.).
- Provide rich terminal output (exit codes + guidance) without leaking secrets; prefer stdout for summaries and stderr for failure reasons.

### Parallel Opportunities
- None; build the CLI (T001) before introducing tests (T002).

### Dependencies
- None. This is the foundational bundle for downstream automation.

### Risks & Mitigations
- **Risk**: Validator misinterprets changelog headings.  
  **Mitigation**: Normalize headings via regex, support both `## [X.Y.Z]` and `## X.Y.Z`.
- **Risk**: Git tag discovery fails in shallow clones.  
  **Mitigation**: Support explicit `--tag` flag and document fetching tags in workflows.

---

## Work Package WP02: PyPI Release Automation (Priority: P0) 🎯 MVP

**Goal**: Automate tag-triggered builds via `.github/workflows/release.yml`, producing validated artifacts and publishing to PyPI with `PYPI_API_TOKEN`.  
**Independent Test**: Create a dry-run tag (`vX.Y.Z`) with secrets disabled; workflow should execute through validation/build/check steps and halt gracefully before publish when token missing, logging remediation guidance.  
**Prompt**: `/kitty-specs/002-lightweight-pypi-release/tasks/planned/WP02-pypi-release-automation.md`

### Included Subtasks
- [X] T003 Update packaging metadata in `pyproject.toml` (readme, project URLs, classifiers) and ensure `CHANGELOG.md` links release notes for PyPI presentation. ✅ (See: `kitty-specs/002-lightweight-pypi-release/tasks/done/WP02-pypi-release-automation.md`)
- [X] T004 Author `.github/workflows/release.yml` to run tests, invoke the validator in tag mode, build (`python -m build`), run `twine check`, upload artifacts, create a GitHub Release with changelog excerpt, and publish via `pypa/gh-action-pypi-publish@release/v1`. ✅ (See: `kitty-specs/002-lightweight-pypi-release/tasks/done/WP02-pypi-release-automation.md`)

### Implementation Notes
- Guard the publish step with `if: secrets.PYPI_API_TOKEN != ''` and emit an informative failure if the secret is absent.
- Use job summaries or uploaded artifacts (`SHA256SUMS`) for audit trails per spec.
- Ensure workflow permissions include `id-token: write` for future trusted publishing.

### Parallel Opportunities
- T003 can start once WP01 delivers validator contracts, but complete it before finalizing the workflow in T004.

### Dependencies
- Depends on WP01 (release workflow requires the validator).

### Risks & Mitigations
- **Risk**: `twine check` fails due to metadata gaps.  
  **Mitigation**: Extend metadata in T003 and perform dry-run packaging locally before enabling publish.
- **Risk**: Publishing step leaks tokens in logs.  
  **Mitigation**: Rely on maintained PyPA action and avoid echoing secrets; keep verbose logs on but sanitize outputs.

---

## Work Package WP03: Release Readiness Guardrails (Priority: P1)

**Goal**: Enforce branch readiness and reject direct pushes to `main` using GitHub Actions checks prior to tagging.  
**Independent Test**: Open a PR with mismatched version/changelog—`release-readiness` workflow fails with validator output. Attempt a direct push to `main` locally—the guard workflow fails and surfaces remediation guidance.  
**Prompt**: `/kitty-specs/002-lightweight-pypi-release/tasks/planned/WP03-release-readiness-guardrails.md`

### Included Subtasks
- [X] T005 [P] Add `.github/workflows/release-readiness.yml` (pull_request + workflow_dispatch) to execute tests, run the validator in branch mode, and surface checklist reminders in the job summary. ✅ (See: `kitty-specs/002-lightweight-pypi-release/tasks/done/WP03-release-readiness-guardrails.md`)
- [X] T006 [P] Create `.github/workflows/protect-main.yml` that runs on `push` to `main`, failing when commits bypass PR merges (e.g., lack `Merge pull request` prefix) and pointing maintainers to branch protection settings. ✅ (See: `kitty-specs/002-lightweight-pypi-release/tasks/done/WP03-release-readiness-guardrails.md`)

### Implementation Notes
- Expose validator results via `$GITHUB_STEP_SUMMARY` so maintainers see unmet criteria without digging through logs.
- Ensure guard workflows exit successfully for merge commits and skip on tag pushes to avoid blocking release automation.

### Parallel Opportunities
- Workflows can be drafted in parallel once WP01 validator behaviors are defined; validate locally with `act` or dry-run YAML linting before pushing.

### Dependencies
- Depends on WP01 (validator), and benefits from metadata updates in WP02 for consistent versioning.

### Risks & Mitigations
- **Risk**: Guard workflow produces false positives for squash merges.  
  **Mitigation**: Allow alternate commit messages via regex and document acceptable strategies.
- **Risk**: Readiness workflow slows PR feedback.  
  **Mitigation**: Cache dependencies where possible and keep steps focused on release checks.

---

## Work Package WP04: Documentation & Secret Hygiene (Priority: P1)

**Goal**: Document the automated pipeline, secret management, and maintainer workflow across README and docs.  
**Independent Test**: New maintainer can follow updated docs to configure `PYPI_API_TOKEN`, run readiness checklist, and understand branch protection expectations without external coaching.  
**Prompt**: `/kitty-specs/002-lightweight-pypi-release/tasks/planned/WP04-documentation-and-secret-hygiene.md`

### Included Subtasks
- [X] T007 [P] Expand documentation (`docs/index.md`, `docs/toc.yml`, `docs/releases/readiness-checklist.md`, `scripts/release/README.md`) to reference the validator, workflows, and rotation cadence. ✅ (See: `kitty-specs/002-lightweight-pypi-release/tasks/done/WP04-documentation-and-secret-hygiene.md`)
- [X] T008 [P] Update `README.md` (release section) with end-to-end instructions: preparing changelog/version, configuring secrets, triggering tags, and linking to the readiness checklist & quickstart. ✅ (See: `kitty-specs/002-lightweight-pypi-release/tasks/done/WP04-documentation-and-secret-hygiene.md`)

### Implementation Notes
- Keep instructions actionable: include GitHub UI paths for secrets, branch protection toggles, and command snippets for tagging releases.
- Cross-link Quickstart and readiness checklist so both entry points stay synchronized.

### Parallel Opportunities
- Documentation work can proceed alongside WP03 once workflow names and behaviors stabilize.

### Dependencies
- Depends on outputs of WP01–WP03 to accurately describe tooling and pipeline behavior.

### Risks & Mitigations
- **Risk**: Docs diverge from automation details over time.  
  **Mitigation**: Centralize authoritative instructions in `docs/releases/readiness-checklist.md` and reuse wording in README via shared snippets where feasible.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02 → WP03 → WP04.
- **Parallelization**: Documentation (WP04) can overlap with final workflow validations once YAML stabilized. Guardrail workflows (WP03) may iterate alongside release pipeline tests after validator completion.
- **MVP Scope**: WP01 + WP02 deliver a functioning automated PyPI release; WP03 and WP04 harden the process and satisfy readiness guidance requirements.

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Implement release validator CLI with branch/tag modes | WP01 | P0 | No |
| T002 | Add pytest coverage for validator behavior | WP01 | P0 | No |
| T003 | Update PyPI metadata in `pyproject.toml` & changelog links | WP02 | P0 | No |
| T004 | Author tag-triggered PyPI release workflow | WP02 | P0 | No |
| T005 | Create pull request release-readiness workflow | WP03 | P1 | Yes |
| T006 | Guard direct pushes to `main` via workflow | WP03 | P1 | Yes |
| T007 | Expand release readiness documentation set | WP04 | P1 | Yes |
| T008 | Update README with automated release guidance | WP04 | P1 | Yes |

---
