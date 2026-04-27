# Release-Gate Requirements Quality Checklist: Mission Retrospective Learning Loop

**Purpose**: Heavy formal release-gate review of *requirements quality* (completeness, clarity, consistency, measurability, coverage) for the Phase 6 FR4 retrospective learning loop. This checklist tests whether the requirements in `spec.md` are well-written and ready for plan/tasks — it does **not** test implementation behavior.
**Created**: 2026-04-27
**Spec**: [../spec.md](../spec.md)
**Audience**: Reviewer + governance owner + future implementer
**Focus**: Broad sweep across governance/lifecycle gating, schema/event contract, provenance/synthesizer, cross-mission summary, action-surface calibration, and cross-cutting NFR/scenario/coverage quality.
**Explicit exclusion**: This checklist does not require the spec to prescribe specific implementation files or module ownership. Those decisions belong to `/spec-kitty.plan`.

---

## Governance & Lifecycle Gating Quality

- [ ] CHK001 — Is the mutually exclusive set of valid mission modes (`autonomous`, `human_in_command`) explicitly enumerated as a closed set with no implicit third value? [Completeness, Spec §Key Entities, §FR-016]
- [ ] CHK002 — Is the resolution precedence among the four mode signals (charter override, explicit flag, environment, parent process) stated as a single total ordering with no ambiguity? [Clarity, Spec §FR-016, §C-013]
- [ ] CHK003 — Are the conditions under which a charter MAY permit autonomous-mode override expressed as observable predicates (rather than as narrative aspiration)? [Clarity, Spec §Assumption 4]
- [ ] CHK004 — Are the audit-trail fields required when a charter authorizes an autonomous-mode override (authorizing charter clause, actor identity, timestamp, override reason) enumerated? [Completeness, Spec §Assumption 4, Gap]
- [ ] CHK005 — Are "silent skip" and "silent auto-run" defined with operational predicates (i.e., what observable runtime behavior counts as "silent") so the prohibitions can be tested? [Clarity, Spec §FR-012, §FR-014, Ambiguity]
- [ ] CHK006 — Are the structured-blocker fields produced when autonomous-mode completion is refused (failure name, missing-evidence reference, mode, mission id) enumerated? [Completeness, Spec §FR-011, Gap]
- [ ] CHK007 — Is the source-signal value that produced the resolved mode required to be persisted in both the retrospective record and the mission event log, not just one of them? [Completeness, Spec §FR-016, §FR-018]
- [ ] CHK008 — Are mode-detection requirements consistent between FR-016 and the acceptance scenario that exercises charter sovereignty over an explicit operator flag? [Consistency, Spec §FR-016, §User Scenarios — scenario 6]
- [ ] CHK009 — Is the behavior on ambiguous mode signals (no charter, no flag, conflicting env and parent-process hints) defined as a deterministic resolution outcome rather than left implementation-defined? [Clarity, Spec §FR-016, §Edge cases]
- [ ] CHK010 — Is the relationship between the lifecycle terminus hook (built-in missions) and the explicit `retrospective` marker step (custom missions) required to invoke the same `retrospect` action with the same gate semantics? [Consistency, Spec §FR-028, §FR-029, §Assumption 10]

## Schema & Event Contract Quality

