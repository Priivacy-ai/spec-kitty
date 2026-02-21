---
description: Review documentation work packages for Divio compliance and quality.
---

# Command Template: /spec-kitty.review (Documentation Mission)

**Phase**: Validate
**Purpose**: Review documentation for Divio compliance, accessibility, completeness, and quality.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Review Philosophy

Documentation review is NOT code review:
- **Not about correctness** (code is about bugs) but **usability** (can readers accomplish their goals?)
- **Not about style** but **accessibility** (can everyone use these docs?)
- **Not about completeness** (covering every edge case) but **usefulness** (solving real problems)
- **Not pass/fail** but **continuous improvement**

---

## Review Checklist

### 1. Divio Type Compliance

For each documentation file, verify it follows principles for its declared type:

**Tutorial Review**:
- [ ] Learning-oriented (teaches by doing, not explaining)?
- [ ] Step-by-step progression with clear sequence?
- [ ] Each step shows immediate, visible result?
- [ ] Minimal explanations (links to explanation docs instead)?
- [ ] Assumes beginner level (no unexplained prerequisites)?
- [ ] Reliable (will work for all users following instructions)?
- [ ] Achieves concrete outcome (learner can do something new)?

**How-To Review**:
- [ ] Goal-oriented (solves specific problem)?
- [ ] Assumes experienced user (not teaching basics)?
- [ ] Practical steps, minimal explanation?
- [ ] Flexible (readers can adapt to their situation)?
- [ ] Includes common variations?
- [ ] Links to reference for details, explanation for "why"?
- [ ] Title starts with "How to..."?

**Reference Review**:
- [ ] Information-oriented (describes what exists)?
- [ ] Complete (all APIs/options/commands documented)?
- [ ] Consistent format (same structure for similar items)?
- [ ] Accurate (matches actual behavior)?
- [ ] Includes usage examples (not just descriptions)?
- [ ] Structured around code organization?
- [ ] Factual tone (no opinions or recommendations)?

**Explanation Review**:
- [ ] Understanding-oriented (clarifies concepts)?
- [ ] Not instructional (not teaching how-to-do)?
- [ ] Discusses concepts, design decisions, trade-offs?
- [ ] Compares with alternatives fairly?
- [ ] Makes connections between ideas?
- [ ] Provides context and background?
- [ ] Identifies limitations and when (not) to use?

**If type is wrong or mixed**:
- Return with feedback: "This is classified as {type} but reads like {actual_type}. Either reclassify or rewrite to match {type} principles."

---

### 2. Accessibility Review

**Heading Hierarchy**:
- [ ] One H1 per document (the title)
- [ ] H2s for major sections
- [ ] H3s for subsections under H2s
- [ ] No skipped levels (H1 → H3 is wrong)
- [ ] Headings are descriptive (not "Introduction", "Section 2")

**Images**:
- [ ] All images have alt text
- [ ] Alt text describes what image shows (not "image" or "screenshot")
- [ ] Decorative images have empty alt text (`![]()`)
- [ ] Complex diagrams have longer descriptions

**Language**:
- [ ] Clear, plain language (technical terms defined)
- [ ] Active voice ("run the command" not "the command should be run")
- [ ] Present tense ("returns" not "will return")
- [ ] Short sentences (15-20 words max)
- [ ] Short paragraphs (3-5 sentences)

**Links**:
- [ ] Link text is descriptive ("see the installation guide" not "click here")
- [ ] Links are not bare URLs (use markdown links)
- [ ] No broken links (test all links)

**Code Blocks**:
- [ ] All code blocks have language tags for syntax highlighting
- [ ] Expected output is shown (not just commands)
- [ ] Code examples actually work (tested)

**Tables**:
- [ ] Tables have headers
- [ ] Headers use `|---|` syntax
- [ ] Tables are not too wide (wrap if needed)

**Lists**:
- [ ] Proper markdown lists (not paragraphs with commas)
- [ ] Consistent bullet style
- [ ] Items are parallel in structure

**If accessibility issues found**:
- Return with feedback listing specific issues and how to fix

---

### 3. Inclusivity Review

**Examples and Names**:
- [ ] Uses diverse names (not just Western male names)
- [ ] Names span different cultures and backgrounds
- [ ] Avoids stereotypical name choices

