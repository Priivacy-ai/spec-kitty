---
work_package_id: WP08
title: Documentation & Acceptance
dependencies: []
requirement_refs:
- NFR-001
- NFR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks: [T046, T047, T048, T049, T050, T051]
history:
- date: '2026-04-04'
  action: created
  by: spec-kitty.tasks
authoritative_surface: docs/
execution_mode: code_change
owned_files: [README.md, docs/**, glossary/**, examples/**, architecture/**, src/kernel/**]
---

# WP08: Documentation & Acceptance

## Objective

Rename documentation files with "constitution" in their names. Update content in 30+ documentation files containing 100+ "constitution" references. Run the acceptance verification gate to confirm zero remaining matches (outside bounded exceptions).

## Context

This is the final WP. All code, migration, and test changes are complete. This WP handles the documentation surface and runs the acceptance gate. The documentation surface is large: README.md, reference docs, glossary, examples, architecture docs, kernel docs, and development notes.

## Implementation Command

```bash
spec-kitty implement WP08 --base WP07
```

## Subtask T046: Rename 4 doc files with "constitution" in filename

**Purpose**: Rename documentation files that have "constitution" in their name.

**Steps**:
1. `git mv docs/2x/doctrine-and-constitution.md docs/2x/doctrine-and-charter.md`
2. `git mv docs/development/constitution-path-resolution-gaps.md docs/development/charter-path-resolution-gaps.md`
3. `git mv examples/constitution-driven-quality.md examples/charter-driven-quality.md`
4. `git mv architecture/2.x/user_journey/005-governance-mission-constitution-operations.md architecture/2.x/user_journey/005-governance-mission-charter-operations.md`
5. Update content within each renamed file: replace all "constitution" → "charter"
6. Check for any cross-references to these files from other docs and update those links

**Validation**: `find . -name '*constitution*' -not -path './.git/*' -not -path './kitty-specs/*'` returns zero results.

## Subtask T047: Update README.md + docs/reference/ files

**Purpose**: Update the main README and all reference documentation.

**Steps**:

1. **README.md** (9 matches):
   - `/spec-kitty.constitution` → `/spec-kitty.charter`
   - `.kittify/memory/constitution.md` → `.kittify/charter/charter.md`
   - "Missions do not have separate constitutions" → "Missions do not have separate charters"
   - "Worktree Constitution Sharing" → "Worktree Charter Sharing"
   - All other "constitution" references

2. **docs/reference/cli-commands.md** (27 matches):
   - `## spec-kitty constitution` → `## spec-kitty charter`
   - All subcommand documentation: interview, generate, context, sync, status
   - Synopsis, descriptions, examples
   - "Constitution management commands" → "Charter management commands"

3. **docs/reference/slash-commands.md** (18 matches):
   - `## /spec-kitty.constitution` → `## /spec-kitty.charter`
   - Purpose, syntax, examples, outputs
   - Cross-references from other commands

4. **docs/reference/file-structure.md** (3 matches):
   - `constitution.md` → `charter.md` in directory trees
   - Description table entries

5. **docs/reference/supported-agents.md** (1 match):
   - `/spec-kitty.constitution` → `/spec-kitty.charter`

6. **docs/reference/configuration.md** (8 matches):
   - `## constitution.md (Project Principles)` → `## charter.md (Project Principles)`
   - Location paths, examples, creating instructions

**Validation**: `rg -i constitution README.md docs/reference/` returns zero matches.

## Subtask T048: Update glossary/ files

**Purpose**: Update the glossary term definitions and cross-references.

**Steps**:

1. **glossary/README.md** (1 match):
   - "Governance | Constitution/ADR/policy" → "Governance | Charter/ADR/policy"

2. **glossary/contexts/governance.md** (16 matches):
   - `### Constitution` → `### Charter`
   - `### Constitution Interview` → `### Charter Interview`
   - `### Constitution Compiler` → `### Charter Compiler`
   - All definition text, cross-references, and examples

3. **glossary/contexts/configuration-project-structure.md** (6 matches):
   - `### Project Constitution` → `### Project Charter`
   - `.kittify/constitution/` → `.kittify/charter/`
   - Cross-references

4. **glossary/contexts/doctrine.md** (13 matches):
   - `### Constitution Selection` → `### Charter Selection`
   - `.kittify/constitution/` → `.kittify/charter/`
   - All cross-references and relationship descriptions

**Validation**: `rg -i constitution glossary/` returns zero matches.

## Subtask T049: Update remaining docs

**Purpose**: Update development docs, how-to guides, examples, and architecture docs.

**Steps**:

1. **docs/development/** files (6+ files):
   - `test-execution-report-pr305.md`
   - `doctrine-inclusion-assessment.md`
   - `pr305-review-resolution-plan.md`
   - `code-review-2026-03-25.md`
   - `test-plan-pr305.md`
   - `charter-path-resolution-gaps.md` (already renamed in T046, verify content)

2. **docs/how-to/** files (2 files):
   - `non-interactive-init.md`
   - `setup-governance.md`

3. **examples/** files (3 remaining after T046):
   - `claude-cursor-collaboration.md`
   - `solo-developer-workflow.md`
   - `worktree-parallel-features.md`

4. **architecture/** files (3+ files after T046):
   - `architecture/2.x/04_implementation_mapping/README.md`
   - `architecture/audience/internal/maintainer.md`
   - `architecture/audience/internal/spec-kitty-cli-runtime.md`
   - `architecture/audience/internal/lead-developer.md`

For each file: case-preserving replacement of "constitution" → "charter".

**Validation**: `rg -i constitution docs/ examples/ architecture/ --glob '!**/CHANGELOG*'` returns zero matches.

## Subtask T050: Update .kittify/memory notes + src/kernel/ files

**Purpose**: Update project memory notes and kernel documentation.

**Steps**:

1. **src/kernel/README.md** (5 matches):
   - Update dependency hierarchy descriptions
   - Update architecture documentation

2. **src/kernel/paths.py** (1 match):
   - Update comment about paths used by constitution → charter

**Validation**: `rg -i constitution src/kernel/` returns zero matches.

## Subtask T051: Run acceptance verification gate

**Purpose**: Verify the entire rename is complete with zero remaining matches.

**Steps**:

1. **Primary content gate**:
```bash
rg -n -i constitution . \
  --glob '!CHANGELOG.md' \
  --glob '!kitty-specs/' \
  --glob '!src/specify_cli/upgrade/migrations/m_3_1_1_charter_rename.py' \
  --glob '!src/specify_cli/upgrade/metadata.py'
```
Must return zero matches.

2. **Filename gate**:
```bash
find . -name '*constitution*' -not -path './.git/*' -not -path './kitty-specs/*'
```
Must return zero results.

3. **Bounded exception audit** (informational):
```bash
# Verify exception files contain only expected matches
rg -c -i constitution src/specify_cli/upgrade/migrations/m_3_1_1_charter_rename.py
# Expected: 10-15 matches (path detection literals)

rg -c -i constitution src/specify_cli/upgrade/metadata.py
# Expected: 5 matches (legacy ID map keys)
```

4. **Test gate**:
```bash
python -m pytest tests/ -x -q
```

5. **Type gate**:
```bash
mypy --strict src/charter/ src/specify_cli/charter/
```

6. **Old migration stub verification**:
```bash
for f in src/specify_cli/upgrade/migrations/m_0_10_12_*.py \
         src/specify_cli/upgrade/migrations/m_0_13_0_*.py \
         src/specify_cli/upgrade/migrations/m_2_0_0_*.py \
         src/specify_cli/upgrade/migrations/m_2_0_2_*.py \
         src/specify_cli/upgrade/migrations/m_2_1_2_*.py; do
  count=$(rg -c -i constitution "$f" 2>/dev/null || echo "0")
  if [ "$count" -gt "0" ]; then
    echo "FAIL: $f still contains $count 'constitution' matches"
  fi
done
```
Must report zero matches for all stubs.

**If any gate fails**: Identify the remaining matches, fix them, and re-run. Do NOT declare the WP done until all gates pass.

**Validation**: All 6 gates pass.

## Definition of Done

- [ ] 4 doc files renamed (no filenames contain "constitution")
- [ ] README.md updated (zero matches)
- [ ] docs/reference/ updated (5 files, zero matches)
- [ ] glossary/ updated (4 files, zero matches)
- [ ] Remaining docs, examples, architecture updated (zero matches)
- [ ] src/kernel/ updated (zero matches)
- [ ] Primary content gate: zero matches (excluding 2 exception files)
- [ ] Filename gate: zero results
- [ ] Test gate: pytest passes
- [ ] Type gate: mypy passes
- [ ] Exception audit: only expected matches in 2 files

## Risks

- **Hidden files**: Some documentation may be in unexpected locations. If the acceptance gate finds matches, investigate and fix.
- **Cross-references**: Renamed doc files may be linked from other docs. Update broken links.
- **CLAUDE.md edits**: CLAUDE.md is owned by WP05. If it still has matches, coordinate.

## Reviewer Guidance

- Run the acceptance gate yourself — it's the ultimate arbiter
- Check that glossary term definitions are coherent after the rename (not just mechanically replaced)
- Verify cross-references between docs still work after file renames
- Check README.md workflow descriptions make sense with "charter" terminology
