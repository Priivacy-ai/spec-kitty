# Review Severity Rubric

Reference for classifying review findings as blocking or non-blocking.

---

## Blocking Findings

A finding is **blocking** when it prevents the work package from being approved.
The WP must be rejected and the implementing agent must address all blocking
findings before re-submission.

### Category 1: Acceptance Criteria Not Met

A required deliverable is missing, incomplete, or does not satisfy the acceptance
criterion as written in the WP frontmatter.

**Examples:**

- WP requires "add validation for email input" but no validation logic exists
- WP requires "update API endpoint to return 404" but endpoint still returns 500
- WP requires "create migration script" but no migration file is present

**Decision rule:** Compare each acceptance criterion line-by-line against the
diff. If any criterion has no corresponding change, it is blocking.

### Category 2: Doctrine Violation

The output contradicts an explicit rule in the project constitution or doctrine
context loaded via `spec-kitty constitution context --action review --json`.

**Examples:**

- Constitution says "all API responses use snake_case keys" but new endpoint
  uses camelCase
- Doctrine requires "no direct database queries in route handlers" but the WP
  adds a raw SQL call in a handler
- Constitution mandates "all public functions have docstrings" but new public
  functions lack them

**Decision rule:** The violated rule must be explicitly documented in the
constitution or doctrine context. Unstated preferences are not blocking.

### Category 3: Glossary Term Misuse in Public Surface

A glossary term is used incorrectly in a public-facing artifact (API name,
user-visible message, documentation, CLI flag).

**Examples:**

- Glossary defines "workspace" but the new CLI flag uses "--worktree" in
  user-facing help text
- Glossary defines "work package" but documentation refers to "task bundle"
- Glossary defines "feature" but API endpoint uses "/projects/" for the same
  concept

**Decision rule:** The term must appear in the project glossary, the misuse must
be in a public-facing surface (not internal code comments), and the correct term
must be clear.

### Category 4: Broken Functionality

Tests fail, the build breaks, or the implementation introduces a regression.

**Examples:**

- Existing test suite fails after applying the WP changes
- New code has syntax errors preventing compilation
- A previously working feature is broken by the changes

**Decision rule:** Run the project test suite in the worktree. Any new failure
attributable to the WP changes is blocking.

### Category 5: Missing Deliverables

A file, module, or artifact that the WP explicitly requires is absent from the
diff.

**Examples:**

- WP lists "create tests/test_widget.py" in deliverables but the file is not
  in the diff
- WP requires "update CHANGELOG.md" but no changelog entry exists
- WP requires a migration file but none was created

**Decision rule:** Cross-reference the WP deliverable list against the files
changed in the diff.

---

## Non-Blocking Findings

A finding is **non-blocking** when it represents an improvement opportunity that
does not prevent approval. The WP can be approved with these findings noted.

### Category A: Style Preferences

The implementation works correctly but the reviewer would have structured it
differently.

**Examples:**

- Using a for-loop instead of a list comprehension
- Variable named `data` instead of a more descriptive name
- Function order within a module

**Decision rule:** If no explicit style rule is documented in the constitution or
a project linter config, it is non-blocking.

### Category B: Internal Naming Suggestions

A glossary term is used imprecisely in internal code (private functions, local
variables, code comments) but correctly in all public surfaces.

**Examples:**

- Internal variable named `task` when the glossary term is "work package" but
  no public surface exposes this name
- Comment says "job" when glossary says "mission" but the comment is in an
  internal helper module

**Decision rule:** Glossary enforcement is strict for public surfaces, advisory
for internal code.

### Category C: Additional Test Coverage

The reviewer identifies test scenarios beyond what the WP acceptance criteria
required.

**Examples:**

- Edge case not listed in acceptance criteria
- Performance test for a feature that has no performance requirement
- Integration test when only unit tests were required

**Decision rule:** If the acceptance criteria do not require it, additional
coverage is a suggestion, not a gate.

### Category D: Documentation Improvements

The implementation is correct but documentation could be clearer or more
complete, beyond what the WP required.

**Examples:**

- A docstring could include an example
- A README section could mention the new feature
- Inline comments could explain a non-obvious algorithm

**Decision rule:** If the WP did not list documentation as a deliverable, this
is non-blocking.

### Category E: Future Refactoring

The code works but the reviewer sees an opportunity for structural improvement
in a future iteration.

**Examples:**

- A function could be extracted to reduce duplication
- A configuration value could be moved to a constants file
- An interface could be generalized for future use cases

**Decision rule:** Refactoring suggestions that do not affect correctness or
acceptance criteria are always non-blocking.

---

## Edge Cases

### Ambiguous Acceptance Criteria

If an acceptance criterion is vaguely worded and the implementation could
reasonably satisfy it, rule **non-blocking**. The ambiguity is a planning
defect, not an implementation defect.

### Partial Deliverable

If a deliverable exists but is incomplete (e.g., a test file with one test when
three were expected), check whether the criterion specifies quantity. If it does,
the finding is blocking. If it says "add tests" without a count, one passing
test satisfies the criterion.

### Pre-existing Issues

If the diff reveals a problem that existed before this WP (a pre-existing bug
or doctrine violation), it is **non-blocking** for this review. File it as a
separate issue or note it for a future WP.
