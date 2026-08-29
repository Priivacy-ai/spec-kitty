# Mission Specification: Mission Type Guard Registry

**Mission Branch**: `kitty/mission-mission-type-guard-registry-01KZY2FG`
**Created**: 2026-08-13
**Status**: Draft
**Input**: GitHub issue [#3386](https://github.com/Priivacy-ai/spec-kitty/issues/3386) — "Unknown mission_type silently executes under software-dev guard tables — already misfires on the built-in 'plan' type"

## Clarifications

### Session 2026-08-13 — operator scope decision

The operator (human-in-command, via the orchestrating agent) selected the mission's scope
from three options presented in the pre-spec readiness probe
(`/home/jeroennouws/dev/SK-missions/_readiness/3386-mission-type-guard-registry.md`, Open
Question 1). The decision is binding, attributed to **the operator, dated 2026-08-13**. The
summary below is a **paraphrase of the operator's Option-A selection, not a verbatim
quotation** — the substantive source of record is the readiness probe's own Option A text
under "Open questions → Question 1" (the bullet beginning "Scope to the guard-table registry +
`plan` table + `doctor mission-type` only (Recommended)"):

> Registry + plan table + doctor. Builds: the `_GUARD_TABLES` registry replacing the
> fall-through, `plan`'s guard table (empty `review`, artifact-checks elsewhere), the
> loud-block-vs-neutral-degrade split between legacy and composed paths, `doctor mission-type
> --json [--fail-on ...]` modeled on `doctor identity`, and tests for exactly those. The
> override hatch, the two divergent meta readers, and the dashboard default get filed as one
> follow-up tracking issue. Matches the issue's own PR sizing and the charter's
> locality-of-change default.

This is **Option A** from the readiness probe (of three: A — registry + `plan` table + doctor
only [recommended, chosen]; B — Option A plus the four independently-verified misc sites; C —
full unverified ~22-site census in one mission). The four sites named below in
"Out of Scope" are explicitly deferred, not silently dropped.

### Numbers corrected from the source GitHub issue

The issue body (quoted in full in the mission brief) restates several unverified figures. A
first-hand readiness probe (same path as above) verified or corrected each one; this spec uses
only the corrected figures, never the issue's original ones:

| Issue's claim | Status | Corrected figure used in this spec |
|---|---|---|
| "~22 silent-misbehavior sites" | Unverified — no census was ever completed | Not cited as a count anywhere in this spec; the 4 sites this mission does NOT fix (independently verified) are named individually in Out of Scope instead |
| "nine tests" pin the custom-mission-type extension point | Undercount | **≥24 tests** across three files: `tests/integration/test_custom_mission_runtime_walk.py` (5), `tests/next/test_composition_gate_widening.py` (14 of that file's tests exercise this predicate), `tests/runtime/test_bridge_composition.py` (6 more) |
| "six tests" pin `_should_dispatch_via_composition` degrading rather than raising | Overcount, not independently re-verified to an exact number | **At least 4** unambiguous direct hits (named in NFR-002 below) |
| "~16 tests" pin typeless-mission behavior | Directionally confirmed only, not a pinned count | Treated as an estimate; this spec does not assert a specific count, only that the behavior is preserved (see NFR-001) |
| "12 of 30 `write_meta` callers pass `validate=False`" | Wrong and inverted | **15 of 27 (56%)** call sites skip validation — corrected figure per one direct enumeration (27 sites, 15 skipping validation); direction independently re-checked by a second, rougher grep (~29/17, "close enough... to trust its direction" per the probe). This spec cites the corrected fraction only where relevant (C-004) |
| "~145 LOC src + ~245 test" sizing | The issue's own rough estimate, not a commitment | Not restated as a target in this spec; left to the plan phase |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - An unrecognized mission family no longer silently borrows software-dev's guard table on the composed path (Priority: P1)

An operator or agent runs `spec-kitty next` (or any composed-dispatch caller) against a
mission whose `mission_family` is not one of the explicitly registered families
(`software-dev`, `research`, `documentation`, and — after this mission — `plan`). Today,
`evaluate_guards` falls through to `_evaluate_software_dev_guards`, so the mission is silently
evaluated against work-package/tasks guard logic that has no relationship to what that mission
type actually produces. After this mission, the composed path recognizes the family as
unregistered and returns an explicit neutral result (no guard failures manufactured from the
wrong family's rules) plus a log line naming the unrecognized family — never the borrowed
software-dev verdict, and never a raised exception that would break the custom-mission-type
extension point's existing degrade contract.

**Why this priority**: This is the mission's core defect. Every other requirement exists to
close this specific silent-misfire.

**Independent Test**: Call `evaluate_guards` (or the composed guard entry point that wraps it)
with a `snapshot.mission_family` value that has no entry in `_GUARD_TABLES` (e.g.
`"totally-unregistered-family"`) and any `step_id`. Assert the returned failure list is NOT the
software-dev `_evaluate_wp_iteration_guard` message (`"Not all work packages are approved or
done"` / `"Not all work packages have required status (for_review, approved, or done)"`) and
is instead the explicit neutral-degrade result, and assert a log record was emitted naming the
unregistered family.

**Acceptance Scenarios**:

1. **Given** a mission snapshot with `mission_family="plan"` and `step_id="review"`, **When**
   `evaluate_guards` is called on the composed path, **Then** the result is `plan`'s own
   (empty) `review` guard list — never `["Not all work packages are approved or done"]`.
2. **Given** a mission snapshot with `mission_family="some-future-custom-type"` (not in
   `_GUARD_TABLES`) reached via the composed path (`_check_composed_action_guard`), **When**
   `evaluate_guards` is called, **Then** the result is an explicit neutral guard outcome (not
   the software-dev table's verdict) and a log line records the unregistered family — no
   Python exception propagates to the caller.

---

### User Story 2 - `plan`-type missions get their own guard table instead of inheriting software-dev's by accident (Priority: P1)

`plan`'s action sequence is `specify → research → plan → review` (`terminal_step: review`) with
no `tasks` step and no work packages ever created. Today its `review` step deterministically
emits `"Not all work packages are approved or done"` because `evaluate_guards` falls through to
the software-dev family. After this mission, `plan` has its own explicit guard table: an empty
list for `review` (a terminal narrative-approval step, by direct analogy to
`_evaluate_documentation_guards`'s existing `accept` case at
`src/runtime/next/runtime_bridge_cores.py:455-456`, which already returns `[]` with the
rationale "terminal status commit step; publish gate is sufficient") and artifact-presence
checks for `specify` / `research` / `plan` mirroring the pattern used by the `research` and
`documentation` tables (e.g. `_check_artifact_present` against the step's expected output
artifact).

**Why this priority**: This is the live, shipped, reproducing defect named in the issue title —
not a hypothetical for custom types only.

**Independent Test**: Drive a `plan`-type mission through its full step sequence
(`specify → research → plan → review`) using `spec-kitty next` against a fixture project, and
assert the `review` step never blocks on a work-package-related guard message.

**Acceptance Scenarios**:

1. **Given** a `plan`-type mission that has produced `spec.md` and `plan.md` (no `tasks/`
   directory ever exists for this mission type), **When** the mission reaches its `review`
   step and `evaluate_guards` is invoked, **Then** the guard failure list is empty and the
   mission is not blocked.
2. **Given** a `plan`-type mission that has NOT yet produced `spec.md` at the `specify` step,
   **When** `evaluate_guards` is invoked for `step_id="specify"`, **Then** the guard failure
   list names the missing artifact (mirroring the research/documentation pattern) — the guard
   table is not empty across the board; only the terminal `review` step is intentionally
   empty.
3. **Given** a `plan`-type mission that has produced `spec.md` but has NOT yet produced
   `research.md` at the `research` step, **When** `evaluate_guards` is invoked for
   `step_id="research"`, **Then** the guard failure list names the missing `research.md`
   artifact (mirroring the `specify`/`plan` artifact-presence pattern) — the `research` step's
   guard is exercised by an acceptance scenario, not left implicit.

---

### User Story 3 - The legacy CLI-native guard path fails loudly, never silently, on an unrecognized family (Priority: P2)

`_check_cli_guards` (`src/runtime/next/runtime_bridge.py:785-803`) is the legacy/CLI-native
guard entry point. It currently hardcodes `mission_family="software-dev"` unconditionally
(line 797), so no custom mission type can reach it today by construction — the custom-type
extension point is exclusively a composed-path capability (pinned by ≥24 tests; see
Clarifications). This mission adds an explicit registry that would allow `evaluate_guards` to
recognize *any* family reaching it, including via the legacy path. The requirement:
should the legacy path ever be extended in the future to pass through a non-hardcoded family
(a possibility this mission does not implement, but the registry must not silently accommodate
by half-measure), an unregistered family reaching `evaluate_guards` through the legacy/CLI-native
call site must raise a loud, structured error — never fall through to software-dev's table and
never neutrally degrade the way the composed path does. The two paths are deliberately
asymmetric: composed = tolerant (custom mission types are supported there), legacy = strict
(no custom mission type can legitimately reach it).

**Call-site shape (binding, not cosmetic)**: today both `_check_cli_guards` and
`_check_composed_action_guard` end with the identical `return _cores.evaluate_guards(snapshot)`
— both delegate to the same shared function with no path-identifying parameter distinguishing
them. Without more, a compliant-but-lazy implementation could add an isolated, unit-tested
raising helper that is never actually wired into `_check_cli_guards`'s real call chain, leaving
`_check_cli_guards` still delegating to the tolerant, neutral-degrading path exactly as today —
satisfying a literal unit-test assertion while silently failing this story's actual subject. To
close that loophole, this mission MUST split the shared dispatch into two concrete call sites: a
**strict lookup** (raises a structured, typed exception for an unregistered family) that
`_check_cli_guards` itself calls directly, and a **tolerant wrapper** (catches that same
exception, logs it, and returns `[]`) that `_check_composed_action_guard` itself calls directly.
`_check_cli_guards` being the direct caller of the strict lookup — not merely a
unit-tested-but-unwired helper existing somewhere in the module — is part of this story's
acceptance bar (see Acceptance Scenario 3, FR-005, and C-002).

**Why this priority**: Defensive correctness for the registry's shape, not a live defect today
(the legacy path's own hardcoding already prevents an unregistered family from reaching it in
current code) — but the issue explicitly calls for this split as part of the registry's design,
and an untested asymmetry is exactly the kind of silent-misbehavior seam this mission exists to
close.

**Independent Test**: Two parts. (1) Directly unit-test the strict lookup function with a
family string that has no `_GUARD_TABLES` entry and confirm it raises (does not return a list,
does not log-and-neutral-degrade the way the composed path does). (2) Confirm `_check_cli_guards`
itself is the caller of that strict lookup — e.g. via a spy/mock on the strict-lookup function
asserting it is invoked when `_check_cli_guards` runs, or by injecting an unregistered family
through a test seam and asserting the raised exception is observed to propagate out of
`_check_cli_guards` itself. Part (2) exists specifically so an isolated, unit-tested-but-unwired
raising helper cannot satisfy this story while `_check_cli_guards`'s real call chain keeps
delegating to the tolerant path.

**Acceptance Scenarios**:

1. **Given** a call into the guard-table registry's legacy-path entry point with an
   unregistered `mission_family`, **When** the lookup executes, **Then** it raises a structured
   exception (not `UnknownMissionTypeError` necessarily, but an explicit, typed, loud failure)
   rather than returning any guard-failure list.
2. **Given** the existing three registered families reached via the legacy path
   (`software-dev`, `research`, `documentation`), **When** `_check_cli_guards` is exercised
   end-to-end, **Then** behavior is byte-for-byte unchanged from pre-mission `main` (see
   NFR-001) — the loud-block path is unreachable under current callers and must stay that way
   without regressing the reachable ones.
3. **Given** `_check_cli_guards`'s internal dispatch is exercised with an unregistered
   `mission_family` (via a test double/injection seam, since no current caller can reach this
   state), **When** the call executes, **Then** the raised exception is observed to propagate
   from `_check_cli_guards` itself — confirming `_check_cli_guards` is wired directly to the
   strict lookup, not to an isolated helper that its real call chain never invokes.

---

### User Story 4 - `spec-kitty doctor mission-type` surfaces unresolved/unregistered mission types before they silently misfire mid-run (Priority: P2)

An operator can run `spec-kitty doctor mission-type --json [--fail-on <states>]`, modeled
directly on the existing `spec-kitty doctor identity` command
(`src/specify_cli/cli/commands/doctor.py:396-444`, report-builder pattern in
`src/specify_cli/cli/commands/_identity_audit.py`), to audit every mission under `kitty-specs/`
and classify its `mission_type` into one of a fixed, enumerated state taxonomy — surfacing the
class of misconfiguration this mission fixes (an unregistered or unresolvable mission type)
*before* it silently degrades a running mission's guard evaluation.

**Why this priority**: Operator-facing diagnosability. Without this, the registry fix is
invisible until a mission actually hits the composed path's neutral-degrade log line — this
command lets an operator check proactively.

**Independent Test**: Run `spec-kitty doctor mission-type --json` against a fixture
`kitty-specs/` tree containing at least one mission of each taxonomy state (see FR-008) and
assert the JSON report classifies each correctly; run with `--fail-on unknown` against a tree
containing an unknown-type mission and assert non-zero exit.

**Acceptance Scenarios**:

1. **Given** a `kitty-specs/` tree with missions of type `software-dev`, `research`,
   `plan` (all resolvable/registered) and one mission with an unrecognized custom
   `mission_type` string not defined anywhere in the project, **When**
   `spec-kitty doctor mission-type --json` runs, **Then** the JSON report lists the fourth
   mission under the `unknown` state and the first three under `resolved` (or the appropriate
   registered state).
2. **Given** the same tree, **When** `spec-kitty doctor mission-type --fail-on unknown` runs,
   **Then** the command exits non-zero; **When** run with no `--fail-on` flag, **Then** it
   exits zero regardless of findings (report-only by default, matching `doctor identity`'s
   shape).

---

### Edge Cases

- What happens when `evaluate_guards` is called with `mission_family=None` (a typeless
  mission, meta.json carries no `mission_type` at all)? Behavior must be unchanged from
  pre-mission `main` — typeless-mission neutrality is independently pinned (directionally
  confirmed by an estimated ~16 tests; see Clarifications) and this mission must not touch it.
- How does the system handle a `mission_family` value that IS registered in `_GUARD_TABLES`
  today (`software-dev`, `research`, `documentation`) after the registry replaces the
  if/if/fall-through? The guard-failure list for every currently-registered family, every
  `step_id`, and every artifact-presence state must be byte-for-byte identical before and
  after this mission (NFR-001) — this is a refactor-with-extension, not a behavior change for
  already-registered families.
- What happens to a mission that is *already mid-flight* (has an open worktree, has already
  advanced past some steps) on `research`, `documentation`, or `software-dev` when this change
  merges? Its next `evaluate_guards` call must produce the same result it would have produced
  on pre-mission `main` for that exact snapshot — see NFR-001 (this is not an assumption; it is
  a binding constraint because `evaluate_guards` runs on every `next` call for every mission
  currently in flight across every workspace, not only future ones).
- What happens to a mission that is mid-flight on a *custom* (composed-path-only) family that
  is not `software-dev`/`research`/`documentation`/`plan`? Before this mission, it silently
  received the software-dev table's verdict (the exact defect this mission fixes). After this
  mission, it will receive the explicit neutral-degrade result instead — this IS a behavior
  change for that one case, and it is the intended fix, not a regression. It must never regress
  further into a raised exception (User Story 1, AC2) or a fresh silent misfire.
- What happens when the `doctor mission-type` audit encounters a `meta.json` it cannot read or
  parse for a given mission directory? It must classify that mission into an explicit `error`
  state in the report (never silently skip it and never crash the whole audit run) — mirroring
  `doctor identity`'s `orphan` state for unreadable metadata.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Replace the `evaluate_guards` if/if/fall-through with an explicit `_GUARD_TABLES` registry | As a maintainer, I want `evaluate_guards` (`src/runtime/next/runtime_bridge_cores.py:351-374`) dispatched via an explicit per-family registry (e.g. a `dict[str, Callable]`) instead of the current `if research / if documentation / else software-dev` chain, so that a family with no entry is a distinguishable case rather than an implicit software-dev alias. | High | Open |
| FR-002 | Author `plan`'s own guard table | As a maintainer, I want a `_evaluate_plan_guards` function registered for `mission_family="plan"` that returns `[]` for the terminal `review` step (by direct analogy to `_evaluate_documentation_guards`'s existing `accept` case) and artifact-presence checks for `specify` (`spec.md`), `research` (`research.md`), and `plan` (`plan.md`), so that `plan`-type missions are evaluated against rules that match what they actually produce. | High | Open |
| FR-003 | Composed-path unregistered family → explicit neutral degrade, never a crash, never a software-dev misfire | As an operator running a mission of a custom, composed-path-only mission type not present in `_GUARD_TABLES`, I want `evaluate_guards` to return an explicit neutral result (not the software-dev table's verdict, not a raised exception) so my mission is not blocked by rules that don't apply to it. Because the returned `list[str]` shape is unchanged (Key Entities), this neutral result is interface-indistinguishable from a genuine guard pass — FR-004's log line is the only differentiator, and FR-007's `doctor mission-type` command is the operator-facing, non-log-dependent answer for the same discoverability need; see FR-004 and FR-007. | High | Open |
| FR-004 | Composed-path neutral degrade logs the unregistered family at WARNING level or above | As an operator debugging why a custom mission type's guards behave neutrally, I want a new log line — added to `_check_composed_action_guard` in `src/runtime/next/runtime_bridge_composition.py` (the composed path's actual implementation site, not `runtime_bridge.py`) — recording the specific unregistered `mission_family` value at the moment of the degrade, emitted at **WARNING level or above** and never DEBUG or lower, so the condition is discoverable in default-configured logs without reading source. This WARNING level is a deliberately NEW requirement for this specific degrade case, not a claim that it matches `runtime_bridge_composition.py`'s own existing convention for an analogous case: that module's `_dispatch_via_composition` already logs its own degrade-and-continue path (an executor exception, turned into a structured failure list rather than a raised error) via `logger.exception` at ERROR level, a different level for a different failure mode. WARNING is instead chosen by cross-file precedent — `runtime_bridge.py:399-405`'s `DecisionGitLog`-construction-failure fallback is the pattern that motivated picking WARNING for a "problem detected, continuing anyway" log, cited here as the precedent that informed the choice, not as an existing convention already in force in the destination file. Cross-reference: FR-003 (this is the sole interface differentiator for that neutral result) and FR-007 (`doctor mission-type` gives operators a proactive, non-log-dependent way to discover the same unregistered/unresolved state). | High | Open |
| FR-005 | Legacy/CLI-native path raises loudly on an unregistered family, via a strict lookup that `_check_cli_guards` itself calls directly | As a maintainer, I want the shared guard-table dispatch split into a **strict lookup** (raises a structured, typed exception for a family with no `_GUARD_TABLES` entry) called directly by `_check_cli_guards` (`src/runtime/next/runtime_bridge.py:785-803`), and a separate **tolerant wrapper** (catches that exception, logs, returns `[]`) called directly by `_check_composed_action_guard` — not an isolated, unit-tested-but-unwired raising helper that `_check_cli_guards`'s real call chain never invokes — so the legacy path raises loudly in its actual, exercised call chain, not only in an unreachable helper. See User Story 3 (Acceptance Scenario 3) and C-002 for the same call-site requirement. | Medium | Open |
| FR-006 | Registered-family behavior is unchanged through the registry refactor | As a maintainer, I want the guard-failure output for every currently-registered family (`software-dev`, `research`, `documentation`) and every `step_id` to be identical before and after the `_GUARD_TABLES` refactor, so existing in-flight missions on those families see zero behavior change. | High | Open |
| FR-007 | `spec-kitty doctor mission-type --json` command | As an operator, I want a `spec-kitty doctor mission-type` CLI command, modeled directly on `spec-kitty doctor identity` (`src/specify_cli/cli/commands/doctor.py:396-444`), accepting `--json` and a mission-scoping option, so I can audit mission-type resolution health across `kitty-specs/`. | High | Open |
| FR-008 | `doctor mission-type` enumerated state taxonomy | As an operator, I want every mission classified into exactly one of a fixed, documented state: `resolved` (mission_type present and loadable), `activated-unresolvable` (mission_type is activated in project charter but has no loadable profile/definition on disk — matches the `UnknownMissionTypeError` FR-006/SC-003 distinction already made at `src/charter/activation/mission_type_profiles.py:193-210`), `unknown` (mission_type string present but not registered/activated anywhere), `typeless` (no `mission_type` key at all — the pre-existing neutral case), `legacy-key-only` (only the retired `mission` key is present, no `mission_type` key), or `error` (meta.json unreadable/malformed), so the report is exhaustive and non-ambiguous — no mission is silently omitted from every bucket. A `mission_type` key that is present but blank (`""`), `null`, or a non-string value MUST classify as `typeless`, matching the existing canonicalization convention already used by `_canonical_meta_mission_type` (`src/specify_cli/mission.py:542-556`), which treats blank/null/non-string values as absent rather than as a distinguishable `unknown` — stated explicitly here so the taxonomy is exhaustive-by-construction rather than left to each implementer's own key-presence-vs-canonicalization reading. A boundary test case covering this (blank/null/non-string `mission_type` classified as `typeless`) is to be added to `test_doctor_mission_type.py` at implementation/tasks time. | High | Open |
| FR-009 | `doctor mission-type --fail-on <states>` | As an operator wiring this into CI, I want `--fail-on <comma-separated-states>` (e.g. `--fail-on unknown,activated-unresolvable`) to make the command exit non-zero when any mission matches a listed state, and exit zero with no flag regardless of findings, mirroring `doctor identity`'s `--fail-on` contract exactly. | Medium | Open |
| FR-010 | ATDD red-first pin for the live `plan`-type defect | As a reviewer, I want a failing-first test that reproduces the `plan`-mission `review`-step misfire (asserting the software-dev WP-iteration message is emitted) committed and RED against pre-mission `main`, before any fix lands, per charter C-011 / Standing Order #4. | High | Open |
| FR-011 | Test coverage for the previously-uncovered fall-through itself | As a reviewer, I want at least one test that feeds an unregistered/synthetic `mission_family` value to `evaluate_guards` on both the legacy and composed call paths (zero such tests exist today — verified by direct grep of `tests/runtime/test_bridge_cores.py`, `tests/runtime/test_bridge_composition.py`, `tests/next/test_decision_unit.py`), so this defect class cannot silently regress. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Zero behavior change for already-registered families and typeless missions | For every `mission_family` in `{"software-dev", "research", "documentation"}` and for `mission_family=None` (typeless), the guard-failure list returned by `evaluate_guards` for every `step_id` and every `snapshot` shape must be identical (list contents and order) before and after this mission's changes land. Verification method: capture the pass/fail state of `tests/runtime/test_bridge_cores.py`, `tests/runtime/test_bridge_composition.py`, `tests/next/test_runtime_bridge_unit.py`, `tests/next/test_occurrence_gate_next_loop.py`, `tests/specify_cli/next/test_runtime_bridge_composition.py`, and the ~16-estimate typeless-preservation test set as a **captured baseline BEFORE touching `runtime_bridge_cores.py`**, then require **zero NEW reds relative to that baseline** after the change lands (no test in those files may need to change its expected assertion value as a result of this mission), consistent with how SC-004 already frames its own check. The three added files are named explicitly because `test_bridge_cores.py` alone calls `evaluate_guards` directly (bypassing both real delegate functions) and `test_bridge_composition.py`'s guard-dispatch tests monkeypatch `evaluate_guards` to a stub — neither exercises the real, unmocked `_check_cli_guards` / `_check_composed_action_guard` call chains end-to-end on its own, so the byte-for-byte-identical claim needs the added files to be backed by tests that do. | Reliability | High | Open |
| NFR-002 | Custom-mission-type composed-path tolerance is preserved | The ≥24 tests across `tests/integration/test_custom_mission_runtime_walk.py`, `tests/next/test_composition_gate_widening.py`, and `tests/runtime/test_bridge_composition.py` that pin the composed path's tolerant degrade behavior for custom mission types, and the at-least-4 tests that pin `_should_dispatch_via_composition` degrading rather than raising (`tests/specify_cli/next/test_runtime_bridge_dispatch.py::TestGracefulDegradation::test_unknown_mission_type_returns_false`, `tests/specify_cli/next/test_runtime_bridge_composition.py::test_should_dispatch_falls_through_for_unknown_mission_helper`, `::test_dispatch_falls_through_for_unknown_mission`, `tests/runtime/test_bridge_composition.py::test_should_dispatch_via_composition_both_branches_via_charter_lookup`), must all remain green, unmodified, after this mission. | Reliability | High | Open |
| NFR-003 | Complexity ceiling | Every new or modified function introduced by the `_GUARD_TABLES` registry and the `doctor mission-type` report builder must stay at or under the repo's `ruff C901` / Sonar `S3776` complexity ceiling of 15 (per charter Sonar Expectations); none of the existing per-family guard functions (`_evaluate_research_guards`, `_evaluate_documentation_guards`, `_evaluate_software_dev_guards`) are close to that limit today, so the registry entries should follow the same shape. | Maintainability | Medium | Open |
| NFR-004 | `doctor mission-type` completes within CLI performance budget | `spec-kitty doctor mission-type --json` must complete in under 2 seconds for a typical `kitty-specs/` tree (charter Performance and Scale standard), matching `doctor identity`'s existing budget. | Performance | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Composed path stays tolerant by design, never raises for an unregistered family | The composed path (`_check_composed_action_guard`) MUST NOT raise a Python exception for an unregistered `mission_family`. Raising would break the custom-mission-type extension point contract pinned by ≥24 tests (NFR-002) and the six/four-plus tests pinning `_should_dispatch_via_composition`'s degrade-not-raise behavior. This is a hard boundary, not a design preference. `_check_composed_action_guard` must itself be the direct caller of the tolerant wrapper (catches the strict lookup's exception, logs it, returns `[]`) described in C-002 / FR-005 — post-mission, the two paths no longer both terminate in the identical shared `evaluate_guards` call for the unregistered-family case; each calls its own wrapper directly. | Technical | High | Open |
| C-002 | Legacy path stays strict by design, never silently falls through | The legacy/CLI-native path (`_check_cli_guards`) MUST NOT silently degrade an unregistered family to the software-dev table (today's defect) or to a neutral empty-list result (the composed path's new behavior). It must raise — and it must do so via `_check_cli_guards` itself directly calling a strict, raising lookup, not via an isolated, unit-tested-but-unwired helper that `_check_cli_guards`'s real call chain never invokes (see FR-005 and User Story 3, Acceptance Scenario 3). This is the deliberate asymmetry requested by the operator's Option A scope decision and the issue's own suggested design. | Technical | High | Open |
| C-003 | Mission scope bounded to registry + `plan` table + doctor command + their tests only | This mission implements exactly: (1) the `_GUARD_TABLES` registry, (2) `plan`'s guard table, (3) the loud-block/neutral-degrade split, (4) `spec-kitty doctor mission-type`, and (5) tests for those four. It does not touch any of the four sites listed in Out of Scope below, per the operator's binding Option A decision (see Clarifications). | Business | High | Open |
| C-004 | No roster/validation check added to `validate_meta` or `write_meta` | Per the issue's own reasoning (strengthened by the corrected figure: 15 of 27 — 56% — of `write_meta` call sites pass `validate=False` and would silently bypass any such check), this mission MUST NOT add a mission-type roster/registration check inside `validate_meta`. Diagnosability for unregistered types is delivered exclusively through `doctor mission-type` (FR-007–FR-009), which audits after the fact rather than gating at every write site. | Technical | High | Open |
| C-005 | Targeted test surface, not the full suite | Per charter Testing Requirements, this mission's own validation runs target `tests/runtime/test_bridge_cores.py`, `tests/runtime/test_bridge_composition.py`, `tests/next/`, `tests/integration/test_custom_mission_runtime_walk.py`, `tests/specify_cli/next/`, and a new `tests/specify_cli/cli/commands/test_doctor_mission_type.py` (or equivalent) — not a full `pytest tests/` run mid-implementation. A full-suite run is reserved for post-merge mission-level validation. | Technical | Medium | Open |

### Key Entities

- **`_GUARD_TABLES` registry**: A mapping from `mission_family` (string) to the guard-evaluation
  function for that family, replacing the current if/if/fall-through chain in `evaluate_guards`.
  Carries exactly the families this mission registers explicitly (`software-dev`, `research`,
  `documentation`, `plan`); any family not present is, by definition, unregistered and routes to
  the loud-block (legacy path) or neutral-degrade (composed path) behavior instead of an implicit
  entry.
- **Guard evaluation result**: A `list[str]` of human-readable failure descriptions, empty when
  all guards pass — the existing contract of `evaluate_guards`, unchanged in shape by this
  mission.
- **`doctor mission-type` state taxonomy**: The fixed, enumerated set of classification states a
  mission can fall into (`resolved`, `activated-unresolvable`, `unknown`, `typeless`,
  `legacy-key-only`, `error`) — see FR-008. Every mission in `kitty-specs/` must land in exactly
  one state; the taxonomy is exhaustive by construction (this spec's own requirement, not an
  implementation detail).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A `plan`-type mission's `review` step, evaluated with no `tasks/` directory and no
  work packages present, returns an empty guard-failure list (not the WP-iteration message) —
  verified by the ATDD test from FR-010 flipping from RED (pre-mission `main`) to GREEN
  (post-mission).
- **SC-002**: Feeding an unregistered/synthetic `mission_family` to `evaluate_guards` via the
  composed call path returns a neutral result with zero elements resembling the software-dev
  table's messages, and a log record is emitted at **WARNING level or above** (per FR-004)
  naming the family — verified by the new test from FR-011 asserting both the returned list and
  the captured log record's level.
- **SC-003**: Feeding the same unregistered `mission_family` to the legacy/CLI-native lookup
  function raises a structured exception — verified by the new test from FR-011 / User Story 3.
- **SC-004**: `tests/runtime/test_bridge_cores.py` and `tests/runtime/test_bridge_composition.py`
  pass unmodified (zero assertion-value changes) after the registry refactor — verified directly
  by running both files and diffing them against their pre-mission state.
- **SC-005**: `spec-kitty doctor mission-type --json` run against a fixture tree containing one
  mission per taxonomy state in FR-008 classifies every mission into the correct, single state
  with none omitted — verified by the new `test_doctor_mission_type.py` suite.
- **SC-006**: `spec-kitty doctor mission-type --fail-on <state>` exits non-zero when a matching
  mission exists and zero otherwise, matching `doctor identity`'s existing `--fail-on` exit-code
  contract byte-for-byte in shape.

## Out of Scope

The following four sites, independently verified as real, distinct-root-cause defects during
the readiness probe, are explicitly **deferred to one follow-up tracking issue that references
#3386** (per the operator's binding Option A decision — see Clarifications). This mission does
not modify, patch around, or partially address any of them; a follow-up issue naming all four
must be filed as part of this mission's close-out, but authoring that issue is close-out work,
not something this spec's functional requirements cover:

1. **The project-wide doctrine-override hatch** — `_project_has_doctrine_overrides`
   (`src/charter/activation/mission_type_profiles.py:1041`): an unknown `mission_type` hard-fails only when
   the project's `charter.yaml` declares no governance selections at all; any single selection
   anywhere silences the hard-fail for every unknown type project-wide.
2. **The two divergent meta readers** — `_read_meta_mission_type`
   (`src/charter/activation/mission_type_profiles.py:681`), which reads only the canonical `mission_type`
   key with no legacy fallback, versus `_canonical_meta_mission_type`
   (`src/specify_cli/mission.py:542`), which reads `mission_type` then falls back to the legacy
   `mission` key — the same conceptual read producing two different answers for a `meta.json`
   that carries only the legacy key.
3. **The dashboard's silent default to `"software-dev"`** —
   `src/specify_cli/dashboard/handlers/features.py:68`
   (`meta.get("mission", "software-dev")`), which reads only the legacy `mission` key and
   silently mislabels any mission authored entirely through the canonical `mission_type` key (no
   legacy key at all — the modern, expected case) as software-dev with no error, and is
   internally inconsistent with `src/specify_cli/dashboard/diagnostics.py:31-34`, which reads
   `mission_type` correctly as primary.
4. **The unverified wider census** (the issue's own "~22 sites" figure) — any site beyond the
   three named above and the guard-dispatch fall-through this mission fixes. The exact
   membership and count of that wider set was never established (see Clarifications); this
   mission does not attempt to enumerate or fix it.

This mission also does **not**:

- Add a mission-type roster/validation check inside `validate_meta` (see C-004 — the issue's
  own reasoning, strengthened by the corrected 15-of-27 figure, argues against this).
- Model guards as DRG graph primitives (`NodeKind.GUARD` / a `GATES` relation) — confirmed via
  `docs/adr/3.x/2026-07-16-2-mission-type-step-authority-and-template-vocabulary.md:104-105,122-123`
  to be an explicitly deferred, unrelated future epic slice ("Deferred without debt"). The
  `_GUARD_TABLES` registry fills in the existing engine-baked condition-table pattern; it does
  not anticipate or block that epic.
- Change typeless-mission behavior (no `mission_type` key at all) in any way — see NFR-001 and
  the Edge Cases section.

## Related Ledger Entry

`SPEC-KITTY-LEDGER.md` **SK-06** (`record-analysis` silently accepting a legacy carrier shape
and writing `verdict: unknown` instead of raising) is the same failure class this mission
fixes: silent success/degrade standing in for a loud, structured error. Noted here for the
pattern parallel per the mission brief; SK-06 itself is a distinct defect in a different
subsystem (`src/specify_cli/analysis_report.py:358`) and is not touched by this mission.
