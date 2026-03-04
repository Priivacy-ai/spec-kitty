# Blocked State Recovery Patterns

Reference for diagnosing and recovering from blocked runtime states.

## Pattern 1: Unmet WP Dependencies

**Symptom:** `spec-kitty next` returns `kind: "blocked"` with `reason` describing unmet dependencies and `guard_failures` listing specific guards that failed.

**Diagnosis:**

```bash
# Check which WPs are blocking
spec-kitty agent tasks status --feature <feature-slug>

# Check specific WP dependencies
grep 'dependencies:' kitty-specs/<feature>/tasks/WP##-*.md
```

**Recovery:**
1. Identify the upstream WP that is not yet done
2. If it is in `planned`: implement it first
3. If it is in `doing`: wait for the implementing agent to complete
4. If it is in `for_review`: run the review to unblock

## Pattern 2: Review Feedback Not Addressed

**Symptom:** A WP is in `planned` lane with `review_status: has_feedback`. The mission cannot advance because this WP's changes were rejected.

**Diagnosis:**

```bash
# Check review status
grep 'review_status:' kitty-specs/<feature>/tasks/WP##-*.md
```

**Recovery:**
1. Read the Review Feedback section in the WP prompt file
2. Re-implement to address all feedback items
3. Move WP back to `for_review`
4. Re-run the review

## Pattern 3: Stale Agent

**Symptom:** A WP is in `doing` lane but no agent is actively working on it. `shell_pid` refers to a dead process.

**Diagnosis:**

```bash
# Check if the implementing process is still alive
PID=$(grep 'shell_pid:' kitty-specs/<feature>/tasks/WP##-*.md | awk '{print $2}' | tr -d '"')
kill -0 "$PID" 2>/dev/null && echo "alive" || echo "stale"
```

**Recovery:**
1. Move the WP back to `planned`:
   ```bash
   spec-kitty agent tasks move-task WP## --to planned --force --note "Reclaimed from stale agent"
   ```
2. Check the worktree for partial work worth keeping
3. Re-dispatch implementation

## Pattern 4: Missing Feature Artifacts

**Symptom:** Runtime cannot find spec, plan, or task files for the active feature.

**Diagnosis:**

```bash
ls kitty-specs/<feature-slug>/
```

**Recovery:**
1. If artifacts are missing: re-run the planning workflow (`/spec-kitty.specify`, `/spec-kitty.plan`, `/spec-kitty.tasks`)
2. If artifacts exist but are corrupted: restore from git history
3. If the feature directory is entirely absent: check that you are on the correct branch

## Pattern 5: Circular Dependencies

**Symptom:** `spec-kitty next` returns `blocked` but no clear linear path exists to unblock any WP.

**Diagnosis:**
The dependency graph has a cycle. This should have been caught by `finalize-tasks`.

**Recovery:**
1. Review the dependency declarations in WP frontmatter
2. Break the cycle by removing one dependency that is not strictly required
3. Re-run `spec-kitty agent mission finalize-tasks` to validate

## Pattern 6: All WPs Done But Mission Not Complete

**Symptom:** All WPs are in `done` lane but `spec-kitty next` does not return `kind: "terminal"`.

**Diagnosis:**
The mission state machine may require additional steps beyond WP completion (e.g., acceptance validation, merge).

**Recovery:**
1. Run `/spec-kitty.accept` to check acceptance criteria
2. If acceptance passes: run `/spec-kitty.merge` to complete the mission
3. If acceptance fails: create additional WPs to address gaps
