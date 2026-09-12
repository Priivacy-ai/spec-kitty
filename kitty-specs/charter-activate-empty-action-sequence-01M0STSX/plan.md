# Implementation Plan: Charter Activation Empty-Action-Sequence Gate

**Branch**: `fix/charter-activate-empty-action-sequence-3702` | **Date**: 2026-08-24 | **Spec**: [spec.md](./spec.md)
**Input**: Mission specification from `kitty-specs/charter-activate-empty-action-sequence-01M0STSX/spec.md`

## Summary

`spec-kitty charter activate mission-type <T>` writes `<T>` into
`.kittify/config.yaml`'s `mission_type_activations` and exits 0 even when `<T>`'s
resolved action sequence is empty, because the read-path guard that would catch this
(`charter/mission_type_profiles.py::_resolve_action_slot`'s
`MissionTypeEmptyActionSequenceError` check) short-circuits to `[]` for any
**unregistered** candidate — and at the moment activation runs, the candidate is by
definition not yet registered. Every later governed entry point that resolves `<T>`
(mission creation, `charter mission-type list`, a second `charter activate`) then
hard-fails, and the CLI gives the operator no way back out.

This plan adds one new **public** function to `src/charter/mission_type_profiles.py` —
`validate_activatable_mission_type()` — that performs the same roster
resolution + single-level `extends` fallback `_resolve_action_slot` already performs,
but unconditionally (not gated on `is_registered`), and raises the existing
`MissionTypeEmptyActionSequenceError` when the result is empty. It is called from
`activate_cmd` in `src/specify_cli/cli/commands/charter/activate.py`, immediately
before `manager = CharterPackManager()` — mirroring the existing
`_emit_step_removal_warnings` preflight one call site above it — so the check runs and
can refuse before any write is attempted. No other module is touched.

## Technical Context

**Language/Version**: Python 3.11+ (repo-pinned; no version change)
**Primary Dependencies**: none added — reuses `doctrine.missions.mission_type_repository.resolve_layered_mission_types`, `doctrine.missions.repository.MissionTemplateRepository`, `charter.pack_context.PackContext` (all already imported by `mission_type_profiles.py` for the same purpose)
**Storage**: `.kittify/config.yaml` (read/write target; this mission narrows *when* it is written, not its schema)
**Testing**: pytest, targeted surface only (see Baseline / Gate Set below) — `.venv/bin/python -m pytest`, never a bare `uv run`
**Target Platform**: spec-kitty CLI (Linux/macOS/Windows via CI matrix; no platform-specific code touched)
**Project Type**: single project (Python package + CLI), no web/mobile split
**Performance Goals**: none new; the added check reuses `resolve_layered_mission_types`'s existing `functools.cache` (keyed on `(mission_types_dirs, pack_context)`), so it does not add a second filesystem walk beyond what `_emit_step_removal_warnings` already triggers one line above it for `kind == "mission-type"`
**Constraints**: C-007 two-file blast radius (binding, confirmed below); NFR-002 `__all__`/dead-symbol obligation (binding); C-011 ATDD red-first (binding)
**Scale/Scope**: 2 production files, 2 test files, ~3 commits, 1 work package

## Constitution / Charter Check

*Gate: charter.md's Governing Principles + Quality & Tech-Debt Standing Orders, re-checked after this design.*

- **Single canonical authority**: the empty-action-sequence defect class has exactly
  one error type (`MissionTypeEmptyActionSequenceError`) and this plan reuses it
  rather than inventing a second. PASS.
- **Architectural alignment**: the new check stays inside the `charter` package tier
  and is invoked from the `specify_cli.cli.commands.charter` tier — the same two
  tiers the pre-existing `_emit_step_removal_warnings` call already crosses at the
  same call site. No new tier crossing. PASS.
- **ATDD-first (C-011)**: sequencing defined below (RED commit before GREEN commit).
  PASS (by construction, verified during implementation).
- **Campsite-clean (standing order 2)**: assessed below — no cleanup commit
  warranted. PASS (explicit no-op, not silence).
- **Red-main acknowledgment (standing order 9 / C-005)**: baseline-capture step
  defined below, before the first change lands. PASS (by construction).
- **`__all__` / dead-symbol discipline (C-007 binding)**: the one new public symbol
  is sized and placed below. PASS (by construction).

