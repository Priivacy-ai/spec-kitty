# WP03 Review — Cycle 1 — CHANGES REQUESTED

Reviewer: reviewer-renata (opus). Verdict: **REJECT** on one blocking issue.

The extraction is very clean and almost everything passes. The single blocker is a
**real, reachable, observable parity break** that the WP's own contract (FR-004 /
NFR-001, "reproduce, do not unify") does not permit to ship silently. It is
currently **undocumented** in code, WP, or spec — the core docstring even asserts
"Nothing here reconciles or unifies behaviour," which is false for this edge.

---

## BLOCKER — partial-write-on-refusal timing change (side effects deferred to `Emit`)

**What changed.** In the ORIGINAL `move_task` the two proceed-side effects fire
*during* the guard sequence, before later guards run:

- **Override-persist** (`_persist_review_artifact_override` +
  `_persist_review_artifact_override_in_coord`) fires inside the rejected-verdict
  guard's proceed arm — OLD `tasks.py:1202–1220` — which sits at guard position 5,
  **before** feedback-file, subtasks, review-currency, done-ancestry and
  issue-matrix guards.
- **Arbiter-persist** (`persist_arbiter_decision`) fires OLD `tasks.py:1430`,
  **before** the issue-matrix guard OLD `tasks.py:1449–1465`.

In the NEW wiring both fire only *after* `decide_transition` returns an `Emit`,
i.e. after **all** guards clear (NEW `tasks.py:1400–1415` override, `1440–1449`
arbiter). So a call that OLD would service as "persist artifact, THEN a later
guard refuses (exit 1)" now refuses **without** the persist.

**Reachable.** Override authorization depends only on early facts
(`review_verdict==rejected`, `review_artifact_name`, `skip_review_artifact_check`,
non-empty `note`, target in {approved,done}). Guards 8/9/10/11 can still refuse
after it. Concrete inputs that flip:

- `move-task WP0x --to done --skip-review-artifact-check --note "<r>"` on a
  code_change WP with a rejected latest artifact, **unmerged lane**, and **no**
  `--done-override-reason` → OLD stamps the override into the artifact then the
  done-ancestry guard refuses (exit 1); NEW refuses clean. (Very common: forgot
  `--done-override-reason`.)
- `move-task WP0x --to approved --skip-review-artifact-check --note "<r>"` with a
  rejected artifact **and uncommitted changes** (`_validate_ready_for_review`
  invalid) → OLD stamps override then review-currency refuses; NEW refuses clean.
- Same shape with an issue-matrix blocker, or with unchecked subtasks (no
  `--force`) → OLD stamps override then guard 11/8 refuses.
- Arbiter: a force forward-from-planned move to approved/done that is an arbiter
  override **and** hits an issue-matrix blocker → OLD writes the
  `arbiter-override-*.json` then refuses; NEW refuses clean.

**Observable.** `_persist_review_artifact_override`
(`tasks_materialization.py:46`) writes `review_artifact_override_*` frontmatter
into the review artifact file on disk via `write_text_within_directory`; the
`_in_coord` twin writes/commits the coord copy; `persist_arbiter_decision` writes
a JSON decision file. These are durable filesystem/coord mutations that survive
the exit-1 and are visible to a subsequent run and to the merge gate. This is a
persisted-side-effect divergence, not a cosmetic one.

**Not #2300.** #2300 defers the *skip-vs-refuse* divergence. This partial-write
timing change is a **new** divergence introduced by this refactor, not a
pre-existing one being carried forward.

**Feasible to reproduce (so the waiver escape does not apply).** The override
decision is computable from early facts alone — you can compute
`_authorize_review_override(_request)` from the pass-1 request and fire the
persist right after gathering the rejected-verdict facts, *before* running the
rest of the guard sequence, exactly matching OLD timing. This does **not** touch
the two-pass late-fact machinery (which only defers done-ancestry/issue-matrix)
and does **not** re-introduce the `test_force_done_blocked_by_rejected_verdict`
ordering bug. The same applies to the arbiter-persist (fire it before computing
the issue-matrix blocker).

### Required fix (choose one, explicitly)

1. **Reproduce the OLD timing (preferred).** Fire the override-persist in the
   shell immediately after the rejected-verdict facts are gathered (before the
   guard sequence / pass 1), and fire the arbiter-persist before the issue-matrix
   fact is computed — so a later-guard refusal still leaves the OLD partial write.
   Add a red-first test asserting the artifact carries the override frontmatter
   even when a later guard (e.g. done-ancestry) refuses exit 1. Keep the pure core
   as the decision authority; only the *ordering of the shell's side-effect
   execution* moves. Correct the core docstring's "Nothing here reconciles or
   unifies behaviour" claim.

OR

2. **Waive explicitly.** If you judge faithful reproduction infeasible, file a
   #2300-style deferred-edge follow-up issue, reference it in this WP prompt AND
   in `spec.md` (FR-004 note), and add a comment at the two persist sites naming
   the accepted divergence. Not acceptable to leave it undocumented.

---

## Everything else — PASS (recorded for the next cycle)

- **Purity (NFR-001):** `decide_transition` / helpers do no filesystem/git/emit/
  clock I/O — grep clean (only `emit_*` variable-name substrings).
- **Two-pass soundness:** decide is pure → no side effect fires twice across the
  two `decide_transition` calls (side effects run once, after the final
  decision); guards 1–9 consume only early facts so both passes agree; late-fact
  guards (done-ancestry, issue-matrix) correctly deferred via skip-defaults.
  `test_force_done_blocked_by_rejected_verdict` passes; no test weakened/xfailed.
- **Inline block deleted, not shadowed:** the 4 inline guard error fragments +
  AGENT OWNERSHIP WARNING are gone from `tasks.py`; `decide_transition` drives the
  live path; `Emit.skip_primary` (not the raw fact) drives the WP-file-commit skip
  and the `--json` envelope.
- **Sentinel (T017):** non-tautological — monkeypatched fake core flips exit code
  and the `--json` `wp_file_update` envelope. Genuine drive proof.
- **Coverage:** `--cov-branch` 99% on the module; the 2 uncovered partials
  (390→392, 457→461) are genuinely unreachable via `decide_transition` (force
  makes review_ready True; done-ancestry already refused when override_reason
  absent). Verified, not taken on faith.
- **Parity:** WP01 golden `test_tasks_cli_contract.py` 42 byte-identical; WP02
  `test_tasks_ports.py` 19 green (FR-010 :1138 hazard intact); broader
  `tests/specify_cli/cli/commands/agent/` 851 passed / 2 xfailed.
- **NFR-003:** mypy strict clean on core + test + wired `tasks.py`; ruff clean;
  zero `# noqa` / `# type: ignore` added.
- **C-003:** selector/handle ambiguity still raises (issue-matrix canonicalizer
  fold retained inline); skip-vs-refuse divergence preserved (not reconciled).

Re-request review after the timing fix (or the documented waiver) lands.
