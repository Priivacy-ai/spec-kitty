---
work_package_id: WP04
title: Architecture Artifacts — Rulebook and Registry
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-012
- FR-013
- FR-014
planning_base_branch: kitty/mission-migration-shim-ownership-rules-01KPDYDW
merge_target_branch: kitty/mission-migration-shim-ownership-rules-01KPDYDW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-migration-shim-ownership-rules-01KPDYDW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-migration-shim-ownership-rules-01KPDYDW unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
agent: "claude"
shell_pid: "1344828"
history:
- date: '2026-04-19'
  event: created
authoritative_surface: architecture/2.x/
execution_mode: planning_artifact
agent_profile: architect
mission_id: 01KPDYDWVF8W838HNJK7FC3S7T
mission_slug: migration-shim-ownership-rules-01KPDYDW
owned_files:
- architecture/2.x/shim-registry.yaml
- architecture/2.x/06_migration_and_shim_rules.md
tags: []
---

# WP04 — Architecture Artifacts — Rulebook and Registry

## Objective

Write the two primary deliverables of this mission: the machine-readable shim registry (`architecture/2.x/shim-registry.yaml`) and the human-readable rulebook (`architecture/2.x/06_migration_and_shim_rules.md`). These artifacts are cited directly by downstream extraction missions #612, #613, and #614.

## Context

