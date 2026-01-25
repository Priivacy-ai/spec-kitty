# GitHub Issues Analysis - 2026-01-25

Comprehensive analysis of all open GitHub issues against spec-kitty 0.13.0 codebase.

---

## Critical Issues (Fix Immediately)

### #101: UTF-8 encoding crash on Windows ⚠️ CRITICAL

**Status**: Open (2026-01-25)
**PR**: #100 (pending)
**Severity**: HIGH - Blocks Windows users from creating features

**Problem**: `write_text()` calls don't specify `encoding='utf-8'`, causing crashes on Windows when files contain UTF-8 characters.

**Root Cause**: Line 336 in `src/specify_cli/cli/commands/agent/feature.py`:
```python
path.write_text(content)  # ❌ No encoding specified
```

**Recommendation**: ✅ **MERGE PR #100 IMMEDIATELY**
- Windows represents ~40% of developer workstations
- This is a one-line fix per file
- Should be included in 0.13.0 or released as 0.13.1 hotfix
- Review PR #100, test on Windows, merge ASAP

**Priority**: P0 - Release blocker

---

### #97: Wrong suggestion after /spec-kitty.constitution ⚠️ MINOR

**Status**: Open (2026-01-24)
**PR**: #98 (pending)
**Severity**: LOW - Confusing but not blocking

**Problem**: After running `/spec-kitty.constitution`, template suggests `/spec-kitty.plan` instead of `/spec-kitty.specify`.

**Root Cause**: Line 422 in `.kittify/missions/software-dev/command-templates/constitution.md`

**Recommendation**: ✅ **MERGE PR #98**
- Simple documentation fix
- Improves user experience
- Can be included in 0.13.0 or next patch release

**Priority**: P1 - Include in next release

---

## Medium Priority Issues (Address Soon)

### #96: Missing --base parameter in agent workflow implement 🔧 FEATURE GAP

**Status**: Open (2026-01-24)
**Severity**: MEDIUM - Workaround exists but confusing

**Problem**: `spec-kitty agent workflow implement` lacks `--base` flag that exists in `spec-kitty implement`.

**Current State**:
| Command | Has --base | Creates Worktree | Outputs Prompt |
|---------|------------|------------------|----------------|
| `spec-kitty implement` | ✅ | ✅ | ❌ |
| `spec-kitty agent workflow implement` | ❌ | ❌ | ✅ |

**User Impact**:
- WP prompt files reference `spec-kitty implement --base`
- `/spec-kitty.implement` skill says to use `spec-kitty agent workflow implement`
- Confusion when dependencies exist between WPs

**Workaround**: Use `spec-kitty implement WP04 --base WP03` directly (works fine)

**Recommendation**: ✅ **DESIGN DECISION NEEDED**

**Option A: Add --base to agent workflow implement**
```python
# In src/specify_cli/cli/commands/agent/workflow.py
@click.option('--base', type=str, default=None,
              help='Base WP to branch from (delegates to top-level implement)')
```
When `--base` provided:
1. Call `spec-kitty implement WP_ID --base BASE_WP` internally
2. Then output prompt as normal

**Option B: Update documentation**
- Clarify that dependent WPs use `spec-kitty implement --base`
- Update WP prompt templates to show correct command
- Document the two-command workflow clearly

**My Recommendation**: **Option B** (documentation fix)
- Commands already work correctly
- Agent workflow is for prompts, implement is for worktrees
- Clear separation of concerns
- Less code complexity

**Action Items**:
1. Update WP prompt template to show both commands:
   ```markdown
   # Step 1: Create worktree (if WP has dependencies)
   spec-kitty implement WP04 --base WP03

   # Step 2: Get implementation prompt
   cd .worktrees/.../
   spec-kitty agent workflow implement WP04 --agent <name>
   ```
2. Update `/spec-kitty.implement` skill documentation
3. Add to FAQ: "How do I implement a WP that depends on another?"

**Priority**: P2 - Documentation update in 0.13.1

---

### #95: Kebab-case not always enforced 🤖 LLM BEHAVIOR

**Status**: Open (2026-01-23)
**Severity**: MEDIUM - Intermittent, agent-dependent

**Problem**: Agents sometimes create feature slugs with spaces instead of kebab-case, even though `specify.md` clearly states kebab-case is required.

