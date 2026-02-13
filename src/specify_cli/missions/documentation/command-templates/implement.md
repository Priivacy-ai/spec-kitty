---
description: Implement documentation work packages using Divio templates and generators.
---

# Command Template: /spec-kitty.implement (Documentation Mission)

**Phase**: Generate
**Purpose**: Create documentation from templates, invoke generators for reference docs, populate templates with content.

## ⚠️ CRITICAL: Working Directory Requirement

**After running `spec-kitty implement WP##`, you MUST:**

1. **Run the cd command shown in the output** - e.g., `cd .worktrees/###-feature-WP##/`
2. **ALL file operations happen in this directory** - Read, Write, Edit tools must target files in the workspace
3. **NEVER write deliverable files to the main repository** - This is a critical workflow error

**Why this matters:**
- Each WP has an isolated worktree with its own branch
- Changes in main repository will NOT be seen by reviewers looking at the WP worktree
- Writing to main instead of the workspace causes review failures and merge conflicts

**Verify you're in the right directory:**
```bash
pwd
# Should show: /path/to/repo/.worktrees/###-feature-WP##/
```

---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Implementation Workflow

Documentation implementation follows the standard workspace-per-WP model:
- **Worktrees used** - Each WP has its own worktree with dedicated branch (same as code missions)
- **Templates populated** - Use Divio templates as starting point
- **Generators invoked** - Run JSDoc/Sphinx/rustdoc to create API reference
- **Content authored** - Write tutorial/how-to/explanation content in worktree
- **Quality validated** - Check accessibility, links, build before merging
- **Release prepared (optional)** - Draft `release.md` when publish is in scope

---

## Per-Work-Package Implementation

### For WP01: Structure & Generator Setup

**Objective**: Create directory structure and configure doc generators.

**Steps**:
1. Create docs/ directory structure:
   ```bash
   mkdir -p docs/{tutorials,how-to,reference/api,explanation}
   ```
2. Create index.md landing page:
   ```markdown
   # {Project Name} Documentation

   Welcome to the documentation for {Project Name}.

   ## Getting Started

   - [Tutorials](tutorials/) - Learn by doing
   - [How-To Guides](how-to/) - Solve specific problems
   - [Reference](reference/) - Technical specifications
   - [Explanation](explanation/) - Understand concepts
   ```
3. Configure generators (per plan.md):
   - For Sphinx: Create docs/conf.py from template
   - For JSDoc: Create jsdoc.json from template
   - For rustdoc: Update Cargo.toml with metadata
4. Create build script:
   ```bash
   #!/bin/bash
   # build-docs.sh

   # Build Python docs with Sphinx
   sphinx-build -b html docs/ docs/_build/html/

   # Build JavaScript docs with JSDoc
   npx jsdoc -c jsdoc.json

   # Build Rust docs
   cargo doc --no-deps

   echo "Documentation built successfully!"
   ```
5. Test build: Run build script, verify no errors

**Deliverables**:
- docs/ directory structure
- index.md landing page
- Generator configs (conf.py, jsdoc.json, Cargo.toml)
- build-docs.sh script
- Successful test build

---

### For WP02-05: Content Creation (Tutorials, How-Tos, Reference, Explanation)

**Objective**: Write documentation content using Divio templates.

**Steps**:
1. **Select appropriate Divio template**:
   - Tutorial: Use `templates/divio/tutorial-template.md`
   - How-To: Use `templates/divio/howto-template.md`
   - Reference: Use `templates/divio/reference-template.md` (for manual reference)
   - Explanation: Use `templates/divio/explanation-template.md`

