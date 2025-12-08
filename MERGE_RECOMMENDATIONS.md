# Spec Kit → Spec Kitty Merge Recommendations

**Generated:** December 8, 2025
**Analysis Basis:** 251 upstream commits reviewed (Oct 1 - Dec 8, 2025)
**Recommendation:** Cherry-pick only critical fixes; skip 96% of upstream commits

---

## Executive Summary

Spec Kit and Spec Kitty have diverged significantly. Most upstream changes are not applicable due to architectural differences:

| Metric | Value |
|--------|-------|
| Total commits analyzed | 251 |
| **Recommended to merge** | **1** (CDPATH fix) |
| Conditionally merge | 5-8 |
| Skip/Not applicable | 242 |
| **Merge success rate** | **0.4%** |

**Key Finding:** The 96% "skip" rate reflects **deliberate architectural divergence**, not neglect. Spec Kitty's worktree-based approach, mission system, and dashboard are incompatible with Spec Kit's branch-centric design.

---

## Quick Decision Matrix

| Commit | Type | Priority | Recommendation | Effort |
|--------|------|----------|-----------------|--------|
| 2a7c2e93 | CDPATH fix | 🔴 HIGH | **MERGE NOW** | 1hr |
| 098380a4 | IDE agent CLI skip | 🟡 MEDIUM | **REVIEW & MERGE** | 2hrs |
| 236bcb39 | Existing project docs | 🟡 MEDIUM | **MERGE (adapted)** | 2hrs |
| af2b14e9 | Escaping guidelines | 🟡 MEDIUM | **REVIEW & ADAPT** | 2hrs |
| b40b41cf | Remote branch detection | 🟡 MEDIUM | **CONDITIONAL** | 3hrs |
| 8d552e6d, 537f349f, b291a6ef | New agents | 🟢 LOW | **DEFER** | TBD |
| All VS Code commits | VS Code integration | 🟢 LOW | **SKIP** | — |
| Release/packaging commits | Release workflow | 🟢 LOW | **SKIP** | — |
| Devcontainer config | Dev environment | 🟢 LOW | **SKIP** | — |

---

## 🔴 PHASE 1: Critical (Do This Week)

### 1. CDPATH Fix (Commit 2a7c2e93)
**Status:** ⚠️ **NOT YET APPLIED**

Apply this fix to prevent script failures when users have `CDPATH` environment variable set:

**Files to update:**
- `scripts/bash/common.sh`
- `scripts/bash/create-new-feature.sh`
- `scripts/bash/check-prerequisites.sh`
- `scripts/bash/update-agent-context.sh`
- `scripts/bash/setup-plan.sh`

**Change (in each file):**
```bash
# Line 2-3 of each script:
# Before:
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# After:
SCRIPT_DIR="$(unset CDPATH && cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
```

**Testing:**
```bash
# Test that scripts still work with CDPATH set
CDPATH=/tmp .kittify/scripts/bash/create-new-feature.sh --help
```

**Commit message:**
```
fix: Unset CDPATH in bash scripts to prevent directory resolution issues

Prevents rare but hard-to-debug script failures when users have
CDPATH environment variable set. Aligns with upstream Spec Kit
commit 2a7c2e93.
```

---

## 🟡 PHASE 2: Medium Priority (Next 2 Weeks)

### 2. Skip CLI Checks for IDE Agents (Commit 098380a4)
**Status:** ⚠️ **NEEDS REVIEW**

Current issue: Spec Kitty checks if CLI agent (e.g., `claude`, `cursor`) exists, but fails for IDE-integrated agents.

**Review needed for:**
- `src/specify_cli/__init__.py` (check command)

**Proposed change:**
```python
# In agent validation logic:
IDE_AGENTS = {'cursor', 'windsurf', 'vscode', 'bob'}

if agent_name not in IDE_AGENTS:
    # Check CLI availability only for non-IDE agents
    verify_agent_installed(agent_name)
```

**Test coverage needed:**
- Cursor agent (should skip CLI check)
- Windsurf agent (should skip CLI check)
- Claude CLI agent (should check CLI)

**Decision needed:** Is this important for your user base? Defer if users haven't requested.

---

### 3. Documentation: Existing Project Integration (Commit 236bcb39)
**Status:** 📖 **REVIEW FOR ADAPTATION**

Upstream docs for adding Spec Kit to existing projects are strong. Adapt for Spec Kitty:

**Work:**
- Review upstream `CONTRIBUTING.md` additions
- Adapt path references from `.specify/` to `.kittify/`
- Add Spec Kitty-specific examples
- Update `README.md` with clearer "add to existing project" section

**Estimated effort:** 2 hours

**Value:** Better UX for users adding Spec Kitty to ongoing projects

---

### 4. Review Escaping Guidelines (Commit af2b14e9)
**Status:** 📝 **AUDIT TEMPLATES**

Ensure all Spec Kitty command templates properly escape shell metacharacters.

**Work:**
- Review all files in `.kittify/missions/*/commands/`
- Compare escaping patterns with upstream
- Add examples/documentation if needed

