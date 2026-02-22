# Feature Specification: Doctrine-Lite Deterministic Constitution Generator

**Feature Branch**: `043-doctrine-lite-constitution-generator`
**Created**: 2026-02-22
**Status**: Draft
**Target Branch**: `2.x`

## Goals

- Keep doctrine as a deterministic, constitution-first system.
- Remove agent-profile governance concepts from doctrine/constitution.
- Provide a one-step constitution creator (`spec-kitty constitution generate`).
- Ensure doctrine selections are read and surfaced in runtime prompt contexts.
- Remove scaffolding-only doctrine artifacts and keep wired, concrete assets.

## User Scenarios & Testing

### User Story 1 - One-Step Constitution Creation (Priority: P1)

As a maintainer, I can run one command to generate a valid constitution with deterministic doctrine selections.

**Acceptance**:

1. Given a repo with `.kittify/constitution/`, when I run `spec-kitty constitution generate`, then `constitution.md` is created and `governance.yaml`, `directives.yaml`, `metadata.yaml` are synced.
2. Given existing `constitution.md`, when I run without `--force`, then generation fails safely.
3. Given existing `constitution.md`, when I run with `--force`, then generation overwrites and resyncs.

### User Story 2 - No Agent Governance Surface (Priority: P1)

As a maintainer, doctrine does not model/resolve agent profiles in constitution governance.

**Acceptance**:

1. `agents.yaml` is not emitted by constitution sync.
2. Governance resolution output no longer includes `agent_profiles`.
3. Constitution selection parsing ignores `selected_agent_profiles` keys.

### User Story 3 - Deterministic Catalog Validation (Priority: P1)

As a maintainer, constitution doctrine selections are validated against concrete doctrine catalogs.

**Acceptance**:

1. Unknown `selected_directives` values fail governance resolution.
2. Unknown `selected_paradigms` values fail governance resolution when catalogs are present.
3. Unknown `template_set` fails governance resolution.
4. Unknown `available_tools` fails governance resolution.

### User Story 4 - Constitution Context in Runtime Prompts (Priority: P2)

As an operator using `spec-kitty next`, generated prompts include current doctrine/governance context.

**Acceptance**:

1. Template-based `next` prompts include a governance header with paradigms/directives/template_set/tools.
2. WP prompts include the same governance header.
3. Missing governance files degrade gracefully (warning text, no crash).

## Requirements

### Functional Requirements

- **FR-001**: CLI MUST provide `spec-kitty constitution generate` with `--force`, `--mission`, and `--json`.
- **FR-002**: Constitution sync MUST emit only `governance.yaml`, `directives.yaml`, `metadata.yaml`.
- **FR-003**: Governance resolution MUST validate doctrine selections against deterministic catalogs.
- **FR-004**: Governance resolution MUST not depend on or return agent-profile data.
- **FR-005**: Runtime prompt generation MUST inject governance context in both template and WP prompt paths.
- **FR-006**: Doctrine package content MUST not contain empty scaffolding-only directories for core governance entities.

### Non-Goals

- Building a full doctrine orchestration framework.
- Introducing new agent orchestration entities.
- Reworking mission runtime state machines.

## Success Criteria

- **SC-001**: `constitution generate` works end-to-end and exits 0 in a clean repo.
- **SC-002**: Constitution tests pass without `agents.yaml` expectations.
- **SC-003**: Governance resolver tests cover directive/paradigm/template/tool validation.
- **SC-004**: `next` prompt builder tests verify governance context injection.
- **SC-005**: No runtime regression in existing global/runtime doctor checks.
