---
name: spec-kitty.review
description: Review a work package implementation
user-invocable: true
---
# /spec-kitty.review - Review Work Package Implementation

**Version**: 0.12.0+

## Purpose

Review the implementation of a work package against its prompt file, acceptance
criteria, and owned-file boundaries. Verify correctness, test coverage, and
compliance with any applicable guardrails (e.g., bulk edit occurrence maps).

---

## Working Directory

**IMPORTANT**: This step works inside the execution workspace (worktree)
allocated by `spec-kitty agent action review WPxx --agent <name>`. Do NOT modify files outside
your `owned_files` boundaries.

**In repos with multiple missions, always pass `--mission <handle>` to every spec-kitty command.** The `<handle>` can be the mission's `mission_id` (ULID), `mid8` (first 8 chars of the ULID), or `mission_slug`. The resolver disambiguates by `mission_id` and returns a structured `MISSION_AMBIGUOUS_SELECTOR` error on ambiguity — there is no silent fallback.

## User Input

The content of the user's message that invoked this skill (everything after the skill invocation token, e.g. after `/spec-kitty.<command>` or `$spec-kitty.<command>`) is the User Input referenced elsewhere in these instructions.

You **MUST** consider this user input before proceeding (if not empty).

## Governance Payload Contract

The prompt produced by `spec-kitty agent action review` is guaranteed to carry
the following surfaces. Trust the prompt; do not consult external governance
sources unless explicitly cited by a fetch command + when-doing rule in the
prompt.

**Guaranteed bodies** (verbatim in the prompt when under the token budget; the
resolver substitutes a `spec-kitty charter context --include section:<slug>`
fetch + when-doing stanza only when the budget would otherwise be exceeded):

- **Terminology Canon** — from `.kittify/charter/charter.md` — governs the
  identifiers and term usage you assess in the diff.
- **Code Review Checklist** — from `.kittify/charter/charter.md` — your
  primary gate set when judging the WP.
- **Regression Vigilance** — from `.kittify/charter/charter.md` — the
  project's explicit drift guard; apply when the diff renames or introduces
  identifier-bearing terms.
- Any additional action-critical sections the mission declares are appended
  automatically.

**Guaranteed citations** (catalog IDs always present in the prompt when the
WP frontmatter selects a reviewer `agent_profile`):

- Every `DIRECTIVE_NNN` declared in the loaded reviewer profile's
  `directive-references` list (for example, `reviewer-renata` cites
  `DIRECTIVE_032` — Conceptual Alignment).
- Every tactic-id declared in the loaded reviewer profile's
  `tactic-references` list (for example, `reviewer-renata` cites the
  `language-driven-design` tactic).

When you assess a WP that renames identifiers or terms, the prompt cites
DIRECTIVE_032 (Conceptual Alignment) by ID; consult its rule body inline or
via the paired fetch command and apply.

**Guaranteed authority pointers** (path + when-doing conditional):

- `glossary/contexts/` — canonical terminology. Consult when the diff
  introduces or renames a domain term.
- `architecture/2.x/adr/` — architectural intent. Consult when the diff
  changes a structural boundary (package layout, public API surface,
  dependency edges).
- Any additional paths declared in the charter's `authority_paths:` block are
  emitted alongside these defaults.

**Fetch commands** (the prompt may substitute these for bodies that exceed the
token budget; whenever a fetch command appears, the accompanying
"When you <verb>, run this and apply" line specifies the trigger):

- `spec-kitty charter context --include directive:DIRECTIVE_NNN`
- `spec-kitty charter context --include tactic:<id>`
- `spec-kitty charter context --include section:<slug>`

## Review Steps

### 1. Setup

Run:

```bash
spec-kitty agent context resolve --action review --mission <handle> --json
```

Then execute the returned `check_prerequisites` command and capture
`feature_dir`. All paths must be absolute.

The output of `spec-kitty agent action review ...` is the authoritative work
package prompt and review context. Do **not** separately call
`spec-kitty charter context` or go hunting for alternate prompt files unless
the command output tells you to. The **Governance Payload Contract** section
above documents what the prompt is guaranteed to carry.

### 2. Load Work Package Prompt

Read the WP prompt file from `feature_dir/tasks/WPxx-slug.md`.
Parse frontmatter for:
- `owned_files` -- only these globs should have been modified
- `authoritative_surface` -- primary directory for this WP
- `execution_mode` -- `code_change` or `planning_artifact`
- `subtasks` -- ordered list of subtask IDs
- `dependencies` -- WPs that must be done first

### 2a. Load Agent Profile

Before proceeding with the review, load the agent profile from the WP frontmatter
using the `/ad-hoc-profile-load` skill (or `spec-kitty agent profile list` to browse
available profiles). Apply the profile's reviewer guidance and self-review gates for
the rest of this review session.

