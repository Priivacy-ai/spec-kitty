# Implementation Plan: Mission lifecycle, dispatch & DRG closeout

**Branch**: `feat/mission-lifecycle-dispatch-drg-closeout` (planning = merge target; PR-bound onto `upstream/main`) | **Date**: 2026-06-13 | **Spec**: [spec.md](./spec.md)
**Input**: Mission specification from `kitty-specs/mission-lifecycle-dispatch-drg-closeout-01KV0S99/spec.md`

## Summary

Finish the unfinished tails of three tracked residuals so they close honestly:
(A) **#1802** — deliver the post-mission lifecycle surface (record a follow-up commit/PR
against a merged mission; re-open a merged mission) by **extending the canonical status
event stream** with two new lifecycle events; (B) **#1810/#1804** — unify `do`/`ask`/`advise`
onto the single governed-invocation mechanism with `spec-kitty dispatch` as canonical and
the three verbs kept as first-class, byte-identical aliases; (C) **#1863** — repair the
stale `java-implementer` DRG reference (+ same-class refs), triage the remaining orphans
(wire or document — never bulk-delete valid doctrine), regenerate deterministically, and
pin the reduced orphan count. Three independent lanes; closure of #1863/#1802/#1804 is the
mission's definition of done.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), pydantic v2 (frozen event records), ruamel.yaml
(deterministic graph emit), `spec_kitty_events` (external lifecycle-event contract — consumed
via public imports only, never edited here), pytest/ruff/mypy (gates)
**Storage**: Append-only JSONL event logs (`kitty-specs/<slug>/status.events.jsonl`),
`meta.json` mission metadata, `src/doctrine/graph.yaml` (generated DRG)
**Testing**: pytest (ATDD: failing acceptance test first), with parity/byte-identity tests
for the dispatch aliases (NFR-001), idempotency tests for follow-up dedup, a deterministic-
regen + orphan-count regression for the DRG. `pytest tests/architectural/` is the safety net;
`tests/architectural/test_no_legacy_terminology.py` is a pre-push gate for doctrine/prose.
**Target Platform**: Linux/macOS developer + CI environments (spec-kitty CLI)
**Project Type**: single (CLI tool — `src/specify_cli/`, `src/doctrine/`, `tests/`)
**Performance Goals**: N/A (correctness/determinism mission, not perf-sensitive)
**Constraints**: behavior-preserving for alias surfaces (byte/contract-identical Op records);
fail-closed over silent fallback for lifecycle surfaces; deterministic + no-op-stable graph
regen; ruff + mypy `--strict` zero-new-issue; terminology canon (`spec-kitty dispatch`,
`Mission`); the dispatch collapse must never break `spec-kitty do --profile …` (C-002)
**Scale/Scope**: 3 independent workstreams, ~8–10 implementation concerns; additive (not a
bulk-edit/occurrence-map mission)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter context loaded (`charter context --action plan`, mode=compact; template set
`software-dev-default`, directives DIR-001..DIR-013, tools git/mypy/pytest/ruff/spec-kitty).
Relevant gates and how this plan satisfies them:

- **Shared Package Boundary** (ADR 2026-04-25-1): `spec_kitty_events` is an external contract
  consumed via public imports only. **Satisfied** — workstream A is local-first; no external
  package edits, SaaS fan-out is best-effort/off-critical-path (research C-SAAS).
- **Terminology Canon**: `Mission` (not feature), `spec-kitty dispatch` (not a forbidden
  alias-of-a-banned-term). **Satisfied** — run the terminology guard before pushing the
  doctrine/prose touches in workstreams B/C.
- **Canonical sources, never improvise** (DIR): DRG edits go through SOURCE doctrine YAML +
  `regenerate-graph`; dispatch propagation (if any) via SOURCE templates + migration, never
  hand-edited agent copies (C-004). **Satisfied** by design (D-B4, D-C1).
- **Tiered rigour / fail-closed**: lifecycle surfaces resolve through declared authorities
  (`mission_id`, git registry), never name-derived guesses (NFR-004). **Satisfied** (D-A4).

- **Recently-merged surface check (SC-5):** lane A changes `status/lifecycle.py`
  (`derive_mission_lifecycle` classification + `lifecycle.json` shape) and `status/views.py`.
  A tasks-phase sub-task must confirm these do not collide with the just-merged #1908/#1910
  coordination/status-surface work or the WP-lane FSM `State` pattern (run the architectural
  suite; diff the touched surfaces against those PRs). Recorded here so the check is not lost.

