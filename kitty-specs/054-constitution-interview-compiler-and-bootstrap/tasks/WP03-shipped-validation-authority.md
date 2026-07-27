---
work_package_id: WP03
title: Enforce Shipped-Only Validation Authority
lane: "done"
dependencies: []
base_branch: feature/agent-profile-implementation
base_commit: 6574829a137207f0939d7cf3ca500471284509c1
created_at: '2026-03-09T16:28:15.046882+00:00'
subtasks:
- T012
- T013
- T014
- T015
- T016
- T017
phase: Phase 1 - Validation
assignee: claude
agent: claude
shell_pid: '405823'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-03-09T14:23:30Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-003
- FR-005
- NFR-003
---

# Work Package Prompt: WP03 - Enforce Shipped-Only Validation Authority

## ⚠️ IMPORTANT: Review Feedback Status

- If this WP returns from review, handle every listed issue before requesting approval again.

---

## Review Feedback

*[Empty initially.]*  

---

## Markdown Formatting

Use fenced code blocks with language identifiers. Quote literal flags and filenames with backticks.

## Objectives & Success Criteria

- Shipped doctrine artifacts remain the default authoritative validation source.
- `_proposed/` artifacts participate only when a caller explicitly opts into curation behavior.
- Template-set validation never silently skips just because metadata is empty.
- Validation errors name the exact directive, paradigm, tool, or template-set value that failed.
- Constitution sync output stays limited to `governance.yaml`, `directives.yaml`, and `metadata.yaml`, with no `agents.yaml`.

## Context & Constraints

- Primary files:
  - `src/specify_cli/constitution/catalog.py`
  - `src/specify_cli/constitution/resolver.py`
  - `src/specify_cli/constitution/sync.py`
- Existing test anchors:
  - `tests/specify_cli/constitution/test_catalog.py`
  - resolver-focused tests near the constitution suite
  - `tests/specify_cli/cli/commands/test_constitution_cli.py` if sync/status output assertions need adjustment
- Implementation command: `spec-kitty implement WP03`
- This WP can run in parallel with WP01 and WP04.

## Subtasks & Detailed Guidance

### Subtask T012 - Audit catalog, resolver, and sync assumptions

- **Purpose**: Establish exactly where validation authority and output assumptions currently live.
- **Steps**:
  1. Read `load_doctrine_catalog()` and `_load_yaml_id_catalog()` in `src/specify_cli/constitution/catalog.py`.
  2. Read template-set and shipped-selection validation in `src/specify_cli/constitution/resolver.py`.
  3. Confirm what `sync()` actually writes in `src/specify_cli/constitution/sync.py` and where tests still mention `agents.yaml`.
  4. Note any call sites that might still assume `_proposed/` visibility without opting in.
- **Files**:
  - `src/specify_cli/constitution/catalog.py`
  - `src/specify_cli/constitution/resolver.py`
  - `src/specify_cli/constitution/sync.py`
- **Parallel?**: No
- **Notes**: This WP should leave a clear audit trail so reviewers can see that every validation path was considered.

### Subtask T013 - Keep shipped-only catalog loading authoritative

- **Purpose**: Preserve the curation boundary and make the contract explicit in code and tests.
- **Steps**:
  1. Confirm `load_doctrine_catalog()` defaults to shipped-only for every artifact family.
  2. Ensure `_proposed/` visibility requires an explicit opt-in parameter and is not reintroduced through helper fallbacks.
  3. Review any tests or helper utilities that rely on flat-directory fixtures and preserve that fixture convenience where appropriate.
  4. Tighten documentation/comments where needed so future maintainers do not misread curation-only behavior as default runtime behavior.
- **Files**:
  - `src/specify_cli/constitution/catalog.py`
  - `tests/specify_cli/constitution/test_catalog.py`
- **Parallel?**: Yes
- **Notes**: The contract change itself is small; the risk is accidental backsliding through another path.

### Subtask T014 - Add template-set fallback validation

