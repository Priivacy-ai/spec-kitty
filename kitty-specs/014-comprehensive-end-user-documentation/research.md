# Research: Documentation Audit & Coverage Analysis

**Feature**: 014-comprehensive-end-user-documentation
**Date**: 2026-01-16
**Purpose**: Audit existing documentation, assess accuracy, identify gaps, and plan Divio restructure

## Executive Summary

The existing documentation in `docs/` is **woefully outdated** compared to the 0.11.0 release. Key issues:

1. **index.md** (869 lines) tries to be tutorial + reference + explanation simultaneously
2. **quickstart.md** references deprecated `/tasks/planned/` directory structure
3. Most docs reference the pre-0.11.0 worktree-per-feature model
4. No clear Divio structure - content is mixed randomly
5. Some excellent content exists (workspace-per-wp.md, upgrading-to-0-11-0.md) that should be preserved

**Recommendation**: Complete restructure with aggressive cleanup. Preserve ~30% of content, rewrite ~70%.

---

## Part 1: Existing Documentation Inventory

### Files in `docs/` Directory

| File | Lines | Accuracy | Divio Type | Verdict |
|------|-------|----------|------------|---------|
| `index.md` | 869 | ⚠️ Outdated | Mixed (all types) | **Rewrite** - Too long, mixed types, outdated worktree model |
| `quickstart.md` | 209 | ⚠️ Outdated | Tutorial | **Rewrite** - References `/tasks/planned/` (deprecated) |
| `installation.md` | 145 | ✅ Accurate | How-To | **Keep** - Good installation instructions |
| `workspace-per-wp.md` | 570 | ✅ Accurate | Explanation | **Keep** - Excellent 0.11.0 explanation |
| `upgrading-to-0-11-0.md` | 530 | ✅ Accurate | How-To | **Keep** - Comprehensive upgrade guide |
| `README.md` | ~50 | ⚠️ Partial | Landing | **Rewrite** - Placeholder only |
| `ARCHITECTURE.md` | ? | ⚠️ Unknown | Explanation | **Audit** - Check for accuracy |
| `WORKTREE_MODEL.md` | ? | ⚠️ Unknown | Explanation | **Audit** - Likely outdated |
| `claude-code-integration.md` | ? | ⚠️ Unknown | How-To | **Audit** - Check for accuracy |
| `claude-code-workflow.md` | ? | ⚠️ Unknown | Tutorial | **Audit** - Check for accuracy |
| `documentation-mission.md` | ? | ✅ Likely accurate | Explanation | **Keep** - Recent addition |
| `kanban-dashboard-guide.md` | ? | ⚠️ Unknown | How-To | **Audit** - Check for accuracy |
| `local-development.md` | ? | ⚠️ Unknown | How-To | **Audit** - For contributors, out of scope? |
| `multi-agent-orchestration.md` | ? | ⚠️ Unknown | Explanation | **Audit** - Check for accuracy |
| `spec-workflow-automation.md` | ? | ⚠️ Unknown | Reference | **Audit** - Check for accuracy |
| `task-metadata-validation.md` | ? | ⚠️ Unknown | Reference | **Audit** - Check for accuracy |
| `testing-guidelines.md` | ? | N/A | N/A | **Remove** - Contributor doc, out of scope |
| `plan-validation-guardrail.md` | ? | ⚠️ Unknown | Reference | **Audit** - Check for accuracy |
| `non-interactive-init.md` | ? | ⚠️ Unknown | How-To | **Audit** - Check for accuracy |
| `encoding-requirements.md` | ? | ⚠️ Unknown | Reference | **Audit** - Check for accuracy |
| `encoding-validation.md` | ? | ⚠️ Unknown | Reference | **Audit** - Check for accuracy |
| `CONTEXT_SWITCHING_GUIDE.md` | ? | ⚠️ Unknown | How-To | **Audit** - Check for accuracy |
| `releases/readiness-checklist.md` | ? | N/A | N/A | **Remove** - Contributor doc, out of scope |

### Summary Statistics

- **Total files**: ~23
- **Accurate**: 4 (installation.md, workspace-per-wp.md, upgrading-to-0-11-0.md, documentation-mission.md)
- **Outdated**: 6+ (index.md, quickstart.md, WORKTREE_MODEL.md, others)
- **Unknown**: 10+ (need deeper audit)
- **Out of scope**: 2+ (contributor docs)

---

## Part 2: Detailed Accuracy Assessment

### index.md - ⚠️ MAJOR ISSUES

**Problems identified**:

