# Implementation Plan: Lightweight PyPI Release Workflow

**Branch**: `002-lightweight-pypi-release` | **Date**: 2025-11-02 | **Spec**: [kitty-specs/002-lightweight-pypi-release/spec.md](kitty-specs/002-lightweight-pypi-release/spec.md)
**Input**: Feature specification from `/kitty-specs/002-lightweight-pypi-release/spec.md`

## Summary

Automate packaging and publication of `spec-kitty-cli` to PyPI by wiring a GitHub Actions workflow that runs tests, validates metadata, builds distributions with `python -m build`, and uploads on `vMAJOR.MINOR.PATCH` tags while sourcing credentials from the `PYPI_API_TOKEN` secret. Provide readiness guidance so feature branches verify version bumps, changelog updates, and secret configuration before merging to `main`.

## Technical Context

**Language/Version**: Python 3.11 (per `pyproject.toml`)  
**Primary Dependencies**: Typer, Rich, Hatch build backend, PyPA `build` tool for packaging  
**Storage**: N/A (CLI with no external persistence)  
**Testing**: pytest (leveraging existing `test` extra)  
**Target Platform**: GitHub Actions runners (`ubuntu-latest`) executing release pipeline
**Project Type**: Single CLI project distributed as a PyPI package  
**Performance Goals**: N/A — focus on deterministic builds and publish success rate  
**Constraints**: Secrets must remain in GitHub Actions secret storage; release tags must align with `pyproject.toml` version and `CHANGELOG.md` entry; automation must fail-safe on validation issues  
**Scale/Scope**: Single-maintainer workflow with infrequent releases (<10 per quarter)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Secret Hygiene (Non-Negotiable)** — Plan keeps PyPI API token solely in GitHub Actions `PYPI_API_TOKEN`, never stored in VCS; documentation includes rotation guidance. **PASS**
- **Release Testing Discipline** — Workflow will run `pytest` and sanity packaging validation before upload, preventing untested artifacts from shipping. **PASS**
- **Version Governance** — Workflow enforces semantic tag ↔ `pyproject.toml` version parity with changelog entry; releases abort on mismatch, satisfying versioning controls. **PASS**

**Post-Design Review**: Phase 1 artifacts maintain all gates without introducing new violations.

## Project Structure

### Documentation (this feature)

```
kitty-specs/[###-feature]/
├── plan.md              # This file (/spec-kitty.plan command output)
├── research.md          # Phase 0 output (/spec-kitty.plan command)
├── data-model.md        # Phase 1 output (/spec-kitty.plan command)
├── quickstart.md        # Phase 1 output (/spec-kitty.plan command)
├── contracts/           # Phase 1 output (/spec-kitty.plan command)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command - NOT created by /spec-kitty.plan)
```

### Source Code (repository root)
```
.github/workflows/
└── release.yml              # Tag-triggered build-and-publish pipeline

scripts/release/
├── validate_release.py      # Ensures version, changelog, and tag alignment
└── README.md                # Describes local readiness steps and CI parity

docs/
└── releases/
    └── readiness-checklist.md  # Maintainer guidance for branch readiness
```

**Structure Decision**: Single CLI project; extend automation assets under `.github/workflows/` and supporting release scripts/docs as listed above. Existing `src/` and `tests/` layout remains unchanged.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _None_ | — | — |
