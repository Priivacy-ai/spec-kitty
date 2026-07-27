# Research: Retrospective Learning Default-On Policy

**Mission**: `retrospective-default-policy-01KS049J` (mission_id `01KS049J4V9CSWBKJHTY2FB69H`)
**Date**: 2026-05-19
**Phase**: 0 — Outline & Research

This document resolves unknowns from the Technical Context and captures the decisions and rationale that feed Phase 1 (data model, contracts, quickstart).

## R-1 — Generator architecture

**Decision**: Pure-Python module. Generator lives at `src/specify_cli/retrospective/generator.py` as a deterministic function `generate_retrospective(mission_handle, policy, repo_root) -> RetrospectiveRecord`. The runtime calls it directly. Decision Moment: `01KS051316C8Z0SDEKZ2B088CS`.

**Rationale**:

- The "default-on" goal requires every completed mission to produce a record. Sub-second latency is a hard requirement (NFR-005 ≤ 2s wall-clock total including I/O). Profile invocation routinely takes 5–30s due to agent dispatch.
- Determinism matters for FR-021 (existing retrospective events still reduce correctly). A pure Python function is byte-deterministic given the same inputs; an agent-invoked generator is not.
- Testability: unit tests construct mission artifacts on disk and call the generator directly; no agent harness mocks needed.
- The `retrospective-facilitator` agent profile stays useful as a *human-mediated* tool for richer mission post-mortems via the existing profile-invocation pipeline (`spec-kitty agent action retrospect` style invocations). It is simply not the runtime default.

**Alternatives considered**:

- *Profile invocation* (`retrospective-facilitator.agent.yaml` via profile pipeline) — rejected as the runtime default for the reasons above. Remains available as an explicit operator action.
- *Hybrid (policy-selectable)* — deferred. Could land as a follow-up if governed projects ask for it. The policy schema we land in this mission is forward-compatible: adding `retrospective.generator: profile` later does not require a schema break.

## R-2 — Policy file location and precedence

**Decision**: `.kittify/config.yaml` top-level `retrospective:` block is the canonical home. Charter frontmatter under `retrospective:` is the governed-project escalation point. Default precedence: **charter wins** when present. Charter may explicitly delegate to config with `retrospective.precedence: config`.

**Rationale**:

- `.kittify/config.yaml` is the established home for durable project settings (`vcs`, `agents`, `merge`, `project`) — adding `retrospective:` here matches existing convention.
- Charter is the governance surface; governed projects expect charter to be authoritative. The `retrospective.precedence: config` escape hatch covers the (rare) case where the charter wants config-level flexibility.
- The resolver returns a `(policy, source_map)` tuple so every resolved field carries a `source: <path>` pointer for event-payload attribution (NFR-007).

**Schema sketch** (validated in Phase 1):

```yaml
# .kittify/config.yaml
retrospective:
  enabled: true                    # default true
  timing: post_completion          # post_completion | before_completion
  failure_policy: warn             # warn | block
  write_record: true               # default true
  generate_proposals: true
  apply_proposals: require_human   # require_human | low_risk_auto
  permissions:
    write_record: true
    inspect_mission_artifacts: true
    propose_glossary_changes: true
    propose_drg_changes: true
    propose_doctrine_changes: true
    apply_low_risk_changes: false
    apply_structural_changes: false
  # forward-compatible:
  # generator: python              # python | profile (future)
  # precedence: config             # only meaningful in charter frontmatter
```

**Alternatives considered**:

- *Dedicated `.kittify/retrospective.yaml`* — rejected; adds a new top-level file with no precedent.
- *Config wins by default* — rejected; governed projects need charter to be authoritative without an explicit charter declaration.

## R-3 — Existing event-type coverage

**Decision**: Confirm at implementation time whether `spec_kitty_events` already exposes a retrospective-capture event. If yes, reuse with additive policy-source attribution. If no, add `RetrospectiveCaptured` and `RetrospectiveCaptureFailed` to the local emit path under the existing wire-shape additivity rule (NFR-007).

**Rationale**:

- FR-024 freezes the public surface of `spec_kitty_events`. Adding new event types upstream is out of scope. If our local emit path needs new types, they go through the `specify_cli.status` reducer the same way other `WPStatusChanged` / mission-lifecycle events already do (event_log_authority capability).
- The existing retrospective tranche (#506, #507, #508) defined a `RetrospectiveCaptured`-ish event semantically. Confirm exact name during WP-Runtime implementation.

**Alternatives considered**:

- *Always add new event types* — rejected; risks duplicate events with subtly different shapes.
- *Defer to a follow-up* — rejected; the new event payloads are load-bearing for FR-008/FR-009 (mission completion must emit a structured outcome).

## R-4 — Retrospective generator inputs

**Decision**: The generator reads, in this order:

1. `kitty-specs/<mission_slug>/meta.json` — mission identity, target branch, mission_type, friendly_name, purpose summaries.
2. `kitty-specs/<mission_slug>/spec.md` — FR/NFR/C tables, success criteria, scenarios.
3. `kitty-specs/<mission_slug>/plan.md` + `research.md` + `data-model.md` + `contracts/` + `quickstart.md` — design context.
4. `kitty-specs/<mission_slug>/tasks.md` + `tasks/WP*.md` — task decomposition and WP boundaries.
5. `kitty-specs/<mission_slug>/status.events.jsonl` — canonical lifecycle history (claims, reviews, rejections, approvals, completion).
6. Review/rejection cycles — derived from #5 by filtering `WPStatusChanged` events in the backward-rewind family (`in_review → planned`, `approved → planned`, etc., per `backward-transition-cli-emit-01KRV8GC` in this repo).
7. `kitty-specs/<mission_slug>/mission-review-report.md` if present — produced by `/spec-kitty.merge`'s mission-review step.
8. Charter context for this mission (if charter exists) — loaded via `spec-kitty charter context --action <action> --json`.

**Rationale**:

- This matches the artifact set the brief specifies. The artifacts already exist for every mission past `mission_system_architecture` (kitty-specs/001-...) and are stable formats.
- The generator MUST tolerate missing optional artifacts (e.g. `mission-review-report.md` if not produced) without failing — under default `failure_policy: warn` it would otherwise generate spurious warnings.

**Output schema**: See [data-model.md](./data-model.md) for the `RetrospectiveRecord` shape.

## R-5 — Deprecation-warning UX

**Decision**: One warning per process via `warnings.warn(..., DeprecationWarning, stacklevel=2)` AND a Rich-styled stderr notice on the first command invocation that observes the env var. Suppressed by setting the canonical replacement key in `.kittify/config.yaml`. Hidden when `SPEC_KITTY_NO_DEPRECATION_WARNINGS=1` is set (a separate test-and-dev escape hatch).

**Rationale**:

- NFR-006 caps the warning at one per process. Per-command spam trains users to suppress, defeating the deprecation signal.
- Two channels (`warnings` module + Rich stderr) cover both library consumers (pytest's `-W` capture) and humans running the CLI.
- The dedicated suppression env var lets CI runs quiet the noise without re-enabling the deprecated behavior.

**Alternatives considered**:

- *Per-command warning* — rejected (NFR-006 violation).
- *Hard deprecation immediately* — rejected; the brief explicitly grants one release cycle of soft deprecation. We follow that.

## R-6 — Overwrite semantics for `retrospect create`

**Decision**: Default behavior is **error if record exists**. Operators may pass `--overwrite` to replace or `--update` to merge. Both actions are recorded in the per-mission `status.events.jsonl` with actor identity and a structured reason.

**Rationale**:

- The brief explicitly forbids silent overwrite. Failing closed by default is the safest user experience: an operator who runs `retrospect create` on a mission that already has a record gets a clear actionable error instead of a destructive surprise.
- `--update` (merge) is useful for incremental capture (append observations after a real-world incident reveals more), but merge semantics are non-trivial. Phase 1 (`data-model.md`) defines them: deduplicate by `(category, evidence_ref)`; new `proposals` are appended; provenance entries accumulate.

**Alternatives considered**:

- *Default overwrite* — rejected; violates the brief.
- *Reject `--update`, only `--overwrite`* — considered, but `--update` is the right operator ergonomics for adding to a record without losing earlier observations.

## R-7 — `agent retrospect synthesize` fabrication fallback (FR-014)

**Decision**: Remove the silent path. When `synthesize` is invoked on a mission without a record, error with: `"No retrospective record found for <handle>. Author one with: spec-kitty retrospect create --mission <handle>"`. Behind an explicit `--fabricate-empty` flag (FR-014), the legacy behavior is preserved but logged as actor-attributed provenance in the mission's event log.

**Rationale**:

- The fabrication path is the single largest source of "empty completed records" in the wild and trains users to ignore retrospective files. Removing it from the default path is the highest-leverage quality improvement in this mission.
- The `--fabricate-empty` flag covers any tooling that depended on the legacy behavior (likely none, but cheap to keep for compatibility this cycle). Tests cover both default-error and explicit-fabricate paths.

**Alternatives considered**:

- *Remove the flag entirely* — rejected this release cycle. We have no telemetry on who depends on the legacy path; keeping `--fabricate-empty` is a one-line behavior preservation.
- *Make `synthesize` author records under a sub-mode* — rejected; conflicts with the brief's separation between `create` (authors) and `synthesize` (previews/applies proposals from an existing record).

## R-8 — Backfill scope

**Decision**: `spec-kitty retrospect backfill --since <ISO-date> [--mission <handle>] [--dry-run]` iterates over completed missions in `kitty-specs/` whose `meta.json` completion timestamp is on or after `--since`. For each candidate, it calls the same generator the runtime uses. Existing records skip with reason `already_exists`. Missing artifacts skip with reason `incomplete_artifacts` and a list of which artifacts were missing.

**Rationale**:

- Reusing the runtime generator is the correctness lever — backfilled records have the same shape as fresh records.
- `--dry-run` is essential for a destructive-feeling batch op even though it's non-destructive (no overwrites). Operators want to preview what will be written.
- Skip reasons must be structured (an enum) so dashboards/scripts can filter and re-process.

**Alternatives considered**:

- *Backfill from spec/plan/tasks only (no event log)* — rejected; produces poor-quality records lacking lifecycle context.
- *Backfill emits new lifecycle events* — rejected; backfilled records are descriptive of historical state, not state changes. The event log gets a single `RetrospectiveCaptured` event with `provenance.kind = backfill` to attribute the authoring action.

## R-9 — Policy-source attribution on events

**Decision**: Every retrospective event payload carries an additive `policy_source` field listing the resolved file path(s) and key path(s) for each policy field that influenced the decision. Example:

```json
{
  "policy_source": {
    "enabled": ".kittify/config.yaml#retrospective.enabled",
    "timing": ".kittify/charter/charter.md#retrospective.timing",
    "failure_policy": "<default>"
  }
}
```

**Rationale**:

- NFR-007 mandates additivity. `policy_source` is purely additive — older consumers ignoring it work identically.
- Operators reading event logs after a strict-gate block need to know *why* the gate fired and *where* to change policy. Pointing at the exact file + key path eliminates a guessing game.
- `<default>` is the explicit sentinel for "no override — built-in default used."

**Alternatives considered**:

- *Single string source* — rejected; not granular enough.
- *No source attribution* — rejected; operators have repeatedly asked for this and it directly satisfies FR-001's "source reporting" clause.

## R-10 — Test coverage strategy

**Decision**: Three test tiers:

1. **Unit tests in `tests/retrospective/`** — `RetrospectivePolicy` resolver, `generate_retrospective`, writer (overwrite/update/error), summary read paths, schema validation. Pure-Python, no subprocesses, no agent harness mocks.
2. **Integration tests in `tests/integration/retrospective/`** — default flow, strict flow, warn-on-failure flow, opt-out flow, `retrospect create` end-to-end, `retrospect backfill` end-to-end. Each test scaffolds a fake mission directory in `tmp_path` and exercises the real runtime entry points.
3. **Wiring test in `tests/next/test_retrospective_terminus_wiring.py`** — asserts `runtime_bridge.py` no longer passes `facilitator_callback=None` for enabled policy paths.

**Rationale**:

- Three tiers mirror the existing project convention (unit → integration → wiring) and keep each tier focused on one concern.
- Integration tests assert end-to-end behavior; wiring test asserts the structural fix in `runtime_bridge.py`. Both are needed because the structural test would pass even if the wiring was syntactically present but semantically inert.

**Alternatives considered**:

- *End-to-end shell tests* — rejected; slow and brittle. The integration tier already covers the CLI surface via in-process Typer test client.
- *No wiring test* — rejected; the `facilitator_callback=None` regression is exactly what this mission fixes and exactly what a future regression test should catch.

## R-11 — Bulk-edit classification

**Decision**: Mark the mission `change_mode: bulk_edit` at `/spec-kitty.tasks` time. Two distinct bulk-edit shapes are present:

1. **Env-var deprecation** — `SPEC_KITTY_RETROSPECTIVE` and `SPEC_KITTY_MODE` appear in env reads, tests, docs, and skill text. The change is "swap primary-meaning labels and add deprecation warning."
2. **Doc semantics correction** — `summary` / `synthesize` framing across docs and shipped skills (carried by PR #1136) is changing to four distinct categories.

`occurrence_map.yaml` enumerates each occurrence under the 8 standard categories with an explicit action. WP-Env-Deprecate and WP-Docs-Skills are the carriers.

**Rationale**:

- Both shapes match the bulk-edit classification rules (same identifier or phrase changing meaning across many files). Better to over-classify than miss DIRECTIVE_035's silent cross-file breakage.

## R-12 — Performance budget validation

**Decision**: NFR-005's 2-second budget is validated by a single integration test that scaffolds a representative mission (4 WPs, 30-ish events) and asserts `generate_retrospective` wall-clock under 2.0s on a stock CI runner. The test uses `time.perf_counter()` and a generous CI margin (the assertion is < 2.0s; locally the function should be well under 500ms).

**Rationale**:

- Concrete measurable threshold lets us catch regressions without speculative profiling. The 2s budget is loose enough not to be flaky in CI but tight enough that any algorithmic regression (e.g. quadratic event scan) would trigger it.

## Open Questions

None at planning time. All planning questions either resolved here or defaulted with documented rationale. Phase 1 (data-model, contracts, quickstart) implements these decisions.

## Inputs to Phase 1

- R-2 → `data-model.md` policy schema and source-map structure.
- R-3, R-9 → `contracts/retrospective-events.contract.md` event payloads.
- R-4 → `data-model.md` `RetrospectiveRecord` ingestion inputs.
- R-6, R-8 → `contracts/retrospect-cli.contract.md` CLI contracts.
- R-7 → `contracts/retrospect-cli.contract.md` `synthesize` error and `--fabricate-empty` flag contract.
- R-10 → `quickstart.md` operator quickstart + test-runner commands.