No constitution violations requiring the Complexity Tracking table below (left
empty).

## Architecture

### Seam confirmation (spec C-007's two-file blast radius, verified against the read code)

Call graph actually walked for this mission (not paraphrased from the spec):

```
activate_cmd (specify_cli/cli/commands/charter/activate.py:~503)
  -> _emit_step_removal_warnings(kind, artifact_id, repo_root)          [existing, ~line 553]
  -> [NEW] _validate_mission_type_activatable(kind, artifact_id, repo_root)   [new private wrapper, activate.py]
       -> validate_activatable_mission_type(artifact_id, repo_root=repo_root)  [NEW public fn, charter/mission_type_profiles.py]
            -> PackContext.from_config(repo_root)                        [existing]
            -> resolve_layered_mission_types(mission_types_dirs, pack_context)  [existing, cached]
            -> _resolve_with_extends_fallback(mission, roster)           [NEW private helper, same module]
            -> resolve_action_sequence_layer(...)                        [existing, already public]
            -> raise MissionTypeEmptyActionSequenceError(...)            [existing error class]
  -> manager = CharterPackManager()                                      [existing]
  -> manager.activate(...)                                               [existing; unchanged]
       -> plan_activation(...) / commit_plan(...)                        [activation_engine.py; unchanged]
```

Every new line of code lands in exactly the two files C-007 names:
`src/specify_cli/cli/commands/charter/activate.py` (a new private wrapper function
plus one new call + `except ValueError` block, same shape as the existing
`_emit_step_removal_warnings` call immediately above it) and
`src/charter/mission_type_profiles.py` (one new public function + one new private
helper, both reusing symbols the module already imports). `activation_engine.py` and
`pack_manager.py` are read-only reference points in this plan (their existing
contracts are cited to justify the seam) — no line in either is modified. No CLI
command reaches into kernel internals; the new call is a preflight guard ahead of the
manager, the same shape the codebase already uses for the step-removal warning.

### The plan/commit seam resolution (the crux)

**Why not inside `plan_activation()` / `commit_plan()` (`activation_engine.py`)?**
Read against the actual code: `activation_engine.py`'s own module docstring
(lines 1–43, specifically 36–43) states the module "performs no filesystem discovery
and no `config.yaml` load of its own" — inputs arrive **as data** (C-008), and the
single write in `commit_plan()` delegates to a caller-supplied `save` callable so the
engine stays free of I/O. `plan_activation()` (line ~193) validates only that
`artifact_id in set(available_ids)` — membership, not content — before computing
post-state; it has no notion of "action sequence" for any kind. Resolving whether a
candidate's action sequence is empty requires exactly the filesystem-touching
resolution `_resolve_action_slot` performs (walking `mission_types_dirs` +
`pack_context.pack_roots`, invoking `resolve_layered_mission_types`, a
schema-validating YAML load). Putting that resolution inside `plan_activation()` would
violate the module's own documented no-filesystem-discovery contract — this is the
exact non-viability the spec's review already established (`SPEC-GOV-002`,
`reviews/spec.confirmed.yaml`, confirmed+resolved) and the spec's final C-003 text
states this reading explicitly. This plan does not re-litigate it; it implements the
call site C-003 already names.

**Why `activate_cmd` calling a new `mission_type_profiles.py` helper, precisely?**
`activate_cmd` already resolves mission-type-specific, filesystem-touching state via
`_emit_step_removal_warnings(kind, artifact_id, repo_root)` (`activate.py:553`)
immediately before `manager.activate(...)` (`activate.py:560`) — and that existing
function *already* calls `resolve_mission_type_context(repo_root,
mission_type=artifact_id)` internally (`activate.py:181-183`) for exactly this kind,
catching `UnknownMissionTypeError` but *not* `MissionTypeEmptyActionSequenceError`.
Read closely: that existing call does NOT trip on today's bug, because
`resolve_mission_type_context` computes `is_registered = type_key in registered`
(`mission_type_profiles.py:639`) against `existing_mission_types(repo_root)` — the
candidate is by definition not yet in that set, so `_resolve_action_slot`'s
`if not is_registered: return []` (line 967) fires first and the empty-sequence branch
is never reached. This is the precedented, C-007-compatible call site: same file, same
point in the flow, same filesystem-resolution shape, one line below the existing call.