No charter violations requiring Complexity Tracking.

## Project Structure

### Documentation (this mission)

```
kitty-specs/mission-lifecycle-dispatch-drg-closeout-01KV0S99/
├── plan.md              # This file
├── research.md          # Phase 0 — consolidated findings + decisions
├── data-model.md        # Phase 1 — new lifecycle event payloads + dedup keys
├── quickstart.md        # Phase 1 — validation scenarios per workstream
├── contracts/           # Phase 1 — dispatch parity + reopen/follow-up + DRG regen contracts
├── issue-matrix.md      # Closure ledger (#1802/#1804/#1810/#1863)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── status/
│   ├── lifecycle_events.py     # A: add MissionReopened/FollowUpRecorded to LIFECYCLE_EVENT_TYPES + __all__ + emit helpers (kept off SaaS strict path)
│   ├── store.py                # A: back-compat read verification — new event-type envelopes round-trip as reducer-skipped
│   ├── lifecycle.py            # A: derive_mission_lifecycle HONORS MissionReopened as authority (new `reopened` surface_state) + surface post_mission_events
│   └── views.py                # A: render post-mission events in the lifecycle/history view
├── mission_metadata.py         # A: reopen clears merged_* metadata; follow-up attribution by mission_id
├── cli/commands/
│   ├── mission_type.py         # A: extend the existing `spec-kitty mission` group with `reopen` + `follow-up` subcommands (mission.py is the shim)
│   ├── do_cmd.py               # B: collapse into shared _dispatch_impl (alias)
│   ├── advise.py               # B: collapse into shared _dispatch_impl (advise + ask aliases)
│   ├── dispatch.py (new)       # B: canonical `spec-kitty dispatch` + shared _dispatch_impl
│   └── __init__.py             # B: register `dispatch`; keep do/ask/advise registrations
├── invocation/modes.py         # B: add `dispatch` entry to _ENTRY_COMMAND_MODE
└── upgrade/migrations/         # B: (conditional) migration to propagate dispatch to agent surfaces

src/doctrine/
├── styleguides/built-in/java-conventions.styleguide.yaml  # C: repaint java-implementer → java-jenny
├── (tactics/toolguides/styleguides referenced by orphan triage)  # C: wire inbound edges or document
└── graph.yaml                  # C: regenerate deterministically (generated artifact)

tests/
├── specify_cli/invocation/cli/test_dispatch_parity*.py     # B: NFR-001 byte/contract parity
├── status/test_post_mission_lifecycle*.py                  # A: reopen/follow-up + idempotency
├── cli/commands/test_mission_reopen*.py / test_mission_follow_up*.py  # A: command surface
└── specify_cli/cli/commands/test_doctrine_regenerate_graph.py  # C: orphan-count regression pin
```

**Structure Decision**: Single-project CLI layout. Three workstreams map to disjoint module
trees (`status/`+`cli/commands/mission*` ; `invocation/`+`cli/commands/{do,ask,advise,dispatch}` ;
`src/doctrine/`), so `owned_files` partition cleanly with no cross-lane overlap.

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.
> Three independent lanes (A/B/C). ATDD applies throughout: the failing acceptance test for
> each closing behavior is authored first (NFR-005).

### IC-01 — Lifecycle event types, emit helpers & re-open-aware classification (A)

- **Purpose**: Add `MissionReopened` and `FollowUpRecorded` to the lifecycle event stream
  with emit helpers, AND make `derive_mission_lifecycle` honor `MissionReopened` as the
  authority so a re-opened mission actually reads as actionable (the crux of FR-002).
- **Relevant requirements**: FR-001, FR-002, NFR-002, NFR-004, NFR-005
- **Affected surfaces**: `status/lifecycle_events.py` (register both constants in
  `LIFECYCLE_EVENT_TYPES` **and** `__all__` — `append_lifecycle_event` hard-drops
  unregistered types; add `_build_envelope`-based emit helpers + dedup), `status/store.py`
  (read back-compat — new envelopes round-trip as reducer-skipped), `status/lifecycle.py`
  (`derive_mission_lifecycle` / `_classify_state`: a `MissionReopened` postdating the last
  merge/completion marker forces a new `reopened` surface_state / actionable result until a
  subsequent merge re-stamps).
