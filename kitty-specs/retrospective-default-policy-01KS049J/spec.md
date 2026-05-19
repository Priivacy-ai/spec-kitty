# Retrospective Learning Default-On Policy

**Mission ID**: 01KS049J4V9CSWBKJHTY2FB69H
**Slug**: retrospective-default-policy-01KS049J
**Mission Type**: software-dev
**Target Branch**: main
**Created**: 2026-05-19

## Purpose

Make retrospective learning a default-on, policy-driven feedback loop in Spec Kitty 3.2.0. Every completed mission should produce a useful `.kittify/missions/<mission_id>/retrospective.yaml`. Policy lives in `.kittify/config.yaml` and charter frontmatter — not in environment variables. The default behavior is "post-completion, warn-on-failure"; strict projects can opt into pre-completion blocking via durable policy. Real authoring surfaces (`spec-kitty retrospect create`, `backfill`) replace the practice of using `agent retrospect synthesize` (a proposal preview/apply tool) as the de facto author.

## Context

Tracking issues:

- Primary epic: [Priivacy-ai/spec-kitty#1138](https://github.com/Priivacy-ai/spec-kitty/issues/1138) — Epic: Make retrospective learning default-on and policy-driven for 3.2.0
- 3.2.0 release context: [#822](https://github.com/Priivacy-ai/spec-kitty/issues/822) — Epic: 3.2.0 stabilization and release readiness
- Pytest collection blocker (in scope this mission): [#1137](https://github.com/Priivacy-ai/spec-kitty/issues/1137) — `spec_kitty_events` 5.1.0 missing `normalize_event_id`/`Event` exports
- Schema-version bootstrap papercut surfaced during specify: [#1158](https://github.com/Priivacy-ai/spec-kitty/issues/1158) — `mission create` blocked while `upgrade` reports up-to-date
- Recent doc PR to revisit: [#1136](https://github.com/Priivacy-ai/spec-kitty/pull/1136) — Clarify accept, merge, and retrospective workflow (its post-merge guidance currently overstates what `summary`/`synthesize` capture)

Historical retrospective tranche (Phase 6 epic [#468](https://github.com/Priivacy-ai/spec-kitty/issues/468)): [#506](https://github.com/Priivacy-ai/spec-kitty/issues/506), [#507](https://github.com/Priivacy-ai/spec-kitty/issues/507), [#508](https://github.com/Priivacy-ai/spec-kitty/issues/508), [#509](https://github.com/Priivacy-ai/spec-kitty/issues/509), [#511](https://github.com/Priivacy-ai/spec-kitty/issues/511), [#965](https://github.com/Priivacy-ai/spec-kitty/issues/965).

Today's incoherence:

- `SPEC_KITTY_RETROSPECTIVE=1` is the user-facing on/off switch.
- `SPEC_KITTY_MODE=autonomous` is the user-facing strict-mode switch.
- `runtime_bridge.py` passes `facilitator_callback=None` into `run_terminus`, so enabled strict paths fail closed instead of producing useful learning.
- `spec-kitty retrospect summary` is read-only aggregation, but PR #1136 docs treat it as the post-merge "capture the retrospective" step.
- `spec-kitty agent retrospect synthesize` is a proposal preview/apply tool, but it has a quiet fallback that fabricates an empty completed record when artifacts look sufficient — used in practice as the de facto authoring surface.
- No `retrospect create` or `retrospect backfill` command exists; there is no real, durable authoring path.

The product thesis (from the workspace's `start-here.md` handoff):

> Retrospective learning should be a core Spec Kitty feedback loop, not an env-gated experimental terminus trap.

Workspace handoff: `/Users/robert/spec-kitty-dev/retrospective-default-policy-20260519-131623-oUG5Kq/start-here.md`. Local CLI/runtime work only; SaaS sync flag (`SPEC_KITTY_ENABLE_SAAS_SYNC=1`) is not normally required for this mission.

## Hotspot

The following are the highest-leverage code/doc surfaces the implementation will touch. Final task decomposition happens at `/spec-kitty.plan` and `/spec-kitty.tasks` time.

| Item | Location |
|---|---|
| Env-driven policy resolver (today) | `src/specify_cli/retrospective/config.py` |
| Mode/strictness resolver (today) | `src/specify_cli/retrospective/mode.py` |
| Runtime callback wiring (`facilitator_callback=None`) | `src/specify_cli/next/runtime_bridge.py` |
| Terminus integration point | `src/specify_cli/next/_internal_runtime/retrospective_terminus.py` |
| Schema definitions | `src/specify_cli/retrospective/schema.py` |
| Writer | `src/specify_cli/retrospective/writer.py` |
| Read-only aggregation | `src/specify_cli/retrospective/summary.py` |
| Existing CLI surface (preview/apply) | `src/specify_cli/cli/commands/agent_retrospect.py` |
| Proposal synthesis | `src/specify_cli/doctrine_synthesizer/` |
| Shipped retrospective-facilitator profile | `src/doctrine/agent_profiles/shipped/retrospective-facilitator.agent.yaml` |
| Pytest collection blocker (issue #1137) | `src/specify_cli/status/validate.py` imports `normalize_event_id` from `spec_kitty_events`; 5.1.0 lacks the top-level export |
| Docs likely to update | `README.md`, `docs/how-to/accept-and-merge.md`, `docs/how-to/merge-feature.md`, `docs/how-to/use-retrospective-learning.md`, `docs/explanation/retrospective-learning-loop.md`, `docs/reference/cli-commands.md`, `docs/reference/slash-commands.md`, `docs/tutorials/your-first-feature.md` |
| Shipped skills likely to update | `src/doctrine/skills/spec-kitty-mission-review/SKILL.md`, `spec-kitty-implement-review/SKILL.md`, `spec-kitty-program-orchestrate/SKILL.md`, `spec-kitty-runtime-next/SKILL.md` |

## User Scenarios & Testing

### Primary Scenario — Default post-completion success

**Actor**: A developer who has just merged a mission via `spec-kitty merge`.
**Trigger**: Mission completion path runs after merge with the default `RetrospectivePolicy` (`enabled: true`, `timing: post_completion`, `failure_policy: warn`).
**Happy-path outcome**: The runtime invokes the real retrospective generator. It reads `spec.md`, `plan.md`, `tasks.md`, `tasks/WP*.md`, `meta.json`, `status.events.jsonl`, review/rejection cycles, mission-review report (if present), and applicable DRG/doctrine/glossary context. It writes `.kittify/missions/<mission_id>/retrospective.yaml` (or the canonical analog) with `helped`, `not_helpful`, `gaps`, `proposals`, provenance, mission metadata, and evidence references. A `RetrospectiveCaptured` (or equivalent) event lands in the event log. Mission completion proceeds normally. No doctrine/DRG/glossary mutation happens automatically — proposals stay pending human approval.

### Strict Scenario — Pre-completion block on missing/failed retrospective

**Actor**: A governed-project operator running on policy `timing: before_completion, failure_policy: block`.
**Trigger**: Mission ready to complete; retrospective generation either fails or has not run.
**Outcome**: Completion blocks with a structured reason that cites the policy source (e.g. `.kittify/config.yaml#retrospective.timing` or charter frontmatter path) and the failure category. Operator fixes the underlying cause (artifacts present, generator error, etc.) and re-runs. Skipping requires explicit permission and records actor/provenance in the event log.

### Failure-Warn Scenario — Default policy, generator error

**Actor**: A developer on the default policy whose generator hits an exception (e.g. malformed `status.events.jsonl`, missing `mission-review-report.md` that was expected, a transient I/O error).
**Outcome**: A warning event is emitted with the failure category and remediation hint; mission completion is not blocked. The user can run `spec-kitty retrospect create --mission <handle>` later to author the record.

### Opt-Out Scenario — `enabled: false`

**Actor**: A project that has set `retrospective.enabled: false` in `.kittify/config.yaml`.
**Outcome**: No generator runs at any mission boundary. No warning. No event noise. `spec-kitty retrospect create --mission <handle>` continues to work as an explicit manual surface.

### Authoring Scenario — `retrospect create` for one mission

**Actor**: A maintainer who wants to author or refresh a retrospective for a specific completed mission.
**Trigger**: `spec-kitty retrospect create --mission <handle>` (where `<handle>` is `mission_id` ULID, `mid8`, or `mission_slug`).
**Outcome**: A real `retrospective.yaml` is authored from mission artifacts. If a record already exists, the command does not silently overwrite — the user must pass an explicit flag (e.g. `--overwrite` or `--update`) and the action is recorded in the event log with actor/provenance. Missing artifacts produce actionable errors, not empty "completed" records.

### Backfill Scenario — historical missions

**Actor**: A maintainer who wants to seed retrospectives for missions completed before this mission shipped.
**Trigger**: `spec-kitty retrospect backfill --since 2026-05-01` (or another time window) with optional `--mission <handle>` for single-target backfill.
**Outcome**: For each candidate mission, the command attempts authoring. JSON output enumerates `created`, `skipped` (with reason: already exists / not completed / not in window), `failed` (with category), and `next_actions`. Existing records are never silently overwritten.

### Synthesize Scenario — preview/apply unchanged but no longer the author

**Actor**: A maintainer reviewing proposals in an already-authored `retrospective.yaml`.
**Trigger**: `spec-kitty agent retrospect synthesize --mission <handle> [--preview | --apply <proposal_id>]`.
**Outcome**: Preview shows the proposed glossary/DRG/doctrine changes. Apply requires explicit selection and human confirmation. Auto-application is permitted only for explicitly low-risk classes (e.g. `flag_not_helpful`) and only when policy permits. Structural changes to doctrine/DRG/glossary never auto-apply.

### Env-Var Deprecation Scenario

**Actor**: A developer with `SPEC_KITTY_RETROSPECTIVE=1` and `SPEC_KITTY_MODE=autonomous` in their shell.
**Outcome**: The runtime emits a deprecation warning at first use per session: `SPEC_KITTY_RETROSPECTIVE is deprecated; set retrospective.enabled in .kittify/config.yaml or charter`. The runtime still honors the env var for test/dev use this release cycle, but it does not override durable policy when both are present (durable policy wins, deprecation warning still emitted). Tests prefer injected policy over ambient env.

### Acceptance Rule (must always hold)

For every completed mission under default policy:
- The retrospective generator MUST be attempted exactly once.
- On success, `retrospective.yaml` MUST exist with a schema-valid record and a `RetrospectiveCaptured` event MUST appear in `status.events.jsonl`.
- On failure, a `RetrospectiveCaptureFailed` (or equivalently named) event MUST be emitted with a structured failure category, and mission completion MUST NOT be blocked.
- The policy source MUST be recorded on every emitted retrospective event.
- Generation MUST NOT mutate doctrine/DRG/glossary as a side effect.

## Domain Language

| Term | Meaning |
|---|---|
| RetrospectivePolicy | The durable policy model defining whether retrospective generation runs, when (before vs after completion), how to react to failure (block vs warn), and which permission classes are granted. Resolved from `.kittify/config.yaml` and charter frontmatter with documented precedence. |
| Retrospective record | A schema-valid YAML artifact (`retrospective.yaml`) containing `helped`, `not_helpful`, `gaps`, `proposals`, provenance, mission metadata, and evidence references for a single mission. |
| Generator | The runtime code path that inspects mission artifacts and produces a `RetrospectiveRecord`. Distinct from "writer" (persistence) and "synthesizer" (proposal application). |
| Synthesize | The existing proposal preview/apply surface (`spec-kitty agent retrospect synthesize`). Operates on proposals inside an already-authored retrospective record. Not a real author. |
| Create | The new authoring surface (`spec-kitty retrospect create`) that runs the generator on demand for one mission. |
| Backfill | The new historical-authoring surface (`spec-kitty retrospect backfill`) that authors records for previously completed missions. |
| Summary | The read-only aggregation surface (`spec-kitty retrospect summary`). Reports across existing records. Not an author. |
| Policy source | A structured pointer to where a given policy field was resolved from (e.g. `.kittify/config.yaml#retrospective.timing`, charter frontmatter key, env-var fallback). Recorded on emitted retrospective events. |
| Failure policy | Branch of `RetrospectivePolicy` controlling block-vs-warn on generation failure. Default `warn`. |
| Timing | Branch of `RetrospectivePolicy` controlling `before_completion` vs `post_completion`. Default `post_completion`. |
| Apply mode | Branch of `RetrospectivePolicy` controlling whether generated proposals can be auto-applied. Default `require_human` for all proposal classes except an explicitly enumerated low-risk allowlist. |
| Empty findings | A retrospective record explicitly representing "ran, no findings". MUST be distinct from "missing retrospective" or "failed retrospective" in both event payloads and read-only summaries. |

## Functional Requirements

| ID | Description | Status |
|---|---|---|
| FR-001 | A `RetrospectivePolicy` model and resolver exist that read policy from `.kittify/config.yaml` (top-level `retrospective:` block) and charter frontmatter with documented precedence (config overrides charter only on explicit `precedence: config` directive; charter wins by default for governed projects). The resolver returns the resolved policy AND a `source` map naming the origin of every resolved field. | Required |
| FR-002 | The default `RetrospectivePolicy` is `enabled: true`, `timing: post_completion`, `failure_policy: warn`, `write_record: true`, `generate_proposals: true`, `apply_proposals: require_human`. Default permissions: `write_record: true`, `inspect_mission_artifacts: true`, `propose_glossary_changes: true`, `propose_drg_changes: true`, `propose_doctrine_changes: true`, `apply_low_risk_changes: false`, `apply_structural_changes: false`. | Required |
| FR-003 | Explicit opt-out (`retrospective.enabled: false`) prevents any generator invocation at any mission boundary, emits no warning, and produces no retrospective events. | Required |
| FR-004 | Strict policy (`timing: before_completion + failure_policy: block`) preserves today's gate semantics: missing or failed retrospective blocks completion with a structured reason that cites the resolved policy source. | Required |
| FR-005 | The runtime no longer passes `facilitator_callback=None` into `run_terminus` for enabled paths. A real generator callback is wired such that the strict path produces useful learning rather than failing closed. | Required |
| FR-006 | A retrospective generator function exists that inspects, at minimum: `spec.md`, `plan.md`, `tasks.md`, `tasks/WP*.md`, `meta.json`, `status.events.jsonl`, review/rejection cycles, mission-review report when present, and policy-relevant DRG/doctrine/glossary context. It produces a schema-valid `RetrospectiveRecord` with `helped`, `not_helpful`, `gaps`, `proposals`, provenance, mission metadata, and evidence references. | Required |
| FR-007 | Empty-findings retrospectives MUST be explicitly represented (e.g. `findings_status: ran_no_findings`) and MUST NOT be confused with "missing retrospective" or "failed retrospective" anywhere in events, schema, summary, or CLI output. | Required |
| FR-008 | Under default policy, mission completion path: (a) attempts retrospective generation exactly once; (b) on success writes `retrospective.yaml` and emits a `RetrospectiveCaptured` event; (c) on failure emits a `RetrospectiveCaptureFailed` event with a structured failure category and remediation hint, and does NOT block completion. | Required |
| FR-009 | Under strict policy (`before_completion + block`), mission completion path enforces the gate before the completion event lands; the blocking message MUST cite the resolved policy source verbatim. Skips require an explicit `--skip-retrospective` permission and record actor/provenance in the event log. | Required |
| FR-010 | Automatic retrospective record generation MUST NOT mutate doctrine, DRG, or glossary. Application of proposals stays human-approved by default; the existing `agent retrospect synthesize` surface remains the preview/apply path. Narrow low-risk auto-application (e.g. `flag_not_helpful`) is permitted only when policy explicitly enables it. | Required |
| FR-011 | A new `spec-kitty retrospect create --mission <handle>` command authors a real retrospective for one completed mission. `<handle>` resolves via the canonical resolver (`mission_id` > `mid8` > `mission_slug`) with structured ambiguity errors. If a record already exists, the command does not silently overwrite; explicit `--overwrite` or `--update` flag is required, and the action is logged with actor/provenance. | Required |
| FR-012 | A new `spec-kitty retrospect backfill --since <ISO-date>` command (with optional `--mission <handle>` for single-target backfill) authors records for historical missions. JSON output enumerates `created`, `skipped` (with reason), `failed` (with category), and `next_actions`. Existing records are never silently overwritten. | Required |
| FR-013 | `spec-kitty retrospect summary` remains read-only aggregation. It MUST NOT author, mutate, or write any retrospective record. Its output MUST distinguish "ran, no findings" from "missing" from "failed". | Required |
| FR-014 | The silent "fabricate an empty completed record when artifacts look sufficient" fallback inside `agent retrospect synthesize` is removed OR is moved behind an explicit `--fabricate-empty` flag whose use is logged as actor-attributed provenance. The default path errors with an actionable message pointing at `retrospect create`. | Required |
| FR-015 | `SPEC_KITTY_RETROSPECTIVE` and `SPEC_KITTY_MODE` are demoted to test/developer overrides. At first use per session, the runtime emits a deprecation warning naming the durable equivalent (`retrospective.enabled` / `retrospective.timing` + `retrospective.failure_policy`). Durable policy takes precedence when both are present; deprecation warning still emits. | Required |
| FR-016 | Tests prefer injected policy over ambient env. The retrospective unit and integration test suites MUST construct `RetrospectivePolicy` objects directly rather than mutating `os.environ`, with at most a single dedicated test module exercising the deprecation-warning path. | Required |
| FR-017 | The pytest collection blocker tracked in [#1137](https://github.com/Priivacy-ai/spec-kitty/issues/1137) is resolved within this mission. Resolution may be (a) a fix to `spec_kitty_events` that restores `normalize_event_id` and `Event` top-level exports, (b) a local import-site fallback that uses a stable subpath import compatible with the released `spec_kitty_events` 5.1.0, or (c) a pinned compatible `spec_kitty_events` version in `pyproject.toml` with a follow-up tracking issue. The chosen approach is documented in the plan and mission-review report. | Required |
| FR-018 | Docs are updated to reflect the post-mission CLI semantics: `summary` is read-only aggregation; `create` authors a record; `backfill` creates historical records; `synthesize` previews/applies proposals from an existing record. Affected files at minimum: `README.md`, `docs/how-to/accept-and-merge.md`, `docs/how-to/merge-feature.md`, `docs/how-to/use-retrospective-learning.md`, `docs/explanation/retrospective-learning-loop.md`, `docs/reference/cli-commands.md`, `docs/reference/slash-commands.md`, `docs/tutorials/your-first-feature.md`. PR #1136 wording is corrected as part of this update (no separate short-term doc PR is required since this mission ships before that fix would otherwise lapse). | Required |
| FR-019 | Shipped skills are updated to reflect the same semantics. Affected at minimum: `src/doctrine/skills/spec-kitty-mission-review/SKILL.md`, `spec-kitty-implement-review/SKILL.md`, `spec-kitty-program-orchestrate/SKILL.md`, `spec-kitty-runtime-next/SKILL.md`. The post-merge guidance reads: mission review first, then create/capture retrospective, then summary or synthesize. | Required |
| FR-020 | The retrospective-facilitator agent profile (`src/doctrine/agent_profiles/shipped/retrospective-facilitator.agent.yaml`) is reviewed and, if needed, updated so its declared boundaries and permissions match the FR-001/FR-002 policy model and the FR-010 separation between authoring and applying. | Required |
| FR-021 | Existing retrospective events still reduce correctly. The reducer in `src/specify_cli/status/reducer.py` (or the equivalent retrospective-event reducer) is exercised against historical fixtures and produces the same materialized snapshots before and after this mission, with the exception of new event types added by this mission (which MUST be additive). | Required |
| FR-022 | Bulk-edit guardrails apply where the work performs cross-file string changes. The plan/tasks phase MUST decide whether the env-var deprecation messaging and doc-semantics updates qualify as `change_mode: bulk_edit`; if yes, an `occurrence_map.yaml` is produced and the bulk-edit gate must pass. The decision and rationale are recorded in the mission plan. | Required |

## Non-Functional Requirements

| ID | Description | Measurable Threshold | Status |
|---|---|---|---|
| NFR-001 | Targeted test runtime for retrospective surfaces | `uv run pytest tests/retrospective tests/integration/retrospective tests/next/test_retrospective_terminus_wiring.py -q` completes in under 60 seconds wall-clock on a stock developer machine. | Required |
| NFR-002 | No regression in the full test suite | `uv run pytest tests/ -q` exits 0 on `main` after the mission merges; the FR-017 fix unblocks collection. | Required |
| NFR-003 | Lint and type-check gates pass | `uv run ruff check src tests` exits 0. Mypy/pyright configuration follows existing repo conventions for the touched modules. | Required |
| NFR-004 | Coverage gate for new retrospective code paths | Combined line coverage of `src/specify_cli/retrospective/`, `src/specify_cli/next/runtime_bridge.py`, `src/specify_cli/next/_internal_runtime/retrospective_terminus.py`, and the new `retrospect create` / `backfill` CLI surface is ≥ 85% measured by `coverage` after the mission's tests run. | Required |
| NFR-005 | Default-policy completion latency | Default-policy mission completion (post-merge path) adds at most 2 seconds wall-clock on a representative mission (≤ 5 WPs, ≤ 50 events) for retrospective generation. Measured by a focused integration test. | Required |
| NFR-006 | Deprecation-warning noise budget | Setting either deprecated env var emits exactly one warning per process, not per command invocation. The warning text includes both the durable replacement key path AND a link to docs. | Required |
| NFR-007 | Wire shape additivity for retrospective events | This mission MUST NOT remove fields from existing retrospective event payloads. New fields (e.g. policy-source attribution) are additive and documented in the schema. | Required |
| NFR-008 | Docs render cleanly | `uv run markdownlint --config .markdownlint-cli2.jsonc <touched-doc-paths>` exits 0; the documented commands in updated how-tos succeed against a fresh project. | Required |

## Constraints

| ID | Description | Status |
|---|---|---|
| C-001 | Target branch is `main`; planning/base branch is `main`; completed changes merge back into `main` (resolved via `spec-kitty agent mission branch-context --json`). | Required |
| C-002 | Local CLI/runtime work only. No SaaS/teamspace-specific retrospective implementation in this mission. `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is NOT required in normal operation; if a command path inadvertently exercises hosted auth/tracker/SaaS behavior, the test runs with the flag set. | Required |
| C-003 | Do not delete existing retrospective schema, event types, or historical records. All changes are additive; deprecated paths are demoted, not removed, this release cycle. | Required |
| C-004 | Environment variables MUST NOT be the durable user-facing policy model. They remain as test/developer overrides for one release cycle and are documented as such. | Required |
| C-005 | Auto-application of structural doctrine/DRG/glossary changes is OFF by default. Policy may explicitly enable narrow low-risk classes; structural changes always require human approval. | Required |
| C-006 | Existing tests under `tests/` MUST continue to pass post-merge (gated by FR-017). | Required |
| C-007 | Mission identity uses ULID + `mid8`. Mission slug is `retrospective-default-policy-01KS049J`; `mission_number` is display-only and `null` pre-merge. All cross-mission references use `mission_id` or `mid8`, never `mission_number`. | Required |
| C-008 | The schema-version bootstrap quirk surfaced in [#1158](https://github.com/Priivacy-ai/spec-kitty/issues/1158) was worked around in-session by directly invoking `_update_schema_version()`; this mission MUST NOT depend on that workaround at production sites. If the proper fix lands in #1158 before this mission merges, depend on it; otherwise note the workaround in the mission-review report. | Required |

## Success Criteria

| ID | Statement | Measurement |
|---|---|---|
| SC-001 | A reader can run `spec-kitty merge` on a default-policy project and find a non-empty, schema-valid `retrospective.yaml` afterward, with a `RetrospectiveCaptured` event in the mission's event log. | Manual smoke test on a fresh project + the FR-008 integration test green. |
| SC-002 | Setting `retrospective.enabled: false` in `.kittify/config.yaml` produces a merge with no retrospective artifacts, no retrospective events, and no warning. | Manual smoke + FR-003 integration test green. |
| SC-003 | Setting `retrospective.timing: before_completion` and `retrospective.failure_policy: block` reproduces today's gate semantics with a clear blocking message citing the policy source. | FR-004 + FR-009 integration tests green. |
| SC-004 | `spec-kitty retrospect create --mission <handle>` on an arbitrary completed mission in this repo produces a real, schema-valid record. | Manual exercise on at least three already-completed missions in `kitty-specs/`, e.g. `068-post-merge-reliability-and-release-hardening`, `034-feature-status-state-model-remediation`, `047-namespace-aware-artifact-body-sync`. |
| SC-005 | `spec-kitty retrospect backfill --since 2026-01-01` on this repo's `kitty-specs/` produces a JSON report enumerating created/skipped/failed counts that match a hand-tabulated expected count. | One-off verification table in the mission-review report. |
| SC-006 | The deprecation warning fires exactly once per process when an env var is set, names the durable replacement key, and the durable policy still wins. | FR-015, FR-016, NFR-006 tests green. |
| SC-007 | A reader of the updated docs can find — within 30 seconds of opening `docs/how-to/use-retrospective-learning.md` — the canonical post-merge sequence (mission review → create/capture retrospective → summary/synthesize) and the difference between `create`, `summary`, and `synthesize`. | Mission-review doc walkthrough. |
| SC-008 | `uv run pytest tests/ -q` collects without error AND exits 0. | CI green; the FR-017 fix is the load-bearing piece. |

## Assumptions

- The retrospective schema (`src/specify_cli/retrospective/schema.py`) is broadly fit for purpose and does not need a structural rewrite this release. Field additions (e.g. policy-source attribution) are additive only.
- The existing retrospective event types in the canonical event log are not renamed by this mission. New event types (e.g. `RetrospectiveCaptured`, `RetrospectiveCaptureFailed`) are added if and only if no existing event type already serves the same purpose; otherwise the existing one is reused.
- The shipped `retrospective-facilitator.agent.yaml` profile boundaries are close enough to the FR-010 model that they need at most a configuration-level refinement, not a profile rewrite.
- The default policy can be implemented and tested without depending on charter being present; missing charter is a no-op for policy resolution, with config-file or built-in defaults filling the resolved policy.
- The schema-version bootstrap fix (#1158) is independent of this mission's logic and can land separately.

## Dependencies & Risks

**Dependencies**:

- [#1137](https://github.com/Priivacy-ai/spec-kitty/issues/1137) (`spec_kitty_events` 5.1.0 top-level exports) — addressed in scope per FR-017.
- The canonical event-log infrastructure (`src/specify_cli/status/`) and the canonical mission-identity model (mission 083+) — both already merged.
- The `spec-kitty merge` and mission-completion paths — load-bearing for FR-008 / FR-009.

**Risks**:

- **R-1 Scope creep into proposal application**: The mission is bounded to *generation* as the default-on behavior. Application semantics could expand. Mitigation: FR-010 hard-bounds the default to `require_human` for structural changes; auto-apply allowlist is explicitly enumerated, not implicit.
- **R-2 Deprecation warning fatigue**: If the warning fires on every command, users will configure environments to suppress it and we will lose the deprecation signal. Mitigation: NFR-006 enforces a per-process budget.
- **R-3 Failure policy ambiguity at completion time**: If the generator throws a transient error under default policy, the mission completes with a warning event. If a strict project then surveys completions and finds a warning, they may not know whether the retrospective is missing or just deferred. Mitigation: FR-007 + summary distinguishes "ran, no findings" / "failed" / "missing" / "deferred" in both events and read-only outputs.
- **R-4 Generator quality**: An automatic generator that produces low-signal records is worse than no record (training the user to ignore retrospectives). Mitigation: SC-004 sanity-checks the generator against three real completed missions in `kitty-specs/` and the mission-review report validates output quality.
- **R-5 Docs/skills drift**: The cross-cutting doc and skill updates risk getting partial coverage. Mitigation: FR-018 + FR-019 enumerate the exact files; FR-022 forces bulk-edit classification at plan-time if the work pattern qualifies.
- **R-6 PR #1136 wording remains stale if this mission slips the release window**: The post-merge guidance in `docs/how-to/accept-and-merge.md` currently overstates `summary`/`synthesize`. Mitigation: if this mission cannot ship in 3.2.0, a short-term doc-only correction lands separately; otherwise FR-018 catches it as part of this mission.

## Non-Goals

- SaaS/teamspace-specific retrospective implementation.
- Auto-applying structural doctrine/DRG/glossary changes by default.
- Deleting existing retrospective schema or event history.
- Promoting environment variables as the durable user-facing policy model.
- Restructuring `RetrospectiveRecord` schema fields beyond additive policy-source attribution.

## Suggested Work Package Shape

Decomposition lives at `/spec-kitty.tasks` time. The brief's suggestion (to validate or revise at planning):

1. **WP-Policy** — `RetrospectivePolicy` model + resolver + tests (covers FR-001, FR-002, FR-003, FR-004, NFR-002, NFR-003, NFR-007).
2. **WP-Generator** — Real retrospective generator + schema additions + tests (FR-005, FR-006, FR-007, FR-010, NFR-004, NFR-007).
3. **WP-Runtime** — Wire generator into runtime; default post-completion best-effort + strict pre-completion gate + policy-source attribution on events (FR-005, FR-008, FR-009, FR-021, NFR-005).
4. **WP-CLI** — `retrospect create` and `retrospect backfill` commands; tighten `synthesize` fallback (FR-011, FR-012, FR-013, FR-014).
5. **WP-Env-Deprecate** — Deprecation warnings + test rewrites to prefer injected policy (FR-015, FR-016, NFR-006).
6. **WP-Docs-Skills** — Docs and shipped-skills updates; PR #1136 wording fix; retrospective-facilitator profile review (FR-018, FR-019, FR-020, FR-022, NFR-008).
7. **WP-Events-Unblock** — Resolve [#1137](https://github.com/Priivacy-ai/spec-kitty/issues/1137) pytest collection blocker (FR-017, NFR-002).

The dependency order is roughly Policy → Generator → Runtime → CLI in parallel with Env-Deprecate, with Docs-Skills landing after the surfaces stabilize. WP-Events-Unblock should land first (or in parallel) so the test suite is honest end-to-end.