1. **Line 169-170**: "move into the dedicated worktree it creates" - **WRONG** for 0.11.0
   - Old: `/spec-kitty.specify` creates worktree
   - New: Planning happens in main, no worktree created

2. **Lines 356-393**: Worktree Strategy section - **OUTDATED**
   - Documents old workspace-per-feature model
   - Pattern shown: `.worktrees/001-auth-system/` (old)
   - Should be: `.worktrees/001-auth-system-WP01/` (new)

3. **Lines 380-393**: Complete Workflow - **WRONG**
   - Shows `cd .worktrees/001-my-feature` after specify
   - This is the OLD model; new model stays in main

4. **Lines 398-400**: "Once every work package lives in `tasks/done/`" - **WRONG**
   - Lane is tracked in frontmatter, not directory location
   - No `tasks/done/` directory exists in 0.11.0

5. **Lines 456-458**: WP files live in flat `tasks/` directory - **CORRECT**
   - This is accurate for 0.11.0

6. **Lines 462-482**: Mission System - **OUTDATED**
   - References `spec-kitty mission switch` which was REMOVED in v0.8.0
   - Missions are now per-feature during specify

**Salvageable content**:

- Supported AI Agents table (lines 234-249) - accurate
- Installation commands (lines 82-132) - accurate
- Dashboard section (lines 27-49) - accurate
- Prerequisites (lines 532-538) - accurate

### quickstart.md - ⚠️ OUTDATED

**Problems identified**:

1. **Lines 107-109**: "produce items under `/tasks/planned/`" - **WRONG**
   - Old model: `tasks/planned/`, `tasks/doing/`, `tasks/for_review/`, `tasks/done/`
   - New model: Flat `tasks/` with `lane:` in frontmatter

2. **Lines 89-90**: "Change into that directory before running planning" - **WRONG**
   - New model: Planning happens in main, no worktree to cd into

