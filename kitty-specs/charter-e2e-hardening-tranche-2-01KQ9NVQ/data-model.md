# Data Model: Charter E2E Hardening Tranche 2

**Mission**: `charter-e2e-hardening-tranche-2-01KQ9NVQ`
**Date**: 2026-04-28

## Summary

**This mission introduces no new entities, no schema changes, and no new persisted state.**

The mission fixes existing public-CLI behavior and tightens an existing E2E test. All entities the mission touches already exist in the codebase. No new models are added.

## Existing entities (no change to schema)

The entities below are listed for traceability between the spec, the contracts, and the verification plan. They are **not** redefined by this tranche.

| Entity | Where it lives today | Touched by this mission how |
|---|---|---|
| `.kittify/metadata.yaml` | Project root, written by `spec-kitty init` and updated by upgrade migrations | FR-001 ensures `spec_kitty.schema_version` and `spec_kitty.schema_capabilities` are stamped at init time. The set of fields and their canonical values are unchanged from the existing upgrade-migration source of truth. |
| `.kittify/doctrine/` | Project root, populated by `charter synthesize` | FR-004 ensures the directory and its expected synthesis manifest/provenance artifacts are produced by the public `synthesize --adapter fixture --json` path. The artifact tree shape is unchanged from what existing fixture/adapter implementations target. |
| `.kittify/events/profile-invocations/` | Project root, populated by mission-step-contracts executor | FR-007 ensures paired `started` and `completed` records exist for issued composed actions. Record schema (action identity, outcome vocabulary) is unchanged from the existing canonical writer. |
| `charter.md` (generated) | Path under project root chosen by `charter generate` | FR-002 makes generate↔validate agree about where the file must live and how it must be tracked. Path and content schema unchanged. |
| Issued step (returned by `next --json`) | Wire-format, no persisted file | FR-006 makes the `prompt_file` field strictly non-empty and resolvable. Field set unchanged otherwise. |
| Profile-invocation lifecycle record | JSON file under `.kittify/events/profile-invocations/` | FR-007 / FR-010 ensure paired records exist. Record schema is the canonical one written by `src/specify_cli/invocation/`; not redefined here. |

## Why no data-model changes

- **No new persisted state**: All artifacts the mission touches are already produced by existing CLI commands. The mission ensures they are produced reliably and on the public path; it does not change their shape.
- **No new wire formats beyond contracts**: The JSON envelopes are documented in `contracts/` to lock current public CLI shapes. They are not new schemas; they are explicit captures of behavior the public CLI must honor.
- **Charter unchanged**: No new charter sections, new doctrine artifact types, or new mission-runtime YAML keys are introduced.

## Implication for plan / tasks

WPs do **not** need a data-model migration step. WP02 (init schema metadata) reuses existing schema constants from upgrade migrations; WP07 (profile-invocation lifecycle) extends the existing executor's writer to cover composed actions but does not redefine the record format. WP08 (E2E hardening) reads existing artifacts and asserts existing wire shapes.

If verification (WP01 research) discovers that fixing #841 requires *modifying* an existing schema (e.g., adding a `tracking_instruction` field to `charter generate --json`), this document must be updated and Charter Check re-evaluated before WP04 commits. Treat any schema delta as a Decision Documentation event under DIRECTIVE_003.
