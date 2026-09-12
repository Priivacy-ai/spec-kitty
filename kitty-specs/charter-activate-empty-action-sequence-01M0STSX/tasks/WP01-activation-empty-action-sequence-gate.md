---
work_package_id: WP01
title: Activation-time empty-action-sequence gate
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- NFR-001
- NFR-002
- C-001
- C-002
- C-003
- C-004
- C-005
- C-006
- C-007
planning_base_branch: fix/charter-activate-empty-action-sequence-3702
merge_target_branch: fix/charter-activate-empty-action-sequence-3702
branch_strategy: Planning artifacts for this mission were generated on fix/charter-activate-empty-action-sequence-3702. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-activate-empty-action-sequence-3702 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
history: []
authoritative_surface: src/charter/mission_type_profiles.py
create_intent: []
execution_mode: code_change
owned_files:
- src/charter/mission_type_profiles.py
- src/specify_cli/cli/commands/charter/activate.py
- tests/charter/test_mission_type_profiles.py
- tests/specify_cli/cli/commands/charter/test_charter_activate_commands_core.py
tags: []
tracker_refs: []
---

## Objective

Add a fail-closed gate on `charter activate mission-type <T>` so that a
candidate mission type whose resolved action sequence is empty (after
applying any single-level `extends` fallback) is refused — non-zero exit,
no mutation of `.kittify/config.yaml` — **before** `mission_type_activations`
is ever written (FR-001, NFR-001). The existing read-path guard inside
`_resolve_action_slot` (its `is_registered` short-circuit) must remain
untouched in location and behavior (FR-004). This closes the activation-time
gap that currently lets an unusable mission type get written into config and
then brick every later governed entry point that resolves it.

## Context