2. **Copy template to docs/**:
   ```bash
   # Example for tutorial
   cp templates/divio/tutorial-template.md docs/tutorials/getting-started.md
   ```

3. **Fill in frontmatter**:
   ```yaml
   ---
   type: tutorial
   audience: "beginners"
   purpose: "Learn how to get started with {Project}"
   created: "2026-01-12"
   estimated_time: "15 minutes"
   prerequisites: "Python 3.11+, pip"
   ---
   ```

4. **Replace placeholders with content**:
   - {Title} → Actual title
   - [Description] → Actual description
   - [Step actions] → Actual step-by-step instructions
   - [Examples] → Real code examples

5. **Follow Divio principles for this type**:
   - **Tutorial**: Learning-oriented, step-by-step, show results at each step
   - **How-To**: Goal-oriented, assume experience, solve specific problem
   - **Reference**: Information-oriented, complete, consistent format
   - **Explanation**: Understanding-oriented, conceptual, discuss alternatives

6. **Add real examples and content**:
   - Use actual project APIs, not placeholders
   - Test all code examples (they must work!)
   - Add real screenshots (with alt text)
   - Use diverse example names (not just "John")

7. **Validate against checklists**:
   - Divio compliance (correct type characteristics?)
   - Accessibility (heading hierarchy, alt text, clear language?)
   - Inclusivity (diverse examples, neutral language?)

**For Reference Documentation**:

**Auto-Generated Reference** (API docs):
1. Ensure code has good doc comments:
   - Python: Docstrings with Google/NumPy format
   - JavaScript: JSDoc comments with @param, @returns
   - Rust: /// doc comments
2. Run generator:
   ```bash
   # Sphinx (Python)
   sphinx-build -b html docs/ docs/_build/html/

   # JSDoc (JavaScript)
   npx jsdoc -c jsdoc.json

   # rustdoc (Rust)
   cargo doc --no-deps --document-private-items
   ```
3. Review generated output:
   - Are all public APIs present?
   - Are descriptions clear?
   - Are examples included?
   - Are links working?
4. If generated docs have gaps:
   - Add/improve doc comments in source code
   - Regenerate
   - Or supplement with manual reference

**Manual Reference** (CLI, config, data formats):
1. Use reference template
2. Document every option, every command, every field
3. Be consistent in format (use tables)
4. Include examples for each item

**Deliverables**:
- Completed documentation files in docs/
- All templates filled with real content
- All code examples tested and working
- All Divio type principles followed
- All accessibility/inclusivity checklists satisfied

---

### For WP06: Quality Validation

**Objective**: Validate documentation quality before considering complete.

**Steps**:
1. **Automated checks**:
   ```bash
   # Check heading hierarchy
   find docs/ -name "*.md" -exec grep -E '^#+' {} + | head -50

   # Check for broken links
   markdown-link-check docs/**/*.md

   # Check for missing alt text
   grep -r '!\[.*\](' docs/ | grep -v '\[.*\]' || echo "✓ All images have alt text"

   # Spell check
   aspell check docs/**/*.md

   # Build check
   ./build-docs.sh 2>&1 | grep -i error || echo "✓ Build successful"
   ```

2. **Manual checks**:
   - Read each doc as target audience
   - Follow tutorials - do they work?
   - Try how-tos - do they solve problems?
   - Check reference - is it complete?
   - Read explanations - do they clarify?

3. **Divio compliance check**:
   - Is each doc correctly classified?
   - Does it follow principles for its type?
   - Is it solving the right problem for that type?

4. **Accessibility check**:
   - Proper heading hierarchy?
   - All images have alt text?
   - Clear language (not jargon-heavy)?
   - Links are descriptive?

5. **Peer review**:
   - Have someone from target audience review
   - Gather feedback on clarity, completeness, usability
   - Revise based on feedback

6. **Final build and deploy** (if applicable):
   ```bash
   # Build final documentation
   ./build-docs.sh

   # Deploy to hosting (example for GitHub Pages)
   # (Deployment steps depend on hosting platform)
   ```

**Deliverables**:
- All automated checks passing
- Manual review completed with feedback addressed
- Divio compliance verified
- Accessibility compliance verified
- Final build successful
- Documentation deployed (if applicable)

---

## Key Guidelines

**For Agents**:
- Use Divio templates as starting point, not empty files
- Fill templates with real content, not more placeholders
- Test all code examples before committing
- Follow Divio principles strictly for each type
- Run generators for reference docs (don't write API docs manually)
- Validate quality at end (automated + manual checks)

**For Users**:
- Implementation creates actual documentation, not just structure
- Templates provide guidance, you provide content
- Generators handle API reference, you write the rest
- Quality validation ensures documentation is actually useful
- Peer review from target audience is valuable

---

## Common Pitfalls

**DON'T**:
- Mix Divio types (tutorial that explains concepts, how-to that teaches basics)
- Skip testing code examples (broken examples break trust)
- Use only Western male names in examples
- Say "simply" or "just" or "obviously" (ableist language)
- Skip alt text for images (accessibility barrier)
- Write jargon-heavy prose (clarity issue)
- Commit before validating (quality issue)

**DO**:
- Follow Divio principles for each type
- Test every code example
- Use diverse names in examples
- Use welcoming, clear language
- Add descriptive alt text
- Define technical terms
- Validate before considering complete

---

## Commit Workflow

**BEFORE moving to for_review**, you MUST commit your documentation:

```bash
cd .worktrees/###-feature-WP##/
git add docs/
git commit -m "docs(WP##): <describe your documentation>"
```

<details><summary>PowerShell equivalent</summary>

```powershell
Set-Location .worktrees\###-feature-WP##\
git add docs/
git commit -m "docs(WP##): <describe your documentation>"
```

</details>

**Example commit messages:**
- `docs(WP01): Add Divio structure and generator configs`
- `docs(WP02): Add getting started tutorial`
- `docs(WP05): Add API reference documentation`

**Then move to review:**
```bash
spec-kitty agent tasks move-task WP## --to for_review --note "Ready for review: <summary>"
```

**Why this matters:**
- `move-task` validates that your worktree has commits beyond main
- Uncommitted changes will block the move to for_review
- This prevents lost work and ensures reviewers see complete documentation
- Dependent WPs will receive your work through the git merge-base

---

## Status Tracking Note

If `/spec-kitty.status` shows your WP in "doing" after you moved it to "for_review", don't panic - a reviewer may have moved it back (changes requested), or there's a sync delay. Focus on your WP.
