# Implementation Plan: Mission Type Guard Registry

**Branch**: `kitty/mission-mission-type-guard-registry-01KZY2FG` | **Date**: 2026-08-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/mission-type-guard-registry-01KZY2FG/spec.md`

## Summary

Replace `evaluate_guards`'s `if research / if documentation / else software-dev`
fall-through (`src/runtime/next/runtime_bridge_cores.py:351-374`, verified at this
line range on this checkout) with an explicit `_GUARD_TABLES` registry, author
`plan`'s own guard table so it stops silently inheriting software-dev's
work-package guard, and split the single shared `_cores.evaluate_guards(snapshot)`
call (used identically today by both the legacy path,
`runtime_bridge.py:785-803`'s `_check_cli_guards`, and the composed path,
`runtime_bridge_composition.py:427-486`'s `_check_composed_action_guard`) into two
concrete call sites: a strict lookup the legacy path calls directly (raises on an
unregistered family) and a tolerant, WARNING-logging wrapper the composed path
calls directly (degrades to `[]`, never raises, never borrows software-dev's
verdict). Add `spec-kitty doctor mission-type --json [--fail-on <states>]`,
modeled directly on `doctor identity` (`src/specify_cli/cli/commands/doctor.py:396-444`,
report-builder pattern in `_identity_audit.py`), to surface the same
unregistered/unresolvable-type class proactively. Registered-family behavior
(`software-dev`, `research`, `documentation`) and typeless-mission behavior are
unchanged — this is a refactor-with-extension for those, a genuine (intended) fix
for `plan` and for any composed-path-only custom family, and a defensive,
currently-unreachable strictness for the legacy path.

One first-hand finding this plan surfaces that neither the spec nor the readiness
probe named: `plan`'s new `research` guard needs an artifact-presence check
against `research.md`, but `runtime_bridge_io.py`'s `_PRESENCE_FILE_TAGS` tuple
(the fixed set of filenames `gather_artifact_presence` scans for) does not
currently include `"research.md"` — it must be added there, or the check will
always report the artifact missing regardless of whether `research.md` exists on
disk. This is a small, additive, behavior-preserving change (see IC-02 and
Contracts below).

## Technical Context

**Language/Version**: Python 3.11+ (`pyproject.toml:7` — `requires-python = ">=3.11"`, matches charter.md's Technical Standards)
**Primary Dependencies**: no new third-party dependency. Touches `runtime.next.runtime_bridge_cores` / `runtime_bridge_composition` / `runtime_bridge` (kernel-adjacent runtime seam), `charter.mission_type_key` (`canonical_mission_type_key`), `charter.mission_type_profiles` (`existing_mission_types`), `doctrine.missions.mission_type_repository` (`MissionTypeRepository`), `specify_cli.core.paths` (`load_meta_fail_closed`, `MissionMetaReadError`), `typer` (new CLI command)
**Storage**: none new — reads existing `meta.json` / `.kittify/config.yaml` / doctrine mission-type YAML; no schema, no DB
**Testing**: pytest, targeted surface only (see Gate Set below) — `tests/runtime/test_bridge_cores.py`, `tests/runtime/test_bridge_composition.py`, `tests/next/`, `tests/specify_cli/next/`, `tests/integration/test_custom_mission_runtime_walk.py`, new `tests/specify_cli/cli/commands/test_doctor_mission_type.py`, plus `tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py` (frozen-contract update, see Contracts)
**Target Platform**: Linux/macOS/Windows developer CLI (charter Deployment and Constraints)
**Project Type**: single (Python CLI/library)
**Performance Goals**: `doctor mission-type --json` under 2s for a typical `kitty-specs/` tree (NFR-004, matches `doctor identity`'s existing budget — `identity_audit.py`'s own docstring commits to <3s for 200 missions with a synchronous, subprocess-free walk; this mission reuses the identical walk shape)
**Constraints**: zero behavior change for `software-dev`/`research`/`documentation`/typeless (NFR-001); composed path must never raise for an unregistered family (C-001); legacy path must never silently degrade or fall through (C-002); no roster check added to `validate_meta`/`write_meta` (C-004); targeted test surface only, not the full suite (C-005); complexity ceiling 15 for every new/changed function (NFR-003)
**Scale/Scope**: 2 new small functions + 1 new exception class in `runtime_bridge_cores.py`; ~10-line change split across `runtime_bridge.py` (1 line) and `runtime_bridge_composition.py` (~6 lines); 1-line addition to `runtime_bridge_io.py`'s `_PRESENCE_FILE_TAGS`; 1 new CLI command (thin shell in `doctor.py`) + 1 new sibling module (`_mission_type_audit.py`, combining the roles of both `doctor identity` precedent modules into one file — `specify_cli/status/identity_audit.py` (361 lines: the `IdentityState`/classifier/audit-walk/summarize shape) and `cli/commands/_identity_audit.py` (346 lines: the CLI-glue/report-builder shape) — rather than mirroring either single file's LOC); 1 frozen-contract test file updated (golden CLI surface); new test file(s) for the above. No LOC target is asserted as a commitment — the issue's own "~145 LOC src + ~245 test" figure is explicitly not restated as a target anywhere in spec.md and is not restated here either; the component list above is a verified, first-hand-derived scope statement, not a size estimate.

## Charter Check

*GATE: must pass before Phase 0 research; re-checked after Phase 1 design.*

- **Single canonical authority** — satisfied. The `_GUARD_TABLES` registry is the
  one dispatch authority `evaluate_guards` uses; it does not create a second,
  competing mission-family taxonomy (`doctor mission-type`'s state taxonomy is a
  *diagnostic report*, not a second dispatch table — it reads the same
  `existing_mission_types` / `MissionTypeRepository` the runtime already uses).
- **Architectural alignment** — satisfied. See Seam & Module Placement below: no
  CLI command reaches past a service into kernel internals; `doctor.py` stays a
  thin shell per its own binding docstring ("do NOT add new responsibilities
  here... New subcommand logic belongs in a sibling").
- **ATDD-first (C-011)** — see ATDD-First Sequencing below.
- **Canonical sources, never improvise** — `doctor mission-type` is modeled
  directly on the verified `doctor identity` shape: `doctor.py:396-444` for the
  thin CLI shell, `specify_cli/status/identity_audit.py` (361 lines) for the
  classifier/audit-walk/summarize shape, and `cli/commands/_identity_audit.py`
  (346 lines) for the CLI-glue/report-builder shape — not invented from
  scratch.
- **Campsite cleaning (Standing Order #2)** — see Campsite-Clean Scope below;
  determination made explicitly, not silently skipped.
- **Locality of change / smallest-viable-diff** — the file set is bounded to the
  six production files and four test files named in Project Structure below
  (the three-file runtime guard-dispatch seam, `runtime_bridge_io.py`,
  `doctor.py`, and `_mission_type_audit.py`, plus the four test files
  including the golden-contract test the new command mechanically requires
  updating); C-003's mission-scope boundary (out of scope: the override
  hatch, the two divergent meta readers, the dashboard default, the wider
  unverified census) is respected — none of those files are touched.

Section satisfied; no complexity violations to justify (see Complexity Tracking).

## Seam & Module Placement

This mission touches exactly one seam-family: the **kernel-adjacent runtime
guard-dispatch seam** (`src/runtime/next/`) and its **CLI-layer diagnostic
sibling** (`src/specify_cli/cli/commands/`). No new module, no cross-seam
reach-through.

**Runtime seam** (`src/runtime/next/`) — verified first-hand on this checkout
(all citations below re-checked against the actual file content, not carried
over from spec.md unchecked; two of the four functions User Story 3 names live
in a *different* file than a literal reading of spec.md's prose might suggest —
noted explicitly):

- `runtime_bridge_cores.py` — the **pure, zero-dependency leaf** (its own module
  docstring: "may import stdlib, `Lane`/decision types, and nothing else...
  Every function here is pure: no filesystem, no git, no `meta.json` reads").
  This is where the registry itself lives, because it is the module that already
  owns `evaluate_guards` (def at line 351, body through line 374),
  `_evaluate_research_guards` (415), `_evaluate_documentation_guards` (439,
  whose existing terminal-step precedent is the literal two lines 455-456: `if
  action == "accept": return []  # terminal status commit step; publish gate is
  sufficient`), and `_evaluate_software_dev_guards` (554). Changes here:
  - Add `_GUARD_TABLES: dict[str, Callable[[_ArtifactPresenceSnapshotLike], list[str]]]`
    mapping `"research"` / `"documentation"` / `"software-dev"` / `"plan"` to
    their four evaluator functions (`Callable` is already imported at line 73 —
    zero new imports).
  - Add `class UnregisteredMissionFamilyError(ValueError)` — a **new, local**
    exception, deliberately NOT importing or reusing `charter.mission_type_profiles.UnknownMissionTypeError`.
    Two independent reasons: (1) this module's own zero-dependency-leaf
    invariant forbids importing `charter` at all; (2) the two exceptions answer
    different questions at different layers — `UnknownMissionTypeError` is
    about whether a mission TYPE resolves to a loadable governance/action-slot
    profile at the charter layer; `UnregisteredMissionFamilyError` is about
    whether a guard-evaluation FAMILY string has a `_GUARD_TABLES` entry at the
    runtime layer. They rhyme in shape (both carry the offending string) but
    are not the same concept, and collapsing them would create exactly the
    kind of cross-layer coupling the module docstring's "in particular NEVER"
    list exists to prevent. Because the two exception classes "rhyme in shape"
    (both `ValueError` subclasses carrying the offending string) but live at
    different layers with no other code-level link between them, the
    implementation's docstring for `UnregisteredMissionFamilyError` must
    include a one-line cross-reference comment naming the sibling explicitly —
    e.g. "Sibling concept: `charter.mission_type_profiles.UnknownMissionTypeError`
    — same shape (ValueError carrying the offending string), different layer
    (runtime guard-family dispatch vs charter mission-type resolution);
    intentionally not unified, see plan.md's Seam & Module Placement for the
    two-independent-reasons rationale" — so a future maintainer touching one
    taxonomy has an in-code signal to check the other.
  - Add `def evaluate_guards_strict(snapshot) -> list[str]:` — looks up
    `_GUARD_TABLES.get(snapshot.mission_family)`; calls it if found; raises
    `UnregisteredMissionFamilyError(snapshot.mission_family)` if not.
  - Change `evaluate_guards(snapshot) -> list[str]` (the existing public name,
    kept byte-identical in signature so every existing direct caller —
    including `tests/runtime/test_bridge_cores.py`, per SC-004's
    unmodified-test requirement — keeps working unmodified) to a **tolerant,
    still-pure** wrapper: `try: return evaluate_guards_strict(snapshot) except
    UnregisteredMissionFamilyError: return []`. No logging call is added here —
    logging stays out of this module deliberately (see next bullet) so the
    "every function here is pure" invariant is not broken by a new I/O side
    effect. After this mission both production call sites (`runtime_bridge.py`
    and `runtime_bridge_composition.py`) bypass this tolerant wrapper in favor
    of `evaluate_guards_strict` directly (IC-03/IC-04) — `evaluate_guards()`
    stays public only for `tests/runtime/test_bridge_cores.py`'s existing
    direct callers (SC-004's unmodified-test requirement). Its docstring must
    say so explicitly: a one-line note that it is kept tolerant/public only
    for existing direct test callers, and that any new production call site
    should use `evaluate_guards_strict` instead so an unregistered family is
    never silently swallowed.
  - Add `def _evaluate_plan_guards(snapshot) -> list[str]:` (FR-002) — a 5-way
    `if`/`elif` chain (`specify` → `spec.md` via the existing `SPEC_ARTIFACT`
    constant; `research` → the literal `"research.md"`, a **new** one-off
    string, not currently a module constant since it is used exactly once here
    — see the "local literal duplicates" convention this module's own header
    comment already documents for `SPEC_ARTIFACT`/`PLAN_ARTIFACT`/`TASKS_ARTIFACT`,
    lines 79-91; `plan` → `plan.md` via the existing `PLAN_ARTIFACT` constant;
    `review` → `[]` with a comment citing the direct analogy to
    `_evaluate_documentation_guards`'s `accept` case at lines 455-456; anything
    else → a fail-closed `[f"No guard registered for plan action: {action}"]`,
    matching the research/documentation families' own unknown-action
    fail-closed convention). Complexity: ~5-way flat `if`/`elif`, far under the
    ceiling of 15 (NFR-003).

- `runtime_bridge_composition.py` — the **composed path's actual implementation
  site** (its module already owns `_check_composed_action_guard`, def at line
  427, body through 486, and already has `logger = logging.getLogger("runtime.next.runtime_bridge")`
  at line 101 and an established WARNING/ERROR-logging convention via
  `_dispatch_via_composition`'s own `logger.exception(...)` at line 567). The
  function's current last line, `return _cores.evaluate_guards(snapshot)`
  (line 486), changes to a try/except that calls `_cores.evaluate_guards_strict(snapshot)`
  directly, catches `_cores.UnregisteredMissionFamilyError`, logs at
  **WARNING** naming the unregistered `mission` value, and returns `[]` (FR-003,
  FR-004, C-001). `_cores` is already imported at line 88 — zero new imports.
  This is the destination FR-004 names explicitly ("the composed path's actual
  implementation site, not `runtime_bridge.py`") and the verification above
  confirms `runtime_bridge.py`'s own `_check_composed_action_guard` (line 983,
  re-verified post-#3346-rebase — this compat delegate shifted +105 lines
  from its plan-authoring-time location at line 878; the code itself is
  byte-identical, only its line number moved)
  is a thin compat delegate that forwards here — the log call must not be added
  to that delegate, only to this real implementation.

- `runtime_bridge.py` — the **legacy/CLI-native residual + compat-delegate
  facade**. `_check_cli_guards` (def at line 785, body through line 803 —
  re-verified against the current checkout after the mission branch's rebase
  onto `main` @ `7923fda40` (#3346, "isolate explicit owned-checkout mission
  state"), which added 182 lines to this file starting at line 233 and shifted
  every citation below it by +105 lines through this point in the file; the
  guard-dispatch code itself is unchanged, byte-for-byte, from this plan's
  original verification — only line numbers moved) has its last
  line, `return _cores.evaluate_guards(snapshot)` (line 803), changed to `return
  _cores.evaluate_guards_strict(snapshot)`. No try/except is added — letting
  `UnregisteredMissionFamilyError` propagate uncaught IS the "raise loudly"
  requirement (C-002); `_check_cli_guards` itself hardcodes
  `mission_family="software-dev"` unconditionally at line 797 today (confirmed:
  this is the ONLY call site that ever populates `mission_family` for this
  function — grep across `src/` finds no other caller reaching
  `_check_cli_guards` with a different family), so this raise path is real,
  wired, and currently unreachable by any existing caller — exactly the
  "defensive correctness, not a live defect today" framing User Story 3 states.
  `_cores` is already imported at line 162 — zero new imports. This satisfies
  FR-005 and User Story 3 Acceptance Scenario 3's exact requirement:
  `_check_cli_guards` itself is the direct, real caller of the strict lookup,
  not an isolated unit-tested-but-unwired helper.

- `runtime_bridge_io.py` — **the one file not named by spec.md's citations that
  this plan's own verification found necessary.** `_PRESENCE_FILE_TAGS` (a
  9-tuple at lines 708-718: `"spec.md"`, `"plan.md"`, `"tasks.md"`,
  `"source-register.csv"`, `"findings.md"`, `"report.md"`, `"gap-analysis.md"`,
  `"audit-report.md"`, `"release.md"`) is the fixed set of filenames
  `gather_artifact_presence` scans for with `Path.is_file()` to build
  `present_artifacts`. It does not include `"research.md"`. Without adding it,
  `_check_artifact_present(snapshot, "research.md")` inside the new
  `_evaluate_plan_guards` would always report the artifact missing, even when
  `kitty-specs/<slug>/research.md` genuinely exists — a real, silent-again
  defect this mission would otherwise ship inside its own fix. The change is
  one line: add `"research.md"` to the tuple. **Why this is safe for NFR-001**:
  `present_artifacts` is purely additive — adding a new tag can only make a
  NEW `tag in snapshot.present_artifacts` check (used exclusively, and only
  once, by `_evaluate_plan_guards`'s `research` branch) succeed when the file
  exists; no existing family's guard function reads the `"research.md"` tag
  (verified directly: this literal string does not appear anywhere in
  `runtime_bridge_cores.py` today), so `research`/`documentation`/`software-dev`/
  typeless behavior is provably unaffected. The module docstring's own claim
  ("mirrors the exact set of ... reads ... across all three mission families")
  gets a one-line update to say "all four" once `plan` is added.

**CLI seam** (`src/specify_cli/cli/commands/`) — new diagnostic surface, modeled
directly on the verified `doctor identity` shape:

- `doctor.py` — add one thin `@app.command(name="mission-type")` shell (mirrors
  `identity`'s shell exactly, lines 396-444: `--json` flag, `--mission` scoping
  option, `--fail-on` comma-separated-states option; resolves `repo_root` via
  the same `locate_project_root()` try/except; delegates immediately to the
  sibling). This file's own binding docstring already states the rule this
  mission follows: "New subcommand logic belongs in a sibling, not here; this
  file stays a thin shim of command shells." Import line mirrors line 97-98's
  exact pattern: `from ._mission_type_audit import (  # noqa: E402\n
  run_mission_type_audit,\n)`.
- `_mission_type_audit.py` (**new sibling module**, combines the roles of
  BOTH `doctor identity` precedent modules into one file: the domain-layer
  shape of `specify_cli/status/identity_audit.py` (361 lines —
  `IdentityState`, `classify_mission`, `audit_repo`, `summarize`) and the
  CLI-glue/report-builder shape of `cli/commands/_identity_audit.py` (346
  lines — `run_identity_audit`, `_build_identity_json`, `_compute_fail_on`) —
  rather than splitting into that same two-module shape, because mission-type
  resolution logic already lives entirely in `charter`/`doctrine` and does not
  need a second domain-layer home; this is the smallest-viable-diff shape, at
  the real combined-precedent LOC scale, not a 1:1 mirror of either single
  file):
  - `MissionTypeState` dataclass — `path`, `slug`, `mission_type_raw:
    str | None`, `resolved_key: str | None`, `state` (the FR-008 6-value
    `Literal`), `error: str | None`. `to_dict()` mirrors `IdentityState.to_dict()`.
  - `classify_mission_type(feature_dir, *, registered: list[str], repo:
    MissionTypeRepository) -> MissionTypeState` — the FR-008 taxonomy
    classifier (exact decision procedure below); takes the activation set and
    the built-in-bundle repository as parameters (computed ONCE per audit run
    by the caller) rather than re-resolving them per mission, avoiding N
    redundant `.kittify/config.yaml` reads across a `kitty-specs/` tree
    (NFR-004 performance discipline).
  - `audit_mission_types(repo_root) -> list[MissionTypeState]` — walks
    `kitty-specs/` exactly like `identity_audit.audit_repo` (same
    `safe_is_dir`/`KITTY_SPECS_DIR` pattern), computing `registered =
    existing_mission_types(repo_root)` and `repo = MissionTypeRepository.default()`
    once before the loop.
  - `summarize_mission_types(states) -> dict[str, object]` — per-state counts,
    zero-filled across all six states (mirrors `identity_audit.summarize`).
  - `run_mission_type_audit(repo_root, json_output, mission, fail_on) -> None`
    — the command entry point; mirrors `run_identity_audit`'s exact shape
    (`_compute_fail_on`-equivalent parsing, JSON builder, human-print,
    `typer.Exit(1 if fail_on_triggered else 0)`).

**FR-008 taxonomy classifier — the exact decision procedure** (this is the
concrete design decision SPEC-VERIFY-004 asked the plan to pin down, not left
to each WP's own reading):

1. Read `meta.json` via the same fail-closed reader `classify_mission` already
   uses (`specify_cli.core.paths.load_meta_fail_closed` / `MissionMetaReadError`).
   On `OSError` / `MissionMetaReadError` → state `error` (mirrors `identity`'s
   `orphan`-on-unreadable-metadata posture, per the Edge Cases section).
2. If the raw dict has a `"mission_type"` key (checked by key presence, `"mission_type"
   in raw`, not by truthiness):
   - `raw_val = raw["mission_type"]`; `key = canonical_mission_type_key(raw_val) if
     isinstance(raw_val, str) else None`.
   - If `key is None` (blank string, `null`, or a non-string value) → state
     `typeless`. This is the literal, explicit reading of FR-008's boundary
     sentence: a *present-but-blank/null/non-string* `mission_type` key
     classifies as `typeless` **regardless of what the legacy `mission` key
     contains** — the key's own presence-with-a-value is what routes into this
     branch at all; a present-but-empty value never falls through to check the
     legacy key. (A boundary test for this exact case — `mission_type: ""` with
     a real string in the legacy `mission` key, still `typeless` — is added per
     FR-008's own closing sentence.)
   - Else (`key` is a non-blank string) → `is_registered = key in registered`.
     - Not registered → state `unknown`.
     - Registered, and `repo.get(key) is not None` → state `resolved`.
     - Registered, but `repo.get(key) is None` → state `activated-unresolvable`
       (this is the exact branch `_resolve_action_slot` in
       `charter/mission_type_profiles.py` already hits at its own `raise
       UnknownMissionTypeError(...)` call, line 799 — "activated but has no
       YAML definition in the built-in doctrine bundle" — reused here as a
       read-only classification instead of a raise).
3. Else (no `"mission_type"` key at all):
   - `raw_legacy = raw.get("mission")`; `legacy_key = canonical_mission_type_key(raw_legacy)
     if isinstance(raw_legacy, str) else None`.
   - `legacy_key is not None` → state `legacy-key-only`.
   - `legacy_key is None` → state `typeless`.

This procedure deliberately does **not** call `_canonical_meta_mission_type`
(`specify_cli/mission.py:542-556`) directly, even though it uses the same
`canonical_mission_type_key` primitive that function uses — `_canonical_meta_mission_type`
collapses "which key produced this key" into a single winner-takes-all string,
which is exactly the information FR-008's `legacy-key-only` state needs to keep
visible. Reusing the shared *primitive* (not the shared *reader function*) is
the correct level of reuse here — the two divergent-meta-readers defect
(Out of Scope item 2) is explicitly not being fixed or worked around by this
choice, only avoided as an accidental dependency.

## Contracts

**No contract moves.** This mission does not touch: doctrine schemas, mission
step contracts, action indices, the orchestrator-api surface, or the vendored
`spec-kitty-events` / `spec-kitty-tracker` PyPI packages. The `_GUARD_TABLES`
registry is an **internal runtime implementation detail** (private, `_`-prefixed
where applicable; `evaluate_guards`'s public name and signature are unchanged);
`plan`'s `mission-runtime.yaml` action sequence (`specify → research → plan →
review`) is unchanged — only the guard evaluated *at* those existing steps
changes. `doctor mission-type` is a **new** CLI surface, not a change to an
existing one, so there is no existing contract to preserve or break for it.

**One frozen, hand-maintained test contract IS touched, deliberately and
necessarily**: `tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py`.
This is not a code-generated artifact (nothing regenerates it from a command);
it is a hand-authored golden characterization test that pins the `doctor`
group's exact subcommand set, option contract, and `--help` text
byte-for-byte, by frozenset equality (`test_registered_command_names_match_frozen_subcommands`,
line 475-482) and parametrized per-subcommand assertions (lines 504-528).
Adding `doctor mission-type` as a real, registered Typer subcommand WILL fail
this test's `FROZEN_SUBCOMMANDS` equality check unless the mission's own diff
updates, in the same commit as the new command:
- `FROZEN_SUBCOMMANDS` (line 56-78): add `"mission-type"`, and update the
  count comment at line 11 (19 → 20).
- `EXPECTED_OPTIONS` (line 82+): add `"mission-type": {"--json": "flag",
  "--mission": "value", "--fail-on": "value"}` (identical shape to
  `identity`'s own entry, line 93).
- `EXPECTED_HELP` (line 120+): add the new command's exact, whitespace-
  normalized `--help` snapshot (authored at implementation time from the
  command's actual docstring — the golden test captures whatever text ships,
  it does not prescribe the text in advance).
This is the one place in this mission where "what looks like a docs-only test
file" is actually load-bearing production-contract enforcement — calling it out
explicitly here so no WP treats it as optional or discovers it only via a late
CI failure.

**`__all__` note**: `src/runtime/next/runtime_bridge.py` declares `__all__`
(lines 2655-2664); none of the symbols this mission touches or adds
(`_check_cli_guards`, `evaluate_guards`, `evaluate_guards_strict`,
`UnregisteredMissionFamilyError`) are `_`-unprefixed public names, and none
need adding to that list. `runtime_bridge_cores.py` and
`runtime_bridge_composition.py` do not declare `__all__` and are not required
to (charter's C-007 `__all__` convention binds only `src/charter/` and
`src/kernel/`).

## Baseline & Reflexivity

**Captured baseline (first-hand, this plan-authoring session, commit
`7deadff0a4f3dfd2744b5e1e35680c0d70f4565e`, 2026-08-13T20:29:55+02:00)** —
this supersedes NFR-001/SC-004's more hedged framing (SPEC-VERIFY-005) with an
actual number, run before any change lands:

```
$ .venv/bin/python -m pytest tests/runtime/test_bridge_cores.py tests/runtime/test_bridge_composition.py -q
71 passed in 4.48s

