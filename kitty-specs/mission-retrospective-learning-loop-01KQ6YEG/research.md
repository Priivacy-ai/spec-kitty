# Phase 0 Research: Mission Retrospective Learning Loop

**Mission**: `01KQ6YEGT4YBZ3GZF7X680KQ3V` (mid8: `01KQ6YEG`)
**Plan**: [./plan.md](./plan.md)
**Date**: 2026-04-27

This document closes every research task identified in `plan.md` Phase 0. Each entry follows the charter-required record shape: **Decision · Rationale · Alternatives considered**.

---

## R-001 — Mode-detection precedence

**Decision**: Resolve mode in strict order: charter override → explicit flag → environment variable → parent process. The first signal that produces a definite value (`autonomous` or `human_in_command`) wins. The signal that produced the resolved mode is recorded as a `source_signal` field in both the retrospective record and the mission events.

Concretely:

1. **Charter override.** Read `.kittify/charter/charter.md` policy declarations via the existing charter context loader. If the charter declares `mode: autonomous` or `mode: human_in_command` (with optional clauses naming when an operator override is permitted), that value wins.
2. **Explicit flag.** If no decisive charter override, read `--mode autonomous|hic` passed to `spec-kitty next` (or any future entry point that triggers retrospective lifecycle).
3. **Environment variable.** If no flag, read `SPEC_KITTY_MODE`. Allowed values: `autonomous`, `human_in_command`. Anything else is treated as "no signal."
4. **Parent process.** If no env var, inspect the parent process via `psutil`. Heuristic: if the parent is interactive (a TTY-attached shell, or known IDE PIDs), resolve to `human_in_command`; if the parent is a CI runner / cron / agent harness, resolve to `autonomous`. The list of recognized non-interactive parents is stored as a small constant in `retrospective/mode.py` and is conservative (when in doubt → HiC).

**Audit trail**: every retrospective record carries `mode: {value, source_signal: {kind, evidence}}`. The mission event log carries the same on `retrospective.requested` and `retrospective.started`.

**Charter sovereignty**: an explicit operator flag that asks to skip retrospective in autonomous mode is honored only if the charter override clause permits it. Otherwise the flag is rejected at the gate, the mission cannot complete, and a structured blocker is surfaced naming the charter clause and the rejected flag value.

**Rationale**: This precedence (Q1-B) treats project policy as sovereign and ambient signals as fallback. It also makes the test surface easy: each layer is independently fakeable.

**Alternatives considered**:
- *Flag > charter*: rejected because it lets a runtime invocation override codified policy.
- *Env > flag*: rejected because explicit operator intent should outrank ambient.
- *Auto-detect-only (parent process first)*: rejected — too easy to misclassify CI as interactive or vice versa; no provenance for the resolution.

---

## R-002 — Canonical retrospective path under post-083 identity

**Decision**: `.kittify/missions/<mission_id>/retrospective.yaml` where `<mission_id>` is the canonical ULID from `meta.json`, **never** the display-only `mission_number`. The directory is created lazily by the writer; if `meta.json` is missing the writer raises a structured `MissionIdentityMissing` error rather than guessing.

**Companion files** in the same directory (created on demand):
- `retrospective.yaml` — the durable record (this tranche).
- *(future)* may host additional learning artifacts; layout is reserved.

**Rationale**: keys to canonical immutable identity (per ADR `2026-04-09-1`); survives mission_slug churn; placed under `.kittify/` so it lives at the project-governance layer (alongside charter and config) rather than buried in feature work. Spec FR-009, C-014, Resolved Clarification 1.

**Alternatives considered**:
- `kitty-specs/<slug>/retrospective.yaml`: rejected because the feature directory is mission-domain content; the retrospective is governance metadata that should outlive the feature directory's lifecycle (e.g., a future `/spec-kitty.tasks` regenerator should never wipe a retrospective).
- `.kittify/retrospectives/<mission_id>.yaml` (flat): rejected because it forecloses on companion files; the directory shape gives room to add per-mission learning artifacts later without another migration.

---

## R-003 — Atomic-write strategy for `retrospective.yaml`

**Decision**: write to a sibling tempfile in the same directory, then `os.replace()` onto the canonical path. Never write in place. This satisfies NFR-002 (atomic write) on POSIX filesystems; on macOS APFS and Linux ext4/xfs, `os.replace()` is atomic.

Implementation outline (in `retrospective/writer.py`, schema-validated upstream):
1. Validate the in-memory record via Pydantic.
2. Serialize through `ruamel.yaml` round-trip-safe dumper.
3. Open `<canonical>.tmp.<pid>.<random>` in the same directory; write; `fsync()`; close.
4. `os.replace(tmp, canonical)`.
5. Best-effort `fsync()` on the directory fd.