**Symptoms**:
- Artifacts don't show in dashboard
- Implement phase fails (git branch names can't have spaces)

**Root Cause**: LLM agents don't always follow instructions perfectly, especially when:
- Instructions are far from the action point
- Multiple steps involved
- Agent is rushing to complete task

**Current Mitigation**: Template already says "kebab-case required"

**Recommendation**: ✅ **ENHANCE VALIDATION**

**Implementation**:
1. Add validation in `create_feature()` function:
   ```python
   # In src/specify_cli/cli/commands/agent/feature.py
   def validate_slug(slug: str) -> tuple[bool, str]:
       """Validate and suggest fixed slug."""
       if ' ' in slug or '_' in slug or slug != slug.lower():
           fixed = slug.lower().replace(' ', '-').replace('_', '-')
           return False, fixed
       return True, slug

   # Before creating feature:
   is_valid, fixed_slug = validate_slug(feature_slug)
   if not is_valid:
       raise click.UsageError(
           f"Feature slug must be kebab-case (lowercase with hyphens).\n"
           f"  Invalid: {feature_slug}\n"
           f"  Suggested: {fixed_slug}\n"
           f"Run command again with: --slug {fixed_slug}"
       )
   ```

2. Auto-fix option (aggressive):
   ```python
   # Auto-convert to kebab-case with warning
   if not is_valid:
       console.print(f"[yellow]⚠️  Slug converted: {feature_slug} → {fixed_slug}[/yellow]")
       feature_slug = fixed_slug
   ```

**My Recommendation**: **Option 2** (auto-fix with warning)
- Less friction for users
- Prevents workflow breakage
- Clear feedback about what happened
- Follows principle of "be liberal in what you accept"

**Priority**: P2 - Enhancement for 0.13.1 or 0.14.0

---

### #94: /spec-kit.dashboard typo doesn't work 🐛 SIMPLE FIX

**Status**: Open (2026-01-23)
**Severity**: LOW - User typo, not a bug

**Problem**: User typed `/spec-kit.dashboard` instead of `/spec-kitty.dashboard`

**Analysis**: This is a typo, not a bug. The correct command is documented.

**Recommendation**: ❌ **CLOSE AS USER ERROR**
- Add to FAQ: Common typos and correct commands
- Optionally: Add command alias detection in agent slash commands
- Consider adding `.github/ISSUE_TEMPLATE/bug_report.md` with checklist:
  - [ ] I checked for typos in the command
  - [ ] I verified this command exists in the documentation

**Priority**: P3 - Close with kind explanation, add to FAQ

---

### #93: Research mission auto-detect not working 🔬 NEEDS INVESTIGATION

**Status**: Open (2026-01-23)
**Severity**: MEDIUM - Research mission users affected

**Problem**:
1. `--mission` flag deprecated (expected)
2. LLM correctly identifies research mission (good)
3. `/research` directory created (good)
4. `spec-kitty mission current` shows "Software Dev Kitty" (BUG)

**Relevant Files**:
- `src/specify_cli/cli/commands/mission.py` - Current mission detection
- `src/specify_cli/missions/` - Mission definitions

**Recommendation**: ✅ **INVESTIGATE & FIX**

**Action Items**:
1. Check `get_current_mission()` logic in mission.py
2. Verify `meta.json` is being created with correct mission field
3. Add test case:
   ```python
   def test_research_mission_detection_in_meta_json():
       # Create research feature
       # Verify meta.json has "mission": "research"
       # Verify spec-kitty mission current outputs "Research"
   ```
4. Add validation during feature creation that mission is persisted correctly

**Expected Behavior**: `spec-kitty mission current` should read from:
1. `kitty-specs/<feature>/meta.json` (feature-specific mission)
2. Fall back to `.kittify/config.yaml` (project default)

**Priority**: P1 - Bug fix for 0.13.1

---

## Feature Requests (Evaluate for Roadmap)

### #84: Dashboard "blocked by" markers 📊 ENHANCEMENT

**Status**: Open (2026-01-20)
**Request**: Add "blocked by" indicator to dashboard Kanban cards

**Analysis**:
- Dependency information already in WP frontmatter (`dependencies: []`)
- Dashboard already has access to this data
- Would improve parallel workflow visibility

**Recommendation**: ✅ **ACCEPT FOR 0.14.0**

**Implementation Plan**:
```python
# In dashboard scanner
def scan_feature_kanban(feature_path: Path) -> list[KanbanCard]:
    for wp in work_packages:
        # Parse dependencies from frontmatter
        deps = wp.frontmatter.get('dependencies', [])
        if deps:
            card.badges.append({
                'text': f'Blocked by: {", ".join(deps)}',
                'color': 'orange',
                'icon': '🔒'
            })
```

**UI Mockup**:
```
┌─────────────────────────┐
│ WP04: Implement API     │
│                         │
│ 🔒 Blocked by: WP02, WP03│
│ 👤 Assigned: Claude     │
└─────────────────────────┘
```

**Priority**: P2 - Feature enhancement for 0.14.0

---

### #51: spec-kitty add-agent command ✅ ALREADY IMPLEMENTED!

**Status**: Open (2025-12-17)
**Request**: Add command to safely add agents after initialization

**Analysis**: ✅ **THIS WAS IMPLEMENTED IN 0.12.0!**

Feature 022 (Config-Driven Agent Management) added:
- `spec-kitty agent config add <agents>`
- `spec-kitty agent config remove <agents>`
- `spec-kitty agent config list`
- `spec-kitty agent config status`
- `spec-kitty agent config sync`

**Recommendation**: ✅ **CLOSE AS COMPLETED**

**Response to issue**:
```markdown
@[author] Great news! This feature was implemented in version 0.12.0 as part of the config-driven agent management system.

You can now add agents after initialization using:

bash
spec-kitty agent config add gemini,cursor,qwen


Available commands:
- `spec-kitty agent config add <agents>` - Add agents to project
- `spec-kitty agent config remove <agents>` - Remove agents
- `spec-kitty agent config list` - Show configured agents
- `spec-kitty agent config status` - Show configured vs orphaned
- `spec-kitty agent config sync` - Sync filesystem with config

This is exactly what you requested! See CHANGELOG v0.12.0 for details.

Thanks for the feature request - it's now live!
```

**Priority**: P0 - Close immediately with success message

---

### #39: Template update command 🔄 COMPLEX FEATURE

**Status**: Open (2025-11-20)
**Request**: `spec-kitty update` command to merge template changes without overwriting customizations

**Analysis**:
- Complex problem: How to merge upstream template changes with local customizations?
- Git history of templates not available (templates are in package, not git)
- Similar to system package managers (apt, brew) updating config files

**Current Workaround**:
```bash
spec-kitty init . --ai claude,gemini --force
git checkout HEAD -- .kittify/
```

**Recommendation**: ⚠️ **DEFER TO 0.15.0+ (Complex)**

**Why Defer**:
1. Requires template version tracking system
2. Need merge strategy (3-way merge? Interactive?)
3. What if template structure changed fundamentally?
4. Risk of breaking working projects

**Better Short-Term Solution**: Documentation
Add to docs: "How to update templates safely"
```markdown
## Updating Templates After Upgrade

Spec-kitty templates are versioned with the CLI. When you upgrade:

### Option 1: Fresh Init (Destructive)
bash
Back up customizations
cp -r .kittify/memory ./backup-memory
cp .kittify/missions/software-dev/mission.yaml ./backup-mission.yaml
Re-init with new templates
spec-kitty init . --ai <agents> --force
Restore customizations
cp -r ./backup-memory .kittify/memory
cp ./backup-mission.yaml .kittify/missions/software-dev/


### Option 2: Manual Merge
bash
Download new templates to temp location
spec-kitty init /tmp/fresh-project --ai <agents>
Manually compare and merge
diff -r .kittify /tmp/fresh-project/.kittify
Use your editor to merge desired changes


### Option 3: Accept Current Templates
If templates work for you, no action needed. Templates are backward compatible.
```

**Future Enhancement** (0.15.0+):
```bash
spec-kitty upgrade --templates
  - Shows diff of template changes
  - Interactive merge for conflicts
  - Preserves customizations automatically
```

**Priority**: P3 - Defer to 0.15.0, document workarounds now

---

## Speculative/Low Priority

### #83: venv installation issues 🐍 USER ENVIRONMENT

**Status**: Open (2026-01-19)
**Problem**: Frequent venv/installation issues

**Analysis**: This is an environmental issue, not a spec-kitty bug.

**Common Causes**:
1. Multiple Python versions
2. Virtual environment activation issues
3. PATH problems
4. Different agents using different Python interpreters

**Recommendation**: ✅ **IMPROVE DOCUMENTATION**

Add to docs: "Troubleshooting Installation"
```markdown
## Common Installation Issues

### "spec-kitty: command not found"

Cause: spec-kitty not in PATH

Solution:
bash
Use full path
python -m specify_cli.cli --version
Or install with pipx (recommended)
pipx install spec-kitty-cli


### "Version mismatch" or "ModuleNotFoundError"

Cause: Multiple installations or cached imports

Solution:
bash
Uninstall all versions
pip uninstall spec-kitty-cli -y
pipx uninstall spec-kitty-cli
Clear cache
pip cache purge
Reinstall
pipx install spec-kitty-cli


### "Permission denied"

Cause: System Python protection

Solution:
bash
Use virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install spec-kitty-cli
```

**Priority**: P3 - Documentation improvement

---

### #78: Multilevel worktree idea 💡 ARCHITECTURE CHANGE

**Status**: Open (2026-01-15)
**Proposal**: Feature worktree with WP sub-worktrees

**Analysis**: Interesting idea but conflicts with current architecture.

**Current Model (0.11.0+)**:
```
main
  └── .worktrees/
      ├── feature-001-WP01/
      ├── feature-001-WP02/
      └── feature-001-WP03/
```

**Proposed Model**:
```
main
  └── .worktrees/
      └── feature-001/  (feature worktree)
          ├── WP01/  (sub-worktree)
          ├── WP02/  (sub-worktree)
          └── WP03/  (sub-worktree)
```

**Recommendation**: ❌ **CLOSE AS WONTFIX**

**Reasons**:
1. **Git limitation**: Worktrees can't contain other worktrees (git restriction)
2. **Current model works**: Planning in main, WPs in worktrees is proven
3. **Added complexity**: Sub-worktrees would complicate merge logic
4. **No clear benefit**: What problem does this solve?

**Alternative**: Current model already achieves goals:
- Planning in main (spec, plan, tasks.md)
- Parallel WP development (each WP has worktree)
- Dependency tracking (frontmatter dependencies field)

**Response to issue**:
```markdown
Thanks for the suggestion! Unfortunately, git doesn't support nested worktrees (a worktree can't contain another worktree).

The current 0.11.0+ model achieves similar benefits:
- Planning happens in main repo
- Each WP gets its own worktree (parallel development)
- Dependencies tracked in frontmatter

Closing as the requested architecture isn't possible with git's worktree implementation.

The workflow table you shared is great! We'll consider adding something similar to the docs.
```

**Priority**: P3 - Close with explanation

---

### #76: Google Antigravity support 🚀 AGENT REQUEST

**Status**: Open (2026-01-13)
**Request**: Add support for Google Antigravity editor

**Analysis**:
- Google Antigravity (antigravity.google) is mentioned
- Gemini 3 integration desired
- Unclear if Antigravity has slash command support

**Recommendation**: ⚠️ **NEEDS MORE INFO**

**Questions**:
1. Does Google Antigravity support agent slash commands? (Like Claude Code, Cursor, etc.)
2. What directory structure does it use? (`.antigravity/`?)
3. Is this widely available or beta?
4. Can we test it?

**Action Items**:
1. Research Google Antigravity's agent capabilities
2. If it supports slash commands:
   - Add to `AGENT_DIRS` in migrations
   - Create `.antigravity/` template structure
   - Add to supported agents list
3. If no slash command support:
   - Users can still use `spec-kitty` CLI directly
   - No template integration needed

**Priority**: P3 - Research needed, defer until more info

---

### #67: Monorepo support 📦 ARCHITECTURE CHANGE

**Status**: Open (2026-01-06)
**Request**: Support for monorepo with nested AGENT.MD files to shard context

**Analysis**:
- Spec-kitty is currently designed for single-repo
- Monorepo would need:
  - Multiple `.kittify/` directories (per workspace?)
  - Separate constitution per workspace
  - Shared or separate worktrees?

**Recommendation**: ⚠️ **DEFER TO 1.0.0 (Major Architecture)**

**Why Defer**:
1. **Unclear requirements**: What's the exact use case?
2. **Design needed**: How should features span workspaces?
3. **Breaking change**: Would require rethinking core assumptions
4. **AGENT.MD sharding**: Not related to spec-kitty (that's agent feature)

**Current Workaround**:
```bash
# Each workspace is separate spec-kitty project
monorepo/
  packages/
    frontend/
      .kittify/  # Frontend spec-kitty
    backend/
      .kittify/  # Backend spec-kitty
    shared/
      .kittify/  # Shared spec-kitty
```

**Future Consideration** (1.0.0+):
- Shared constitution at repo root
- Workspace-specific features
- Cross-workspace dependency tracking

**Priority**: P4 - Defer to 1.0.0, document workarounds

---

### #65: Avoid new request for each question 💰 COST OPTIMIZATION

**Status**: Open (2026-01-06)
**Request**: Use `input()` instead of `WAITING_FOR_*_INPUT` to stay in same request

**Analysis**:
- Currently: Agent ends request with `WAITING_FOR_PLANNING_INPUT`, user responds, new request
- Proposed: Use `uv run python -c "input('Your answer: ')"` in same request
- Impact: Saves LLM API costs (fewer requests)

**Recommendation**: ⚠️ **EVALUATE FOR 0.14.0**

**Pros**:
- Reduces API costs (important for users)
- Keeps conversation in single context
- Simpler workflow

**Cons**:
- May not work in all agent environments
- Less control flow visibility
- Harder to debug failures

**Action Items**:
1. Test `input()` approach with major agents:
   - Claude Code
   - GitHub Copilot
   - Cursor
   - Gemini
2. Verify it works in:
   - Terminal contexts
   - Web interfaces (claude.ai)
   - VS Code extensions
3. If successful, update all templates

**My Recommendation**: ✅ **TEST AND IMPLEMENT**
- If it works across agents, this is a clear win
- If it breaks some environments, make it configurable
- Add to `.kittify/config.yaml`:
  ```yaml
  agent_interaction:
    use_inline_input: true  # Use input() vs WAITING markers
  ```

**Priority**: P2 - Test in 0.13.x, implement in 0.14.0 if successful

---

## Summary & Recommendations

### Immediate Actions (Include in 0.13.0/0.13.1)

1. ✅ **MERGE PR #100** - UTF-8 encoding fix (P0 - Critical)
2. ✅ **MERGE PR #98** - Constitution template fix (P1 - Minor)
3. ✅ **CLOSE #51** - Already implemented in 0.12.0 (Success story!)
4. ✅ **INVESTIGATE #93** - Research mission detection bug (P1 - Bug)

### Documentation Updates (0.13.1)

5. ✅ **UPDATE #96** - Document two-command workflow for dependent WPs
6. ✅ **ENHANCE #83** - Troubleshooting installation guide
7. ✅ **FAQ #94** - Common command typos

### Feature Enhancements (0.14.0)

8. ✅ **IMPLEMENT #95** - Auto-fix slug to kebab-case with warning
9. ✅ **IMPLEMENT #84** - Dashboard blocked-by indicators
10. ✅ **EVALUATE #65** - Test inline input() approach

### Research/Defer

11. ⚠️ **RESEARCH #76** - Google Antigravity agent support (need more info)
12. ⚠️ **DEFER #39** - Template update command to 0.15.0 (complex)
13. ⚠️ **DEFER #67** - Monorepo support to 1.0.0 (architecture change)
14. ❌ **CLOSE #78** - Multilevel worktrees (git limitation)

### Issue Triage Summary

- **Close Immediately**: #51 (✅ completed), #78 (❌ not possible), #94 (user error)
- **Fix in 0.13.1**: #100, #98, #93
- **Document**: #96, #83
- **Enhance in 0.14.0**: #95, #84, #65
- **Research**: #76
- **Long-term**: #39 (0.15.0), #67 (1.0.0)

---

## Recommended Issue Labels

Suggest adding these labels to organize issues:

- `P0-critical` - Blocks users, fix immediately
- `P1-bug` - Confirmed bugs, fix soon
- `P2-enhancement` - Approved features, next minor version
- `P3-future` - Good ideas, defer to later
- `P4-wontfix` - Declining to implement
- `windows` - Windows-specific issues
- `documentation` - Docs improvements needed
- `agent-specific` - Specific to one agent
- `research-mission` - Research mission related
- `dashboard` - Dashboard feature
- `workflow` - Workflow/UX improvements

This would make issue triage much clearer for contributors and users.
