---
work_package_id: WP12
title: Arbiter override retirement
dependencies:
- WP06
- WP07
- WP11
requirement_refs:
- FR-009
- FR-010
- FR-011
planning_base_branch: pr/review-verdict-write-integrity-01KZ1CGF
merge_target_branch: pr/review-verdict-write-integrity-01KZ1CGF
branch_strategy: Planning artifacts for this mission were generated on pr/review-verdict-write-integrity-01KZ1CGF. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/review-verdict-write-integrity-01KZ1CGF unless the human explicitly redirects the landing branch.
created_at: '2026-08-03T08:13:56Z'
subtasks:
- T051
- T052
- T053
- T054
- T055
- T056
agent: claude
history:
- at: '2026-08-03T08:13:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/
create_intent:
- src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/arbiter.py
- tests/review/test_arbiter.py
- src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py
- tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP12 - Arbiter override retirement

> **On `create_intent` in this WP's frontmatter.** It lists
> `tasks_verdict_persistence.py`, which **WP06 creates, not this WP**. The entry is
> required by the ownership gate, which rejects any literal `owned_files` path
> matching zero files unless it is declared planned-new — and at validation time
> that module does not exist yet. Read it as "this path is planned-new at mission
> level", not as a claim that this WP creates it. By the time this WP starts, WP06
> has already extracted the module.

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

## Objective

**The framing changed after review, and it matters for what this WP actually
does.** An earlier reading of this mission assumed the arbiter override writer
(`persist_arbiter_decision` and friends, `src/specify_cli/review/arbiter.py`)
needed to be MADE durable — given a commit step, the way WP01 of the predecessor
mission gave the review-cycle writer one. **That is not the residual work.**
`_persist_review_artifact_override` in
`src/specify_cli/cli/commands/agent/tasks_materialization.py:40-80` **already**
event-sources the override durably: it emits a single `InnerStateChanged`
`review` delta carrying a `ReviewOverride{at, actor, wp_id, reason}` via
`emit_inner_state_changed`, which is the SAME event-log commit path every other
status transition uses. That path is already correct, already durable, and
already consumed by the merge gate without any flag.

**The actual residual is retirement**: `persist_arbiter_decision`'s frontmatter
block (`arbiter_override` written into `review-cycle-N.md`'s YAML, `arbiter.py:437-475`)
and its JSON sidecar fallback (`arbiter-override-N.json`, `arbiter.py:478-500`)
are TWO NON-AUTHORITATIVE, NEVER-DURABLY-COMMITTED representations of the SAME
fact `ReviewOverride` already carries authoritatively. FR-009/FR-010/FR-011 are
about retiring these two representations INTO `ReviewOverride`, not building a
third mechanism alongside them. **`ReviewOverride`'s own docstring
(`src/specify_cli/status/models.py:398-405`) forbids inventing
`review_artifact_override_*` fields** — "do NOT reuse the review-result shape...
and do NOT invent `review_artifact_override_*` fields" — so any fix here must
route through the EXISTING four-field shape, never widen it.

**The arbiter's own resolver is broken independently of durability, and this is
the more severe finding.** `_find_review_cycle_artifact`
(`arbiter.py:370-397`) resolves the artifact directory as `feature_dir /
"tasks" / wp_id` — a **bare** work-package id (e.g. `tasks/WP06/`) — while the
writer (`_review_cycle_wp_dir` in `review/cycle.py`, and `_resolve_wp_slug` in
`tasks_materialization.py`) resolves and writes under the WP's full **slug**
(e.g. `tasks/WP06-arbiter-override-retirement/`). In the normal case these two
strings differ, so `_find_review_cycle_artifact` reads a directory that **does
not exist**, `wp_subdir.exists()` is `False`, and the function falls through to
its `tasks_dir.glob(f"*{wp_id}*review-cycle*.md")` fallback scan — which may or
may not find anything depending on the glob's luck. **The override is not
merely un-durable; in the ordinary case it is never found at all**, which means
`persist_arbiter_decision` takes its FALLBACK JSON-sidecar path far more often
than its "primary" frontmatter-stamping path was ever designed to run, and the
frontmatter path is effectively dead code masquerading as the primary
mechanism.

**A second, independent bug in the fallback path**: `_find_review_cycle_artifact`
picks `for candidate in sorted(wp_subdir.glob("review-cycle-*.md")): return
candidate` — with a comment claiming this returns "the most recently created
one." **`sorted()` on filename strings is lexicographic, not numeric or
chronological** — `"review-cycle-10.md"` sorts BEFORE `"review-cycle-2.md"`
(because `"1" < "2"` as the first differing character), so once a WP reaches its
tenth review cycle, this function silently starts returning the WRONG (older)
artifact. The comment's claim was never true; it happened to work only while
every WP's cycle count stayed single-digit.

**Failure surfacing is inconsistent and, under `--json`, silent.** In
`tasks_move_task.py`'s arbiter-persist call site (post-WP06 extraction, in
`tasks_verdict_persistence.py`), the `except Exception as _arb_err:` handler's
diagnostic print is guarded by `if not json_output:` — so under `--json`, an
arbiter-persist failure produces **no output at all**: no exception propagates,
no JSON key reports it, nothing. An operator/script running `--json` has no way
to learn the override failed to persist. Spec.md's User Story 2, Acceptance
Scenario 3 is explicit: *"an override whose persistence fails... the failure is
surfaced — never swallowed into a warning."* Today it is swallowed into a
warning that is itself invisible under `--json`.

