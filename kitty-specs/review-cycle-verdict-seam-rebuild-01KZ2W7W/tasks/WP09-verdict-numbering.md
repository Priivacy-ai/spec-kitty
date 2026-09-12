---
work_package_id: WP09
title: Verdict numbering
dependencies:
- WP01
requirement_refs:
- FR-006
planning_base_branch: pr/review-verdict-write-integrity-01KZ1CGF
merge_target_branch: pr/review-verdict-write-integrity-01KZ1CGF
branch_strategy: Planning artifacts for this mission were generated on pr/review-verdict-write-integrity-01KZ1CGF. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/review-verdict-write-integrity-01KZ1CGF unless the human explicitly redirects the landing branch.
created_at: '2026-08-03T08:13:56Z'
subtasks:
- T032
- T033
- T034
agent: claude
history:
- at: '2026-08-03T08:13:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/artifacts.py
- tests/review/test_artifacts.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP09 - Verdict numbering

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

## Objective

`ReviewCycleArtifact.next_cycle_number` computes the next cycle number as
`len(candidates) + 1` — a **count**, not a **derivation from the numbers already
on disk**. The moment a gap opens in the numbering (a deleted file, a reconciled
record, a record moved out-of-band), the count and the true next-number diverge,
and the count-based path can hand out a number that is already live on disk.

Reproduced, verbatim from spec.md's Edge Cases: with `['review-cycle-1.md',
'review-cycle-3.md']` present, `next_cycle_number()` returns `3` — colliding with
the file that is already there. `create_rejected_review_cycle` (`review/cycle.py`)
then calls `artifact.write(artifact_path)` on that colliding path with no
existence check first, so the write **silently truncates and replaces the live
`review-cycle-3.md`** — destroying whichever verdict, reviewer prose, and
affected-files list that record carried. This is not a hypothetical: any upgrade,
manual repair, or WP08 reconciliation pass that leaves a numbering gap turns into
a silent data-loss bug the instant this WP's fix is not in place.

**FR-006** (spec.md) requires a new record to *never* overwrite an existing one.
**I-2** (data-model.md) states the same invariant. This WP closes the gap with two
changes to `ReviewCycleArtifact.next_cycle_number`:

1. Derive the next number as `max(parsed cycle numbers) + 1`, not `len(candidates) + 1`.
2. Refuse — raise, don't silently pick a different number — when the derived next
   number is somehow already occupied (belt-and-suspenders against a future
   caller that supplies its own cycle number, or a second concurrent writer that
   raced this one; WP10 owns the concurrency *serialization*, this WP owns the
   *arithmetic* that serialization protects).

**The unparseable-sibling case is the trap, and it is why `max` alone is not
enough.** `ReviewCycleArtifact.latest`'s own local `_cycle_num` helper (same
file, `review/artifacts.py:290-292`) returns `0` for any filename that does not
match `review-cycle-(\d+)\.md` — so a junk or hand-edited sibling
(`review-cycle-final.md`, `review-cycle-N.md.bak` picked up by an over-broad
glob, or a filename with a corrupted digit run) sorts **first** under
`candidates.sort(key=_cycle_num)`, not last. A naive `max(parsed) + 1` that
silently skips anything it cannot parse reproduces exactly the same defect this
WP exists to close, one level down: it derives a next-number that is blind to a
file it could not read, and a later reconciliation pass that fixes the
unparseable name then finds its real cycle number already double-allocated.
T033 exists specifically to make the unparseable case a **refusal**, not a
silent skip.

**Success criteria this WP is directly responsible for** (from spec.md, verbatim
where useful):
- **FR-006**: "As an auditor, I want a new record to never overwrite an existing
  one, so that history cannot be destroyed by a gap in numbering."
- **SC-002** (this WP's share): under the numbering-gap edge case specifically,
  the readable verdict for cycle 3 never disagrees with what was actually
  recorded for cycle 3 — i.e., recording cycle 4 must not silently become a
  second write to cycle 3's path.
- **I-2** (data-model.md): "A verdict record is never overwritten by a new one
  — enforced by FR-006 (`max + 1` + collision refusal)." This is the exact
  mechanism named in the invariant table; implement precisely this, not a
  variant.

## Independent Test

Per `tasks.md`'s own framing for this WP: *"With cycles 1 and 3 present,
recording a new verdict does not touch cycle 3."* Build the fixture exactly
this way — do not substitute a smaller or larger gap as a shortcut, since the
specific `[1, 3]` shape is the one the mission's spec, plan, and data-model all
cite verbatim, and a reviewer will look for that exact case. The test must
prove two things simultaneously: the new record lands at `review-cycle-4.md`
(not `review-cycle-3.md`, which `len()+1` would have produced), AND
`review-cycle-3.md`'s bytes on disk are unchanged by the operation — read it
before and after and compare, rather than trusting "no exception was raised"
as a proxy for "nothing was touched."

## Context & Constraints

- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/spec.md` — FR-006, Edge Cases ("Cycle-number gaps"), SC-002
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/plan.md` — IC-05b ("Verdict numbering")
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/data-model.md` — I-2, "Verdict record" cycle_number note
- `src/specify_cli/review/artifacts.py:280-304` — `ReviewCycleArtifact.latest` and `next_cycle_number`, the two functions sharing the identical glob-and-sort shape this WP must keep consistent
- `src/specify_cli/review/artifacts.py:307-347` — `latest_review_artifact_verdict`, a **third** copy of the same `_cycle_num`/glob/sort shape (not touched by this WP's owned files list beyond consistency — do not fork a fourth copy; reuse the corrected helper)

**Constraints (binding)**:
- **C-002**: do not introduce a new verdict value or weaken any of the three named behaviour floors. This WP touches only cycle-number derivation; it must not alter `verdict` semantics.
- **Do not touch `ReviewCycleArtifact.latest`'s read behaviour** beyond what's needed to share the corrected parsing helper — `latest` returning the highest-numbered *existing* artifact is correct today; only the *next*-number derivation is wrong.
- **WP10 owns concurrency serialization** (locking `next_cycle_number` + the write into one critical section). This WP owns only the arithmetic; do not add locking here — that would duplicate WP10's critical section and risk two different lock scopes disagreeing.
- This module (`review/artifacts.py`) is a convergence point also claimed by WP13 and WP14, serialized `WP09 → WP13 → WP14` per `tasks.md`'s ownership table. Keep the diff narrow to numbering — broader consolidation is those WPs' job.

## Subtasks & Detailed Guidance

### Subtask T032 – Derive cycle numbers from `max(parsed) + 1`

- **Purpose**: Replace the count-based `len(candidates) + 1` with a derivation from the actual numbers present on disk, so a numbering gap can no longer produce a colliding number.
- **Steps**:
  1. In `src/specify_cli/review/artifacts.py`, add a module-level (or `ReviewCycleArtifact`-scoped) helper that, given `sub_artifact_dir: Path`, globs `review-cycle-*.md`, extracts the integer cycle number from each filename via the SAME regex `latest` already uses (`re.search(r"review-cycle-(\d+)\.md$", p.name)`), and returns the set/list of **successfully parsed** integers alongside the list of filenames that did NOT parse (for T033).
  2. Rewrite `next_cycle_number(sub_artifact_dir: Path) -> int` to: return `1` when no candidates exist at all (unchanged for the empty-directory case); otherwise return `max(parsed_numbers) + 1` when every candidate parsed cleanly.
  3. Do not change the return type (`int`) or the function's public signature — every existing caller (`review/cycle.py`'s `create_rejected_review_cycle`) must keep compiling and calling it identically.
