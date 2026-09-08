# Implementation Plan: Project-layer doctrine ingestion

**Branch**: `issue-4103-migrate-guidance-glossary-step` | **Date**: 2026-09-09 | **Spec**: [spec.md](spec.md)

## Summary

Preserve PR #4104 and transplant its glossary-procedure commit onto released v3.2.6.1. Implement the five code defects as ordered, separable commits. Reuse public doctrine handlers for charter command parity, resolve seed terms through the existing glossary store, and register direct-authored project artifacts in the canonical graph/provenance path. Then repair cascade and layered resynthesis, with mutation preflight and realistic CLI acceptance.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Typer, Pydantic, ruamel.yaml, existing charter and glossary domain services
**Storage**: Project YAML artifacts, charter activation bundle, DRG and synthesis provenance manifest
**Testing**: pytest targeted CLI/charter/doctrine/glossary suites, ruff, mypy, terminology guard, fresh-repository acceptance transcript
**Target Platform**: macOS local verification; supported CI platforms
**Project Type**: Python CLI and domain packages
**Performance Goals**: Preserve local command execution without network dependencies
**Constraints**: One existing PR; released v3.2.6.1 base; final remote CI only insofar as possible; no new suppressions or singular-directory changes
**Scale/Scope**: Six issues, five project artifact kinds, four profile dependency kinds

## Charter Check

Red-first CLI reproductions before each functional fix. Existing authorities own kind vocabulary, schema validation, reference edges and layer precedence. Independent architect investigation completed under resolved architect-alphonso; independent implementation review required before handoff. Operator controls merge. User's explicit one-PR and ordered-commit contract supersedes creating additional delivery branches or PRs.

## Project Structure

CLI adapter changes: `src/specify_cli/cli/commands/charter/`, `doctrine.py`, `glossary.py`.
Domain changes: `src/charter/offering/drg/`, `src/charter/activation/`, existing synthesis/provenance and compiler resolution.
Verification: corresponding CLI tests, `tests/charter/`, `tests/doctrine/`, `tests/glossary/`, terminology guard and fresh-repository transcript.

## Design and Data Flow

`charter new` writes canonical user-owned project YAML. Validation uses existing schema registry. Activation discovers validated project nodes and reference edges, records source provenance, computes cascade, validates resynthesis support, then writes activations. Context compilation resolves activated IDs across built-in, org and project layers. Status reads the same provenance/manifest authority. Glossary show falls back to the same seed store as list when compiled content is unavailable.

Choice (b) from #4097: direct-authored registration fits the required new/validate/activate acceptance flow and avoids duplicate generated authority. Record the rationale on the issue before code changes. Preserve unrelated graph entries and user source files; avoid rewriting sources during registration.

## Ordered Work and Verification

One sequential WP owns these tightly coupled changes; internal commits follow #4098, #4102, #4097, #4100, #4101 after existing #4103. This avoids conflicting ownership of shared activation/compiler/provenance files. Run local regressions before each commit; consolidate planning commits before delivery if needed. Run full owning subsystem suites and fresh CLI acceptance before the final push. Retarget existing PR to maintenance release base, preserve previous verification block, add six issue sections and transcript, then verify CI on the actual final head.

## Risks

Layer roots differ: project lookup receives `.kittify`, not `.kittify/doctrine`. Manifest kinds currently omit profiles/procedures. Project scan emits profile nodes without dependencies. Resynthesis currently mutates activation before failing. Tests must start with direct-written files and no preseeded graph to expose these defects.