- [ ] CHK011 — Is the canonical durable path stated as a single normative location (not "either/or") with an explicit rationale for not using the feature directory? [Clarity, Spec §FR-009, §Resolved Clarification 1]
- [ ] CHK012 — Are all four `status` enum values (`completed`, `skipped`, `failed`, `pending`) defined together with the lifecycle transitions that legally produce each? [Completeness, Spec §FR-005, Gap]
- [ ] CHK013 — Are required `retrospective.yaml` fields explicitly distinguished from optional fields, so plan/tasks cannot accidentally treat an optional field as load-bearing? [Clarity, Spec §FR-005, Ambiguity]
- [ ] CHK014 — Are proposal-type-specific payload requirements (e.g., what `add_edge` carries vs. what `synthesize_directive` carries) either specified, or explicitly deferred to plan with a documented rationale? [Completeness, Spec §FR-007, Gap]
- [ ] CHK015 — Are the eight stable event names in FR-017 required to be unique against existing mission event names (no name reuse, no overlap with existing lane events)? [Consistency, Spec §FR-017, Gap]
- [ ] CHK016 — Is the relationship between proposal-lifecycle events (`generated` / `applied` / `rejected`) and the retrospective record's proposal-state field defined so a reader can reconstruct one from the other? [Clarity, Spec §FR-017, §FR-018, §Key Entities]
- [ ] CHK017 — Are retry semantics for retrospective execution defined so re-runs append events rather than mutate prior ones? [Completeness, Spec §FR-018, §NFR-005]
- [ ] CHK018 — Is the "two retrospectives for the same mission" precedence (most-recent wins for summary, prior preserved with successor pointer) elevated from edge-case narrative into a normative requirement? [Clarity, Spec §Edge cases, Gap]
- [ ] CHK019 — Are durable evidence-event references in findings required to be opaque, redaction-stable identifiers (i.e., not substitutable for the underlying content)? [Completeness, Spec §Open Risks — privacy, Gap]
- [ ] CHK020 — Is "schema-valid" defined precisely enough that the gate can refuse a half-written file (i.e., is `completed` defined as "schema-valid AND status=completed", not just "file exists")? [Clarity, Spec §FR-008, §NFR-002, Gap]

## Provenance, Synthesizer, and Reversibility Quality