- **Files**: `src/specify_cli/review/artifacts.py`
- **Parallel?**: No — T033 extends this same function's body.
- **Notes**: The existing `latest()` method's `_cycle_num` closure (lines 290-292) already embodies "unparseable sorts as 0" — do not reuse that closure's *sorting* behaviour for the *next-number* derivation; T032/T033 need "unparseable is a refusal", `latest()`'s "unparseable sorts first" is a DIFFERENT, already-shipped behaviour for a different question (which is the *highest currently-readable* artifact) and is out of this WP's scope to change.

### Subtask T033 – Refuse on collision, including the unparseable-sibling case

- **Purpose**: Make the refusal cover BOTH ways a new record could destroy an existing one: (a) the derived next-number is somehow already a file on disk, and (b) a sibling file exists that looks like a review-cycle artifact but cannot be parsed for its number — which `max()` alone would silently ignore, reintroducing exactly the defect class T032 fixes.
- **Steps**:
  1. Define (or reuse a project-standard) exception for this refusal — `ReviewCycleError` already exists in `src/specify_cli/review/cycle.py`; either import it here (check for an import-cycle risk first — `cycle.py` imports FROM `artifacts.py`, so `artifacts.py` importing FROM `cycle.py` would create one) or raise a plain `ValueError` from `artifacts.py` and let `cycle.py`'s caller translate it to `ReviewCycleError` at the call site in `create_rejected_review_cycle`. Prefer the translation-at-call-site shape to avoid the cycle.
  2. In the helper from T032, when ANY candidate filename fails to parse (i.e., matches the `review-cycle-*.md` glob but not the strict `review-cycle-(\d+)\.md$` regex — e.g. `review-cycle-final.md`, `review-cycle-.md`, `review-cycle-1.md.bak` if the glob is broad enough to catch it), raise/return a refusal identifying the unparseable filename(s) by name rather than silently excluding them from the `max()` computation. Do NOT let an unparseable sibling be silently dropped — that reproduces the identical failure shape one level down, just triggered by a different malformed input.
  3. Additionally guard the derived number itself: after computing `max(parsed) + 1`, check whether a file at that exact cycle number already exists (defensive — should be unreachable given (2), but a caller could have injected a discontiguous set some other way); raise the same refusal if so.
  4. Surface the refusal from `create_rejected_review_cycle` (`review/cycle.py`) as a `ReviewCycleError` with a message naming the offending directory and (for the unparseable case) the specific filename(s), so an operator has enough information to run a WP08 reconciliation pass rather than guessing.
