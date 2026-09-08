# Mission Specification: Project-layer doctrine ingestion

**Mission Branch**: `issue-4103-migrate-guidance-glossary-step`
**Created**: 2026-09-09
**Status**: Accepted brief
**Input**: Operator-provided gist d3724d397eed848be27918a6d8ddb624 and explicit instruction to branch from v3.2.6.1 for 3.2.6.2.

## Intent Summary

A project maintainer ingests an SOP into a procedure, agent profile, directive, tactic, styleguide and glossary. Scaffolding, validation, activation with cascade, synthesis and agent context must work through public commands without manually activating dependencies or editing generated graphs. The operator supplied the complete scenarios and directed implementation of all fixes in existing PR #4104; no additional product discovery is needed.

## User Scenarios & Testing

### User Story 1 - Ingest and activate project guidance (Priority: P1)

Given a fresh initialized repository with generated and synthesized charter, scaffold five project artifacts through `charter new`, complete required fields, and reference the procedure, directive, tactic and styleguide from the profile. `charter validate .kittify/doctrine` passes all five. Activating the profile with `--cascade all` activates all five from a clean deactivated state. Repeating with `--resynthesize` succeeds. Context inclusion renders procedure steps and all profile reference IDs; default implement context includes the directive. Status counts all five with provenance.

### User Story 2 - Discover authoring commands (Priority: P1)

`charter new`, `validate`, `org` and `fetch` preserve existing doctrine command behavior. Deprecated-command guidance identifies commands that remain on doctrine.

### User Story 3 - Resolve glossary seed terms (Priority: P1)

Given a valid team_domain seed term, validate and list succeed and show renders its definition without a compile workaround. The migration procedure explicitly captures source vocabulary.

### Edge Cases

Missing cascade references produce actionable warnings. Unsupported resynthesis refuses before activation writes. Layer precedence matches profile resolution. Existing compiled glossary terms remain readable. Unknown glossary terms report actionable recovery. Singular project directories remain canonical.

## Requirements

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Migration glossary step (#4103) | Maintainers capture source vocabulary during guidance migration. | High | Open |
| FR-002 | Charter command parity (#4098) | Maintainers scaffold, validate, manage org packs and fetch through charter. | High | Open |
| FR-003 | Seed glossary lookup (#4102) | Maintainers show every seed term returned by list. | High | Open |
| FR-004 | Project artifact promotion (#4097) | Maintainers register procedures and profiles in project graph and provenance; status counts them and shipped skill documents all supported kinds. | High | Open |
| FR-005 | Project cascade (#4100) | Activating a profile activates all four referenced kinds or warns about unresolved references. | High | Open |
| FR-006 | Layered resynthesis (#4101) | Activated profiles resolve across built-in, org and project layers; unsupported requests fail before writes and point to charter.yaml. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Regression proof | Every issue has a passing local regression; required subsystem suites, ruff and mypy report zero introduced failures. | Quality | High | Open |
| NFR-002 | End-to-end proof | All operator acceptance commands pass in a fresh throwaway repo and transcript is in the PR. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Delivery | Existing PR #4104 only; base v3.2.6.1, intended release 3.2.6.2; no main push or merge. Preserve separable issue commits in requested order. | Delivery | High | Open |
| C-002 | CI | Defer remote CI until final local acceptance insofar as possible. | Delivery | High | Open |
| C-003 | Canonical artifacts | Preserve singular project directories, regenerate built-in graphs/manifests, one Unreleased changelog entry per issue. | Technical | High | Open |
| C-004 | Scope | Post-merge spk-doctrine-ingest skill belongs to a separate future PR, excluded here. | Delivery | High | Open |

### Key Entities

Project doctrine artifact, activation, reference edge, provenance record, glossary surface and scoped sense.

## Success Criteria

All six issues meet their scenarios; PR title and six issue sections/closing references are updated, prior verification retained, local acceptance transcript included, and CI passes on the final PR head.
