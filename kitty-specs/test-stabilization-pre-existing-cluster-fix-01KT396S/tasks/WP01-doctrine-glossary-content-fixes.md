---
work_package_id: WP01
title: Doctrine/Glossary Content Fixes
dependencies: []
requirement_refs:
- FR-004
- FR-005
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: claude
history:
- date: '2026-06-02'
  event: created
agent_profile: curator-carla
authoritative_surface: glossary/contexts/
execution_mode: code_change
owned_files:
- glossary/contexts/**/*.md
- tests/doctrine/test_glossary_link_integrity.py
- tests/doctrine/test_tactic_compliance.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load curator-carla
```

This configures your working style for content-focused fixes.

---

## Objective

Fix two broken markdown link fragments in `glossary/contexts/` and repair the invalid `five-paradigm-parallel-debugging` tactic YAML schema. After this WP, `test_glossary_link_integrity` (× 2) and `test_tactic_compliance` (× 2) must pass.

**GitHub issue closed**: #1304

---

## Context

During the triage of mission `test-stabilization-and-debt-pass-01KSF9HJ`, two types of failures were identified in cluster C99-d:

1. Two glossary context files contain `[text](#anchor)` links whose `#anchor` fragment does not match any heading in the target file after slugification.
2. The `five-paradigm-parallel-debugging` tactic has an invalid YAML schema (missing required field or dangling `$ref`).

These are **pure content fixes** — no production Python code changes. Tests must not be weakened.

### Slugification algorithm (from `tests/doctrine/test_glossary_link_integrity.py`)

The test slugifies headings as follows:

```python
def _slugify_heading(text: str) -> str:
    heading = re.sub(r"\s+#+\s*$", "", text.strip())      # strip trailing hashes
    heading = heading.replace("`", "").lower()             # lowercase, remove backticks
    heading = re.sub(r"[^a-z0-9 _-]", "", heading)        # keep only safe chars
    heading = heading.replace(" ", "-")                    # spaces → dashes
    heading = re.sub(r"-{2,}", "-", heading).strip("-")   # collapse double dashes
    return heading
```

**Important**: The anchor `platform-darwin--platform-linux` contains a **double dash**. The collapse rule above removes double dashes — so this anchor can only come from a heading that already contained a literal double dash or two consecutive hyphens before slugification. Investigate whether this is an intentional anchor (e.g., the heading is `Platform Darwin--Platform Linux`) or a typo in the link.

---

## Subtasks

### T001 — Locate the two broken glossary context files

**Steps**:

1. Run the failing test in verbose mode to see which files and which links are broken:
   ```bash
   cd spec-kitty
   pytest tests/doctrine/test_glossary_link_integrity.py -v 2>&1 | head -60
   ```
   The test output names the source file, line number, and the unresolvable link target.

2. Record both:
   - Source file (the `.md` that contains the broken link)
   - Target file + fragment (where the link points)
   - The exact expected anchor string

3. Open each source file and find the broken `[text](#fragment)` link.

**Files**: `glossary/contexts/*.md`

**Validation**: You have two broken links identified, each with source file, target file, and anchor.

---

### T002 — Fix `#doctrine-pack` anchor

**Steps**:

1. Determine what the target file is for the link that uses `#doctrine-pack` (from T001 output).
2. Open the target file.
3. Check whether any existing heading slugifies to `doctrine-pack`. If yes, the link fragment is wrong — correct it to the right anchor. If no heading exists, add:
   ```markdown
   ## Doctrine Pack
   ```
   in a semantically appropriate location in the target file (above the content it describes, or as a new top-level section if content doesn't exist).
4. Verify: `_slugify_heading("Doctrine Pack")` → `"doctrine-pack"` ✓

**Files**: Target glossary file identified in T001.

**Validation**: The link resolves; T001-style grep finds the anchor in the target file.

---

### T003 — Fix `#platform-darwin--platform-linux` anchor

**Steps**:

1. Use the T001 output to identify the target file for the link to `#platform-darwin--platform-linux`.
2. Open the target file and search for headings containing "darwin" or "linux".
3. Determine whether:
   - **Option A**: A heading exists that should slugify to `platform-darwin--platform-linux`. Since the collapse rule eliminates double dashes, this fragment can only arise if the heading has *no* double dashes and the collapse rule is not triggered — meaning the fragment itself may be a typo (should be `platform-darwin-platform-linux`, single dash).
   - **Option B**: The heading genuinely contains `--` (e.g., `## Platform Darwin -- Platform Linux`), making the intended slug `platform-darwin-platform-linux` (after collapse). If so, the link fragment `platform-darwin--platform-linux` is wrong.
   - **Option C**: No heading exists and one must be added.
4. Apply the correct fix: update the link fragment to match an existing heading's slug, or add the heading.

**Files**: Target glossary file identified in T001; source file containing the broken link.

**Validation**: Run the slugification algorithm mentally on the heading and confirm it matches the link fragment exactly.

---

### T004 — Fix the `five-paradigm-parallel-debugging` tactic schema

**Steps**:

1. Locate the tactic file. Search in order:
   ```bash
   find . -name '*five-paradigm*' -not -path '*/.venv/*'
   find . -path '*doctrine/tactics*' -name '*.yaml' | xargs grep -l 'five-paradigm' 2>/dev/null
   ```

2. Run the failing tactic test to see the exact validation error:
   ```bash
   pytest tests/doctrine/test_tactic_compliance.py -v -k "five-paradigm" 2>&1
   ```

3. The error will name the missing field or the unresolvable `$ref`. Common causes:
   - Missing required field (e.g., `id`, `title`, `description`, `applies_when`)
   - A `$ref` pointing to a term not in the glossary
   - An enum value not in the allowed set

4. Open the tactic YAML and apply the minimum fix:
   - Add the missing required field with the correct value.
   - Resolve any `$ref` by either fixing the reference key or adding the referenced term to the glossary.

5. Do **not** change the tactic's semantics — only make it structurally valid.

**Files**: The `five-paradigm-parallel-debugging` tactic YAML file.

**Validation**: `pytest tests/doctrine/test_tactic_compliance.py -v -k "five-paradigm"` passes.

---

### T005 — Run full doctrine test suite

**Steps**:

```bash
pytest tests/doctrine/test_glossary_link_integrity.py \
       tests/doctrine/test_tactic_compliance.py -v
```

Expected: all four previously-failing tests pass. Zero new failures.

If any test still fails, return to T002–T004 and address the remaining issue.

**Final check** — run the broader doctrine suite to confirm no regression:
```bash
pytest tests/doctrine/ -q
```

---

## Branch Strategy

**Planning base branch**: `main`
**Merge target**: `main`
**Execution**: Worktree allocated per Lane A from `lanes.json`. Run `spec-kitty agent action implement WP01 --agent claude` to enter the correct workspace.

Do not modify files outside `owned_files`. Specifically: do not touch any Python source files in `src/`.

---

## Definition of Done

- [ ] `test_glossary_link_integrity` (both parametrize cases that were failing) pass
- [ ] `test_tactic_compliance` (both cases for `five-paradigm-parallel-debugging`) pass
- [ ] No previously-passing doctrine test regresses
- [ ] No Python source files modified
- [ ] `mypy --strict` not applicable (no Python changes)

## Risks

- The double-dash anchor (`platform-darwin--platform-linux`) may require careful investigation — the slugifier collapses double dashes, so the only way this anchor is valid is if the heading itself has a structure that produces it without collapsing. Trace carefully.

## Reviewer Guidance

Verify:
1. Both broken links now resolve to valid headings in the target files.
2. The tactic YAML validates against the tactic schema (Pydantic error gone).
3. The diff contains only content file changes — no Python, no test code changes.
