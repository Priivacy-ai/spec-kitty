# Mission Specification: Charter Activation Empty-Action-Sequence Gate

**Mission Branch**: `fix/charter-activate-empty-action-sequence-3702`  
**Created**: 2026-08-24  
**Status**: Draft  
**Input**: [GitHub issue #3702](https://github.com/Priivacy-ai/spec-kitty/issues/3702)

## Intent Summary

`spec-kitty charter activate mission-type <T>` currently succeeds — exit 0,
"Activated: `<T>`" — for a mission type whose resolved action sequence is
empty, and writes `<T>` into `.kittify/config.yaml`'s
`mission_type_activations`. The project is now permanently activated onto a
type that can plan nothing: every later governed entry point that resolves
that type (`agent mission create --mission-type <T>`, `charter activate`
itself on any subsequent call, even the unrelated `charter mission-type
list`) then fails with `mission type` `` `<T>` `` `resolved from layer` ``
`<layer>` `` `has an empty action sequence.` This is the repo's dominant
failure mode (silent success followed by a hard brick, #3133/#3212/#3282/
#3336) reproduced in a new specimen: the read-path check that would have
caught this
(`charter/mission_type_profiles.py::_resolve_action_slot`, its
empty-sequence guard) never runs during activation, because activation is
the one call where the candidate type is by definition **not yet**
registered, and that function short-circuits to an empty list — silently
skipping its own guard — for any unregistered candidate. This mission adds
a fail-closed check on the activation path itself so an empty-sequence type
is refused before `mission_type_activations` is ever mutated, instead of
being accepted and bricking the project on the next call.

## Provenance

Reported as GitHub issue #3702, first verified in ledger entry SK-81
(2026-08-23) and re-verified first-hand during this spec's authoring against
the current checkout, using the natural operator path described below (see
Edge Cases). `Closes #3702` belongs in the eventual PR body, not this spec;
it is noted here only as a mission fact.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Activation refuses an unusable mission type instead of bricking the project (Priority: P1)

As a spec-kitty operator, after I declare an org-tier doctrine pack whose
`mission_types/<T>.yaml` has no `action_sequence` (and no `extends` that
would supply one), I run `spec-kitty charter activate mission-type <T>`. I
want the command to refuse — report the same kind of error the read path
already reports for an *activated* empty-sequence type, exit non-zero, and
leave `.kittify/config.yaml` untouched — rather than report success and
leave my project permanently activated onto a type nothing can use.

**Why this priority**: This is the mission's entire reason for existing.
Without this fix, the only path back to a healthy project after a run-1
success is manually editing `mission_type_activations` back out of
`.kittify/config.yaml` — the CLI itself gives the operator no way out, since
every governed entry point that would normally help (including
`charter activate` on the very type that needs deactivating) is bricked by
the same guard the fix must move earlier.

**Independent Test**: Using the **natural operator path** — declare an org
pack that defines `mission_types/<T>.yaml` with no `action_sequence` and no
`extends`, and do **not** pre-seed `<T>` into `mission_type_activations` —
run `spec-kitty charter activate mission-type <T>` exactly once. The command
must exit non-zero, print an error naming `<T>` and the resolving layer, and
`.kittify/config.yaml`'s `mission_type_activations` must not contain `<T>`
(and must otherwise be byte-identical to its pre-command state). A second
run of the same command must behave identically to the first — there is no
"run 2 now catches it" difference, because run 1 never wrote anything.

**Acceptance Scenarios**:

1. **Given** an org-tier pack declaring mission type `<T>` with no
   `action_sequence` and no `extends`, and `<T>` absent from
   `mission_type_activations`, **When** the operator runs
   `spec-kitty charter activate mission-type <T>`, **Then** the command exits
   non-zero, reports an error naming `<T>` and the resolving layer (`org`),
   and `mission_type_activations` does not gain `<T>`.
2. **Given** the same precondition, **When** the operator inspects
   `.kittify/config.yaml` after the failed activation attempt, **Then** the
   file is unchanged from its pre-command state (no partial write, no other
   key mutated).
3. **Given** an org-tier pack declaring mission type `<T>` with a non-empty
   `action_sequence`, **When** the operator runs
   `spec-kitty charter activate mission-type <T>`, **Then** activation
   succeeds exactly as it does today (no regression to the healthy path).
4. **Given** a type `<T>` that resolves an action sequence only through a
   single-level `extends` chain to a parent with a non-empty sequence,
   **When** the operator activates `<T>`, **Then** activation succeeds (the
   new check honors the same `extends` fallback the read path already
   honors, it does not re-derive a stricter rule).

---

### User Story 2 - The existing read-path error is unchanged for an already-activated type (Priority: P2)

As a spec-kitty operator who activated a type before this fix shipped (or
whose config was edited directly), I still want every later governed entry
point that resolves an already-registered, empty-sequence mission type to
fail loudly with the existing, well-understood error — this mission must
not weaken, relocate, or duplicate that behavior while closing the
activation-time gap.

**Why this priority**: The read-path guard (`_resolve_action_slot`'s
empty-sequence check) is correct, pre-existing, and load-bearing for every
other caller of `resolve_mission_type_context` (mission creation, mission
type listing, etc.). The fix for #3702 must add a new gate on the
activation write path without touching the read path's `is_registered`
short-circuit, which other callers still depend on to resolve a genuinely
unregistered type to an empty sequence rather than raising.

**Independent Test**: With `<T>` already present in
`mission_type_activations` and resolving to an empty action sequence (the
pre-seeded state SK-81 warned against treating as the primary repro),
confirm `charter mission-type list` and `charter activate mission-type <T>`
still raise the existing `MissionTypeEmptyActionSequenceError`-shaped error,
unchanged in wording, after this mission's fix lands.

**Acceptance Scenarios**:

1. **Given** `<T>` already registered in `mission_type_activations` and
   resolving to an empty action sequence, **When** the operator runs
   `charter mission-type list`, **Then** the command still fails with the
   same error it fails with today (naming `<T>` and its resolving layer),
   unchanged by this mission.
2. **Given** the same precondition, **When** any other caller of
   `resolve_mission_type_context` resolves a genuinely unregistered type
   (not `<T>`), **Then** that call still degrades to an empty action
   sequence without raising, exactly as today (the `is_registered`
   short-circuit at the top of `_resolve_action_slot` is not moved or
   altered by this mission).

### Edge Cases

- **The pre-seeded-vs-natural-path trap (methodological note, binding on
  this mission's own tests as well as on the spec).** Two prior
  observations of this defect — a correspondence lens and a prior mission's
  spec author — recorded `charter activate mission-type <T>` as *already
  failing* against the unmodified pack. Both reached that conclusion by
  **pre-seeding** `<T>` into `mission_type_activations` before calling
  activation, to isolate the failure from a separate, unrelated
  roster-membership check. Under that precondition the command genuinely
  does fail today — `is_registered` is already `True` before the call, so
  the existing read-path guard fires and the command never gets a chance to
  demonstrate the actual defect. Under the precondition a real operator
  actually has — the documented order is declare the pack, then activate,
  with the type starting **absent** from `mission_type_activations` — the
  command succeeds and bricks the project; that is the real defect this
  mission closes. Both observations were individually correct; generalizing
  from the pre-seeded one to "this already fails" was not. Any acceptance
  test, and any regression test written during implementation, MUST use the
  natural (not-pre-seeded) precondition: declare the org pack, leave `<T>`
  out of `mission_type_activations`, then call activation. A test that
  pre-seeds the activation set before calling the command under test would
  pass even with zero code changed, and must not be accepted as coverage
  for this mission's fix. **Required fixture shape**: two calls, not one.
  Author `<T>`'s org-pack YAML with
  `_write_layered_mission_type_yaml(org_root / "mission_types", "<T>.yaml",
  "<T>", action_sequence=None)`
  (`tests/charter/test_mission_type_profiles.py:449`) — this is the only
  helper in the file that writes `mission_types/<T>.yaml` itself.
  Separately, author `.kittify/config.yaml` with `_write_org_pack_config`
  (`tests/charter/test_mission_type_profiles.py:846`), called with `<T>`'s
  org pack declared via `packs`, but with `activated_mission_types`
  *omitting* `<T>` — every existing call site in that file populates both
  lists together, which is exactly the pre-seeding trap; do not follow that
  convention here — or an equivalent pair of fixtures with the same shape.
  `_write_org_pack_config` itself only ever writes `.kittify/config.yaml`;
  it never creates the mission-type YAML, so relying on it alone is not
  sufficient to construct the fixture. Assert `<T>` is absent from
  `mission_type_activations` immediately before invoking
  `charter activate mission-type <T>`.
  **Extends-fallback fixture gap (AC4/FR-005)**: as of this writing,
  `_write_layered_mission_type_yaml` has no `extends` parameter, and no
  test in `tests/charter/test_mission_type_profiles.py` exercises
  `extends` at all (zero matches for the string in the file). Acceptance
  Scenario 4 and FR-005 require an extends-chain fixture (candidate's own
  sequence empty, `extends` resolves a non-empty parent) for which there is
  currently no helper or precedent — the plan phase MUST size and schedule
  either widening `_write_layered_mission_type_yaml` with an
  `extends: str | None` parameter or adding a sibling helper before AC4
  coverage can be written; this is not implicit follow-on work.
- What happens when the candidate type's own `action_sequence` is empty but
  it declares `extends` to a parent with a non-empty sequence? Activation
  must succeed — the activation-time check resolves the same
  `extends`-fallback the read path already honors; it is not a stricter,
  independently-derived rule.
- What happens when the candidate type's own `action_sequence` is empty and
  its `extends` parent (if any) is itself unresolvable or also empty?
  Activation must refuse, naming the candidate type's own id and its own
  resolving layer (not the unresolvable parent's).
- What happens when the candidate type id has no resolvable YAML definition
  in any layer at all (a different configuration inconsistency from "empty
  sequence")? That case is already governed by `UnknownMissionTypeError` on
  the read path; this mission's activation-time check must not weaken or
  bypass that existing behavior, whichever check the type trips first.
- What happens on a built-in mission type? Built-in types always resolve a
  non-empty action sequence by construction (locked by
  `tests/runtime/test_runtime_seam.py`'s golden-parity suite); this
  mission's new check is never reachable for a built-in candidate and must
  not be observable as a behavior change for one.
- What happens to cascade-activated targets (`--cascade`) that include a
  mission-type kind alongside the direct target? This case cannot occur in
  the current codebase, so it needs no second gate call site. As a cascade
  *source*: `ArtifactKind.from_operator_token("mission-type")` raises
  `MissionTypeNotAnArtifactKind`
  (`src/doctrine/artifact_kinds.py`), so `_source_urn()`
  (`src/specify_cli/cli/commands/charter/activate.py`) returns `None`
  whenever the direct target's kind is `mission-type`, and `activate_cmd`
  never calls `_render_cascade_activation` in that case — the cascade path
  is skipped entirely. As a cascade *target*: `NodeKind` does carry a
  `MISSION_TYPE` member (`src/doctrine/drg/models.py`), so a mission-type
  node can exist in the DRG and be reached by graph traversal, but cascade
  *candidacy* is filtered separately — `_kind_of()`
  (`src/charter/cascade.py`) resolves a URN's kind by trying
  `ArtifactKind(prefix)`, and `ArtifactKind` has no `mission_type` member,
  so `_kind_of()` returns `None` for any `mission_type:` URN (the same
  treatment as `action:`/`glossary:` nodes). `_referenced_artifacts()`
  drops every node where `_kind_of()` returns `None` before it ever reaches
  the `CHARTER_ACTIVATABLE_KINDS` filter, so a mission-type node can never
  surface as a `ReferencedArtifact`/cascade candidate. Net effect: a
  mission-type can be neither a cascade source nor a cascade target today,
  so C-003's single call site inside `activate_cmd` (immediately before the
  direct-target `manager.activate()`) is already exhaustive over the
  direct-activation and `--cascade` paths — no second gate call site is
  needed for either.
- **Second write path (`promote_activations`)**: Is `activate_cmd` the
  *only* code path that can ever write
  `mission_type_activations`? No — `promote_activations()`
  (`src/charter/activation_engine.py`) is a second, pre-existing entry
  point onto the same `commit_plan()` write chokepoint, used today by
  `org_charter.py`'s `required_*` union, `interview.py`'s selection
  promotion, and the `m_unify_charter_activation.py` migration. It is
  explicitly out of scope for this mission: `_PROMOTABLE_KINDS`
  (`m_unify_charter_activation.py`) has no mission-type entry and
  `REQUIRED_KIND_FIELDS` (`org_charter.py`) has no `mission_types` field,
  so no current caller can route a mission-type id through
  `promote_activations()` — verified against the current checkout, this is
  a dormant chokepoint, not a live gap. A future widening of either
  constant to add mission-type support would reopen this exact bug class
  through a second write path this mission's fix does not gate; the plan
  phase should note that possibility rather than assume `activate_cmd` is
  the only write path forever.

## Domain Language

- **Activation-time (write) path**: the flow triggered by
  `spec-kitty charter activate mission-type <T>` that, on success, mutates
  `.kittify/config.yaml`'s `mission_type_activations`. Entered through
  `activate_cmd` in `src/specify_cli/cli/commands/charter/activate.py`, which
  delegates the mutation to `CharterPackManager.activate()`
  (`src/charter/pack_manager.py`). This is the only route onto that write
  *this mission's fix* needs to gate — `promote_activations()`
  (`src/charter/activation_engine.py`) is a second, currently-inert entry
  point onto the same underlying `commit_plan()` chokepoint; see the Edge
  Cases "Second write path (`promote_activations`)" note for why no caller
  can route a mission-type through it today.
- **Read (resolution) path**: the flow any later governed operation uses to
  resolve an already-registered mission type's governance and action
  sequence — `resolve_mission_type_context()` in
  `src/charter/mission_type_profiles.py`, which calls
  `_resolve_action_slot()` internally. This path is where the existing
  empty-sequence guard already lives and must keep living.
- **Candidate type**: the mission type id named on the activation command
  line, before it has been written into `mission_type_activations`. By
  definition not yet registered at the moment activation is attempted.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Fail-closed activation gate | As an operator, I want `charter activate mission-type <T>` to refuse activation, exit non-zero, when `<T>`'s resolved action sequence (after applying any single-level `extends` fallback) is empty. | High | Open |
| FR-002 | No mutation on refusal | As an operator, I want a refused activation to leave `.kittify/config.yaml` byte-identical to its pre-command state — `mission_type_activations` must not gain the candidate id, and no other key may be touched. | High | Open |
| FR-003 | Actionable, consistent error text | As an operator, I want the activation-time refusal to name the candidate type id and the layer it resolved from, in the same message shape the existing read-path `MissionTypeEmptyActionSequenceError` already uses, so the two errors read as one consistent diagnostic rather than two different messages for the same defect class. | High | Open |
| FR-004 | Read path unchanged | As an operator relying on existing behavior, I want the read-path `is_registered` short-circuit in `_resolve_action_slot` (the branch that lets a genuinely unregistered type resolve to an empty sequence without raising) to remain exactly where it is and behave exactly as it does today — this mission adds a new check on the activation path, it does not relocate or rewrite the existing read-path check. | High | Open |
| FR-005 | Extends fallback honored | As an operator whose type inherits its action sequence via a single-level `extends`, I want the activation-time check to resolve that fallback the same way the read path does, so a type that would successfully resolve a non-empty sequence at read time is not incorrectly refused at activation time. | High | Open |
| FR-006 | Built-in types unaffected | As an operator activating a built-in mission type, I want no observable behavior change — built-in types always resolve non-empty and must never trip the new gate. | Medium | Open |
| FR-007 | Healthy activation path unaffected | As an operator activating a type whose resolved action sequence is non-empty, I want activation to succeed exactly as it does today, with the same output and the same config mutation. | High | Open |

**Non-goals (explicitly out of scope for this mission):**

- **#3701 / PR #3707** — that issue and PR fix a *false-empty* action-sequence
  **projection** bug in `src/doctrine/missions/mission_type_repository.py`
  (a `pack_context=None` hardcoding that made a correctly-authored org type
  with a real `mission-steps/<type>/` tree resolve empty when it shouldn't).
  Its *production* diff touches a different package tier (`doctrine/`, not
  `charter/` or `specify_cli/`) and adds no activation-time gate. PR #3707
  also touches `tests/charter/test_mission_type_profiles.py` (a small,
  localized change — an optional-args widening to the
  `_write_org_mission_step_yaml` helper plus one new call site); expect a
  routine rebase on that shared test file, same as already stated for PR
  #3711 and PR #3708. Both issues name each other as explicit non-goals in
  their own text. A type with a *genuinely* empty action sequence still
  needs this mission's fix to avoid bricking the project, even after #3707
  merges — the two issues are independent and neither depends on the
  other.
- **#3705 / PR #3711** — cascade-reporting changes
  (`_render_cascade_activation` / `_render_kind_filtered_line`) in the same
  `activate.py` file this mission touches, but a different function and a
  different concern (rendering output, not the activation gate). Expect a
  routine rebase on that file, not a design conflict.
- **#3703 / PR #3708** — shares only a test file
  (`tests/charter/test_mission_type_profiles.py`) with this mission; its
  production changes live entirely in `org_expected_artifacts.py`, an
  unrelated resolution slot.
- **Ledger SK-78** (no `_GUARD_TABLES` row for a custom mission type) — the
  same family of problem (an org-tier mission type presenting as configured
  when it is not fully usable) but a different mechanism: guard tables, not
  the activation-time action-sequence gate this mission adds. Out of scope
  for this mission.

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Never silent success | In 100% of activation attempts against a candidate whose resolved action sequence is empty, the command exits non-zero and reports an error — it must never exit 0 while writing an unusable type into `mission_type_activations`. This mirrors the existing read-path guard's own rationale (its code comment: "Silently returning [] would plan nothing and report success... raise loudly instead"), extended to the activation-time seam where the gap currently lives. | Reliability | High | Open |
| NFR-002 | Dead-symbol / `__all__` consequence | If implementation introduces a new public symbol in `src/charter/mission_type_profiles.py` (or any other module under `src/charter/` or `src/kernel/`) for the activation-time check to call, that symbol MUST be added to the module's `__all__` (charter.md C-007, enforced by `tests/architectural/test_no_dead_symbols.py`) and MUST have a real caller in `src/` — an underscored/private helper reused in place has no such obligation, but a newly-public one does. | Maintainability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | ATDD-first, red before green (charter C-011, binding) | The failing-first test that pins this mission's user-observable behavior (an activation attempt against the natural-operator-path precondition exits non-zero and leaves config unmutated) is committed as a separate commit before any implementation commit; it must be RED on `main` and GREEN on the final commit. A test that still passes with the fix reverted does not satisfy this constraint. | Process | High | Open |
| C-002 | `__all__` convention (charter C-007, binding) | Every module under `src/charter/` and `src/kernel/` declares `__all__`; any new public symbol this mission adds to `src/charter/mission_type_profiles.py` joins that module's existing `__all__` list. | Process | High | Open |
| C-003 | Plan/commit seam awareness | Mission-type activation already routes through `charter.activation_engine`'s `plan_activation()` (pure, validates before computing post-state) / `commit_plan()` (writes only after the plan succeeds) seam, wrapped by `CharterPackManager.activate()` (the literal `commit_plan(...)` call site is `pack_manager.py:643`). `plan_activation()`'s existing validation checks only that the candidate id is a *known* id (membership in the roster) — it has no awareness of action-sequence content for any kind. `activation_engine.py` is not a viable home for the new check anyway: its own module docstring (`activation_engine.py:36-43`) states the module "performs no filesystem discovery and no `config.yaml` load of its own" and receives all inputs as data, while resolving a candidate's action sequence requires the same filesystem-touching resolution `_resolve_action_slot` performs. This mission's fail-closed check is invoked from `activate_cmd` in `src/specify_cli/cli/commands/charter/activate.py` — mirroring the existing `_emit_step_removal_warnings` call (`activate.py:553`) immediately preceding `manager.activate()` (`activate.py:560`) — calling a new helper added to `src/charter/mission_type_profiles.py`, so the check runs before any write and never touches `activation_engine.py` or `pack_manager.py`. This is consistent with C-007's two-file blast radius and NFR-002's `__all__`/dead-symbol obligation. | Technical | High | Open |
| C-004 | Targeted test surface | The repository carries roughly 17,000 tests; a full run is not the per-PR gate. This mission's tests target `tests/charter/test_mission_type_profiles.py` and the `charter activate` command's own coverage (`tests/specify_cli/cli/commands/charter/test_charter_activate_commands_core.py`, plus related siblings in that directory and `tests/charter/test_mission_type_activation*.py`) — not the full suite. | Process | Medium | Open |
| C-005 | Baseline red-main acknowledgment (charter C-9, standing order 9) | `main` carries roughly 23 known-red tests and 2 errors (issue #3284) at the time this spec was authored. That baseline is not this mission's to fix; the plan phase should confirm which of the touched test files are green on `main` before attributing any red result to this mission's own change, rather than rediscovering the baseline mid-implementation. | Process | Low | Open |
| C-006 | Campsite-clean note (standing order 2) | If an opening campsite-clean of the touched files (`activate.py`, `mission_type_profiles.py`) is warranted, it is a distinct, behavior-preserving commit, sequenced tidy-first, before the functional change, folding only domain-matched debt — left to the plan phase to size, not prescribed here. | Process | Low | Open |
| C-007 | Two-file blast radius | The production change is scoped to `src/specify_cli/cli/commands/charter/activate.py` (the activation command flow) and `src/charter/mission_type_profiles.py` (the resolution/validation helper); it does not need to touch `src/doctrine/` or any other package tier. | Technical | Medium | Open |

### Key Entities

- **`MissionTypeEmptyActionSequenceError`**: the existing, pre-fix error type
  (`src/charter/mission_type_profiles.py`) raised on the read path when a
  registered mission type resolves an empty action sequence. Carries
  `mission_type_id` and `layer`. This mission's activation-time refusal
  reports the same defect class, in the same message shape, for a
  candidate that is not yet registered.
- **`mission_type_activations`**: the `.kittify/config.yaml` list key that
  records which mission types a project has activated — the config state
  this mission's fix must leave unmutated on refusal.
- **Activation candidate**: the mission type id passed to
  `charter activate mission-type <T>`, evaluated for a usable (non-empty,
  after `extends` fallback) action sequence before any write is attempted.

## Assumptions

- The natural operator path — declare the pack, then activate, with the
  candidate absent from `mission_type_activations` at call time — is the
  only precondition this mission's acceptance criteria are written against;
  pre-seeded-activation-set reproductions are explicitly rejected as
  coverage for this fix (see Edge Cases).
- The single-level `extends` fallback semantics already implemented on the
  read path are the correct semantics for the activation-time check to
  reuse, not a new rule to design.
- No schema change, migration, or cross-package boundary crossing is
  required; the fix stays inside `charter/` and
  `specify_cli/cli/commands/charter/`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Activating a mission type whose resolved action sequence is
  empty (natural operator path: pack declared, candidate absent from
  `mission_type_activations` before the call) exits non-zero and
  `mission_type_activations` is unchanged on disk before and after the
  attempt, verified by a test that fails when the fix is reverted.
- **SC-002**: The existing read-path error (an already-registered,
  empty-sequence type resolved through `charter mission-type list` or a
  second activation attempt) and the new activation-time error name the
  same type id and the same resolving layer for the same underlying
  condition, verified by a test comparing both messages' content.
- **SC-003**: Activating a mission type whose resolved action sequence is
  non-empty (directly, or via a single-level `extends` fallback to a
  non-empty parent) continues to succeed with unchanged output and config
  mutation, verified by regression coverage over the existing healthy-path
  tests remaining green.
- **SC-004**: A regression test pinned against the pre-seeded-activation-set
  precondition (the SK-81 methodological trap) is explicitly rejected as
  insufficient coverage for FR-001/SC-001 — the accepted test suite must
  include at least one test using the natural, not-pre-seeded precondition.
- **SC-005**: `tests/charter/test_mission_type_profiles.py` and the
  `charter activate` command's targeted test directory pass, with no new
  failures introduced outside the pre-existing #3284 baseline.