**Language**:
- [ ] Gender-neutral ("they" not "he/she", "developers" not "guys")
- [ ] Avoids ableist language ("just", "simply", "obviously", "easy" imply reader inadequacy)
- [ ] Person-first language where appropriate ("person with disability" not "disabled person")
- [ ] Avoids idioms (cultural-specific phrases that don't translate)

**Cultural Assumptions**:
- [ ] No religious references (Christmas, Ramadan, etc.)
- [ ] No cultural-specific examples (American holidays, sports, food)
- [ ] Date formats explained (ISO 8601 preferred)
- [ ] Currency and units specified (USD, meters, etc.)

**Tone**:
- [ ] Welcoming to newcomers (not intimidating)
- [ ] Assumes good faith (users aren't "doing it wrong")
- [ ] Encouraging (celebrates progress)

**If inclusivity issues found**:
- Return with feedback listing examples to change

---

### 4. Completeness Review

**For Initial Documentation**:
- [ ] All selected Divio types are present
- [ ] Tutorials enable new users to get started
- [ ] Reference covers all public APIs
- [ ] How-tos address common problems (from user research or support tickets)
- [ ] Explanations clarify key concepts and design

**For Gap-Filling**:
- [ ] High-priority gaps from audit are filled
- [ ] Outdated docs are updated
- [ ] Coverage percentage improved

**For Feature-Specific**:
- [ ] Feature is documented across relevant Divio types
- [ ] Feature docs integrate with existing documentation
- [ ] Feature is discoverable (linked from main index, relevant how-tos, etc.)

**Common Gaps**:
- [ ] Installation/setup covered (tutorial or how-to)?
- [ ] Common tasks have how-tos?
- [ ] All public APIs in reference?
- [ ] Error messages explained (troubleshooting how-tos)?
- [ ] Architecture/design explained (explanation)?

**If completeness gaps found**:
- Return with feedback listing missing documentation

---

### 5. Quality Review

**Tutorial Quality**:
- [ ] Tutorial actually works (reviewer followed it successfully)?
- [ ] Each step shows result (not "do X, Y, Z" without checkpoints)?
- [ ] Learner accomplishes something valuable?
- [ ] Appropriate for stated audience?

**How-To Quality**:
- [ ] Solves the stated problem?
- [ ] Steps are clear and actionable?
- [ ] Reader can adapt to their situation?
- [ ] Links to reference for details?

**Reference Quality**:
- [ ] Descriptions match actual behavior (not outdated)?
- [ ] Examples work (not broken or misleading)?
- [ ] Format is consistent across similar items?
- [ ] Search-friendly (clear headings, keywords)?

**Explanation Quality**:
- [ ] Concepts are clarified (not more confusing)?
- [ ] Design rationale is clear?
- [ ] Alternatives are discussed fairly?
- [ ] Trade-offs are identified?

**General Quality**:
- [ ] Documentation builds without errors
- [ ] No broken links (internal or external)
- [ ] No spelling errors
- [ ] Code examples work
- [ ] Images load correctly
- [ ] If `release.md` is present, it reflects the actual publish path and handoff steps

**If quality issues found**:
- Return with feedback describing issues and how to improve

---

## Review Process

1. **Load work package**:
   - Read WP prompt file (e.g., `tasks/WP02-tutorials.md`)
   - Identify which documentation was created/updated

2. **Review each document** against checklists above

3. **Build documentation** and verify:
   ```bash
   ./build-docs.sh
   ```
   - Check for build errors/warnings
   - Navigate to docs in browser
   - Test links, images, navigation

4. **Test tutorials** (if present):
   - Follow tutorial steps exactly
   - Verify each step works
   - Confirm outcome is achieved

5. **Test how-tos** (if present):
   - Attempt to solve the problem using the guide
   - Verify solution works

6. **Validate generated reference** (if present):
   - Check auto-generated API docs
   - Verify all public APIs present
   - Check descriptions are clear

7. **Decide**:

   **If all checks pass**:
   - Move WP to "done" lane
   - Update activity log with approval
   - Proceed to next WP

   **If issues found**:
   - Populate Review Feedback section in WP prompt
   - List specific issues with locations and fix guidance
   - Set `review_status: has_feedback`
   - Move WP back to "planned" or "doing"
   - Notify implementer

---

## Review Feedback Format

When returning work for changes, use this format:

```markdown
## Review Feedback

### Divio Type Compliance

**Issue**: docs/tutorials/getting-started.md is classified as tutorial but reads like how-to (assumes too much prior knowledge).

**Fix**: Either:
- Reclassify as how-to (change frontmatter `type: how-to`)
- Rewrite to be learning-oriented for beginners (add prerequisites section, simplify steps, show results at each step)

### Accessibility

**Issue**: docs/tutorials/getting-started.md has image without alt text (line 45).

**Fix**: Add alt text describing what the image shows:
```markdown
![Screenshot showing the welcome screen after successful login](images/welcome.png)
```

### Inclusivity

**Issue**: docs/how-to/authentication.md uses only male names in examples ("Bob", "John", "Steve").

**Fix**: Use diverse names: "Aisha", "Yuki", "Carlos", "Alex".

### Completeness

**Issue**: Public API `DocumentGenerator.configure()` is not documented in reference.

**Fix**: Add entry to docs/reference/api.md or regenerate API docs if using auto-generation.

### Quality

**Issue**: Tutorial step 3 command fails (missing required --flag option).

**Fix**: Add --flag to command on line 67:
```bash
command --flag --other-option value
```
```

---

## Key Guidelines

**For Reviewers**:
- Focus on usability and accessibility, not perfection
- Provide specific, actionable feedback with line numbers
- Explain why something is an issue (educate, don't just reject)
- Test tutorials and how-tos by actually following them
- Check Divio type compliance carefully (most common issue)

**For Implementers**:
- Review feedback is guidance, not criticism
- Address all feedback items before re-submitting
- Mark `review_status: acknowledged` when you understand feedback
- Update activity log as you address each item

---

## Success Criteria

Documentation is ready for "done" when:
- [ ] All Divio type principles followed
- [ ] All accessibility checks pass
- [ ] All inclusivity checks pass
- [ ] All completeness requirements met
- [ ] All quality validations pass
- [ ] Documentation builds successfully
- [ ] Tutorials work when followed
- [ ] How-tos solve stated problems
- [ ] Reference is complete and accurate
- [ ] Explanations clarify concepts