- **Purpose**: Close the silent-validation hole when template-set catalog metadata is empty.
- **Steps**:
  1. Update template-set validation in `src/specify_cli/constitution/resolver.py` so it falls back to enumerating packaged mission directories when `doctrine_catalog.template_sets` is empty.
  2. Keep the fallback deterministic and offline-friendly.
  3. If the fallback root is missing in a packaged environment, do not invent a new hard failure. Preserve the current graceful behavior after logging or diagnostics if appropriate.
  4. Ensure the resulting error still names the rejected `template_set`.
- **Files**:
  - `src/specify_cli/constitution/resolver.py`
- **Parallel?**: Yes
- **Notes**: Use the packaged mission directory as the validation source, not arbitrary filesystem scanning outside doctrine assets.

### Subtask T015 - Preserve strict shipped validation while exempting local support docs

- **Purpose**: Keep shipped ID validation strict without accidentally treating local markdown as catalog-backed doctrine.
- **Steps**:
  1. Separate shipped artifact validation from local support declaration handling.
  2. Ensure unknown shipped directives/paradigms/tools/template sets still fail.
  3. Ensure local support declarations do not trigger shipped-catalog ID failures just because they are free-form or additive.
  4. Keep error messaging clear about which class of input failed.
- **Files**:
  - `src/specify_cli/constitution/resolver.py`
  - nearby compiler or interview helpers if validation ownership needs to be moved
- **Parallel?**: No
- **Notes**: The failure mode should identify “shipped selection” vs “local support declaration” clearly.

### Subtask T016 - Remove stale agents.yaml assumptions from sync and status surfaces

- **Purpose**: Align generated-output expectations with the feature spec and avoid stale test failures.
- **Steps**:
  1. Confirm no sync code path writes `agents.yaml`.
  2. Update any CLI or status reporting code/tests that still assume `agents.yaml` or another pre-feature output inventory.
  3. Keep the sync surface focused on the existing three YAML files.
  4. If `status` or human-readable output still references removed outputs, update them in a way that remains backward-readable.
- **Files**:
  - `src/specify_cli/constitution/sync.py`
  - `src/specify_cli/cli/commands/constitution.py`
  - related tests
- **Parallel?**: No
- **Notes**: This is a cleanup task, but it matters because stale output lists create misleading automation behavior.

### Subtask T017 - Add regression tests for named-ID validation failures

- **Purpose**: Freeze the validation contract under tests before downstream work relies on it.
- **Steps**:
  1. Add or update tests for:
     - unknown directive
     - unknown paradigm
     - unknown tool
     - unknown template set with empty catalog metadata fallback
     - shipped-only default catalog scan
     - explicit `include_proposed=True`
  2. Assert on named offending IDs/values in the error text.
  3. Add one sync/output assertion that `agents.yaml` is absent.
- **Files**:
  - `tests/specify_cli/constitution/test_catalog.py`
  - resolver tests in the constitution suite
  - any sync/CLI tests that verify output inventories
- **Parallel?**: No
- **Notes**: Keep the tests specific; this package is about validation authority, not the full context pipeline.

## Test Strategy

- Run:
  - `pytest -q tests/specify_cli/constitution/test_catalog.py`
  - targeted resolver/sync tests covering invalid selections and output inventories
- Confirm at least one failure path for each shipped selection type and one explicit `_proposed/` opt-in path.

## Risks & Mitigations

- The shipped-only default is easy to preserve in `catalog.py` but easy to lose again through helper reuse. Guard it with tests, not comments alone.
- Template-set fallback logic can become environment-sensitive. Keep the fallback rooted in packaged doctrine paths only.

## Review Guidance

- Confirm `_proposed/` content is never visible unless a caller explicitly asks for it.
- Confirm every failure message names the bad value.
- Confirm no stale `agents.yaml` expectations remain in tests or human output.

## Activity Log

- 2026-03-09T14:23:30Z - system - lane=planned - Prompt created.
- 2026-03-09T16:38:37Z – claude – shell_pid=405823 – lane=for_review – Shipped-only validation enforced, domains_present tracking, named-ID errors, agents.yaml removed from sync, 15 new tests
- 2026-03-09T16:42:56Z – claude – shell_pid=405823 – lane=done – Reviewed and approved. 53 tests pass. Merged into feature branch.
