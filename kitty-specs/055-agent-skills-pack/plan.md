# Implementation Plan: Agent Skills Pack

**Branch**: `055-agent-skills-pack` | **Date**: 2026-03-21 | **Spec**: [spec.md](spec.md)
**PRD Source**: `prd-spec-kitty-agent-skills-pack-v1.md`
**Target**: Spec Kitty 2.0.11+ (`2.x` line only)

## Summary

Ship one canonical customer-facing skill pack for Spec Kitty 2.0.11+. Skills are authored once in `src/doctrine/skills/`, distributed deterministically by `spec-kitty init` into correct agent-specific skill roots based on the framework capability matrix, and tracked by a dedicated managed-file manifest for sync/repair/verification. Wrappers remain thin generated transport. First slice delivers `spec-kitty-setup-doctor` end-to-end with full installer, manifest, and verify plumbing.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, pytest, mypy (strict)
**Storage**: Filesystem only (JSON manifest in `.kittify/`, skill source in `src/doctrine/skills/`)
**Testing**: pytest with 90%+ coverage, mypy --strict
**Target Platform**: Linux, macOS, Windows 10+ (cross-platform)
**Project Type**: Single project (existing CLI codebase)
**Performance Goals**: Skill installation adds < 2s to init
**Constraints**: Local-first, no SaaS dependency, no pre-2.0.11 compat
**Scale/Scope**: 8 skills, 13 agents, 3 installation classes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Python 3.11+ | PASS | Existing requirement, no change |
| typer/rich/ruamel.yaml/pytest/mypy | PASS | Using existing dependencies only |
| 90%+ test coverage for new code | PASS | Planned, NFR-003 |
| mypy --strict passes | PASS | Planned, NFR-004 |
| CLI < 2s for typical operations | PASS | Skill install within budget, NFR-001 |
| Cross-platform (Linux, macOS, Windows) | PASS | No platform-specific code, pathlib only |
| Git required | PASS | No additional VCS requirements |
| 2.x branch active development | PASS | Targeting 2.x exclusively |
| No 1.x compatibility | PASS | C-001 explicitly forbids |
| Terminology: Mission not Feature | PASS | "Skill" is a distinct concept, not replacing "Mission" |
| Private dependency pattern | PASS | No new external dependencies |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```
kitty-specs/055-agent-skills-pack/
├── spec.md
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```
src/doctrine/skills/                       # NEW: Canonical authored skill source
├── spec-kitty-setup-doctor/               # First shipped skill
│   ├── SKILL.md                           # Skill body with frontmatter
│   ├── references/                        # Extended guidance docs
│   │   ├── agent-path-matrix.md
│   │   └── common-failure-signatures.md
│   └── scripts/                           # Deterministic check scripts
│       └── health-check.sh
├── spec-kitty-constitution-doctrine/      # Shipped: governance workflows
├── spec-kitty-glossary-context/           # Shipped: glossary curation
├── spec-kitty-runtime-next/               # Shipped: runtime control loop
├── spec-kitty-runtime-review/             # Shipped: review workflow
└── spec-kitty-orchestrator-api-operator/  # Shipped: external orchestration API
# spec-kitty-specify-plan — DEFERRED to doctrine mission compiler (PR #305 / Issue #327)
# spec-kitty-mission-orchestrator — DEFERRED to doctrine mission compiler

src/specify_cli/skills/                    # NEW: Skill distribution runtime
├── __init__.py
├── manifest.py                            # ManagedSkillManifest dataclass + persistence
├── installer.py                           # Copy skills to agent roots per capability matrix
├── verifier.py                            # Check installed skills against manifest
└── registry.py                            # Discover canonical skills from doctrine/package

src/specify_cli/cli/commands/init.py       # MODIFIED: Add skill installation step
src/specify_cli/verify_enhanced.py         # MODIFIED: Add managed skill verification
src/specify_cli/core/config.py             # MODIFIED: Add AGENT_SKILL_CONFIG

tests/specify_cli/skills/                  # NEW: Test suite
├── __init__.py
├── test_manifest.py
├── test_installer.py
├── test_verifier.py
├── test_registry.py
└── test_init_integration.py

pyproject.toml                             # MODIFIED: Verify also_copy covers skills
```

**Structure Decision**: Follows existing 2.x dual-repo pattern. Skill content in `src/doctrine/skills/` (content layer), distribution runtime in `src/specify_cli/skills/` (implementation layer). This is consistent with how missions, templates, and other content already flow through the codebase.

## Architecture Decisions

### AD-1: Skill Source in Doctrine Layer

The PRD specifies `src/specify_cli/templates/skills/` as the canonical source. The 2.x codebase uses a dual-repo pattern where `src/doctrine/` holds all authored content. Skills follow the doctrine pattern.

- `src/doctrine/` is already included in `also_copy` in `pyproject.toml`, so skills are automatically bundled in the wheel
- The 4-tier template resolver already knows how to find doctrine content
- No additional packaging configuration needed

### AD-2: Framework Capability Matrix as Config

The PRD's capability matrix (section 6) is encoded as a new `AGENT_SKILL_CONFIG` constant alongside the existing `AGENT_COMMAND_CONFIG`:

```python
# Installation classes
SKILL_CLASS_SHARED = "shared-root-capable"
SKILL_CLASS_NATIVE = "native-root-required"
SKILL_CLASS_WRAPPER = "wrapper-only"