**Suppressing the fabricated approval alone is a regression, not a fix.** The
naive read of "an override should never produce an approval record" is an early
return that skips writing an approval — but that LEAVES the WP's latest
review-cycle verdict as a standing `rejected`, with NOTHING recording that an
arbiter knowingly proceeded over it. Spec.md's User Story 2 framing is explicit
about this: *"the second half is what makes the first half safe... Raised to P1
because the naive fix (an early return) suppresses the record without replacing
it."* Both halves — no fabricated approval, AND a real override record — must
land together.

**The re-pin belongs here, not to a later WP.**
`tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py:721`
(inside `TestMoveTaskDecisionBranchesFrozen.test_arbiter_override_persists_decision`)
currently pins the DIVERGENT bare-id directory as the expected output:
`assert sc.evidence["arbiter_artifacts"] == ["tasks/WP01/arbiter-override-1.json"]`
— i.e., it locks in today's broken resolver's output shape (a bare `WP01`
directory, a JSON sidecar) as the frozen contract. Once T053 fixes the resolver
to use the correct slug and T051/T052 retire the frontmatter/sidecar
representations into `ReviewOverride`, this exact assertion becomes both
factually wrong (the resolved path changes) AND conceptually wrong (there is no
longer a sidecar/frontmatter artifact to assert on — the override lives in the
event log). **T056 re-pins this test deliberately, in this WP**, not left for
WP13/WP14 to discover as unexplained breakage.

## Context & Constraints

- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/spec.md` — User Story 2 in full, FR-009, FR-010, FR-011, SC-005
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/plan.md` — IC-09 ("Arbiter override retirement")
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/data-model.md` — the "Arbiter override" entity, the four-representations table, I-4
- `src/specify_cli/review/arbiter.py` — `persist_arbiter_decision`, `_persist_in_artifact`, `_persist_standalone_json`, `_find_review_cycle_artifact`, `get_arbiter_overrides_for_wp`
- `src/specify_cli/cli/commands/agent/tasks_materialization.py:40-80` — `_persist_review_artifact_override` (the ALREADY-correct event-sourced mechanism this WP retires the other two representations INTO), and `:105-129` — `_resolve_wp_slug` (the CORRECT slug-aware resolver the arbiter should have been using all along)
- `src/specify_cli/status/models.py:398-424` — `ReviewOverride`, including its docstring's explicit prohibition on inventing new fields
- `docs/adr/3.x/2026-07-19-1-...` (ADR 2026-07-19-1) — governs the event-sourced mechanism as the chartered single authority
- `tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py:377-395` (approx.) and `:715-725` (approx., `test_arbiter_override_persists_decision`) — the test this WP MUST re-pin (T056)

**This WP's surface has moved** (same note as WP11): by the time this WP starts,
WP06 has extracted the arbiter-persist CALL SITE (not `arbiter.py` itself, which
stays where it is) out of `tasks_move_task.py` and into
`tasks_verdict_persistence.py`. Locate the actual current call site there.
**This WP also depends on WP11** because both land in the same new module —
confirm WP11's durability-signal and call-ordering changes are already present
before adding this WP's failure-surfacing and no-fabricated-approval changes on
top, so the two don't collide on the same `except`/`--json` envelope code.

**Constraints (binding)**:
- **Do not widen `ReviewOverride`.** Its docstring is explicit and load-bearing: no new fields, no reused `review`-slot shape from elsewhere. If a piece of information the arbiter frontmatter/JSON currently carries (e.g. `ArbiterCategory`, `ArbiterChecklist`'s five answers) has no home in `ReviewOverride`'s four fields, that information is EITHER folded into `reason` as prose, OR explicitly dropped as out-of-scope with a rationale — it is NOT a justification for adding a fifth field.
- **`review_artifact_override_*` artifact fields (representation #4 in data-model.md's table) are OUT OF SCOPE** — read-only, no writer since 2026-07-01, owned by `wp-runtime-state-eviction-01KXWN13`'s deferred WP10, explicitly RETAINED by operator decision. Do not touch `ReviewCycleArtifact.override_actor`/`override_reason` or their frontmatter round-trip in `review/artifacts.py`.
- **C-002**: no verdict-vocabulary changes. This WP's "no fabricated approval" fix must not introduce any new `verdict` value — the override remains a `ReviewOverride` fact, never disguised as `verdict: approved`.

## Subtasks & Detailed Guidance

### Subtask T051 – Retire the arbiter frontmatter block into `ReviewOverride`

- **Purpose**: Stop `_persist_in_artifact` from stamping a non-authoritative `arbiter_override` YAML block onto `review-cycle-N.md` — the fact it records is already durably carried by `ReviewOverride` via `_persist_review_artifact_override`.
- **Steps**:
  1. Confirm the call chain: does `persist_arbiter_decision` currently get called from a site that ALSO independently calls `_persist_review_artifact_override` (i.e., is the event-sourced emit already happening alongside the frontmatter stamp, making the frontmatter genuinely redundant), or does today's flow call ONLY `persist_arbiter_decision` and never reach `_persist_review_artifact_override` at all? Trace this from the actual `tasks_verdict_persistence.py` call site (post-WP06/WP11) before assuming redundancy — the objective's framing above states `_persist_review_artifact_override` "already" event-sources durably, but confirm it is actually WIRED IN on the arbiter-override code path specifically, not just present somewhere else in the codebase for a different trigger.
  2. If the event-sourced emit is NOT currently reached from the arbiter-override path: wire `persist_arbiter_decision`'s caller to call `_persist_review_artifact_override` (or the WP06-relocated equivalent) with the arbiter's `actor`/`reason`, so the durable record is created on the SAME call that used to only stamp frontmatter.
  3. Remove `_persist_in_artifact` and its frontmatter-stamping call path from `persist_arbiter_decision` — the function should no longer rewrite `review-cycle-N.md`'s YAML at all for this purpose. Fold whatever non-`ReviewOverride` information `ArbiterDecision`/`ArbiterCategory`/`ArbiterChecklist` carry into the `reason` string passed to `ReviewOverride` (e.g. `f"[{category}] {explanation}"`, reusing the existing `[category] explanation` note format `parse_category_from_note` already parses elsewhere) rather than inventing a new field.
  4. Confirm `get_arbiter_overrides_for_wp` (used by `agent tasks status` for kanban display) is updated to read from the event-sourced `ReviewOverride` (via whatever reducer/snapshot API WP07 built) INSTEAD of scanning `review-cycle-*.md` frontmatter for an `arbiter_override` key — this display path must not silently start returning nothing once the frontmatter write stops happening.
- **Files**: `src/specify_cli/review/arbiter.py`, `src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py`
- **Parallel?**: No — T052 depends on understanding this same call chain.
- **Notes**: `ReviewCycleArtifact.write()`'s docstring already carries a long note about `serialize_mapping`'s byte-for-byte parity with the prior YAML dumper — removing `_persist_in_artifact`'s separate, DIFFERENT-width YAML dump (`YAML()` default width ~80, per its own `#3058` comment) is itself a small piece of the truthfulness sweep this mission cares about; do not preserve it "just in case" once it is no longer called.

### Subtask T052 – Retire the JSON sidecars into `ReviewOverride`