**New helper — exact module, name, signature:**

`src/charter/mission_type_profiles.py`:

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

Plus one private, same-module helper factored out of `_resolve_action_slot` (both
callers converge on it, so the extends-fallback rule is defined once — DRY, and it
carries no `__all__` obligation as an underscored symbol):

```python
def _resolve_with_extends_fallback(mission: MissionType, roster: Mapping[str, MissionType]) -> list[str]:
    """Own action_sequence, or single-level extends fallback if own is empty."""
```

`_resolve_action_slot` is refactored to call `_resolve_with_extends_fallback` after
its existing `mission is None -> raise UnknownMissionTypeError` branch (that branch
stays exactly where it is — FR-004 requires the `is_registered` short-circuit and this
adjacent branch untouched in substance) instead of inlining the same six lines twice.
This is the one behavior-preserving refactor this plan makes inside the read path, and
it is covered by FR-004's own regression suite (existing tests must stay green,
unchanged assertions).

**Exact call site in `activate.py`** — a new private wrapper (mirroring
`_emit_step_removal_warnings`'s `if kind != "mission-type": return` shape, so
`activate_cmd`'s body keeps its "no inline kind branch" discipline), added directly
below that function:

```python
def _validate_mission_type_activatable(kind: str, artifact_id: str, repo_root: Path) -> None:
    """FR-001 preflight: refuse activation of an empty-action-sequence mission type."""
    if kind != "mission-type":
        return
    from charter.mission_type_profiles import validate_activatable_mission_type  # noqa: PLC0415

    validate_activatable_mission_type(artifact_id, repo_root=repo_root)
```

Called in `activate_cmd`, between the existing `_emit_step_removal_warnings` try/except
block (ends `activate.py:556`) and `manager = CharterPackManager()` (`activate.py:558`):

```python
try:
    _validate_mission_type_activatable(kind, artifact_id, repo_root)
except ValueError as exc:
    console.print(f"[red]Error:[/red] {exc}")
    raise typer.Exit(1) from exc

manager = CharterPackManager()
```

Identical shape to the two existing `try/except ValueError` blocks in this function
(`MissionTypeEmptyActionSequenceError` is a `ValueError` subclass, per its class
definition at `mission_type_profiles.py:259`), so FR-003's "same message shape"
requirement is satisfied by construction — the CLI never reformats the message, it
prints `str(exc)` exactly as the two adjacent blocks already do.

### Second write chokepoint (`promote_activations()`) — explicitly scoped out

`promote_activations()` (`activation_engine.py:457`) is a second, pre-existing entry
point onto the same `commit_plan()` write chokepoint `CharterPackManager.activate()`
uses. Verified against the current checkout (not assumed):

- `_PROMOTABLE_KINDS` (`src/specify_cli/upgrade/migrations/m_unify_charter_activation.py:76-84`)
  lists 8 `ArtifactKind` members (`DIRECTIVE`, `TACTIC`, `STYLEGUIDE`, `TOOLGUIDE`,
  `PARADIGM`, `PROCEDURE`, `AGENT_PROFILE`, `MISSION_STEP_CONTRACT`) — no
  mission-type entry, and its own comment states mission-type is deliberately
  excluded ("has no `selected_<kind>` answers key").
- `REQUIRED_KIND_FIELDS` (`src/specify_cli/doctrine/org_charter.py:85-95`) lists 10
  string kinds (`directives` … `assets`) — no `mission_types` field.

No current caller (the config-seeded migration, the interview command, or the
org-pack `required_*` union) can route a mission-type id through
`promote_activations()` today. This plan **does not** add a guard inside
`promote_activations()` or `activation_engine.py` — doing so would require the same
filesystem-touching resolution the crux section above already established is
architecturally non-viable inside that module's data-only contract, so defensive
coverage isn't even cheaply available there without re-opening the C-003/SPEC-GOV-002
question the spec already closed. This is a conscious scoping decision, not silence:
a future mission that widens `_PROMOTABLE_KINDS` or `REQUIRED_KIND_FIELDS` to add
mission-type support would reopen this exact bug class through a path this mission's
`activate_cmd` gate does not touch, and must re-examine this gate at that time. No
new tracker issue is filed for this now — it is a documented, dormant seam, consistent
with the spec's own Edge Cases treatment, not a live defect.

### What is generated

Nothing. This change touches no generated artifact: no doctrine schema (nothing under
`src/doctrine/` is edited), no Contextive glossary file, no agent command copy (no
`packs/built-in/missions/mission-steps/` template is touched), no `uv.lock` (no
dependency added). The "generated doctrine schemas up to date" and "Contextive
glossary files up to date" CI gates run unconditionally on every PR regardless of
diff content; this mission's diff gives them nothing to regenerate.

### Contracts moved

None. Doctrine schemas, mission step contracts, action indices, the
`orchestrator-api` surface, and the vendored `spec-kitty-events` package are
untouched — explicitly preserved. The only contract this mission touches is the
`__all__` surface of `src/charter/mission_type_profiles.py` (one addition, see below)
and the operator-facing exit code / message of one CLI command path that previously
had no gate at all (adding a refusal, not removing or relaxing one).

## Gate Set

Enforced by `.github/workflows/ci-quality.yml` unless noted; verified against the
`[ENFORCED]` step names in that workflow, not assumed from the gate name list alone.

**In scope for this mission:**

- **commitlint** — every commit message on this branch must pass; binding regardless
  of diff content.
- **markdown style lint on changed .md files** — this mission edits `plan.md` (and
  will edit `tasks.md` in the tasks phase); both are in scope for the lint pass.
- **architecture/docs consistency tests on changed markdown** — same reason;
  `plan.md`'s content must not contradict the architecture it documents (which this
  plan takes care to ground in the real call graph, not paraphrase).
