# Quickstart — Operator Runbook

**Mission**: `investigate-canary-followups-1142-1141-01KS02TV`
**Audience**: Operator picking up the two investigations from spec.md / plan.md
**Time budget**: ≤ 1 operator-day if H1 confirms on #1142 and H4/H3 explains #1141

## Step 0 — Pre-flight (FR-008)

Verify the repo state matches the handoff snapshot:

```bash
cd /Users/robert/spec-kitty-dev/1122-1123-1124-43/spec-kitty   # or wherever your checkout lives

git status                                                      # expect: clean tree
git rev-list --left-right --count main...origin/main            # expect: 0 0  (after our two new commits land on origin, expect this to be 2 0 or 0 0)
git log --oneline -1                                            # expect HEAD to include this mission's spec/plan commits
git branch --list 'kitty/pr/unblock-sync-identity-boundary-canary-01KRZJ07-to-main'   # expect: present
gh pr list --repo Priivacy-ai/spec-kitty --state open --search "1143 OR 1154"          # expect: #1143 and #1154 still open (or document if either merged)
```

If `gh` returns "Missing required token scopes":

```bash
unset GITHUB_TOKEN && gh auth status   # fall back to keyring token (CLAUDE.md guidance)
```

## Step 1 — #1142 H1 (clean-venv repro, 10–15 min)

```bash
# 1. Snapshot the canonical issue body so you can compare hypotheses later
mkdir -p kitty-specs/investigate-canary-followups-1142-1141-01KS02TV/research
gh issue view 1142 --repo Priivacy-ai/spec-kitty --json title,body,labels,state \
  > kitty-specs/investigate-canary-followups-1142-1141-01KS02TV/research/issue-1142-snapshot.json

# 2. Fresh canary venv in a scratch dir
cd /tmp && rm -rf canary-clean && mkdir canary-clean && cd canary-clean
git clone https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing.git
cd spec-kitty-end-to-end-testing
python3 -m venv .venv && source .venv/bin/activate
pip install -e . 2>&1 | tee /tmp/h1-pip-canary.log

# 3. Install spec-kitty from THIS checkout (non-editable, no --force-reinstall)
pip install /Users/robert/spec-kitty-dev/1122-1123-1124-43/spec-kitty 2>&1 | tee /tmp/h1-pip-spec-kitty.log
spec-kitty --version

# 4. Re-run scenarios 1+2 only
pytest tests/identity_boundary/test_scenario_1_*.py tests/identity_boundary/test_scenario_2_*.py \
  -v --capture=no 2>&1 | tee /tmp/h1-run.log
```

**Interpretation**:
- **Green twice in a row** → H1 confirmed. Move to Step 2 (comment + close + follow-up update).
- **Red** → H1 ruled out. Move to Step 3 (#1142 H2 emitter walk).

## Step 2 — Post #1142 comment + close (FR-002, FR-003)

Author the comment per `contracts/issue-comment-shape.md`. Save it to `research/comment-1142.md` first so you have an audit trail:

```bash
# Edit research/comment-1142.md filling in Hypothesis / Commands / Evidence / Conclusion / Fix-pattern
gh issue comment 1142 --repo Priivacy-ai/spec-kitty --body-file kitty-specs/investigate-canary-followups-1142-1141-01KS02TV/research/comment-1142.md

# If H1 CONFIRMED + closing:
gh issue close 1142 --repo Priivacy-ai/spec-kitty --reason completed
```

Capture the resulting comment URL — it goes in the follow-up row (Step 6).

## Step 3 — #1142 H2 (emitter walk, ~30–60 min, only if H1 red)

Open each emitter file and verify every `aggregate_type=...` call satisfies the WP01 predicate (`aggregate_type == "Mission"` AND `event_type` non-empty):

```
src/specify_cli/status/lifecycle_events.py          (lines 410, 459, 521 already audited in research.md R3)
src/specify_cli/invocation/propagator.py
src/specify_cli/dossier/                            (whole package)
src/specify_cli/next/_internal_runtime/engine.py
src/specify_cli/retrospective/events.py
```

If any emitter produces a row that does NOT match the predicate, open a 1-WP follow-up mission (don't fix in this mission — C-003). Set `follow_up_mission_slug` in the outcome record.

If all emitters match, advance to H3 per the issue body.

## Step 4 — #1141 hypothesis sweep (H4 → H3 → H2 → H1, in order)

```bash
# Snapshot the issue body
gh issue view 1141 --repo Priivacy-ai/spec-kitty --json title,body,labels,state \
  > kitty-specs/investigate-canary-followups-1142-1141-01KS02TV/research/issue-1141-snapshot.json

# Inspect the scenario file end-to-end
cd /tmp/canary-clean/spec-kitty-end-to-end-testing
$EDITOR tests/identity_boundary/test_scenario_4_review_rejection_contract.py
```

Walk hypotheses cheapest-first:

| # | Check | Where |
|---|---|---|
| H4 | Does the fixture actually reach `in_review`? | the fixture function near top of `test_scenario_4_review_rejection_contract.py` |
| H3 | Is the peek-the-queue assertion racing the `move-task` write? | canary line 543 |
| H2 | Does `WPStatusChanged` payload shape match current spec-kitty emission? | compare against `src/specify_cli/status/lifecycle_events.py` + `src/specify_cli/status/store.py` |
| H1 | Recent backward-transition emission changes? | `git log --oneline -- src/specify_cli/status/store.py src/specify_cli/cli/commands/agent/tasks.py` |

Stop at the first hypothesis that explains the failure.

## Step 5 — Post #1141 comment (FR-006)

Same structure as Step 2, but the comment MUST include an `### Recommendation` heading with A / B / C per `contracts/issue-comment-shape.md`. #1141 is NOT closed by this mission unless the recommendation is C and the issue body already shows the small fix landed.

## Step 6 — Update mission-exception.md `## Follow-up` (FR-007)

Per `contracts/follow-up-update-shape.md`. The default branch is the focused-PR branch:

```bash
# From repo root
git fetch origin
git checkout kitty/pr/unblock-sync-identity-boundary-canary-01KRZJ07-to-main
git pull --ff-only

# Edit kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/mission-exception.md
# Update the ## Follow-up section per the contract

git add kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/mission-exception.md
git commit -m "$(cat <<'EOF'
Record outcome of #1142 / #1141 follow-up commitments

Investigation: investigate-canary-followups-1142-1141-01KS02TV
Result: <one-line summary>
EOF
)"
git push origin kitty/pr/unblock-sync-identity-boundary-canary-01KRZJ07-to-main

# Return to mission branch
git checkout main
```

**If PR #1143 has merged** (branch deleted from origin), use the fallback path:

```bash
git checkout main
git pull --ff-only
git checkout -b chore/record-canary-followup-outcome
# Edit the file on main; commit; push; open PR
```

## Step 7 — Window-deadline reporting (NFR-001 / NFR-002)

Even if investigation continues past one hypothesis, you MUST post a substantive comment inside each issue's window:

- #1142 substantive comment by **2026-05-26 (UTC end-of-day)**
- #1141 substantive comment by **2026-06-02 (UTC end-of-day)**

When `conclusion == INCONCLUSIVE_IN_WINDOW`, use the inconclusive-in-window row shape from `contracts/follow-up-update-shape.md`.

## Step 8 — Done

This mission's acceptance checklist (NFR-001/002/003 + FR-002/003/006/007) is satisfied. Run the standard `spec-kitty` acceptance flow when ready to move toward merge.