- **Sequencing/depends-on**: none (lane-A foundation)
- **Risks**: **(verified BLOCKING in review)** `_classify_state` is currently a pure function
  of WP-lane counts + age and never reads `merged_*` or events — clearing `merged_*` alone is
  a no-op, so re-open MUST drive classification via the event. Reducer must keep skipping
  lifecycle events (it discriminates on `event_type` presence — confirm with a round-trip
  test). Dedup key `(mission_id, commit_sha|pr_number)`. **SaaS boundary:** keep the two new
  types OFF the SaaS strict-validation path (`_validate_lifecycle_payload(strict=True)` would
  raise if/when the external `spec_kitty_events` learns them) — they are local-only this
  mission; SaaS propagation needs an external contract bump (follow-up, not in scope).
  `MissionReopened` is append-each; sort `post_mission_events` by `(timestamp, event_id)` for
  byte-stable `lifecycle.json`.

### IC-02 — Mission re-open + follow-up command surface (A)

- **Purpose**: `spec-kitty mission reopen <id> --reason …` (clears `merged_*`, records actor,
  fail-closed if branch/worktree unrecoverable) and `spec-kitty mission follow-up <id>
  --commit <sha>|--pr <n>` (attribute to `mission_id`, any state, idempotent).
- **Relevant requirements**: FR-001, FR-002, FR-003, NFR-002, NFR-004
- **Affected surfaces**: `cli/commands/mission_type.py` (extend the existing `spec-kitty
  mission` group — `mission.py` is its shim — with `reopen` + `follow-up`), `mission_metadata.py`
  (clear `merged_*` on reopen; handle→`feature_dir` resolution by `mission_id`/`mid8`/slug),
  `status/views.py` (render `post_mission_events`). The classification change lives in IC-01
  (`lifecycle.py`); IC-02 only **renders** — so the two ICs do not both edit `lifecycle.py`'s
  classifier (owned-files note for tasks).
- **Sequencing/depends-on**: IC-01
- **Risks**: re-open must NOT cascade WP lane edits (D-A2) — actionability comes from the
  IC-01 classification change, not a lane edit; resolve via `mission_id`+git registry, never
  slug guess. The handle resolver (`mid8`/slug → `feature_dir`, ambiguity →
  `MISSION_AMBIGUOUS_SELECTOR`) is a named net-new helper, not assumed to pre-exist.

### IC-03 — #1802 closure (A)

- **Purpose**: confirm FR-001/FR-002 deliver #1802's epic scope; if any residual remains,
  split it into a fresh scoped child ticket so #1802 closes honestly.
