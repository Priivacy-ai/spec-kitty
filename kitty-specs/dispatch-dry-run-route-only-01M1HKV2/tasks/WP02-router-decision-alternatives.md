---
work_package_id: WP02
title: RouterDecision.alternatives on dry-run and real dispatch
dependencies:
- WP01
requirement_refs:
- FR-005
planning_base_branch: feat/dispatch-dry-run-route-only-3840
merge_target_branch: feat/dispatch-dry-run-route-only-3840
branch_strategy: Planning artifacts for this mission were generated on feat/dispatch-dry-run-route-only-3840. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/dispatch-dry-run-route-only-3840 unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/invocation/
create_intent: []
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/invocation/router.py
- src/specify_cli/invocation/executor.py
- src/specify_cli/invocation/empty_charter.py
- tests/specify_cli/invocation/test_router.py
- tests/specify_cli/invocation/cli/test_dispatch.py
- tests/specify_cli/invocation/test_invocation_e2e.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP02 – `RouterDecision.alternatives` on dry-run and real dispatch

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Add a new `alternatives: list[dict[str, str]]` field to `RouterDecision` and thread it onto
**both** the dry-run (WP01) and real dispatch success payloads, exposing the router's
already-computed losing candidates so a consumer can judge routing confidence itself
(spec.md FR-005, User Story 2).

## Context

