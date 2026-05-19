# Implementation Plan: Retrospective Learning Default-On Policy

**Branch**: `main` | **Date**: 2026-05-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/retrospective-default-policy-01KS049J/spec.md`
**Mission ID**: `01KS049J4V9CSWBKJHTY2FB69H` (`mid8` `01KS049J`)

## Summary

Replace today's env-var-gated retrospective behavior (`SPEC_KITTY_RETROSPECTIVE`, `SPEC_KITTY_MODE`, `facilitator_callback=None`) with a durable `RetrospectivePolicy` model resolved from `.kittify/config.yaml` and charter frontmatter. Wire a pure-Python retrospective generator (decision `01KS051316C8Z0SDEKZ2B088CS` resolved `pure_python_module`) into the runtime, default to post-completion best-effort with warn-on-failure, preserve the existing strict gate as policy-owned, and add first-class `spec-kitty retrospect create` and `spec-kitty retrospect backfill` CLI surfaces. Tighten `agent retrospect synthesize` so its empty-record fallback no longer masquerades as authoring. Deprecate the env vars to test/dev overrides for one release cycle. Update docs and shipped skills so `summary` (read-only), `create` (authors), `backfill` (historical), and `synthesize` (proposal preview/apply on an existing record) carry distinct, accurate meanings — correcting PR #1136's post-merge wording in the same pass. The #1137 pytest-collection issue closed not-a-bug (decision `01KS0513SEHSEE82WN4RJBFDRG`); this mission ships only the CONTRIBUTING note explaining the namespace-package corruption diagnostic.

## Technical Context

**Language/Version**: Python 3.11+ (CLI requirement; project pyproject pins `>=3.11`).
**Primary Dependencies**: `ruamel.yaml` (config + charter parsing, already in `pyproject.toml`), `pydantic` v2 (or the project's existing dataclass-based domain models — confirm in research), `typer` + `rich` (CLI surface), `pytest` + `coverage` (tests), the in-tree event log (`spec_kitty_events` consumed via the frozen public surface per FR-024), the in-tree `specify_cli.status` reducer/event log, and the existing `specify_cli.retrospective` package (schema, writer, summary).
**Storage**: Filesystem only. Policy in `.kittify/config.yaml` (top-level `retrospective:` block) and optionally in charter frontmatter under `retrospective:`. Records in `.kittify/missions/<mission_id>/retrospective.yaml`. Events in the canonical per-mission `kitty-specs/<mission_slug>/status.events.jsonl`.
**Testing**: `pytest` under `uv run`. Unit tests in `tests/retrospective/`, integration in `tests/integration/retrospective/`, contract tests in `tests/contract/` if new event types are added, regression fixture-loading in `tests/next/test_retrospective_terminus_wiring.py`. CI runs via existing GitHub Actions workflows (`.github/workflows/ci-quality.yml` etc).
**Target Platform**: Local developer machines (macOS, Linux, Windows-via-WSL). No hosted/SaaS dependency for the default path. `SPEC_KITTY_ENABLE_SAAS_SYNC=1` only when an integration test exercises the hosted ingress path.
**Project Type**: Single Python project (existing repo layout). No new top-level packages; this mission adds modules under `src/specify_cli/retrospective/` and `src/specify_cli/cli/commands/`.
**Performance Goals**: NFR-005 — default-policy retrospective generation completes in ≤ 2 seconds wall-clock for a representative mission (≤ 5 WPs, ≤ 50 status events). NFR-001 — targeted retrospective test suite under 60 seconds.
**Constraints**: NFR-007 (additive-only event/schema changes), C-003 (no deletion of existing schema/events/records), C-005 (no auto-apply of structural doctrine/DRG/glossary changes by default), C-004 (env vars never durable policy), NFR-006 (one deprecation warning per process, not per command).
**Scale/Scope**: ~30 files touched in `src/`: new modules in `retrospective/` (policy resolver, generator), edits in `next/runtime_bridge.py`, `next/_internal_runtime/retrospective_terminus.py`, `cli/commands/agent_retrospect.py`, and a new `cli/commands/retrospect.py`. ~12 doc/skill files touched. Coverage target NFR-004 = ≥ 85% for new code paths.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project carries a charter under `.kittify/charter/`. Charter context for this action was loaded via `spec-kitty charter context --action plan --json` (returned `mode: bootstrap`). Charter-derived gates for this mission:

- **Local-first, env-var-free product configuration**: ✓ FR-001/FR-002/FR-015 align — durable policy lives in `.kittify/config.yaml` and charter frontmatter; env vars are demoted to test/dev overrides.
- **Additive evolution, no deletion of historical state**: ✓ C-003 forbids deletion of existing retrospective schema/events/records. NFR-007 enforces additive-only payload changes.
- **Human-approval for structural changes**: ✓ FR-010 and C-005 keep doctrine/DRG/glossary mutation behind explicit human approval; auto-apply allowed only for an enumerated low-risk class.
- **Frozen public consumer surface for `spec_kitty_events` (FR-024 from the events-consumer-contract dossier)**: ✓ FR-017 explicitly refuses a code workaround in `validate.py` for #1137; resolution is documentation-only.
- **Mission identity uses ULID + mid8 (mission 083+)**: ✓ C-007 — this mission uses `mission_id=01KS049J4V9CSWBKJHTY2FB69H`, slug `retrospective-default-policy-01KS049J`. `mission_number` stays `null` pre-merge.

No charter conflicts; no gate violations. Re-check after Phase 1 design (no anticipated drift; design is small and aligned).

## Project Structure

### Documentation (this feature)

```
kitty-specs/retrospective-default-policy-01KS049J/
├── plan.md              # This file
├── spec.md              # Mission specification (committed)
├── research.md          # Phase 0 output — defaults & precedent decisions
├── data-model.md        # Phase 1 output — RetrospectivePolicy, RetrospectiveRecord, events
├── quickstart.md        # Phase 1 output — operator's quickstart for the new commands
├── contracts/           # Phase 1 output — event payload contracts + CLI contracts
│   ├── retrospective-policy.schema.json
│   ├── retrospective-record.schema.json
│   ├── retrospect-cli.contract.md
│   └── retrospective-events.contract.md
├── checklists/
│   └── requirements.md  # Spec quality checklist (committed)
├── decisions/           # Decision Moment artifacts
├── status.events.jsonl  # Per-mission canonical event log
├── meta.json
└── tasks/               # Phase 2 output — created by /spec-kitty.tasks
```

### Source Code (repository root)

This mission touches an existing single-Python-project layout. Key paths:

```
src/specify_cli/
├── retrospective/
│   ├── __init__.py
│   ├── config.py            # EXISTS — extend or replace with RetrospectivePolicy resolver
│   ├── mode.py              # EXISTS — fold into policy resolver; keep as compatibility shim
│   ├── policy.py            # NEW — RetrospectivePolicy model + resolver
│   ├── generator.py         # NEW — pure-Python generator (decision: pure_python_module)
│   ├── schema.py            # EXISTS — additive policy-source field
│   ├── writer.py            # EXISTS — extend to write policy source attribution
│   ├── summary.py           # EXISTS — read-only; ensure "ran no findings" vs "missing" vs "failed" distinction
│   └── events.py            # NEW or extended — RetrospectiveCaptured / RetrospectiveCaptureFailed event payloads
├── next/
│   ├── runtime_bridge.py    # EXISTS — replace facilitator_callback=None with real generator wiring
│   └── _internal_runtime/
│       └── retrospective_terminus.py  # EXISTS — consume policy decision; emit events
├── cli/commands/
│   ├── agent_retrospect.py  # EXISTS — tighten silent-fabrication fallback
│   └── retrospect.py        # NEW — `spec-kitty retrospect create` + `backfill`
├── doctrine_synthesizer/    # EXISTS — proposal application path unchanged in shape
└── status/
    └── reducer.py           # Verify additive event types reduce cleanly (FR-021)