- **Relevant requirements**: FR-003
- **Affected surfaces**: issue-matrix.md; tracker (#1802)
- **Sequencing/depends-on**: IC-02
- **Risks**: scope creep — re-open WP-cascade and merge-policy knobs are explicitly deferred.

### IC-04 — Dispatch mechanism unification + canonical command (B)

- **Purpose**: extract the duplicated CLI helpers into one `_dispatch_impl`; add canonical
  `spec-kitty dispatch`; make `do`/`ask`/`advise` thin aliases over it (kept first-class).
- **Relevant requirements**: FR-004, FR-005, NFR-002
- **Affected surfaces**: `cli/commands/dispatch.py` (new), `do_cmd.py`, `advise.py`,
  `cli/commands/__init__.py`, `invocation/modes.py`
- **Sequencing/depends-on**: none (lane-B foundation)
- **Risks**: **C-002** — aliases land in the same change; never a window where the trio is
  broken. Preserve each verb's exact argument shape (ask positional profile, advise advisory).

### IC-05 — Dispatch parity pinning (B)

- **Purpose**: prove `do`/`ask`/`advise`/`dispatch` produce byte/contract-identical Op records
  + JSON envelopes + exit codes (before/after).
- **Relevant requirements**: NFR-001, FR-005
- **Affected surfaces**: `tests/specify_cli/invocation/cli/test_dispatch_parity*.py`
- **Sequencing/depends-on**: IC-04 (can be authored test-first alongside)
- **Risks**: must assert mode mapping (do/ask/dispatch→task_execution, advise→advisory) and
  identical Op-record JSONL shape.

### IC-06 — Dispatch propagation to the canonical command-skill (B)

- **Purpose**: add `dispatch` to the **single** generated command-skill that documents the
  trio (`src/doctrine/skills/spec-kitty.advise/SKILL.md`) and refresh the manifest +
  skill-routing prose, so all configured agents get `dispatch` via the canonical install path.
- **Relevant requirements**: FR-006, NFR-002, C-004
- **Affected surfaces**: `src/doctrine/skills/spec-kitty.advise/SKILL.md` (SOURCE),
  `.kittify/command-skills-manifest.json` (hash refresh via the skills install path), and the
  skill-routing prose that names the trio. **Verified:** there is exactly ONE generated skill
  for do/ask/advise (no per-agent hand-maintained copies, no separate `do`/`ask` skills) — so
  this is NOT a "19-way" edit. Never hand-edit agent copies (C-004).
- **Sequencing/depends-on**: IC-04
- **Risks**: keep scope to the one skill + manifest; do not fabricate a per-agent surface.

### IC-07 — #1804 closure (B)

- **Purpose**: with #1810 delivered, verify epic #1804 is substantially complete and close it;
  note genuine refinements (not gaps) as out-of-scope follow-ups.
- **Relevant requirements**: FR-007
- **Affected surfaces**: issue-matrix.md; tracker (#1804, #1810)
- **Sequencing/depends-on**: IC-04, IC-05, IC-06
- **Risks**: none beyond honest scoping.

### IC-08 — DRG stale-reference repair (C)

- **Purpose**: repaint `java-conventions.styleguide.yaml` `references` from the non-existent
  `java-implementer` to the real `java-jenny`; sweep + repair other same-class stale refs.
- **Relevant requirements**: FR-008, NFR-002
- **Affected surfaces**: `src/doctrine/styleguides/built-in/*.yaml` (+ any other stale-ref
  source files surfaced by the sweep)
- **Sequencing/depends-on**: none (lane-C foundation)
- **Risks**: distinguish a *stale reference* (fix) from a *valid unreferenced artifact*
  (do NOT touch the artifact here — that's IC-09). Sweep predicate is precise: a `references`
  path whose pattern matches a doctrine kind **AND** whose target file is absent on disk
  (the extractor mints a phantom node for exactly these); do not repaint live references.

### IC-09 — Orphan triage: wire or document (C)

- **Purpose**: for each genuinely-orphaned valid artifact, **wire a real inbound edge** when a
  natural referent exists, else **document it as an accepted residual** with rationale.
  Individually-justified prunes only for genuinely-retired artifacts — never bulk-delete.
- **Relevant requirements**: FR-009, NFR-002, C-003
- **Affected surfaces**: `src/doctrine/` referent artifacts (directives/procedures that should
  cite a tactic/toolguide), residual-doc in-mission
- **Sequencing/depends-on**: IC-08
- **Risks**: **content-destruction risk** — the research's "prune 18" recommendation is
  rejected (D-C2); default to wire-or-document.

### IC-10 — Deterministic regen + orphan-count regression + #1863 closure (C)

- **Purpose**: regenerate `graph.yaml` deterministically; pin the reduced orphan count as a
  regression; document residual + file a curation follow-up if non-empty; close #1863.
- **Relevant requirements**: FR-008, FR-009, NFR-003, C-003
- **Affected surfaces**: `src/doctrine/graph.yaml`,
  `tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py`; tracker (#1863)
- **Sequencing/depends-on**: IC-08, IC-09
- **Risks**: NFR-003 already satisfied (deterministic emit) — pin it, don't re-architect it.

### IC-11 — Type-safety boyscout: `status/` package mypy --strict clean (cross-cutting, opportunistic)

- **Purpose**: clear the pre-existing `mypy --strict` debt on the `status/` package the lifecycle
  work builds on, so `mypy --strict src/specify_cli/status/` exits 0 (SC-6). Surface scan found 20
  strict errors in `status/`, 0 in `invocation/`. WP01 clears its own `lifecycle_events.py` (3) and
  WP02 its own `views.py` (1) under NFR-002 (boy-scout touched paths). The **17 adjacent un-owned**
  errors (`emit.py` 10, `aggregate.py` 4, `__init__.py` 2, `progress.py` 1) are cleared by a
  dedicated, behavior-preserving boyscout WP that does NOT overlap any feature WP's owned files.
- **Relevant requirements**: NFR-002, SC-6
- **Affected surfaces**: `src/specify_cli/status/emit.py`, `aggregate.py`, `__init__.py`, `progress.py`.
- **Sequencing/depends-on**: none (independent; no file overlap with WP01/WP02).
- **Risks**: `emit.py` is critical-path (the status-event emit pipeline) — fixes MUST be
  type-only/behavior-preserving (no logic change), pinned by the existing status suite. Scope is
  bounded to `status/`; do NOT expand into a project-wide mypy crusade (charter/doctrine debt is
  out of scope). Sonar is not locally assessable for this branch — finding is mypy-only.
