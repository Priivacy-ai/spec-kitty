---
work_package_id: WP02
title: Doctrine artefacts — codify the three new directives + paradigm
dependencies:
- WP01
requirement_refs:
- C-003
- FR-006
- FR-007
- FR-008
- NFR-007
planning_base_branch: feature/650-dashboard-ui-ux-overhaul
merge_target_branch: feature/650-dashboard-ui-ux-overhaul
branch_strategy: Planning artifacts for this feature were generated on feature/650-dashboard-ui-ux-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/650-dashboard-ui-ux-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
agent: "claude:opus-4-7:architect-alphonso:architect"
shell_pid: "1366386"
history:
- date: '2026-05-03'
  event: created
  note: Auto-generated alongside tasks.md
agent_profile: architect-alphonso
authoritative_surface: src/doctrine/
execution_mode: code_change
owned_files:
- src/doctrine/directives/shipped/api-dependency-direction.directive.yaml
- src/doctrine/directives/shipped/rest-resource-orientation.directive.yaml
- src/doctrine/paradigms/shipped/hateoas-lite.paradigm.yaml
role: architect
tags:
- doctrine
- architecture
---

## ⚡ Do This First: Load Agent Profile

Load the `architect-alphonso` agent profile:

```
/ad-hoc-profile-load architect-alphonso
```

You are Architect Alphonso. Your role is precise architectural documentation. You do not write source code or tests in this WP — those land in WP03 / WP05. Your output is three YAML artefacts that codify the rules.

## Objective

Codify three new doctrine artefacts as YAML files in the shipped doctrine. They make the architectural rules explicit so future contributors cannot regress them by accident, and they cross-link to the architectural tests (landing in WP05) that enforce them in CI.

## Context

The mission's three new doctrine artefacts:

1. `DIRECTIVE_API_DEPENDENCY_DIRECTION` — transports go through services; services go through the registry; registry goes to the backbone. Cross-linked to `tests/architectural/test_transport_does_not_import_scanner.py` (WP05).

2. `DIRECTIVE_REST_RESOURCE_ORIENTATION` — URLs are noun-shaped; methods carry the verb. Cross-linked to `tests/architectural/test_url_naming_convention.py` (WP05).

3. `HATEOAS-LITE` paradigm — `_links` block convention; future-graduation triggers documented. Cross-linked to `tests/architectural/test_resource_models_have_links.py` (WP05).

The exact YAML shapes are specified in `kitty-specs/mission-registry-and-api-boundary-doctrine-01KQPDBB/contracts/doctrine-artefact-shapes.md`. Read that contract before writing the YAML files; the contract is the source of truth.

The HATEOAS-LITE rationale and future-migration triggers (HAL / JSON:API graduation) live in `architecture/2.x/initiatives/2026-05-stable-application-api-surface/README.md` § 3.3. Quote the rationale into the paradigm YAML so the doctrine is self-contained.

## Subtasks

### T004 — `DIRECTIVE_API_DEPENDENCY_DIRECTION`

**File**: `src/doctrine/directives/shipped/api-dependency-direction.directive.yaml`

**Action**: copy the YAML structure from `kitty-specs/mission-registry-and-api-boundary-doctrine-01KQPDBB/contracts/doctrine-artefact-shapes.md` § 1. Verify:

- `directive-id` is the next sequential ID (check `src/doctrine/directives/shipped/` for the current max).
- `referenced-tests` lists `tests/architectural/test_transport_does_not_import_scanner.py` (the test file lands in WP05 — that's expected; the doctrine references it forward).
- `forbidden-imports` and `forbidden-patterns` enumerate the AST patterns the test will detect.
- `introduced-by-mission` and `introduced-at` are populated.

### T005 — `DIRECTIVE_REST_RESOURCE_ORIENTATION`

**File**: `src/doctrine/directives/shipped/rest-resource-orientation.directive.yaml`

**Action**: copy the YAML structure from the contract § 2. Verify:

- `directive-id` is the next sequential ID after T004.
- `referenced-tests` lists `tests/architectural/test_url_naming_convention.py`.
- The rule explicitly carves out action-shaped URLs (`/api/sync/trigger`, `/api/shutdown`) as permitted but tagged `actions`.
- The deprecation cycle (RFC 8594 `Deprecation` header, one-release retention) is documented.

### T006 — `HATEOAS-LITE` paradigm + schema-extension if needed

**File**: `src/doctrine/paradigms/shipped/hateoas-lite.paradigm.yaml`

**Action**: copy the YAML structure from the contract § 3. Verify:

- `referenced-tests` lists `tests/architectural/test_resource_models_have_links.py`.
- `future-graduation-triggers` enumerates the four triggers (external SDK consumer, paginated compound documents, multi-tenant deployment, operations discovery).
- `future-migration-shape` documents the additive migration path (new fields alongside `_links`).
- The `example` block shows the `_links` JSON shape verbatim from the initiative § 3.3.

**After writing all three files**, run:

```bash
.venv/bin/python -m pytest tests/doctrine/ -v
```

Expected: all schema-validation tests pass.

**If any new field is rejected by the schema** (e.g., `referenced-tests:` doesn't validate against the existing schema):

1. Identify the rejecting field via the test failure.
2. Land an additive schema extension in this WP02. The extension adds the field as optional with default None / empty list.
3. Verify all existing shipped artefacts still validate after the extension.
4. Re-run `pytest tests/doctrine/`.

Do NOT use a free-form `metadata:` escape hatch — that bypasses the schema validation that catches typos.

## Branch Strategy

Same as WP01: lane-less on `feature/650-dashboard-ui-ux-overhaul`. Three small YAML files; commit as a single commit with a `doctrine(...)` prefix.

## Definition of Done

- [ ] Three YAML files exist at the paths owned by this WP.
- [ ] Each artefact references the test file in WP05 that enforces it (forward reference is intentional).
- [ ] `.venv/bin/python -m pytest tests/doctrine/ -v` passes (or, if a schema extension was needed, both the extension and the existing artefacts validate).
- [ ] No `metadata:` escape hatch in any new artefact.
- [ ] Each artefact's `introduced-by-mission` field reads `mission-registry-and-api-boundary-doctrine-01KQPDBB`.

## Reviewer guidance

- **Schema integrity**: if a schema extension was needed, the reviewer verifies it is additive (no field removals; no required-field changes for existing artefacts).
- **Cross-link consistency**: each new artefact's `referenced-tests` must match the paths WP05 uses. If WP05's filenames diverge, this WP's artefacts must update to match (or the divergence is a bug).
- **No source-code escape hatches** (mission-wide rule C-003): if a directive's rule has carve-outs, they live in the YAML's `allowlist` or `exempt-from-rule` field — never as `# noqa` markers in source code.

## Risks

- **Schema extension scope creep**: if the schema needs more than one field, resist the temptation to redesign. Add only what FR-006/007/008 require.
- **Test files in WP05 don't exist yet**: this is expected. The doctrine references the test path forward; WP05 creates the file at the referenced path. The doctrine's correctness check is "the test path matches what WP05 will create", not "the test file exists today."

## Activity Log

- 2026-05-03T14:08:27Z – claude:opus-4-7:architect-alphonso:architect – shell_pid=1366386 – Started implementation via action command
