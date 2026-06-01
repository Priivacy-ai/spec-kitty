---
work_package_id: WP05
title: '#1304: Doctrine/Glossary Anchor & Tactic Fix'
dependencies:
- WP04
requirement_refs:
- FR-005
- FR-007
- FR-008
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
- T023
agent: "claude:sonnet-4-6:reviewer:reviewer"
history: []
agent_profile: curator-carla
authoritative_surface: glossary/contexts/
execution_mode: code_change
owned_files:
- glossary/contexts/**
- src/specify_cli/doctrine/**
- tests/doctrine/**
role: curator
tags: []
shell_pid: "73444"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load curator-carla
```

This configures your curator persona. Proceed only after the profile is loaded.

---

## Objective

Fix the doctrine and glossary integrity failures in the #1304 cluster:
1. Add the `doctrine-pack` anchor to glossary contexts.
2. Add the `platform-darwin--platform-linux` anchor to glossary contexts.
3. Fix the `five-paradigm-parallel-debugging` tactic YAML so it passes schema validation and has no unresolved references.

This WP is pure data/definition work — no Python source logic changes.

---

## Context

Issue #1304 (cluster C99-e) reports 4 test failures:
- `tests/doctrine/test_glossary_link_integrity` × 2 — missing anchors `doctrine-pack` and `platform-darwin--platform-linux`.
- `tests/doctrine/test_tactic_compliance` × 2 — `five-paradigm-parallel-debugging` tactic schema invalid + unresolved refs.

These are all in `glossary/contexts/` and the doctrine tactic files. No runtime code changes needed.

**Prerequisite**: WP04 must be complete. `tests/next/` must be green.

---

## Subtask T019 — Reproduce the #1304 Cluster

**Purpose**: Confirm which tests fail and capture the exact error messages.

**Steps**:
```bash
pytest tests/doctrine/ -q --tb=long -p no:cacheprovider 2>&1 | tee /tmp/wp05-before.txt
```

Note:
- Which anchor names are reported missing?
- Which tactic ID is reported invalid?
- What schema fields are missing? What refs are unresolved?

**Validation**:
- [ ] All 4 failures reproduced and error messages recorded
- [ ] If zero failures: mark WP05 stale, stop

---

## Subtask T020 — Add doctrine-pack Anchor

**Purpose**: The glossary link integrity test expects an anchor named `doctrine-pack` to exist in `glossary/contexts/`. It is missing.

**Steps**:
1. Understand the anchor format by reading existing context files:
   ```bash
   ls glossary/contexts/
   cat glossary/contexts/<any-existing-file>.md | head -40
   ```
   Anchors are typically HTML anchor tags or frontmatter-defined IDs in Markdown.

2. Find where `doctrine-pack` is referenced to understand what concept it should define:
   ```bash
   grep -r "doctrine-pack" src/ tests/ docs/ glossary/ --include="*.md" --include="*.yaml" --include="*.yml" --include="*.py" -l
   grep -r "doctrine-pack" src/ docs/ glossary/ --include="*.md" | head -20
   ```

3. Add the anchor to the appropriate context file. Use the same format as existing anchors. If a new context file is needed (because the concept has no existing home), create it following the naming conventions of the `glossary/contexts/` directory.

4. Run the link integrity test to confirm:
   ```bash
   pytest tests/doctrine/test_glossary_link_integrity.py -q --tb=short -k "doctrine-pack"
   ```

**Files modified**: One file in `glossary/contexts/`.

**Validation**:
- [ ] `doctrine-pack` anchor passes link integrity test

---

## Subtask T021 — Add platform-darwin--platform-linux Anchor

**Purpose**: Same pattern as T020 for the `platform-darwin--platform-linux` anchor.

**Steps**:
1. Find where `platform-darwin--platform-linux` is referenced:
   ```bash
   grep -r "platform-darwin--platform-linux\|platform-darwin\|platform-linux" \
     src/ tests/ docs/ glossary/ --include="*.md" --include="*.yaml" -l
   ```

2. Understand what concept this anchor represents (platform-specific context, likely relating to Darwin/Linux platform distinctions in doctrine).

3. Add the anchor to the appropriate context file in `glossary/contexts/`. The double-dash format suggests it's a compound term combining two platform concepts.

4. Confirm:
   ```bash
   pytest tests/doctrine/test_glossary_link_integrity.py -q --tb=short -k "platform"
   ```

**Files modified**: One file in `glossary/contexts/` (may be the same file as T020 or a different one).

**Note**: T020 and T021 are independent and can be done in either order.

**Validation**:
- [ ] `platform-darwin--platform-linux` anchor passes link integrity test

---

## Subtask T022 — Fix five-paradigm-parallel-debugging Tactic

**Purpose**: The `five-paradigm-parallel-debugging` tactic YAML is both schema-invalid and has unresolved references.

**Steps**:
1. Locate the tactic file:
   ```bash
   find src/specify_cli/doctrine/ .kittify/ -name "*five-paradigm*" -o -name "*parallel-debug*" 2>/dev/null
   find . -name "*.yaml" -o -name "*.yml" | xargs grep -l "five-paradigm-parallel-debugging" 2>/dev/null
   ```

2. Understand the tactic schema. Find the schema definition:
   ```bash
   find src/specify_cli/doctrine/ -name "*.py" | xargs grep -l "tactic.*schema\|TacticSchema\|class Tactic" 2>/dev/null
   ```
   Or look for JSON Schema / Pydantic model that the compliance test uses.

3. Run the compliance test with verbose output to see exactly what fails:
   ```bash
   pytest tests/doctrine/test_tactic_compliance.py -q --tb=long -k "five-paradigm"
   ```

4. Fix the tactic YAML:
   - Add any missing required fields (e.g., `id`, `title`, `summary`, `applies_when`, `directives`).
   - Resolve dangling `$ref` values: for each ref that points to a removed or renamed glossary term, either update the ref to the current term or remove the reference if the concept is no longer applicable.

5. Run the compliance test again to confirm it passes.

**Files modified**: The `five-paradigm-parallel-debugging` tactic YAML (path found in step 1).

**Validation**:
- [ ] Both `test_tactic_compliance` tests for `five-paradigm-parallel-debugging` pass
- [ ] No other tactic compliance tests regress

---

## Subtask T023 — Full #1304 Verification

**Purpose**: Confirm all 4 doctrine tests pass and no regressions.

**Steps**:
```bash
pytest tests/doctrine/ -q --tb=short -p no:cacheprovider 2>&1 | tee /tmp/wp05-after.txt
```

If any tests still fail: diagnose and fix before committing.

Run a broader check:
```bash
pytest tests/ -q --tb=no -p no:cacheprovider \
  --ignore=tests/charter/ \
  -x 2>&1 | tail -5
```

**FR-007 — Regression test**: The link-integrity and tactic-compliance tests themselves are the regression guards — confirm they are not marked `xfail` or skipped. If the anchor format required discovery (e.g., the format was not obvious from context), add a brief inline comment in the context file explaining the expected format so future contributors maintain it correctly.

**FR-008 — Record post-fix results**: Append to `docs/p0-baseline-refresh.md`:
```bash
echo "\n## WP05 Post-Fix Results (#1304)" >> docs/p0-baseline-refresh.md
cat /tmp/wp05-after.txt | grep "passed\|failed" | tail -1 >> docs/p0-baseline-refresh.md
```

Commit:
```bash
git add glossary/contexts/ src/specify_cli/doctrine/
git add -p  # include any other changed files
git commit -m "fix(#1304): add missing glossary anchors and fix five-paradigm tactic schema"
```

**Validation**:
- [ ] All 4 `tests/doctrine/` tests pass
- [ ] No regressions in sync/contract/next tests
- [ ] **FR-007**: Regression guards confirmed active (not xfail/skipped)
- [ ] **FR-008**: Post-fix results appended to `docs/p0-baseline-refresh.md`
- [ ] Changes committed

---

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution worktree**: Allocated by `lanes.json`.

Implementation command:
```bash
spec-kitty agent action implement WP05 --agent claude
```

---

## Definition of Done

- [ ] `test_glossary_link_integrity` passes for `doctrine-pack` anchor
- [ ] `test_glossary_link_integrity` passes for `platform-darwin--platform-linux` anchor
- [ ] Both `test_tactic_compliance` tests for `five-paradigm-parallel-debugging` pass
- [ ] No regressions in any other doctrine, sync, contract, or next tests
- [ ] **FR-007**: Regression guards confirmed active (link-integrity + tactic-compliance tests not skipped)
- [ ] **FR-008**: Post-fix results appended to `docs/p0-baseline-refresh.md`
- [ ] Changes committed with issue-scoped message

---

## Risks

- **Anchor format ambiguity**: If the glossary context files use a non-obvious anchor format, read several existing files before adding new entries.
- **Tactic ref targets may not exist**: If the refs in `five-paradigm-parallel-debugging` point to terms that were genuinely removed, decide whether to remove the ref (simplest) or recreate the term (only if it's clearly needed). Default to removing the ref.
- **New anchor creates unexpected failures**: Adding an anchor may cause other tests to discover it — run the full doctrine suite to check.

## Activity Log

- 2026-06-01T17:46:14Z – claude – WP05 claimed by claude (lane-d worktree created)
- 2026-06-01T17:49:30Z – claude – Ready for review (cycle 1/3). WP05 is stale — all #1304 doctrine tests pass pre-implementation. FR-007 guards confirmed active. FR-008 results appended to docs/p0-baseline-refresh.md.
- 2026-06-01T17:49:47Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=73444 – Started review via action command
- 2026-06-01T17:51:31Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=73444 – Review passed: WP05 correctly identified as stale (#1304 tests all passing pre-implementation). FR-007 guards confirmed active (no xfail/skip). FR-008 results documented in docs/p0-baseline-refresh.md. 1975 doctrine tests pass, 0 failed.
