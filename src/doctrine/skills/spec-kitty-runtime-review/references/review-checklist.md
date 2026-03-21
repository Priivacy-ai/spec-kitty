# Runtime Review Checklist

Structured checklist for reviewing runtime-owned work package outputs. Work
through each section in order. Record findings with their severity (blocking or
non-blocking) as defined in `review-severity-rubric.md`.

---

## 1. Claim and Context

- [ ] Loaded doctrine context: `spec-kitty constitution context --action review --json`
- [ ] Claimed WP for review: `spec-kitty agent workflow review WP## --agent <name>`
- [ ] Read the review prompt at the generated path
- [ ] Identified the feature slug and WP ID under review
- [ ] Noted the mission type (software-dev, documentation, research)

## 2. Acceptance Criteria Gate

For each acceptance criterion in the WP frontmatter:

- [ ] Criterion is addressed by changes in the diff
- [ ] Implementation matches the criterion's intent (not just surface wording)
- [ ] Any quantitative requirements are met (counts, thresholds, coverage)

**Verdict:** All criteria met? If any criterion is unmet, the finding is
**blocking**.

## 3. Deliverable Completeness

Cross-reference the WP deliverable list against the diff:

- [ ] Every listed file or artifact exists in the diff
- [ ] No deliverable is an empty stub or placeholder
- [ ] File paths match what the WP specified

**Verdict:** All deliverables present? If any is missing, the finding is
**blocking**.

## 4. Doctrine Compliance

Check the changes against constitution rules loaded in section 1:

- [ ] Architecture patterns respected (module boundaries, layering)
- [ ] Coding standards followed (naming conventions, formatting rules)
- [ ] API conventions adhered to (response format, error handling)
- [ ] Security and safety rules applied (no secrets in code, input validation)

**Verdict:** Any explicit doctrine rule violated? If yes, the finding is
**blocking**.

## 5. Glossary Consistency

Check public-facing surfaces against the project glossary:

- [ ] CLI flags and help text use glossary terms
- [ ] API endpoint names and response keys use glossary terms
- [ ] User-visible messages and errors use glossary terms
- [ ] Documentation uses glossary terms
- [ ] No new jargon introduced that contradicts existing definitions

**Verdict:** Glossary misuse in public surface? If yes, the finding is
**blocking**. Misuse in internal code only is **non-blocking**.

## 6. Functional Correctness

Verify the implementation works:

- [ ] Existing test suite passes in the worktree
- [ ] New tests (if any) pass
- [ ] No obvious regressions in related functionality
- [ ] Error paths handled (not just the happy path)

**Verdict:** Tests failing or regressions found? If yes, the finding is
**blocking**.

## 7. Dependency Validation

Check the WP's relationship to other work packages:

- [ ] All upstream dependencies (listed in `dependencies:` frontmatter) are
      in `done` lane or merged to main
- [ ] Code dependencies match declared WP dependencies (imports, shared
      modules, API contracts)
- [ ] If rejecting: identified downstream WPs that will need to rebase

## 8. Doctrine Consistency Examples

Common doctrine-consistency patterns to check:

**Naming patterns:**
- If the constitution defines a naming convention for test files
  (e.g., `test_<module>.py`), verify new test files follow it
- If the glossary defines "work package" (not "task", "ticket", or "item"),
  verify public surfaces use "work package"

**Structural patterns:**
- If the constitution separates concerns into layers (e.g., CLI / core / data),
  verify new code lands in the correct layer
- If the constitution requires new features to have corresponding tests,
  verify tests exist

**Documentation patterns:**
- If the constitution requires changelog entries for user-facing changes,
  verify a changelog entry exists
- If the constitution requires docstrings on public functions, verify
  coverage

## 9. Final Verdict

Compile all findings and classify:

- [ ] Listed all blocking findings with required remediation actions
- [ ] Listed all non-blocking findings as suggestions
- [ ] Chose exactly one outcome: **approve** or **reject**

### If approving:

```bash
spec-kitty agent tasks move-task WP## --to done --note "Review passed: <summary>"
```

### If rejecting:

```bash
# Write feedback to temp file
cat > /tmp/feedback.md << 'FEEDBACK'
## Blocking Findings

1. **[Category]**: <description>

## Non-Blocking Findings

1. **[Category]**: <description>

## Required Actions

- [ ] <specific remediation for each blocking finding>
FEEDBACK

# Move back to planned with feedback
spec-kitty agent tasks move-task WP## --to planned --force --review-feedback-file /tmp/feedback.md
```

## 10. Post-Review

- [ ] If rejected and WP has downstream dependents, warned those agents
      about upcoming rebase requirement
- [ ] Confirmed WP lane updated correctly: `spec-kitty agent tasks status`