src/doctrine/
├── agent_profiles/shipped/retrospective-facilitator.agent.yaml   # Review for FR-020 alignment
└── skills/
    ├── spec-kitty-mission-review/SKILL.md            # FR-019
    ├── spec-kitty-implement-review/SKILL.md          # FR-019
    ├── spec-kitty-program-orchestrate/SKILL.md       # FR-019
    └── spec-kitty-runtime-next/SKILL.md              # FR-019

tests/
├── retrospective/                                 # Unit tests for policy/generator/writer/summary
├── integration/retrospective/                     # Default + strict + warn flows end-to-end
├── next/test_retrospective_terminus_wiring.py    # Runtime wiring assertion
├── agent/test_orchestrator_commands_integration.py  # TestAcceptMission still green
└── retrospective/test_specify_synthesize_fallback.py  # FR-014 fallback tightening

docs/
├── how-to/accept-and-merge.md             # FR-018 — correct PR #1136 wording
├── how-to/merge-feature.md                # FR-018
├── how-to/use-retrospective-learning.md   # FR-018 — canonical user-facing how-to
├── explanation/retrospective-learning-loop.md  # FR-018
├── reference/cli-commands.md              # FR-018 — `retrospect create`/`backfill`
├── reference/slash-commands.md            # FR-018
└── tutorials/your-first-feature.md        # FR-018