- **Purpose**: Stop `_persist_standalone_json` from writing `arbiter-override-N.json` files — the same fact, in a second non-authoritative representation.
- **Steps**:
  1. Once T051's wiring makes the event-sourced emit reachable from every arbiter-override call (both the "artifact exists" and "artifact does not exist" cases `persist_arbiter_decision` currently branches on), the JSON-sidecar fallback branch becomes entirely dead — the emit does not need an existing artifact to succeed (per `_persist_review_artifact_override`'s own docstring, it resolves the emit target from the artifact PATH already known to the caller, or independently if none exists — confirm which).
  2. Remove `_persist_standalone_json` and the `artifact_path is not None and artifact_path.exists()` branch in `persist_arbiter_decision` that chooses between the two representations — after this subtask, `persist_arbiter_decision` (or its replacement) should have exactly ONE path: emit the `ReviewOverride` event, unconditionally.
  3. Update `get_arbiter_overrides_for_wp`'s JSON-sidecar-scanning half (the `for json_file in sorted(wp_subdir.glob("arbiter-override-*.json")):` loop) to be removed alongside — same reasoning as T051 step 4, this display path reads from the event-sourced snapshot now, not from either on-disk representation.
  4. Decide and document the migration story for ALREADY-WRITTEN `arbiter-override-*.json` files and `arbiter_override` frontmatter blocks from BEFORE this WP lands — are they silently orphaned (never read again), or does `get_arbiter_overrides_for_wp` need a one-time fallback read for pre-existing data? Check whether WP08's reconciliation-command scope (a separate WP, out of this WP's `owned_files`) is meant to cover this, or whether it is explicitly out of scope per data-model.md's Lifecycle note for `ReviewCycleArtifact` ("`arbiter._persist_in_artifact` rewrites a persisted artifact's frontmatter in place today, and IC-09 keeps that path until it is retired" — confirming THIS WP is the one retiring it, but not necessarily migrating old data). If genuinely out of scope, say so explicitly in this WP's PR description rather than leaving it unaddressed and undocumented.