The WP frontmatter should already have `agent_profile` set to a reviewer profile
(e.g., `reviewer-renata`) by the implementing agent before it moved the WP to
`for_review`. If `agent_profile` is still set to an implementer profile, load the
implementer profile anyway and note the oversight in your review comments.

### 3. Verify Implementation

For each subtask:
1. Confirm the subtask has been implemented as specified
2. Check that tests exist and pass (for code_change subtasks)
3. Verify no files outside `owned_files` were modified

### 4. Check Quality

- All tests pass
- Code follows project conventions (run linter if configured)
- No unintended side effects or regressions
- Changes are well-documented where appropriate
- [ ] **Error-path reachability (deletion test)**: For each test that validates
  an error path, verify the test would fail if the implementation fix were
  deleted. A test that validates only the *structure* of an exception handler
  (e.g., that a `try/except` exists) without exercising the real dependency is
  insufficient. Apply the deletion test: temporarily delete the implementation
  change, run the test, confirm it fails. If it does not fail, the error path
  is untested — the test validates structure, not behaviour. Restore the fix
  before proceeding.

### 4a. Anti-pattern Checklist (WP-Level Cheap Version of Mission-Review)

For each item below, state PASS / FAIL / N/A in your verdict. A FAIL on any
item blocks approval.

1. **Dead code**: every new public function, class, or module created by this
   WP has at least one live caller from production code, excluding tests. For
   each new module, run targeted import/call-site greps, for example
   `grep -r -e "from <new_module> import" -e "import <new_module>" src/ --include="*.<ext>"`.
   Zero production hits means dead code.
2. **Synthetic-fixture test**: every test marked as covering an FR listed in
   this WP's frontmatter actually invokes the production code path that would
   produce the asserted shape. A test that constructs a literal dict matching
   the assertion is a synthetic fixture. Ask: if I delete the implementation
   code, does this test still pass? If yes, the FR is untested.
3. **Silent empty return**: search every new code path for `except ...:
   return ""`, `return None`, `return []`, `return {}`, or `pass`. Each hit
   must have a documented reason; absent that, it is a silent failure
   candidate.
4. **FR coverage**: every FR in `requirement_refs` has at least one test
   assertion that references the behavior it names, not just a comment or
   frontmatter entry.
5. **Frozen surface**: no commit in this WP modifies a file the spec,
   contract, or WP prompt marks as frozen or untouchable. For each frozen file,
   `git log --oneline <base>..HEAD -- <frozen-file>` must be empty.
6. **Locked decision**: no new code path contradicts a `MUST NOT` clause in
   `spec.md`, `plan.md`, or `contracts/`. Grep the diff for forbidden patterns
   named by those clauses.
7. **Shared-file ownership**: any file modified by this WP that is also
   modified by another WP, visible in `lanes.json`, shared lane metadata, or
   the same mission merge, has an explicit coordination note in the move-task
   reason or review feedback.
8. **Production fragility**: any new `raise` in a production code path has a
   documented fail-loud rationale. A bare `raise` in a request handler, worker,
   or CLI path that can fire on a transient race is a fragility risk.

---

## Bulk Edit Compliance (if applicable)

If this mission has `change_mode: bulk_edit` in `meta.json`:

1. **Verify occurrence map exists**: `occurrence_map.yaml` must be present in the feature directory
2. **Reference during review**: The occurrence map is the governing artifact for this bulk edit
3. **Check category compliance**:
   - Verify changes respect `do_not_change` categories — reject if these were modified
   - Verify `manual_review` categories have documented justification
   - Flag any changed files that fall outside classified categories
4. **Check exceptions**: Verify exception files/patterns were not modified
5. **If occurrence map is missing**: Reject the review — bulk edit missions require classification

The system enforces map existence automatically, but as a reviewer you should verify
that the *substance* of the changes aligns with the classification, not just that the
file exists.

---

## Output

After completing review:
- Approve or reject each subtask with clear reasoning
- If rejecting, provide specific feedback on what needs to change
- Commit any review notes or annotations

### On Approval

Move the WP forward:
```bash
spec-kitty agent status emit WPxx --to approved --actor <name> --mission <handle>
```

### On Rejection

Before rejecting, update `agent_profile` in the WP frontmatter back to the
implementer profile so the next implementation cycle starts with the right context:

1. Identify the implementer profile that worked on this WP (check the history field
   or `status.events.jsonl` to find the last `in_progress` actor).
   Alternatively, use the default: `implementer-ivan` (or `python-pedro`/`java-jenny`
   for language-specific work).

2. Update the WP frontmatter:
   ```yaml
   agent_profile: "implementer-ivan"
   role: "implementer"
   ```

3. Commit the updated frontmatter together with your review notes **before** running:
   ```bash
   spec-kitty agent status emit WPxx --to in_progress --actor <name> --mission <handle>
   ```

The implementing agent will then load the correct profile via `/ad-hoc-profile-load`
and resume work with the proper persona and self-review gates.

**Next step**: `spec-kitty next --agent <name>` will advance to the next phase.