- **template/compat regression tests on matching changes** — no template file is
  touched by the *production* diff, but the gate runs on every PR; expected to pass
  trivially (no matching changes).
- **generated doctrine schemas up to date** — runs unconditionally; expected to pass
  with zero regeneration needed (see "What is generated" above).
- **Contextive glossary files up to date** — same: runs unconditionally, no glossary
  term touched by this mission, expected to pass with no changes needed.
- **banned-API lint gate (TID251)** — applies to any `src/` edit; the new code adds
  no banned import (reuses existing lazy-import patterns already present in the same
  module).
- **Typer 0.26 JSON error surface** — `activate.py` is a Typer command file; the new
  `except ValueError` block matches the existing two blocks' shape exactly, so no new
  divergence from the pinned JSON error contract.
- **Bandit + pip-audit** — run unconditionally on `src/`; no new dependency, no new
  subprocess/eval/pickle-shaped code introduced.
- **`uv.lock` up to date** — no dependency added; expected to pass with no lockfile
  change.
- **Targeted test shards this mission's tests fall under**: `fast-tests-cli` (covers
  `tests/specify_cli/cli/commands/charter/`) and the `fast-tests-core-misc` /
  `integration-tests-core-misc` shard(s) that carry `tests/charter/`. Both run with
  coverage; this mission's tests are additive to files already exercised by those
  shards, so no new shard assignment is needed.
- **clean-install-verification** — runs unconditionally on every PR (structurally
  proves `spec-kitty next` runs from a clean install); this mission does not touch
  packaging, entry points, or the install path, so it is not expected to interact
  with the diff, but it is not excludable — it stays in the enforced set.

**Explicitly excluded, with reason:**

- **`make lint` (ruff)** — LOCAL-ONLY discipline per CLAUDE.md: CI runs ruff as
  `[INFO]` advisory in `ci-quality.yml`, not enforced. Will be run locally before
  each commit as authoring discipline, but is not a PR gate to report on.
- **`make typecheck` (mypy --strict)** — scoped to exactly one file,
  `src/specify_cli/runtime/agent_commands.py`, per the Makefile target; this mission
  touches neither that file nor anything importing it as a type dependency, and the
  CI job that runs mypy is advisory (`[INFO]`), not enforced. Excluded.
- **`make test`** — a two-file targeted surface
  (`tests/specify_cli/runtime/test_agent_commands.py`,
  `tests/specify_cli/cli/commands/test_doctor_slash_commands.py`) unrelated to this
  mission's files; not the gate for this diff. Excluded; C-004's own named test
  surface (below) is the real target.
