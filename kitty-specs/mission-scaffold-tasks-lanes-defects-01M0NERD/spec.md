# Mission Specification: Mission scaffold → tasks → lanes: three compounding defects

**Mission Branch**: `fix/mission-scaffold-lanes-defects-3673`
**Created**: 2026-08-22
**Status**: Draft
**Input**: GitHub issue [Priivacy-ai/spec-kitty#3673](https://github.com/Priivacy-ai/spec-kitty/issues/3673) — "Three defects in the mission scaffold → tasks → lanes path"

## Summary

Three defects in `spec-kitty` sit on a single chain — `specify` scaffolding a mission,
`finalize-tasks` bootstrapping ownership, and lane computation writing `lanes.json` — and
each one hides the next. A mission that hits the first cannot reach `implement` at all,
and today there is no supported repair path for any of them. This mission does not add a
repair command; it makes every one of the three failure points **fail loudly instead of
succeeding silently**, so the defect is visible and diagnosable at the moment it occurs
rather than several commands later as an unexplained downstream error.

## Clarifications

### Decision Record — D1 (operator decision, binding)

Transcribed verbatim from `kitty-specs/mission-scaffold-tasks-lanes-defects-01M0NERD/tracer-design-decisions.md`,
recorded 2026-08-22. This decision is binding on this spec and on everything implemented
under it.

> ## D1 — Scope is fail-loud / reject-only. NO new CLI surface. (Operator decision, binding)
>
> Asked of the operator by the readiness probe, because CONTRIBUTING.md:377 requires prior
> maintainer agreement for new commands and arguments ("Pull requests with large changes
> that did not have a prior conversation and agreement will be closed."). Operator chose
> the fail-loud option:
>
> 1. `specify`'s `meta.json` commit **raises** instead of silently swallowing the exception —
>    the existing rollback machinery already handles this cleanly.
> 2. `execution_mode: code_change` combined with an explicit `owned_files: []` is **rejected
>    as an authoring error**, not accepted as intent.
> 3. Lane computation **raises** instead of silently writing nothing, and
>    `authoritative_surface` validation runs **regardless** of whether the manifest map is
>    empty.
>
> **Explicitly out of scope**: `spec-kitty migrate rebuild-meta`, a
> `finalize-tasks --reinfer-ownership` flag, or any other new command or flag.
>
> **Known, operator-accepted gap**: missions already broken today (with `meta.json` already
> missing) get **no repair path** from this mission. Deferred to a later, separately-agreed
> mission. The spec must state this gap explicitly rather than quietly growing CLI surface
> back in to close it.

This mission's requirements (FR-001 through FR-005 below) implement D1 exactly. No
requirement in this spec may be satisfied by introducing a new CLI command or flag — see
C-001.

### Charter/CLAUDE.md drift spotted during authoring

CLAUDE.md (`AGENTS.md:14` in this checkout) states "the eight binding practices"; the
charter (`.kittify/charter/charter.md:45-99`, "Quality & Tech-Debt Standing Orders") lists
**nine**, explicitly headed "Nine standing practices" at line 47, with practice 9 being
"Red-main & release discipline" (lines 92-99). This is the known drift called out in the
mission briefing; it is recorded here rather than silently resolved, per the charter's own
rule that the charter wins on disagreement and drift gets flagged, not silently picked. No
other charter/AGENTS.md disagreement was found during this authoring pass.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - `specify`'s meta.json commit fails loudly instead of silently (Priority: P1)

As a mission author running `spec-kitty specify` (or the `agent mission create` seam it
shares), when the commit that persists `meta.json` to its resolved home hits a hard git
failure, I need the command to fail and roll back rather than report success while
`meta.json` never lands — because a mission missing `meta.json` cannot run `next`,
`tasks`, `status lifecycle`, or `doctor topology`, and today there is no way to repair it
short of a fresh scaffold that forks a duplicate mission directory.

**Why this priority**: this is the first link in the chain. Every mission that hits this
defect is dead on arrival — it never reaches `plan`, let alone `implement` — so it is the
highest-priority defect to close even though it is the least frequently triggered of the
three (most environments do not have a dirty enough working tree to hit a hard commit
failure).

**Independent Test**: can be fully tested in isolation by forcing `_commit_feature_file`
to raise during `create_mission_core` (e.g. a locked `.git/index`, a pre-commit hook that
exits non-zero, or a detached-HEAD checkout) and asserting the command exits non-zero, the
working tree is restored to its pre-mission-create state, and no partially-scaffolded
mission directory is left in a state that reads as complete.

**Acceptance Scenarios**:

1. **Given** a checkout where the `meta.json` commit step will hit a hard git failure
   (e.g. a pre-commit hook that always rejects), **When** `spec-kitty specify` (or
   `agent mission create`) runs to completion of its git-mutating phase, **Then** the
   command exits non-zero, the error surfaces the underlying git failure (not a generic
   "something went wrong"), and `create_mission_core`'s existing rollback
   (`_restore_git_state_after_failed_create`) restores the operator's original branch,
   commit, and index tree — no orphaned mission directory, no orphaned coordination
   branch.
2. **Given** the same forced hard failure, **When** the command is invoked with
   `--json`, **Then** the JSON error payload names the failed step (`meta.json commit`)
   and the underlying git error text, so a calling agent can distinguish this from any
   other `specify` failure without parsing prose.
3. **Given** a checkout where there is genuinely nothing new to commit for `meta.json`
   (the legitimate no-op case `_commit_feature_file`'s docstring already documents),
   **When** `specify` runs, **Then** the command still succeeds exactly as it does today —
   this scenario proves the fix distinguishes "nothing to commit" (still silent, by
   design) from "hard failure" (now raises).
4. **Given** the `documentation` mission-type branch (the second call site, currently at
   `mission_creation.py:792-793`), **When** the same forced hard-failure condition is
   applied to that path, **Then** the identical raise-and-rollback behavior applies — the
   fix is not partial to only the primary mission-type branch.

---

### User Story 2 - a self-contradictory WP is rejected at bootstrap instead of silently degrading lane computation (Priority: P1)

As a mission author or the tasks-authoring agent, when a work package declares
`execution_mode: code_change` together with an explicit `owned_files: []` — a
self-contradictory pair, since a code-change WP that owns no files cannot be validated or
scheduled — I need `finalize-tasks` to reject that WP as an authoring error at bootstrap
time, before it is allowed to silently fall out of the ownership manifest and take lane
computation down with it.

**Why this priority**: this is the defect actually hit in the reported real-world mission
(8 of 8 WPs authored this way). It is also the one that most directly produces the
degrade-to-silent-success failure this mission exists to close: today the WP is accepted,
dropped from the manifest with no warning, and every downstream WP then fails to start
with an opaque `lanes.json is required` error that gives no hint the root cause was an
authoring mistake three commands earlier.

**Independent Test**: can be fully tested in isolation by authoring one WP file with
`execution_mode: code_change` and an explicit `owned_files: []` in its frontmatter, running
`finalize-tasks --validate-only` (or the full run) against it, and asserting the run fails
with an error identifying that WP by ID and naming the specific contradiction, rather than
succeeding and silently omitting the WP from the manifest.

**Acceptance Scenarios**:

1. **Given** a WP file with `execution_mode: code_change` and an explicit
   `owned_files: []`, **When** `finalize-tasks` runs its ownership-inference bootstrap
   (`_apply_ownership_inference`, `mission_finalize.py:1264`), **Then** the run fails
   before any manifest is built, naming the offending WP ID and stating the specific
   contradiction ("code_change WP declares no owned files"), instead of treating the
   explicit empty list as intent and silently skipping inference.
2. **Given** the same fixture, **When** `finalize-tasks --json` runs, **Then** the JSON
   error payload includes a machine-readable field identifying the WP ID and a stable
   error code for this specific contradiction, distinguishable from other
   `finalize-tasks` failure modes.
3. **Given** a WP with `execution_mode: planning_artifact` and an explicit
   `owned_files: []` (the existing, legitimate escape hatch — see Edge Cases and the
   SK-24 note below), **When** `finalize-tasks` runs, **Then** the WP is accepted exactly
   as it is today — this scenario proves the fix is scoped to the `code_change` +
   explicit-empty-list combination only, and does not touch the planning-artifact path.
4. **Given** a mission with a mix of WPs — some validly authored, one hitting the
   `code_change` + `owned_files: []` contradiction — **When** `finalize-tasks` runs,
   **Then** the run fails and reports the specific offending WP(s); it does not silently
   drop only the bad WP and proceed to compute lanes for the rest (that would still be a
   silent-success degradation for the mission as a whole).

---

### User Story 3 - lane computation and authoritative_surface validation fail loudly instead of degrading to a silent no-op (Priority: P2)

As a mission orchestrator relying on `finalize-tasks` to produce a trustworthy
`lanes.json`, when `_compute_and_write_lanes`'s actual guard condition trips — either the
ownership-manifest map (`wp_manifests`) ends up empty, or the dependency map
(`wp_dependencies`) ends up empty even though `wp_manifests` is non-empty (the guard is
the compound `if not (wp_manifests and wp_dependencies)`, `mission_finalize.py:1834`) —
whether from the defect-2 authoring error, from every WP legitimately being a planning
artifact, from a dependency-resolution gap, or from any other cause — I need lane
computation to raise a clear error instead of silently returning `(None, None)` while the
caller reports success, and I need `authoritative_surface` validation (glob-match,
overlap, audit-coverage) to run unconditionally rather than being skipped whenever the
manifest map happens to be empty.

**Why this priority**: this is the defect that turns 1 and 2 from "loud failures early"
into "silent failures with real consequences" if left unfixed — it is what let the
real-world mission report success while `lanes.json` was never written, and it is the
reason a placeholder or typo'd `authoritative_surface` value can sit unvalidated across
missions indefinitely (35+ occurrences of `authoritative_surface: src/` and 53 of
`authoritative_surface: ''` observed across mission task files in a downstream checkout,
none of them ever validated, because validation never ran). Ranked P2 relative to defect 2
because fixing defect 2 alone already prevents the most common real-world trigger; defect 3
closes the general case.

**Independent Test**: can be fully tested in isolation three ways — (a) construct a
fixture where `wp_manifests` is empty (e.g. every WP is a planning artifact with no
code-owning WPs, or all WPs were rejected under defect 2's fix) and assert
`_compute_and_write_lanes` raises rather than returning `(None, None)`; (b) construct a
fixture where `wp_manifests` is non-empty but `wp_dependencies` is empty, and assert
`_compute_and_write_lanes` also raises rather than returning `(None, None)` — the guard is
the compound `not (wp_manifests and wp_dependencies)`, and both halves must be covered,
not just the `wp_manifests`-empty half; (c) construct a fixture with a bad
`authoritative_surface` value (bare `src/`, empty string, a path with a spurious trailing
slash) on a mission whose manifest map is empty, and assert `_validate_ownership_manifests`
still runs and rejects it, rather than short-circuiting on emptiness.

**Acceptance Scenarios**:

1. **Given** a mission where, after valid WP filtering, `wp_manifests` is empty (all
   code-owning WPs were rejected, or none exist), **When** `_compute_and_write_lanes`
   (`mission_finalize.py:1820`) is reached, **Then** it raises a named error stating that
   lane computation cannot proceed with no ownership manifests, instead of returning
   `(None, None)` and letting the caller proceed to report success with no `lanes.json`
   written.
2. **Given** the same empty-manifest condition, **When** `finalize-tasks --json` runs,
   **Then** the JSON payload reports failure (not `"result": "success"`) with a
   machine-readable indication that lane computation did not run, and `lanes.json` is
   confirmed absent from the working tree — the caller cannot observe a success report
   alongside a missing artifact.
3. **Given** a mission where `wp_manifests` is empty AND at least one WP frontmatter
   carries a malformed `authoritative_surface` (bare `src/`, empty string, or a trailing
   slash on an otherwise-valid path), **When** `_validate_ownership_manifests`
   (`mission_finalize.py:1475`) is reached, **Then** validation still runs and rejects the
   malformed value with a specific error identifying the WP and the field — it does not
   return silently on the `if not wp_manifests: return` short-circuit at line 1484.
4. **Given** a mission where `authoritative_surface` values are all valid prefixes that
   genuinely match the project layout, **When** validation runs (now unconditionally),
   **Then** the mission passes exactly as it would with a non-empty manifest map — this
   scenario proves the fix does not turn a legitimately-empty, legitimately-valid mission
   into a spurious failure.
5. **Given** a mission where `wp_manifests` is non-empty (at least one valid code-owning
   WP survived filtering) but `wp_dependencies` is empty, **When**
   `_compute_and_write_lanes` (`mission_finalize.py:1820`, guard at line 1834) is reached,
   **Then** it also raises a named error rather than returning `(None, None)` — this
   scenario proves the fix covers the whole compound guard
   (`not (wp_manifests and wp_dependencies)`), not only the `wp_manifests`-empty half
   exercised by Acceptance Scenario 1.
6. **Given** an FR-003 reject fires (either half of the compound guard), **When** the
   working tree is inspected afterward, **Then** `lanes.json` is confirmed absent
   (guaranteed by this fix) — but WP frontmatter mutations and the `TasksCompleted` event
   persisted earlier in the same rejected run are **not** guaranteed absent; see NFR-004's
   narrowed scope below, which documents this as a known, accepted gap rather than a
   defect this mission closes.

---

### Edge Cases

- **Explicit-empty-list vs field-absent WP frontmatter**: a WP with `owned_files` entirely
  absent from frontmatter (the field never written) must continue to go through the
  existing inference path unchanged (`need_owned_files` remains true) — only an *explicit*
  `owned_files: []` combined with `execution_mode: code_change` is rejected under FR-002.
  This distinction is load-bearing: `_owned_files_yaml_is_explicit_empty_list` already
  exists to detect exactly this, and the fix must not collapse the two cases.
- **A mission with a mix of valid and invalid WPs**: see User Story 2, Acceptance
  Scenario 4 — the run fails and names every offending WP; it does not silently drop the
  bad ones and compute lanes for the rest.
- **A meta.json commit failure on a genuinely dirty working tree** (uncommitted, unrelated
  changes already present before `specify` runs): the fix must distinguish "hard commit
  failure" (now raises) from pre-existing dirt that is not this commit's concern — the
  rollback (`_restore_git_state_after_failed_create`) restores only what `create_mission_core`
  itself mutated, via its captured `original_branch`/`original_commit`/`original_index_tree`
  snapshot, not the operator's pre-existing uncommitted changes.
- **An `authoritative_surface` that is a valid prefix reachable only because fix 3 removes
  the short-circuit**: today, a mission whose manifest map is empty never has its
  `authoritative_surface` values checked at all — valid or not. After the fix, a
  previously-unreachable-but-valid value must pass validation cleanly (User Story 3,
  Acceptance Scenario 4); a previously-unreachable-and-invalid value must now be caught
  (Acceptance Scenario 3). Both directions must be tested, not just the rejection path.
- **A planning-artifact WP with an explicit `owned_files: []`**: remains the existing,
  legitimate escape hatch (User Story 2, Acceptance Scenario 3) — this mission does not
  touch that path. Note, however, that ledger entry SK-24 (see Related Known Defects
  below) documents that this escape hatch is *itself* unreachable today for a different
  reason (the `PLANNING_ARTIFACT` branch in `compute_lanes` requires a manifest, and a
  manifest requires truthy `owned_files`) — this mission does not fix that separate defect
  and must not be read as having done so.
- **Mid-flight missions when this change lands** — see Reflexivity below; treated as an
  edge case of "when does the new raise/reject first fire against pre-existing state."

## Reflexivity — this mission is self-hosting

This spec will itself be finalized by the exact `finalize-tasks` code path that defects 2
and 3 live in, and this mission's own `meta.json` was committed through the exact code
path defect 1 lives in. Two concrete questions follow, and this mission must answer both
rather than leave them implicit:

- **(a) A mission whose `meta.json` commit would now raise where it previously silently
  swallowed the exception — does this change break any currently-passing (if
  silently-broken) workflow?** No. `_commit_feature_file`'s own docstring already commits
  to "raises on hard failures and silently succeeds when there is nothing to commit" — the
  no-op case is unchanged by this fix; only the previously-discarded hard-failure case
  starts surfacing. A workflow that depends on a hard commit failure being silently
  ignored is, by definition, a workflow currently producing a mission with a missing or
  stale `meta.json` — i.e. already broken in the way the upstream issue reports. This
  mission does not change behavior for any mission whose commit already succeeds or
  already has nothing to commit; it only changes behavior for the case that was already
  producing a defective mission.
- **(b) A mission with WPs already authored with `execution_mode: code_change` +
  `owned_files: []` sitting in an existing `tasks.md`/WP files somewhere — what does
  re-running `finalize-tasks` against it now do?** It rejects at that point, loudly,
  naming the offending WP — which is the intended behaviour under FR-002, not a
  regression. Before this fix such a mission would have silently lost lane computation
  entirely (the exact failure mode reported in issue #3673); after this fix it fails
  earlier, with an actionable message, at the same command invocation. No new repair
  command is provided for such a mission (see C-001/FR-005) — the author must correct the
  WP frontmatter by hand (a genuine authoring fix, not a tooling workaround) and re-run
  `finalize-tasks`.
- This mission's own `spec.md` finalization (via `spec-kitty.tasks-finalize` /
  `agent mission finalize-tasks`) is expected to complete cleanly under both the
  pre-fix and post-fix code, because this mission's own WPs are not expected to be
  authored with the `code_change` + explicit-empty-`owned_files` contradiction. If the
  tasks/finalize phase for this very mission hits any of the three defects being fixed,
  that is itself a live, first-hand reproduction and must be recorded in
  `tracer-tooling-friction.md`, not silently worked around.

### Related known defects (ledger cross-reference)

Per the mission's ledger, this section accounts for every entry the readiness probe
flagged as same-subsystem-or-family, without claiming to fix any of them:

- **SK-24** (planning-artifact WP cannot satisfy `INVALID_WP_OWNED_FILES_KITTY_SPECS` and
  `compute_lanes` at once — the `PLANNING_ARTIFACT` escape branch is unreachable for
  exactly the WPs it exists for). Different `execution_mode` case than this issue's
  `code_change` combination; already partially addressed by merged commit `31798b6bd`,
  which stayed fail-closed for `code_change` and did not touch this issue's combo. This
  mission does not fix SK-24 and must not be read as having done so — the escape hatch
  described in the Edge Cases section above remains broken for the reasons SK-24
  documents, independent of this mission's changes.
- **SK-25** (a lane collapse can turn an acyclic WP graph into a cyclic lane graph, and
  `finalize-tasks` reports success while writing it). Same command, same
  silent-partial-success family, but a different failure axis: SK-25's `lanes.json` *is*
  written but is topologically wrong; this issue's defect 2/3 is that `lanes.json` is
  *never written at all*. This mission's fixes to defect 3 (raise instead of returning
  `(None, None)`) do not touch the post-collapse cycle-detection gap SK-25 describes, and
  do not regress it either way — SK-25 remains open and unaddressed.
- **SK-61** (`finalize-tasks` writes all its mutations to disk, then refuses to commit,
  leaving a forked event log and a degenerate `status.json`). A refusal-*after*-mutation
  bug — the opposite ordering problem from this issue's degrade-to-silent-success (this
  issue's defects never mutate `lanes.json` in the first place; SK-61's problem is that
  everything *except* the final commit already landed). This mission's fixes do not
  reorder `finalize-tasks`' commit-vs-mutation sequencing and do not regress or resolve
  SK-61.
- **SK-68** (`finalize-tasks` holds two contradictory dependency sources — `wps.yaml` /
  frontmatter `dependencies` vs `tasks.md` prose — silently prefers one, and emits a lane
  graph that contradicts `tasks.md` while reporting success). Same file, same
  "reports-success-while-state-is-wrong" family, but a distinct specific bug: dependency
  *source* disagreement, not ownership-manifest emptiness. This mission's FR-003/FR-004
  changes do not touch `_resolve_dependencies_and_refs` and do not resolve SK-68.
- **SK-69** (under `single_branch` topology, `agent status emit` demands an implementation
  commit on a lane branch the topology never creates, so a completed WP can never leave
  `planned`). Same subsystem (mission lifecycle / lane-aware state transitions), different
  bug — a post-lane-computation guard mismatch under a specific topology, not a
  lane-computation-time failure. Out of scope for this mission; not addressed, not
  regressed.

A closed upstream GitHub issue does not close a ledger entry — verified-by-behaviour is
the ledger's convention, not issue state. None of the five entries above are treated as
resolved by virtue of issue #3673 being the current mission's subject.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | `meta.json` commit raises on hard failure instead of being suppressed | As a mission author, I want a hard git failure while committing `meta.json` to abort mission creation loudly and roll back, so that I never end up with a scaffolded mission missing the file every later command depends on. | High | Open |
| FR-002 | `execution_mode: code_change` + explicit `owned_files: []` is rejected at bootstrap | As a mission author, I want a self-contradictory WP declaration caught and named at `finalize-tasks` time, so that an authoring mistake fails where it was made instead of degrading lane computation three steps downstream. | High | Open |
| FR-003 | Lane computation raises instead of silently returning `(None, None)` | As a mission orchestrator, I want `_compute_and_write_lanes` to fail loudly when it cannot produce `lanes.json`, so that `finalize-tasks` never reports success while the artifact every WP depends on was never written. | High | Open |
| FR-004 | `authoritative_surface` validation runs unconditionally, not gated on manifest-map emptiness | As a mission orchestrator, I want ownership-manifest validation (including `authoritative_surface` glob-match/overlap/audit-coverage checks) to run regardless of whether the manifest map is empty, so that a placeholder or malformed value cannot escape validation purely by virtue of every WP having been filtered out upstream. | High | Open |
| FR-005 | No new CLI surface; no repair path for already-broken missions | As the spec-kitty maintainer team, I want this mission to add zero new commands or flags (no `migrate rebuild-meta`, no `--reinfer-ownership`, no `--force`/"recovery mode" substitute), and to state explicitly that missions whose `meta.json` is already missing today get no repair path from this change, so that the fix stays within the fail-loud/reject-only scope the operator bound it to and does not require prior-maintainer-agreement review under CONTRIBUTING.md:377. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | New failures are actionable in both output modes | Every new raise/reject introduced by FR-001 through FR-004 must, in human-readable output, name the failing step and the specific offending value (WP ID, file, or field) in prose; and in `--json` output, surface a stable machine-readable field (an error code or equivalent) plus the same identifying detail, so a calling agent can branch on the failure type without parsing prose. | Usability | High | Open |
| NFR-002 | No regression to test-suite runtime budget | The full test suite (~17,000 tests) must not regress in wall-clock runtime beyond the repository's existing CI budget as a result of the new validation/raise paths added under FR-001 through FR-004 — the added checks are bounded, in-memory, and run once per `finalize-tasks`/`specify` invocation, not per-test-iteration overhead. See C-005 for the related baseline-red discipline this mission's test-writing WPs must follow when interpreting any red observed against the full suite. | Performance | Medium | Open |
| NFR-003 | Rollback correctness on the new FR-001 raise path | When FR-001's raise fires, `_restore_git_state_after_failed_create` must leave the checkout in a state indistinguishable (branch, HEAD commit, index tree) from before `create_mission_core` was invoked, verified by a test that snapshots and compares all three before and after a forced failure. | Reliability | High | Open |
| NFR-004 | No silent partial state on the new FR-002 reject path (FR-003/FR-004 gap explicitly documented) | When FR-002 rejects — which fires inside `_apply_ownership_inference` during the bootstrap loop, strictly before `_flush_frontmatter_writes` and before `_run_commit_pipeline` ever run — no `lanes.json`, no mutated WP frontmatter, and no `TasksCompleted` (or equivalent completion) event may be written or committed as a side effect of the run that rejected, consistent with the fail-loud intent and the partial-mutation trail ledger entries SK-24 and SK-61 already document for other `finalize-tasks` failure paths. **This guarantee is scoped to the FR-002 reject path only.** For an FR-003 or FR-004 reject, the current pipeline order in `finalize_tasks` cannot support the same guarantee: `_flush_frontmatter_writes` (`mission_finalize.py:2752`, an actual disk write of WP frontmatter) already runs before `_validate_ownership_manifests` (FR-004's check, line 2766) and before `_run_commit_pipeline` (line 2789, which contains FR-003's `_compute_and_write_lanes` at line 2342); and inside `_run_commit_pipeline`, `_emit_local_canonical_events` (persisting `TasksCompleted`, line 2332) runs before `_compute_and_write_lanes` is even reached (line 2342). Neither write has an existing revert path (the only revert in `finalize_tasks` undoes a `meta.json` `target_branch` override, unrelated). Therefore an FR-003 or FR-004 reject is only guaranteed to leave `lanes.json` absent; it may still leave WP frontmatter already mutated on disk, and — for FR-003 specifically — the `TasksCompleted` event already persisted, from earlier phases of the same rejected run. This is a known, operator-accepted gap, documented the same way C-003 documents the no-repair-path gap, not a defect this mission closes. Reordering `_flush_frontmatter_writes`/`_emit_local_canonical_events` to run only after validation succeeds would close it, but that is a scoped pipeline-reorder design change outside D1's fail-loud/reject-only scope (D1 is about failure paths raising, not about re-sequencing write-then-validate ordering), and would need its own operator sign-off given C-002's rebase-risk note about PR #3666 touching this same file. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No new CLI surface | CONTRIBUTING.md:377 requires prior maintainer agreement before a PR introduces new commands or arguments ("Pull requests with large changes that did not have a prior conversation and agreement will be closed"). The operator's binding decision D1 (see Clarifications) already resolved scope to fail-loud/reject-only with no new command or flag; no work package under this mission may introduce one, including as a disguised escape hatch (`--force`, a "recovery mode", or similar). | Business | High | Open |
| C-002 | PR #3666 sequencing risk | Open PR #3666 ("fix: preserve planning branch for legacy PR-bound missions") edits `src/specify_cli/cli/commands/agent/mission_finalize.py` directly — different functions than this mission touches (`_apply_ownership_inference`, `_validate_ownership_manifests`, `_compute_and_write_lanes` vs #3666's planning-branch-preservation logic), but the same 2800+ line file, and both PRs reason about `meta.json`/commit robustness in that file. Not blocking, but a real rebase-conflict risk this mission's plan should note and its implementation should watch for. | Technical | Medium | Open |
| C-003 | No repair path for already-broken missions (operator-accepted gap) | Missions whose `meta.json` is already missing today (created before this fix, or created by a still-unpatched version of `specify`) get **no repair path** from this mission — explicitly, not `spec-kitty migrate rebuild-meta` or any equivalent. This is a known, operator-accepted gap under D1, deferred to a later, separately-agreed mission. | Business | Medium | Open |
| C-004 | Reflexivity — this spec's own finalize-tasks run | This mission's own tasks phase will be finalized by the exact code paths FR-002/FR-003/FR-004 change. Any WP in this mission's own `tasks.md` must not be authored with `execution_mode: code_change` + explicit `owned_files: []`, or it will hit the very rejection this mission introduces — which would be a correct rejection, not a bug, but the mission's own tasks-authoring step should get it right the first time rather than relying on the new gate to catch it. | Technical | Low | Open |
| C-005 | `main` carries known pre-existing red tests — baseline before attributing red to this mission | This mission's test suite (covering FR-001 through FR-004) is added against a `main` known to carry pre-existing red tests (documented in AGENTS.md's "Test-run baseline-red gotcha" and in SPEC-KITTY-LEDGER.md's P0 entries). Before attributing any red observed while implementing/testing FR-001 through FR-004 to this mission, the implementing WP must confirm the same test is red on-branch AND green on the merge-base / `upstream/main` before folding it in as this mission's responsibility — a red that is already red on the merge-base is out of scope and must not be "fixed" as part of this mission, and a red that is green on the merge-base but red on-branch is a real regression this mission must not ship. | Technical | High | Open |

### Key Entities

- **`meta.json`**: per-mission metadata file at `kitty-specs/<slug>/meta.json`, written by
  `write_meta` and committed via `_commit_feature_file`. Carries `topology`,
  `mission_type`, `target_branch`, and (for `documentation` missions) `documentation_state`.
  Every later command (`next`, `tasks`, `status lifecycle`, `doctor topology`) depends on
  its presence; FR-001 governs the commit step that persists it.
- **`lanes.json`**: per-mission execution-lane manifest, written by
  `_compute_and_write_lanes` / `compute_lanes` + `write_lanes_json`. Required before any
  WP can start implementation ("`lanes.json` is required for `<slug>`. Run the
  task-finalization step to compute execution lanes."). FR-003 governs the failure
  behaviour when it cannot be produced.
- **`OwnershipManifest`**: per-WP structure built by `build_wp_manifests`
  (`ownership/validation.py:335`) from WP frontmatter, carrying `execution_mode`,
  `owned_files`, and `authoritative_surface`. A WP is only included when
  `fm.execution_mode and fm.owned_files` are both truthy (line 356) — the condition FR-002
  changes the upstream authoring rules around.
- **WP frontmatter fields — `execution_mode`, `owned_files`, `authoritative_surface`**:
  `execution_mode` distinguishes `code_change` from `planning_artifact` (and others);
  `owned_files` declares the WP's write scope (a list, an explicit empty list, or absent);
  `authoritative_surface` declares the WP's canonical-source prefix, validated (when
  validation runs) via glob-match/overlap/audit-coverage checks in
  `_validate_ownership_manifests`. FR-002 changes when the `code_change` +
  explicit-empty-`owned_files` combination is accepted; FR-004 changes when
  `authoritative_surface` is checked at all.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Re-running the exact repro from issue #3673 (a `meta.json` commit hitting a
  hard git failure during `specify`) now fails at that step with a named error and a
  restored working tree, instead of `specify` reporting success with `meta.json` never
  persisted. (FR-001)
- **SC-002**: Re-running the exact repro from issue #3673 (a `code_change` WP with an
  explicit `owned_files: []`) now fails at `finalize-tasks` time with a named error
  identifying the offending WP, before any `lanes.json` write is attempted — instead of
  `finalize-tasks` reporting success while lane computation silently produced nothing.
  (FR-002)
- **SC-003**: A fixture that trips `_compute_and_write_lanes`'s compound guard
  (`not (wp_manifests and wp_dependencies)`, `mission_finalize.py:1834`) — whether via an
  empty ownership-manifest map (from FR-002's rejection, or any other cause) or via a
  non-empty manifest map paired with an empty `wp_dependencies` map — now causes
  `_compute_and_write_lanes` to raise a named error in both cases, verified by tests
  asserting no `lanes.json` is written and `finalize-tasks`' exit code/`--json` payload
  reports failure, not success. (FR-003)
- **SC-004**: A fixture with a malformed `authoritative_surface` value (bare `src/`, empty
  string, or a spurious trailing slash) on a mission whose manifest map is empty is now
  rejected by `_validate_ownership_manifests`, verified by a test that would have passed
  silently (validation skipped) before this fix and fails loudly with a specific,
  identifiable error after it. (FR-004)
- **SC-005**: A repository-wide search of this mission's own diff and PR description
  confirms zero new CLI commands, subcommands, or flags were introduced anywhere in
  `src/specify_cli/` as part of this mission — verified by diffing the CLI command
  registration surface (`typer` app definitions / command decorators) before and after,
  confirming the set is unchanged. (FR-005 / C-001)