**Priority:** LOW (only if you've had user issues with command escaping)

---

### 5. Evaluate Remote Branch Detection (Commit b40b41cf)
**Status:** ❓ **NEEDS ANALYSIS**

Upstream improved branch number detection using `git ls-remote`. Determines if this helps Spec Kitty's worktree strategy.

**Analysis needed:**
- Could worktree branch numbers conflict in distributed teams?
- Does current `create-new-feature.sh` robustly detect existing branches?
- Would `git ls-remote` check reduce false negatives?

**If yes to all:** Worth merging
**If uncertain:** Defer for now

---

## 🟢 PHASE 3: Low Priority (Future / On Demand)

### New Agent Support
**Candidates:** Qoder, IBM Bob, Amp, OVHcloud SHAI

**Recommendation:** Add only when users request specific agents

**Effort per agent:** ~3-4 hours each (templating + testing)

---

### Constitution Documentation Review (Commit 41a9fc88)
**Status:** ✅ **ALREADY IMPLEMENTED IN SPEC KITTY**

Spec Kitty already has robust constitution framework. Review upstream docs only if clearer than existing Spec Kitty docs.

---

### Quickstart Formatting (Commit bb21eeda)
**Status:** 📝 **NICE-TO-HAVE**

Upstream improved admonitions/formatting. Optional UX improvement.

---

## 🚫 DO NOT MERGE

These commits are **incompatible** with Spec Kitty's architecture:

### VS Code Integration (Commits: 7e568c12, 3dcbb6e3, f4fcd829, ~40 others)
- **Reason:** Spec Kitty supports all agents equally; Spec Kit is VS Code-centric
- **Risk:** Breaking changes to agent abstraction layer
- **Action:** SKIP

### Branch Numbering Overhaul (Commits: 33df8976, f65bf6cc, bf5ae420)
- **Reason:** Spec Kitty uses simpler directory-based numbering
- **Risk:** Conflicts with worktree strategy
- **Action:** SKIP

### Release Package Restructuring (Commits: f7fe48bd, d6136cb2)
- **Reason:** Different release workflow
- **Risk:** May break deployment process
- **Action:** SKIP

### Devcontainer Configuration (Commits: 900bc2ed, 03c7021, 71c2c63d)
- **Reason:** Spec Kitty has different dev environment setup
- **Action:** SKIP

---

## Implementation Strategy

### Cherry-pick, Don't Merge
```bash
# DON'T DO THIS:
git merge upstream/main

# DO THIS INSTEAD:
git cherry-pick -n <commit-hash>
# Review & adapt
# git commit
```

### Testing After Each Merge
```bash
# Run full test suite
pytest tests/

# Run on macOS (your primary platform)
./.kittify/scripts/bash/create-new-feature.sh --help

# Test in real environment
cd /tmp && mkdir test-spec-kitty
cd test-spec-kitty
git init
```

### Documentation
- Update `CHANGELOG.md` with merged changes
- Reference upstream commit hash in commit message
- Document any path/terminology adaptations

---

## Risk Matrix

| Change | Compatibility | Testing | Risk |
|--------|---------------|---------|------|
| CDPATH fix | Very high | Low | 🟢 LOW |
| IDE agent check skip | High | Medium | 🟡 MEDIUM |
| Escaping guidelines | Medium | Medium | 🟡 MEDIUM |
| Remote branch detection | Medium | High | 🟡 MEDIUM |
| New agents | High | High | 🟢 LOW |
| Doc improvements | Very high | Low | 🟢 LOW |

---

## Next Steps

### Immediate (This Week)
1. ✅ Apply CDPATH fix to all bash scripts
2. ✅ Test on macOS + Linux
3. ✅ Commit & validate

### Near-term (Next 2 Weeks)
4. Review IDE agent CLI check skip (decide: implement or defer)
5. Adapt existing project documentation from upstream
6. Audit command templates for escaping consistency

### Future (On Demand)
7. Add agent support when requested by users
8. Review constitution docs for improvements
9. Evaluate other medium-priority commits as workflows evolve

---

## Questions for User Clarification

Before proceeding with Phase 2, answer:

1. **IDE Agents:** Are users requesting Cursor/Windsurf support in checks?
2. **Remote Teams:** Do you have distributed teams where branch number conflicts are a concern?
3. **Documentation:** What's your priority—docs clarity vs code changes?
4. **Agent Roadmap:** Any planned agent additions to prioritize support for?

---

## Summary Statistics

- **Commits analyzed:** 251
- **Applicable commits:** 10 (~4%)
- **High priority:** 1 (do immediately)
- **Medium priority:** 5-8 (review next 2 weeks)
- **Low priority:** 1-3 (future/optional)
- **Total merge effort:** 6-16 hours
- **Test effort:** 4-8 hours
- **Overall risk:** LOW-MEDIUM
- **Value:** MEDIUM (reliability + docs improvements)

---

**Report Reference:** See `UPSTREAM_DELTA_ANALYSIS.md` for detailed analysis of all 251 commits.