$ .venv/bin/python -m pytest tests/next/ tests/specify_cli/next/ tests/integration/test_custom_mission_runtime_walk.py -q
713 passed in 107.86s
```

784 tests total, 0 failed, across every file NFR-001/NFR-002/C-005 name
(`test_bridge_cores.py`, `test_bridge_composition.py`, all of `tests/next/`
— which contains `test_runtime_bridge_unit.py` and
`test_occurrence_gate_next_loop.py`, confirmed present — all of
`tests/specify_cli/next/` — which contains `test_runtime_bridge_composition.py`,
`test_runtime_bridge_dispatch.py`, and
`test_workflow_software_dev_default_is_byte_stable.py`, all confirmed present
— and `test_custom_mission_runtime_walk.py`). This IS the pre-mission baseline
referenced below; it is not an estimate and not a claim about the full
~17,000-test suite.

**Verification method (NFR-001, supersedes the spec's "all green" framing per
SPEC-VERIFY-005's own remediation)**: re-run the exact same four commands
(the two above, split as shown, since that split is what was actually run and
is faster to re-run in isolation during iteration) after each implementation
commit. The bar is **zero NEW reds relative to the 784-passed/0-failed baseline
above** — not "all green" unconditionally, and not a claim that any test's
*assertion values* change (SC-004: `test_bridge_cores.py` and
`test_bridge_composition.py` pass **unmodified**, zero assertion-value edits).
If a red appears that is NOT attributable to this mission's diff, classify it
per CLAUDE.md's baseline-red gotcha (pre-existing known-P0 / CI-environment /
stale-install) before treating it as introduced — cite #3284 (a real, open
red-main tracking issue — "main full suite has 23 untracked failures and 2
errors after bootstrap prewarm" — independently confirmed via `gh issue view
3284`; not yet cross-referenced from CLAUDE.md or spec.md, so name it fresh
rather than pointing at an existing reference) rather than filing a duplicate. None of the 784 tests captured above were red at baseline, so any
red appearing in this specific set during implementation is, by construction,
this mission's own regression to fix before proceeding — the "which category"
question only has real teeth for tests outside this targeted set (i.e., if a
full-suite run is ever done post-merge per C-005's own carve-out).

**Reflexivity — what happens to a mission mid-flight when this merges**, per
family:

- `software-dev` / `research` / `documentation` (registered today): NFR-001
  guarantees identical `evaluate_guards` output for every `step_id` and
  snapshot shape, before and after. A mission mid-flight on any of these three
  families sees zero behavior change on its next `next` call — the 784-test
  baseline above is the mechanism that proves this, not an assumption.
- `plan` (registered by this mission, User Story 2): a mission mid-flight on
  `plan` that has already been silently hitting the WP-iteration guard message
  at its `review` step will, after this mission merges, see that guard clear
  (return `[]`) on its next `next` call — this is the intended fix landing
  under the mission's feet, not a regression; no other step's behavior for
  `plan` changes (its `specify`/`research` steps had no guard AT ALL before this
  mission — `evaluate_guards` fell through to `_evaluate_software_dev_guards`,
  whose `specify`/`plan` branches happen to check `spec.md`/`plan.md` presence
  already by coincidence of shared step-id naming with software-dev's own
  steps, but `plan`'s `research` step had no software-dev equivalent at all and
  fell through to the software-dev chain's `return []` default at line 566 —
  meaning a mid-flight `plan` mission's `research` step guard goes from
  "always passes, checks nothing" to "checks for `research.md`" after this
  mission. This is a second, smaller behavior change for `plan` beyond the
  `review`-step fix, and it is squarely inside FR-002's own scope, not an
  incidental side effect — flagged here so no reviewer discovers it late.)
- A custom, composed-path-only family not in
  `{software-dev, research, documentation, plan}` (User Story 1 / Edge Cases):
  before this mission, a mid-flight mission of such a family silently received
  software-dev's verdict (the defect). After, it receives the explicit
  neutral-degrade `[]` plus a WARNING log line. This IS an intended behavior
  change for that one case (never a regression into a raised exception or a
  fresh silent misfire) — explicitly called out as such in spec.md's Edge Cases
  and restated here because it is the one case where "mid-flight behavior
  changes" is the correct, intended outcome rather than a violation of NFR-001.
- Typeless missions (`mission_family=None`): untouched by any change in this
  plan — `_GUARD_TABLES` is keyed by string family names; `None` never reaches
  a dict lookup differently than it does today (the existing dispatch already
  only branches on `snapshot.mission_family == "research"` / `"documentation"`
  string equality, so `None` already fell through to software-dev before this
  mission and continues to do so after, unchanged — this is the existing,
  independently-pinned typeless-neutrality behavior NFR-001 and the Edge Cases
  section both require this mission not to touch, and this plan does not touch
  it).

## Campsite-Clean Scope

Explicit determination (Standing Order #2 requires stating this, not silently
skipping it): I checked `runtime_bridge_cores.py`'s guard-evaluation section
(lines 348-567), `runtime_bridge.py:670-699` (re-verified post-#3346-rebase:
now `runtime_bridge.py:775-804`, shifted +105 lines — same code, new
coordinates), and
`runtime_bridge_composition.py:427-486` — the exact lines this mission's
functional change touches — for pre-existing, unrelated Sonar findings,
complexity violations, or stale in-code citations (distinct from spec.md's own
SPEC-VERIFY / SPEC-ARCH review findings, all of which were prose-only fixes
already committed to spec.md, not code). **Found none**: NFR-003 already
confirms no touched function is near the complexity ceiling; no stale
line-number citation exists in these files' own comments (the historical
citations in `runtime_bridge_cores.py`'s module docstring, e.g. "moved
VERBATIM from `runtime_bridge.py:343-473` (pre-decomposition line numbers)",
are deliberately historical provenance records, not live cross-references, and
are correct as historical records). **Conclusion: this mission has no distinct
campsite-clean-first commit.** The first commit in sequence is the FR-010
ATDD red-first test (see below), not a tidy-up commit; the registry/split/
`doctor` changes land in the implementation commit(s) that follow it. The one
file this mission DOES need to update purely because the new command's
existence mechanically requires it — the golden CLI-surface test (see
Contracts) — is not "debt cleanup," it is a direct, necessary consequence of
FR-007's own scope and is folded into the `doctor mission-type` implementation
commit, not treated as a separate cleanup pass.

## ATDD-First Sequencing (charter C-011, binding)

Every changed behaviour gets a failing-first test, committed as a separate
commit before the implementation that turns it green, verified RED on the
mission's base commit (`7deadff0a4f3dfd2744b5e1e35680c0d70f4565e`, the captured
baseline above) and GREEN on the final commit:

1. **Commit 1 (RED, FR-010)** — the live `plan`-type defect's ATDD pin: a test
   driving (or directly constructing) a `plan`-family snapshot at `step_id="review"`
   with no `tasks/` directory, asserting the target/fixed shape directly — an
   empty guard-failure list, `[]`. This assertion is genuinely RED against the
   base commit: today `evaluate_guards` returns `["Not all work packages are
   approved or done"]` for this exact snapshot (the bug's own output), so
   asserting `[]` fails for the right reason until the fix lands, satisfying
   DIRECTIVE_034's "prove red-first" requirement directly. No separate
   "asserting today's actual output" pin is added and none is deferred to a
   later phase — the target-shape assertion alone proves the flip, is
   committed whole in this one commit before any implementation commit (C-011),
   and turns GREEN in the implementation commit that follows, with nothing
   left over to remove or convert once the fix lands. Location: extends
   `tests/runtime/test_bridge_cores.py` (or a new file under
   `tests/runtime/` if the reviewer squad prefers a dedicated FR-010 file —
   left to tasks-phase judgment, not fixed here).
2. **Commit 2 (RED, FR-011)** — the previously-uncovered fall-through itself:
   a test feeding a synthetic unregistered `mission_family` (e.g.
   `"totally-unregistered-family"`) to (a) `evaluate_guards_strict` directly,
   asserting it raises `UnregisteredMissionFamilyError`; (b) `_check_cli_guards`
   via an injection seam, asserting the same exception propagates out of
   `_check_cli_guards` itself (User Story 3 AC3 / FR-005's real-call-chain
   requirement); (c) `_check_composed_action_guard`, asserting `[]` is returned
   AND a WARNING-level log record naming the family was emitted (FR-003/FR-004/
   SC-002). All three assertions are RED against the base commit (none of
   these code paths or the exception class exist yet).
3. **Implementation commit(s)** — the registry, the split call sites, the
   `_PRESENCE_FILE_TAGS` addition, and `plan`'s guard table land together (they
   are one coherent, small change — see Campsite-Clean Scope above for why they
   are not further split by a tidy-up pre-commit). Commits 1 and 2 flip to
   GREEN.