3. **Lines 113-119**: Accept & Merge section - **PARTIALLY OUTDATED**
   - References `/tasks/done/` directory (doesn't exist)
   - Accept/merge commands themselves are accurate

**Salvageable content**:

- Installation section (lines 24-46) - accurate
- Key Principles (lines 196-204) - accurate

### installation.md - ✅ MOSTLY ACCURATE

**Assessment**: Good quality, minor updates needed.

**Minor issues**:

- Line 103: References "Cross-Platform Python CLI (v0.10.0+)" but we're on 0.11.0
- Line 107: References MIGRATION-v0.10.0.md which may not exist

**Salvageable**: 95% - excellent how-to content

### workspace-per-wp.md - ✅ ACCURATE

**Assessment**: Excellent quality, comprehensive explanation of 0.11.0 model.

**Content**:

- Correct workflow comparison (old vs new)
- Correct dependency syntax
- Correct troubleshooting
- Excellent diagrams of dependency patterns

**Salvageable**: 100% - should become primary explanation doc

### upgrading-to-0-11-0.md - ✅ ACCURATE

**Assessment**: Comprehensive upgrade guide, well-structured.

**Content**:

- Pre-upgrade checklist (accurate)
- Step-by-step migration (accurate)
- Troubleshooting (accurate)
- New commands documentation (accurate)

**Salvageable**: 100% - should become primary upgrade how-to

---

## Part 3: Coverage Matrix

### Feature/Concept × Divio Type Coverage

| Feature/Concept | Tutorial | How-To | Reference | Explanation |
|-----------------|----------|--------|-----------|-------------|
| **Installation** | ❌ Missing | ✅ installation.md | ⚠️ Partial in index.md | ❌ Missing |
| **Quickstart (first feature)** | ⚠️ Outdated | ❌ Missing | ❌ Missing | ❌ Missing |
| **Missions (software-dev)** | ❌ Missing | ❌ Missing | ⚠️ Partial | ❌ Missing |
| **Missions (research)** | ❌ Missing | ❌ Missing | ❌ Missing | ❌ Missing |
| **Missions (documentation)** | ❌ Missing | ❌ Missing | ⚠️ Partial | ✅ documentation-mission.md |
| **Upgrading** | ❌ N/A | ✅ upgrading-to-0-11-0.md | ❌ Missing | ❌ Missing |
| **Workspace-per-WP model** | ❌ Missing | ⚠️ Partial | ❌ Missing | ✅ workspace-per-wp.md |
| **Philosophy (SDD)** | ❌ Missing | ❌ Missing | ❌ Missing | ⚠️ Outdated in index.md |
| **Dashboard** | ❌ Missing | ⚠️ Partial | ❌ Missing | ❌ Missing |
| **Dependencies** | ❌ Missing | ⚠️ In workspace-per-wp.md | ❌ Missing | ✅ In workspace-per-wp.md |
| **Git Worktrees** | ❌ Missing | ❌ Missing | ❌ Missing | ⚠️ Partial in workspace-per-wp.md |
| **Sparse Checkouts** | ❌ Missing | ❌ Missing | ❌ Missing | ❌ Missing |

### Slash Command Coverage

| Command | Tutorial | How-To | Reference |
|---------|----------|--------|-----------|
| `/spec-kitty.specify` | ⚠️ Outdated | ❌ Missing | ⚠️ Partial |
| `/spec-kitty.plan` | ⚠️ Outdated | ❌ Missing | ⚠️ Partial |
| `/spec-kitty.tasks` | ⚠️ Outdated | ❌ Missing | ⚠️ Partial |
| `/spec-kitty.implement` | ⚠️ Outdated | ❌ Missing | ⚠️ Partial |
| `/spec-kitty.review` | ⚠️ Outdated | ❌ Missing | ⚠️ Partial |
| `/spec-kitty.accept` | ⚠️ Outdated | ❌ Missing | ⚠️ Partial |
| `/spec-kitty.merge` | ⚠️ Outdated | ❌ Missing | ⚠️ Partial |
| `/spec-kitty.status` | ❌ Missing | ❌ Missing | ❌ Missing |
| `/spec-kitty.dashboard` | ❌ Missing | ❌ Missing | ⚠️ Partial |
| `/spec-kitty.constitution` | ❌ Missing | ❌ Missing | ⚠️ Partial |
| `/spec-kitty.clarify` | ❌ Missing | ❌ Missing | ⚠️ Partial |
| `/spec-kitty.research` | ❌ Missing | ❌ Missing | ⚠️ Partial |
| `/spec-kitty.checklist` | ❌ Missing | ❌ Missing | ⚠️ Partial |
| `/spec-kitty.analyze` | ❌ Missing | ❌ Missing | ⚠️ Partial |

### CLI Command Coverage

| Command | Reference Doc |
|---------|---------------|
| `spec-kitty init` | ⚠️ Partial in index.md |
| `spec-kitty upgrade` | ✅ upgrading-to-0-11-0.md |
| `spec-kitty implement` | ✅ workspace-per-wp.md |
| `spec-kitty accept` | ⚠️ Partial |
| `spec-kitty merge` | ⚠️ Partial |
| `spec-kitty dashboard` | ⚠️ Partial |
| `spec-kitty research` | ❌ Missing |
| `spec-kitty mission list/current/info` | ❌ Missing |
| `spec-kitty agent feature *` | ❌ Missing |
| `spec-kitty agent tasks *` | ❌ Missing |
| `spec-kitty agent workflow *` | ❌ Missing |
| `spec-kitty agent context *` | ❌ Missing |
| `spec-kitty agent release *` | ❌ Missing |
| `spec-kitty validate-encoding` | ❌ Missing |
| `spec-kitty validate-tasks` | ❌ Missing |
| `spec-kitty verify-setup` | ❌ Missing |
| `spec-kitty list-legacy-features` | ✅ upgrading-to-0-11-0.md |
| `spec-kitty repair` | ❌ Missing |

---

## Part 4: Gap Analysis Summary

### HIGH Priority Gaps (blocks user adoption)

1. **No accurate Getting Started tutorial** - quickstart.md is outdated
2. **No complete workflow tutorial** for 0.11.0 model
3. **No reference documentation** for slash commands (only scattered partial info)
4. **No reference documentation** for CLI commands (especially `spec-kitty agent *`)

### MEDIUM Priority Gaps

5. **Mission documentation incomplete** - software-dev and research missions not documented
6. **No how-to guides** for common tasks (review WP, handle dependencies, etc.)
7. **Dashboard usage** not properly documented
8. **Parallel development** workflow not explained for end users

### LOW Priority Gaps

9. **Philosophy/explanation** content is outdated but less critical
10. **Environment variables** not comprehensively documented
11. **File structure** not documented (where is everything?)

---

## Part 5: Content Migration Plan

### Files to KEEP (migrate to Divio structure)

| Source | Target | Notes |
|--------|--------|-------|
| `installation.md` | `how-to/install-and-upgrade.md` | Merge with upgrade content |
| `workspace-per-wp.md` | `explanation/workspace-per-wp.md` | Keep as-is, add cross-refs |
| `upgrading-to-0-11-0.md` | `how-to/upgrade-to-0-11-0.md` | Keep as-is |
| `documentation-mission.md` | `explanation/documentation-mission.md` | Keep as-is |

### Files to REWRITE

| Source | Target | Notes |
|--------|--------|-------|
| `index.md` | `index.md` | Complete rewrite as landing page with Divio navigation |
| `quickstart.md` | `tutorials/getting-started.md` | Complete rewrite for 0.11.0 |
| `README.md` | Remove | Redirect to index.md |

### Files to REMOVE (out of scope or redundant)

| File | Reason |
|------|--------|
| `testing-guidelines.md` | Contributor doc, out of scope for end-user documentation |
| `releases/readiness-checklist.md` | Contributor doc, out of scope for end-user documentation |
| `local-development.md` | Contributor doc, out of scope for end-user documentation |
| `WORKTREE_MODEL.md` | Replaced by workspace-per-wp.md (more comprehensive) |
| `ARCHITECTURE.md` | Contributor/internal doc; architecture details belong in CLAUDE.md or contributor docs |
| `CONTEXT_SWITCHING_GUIDE.md` | Contributor-focused guide for development context; not relevant to end users |
| `encoding-requirements.md` | Internal validation requirements; CLI handles this automatically for users |
| `encoding-validation.md` | Internal validation implementation details; not needed by end users |
| `plan-validation-guardrail.md` | Internal validation guardrail details; CLI handles automatically |
| `spec-workflow-automation.md` | Contributor doc describing internal workflow automation |
| `task-metadata-validation.md` | Internal validation implementation; not needed by end users |

**Justification for internal/contributor doc removal**: These files document internal implementation details, contributor guidelines, or validation mechanisms that the CLI handles automatically. End users don't need to understand these internals—they just use the slash commands. Contributor documentation belongs in CONTRIBUTING.md, CLAUDE.md, or AGENTS.md (already present in repo root).

### Files to CREATE (new content)

| File | Divio Type | Content |
|------|------------|---------|
| `tutorials/your-first-feature.md` | Tutorial | End-to-end 0.11.0 workflow |
| `tutorials/missions-overview.md` | Tutorial | Using different missions |
| `how-to/create-specification.md` | How-To | /spec-kitty.specify workflow |
| `how-to/create-plan.md` | How-To | /spec-kitty.plan workflow |
| `how-to/generate-tasks.md` | How-To | /spec-kitty.tasks workflow |
| `how-to/implement-work-package.md` | How-To | /spec-kitty.implement workflow |
| `how-to/review-work-package.md` | How-To | /spec-kitty.review workflow |
| `how-to/accept-and-merge.md` | How-To | /spec-kitty.accept + merge |
| `how-to/handle-dependencies.md` | How-To | WP dependencies |
| `how-to/use-dashboard.md` | How-To | Dashboard usage |
| `reference/cli-commands.md` | Reference | All CLI commands |
| `reference/slash-commands.md` | Reference | All slash commands |
| `reference/agent-subcommands.md` | Reference | spec-kitty agent * |
| `reference/missions.md` | Reference | Mission details |
| `reference/supported-agents.md` | Reference | All 12 agents |
| `reference/file-structure.md` | Reference | Directory layout |
| `reference/environment-variables.md` | Reference | Env vars |
| `explanation/spec-driven-development.md` | Explanation | Philosophy |
| `explanation/git-worktrees.md` | Explanation | Git worktrees for spec-kitty users (what, why, how) |
| `explanation/mission-system.md` | Explanation | Why missions exist |
| `explanation/kanban-workflow.md` | Explanation | Lane workflow |

---

## Part 6: Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Divio structure | 4 subdirectories | Industry standard, clear separation |
| index.md approach | Complete rewrite | Current version is unmaintainable |
| Contributor docs | Remove | Out of scope (end-user focus) |
| workspace-per-wp.md | Preserve | Excellent accurate content |
| CLI reference | Generate from --help | Single source of truth |
| Slash command reference | Generate from templates | Consistent, accurate |

---

## Part 7: Work Package Estimation

Based on the gap analysis, estimated work packages:

| WP | Description | Effort |
|----|-------------|--------|
| WP01 | Audit & remove outdated docs | Small |
| WP02 | Create Divio directory structure | Small |
| WP03 | Rewrite index.md landing page | Medium |
| WP04 | Create getting-started tutorial | Large |
| WP05 | Create your-first-feature tutorial | Large |
| WP06 | Create how-to guides (batch 1: specify, plan, tasks) | Large |
| WP07 | Create how-to guides (batch 2: implement, review, merge) | Large |
| WP08 | Create reference docs (CLI + slash commands) | Large |
| WP09 | Create explanation docs | Medium |
| WP10 | Update toc.yml and cross-references | Medium |
| WP11 | Validate DocFX build and test | Small |

**Total estimated WPs**: 11
