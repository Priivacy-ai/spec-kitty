# Quickstart: Verifying Review Verdict Write Integrity

Manual verification steps for each requirement, for use during implementation and review.

## FR-001 — Approved-verdict persists

```bash
# 1. Reject a WP (writes review-cycle-1.md, verdict: rejected)
spec-kitty agent tasks move-task WP01 --to planned --review-feedback-file <feedback>.md --mission <slug>

# 2. Approve normally — no override flag
spec-kitty agent tasks move-task WP01 --to approved --mission <slug>

# 3. Confirm a real approved artifact exists
cat kitty-specs/<slug>/tasks/WP01-*/review-cycle-2.md
# Expect: verdict: approved, reviewer_agent: <real value>, cycle_number: 2

# 4. Confirm merge no longer blocks
spec-kitty merge --mission <slug> --dry-run
# Expect: no REJECTED_REVIEW_ARTIFACT_CONFLICT for WP01, and no --skip-review-artifact-check needed
```

## FR-002 — Fabrication/wrapping refused

```bash
# Path-identity case
spec-kitty agent tasks move-task WP02 --to planned \
  --review-feedback-file kitty-specs/<slug>/tasks/WP02-*/review-cycle-1.md --mission <slug>
# Expect: refused with a clear ReviewCycleError, no review-cycle-2.md written

# Content-identity (renamed copy) case
cp kitty-specs/<slug>/tasks/WP02-*/review-cycle-1.md /tmp/renamed-feedback.md
spec-kitty agent tasks move-task WP02 --to planned \
  --review-feedback-file /tmp/renamed-feedback.md --mission <slug>
# Expect: same refusal — detection is not defeated by the rename

# Regression pinning
pytest tests/review/test_cycle.py::test_self_referential_feedback_source_is_rejected \
       tests/review/test_cycle.py::test_new_cycle_body_never_duplicates_a_prior_cycle_file -v
# Expect: both PASS (they are RED on main before this mission's fix)
```

## FR-003 — Verify #2646 closes via FR-001 alone (verify-first, not a redesign)

```bash
# After FR-001 has landed — in a lanes_with_coord mission, reject then approve via the shipped writer:
spec-kitty agent tasks move-task WP01 --to planned --review-feedback-file <feedback>.md --mission <coord-slug>
spec-kitty agent tasks move-task WP01 --to approved --mission <coord-slug>
spec-kitty agent tasks status --mission <coord-slug> --json
# Expect: the WP reports no stale-verdict warning, with ZERO changes to src/specify_cli/agent_utils/status.py
# This is the verification research.md R3 requires before any status.py fix is considered.

# Flat/single-branch regression (must be unchanged either way)
spec-kitty agent tasks status --mission <flat-slug> --json
# Expect: identical behavior to pre-mission baseline

# Only if the coord-topology check above still shows a stale-verdict warning:
# design and implement a targeted fix against the actual observed mechanism, then re-run this checklist.
```

## FR-001's commit step (added post-plan)

```bash
# Immediately after either a rejection or an approval write:
git -C <repo_root> status --porcelain kitty-specs/<slug>/tasks/<wp-slug>/review-cycle-*.md
# Expect: no untracked/modified marker — the file is already committed by the writer itself
```

## Full regression surface

```bash
source .venv/bin/activate
pytest tests/review/ tests/post_merge/ tests/agent/ tests/regression/ -q
mypy --strict src/specify_cli/review/cycle.py src/specify_cli/review/artifacts.py \
     src/specify_cli/cli/commands/agent/tasks_move_task.py src/specify_cli/agent_utils/status.py
```
