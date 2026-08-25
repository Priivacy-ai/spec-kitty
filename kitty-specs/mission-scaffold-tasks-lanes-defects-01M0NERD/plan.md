# Implementation Plan: Mission scaffold → tasks → lanes: three compounding defects

**Branch**: `fix/mission-scaffold-lanes-defects-3673` | **Date**: 2026-08-22 | **Spec**: [`spec.md`](./spec.md)
**Input**: `kitty-specs/mission-scaffold-tasks-lanes-defects-01M0NERD/spec.md` (434 lines, FR-001..FR-005, NFR-001..NFR-004, C-001..C-005)

## Summary

Three failure points on the `specify → finalize-tasks → lane computation` chain currently
degrade to silent success instead of failing loudly: (1) `mission_creation.py` swallows a
hard git failure on the `meta.json` commit; (2) `ownership/validation.py` silently drops a
self-contradictory `execution_mode: code_change` + explicit `owned_files: []` WP from the
ownership manifest instead of rejecting it; (3) `mission_finalize.py`'s
`_compute_and_write_lanes` returns `(None, None)` instead of raising when its manifest/
dependency guard trips, and `_validate_ownership_manifests` short-circuits entirely when the
manifest map is empty, letting a malformed `authoritative_surface` escape validation. Per
binding operator decision D1, the fix is strictly fail-loud/reject-only: every failure mode
above starts raising/rejecting with a named, actionable error, in both prose and `--json`
output. No new CLI command, subcommand, or flag is introduced anywhere. No repair path is
added for missions already broken today (C-003, operator-accepted gap). The existing rollback
machinery (`_restore_git_state_after_failed_create`) already handles FR-001's cleanup; no new
rollback machinery is built.

## Technical Context

**Language/Version**: Python 3.11+ (per charter, no change)
**Primary Dependencies**: typer (CLI), rich (console output), ruamel.yaml (frontmatter) — no new dependency introduced
**Storage**: N/A — filesystem-based mission state (`meta.json`, WP frontmatter, `lanes.json`), no schema change
**Testing**: pytest, targeted packages per charter's scoped-test-surface rule (not the full ~17,000-test suite for per-WP validation)
**Target Platform**: CLI, cross-platform (Linux/macOS/Windows), no platform-specific code touched
**Project Type**: Single project — internal CLI/service-layer defect fix, no new module, no new package
**Performance Goals**: No change; NFR-002 requires the new checks add no measurable regression to the ~17,000-test CI budget (they are bounded, in-memory, run once per invocation)
**Constraints**: C-001 (no new CLI surface, binding), NFR-004 (narrowed no-silent-state guarantee, FR-002 only), C-005 (baseline-red discipline before attributing any red to this mission)
**Scale/Scope**: 2 source files receive an actual diff (`mission_creation.py`, `mission_finalize.py`), 6 changed call sites total, no new files, no new public API surface. (`ownership/validation.py`'s `build_wp_manifests` is examined in §1's seam map and confirmed **unchanged** by this mission — its acceptance predicate is left as-is; it is not a third diffed file. Corrected per PLAN-ARCH-003, further corrected per PLAN-FRESH-002 — `_run_bootstrap_loop` was omitted from the prior "5" count even though it receives a real body change; see §1 for the full count.)

## Charter / Constitution Check

*GATE: checked against `.kittify/charter/charter.md` before Phase 0 research; re-checked here after this plan's design.*

- **Governing principles**: architectural alignment holds — this stays inside the existing
  CLI/service layer that already implements these checks; no kernel seam is touched (see
  §1 below). Single canonical authority holds — no second validation path is added; the
  existing `build_wp_manifests`/`_apply_ownership_inference`/`_compute_and_write_lanes`/
  `_validate_ownership_manifests` functions are tightened in place, not duplicated.
- **ATDD-first / Standing Order #4/#9**: satisfied by design — see §11 (red-first test
  strategy), one revert-sensitive test per FR.
- **Campsite cleaning / Standing Order #2**: checked against the actual touched functions
  (§10) — no campsite-clean WP is warranted; none of the touched functions are near the
  complexity ceiling.
- **Git & workflow discipline / Standing Order #7**: this mission stays on
  `fix/mission-scaffold-lanes-defects-3673`, targets `main` via PR, operator merges. No
  violation.
- **No charter violation requires a Complexity Tracking justification.** The Complexity
  Tracking table below is intentionally empty.
- **Charter/AGENTS.md drift** (eight vs. nine standing practices) is pre-flagged in spec.md's
  Clarifications section and is not re-litigated here, per the mission briefing.

## Complexity Tracking

*No entries — the charter check above found no violations to justify.*

---

## 1. Seam / Module Map

**Corrected per PLAN-ARCH-003, further corrected per PLAN-FRESH-002 (confirmed adversarial
findings — the seam map below is the source of truth, this line now matches it exactly):**
exactly **6 changed call sites across 2 files** change (`mission_creation.py`'s 2 call sites
inside `_create_mission_core_impl`, plus `_apply_ownership_inference`, `_run_bootstrap_loop`,
`_validate_ownership_manifests`, and `_compute_and_write_lanes` in `mission_finalize.py`).
**PLAN-FRESH-002 found the prior "5" count silently omitted `_run_bootstrap_loop` even though
this row's own design below requires a real body change to it (new
`state.ownership_contradictions` accumulation plus a new post-loop aggregated raise, and a new
field on the `_BootstrapState` dataclass at `mission_finalize.py:1188`) — it is now counted as
its own changed call site, distinct from `_apply_ownership_inference`, and given its own row
below.** `ownership/validation.py`'s `build_wp_manifests` is examined below but is explicitly
**unchanged** — it does not receive a diff and is not counted among the 6. All line numbers
verified first-hand
against this checkout's HEAD on `fix/mission-scaffold-lanes-defects-3673` on 2026-08-22
(not copied from the spec without re-checking):

