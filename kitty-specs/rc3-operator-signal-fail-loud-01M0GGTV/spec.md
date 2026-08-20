# Mission Specification: M4 — Operator-signal / fail-loud sweep

**Mission Branch**: `[TBD-operator-signal-fail-loud-sweep]`
**Created**: 2026-08-20
**Status**: Draft (LIGHT spec — specify-phase only; NOT finalized). Operator decisions resolved 2026-08-20 — see Resolved Decisions.
**Input**: Author a single fail-loud sweep spec, one of eight feeding a single-branch pre-rc2 PR. Establish the operator-signal / fail-loud discipline (vocabulary owned by epics #3410 and #3549) and apply it to six concrete silent sites.

---

## Problem & Impact (BLUF)

Across the tooling there is a recurring defect **class**, not a set of unrelated bugs: a code path **decides correctly** and the interface **says nothing**. The machine-readable half of a contract stays intact (correct `error_code`, byte-stable file, truthy return) while the human-readable half — the sentence that tells an operator what happened and what to do — is dropped, discarded, or never emitted. Epic #3410 names this for the charter/doctrine layer ("silent-success / silent-drop … fake-green"); epic #3549 names it for the event pipeline ("silent false success on mission state"). This mission does **not mint a new term** — it adopts that existing vocabulary and applies the **operator-signal / fail-loud** discipline to six ground-level sites where the signal is currently invisible.

Impact: operators cannot distinguish a genuine failure from a wrong-layout/wrong-subsystem one (#3548 — the drop preferentially silences the *most* actionable errors); a reviewer-rejected work package refuses re-review with no clue why (#3578); an author believes traceability exists when the reference was discarded (#2991); a corrupt manifest reports as "not found" (#3412); a durably-unqueued event is still eligible for downstream publication (#3517); a decomposition authors a work package that cannot honestly terminate and nothing warns at authoring time (#3590 interim). Each is invisible to tests that assert only on codes, payload shape, or byte-stability — so the suite is green while the operator is blind.

## In Scope

- **Establish the discipline as this mission's organising contract** — cite epic #3410 (charter/doctrine silent-drop) and epic #3549 (event-log integrity) for the vocabulary. Adopt, do not rename. **Author an operator-signal-contract DIRECTIVE** codifying "a path that decides must also signal", placed in the **spec-kitty-internal** dogfooding pack (see Directive Provenance below) — NOT `packs/built-in` (which ships to consumers).
- **#3578** — the rollback subtask-reset is invisible: emit a `subtasks_reset_count` operator signal (both a human-readable line AND a JSON field) via `_mt_output` (`tasks_move_task.py`; reset performed by `_mt_rollback_subtasks_reset` at `:2102`, called `:2184`). Also surface the **two co-located silent siblings** applied in the same delta: `release_runtime_claim=True` (`:2187`) and the review-override clear (`_build_claim_review_override`, `:2140`/`:2263`). **AND separate work-state from review-state in the subtask roster NOW**: a subtask genuinely completed in an earlier cycle and untouched by the current cycle's findings must be distinguishable from one never started (the "secondary consequence" in #3578) — this is in scope, not deferred.
- **#3590 — INTERIM ONLY.** Add an **authoring-time warning** when a work package's acceptance criteria are observable only *post-integration* (an action, not a diff). Net-new **prose detector**; hook into the finalize bootstrap loop at `mission_finalize.py:~1253` where `infer_warnings` are already collected and surfaced. Warn-only, non-blocking. **Does NOT touch terminal states.**
- **#3548** — `_fail()` drops `message` whenever `data` is passed (`orchestrator_api/commands.py:230`, `data or {"message": message}`); 16 of 33 call sites lose their explanation. Merge message into the payload so both halves reach the operator.
- **#3517** — `_emit` discards `_route_event`'s `bool` (`sync/emitter.py:2353`); an event that never landed in the durable outbox is still returned truthy and remains publication-eligible at the 9 gated call sites in `sync/events.py`. Consume the bool (or record via the existing `_record_capture_failure` surface) so failure is legible. **This mission owns only the `_route_event`-bool signal residual, not the bounded-retry redesign** (that stays with #3549's sync owners).
- **#3412** — a YAML-syntax-malformed `expected-artifacts.yaml` degrades to `None`, identical to "absent" (`src/doctrine/missions/repository.py:316-317` catches `(OSError, UnicodeDecodeError, YAMLError)` → `None`). Let it fail loud, distinct from absence.
- **#2991** — `finalize-tasks` silently drops `SC-###` from `requirement_refs`; the scanner alternation is `(?:FR|NFR|C)-\d+` (`requirement_mapping.py:15-16`, `mission_parsing.py:108`), so `SC-` is outside the graph by construction. Warn on discard when SC is not admitted as a first-class ref (per resolved decision (c)).

## Out of Scope (defer / reference only)

- The **deep WP terminal-state fix** — Mission **M6** / epic **#3550** / issues **#3432 / #3433 / #2745**. The #3590 work here is the **interim authoring-time warning only** and explicitly does **not** add, alter, or reach any terminal state, `accept`/`merge` gate, or lane-model exit. If the detector fires, its remedy is a warning telling the author to re-home the content at planning time — nothing more.
- The **#3517 bounded-retry-past-`busy_timeout`** redesign (residual 1) — stays with #3549 sync owners; M4 takes only the `_route_event` bool-discard (residual 2).
- The **#3548 error-taxonomy / envelope-schema** redesign — M4 does the one-line merge, not a contract rework.
- Any change to `error_code` values, lane state machine, or event schema.

## Requirements

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Rollback reset signal (line + JSON) | As an operator rejecting a WP to `planned`, I want both a visible line AND a `subtasks_reset_count` JSON field stating N subtasks were reset, so I re-mark them before returning to review. | High | Open |
| FR-002 | Co-located siblings surfaced | As an operator, I want the `release_runtime_claim` and review-override clear applied in the same rollback delta to be operator-visible, not silent. | Medium | Open |
| FR-003 | Roster work-state / review-state split | As an operator, I want the subtask roster to distinguish a subtask genuinely completed in an earlier cycle (and untouched by current findings) from one never started, so rollback does not conflate work-state with review-state. | High | Open |
| FR-004 | Post-integration AC detector (interim, warn-only) | As an author running finalize, I want a warn-only, non-blocking notice when a WP's acceptance criteria are observable only after integration; it MUST NEVER block finalize. | High | Open |
| FR-005 | `_fail` preserves message | As an operator hitting an orchestrator-api refusal, I want the human-readable message AND the structured `data` in the envelope, never one at the cost of the other. | High | Open |
| FR-006 | `_route_event` bool consumed (bool-discard only) | As a sync/mission operator, I want an event that failed to queue durably to be legible as failed, not returned truthy and published downstream. Bound to the bool-discard residual only — no retry redesign. | High | Open |
| FR-007 | Malformed manifest fails loud | As an operator debugging a mission, I want a YAML-syntax-broken `expected-artifacts.yaml` to fail loud, distinct from "not found". | High | Open |
| FR-008 | SC-### discard is signalled | As a spec author, I want `finalize-tasks` to warn (or record) when an `SC-###` ref is discarded, so I never believe traceability exists when it does not. | High | Open |
| FR-009 | Operator-signal-contract directive | As a maintainer, I want a directive in the spec-kitty-internal pack codifying "a path that decides must also signal", so future authors have a named contract to cite. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No new silence | Every site fixed emits through an existing operator-visible surface (`_mt_output`, `infer_warnings`, envelope, capture-failure registry); no new sink that can itself be swallowed. | Reliability | High | Open |
| NFR-002 | Non-blocking interim | FR-003 is warn-only; finalize exit code and success path are unchanged when the detector fires. | Reliability | High | Open |
| NFR-003 | Contract preservation | FR-004/FR-005 change no `error_code` value and no `emit_*` signature; `_emit`'s never-raise contract holds. | Compatibility | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Vocabulary reuse | Use epic #3410 / #3549 "fail-loud / silent-drop" vocabulary; do NOT mint a new term. | Doctrine | High | Open |
| C-002 | Interim boundary | #3590 work touches NO terminal state, gate, or lane exit — authoring-time warning only, never blocks finalize. | Technical | High | Open |
| C-003 | Red-first repro | Each site lands an issue-pinned red-first regression per ADR 2026-07-17-1 (per epic #3410). | Technical | High | Open |
| C-004 | Directive placement | FR-009's directive lands in the `spec-kitty-internal` pack (`packs/internal/`), registered via `packs/internal/drg/fragment.yaml`; it MUST NOT land in `packs/built-in` (ships to consumers). | Doctrine | High | Open |

## Success Criteria

- **SC-001**: Each of the six sites emits an operator-visible signal that a test asserts on directly (not merely a code/shape assertion) — six new signals, six new focused tests.
- **SC-002**: A rollback-to-`planned` prints a `subtasks_reset_count` line, emits the same count as a JSON field, and names the two sibling actions; re-running the reported recovery clears the refusal.
- **SC-003**: After a reject/re-implement cycle, the roster distinguishes a subtask completed in an earlier cycle and untouched by current findings from one never started — a test asserts the two are not conflated.
- **SC-004**: The #3590 detector fires on a known post-integration WP fixture (warn-only) and does NOT fire on a normal code-bearing WP fixture (false-positive control), with finalize exit code and success path unchanged in both.
- **SC-005**: An orchestrator-api `_fail` with `data` yields an envelope carrying both the message and the payload; a YAML-syntax-broken manifest raises rather than returning `None`; an `SC-###` ref produces a warning/record rather than vanishing.
- **SC-006**: The operator-signal-contract directive exists in `packs/internal/`, is registered in the DRG fragment, and `spec-kitty doctor doctrine --json` reports the internal pack healthy (no skipped/inert artifact).

## Key Design Decisions

- **This is a sweep, not a framework.** Per operator decision it is ONE sweep across six sites; the unifying artifact is the shared *discipline* (already owned by #3410/#3549), applied site-by-site through each site's existing signal surface. It ALSO ships a standalone operator-signal-contract **directive** (FR-009) — placed in the `spec-kitty-internal` dogfooding pack, not `packs/built-in` — so the discipline is a citable named contract for maintainers without shipping governance to consumers.
- **Reuse existing surfaces.** `_mt_output` (already the reader of the approval no-op guard marker, `:258`), `infer_warnings` (already collected/surfaced in the finalize bootstrap loop), the orchestrator-api envelope, and the `_record_capture_failure` registry are all pre-existing operator-visible sinks. No new signalling mechanism.
- **#3590 is a heuristic prose detector** — net-new, precision-sensitive; scoped warn-only, non-blocking, precisely because a heuristic must not block (resolved decision (b); see Risks).

## Resolved Decisions (operator, 2026-08-20)

- **(a) #3578 signal shape + roster split** — RESOLVED: emit the operator signal **line + JSON field** (`subtasks_reset_count`) via `_mt_output` **AND** separate work-state from review-state in the subtask roster **NOW** (not deferred), so an earlier-cycle-completed subtask is distinguishable from a never-started one. Also surface the two co-located siblings (`release_runtime_claim`, review-override clear). → FR-001, FR-002, FR-003; SC-002, SC-003.
- **(b) #3590 interim detector** — RESOLVED: **warn-only, non-blocking**; never blocks finalize. → FR-004; NFR-002; C-002; SC-004.
- **(c) Sweep set** — RESOLVED: **keep all six** sites (#3578, #3590-interim, #3548, #3517, #3412, #2991); **bind #3517 to the bool-discard residual only** (no retry redesign — stays with #3549). → FR-006; Out of Scope.
- **(d) Directive** — RESOLVED: **author** the operator-signal-contract directive, placed in the **`spec-kitty-internal`** dogfooding pack (NOT `packs/built-in`). → FR-009; C-004; Directive Provenance.

## Directive Provenance (FR-009 target)

The internal/dogfooding doctrine pack exists on `main`:

- Pack root: **`packs/internal/`** — `org_name: spec-kitty-internal` (`packs/internal/org-charter.yaml`).
- DRG fragment: **`packs/internal/drg/fragment.yaml`** — `pack_name: spec-kitty-internal`, `provenance_marker: org`, `layer_index: 1`. New artifacts register as `nodes:` entries here.
- Existing kind subdirs: `procedures/`, `glossary_packs/`, `drg/`. **No `directives/` dir exists yet** — FR-009 introduces `packs/internal/directives/<slug>.directive.yaml` and adds a matching `nodes:` entry (`kind: directives`) to the fragment. (Built-in convention is `NNN-slug.directive.yaml`; the internal pack has no directive number sequence, so plan proposes a descriptive slug, e.g. `operator-signal-contract.directive.yaml` — final name is a plan-phase detail.)
- **Provenance flag for the orchestrator**: the directory and DRG-node wiring are net-new; confirm at plan time that a `directives`-kind node resolves through the internal fragment's DRG the same way `procedures`/`glossary_packs` do (verify via `spec-kitty doctor doctrine --json`, SC-006). No blocker found — the pack and fragment mechanism are present and healthy.

## Risks

- **Heuristic false positives (#3590)** — a prose detector over acceptance criteria will misfire; mitigated by warn-only + a false-positive control fixture (SC-003). Chief residual risk of the mission.
- **Scope breadth** — sites span orchestrator-api, sync, doctrine/missions, and tasks; a regression in one is unrelated to the others. Mitigated by per-site red-first regressions (C-003) and the C3 split fallback.
- **Signal-into-a-swallowed-sink** — surfacing a signal through a path that is itself silenced (e.g. #3548's own drop) would be self-defeating; NFR-001 requires an already-operator-visible surface per site.
- **Interim/deep-fix drift** — the #3590 interim must not pre-empt or contradict M6's terminal-state design; C-002 fences it to authoring-time warning only.

## Issues

- **In scope**: #3578 (rollback reset signal + siblings), #3590 (INTERIM authoring-time warning only), #3548 (`_fail` message drop), #3517 (`_route_event` bool discard — residual 2 only), #3412 (malformed manifest → None), #2991 (finalize-tasks drops `SC-###`).
- **Vocabulary / epics**: #3410 (charter/doctrine silent-drop, fail-loud), #3549 (event-log integrity).
- **Deferred to M6**: #3432, #3433, #2745 (and epic #3550) — deep WP terminal-state fix; the #3590 interim explicitly does NOT touch terminal states.
