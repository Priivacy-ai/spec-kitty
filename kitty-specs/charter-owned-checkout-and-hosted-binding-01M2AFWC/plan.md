# Implementation Plan: Owned checkout charter operations and hosted binding governance

**Branch**: `codex/issue-4250-charter-owned-checkout` | **Date**: 2026-09-12 | **Spec**: [spec.md](spec.md)

## Summary

Explicit checkout ownership must survive the full charter authoring/context pipeline. Reuse canonical checkout identity validation; propagate the validated effective checkout through activation bundle freshness, include and JSON rendering. Existing implicit main-checkout semantics remain compatible. Independently author and activate CLI hosted-binding doctrine in the existing project authority. No installed CLI patch or deployment belongs here.

## Planning Decisions

User authorized cross-project recovery prevention; root authorized this bounded source fix. No unresolved product choice remains. Source API supports explicit `--owned-checkout` validated through existing ownership seams; it is not a global change to `find_repo_root`. Root owns source/tests WP01; curator owns project doctrine and activation witness WP02. Runtime allocates nonoverlapping lanes; integration happens only through Spec Kitty and independent review.

## Technical Context

**Language/Version**: Python 3.11+; installed canonical CLI 3.2.7.
**Primary Dependencies**: Typer, canonical checkout ownership, charter activation resolver.
**Storage**: Existing YAML and generated context bundle; no database.
**Testing**: pytest real temporary Git linked worktree CLI tests; make test-fast and touched subsystem suites.
**Target Platform**: Supported local Linux/macOS checkouts.
**Project Type**: Single Python project.
**Performance Goals**: No network/provider calls during checkout selection.
**Constraints**: Zero unrelated checkout mutations; preserve default behavior.
**Scale/Scope**: Two independent concerns and four functional requirements.

## Charter Check

Read charter governing principles and standing orders before authoring. Canonical source unification, red-first real entry points, activated resolver and separated review apply. Source fix is necessary because the sanctioned CLI itself routes the requested lane to main; no workaround becomes an alternate authority. No charter violation or release authority is requested. Recheck after doctrine activation because context binding changes.

## Project Structure

Mission docs live in this directory. Source ownership follows `src/specify_cli/cli/commands/doctrine.py`, `src/specify_cli/cli/commands/charter/context.py`, canonical checkout ownership helpers, and `src/charter/activation/context*.py` / `sync.py`. Project governance owns `.kittify/charter/**`, new directive/procedure artifacts, minimal config activation and a governance consumer witness test. Do not edit generated agent command copies.

## Data Flow and Contracts

CLI input → existing repository identity and explicit ownership validation → effective checkout → project authoring or activation-aware context → bundle/include/JSON output. `kernel.git_topology.git_toplevel` identifies the current checkout; `core.checkout_ownership` validates claims. `find_repo_root` and `locate_project_root` keep their broader established contracts. `ensure_charter_bundle_fresh` and JSON bundle-root selection currently normalize to common-dir primary and must accept explicit validated effective ownership without silently changing defaults. Explicit invalid/foreign claims fail before file writes. Tests use distinct primary and lane doctrine and absent/inactive artifacts, not mock-only selected-path assertions.

The project directive `CLI_HOSTED_BINDING_COMPATIBILITY` requires `cli-hosted-binding-verification`: native provider ID, verified current locator and installation eligibility, supported client/SaaS/relay versions, fail-closed mismatch and receipt-based completion. Canonical activation registers provenance; actual effective consumer must reject missing source/activation. Existing identity behavior is governed, not rewritten in this mission.

## Implementation Concern Map

### IC-01 — Validated effective checkout propagation
- Purpose: Fix authoring and context isolation through all downstream bundle consumers.
- Relevant requirements: FR-001, FR-002, NFR-001, C-001, C-002.
- Affected surfaces: CLI command wrappers, checkout ownership integration, activation context/sync/JSON, real CLI regression tests and usage docs.
- Sequencing/depends-on: None.
- Risks: Entry-point-only fixes still leak primary context; global root-helper changes break unrelated commands. Propagate explicit context narrowly.

### IC-02 — Hosted binding governance
- Purpose: Bind contributor decisions to stable identity and truthful completion.
- Relevant requirements: FR-003, FR-004, NFR-002, C-001, C-002.
- Affected surfaces: Existing charter/config, new directive/procedure and activation witness test.
- Sequencing/depends-on: Authoring can proceed independently using explicit activation root; final canonical CLI lane witness needs IC-01 integration.
- Risks: File presence or source tests can masquerade as installed protection; record source-only scope and use inactive/missing negative witnesses.

## Validation and Operational Boundary

WP01 demonstrates the old defect red-first through real CLI commands; tests creation, text/JSON/include context, nested paths, invalid ownership and unchanged primary bytes. WP02 validates schemas and canonical activation, then removes each activation/source to prove refusal. Run relevant tests plus required baseline. Independent reviewer validates integrated checkout pipeline. Record source revision and canonical context digest; deployment of a released CLI remains outside scope and open in the recovery program.

## Complexity Tracking

No violations. Two lanes avoid overlapping source/config ownership; no new repository identity abstraction or installed-tool mutation.
