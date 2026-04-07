# Quickstart: Post-Merge Reliability And Release Hardening

**Mission**: 068-post-merge-reliability-and-release-hardening
**Audience**: Spec Kitty maintainers verifying the mission's behavior changes

This quickstart walks through every new and modified surface introduced by mission 068. Each section corresponds to one or more WPs and points at the FR(s) it exercises.

---

## Prereqs

- A local clone of `Priivacy-ai/spec-kitty` checked out to `main` after the mission lands
- Python 3.11+ with the project installed in editable mode (`pip install -e .` or `pipx install --force --pip-args="--pre" spec-kitty-cli`)
- A clean working tree (`git status` empty)

---

## 1. Verify FR-019: status events survive a merge rebuild

This is the bug that motivated the mission. Reproduce-then-verify-fix:

```bash
# 1. Pick a synthetic mission (or use the integration test fixture)
cd /tmp && rm -rf demo-068 && git init demo-068 && cd demo-068
spec-kitty init --agent claude
spec-kitty agent mission create "demo" --json | jq -r '.feature_dir'

# ... walk through specify/plan/tasks/implement/review for two synthetic WPs ...

# 2. Run the merge
spec-kitty merge --feature 001-demo

# 3. Verify the done events are committed in git, not just on disk.
#    `git show HEAD:` reads from committed state, not the working tree —
#    this is the authoritative answer to "is this file's state durable in git?"
git show HEAD:kitty-specs/001-demo/status.events.jsonl | grep '"to_lane": "done"'
# Expected: at least one matching line per WP
```

**Before the fix**, step 3 would have failed: `git show HEAD:kitty-specs/001-demo/status.events.jsonl` would either error (the file was never tracked) or return content with zero `done` entries (the events were written to the working tree but never staged or committed). After FR-019, `safe_commit` runs after the mark-done loop and the events are present in `HEAD`.

> **Why no `git reset --hard HEAD`**: `git show HEAD:` reads from committed state, not the working tree — that is already the authoritative check. Resetting the working tree to HEAD first and then re-running `git show HEAD:` produces the same result either way; the step proves nothing. The mechanically-correct regression test for FR-019 is in `tests/cli/commands/test_merge_status_commit.py` and it asserts `git show HEAD:` directly, no reset needed.

---

## 2. Verify FR-005..FR-009: --strategy is honored end-to-end

```bash
# Default behavior: squash for mission→target
spec-kitty merge --feature 001-demo
git log -1 --pretty=format:'%P' main  # Expected: single parent (squash commit, not merge commit)

# Explicit override: merge commit
spec-kitty merge --feature 002-demo --strategy merge
git log -1 --pretty=format:'%P' main  # Expected: two parents (merge commit)

# Project-level config
echo -e "merge:\n  strategy: rebase" >> .kittify/config.yaml
spec-kitty merge --feature 003-demo
# Expected: rebase semantics, no merge commit

# Push-rejection remediation hint (FR-009)
# Configure a protected branch with linear history, then:
spec-kitty merge --feature 004-demo --strategy merge
# Expected: push fails with "linear history" error; spec-kitty emits a hint
# pointing at `--strategy squash` and the `merge.strategy` config key
```

---

## 3. Verify FR-001..FR-004: stale-assertion analyzer

```bash
# Run the analyzer directly via the new CLI subcommand
spec-kitty agent tests stale-check --base main~5 --head main

# Expected output (text mode):
#   Stale-assertion analyzer
#   Base: main~5  Head: main
#   Files scanned: <N>
#   Findings: <K>
#
#   tests/some_test.py:42  high  function `do_thing` was renamed to `perform_thing` in src/foo.py:12
#   tests/other_test.py:88 low   string literal "old name" matched a Constant in an assertion

# JSON mode
spec-kitty agent tests stale-check --base main~5 --head main --json | jq '.findings[0]'

# Confirm the analyzer fires inline with the merge runner
spec-kitty merge --feature 001-demo
# Expected: the merge summary includes a "Stale assertion findings" block at the end
```

**FR-022 self-monitoring**: if the false-positive ceiling (NFR-002, ≤ 5/100 LOC) is exceeded on the curated benchmark, the test suite fails the build and surfaces the FR-022 narrowing path.

---

