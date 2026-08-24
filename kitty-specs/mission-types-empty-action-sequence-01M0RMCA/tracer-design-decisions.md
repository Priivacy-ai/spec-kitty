# Tracer: Design Decisions

Two decision forks, both resolved before spec authoring began and persisted verbatim (with evidence) into `spec.md`'s `## Clarifications` section. Recorded here in short form, cross-referenced to that section.

## Decision 1 — thread `PackContext`, or migrate to consumption-boundary sourcing?

**Resolved: thread it.** `template_set` already underwent a full, completed retirement off the `MissionType` model (mission `mission-step-creatability-01KXQA6R`) and now sources from a consumption-boundary resolver (`_resolve_template_set_slot`). `action_sequence` has had no equivalent migration — it is still a first-class validated model field read at eight call sites across the codebase, and its own docstring calls the raw-YAML fallback "C-007-retained, transitional" (i.e. still authoritative, not deprecated). No ADR authorizes an `action_sequence` migration. Threading `pack_context` through the existing seam mirrors the pattern `resolve_layered_mission_types` already uses successfully for the roster (#3397) and mirrors `_resolve_template_set_slot`'s own already-working, already-production-consumed pattern (confirmed stale-claim correction, SK-82). See `spec.md` § Clarifications, Decision 1, for the full evidence trail.

## Decision 2 — does the activation-gate fix belong in this mission?

**Resolved: no.** Issue #3701's Non-goals section names the activation-gate gap explicitly and points to #3702 (confirmed open, unassigned). SPEC-KITTY-LEDGER.md's SK-81 (verified first-hand) documents the operational consequence — `charter activate mission-type <T>` succeeds and writes the activation even when `<T>` resolves an empty sequence, so the failure only surfaces on the next invocation, after the project is already activated into a broken state — and is cited in `spec.md` as motivation for why this mission's projection defect matters, not as in-scope work. See `spec.md` § Clarifications, Decision 2.
