# Implementation Plan: Constitution Interview Compiler and Context Bootstrap

*Path: [src/doctrine/templates/plan-template.md](/home/stijn/Documents/_code/fork/spec-kitty/src/doctrine/templates/plan-template.md)*

**Branch**: `feature/agent-profile-implementation` | **Date**: 2026-03-09 | **Spec**: [spec.md](/home/stijn/Documents/_code/fork/spec-kitty/kitty-specs/054-constitution-interview-compiler-and-bootstrap/spec.md)
**Input**: Feature specification from `/home/stijn/Documents/_code/fork/spec-kitty/kitty-specs/054-constitution-interview-compiler-and-bootstrap/spec.md`

**Note**: This plan reflects the confirmed planning alignment for feature 054 and stops at Phase 1 artifacts.

## Summary

Harden the constitution workflow into a strict `interview -> generate -> context` pipeline, make shipped doctrine artifacts the default authoritative validation catalog, and move command-template governance prose into runtime doctrine retrieval. Planning alignment confirmed:

- Project-local override/supporting doctrine files are discovered only through explicit declarations in `answers.yaml` and `references.yaml`.
- Those declarations use explicit file paths only; directory and glob expansion are out of scope.
- Shipped artifacts remain authoritative when a local file targets the same doctrine concept; local files are additive only and must trigger a warning on conflict.
- Local declarations may be global or action-scoped for `specify`, `plan`, `implement`, and `review`.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: `typer`, `rich`, `ruamel.yaml`, existing `specify_cli.constitution.*` modules, `doctrine.service.DoctrineService`  
**Storage**: Filesystem only under `.kittify/constitution/` plus packaged doctrine assets under `src/doctrine/`  
**Testing**: `pytest` unit + integration tests, targeted CLI contract tests, `mypy --strict` compatibility preserved  
**Target Platform**: Cross-platform CLI runtime on Linux, macOS, and Windows 10+  
**Project Type**: Single Python CLI/package with packaged doctrine assets and generated markdown/yaml artifacts  
**Performance Goals**: Typical constitution CLI operations remain within the constitution target of under 2 seconds for normal project sizes; bootstrap/compact context retrieval remains action-scoped to keep output bounded  
**Constraints**: No new external dependencies; shipped doctrine catalog is authoritative by default; `_proposed/` doctrine is curation-only unless explicitly requested; local support files must be explicit file paths; shipped artifacts stay primary on conflicts; no `library/` materialization; no `agents.yaml` sync output  
**Scale/Scope**: Existing constitution subsystem plus doctrine mission assets, 3 CLI command surfaces (`interview`, `generate`, `context`), 48 generated agent template copies, and action-scoped planning/runtime metadata

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- PASS: Implementation stays within Python 3.11+ and the existing CLI stack (`typer`, `rich`, `ruamel.yaml`, `pytest`, `mypy`), consistent with [constitution.md](/home/stijn/Documents/_code/fork/spec-kitty/.kittify/constitution/constitution.md).
- PASS: Filesystem-only storage and packaged doctrine retrieval remain aligned with the constitution's deployment and performance constraints.
- PASS: No new external dependencies or alternative search/tooling patterns are introduced.
- PASS: Planned tests cover CLI behavior, catalog validation, and runtime context retrieval, matching the constitution's unit/integration emphasis.
- PASS: Phase 1 design does not introduce a conflict with the private dependency pattern or the two-branch release strategy.
- Re-check after Phase 1: still passing; design artifacts keep shipped doctrine authoritative, preserve deterministic CLI behavior, and do not require constitution exceptions.

## Project Structure

### Documentation (this feature)

```text
kitty-specs/054-constitution-interview-compiler-and-bootstrap/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── constitution-cli-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
src/specify_cli/
├── cli/commands/
│   ├── constitution.py
│   └── agent/context.py
├── constitution/
│   ├── catalog.py
│   ├── compiler.py
│   ├── context.py
│   ├── interview.py
│   ├── resolver.py
│   └── sync.py
└── core/
    └── agent_context.py

src/doctrine/
├── service.py
├── directives/
├── paradigms/
├── styleguides/
├── toolguides/
├── tactics/
└── missions/software-dev/
    ├── command-templates/
    └── actions/

tests/specify_cli/
├── constitution/
├── cli/commands/
└── test_constitution_template_migration.py
```

**Structure Decision**: Keep the work inside the existing single-package CLI architecture. Feature 054 extends existing constitution modules, adds Phase 1 documentation artifacts under `kitty-specs/054-constitution-interview-compiler-and-bootstrap/`, and introduces one contract document under `kitty-specs/054-constitution-interview-compiler-and-bootstrap/contracts/` rather than adding a new runtime package or service boundary.

## Complexity Tracking

No constitution violations or extra complexity justifications are required at planning time.
