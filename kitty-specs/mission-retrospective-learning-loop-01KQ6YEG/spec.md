# Mission Retrospective Learning Loop

**Mission ID**: `01KQ6YEGT4YBZ3GZF7X680KQ3V` (mid8: `01KQ6YEG`)
**Mission slug**: `mission-retrospective-learning-loop-01KQ6YEG`
**Mission type**: software-dev
**Target branch**: `main`
**Branch contract**: planning base `main` → final merge `main`
**Created**: 2026-04-27
**Source**: `start-here.md` (Phase 6 FR4 tranche under epic [#468](https://github.com/Priivacy-ai/spec-kitty/issues/468))
**Issues covered**: [#507](https://github.com/Priivacy-ai/spec-kitty/issues/507), [#506](https://github.com/Priivacy-ai/spec-kitty/issues/506), [#508](https://github.com/Priivacy-ai/spec-kitty/issues/508), [#509](https://github.com/Priivacy-ai/spec-kitty/issues/509), [#511](https://github.com/Priivacy-ai/spec-kitty/issues/511), [#510](https://github.com/Priivacy-ai/spec-kitty/issues/510)

---

## Overview

Spec Kitty already governs how missions run. This tranche makes Spec Kitty *learn from* every mission it runs.

When any mission reaches its end, Spec Kitty captures a structured retrospective: what helped, what did not help, what governance/context gaps appeared, and what concrete doctrine, dependency-and-relationship-graph (DRG), or glossary changes are proposed. In autonomous mode, that retrospective is mandatory — the mission cannot be marked done without it. In human-in-command (HiC) mode, the retrospective is offered to the operator and may be skipped explicitly with an audit trail. Findings become structured data, can be summarized across the whole mission history of a project, and accepted proposals feed a synthesizer that updates project-local doctrine, DRG edges, and glossary terms with provenance back to the source mission.

The value proposition is not "another report." It is: every governed run becomes evidence about which governance helped, which harmed, and which was missing — and the system turns those lessons into structured findings that improve future mission context.

---

## User Scenarios

### Primary actors

- **Operator** — a human running missions in human-in-command (HiC) mode against a project.
- **Autonomous agent** — a coding agent running missions without an attentive human (background runner, scheduled job, or hands-off CI flow).
- **Reviewer / governance owner** — the human responsible for approving doctrine and glossary changes proposed by retrospectives.
- **Spec Kitty itself** — the runtime that gates lifecycle transitions and emits retrospective events.

### Acceptance scenarios

1. **Autonomous run cannot silently skip learning.** An autonomous mission finishes its last domain step. The runtime invokes the retrospective. The retrospective produces structured findings. Only then is the mission marked done. If the retrospective is unavailable or fails, the mission is blocked from completion with a structured reason that names the failure.

2. **Autonomous run cannot silently skip learning even if the agent tries.** An autonomous mission finishes and the agent attempts to move directly to a "done" state without invoking the retrospective. The runtime refuses the transition and emits a `retrospective.required` blocker that names the missing evidence.

3. **HiC operator opts in.** A HiC operator finishes a mission. The runtime offers the retrospective. The operator runs it. Findings are written, the mission is marked done, and the synthesizer is available to apply accepted proposals.

4. **HiC operator opts out with an audit trail.** A HiC operator finishes a mission and chooses to skip the retrospective, optionally providing a reason ("low-value docs fix"). The runtime writes a `retrospective.skipped` record with the reason and the actor identity. The mission is marked done. The skip is visible in cross-mission summaries.

5. **HiC mode cannot silently auto-run.** In HiC mode, no code path runs the retrospective without the operator explicitly choosing to. An attempted auto-run by the agent is blocked and surfaced as a governance violation.

6. **Charter sovereignty.** A project's charter declares "always run retrospective, no skip allowed." A HiC operator passes a flag asking to skip. The runtime honors the charter, refuses the skip, and explains why. (Charter override > explicit flag > environment > parent process.)

7. **Findings are structured.** A completed retrospective writes a `retrospective.yaml` whose schema is validatable. The file captures helped / not-helpful / gaps / proposals, each with provenance pointing at evidence event ids. A reader can answer "which doctrine artifact was flagged not-helpful in mission X" by parsing the file, not by grepping prose.

8. **Synthesizer applies accepted proposals.** A reviewer accepts a proposal to add a new glossary term. The synthesizer materializes the term in project-local glossary state, records that the source was this retrospective and mission, and a later mission run sees the new term in its context bootstrap. Doctrine, DRG-edge, and glossary proposals are *staged for human approval* before being applied (Q2-A); only `flag_not_helpful` is auto-applied.

9. **Cross-mission patterns become visible.** An operator runs the cross-mission summary. They see "directive D was flagged not-helpful in 4 of last 5 missions," "term Y was missing in 3 missions," "1 mission has a malformed retrospective and is excluded with a reason." Three different fixture missions — rich findings, brief findings, skipped — are all rendered without the view crashing.

10. **Action surface calibration.** A governance owner runs the calibration report against the four in-scope missions (software-dev, research, documentation, ERP custom). The report shows, for every (profile, action) pair: which DRG artifacts were surfaced, which were missing, and which were too broad. Recommended fixes are expressed strictly as DRG edge changes — not as filters or hidden runtime logic.

### Edge cases

- The retrospective writer fails mid-write. Half-written `retrospective.yaml` must not be treated as valid; the lifecycle gate must surface the failure as `retrospective.failed`, not as `completed`.
- A legacy mission has no `retrospective.yaml` at all. Cross-mission summary reports it as "no retrospective" without crashing.
- A `retrospective.yaml` exists but is malformed or schema-incompatible (older finding format, hand-edited mistake). The summary excludes it with a structured reason and surfaces it for repair, instead of failing the entire summary.
- Two retrospectives for the same mission exist (re-run scenario). The most recent one wins for summary purposes; the prior one is preserved as history with a clear successor pointer.
- The synthesizer is asked to apply two proposals that conflict (e.g., "remove DRG edge E" and "rewire DRG edge E"). The synthesizer fails closed with a structured reason; nothing is applied silently.
- The mission's mode signal is ambiguous (no charter override, no explicit flag, conflicting environment and parent-process hints). The runtime resolves via the documented precedence (charter > flag > environment > parent-process); the resolution is logged with the source signal so the choice is auditable.
- An autonomous mission produces a retrospective that itself is empty (no findings). That is allowed — empty findings are still a valid `retrospective.completed` outcome — but cross-mission summary distinguishes "ran, no findings" from "ran, rich findings."
- A custom mission's loader-required `retrospective` marker step is missing. Loading must fail with a clear governance error; built-in missions are unaffected because they use the lifecycle terminus hook (Q3-C) rather than an explicit step.

---

## Functional Requirements

| ID      | Requirement                                                                                                                                                                                                                                                          | Status |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| FR-001  | The system MUST provide a `retrospective-facilitator` profile that exists in the shipped DRG and resolves through normal profile lookup.                                                                                                                              | Draft  |
| FR-002  | The system MUST provide a `retrospect` action that exists in the shipped DRG and resolves through normal action lookup.                                                                                                                                              | Draft  |
| FR-003  | The `retrospect` action's resolved DRG context MUST surface the mission's full event stream, mission metadata and detected mode, completed/skipped/blocked step history, paired invocation records and evidence references, the active DRG slice used during the mission, relevant charter/doctrine artifacts, relevant glossary terms, and the mission's output artifacts. | Draft  |
| FR-004  | A retrospective invocation against a fixture mission MUST produce a structured response that conforms to the `retrospective.yaml` schema.                                                                                                                            | Draft  |
| FR-005  | The system MUST define a Pydantic-backed schema for `retrospective.yaml` that captures: mission identity (id, slug, type, started/completed timestamps), mode and the source signal that produced it, retrospective status (`completed`, `skipped`, `failed`, `pending`), skip reason (when status is `skipped`), `helped`, `not_helpful`, `gaps`, and `proposals`. | Draft  |
| FR-006  | The schema MUST require provenance on every finding and proposal: source mission id, source evidence event ids, and the actor/profile that authored or approved the entry.                                                                                            | Draft  |
| FR-007  | The schema MUST support at least the proposal types `synthesize_directive`, `synthesize_tactic`, `synthesize_procedure`, `rewire_edge`, `add_edge`, `remove_edge`, `add_glossary_term`, `update_glossary_term`, and `flag_not_helpful`.                                | Draft  |
| FR-008  | The system MUST provide a writer that round-trips a fixture finding set through `retrospective.yaml` without loss or reordering of stable identifiers.                                                                                                                | Draft  |
| FR-009  | The canonical durable path for a mission's retrospective MUST be `.kittify/missions/<mission_id>/retrospective.yaml`, keyed by `mission_id` (ULID), and MUST be git-trackable.                                                                                         | Draft  |
| FR-010  | When a retrospective is skipped, the system MUST write both a `retrospective.yaml` with `status: skipped` (and the skip reason, actor, and timestamp) AND emit a `retrospective.skipped` event. Neither alone is sufficient.                                            | Draft  |
| FR-011  | In autonomous mode, the runtime MUST block the mission's transition to `done` until a `retrospective.completed` event is present. A missing or failed retrospective MUST surface a structured blocker that names the failure.                                          | Draft  |
| FR-012  | In autonomous mode, the runtime MUST NOT permit `retrospective.skipped` as a substitute for `retrospective.completed`. Silent skip in autonomous mode MUST be impossible.                                                                                              | Draft  |
| FR-013  | In HiC mode, at mission terminus the runtime MUST offer the retrospective to the operator before the mission can be marked done, and MUST permit the operator to either run it or explicitly skip it.                                                                | Draft  |
| FR-014  | In HiC mode, the runtime MUST NOT auto-invoke the retrospective without explicit operator action. Silent auto-run in HiC mode MUST be impossible.                                                                                                                     | Draft  |
| FR-015  | In HiC mode, mission completion MUST be allowed after either `retrospective.completed` or `retrospective.skipped`.                                                                                                                                                    | Draft  |
| FR-016  | Mode detection MUST resolve through the precedence: charter/project override > explicit flag > environment > parent process. The selected mode and its source signal MUST be recorded in the retrospective record and in mission events.                              | Draft  |
| FR-017  | The system MUST emit the following events with stable names and durable payloads: `retrospective.requested`, `retrospective.started`, `retrospective.completed`, `retrospective.skipped`, `retrospective.failed`, `retrospective.proposal.generated`, `retrospective.proposal.applied`, and `retrospective.proposal.rejected`. | Draft  |
| FR-018  | Retrospective events MUST be persisted to the same canonical mission event log used by other lifecycle events and MUST be reduced into the same mission status snapshot. Retries and re-runs MUST be representable as additional events on the same mission, not as silent overwrites. | Draft  |
| FR-019  | The system MUST provide a synthesizer that consumes a retrospective finding set and materializes accepted proposals against project-local doctrine, DRG, and glossary surfaces.                                                                                       | Draft  |
| FR-020  | The synthesizer MUST treat only `flag_not_helpful` as auto-applicable; all `synthesize_*`, `*_edge`, `add_glossary_term`, and `update_glossary_term` proposals MUST be staged for human approval and MUST NOT be applied silently in any mode.                          | Draft  |
| FR-021  | The synthesizer MUST run as an explicit operator/agent action (separate command or subcommand), not as an automatic post-completion hook.                                                                                                                              | Draft  |
| FR-022  | Every artifact, edge, or glossary term created or modified by the synthesizer MUST carry provenance metadata: `source: retrospective`, source mission id, source proposal id, source evidence event ids, and the approving actor.                                       | Draft  |
| FR-023  | When two staged proposals conflict (e.g., conflicting edge mutations on the same DRG edge or contradictory glossary updates), the synthesizer MUST fail closed with a structured reason and apply nothing from the conflicting set.                                     | Draft  |
| FR-024  | A later mission run, after a retrospective proposal has been accepted and synthesized, MUST observe the updated context (new directive, new edge, updated glossary term, etc.) when its DRG bootstrap loads.                                                            | Draft  |
| FR-025  | The system MUST provide a cross-mission retrospective summary surface, available as a CLI command and emitting both a human-readable report and a structured (e.g., JSON) artifact suitable for downstream tools.                                                       | Draft  |
| FR-026  | The cross-mission summary MUST surface, at minimum: directive/artifact references repeatedly flagged not-helpful, repeatedly missing glossary terms, repeatedly missing DRG edges, repeated context over- or under-inclusion, proposal acceptance/rejection rates, skipped-retrospective count and reasons, and missions with no retrospective. | Draft  |
| FR-027  | The cross-mission summary MUST handle rich, brief, skipped, missing, and malformed retrospective records without crashing; malformed records MUST be excluded with a structured reason that surfaces them for repair.                                                  | Draft  |
| FR-028  | Built-in missions (`software-dev`, `research`, `documentation`) MUST trigger the retrospective via a lifecycle terminus hook that invokes the `retrospect` action; they MUST NOT require their domain composition to declare an explicit `retrospect` step.            | Draft  |
| FR-029  | Custom missions loaded by the local custom-mission loader MUST continue to declare the structural final `retrospective` marker step; this requirement MUST remain part of the loader contract.                                                                          | Draft  |
| FR-030  | The system MUST produce per-mission action surface calibration reports for `software-dev`, `research`, `documentation`, and the ERP example custom mission, where each report enumerates every `(profile, action)` pair with: action id, profile id, resolved DRG artifact URNs, scope edges involved, context judged missing, context judged irrelevant or too broad, recommended DRG edge changes, and before/after evidence for any changed surfaces. | Draft  |
| FR-031  | All calibration outcomes MUST be expressed solely as DRG edge changes in `src/doctrine/graph.yaml` or in project-local graph overlays. The calibration tranche MUST NOT introduce prompt-builder filtering logic to hide over-broad context.                            | Draft  |
| FR-032  | Action surface inequalities derived from the architecture document's §4.5.1 contract (each step's surfaced context is a strict subset of its action's resolved scope, and is not a strict superset of what is needed) MUST hold for every step of every in-scope mission, validated by the calibration. | Draft  |
| FR-033  | The system MUST cover the lifecycle path with real-runtime integration tests that drive missions through autonomous and HiC terminus paths end-to-end, including silent-skip and silent-auto-run negative cases. Acceptance MUST NOT be proven solely through private helper calls. | Draft  |

---

## Non-Functional Requirements

| ID       | Requirement                                                                                                                                                                                                                              | Status |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| NFR-001  | Schema validation of a typical (≤200 findings) `retrospective.yaml` MUST complete in under 200 ms on a developer laptop, so retrospective gating does not perceptibly delay mission completion.                                          | Draft  |
| NFR-002  | The retrospective writer MUST be atomic: a successful write MUST result in a complete schema-valid file; an interrupted write MUST NOT leave a half-written `retrospective.yaml` that subsequent reads treat as `completed`.              | Draft  |
| NFR-003  | The cross-mission summary MUST handle a project with at least 200 historical missions and produce its report in under 5 seconds on a developer laptop.                                                                                   | Draft  |
| NFR-004  | The cross-mission summary MUST be tolerant: 100% of malformed or legacy records in a corpus MUST be skipped with a structured reason without aborting the summary run, and the count of skipped records MUST be reported.                | Draft  |
| NFR-005  | All retrospective and proposal events MUST be append-only; no operation MUST mutate or delete a previously persisted event during normal operation.                                                                                      | Draft  |
| NFR-006  | Provenance fidelity: 100% of synthesized doctrine, DRG-edge, or glossary changes MUST be traceable back to a source mission id, proposal id, and evidence event ids via the artifact's metadata alone (no log grep required).             | Draft  |
| NFR-007  | The retrospective gate MUST add no more than 500 ms of overhead to mission completion when a `retrospective.completed` event is already present.                                                                                          | Draft  |
| NFR-008  | The lifecycle gate MUST be deterministic: given the same mission event log and the same charter/mode signals, mode resolution and gate decision MUST always produce the same outcome.                                                    | Draft  |
| NFR-009  | Test coverage for new code in this tranche MUST be at least 90%, consistent with project policy from the charter.                                                                                                                        | Draft  |
| NFR-010  | The mypy `--strict` type check MUST pass for all new modules and changed modules in this tranche, consistent with project policy from the charter.                                                                                       | Draft  |

---

## Constraints

| ID     | Constraint                                                                                                                                                                                                                              | Status |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| C-001  | Existing software-dev composition MUST remain single-dispatch; this tranche MUST NOT regress that property.                                                                                                                              | Active |
| C-002  | Existing research and documentation composition MUST remain runnable through their existing entry points without behavioral regression.                                                                                                  | Active |
| C-003  | The local custom mission loader MUST remain runnable; the structural final `retrospective` marker requirement MUST remain enforced.                                                                                                      | Active |
| C-004  | Paired invocation lifecycle records MUST remain intact; this tranche MUST NOT alter their schema or their relationship to mission events.                                                                                                | Active |
| C-005  | Persistence of `decision_required` runtime side effects MUST remain intact; this tranche MUST NOT change how or where they are stored.                                                                                                   | Active |
| C-006  | This tranche MUST NOT introduce imports from the retired `spec_kitty_runtime` PyPI package; the CLI-internal runtime under `src/specify_cli/next/_internal_runtime/` is the only runtime surface in scope.                                | Active |
| C-007  | New code MUST use the canonical typed `Lane`, `WPState`, status `emit`/`reduce` primitives, and mission run state abstractions; raw lane strings or legacy frontmatter dictionaries MUST NOT be mutated where typed APIs exist.            | Active |
| C-008  | This tranche MUST NOT bundle non-blocking hygiene issues #735, #801, or #805 unless they directly block tests or the Spec Kitty workflow for the work in scope.                                                                          | Active |
| C-009  | This tranche MUST NOT redo work covered by closed Phase 6 issues #502, #503, #504, or #505, and MUST NOT treat stale local review findings as current unless they have been reproduced against the current `origin/main` baseline.        | Active |
| C-010  | This tranche MUST NOT start SaaS, tracker, mobile, website, or hub work; scope is limited to Spec Kitty's local mission-learning surface.                                                                                                | Active |
| C-011  | Calibration MUST adjust governance only via DRG edges in `src/doctrine/graph.yaml` or project-local graph overlays; this tranche MUST NOT introduce prompt-builder filtering logic to hide over-broad context.                            | Active |
| C-012  | All retrospective-driven doctrine, DRG, or glossary changes MUST be reviewable and reversible: no proposal type may produce a change that cannot be inspected and rolled back through the same provenance metadata.                       | Active |
| C-013  | Charter/project policy is sovereign for mode detection: in any conflict, the project's charter override MUST win over an explicit operator flag, an environment signal, or a parent-process signal. (Q1-B)                                | Active |
| C-014  | Retrospective findings, schema, and writer MUST live alongside `.kittify/missions/<mission_id>/retrospective.yaml` keyed by canonical `mission_id` (ULID), not by the display-only `mission_number` prefix.                                | Active |

---

## Success Criteria

These criteria describe outcomes from the operator and reviewer perspective. They do not name technologies, file paths, or APIs.

- **SC-001**: 100% of autonomous mission runs in real-runtime tests are blocked from "done" until a retrospective is captured. No autonomous mission can be silently completed without learning evidence.
- **SC-002**: 100% of HiC mission runs in real-runtime tests reach "done" only after the operator either ran the retrospective or explicitly skipped it; no run reaches "done" via silent auto-run.
- **SC-003**: A mission's retrospective record is machine-readable: an automated reader can answer the questions "what helped," "what did not help," "what was missing," and "what was proposed" by parsing structured fields, without relying on prose extraction.
- **SC-004**: Operators can answer the question "which directives, terms, or context have repeatedly hurt our missions?" from a single cross-mission view in under one operator action, with results returned in under five seconds for a project with up to 200 missions.
- **SC-005**: Reviewers can trace any synthesized doctrine, DRG-edge, or glossary change back to the originating mission and proposal in one step (read the artifact's provenance), 100% of the time.
- **SC-006**: A reviewer who rejects a proposal sees that the project state is unchanged, and a later cross-mission summary reflects the rejection in proposal acceptance/rejection rates.
- **SC-007**: After a reviewer accepts a proposal, the next mission of any in-scope type observes the change in its bootstrapped context — the improvement is visible in the next run, not only documented in a report.
- **SC-008**: Calibration produces a per-mission report that operators can act on: every (profile, action) pair has a verdict on missing context, irrelevant context, and the recommended DRG edge change. No recommendation is expressed as runtime filtering.
- **SC-009**: The cross-mission summary survives a corpus that mixes rich, brief, skipped, missing, and malformed retrospectives; zero malformed records cause the summary to fail.
- **SC-010**: Existing built-in mission composition tests and existing custom mission loader tests continue to pass after this tranche lands. No regression in those surfaces is acceptable.

---

## Key Entities

- **Retrospective record** — the durable structured artifact produced at mission terminus. Identified by mission id. Carries status, mode, helped/not-helpful/gaps/proposals, and provenance metadata. Must be schema-valid before it counts as `completed`.
- **Finding** — a single entry inside `helped`, `not_helpful`, or `gaps`. Always carries a typed reference (doctrine artifact, DRG edge, glossary term, prompt/template, test) and provenance back to evidence events.
- **Proposal** — a single machine-actionable change request inside `proposals`. Has a typed kind (e.g., `synthesize_directive`, `add_edge`, `flag_not_helpful`), a payload, and provenance. Has an acceptance state (pending, accepted, rejected) carried by the proposal lifecycle events.
- **Mode** — the resolved governance mode for a mission run. Either `autonomous` or `human_in_command`, with the source signal that produced the resolution recorded for audit.
- **Mode signal** — one of: charter override, explicit flag, environment, parent-process. Combined under the documented precedence (Q1-B) to produce `mode`.
- **Synthesizer** — the component that consumes accepted proposals and applies them to project-local doctrine, DRG, and glossary. Operates on staged proposals only (auto-application is reserved for `flag_not_helpful`); always writes provenance.
- **Cross-mission summary** — the aggregated view across the project's mission history. Reads the corpus of retrospective records and proposal lifecycle events; tolerant to malformed/missing entries.
- **Calibration report** — the per-mission diagnostic that walks every (profile, action) pair, compares the surfaced context to what each step actually needed, and recommends DRG edge changes.
- **Lifecycle terminus hook** — the runtime mechanism that invokes the `retrospect` action at the end of a built-in mission's last domain step. Custom missions reach the same point via their explicit `retrospective` marker step.
- **Action surface inequality** — the architectural property (architecture §4.5.1) that each step's surfaced context is a non-strict subset of the action's resolved scope and not a strict superset of what the step needs. Used as the verification target for calibration.

---

## Assumptions

These reasonable defaults are recorded here per charter directive DIRECTIVE_003 (Decision Documentation Requirement). Each is open to revision before plan if the user disagrees.

1. **Canonical retrospective path is `mission_id`-keyed under `.kittify/missions/`**. This survives renames, mission_slug churn, and is consistent with the post-083 mission identity model. The mission feature directory under `kitty-specs/<slug>/` is *not* the canonical home for the retrospective record because the feature directory is mission-domain content; the retrospective is mission-governance metadata that should outlive the feature directory's lifecycle.
2. **Skipped retrospectives produce both an event and a `retrospective.yaml` with `status: skipped`**. (Brief item 2.) The yaml acts as durable, git-trackable provenance for the skip; the event integrates with the existing event reducer and gate.
3. **Mode-detection precedence is charter/project override > explicit flag > environment > parent process**. (Q1-B.) Project policy is sovereign — operator flags and ambient signals can only override where the charter permits.
4. **Autonomous mode cannot be overridden silently by a human**. A charter MAY declare an explicit "operator may override autonomous to skip" rule; absent such a declaration, autonomous mode does not permit skipping. Any override that occurs is recorded with the actor identity and the charter clause that authorized it.
5. **Event names are stable as listed in FR-017**. Subsequent renames will require a deprecation cycle and event-log compatibility shim.
6. **Auto-applied proposal types are limited to `flag_not_helpful`**. (Q2-A.) All other proposal kinds are staged for human approval before they touch project-local doctrine, DRG, or glossary state. The auto-applied set is intentionally small so that a runaway autonomous loop cannot mutate governance.
7. **The synthesizer is an explicit command, not an automatic post-completion hook**. This keeps retrospective writing and proposal application as separate auditable operations, and avoids surprising governance mutations the moment a retrospective lands.
8. **Cross-mission summary surface is a CLI command that emits both a human-readable report and a structured (JSON) artifact**. CLI-first matches the brief's preference; the structured artifact gives downstream tools (dashboards, future SaaS surfaces) a stable consumer without requiring those tools to ship in this tranche.
9. **Built-in missions use a lifecycle terminus hook; custom missions keep the explicit `retrospective` marker step**. (Q3-C.) This avoids per-mission template churn for built-ins and preserves the existing custom-loader contract.
10. **The `retrospect` action is the single behavioral entry point** for both the lifecycle hook (built-ins) and the explicit `retrospective` marker step (custom missions). They invoke the same action so the schema, events, and gate behavior are uniform.

---

## Out of Scope

These items are explicitly *not* part of this tranche. They are listed so plan/tasks does not absorb them.

- SaaS, tracker, mobile, website, and hub work (per `start-here.md` and C-010).
- Reopening or re-doing closed Phase 6 issues #502, #503, #504, #505 (per C-009).
- Bundling the non-blocking hygiene issues #735, #801, #805 (per C-008) unless they prove to directly block testing or workflow for in-scope work.
- Rewriting any built-in mission's domain composition. The composition pattern shipped in WP6.1–WP6.5 is treated as a baseline; this tranche only adds the retrospective lifecycle hook around it.
- Building a dashboard or web UI for the cross-mission summary. The CLI report and the structured (JSON) artifact are the surface for this tranche; downstream UIs are downstream.
- Designing a generic governance-event SDK. Retrospective events use the existing mission event log primitives.
- Migrating historical missions to backfill retrospectives. Legacy missions without a retrospective are surfaced as such by the cross-mission summary, not retroactively populated.
- Adding prompt-builder runtime filtering to compensate for over-broad context. Calibration must express its findings as DRG edge changes only (C-011).

---

## Dependencies

- The post-083 mission identity model (`mission_id`, `mid8`) — already on `main`. Used as the key for the canonical retrospective path.
- The 3.0 status event log (`status.events.jsonl`) primitives in `specify_cli.status` — already on `main`. Used as the substrate for retrospective lifecycle events and the gate's deterministic decision.
- Charter context bootstrap (`spec-kitty charter context`) — already on `main`. Used to source charter override signals for mode detection.
- The DRG / doctrine surface in `src/doctrine/graph.yaml` and project-local graph overlays — already on `main`. Used as the only knob for action-surface calibration outcomes.
- Existing built-in mission compositions (software-dev, research, documentation) and the local custom mission loader (including the ERP example) — already on `main`. Required as test surfaces for FR-028, FR-029, FR-030, FR-032.

---

## Open Risks (for premortem during plan)

These are recorded so plan/tasks can apply the `premortem-risk-identification` tactic from charter doctrine.

- **Drift between event names and event payloads.** If event names land before payloads stabilize, the gate may pass on a `retrospective.completed` event whose payload is unusable to the cross-mission summary. Mitigation belongs in plan.
- **Synthesizer staleness.** A staged proposal may sit untouched for months and then be applied against a doctrine surface that has moved. Mitigation belongs in plan (e.g., proposal staleness checks before apply).
- **Calibration churn.** Adjusting DRG edges to satisfy §4.5.1 inequalities for one step may regress another step. Mitigation: per-step before/after evidence and a regression bar in calibration tests.
- **Mode misattribution.** A misconfigured CI environment may look like autonomous when the operator intended HiC, or vice versa. Mitigation: record the source signal that produced the mode and surface it in retrospective events.
- **Privacy of evidence references.** Evidence event ids are durable; if a retrospective ever references something a charter wants redacted, redaction needs to flow through. Mitigation: provenance treats event ids as opaque references, not as substitutes for the underlying content.

---

## Acceptance Gates (mirrored from `start-here.md` for this spec)

The eventual implementation is considered acceptance-complete only when:

1. `profile:retrospective-facilitator` and `action:retrospect` exist and resolve through the shipped DRG.
2. `retrospective.yaml` schema validates and round-trips fixture data.
3. The retrospective writer writes to the canonical durable location (`.kittify/missions/<mission_id>/retrospective.yaml`).
4. Autonomous mode blocks mission completion until `retrospective.completed`.
5. HiC mode offers the retrospective and permits explicit skip with `retrospective.skipped`.
6. Silent auto-run in HiC mode is impossible and is covered by tests.
7. Silent skip in autonomous mode is impossible and is covered by tests.
8. A retrospective finding set can produce synthesized project-local artifacts/graph/glossary changes (subject to the auto vs. staged policy in FR-020).
9. Provenance for synthesized changes references the source retrospective and mission.
10. A later mission run sees updated context from accepted retrospective changes.
11. The cross-mission summary handles rich, brief, skipped, missing, and malformed retrospective data.
12. Calibration reports exist for software-dev, research, documentation, and the ERP custom mission.
13. Calibration changes adjust DRG/project-graph edges only.
14. Existing built-in mission composition tests still pass.
15. Existing custom mission loader tests still pass.
16. Real-runtime integration tests drive the lifecycle path; acceptance is not proved only through private helper calls.

---

## Resolved Clarifications

The brief listed ten clarifications for `/spec-kitty.specify` to resolve before plan/tasks. They are resolved here:

1. **Canonical `retrospective.yaml` path** — `.kittify/missions/<mission_id>/retrospective.yaml`. Rationale: durable, project-local, git-trackable, keyed by canonical ULID identity, and outlives the feature directory's lifecycle. (FR-009, C-014, Assumption 1.)
2. **Skipped retrospective representation** — both an event AND a `retrospective.yaml` with `status: skipped`. (FR-010, Assumption 2.)
3. **Mode-detection precedence** — charter/project override > explicit flag > environment > parent process. (FR-016, C-013, Q1-B.)
4. **Autonomous override by a human** — only if the project charter declares it permissible; the override is recorded with actor identity and the charter clause that authorized it. (Assumption 4.)
5. **Event names and payloads** — names are fixed in FR-017; payload shape is constrained by FR-018 (must reduce into the canonical mission status snapshot, must be append-only, must support retries as additional events). Final field-level payload schema is plan-time work.
6. **Auto-applied vs. staged proposals** — only `flag_not_helpful` auto-applies; everything else is staged. (FR-020, Q2-A.)
7. **Synthesizer handoff timing** — explicit command, not an automatic post-completion hook. (FR-021, Assumption 7.)
8. **Cross-mission summary surface** — CLI command that emits both a human-readable report and a structured artifact. (FR-025, Assumption 8.)
9. **Verification of architecture §4.5.1 action-surface inequalities** — calibration walks every `(profile, action)` pair and asserts each step's surfaced context is a non-strict subset of the action's resolved scope and not a strict superset of what the step needs. (FR-032.)
10. **Built-in vs. custom mission integration** — built-ins use a lifecycle terminus hook that invokes `action:retrospect`; custom missions keep their explicit `retrospective` marker step. Both reach the same action. (FR-028, FR-029, Q3-C, Assumption 9 and 10.)
