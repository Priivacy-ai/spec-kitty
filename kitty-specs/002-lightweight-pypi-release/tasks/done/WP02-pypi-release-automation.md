---
work_package_id: "WP02"
subtasks:
  - "T003"
  - "T004"
title: "PyPI Release Automation"
phase: "Phase 1 - Automation"
lane: "done"
assignee: ""
agent: "claude-sonnet-4.5"
shell_pid: "16185"
history:
  - timestamp: "2025-11-02T16:58:36Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---
*Path: [kitty-specs/002-lightweight-pypi-release/tasks/planned/WP02-pypi-release-automation.md](kitty-specs/002-lightweight-pypi-release/tasks/planned/WP02-pypi-release-automation.md)*


# Work Package Prompt: WP02 – PyPI Release Automation

## Objectives & Success Criteria

- Prepare packaging metadata so `python -m build` followed by `twine check` succeeds with no warnings.
- Create `.github/workflows/release.yml` that builds, checks, and publishes artifacts when `v*` tags are pushed, failing fast when prerequisites are unmet or secrets missing.
- Capture release notes and artifacts for auditing (checksum file + GitHub Release).

## Context & Constraints

- Align with FR-004 and FR-005 in the feature spec: validate distributables before publishing and trigger releases on semantic tags.
- Reference `plan.md` project structure guidance and `contracts/github-release-workflow.yml` for required workflow stages.
- Continue leveraging Hatch build backend; avoid introducing alternative build tooling.
- Pipeline must not leak `PYPI_API_TOKEN`; rely on `pypa/gh-action-pypi-publish@release/v1`.

## Subtasks & Detailed Guidance

### Subtask T003 – Update packaging metadata
- **Purpose**: Ensure PyPI presentation is complete and `twine check` passes.
- **Steps**:
  1. Edit `pyproject.toml`:
     - Add `readme = "README.md"` and `license = { file = "LICENSE" }`.
     - Provide `authors`, `maintainers`, `keywords`, and `classifiers` (include Python 3.11).
     - Add `[project.urls]` entries (Repository, Issues, Documentation, Changelog).
  2. Verify README renders correctly (no relative image paths that break on PyPI).
  3. Update `CHANGELOG.md` so each release header is linkable (e.g., anchor or bullet) and mention release notes path expected by workflow.
  4. Run `python -m build` locally and `twine check dist/*` to confirm metadata completeness; clean `dist/` afterwards.
- **Files**:
  - `pyproject.toml`
  - `CHANGELOG.md`
- **Parallel?**: No; metadata must be ready before authoring workflow.
- **Notes**:
  - If `packaging` metadata needs restructure, document reasoning in commit message.
  - Keep version unchanged until feature release; rely on future tag to bump.

### Subtask T004 – Author release workflow
- **Purpose**: Automate build, validation, and publication on semantic tags.
- **Steps**:
  1. Create `.github/workflows/release.yml`.
  2. Trigger on `push` to tags matching `v*.*.*` and allow manual `workflow_dispatch`.
  3. Steps:
     - Checkout with full history (`fetch-depth: 0`) to access tags.
     - Setup Python 3.11 using `actions/setup-python@v5`.
     - Install dependencies: `pip install --upgrade pip`, `pip install build twine tomli packaging pytest`.
     - Run `python -m pytest`.
     - Execute validator: `python scripts/release/validate_release.py --mode tag --tag "${GITHUB_REF_NAME}"`.
     - Build artifacts: `python -m build`.
     - Run `twine check dist/*`.
     - Generate checksums: `sha256sum dist/* > dist/SHA256SUMS.txt`.
     - Upload artifacts (wheel, sdist, checksum) via `actions/upload-artifact@v4`.
     - Publish to PyPI using `pypa/gh-action-pypi-publish@release/v1` with `password: ${{ secrets.PYPI_API_TOKEN }}` and `skip-existing: true`.
     - Create GitHub release (e.g., `softprops/action-gh-release@v2`) with body sourced from `CHANGELOG.md` entry for the tagged version.
  4. Provide informative failure output when the secret is missing (`if: always()` step posting `echo "::error::..."`).
  5. Restrict workflow permissions: `permissions: contents: read, id-token: write`.
- **Files**:
  - `.github/workflows/release.yml`
  - Optional helper script to extract changelog snippet (can live in `scripts/release/`).
- **Parallel?**: No; relies on metadata updates from T003.
- **Notes**:
  - Consider caching pip downloads (`actions/cache`) to speed up runs.
  - Use environment variable `PYPI_REPOSITORY_URL` if supporting TestPyPI later; keep extensible.

## Test Strategy

- Dry-run the workflow with a temporary tag and `PYPI_API_TOKEN` unset—confirm failure occurs at publish with clear messaging.
- Run `act` or GitHub Actions workflow_dispatch event to validate YAML syntax.

## Risks & Mitigations

- Build step fails due to missing MANIFEST entries → leverage Hatch `force-include` config already present; adjust if new docs/scripts need packaging.
- GitHub Release creation fails if tag exists → guard with `if: startsWith(github.ref, 'refs/tags/')`.

## Definition of Done Checklist

- [ ] `pyproject.toml` metadata meets PyPI expectations; `twine check` passes locally.
- [ ] `.github/workflows/release.yml` builds, validates, and publishes artifacts on tag pushes.
- [ ] Workflow surfaces actionable errors when secrets absent or checks fail.
- [ ] Artifacts (wheel, sdist, checksum) uploaded for traceability.
- [ ] GitHub Release populated from changelog entry.
- [ ] `tasks.md` updated with status change.

## Review Guidance

- Confirm workflow aligns with `contracts/github-release-workflow.yml`.
- Ensure secret-handling steps do not echo credentials.
- Validate metadata changes do not break existing local development (run `pip install -e .` if necessary).

## Activity Log

- 2025-11-02T16:58:36Z – system – lane=planned – Prompt created.

---

### Updating Metadata When Changing Lanes

1. Capture your shell PID: `echo $$`.
2. Update frontmatter (`lane`, `assignee`, `agent`, `shell_pid`).
3. Append a new entry in **Activity Log** describing the transition.
4. Use `.kittify/scripts/bash/tasks-move-to-lane.sh 002-lightweight-pypi-release WP02 <lane>` to propagate metadata changes.
5. Commit or stage prompt updates to maintain workflow auditability.
- 2025-11-02T17:54:32Z – claude-sonnet-4.5 – shell_pid=10832 – lane=doing – Started implementation
- 2025-11-02T18:02:57Z – claude-sonnet-4.5 – shell_pid=10832 – lane=for_review – Ready for review
- 2025-11-02T22:51:06Z – claude-sonnet-4.5 – shell_pid=16185 – lane=done – Approved - Release pipeline working