4. **`doctor mission-type` commit(s)** — the new CLI command + sibling module,
   with its own ATDD test committed first (`test_doctor_mission_type.py`
   asserting the fixture-tree classification behavior of SC-005/SC-006 fails
   against the base — the command does not exist yet, so this is trivially
   RED — then the command implementation lands and it goes GREEN). Includes
   the FR-008 boundary test case (blank/null/non-string `mission_type` →
   `typeless`, per the Seam & Module Placement section's exact decision
   procedure).
5. **Golden-contract commit** — the `test_doctor_cli_surface_golden.py` update
   is folded into commit 4 (it is a direct, mechanical consequence of the new
   command existing, not a separate concern) — not its own ATDD pin (there is
   no new *behavior* here, only a frozen-contract update reflecting behavior
   commit 4 already introduces).

## PR Shape

**One PR for the whole mission** — the spec-kitty default (not Team Kitty's
per-WP convention). Rationale: the touched-file set is small and coherent (6
production files + 4 test files, including the golden-contract test — see
Project Structure below for the full manifest), the behavior
change is a single conceptual unit (close one silent-fallback defect class
across two call paths, plus one diagnostic command that reads the same
underlying facts), and none of the charter's "split it" triggers apply — no
migration-chain touch, no contract move, no cross-repo coordination. If the
implementation phase discovers the diff growing meaningfully beyond the
Implementation Concern Map below (e.g. the golden-contract update turns out to
ripple into other doctor-surface tests not identified here), that discovery is
itself a signal to STOP and re-scope rather than silently exceed C-003's
mission-scope boundary — but the verified scope above does not present that
risk.

