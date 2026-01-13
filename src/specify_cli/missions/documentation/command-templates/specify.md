---
description: Create a documentation-focused feature specification with discovery and Divio scoping.
---

# Command Template: /spec-kitty.specify (Documentation Mission)

**Phase**: Discover
**Purpose**: Understand documentation needs, identify iteration mode, select Divio types, detect languages, recommend generators.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Discovery Gate (mandatory)

Before running any scripts or writing to disk, conduct a structured discovery interview tailored to documentation missions.

**Scope proportionality**: For documentation missions, discovery depth depends on project maturity:
- **New project** (initial mode): 3-4 questions about audience, goals, Divio types
- **Existing docs** (gap-filling mode): 2-3 questions about gaps, priorities, maintenance
- **Feature-specific** (documenting new feature): 1-2 questions about feature scope, integration

### Discovery Questions

**Question 1: Iteration Mode** (CRITICAL)

Ask user which documentation scenario applies:

**(A) Initial Documentation** - First-time documentation for a project (no existing docs)
**(B) Gap-Filling** - Improving/extending existing documentation
**(C) Feature-Specific** - Documenting a specific new feature/module

**Why it matters**: Determines whether to run gap analysis, how to structure workflow.

**Store answer in**: `meta.json → documentation_state.iteration_mode`

---

**Question 2A: For Initial Mode - What to Document**

Ask user:
- What is the primary audience? (developers, end users, contributors, operators)
- What are the documentation goals? (onboarding, API reference, troubleshooting, understanding architecture)
- Which Divio types are most important? (tutorial, how-to, reference, explanation)

**Why it matters**: Determines which templates to generate, what content to prioritize.

---

**Question 2B: For Gap-Filling Mode - What's Missing**

Inform user you will audit existing documentation, then ask:
- What problems are users reporting? (can't get started, can't solve specific problems, APIs undocumented, don't understand concepts)
- Which areas need documentation most urgently? (specific features, concepts, tasks)
- What Divio types are you willing to add? (tutorial, how-to, reference, explanation)

**Why it matters**: Focuses gap analysis on user-reported issues, prioritizes work.

---

**Question 2C: For Feature-Specific Mode - Feature Details**

Ask user:
- Which feature/module are you documenting?
- Who will use this feature? (what audience)
- What aspects need documentation? (getting started, common tasks, API details, architecture/design)

**Why it matters**: Scopes documentation to just the feature, determines which Divio types apply.

---

**Question 3: Language Detection & Generators**

Auto-detect project languages:
- Scan for `.js`, `.ts`, `.jsx`, `.tsx` files → Recommend JSDoc/TypeDoc
- Scan for `.py` files → Recommend Sphinx
- Scan for `Cargo.toml`, `.rs` files → Recommend rustdoc

Present to user:
"Detected languages: [list]. Recommend these generators: [list]. Proceed with these?"

Allow user to:
- Confirm all
- Select subset
- Skip generators (manual documentation only)

**Why it matters**: Determines which generators to configure in planning phase.

**Store answer in**: `meta.json → documentation_state.generators_configured`

---

**Question 4: Target Audience (if not already clear)**

If not clear from earlier answers, ask:
"Who is the primary audience for this documentation?"
- Developers integrating your library/API
- End users using your application
- Contributors to your project
- Operators deploying/maintaining your system
- Mix of above (specify)

**Why it matters**: Affects documentation tone, depth, assumed knowledge.

**Store answer in**: `spec.md → ## Documentation Scope → Target Audience`

---

**Question 5: Publish Scope (optional)**

Ask user:
- Is documentation release/publish in scope for this effort?
- If yes, should we produce `release.md` with hosting and handoff details?

**Why it matters**: Avoids unnecessary release work when publishing is handled elsewhere.

---

### Intent Summary

After discovery questions answered, synthesize into Intent Summary:

```markdown
## Documentation Mission Intent

**Iteration Mode**: [initial | gap-filling | feature-specific]
**Primary Goal**: [Describe what user wants to accomplish]
**Target Audience**: [Who will read these docs]
**Selected Divio Types**: [tutorial, how-to, reference, explanation]
**Detected Languages**: [Python, JavaScript, Rust, etc.]
**Recommended Generators**: [JSDoc, Sphinx, rustdoc]

**Scope**: [Summary of what will be documented]
```

Confirm with user before proceeding.

---

## Outline

1. **Check discovery status**: If questions unanswered, ask one at a time (Discovery Gate above)

2. **Generate feature directory**: Run `spec-kitty agent feature create-feature "doc-{project-name}" --json --mission documentation`
   - Feature naming convention: `doc-{project-name}` or `docs-{feature-name}` for feature-specific

3. **Create meta.json**: Include `mission: "documentation"` and `documentation_state` field:
   ```json
   {
     "feature_number": "###",
     "slug": "doc-project-name",
     "friendly_name": "Documentation: Project Name",
     "mission": "documentation",
     "source_description": "...",
     "created_at": "...",
     "documentation_state": {
       "iteration_mode": "initial",
       "divio_types_selected": ["tutorial", "reference"],
       "generators_configured": [
         {"name": "sphinx", "language": "python"}
       ],
       "target_audience": "developers",
       "last_audit_date": null,
       "coverage_percentage": 0.0
     }
   }
   ```

4. **Run gap analysis** (gap-filling mode only):
   - Scan existing `docs/` directory
   - Classify docs into Divio types
   - Build coverage matrix
   - Generate `gap-analysis.md` with findings

5. **Generate specification**:
   - Use `templates/spec-template.md` from documentation mission
   - Fill in Documentation Scope section with discovery answers
   - Include gap analysis results if gap-filling mode
   - Define requirements based on selected Divio types and generators
   - Define success criteria (accessibility, completeness, audience satisfaction)

6. **Validate specification**: Run quality checks (see spec-template.md checklist)

7. **Report completion**: Spec file path, next command (`/spec-kitty.plan`)

---

## Key Guidelines

**For Agents**:
- Ask discovery questions one at a time (don't overwhelm user)
- Auto-detect languages to recommend generators
- For gap-filling, show audit results to user before asking what to fill
- Store iteration state in meta.json (enables future iterations)
- Emphasize Divio types in specification (tutorial/how-to/reference/explanation)
- Link to Write the Docs and Divio resources in spec

**For Users**:
- Discovery helps ensure documentation meets real needs
- Gap analysis (if iterating) shows what's missing
- Generator recommendations save manual API documentation work
- Iteration mode affects workflow (initial vs gap-filling vs feature-specific)
