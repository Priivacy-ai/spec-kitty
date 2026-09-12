# Quickstart: verifying the trusted commit path

## Run the live #2861 causation repro FIRST (NFR-002 / D-B)

```bash
# In a real coord-topology mission fixture (see tests/regression/test_issue_2508.py builder):
spec-kitty agent action review WP01 --mission <slug> --agent claude:opus:reviewer-renata:reviewer
# Record the failure mode: SafeCommitHeadMismatch / "[refused]"  => FR-002 misroute (the blocker)
#                          actor "invalid value" warning only    => FR-006 (non-fatal SaaS fanout)
```

## Run the real-repo e2e (NFR-001)

```bash
# Reuses the un-stubbed real-git harness (real git init + real git worktree add).
PWHEADLESS=1 uv run --extra test pytest tests/regression/test_coord_commit_integrity_e2e.py -q
# Asserts (via git show <ref>:<path>, not filesystem state):
#   - status.events.jsonl exists on the coord branch, absent on target
#   - review-cycle-N.md exists on the target (PRIMARY), absent on coord
#   - analysis-report.md exists on the target (PRIMARY, re-homed), NO coord copy
#   - negative: safe_commit(worktree_root != destination_ref) raises SafeCommitHeadMismatch
```

## Check coord staleness

```bash
spec-kitty doctor coordination --check-staleness            # non-blocking report
spec-kitty doctor coordination --fix                        # fast-forwards ONLY if strict-ancestor + clean
# diverged / dirty  => fails loud with a unified diff, mutates nothing
```

## Gate exemption (Symptom B)

```bash
# A bulk-edit/review diff touching the mission's own status.events.jsonl passes with NO occurrence_map entry;
# a non-runtime file (or another mission's runtime file) under the same feature_dir still classifies.
```

## Acceptance validation

1. Live repro classifies the #2861 block as the FR-002 seam (or not) — recorded before FR-005/006 lands.
2. Real-repo e2e green: coord artifacts on coord, PRIMARY artifacts (incl. re-homed analysis-report) on
   target, no residue, mis-placed write unrepresentable.
3. `assert_partition_invariant` green after the re-home; coord-less topologies still commit correctly.
4. `doctor coordination --fix` fast-forwards only when safe; else fails loud.
5. `ruff` + `mypy --strict` clean on touched modules; complexity ≤15; no new suppressions.