## Gate Set

Enforced for this mission, with an explicit reason for every listed gate NOT
included:

| Gate | Status | Why |
|---|---|---|
| Targeted pytest surface | **Enforced** | `tests/runtime/test_bridge_cores.py`, `tests/runtime/test_bridge_composition.py`, `tests/next/`, `tests/specify_cli/next/`, `tests/integration/test_custom_mission_runtime_walk.py`, new `tests/specify_cli/cli/commands/test_doctor_mission_type.py`, `tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py` — the exact set named by C-005 plus the one golden-contract file Contracts identifies. Verified baseline: 784 passed, 0 failed (see Baseline & Reflexivity). |
| `mypy --strict` | **Enforced** | Charter Testing Requirements, binding. New code: the registry dict, the new exception class, `_evaluate_plan_guards`, `_mission_type_audit.py`. |
| `ruff check` (incl. C901 complexity ≤15) | **Enforced** | Charter Sonar Expectations. NFR-003 restates this for the guard functions specifically; `_evaluate_plan_guards` and the `_mission_type_audit.py` classifier are both flat, low-branch-count functions well under the ceiling. |
| `pytest tests/architectural/test_no_legacy_terminology.py` | **Enforced, pre-push** | `doctor mission-type`'s `--help` text is new user-facing prose (charter's own "Pre-push" rule names this exact scenario); this gate runs only in CI's `integration-tests-core-misc` job, not the fast-tests shards, so it must be run locally before push, not assumed from local fast-test green. |
| `tests/architectural/test_shared_package_boundary.py` / `test_pyproject_shape.py` | **Runs on this PR (`arch-adversarial`, always-on), expected to pass** | `arch-adversarial`'s job-level `if:` gate carries no path filter and always fires on every push of this PR — not only incidentally at a separate merge-time full-suite run (`.github/workflows/ci-quality.yml:2144`, job definition; `if:` condition at line 2147: `(always()) && !contains(github.event.pull_request.labels.*.name, 'pr:deferred') && !contains(github.event.pull_request.labels.*.name, 'pr:skip-ci')`) — the only *job-level* opt-outs are the `pr:deferred`/`pr:skip-ci` PR labels. The job's own run step then applies a second, runtime diff-content-based narrowing: a "Detect docs-only PR" step (`ci-quality.yml:2201-2220`) diffs the PR base against HEAD, and the "Run architectural + adversarial suite" step (`ci-quality.yml:2228-2265`) collapses the pytest marker selection to `-m '<shard> and docs_scoped and not windows_ci'` (line 2241) when the changeset is docs-only, versus the full `-m '<shard> and not windows_ci and (git_repo or integration or architectural) and not timing'` selection (line 2258) otherwise — so a docs-only/non-docs-only distinction does exist, just at test-selection time inside the job rather than at its `if:` gate. Neither `test_shared_package_boundary.py` (`pytestmark = pytest.mark.architectural`, line 11) nor `test_pyproject_shape.py` (same, line 13) carries the `docs_scoped` marker, so on a hypothetical docs-only PR neither file would actually run within this job. That carve-out does not apply here: this mission's real PR touches `src/runtime/next/*` and `src/specify_cli/cli/commands/*`, so it is never docs-only, and the full (unnarrowed) marker selection runs, including both files. No dependency, `pyproject.toml`, or `spec-kitty-events`/`spec-kitty-tracker` import is touched by this mission, so both are expected to pass. |
| Doctrine schema freshness / Contextive glossary | **Runs on this PR, expected to pass** | Not skipped: the Contextive-glossary step is triggered by this mission's own `src/specify_cli/**` changes (`ci-quality.yml:848-869`'s path filter includes `src/specify_cli/**`, and this mission changes/adds files under it), and the doctrine-schema-freshness step (`ci-quality.yml:653`) is not path-gated at all — it runs whenever the always-invoked `lint` job runs, deliberately placed there per its own comment ("a freshness gate behind a paths filter is the same silence #2957 is about"). Both execute on this PR's CI run and are expected to pass because this mission changes no glossary markdown/traceability content and no doctrine Pydantic model. |
| PR diff-coverage (critical-path, 90%, `src/runtime/next/*`) | **Enforced** | Every IC-01–IC-04 production file lives under `src/runtime/next/`, inside this gate's `critical_paths` include list (`ci-quality.yml:3512`, re-verified post-#3346-rebase — shifted +23 lines from 3489 by that PR's unrelated 23-line e2e-acceptance-step insertion at old line 3392, same array entry — fed by `integration-tests-next`'s `--cov=src/runtime/next` report, `ci-quality.yml:2927` (unaffected — precedes the #3346 insertion point), consumed by the `diff-coverage` job via `--fail-under=90 --include "${critical_paths[@]}"` at `ci-quality.yml:3539-3540` (also +23 from 3516-3517)). ATDD Commit 1/2 and IC-02's plan-guard-table tests are expected to satisfy the 90% floor on new/changed lines, but this should be verified locally with `uv run diff-cover` against the base branch before push, not assumed. |
| Kernel coverage ≥90% / mission-loader coverage ≥90% | **Not a distinct gate for this mission** | This mission's touched files are not under the `src/kernel/` coverage-gated boundary or the mission-loader package (distinct from the diff-coverage critical-path gate above, which does apply); new-code coverage is instead driven by the "every new branch/helper gets tests in the same PR" rule (charter Sonar Expectations), satisfied by the ATDD sequencing above covering every new branch in `_GUARD_TABLES`'s dispatch, both split call sites, `_evaluate_plan_guards`'s 5 branches, and the FR-008 classifier's 6 states. |
| `make lint` | **Advisory only** | Per charter/design-pipeline convention, `make lint` is advisory in CI for this repo, not a hard gate; `ruff check` above is the enforced equivalent. |
| commitlint / markdown lint / TID251 banned-API / Typer JSON error surface / `patch()` target validation / Bandit / pip-audit / `uv.lock` freshness / SonarCloud Quality Gate | **Unaffected, run incidentally by CI** | None of this mission's changes introduce a new dependency, a new banned-API usage, a new `patch()` target, a security-sensitive code path, or a lockfile change; these CI-wide gates run automatically on the PR regardless of this plan's own scoping and are not called out with a per-gate rationale beyond "this diff does not touch what they check." |
| Full `pytest tests/` (~17,000 tests) | **Deliberately deferred to post-merge** | Per charter Testing Requirements and C-005: reserved for post-merge mission-level validation against the merged branch, not mid-implementation. |