- **Files**: `src/specify_cli/review/arbiter.py`
- **Parallel?**: [P] with T051's later steps once the wiring question (T051 step 1) is answered, but do not start before that.
- **Notes**: Do not delete `ArbiterDecision`/`ArbiterCategory`/`ArbiterChecklist`/`create_arbiter_decision`/`prompt_arbiter_checklist`/`parse_category_from_note` — these remain the interactive/non-interactive DECISION-CONSTRUCTION machinery; only the two PERSISTENCE functions (`_persist_in_artifact`, `_persist_standalone_json`) and their dispatcher (`persist_arbiter_decision`'s branching body) are retired/replaced.

### Subtask T053 – Fix the bare-`wp_id` resolver and the lexicographic sort

- **Purpose**: `_find_review_cycle_artifact` reads the wrong directory in the ordinary case (bare id vs. slug) and picks the wrong file once cycle counts reach double digits. Fix both.
- **Steps**:
  1. Replace `_find_review_cycle_artifact`'s directory resolution (`tasks_dir / wp_id`) with the SAME slug-aware resolution the writer uses — reuse `_resolve_wp_slug(main_repo_root, mission_slug, wp_id)` (from `tasks_materialization.py`) or whatever WP06/WP13 has consolidated it to, rather than re-deriving a second, independent slug-lookup.
  2. Confirm this function still has access to `main_repo_root`/`mission_slug` (it currently takes only `feature_dir`, `wp_id`, `review_ref`) — thread whatever additional parameter is needed through `persist_arbiter_decision`'s own signature and its call site, since `feature_dir` alone is not sufficient to resolve a slug via the placement-seam-aware resolver.
  3. Fix the lexicographic-sort bug: replace `for candidate in sorted(wp_subdir.glob("review-cycle-*.md")): return candidate` (which returns the LEXICOGRAPHICALLY FIRST match, mislabeled by its own comment as "the most recently created one") with a NUMERIC sort by cycle number, returning the HIGHEST cycle number — reuse `ReviewCycleArtifact.latest()` (`review/artifacts.py`) directly instead of hand-rolling a second glob-and-pick, now that the directory resolution (step 1) is correct.
  4. Add a regression test with 10+ review cycles present (`review-cycle-1.md` through `review-cycle-10.md` or more) confirming the resolver picks `review-cycle-10.md` (or whichever is numerically highest), not `review-cycle-1.md`.
  5. Add a regression test confirming the resolver finds an artifact that a bare-id lookup would have missed — i.e., a fixture where `tasks/<wp_id>/` (bare) does NOT exist but `tasks/<wp_id>-<slug>/` (full slug) DOES, with a review-cycle artifact inside the latter — asserting the fixed resolver finds it.
- **Files**: `src/specify_cli/review/arbiter.py`
- **Parallel?**: No — T054/T055 build on a correctly-resolving `persist_arbiter_decision`.
- **Notes**: Given T051/T052 retire BOTH persistence representations this function was originally locating (the frontmatter target and the JSON-sidecar fallback), confirm whether `_find_review_cycle_artifact` is even still CALLED after T051/T052 land, or whether it becomes dead code itself — if the event-sourced emit path (T051's wiring) never needs to locate/rewrite an existing artifact file at all, this whole function may be deletable rather than fixable. Re-derive from the actual post-T051/T052 call graph before doing more work than necessary here; if it is genuinely still needed (e.g. to populate `ReviewOverride`'s emit-target resolution the way `_persist_review_artifact_override`'s docstring describes — "resolves the emit target from the caller-resolved artifact path"), fix it as described above.

### Subtask T054 – Surface arbiter-persist failure, including under `--json`

- **Purpose**: An override-persistence failure must be surfaced, never swallowed — under BOTH human console output and `--json`.
- **Steps**:
  1. Locate the `try: ... persist_arbiter_decision(...) ... except Exception as _arb_err: if not json_output: console.print(...)` shape (post-WP06/WP11 extraction, in `tasks_verdict_persistence.py`).
  2. Decide, per spec.md User Story 2 Acceptance Scenario 3's wording ("the failure is surfaced — never swallowed into a warning"), whether "surfaced" means: (a) the exception propagates and the command exits non-zero, or (b) the command still exits per its normal contract but the `--json`/console output unambiguously reports the failure as a FAILURE, not a dim warning easily missed. Re-read the surrounding acceptance scenario and this command's existing error-handling conventions (does `move-task` generally exit non-zero when A REQUIRED side effect fails, vs. exit 0 with a reported partial failure for a BEST-EFFORT one?) to make this call consistently with how the rest of the command behaves — arbiter-override persistence is not best-effort (it is the ONLY record of the override once T051/T052 retire the frontmatter/sidecar fallbacks), which argues for (a) or a very loud (b).
  3. Implement whichever surfacing the analysis in step 2 selects. If (b), add a named `--json` key (e.g. `"arbiter_override_persisted": false` with an accompanying `"arbiter_override_error"` message) mirroring T049's pattern from WP11 for the durability signal, and remove the `if not json_output:` guard around the equivalent human-readable failure notice (a FAILURE notice should print regardless of `--json`, or be captured in the JSON payload — not be silently dropped either way).
  4. Add a test forcing `persist_arbiter_decision`/its replacement to raise, confirming the failure is visible in BOTH `--json` and plain output — not just one.
- **Files**: `src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py`, `tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py` (or `test_move_task_durability.py` from WP11, if the fixture harness there is a better fit — check before duplicating a harness)
- **Parallel?**: [P] with T055, coordinate on the same `except` block.
- **Notes**: Do not conflate this failure-surfacing fix with T055's "suppress the fabricated approval" fix — they touch overlapping code (the arbiter-override handling in the same call site) but are two independent correctness properties. Land them together but verify each with its own explicit test.

### Subtask T055 – Suppress the fabricated approval on the override path

- **Purpose**: An arbiter override must never be recorded as (or indistinguishable from) an approval — but suppressing the fabrication alone, without ensuring the override itself is durably recorded, is a regression (per the Objective's explicit warning).
- **Steps**:
  1. Locate wherever the CURRENT code path, on an arbiter override, might produce something that LOOKS like an approval — e.g. does the override flow currently ALSO call the approval-side review-cycle writer (`_persist_approved_review_cycle` / its WP06-relocated equivalent) alongside `persist_arbiter_decision`, or does it rely solely on the FSM's own lane-transition semantics (force-forward from `planned`) with no separate approval-verdict write? Trace this precisely — the objective's "naive fix (an early return) suppresses the record without replacing it" language implies there IS currently some code path an implementer might be tempted to just early-return out of; find it.
  2. If a fabricated-approval code path exists, confirm the override case is EXCLUDED from it — i.e., when `_is_arbiter_override(...)` returns `True` for this transition, the approval-verdict writer must NOT be called (no `review-cycle-N.md` with `verdict: approved` gets written for an override — I-4 in data-model.md: "an override recorded as an approval, in either store" is a state this mission makes unrepresentable).
  3. Simultaneously — this is the part a naive early-return skips — confirm the override IS durably recorded via T051's wiring (the `ReviewOverride` event-sourced emit) on this SAME code path. Write a test asserting BOTH halves for one override transition: (a) no new `review-cycle-N.md` with `verdict: approved` exists after the override, AND (b) `ReviewOverride` for this WP is present, `complete`, and carries the actual `actor`/`reason` supplied.
  4. Confirm the merge gate (read-only from this WP's perspective — do not modify `post_merge/review_artifact_consistency.py` here, that is WP04/WP07/WP13 territory) still passes for this WP once the override is recorded via `ReviewOverride` alone, with no approval artifact — this should already work per FR-010's note that "a complete override already clears the gate without any flag," but confirm it end-to-end as this WP's own acceptance evidence, not by inspection.
- **Files**: `src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py`, `tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py`
- **Parallel?**: No — depends on T051's wiring (the durable-record half of "suppress AND replace") being in place first.
- **Notes**: Re-read spec.md's User Story 2 framing once more before implementing: *"Suppressing the fabricated approval alone would leave the work package with a rejected latest verdict and nothing recording the arbitration."* Your test for this subtask must fail against a fix that ONLY does the suppression half — construct the test to catch exactly that half-measure.

### Subtask T056 – Re-pin `test_tasks_cli_contract_coord.py`'s arbiter path

- **Purpose**: The frozen contract test currently pins the BROKEN bare-id/JSON-sidecar output shape as correct. Re-pin it against the POST-retirement shape, deliberately, in this WP.
- **Steps**:
  1. In `tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py`, locate `TestMoveTaskDecisionBranchesFrozen.test_arbiter_override_persists_decision` (around line 715-725) and its `assert sc.evidence["arbiter_artifacts"] == ["tasks/WP01/arbiter-override-1.json"]` assertion, plus the `evidence={"arbiter_artifacts": [...]}` construction that feeds it (around line 387, in the scenario-running harness — `[str(p.relative_to(fd)) for p in fd.rglob("arbiter-override-*.json")]`).
  2. Determine the NEW observable shape after T051/T052 retire the JSON-sidecar and frontmatter representations: there is no longer an `arbiter-override-*.json` file to glob for at all. Decide what THIS test should assert instead — most likely, that the `ReviewOverride` event exists in `status.events.jsonl` (or the materialized snapshot) with the expected `actor`/`reason`/`wp_id`, rather than scanning the filesystem for a sidecar. Reuse whatever assertion helper WP07's reducer work already provides for reading back a `ReviewOverride` from a test fixture's event log, rather than hand-rolling a raw JSONL parse.
  3. Rewrite the scenario harness's `evidence` construction (if `arbiter_artifacts`'s filesystem-glob shape is no longer meaningful at all) to capture the NEW observable — e.g. `evidence={"arbiter_override": <the resolved ReviewOverride dict or None>}` — and update the test's assertion to match, explicitly citing this WP and ADR 2026-07-19-1 / the mission's superseding decision in the test's docstring or an inline comment, so a future reader understands WHY the pin changed and does not mistake it for an unexplained regression.
  4. Confirm every OTHER test in `TestMoveTaskDecisionBranchesFrozen` (the class this test lives in, which freezes several OTHER move-task decision branches per its own docstring: "Freeze each named move_task guard branch WP03 extracts (FR-004)") is unaffected by this WP's changes — run the full class, not just the one re-pinned test, before marking this subtask done.
- **Files**: `tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py`
- **Parallel?**: No — depends on T051-T053 all being complete, since this test needs to know the FINAL post-retirement observable shape to re-pin against.
- **Notes**: This re-pin is EXPECTED and INTENTIONAL — do not treat the test going red mid-WP as a regression to avoid; it is the exact signal this subtask exists to close. Per C-007/the mission's general discipline, a frozen-contract test changing its assertion always needs a citing rationale in the diff (commit message or inline comment), not a silent value swap.

## Test Strategy

- `pytest tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py -v` — especially `TestMoveTaskDecisionBranchesFrozen`
- `pytest tests/review/ -k arbiter -v` (if any exist) plus any new arbiter-focused tests this WP adds
- Full scoped regression: `pytest tests/specify_cli/cli/commands/agent/ tests/review/ tests/status/ -q` (NFR-001)
- `mypy --strict src/specify_cli/review/arbiter.py src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py`
- `ruff check src/specify_cli/review/arbiter.py src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py`

## Branch Strategy

Planning artifacts for this mission were generated on
`pr/review-verdict-write-integrity-01KZ1CGF`. During `/spec-kitty.implement` this
WP may branch from a dependency-specific base (WP06, WP07 and WP11 must be
merged into whatever base this WP branches from), but completed changes must
merge back into `pr/review-verdict-write-integrity-01KZ1CGF` unless the human
explicitly redirects the landing branch.

## Definition of Done

- [ ] T051/T052: `_persist_in_artifact` and `_persist_standalone_json` are
      deleted and `git grep` returns zero hits for either name across the
      repository — not merely unused-but-present code paths.
      `persist_arbiter_decision` (or its replacement) has exactly one path:
      emit the `ReviewOverride` event, unconditionally.
      `get_arbiter_overrides_for_wp` reads from the event-sourced
      `ReviewOverride` (via the reducer/snapshot API), not from
      `arbiter_override` frontmatter or `arbiter-override-*.json` sidecars.
- [ ] T053: `_find_review_cycle_artifact` (or its successor, if T053's own
      dead-code analysis concludes it should be deleted) resolves via the same
      slug-aware resolver the writer uses, and a 10+-cycle regression test
      confirms the numerically highest cycle is selected, not the
      lexicographically first.
- [ ] T054: an arbiter-persist failure is surfaced under BOTH `--json` and
      plain console output, each proven by its own explicit test.
- [ ] T055: a single test proves BOTH halves together — no `review-cycle-N.md`
      with `verdict: approved` is written for an override, AND `ReviewOverride`
      for that WP is present, `complete`, and carries the actual `actor`/
      `reason` supplied.
- [ ] T056: `test_arbiter_override_persists_decision`'s re-pin cites this WP
      and ADR 2026-07-19-1 inline, and the full
      `TestMoveTaskDecisionBranchesFrozen` class passes, not just the
      re-pinned test.
- [ ] `ReviewOverride` gains no new field — any information the retired
      frontmatter/JSON carried that has no home in the existing four fields is
      folded into `reason` as prose or explicitly dropped with a stated
      rationale.
- [ ] No `review_artifact_override_*` artifact-frontmatter code path
      (representation #4, retained by operator decision for a different
      mission) appears in this WP's diff.
- [ ] NFR-002: every function touched by this WP ends at cyclomatic complexity
      ≤15 (`ruff C901`).
- [ ] NFR-003: `ruff` and `mypy --strict` report zero issues on every touched
      file, with zero new suppressions.
- [ ] Full scoped regression (`pytest tests/specify_cli/cli/commands/agent/
      tests/review/ tests/status/ -q`) shows no new failures beyond
      `research/baseline-8466727eb.md`'s two rows (NFR-001).

## Risks & Mitigations

- **Widening `ReviewOverride` under pressure**: if `ArbiterCategory`/`ArbiterChecklist`'s richer structure feels like it "deserves" its own field once you're mid-retirement, resist — the docstring's prohibition is explicit and this is exactly the kind of pressure C-002-style behaviour-floor violations come from. Fold into `reason` as prose, or drop, but do not add a field.
- **Deleting `_find_review_cycle_artifact` prematurely**: T053's note flags that this function may become dead code after T051/T052 — but confirm via the ACTUAL post-T051/T052 call graph, not by assumption, before deleting it. If `_persist_review_artifact_override`'s emit-target resolution genuinely still needs it, fixing (not deleting) is correct.
- **Landing T055 without T051's wiring**: suppressing the fabricated-approval write without confirming the override event actually lands reproduces the exact regression the objective warns about, in a way that might not be caught by a shallow test (a test that only checks "no approval artifact exists" would pass even with NOTHING recording the override at all). T055's own test must check BOTH halves.
- **The T056 re-pin masking a genuine regression**: because a re-pin is expected here, there's a risk of re-pinning to whatever the new code happens to produce without checking that the NEW behavior is actually correct per FR-009/FR-010/FR-011 — verify the new assertion's VALUES (actor, reason, wp_id) are the real, correctly-resolved ones, not just "some object exists now."

## Reviewer Guidance

- Confirm `_persist_in_artifact` and `_persist_standalone_json` are actually REMOVED (or their call sites are), not merely left in place unused alongside a new parallel event-sourced path — "retirement" means the non-authoritative representations stop being written, not that a third mechanism was added on top of two live ones.
- Confirm the resolver fix (T053) uses the SAME slug-derivation the writer uses (`_resolve_wp_slug` or its consolidated successor), not a second independent slug-guessing heuristic.
- Confirm the double-digit-cycle regression test (T053) actually exercises 10+ cycles and would have failed against the old lexicographic sort.
- Confirm T054's failure-surfacing fix makes an arbiter-persist failure visible under BOTH `--json` and plain output — test both explicitly.
- Confirm T055's test checks BOTH "no fabricated approval" AND "the override IS durably recorded" — a test checking only one half does not prove this subtask's actual requirement.
- Confirm T056's re-pin cites its rationale (WP number, ADR, or mission decision) inline, and that the full `TestMoveTaskDecisionBranchesFrozen` class was re-run, not just the one re-pinned test.
- Confirm no `review_artifact_override_*` artifact-frontmatter code path (representation #4, the deferred-mission's retained fields) was touched.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-03T08:13:56Z – system – lane=planned – Prompt created.

- 2026-08-04T00:00:00Z – claude – note – T051/T052/T053 landed together: `persist_arbiter_decision`
  retired to a single unconditional event-sourced `ReviewOverride` emit via `_persist_review_artifact_override`
  (routed through the fixed slug-aware/numeric-highest-cycle resolver, `_resolve_wp_slug` + `_review_cycle_wp_dir`
  + `ReviewCycleArtifact.latest`); `_find_review_cycle_artifact`, `_persist_in_artifact`, `_persist_standalone_json`
  deleted outright (git grep zero hits). T054: `persist_arbiter_override_decision`'s fail-open swallow removed —
  a persist failure now propagates to `tasks_move_task.py`'s existing outer handler (surfaced under both `--json`
  and plain output). T055: `_persist_approved_review_cycle` gained an `is_arbiter_override` guard so an arbiter
  override targeting approved/done never also fabricates an approval — verified with a test that fails against a
  suppression-only half-measure. T056: re-pinned `test_arbiter_override_persists_decision` against the
  event-sourced `review` snapshot slot; full `TestMoveTaskDecisionBranchesFrozen` class green.
  `verdict_seam_IC01.yaml` updated (disclosed cross-WP edit, WP01's own WP06/WP10/WP11 precedent) to drop the
  three retired arbiter.py rows per category; `verdict_seam_IC08.yaml`'s three FR-009 retire rows for
  `_find_review_cycle_artifact`/`persist_arbiter_decision`/`get_arbiter_overrides_for_wp` are now satisfied.
  Known collateral (both outside this WP's `owned_files`, disclosed in the WP12 implementer report): all of
  `tests/review/test_arbiter.py` (43 tests) fails at collection (`ImportError`) since it imports the two deleted
  functions directly; `tests/specify_cli/cli/commands/agent/test_tasks_move_task_seam.py::
  test_persist_arbiter_override_decision_fail_open_on_persist_error` fails by design (it pins the exact
  fail-open swallow T054 retires).
- 2026-08-04T00:00:00Z – claude – note – Operator ruling `DM-01KZ6X4Y7A3XPK5AJ96AA49XJ9`: `tests/review/
  test_arbiter.py` added to this WP's `owned_files`; the ~20-test `tests/architectural/` cascade (`_gate_coverage.py
  ::collect_universe` runs its own whole-tree `--collect-only` regardless of invocation scope) was confirmed as the
  same single root cause. Fixed: deleted 13 tests whose behaviour no longer exists anywhere (four
  `_find_review_cycle_artifact` tests, two `_persist_in_artifact` tests, the #3058 frontmatter-wrap test, and the
  six-case `_persist_standalone_json` traversal-guard class — its guarded `mkdir(wp_id)` call site is gone, and the
  full `tests/architectural/test_untrusted_path_containment.py` audit, re-run, confirms no replacement sink exists);
  rewrote the tests whose behaviour survived under the new event-sourced shape (persist-then-materialize,
  slug-vs-bare-id resolution, empty/no-override/incomplete-override reads); net 48 → 35 collected, each removal
  annotated in-file. Also rewrote (did not delete) `test_tasks_move_task_seam.py::
  test_persist_arbiter_override_decision_fail_open_on_persist_error` → `..._propagates_persist_error`, asserting
  the new T054 contract (raises, no console output) instead of the retired swallow. `tests/review/` (455 passed),
  `tests/specify_cli/cli/commands/agent/` (green except pre-existing #3160), and `tests/architectural/` (full,
  27-item cascade cleared) all reverified.
---

### Updating Lane Status

Use: `spec-kitty agent tasks move-task WP12 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
