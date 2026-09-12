# Research: Review-Cycle Verdict Seam Rebuild

Phase 0 output. Unusually for a research document, almost none of this is
literature review — the unknowns here were *facts about this codebase* that two
successive spec revisions got wrong. Every finding below was produced by a probe
or a reproduction, not by reading code and reasoning.

The methodology matters because it is what the previous two revisions lacked.
Where a claim is inferred rather than measured, it says so.

---

## R1 — What is actually authoritative for a verdict?

**Decision**: The status event is authoritative for *which* verdict is current and
where its content lives. The verdict record is authoritative for *what the
reviewer said*. Neither reconstructs the other.

**Rationale**: Measured directly.

```
ReviewResult fields       : feedback_path, reference, reviewer, verdict
ReviewCycleArtifact fields: affected_files, body, cycle_number, mission_slug,
                            override_actor, override_reason, reproduction_command,
                            reviewed_at, reviewer_agent, verdict, wp_id
review_result survives read_events : yes
'review_result' in reduced snapshot: False
```

Six artifact fields have no counterpart on the event, so the artifact is not
reconstructible from the log. `ReviewResult.reference` is a `feedback://` URI and
`feedback_path` is a pointer — the event is an **index**, the artifact is the
**payload**. And `reduce()` never surfaces `review_result`, so the index has no
reader downstream of the reducer today.

**Alternatives considered**:

- *Two-phase commit across both stores* (spec v1). Rejected as unachievable: the
  verdict commits to the primary branch, the lane event commits to the
  coordination branch inside `BookkeepingTransaction`, and that transaction
  refuses paths outside the coord worktree by design.
- *The artifact is a projection of the event* (spec v2). Rejected as factually
  false — see the field census above. This was the recommendation of the v1
  architecture review, adopted without verification, and falsified by the v2
  probe. Recorded because the failure mode (adopting a plausible recommendation
  without measuring it) is the one this mission keeps hitting.
- *Widen `ReviewResult` to carry the artifact's payload*. Viable but materially
  larger — it makes the event log carry reviewer prose. Not chosen; the split
  above delivers the invariant without changing what an event is for.

---

## R2 — Is #3157 a product defect?

**Decision**: No. It is a test that rots on a date. The product is correct and
must not be changed.

**Rationale**: Reproduced twice, independently. `reducer.py` sorts events by
`(e.at, e.event_id)`. The test hard-codes `at="2026-08-01T10:00:00+00:00"` on a
manually-appended `in_progress → for_review` event, while `start_implementation_status`
stamps wall-clock. Before 2026-08-01 the manual event sorted last and the WP
reduced to `for_review`; from that date it sorts between the seed and the live
events, the lane stays `in_progress`, and `start_review_status` correctly rejects.

Changing the literal to `2027-08-01` — **zero product code touched** — passes.

**Alternatives considered**: The issue itself offered "either the test's manual
event append is stale, or a real regression", and explicitly deferred the
investigation. Spec v1 assumed the latter and wrote an FR requiring
`start_review_status` to observe the recorded lane. Had it shipped, the shortest
compliant implementation would have widened the accepted lane set and deleted
`test_start_review_rejects_non_review_lane` — a real guard, removed to accommodate
a broken fixture.

---

## R3 — How wide is the date-rot class?

**Decision**: Ban the *mixture* of hard-coded and `now()`-generated event
timestamps in one event log. Do not ban the literal.

**Rationale**: Measured.

```
files with an absolute ISO date literal in tests/ : ~611  (~2061 occurrences)
files with absolute event ts (union)              : ~215-218   [reproducible]
  of those, ALSO producing runtime-now() events   :  ??        [NOT reproducible]
```

**Correction, recorded rather than quietly fixed.** The union figure reproduces
(215 on a re-measure, drift from test files this branch added). The "28" does
**not** — candidate classifier rules yield 12 (`∩ now(`), 10 (`∩ datetime.now`),
48 (`∩` status-emitter call) or 64 (`∩ CliRunner|_do_move_task`). No rule was
recorded alongside the number, so it cannot be re-derived.

The *direction* of the finding survives: a fixture whose events are all hard-coded
has stable relative order forever, so a literal ban is mostly false positives and
its allowlist would have exempted #3157 itself. But the ratio that quantified
"mostly" is unverified, and the classifier **is** IC-02's deliverable. IC-02 owns
deriving the rule, recording it, and reporting the true denominator — it must not
inherit an unreproducible number as a target.

**Alternatives considered**: Spec v2 additionally claimed a second live instance in
this mission's own #2646 fixture, and used "two is a class" as the justification.
That was checked by running the file: **2 passed**. Its events are all hard-coded,
so its order is stable. The claim is withdrawn. Two lenses had inferred it had
fired; one ran it. The run wins.

---

## R4 — How many readers, writers and resolvers are there?

**Decision**: Do not pin a number. Build the census check first and let it produce
the enumeration.

**Rationale**: Three successive counts were all wrong, and the reviewing lenses
disagreed with each other about how to count:

| Claimed | Actually found |
|---|---|
| 3 writers | ≥5 — including `arbiter._persist_in_artifact` and `_persist_standalone_json`, and the public `ReviewCycleArtifact.write` |
| 2 resolvers | 3–5 depending on whether raw `feature_dir/"tasks"/slug` joins count as one class or several |
| 5 frontmatter readers | ~16–20 modules |

The disagreement is itself the finding: "component" was never defined, so any
number is defensible and none is verifiable. A check that emits the census is the
only form of this requirement that a reviewer can re-run.

**Alternatives considered**: Naming the members in an appendix. Rejected — it
freezes a snapshot that drifts, and it still requires someone to have counted
correctly once.

---

## R5 — Where does verdict location resolution actually diverge?

**Decision**: The divergence is upstream of the directory resolver, in slug
derivation.

**Rationale**: `_resolve_wp_slug` matches only `stem.startswith(f"{task_id}-")` or
`stem == task_id`, and otherwise falls back to the bare task id:

```
WP01-durable-writer.md   -> WP01-durable-writer   (agrees)
WP01_durable_writer.md   -> WP01                  (DISAGREES with locate_work_package)
WP01.v2.md               -> WP01                  (DISAGREES)
```

Unifying `_review_cycle_wp_dir` alone therefore fixes nothing. Live on-disk proof
of the consequence exists in this repository: `slice-f-multi-context-extensibility-01KRX5C8/tasks/`
holds `WP03/arbiter-override-1.json` beside `WP03-contract-round-trip-gate/review-cycle-*.md`
— the arbiter's fallback wrote to a directory the real records do not live in.

**Alternatives considered**: Refusing non-hyphen filenames outright. Kept as a
sub-option within FR-007 (AC3), because a filename the system cannot resolve
unambiguously is better refused than silently degraded — but it cannot be the
whole answer, since existing repositories already contain such files.

---

## R6 — What does a damaged verdict record mean?

**Decision**: Every reader declares one of two polarities — refuse, or
skip-and-continue. No reader crashes uncaught; no safety gate fails open.

**Rationale**: Measured over one non-UTF-8 record:

| Reader | Behaviour |
|---|---|
| `agent_utils/status.py` (kanban) | returns `None` — **fail-open** |
| `review/cycle.py` provenance scan | skips and continues |
| `post_merge/review_artifact_consistency.py` | structured finding — **fail-closed** |
| `review/arbiter.py` | **uncaught crash** |

Four behaviours, not two. Note the correction: spec v2 claimed the merge gate
crashes. It does not — that was already fixed, and stating it wrongly would have
sent an implementer hunting a defect that is not there.

**Alternatives considered**: A single global polarity. Rejected — a provenance
scan legitimately skips an unreadable sibling (it cannot be the duplicate you are
looking for), while a merge gate legitimately refuses. The invariant is that the
polarity is *declared*, not that it is uniform.

---

## R7 — Can FR-002 be tested without building a new seam?

**Decision**: Yes. No new test infrastructure is required.

**Rationale**: `_do_move_task` resolves `_mt_execute` from module globals at call
time, so `monkeypatch.setattr(tasks_move_task, "_mt_execute", boom)` intercepts
cleanly — verified with a probe that produced `{"error": "index.lock held by a
concurrent agent"}` in the captured envelope. `TasksPorts` is a full DI bundle with
`FakeCoordCommitRouter` / `FakeGitOps` / `FakeFsReader` already in the suite, and
`test_move_task_approval_body_collision.py` is a ready-made harness to copy.

**Caveat carried into planning**: `FakeCoordCommitRouter` returns success
unconditionally, so a commit-failure variant needs a one-line configurable status.
That is a fixture change, not a seam.

---

## R8 — What is the real starting failure set?

**Decision**: Two failures, both pre-existing to `main`. Committed at
`research/baseline-8466727eb.md`.

**Rationale**: `2 failed, 2815 passed, 1 skipped, 2 xfailed` over the
affected-suites list at branch HEAD; merge-base confirmation run produced identical
node ids. Both are tracked (#3157, #3160).

**Consequence for NFR-001**: verification is a diff against that committed node-id
set, not a re-run nobody will perform over 2820 tests. Note also that
`tests/regression/test_2646_*.py` does **not exist** at the merge-base — it was
added by this branch — so no failure in it can ever be "retained as pre-existing".

---

## R9 — Why can this mission not measure itself today?

**Decision**: Sequence the CI shard fix early. It is a prerequisite, not P3 work.

**Rationale**: `fast-tests-review` is the only shard running `tests/review/` with
`--cov=src/specify_cli/review`, and it carries
`needs.fast-tests-status.result != 'failure'`. `fast-tests-status` is red from
#3157. So while the date-bomb stands, this mission's own primary write surface
produces no coverage XML, NFR-004's 90% gate is starved, and SC-009 is unverifiable
in CI. Five fast shards plus their integration counterparts are affected on every
push to the mainline.

**Alternatives considered**: Measuring coverage locally only. Viable as an interim
and recorded in the baseline document, but it leaves the gate blind for anyone
else's PR too — which is the cost #3157 has been imposing silently.