The reader in `retrospective/reader.py` validates schema on load and **refuses** to treat any file that fails validation as `completed`. A file that is missing entirely is treated as "no retrospective." A file that exists but fails schema is surfaced as `retrospective.failed` with the validation error attached.

**Rationale**: matches the project's existing pattern for `status.events.jsonl` and `meta.json`. Avoids the half-written-file failure mode the spec edge case calls out.

**Alternatives considered**:
- In-place write: rejected (NFR-002 violation).
- Two-phase journal (separate journal + commit): rejected as overkill for a YAML record bound by a Pydantic schema; the gate already refuses to treat invalid files as completed, so we don't need a journal to detect partial state.
- Per-write content hash sidecar: deferred; `os.replace()` plus schema-on-read is sufficient for the spec's failure modes.

---

## R-004 — Append-only event log integration

**Decision**: retrospective events are written into the existing `kitty-specs/<slug>/status.events.jsonl` event log via `specify_cli.status.emit.emit_status_transition(...)` for events that correspond to mission status transitions, and via a new sibling `specify_cli.status.emit.emit_event(...)` (or equivalent helper) for retrospective-only events that do not correspond to a `lane` change.

The reducer (`specify_cli.status.reducer.reduce`) is **not** changed in shape; retrospective events surface in the snapshot under a new `retrospective` field whose value is derived from the most recent retrospective event for the mission. The new field is additive — existing snapshot consumers see no change.

Retries / re-runs are represented as additional events on the same mission with the same `mission_id`. Two `retrospective.completed` events on the same mission are valid; the latest (by `at` timestamp, with `event_id` ULID as tiebreak) wins for the gate decision. Prior completed events are preserved.

**Rationale**: matches FR-018 (events join the canonical log) and NFR-005 (append-only). Reuses status-event primitives so we don't fork the durability story.

**Alternatives considered**:
- A separate `retrospective.events.jsonl` per mission: rejected because cross-mission summary would have to read 1+200 files; existing log already suffices.
- Event sourcing as the authority for the retrospective record itself: rejected — the YAML record is the editable artifact for human review; events are the lifecycle signal.

---

## R-005 — Action-surface inequality (architecture §4.5.1)

**Decision**: state the inequality concretely and locally so calibration can verify without re-deriving:

> For every `(profile, action)` pair invoked by a step `s`, let `ResolvedScope(s)` be the set of DRG artifact URNs surfaced to the step at runtime, and let `RequiredScope(s)` be the set of DRG artifact URNs the step needs to make its decision (defined per step by inspection during calibration). Then:
>
> 1. `ResolvedScope(s) ⊇ RequiredScope(s)` — surfaced context is a superset of required context (no missing-context regressions).
> 2. `ResolvedScope(s)` is **not** a strict superset of `RequiredScope(s) ∪ {known-irrelevant URNs}` — surfaced context does not include URNs identified as irrelevant or too-broad for this step.

Calibration tests assert these two conditions per step. Failure produces a calibration report row identifying the violating URNs and the recommended DRG edge change to fix it.

**Rationale**: the spec deferred precise definition to plan; this is the minimal predicate that captures both "missing context" (1) and "over-broad context" (2) without requiring an external architecture-document reading. Spec FR-032, CHK037.

**Alternatives considered**:
- Equality: rejected — disallows benign supersets; would fail real workflows that surface a stable scope across actions.
- Subset only: rejected — disallows real over-broad-context findings, which is the whole point of calibration.
- "It is whatever the architecture document says": rejected — the spec checklist (CHK037) explicitly flags this as ambiguity to remove.

---

## R-006 — Conflict predicates for paired proposal kinds

**Decision**: define conflict pairwise and conservatively. The synthesizer's `conflict.py` enumerates conflicting pairs:

| Proposal A | Proposal B | Conflicts when |
|---|---|---|
| `add_edge(E)` | `remove_edge(E)` | targeting the same `(from, to, kind)` triple |
| `add_edge(E)` | `rewire_edge(E_old → E)` | the destination of B equals A |
| `remove_edge(E)` | `rewire_edge(E → E_new)` | the source of B equals A |
| `add_glossary_term(T)` | `add_glossary_term(T)` | same term key, different definition payloads |
| `update_glossary_term(T)` | `update_glossary_term(T)` | same term key, payloads do not converge |
| `flag_not_helpful(X)` | any other proposal targeting X | non-conflicting; `flag_not_helpful` is informational |
| `synthesize_directive(D)` | `synthesize_directive(D)` | same directive id with diverging body |
| `synthesize_tactic(T)` | `synthesize_tactic(T)` | same tactic id with diverging body |
| `synthesize_procedure(P)` | `synthesize_procedure(P)` | same procedure id with diverging body |