CONTRIBUTING.md                            # FR-017 — namespace-package diagnostic note
README.md                                  # FR-018 — top-level retrospective-learning blurb
```

**Structure Decision**: Single project (Option 1). No new top-level package directories; all changes land within the existing `src/specify_cli/` and `docs/` trees. The new `retrospect.py` CLI surface follows the convention already established by `cli/commands/agent_retrospect.py`. The new `retrospective/policy.py` and `retrospective/generator.py` modules sit beside existing `retrospective/config.py` and `retrospective/schema.py`.

## Bulk-Edit Classification (FR-022)

Per the `spec-kitty-bulk-edit-classification` skill, this mission has two distinct bulk-edit shapes that we'll capture in `occurrence_map.yaml` at `/spec-kitty.tasks` time:

1. **Env-var deprecation messaging**: `SPEC_KITTY_RETROSPECTIVE` and `SPEC_KITTY_MODE` are existing identifiers referenced across code (env-var lookups), tests, and docs. The deprecation re-frames them as "test/dev overrides only, durable replacements live in `retrospective.enabled` / `retrospective.timing` + `retrospective.failure_policy`." This qualifies as `change_mode: bulk_edit`.

2. **Doc semantics correction**: The phrases "summary captures retrospective learning" and "synthesize generates the retrospective" — present in PR #1136 docs and in shipped skills — are changing to distinct semantic categories (`summary` aggregates, `create` authors, `backfill` historical-authors, `synthesize` previews/applies proposals from an existing record). This is terminology change across many files; it qualifies as `change_mode: bulk_edit`.

`/spec-kitty.tasks` will produce `kitty-specs/retrospective-default-policy-01KS049J/occurrence_map.yaml` with all 8 standard categories (code_symbols, import_paths, filesystem_paths, serialized_keys, cli_commands, user_facing_strings, tests_fixtures, logs_telemetry) before the first WP starts. The plan's WP-Env-Deprecate and WP-Docs-Skills are the carriers for the bulk edits.

## Engineering Alignment

Captured for the record so future re-reads can pick up cold:

- **Generator architecture**: Pure-Python module in `src/specify_cli/retrospective/generator.py`, called directly by `runtime_bridge.py`. Profile invocation of `retrospective-facilitator.agent.yaml` is NOT the runtime default this release. The profile YAML stays as descriptive metadata, and `apply_proposals` still routes through the existing `agent retrospect synthesize` path for human approval. (Decision `01KS051316C8Z0SDEKZ2B088CS` resolved `pure_python_module`.) See ADR [`architecture/3.x/adr/2026-05-19-1-retrospective-default-policy-architecture.md`](../../architecture/3.x/adr/2026-05-19-1-retrospective-default-policy-architecture.md) for the durable record.
- **#1137**: Documentation-only resolution per the issue's closing comment. No code fallback in `validate.py`; this would violate the FR-024 frozen public-surface contract. CONTRIBUTING.md gets the diagnostic + fix command. (Decision `01KS0513SEHSEE82WN4RJBFDRG` resolved `out_of_scope_not_a_bug_add_contributing_note`.)
- **Policy file location**: `.kittify/config.yaml` top-level `retrospective:` block is the canonical home. Charter frontmatter under `retrospective:` is the governed-project escalation point. Precedence: charter wins for governed projects (charter must opt into being overridable via an explicit `retrospective.precedence: config` directive). For projects without a charter, config-file values fill the resolved policy. Captured durably in the ADR cited above.
- **Mission completion definition**: For retrospective-gate purposes, the canonical evaluation point is "immediately before the runtime emits `MissionCompleted`, after all WPs are in terminal lanes AND the merge has landed." Defined in [data-model.md](./data-model.md#mission-completion-canonical-definition) and in spec.md Domain Language. The strict gate hangs off this point; `--skip-retrospective` is the documented bypass with logged actor/provenance.
- **Malformed-policy handling (FR-024)**: The resolver never raises an unhandled exception. Malformed `.kittify/config.yaml` or charter frontmatter produces a `PolicyResolutionError` that — under default policy — downgrades to a `RetrospectiveCaptureFailed` event with `failure_category: policy_resolution_error` and the completion path proceeds with built-in defaults. Under strict policy, malformed input blocks completion with a structured reason. Specified in [data-model.md](./data-model.md#malformed-input-handling-fr-024).
- **Reducer regression fixtures (FR-025)**: An explicit fixture set under `tests/retrospective/fixtures/event_logs/` covers FR-021's byte-identical reduction guarantee for both "no retrospective events" and "with new retrospective events appended" cases. Fixture inventory checked in alongside expected snapshots.
- **Shim retirement for `config.py` / `mode.py` (FR-023)**: The planning task decomposition MUST resolve into one of two terminal states for these modules: (a) folded into `policy.py` and deleted with all references updated within this mission, OR (b) retained as documented compatibility shims with a published retirement plan (deprecation target version, follow-up issue link). "Half-deleted" is not an acceptable end state.
- **Overwrite semantics for `retrospect create`**: Default is **error if record exists**; user must pass `--overwrite` to replace or `--update` to merge (merge semantics defined in `data-model.md`). Either action logs actor/provenance in the mission's event log.
- **Event-log integration**: Add new event types `RetrospectiveCaptured` and `RetrospectiveCaptureFailed` only if no existing event in `spec_kitty_events` already serves the purpose. Research will confirm; if existing events suffice, reuse them with additive policy-source attribution. Either path is additive (NFR-007).
- **Synthesize fabrication invariant**: `provenance.kind == synthesize_fabricate` MUST imply `findings_status == ran_no_findings`. Writer validation enforces this; tests cover both the default-error path and the explicit-`--fabricate-empty` path.

## Complexity Tracking

No Charter Check violations were found, so this section is empty. The mission's scope is intentionally narrow (CLI/runtime/docs in one repo, no SaaS, no schema breakage, no upstream dependency releases).

## Phase 0 Output

See [research.md](./research.md) for resolved unknowns (policy precedence semantics, existing event-type coverage, generator-input inventory, deprecation-warning UX standards).

## Phase 1 Output

- [data-model.md](./data-model.md) — `RetrospectivePolicy`, `RetrospectiveRecord` additions, event-payload deltas.
- [contracts/](./contracts/) — JSON schemas for policy and record, CLI contracts for `retrospect create` / `backfill`, event-payload contracts for new (or extended) retrospective events.
- [quickstart.md](./quickstart.md) — operator's quickstart for the new defaults and CLI commands.

## Stop Point

This command ends after Phase 1 planning. `/spec-kitty.tasks` is the next step (user-invoked) and will produce `tasks.md` + per-WP files under `tasks/`, plus `occurrence_map.yaml` per FR-022.