The `architecture/2.x/` directory already contains `05_ownership_map.md` and `05_ownership_manifest.yaml` (from mission #610). This WP adds the next two files in sequence.

The rulebook must cover four rule families (FR-002) and include a worked example from mission `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` (FR-012). It must reference `architecture/2.x/05_ownership_map.md` (FR-014) and name #461 Phase 7 as the follow-up for doctrine versioning (FR-013).

The registry starts empty because zero shims exist at mission start (confirmed by WP01/T001).

This WP has **no code dependency** — it can run in parallel with WP01.

## Branch Strategy

- **Working branch**: `kitty/mission-migration-shim-ownership-rules-01KPDYDW`
- **Merge target**: `main`
- Run: `spec-kitty agent action implement WP04 --agent <name>`

---

## Subtask T007 — Write `architecture/2.x/shim-registry.yaml`

**Purpose**: Create the initial empty machine-readable registry. Future extraction missions will add entries in their own PRs.

**Content**:

```yaml
# Compatibility Shim Registry
# Mission: migration-shim-ownership-rules-01KPDYDW (#615)
#
# Schema: kitty-specs/migration-shim-ownership-rules-01KPDYDW/contracts/shim-registry-schema.yaml
# Rulebook: architecture/2.x/06_migration_and_shim_rules.md
#
# To register a new shim: follow the instructions in the rulebook Section 4
# (rule family d — removal plans and registry contract) and the quickstart at
# kitty-specs/migration-shim-ownership-rules-01KPDYDW/quickstart.md
#
# CI enforcement: spec-kitty doctor shim-registry
# Scanner test: tests/architectural/test_unregistered_shim_scanner.py
#
# Baseline (2026-04-19): zero shims present at mission-615 start.
# Every future entry must set grandfathered: false.

shims: []
```

**Files**:
- `architecture/2.x/shim-registry.yaml` (new)

**Validation**:
- [ ] File parses as valid YAML
- [ ] `spec-kitty doctor shim-registry` reads it without error (exit 0)
- [ ] `pytest tests/architectural/test_shim_registry_schema.py` passes (after WP05)

---

## Subtask T008 — Write `architecture/2.x/06_migration_and_shim_rules.md`

**Purpose**: Write the authoritative rulebook that every future extraction PR must cite and follow.

**Required structure** (FR-002):

```markdown
# Migration and Shim Ownership Rules
*architecture/2.x/06_migration_and_shim_rules.md*
*Mission: migration-shim-ownership-rules-01KPDYDW (#615)*
*See also: 05_ownership_map.md (slice inventory)*

## 1. Scope and Purpose
[one paragraph — why this rulebook exists, what it governs, which missions consume it]

## 2. Rule Family (a) — Project Schema and Version Gating
[Describe the current schema-version contract for .kittify/ artifacts and mission bundles.
Cross-reference #461 Phase 7 as the follow-up that will extend this to doctrine artifacts (FR-013).]

## 3. Rule Family (b) — Bundle and Runtime Migration Authoring Contract
[Shape of a migration module: idempotency requirement, test expectations, naming conventions.
How a migration entry-point is registered and invoked.]

## 4. Rule Family (c) — Compatibility Shim Lifecycle
[The mandatory shim module shape (copy-paste template below).
One-release deprecation window. Extension mechanism with extension_rationale.
The six required module attributes: __deprecated__, __canonical_import__,
__removal_release__, __deprecation_message__, warnings.warn stacklevel=2.
Reference to shim-registry.yaml and doctor shim-registry.]

### Copy-paste shim template
\`\`\`python
"""Compatibility shim — re-exports from <canonical_package>.

Deprecated: import from <canonical_package> instead. Scheduled for removal in <X.Y.Z>.
"""
from __future__ import annotations

import warnings

from <canonical_package> import *  # noqa: F401, F403
from <canonical_package> import __all__  # if canonical defines __all__

__deprecated__ = True
__canonical_import__ = "<canonical_package>"
__removal_release__ = "<X.Y.Z>"
__deprecation_message__ = (
    "specify_cli.<legacy_name> is deprecated; import from <canonical_package>. "
    "Scheduled for removal in <X.Y.Z>."
)

warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)
\`\`\`

## 5. Rule Family (d) — Removal Plans and Registry Contract
[Registry schema summary (refer to contracts/shim-registry-schema.yaml for authoritative schema).
How to add a new entry. The removal-PR contract (FR-005):
  1. Delete shim file
  2. Remove/mark registry entry
  3. CHANGELOG.md under Removed
  4. Close tracker issue
  5. CI passes]

## 6. CI Enforcement
[spec-kitty doctor shim-registry — exit codes 0/1/2, what each means.
tests/architectural/test_unregistered_shim_scanner.py — what it does.
tests/architectural/test_shim_registry_schema.py — what it validates.]

## 7. Worked Example — Charter Mission
[Side-by-side mapping of each rule family to the concrete artifacts in mission
charter-ownership-consolidation-and-neutrality-hardening-01KPD880.
If specify_cli.charter shim was never introduced (because charter had no external importers),
document the "no-shim baseline case" explicitly:
  "The charter mission demonstrates rule family (c) by not introducing a shim because
   the canonical package had no external importers at extraction time. This is a valid
   exception: the registry records it as the empty baseline."]

## 8. Reference Index
- architecture/2.x/05_ownership_map.md — slice-by-slice ownership map (#610)
- architecture/2.x/shim-registry.yaml — machine-readable registry (this mission)
- kitty-specs/migration-shim-ownership-rules-01KPDYDW/contracts/shim-registry-schema.yaml — schema
- kitty-specs/migration-shim-ownership-rules-01KPDYDW/quickstart.md — 5-step registration recipe
- #461 Phase 7 — planned doctrine-versioning extension (cross-ref only, not implemented here)
```

**Writing guidance**:
- Sections 2–5 each need 200–400 words of concrete, rule-level prose — not vague bullet lists.
- Section 3 (migration authoring contract) must describe what a `apply(project_path, dry_run)` migration looks like and where it lives.
- Section 4 copy-paste template must be syntactically correct Python (runnable).
- Section 7 must be specific: name actual file paths from the charter mission where possible. If `specify_cli.charter` was already removed by #610, explicitly say so.
- Do NOT invent rule IDs — use the FR/NFR/C numbering from `spec.md` to cross-reference requirements.

**Files**:
- `architecture/2.x/06_migration_and_shim_rules.md` (new, ~600–800 words of prose)

**Validation**:
- [ ] All 4 rule families covered in distinct sections
- [ ] Copy-paste shim template is syntactically correct Python
- [ ] Section 7 cites `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` by slug
- [ ] Cross-reference to `05_ownership_map.md` present (FR-014)
- [ ] Cross-reference to #461 Phase 7 present (FR-013)
- [ ] Peer reviewer can read end-to-end in ≤15 minutes (NFR-003)

---

## Definition of Done

- [ ] `architecture/2.x/shim-registry.yaml` created with `shims: []`
- [ ] `architecture/2.x/06_migration_and_shim_rules.md` created with all 4 rule families + worked example + reference index
- [ ] `spec-kitty doctor shim-registry` exits 0 reading the new registry
- [ ] Rulebook passes peer-readability check (≤15 min read time, NFR-003)

## Risks

- Charter mission artifacts may be partially removed (if #610 fully merged before this WP). In that case, document the worked example from what is present and note the missing artifacts explicitly. Do not invent artifact paths that don't exist.
- The `architecture/2.x/` directory may have a README or index that needs updating — check and update if it exists.

## Activity Log

- 2026-04-19T13:19:05Z – claude – shell_pid=1340356 – Started implementation via action command
- 2026-04-19T13:23:08Z – claude – shell_pid=1340356 – Rulebook and registry written. All 4 rule families covered. Worked example documents charter no-shim baseline case.
- 2026-04-19T13:25:48Z – claude – shell_pid=1344828 – Started review via action command
- 2026-04-19T13:26:09Z – claude – shell_pid=1344828 – Review passed: all 4 rule families covered, charter no-shim baseline documented, cross-refs to 05_ownership_map.md and #461 Phase 7 present, YAML valid.
