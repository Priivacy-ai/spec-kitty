---
work_package_id: WP03
title: YAML-library choice documentation (ruamel vs PyYAML)
dependencies: []
requirement_refs:
- FR-009
tracker_refs: []
subtasks:
- T013
- T014
- T015
phase: Phase 1 - Thread B
assignee: ''
agent: claude
history:
- at: '2026-06-23T09:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: docs/development/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- docs/development/yaml-libraries.md
role: curator
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – YAML-library choice documentation

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter before parsing the rest of this prompt.

- **Profile**: `curator-carla`
- **Role**: `curator`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Document the rule for choosing between ruamel.yaml (round-trip) and PyYAML (plain load) — **honestly**. The squad confirmed usage is currently ad-hoc, so the doc must declare whether it states current or aspirational practice and must name the mixed-usage sites rather than assert a clean invariant (FR-009, SC-004).

**Done when:** a developer can pick a library from the doc alone; the doc cites ≥3 real call sites and names the contradiction sites; it states current-vs-aspirational explicitly.

## Context

- Spec FR-009, SC-004. Research D-5.
- Evidence (cite these): ruamel round-trip in `src/doctrine/drg/org_pack_config.py` (`_yaml()`, preserve_quotes); PyYAML `safe_load` of the *same* `config.yaml`-class data in `src/specify_cli/.../org_pack_loader.py:38`. Dual-use modules: `pack_assembler.py`, `charter/pack_manager.py`, `dashboard/handlers/glossary.py`.

## Subtasks & Detailed Guidance

### T013 — Audit [P]
- Grep `ruamel`, `import yaml`, `safe_load`, `yaml_utils` under `src/`. Record ≥3 named call sites for each library and the dual-use modules. Determine the *actual* deciding criterion (round-trip/preserve comments+quotes+frontmatter vs read-only simple data).

### T014 — Write the doc [P]
- Create `docs/development/yaml-libraries.md`: state the rule, the deciding criterion, **and** a "Known mixed-usage / to-reconcile" section listing the contradiction sites. Mark the doc **current-state** (with the known violations) — do not fabricate a clean invariant. Keep terminology canon (no forbidden terms).

### T015 — Verify reachability [P]
- Cross-link from a discoverable index (e.g. `docs/development/` README or the docs nav). If a docs link-check/terminology test exists, run it.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}
- Parallel lane (no dependency).

## Definition of Done

- [ ] `docs/development/yaml-libraries.md` exists, cites ≥3 named sites + dual-use sites, declares current-vs-aspirational.
- [ ] Reachable from a docs index. Terminology guard passes (`pytest tests/architectural/test_no_legacy_terminology.py`).

## Risks & Reviewer Guidance

- **Risk**: asserting a clean rule that the code contradicts. **Reviewer**: verify each cited site is real and the contradiction sites are named, not hidden.