- [ ] CHK021 — Are the auto-applied and staged proposal-type lists declared closed sets, with the rule for any unlisted future proposal type stated (default-staged)? [Clarity, Spec §FR-020, Ambiguity]
- [ ] CHK022 — Is the staged-proposal lifecycle (`pending → accepted | rejected → applied | never-applied`) defined as an explicit state machine rather than described only in prose? [Completeness, Spec §FR-020, §FR-022, Gap]
- [ ] CHK023 — Are the provenance fields required on every synthesized artifact enumerated as a fixed minimum set (source: retrospective; source mission id; source proposal id; source evidence event ids; approving actor)? [Completeness, Spec §FR-022, §NFR-006]
- [ ] CHK024 — Is "conflict" between two proposals defined with concrete predicates (which pairs of proposal kinds and payloads count as conflicting), not left to interpretation? [Clarity, Spec §FR-023, Ambiguity]
- [ ] CHK025 — Is reversibility of a synthesized change defined operationally — i.e., what observable evidence proves a change can be inspected and rolled back through provenance alone? [Measurability, Spec §C-012, Gap]
- [ ] CHK026 — Are the requirements across FR-020 (staged), FR-021 (explicit-command synthesizer), and FR-023 (fail-closed on conflict) consistent with no gap through which a proposal could apply silently? [Consistency, Spec §FR-020, §FR-021, §FR-023]
- [ ] CHK027 — Is the requirement "a later mission run sees updated context" stated in a measurable form (the next run's bootstrap surfaces the change with the source provenance attached), not only narrated? [Measurability, Spec §FR-024, §SC-007]
- [ ] CHK028 — Is the proposal-rejection path required to leave project state unchanged, with the rejection visible in cross-mission summary metrics? [Completeness, Spec §SC-006, Gap]
- [ ] CHK029 — Is auto-application of `flag_not_helpful` constrained so that even auto-application carries provenance and is reversible? [Consistency, Spec §FR-020, §C-012]
- [ ] CHK030 — Is the explicit-command requirement for the synthesizer (FR-021) reconciled with FR-024 — i.e., is the path from "proposal accepted" to "next mission sees it" specified end-to-end without leaving an implicit silent step? [Consistency, Spec §FR-021, §FR-024, Gap]

## Cross-Mission Summary & Tolerance Quality

- [ ] CHK031 — Are the categories of tolerable input (rich, brief, skipped, missing, malformed) enumerated with mutually exclusive definitions a reader can apply to any single record? [Clarity, Spec §FR-027, §SC-009]
- [ ] CHK032 — Is the structured-reason content required when a malformed record is excluded specified (e.g., reason code, mission id, schema error class)? [Completeness, Spec §FR-027, §NFR-004, Gap]
- [ ] CHK033 — Is the pattern catalog in FR-026 (not-helpful directives, missing terms, missing edges, over/under-inclusion, acceptance/rejection rates, skip count, no-retro count) declared a normative minimum, with extensions allowed but not required? [Clarity, Spec §FR-026]
- [ ] CHK034 — Is the human-readable report required to be informationally equivalent to the structured (JSON) artifact, so a downstream tool consuming JSON cannot drift from what an operator sees? [Consistency, Spec §FR-025, Gap]
- [ ] CHK035 — Is the 200-mission corpus threshold in NFR-003 the only volumetric bound, or are concurrent-summary-run scenarios (two operators run summary at once) also addressed? [Coverage, Spec §NFR-003, Gap]
- [ ] CHK036 — Is the "missions with no retrospective yet" count specified to distinguish "legacy / pre-tranche" from "in-flight / not yet at terminus"? [Clarity, Spec §FR-026, Ambiguity]

## Action-Surface Calibration Quality

- [ ] CHK037 — Is the architecture §4.5.1 action-surface inequality (each step's surfaced context is a non-strict subset of the action's resolved scope and not a strict superset of what the step needs) stated in `spec.md` in a form that does not require reading the architecture document to test? [Clarity, Spec §FR-032, Ambiguity]
- [ ] CHK038 — Are the calibration report's required columns (action id, profile id, resolved DRG artifact URNs, scope edges involved, missing context, irrelevant/too-broad context, recommended DRG edge change, before/after evidence) treated as a normative minimum schema? [Completeness, Spec §FR-030]
- [ ] CHK039 — Is "recommended DRG edge change" defined as a structured proposal (add / remove / rewire with from-node, to-node, edge-kind) rather than as free-text guidance? [Clarity, Spec §FR-030, §FR-031, Gap]
- [ ] CHK040 — Is the prohibition against prompt-builder filtering expressed as a property a reviewer can detect from the diff (no new filtering call sites introduced) rather than only as policy intent? [Measurability, Spec §FR-031, §C-011]
- [ ] CHK041 — Are calibration scope-completion criteria measurable per in-scope mission (every `(profile, action)` pair walked, zero skipped pairs, before/after evidence for every change)? [Coverage, Spec §FR-030, §SC-008]

## Non-Functional Requirements & Cross-Cutting Measurability

- [ ] CHK042 — Are the NFR thresholds (200 ms schema validation, 500 ms gate overhead, 5 s summary on a 200-mission corpus) qualified with the measurement environment (hardware class, cold/warm state) so they are reproducibly testable? [Measurability, Spec §NFR-001, §NFR-003, §NFR-007, Ambiguity]
- [ ] CHK043 — Is "atomic write" in NFR-002 expressed as a testable predicate (e.g., a crash mid-write either leaves no `retrospective.yaml` at the canonical path or leaves the unchanged prior version)? [Clarity, Spec §NFR-002]
- [ ] CHK044 — Is "deterministic gate decision" in NFR-008 stated as an externally observable property (same event log + same charter/mode signals → same decision) rather than as an internal implementation hint? [Clarity, Spec §NFR-008]
- [ ] CHK045 — Is the 90% coverage threshold in NFR-009 scoped to "new and changed code in this tranche" (not whole-repo), and is the measurement policy referenced or explicitly deferred to plan? [Clarity, Spec §NFR-009, Ambiguity]

## Scenario Coverage, Edge Cases, and Recovery

- [ ] CHK046 — Are recovery requirements specified for a half-written `retrospective.yaml` beyond the single edge-case bullet (i.e., what state the runtime expects on restart, and how it surfaces the partial-write failure)? [Coverage, Spec §Edge cases, §NFR-002, Gap]
- [ ] CHK047 — Are concurrent-actor scenarios addressed (two agents attempting to write a retrospective for the same mission at the same time)? [Coverage, Gap, Exception Flow]
- [ ] CHK048 — Are recovery requirements specified for an interrupted synthesizer run — i.e., is re-running the synthesizer after partial application defined as safe and idempotent? [Coverage, Spec §FR-021, Gap, Recovery Flow]
- [ ] CHK049 — Are exception-flow requirements specified for a mission that produced no usable evidence events (autonomous run that terminated very early), so the retrospective contract still has a defined outcome? [Coverage, Spec §FR-006, Gap, Exception Flow]
- [ ] CHK050 — Is the failure mode "custom mission missing its required `retrospective` marker step" defined as an explicit governance failure with a structured reason, not a silent fallback? [Coverage, Spec §FR-029, §Edge cases]
- [ ] CHK051 — Is the empty-findings-but-completed retrospective ("ran, no findings") distinguished from "ran, rich findings" in cross-mission summary requirements? [Coverage, Spec §Edge cases, §FR-026]

## Dependencies, Assumptions, Conflicts, and Traceability

- [ ] CHK052 — Is each dependency listed in §Dependencies tied to at least one specific FR or constraint that consumes it, so plan/tasks cannot drop a dependency silently? [Traceability, Spec §Dependencies, Gap]
- [ ] CHK053 — Are assumptions classified as either "fixed by a clarification answer" or "default open to revision," so a reviewer can tell which assumptions can be flipped without re-asking the user? [Clarity, Spec §Assumptions]
- [ ] CHK054 — Are FR-020 (staged proposals) and FR-024 ("a later mission run sees updated context") reconciled into a single end-to-end requirement chain so there is no implicit silent application step between them? [Consistency, Spec §FR-020, §FR-024, Gap]
- [ ] CHK055 — Is §Out of Scope distinguishable from §Open Risks — i.e., is the difference between "we are not doing this now" and "we might fail at this" stated explicitly? [Clarity, Spec §Out of Scope, §Open Risks, Ambiguity]
- [ ] CHK056 — Is a requirement & acceptance-criteria ID scheme established and consistently used (FR-###, NFR-###, C-###, SC-###, CHK### scoped to the checklist) with no collisions or duplicates across the spec? [Traceability]
- [ ] CHK057 — Does every acceptance gate in §Acceptance Gates trace back to at least one FR/NFR/C, so a reviewer can verify that the gates are not adding unstated requirements? [Traceability, Spec §Acceptance Gates, Gap]
- [ ] CHK058 — Are §Resolved Clarifications cross-referenced to the FR/NFR/C they constrain, so a future reader can see why a given requirement is shaped as it is? [Traceability, Spec §Resolved Clarifications]

---

## Notes

- Items use `[Quality Dimension, Spec §...]` markers per the checklist authoring rules. ~95% of items carry a spec reference or an explicit `[Gap]` / `[Ambiguity]` / `[Conflict]` / `[Assumption]` marker, well above the 80% traceability minimum.
- Per Q3, no item prescribes a specific implementation module, file path, or module owner. Items that mention concrete artifact names (e.g., `retrospective.yaml`, the eight event names) are testing whether the *spec* defines those contracts clearly — the spec already commits to those names, so they are part of the *what*, not the *how*.
- Items grouped by concern area for review ergonomics, but cross-area consistency items are intentional and traced to multiple spec sections.
- This checklist is a release-gate review, not a per-WP gate; items that need plan-time decisions are flagged with "explicitly deferred to plan with rationale" rather than treated as gaps.