| File | Function | Verified line(s) | Change |
|---|---|---|---|
| `src/specify_cli/core/mission_creation.py` | primary mission-type `meta.json` commit | `write_meta(feature_dir, meta)` at **766**; `with contextlib.suppress(Exception):` at **767**; `_commit_feature_file(...)` call at **768** | FR-001: remove the `contextlib.suppress(Exception)` wrapper so a hard git failure raises. |
| `src/specify_cli/core/mission_creation.py` | `documentation` mission-type second call site | `with contextlib.suppress(Exception):` at **792**; `_commit_feature_file(...)` at **793** | FR-001 (Acceptance Scenario 4): identical fix, same pattern, second call site — the fix must not be partial to the primary branch. |
| `src/specify_cli/ownership/validation.py` | `build_wp_manifests` | `def build_wp_manifests` at **335**; acceptance predicate `if fm.execution_mode and fm.owned_files:` at **356** (verified exact — matches spec's citation) | FR-002 is anchored elsewhere (see below) — this function's *behavior* is not changed for the `code_change` + explicit-`[]` case because that case is rejected upstream before it ever reaches this filter. See resolution below. |
| `src/specify_cli/cli/commands/agent/mission_finalize.py` | `_apply_ownership_inference` | `def _apply_ownership_inference` at **1264**; `owned_files_explicitly_empty = _owned_files_yaml_is_explicit_empty_list(wp_raw_content)` at **1275**; `need_owned_files = not wp_meta.owned_files and not owned_files_explicitly_empty` at **1277**; function body spans **1264–1295** (32 lines, verified — matches §10) | **FR-002's reject condition is *detected* here but not raised here** (collect-all-offenders-then-raise-once, option (a) of PLAN-ARCH-001, adopted explicitly; see resolution below, §5, and the `_run_bootstrap_loop` row immediately below). After computing `owned_files_explicitly_empty`, `_apply_ownership_inference` gains a check: if `wp_meta.execution_mode == "code_change"` (or the field is about to be inferred/confirmed as `code_change`) AND `owned_files_explicitly_empty` is `True`, it does **not** raise — instead its return type changes, pinned down explicitly here (per PLAN-FRESH2-003, verified adversarial finding — do not leave the shape ambiguous): from the CURRENT `tuple[bool, list[str]]` (verified: `changed, warnings = seam._apply_ownership_inference(...)` at `tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py:496`) to **`tuple[bool, list[str], str | None]`** — the third element is the contradiction message (naming the WP ID) when the `code_change` + explicit-empty-`owned_files` condition is detected, `None` otherwise. `infer_warnings` (the existing second element) is unchanged in meaning and does **not** carry contradiction data — the two are kept distinct so a hard-error contradiction is never conflated with an informational inference warning. The third element is returned to its caller, `_run_bootstrap_loop`, for that caller to accumulate. A direct call to `_apply_ownership_inference` alone, bypassing `_run_bootstrap_loop`, never raises under this design regardless of `execution_mode` — see §11's FR-002 test rows for the resulting test split. |
| `src/specify_cli/cli/commands/agent/mission_finalize.py` | `_run_bootstrap_loop` | `def _run_bootstrap_loop` at **1298**; its per-WP `for wp_file in wp_files:` loop at **1324**, calling `_apply_ownership_inference` at **1365**; `return state` at **1394**; function body spans **1298–1394** (97 lines, verified — the next `def` starts at **1397**) | **Added per PLAN-FRESH-002 as its own row — this is where FR-002's reject is actually *resolved*, not merely a signature/call-site detail of the row above.** `_run_bootstrap_loop`'s per-WP `for` loop extracts the third tuple element (`str | None`, per the pinned `tuple[bool, list[str], str | None]` return shape in the row above) from `_apply_ownership_inference`'s return and, when it is not `None`, appends it to a new `state.ownership_contradictions: list[str]` field (added to the `_BootstrapState` dataclass at `mission_finalize.py:1188`) and continues to the next WP file rather than aborting. After the loop finishes iterating all WP files — still inside `_run_bootstrap_loop`, before its `return state` at line 1394 — if `state.ownership_contradictions` is non-empty, raise **one** aggregated error naming every offending WP ID. This is a real diff to `_run_bootstrap_loop`'s own body (new accumulation logic, a new post-loop raise, and the new `_BootstrapState` field), counted as its own changed call site per the corrected count above — not folded silently into the row above. |
| `src/specify_cli/cli/commands/agent/mission_finalize.py` | `_validate_ownership_manifests` | `def _validate_ownership_manifests` at **1475**; guard `if not wp_manifests:` / `return` at **1484-1485** (verified exact, two lines — matches spec's citation) | FR-004: remove/narrow this short-circuit so `authoritative_surface` glob-match/overlap/audit-coverage checks run unconditionally, even when `wp_manifests` is empty. |
| `src/specify_cli/cli/commands/agent/mission_finalize.py` | `_compute_and_write_lanes` | `def _compute_and_write_lanes` at **1820**; compound guard `if not (wp_manifests and wp_dependencies):` / `return None, None` at **1834-1835** (verified exact, two lines — matches spec's citation) | FR-003: replace `return None, None` with a raise naming which half of the compound guard tripped (empty `wp_manifests` vs. empty `wp_dependencies` with non-empty `wp_manifests`) — both halves must be covered per Acceptance Scenario 5/SC-003. **Consequence flagged per PLAN-ARCH-002 (confirmed adversarial finding) — see the note immediately below the table.** |

**Resolving the FR-002 ambiguity between `validation.py` and `mission_finalize.py`
(explicit, per plan-authoring instruction — do not leave this ambiguous):** the reject
belongs in the `_apply_ownership_inference` / `_run_bootstrap_loop` pair
(`mission_finalize.py:1264` / `:1298`), not in `build_wp_manifests` (`validation.py:335`).
Rationale: both functions run during the bootstrap loop, *before* any `OwnershipManifest` is
built and *before* `_flush_frontmatter_writes` or `_run_commit_pipeline` ever execute (this is
also what makes NFR-004's "no silent partial state" guarantee achievable for FR-002
specifically, unchanged by the collect-all-then-raise-once aggregation below — see §5).
`build_wp_manifests` runs later, is the pure/filesystem-free seam explicitly documented as
"WPs that do not declare ownership... are skipped, mirroring finalize-tasks" — it is a
consumer of already-validated frontmatter, not the authoring-time gate. Placing the reject in
`build_wp_manifests` would (a) fire after `_apply_ownership_inference` has already run and
after some frontmatter fields may already be queued for write, defeating NFR-004's guarantee
entirely, and (b) require `build_wp_manifests` to know about `execution_mode` semantics it
currently treats generically. `build_wp_manifests`'s acceptance predicate at line 356 is
**left unchanged** by this mission — it continues to skip WPs with falsy `execution_mode` or
`owned_files`, which after FR-002's fix simply never sees the `code_change` +
explicit-`[]` combination reach it (that WP already failed the run upstream).

**PLAN-ARCH-001 (confirmed adversarial finding) — batch-vs-first-offense decision, made
explicit here rather than left ambiguous:** the design above intentionally adopts **option
(a), collect-all-offenders-then-raise-once**, not raise-on-first-offense. Rationale: placing
the raise immediately inside `_apply_ownership_inference`, invoked synchronously per-WP from
`_run_bootstrap_loop`'s `for` loop, would propagate the exception out of the loop on the
*first* offending WP and never reach subsequent WP files in the same `finalize-tasks`
invocation — directly undercutting this mission's own motivating scenario (spec.md's User
Story 2 "8 of 8 WPs authored this way", Acceptance Scenario 4's "offending WP(s)" plural
wording), which requires every offender to be named in one run rather than forcing N
fix-and-rerun round trips. Instead, `_apply_ownership_inference` returns the contradiction as
data rather than raising, `_run_bootstrap_loop` accumulates every offending WP's descriptor
across the full loop, and the aggregated raise fires once, after the last WP file has been
processed, still inside `_run_bootstrap_loop` and therefore still strictly before
`_flush_frontmatter_writes` (`mission_finalize.py:2752`) and `_run_commit_pipeline`
(`mission_finalize.py:2789`) are ever reached. **NFR-004 preserved unchanged, verified:**
`_run_bootstrap_loop`'s own docstring already states disk writes are deferred to
`state.pending_writes`/`state.would_modify` and "only flushed when `not validate_only`" via
`_flush_frontmatter_writes` — no code path between the per-WP loop and that flush call
performs any write regardless of whether the raise fires after WP #1 or after WP #N, so
moving the raise to end-of-loop changes *which* WPs get named, not *when* the first possible
disk write could occur. §11 adds an explicit test case for this (2+ WPs sharing the
contradiction, asserting all are named in one run) — see the FR-002 "mixed valid/invalid WPs"
row.

**PLAN-ARCH-002 (confirmed adversarial finding) — FR-003's fix leaves two downstream
`is None`/`is not None` guards permanently dead, decision made explicit here rather than left
as an undiscovered surprise for the implementer.** Once FR-003 replaces the line-1834
`return None, None` with a raise, `_compute_and_write_lanes`'s declared return type
(`tuple[Path | None, LanesManifest | None]`) can never again actually produce `(None, None)`
— every remaining path either raises or returns two real values. Its single call site,
`_run_commit_pipeline` (`mission_finalize.py:2342`), threads that return into two downstream
consumers whose `None`-handling branches become unreachable for this call path:
`_scaffold_acceptance_matrix_if_lane_based`'s `if lanes_manifest is None or validate_only:
return` guard (`mission_finalize.py:1951`) and `_collect_finalize_artifacts`'s `if lanes_path
is not None: candidates.append(lanes_path)` guard (`mission_finalize.py:270`). **Adopted
resolution: option (a) — leave both downstream guards in place as harmless-but-now-unreachable
defensive code, each with a short inline comment noting why (e.g. "unreachable for the
`_compute_and_write_lanes` call path since FR-003; kept as defensive code, not dead-code
cleanup").** Rationale for (a) over (b) (narrowing the return annotation to
`tuple[Path, LanesManifest]` and simplifying both downstream guards): (b) would widen this
mission's diff into two additional functions/call sites beyond the 6 changed call sites /
2 files with an actual diff established in §1's corrected count (PLAN-ARCH-003, PLAN-FRESH-002) and §12's
phasing figure — re-introducing the same "how many call sites does this mission actually
touch" ambiguity this fix round just resolved — for a purely defensive-code cleanup that
carries no functional or NFR-004 benefit. This stays consistent with §10's "no
campsite-clean WP warranted, smallest-viable-diff first" position: (a) is the smallest-viable
response, (b) is optional future cleanup outside this mission's fail-loud/reject-only scope
(D1). The implementing WP for FR-003 must add both inline comments as part of its diff — this
is not deferred to a future mission, only the type-annotation narrowing is.

**No CLI command reaches past a service into kernel internals here.** All five touched
functions (`_create_mission_core_impl`, `_apply_ownership_inference`, `_run_bootstrap_loop`,
`_validate_ownership_manifests`, `_compute_and_write_lanes` — corrected per PLAN-FRESH-002 to
include `_run_bootstrap_loop`) live in the existing CLI/service layer (`src/specify_cli/core/`,
`src/specify_cli/ownership/`, `src/specify_cli/cli/commands/agent/`) that already implements
these checks. Nothing under `src/kernel/` is touched, added, or referenced by this mission's
diff — confirmed by the seam map above being the complete list of touched functions. If any
WP's implementation drifts into `src/kernel/**`, that is itself a scope-drift finding, not a
legitimate extension of this plan (this is also why the kernel coverage floor does not gate
this PR — see §8).

## 2. Generated Artifacts

This mission touches **no generated artifact**. Specifically, none of: a doctrine schema
(`scripts/generate_schemas.py --check` output), a Contextive glossary file
(`.kittify/glossaries/**`), an agent command copy (`.claude/commands/`, `.agents/skills/`,
etc. — those are generated from `packs/built-in/missions/mission-steps/` via
`spec-kitty upgrade`, which this mission does not touch), or any `packs/built-in/` template.
All six changed call sites in §1 are pure function-body edits to already-existing, hand-written
source files (corrected per PLAN-FRESH-002 to include `_run_bootstrap_loop`, and per
PLAN-FRESH2-002 to match §1/§12's "six changed call sites" vocabulary — this line previously
still read "five" even though the parenthetical claimed the PLAN-FRESH-002 correction was
already reflected). No WP under this plan should regenerate or hand-edit any generated surface; if
a WP's diff touches one, that is scope drift, not an expected side effect of this fix.

## 3. Contracts

FR-001 through FR-004 change **failure-mode behavior only** (raise instead of
swallow/short-circuit/return-`None`) — they touch:

- **No doctrine schema** — no `.kittify/doctrine/**` change, no `scripts/generate_schemas.py` re-run needed.
- **No mission step contract or action index** — `src/doctrine/missions/**` is untouched;
  the `finalize-tasks` step's documented I/O contract does not change shape (it already could
  fail with a non-zero exit and a JSON error payload; this mission changes *which* conditions
  trigger that, not the payload's contract shape).
- **No orchestrator-api surface** — `src/specify_cli/orchestrator_api/**` is untouched.
- **No vendored `spec-kitty-events` package** — per the charter's Shared Package Boundary
  section, `spec-kitty-events` is consumed only via `spec_kitty_events.*` public imports;
  this mission does not touch event envelope/payload schemas. (The `TasksCompleted` event
  referenced in NFR-004/§5 below is *emitted*, not *schema-changed*, by this mission — its
  emission timing relative to FR-003/FR-004 is exactly the residual gap §5 documents, not a
  contract change.)
- **Cross-check against the spec**: spec.md's Key Entities section (lines 379-403) describes
  `meta.json`, `lanes.json`, `OwnershipManifest`, and the three WP frontmatter fields purely
  in terms of when they are written/validated — none of their *shapes* change. This plan's
  reading is consistent with that: no field is added, removed, or retyped anywhere in this
  mission.
- **Return-contract narrowing, examined explicitly (PLAN-ARCH-002, confirmed adversarial
  finding — do not leave unexamined):** FR-003's raise makes `_compute_and_write_lanes`'s
  declared `tuple[Path | None, LanesManifest | None]` return type permanently unable to
  actually produce `(None, None)` again, which makes two downstream `None`-handling branches
  (`_scaffold_acceptance_matrix_if_lane_based:1951`, `_collect_finalize_artifacts:270`)
  unreachable for this call path. This mission adopts **option (a)** — the type annotation
  itself is **not** narrowed, both downstream guards are left in place as harmless-but-dead
  defensive code with an inline comment (see §1 for the full rationale) — so, strictly,
  **no return-type signature changes** as part of this mission; the "no field is
  added/removed/retyped" claim above holds for the FR-003 change specifically because option
  (a), not (b), was chosen. If a future mission later adopts option (b), that would be a
  genuine contract narrowing requiring its own Contracts-section treatment — out of scope
  here.

## 4. No New CLI Surface (binding, D1 / FR-005 / C-001)

**Binding constraint every WP inherits, stated once here so no WP re-derives it:** no new
command, subcommand, flag, or hidden escape hatch anywhere in `src/specify_cli/` — explicitly
including no `spec-kitty migrate rebuild-meta`, no `finalize-tasks --reinfer-ownership`, no
`--force`/"recovery mode" substitute, disguised or otherwise (C-001). This is not negotiable
per-WP judgment; D1 is an operator decision.

**Verification mechanism for SC-005 — corrected per adversarial review (PLAN-GOV-001):
the recursive `registered_commands` walk is the PRIMARY mechanism; the `git diff` grep
below is a known-incomplete fast first pass only, never sufficient on its own.**

The originally-proposed grep (`grep -E '^\+.*(@app\.command|@.*\.command\(\))'`) is
**broken against this checkout**: its second alternative (`@.*\.command\(\)`) only matches
a decorator with **literal empty parentheses**. Every real sub-app command registration in
this codebase passes a name/keyword argument — e.g. `@decision_app.command("open")`
(`src/specify_cli/cli/commands/decision.py:213`), `@asset_app.command("list")`
(`src/specify_cli/cli/commands/_doctrine_asset.py:125`), `@plugin_app.command("build")`
(`src/specify_cli/cli/commands/plugin.py:30`) — so none match either alternative unless the
sub-app variable is literally named `app`. A WP that added, say,
`@decision_app.command("rebuild-meta")` would produce a **false-clean** SC-005 result for a
binding C-001 violation.

**Primary mechanism (run this, not the grep, to actually gate SC-005):** promote the
recursive `registered_commands`/`registered_groups` walk already used by
`tests/architectural/test_docs_cli_reference_parity.py` to the primary verification method.
That test's `_build_live_app()` helper constructs the live `typer.Typer` app via
`specify_cli.app` + `register_commands(app)`, then `scripts.docs._typer_walker.walk(app)`
recursively visits every registered command and sub-app group — including named sub-apps
like `decision_app`/`asset_app`/`plugin_app` — and returns the complete flat set of command
paths, independent of decorator argument shape. Diff that set's cardinality (or its full
path list) between the merge-base checkout and the mission branch: any new path is a binding
C-001 violation. Run this as the WP-level SC-005 gate; a WP may either invoke `walk()`
directly in a small script/test or add a temporary assertion comparing
`len(walk(app))`/the path set before and after.

**Secondary, known-incomplete fast pass (git diff grep, kept only as a cheap first signal,
never the sole verification):**

```bash
git diff <merge-base>...HEAD -- src/specify_cli/ \
  | grep -E '^\+.*\.(command|add_typer)\('
# A broadened pattern (any argument list, plus new sub-app mounts via add_typer) —
# still heuristic and NOT authoritative. Any hit warrants a look; no hit is NOT proof
# of C-001 compliance on its own — only the registered_commands walk above is.
```

This grep is retained only because it is always available without running pytest and can
catch an obvious case fast; it must never be cited as the primary or sufficient SC-005
verification mechanism.

## 5. Pipeline-Ordering Constraint

**Adopted position for this plan (per binding orchestrator instruction — not re-opened
here): (a).** This plan ships the guarantee NFR-004 states, exactly as narrowed, and does not
attempt to close the residual gap by reordering the pipeline.

- **FR-002's reject** is detected per-WP inside `_apply_ownership_inference` but, per
  PLAN-ARCH-001's resolution in §1 (collect-all-offenders-then-raise-once, option (a)),
  aggregated across every WP in `_run_bootstrap_loop`'s `for` loop and raised **once**, after
  the loop finishes, still strictly before `_flush_frontmatter_writes` (`mission_finalize.py:2752`)
  and before `_run_commit_pipeline` (`mission_finalize.py:2789`) ever run. So an FR-002
  reject — whether it names one offending WP or several — is guaranteed to leave **no**
  mutated WP frontmatter, **no** `lanes.json`, and **no** `TasksCompleted` (or equivalent)
  event written or committed — the full guarantee NFR-004 promises for this path, unchanged
  by batching the report across offenders (verified in §1: disk writes are deferred to
  `_flush_frontmatter_writes` regardless of when inside the loop the raise fires).
- **FR-003/FR-004 rejects cannot make the same promise, under the current pipeline order,
  and this plan does not change that order.** Verified against this checkout:
  `_flush_frontmatter_writes` is called at `mission_finalize.py:2752`, **before**
  `_validate_ownership_manifests` (FR-004's check) at `mission_finalize.py:2766`, and before
  `_run_commit_pipeline` at `mission_finalize.py:2789` (which contains `_compute_and_write_lanes`,
  FR-003's raise site, called internally at `mission_finalize.py:2342`). Inside
  `_run_commit_pipeline`, `_emit_local_canonical_events` (persisting `TasksCompleted`,
  `mission_finalize.py:2332`) runs **before** `_compute_and_write_lanes` is reached
  (`:2342`). So: an FR-003 or FR-004 reject is only guaranteed to leave `lanes.json` absent
  (the raise fires before `write_lanes_json` is ever called) — it may still leave WP
  frontmatter already mutated on disk from the earlier `_flush_frontmatter_writes` call, and,
  for FR-003 specifically, may leave `TasksCompleted` already persisted from
  `_emit_local_canonical_events`, which ran earlier in the same `_run_commit_pipeline` call.
- **This residual gap is stated plainly, not silently absorbed.** It carries the same status
  as C-003's no-repair-path gap: a known, operator-accepted limitation of this mission's
  scope, not a defect this mission closes. It is the same shape SK-24 and SK-61 already
  document for other `finalize-tasks` failure paths (partial mutation surviving a failed run)
  — this mission does not fix that shared pattern; it only ensures `lanes.json` itself is
  never the artifact silently missing while `finalize-tasks` reports success (which was the
  original defect).
- **No WP under this mission may reorder `_flush_frontmatter_writes` / `_emit_local_canonical_events`
  relative to the FR-003/FR-004 checks.** That reorder is explicitly out of scope — it is "a
  scoped pipeline-reorder design change outside D1's fail-loud/reject-only scope" per
  NFR-004's own text, and would need separate operator sign-off given §7's PR #3666
  rebase-risk note (both PRs already reason about commit/mutation ordering in this same
  function).
- **Test coverage for the gap itself**: Acceptance Scenario 6 of User Story 3 (spec.md line
  226-231) requires a test asserting `lanes.json` is confirmed absent after an FR-003 reject,
  while explicitly NOT asserting frontmatter/event-log absence (that would be asserting a
  guarantee this mission does not provide). §11 below assigns this test.

## 6. Reflexivity / Self-Hosting Sequencing

This mission is self-hosting: its own `meta.json` was already committed through the pre-fix
FR-001 swallow-path (confirmed by tracer-tooling-friction.md F2 — the branch-first scaffold
succeeded and auto-committed `meta.json` cleanly), and this mission's own `tasks.md`/WP files
will be finalized by the exact FR-002/FR-003/FR-004 code paths this plan changes.

- **(a) FR-001 does not retroactively endanger this mission's own `meta.json`.** The commit
  already succeeded (no hard failure occurred), so this mission's own `meta.json` is not
  affected by making the swallow-path raise going forward — the no-op case (nothing to
  commit) remains silent by design (Acceptance Scenario 3), and the hard-failure case that
  now raises never fired for this mission's own scaffold.
- **(b) C-004 tasks-authoring discipline — flagged forward, not a plan-phase code change.**
  No WP in this mission's own `tasks.md` may be authored with `execution_mode: code_change`
  and an explicit `owned_files: []` — doing so would trip the very FR-002 reject this mission
  introduces (a correct rejection, not a bug, but this plan flags it forward so the
  tasks-authoring agent gets it right the first time rather than relying on the new gate to
  catch its own authoring mistake). This is a **tasks-phase authoring discipline**, not
  something this plan or any WP implements in code.
- **What happens to other, unrelated missions mid-flight when this lands**: per spec.md's
  own answer, a mission with a pre-existing `code_change` + `owned_files: []` WP sitting in
  an already-authored `tasks.md` will **reject loudly at its next `finalize-tasks` re-run**
  instead of silently losing lane computation. This is the intended fix, not a regression —
  before this fix such a mission would have silently lost lane computation entirely (the
  exact failure mode issue #3673 reports); after this fix it fails earlier, with an
  actionable message, at the same command invocation. **No migration step is needed**,
  because no state format changes — only the failure-mode behavior of existing checks
  changes. The author corrects the WP frontmatter by hand (a genuine authoring fix) and
  re-runs `finalize-tasks`; no new tooling is provided or needed for this.
- If this very mission's own tasks/finalize phase hits any of the three defects being fixed
  (pre-fix, since implementation hasn't landed yet when tasks are authored), that is a live,
  first-hand reproduction and belongs in `tracer-tooling-friction.md`, not a silent
  workaround — consistent with F1/F2/F3 already recorded there.

## 7. Sequencing Risk — PR #3666

**Verified first-hand against the live PR, 2026-08-22** (`gh pr view 3666`, `gh pr diff 3666`)
— this sharpens spec.md's C-002 beyond "same file, different functions":

- **PR #3666** ("fix: preserve planning branch for legacy PR-bound missions") is **OPEN** and
  touches `src/specify_cli/cli/commands/agent/mission_finalize.py` (88 additions / 12
  deletions) plus `tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py` (25
  additions) — **the same test file** this plan's §11 test strategy extends for FR-002.
- **Functions #3666 touches**: `_branch_strategy_text`, `_apply_bootstrap_fields`,
  `_run_bootstrap_loop` (**signature and one body line, not signature-only — corrected per
  PLAN-FRESH2-001**: adds a `merge_target_branch: str | None = None` parameter to the
  signature, and, inside the loop body, inserts a new `merge_target_branch=merge_target_branch,`
  keyword argument to the existing `_apply_bootstrap_fields(...)` call — three lines above the
  `_apply_ownership_inference(...)` call site this mission's own FR-002 change must instrument.
  Verified directly against `gh pr diff 3666`, hunk `@@ -1361,6 +1428,7 @@` in
  `mission_finalize.py`.),
  plus new helpers `_resolve_target_branch`/`_resolve_merge_target_branch`/
  `_persist_recovered_pr_bound_contract`, and edits inside the body of `finalize_tasks`
  itself. **This plan's WPs touch**: `_apply_ownership_inference`, `_run_bootstrap_loop`
  (body — new `state.ownership_contradictions` accumulation plus a new post-loop aggregated
  raise, per §1's FR-002 resolution), `_validate_ownership_manifests`,
  `_compute_and_write_lanes`. **Corrected per PLAN-FRESH-002: this is NOT a fully disjoint
  function set as previously stated — `_run_bootstrap_loop` is touched by both PRs, #3666's
  **signature-and-body** change and this mission's body-only change. Same function, adjacent
  statements in the same loop iteration (not merely "different regions" of it): a real rebase
  chokepoint on the function itself, sharper than the "close proximity in the same body region"
  framing below, not the clean disjoint split the prior text claimed — sharpened further per
  PLAN-FRESH2-001, which pinned down exactly which body line #3666 touches and how close it
  sits to this mission's own instrumentation point.**
- **Sharper finding than C-002's line-based estimate**: #3666's diff inserts a new call to
  `_persist_recovered_pr_bound_contract(...)` inside `finalize_tasks` immediately after
  `mission_slug = planning_dir.name` — i.e., at the hunk anchored
  `@@ -2717,6 +2787,12 @@`, which lands **in the same body region** as this mission's
  `_validate_ownership_manifests` call (line 2766) and `_run_commit_pipeline` call (line
  2789). Not the same lines, but close enough that a rebase onto #3666 (if it lands first)
  will shift this plan's line-number references in §1/§5 and requires a manual diff-context
  re-check, not just an auto-merge assumption.
- **Test-file proximity**: #3666's `test_mission_finalize_phases.py` insertion lands at
  (current-file) line ~459-484, directly before `test_apply_bootstrap_fields_noop_when_already_set`
  (line 462) — close to, but not overlapping, where this plan's FR-002 test is expected to
  land (near `test_apply_ownership_inference_skips_when_present`, current line 487). Different
  hunk regions, so a clean auto-merge is likely, but both PRs editing the same ~50-line window
  of the same test file is a real chokepoint worth a manual look during rebase, not an
  assumed-safe merge.
- **(a) WP-level touch scope** for reviewer cross-check: whichever WP(s) touch
  `mission_finalize.py` under this mission must scope their diff to exactly
  `_apply_ownership_inference`, `_run_bootstrap_loop`'s **body only** (the new
  `state.ownership_contradictions` accumulation and post-loop aggregated raise — not its
  signature), `_validate_ownership_manifests`, and `_compute_and_write_lanes` (plus, if
  needed, the smallest possible plumbing to name the compound-guard half that tripped in
  FR-003's raise) — nothing in `_apply_bootstrap_fields`, `_run_bootstrap_loop`'s **signature,
  or the specific `merge_target_branch=merge_target_branch,` call-argument line #3666 inserts
  into the `_apply_bootstrap_fields(...)` call inside the loop body (corrected per
  PLAN-FRESH2-001 — that line, not just the signature, is #3666's territory)**,
  `_branch_strategy_text`, `_resolve_target_branch`, or `finalize_tasks`'s branch-resolution
  preamble, which remain #3666's territory. **Anchor the new `state.ownership_contradictions`
  accumulation logic strictly after the `_apply_ownership_inference(...)` call's return** — the
  statement(s) immediately following that call in the loop body — and do **not** reformat,
  reorder, or otherwise touch the `_apply_bootstrap_fields(...)` call block three lines above
  it, which belongs to #3666. Because both PRs touch `_run_bootstrap_loop` (corrected above), a
  rebase onto #3666 requires an actual diff-context re-check of this function specifically, not
  just the line-shift caution already noted below.
- **(b) Re-check before landing**: implementation should re-run
  `gh pr view 3666 --json files,state` (or equivalent) shortly before this mission's PR is
  finalized, to catch drift — #3666 may have merged, been amended, or been closed by then.
- **(c) Not blocking.** This mission does not wait on #3666; the disjoint function scope
  means both can proceed independently. This is a rebase-watch, not a dependency.

## 8. Gate Set — Concrete, Evidence-Based

Grounded in `.github/workflows/ci-quality.yml` (4437 lines), read and grepped directly for
this plan on 2026-08-22 against this checkout's HEAD.

**Path-filter groups this mission's diff sets true** (verified against the `filter:` block,
`.github/workflows/ci-quality.yml:230-510`):
- `core_misc` — matches `'src/specify_cli/core/**'` (confirmed present in the `core_misc`
  filter list) → fires on `mission_creation.py`.
- `cli` — matches `'src/specify_cli/cli/**'` (confirmed) → fires on `mission_finalize.py`
  (which lives under `src/specify_cli/cli/commands/agent/`).
- `execution_context` — matches `'src/specify_cli/cli/commands/agent/**'` explicitly
  (confirmed at line ~449) → also fires on `mission_finalize.py`.
- `governance` — matches `'src/specify_cli/ownership/**'` (confirmed at line ~507) → fires
  on `validation.py`.

**Jobs that WILL run on this mission's PR because of those groups:**
- `fast-tests-cli`, `fast-tests-core-misc` — gated on `cli`/`core_misc` respectively.
- `integration-tests-cli`, `integration-tests-core-misc` — same.
- `mission-loader-coverage` — its `if:` condition (line 1442) is
  `needs.changes.outputs.next == 'true' || needs.changes.outputs.core_misc == 'true' || needs.changes.outputs.platform == 'true' || github.event_name == 'push'`
  — `core_misc` alone triggers it, even though this mission adds no code under
  `src/specify_cli/mission_loader/`.
- `e2e-cross-cutting` — its `if:` (line 3218) includes
  `needs.changes.outputs.core_misc == 'true' || needs.changes.outputs.execution_context == 'true'`,
  gated further on the PR being non-draft/non-WIP (or carrying `ci:full`/`ready-for-ci`).
  This mission's diff sets both `core_misc` and `execution_context` true, so this job runs
  once the PR is marked ready-for-review.

**Always-on jobs regardless of path** (the `lint` job at line 613, unconditional except
`pr:deferred`/`pr:skip-ci` labels):
- ruff — `[INFO]` only, advisory (line 871: "Run ruff report (advisory)").
- mypy — `[INFO]` only, advisory (line 902: "Run mypy report (advisory)") — **not enforced**,
  despite the charter's own local-discipline expectation that new code passes
  `mypy --strict`; this mission should still self-check mypy cleanliness locally even though
  CI will not block on it.
- Bandit — `[ENFORCED]` security scan (line 914), included in the job's own
  "Fail job if security checks failed" step (line 976).
- pip-audit — `[ENFORCED]` CVE scan (line 929), included in the same fail-check.
- "Typer 0.26 JSON error surface" — `[ENFORCED]` (line 896) — directly relevant to this
  mission's NFR-001 (JSON error payloads for the new raises), so this gate is a genuine
  signal for this mission's diff, not incidental.
- **Correction on commitlint, verified directly rather than assumed**: commitlint DOES exist
  as a real step (`id: commitlint`, line 673, "[ENFORCED] Run commit message linting",
  invoking `npx @commitlint/cli@19.8.1`) inside this same always-on `lint` job — not merely a
  stale comment. However it is **non-blocking**: the step runs with `continue-on-error: true`
  and is **not** included in the job's "Fail job if security checks failed" step (line
  976, which checks only `bandit`/`pip_audit` outcomes). A commitlint failure only sets
  `commitlint_has_failures`, which triggers the informational `lint-feedback` PR-comment job
  (line 990) on same-repo PRs — it does not fail CI or block merge. Net effect matches the
  practical guidance ("do not plan around a commitlint gate that blocks this PR") even though
  the literal claim that it is "only a stale comment" does not hold — SPEC-KITTY-LEDGER.md's
  SK-64 entry (same day, 2026-08-22) independently confirms commitlint is real and running,
  and warns explicitly against asserting a gate's behavior from reading rather than running
  it — the same correction applies here, made by direct verification rather than repeating
  it.
- Also always-on: `arch-adversarial` (line 2078), `uv-lock-check` (line 3902),
  `diff-coverage` (line 3283), `quality-gate` (line 4249, the final aggregator).

**Explicitly named gates that do NOT apply, with reason:**
- **`kernel-tests`** (line 1082, delegates to `module-kernel.yml`) — gated on
  `needs.changes.outputs.kernel == 'true' || github.event_name == 'push'` only; the `kernel`
  filter group matches `src/kernel/**` / `tests/kernel/**` only. This mission's diff touches
  neither, so `kernel-tests` and its coverage floor are **not live gates** for this PR (though
  several other jobs `needs: [changes, kernel-tests]` and will still wait on/reuse its
  `always()`-gated skip). Per §1: nothing in this mission's diff should ever need to touch
  `src/kernel/**` — if a WP does, that is itself a scope-drift finding.
- **`sonarcloud`** (line 3445) — its `if:` (line 3502) is
  `always() && (github.event_name == 'schedule' || github.event_name == 'workflow_dispatch')`
  only — confirmed it does **not** run on `pull_request`. Do not plan around a Sonar PR
  verdict. The charter's Sonar Expectations (complexity ceiling 15, S1192 constants, etc.)
  still apply as **local discipline** this mission self-checks (§10 already did this for the
  touched functions); no CI gate enforces them on this PR.
- **Every other module-specific shard** (`sync`, `merge`, `missions`, `post_merge`,
  `release`, `status`, `review`, `next`, `lanes`, `dashboard`, `upgrade`, `doctrine`,
  `glossary`, `acceptance`, `auth_audit_git`, `lifecycle`, `agent_surface`, `closeout`,
  `platform`, `docs`, `corpus`) — none of this mission's touched files match those path-filter
  globs (verified against the full filter block), so none of those shards fire. Stated once
  as a class, not exhaustively re-derived per shard.

**Coverage floors:**
- `mission-loader-coverage` (>=90% on `src/specify_cli/mission_loader`, line 1450) **will
  run** (triggered via `core_misc`) even though this mission adds no code there. The floor is
  held **trivially** — no lines added/removed in that package — unless a WP's change has an
  import-time side effect on it. If none (expected), no action needed; state this explicitly
  in the WP validation notes rather than silently assuming it.
- Kernel's 90% floor does **not** apply (see `kernel-tests` above) — do not claim it as a
  held gate for this mission.

## 9. Baseline: Pre-Existing Red vs. Introduced Red (C-005)

`main` carries known-red tests (issue #3284, ~23 failures + 2 errors) and a shared test-venv
lock that can time out (issue #3283) — per `gh issue view 3284` / `gh issue view 3283`,
verified 2026-08-22 (corrected per PLAN-FRESH2-005: neither AGENTS.md's "Test-run baseline-red
gotcha" section, which names #2736/#2772/#1834 as its own worked examples, nor
SPEC-KITTY-LEDGER.md's P0 entries actually names #3284 or #3283 — the issue numbers and their
descriptions are real, confirmed directly against GitHub, just not sourced from either of
those two documents as previously claimed). The classification protocol below still follows
AGENTS.md's baseline-red-gotcha methodology, which does apply generically regardless of which
specific issues are red today.

**Protocol, binding on every implementing WP, before attributing any red observed while
implementing/testing FR-001 through FR-004 to this mission:**

1. Run the specific failing test file/test against the current branch:
   `.venv/bin/python -m pytest <path::test_name> -q`.
2. Run the **same** test against the merge-base / `upstream/main`, using the mechanism
   AGENTS.md's baseline-red section names — a `PYTHONPATH=<worktree>/src` swap against a
   clean checkout of the merge-base commit, or an equivalent `git worktree`/`git stash`
   comparison — **not** a bare re-read of the ledger or issue tracker as a substitute for
   running it.
3. Classify:
   - **Red on-branch AND green on merge-base** → a real regression this mission introduced;
     must not ship.
   - **Red on-branch AND red on merge-base** → pre-existing (category 1/2/3 per AGENTS.md's
     gotcha section); out of scope, must not be "fixed" as part of this mission, and must not
     be silently ignored either — note it in the WP's validation summary so a reviewer can
     confirm the same classification.
4. This confirmation **must happen before the first implementation change lands**, not after
   — i.e., the implementing WP establishes its own local red/green baseline for the test
   files it is about to touch or extend (the `test_mission_finalize_phases.py`,
   `test_mission_create_checkout_restore.py`, `test_finalize_tasks_explicit_empty_owned_files.py`
   files named in §11) as its first step, before writing the FR's failing-first test.

Full policy reference: `docs/development/testing/testing-flakiness.md#test-run-baseline-red-gotcha`.

## 10. Campsite-Clean Scope (Standing Order #2)

**Checked directly against the actual touched functions on this checkout's HEAD, 2026-08-22.
No campsite-clean WP is warranted.** None of the five touched functions (**corrected per
PLAN-FRESH-002 to include `_run_bootstrap_loop`, previously missing from this table even
though it is genuinely touched by this mission's own FR-002 design — see §1**) exceed the
complexity ceiling (15) or carry an obvious Sonar finding in the touched region:

| Function | Lines (verified) | Shape |
|---|---|---|
| `_apply_ownership_inference` | 1264–1295 (32 lines) | 4 simple `if` branches, no nesting beyond one level, no loops |
| `_run_bootstrap_loop` | 1298–1394 (97 lines, verified — next `def` at 1397) | **Added per PLAN-FRESH-002 (confirmed adversarial finding).** A single outer `for wp_file in wp_files:` loop nests up to 3 levels deep in two places — `for`→`try/except`→`if` (unreadable-WP handling) and `for`→`if`→`if`/`else`+`if` (the write-classification block deciding `pending_writes` vs. `would_modify` vs. `modified_wps`/`unchanged_wps`) — and 2 levels deep in a third: `for`→`if`/`else` (dependency-preservation branch, `mission_finalize.py:1344`; corrected per PLAN-FRESH2-006, which found this branch does not reach 3 levels by the same counting convention as the other two). Also contains one nested `for` loop (post-integration-acceptance warnings, `for`→`for`) and one ternary (`bld.build() if frontmatter_changed else wp_meta`). No bare early `return` inside the loop — every path either `continue`s or falls through to the loop-end `return state` at line 1394. This is the longest of the touched functions (97 lines, vs. 62/45/32 for the others). |
| `_validate_ownership_manifests` | 1475–1519 (45 lines) | **Corrected per PLAN-VERIFY-003 (confirmed adversarial finding — verified by direct read of `mission_finalize.py:1475-1519`):** nests up to 3 levels deep in two places — a `for`→`if` pattern (the warning-print loop) and an `if`→`if`/`else`→`for` pattern (inside the ownership-validation-failure branch); **not** "no nesting beyond one level." Of its early exits, only **1** is a bare `return` (`if not wp_manifests:` / `return`, lines 1484-1485); the other **2** are `raise typer.Exit(1) from None` (ownership-validation failure, glob-match failure) — not bare returns, though both are still early exits from the function. |
| `_compute_and_write_lanes` | 1820–1881 (62 lines) | **Corrected per PLAN-VERIFY-003 (confirmed adversarial finding — verified by direct read of `mission_finalize.py:1820-1881`):** nests up to 3 levels deep — a structurally identical `if`→`if`→`for` pattern inside the glob-match-failure branch — plus a separate `if`→`if` (2 levels) around the collapse-report warning print; **not** "no nesting beyond one level." 1 early-return guard (`if not (wp_manifests and wp_dependencies):` / `return None, None`, lines 1834-1835) plus 1 `raise typer.Exit(1) from None` (glob-match failure). |
| `build_wp_manifests` | 335–358 (single 3-line loop) | trivial |
| `mission_creation.py`'s two commit call sites | 767–768, 792–793 | trivial (single `with` + call) |

**The nesting/early-return shape description above is corrected (PLAN-VERIFY-003); the
bottom-line conclusion is NOT disputed by that finding and is unchanged: no campsite-clean WP
is warranted.** **Complexity is now tool-verified, not a rough manual read — corrected per
PLAN-FRESH-002, which flagged that a prior "rough manual… 6–9 range" claim for the two largest
functions was never checked against a real tool and, per its own remediation instruction, had
to be checked honestly rather than assumed:** running
`ruff check --select C901 --config "lint.mccabe.max-complexity=1"` against this checkout's
HEAD reports `_apply_ownership_inference` = **5**, `_run_bootstrap_loop` = **11**,
`_validate_ownership_manifests` = **11**, `_compute_and_write_lanes` = **8**. All four are
under the ceiling of 15, but this corrects the prior "6–9 range" claim, which understated
`_validate_ownership_manifests` (actually 11). `_run_bootstrap_loop` and
`_validate_ownership_manifests` are tied as the most complex of the touched functions — 11 of
15, a 4-point margin — meaningfully higher than the other two but not itself "near the
ceiling" today.

**Honest flag on `_run_bootstrap_loop` specifically, said plainly rather than silently forcing
the existing "no WP warranted" conclusion (per PLAN-FRESH-002's remediation instruction):**
`_run_bootstrap_loop`'s *planned* FR-002 change (§1: a new branch to route each
`_apply_ownership_inference` contradiction descriptor into `state.ownership_contradictions`,
plus a new post-loop `if state.ownership_contradictions: raise …`) adds at least one, likely
two, new branches to a function already measured at 11 — plausibly landing in the 12–13 range
after the change, still under 15 but with a narrower margin than any other touched function.
This does not by itself warrant a preceding campsite-clean WP — the pre-change baseline (11)
is not over or near the ceiling — but the implementing WP for FR-002 **must** re-run
`ruff check --select C901` against `_run_bootstrap_loop` immediately after making the change,
as part of its own validation, and extract a small helper (e.g. splitting the per-WP loop body
into a `_process_bootstrap_wp_file` helper, or a small `_raise_ownership_contradictions_if_any`
post-loop helper) if the post-change measurement is at or above 15 — not defer that decision to
a future mission. This plan does **not** invent cleanup work here; per the reconciliation order
in the charter (smallest-viable-diff first, Boy Scout Rule strictly inside the touched file
set, Locality of Change as the brake), the functional FR-001..FR-004 changes proceed directly,
with no preceding tidy-first WP — the honest post-change re-check above is a validation step
inside the FR-002 WP, not a separate WP.

## 11. Red-First / ATDD Test Strategy

Every FR gets a test that **fails when the fix is reverted** — not merely one that passes
with the fix — extending real, existing test files (verified present in this checkout, not
assumed):

| FR | Fixture / scenario | Assertion that fails on revert | Home file (verified to exist) |
|---|---|---|---|
| **FR-001** (raise on hard commit failure) | Mock/force `_commit_feature_file` to raise inside `create_mission_core` (locked `.git/index`, failing pre-commit hook, or a direct monkeypatch raising from within the `with contextlib.suppress(Exception):` block) | Assert `create_mission_core` (or the `specify` CLI invocation) exits non-zero and the underlying git error text is surfaced — not swallowed into a silent success | `tests/core/test_mission_create_checkout_restore.py` (already tests atomicity of `create_mission_core`'s git side effects via `_restore_git_state_after_failed_create`) — extend with a case that forces the `meta.json` commit itself to fail, distinct from the existing coordination-branch-mint failure cases it covers |
| **FR-001** (no-op case unchanged) | A checkout with genuinely nothing new to commit for `meta.json` | Assert `specify`/`create_mission_core` still succeeds exactly as today (Acceptance Scenario 3 — proves the fix distinguishes hard-failure from no-op) | `tests/specify_cli/core/test_feature_creation.py` — this file already mocks `_commit_feature_file` broadly across ~10 tests; one of those (or a new one following the same pattern) asserts the no-op path is unaffected |
| **FR-001** (documentation branch, Acceptance Scenario 4) | Same forced hard-failure applied to the `mission == "documentation"` branch | Assert identical raise-and-rollback behavior at the second call site (line 792-793) | Same file as above, or `tests/core/test_mission_creation_topology.py` if it already exercises the documentation mission type — verify at WP-start which file already has documentation-mission fixtures before creating a new one |
| **FR-001** (NFR-003, rollback correctness) | Snapshot branch/HEAD-commit/index-tree before a forced failure, force the failure, snapshot again | Assert all three are identical before/after — no partial mutation survives | `tests/core/test_mission_create_checkout_restore.py` — this is exactly its documented purpose |
| **FR-002** (reject at bootstrap — aggregated raise) | WP file with `execution_mode: code_change` and explicit `owned_files: []` in frontmatter | **Corrected per PLAN-FRESH-001 (confirmed adversarial finding — this row previously targeted the wrong function):** under the adopted collect-all-then-raise-once design (§1/§5, PLAN-ARCH-001), a *direct* call to `_apply_ownership_inference` with this fixture does **not** raise — it returns a contradiction descriptor. Assert instead that `_run_bootstrap_loop` (driven with a WP-file list containing this one offending WP), or the full `finalize-tasks` run it's part of, raises **once the loop completes**, naming the WP ID and "code_change WP declares no owned files" | `tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py` — no existing test drives `_run_bootstrap_loop` directly with an ownership-contradiction fixture; add one following the file's established direct-seam-call conventions (see e.g. `test_apply_ownership_inference_skips_when_present`, line ~487, for the fixture-construction pattern), but calling `seam._run_bootstrap_loop(...)` (or invoking `finalize_tasks` end-to-end) rather than `_apply_ownership_inference` alone |
| **FR-002** (direct-seam contradiction descriptor, no raise) | Same WP fixture (`execution_mode: code_change`, explicit `owned_files: []`), called directly against `_apply_ownership_inference` | **Added per PLAN-FRESH-001 — a distinct, narrower row separated out from the raise assertion above, not a substitute for it:** Assert `_apply_ownership_inference`, called directly and bypassing `_run_bootstrap_loop`, does **NOT** raise — it returns a contradiction descriptor for the WP as the third element of its pinned `tuple[bool, list[str], str | None]` return shape (per §1, corrected per PLAN-FRESH2-003) — i.e. `changed, warnings, descriptor = seam._apply_ownership_inference(...)` with `descriptor` a non-`None` `str` naming the WP ID — which is the caller's signal to accumulate rather than an exception | `test_mission_finalize_phases.py` — extend with a sibling test using the same direct-call pattern as `test_apply_ownership_inference_skips_when_present` (line ~487), `execution_mode="code_change"` and an explicit-empty-list raw body, asserting the returned descriptor rather than an exception |
| **FR-002** (JSON payload) | Same fixture, `--json` invocation | **Corrected per PLAN-FRESH-001 — was singular "WP ID" (pre-redesign, single-offender) framing; now explicitly one-or-more, consistent with the batch-report row below:** Assert the JSON error payload carries a stable machine-readable field naming **one or more** offending WP IDs (singular when only one WP contradicts, plural when `_run_bootstrap_loop` has aggregated several before raising) + error code | **Corrected per PLAN-VERIFY-002 (confirmed adversarial finding):** `tests/specify_cli/cli/commands/agent/test_mission_finalize_tasks.py` is **not** a candidate — its own docstring (verified) states it "focus[es] on the resolver itself rather than driving the full `finalize-tasks` Typer command" and names `tests/integration/test_mission_close.py` as the full-pipeline test. Direct verification shows `test_mission_close.py` neither drives `finalize-tasks` at all (it exercises `spec-kitty merge`/mission-close teardown, a different command) nor has any `json_output`/`--json` assertions (`grep` confirms zero). The actual closest existing home, found by grepping for `finalize-tasks --json` usage: **`tests/tasks/test_finalize_tasks_json_output_unit.py`** — it already drives the full command via `runner.invoke(app, ["finalize-tasks", "--json"])` and asserts JSON schema shape (`commit_hash`, `commit_created`, `files_committed`, etc.), but only for **success**-path payloads; add a sibling test there following its existing `CliRunner`/mock-patch pattern, driving a fixture that trips the new FR-002 reject and asserting the resulting `--json` payload's error shape |
| **FR-002** (planning-artifact escape hatch unaffected, Acceptance Scenario 3) | WP with `execution_mode: planning_artifact` and explicit `owned_files: []` | **Corrected per PLAN-FRESH-001's class of finding — "does not raise" is no longer a differentiating assertion under the adopted design:** under the collect-all-then-raise-once redesign, a direct call to `_apply_ownership_inference` never raises for *any* `execution_mode` (raising only happens later, once, inside `_run_bootstrap_loop`) — so "does not raise" alone no longer distinguishes this planning-artifact case from the `code_change` contradiction case above. Assert instead that `_apply_ownership_inference` returns `None` as the third element of its pinned `tuple[bool, list[str], str | None]` return shape (per §1, corrected per PLAN-FRESH2-003) — the "absent" case is `descriptor is None`, not an empty string or empty list slot, distinct from the `code_change` fixture's row above, which returns a non-`None` `str` — and the WP is still accepted exactly as today — proves the fix is scoped to `code_change` only | **Corrected per PLAN-VERIFY-001 (confirmed adversarial finding — do not overstate what an existing file locks):** `tests/specify_cli/cli/commands/test_finalize_tasks_explicit_empty_owned_files.py` **does exist, but its 6 tests call only the pure helper `_owned_files_yaml_is_explicit_empty_list`** — none construct a `WPMetadata`, set `execution_mode`, or call `_apply_ownership_inference` (the actual function FR-002's reject is added to). It is a useful **supporting regression check** on the detection helper, run as part of this WP's own validation to confirm FR-002 does not regress it — it is **not** a substitute for AC3 coverage. Real AC3 coverage requires a **new direct-seam test** in `tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py`, following the existing `test_apply_ownership_inference_skips_when_present` pattern (verified at line **487**: builds a `WPMetadata`, calls `seam._apply_ownership_inference(bld, meta, "body", "001-m", {})` directly) but with `execution_mode="planning_artifact"` and a raw frontmatter body carrying an explicit `owned_files: []`, asserting `_apply_ownership_inference` returns no contradiction descriptor. |
| **FR-002** (batch-report, PLAN-ARCH-001's option (a), Acceptance Scenario 4) | A mission fixture with **2+ WPs sharing the same `code_change` + explicit `owned_files: []` contradiction**, plus at least one valid WP | Assert the single `finalize-tasks` run fails **once** and names **every** offending WP ID in that one aggregated error (not just the first) — proves the collect-all-then-raise-once design from §1/§5, not merely raise-on-first-offense | `test_mission_finalize_phases.py`, driving `_run_bootstrap_loop` (or `finalize_tasks` end-to-end) across a multi-WP fixture so the loop actually iterates past the first offender before the aggregated raise fires |
| **FR-003** (empty `wp_manifests`) | Fixture where `wp_manifests` is empty | Assert `_compute_and_write_lanes` raises rather than returning `(None, None)`; assert `lanes.json` is absent | `test_mission_finalize_phases.py` — no existing direct-seam test for `_compute_and_write_lanes` was found in this file; add one following the same pattern as the existing `_apply_ownership_inference`/`_flush_frontmatter_writes` direct-call tests |
| **FR-003** (non-empty `wp_manifests`, empty `wp_dependencies`, Acceptance Scenario 5) | Fixture where `wp_manifests` is non-empty but `wp_dependencies` is empty | Assert `_compute_and_write_lanes` also raises — covers the whole compound guard, not just the `wp_manifests`-empty half | Same file, sibling test |
| **FR-003** (`--json` failure surfaced, Acceptance Scenario 2/SC-003) | Same empty-manifest fixture, `--json` run | Assert `--json` payload reports failure (not `"result": "success"`) with a machine-readable indication lane computation did not run | **Corrected per PLAN-VERIFY-002 (confirmed adversarial finding):** `test_mission_finalize_tasks.py` dropped as a candidate for the same reason as the FR-002 JSON row above (its docstring rules out driving the full command; `test_mission_close.py`, the file it names instead, verified to neither drive `finalize-tasks` nor assert `json_output`/`--json` anywhere). Same fix: extend **`tests/tasks/test_finalize_tasks_json_output_unit.py`** with a new failure-path test using its existing `runner.invoke(app, ["finalize-tasks", "--json"])` pattern, asserting a non-`"success"` result and the machine-readable lane-computation-failed indicator |
| **FR-003** (residual gap, Acceptance Scenario 6, §5) | An FR-003 reject fires | Assert `lanes.json` is absent; explicitly does **NOT** assert frontmatter/event-log absence (that guarantee is not provided — asserting it would be a false claim) | **Corrected per PLAN-VERIFY-002's class of finding (`test_mission_finalize_tasks.py` does not drive `_run_commit_pipeline` — see its docstring, verified above):** `test_mission_finalize_phases.py` (direct-seam call into `_run_commit_pipeline`/`_compute_and_write_lanes`) or `tests/tasks/test_finalize_tasks_json_output_unit.py` (full-command `runner.invoke(app, ["finalize-tasks", ...])` path) — whichever the FR-003 WP finds cleanest to assert `lanes.json` absence against — the test docstring/comment must say explicitly why it does not check frontmatter/event-log state, so a future reader does not "fix" the test into asserting a guarantee this mission does not make |
| **FR-004** (malformed `authoritative_surface`, empty manifest map, Acceptance Scenario 3) | `wp_manifests` empty AND a WP frontmatter carries a malformed `authoritative_surface` (bare `src/`, empty string, trailing slash) | Assert `_validate_ownership_manifests` still runs and rejects, identifying the WP and field — does not return silently on the old `if not wp_manifests: return` | `test_mission_finalize_phases.py` — extend with a direct-seam call to `seam._validate_ownership_manifests(...)`, following the file's established pattern |
| **FR-004** (valid values still pass, Acceptance Scenario 4) | `wp_manifests` empty, all `authoritative_surface` values valid | Assert the mission still passes exactly as it would with a non-empty manifest map — proves the fix does not turn a legitimately-empty, legitimately-valid mission into a spurious failure | Same file, sibling test — both directions (reject + accept) must be present, not just the rejection path |

**Coverage of every Acceptance Scenario, not just every FR title** (per plan-authoring
instruction): the table above maps every numbered Acceptance Scenario from User Stories 1–3
in spec.md to a concrete test, including the "unchanged behavior" scenarios (US1 Scenario 3,
US2 Scenario 3, US3 Scenario 4/6) that prove the fix does not over-reject — these are as
important as the reject-path tests and must not be skipped as "obviously fine."

## 12. Phasing / WP-Shape Guidance for the Tasks Phase

*(This is PLAN, not TASKS — the following gives tasks.md its constraints; it does not author
work packages.)*

- **Default PR shape: ONE PR** (spec-kitty's own convention, not tk's per-WP-PR rule), unless
  the diff genuinely cannot be read in a sitting. **This plan's judgment: it fits in one
  sitting.** The touched-function set is small (6 changed call sites across 2 files with an
  actual diff — corrected count per §1, PLAN-ARCH-003/PLAN-FRESH-002 — ~32+97+45+62+trivial
  lines of enclosing-function size, not diff size, per §1/§10; the actual diff to each
  function is a small fraction of its full body) and the bulk of the diff will be tests
  (§11), which
  read independently of the production-code diff. Recommend a single PR unless the
  tasks-authoring agent's own count of the assembled diff disagrees at authoring time — if
  so, say so explicitly in tasks.md rather than silently splitting.
- **No campsite-clean WP precedes the functional WPs** — §10 found none warranted.
- **FR-001 (`mission_creation.py`) and FR-002/003/004 (`mission_finalize.py`) are largely
  independent write scopes** — disjoint production files, and could be authored as two
  separate WPs if the tasks phase prefers smaller units. (`validation.py`'s
  `build_wp_manifests` is examined by the FR-002/003/004 WP per §1's resolution but is
  **not** diffed — corrected per PLAN-ARCH-003; do not list it as a third production file to
  write.) **Chokepoint
  to name explicitly if split**: both would touch shared test infrastructure —
  `tests/specify_cli/core/test_feature_creation.py`'s `_commit_feature_file` mocking pattern
  (FR-001 WP) and `tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py`'s
  direct-seam pattern (FR-002/003/004 WP) are in different files, so this is a low-risk
  split, but both WPs will also want to read/extend
  `tests/specify_cli/cli/commands/test_finalize_tasks_explicit_empty_owned_files.py` (FR-002
  WP for the regression check) and both will independently need the C-005 baseline-red
  protocol (§9) run against their own targeted test files before starting — call this out in
  tasks.md so neither WP skips it assuming the other already established the baseline.
- **§7's PR #3666 rebase-watch applies to whichever WP(s) touch `mission_finalize.py`**
  (i.e., the FR-002/003/004 WP if split, or the single WP if not split) — restate the
  function-level write-scope boundary from §7 in that WP's own prompt so its implementer
  does not need to rediscover it.