## 4. Verify FR-013..FR-023: release-prep CLI

```bash
# Text mode
spec-kitty agent release prep --channel alpha
# Expected output:
#   Release Prep
#   Current version: 3.1.0a7
#   Proposed version: 3.1.0a8
#   Channel: alpha
#   Missions included: 068-post-merge-reliability-and-release-hardening
#
#   ## Changelog draft
#   ### 068 — Post-Merge Reliability And Release Hardening
#   - WP01: ...
#   - WP02: ...
#   ...
#
#   ## Structured inputs (for the release tag/PR workflow)
#   <table>

# JSON mode
spec-kitty agent release prep --channel alpha --json | jq '.proposed_version'
# Expected: "3.1.0a8"

# Beta channel
spec-kitty agent release prep --channel beta --json | jq '.proposed_version'
# Expected: "3.1.0b1"

# Stable channel
spec-kitty agent release prep --channel stable --json | jq '.proposed_version'
# Expected: "3.1.0"
```

**FR-014 confirmation**: run the command with `unset GITHUB_TOKEN && spec-kitty agent release prep --channel alpha` and confirm it succeeds without any network access.

---

## 5. Verify FR-021: post-merge unblocking (Scenario 7)

```bash
# Set up a synthetic mission with a dependency chain WP01..WP06
# (using the integration test fixture is easier than walking through manually)

# Implement and merge WP01..WP05; their lane branches are deleted by post-merge cleanup
spec-kitty merge --feature 001-chain  # merges WP01..WP05

# Now try to start WP06 — the bug case is that scan_recovery_state finds nothing
# because the dependency lane branches were merged-and-deleted
spec-kitty implement WP06 --base main

# Expected (after FR-021): a fresh lane workspace is created from main's tip,
# WP06 starts normally, no manual .kittify/ edits required

# Verify the recovery scanner now sees the merged-deleted state
spec-kitty doctor recovery --feature 001-chain
# Expected: WP01..WP05 reported as `merged_and_deleted`, WP06 reported as
# `ready_to_start_from_target`
```

---

## 6. Verify the diff-coverage policy (WP03)

WP03 is verification-first. The deliverable is a written report, then a fork.

```bash
# Read the WP03 validation report
cat kitty-specs/068-post-merge-reliability-and-release-hardening/wp03-validation-report.md

# Two possible decisions:
# - close_with_evidence: current ci-quality.yml already satisfies the policy intent;
#   #455 closed with this report linked
# - tighten_workflow: ci-quality.yml was modified; the diff is the evidence
git log --oneline -- .github/workflows/ci-quality.yml
```

---

## 7. Verify the mission close ledger

```bash
cat kitty-specs/068-post-merge-reliability-and-release-hardening/mission-close-ledger.md
# Expected: a markdown table with one row per issue from the spec's
# Tracked GitHub Issues table (#454, #455, #456, #457, #415, #416)
# Plus a section for any carve-outs filed as follow-ups
```

This is the DoD-4 mechanically-checkable artifact: every tracked issue must have exactly one row.

---

## Test execution

```bash
# Run the new mission's test suite
PWHEADLESS=1 pytest tests/post_merge tests/cli/commands/test_merge_strategy.py \
                    tests/cli/commands/test_merge_status_commit.py \
                    tests/cli/commands/test_implement_base_flag.py \
                    tests/lanes/test_recovery_post_merge.py \
                    tests/cli/commands/agent/test_release_prep.py \
                    tests/cli/commands/agent/test_tests_stale_check.py

# Expected: all green, NFR-001/NFR-004 benchmarks within budget
```

---

## Acceptance gates

The mission is verified complete when:

- ✅ Section 1: status events visible in `git show HEAD:` after a merge
- ✅ Section 2: `--strategy` and `merge.strategy` config key both honored end-to-end
- ✅ Section 3: stale-assertion analyzer produces findings via both CLI and merge runner
- ✅ Section 4: `spec-kitty agent release prep --channel alpha --json` produces a valid payload
- ✅ Section 5: `spec-kitty implement WP06 --base main` succeeds in the post-merge unblocking scenario
- ✅ Section 6: WP03 validation report exists with a documented decision
- ✅ Section 7: mission close ledger has one row per tracked issue
- ✅ Test suite green