- **Files**: `src/specify_cli/review/artifacts.py`, `src/specify_cli/review/cycle.py` (only the translation point, if a plain `ValueError`/exception-cycle avoidance route is taken)
- **Parallel?**: No — depends on T032's helper existing.
- **Notes**: This is the subtask the plan's Risks section calls out by name: *"the refusal must cover the unparseable case too — `_cycle_num` returns 0 for a junk filename, so it sorts first rather than last."* A reviewer should specifically check that a fixture with an unparseable sibling (e.g. `['review-cycle-1.md', 'review-cycle-garbage.md']`) is REFUSED, not silently treated as `next = 2` (which would be `max({1}) + 1` if the garbage file were simply skipped rather than flagged) — the correct behaviour is a hard refusal naming `review-cycle-garbage.md`, because the true next number cannot be established with confidence while an unparseable candidate is present.

### Subtask T034 – Red-first reproduction of the gap-overwrite

- **Purpose**: Per the charter's ATDD-first discipline (C-011) and this mission's explicit "reproduction owed" framing for cycle-number gaps (spec.md Edge Cases marks this **Reproduced**, but the regression pin for THIS mission's fix must still exist before the fix lands), author the red test first, confirm it fails against the unmodified `next_cycle_number`, then let T032/T033 turn it green.
- **Steps**:
  1. In `tests/review/test_artifacts.py`, add `test_next_cycle_number_survives_a_numbering_gap`: create a fixture directory containing `review-cycle-1.md` and `review-cycle-3.md` only (both minimally-valid parseable artifacts, or bare files if `next_cycle_number` operates on filenames alone — check the current implementation's actual dependency before choosing the fixture shape). Assert `ReviewCycleArtifact.next_cycle_number(fixture_dir) == 4`. Run it against the pre-fix code first and confirm it fails with `3` (the reproduction), THEN apply T032/T033 and confirm it passes.
  2. Add `test_next_cycle_number_refuses_on_unparseable_sibling`: fixture directory with `review-cycle-1.md` and a non-conforming file that the current glob would still catch (confirm exactly which glob pattern `next_cycle_number` uses first — `review-cycle-*.md` catches `review-cycle-final.md` and `review-cycle-1.md.bak`-if-suffixed-oddly; pick whichever the real glob actually matches). Assert the call raises the refusal from T033, naming the bad filename in the message.
  3. Add `test_next_cycle_number_empty_directory_still_returns_one`: confirm the unchanged zero-candidate case (`next_cycle_number(empty_dir) == 1`) is not disturbed by the rewrite — a straightforward backward-compatibility regression.
  4. Add an integration-shaped test (or extend an existing `tests/review/test_cycle.py` fixture if that file already has a "cycle 1 and cycle 3 present" setup) asserting that calling `create_rejected_review_cycle` against the gapped directory produces `review-cycle-4.md` and leaves `review-cycle-3.md`'s content byte-identical (the literal SC-002/FR-006 acceptance scenario: "with cycles 1 and 3 present, recording a new verdict does not touch cycle 3").
- **Files**: `tests/review/test_artifacts.py`
- **Parallel?**: No — depends on T032/T033 for the green state, but the red test itself should be authored and run FIRST, per C-011.
- **Notes**: Do not skip step 1's "confirm it fails against the unmodified code" — this is the literal ATDD discipline the charter and this mission's spec (Revision History table) both call out as having been skipped previously, to the mission's detriment ("three successive spec revisions pinned counts that were all wrong"). A reviewer checking this WP should be able to see, in the PR history or activity log, that the red state was observed before the green one.

## Test Strategy

- `pytest tests/review/test_artifacts.py -v`
- Full scoped regression before marking done: `pytest tests/review/ -q` (no regression in `latest()`, `latest_review_artifact_verdict()`, or any other consumer of the shared glob/parse shape)
- `mypy --strict src/specify_cli/review/artifacts.py`
- `ruff check src/specify_cli/review/artifacts.py tests/review/test_artifacts.py`
- SC-002's own wording covers a WIDER guarantee than this WP alone delivers ("under injected failure in either direction... zero work packages reach a state where a readable verdict disagrees with the completed outcome") — this WP's tests are the numbering-arithmetic SLICE of that guarantee; the concurrency slice belongs to WP10 and the transition-ordering slice to WP11. Do not attempt to write a test here that exercises those other WPs' mechanisms; a numbering-only fixture (no threads, no injected commit failures) is the correct scope.
- Why this matters for WP08: a future reconciliation pass (WP08, out of this WP's scope) is exactly the kind of operation that CREATES a numbering gap on purpose — e.g. moving a stranded record from a retired path into the canonical directory at whatever number it already carries, leaving a hole below it. This WP's fix is what makes WP08's reconciliation safe to run without a subsequent write silently clobbering the reconciled record; keep that dependency direction in mind if anything here seems over-engineered for a "simple" arithmetic fix — it is the load-bearing guarantee a later WP relies on.

## Branch Strategy

Planning artifacts for this mission were generated on
`pr/review-verdict-write-integrity-01KZ1CGF`. During `/spec-kitty.implement` this
WP may branch from a dependency-specific base (WP01 must be merged into
whatever base this WP branches from), but completed changes must merge back into
`pr/review-verdict-write-integrity-01KZ1CGF` unless the human explicitly
redirects the landing branch.

## Definition of Done

- [ ] T032: `next_cycle_number` derives its result as `max(parsed cycle
      numbers) + 1`, not `len(candidates) + 1`; the function's return type and
      public signature are unchanged, and the empty-directory case still
      returns `1`.
- [ ] T033: an unparseable sibling filename (one that matches the
      `review-cycle-*.md` glob but not the strict numbering regex) produces a
      hard refusal naming the offending filename, never a silent skip that
      falls back to `max()` over only the parseable candidates; a derived
      number that collides with an existing file on disk also refuses.
- [ ] T034: `test_next_cycle_number_survives_a_numbering_gap` was observed
      failing (returning `3`) against the unmodified `next_cycle_number`
      before T032/T033 landed, with that observation recorded in the Activity
      Log or PR description — not asserted after the fact.
- [ ] With `review-cycle-1.md` and `review-cycle-3.md` present, recording a new
      verdict lands at `review-cycle-4.md`, and `review-cycle-3.md`'s bytes are
      asserted byte-identical before and after the operation in at least one
      test — not inferred from "no exception was raised."
- [ ] `latest()`'s existing "unparseable sorts as cycle `0`" behaviour is
      unchanged by this WP.
- [ ] No locking was added in this WP's diff — concurrency serialization is
      WP10's scope, not this WP's.
- [ ] NFR-002: every function touched by this WP ends at cyclomatic complexity
      ≤15 (`ruff C901`).
- [ ] NFR-003: `ruff` and `mypy --strict` report zero issues on every touched
      file, with zero new suppressions.
- [ ] Full scoped regression (`pytest tests/review/ -q`) shows no new failures
      beyond `research/baseline-8466727eb.md`'s two rows (NFR-001).

## Risks & Mitigations

- **Import-cycle risk on the refusal exception**: `cycle.py` imports from `artifacts.py`; raising `ReviewCycleError` (defined in `cycle.py`) directly from `artifacts.py` would invert that and create a cycle. Mitigate by raising a plain `ValueError`/local exception in `artifacts.py` and translating to `ReviewCycleError` at the `create_rejected_review_cycle` call site, OR by moving `ReviewCycleError` to a location both modules can import from without inversion — confirm which approach the existing import graph (`review/cycle.py:22-26` already imports `REVIEW_ARTIFACT_VERDICTS`, `AffectedFile`, `ReviewCycleArtifact` FROM `artifacts.py`) supports before choosing.
- **Silent-skip regression**: the most tempting shortcut is `max((n for n in parsed_numbers), default=0) + 1` while quietly filtering unparseable names out of the generator — this reads as a fix for the reproduced case (T034's first test) while leaving the unparseable-sibling case (T034's second test) exactly as broken as `len() + 1` was. Both tests must be green, not just the first.
- **Triple-duplicated parsing logic**: `latest()`, `next_cycle_number()`, and `latest_review_artifact_verdict()` each currently carry their own private `_cycle_num`/glob/sort. Consolidating all three into one shared helper is tempting but out of scope here beyond what's needed for T032/T033 — a broader consolidation risks colliding with WP13's consumer-unification work on the same file. Keep the diff to the numbering path only.
- **Fixing the symptom instead of the arithmetic**: a shortcut that special-cases "if the count-based number already exists on disk, try count+1, count+2, ..." until an unused number is found would ALSO close the literal `[1, 3]` reproduction (it would find `4` by probing), while leaving the real defect — the derivation is not anchored to the numbers actually present — intact for any gap shape a probing loop happens to guess around incorrectly (e.g. a gap combined with an unparseable sibling in the wrong order could still probe into a collision). `max(parsed) + 1` is the correct derivation; do not substitute a probe-and-retry loop for it.

## Reviewer Guidance

- Confirm `test_next_cycle_number_survives_a_numbering_gap` was actually run RED before the fix (check activity log / PR description for the observed failure), not just added alongside the green fix.
- Confirm the unparseable-sibling refusal names the actual offending filename in its error message — a generic "cannot determine next cycle number" without identifying which file is the problem does not give an operator enough to act on.
- Confirm `latest()`'s own behaviour (sorting an unparseable sibling as cycle `0`, i.e. first) was NOT changed by this WP — that is a different, already-shipped answer to a different question, and changing it here would be scope creep with its own blast radius.
- Confirm no locking was added in this WP — that is WP10's job, and duplicating it here risks two independently-acquired critical sections that disagree about scope.
- Confirm the fix is `max(parsed) + 1`, not a probe-and-retry loop over candidate numbers — the latter can pass the exact `[1, 3]` reproduction while leaving the underlying derivation unanchored to disk state for other gap shapes.
- Confirm `review-cycle-3.md`'s content is asserted byte-identical before and after the new write, in at least one test — not merely "still exists."

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-03T08:13:56Z – system – lane=planned – Prompt created.
- 2026-08-04T00:00:00Z – claude – lane=in_progress – Ownership conflict noted:
  the prompt's T033 step 4 and T034 step 4 point at `src/specify_cli/review/cycle.py`
  and `tests/review/test_cycle.py`, both owned by WP10/WP13, not WP09. Per the
  orchestrator's explicit resolution, raised a plain `ValueError` from
  `artifacts.py` instead (no `ReviewCycleError` import, no import-cycle risk),
  left the `ReviewCycleError` translation point in `cycle.py` untouched for
  WP10/WP13 to add, and put the T034 step-4 integration test in
  `tests/review/test_artifacts.py` (importing `create_rejected_review_cycle`
  from `cycle.py`, not editing it).
- 2026-08-04T00:00:00Z – claude – lane=in_progress – Red-first (T034,
  C-011): added `test_next_cycle_number_survives_a_numbering_gap` to
  `tests/review/test_artifacts.py` and ran it against the unmodified
  `next_cycle_number`. Observed failure:
  `AssertionError: assert 3 == 4` — confirming the reproduction (count-based
  numbering returns 3 for `['review-cycle-1.md', 'review-cycle-3.md']`,
  colliding with the live cycle-3 file). Only after capturing this did T032/T033
  land in `src/specify_cli/review/artifacts.py`.
- 2026-08-04T00:00:00Z – claude – lane=in_progress – T032/T033 implemented:
  added a private `_parse_review_cycle_candidates` helper (used only by
  `next_cycle_number`, not shared with `latest()` or
  `latest_review_artifact_verdict()` — those two keep their existing
  "unparseable sorts as cycle 0" closures unchanged, per the WP's own Risks
  section against fourth-copy consolidation colliding with WP13). Rewrote
  `next_cycle_number` to derive `max(parsed) + 1`, refuse (plain `ValueError`,
  naming the offending filename) when any sibling fails the strict
  `review-cycle-(\d+)\.md$` regex, and refuse defensively when the derived
  number already exists on disk. No locking added (WP10's scope). All
  required tests plus a defensive-collision-guard test and a
  `create_rejected_review_cycle` integration test (byte-identical
  before/after on cycle 3) added to `tests/review/test_artifacts.py`; all
  green. `ruff`, `ruff --select C901`, and `mypy --strict` clean on both
  owned files with zero new suppressions (also removed one pre-existing
  stale/unused `# type: ignore[arg-type]` in the test file while touching it).
  Full `tests/review/` (462 passed, 1 skipped), `tests/post_merge/` +
  `tests/merge/` (705 passed), and `tests/status/test_reducer.py` (45 passed)
  show no regressions.

---

### Updating Lane Status

Use: `spec-kitty agent tasks move-task WP09 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
