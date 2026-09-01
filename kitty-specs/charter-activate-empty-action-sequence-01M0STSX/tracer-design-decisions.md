# Tracer: Design Decisions — charter-activate-empty-action-sequence-01M0STSX

Seeded during the spec phase (2026-08-24). Append during implementation; assess at close.

## The methodological trap is load-bearing, and the spec says so explicitly

Per ledger SK-81, two independent prior reviewers concluded this bug "already fails"
because they pre-seeded the candidate mission type into `mission_type_activations`
before calling activation — which trips the pre-existing read-path guard and masks the
real defect. The spec's Edge Cases section states this trap in first-person prose (not
just cited from the brief) and SC-004 makes a pre-seeded-only test suite explicitly
insufficient coverage. The `verify` lens (mission-derived) stress-tested this directly
and found the spec's own defense had a gap: the nearest reusable test helper's every
existing call site conflates "declare the pack" with "set activations", inviting an
implementer to reproduce the trap one level up inside this mission's own tests. Fixed by
naming the exact fixture shape required (declare via `packs`, omit `<T>` from
`activated_mission_types`).

## The fix's call site is a plan-phase decision, but the spec had to stop contradicting
   itself about where

Constraint C-003 originally offered two call-site options ("inside `plan_activation`" or
"before `commit_plan`") that both live outside C-007's stated two-file blast radius, and
"inside `plan_activation`" is architecturally non-viable given that module's own
no-filesystem-discovery docstring contract (confirmed by reading the actual code, not
assumed). Both the `gov` and `arch` lenses independently found this — merged as one
finding in R2. Resolved by naming the concrete, precedented call site: a guard in
`activate_cmd` (`activate.py`), mirroring the existing `_emit_step_removal_warnings`
preflight, calling a new helper in `mission_type_profiles.py` — consistent with C-007
and with NFR-002's `__all__` obligation. The exact helper signature/wiring remains a
plan-phase decision; only the *file* it lands in was pinned here.

## A second, currently-inert write chokepoint was surfaced and explicitly scoped out

The round-2 fresh sweep found that `promote_activations()` (`activation_engine.py`) is a
second entry point onto the same `commit_plan()` seam `CharterPackManager.activate()`
uses, and that the spec's Domain Language section implied `activate_cmd` was the *only*
route into `mission_type_activations`. Verified live: no current caller
(`org_charter.py`, `interview.py`, the `m_unify_charter_activation` migration) can route
a mission-type through it today, so there is no live bug — but a future widening of
`_PROMOTABLE_KINDS`/`REQUIRED_KIND_FIELDS` to include mission-type could silently reopen
this exact bug class through a path this mission's `activate_cmd` gate never touches.
The spec now documents this explicitly as a currently-inert, out-of-scope chokepoint
rather than staying silent about it — a deliberate choice to leave a documented seam for
the next reader rather than either (a) silently gating a dead path or (b) silently
leaving the exhaustiveness claim overbroad.

## Non-goals were tightened against the live PR diffs, not just issue text

The `gov` lens caught that the spec's non-goals bullet for #3701/PR#3707 claimed zero
`charter/`-tier overlap while PR #3707's actual diff (checked via `gh pr view/diff`,
live) also touches `tests/charter/test_mission_type_profiles.py` — the exact file this
mission's own tests target. Fixed by narrowing the claim to the *production* diff only
and adding the same shared-test-file rebase caveat already given to #3703/PR#3708 and
#3705/PR#3711. Lesson for future missions in this family: a non-goals boundary claim
needs to be checked against the actual open PR diff, not just the issue's own scope
text, before it's trustworthy.

## Plan phase (2026-08-24): concrete helper signature and call-site decisions

The spec pinned the *file* the new check lands in (`mission_type_profiles.py`,
called from `activate_cmd`) but explicitly left the exact function name/signature and
several edge-case behaviors to the plan phase. Decisions made, reading the real code
first:

- **New public function**: `validate_activatable_mission_type(mission_type_id, *,
  repo_root)` in `mission_type_profiles.py`, plus a private
  `_resolve_with_extends_fallback()` factored out of `_resolve_action_slot` so both
  callers share one extends-fallback implementation (DRY) rather than duplicating the
  six-line extends-resolution block. `_resolve_action_slot`'s existing `is_registered`
  short-circuit and its `mission is None -> UnknownMissionTypeError` branch are left
  exactly where they are (FR-004) — only the post-`mission is not None` tail is
  shared.
- **`mission is None` (no resolvable YAML anywhere) is a no-op, not a raise**: the
  new function does not raise `UnknownMissionTypeError` for a candidate with no YAML
  in any layer. That case is already caught moments later by `plan_activation`'s
  pre-existing `UnknownActivationIdError` (via `available_ids` membership, inside
  `CharterPackManager.activate()`) — deferring to it avoids introducing a second,
  slightly-different error for the same "doesn't exist" condition and keeps the new
  function's scope strictly to the empty-action-sequence defect class per the spec's
  Edge Cases note.
- **CLI-level ATDD test fixture is written locally, not cross-imported**: the spec's
  Edge Cases named `_write_layered_mission_type_yaml`/`_write_org_pack_config`
  (both in `tests/charter/test_mission_type_profiles.py`) as the required *shape*
  ("two separate calls... or an equivalent pair of fixtures with the same shape").
  `test_charter_activate_commands_core.py` has no `CliRunner`-free precedent for
  cross-importing private helpers from a sibling test module (checked: no other file
  in that directory imports a leading-underscore helper from
  `tests/charter/`), so the plan reproduces the same two-call shape locally in that
  file rather than importing across test modules — the CLI-level test needs
  `CliRunner`/exit-code/byte-diff assertions `test_mission_type_profiles.py` has no
  precedent for either. The named helpers are still used verbatim for the supporting
  unit-level tests in `test_mission_type_profiles.py` itself.
