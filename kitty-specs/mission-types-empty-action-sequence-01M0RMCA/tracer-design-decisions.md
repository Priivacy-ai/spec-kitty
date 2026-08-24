# Tracer: Design Decisions

Two decision forks, both resolved before spec authoring began and persisted verbatim (with evidence) into `spec.md`'s `## Clarifications` section. Recorded here in short form, cross-referenced to that section.

## Decision 1 — thread `PackContext`, or migrate to consumption-boundary sourcing?

**Resolved: thread it.** `template_set` already underwent a full, completed retirement off the `MissionType` model (mission `mission-step-creatability-01KXQA6R`) and now sources from a consumption-boundary resolver (`_resolve_template_set_slot`). `action_sequence` has had no equivalent migration — it is still a first-class validated model field read at eight call sites across the codebase, and its own docstring calls the raw-YAML fallback "C-007-retained, transitional" (i.e. still authoritative, not deprecated). No ADR authorizes an `action_sequence` migration. Threading `pack_context` through the existing seam mirrors the pattern `resolve_layered_mission_types` already uses successfully for the roster (#3397) and mirrors `_resolve_template_set_slot`'s own already-working, already-production-consumed pattern (confirmed stale-claim correction, SK-82). See `spec.md` § Clarifications, Decision 1, for the full evidence trail.

## Decision 2 — does the activation-gate fix belong in this mission?

**Resolved: no.** Issue #3701's Non-goals section names the activation-gate gap explicitly and points to #3702 (confirmed open, unassigned). SPEC-KITTY-LEDGER.md's SK-81 (verified first-hand) documents the operational consequence — `charter activate mission-type <T>` succeeds and writes the activation even when `<T>` resolves an empty sequence, so the failure only surfaces on the next invocation, after the project is already activated into a broken state — and is cited in `spec.md` as motivation for why this mission's projection defect matters, not as in-scope work. See `spec.md` § Clarifications, Decision 2.

## Plan-phase decision — one Implementation Concern, not several

Considered splitting the plan's Implementation Concern Map into per-function ICs (one per touched function in the four-function chain) to mirror C-007's own function-by-function enumeration, but rejected that shape: the four functions are not independent architectural areas, they are one call chain that must be threaded together as a single unit — a partial threading (e.g. only `_inject_projected_fields` and `_load_layered_mission_type_file` fixed, `resolve_layered_mission_types`'s call sites left unfixed) would still leave the defect live end-to-end. Used exactly one IC (IC-01) and said so explicitly in plan.md, per this mission's own instruction that a single-IC plan is acceptable and should be stated as a deliberate choice rather than an omission.

## Plan-phase decision — campsite-clean scope

Identified one real candidate for the opening campsite-clean (the near-duplicated per-file YAML-parse/validate block between `MissionTypeRepository._load()` and `_load_layered_mission_type_file`) but declined to fold it: extracting a shared helper would necessarily touch `_load()`'s body, which spec.md's own FR-005/C-001 require to stay untouched (threading a project-dependent value into `_load()`'s `cls`-keyed cache would poison it for later-resolved projects in the same process — the exact hazard FR-005 exists to prevent — and even a *non*-pack_context-related touch to `_load()` would still make it a fifth touched function under C-007's four-function bound). Recorded this as an explicit "not folded, flagged for a future mission" finding in plan.md's Campsite-clean section rather than silently skipping it or silently folding it anyway.

## Tasks-phase decision — one WP, not several

Per plan.md's own "PR shape" section (explicit instruction: "/spec-kitty.tasks should reflect
that as (most likely) a single WP, or at most a small number of WPs that still land in one PR"),
authored `wps.yaml` with exactly one WP (WP01) covering all of FR-001..FR-008, NFR-001..NFR-004,
and C-001..C-008. Considered and rejected splitting into e.g. a "production code" WP and a "test"
WP: red-first/ATDD discipline (C-011, spec.md SC-004) requires the red test to be authored and
witnessed red *before* the production-code fix lands, and both must be verified together (the
git-stash/rerun/stash-pop cycle) by the same actor in the same sitting — splitting across two WPs
would either force an artificial dependency (test-WP blocks code-WP, defeating the point of
parallelizable WPs) or break the stash/rerun witnessing requirement across two different
implementers who cannot literally `git stash` each other's uncommitted work. IC-01 is one seam,
one coherent change; the four touched functions and their three call-site edits are inseparable
(a partial threading leaves the defect live end-to-end, per plan.md's own IC-01 framing). One WP
is the honest decomposition — confirmed, not just carried forward by default.