Any conflict in a single `synthesize` invocation causes the entire invocation to fail closed (FR-023): nothing in the conflicting set is applied, the operator sees a structured error listing the conflict pairs, and the staged proposals stay in their pre-apply state.

Per-proposal-kind payload schemas (carried into the schema contract) constrain "diverging body" to a comparable form (e.g., directive bodies are compared by normalized text hash plus an explicit `id` collision check).

**Rationale**: covers the realistic conflict surface without a combinatorial explosion. Conservatism (treat mismatched definitions as conflict) preserves auditability — operators decide which version wins.

**Alternatives considered**:
- "Last-writer-wins": rejected (silent overwrite violates FR-023, C-012).
- "Always require all proposals in one batch to be from the same retrospective": rejected — operators may legitimately approve proposals from multiple retrospectives in one batch.

---

## R-007 — Upstream `spec_kitty_events` boundary test pattern

**Decision**: introduce a boundary test in `tests/architectural/test_shared_package_boundary.py` that, when the upstream `spec_kitty_events` release ships the eight retrospective events, asserts no Pydantic models named `Retrospective*Event` are defined under `specify_cli.*` outside `specify_cli.retrospective.events` (and its specific re-export shim). Until upstream ships, the test is `pytest.skip(...)` with a reason `"pending spec_kitty_events upstream release: <upstream-issue-link>"`.

The cutover (when upstream ships) is mechanical:

1. Verify `spec_kitty_events.retrospective.*` matches the local module's names and payloads (a contract test in this tranche checks pairwise equivalence today against a fixture of the local shapes).
2. Bump `spec_kitty_events>=` in `pyproject.toml`.
3. Replace `from specify_cli.retrospective import events as ev` with `from spec_kitty_events import retrospective as ev` everywhere.
4. Delete `specify_cli/retrospective/events.py`.
5. The skipped boundary test now runs and passes.

**Rationale**: keeps this tranche shippable independent of upstream; documents the cutover so it is a one-PR change.

**Alternatives considered**:
- Block this tranche on upstream release: rejected — too much coupling for a tranche-shippable plan.
- Inline event names as plain strings (no Pydantic models locally): rejected — loses validation; the local module is already a thin Pydantic shim.

---

## R-008 — Cross-mission summary reduction strategy

**Decision**: streaming reducer. The summary command:

1. Discovers retrospective records by globbing `.kittify/missions/*/retrospective.yaml` (one stat-call per project path).
2. For each, attempts `reader.load(path)`. On schema failure, records a `MalformedSummaryEntry(mission_id, reason)` and continues; the summary report includes a `malformed: [...]` section. Records that fail to even parse YAML are also captured. (NFR-004.)
3. Reads proposal-lifecycle events from each mission's `kitty-specs/<slug>/status.events.jsonl` (lookup by `mission_id` → `mission_slug` from `meta.json`). On missing log or unreachable slug, marks the entry as "no retrospective events" without crashing.
4. Reduces into a `SummarySnapshot` Pydantic model carrying the FR-026 minimum pattern set: not-helpful counts, missing-term counts, missing-edge counts, over/under-inclusion counts, proposal acceptance/rejection rates, skip count + reasons, no-retrospective count, malformed-entry count.
5. Renders both human-readable Rich output and a JSON artifact whose schema is the same `SummarySnapshot` model (FR-025, CHK034 informational equivalence).

Performance: linear in mission count. Target: ≤200 missions, ≤200 findings each, < 5 s on a developer laptop (NFR-003). The reducer is single-process; no concurrency required at this corpus size.

The "missions with no retrospective" count distinguishes:
- `legacy` — mission existed before this tranche shipped (heuristic: created_at before tranche release tag).
- `in_flight` — mission is not at terminus yet.
- `terminus_no_retrospective` — mission reached terminus but neither completed nor skipped a retrospective; this is an anomaly worth surfacing.

**Rationale**: simplest reducer that meets the spec's tolerance and performance bar. No DB, no caching layer. Streaming keeps memory bounded.

**Alternatives considered**:
- Pre-computed per-mission summary cache: rejected — premature optimization for the 200-mission scale.
- Streaming with parallel I/O: deferred — single-thread file reads are well within 5 s for 200 small YAML files.
- Surface only `terminus_no_retrospective` (skip the tri-state): rejected — operators can't tell legacy from in-flight, and the cross-mission view is supposed to surface that.

---

## Closure

All eight research tasks closed. Zero `[NEEDS CLARIFICATION]` markers remain. Phase 1 design proceeds.
