---
name: spec-kitty-runtime-review
description: >-
  Review runtime-owned outputs with doctrine and glossary checks, then direct
  approval or retry.
  Triggers: "review this work package", "check runtime output", "approve this step",
  "review WP", "is this WP ready to approve", "check this implementation".
  Does NOT handle: setup-only repair requests, direct implementation work,
  editorial glossary maintenance, or runtime loop advancement.
---

# spec-kitty-runtime-review

Review work-package outputs produced by the runtime, apply doctrine and glossary
consistency checks, classify findings by severity, and direct approval or
rejection with actionable feedback.

## When to Use This Skill

- Review a completed work package before approval
- Check whether runtime output satisfies acceptance criteria
- Validate doctrine and glossary compliance of implementation artifacts
- Decide whether to approve or reject a WP with structured feedback

## Step 1: Load Doctrine Context

```bash
spec-kitty constitution context --action review --json
```

Use the returned JSON `text` as governance context. Note the glossary terms and
constitution rules that apply to this review.

---

## Step 2: Claim the Work Package

```bash
# Claim a specific WP (or omit WP## to auto-select from for_review lane)
spec-kitty agent workflow review WP## --agent <your-name>
```

This moves the WP from `for_review` to `doing` and prints the path to a
generated review prompt file (read the path from the command output).

---

## Step 3: Inspect Changes

```bash
# Read the review prompt (use the path printed by the workflow command)
cat <prompt-file-path>

# Check WP status
spec-kitty agent tasks status
```

The review prompt includes the correct git diff commands with the resolved base
branch (which may differ from `main` on stacked worktrees). Use those commands
rather than hardcoding `main`:

```bash
# Use the diff commands from the review prompt — they reference the correct base
cd .worktrees/<feature>-WP##/
git log <base-branch>..HEAD --oneline
git diff <base-branch>..HEAD --stat
```

Extract from the prompt: acceptance criteria, required deliverables, and
dependency declarations. Verify the diff addresses every criterion and contains
no unrelated changes.

---

## Step 4: Apply Doctrine, Glossary, and Acceptance Checks

Work through `references/review-checklist.md` systematically. Key areas:

**Acceptance criteria** -- Compare each criterion line-by-line against the diff.
Every criterion must have a corresponding change.

**Doctrine compliance** -- Check architecture patterns, naming conventions, and
constitution rules loaded in Step 1.

**Glossary consistency** -- Verify public-facing surfaces (CLI flags, API names,
documentation, user messages) use glossary terms precisely. Internal code has
more latitude.

---

## Step 5: Classify Findings

Every finding must be classified. See `references/review-severity-rubric.md`
for the complete rubric.

| Severity | Criteria | Effect |
|----------|----------|--------|
| **Blocking** | Acceptance criteria unmet, doctrine violation, broken tests, missing deliverables | Must reject |
| **Non-blocking** | Style preferences, internal naming, optional improvements | Can approve; note for future |

Key distinctions: glossary misuse in a public API is blocking; in an internal
comment it is non-blocking. A missing deliverable is always blocking. Suggested
test coverage beyond requirements is non-blocking.

---

## Step 6: Direct Approval or Rejection

Take exactly one action -- never "approve with conditions".

### Approve (no blocking findings)

```bash
spec-kitty agent tasks move-task WP## --to approved --note "Review passed: <summary>"
```

### Reject (blocking findings exist)

```bash
# Write structured feedback to a temp file
cat > "$(mktemp)" << 'FEEDBACK'
## Blocking Findings
1. **[Category]**: <what is wrong and why it blocks>

## Non-Blocking Findings
1. **[Category]**: <suggestion>

## Required Actions
- [ ] <specific, verifiable remediation for each blocking finding>
FEEDBACK

# Move back to planned with feedback
spec-kitty agent tasks move-task WP## --to planned --force --review-feedback-file <feedback-file-path>
```

Every blocking finding must map to a Required Actions item. Actions must be
specific and verifiable.

---

## Step 7: Check Downstream Impact

If you rejected and the WP has downstream dependents, warn those agents:

```bash
spec-kitty agent tasks status --feature <feature-slug>
```

Note dependent WPs and include a rebase warning in your feedback.

---

## Review Precedence Rules

1. **Acceptance criteria are the primary gate** -- a WP meeting all criteria
   passes even if the reviewer would have done it differently
2. **Doctrine violations block only when they contradict explicit rules** --
   not unstated preferences
3. **Glossary checks are strict for public surfaces, advisory for internals**
4. **The reviewer does not implement fixes** -- feedback must be actionable by
   the original implementing agent
5. **One clear verdict per review** -- approve or reject, nothing in between

## References

- `references/review-severity-rubric.md` -- Severity classification rules with examples
- `references/review-checklist.md` -- Structured checklist for doctrine and glossary validation
