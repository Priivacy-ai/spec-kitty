---
work_package_id: "WP04"
subtasks:
  - "T007"
  - "T008"
title: "Documentation and Secret Hygiene"
phase: "Phase 2 - Enablement"
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
*Path: [kitty-specs/002-lightweight-pypi-release/tasks/planned/WP04-documentation-and-secret-hygiene.md](kitty-specs/002-lightweight-pypi-release/tasks/planned/WP04-documentation-and-secret-hygiene.md)*


# Work Package Prompt: WP04 – Documentation and Secret Hygiene

## Objectives & Success Criteria

- Publish clear, actionable documentation guiding maintainers through branch readiness, tagging, secret management, and token rotation.
- Ensure README newcomers immediately understand the automated pipeline and how to configure `PYPI_API_TOKEN`.
- Keep documentation aligned with workflows built in WP01–WP03.

## Context & Constraints

- Base content on `docs/releases/readiness-checklist.md`, `quickstart.md`, and plan commitments.
- Respect security requirements—no secrets or token values in docs; provide UI navigation rather than screenshots containing sensitive info.
- Link to GitHub Actions workflows and validator CLI to keep instructions cohesive.

## Subtasks & Detailed Guidance

### Subtask T007 – Expand documentation set
- **Purpose**: Provide long-form guidance referenced by workflows and readiness summaries.
- **Steps**:
  1. Update `docs/index.md` with a new section (e.g., “Automated PyPI Releases”) referencing the readiness checklist and quickstart.
  2. Modify `docs/toc.yml` to include `releases/readiness-checklist.md`.
  3. Refine `docs/releases/readiness-checklist.md` with latest workflow names, validator commands, and failure remediation (e.g., how to rotate tokens, fetch tags).
  4. Update `scripts/release/README.md` to describe validator usage (`--mode tag`, `--mode branch`), integration in workflows, and local dry-run instructions.
  5. Cross-link to relevant spec sections (FR-006 secret hygiene).
- **Files**:
  - `docs/index.md`
  - `docs/toc.yml`
  - `docs/releases/readiness-checklist.md`
  - `scripts/release/README.md`
- **Parallel?**: Yes; can iterate while workflows stabilize, but keep details consistent with YAML.
- **Notes**:
  - Use absolute URLs for PyPI references.
  - Document rotation cadence and note to record the date in checklist.

### Subtask T008 – Update README release guidance
- **Purpose**: Provide succinct onboarding for automated releases and secret setup.
- **Steps**:
  1. Add “Releasing to PyPI” section to `README.md` (or expand existing content) summarizing pipeline flow (branch readiness → merge → tag).
  2. Include step-by-step instructions for creating `PYPI_API_TOKEN` and storing it as a GitHub secret, referencing quickstart for detail.
  3. Describe how to run the validator locally and mention the guard workflows (pre-merge, protect-main).
  4. Link to `docs/releases/readiness-checklist.md` and `kitty-specs/002-lightweight-pypi-release/quickstart.md` for deep dives.
  5. Note branch protection expectations and failure remediation steps from guard workflow messages.
- **Files**:
  - `README.md`
- **Parallel?**: Yes; may commence after workflow names finalised.
- **Notes**:
  - Keep README concise; offload long instructions to docs but ensure critical steps remain.
  - Provide command snippets `git tag vX.Y.Z` and `git push origin vX.Y.Z`.

## Test Strategy

- Perform Markdown linting if available and ensure doc site builds (if doc tooling present).
- Manually follow documentation instructions to confirm they map to actual workflows.

## Risks & Mitigations

- Docs drifting from automation behavior → include references to workflow file paths so future changes remain discoverable.
- Secret creation instructions out-of-date due to GitHub UI changes → date the guidance or link to official GitHub docs.

## Definition of Done Checklist

- [ ] Docs index, TOC, readiness checklist, and script README updated with final workflow details.
- [ ] README outlines release process and secret handling succinctly with links to detailed docs.
- [ ] Documentation aligns with validator options and workflow names.
- [ ] No sensitive data introduced; all instructions reference secure storage.
- [ ] `tasks.md` updated with status change.

## Review Guidance

- Confirm docs correctly cite workflow filenames and CLI commands.
- Ensure instructions satisfy FR-001 (documented feature branch workflow) and FR-006 (secret hygiene).
- Verify README remains approachable while pointing to deeper resources.

## Activity Log

- 2025-11-02T16:58:36Z – system – lane=planned – Prompt created.

---

### Updating Metadata When Changing Lanes

1. Capture your shell PID: `echo $$`.
2. Update frontmatter (`lane`, `assignee`, `agent`, `shell_pid`).
3. Append an entry to the **Activity Log** documenting the transition.
4. Use `.kittify/scripts/bash/tasks-move-to-lane.sh 002-lightweight-pypi-release WP04 <lane>` for consistent metadata updates.
5. Commit or stage edits to maintain change history.
- 2025-11-02T18:19:01Z – claude-sonnet-4.5 – shell_pid=16185 – lane=doing – Started implementation
- 2025-11-02T21:56:56Z – claude-sonnet-4.5 – shell_pid=16185 – lane=for_review – Ready for review
- 2025-11-02T22:51:28Z – claude-sonnet-4.5 – shell_pid=16185 – lane=done – Approved - Documentation complete