Summary (plan.md's "Summary" section): `spec-kitty charter activate
mission-type <T>` writes `<T>` into `.kittify/config.yaml`'s
`mission_type_activations` and exits 0 even when `<T>`'s resolved action
sequence is empty, because the read-path guard that would catch this
(`charter/mission_type_profiles.py::_resolve_action_slot`'s
`MissionTypeEmptyActionSequenceError` check) short-circuits to `[]` for any
**unregistered** candidate — and at the moment activation runs, the
candidate is by definition not yet registered. Every later governed entry
point that resolves `<T>` (mission creation, `charter mission-type list`, a
second `charter activate`) then hard-fails, and the CLI gives the operator
no way back out.

This WP adds one new **public** function to `src/charter/mission_type_profiles.py`
— `validate_activatable_mission_type()` — that performs the same roster
resolution + single-level `extends` fallback `_resolve_action_slot` already
performs, but unconditionally (not gated on `is_registered`), and raises the
existing `MissionTypeEmptyActionSequenceError` when the result is empty. It
is called from `activate_cmd` in
`src/specify_cli/cli/commands/charter/activate.py`, immediately before
`manager = CharterPackManager()` — mirroring the existing
`_emit_step_removal_warnings` preflight call one line above it — so the
check runs and can refuse before any write is attempted. No other module is
touched.

**The plan/commit seam resolution (the crux, plan.md "Architecture" ->
"The plan/commit seam resolution").** Why not inside `plan_activation()` /
`commit_plan()` (`activation_engine.py`)? Read against the actual code:
`activation_engine.py`'s own module docstring (lines 1-43, specifically
36-43) states the module "performs no filesystem discovery and no
`config.yaml` load of its own" — inputs arrive **as data** (C-008), and the
single write in `commit_plan()` delegates to a caller-supplied `save`
callable so the engine stays free of I/O. `plan_activation()` (line ~193)
validates only that `artifact_id in set(available_ids)` — membership, not
content — before computing post-state; it has no notion of "action
sequence" for any kind. Resolving whether a candidate's action sequence is
empty requires exactly the filesystem-touching resolution
`_resolve_action_slot` performs (walking `mission_types_dirs` +
`pack_context.pack_roots`, invoking `resolve_layered_mission_types`, a
schema-validating YAML load). Putting that resolution inside
`plan_activation()` would violate the module's own documented
no-filesystem-discovery contract — this is the exact non-viability the
spec's review already established (`SPEC-GOV-002`,
`reviews/spec.confirmed.yaml`, confirmed+resolved) and the spec's final
C-003 text states this reading explicitly. This WP does not re-litigate it;
it implements the call site C-003 already names.

Why `activate_cmd` calling a new `mission_type_profiles.py` helper,
precisely? `activate_cmd` already resolves mission-type-specific,
filesystem-touching state via `_emit_step_removal_warnings(kind,
artifact_id, repo_root)` (`activate.py:553`) immediately before
`manager.activate(...)` (`activate.py:560`) — and that existing function
*already* calls `resolve_mission_type_context(repo_root,
mission_type=artifact_id)` internally (`activate.py:181-183`) for exactly
this kind, catching `UnknownMissionTypeError` but *not*
`MissionTypeEmptyActionSequenceError`. Read closely: that existing call does
NOT trip on today's bug, because `resolve_mission_type_context` computes
`is_registered = type_key in registered` (`mission_type_profiles.py:639`)
against `existing_mission_types(repo_root)` — the candidate is by
definition not yet in that set, so `_resolve_action_slot`'s `if not
is_registered: return []` (line 967) fires first and the empty-sequence
branch is never reached. This is the precedented, C-007-compatible call
site: same file, same point in the flow, same filesystem-resolution shape,
one line below the existing call.

### The SK-81 methodological trap (binding — copy this verbatim into the WP, do not paraphrase or shorten it):

> Two prior observations of this defect recorded `charter activate
> mission-type <T>` as already failing, by pre-seeding `<T>` into
> `mission_type_activations` before calling activation — under that
> precondition `is_registered` is already `True`, so the existing read-path
> guard fires and the command never demonstrates the actual defect. The
> regression test for this mission MUST use the natural operator path
> instead: declare the org pack
> (`_write_layered_mission_type_yaml(org_root / "mission_types", "<T>.yaml",
> "<T>", action_sequence=None)` — `tests/charter/test_mission_type_profiles.py:449`),
> and leave `<T>` OUT of `mission_type_activations` in `.kittify/config.yaml`
> (via `_write_org_pack_config`, `tests/charter/test_mission_type_profiles.py:846`,
> called with `<T>`'s org pack declared but `activated_mission_types`
> omitting `<T>` — every existing call site in that file populates both
> lists together; do NOT follow that convention here). Assert `<T>` is
> absent from `mission_type_activations` immediately before invoking the
> command under test. A test that pre-seeds the activation set before
> calling activation would pass even with zero code changed (spec.md
> SC-004) and MUST NOT be accepted as coverage for FR-001/SC-001.

## Subtask T001: Baseline capture

**Purpose**: Before any change, run the targeted test surface on the
pre-mission tree and record pass/fail per test, so later red results are
attributable correctly (charter Standing Order 9 / spec C-005). `main`
carries roughly 23 known-red tests and 2 errors (issue #3284) — that
baseline is not this mission's to fix.

**Steps**: Run exactly this pytest invocation (plan.md's "Baseline"
section, quoted verbatim — 8 test files, `.venv/bin/python -m pytest`,
never a bare `pytest` or `uv run`):

```
.venv/bin/python -m pytest \
  tests/charter/test_mission_type_profiles.py \
  tests/charter/test_mission_type_activation.py \
  tests/charter/test_mission_type_activation_gating.py \
  tests/charter/test_mission_type_activation_emit.py \
  tests/charter/test_mission_type_activations_seed_read_parity.py \
  tests/specify_cli/cli/commands/charter/test_charter_activate_commands_core.py \
  tests/specify_cli/cli/commands/charter/test_charter_activate_commands_cascade_flags.py \
  tests/specify_cli/cli/commands/charter/test_charter_activate_commands_cascade_output.py \
  -v
```

Run on the pre-mission tree (current `HEAD` of this branch, before any
mission commit). Record pass/fail per test — this recorded baseline is what
SC-005 ("no new failures introduced outside the pre-existing #3284
baseline") is verified against, not a fresh assumption. Do not attribute
pre-existing red (issue #3284, ~23 known-red tests + 2 errors) to this
mission. Record the per-test pass/fail result table in `tracer-approach.md`
(this mission's existing tracer file for authoring notes) so the baseline
has a durable, checkable location before any mission commit lands.
**No code changes in this subtask; no commit.**

## Subtask T002: `test:` RED commit (commit 1)

Adds the natural-operator-path acceptance test to
`tests/specify_cli/cli/commands/charter/test_charter_activate_commands_core.py`:
a new test that:

(a) authors an org-pack `mission_types/<T>.yaml` with no `action_sequence`
(equivalent-shape fixture to `_write_layered_mission_type_yaml(...,
action_sequence=None)`, written **locally in this file's own existing
direct-`write_text` fixture style** — this file has no
`typer.testing.CliRunner`-free precedent for cross-importing private
helpers from `tests/charter/test_mission_type_profiles.py`, so reproduce
the two-call fixture shape locally, do not import it);

(b) authors `.kittify/config.yaml` declaring the org pack via `packs` with
`<T>` **absent** from `mission_type_activations` (the second, separate
fixture call the spec's Edge Case requires — never combined with step (a)
into one call);

(c) asserts `<T>` is absent from `mission_type_activations` immediately
before invoking;

(d) invokes `charter activate mission-type <T>` via `CliRunner`;

(e) asserts non-zero exit, an error naming `<T>` and layer `org`, and
`.kittify/config.yaml` byte-identical to its pre-command state.

Also adds, in the **same commit**, the supporting unit-level tests in
`tests/charter/test_mission_type_profiles.py` using the named helpers
directly per the spec's literal Edge Case instruction:
`_write_layered_mission_type_yaml` (empty-sequence case) +
`_write_org_pack_config` (packs declared, `<T>` omitted from
`activated_mission_types`) exercising the new
`validate_activatable_mission_type()` function directly:

- raises case (empty sequence, natural-path fixture),
- a non-empty case (no-raise, FR-007 regression shape),
- a message-parity assertion comparing the new function's raised message
  against `_resolve_action_slot`'s message for the same `(id, layer)` pair
  (SC-002).

**Verify RED on `planning_base_branch`** (this branch's `HEAD` before this
commit) — the CLI test fails because activation currently succeeds; the
unit tests fail with `ImportError`/`AttributeError` because
`validate_activatable_mission_type` does not exist yet. Both are legitimate
RED, not accidental collection breakage elsewhere (baseline captured in
T001 rules that out).

For the exact fixture shape (both the CLI-level and unit-level tests in
this subtask), follow the SK-81 methodological trap section above verbatim
— do not restate it here, point back to it.

## Subtask T003: `test:` fixture-widening + AC4 commit (commit 2)

Widens `_write_layered_mission_type_yaml`
(`tests/charter/test_mission_type_profiles.py:449`) with a new `extends:
str | None = None` keyword parameter (default preserves every existing
call site's behavior — a non-breaking widening, not a signature-breaking
change), and adds the AC4/FR-005 extends-fallback fixture + test: a
candidate `<T>` with its own `action_sequence=None` and
`extends="<parent>"`, a parent with a non-empty sequence, asserting
`validate_activatable_mission_type()` does **not** raise. This is sized
explicit work per the spec's Edge Cases instruction (zero `extends`
precedent existed in this file before this mission), not implicit
follow-on work.

Also adds, in the same commit, a CLI-level (`CliRunner`) test in
`tests/specify_cli/cli/commands/charter/test_charter_activate_commands_core.py`
mirroring T002's CLI-level test shape: it declares an org-pack candidate
`<T>` with empty own `action_sequence` and `extends` set to a parent with a
non-empty `action_sequence`, invokes `charter activate mission-type <T>`
via `CliRunner`, and asserts exit code 0 and that `<T>` is now present in
`.kittify/config.yaml`'s `mission_type_activations` — closing the gap
where AC4 previously had only unit-level coverage of
`validate_activatable_mission_type()` and no end-to-end CLI assertion
(unlike AC1-2, which get a new end-to-end CLI assertion from T002's
CLI-level test, and AC3, which already has end-to-end CLI coverage from the
existing healthy-path tests — T002 adds only a unit-level regression case
for AC3, not a new CLI-level test).

**State explicitly and exactly as plan.md does**: this CLI-level AC4 test
is a **documented exception** — it is expected GREEN already at this
commit (it pins today's unconditional-success behavior, not the fix), and
is NOT part of this commit's RED signal; only the new unit-level extends
test is RED here. This is not a contradiction of C-001/C-011 — activation
already unconditionally succeeds today for any unregistered candidate,
including one whose extends chain would resolve non-empty; the bug is
"always succeeds", not "wrongly fails", so there is nothing for this
particular CLI assertion to be RED against yet. Do not let implementation
treat this as an inconsistency to "fix" — plan.md's own text explains why
it is correct as specified.

**Verify RED**: run the targeted surface (T001's Baseline command) after
this commit — the new unit-level extends test fails with `AttributeError:
module 'charter.mission_type_profiles' has no attribute
'validate_activatable_mission_type'` (the function does not exist yet);
the new CLI-level test passes already (asserts today's unconditional
success path), so it is expected GREEN at this commit and is not part of
this commit's RED signal. Confirm the `AttributeError` is the only new
failure and not accidental collection breakage elsewhere (T001's recorded
baseline rules that out).

Kept as a separate commit from T002 because it depends on the widened
fixture helper — a distinct, reviewable unit of test-infrastructure
change.

## Subtask T004: `fix:` GREEN commit (commit 3)

The production change. Add to `src/charter/mission_type_profiles.py`:

**New helper — exact module, name, signature** (plan.md "Architecture" ->
"New helper — exact module, name, signature", transcribed verbatim):

```python
def validate_activatable_mission_type(mission_type_id: str, *, repo_root: Path) -> None:
    """Fail-closed activation-time gate (FR-001/NFR-001): raise if *mission_type_id*
    would resolve an empty action sequence (after the single-level ``extends``
    fallback) were it activated. No-ops when *mission_type_id* has no resolvable
    YAML in any layer at all -- that configuration inconsistency is already governed
    by ``plan_activation``'s ``UnknownActivationIdError`` (raised moments later,
    inside ``CharterPackManager.activate()`` via the ``available_ids`` membership
    check), which this function does not weaken, duplicate, or race (FR-004 note:
    this is a *different* pre-existing check than the read path's
    ``UnknownMissionTypeError``, and this function defers to the activation-time one).
    Bridge to spec.md's Edge Cases: spec.md names the read path's
    ``UnknownMissionTypeError`` as the general governance for "no resolvable YAML in
    any layer"; on this activation-time path specifically, it is
    ``plan_activation``'s ``available_ids`` membership check -- a distinct,
    pre-existing gate on a different module -- that actually fires first, before this
    function's caller (``activate_cmd``) is ever reached for such a candidate. The
    two named errors are not in tension: each is simply the check that governs its
    own path (read vs. activation-time), and this function correctly no-ops rather
    than re-deriving or racing either one.

    Raises
    ------
    MissionTypeEmptyActionSequenceError
        If the candidate's own action sequence, or its single-level ``extends``
        fallback, is empty.
    """
```

Plus one private, same-module helper factored out of `_resolve_action_slot`
(both callers converge on it, so the extends-fallback rule is defined once
— DRY, and it carries no `__all__` obligation as an underscored symbol):

```python
def _resolve_with_extends_fallback(mission: MissionType, roster: Mapping[str, MissionType]) -> list[str]:
    """Own action_sequence, or single-level extends fallback if own is empty."""
```

`_resolve_action_slot` is refactored to call `_resolve_with_extends_fallback`
after its existing `mission is None -> raise UnknownMissionTypeError` branch
(that branch stays exactly where it is — FR-004 requires the
`is_registered` short-circuit and this adjacent branch untouched in
substance) instead of inlining the same six lines twice. This is the one
behavior-preserving refactor made inside the read path, and it is covered
by FR-004's own regression suite (existing tests must stay green, unchanged
assertions).

**Exact call site in `activate.py`** (plan.md "Architecture" -> "Exact call
site in `activate.py`", transcribed verbatim) — a new private wrapper
(mirroring `_emit_step_removal_warnings`'s `if kind != "mission-type":
return` shape, so `activate_cmd`'s body keeps its "no inline kind branch"
discipline), added directly below that function:

```python
def _validate_mission_type_activatable(kind: str, artifact_id: str, repo_root: Path) -> None:
    """FR-001 preflight: refuse activation of an empty-action-sequence mission type."""
    if kind != "mission-type":
        return
    from charter.mission_type_profiles import validate_activatable_mission_type  # noqa: PLC0415

    validate_activatable_mission_type(artifact_id, repo_root=repo_root)
```

Called in `activate_cmd`, **between** the existing
`_emit_step_removal_warnings` try/except block (ends `activate.py:556`) and
`manager = CharterPackManager()` (`activate.py:558`):

```python
try:
    _validate_mission_type_activatable(kind, artifact_id, repo_root)
except ValueError as exc:
    console.print(f"[red]Error:[/red] {exc}")
    raise typer.Exit(1) from exc

manager = CharterPackManager()
```

Identical shape to the two existing `try/except ValueError` blocks in this
function (`MissionTypeEmptyActionSequenceError` is a `ValueError`
subclass, per its class definition at `mission_type_profiles.py:259`), so
FR-003's "same message shape" requirement is satisfied by construction —
the CLI never reformats the message, it prints `str(exc)` exactly as the
two adjacent blocks already do.

**`__all__` placement** (plan.md "`__all__` / dead-symbol governance",
binding): `validate_activatable_mission_type` is **public**: its only
caller is `_validate_mission_type_activatable` in `activate.py` — a real,
non-test caller in `src/`, satisfying
`tests/architectural/test_no_dead_symbols.py`'s "every `__all__` name
needs a non-test caller" gate without needing a `_SYMBOL_ALLOWLIST` entry.
Lands in `src/charter/mission_type_profiles.py`'s existing `__all__` list
(`mission_type_profiles.py:71-83`). The list's existing order is a plain
case-sensitive `sorted()`; under that sort, uppercase-first class names
group before lowercase-first function names, so the new, lowercase-first
`validate_activatable_mission_type` sorts as the **LAST entry**,
immediately after `"resolve_mission_type_key",` and before the closing
`]` — not adjacent to `UnknownMissionTypeError`.

`_resolve_with_extends_fallback` is **private** (leading underscore): no
`__all__` obligation. Both its callers (`_resolve_action_slot`,
`validate_activatable_mission_type`) live in the same module.
`_validate_mission_type_activatable` (in `activate.py`) is **private**: no
`__all__` obligation, same shape as its sibling
`_emit_step_removal_warnings` (also private, also uncounted in any
`__all__`).

**Verify GREEN** on this commit: every test added in T002/T003 passes,
plus the full targeted surface (T001's Baseline command list) shows no new
regressions relative to the baseline recorded in T001.

## Definition of Done

- [ ] T001 baseline captured (pass/fail per test recorded in
      `tracer-approach.md`, attributable before any mission commit lands).
- [ ] 3 commits landed in order: `test:` RED (T002), `test:` fixture-widening
      + AC4 (T003), `fix:` GREEN (T004).
- [ ] C-001/C-011 verified RED-then-GREEN: T002's CLI + unit tests RED on
      `planning_base_branch`; T003's unit-level extends test RED, its
      CLI-level AC4 test GREEN already (documented exception per plan.md,
      not a violation); T004 GREEN across all of the above.
- [ ] `__all__` updated in `src/charter/mission_type_profiles.py` — new
      entry sorts as the last element, after `"resolve_mission_type_key",`.
- [ ] Targeted test surface green with no new failures outside the #3284
      baseline recorded in T001. The 8 files:
      `tests/charter/test_mission_type_profiles.py`,
      `tests/charter/test_mission_type_activation.py`,
      `tests/charter/test_mission_type_activation_gating.py`,
      `tests/charter/test_mission_type_activation_emit.py`,
      `tests/charter/test_mission_type_activations_seed_read_parity.py`,
      `tests/specify_cli/cli/commands/charter/test_charter_activate_commands_core.py`,
      `tests/specify_cli/cli/commands/charter/test_charter_activate_commands_cascade_flags.py`,
      `tests/specify_cli/cli/commands/charter/test_charter_activate_commands_cascade_output.py`.
- [ ] SC-001 through SC-005 all satisfied (spec.md "Success Criteria").
- [ ] FR-006 (built-in mission types unaffected) is satisfied by
      construction, not by a new or added test: the new gate inside
      `validate_activatable_mission_type()` only fires for a candidate
      whose resolved action sequence is empty, and every built-in mission
      type resolves a non-empty action sequence by construction. This
      guarantee is locked by the pre-existing
      `tests/runtime/test_runtime_seam.py` golden-parity suite, which this
      mission's diff does not touch and does not need to re-run, since no
      code path for built-in types changes. FR-006 is therefore
      intentionally absent from the targeted test surface and Gate Set
      above, the same way C-006's "skip campsite-clean" decision (plan.md
      "Campsite-clean scope") is stated explicitly rather than left
      implied.
- [ ] `make lint` / ruff run locally as authoring discipline before each
      commit (not a CI gate per this WP's Gate Set below).

## Gate Set

Transcribed from plan.md's "Gate Set" section — this WP's implementer and
reviewer both need this list without re-reading plan.md.

**In scope for this mission:**

- commitlint — every commit message on this branch must pass; binding
  regardless of diff content.
- markdown style lint on changed `.md` files — this mission edits `plan.md`
  and `tasks.md`; both in scope.
- architecture/docs consistency tests on changed markdown.
- template/compat regression tests on matching changes (expected to pass
  trivially — no template file touched by the production diff).
- generated doctrine schemas up to date (runs unconditionally; expected to
  pass with zero regeneration needed).
- Contextive glossary files up to date (runs unconditionally; expected to
  pass with no changes needed).
- banned-API lint gate (TID251) — applies to any `src/` edit; no banned
  import introduced.
- Typer 0.26 JSON error surface — the new `except ValueError` block
  matches the existing two blocks' shape exactly.
- Bandit + pip-audit — run unconditionally; no new dependency, no new
  subprocess/eval/pickle-shaped code.
- `uv.lock` up to date — no dependency added.
- Targeted test shards: `fast-tests-cli` (covers
  `tests/specify_cli/cli/commands/charter/`) and the `fast-tests-core-misc`
  / `integration-tests-core-misc` shard(s) that carry `tests/charter/`.
- clean-install-verification — runs unconditionally on every PR; not
  expected to interact with this diff, but stays in the enforced set.

**Explicitly excluded, with reason:**

- `make lint` (ruff) — LOCAL-ONLY discipline per CLAUDE.md; CI runs ruff as
  `[INFO]` advisory, not enforced. Run locally before each commit as
  authoring discipline, not reported as a PR gate.
- `make typecheck` (mypy --strict) — scoped to exactly one unrelated file
  (`src/specify_cli/runtime/agent_commands.py`); CI job advisory, not
  enforced. Excluded.
- `make test` — a two-file targeted surface unrelated to this mission's
  files. Excluded; the C-004 targeted surface above is the real target.
- SonarCloud Scan / Quality Gate — gated to `schedule`/`workflow_dispatch`
  only; does not run on pull requests. Sonar's code-shaping constraints
  (complexity ceiling 15, no literal repeated >=3 times, no empty `except`
  blocks) are still honored as authoring discipline in the new/refactored
  functions.
- kernel coverage floor (90%), mission-loader coverage (>=90%),
  fast-status / integration-status shards — run unconditionally as part of
  the whole-repo CI matrix but gate files this mission does not touch.
- e2e/cross-cutting, slow shard — whole-repo shards that will run as part
  of CI; not this mission's targeted authoring surface, but must stay
  green as part of the overall PR.

## Risks

The shared test file `tests/charter/test_mission_type_profiles.py` is also
touched by open PRs #3707, #3708, #3711 — routine rebase surface, not a
design conflict (spec.md's Non-goals section already establishes this: PR
#3707 touches a different package tier and adds no activation-time gate;
PR #3708 shares only the test file, production changes live in
`org_expected_artifacts.py`; PR #3711 touches `activate.py` itself but a
different function/concern, cascade rendering). Expect a rebase, not a
conflict investigation, when landing this WP.

## Reviewer Guidance

- Independently verify RED on `planning_base_branch` for T002's tests and
  T003's unit-level extends test, and GREEN on T004 (C-001/C-011) — do not
  accept a self-reported "RED confirmed" without re-running the diff
  yourself against the pre-fix tree.
- Verify the CLI-level AC4 test's documented GREEN-at-commit-2 exception is
  real: confirm it actually asserts today's unconditional-success behavior
  (exit 0, `<T>` present in `mission_type_activations`) and is not a
  vacuous or trivially-true assertion.
- Verify the regression test added in T002 uses the **natural** (not
  pre-seeded) precondition per the SK-81 methodological trap section above
  — `<T>` must be asserted absent from `mission_type_activations`
  immediately before the command under test is invoked, and the org-pack
  YAML must be authored separately from the config fixture (two calls, not
  one). A pre-seeded-only test is a severity-4 finding per spec.md SC-004.
- Confirm `_resolve_action_slot`'s `is_registered` short-circuit was not
  moved, rewritten, or weakened (FR-004) — only its extends-fallback
  computation was factored into the new private helper.
- Confirm `__all__` sort placement (new entry last, after
  `"resolve_mission_type_key",`).
- Confirm no line was added to, or changed in, `activation_engine.py` or
  `pack_manager.py` (C-007 two-file blast radius).
- Confirm FR-006 (built-in mission types unaffected) is satisfied by
  construction: the new gate only fires when a candidate's resolved action
  sequence is empty, and built-in mission types always resolve non-empty
  by construction, so no new test surface is required. This guarantee
  stays locked by `tests/runtime/test_runtime_seam.py`'s golden-parity
  suite, which this WP's diff does not touch and does not need to re-run.

Implementation command: `.venv/bin/spec-kitty agent action implement WP01 --agent <name>`