## Project Structure

### Documentation (this mission)

```
kitty-specs/mission-type-guard-registry-01KZY2FG/
├── plan.md                      # This file
├── tracer-tooling-friction.md   # Already exists (seeded at spec phase) — append only
├── tracer-approach.md           # Seeded by this plan (new)
├── tracer-design-decisions.md   # Seeded by this plan (new)
└── tasks.md                     # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

No `research.md`, `data-model.md`, `quickstart.md`, or `contracts/` directory is
generated for this mission — the spec's own verified-figures table and this
plan's Seam & Module Placement / Contracts sections already carry the design
research and data-shape decisions inline; a separate Phase-0/Phase-1 artifact
set would duplicate content already committed to `spec.md` and this file.

### Source Code (repository root)

```
src/
├── runtime/next/
│   ├── runtime_bridge_cores.py          # _GUARD_TABLES, UnregisteredMissionFamilyError,
│   │                                     #   evaluate_guards_strict, evaluate_guards (now
│   │                                     #   tolerant wrapper), _evaluate_plan_guards
│   ├── runtime_bridge_composition.py    # _check_composed_action_guard: strict call +
│   │                                     #   catch + WARNING log + [] (FR-003/FR-004/C-001)
│   ├── runtime_bridge.py                # _check_cli_guards: strict call, no catch (C-002)
│   └── runtime_bridge_io.py             # _PRESENCE_FILE_TAGS + "research.md"
└── specify_cli/cli/commands/
    ├── doctor.py                        # new thin `mission-type` @app.command shell
    └── _mission_type_audit.py           # NEW — MissionTypeState, classify_mission_type,
                                          #   audit_mission_types, summarize_mission_types,
                                          #   run_mission_type_audit