AGENT_SKILL_CONFIG: dict[str, dict[str, str | list[str] | None]] = {
    "claude":       {"class": SKILL_CLASS_NATIVE,  "skill_roots": [".claude/skills/"]},
    "copilot":      {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".github/skills/"]},
    "gemini":       {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".gemini/skills/"]},
    "cursor":       {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".cursor/skills/"]},
    "qwen":         {"class": SKILL_CLASS_NATIVE,  "skill_roots": [".qwen/skills/"]},
    "opencode":     {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".opencode/skills/"]},
    "windsurf":     {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".windsurf/skills/"]},
    "codex":        {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/"]},
    "kilocode":     {"class": SKILL_CLASS_NATIVE,  "skill_roots": [".kilocode/skills/"]},
    "auggie":       {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".augment/skills/"]},
    "roo":          {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".roo/skills/"]},
    "q":            {"class": SKILL_CLASS_WRAPPER, "skill_roots": None},
    "antigravity":  {"class": SKILL_CLASS_SHARED,  "skill_roots": [".agents/skills/", ".agent/skills/"]},
}
```

### AD-3: Managed-File Manifest Schema

Persisted as `.kittify/skills-manifest.json`:

```json
{
  "version": 1,
  "created_at": "2026-03-21T00:00:00Z",
  "updated_at": "2026-03-21T00:00:00Z",
  "spec_kitty_version": "2.0.11",
  "entries": [
    {
      "skill_name": "spec-kitty-setup-doctor",
      "source_file": "SKILL.md",
      "installed_path": ".claude/skills/spec-kitty-setup-doctor/SKILL.md",
      "installation_class": "native-root-required",
      "agent_key": "claude",
      "content_hash": "sha256:abc123...",
      "installed_at": "2026-03-21T00:00:00Z"
    }
  ]
}
```

### AD-4: Init Integration Point

Skill installation happens in the init flow after `generate_agent_assets()` (wrapper generation) and before the git step. This preserves existing wrapper behavior (C-003) and adds skill distribution as an additional step.

```python
# In init.py, after line ~775 (generate_agent_assets call):
# ... existing wrapper generation ...
generate_agent_assets(render_templates_dir, project_path, agent_key, selected_script)

# NEW: Install skill pack for this agent
from specify_cli.skills.installer import install_skills_for_agent
install_skills_for_agent(project_path, agent_key, manifest)
```

### AD-5: Skill Discovery from Package vs Local

The skill registry discovers canonical skills from either:
1. **Local dev checkout**: `src/doctrine/skills/` (when `get_local_repo_root()` returns a path)
2. **Installed package**: The `doctrine/skills/` directory bundled via `also_copy`

This mirrors the existing `copy_specify_base_from_local()` vs `copy_specify_base_from_package()` pattern.

### AD-6: Edge Case Handling

- **Custom files colliding with managed skill names**: Installer skips files that already exist and are not tracked in the manifest. Verify reports them as "unmanaged conflicts".
- **Pre-existing `.agents/skills/`**: Installer creates skill subdirectories within it without removing existing content.
- **Interrupted init**: Manifest is written atomically at the end of all skill installations. Partial state results in missing manifest entries, which verify catches.
- **Corrupted package**: If canonical source is missing, installer raises a clear error with recovery instructions (reinstall spec-kitty).
- **Manually modified managed file**: Verify reports drift. Sync/repair restores from source with user confirmation.

## Integration Points

### Modified Files

| File | Change | Risk |
|------|--------|------|
| `src/specify_cli/cli/commands/init.py` | Add skill installation step after wrapper generation | Low — additive, existing flow untouched |
| `src/specify_cli/core/config.py` | Add `AGENT_SKILL_CONFIG` constant | Low — new constant, no existing code affected |
| `src/specify_cli/verify_enhanced.py` | Add managed skill checks | Low — additive check |
| `pyproject.toml` | Verify `also_copy` covers `src/doctrine/skills/` (already covered by `src/doctrine/`) | None — already bundled |

### New Files

| File | Purpose |
|------|---------|
| `src/doctrine/skills/spec-kitty-setup-doctor/SKILL.md` | First canonical shipped skill |
| `src/doctrine/skills/spec-kitty-setup-doctor/references/` | Extended reference docs |
| `src/specify_cli/skills/__init__.py` | Skills distribution package |
| `src/specify_cli/skills/manifest.py` | ManagedSkillManifest dataclass and JSON persistence |
| `src/specify_cli/skills/installer.py` | Copies skills to agent roots per capability matrix |
| `src/specify_cli/skills/verifier.py` | Checks installed skills against manifest |
| `src/specify_cli/skills/registry.py` | Discovers canonical skills from doctrine/package source |
| `tests/specify_cli/skills/test_*.py` | Test suite |

## Dependency Analysis

```
registry.py (discovers canonical skills)
    ↓
installer.py (copies to agent roots, builds manifest entries)
    ↓
manifest.py (persists entries to JSON)
    ↓
verifier.py (reads manifest, checks installed files)

init.py → installer.py (orchestrates per-agent installation)
verify_enhanced.py → verifier.py (adds skill checks to verify command)
```

No circular dependencies. Each module has a single clear responsibility.
