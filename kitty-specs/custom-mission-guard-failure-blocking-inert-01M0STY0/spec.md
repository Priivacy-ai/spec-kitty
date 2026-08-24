# Mission Specification: Custom Mission Guard Failure Blocking Inert

**Mission Branch**: `fix/custom-mission-guard-3704`
**Created**: 2026-08-24
**Status**: Draft
**Input**: GitHub issue [#3704](https://github.com/Priivacy-ai/spec-kitty/issues/3704) —
"A custom mission family can never report a guard failure, and its `blocking:` manifest is
never read"

**Stacking note**: this mission's branch is based on `fix/org-tier-expected-artifacts-3703`
(PR [#3708](https://github.com/Priivacy-ai/spec-kitty/pull/3708), not yet merged at spec time).
See **Clarifications** below for the binding operator decision on why, and what that means for
red-first verification.

---

## Clarifications

### Decision record — stack vs. wait for PR #3708 (operator, 2026-08-24)

This answers **Q1** of the readiness probe
(`_readiness/3704-custom-mission-guard-failure-blocking-inert.md`, "Open questions" section),
which recommended **option A** ("land #3708 first, then start #3704"). The operator was asked
to choose between waiting for #3708 to merge, proceeding in parallel, or splitting the
mission, and **did not take the recommended option**. The operator's answer, recorded here
verbatim:

> STACK on #3708's branch. Do not wait for the merge; do not split the mission. The issue says
> Part 1 and Part 2 were "filed together deliberately" — keep them together in one mission, one
> PR.
>
> Rationale: AC-10 ("a custom mission family gates on its own filenames as long as it ships an
> `expected-artifacts.yaml`") can only be demonstrated end-to-end at the conventional
> `<org_root>/missions/<type>/` layout once #3708's path fix is live. Stacking gets that without
> waiting on the merge.

Consequences recorded for design/plan/implementation:

- This mission's actual branch, `fix/custom-mission-guard-3704`, is checked out **based on**
  `fix/org-tier-expected-artifacts-3703` (PR #3708) — not on `main`. It stays a single mission,
  single PR, covering both halves of the issue (guard-table dispatch AND presence/blocking).
- **§ATDD-First Discipline (charter, C-011)**: because of the stack, every WP's red-first ATDD
  verification MUST use `planning_base_branch = fix/org-tier-expected-artifacts-3703`, **not**
  `main`, when a reviewer checks that a test is RED before the WP's implementation commit. Using
  `main` as the red-verification base would spuriously show tests RED for reasons belonging to
  #3703 (the org-tier path anchor), not to this mission's own changes.
- Diffs computed while implementing this mission must be taken against
  `fix/org-tier-expected-artifacts-3703`, never against `main` (already merged into this
  branch's history; diffing against `main` would show #3703's changes as if this mission
  authored them).
- Option B (proceed now, test org-tier reach via a `SPEC_KITTY_PACKS_ROOT`-style synthetic
  reachability shortcut) and Option C (split Part 1 from Part 2 into two missions) were both
  considered by the readiness probe and rejected by this decision — not chosen, not adopted.

### AC-10 / AC-13 / AC-14 — pre-existing, external, NOT this mission's numbering

`runtime_bridge_io.py:873`'s docstring, `tests/runtime/next/test_pertype_presence_gate.py`, and
`tests/runtime/next/test_cli_guard_family.py` already cite `AC-10`, `AC-13`, and `AC-14`. These
belong to an **earlier, already-merged** mission, `rc3-charter-gate-predicate-inversion-01M0GGT1`
(its own `spec.md`, `AC-10`/`AC-13`/`AC-14`), and to the ADR it produced:
`docs/adr/3.x/2026-08-21-1-charter-gate-predicate-inversion.md`. That ADR's binding decision,
quoted verbatim from its "Decision" section:

> **Custom-family gate mechanism = data-driven presence, not code registration.** A custom
> mission family gates on its own artifacts by shipping an `expected-artifacts.yaml` whose
> `path_pattern` filenames become its presence set (`gather_artifact_presence` consults the
> per-type set): present → gate passes, absent → gate blocks (AC-10). No entry is added to the
> `_GUARD_TABLES` code map for custom families. The `evaluate_guards_strict`
> `UnregisteredMissionFamilyError` strict-raise is **retained** for guard-table *dispatch* of a
> genuinely unregistered family — a distinct concern (WP-iteration guards cannot be evaluated
> for an unknown family), and the correct fail-closed default.

That ADR wired the *presence-detection* half (proven by
`TestCustomFamilyPresenceGateFailsClosedBothDirections` in `test_pertype_presence_gate.py`,
which already passes against a monkeypatched built-in-tier manifest) but **never wired anything
that consumes the resulting presence set into an actual `guard_failures` list for a family
outside `_GUARD_TABLES`** — that gap is exactly issue #3704's Part 1. This mission's job is to
**fulfil** that ADR's stated decision, not reverse it: no entry gets added to `_GUARD_TABLES`
for custom families, and `UnregisteredMissionFamilyError`'s strict-raise stays exactly as-is for
a family with **no** declared manifest anywhere. This spec's own acceptance criteria are numbered
fresh — **AC-1** through **AC-9**, a single flat series that does not reset per user story
(AC-1–AC-3 under User Story 1, AC-4–AC-9 under User Story 2's **Acceptance Scenarios** subsection
— AC-9 appended there to keep the series flat and append-only even though it closes a loop opened
under User Story 1/FR-002, see AC-9's own text) — to avoid confusion with the pre-existing
AC-10/AC-13/AC-14; where a new AC extends or depends on one of those three, it says so explicitly
by full external reference (`rc3-charter-gate-predicate-inversion-01M0GGT1#AC-10`, etc.) rather
than reusing the bare number.

### Ledger corroboration

`SPEC-KITTY-LEDGER.md` entries `SK-78` and `SK-79` independently corroborate both halves of this
issue on `main`, from direct source reads on unrelated missions:

- **SK-78** (`pack-structured-carriers-01M0ME39`, 2026-08-23): confirms `_GUARD_TABLES` has
  exactly the 4 built-in keys, `"qa" in _GUARD_TABLES` is `False`, and the tolerant wrapper
  returns `[]` for the programme's own `qa` custom type — "zero guard failures, always."
- **SK-79** (same mission, same date): confirms `required_artifacts_for` reads `blocking:`
  correctly but has zero production callers and is excluded from `__all__`, and that the wired
  `_presence_filenames_for` is not step-scoped and ignores `blocking:` entirely — "a manifest
  author writes `blocking: true`... and nothing ever blocks."

Both entries match this spec's problem statement; neither is contradicted by anything below.

---

## User Scenarios & Testing *(mandatory)*

Both halves of the issue are written as independently testable stories, per the issue's own
framing ("one pipeline one stage apart"), but — per the Clarifications decision above — they
ship as **one mission, one PR**, because Part 1 alone (real dispatch) has nothing to evaluate
without Part 2's manifest reach, and Part 2 alone (manifest reach) has no consumer without
Part 1's dispatch fix.

### User Story 1 - A custom family's declared blocking artifacts actually gate its steps (Priority: P1)

A pack author ships a custom mission family (e.g. `qa`) with an `expected-artifacts.yaml`
manifest declaring `blocking: true` requirements per step. Today, every guard evaluation for
that family — CLI pre-check, WP-iteration pre-check, and the composed-action guard — either
raises `UnregisteredMissionFamilyError` (caught) or is caught and degraded to `[]` before ever
consulting the manifest, so the mission reports "all guards passed" at every step regardless of
what artifacts actually exist on disk.

**Why this priority**: this is the core silent-success defect (`SK-78`) — a mission "passing"
that was never actually evaluated is indistinguishable, from the operator's side, from a
mission that behaved. Nothing else in this mission matters if this isn't fixed.

**Independent Test**: with a custom mission family and its manifest reachable (built-in tier is
sufficient to test this story alone), call `gather_artifact_presence` +
`evaluate_guards_strict` (or the composed-action guard, or the WP-iteration pre-check) with the
step's blocking artifact absent, then present. Assert `guard_failures` is non-empty in the
absent case and empty *because it was genuinely evaluated* (not because of a swallowed
exception) in the present case.

**Acceptance Scenarios**:

**AC-1**. **Given** a custom mission family `qa` with a declared manifest requiring
   `qa-coverage.json` (`blocking: true`) at step `accept`, and the file absent, **When** the
   composed-action guard evaluates step `accept`, **Then** `guard_failures` contains an entry
   naming the missing artifact and the resulting `Decision.kind` is `blocked` — not `[]`.
**AC-2**. **Given** the same family and step with `qa-coverage.json` present, **When** the same
   guard evaluates, **Then** `guard_failures` is empty **and** this emptiness is reachable only
   via real evaluation against the manifest (provable by flipping the file's presence and
   observing the failure list change — a swallowed-exception `[]` cannot do this).
**AC-3**. **Given** a mission family with **no** manifest declared at any tier (genuinely
   unregistered, e.g. a typeless mission), **When** any of the three call sites evaluate a guard,
   **Then** behavior is **unchanged**: `evaluate_guards_strict` raises
   `UnregisteredMissionFamilyError`, and every tolerant caller degrades to `[]` — the extension
   point non-goal stays intact (`TestTypelessMissionFamily`,
   `TestIssue3627WpIterationUnregisteredFamilyDegrades` stay green).

---

### User Story 2 - An org-tier manifest's `blocking:` flag is the one actually consulted (Priority: P1)

An operator running an org doctrine pack ships `<org_root>/missions/<type>/expected-artifacts.yaml`
declaring which artifacts are `blocking: true` per step. Today the live runtime guard never
reaches that file at all (`_presence_filenames_for` reads only the built-in pack via
`MissionTemplateRepository.default()`), and even when a manifest IS reached, every bucket
(`required_always` + all of `required_by_step` + `optional_always`) is unioned with no
`blocking:` filter — so a `blocking: false` entry gates exactly as hard as a `blocking: true`
one, which is to say: not at all, since nothing consumes the distinction.

**Why this priority**: this is the manifest half of the same silent-success defect (`SK-79`).
Fixing Story 1's dispatch without this still evaluates against an empty or wrong-tier manifest
— fixing this without Story 1 still has no consumer for the correctly-filtered result.

**Independent Test**: stand up an org pack at `<org_root>/missions/<type>/expected-artifacts.yaml`
(the conventional layout, reachable now that this branch is stacked on #3708's path-anchor fix)
with a mix of `blocking: true` / `blocking: false` entries across two steps, and a built-in
manifest for the same family (or none) as a control. Assert the org file wins whole-file (never
merged), that only `blocking: true` absences produce guard failures, and that a `blocking: false`
absence never does — at each step independently.

**Acceptance Scenarios**:

**AC-4**. **Given** an org-tier manifest at `<org_root>/missions/qa/expected-artifacts.yaml` (the
   path #3703/#3708 fixed) declaring `qa-coverage.json` as `blocking: true` at `accept`, and a
   built-in manifest for `qa` that does NOT exist, **When** the guard evaluates step `accept`
   with the file absent, **Then** the org manifest is the one consulted (not silently treated as
   "no manifest") and the step blocks.
**AC-5**. **Given** the same org manifest also declaring `defect-log.md` as `blocking: false` at
   `accept`, absent, **When** the guard evaluates, **Then** its absence does NOT appear in
   `guard_failures` — the flag is honored, not decorative.
**AC-6**. **Given** both a built-in manifest for `qa` (if one existed) and an org manifest for
   `qa`, **When** the manifest is resolved, **Then** the org file wins as a whole-file
   replacement — never field-merged with the built-in one, matching
   `resolve_org_expected_artifacts`'s documented last-existing-match-wins /
   whole-file-replacement contract (#3703).
**AC-7**. **Given** the four built-in families (`research`, `documentation`, `software-dev`,
   `plan`), **When** any of their guards evaluate under the fixed code, **Then** `guard_failures`
   output is byte-identical to pre-fix behavior at every existing fixture — none of them is
   step-scoped or blocking-filtered differently than today (NFR-003; see Non-Goals).
**AC-8**. **Given** the CLI/WP-iteration dispatch path (`_dn_dependency_gate`,
   `runtime_bridge.py`, ~line 1538-1643, which already holds `repo_root` as a local both before
   and after its `_check_cli_guards` calls at ~line 1608 and ~line 1643) runs a custom mission
   family with an org-tier manifest and no built-in manifest, **When** the guard is evaluated,
   **Then** `resolve_org_roots` is invoked with the real, non-`None` `repo_root` the enclosing
   function already holds — not a default `repo_root=None` left unthreaded — so the org manifest
   is genuinely reachable from this call site, not merely reachable in a unit test that calls
   the leaf function directly (see FR-004).
**AC-9**. **Given** two families evaluated at the same step — (a) `qa` with a manifest present
   (built-in or org tier) whose `required_always` and `required_by_step` for that step are each
   either empty or contain only `blocking: false` entries, so `required_artifacts_for` returns
   `[]`; and (b) a genuinely
   typeless family with **no** manifest at any tier, whose `required_artifacts_for` also returns
   `[]` for the same reason — **When** `evaluate_guards_strict` evaluates both, **Then** they are
   NOT treated identically despite both having an empty `required_artifacts_for` result: (a)
   returns `guard_failures == []` via genuine evaluation (`snapshot.blocking_artifact_names ==
   frozenset()`, not `None`) and does **not** raise; (b) still raises
   `UnregisteredMissionFamilyError` (`snapshot.blocking_artifact_names is None`), exactly as AC-3
   requires. This proves FR-002 outcome 1 and outcome 2 are actually distinguishable end to end
   from the snapshot alone — not merely "both empty" (FR-006's `None`-vs-`frozenset()` signal;
   see `SPEC-FRESH-001`).

---

### Edge Cases

- **Malformed manifest — YAML-syntax invalid.** Corrected against live source (a prior draft of
  this spec claimed both tiers degrade "silently... exactly the same" — false; see FR-010): the
  built-in and org tiers are **asymmetric** today, and this mission does not reconcile that
  asymmetry (out of scope). Built-in tier: `MissionTemplateRepository.get_expected_artifacts`
  raises `MalformedManifestError` loudly for a present-but-YAML-broken manifest — fail-loud by
  design, already fixed (issue #3412 is resolved at this call site, not an open gap; pinned by
  the live, passing `tests/doctrine/missions/test_repository.py::test_malformed_manifest_fails_loud_distinct_from_absent`).
  Org tier: `resolve_org_expected_artifacts` still degrades a YAML-syntax failure to "no manifest"
  silently (logging a `WARNING`, not raising). Neither behavior changes in this mission.
- **Malformed manifest — schema invalid.** Corrected against live source (a prior draft claimed
  this "already" raises `ManifestSchemaError` for both tiers "matching the precedent
  `ManifestRegistry.load_manifest` already established" — false for this mission's call path; see
  FR-010): `ManifestSchemaError` is defined and raised only by
  `specify_cli.dossier.manifest.ManifestRegistry.load_manifest`, a sibling module this mission's
  blast radius does not call. This mission's own call path
  (`resolver.py::_load_expected_artifact_manifest` → `ExpectedArtifactManifest.model_validate(...)`)
  has zero exception handling today, so a schema-invalid manifest raises a bare, undomained
  `pydantic.ValidationError` that would otherwise propagate uncaught through
  `decide_next_via_runtime` (the only exception caught on that call path is
  `UnregisteredMissionFamilyError`). Because this mission's WP02 already edits
  `_load_expected_artifact_manifest` to add org-tier awareness (FR-008) — the change that first
  makes this exact crash reachable for the org tier — FR-010 closes that specific crash risk in
  the same function, for both tiers, rather than leaving it as a silent side effect of the
  org-tier work. See FR-010 for the resulting contract and the rationale for this scope choice.
- **Missing manifest at both tiers.** A family with no `expected-artifacts.yaml` in the built-in
  pack AND no org-pack override resolves identically to today's "no manifest" case: empty
  presence set, `UnregisteredMissionFamilyError` strict-raise retained at dispatch, tolerant
  callers degrade to `[]`. This is the sanctioned neutral outcome (Non-Goals) — not a silent
  pass, because nothing was ever declared to check.
- **WP-iteration pre-check vs. composed-action guard disagreeing.** Both
  `runtime_bridge.py`'s WP-iteration pre-check (~line 1607) and
  `runtime_bridge_composition.py::_check_composed_action_guard` (~line 491) currently catch
  `UnregisteredMissionFamilyError` independently and both degrade to `[]` — coincidentally
  agreeing today only because both do nothing. Once either consults a declared manifest, they
  MUST route through the same data-driven evaluation for the same `(mission_family, step_id)`
  snapshot, so a mission cannot see itself blocked on one dispatch path and clear on the other
  for the same underlying artifact state (single canonical authority, charter governing
  principle).
- **A mission mid-flight when this change lands.** See NFR-002 (Reflexivity) below.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Data-driven evaluation for a declared-but-untabled family | US1 | High | Open |
| FR-002 | Three distinguishable dispatch outcomes | US1 | High | Open |
| FR-003 | All three call sites converge on one evaluation | US1 | High | Open |
| FR-004 | Org-tier-aware manifest lookup for the presence gate | US2 | High | Open |
| FR-005 | Presence gathering stays family-scoped, not step-scoped | US2 | High | Open |
| FR-006 | `blocking:` honored at the evaluation layer | US2 | High | Open |
| FR-007 | `required_artifacts_for` wired in and restored to `__all__` | US1/US2 | High | Open |
| FR-008 | `required_artifacts_for`'s own manifest lookup becomes org-aware | US2 | High | Open |
| FR-009 | Byte-identical behavior for the 4 built-in families | US2 | High | Open |
| FR-010 | Malformed-manifest handling: correct the precedent claim; close the org-tier schema-validation crash risk WP02 introduces | Edge cases | Medium | Open |
| FR-011 | `accept` step's built-in `[]` stays untouched | Non-goals | Medium | Open |
| FR-012 | `mission_v1.guards`/`GUARD_REGISTRY` not touched | Non-goals | Medium | Open |

**FR-001 — Data-driven evaluation for a declared-but-untabled family.** When
`_GUARD_TABLES.get(snapshot.mission_family)` (`_GUARD_TABLES` declared at
`runtime_bridge_cores.py:676-681`; the `.get()` dispatch call itself is at
`runtime_bridge_cores.py:693`, inside `evaluate_guards_strict`) has no entry for the family, AND
that family has a declared `expected-artifacts.yaml` manifest reachable at built-in or org tier
(per FR-004), guard evaluation MUST produce real `guard_failures` for `snapshot.step_id` from
that manifest's blocking requirements — instead of raising `UnregisteredMissionFamilyError` /
degrading to `[]`. No entry is added to the `_GUARD_TABLES` dict for the family
(ADR-preserving, see Clarifications). **Layering note (see FR-006):** the manifest's blocking
requirements are resolved into a snapshot-carried name set in the I/O layer, before the snapshot
ever reaches `runtime_bridge_cores.py` — `evaluate_guards_strict`'s own code, which lives inside
`runtime_bridge_cores.py` and is therefore bound by that module's stdlib-only import boundary
(`tests/architectural/test_bridge_cores_import_boundary.py`), only compares snapshot data it is
handed; it never itself calls a manifest-loading, non-stdlib-importing function.

**FR-002 — Three distinguishable dispatch outcomes.** After this fix, exactly three outcomes
must be reachable and distinguishable for a family outside `_GUARD_TABLES`, never collapsed into
one silent `[]`:
1. *No manifest declared at any tier* — the extension-point-preserving neutral case: strict-raise
   / tolerant-degrade-to-`[]`, unchanged from today.
2. *Manifest declared, step's blocking artifacts all present* — a genuine pass: `guard_failures`
   is `[]` because evaluation ran and found nothing missing, not because an exception was
   swallowed.
3. *Manifest declared, one or more blocking artifacts absent* — a genuine failure:
   `guard_failures` is non-empty, naming the missing blocking artifact(s), surfaced as
   `Decision(kind=blocked)` by the existing `step_or_blocked` machinery
   (`runtime_bridge_cores.py`).

**Routing signal (see FR-006):** `required_artifacts_for` alone cannot tell outcome 1 apart from
outcomes 2/3 — its own docstring (`resolver.py:634-654`) collapses "no manifest anywhere" and
"manifest declared, nothing blocking at this step" into the same empty `list[str]`. The signal
that lets `evaluate_guards_strict` route between outcome 1 and outcomes 2/3 is
`ArtifactPresenceSnapshot.blocking_artifact_names`'s `None`-vs-`frozenset()` distinction — `None`
only when no manifest is reachable at any tier, a real (possibly empty) `frozenset` whenever one
is. FR-006 specifies exactly how the I/O layer populates it and how the evaluator consults it.

**FR-003 — All three call sites converge on one evaluation.** The tolerant wrapper
(`evaluate_guards`, `runtime_bridge_cores.py:699-716`), the composed-action guard
(`_check_composed_action_guard`, `runtime_bridge_composition.py:429-499`), and both of
`runtime_bridge.py`'s pre-check blocks (WP-iteration, ~line 1607-1610, inside
`_dn_dependency_gate`; the CLI pre-check, ~line 1631-1643) MUST reach the same FR-001/FR-006
evaluation result for the same `(mission_family, step_id)` input, so the WP-iteration path and
the composed-action path cannot disagree for the same on-disk artifact state (see Edge Cases).
**Layering note:** "reach the same evaluation" means every one of these callers ends up invoking
`runtime_bridge_cores.evaluate_guards_strict`/`evaluate_guards` over an
`ArtifactPresenceSnapshot` that the I/O layer already populated with the manifest-derived
`blocking_artifact_names` field (FR-006) — none of these call sites, including
`evaluate_guards`/`evaluate_guards_strict` themselves, calls `required_artifacts_for` or any
other manifest-loading function directly; only `runtime_bridge_io.py`'s presence-gathering code
does that, upstream of the snapshot. Regression guard for this convergence:
`test_non_software_dev_missing_artifact_owned_by_composed_guard`
(`tests/runtime/test_bridge_parity.py:1242`; see NFR-004).

**FR-004 — Org-tier-aware manifest lookup for the presence gate, threaded to every real call
site.** `_presence_filenames_for` (`runtime_bridge_io.py:841`, currently calling only
`MissionTemplateRepository.default()`) MUST also consult the org tier via
`charter.org_expected_artifacts.resolve_org_expected_artifacts` (already in this branch's
history from #3703/PR #3708) against `<org_root>/missions/<mission_type>/expected-artifacts.yaml`,
with the same last-existing-match-wins precedence and whole-file (never field-merged) replacement
`resolve_org_expected_artifacts` already implements. The parameter shape to follow is the one
`specify_cli.dossier.manifest.ManifestRegistry.load_manifest`'s FR-008/WP05 fix already
established: an optional `repo_root: Path | None = None`-shaped parameter, defaulting to
today's built-in-only behavior for any existing caller that does not (yet) have a project root
in scope, so this fix does not require every current call site to change shape simultaneously —
but the optionality is a compatibility default for callers with no root in scope, **not**
license to leave a real, already-in-scope `repo_root` unforwarded. Specifically, this FR REQUIRES
that each of the following gains a `repo_root: Path | None = None` parameter (or, where it
already has one, forwards it) and passes the REAL value it already holds down to
`_presence_filenames_for` and `required_artifacts_for` — an implementation that adds the optional
parameter only at the leaf and stops does NOT satisfy this FR:
1. `gather_artifact_presence` (`runtime_bridge_io.py:931`) — MUST gain and forward `repo_root`.
2. `_check_cli_guards` (`runtime_bridge.py:751`) — MUST gain and forward `repo_root`, called from
   `_dn_dependency_gate` (`runtime_bridge.py`, ~lines 1538-1643), which already holds `repo_root`
   as a local (`repo_root = ctx.repo_root`) both before and after its two `_check_cli_guards`
   calls (~line 1608, ~line 1643) — that already-live local MUST be the value forwarded, not a
   dropped default.
3. `_check_composed_action_guard` (`runtime_bridge_composition.py:429`) — MUST gain and forward
   `repo_root`, called from `_dispatch_via_composition` (`runtime_bridge_composition.py:502`),
   which already receives `repo_root` as a REQUIRED keyword parameter — its call to the guard at
   `runtime_bridge_composition.py:626` (`_rb._check_composed_action_guard(action, feature_dir,
   mission=mission, legacy_step_id=legacy_step_id)`) currently drops it, and this FR requires
   that it stop dropping it.

See AC-8 for the acceptance scenario pinning this end-to-end wiring (asserting `resolve_org_roots`
is invoked with the real `repo_root` when the CLI/WP-iteration path runs a custom family with an
org-tier manifest).

**FR-005 — Presence gathering stays family-scoped, not step-scoped.** `_presence_filenames_for`
continues to union `required_always` + every `required_by_step` list + `optional_always` across
the *whole family*, not filtered to the caller's `step_id` — this is the documented, deliberate
non-step-scoping (`runtime_bridge_io.py:851-873`) that a prior attempt at step-scoping broke by
spuriously blocking the software-dev composed `tasks` guard and the `plan` family's
`specify`/`plan` guards (their manifest step keys don't match their composed action names). This
fix must not re-trigger `tests/runtime/test_bridge_parity.py::test_coverage_floor_is_met`, which
already caught that regression once.

**FR-006 — `blocking:` honored at the evaluation layer, not the gathering layer, computed in the
I/O layer and handed to cores.py as data — carrying an explicit manifest-declared signal, not
just an empty set.** The `blocking:` distinction (dropped entirely today by
`project_artifact_name_set`, `step_projection.py:128-160`, which the presence-gathering path
uses) MUST be resolved by calling `required_artifacts_for(step, mission_type)` — already
step-scoped and already filtered to `spec.blocking` (`resolver.py:634-654`) —
**from `runtime_bridge_io.py`, alongside `_presence_filenames_for`, during the same
presence-gathering pass FR-005 performs**. The resulting blocking-filtered artifact-name set MUST
be threaded into `ArtifactPresenceSnapshot` (`runtime_bridge_io.py:900`) as a new field typed
`blocking_artifact_names: frozenset[str] | None`, following the same `X | None = None`
optional-field idiom this dataclass already uses for `legacy_step_id` and `wp_advance_ready`. Its
`None`-vs-empty-`frozenset` states are load-bearing and MUST NOT be conflated:

- **`None`** — no `expected-artifacts.yaml` is reachable for this family at *any* tier (built-in
  or org, per FR-004). `required_artifacts_for`'s own collapsing of "no manifest" and "manifest,
  nothing blocking at this step" into the same empty `list[str]` (its documented behavior,
  `resolver.py:634-654`) is therefore NOT what populates this field directly:
  `gather_artifact_presence` MUST determine manifest-reachability itself, reusing the exact same
  tier-checking `config is None` / org-tier-equivalent logic FR-004/FR-005 already have to run for
  `_presence_filenames_for` (`runtime_bridge_io.py:891-892`) — and set `blocking_artifact_names` to
  `None` only when that check finds no manifest at either tier.
- **A real `frozenset`, including `frozenset()`** — a manifest WAS resolved at one of the two
  tiers; `required_artifacts_for(step, mission_type)`'s result (possibly empty, if the manifest
  declares nothing blocking at this particular step) is wrapped in `frozenset(...)` and threaded
  through as-is. An empty `frozenset()` here is therefore a genuine, resolved "nothing blocking"
  fact — never a stand-in for "no manifest".

Because `runtime_bridge_cores.py` types the snapshot only through its structural
`_ArtifactPresenceSnapshotLike` Protocol (`runtime_bridge_cores.py:354`, one read-only `@property`
per field, deliberately not importing `runtime_bridge_io.ArtifactPresenceSnapshot` itself — see
that Protocol's own docstring), the Protocol MUST also gain a matching
`blocking_artifact_names -> frozenset[str] | None` property alongside the dataclass field, exactly
as it already mirrors `legacy_step_id` and `wp_advance_ready`.

`evaluate_guards_strict` reads this signal as the first branch taken once `_GUARD_TABLES.get(snapshot.mission_family)`
(`runtime_bridge_cores.py:693`) misses, mirroring the existing `if guard_table_entry is None:
raise` idiom immediately below that lookup (`runtime_bridge_cores.py:694-695`): it next checks
`snapshot.blocking_artifact_names is None` — if `True`, it raises `UnregisteredMissionFamilyError`
exactly as today (FR-002 outcome 1 / AC-3 / C-001, no manifest anywhere, nothing new to evaluate);
if `False` (a real, possibly-empty, `frozenset`), it evaluates genuinely by comparing
`snapshot.present_artifacts` against `snapshot.blocking_artifact_names`, returning `[]` when the
blocking set is a subset of what's present — including the degenerate case where
`blocking_artifact_names` is itself `frozenset()`, which is now visibly distinct from the `None`
case and yields a genuine pass (FR-002 outcome 2), never a raise. `runtime_bridge_cores.py` stays
a pure function of snapshot data it is merely handed, and is **never itself a caller of
`required_artifacts_for`** or any other non-stdlib-importing resolver. This is a hard requirement,
not an implementation suggestion: `runtime_bridge_cores.py` is bound by
`tests/architectural/test_bridge_cores_import_boundary.py` (an AST-walk gate, catching
in-function and in-`try` imports, forbidding any non-stdlib import out of that module other than
`runtime.next.decision`), and `required_artifacts_for` imports `charter.missions` (non-stdlib) to
do its manifest I/O — calling it from inside `evaluate_guards_strict`/`evaluate_guards` would red
that gate. This keeps the gathering layer's union-everything shape (preserving FR-005) while
making the actual pass/fail decision both step-scoped and `blocking:`-aware, which is what AC-10
(the prior mission's docstring claim) always meant but never had a consumer to enforce, AND makes
FR-002's three outcomes actually distinguishable end to end rather than "both empty" (see AC-9).
(Non-goal: relaxing `test_bridge_cores_import_boundary.py`'s zero-dependency-leaf invariant —
this FR's whole point is to keep that gate green by construction rather than touch it.)

**FR-007 — `required_artifacts_for` wired in and restored to `__all__`.** Once FR-001/FR-006
give `required_artifacts_for` (`resolver.py:634`) its first production caller under `src/`, it
MUST be added back to `resolver.py`'s `__all__` (currently excluded, lines 46-57) alongside that
caller, and the stale comment at lines 58-66 explaining the WP04b deferral MUST be updated or
removed to reflect the real wiring — not left claiming "no runtime caller... until WP04b" once
one exists.

**FR-008 — `required_artifacts_for`'s own manifest lookup becomes org-aware.**
`required_artifacts_for` calls `_load_expected_artifact_manifest(mission_type)`
(`resolver.py:555-576`), whose docstring states plainly "Built-in/project tier only (no org
lookup...)". If FR-006 wires `required_artifacts_for` into the live gate without also fixing
this, an org-tier custom family would silently fall back to "no manifest" one layer down from
where FR-004 just fixed it — reintroducing Part 2's exact defect underneath the fix. This lookup
MUST gain the same org-tier awareness as FR-004, via the same `repo_root`-threading pattern.

**FR-009 — Byte-identical behavior for the 4 built-in families.** `research`, `documentation`,
`software-dev`, and `plan` all have `_GUARD_TABLES` entries today and MUST continue dispatching
through them unchanged — the FR-001 fallback only activates when `_GUARD_TABLES.get(family)` is
`None`, so it is structurally unreachable for any of the four regardless of whether they also
happen to carry a manifest. Pinned by
`tests/specify_cli/runtime/test_configured_artifact_name.py`'s byte-compat characterization and
the existing `TestAC14SoftwareDevUnchanged`-class tests in `test_cli_guard_family.py`.

**FR-010 — Malformed-manifest handling: correct the record, close the new org-tier
schema-validation crash risk.** A prior draft of this FR and its Edge Cases entries asserted
this was already fully handled by existing precedent, at both tiers, identically — that claim is
false against live source (ANALYZE-ARCH-001). True current state, verified against live source:

1. Built-in-tier YAML-syntax failures raise `MalformedManifestError` loudly
   (`MissionTemplateRepository.get_expected_artifacts`) — already fixed, not an open #3412 gap.
2. Org-tier YAML-syntax failures degrade silently (`resolve_org_expected_artifacts`, with a
   `WARNING` log) — a pre-existing built-in/org asymmetry this mission does **not** reconcile
   (out of scope; the two tiers are not symmetric today and this FR does not change that).
3. Neither tier raises `ManifestSchemaError` for schema-invalid content on this mission's call
   path. That contract lives only in `specify_cli.dossier.manifest.ManifestRegistry.load_manifest`
   — a sibling module this mission never calls. `resolver.py::_load_expected_artifact_manifest`
   calls `ExpectedArtifactManifest.model_validate(...)` with zero exception handling, so a
   schema-invalid manifest raises a bare `pydantic.ValidationError`, uncaught, today.

**Design decision (Option A — close the crash risk, chosen over scoping it out):** WP02
(FR-008) already edits `_load_expected_artifact_manifest` to add org-tier awareness — the change
that, for the first time, makes this exact `model_validate(...)` call reachable for an
org-authored manifest (today `resolver.py` has zero org-tier lookup, so this crash path does not
yet exist for org manifests). Rather than leave that newly-introduced crash exposure as an
undocumented side effect of FR-008, this mission closes it in the same function: wrap
`ExpectedArtifactManifest.model_validate(...)` in `try/except pydantic.ValidationError`, and
re-raise the existing domain `ManifestSchemaError` (imported from `specify_cli.dossier.manifest`
— precedented by `specify_cli.sync.namespace` and `specify_cli.sync.dossier_pipeline`, which
already import that same type across the identical `specify_cli.runtime` ↔ `specify_cli.dossier`
sibling-package seam; no architectural boundary gate forbids it), for both the built-in and the
new org-tier branch. This is a small, in-file addition to a function WP02 already edits — it adds
no new file to WP02's owned-files set and does not expand plan.md's Seam/module-placement table
beyond the row it already commits to for `_load_expected_artifact_manifest`. See tasks.md/WP02's
new T009b (ATDD-RED) and T010b (implementation) subtasks.

**Rationale for Option A over Option B (explicit scope-out):** Option B (documenting the
uncaught-crash as an accepted risk) was considered and rejected here specifically because the
fix's cost is smaller than the honesty cost of documenting a self-inflicted, easily-closed defect
as "accepted" — the touched function, the exception type, and the import precedent all already
exist; only the `try/except` and the re-raise are new. This does not reconcile the separate,
pre-existing built-in/org YAML-syntax asymmetry (#2 above), which remains explicitly out of scope
for this mission (matches the smallest-viable-diff / locality-of-change reconciliation the
charter requires: fix only what this mission's own new code introduces).

**FR-011 / FR-012 — Non-goal preservation.** The `accept` step's deliberate `[]` for built-in
families, and `mission_v1.guards`/`GUARD_REGISTRY`, are untouched by this mission — see
Non-Goals.

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Byte-compat for built-in families | `guard_failures` output for `research`/`documentation`/`software-dev`/`plan` is byte-identical, at every existing fixture in `tests/runtime/test_bridge_parity.py` and `tests/specify_cli/runtime/test_configured_artifact_name.py`, before and after this change. | Reliability | High | Open |
| NFR-002 | Reflexivity — mid-flight missions | A mission already running when this change lands is not retroactively re-evaluated: `status.events.jsonl` and past `Decision`s are never rewritten. The mission's *next* `next`/guard-evaluation call after deploy uses the corrected logic. A custom mission previously advancing silently past a step with an unmet `blocking: true` requirement may, on its next evaluation, correctly BLOCK where it previously would not — this is the intended fix, and must be documented as an operator-visible behavior change for in-flight custom missions, not silently absorbed. | Reliability | High | Open |
| NFR-003 | ATDD-first / red-first discipline (charter C-011) | Every WP has a failing-first ATDD test committed as a separate commit before any implementation commit for that WP. Because this mission is stacked (see Clarifications), red-verification MUST use `planning_base_branch = fix/org-tier-expected-artifacts-3703`, not `main`; green is verified on the WP's final commit. **Accepted baseline:** `main` (and therefore this stacked branch) carries known-red tests unrelated to this mission (issue #3284, ~23 failures + 2 errors, confirmed genuinely open, not this mission's to fix) — before implementing, each WP MUST re-run the narrow test files it touches on `fix/org-tier-expected-artifacts-3703` (not `main`) to establish this mission's own true-red baseline for those files, and apply CLAUDE.md's baseline-red classification protocol (§"Test-run baseline-red gotcha") so "green is verified" above is unambiguous about what counts as green versus accepted pre-existing noise. | Process | High | Open |
| NFR-004 | Coverage floor stays met | `tests/runtime/test_bridge_parity.py::test_coverage_floor_is_met`'s guard-branch floor (currently >= 18 branches reached, `_GUARD_BRANCH_FLOOR` at `test_bridge_parity.py:1196`) must stay met after this change. The specific mechanism that keeps it from regressing is the family-scoping of `_check_cli_guards`/the non-WP CLI pre-check to the `software-dev` mission family alone (`runtime_bridge.py`, ~line 1642, #3407/M3) — **not** FR-005 (FR-005's family-scoping is a separate, unrelated mechanism in `runtime_bridge_io.py`'s presence-gathering; see its own rationale). This mission's FR-003 call-site convergence touches exactly the CLI-pre-check code the floor's history (`test_bridge_parity.py:1170-1195`) is about, so `test_non_software_dev_missing_artifact_owned_by_composed_guard` (`test_bridge_parity.py:1242`) — which pins that the CLI pre-check stays software-dev-scoped — is the regression guard that must keep passing. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No hard-block for unknown/typeless families | An unregistered custom mission type with **no declared manifest anywhere** MUST continue to run to completion via the frozen template's `agent_profile`/`contract_ref` binding — `evaluate_guards_strict` keeps raising `UnregisteredMissionFamilyError` for dispatch, and every existing tolerant caller keeps degrading to `[]`. Pinned by `TestTypelessMissionFamily`, `TestIssue3627WpIterationUnregisteredFamilyDegrades`, `test_unregistered_family_guard_dispatch_strict_raise_is_retained`, and `tests/specify_cli/next/test_runtime_bridge_composition.py::TestCustomMissionComposition`'s frozen-template e2e walk. | Technical | High | Open |
| C-002 | No naive step-scoping of `_presence_filenames_for` | A step-scoped redesign of the presence-gathering layer was tried before this mission and reverted after it red `test_coverage_floor_is_met` by spuriously blocking software-dev's composed `tasks` guard and `plan`'s `specify`/`plan` guards. This mission solves `blocking:`-awareness at the evaluation layer (FR-006), not by re-attempting step-scoped gathering. | Technical | High | Open |
| C-003 | Not the org-tier path anchor itself | The `<org_root>/missions/<mission_type>/expected-artifacts.yaml` path anchor fix is #3703/PR #3708, already merged into this branch's history — this mission consumes that fix (FR-004/FR-008), it does not re-implement or re-verify the anchor itself. | Technical | High | Open |
| C-004 | `accept` step's built-in `[]` is deliberate | Not reopened by this mission — see FR-011. | Technical | Medium | Open |
| C-005 | `mission_v1.guards` / `GUARD_REGISTRY` not revived | Not reopened by this mission — see FR-012. | Technical | Medium | Open |

### Key Entities

- **`_GUARD_TABLES`** (`runtime_bridge_cores.py`): the existing 4-key dispatch table for
  `research`/`documentation`/`software-dev`/`plan`. Unchanged in shape and membership by this
  mission (C-001/ADR).
- **`ExpectedArtifactManifest`** (`doctrine.missions`): the parsed `expected-artifacts.yaml`
  model — `required_always`, `required_by_step`, `optional_always`, each spec carrying
  `artifact_key`, `path_pattern`, `blocking`.
- **`ArtifactPresenceSnapshot`** (`runtime_bridge_io.py`): the fact-only structure
  `gather_artifact_presence` builds, including `present_artifacts` (populated from
  `_presence_filenames_for`'s family-scoped, now org-aware, filename set) and the new
  `blocking_artifact_names: frozenset[str] | None` field (FR-006) — the step-scoped,
  `blocking:`-filtered name set `required_artifacts_for` resolves, computed in the I/O layer so
  `runtime_bridge_cores.py`'s evaluator stays a pure consumer of snapshot data. `None` and
  `frozenset()` are two distinct, load-bearing states, not interchangeable emptiness: `None` means
  no manifest is reachable for the family at any tier (routes `evaluate_guards_strict` to raise
  `UnregisteredMissionFamilyError` / degrade, FR-002 outcome 1); `frozenset()` means a manifest
  WAS resolved and declares nothing blocking at this step (routes to a genuine `guard_failures ==
  []` pass, FR-002 outcome 2) — see FR-006. The structural `_ArtifactPresenceSnapshotLike`
  Protocol `runtime_bridge_cores.py` types against (`runtime_bridge_cores.py:354`) carries a
  matching `frozenset[str] | None` property so the evaluator can read the signal without importing
  this dataclass.
- **`Decision` / `DecisionKind.blocked`** (`runtime_bridge_cores.py`): the outcome type a
  non-empty `guard_failures` list surfaces as, via `step_or_blocked`.
- **Org roots** (`charter.drg.org_pack_config.resolve_org_roots`): the existing-filtered list of
  org doctrine roots a `repo_root` resolves to, consumed by
  `resolve_org_expected_artifacts` (FR-004/FR-008).

## Non-Goals

Mirrors the issue's own Non-goals section verbatim in substance:

- **Not** making an unknown/typeless mission family hard-block (C-001). A live end-to-end test
  (`TestCustomMissionComposition`'s frozen-template walk) pins that an unregistered custom
  mission type runs to completion; other tests pin that composition dispatch degrades rather
  than raises for a family with no manifest. This mission gives a family with a *declared*
  manifest real evaluation — it does not change what happens to a family with none.
- **Not** re-introducing a step-scoped `_presence_filenames_for` (C-002). Any fix has to solve
  the `blocking:` gap at the evaluation layer, not by re-attempting the reverted step-scoped
  gathering design.
- **Not** the org-tier manifest path anchor itself (C-003) — that is #3703/PR #3708, already in
  this branch's history; this mission consumes it, does not redo it.
- **Not** the `accept` step's deliberate `[]` for built-in families (C-004/FR-011).
- **Not** reviving `mission_v1.guards` / `GUARD_REGISTRY` (C-005/FR-012).
- **Not** adding a `_GUARD_TABLES` entry for any custom family — the ADR
  (`docs/adr/3.x/2026-08-21-1-charter-gate-predicate-inversion.md`) already decided against
  code-registration in favor of data-driven presence; this mission fulfils that decision, it
  does not reverse it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a custom mission family with a declared manifest (built-in or org tier) and a
  `blocking: true` requirement absent on disk, the family's guard evaluation at the relevant
  step returns a non-empty `guard_failures` naming the missing artifact, at all three call sites
  (tolerant wrapper, composed-action guard, WP-iteration pre-check) — where today all three
  return `[]` unconditionally.
- **SC-002**: The same scenario with the required artifact present returns `guard_failures == []`
  reachable only via genuine evaluation (provable by toggling the file and observing the
  failure list change), not via a swallowed `UnregisteredMissionFamilyError`.
- **SC-003**: An org-tier `expected-artifacts.yaml` at `<org_root>/missions/<type>/` is the
  manifest actually consulted by `_presence_filenames_for` / the new evaluator — a built-in
  manifest for the same family, if any, is not silently preferred or merged with it.
- **SC-004**: A `blocking: false` entry in a declared manifest never contributes to
  `guard_failures` regardless of presence, at every step it's declared for.
- **SC-005**: `research`, `documentation`, `software-dev`, and `plan` produce byte-identical
  `guard_failures` output, at every existing fixture, before and after this change (NFR-001).
- **SC-006**: A family with no manifest declared anywhere still runs to completion with no hard
  block introduced (C-001), and `evaluate_guards_strict`/tolerant-degrade behavior for that case
  is unchanged.
- **SC-007**: `tests/runtime/test_bridge_parity.py::test_coverage_floor_is_met` and the full
  existing test files in the blast radius (`test_bridge_cores.py`, `test_pertype_presence_gate.py`,
  `test_cli_guard_family.py`, `test_configured_artifact_name.py`,
  `test_runtime_bridge_composition.py`) all stay green.