tests/
├── runtime/
│   ├── test_bridge_cores.py             # FR-010/FR-011 ATDD (registry, strict lookup, plan guards)
│   └── test_bridge_composition.py       # FR-011 (composed-path neutral degrade + WARNING log)
├── next/ ; tests/specify_cli/next/      # NFR-001/NFR-002 regression surface (unmodified)
├── integration/test_custom_mission_runtime_walk.py   # NFR-002 regression surface (unmodified)
└── specify_cli/cli/commands/
    ├── test_doctor_mission_type.py      # NEW — SC-005/SC-006, FR-008 boundary case
    └── test_doctor_cli_surface_golden.py  # FROZEN_SUBCOMMANDS / EXPECTED_OPTIONS /
                                            #   EXPECTED_HELP updated for "mission-type"
```

**Structure Decision**: single Python CLI/library. The functional change is
concentrated at the existing three-file runtime guard-dispatch seam plus a
one-line addition to the artifact-presence fact-port; the diagnostic addition
is one new sibling module behind the existing `doctor` command group, following
that group's own binding "thin shell + sibling module" convention.

## Implementation Concern Map

> Concerns are not work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — `_GUARD_TABLES` registry + strict/tolerant split in the cores module

- **Purpose**: Replace `evaluate_guards`'s if/if/fall-through with an explicit
  registry (FR-001), and give the legacy and composed paths their own strict
  vs. tolerant entry points into it (foundation for IC-03/IC-04).
- **Relevant requirements**: FR-001, FR-006, NFR-001, NFR-003.
- **Affected surfaces**: `src/runtime/next/runtime_bridge_cores.py` — new
  `_GUARD_TABLES`, `UnregisteredMissionFamilyError`, `evaluate_guards_strict`;
  `evaluate_guards` becomes a tolerant wrapper over the new strict function.
- **Sequencing/depends-on**: none (foundation); IC-02 adds a table entry to the
  same registry, so IC-01 and IC-02 land in the same commit in practice.
- **Risks**: `evaluate_guards`'s existing direct callers (`tests/runtime/test_bridge_cores.py`)
  must see byte-identical behavior for the three already-registered families —
  the 71-passed baseline captured in Baseline & Reflexivity is the concrete
  check, not an assumption.

### IC-02 — `plan`'s own guard table + the `_PRESENCE_FILE_TAGS` fix

- **Purpose**: Author `_evaluate_plan_guards` (FR-002) and register it under
  `"plan"`; fix the `research.md` presence-tag gap this plan's own
  verification found (Seam & Module Placement, `runtime_bridge_io.py`).
- **Relevant requirements**: FR-002.
- **Affected surfaces**: `runtime_bridge_cores.py` (`_evaluate_plan_guards`,
  registry entry); `runtime_bridge_io.py` (`_PRESENCE_FILE_TAGS` +
  `"research.md"`, docstring update from "three" to "four" mission families).
- **Sequencing/depends-on**: IC-01.
- **Risks**: the `research`-step behavior change for `plan` noted in Baseline &
  Reflexivity (goes from "always passes" to "checks `research.md`") must be
  covered by an acceptance-scenario test (User Story 2 AC3), not left implicit
  — SPEC-VERIFY-003's own remediation already added this scenario to spec.md;
  this IC is where it gets exercised in code.

### IC-03 — Composed path: strict call + WARNING-logging tolerant catch

- **Purpose**: `_check_composed_action_guard` calls `evaluate_guards_strict`
  directly, catches `UnregisteredMissionFamilyError`, logs at WARNING naming
  the family, returns `[]` (FR-003, FR-004, C-001).
- **Relevant requirements**: FR-003, FR-004, C-001, NFR-002.
- **Affected surfaces**: `src/runtime/next/runtime_bridge_composition.py`,
  lines 427-486 (the real implementation; the `runtime_bridge.py:983-996`
  compat delegate — re-verified post-#3346-rebase, shifted +105 lines from
  878-891, same code — needs no change — it already forwards everything through).
- **Sequencing/depends-on**: IC-01.
- **Risks**: must not weaken the ≥24-test / ≥4-test custom-mission-type
  tolerance NFR-002 pins — this IC only changes what happens for a family with
  NO `_GUARD_TABLES` entry; it does not touch `_should_dispatch_via_composition`
  or the agent-profile/contract-ref widening path those tests exercise.

### IC-04 — Legacy path: direct strict call, no catch

- **Purpose**: `_check_cli_guards` calls `evaluate_guards_strict` directly and
  lets the exception propagate — the loud-block half of the split (FR-005,
  C-002, User Story 3).
- **Relevant requirements**: FR-005, C-002.
- **Affected surfaces**: `src/runtime/next/runtime_bridge.py`, lines 785-803
  (re-verified post-#3346-rebase, shifted +105 lines from 680-698, same code).
- **Sequencing/depends-on**: IC-01.
- **Risks**: this path is currently unreachable with an unregistered family
  (hardcoded `mission_family="software-dev"` at line 797) — the test for this
  IC necessarily uses an injection seam (per User Story 3's own Independent
  Test framing), not a real end-to-end caller; do not mistake "no live caller
  reaches this today" for "untested" — FR-011 requires the seam-injected test
  regardless.

### IC-05 — `doctor mission-type` command + sibling module

- **Purpose**: Ship the operator-facing diagnostic (FR-007, FR-008, FR-009).
- **Relevant requirements**: FR-007, FR-008, FR-009, NFR-004.
- **Affected surfaces**: `src/specify_cli/cli/commands/doctor.py` (new thin
  shell); `src/specify_cli/cli/commands/_mission_type_audit.py` (new).
- **Sequencing/depends-on**: none functionally (independent of IC-01-04), but
  sequenced after them in the PR narrative since it is the "diagnosability"
  half of the mission, not the "fix" half.
- **Risks**: the FR-008 taxonomy decision procedure (Seam & Module Placement)
  must be implemented exactly as specified there, including the
  present-but-blank-`mission_type`-key-wins-over-legacy-key ordering — a
  plausible-but-wrong alternate reading (fall through to the legacy key
  whenever `mission_type` is blank, mirroring `_canonical_meta_mission_type`'s
  own behavior) would silently misclassify the FR-008 boundary case.

### IC-06 — Golden CLI-surface contract update

- **Purpose**: Keep `test_doctor_cli_surface_golden.py` truthful once
  `mission-type` is a real registered subcommand (Contracts section).
- **Relevant requirements**: (mechanical consequence of FR-007; no dedicated
  FR, but the golden test's own `test_registered_command_names_match_frozen_subcommands`
  gate fails without this).
- **Affected surfaces**: `tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py`
  — `FROZEN_SUBCOMMANDS`, `EXPECTED_OPTIONS["mission-type"]`,
  `EXPECTED_HELP["mission-type"]`, the "19"→"20" count comment.
- **Sequencing/depends-on**: IC-05 (the command's real `--help` text must exist
  before the golden snapshot can be captured accurately).
- **Risks**: none beyond mechanical accuracy — this is a characterization
  test, so its content must match what the command actually emits, not a
  pre-written aspiration.

## Complexity Tracking

*No entries.* No Charter Check violation requires justification — every new or
modified function stays well under the complexity ceiling of 15 (NFR-003), no
new architectural layer or module is introduced beyond one CLI-sibling module
(the smallest-viable shape, combining rather than 1:1-mirroring the two
`doctor identity` precedent modules' roles — see Seam & Module Placement), and
no gate listed in Gate Set is skipped without a stated reason.