- **SonarCloud Scan / Quality Gate** — gated to `schedule`/`workflow_dispatch` only
  per the workflow's own trigger config; does not run on pull requests. Excluded as a
  PR gate. Sonar's code-shaping constraints (cyclomatic complexity ≤15, no literal
  repeated ≥3 times, no empty `except` blocks) are still honored as authoring
  discipline in the two new functions and one refactored function above — none of
  the three exceeds ~15 lines or introduces a repeated literal.
- **kernel coverage floor (90%, `module-kernel.yml`)**, **mission-loader coverage
  (≥90%)**, **fast-status / integration-status shards** — these run unconditionally
  as part of the whole-repo CI matrix but gate files this mission does not touch
  (`src/kernel/`, the mission loader, the status subsystem); included in the overall
  CI run the PR must pass, but this plan does not target new coverage there because
  the diff has no surface in those trees.
- **e2e/cross-cutting, slow shard** — whole-repo shards that will run as part of CI;
  not this mission's targeted authoring surface (C-004), but must stay green as part
  of the overall PR (no reason to expect them to react to a two-function,
  two-file, `charter`-tier change).

## Baseline (pre-existing red, issue #3284)

Before the first change (including the RED test commit) lands, the targeted test
surface is run against the pre-change tree to record its baseline state, so any red
result later is attributable correctly:

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

