# Charter #828 Implementation Sprint

Mission type: documentation
Source mission: charter-end-user-docs-828-01KQCSYD
Branch: docs/charter-end-user-docs-828 → PR → main
Issue: https://github.com/Priivacy-ai/spec-kitty/issues/828

## Objective

Execute the fully-planned implementation sprint for Charter end-user docs parity. The source mission (`charter-end-user-docs-828-01KQCSYD`) has 10 work packages (WP01–WP10) covering gap analysis, navigation architecture, 14 new documentation pages, 5 updated pages, a validation pass, and a release handoff. This mission runs those WPs in order via `spec-kitty next`, enforces pre-flight checks, and produces one verified docs PR to `Priivacy-ai/spec-kitty:main`.

Do **not** create new planning artifacts for `charter-end-user-docs-828-01KQCSYD`. The planning artifacts on `docs/charter-end-user-docs-828` are the source of truth.

## Context

The Charter epic shipped product surface that is not yet documented. The planning mission produced a complete WP set covering:

- `docs/3x/` Charter-era hub (WP02)
- End-to-end tutorial (WP03)
- How-to guides: governance, synthesis, missions, glossary, retrospective, troubleshooting (WP04, WP05)
- Explanation pages: synthesis/DRG, profile invocation, retrospective loop (WP06)
- Reference: CLI, profile invocation, schema, migration (WP07, WP08)
- Validation pass and release handoff (WP09, WP10)

## Pre-Flight Checks

Before any WP runs, the following checks must all pass:

```bash
git status --short --branch
git pull --ff-only origin main
uv run spec-kitty --version
uv run spec-kitty agent mission check-prerequisites \
  --mission charter-end-user-docs-828-01KQCSYD --json
```

## Execution Entry Point

```bash
uv run spec-kitty next \
  --agent researcher-robbie \
  --mission charter-end-user-docs-828-01KQCSYD
```

## Functional Requirements

| ID | Requirement | Priority | Status |
|---|---|---|---|
| FR-001 | Pre-flight checks (git status, pull, version, check-prerequisites) **must** all pass before any WP execution begins. | P0 | Draft |
| FR-002 | WP01 (gap analysis and navigation architecture, including `docs/docfx.json` update) **must** complete successfully before WP02–WP08 begin. | P0 | Draft |
| FR-003 | WP02–WP08 **must** produce all planned content pages: `docs/3x/` hub, tutorial, how-to guides, explanation pages, reference pages, and migration docs. | P0 | Draft |
| FR-004 | WP09 validation pass **must** run after all WP02–WP08 pages are complete and **must** produce `checklists/validation-report.md` with evidence for every check. | P0 | Draft |
| FR-005 | WP10 **must** produce `release-handoff.md`, confirm zero TODO markers in current-facing pages, confirm zero stale `2.x` references in non-migration pages, and verify branch cleanliness. | P0 | Draft |
| FR-006 | Deliverable is one docs PR against `Priivacy-ai/spec-kitty:main` that includes WP09 validation evidence and the WP10 release handoff artifact. | P0 | Draft |
| FR-007 | If any docs validation step exposes a product bug, execution **must** stop and report the bug without attempting a product code fix. | P0 | Draft |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | All CLI content in generated pages must be verified against live `--help` output before being written. | Zero invented flags or subcommands in any published page | Draft |
| NFR-002 | Smoke commands must not pollute the source repository; all smoke tests must run in isolated temp directories that are cleaned up afterward. | Zero uncommitted changes in source repo after any smoke test | Draft |
| NFR-003 | Documentation mission phases referenced in generated pages must match `src/specify_cli/missions/documentation/mission-runtime.yaml` exactly. | Exact phase-name match, zero discrepancies | Draft |

## Constraints

| ID | Constraint | Rationale | Status |
|---|---|---|---|
| C-001 | All `spec-kitty` invocations **must** use `uv run spec-kitty` from this repository root. The ambient `spec-kitty` binary on PATH must not be used. | Ensures the correct 3.2.0a5 CLI version is exercised. | Active |
| C-002 | Any command touching hosted auth, tracker, or sync behavior **must** be prefixed with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. | Machine rule required for this environment. | Active |
| C-003 | The planning artifacts of `charter-end-user-docs-828-01KQCSYD` are the source of truth. No new planning mission may be created for that scope. | The planning work is complete; this sprint only executes it. | Active |
| C-004 | CLI command surfaces must use the corrected 3.2.0a5 names: `charter synthesize` (not `charter context`) for doctrine promotion; `charter resynthesize` for partial regeneration; `charter bundle validate` for bundle validation; `charter context --action <action>` for action context rendering; `retrospect summary` (not `retro summary`); `agent retrospect synthesize --json` / `--apply` (not `retro synthesizer`). `spec-kitty retro …` does not exist. | Prior planning artifacts were patched to reflect the correct command surface; generated pages must match. | Active |

## Success Criteria

1. All 14 planned new pages and 5 updated pages exist on `docs/charter-end-user-docs-828` and are registered in their respective `toc.yml` files and `docs/docfx.json`.
2. `uv run pytest tests/docs/ -q` passes with zero failures after all content is written.
3. `docs/docfx.json` includes `docs/3x/` and `docs/migration/` so newly added pages appear in the generated site.
4. Zero `TODO` markers remain in any current-facing page.
5. Zero stale `2.x` references in non-migration pages.
6. All CLI flag content in reference pages matches live `--help` output with zero discrepancies.
7. The tutorial smoke-test and `docs/how-to/setup-governance.md` smoke-test both complete without error in isolated temp directories.
8. `release-handoff.md` is complete with all required sections filled.
9. Branch is clean and at least one commit ahead of `main`; PR #885 is ready to merge.

## Scope

### In scope

- Executing WP01–WP10 of `charter-end-user-docs-828-01KQCSYD` in the prescribed order.
- Writing all planned documentation pages in `docs/`.
- Updating navigation files (`toc.yml`, `docs/docfx.json`).
- Running validation checks and producing the validation report.
- Producing the release handoff artifact.

### Out of scope

- Creating new planning artifacts for `charter-end-user-docs-828-01KQCSYD`.
- Fixing product bugs surfaced during validation (stop and report instead).
- Documenting research-mission-specific how-tos, custom-mission lifecycle internals, or operator-level event/sync APIs.
- Any work from #469 Phase 7 or #827 E2E canaries.

## Assumptions

- PR #885 (`docs/charter-end-user-docs-828` → `main`) remains open and has not been force-pushed since the planning patch commit `afbf6701`.
- The working directory is `/Users/robert/spec-kitty-dev/spec-kitty-20260429-161241-ycLfiR/spec-kitty`.
- `uv run spec-kitty --version` returns `3.2.0a5` or later.
- `docs/docfx.json` exists and is valid JSON that can be updated to include new directories.