- **No campsite-clean commit**: both touched files are concurrently being edited by
  three sibling open PRs (#3707, #3708, #3711 per spec.md's Non-goals); any drive-by
  cleanup would only widen rebase-conflict surface for zero domain-matched benefit.
- **One WP, three commits**: WP count is not forced to mirror the RED/GREEN commit
  split — C-011's ATDD sequencing is satisfied at the commit level inside a single
  work package, consistent with this repo's single_branch/one-PR-per-mission default
  and the mission's already-tiny two-file scope.

## Implementation phase (WP01, 2026-08-24): AttributeError over ImportError for the RED shape

T002's plan text allowed either `ImportError`/`AttributeError` for the not-yet-existing
`validate_activatable_mission_type`. Chose `AttributeError`: imported
`charter.mission_type_profiles` as a module (`import charter.mission_type_profiles as
mission_type_profiles`) and called `mission_type_profiles.validate_activatable_mission_type(...)`,
rather than adding the name to the existing top-of-file `from charter.mission_type_profiles
import (...)` block. A name in that block would raise `ImportError` at *collection* time for
the whole test file, breaking every other test in it (including the 62-test baseline) for the
duration of the RED commit — a much larger blast radius than the plan's own "AttributeError:
module ... has no attribute ..." wording implies. The module-attribute form keeps the RED
localized to exactly the 5 new tests, which is what T001's baseline command actually showed
(62 passed / 4 failed at T002, 63 passed / 5 failed at T003).

## Message-parity test built on real disk state, not two competing mocks

T002 asks for a message-parity assertion between the new function and `_resolve_action_slot`'s
message for the same `(id, layer)` pair. The existing precedent tests in
`test_mission_type_profiles.py` construct a `PackContext` by hand and monkeypatch
`PackContext.from_config` to return it — but `validate_activatable_mission_type` calls
`PackContext.from_config(repo_root)` itself internally, so patching it would fight the very
call the function under test makes. Resolved by using one real `.kittify/config.yaml` (via
`_write_org_pack_config`) and calling `PackContext.from_config(tmp_path)` once for both sides
of the comparison: `_resolve_action_slot` directly (with `is_registered=True` supplied
explicitly, since that gate is the one thing this new function deliberately does not
replicate) and `validate_activatable_mission_type` (unregistered, its natural precondition).
Both raise off the same `MissionTypeEmptyActionSequenceError(id, layer)` constructor, so
`str()` equality proves message parity without needing two separate mocked contexts.

## Revert check performed via `git stash`, not a throwaway branch

To satisfy the "verify the test fails with the fix reverted" requirement without touching
tracked history (no extra commit to later scrub), stashed just the two `src/` files
(`git stash push --keep-index -- <src files>`) after T004 landed, re-ran the 6 new RED-commit
tests against the reverted tree (all 5 failed, the 1 documented-GREEN-exception CLI test still
passed), then `git stash pop` to restore the fix. This is a read-only verification technique,
not a git-history change — the committed T004 diff is untouched by it.

## PR-CONTRACT-001 closed: negative-path extends-fallback tests, new surface only

The PR-lens finding PR-CONTRACT-001 (survived refutation, severity 2) noted that
`_resolve_with_extends_fallback`'s documented both-empty/unresolvable-parent branch — the
exact silent-empty-sequence shape #3702 exists to close — was reachable and correct today but
unpinned by any test, for either caller. Closed by adding two tests to
`TestValidateActivatableMissionTypeExtendsFallback` in `tests/charter/test_mission_type_profiles.py`:
`test_extends_fallback_to_also_empty_parent_still_raises` (own `action_sequence` omitted,
`extends` -> a parent whose own `action_sequence` is also omitted) and
`test_extends_fallback_to_nonexistent_parent_still_raises` (own `action_sequence` omitted,
`extends` -> an id with no matching YAML in any layer). Both assert
`MissionTypeEmptyActionSequenceError` is still raised, mirroring the existing
`test_extends_fallback_to_non_empty_parent_does_not_raise` fixture shape exactly (real
`tmp_path` disk state via `_write_layered_mission_type_yaml`/`_write_org_pack_config`, no
`patch()`, natural-path activation with the candidate left out of
`mission_type_activations` and its absence asserted before the call).

Confirmed the tests genuinely pin the behaviour, not just exist: temporarily replaced
`validate_activatable_mission_type`'s `if not action_sequence:` guard with `if False:` in
`src/charter/mission_type_profiles.py`, re-ran the class — the two new tests failed
(`DID NOT RAISE MissionTypeEmptyActionSequenceError`) while the pre-existing success-path
test kept passing — then restored the file to its exact original content (`git diff` empty
afterward) before committing.

Scope followed the refuter's own reasoning: `_resolve_action_slot`'s half of the fallback is
pre-existing (`git show bb9a56226:src/charter/mission_type_profiles.py` has the identical
inline logic before this mission), so it is out of scope and untouched —
`tests/charter/test_action_sequence_dispatch.py` was not modified.
`validate_activatable_mission_type` and its test class are wholly new to this mission's WP01,
so the negative-path test there is in-scope, low-conflict-risk, and is the whole fix. No
production file was touched.