on the pre-mission tree (current `HEAD` of this branch, before any mission commit).
Record pass/fail per test. `main` carries ~23 known-red tests + 2 errors (issue
#3284); this mission does not re-litigate or fix that baseline — only tests in the
list above that are RED on the pre-change tree for reasons unrelated to this mission's
own (not-yet-written) RED test are treated as pre-existing baseline noise, not
mission-introduced regressions. SC-005 ("no new failures introduced outside the
pre-existing #3284 baseline") is verified against this recorded baseline, not against
a fresh assumption.

## Campsite-clean scope

No opening campsite-clean commit is warranted. Both touched files
(`src/specify_cli/cli/commands/charter/activate.py`,
`src/charter/mission_type_profiles.py`) are current, heavily-documented, and under
active, concurrent development by sibling missions sharing the same files (spec.md's
Non-goals section: PR #3707 and PR #3708 both touch
`tests/charter/test_mission_type_profiles.py`; PR #3711 touches `activate.py` itself,
a different function). Applying change-scope reconciliation order — smallest-viable-
diff picks the file set first (already pinned to two files by C-007), Boy Scout
cleans only inside that file set, Locality is the brake — there is no drive-by debt
inside either file's touched regions that this mission's own diff exposes; a
cleanup commit here would only widen the rebase-conflict surface against three
concurrently open PRs for zero domain-matched benefit. Explicit decision: skip.

## ATDD Sequencing (charter C-011, binding)

Three commits, in order, all inside the single work package (see WP Shape below).
Because two commits introduce tests, C-011's binding red→green diff is performed
against both: commits 1 and 2 are each diffed against the WP's
`planning_base_branch`. Commit 1's new tests, and commit 2's new unit-level
extends test, must show RED there. Commit 2's new CLI-level AC4 test is a
documented exception (see commit 2 below): it is expected GREEN already at
commit 2, because it pins today's un-fixed, unconditional-success behavior
rather than the fix — it is not part of C-011's RED signal for commit 2. Commit
3 (the `fix:` commit) is diffed to confirm every test added in commits 1–2
is GREEN on it.

1. **`test:` RED commit** — adds the natural-operator-path acceptance test to
   `tests/specify_cli/cli/commands/charter/test_charter_activate_commands_core.py`:
   a new test that (a) authors an org-pack `mission_types/<T>.yaml` with no
   `action_sequence` (equivalent-shape fixture to
   `_write_layered_mission_type_yaml(..., action_sequence=None)`, written locally in
   this file's own existing direct-`write_text` fixture style — this file has no
   `typer.testing.CliRunner`-free precedent for cross-importing private helpers from
   `tests/charter/test_mission_type_profiles.py`, so the two-call fixture shape is
   reproduced locally, not imported), (b) authors `.kittify/config.yaml` declaring the
   org pack via `packs` with `<T>` **absent** from `mission_type_activations` (the
   second, separate fixture call the spec's Edge Case requires — never combined with
   step (a) into one call), (c) asserts `<T>` is absent from `mission_type_activations`
   immediately before invoking, (d) invokes `charter activate mission-type <T>` via
   `CliRunner`, (e) asserts non-zero exit, an error naming `<T>` and layer `org`, and
   `.kittify/config.yaml` byte-identical to its pre-command state. Also adds, in the
   same commit, the supporting unit-level tests in `tests/charter/test_mission_type_profiles.py`
   using the named helpers directly per the spec's literal Edge Case instruction:
   `_write_layered_mission_type_yaml` (empty-sequence case) + `_write_org_pack_config`
   (packs declared, `<T>` omitted from `activated_mission_types`) exercising the new
   `validate_activatable_mission_type()` function directly (raises), a non-empty case
   (no-raise, FR-007 regression shape), and a message-parity assertion comparing the
   new function's raised message against `_resolve_action_slot`'s message for the same
   `(id, layer)` pair (SC-002). **Verify RED on `main`** (equivalently, on this
   branch's `HEAD` before this commit — `planning_base_branch`) — the CLI test fails
   because activation currently succeeds; the unit tests fail with `ImportError`/
   `AttributeError` because `validate_activatable_mission_type` does not exist yet.
   Both are legitimate RED, not accidental collection breakage elsewhere (baseline
   captured above rules that out).

2. **`test:` fixture-widening + AC4 commit** — widens
   `_write_layered_mission_type_yaml` (`tests/charter/test_mission_type_profiles.py:449`)
   with a new `extends: str | None = None` keyword parameter (default preserves every
   existing call site's behavior — a non-breaking widening, not a signature-breaking
   change), and adds the AC4/FR-005 extends-fallback fixture + test: a candidate
   `<T>` with its own `action_sequence=None` and `extends="<parent>"`, a parent with a
   non-empty sequence, asserting `validate_activatable_mission_type()` does **not**
   raise. This is sized explicit work per the spec's Edge Cases instruction (zero
   `extends` precedent existed in this file before this mission), not implicit
   follow-on. Also adds, in the same commit, a CLI-level (`CliRunner`) test in
   `tests/specify_cli/cli/commands/charter/test_charter_activate_commands_core.py`
   mirroring commit 1's CLI-level test shape: it declares an org-pack candidate
   `<T>` with empty own `action_sequence` and `extends` set to a parent with a
   non-empty `action_sequence`, invokes `charter activate mission-type <T>` via
   `CliRunner`, and asserts exit code 0 and that `<T>` is now present in
   `.kittify/config.yaml`'s `mission_type_activations` — closing the gap where
   AC4 previously had only unit-level coverage of
   `validate_activatable_mission_type()` and no end-to-end CLI assertion — unlike
   AC1-2, which get a new end-to-end CLI assertion from commit 1's CLI-level
   test, and AC3, which already has end-to-end CLI coverage from the existing
   healthy-path tests (commit 1 adds only a unit-level regression case for AC3,
   not a new CLI-level test). This CLI-level test is **not** RED against the pre-fix code (activation
   already unconditionally succeeds today for any unregistered candidate,
   including one whose extends chain would resolve non-empty — the bug is
   "always succeeds", not "wrongly fails"; that same absence of a regression is
   also why the unit tests above are RED, not this one). The unit-level test is
   RED, same as commit 1's unit tests. Kept as a separate commit from commit 1
   because it depends on the widened fixture helper, a distinct, reviewable unit
   of test-infrastructure change. **Verify RED**: run the targeted surface
   (Baseline section) after this commit — the new unit-level extends test fails
   with `AttributeError: module 'charter.mission_type_profiles' has no attribute
   'validate_activatable_mission_type'` (the function does not exist yet); the
   new CLI-level test passes already (it asserts today's — currently
   unconditional — success path, not a fix-dependent outcome), so it is expected
   GREEN at this commit and is not part of this commit's RED signal. Confirm the
   `AttributeError` is the only new failure and not accidental collection
   breakage elsewhere (baseline captured in the Baseline section above rules
   that out).

3. **`fix:` GREEN commit** — the production change: add
   `_resolve_with_extends_fallback()` and `validate_activatable_mission_type()` to
   `src/charter/mission_type_profiles.py`, refactor `_resolve_action_slot()` to call
   the new private helper (behavior-preserving), add `validate_activatable_mission_type`
   to `__all__`; add `_validate_mission_type_activatable()` to
   `src/specify_cli/cli/commands/charter/activate.py` and wire its call + `except
   ValueError` block into `activate_cmd` at the exact location above. **Verify GREEN**
   on this commit: every test added in commits 1–2 passes, plus the full targeted
   surface (Gate Set / Baseline section) shows no new regressions relative to the
   recorded pre-change baseline.

## `__all__` / dead-symbol governance (charter C-007, binding)

- `validate_activatable_mission_type` is **public**: its only caller is
  `_validate_mission_type_activatable` in `activate.py` — a real, non-test caller in
  `src/`, satisfying `tests/architectural/test_no_dead_symbols.py`'s "every `__all__`
  name needs a non-test caller" gate without needing a `_SYMBOL_ALLOWLIST` entry.
  Lands in `src/charter/mission_type_profiles.py`'s existing `__all__` list
  (`mission_type_profiles.py:71-83`). The list's existing order is a plain
  case-sensitive `sorted()` (verified: `sorted([...11 existing entries...,
  "validate_activatable_mission_type"]) == [...]` reproduces the file's own
  order with the new entry appended) — under that sort, uppercase-first class
  names group before lowercase-first function names, so the new,
  lowercase-first `validate_activatable_mission_type` sorts as the LAST entry,
  immediately after `"resolve_mission_type_key",` and before the closing
  `]`, not adjacent to `UnknownMissionTypeError`.
- `_resolve_with_extends_fallback` is **private** (leading underscore): no `__all__`
  obligation. Both its callers (`_resolve_action_slot`, `validate_activatable_mission_type`)
  live in the same module.
- `_validate_mission_type_activatable` (in `activate.py`) is **private**: no
  `__all__` obligation, same shape as its sibling `_emit_step_removal_warnings`
  (also private, also uncounted in any `__all__`).
- Confirmed against `tests/architectural/_baselines.yaml`: no existing entry for
  `mission_type_profiles.py` symbols today (grep returns nothing), so this addition
  needs no baseline/allowlist accommodation — it is expected to pass the dead-symbol
  gate on the strength of its real caller alone.

## WP Shape

**One work package, one PR** (single_branch topology default for this repo). The
production diff is two files with one new public function, one new private helper,
one refactor of an existing private function, and one new private CLI-side wrapper —
well under the threshold that would justify splitting into multiple WPs, and C-007
already pins the file set to two. Manufacturing additional WPs (e.g. "test WP" +
"implementation WP") would fragment a change whose ATDD sequencing already provides
the RED/GREEN separation at the commit level, per C-011 — WPs are not required to
mirror commit boundaries 1:1. WP01 carries all three commits above in sequence.

## Project Structure

### Documentation (this mission)

```
kitty-specs/charter-activate-empty-action-sequence-01M0STSX/
├── plan.md              # This file
├── spec.md              # Input (already reviewed/committed; not edited)
├── reviews/              # spec review findings (SPEC-GOV-002 etc.), read for context
├── tracer-*.md           # Mission tracer files (tooling friction / design decisions / approach)
└── tasks.md              # Phase 2 output (tasks phase — not created here)
```

### Source Code (repository root)

```
src/
├── charter/
│   └── mission_type_profiles.py    # + validate_activatable_mission_type (public)
│                                    # + _resolve_with_extends_fallback (private)
│                                    # ~ _resolve_action_slot refactored to call it
│                                    # ~ __all__ gains one entry
└── specify_cli/cli/commands/charter/
    └── activate.py                 # + _validate_mission_type_activatable (private)
                                     # ~ activate_cmd wires one new call + except block

tests/
├── charter/
│   └── test_mission_type_profiles.py                              # + unit tests, extends param widening
└── specify_cli/cli/commands/charter/
    └── test_charter_activate_commands_core.py                      # + 2 CLI-level ATDD tests (AC1-2 RED-first; AC3 stays covered by
                                                                      #   existing healthy-path CLI tests + a new unit-level regression
                                                                      #   case, no new CLI test; AC4 GREEN-at-commit-2)
```

**Structure Decision**: Single project, no new directories. Every file above already
exists; this mission adds functions and one CLI test case to existing files — no new
module, no new test file. `activation_engine.py` and `pack_manager.py` are read-only
reference points (cited in the plan for why the seam resolves where it does) and are
not listed as touched files because no line in either changes.

## Complexity Tracking

*No constitution violations to justify — table intentionally omitted.*