**This WP depends on WP01** — it builds on `dry_run()`, `to_dry_run_dict()`, and
`build_ambiguous_dry_run_payload()` already existing (WP01's implementation commit is this
WP's `planning_base_branch`). Do not start this WP until WP01's implementation commit has
landed and its ATDD tests are GREEN.

**Decision, stated explicitly (spec.md Clarifications #2)**: `alternatives` ships in v1, on
**both** the dry-run and the real dispatch success path — not deferred, not restricted to
dry-run only. The router already computes the full candidate list internally
(`candidates`/`sorted_candidates`/`top_candidates` in `router.py`'s `route()`) before
discarding all but the winner; this WP threads that already-computed list out through a new
field, additive on both paths.

`RouterDecision` is a **frozen dataclass with no default** for the new field, so adding it
makes every existing constructor call a compile-time-missing-argument error until updated.
There are exactly **five** construction sites — verify this yourself with
`grep -rn "RouterDecision(" --include="*.py" .` against the current tree before starting;
plan.md's "4 call sites" undercounts by one (it misses a test fixture) — do not miss any of
the five:

1. `router.py` `route()` Level 1, explicit `profile_hint` branch (currently ~L262) →
   `alternatives=[]` (the router never computes candidates on this path — Edge Case /
   Acceptance Scenario 2).
2. `router.py` `route()` single-candidate return (currently ~L343-350, `return` at ~L345) →
   `alternatives=[]` (only one candidate existed).
3. `router.py` `route()` tiebreaker-unique-winner return (currently ~L363-370, `return` at
   ~L365) → `alternatives=` every entry of `candidates` **other than** the selected one, each
   rendered as `{"profile_id", "action", "confidence": c["_confidence"], "match_reason"}`.
   SC-003 requires **every** non-winning candidate, not only those that tied for top
   `routing_priority`.
4. `empty_charter.py` `resolve_generic_fallback()` (currently ~L123) → `alternatives=[]`
   (this path never calls `route()` at all — it short-circuits before the router runs).
5. **Test fixture, not production code**: `tests/specify_cli/invocation/test_invocation_e2e.py`'s
   `test_invoke_router_branch_unchanged_with_action_hint` (currently ~L781) builds
   `fake_router.route.return_value = RouterDecision(profile_id=..., action=..., confidence=...,
   match_reason=...)` with no `alternatives` kwarg. Because `RouterDecision` is a frozen
   dataclass with no default on any field, this line raises `TypeError: __init__() missing 1
   required keyword-only argument: 'alternatives'` at collection/run time once this WP lands,
   unless updated to `alternatives=[]` (the test doesn't assert on `alternatives`, it only
   needs a valid stub). This file is added to this WP's `owned_files` specifically for this
   one-line fix — do not widen scope beyond it.

**`alternatives` is never `None` on `RouterDecision`.** Enforced by: (a) the type annotation
`alternatives: list[dict[str, str]]` — no `Optional`, no `None` default — on the frozen
`RouterDecision` dataclass, so a caller passing `None` fails at construction under
`mypy --strict`, not silently at serialization; (b) all five construction sites above pass a
list literal, never a conditional that could resolve to `None`; (c) a direct test asserting
`== []` (not `is None or == []`).

**This guarantee does NOT carry over unchanged to `InvocationPayload.alternatives`** (the
field T009 adds below). `InvocationPayload` (`executor.py`) is a hand-rolled `__slots__`
class whose `__init__(self, **kwargs: object)` accepts arbitrary keyword arguments and
`setattr`s whatever is passed — there is no required-constructor-argument enforcement, mypy
-strict or runtime, the way a real frozen dataclass gets. Its existing `to_dict()` already
tolerates a missing slot: `val = getattr(self, s, None)` silently serializes an omitted slot
as `None` (`tests/invocation/test_dispatch_recommendation.py`'s `_sample_payload()` already
omits several slots this way with no error). So if either of `invoke()`'s or `dry_run()`'s
final `InvocationPayload(...)` construction misses `alternatives=` (T009 steps 2-3), nothing
fails at construction — `to_dict()`/`to_dry_run_dict()` would silently serialize
`"alternatives": null`. **Do not claim mypy-strict/compile-time enforcement for this field at
the `InvocationPayload` layer** — the real backstop there is (1) the T007 ATDD tests asserting
`== []` explicitly, and (2) the explicit fail-fast guard T009 step 5 below requires. **That
guard belongs in `to_dry_run_dict()` only, never in `to_dict()`**: `to_dict()` is the
generic, whole-`__slots__` serializer this very paragraph's `_sample_payload()` example
depends on staying permissive for slots it omits (it omits `empty_charter_fallback` today,
and would omit `alternatives` too) — a strict guard added there would raise on that
fixture's currently-GREEN `.to_dict()` calls. See T009 step 5 for the full reasoning.

`alternatives` is added **only** to the ephemeral `RouterDecision`/`InvocationPayload`
types. `OpStartedEvent` (`record.py`), the type actually persisted to `kitty-ops/*.jsonl`,
is untouched by this mission and has no `alternatives` slot — do not add one; `alternatives`
must not become part of the persisted Op-record schema.

**Write-scope overlap with WP03 (spec.md C-002, accepted, not a defect)**: WP03 (landing
strictly after this WP) also edits the `if len(candidates) == 1:` single-candidate return
and the `routing_priority` tiebreaker block inside `route()` — the same statements this WP
touches to add `alternatives=`. This is not an oversight; it is why WP03 is scoped as "own
commit, auditable and cherry-pickable," not "independently, cleanly revertible regardless of
WP2." The mitigation is strict ordering (this WP lands, commits, and is reviewable before
WP03 starts), not disjointness. Do not attempt to pre-empt WP03's rerank logic here — this
WP's router.py diff is `alternatives=` population only, no selection-logic change.

**ATDD-First (charter C-011 / spec.md C-001)**: this WP's failing-first tests (T007) are
committed as their own commit, before the implementation commit (T008–T010), with **RED
verified on WP01's final commit** (`alternatives` does not exist yet — `KeyError` or
`AttributeError` on the assertion) and **GREEN on this WP's final commit**.

## Marker + CI job for every new test (verified against `.github/workflows/*.yml`)

- **`tests/specify_cli/invocation/test_router.py`** — existing module marker `pytestmark =
  [pytest.mark.unit, pytest.mark.fast]`. New tests MUST carry the same markers. Collected
  by: `doctrine-charter-tests` (path-triggered on `tests/specify_cli/invocation/**`, runs
  `-m "fast and not windows_ci and not timing"`) and `fast-tests-core-misc`'s
  `specify-cli-rest-2` shard (positional path `tests/specify_cli/invocation`, runs
  `-m "fast and not windows_ci and not regression"`).
- **`tests/specify_cli/invocation/cli/test_dispatch.py`** — existing module marker
  `pytestmark = [pytest.mark.non_sandbox, pytest.mark.fast]`. Same two collecting jobs as
  above (this file lives under the same `tests/specify_cli/invocation/` tree).

### Subtask T007: Write the failing-first ATDD tests (own commit, before implementation)

**Purpose**: Pin `alternatives`'s presence/shape contract as RED before any implementation
code exists.

**Steps**:
1. In `tests/specify_cli/invocation/test_router.py` (matching `pytestmark = [pytest.mark.unit,
   pytest.mark.fast]`), add:
   - `test_alternatives_empty_on_single_candidate` — a request matching exactly one profile;
     assert `alternatives == []` (an explicit empty list, not `None`, not an absent key) on
     both dry-run and real dispatch.
   - `test_alternatives_empty_on_explicit_profile_hint` — `--profile <id>` bypasses the
     router entirely; assert `router_confidence == "exact"` and `alternatives == []`.
   - `test_alternatives_nonempty_on_two_candidate_tiebreak` — a request matching two
     profiles (one canonical-verb, one domain-keyword, so `routing_priority` decides today,
     pre-WP03); assert `alternatives` is non-empty and its one entry carries the losing
     candidate's `profile_id`, `action`, `confidence`, and `match_reason` — matching User
     Story 2's own Independent Test.
   - `test_router_ambiguous_candidates_carry_confidence_key` — trigger the existing
     post-tiebreaker `ROUTER_AMBIGUOUS` raise (two candidates tied at the same top
     priority); assert every dict in `err.candidates` (and the resulting dry-run
     `alternatives`) carries a `confidence` key. (WP01 already fixed this raise site's
     candidate-dict shape — this test re-confirms it holds through WP02's edits to the
     surrounding code, it does not re-implement the fix.)
2. In `tests/specify_cli/invocation/cli/test_dispatch.py` (matching `pytestmark =
   [pytest.mark.non_sandbox, pytest.mark.fast]`), add a CLI-level assertion that a real
   (non-dry-run) `dispatch --json` call on a two-candidate request also returns a non-empty
   `alternatives` list — proving the field threads onto the real dispatch path, not only
   dry-run.
3. Run the new tests and confirm every one fails with `KeyError`/`AttributeError` (the
   `alternatives` field/key does not exist on WP01's final commit) — this is RED on WP01's
   final commit.
4. Also re-run (unmodified) `test_router_priority_tiebreaker_selects_higher_priority` and
   confirm it still passes on WP01's final commit — this is the baseline this WP must not
   break.
5. Commit this test-only diff as its own commit, before touching any implementation file.

**Files**: `tests/specify_cli/invocation/test_router.py` (+~100 lines),
`tests/specify_cli/invocation/cli/test_dispatch.py` (+~25 lines).

**Validation**: `pytest tests/specify_cli/invocation/ -v` shows the four new `test_router.py`
tests and the one new `test_dispatch.py` test RED with `KeyError`/`AttributeError`, and
`test_router_priority_tiebreaker_selects_higher_priority` still GREEN.

### Subtask T008: `RouterDecision.alternatives` field + the five construction sites (router.py, empty_charter.py, test_invocation_e2e.py)

**Purpose**: Add the field and populate every existing construction site — the 5 sites (4
production + 1 test fixture) from Context, no more, no less.

**Steps**:
1. In `src/specify_cli/invocation/router.py`, add `alternatives: list[dict[str, str]]` (no
   default) to the `RouterDecision` frozen dataclass.
2. Update construction site 1 (explicit `profile_hint` branch, ~L262): `alternatives=[]`.
3. Update construction site 2 (single-candidate return, ~L343-350): `alternatives=[]`.
4. Update construction site 3 (tiebreaker-unique-winner return, ~L363-370): `alternatives=`
   every entry of `candidates` other than the selected one, each rendered as
   `{"profile_id": c["profile_id"], "action": c["action"], "confidence": c["_confidence"],
   "match_reason": c["match_reason"]}`.
5. In `src/specify_cli/invocation/empty_charter.py`, update construction site 4
   (`resolve_generic_fallback()`, ~L123): `alternatives=[]`.
6. In `tests/specify_cli/invocation/test_invocation_e2e.py`, update construction site 5
   (`test_invoke_router_branch_unchanged_with_action_hint`'s `fake_router.route.return_value
   = RouterDecision(...)` fixture, ~L781): `alternatives=[]`.
7. Confirm via `mypy --strict src/specify_cli/invocation/router.py
   src/specify_cli/invocation/empty_charter.py` that none of the four **production**
   construction sites was missed (a missing `alternatives=` kwarg on a frozen dataclass with
   no default is a compile-time error under strict mode). **This mission's mypy --strict gate
   scope does not include `tests/`** (see T010's gate list), so it will NOT catch a missed
   5th (test-fixture) site — only running the test file does. Confirm site 5 separately by
   running `pytest tests/specify_cli/invocation/test_invocation_e2e.py -v` and checking it
   collects/passes with no `TypeError: __init__() missing 1 required keyword-only argument:
   'alternatives'`.

**Files**: `src/specify_cli/invocation/router.py` (+~20 lines across 4 edits + 1 field),
`src/specify_cli/invocation/empty_charter.py` (+~2 lines),
`tests/specify_cli/invocation/test_invocation_e2e.py` (+1 line: one kwarg on the existing
fixture).

**Validation**: `mypy --strict` passes with zero "missing argument" errors on the four
production sites; `grep -rn "RouterDecision(" --include="*.py" .` confirms exactly 5
`RouterDecision(...)` construction sites in the current codebase (4 production + 1 test
fixture), all updated; `pytest tests/specify_cli/invocation/test_invocation_e2e.py -v` passes
(collection succeeds — site 5's `alternatives=[]` is present).

### Subtask T009: Thread `alternatives` through `InvocationPayload` (executor.py)

**Purpose**: Carry the field from `RouterDecision` onto both `invoke()`'s and `dry_run()`'s
final payloads.

**Steps**:
1. Add `alternatives: list[dict[str, str]]` (no default, no `Optional`) as a type annotation
   and `__slots__` entry on `InvocationPayload`. **Note**: unlike `RouterDecision` (a real
   frozen dataclass), `InvocationPayload.__init__(self, **kwargs: object)` does not enforce
   required constructor arguments — adding this slot does NOT get compile-time/mypy-strict
   protection against a missed construction site the way `RouterDecision.alternatives` does
   (see Context). Step 5 below is what makes a missed site fail loudly instead of silently
   serializing `null`.
2. `invoke()`'s body is unchanged except adding `alternatives=result.alternatives` (or `[]`
   on the explicit-hint branch, matching whatever `RouterDecision.alternatives` already
   carries) to its final `InvocationPayload(...)` construction.
3. `dry_run()` (WP01) similarly threads `alternatives=result.alternatives` onto its
   `InvocationPayload(...)` construction. This is the change WP01's Context section flags as
   the reconciliation point for its own `payload.to_dry_run_dict([])` call (WP01 always passes
   a literal `[]`; from this WP onward a real `alternatives` field exists to read from).
4. Update `to_dry_run_dict()` (WP01) so it reads `alternatives` from `self.alternatives`
   directly rather than requiring a separate parameter, now that the field exists on
   `InvocationPayload` — simplify the call sites in `dispatch.py` accordingly if the
   parameter becomes redundant (confirm with `dispatch.py`'s existing call:
   `payload.to_dry_run_dict([])` (WP01's shape) may collapse to `payload.to_dry_run_dict()`
   — make this change only if it does not regress WP01's tests; keep the diff minimal and
   confirm WP01's GREEN tests stay GREEN).
5. **Required — add a fail-fast guard for a missed construction site, scoped to
   `to_dry_run_dict()` only.** Because step 1's slot carries no constructor-level
   enforcement, add an explicit check inside `to_dry_run_dict()` (the method WP01
   introduces and this WP's step 4 above updates to read `alternatives` off `self`): if
   `getattr(self, "alternatives", None) is None`, raise an explicit exception instead of
   silently emitting `"alternatives": null` — matching this module's existing
   explicit-`raise` style (e.g. `router.py`'s `raise RuntimeError("No profile_hint and no
   router configured. ...")` at ~L334), for example `raise RuntimeError(
   "InvocationPayload.alternatives was not set — a construction site is missing
   alternatives=")`.

   **Do NOT add this guard to `to_dict()`.** `to_dict()` is the generic, whole-`__slots__`
   serializer used by callers outside this WP's control — including
   `tests/invocation/test_dispatch_recommendation.py`'s `_sample_payload()` fixture (owned
   by WP01, not touched by this WP), which constructs `InvocationPayload` omitting several
   slots already (e.g. `empty_charter_fallback`) and relies on `to_dict()`'s permissive
   `getattr(self, s, None)` fallback to keep working. Once `alternatives` is added to
   `__slots__` (step 1), that fixture would omit it too — a strict guard inside `to_dict()`
   would raise `RuntimeError` on that fixture's two currently-GREEN `.to_dict()` calls
   (`test_to_dict_serializes_recommendation_and_is_json_safe`,
   `test_to_dict_recommendation_absent_serializes_to_none`), a regression this WP's own
   `owned_files`/T010 gate scope (`pytest tests/specify_cli/invocation/ -v`) would not
   catch, since that file lives under the separate top-level `tests/invocation/` directory.
   Scoping the guard to `to_dry_run_dict()` avoids this entirely: that method's only caller
   is `dispatch.py`'s dry-run branch, which always constructs `InvocationPayload` with
   `alternatives=` set (T009 step 3).

   This is a required step for `to_dry_run_dict()`, not an optional strengthening — it is
   the real backstop this WP's Context section describes for the `InvocationPayload`
   layer, since the type system does not provide one here.

**Files**: `src/specify_cli/invocation/executor.py` (+~20 lines: 1 new field, 2 construction
site edits, 1 method signature simplification if applicable, 1 fail-fast guard).

**Validation**: `mypy --strict src/specify_cli/invocation/executor.py` passes;
`test_dry_run_payload_shape` (WP01) and the new `test_alternatives_*` tests (T007) both pass;
a new focused unit test (e.g. `test_invocation_payload_serialization_raises_if_alternatives_missing`)
confirms step 5's guard actually fires when `alternatives` is omitted from construction.

### Subtask T010: Gates + commit

**Purpose**: Confirm the diff is clean and land the implementation commit.

**Steps**:
1. Run:
   ```
   ruff check .
   mypy --strict src/specify_cli/invocation/ src/specify_cli/cli/commands/dispatch.py src/glossary/chokepoint.py
   pytest tests/specify_cli/invocation/ -v
   pytest tests/invocation/test_dispatch_recommendation.py -v
   ```
   The second `pytest` invocation is a regression guard for T009 step 5's fail-fast guard:
   it is outside this WP's `owned_files` and outside `tests/specify_cli/invocation/`'s
   scope, but its `_sample_payload()` fixture is exactly what a mis-scoped guard (added to
   `to_dict()` instead of `to_dry_run_dict()`) would break — run it explicitly so that
   class of regression is caught before commit, not just avoided by construction.
2. Confirm `test_router_priority_tiebreaker_selects_higher_priority` still passes unmodified
   (FR-006's future obligation starts here — do not let this WP regress it).
3. Confirm WP01's own ATDD tests (`test_dry_run_writes_nothing_to_kitty_ops`,
   `test_dry_run_suppresses_glossary_event_write`, etc.) still pass after this WP's changes —
   WP02 must not remove or narrow WP01's dry-run-writes-nothing guarantee.
4. Attribute any red per AGENTS.md's baseline-red gotcha (issue #3284/#3283), never
   green-wash pre-existing failures.
5. Commit the implementation (T008–T010) as its own commit, distinct from T007's ATDD
   commit.

**Files**: none new — validation/commit subtask.

**Validation**: All gates above pass modulo pre-existing tracked red; both WP01's and WP02's
own ATDD suites are GREEN together.

## Definition of Done

- [ ] T007's ATDD tests are committed as their own commit, verified RED on WP01's final
      commit (`alternatives` does not exist — `KeyError`/`AttributeError`).
- [ ] `RouterDecision` gains `alternatives: list[dict[str, str]]` (no default, no
      `Optional`); all 5 existing construction sites populate it correctly (Level-1
      explicit-hint → `[]`; single-candidate → `[]`; tiebreaker-winner → every non-winning
      candidate; `empty_charter.py`'s fallback → `[]`; `test_invocation_e2e.py`'s
      `test_invoke_router_branch_unchanged_with_action_hint` fixture → `[]`).
- [ ] `alternatives` never renders as `None` or an absent key on `RouterDecision` — verified
      by `test_alternatives_empty_on_single_candidate` asserting `== []` explicitly (SC-003).
      On `InvocationPayload`, the same guarantee is verified by the same test plus the T009
      step 5 fail-fast guard actually firing when exercised by its dedicated unit test — not
      by the type system, which does not enforce this field on `InvocationPayload`.
- [ ] `alternatives` threads onto **both** dry-run (`to_dry_run_dict()`) and real dispatch
      (`invoke()`'s `InvocationPayload`) success payloads (spec.md Clarifications #2).
- [ ] `OpStartedEvent`/`record.py` (the persisted Op-record type) is untouched — no
      `alternatives` slot added there.
- [ ] New tests carry the exact markers named above (`unit`+`fast` in `test_router.py`,
      `non_sandbox`+`fast` in `test_dispatch.py`) — no invented markers.
- [ ] `test_router_priority_tiebreaker_selects_higher_priority` still passes unmodified.
- [ ] WP01's own ATDD tests still pass after this WP's changes.
- [ ] `ruff check .`, `mypy --strict` (scoped paths), and the targeted pytest paths pass,
      modulo pre-existing #3284/#3283-tracked red.
- [ ] Implementation is committed as its own commit, distinct from T007's ATDD commit.

Implement with: `spec-kitty agent action implement WP02 --agent claude`

## Risks

- **Missing one of the 5 `RouterDecision` construction sites** — mitigated structurally for
  the 4 production sites: `RouterDecision` has no default for the new field, so
  `mypy --strict` fails at every unmigrated production construction site rather than
  silently defaulting to `None`. The 5th site (`test_invocation_e2e.py`'s fixture) is outside
  this mission's `mypy --strict` gate scope — mitigated instead by T008's explicit
  `pytest tests/specify_cli/invocation/test_invocation_e2e.py` check and the live grep-count
  validation.
- **`alternatives` regressing to `None` or an absent key on serialization** — on
  `RouterDecision`, mitigated by the non-`Optional` type annotation (real compile-time
  enforcement). On `InvocationPayload`, that type-system guarantee does not hold (see
  Context) — mitigated instead by T009 step 5's required fail-fast guard plus a direct
  `== []` test assertion (not `is None or == []`, which would mask the regression).
- **Anticipating WP03's rerank logic while touching the same `route()` statements** — do not.
  This WP's router.py diff is `alternatives=` population only; leave selection logic
  (`if len(candidates) == 1`, the priority tiebreaker) behaviorally unchanged for WP03 to
  restructure next.
- **`alternatives` leaking into the persisted `kitty-ops/*.jsonl` Op-record schema** —
  mitigated by keeping the field on `RouterDecision`/`InvocationPayload` only, never on
  `OpStartedEvent`/`record.py`.

## Reviewer Guidance

- Confirm T007's ATDD commit precedes the implementation commit, and RED was actually
  verified on WP01's final commit (not merely "written first").
- Confirm exactly 5 `RouterDecision(...)` construction sites exist in the diff's final state
  (4 production + 1 test fixture in `test_invocation_e2e.py`), each populating `alternatives`
  correctly per the table in Context — no site missed, no site given a placeholder that isn't
  semantically correct for its branch. Re-run the live grep
  (`grep -rn "RouterDecision(" --include="*.py" .`) yourself rather than trusting this count —
  the codebase may have changed since this WP was authored.
- Confirm `alternatives` never appears as `None`/`Optional` anywhere in the diff — check the
  type annotations directly, not just the tests.
- Confirm WP02's Context/DoD language does NOT claim mypy-strict/compile-time enforcement for
  `InvocationPayload.alternatives` specifically (only `RouterDecision.alternatives` gets that);
  confirm T009's fail-fast guard is actually implemented (not just described) and covered by
  its own passing unit test.
- Confirm T009 step 5's fail-fast guard lives in `to_dry_run_dict()` only and was NOT added
  to `to_dict()`; confirm `pytest tests/invocation/test_dispatch_recommendation.py -v`
  (T010) still passes — a guard leaked into `to_dict()` raises on that file's
  `_sample_payload()`-based tests.
- Confirm this WP's `route()` diff is `alternatives=` population only — no change to which
  candidate wins or how ties are broken (that is WP03's job, landing after this WP).
- Confirm `OpStartedEvent`/`record.py` has no new `alternatives` slot.
