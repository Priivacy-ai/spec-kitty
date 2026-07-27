---
work_package_id: WP01
title: Core Ownership Artefacts (map + manifest)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-008
- FR-009
- FR-010
- NFR-001
- C-002
- C-005
- FR-015
planning_base_branch: feature/module_ownership
merge_target_branch: feature/module_ownership
branch_strategy: Planning artifacts for this feature were generated on feature/module_ownership. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/module_ownership unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-functional-ownership-map-01KPDY72
base_commit: f5923c1a75d7799d60baa88958b2f6e877df3cab
created_at: '2026-04-18T05:15:19.848540+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
agent: "claude"
shell_pid: "980115"
history:
- at: '2026-04-18T04:31:57Z'
  event: created
  actor: claude
authoritative_surface: architecture/2.x/
execution_mode: code_change
owned_files:
- architecture/2.x/05_ownership_map.md
- architecture/2.x/05_ownership_manifest.yaml
tags: []
---

# WP01 — Core Ownership Artefacts (map + manifest)

## Objective

Create two normative architecture artefacts that define canonical functional ownership for every major slice of `src/specify_cli/*`:

1. `architecture/2.x/05_ownership_map.md` — human-readable Markdown map (7 sections, 8 slice entries)
2. `architecture/2.x/05_ownership_manifest.yaml` — machine-readable YAML manifest (8 slice keys)

These artefacts are the authoritative source that downstream extraction Missions (#612, #613, #614, #615) and PR reviewers cite. The charter slice entry must already read as "fully consolidated" in this WP, anticipating the deletion that WP02 performs.

**This WP owns exactly two new files. No other files are created or modified.**

## Context

- `architecture/2.x/` already exists and contains `04_implementation_mapping/`, `06_unified_charter_bundle.md`, and others. No `05_*` file exists yet.
- The eight-slice taxonomy, all canonical package paths, and the `model_task_routing` parent-kind decision are pinned in `plan.md` (Structure Decisions table).
- The manifest schema is formally defined in `kitty-specs/functional-ownership-map-01KPDY72/data-model.md`. Read §1.1, §1.2, §1.3, §2.1, and §4 before authoring the manifest.
- The "How to use" section of the map mirrors `kitty-specs/functional-ownership-map-01KPDY72/quickstart.md`.
- The charter shim (`src/specify_cli/charter/`) is deleted by WP02. In this WP, write the charter slice entry *as if it has already been deleted* (`shims: []`, `current_state` pointing only at `src/charter/`). This preserves acceptance scenario 4.
- Terminology canon (C-005): use **Mission** (not "feature") and **Work Package** (not "task") everywhere in the authored prose.

---

## Subtask T001 — Pre-flight grep audit

**Purpose**: Confirm the current state of the charter shim and locate the test-fixture exceptions before authoring begins. Record findings; do not delete or modify anything in this task.

**Steps**:

1. List files under `src/specify_cli/charter/`:
   ```bash
   ls -1 src/specify_cli/charter/
   ```
   Expected: `__init__.py`, `compiler.py`, `interview.py`, `resolver.py` (4 files total, per R-001 in research.md).

2. Grep for non-test references to `specify_cli.charter` in CI workflows, scripts, and source code:
   ```bash
   grep -rn "specify_cli[./]charter" \
     .github/ scripts/ src/ Makefile pyproject.toml setup.cfg \
     --include="*.yml" --include="*.yaml" --include="*.py" \
     --include="*.toml" --include="*.cfg" \
     2>/dev/null | grep -v "src/specify_cli/charter/" | grep -v "tests/"
   ```
   Expected: zero lines. If any non-test callers are found, **stop and report them** — do not proceed to WP02 deletion until cleared.

3. Confirm the 3 C-005 test-fixture exceptions from mission `01KPD880`:
   - `tests/specify_cli/charter/test_defaults_unit.py` — should exist (whole file deleted by WP02).
   - `tests/charter/test_sync_paths.py` — contains `import_module("specify_cli.charter")` around line 36 and a C-005 docstring; lines to be removed by WP02.
   - `tests/charter/test_chokepoint_coverage.py` — contains `src/specify_cli/charter/` references around lines 29–34 and line 72; remove `specify_cli.charter` mentions but keep canonical `charter.*` lines.

4. Record the exact line numbers of the C-005 markers in the two test files (for use by WP02):
   ```bash
   grep -n "specify_cli.charter\|C-005" tests/charter/test_sync_paths.py tests/charter/test_chokepoint_coverage.py
   ```

**Validation**: All 4 charter shim files exist; zero non-test callers found; C-005 fixture locations confirmed.

---

## Subtask T002 — Create map document: front matter, legend, "How to use" section

**Purpose**: Create `architecture/2.x/05_ownership_map.md` with the document preamble that orients readers before the slice entries.

**Steps**:

1. Create the file at `architecture/2.x/05_ownership_map.md` with this structure for the opening sections:

   ```markdown
   # Functional Ownership Map

   | Field        | Value                                                                        |
   |--------------|------------------------------------------------------------------------------|
   | Status       | Active                                                                       |
   | Date         | 2026-04-18                                                                   |
   | Mission      | [functional-ownership-map-01KPDY72](../../kitty-specs/functional-ownership-map-01KPDY72/spec.md) |
   | Manifest     | [05_ownership_manifest.yaml](./05_ownership_manifest.yaml)                   |
   | Exemplar     | Mission `charter-ownership-consolidation-and-neutrality-hardening-01KPD880`  |
   | Direction    | [#461 — Charter as Synthesis & Doctrine Reference Graph](https://github.com/Priivacy-ai/spec-kitty/issues/461) |

   > **Terminology**: This document uses **Mission** (not "feature") and **Work Package** (not "task") per the repository's terminology canon in `AGENTS.md`. All downstream extraction PRs must follow the same convention.

   ---

   ## How to use this map
   ```

2. Write the "How to use" section — two audiences, mirroring `kitty-specs/functional-ownership-map-01KPDY72/quickstart.md`:

   **Audience A — Extraction-PR author**: 4-step procedure (locate slice, read fields, honour runtime dependency_rules if applicable, confirm the slice entry in the PR description). Include the glossary extraction worked example.

   **Audience B — Reviewer**: 6-step checklist (read PR description, open map, check each required field, verify Mission/Work Package canon, verify CHANGELOG entry if shim removal, check runtime dependency_rules test if runtime slice). Include the runtime review worked example.

3. Add the manifest-driven tooling blurb (python consumer pattern from quickstart.md §Manifest-driven tooling).

> **Caution (I3)**: The quickstart.md reviewer worked example lists `may_call: [charter_governance, doctrine, lifecycle_status, kernel]`. **Do not copy the `kernel` entry.** The schema test (WP03) validates all `may_call` values against the 8 canonical slice keys; `kernel` is not a slice and would cause a test failure. The correct list is `[charter_governance, doctrine, lifecycle_status, glossary]`.

**Files**: `architecture/2.x/05_ownership_map.md` (new, started).

**Validation**: File exists and renders cleanly; "How to use" section has both audience procedures.

---

## Subtask T003 — Write cli_shell, charter_governance, doctrine slice entries

**Purpose**: Populate the first three H2 slice sections of the map.

**Steps**:

Append to `05_ownership_map.md`:

```markdown
---

## Slice Entries
```

Then write three H2 sections in this order, using the field structure from `data-model.md §1.1`:

### `cli_shell` slice

- **Canonical package**: `src/specify_cli/cli/` (stays — CLI shell is the permanent home for CLI-only code)
- **Current state**: `src/specify_cli/cli/` — all CLI command modules, argument parsing, Rich rendering, exit-code mapping.
- **Adapter responsibilities**: This slice *is* the adapter layer. Everything in `cli/` is legitimately CLI-only. No extraction planned.
- **Shims**: none (empty list).
- **Seams**: CLI commands call into domain packages (charter, doctrine, runtime, glossary, lifecycle, orchestrator) via their public APIs; no domain logic lives in `cli/`.
- **Extraction sequencing notes**: Not extracted. CLI shell is the stable outer surface of the application.
- **Safeguard dependencies**: None — this slice does not extract.

### `charter_governance` slice

- **Canonical package**: `charter` (= `src/charter/`)
- **Current state** (post-mission): `src/charter/` — fully consolidated. `src/specify_cli/charter/` shim has been deleted.
- **Adapter responsibilities**: `src/specify_cli/cli/commands/charter*.py` — CLI argument parsing + Rich rendering for `spec-kitty charter *` commands. These legitimately remain in `src/specify_cli/`.
- **Shims**: **empty list** — the `src/specify_cli/charter/` shim was the only shim; it is deleted by this Mission.
- **Seams**: runtime reads charter context through `charter.build_charter_context()`; orchestrator reads charter bundle freshness through `charter.ensure_charter_bundle_fresh()`.
- **Extraction sequencing notes**: Already extracted. Serves as the **reference exemplar** for all other slice extractions. See the exemplar callout below.
- **Safeguard dependencies**: N/A — extraction is complete.

> **Reference exemplar** — Mission `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` is the canonical template for slice extraction. It demonstrates: (1) moving implementation to a top-level package, (2) adding a re-export shim under `src/specify_cli/` with `__deprecated__`, `__canonical_import__`, and `__removal_release__` attributes, (3) landing the deletion in a subsequent Mission once all callers have migrated. Every future extraction follows this pattern.

### `doctrine` slice

- **Canonical package**: `doctrine` (= `src/doctrine/`)
- **Current state**: `src/doctrine/` — already extracted.
- **Adapter responsibilities**: none — doctrine has no CLI commands; `kernel` is the sole consumer. No adapter layer needed.
- **Shims**: none.
- **Seams**: `kernel` reads doctrine kinds via `doctrine.load_kind()`; `src/specify_cli/` commands never import `doctrine` directly.
- **Extraction sequencing notes**: Already extracted. Structural tests under #393 enforce the boundary.
- **Safeguard dependencies**: #393 (architectural tests) — boundary enforcement already in place.
- **`model_task_routing` disposition**: `src/doctrine/model_task_routing/` is a **specialization of the `tactic` kind** (not a first-class kind peer). It carries a schema-validated routing catalog + `RoutingPolicy` (objective/weights/tier_constraints/override_policy/freshness_policy) layered on top of the standard tactic contract. The override policy echoes directive enforcement semantics internally, but the artefact is not itself a directive (no standalone `enforcement: required|advisory` field). The model-discipline port (deciding whether to register this as an official specialization subtype) is out of scope for this Mission.

**Files**: `architecture/2.x/05_ownership_map.md` (appended).

**Validation**: Three H2 slice sections rendered; charter section includes exemplar callout box; doctrine section states `model_task_routing` parent kind explicitly.

---

## Subtask T004 — Write runtime_mission_execution slice entry (with `dependency_rules`)

**Purpose**: Populate the runtime slice entry, which is the most complex entry due to the required `dependency_rules` sub-section (FR-004).

**Steps**:

Append the `runtime_mission_execution` H2 to `05_ownership_map.md`:

- **Canonical package**: `src/runtime/`
- **Current state**: Primary modules under `src/specify_cli/`:
  - `src/specify_cli/next/` — canonical mission-next command loop (already in standalone package under `src/`)
  - `src/specify_cli/missions/` — mission type definitions and command templates
  - `src/specify_cli/agent_utils/` — status utilities, kanban, orchestration helpers
  - `src/specify_cli/lanes.py` (or `lanes/`) — lane computation (shared with orchestrator slice)
  - `src/specify_cli/state.py` (or `state/`) — execution state management
  - `src/specify_cli/post_merge/` — post-merge reliability checks (added in mission 068)
  - Adjacent: `src/specify_cli/skills/` — skills renderer/installer/manifest
- **Adapter responsibilities**: `src/specify_cli/cli/commands/agent*.py` and `src/specify_cli/cli/commands/mission*.py` — CLI argument parsing + Rich rendering for `spec-kitty agent …` and `spec-kitty agent mission …` commands.
- **Shims**: one planned shim at `src/specify_cli/runtime/` (exact path TBD by mission #612), `canonical_import: runtime`, `removal_release: 3.4.0` (as pinned by #615).
- **Seams**:
  - "runtime reads charter context through `charter.build_charter_context()`"
  - "runtime reads doctrine kinds through `doctrine.load_kind()`"
  - "runtime emits lifecycle/status transitions through `lifecycle.emit_status_transition()`"
  - "CLI shell dispatches to runtime via `src/specify_cli/next/`"
- **Extraction sequencing notes**: Extracted by mission #612. Depends on #393 (architectural tests), #394 (deprecation shim scaffolding), and #395 (import-graph tooling) all being in place before the extraction PR lands.
- **Safeguard dependencies**: All three — #393, #394, #395 — required before #612 lands.

**`dependency_rules`** (required for runtime only, FR-004):

- `may_call`:
  - `charter_governance` — reads charter context and bundle freshness
  - `doctrine` — reads doctrine kinds for mission type resolution
  - `lifecycle_status` — emits status transitions and reads WP lane state
  - `glossary` — reads glossary runners registered through kernel infrastructure
- `may_be_called_by`:
  - `cli_shell` — the CLI dispatches to runtime; this is the only permitted caller

> **Note**: `kernel` is cross-cutting infrastructure shared by all packages — it is **not** a functional slice and must **not** appear in `may_call` or `may_be_called_by`. The schema test (WP03-T013) validates that every `dependency_rules` value is one of the 8 canonical slice keys; adding `kernel` would fail assertion 8. The quickstart.md worked example incorrectly includes `kernel` — do not replicate it.

Any module that calls into runtime from outside `cli_shell` is an architectural violation. The import-graph tool (#395) will enforce this once it lands.

**Files**: `architecture/2.x/05_ownership_map.md` (appended).

**Validation**: Runtime H2 section rendered; `dependency_rules` sub-section clearly present with both `may_call` and `may_be_called_by` lists; safeguard dependency mapping is explicit.

---

## Subtask T005 — Write glossary, lifecycle_status, orchestrator, migration slice entries

**Purpose**: Populate the remaining four H2 slice sections.

**Steps**:

Append four more H2 sections to `05_ownership_map.md`:

### `glossary` slice

- **Canonical package**: `src/glossary/`
- **Current state**: `src/specify_cli/glossary/` — ~14 modules covering the semantic-integrity pipeline, glossary runners, and CLI surfaces. Also `src/specify_cli/next/glossary.py` (if present) for glossary step integration.
- **Adapter responsibilities**: `src/specify_cli/cli/commands/glossary*.py` — CLI argument parsing + Rich rendering for `spec-kitty glossary *` commands.
- **Shims**: one planned shim at `src/specify_cli/glossary/`, `canonical_import: glossary`, `removal_release: 3.3.0` (or as pinned by #615).
- **Seams**: "doctrine registers a glossary runner via `kernel.glossary_runner.register()`; runtime reads via `get_runner()`" (resolved by ADR `2026-03-25-1`).
- **Extraction sequencing notes**: Extracted by mission #613. Depends on #393 and #394 landing first. #395 is nice-to-have, not blocking.
- **Safeguard dependencies**: #393 and #394 required before #613 lands.

### `lifecycle_status` slice

- **Canonical package**: `src/lifecycle/`
- **Current state**: Spans multiple subdirectories under `src/specify_cli/`:
  - `src/specify_cli/status/` — 9-lane event-log state machine (the bulk of this slice)
  - `src/specify_cli/lanes/` (or `lanes.py`) — lane computation + worktree ownership (shared boundary with orchestrator)
  - Parts of `src/specify_cli/events/` — event ABCs and Pydantic models
  - Parts of `src/specify_cli/state.py` — execution state overlapping with runtime
- **Adapter responsibilities**: `src/specify_cli/cli/commands/status*.py` if present; primarily consumed programmatically by runtime and orchestrator, not through its own CLI surface.
- **Shims**: multiple planned shims (one per moved module root); governed by the #615 rulebook.
- **Seams**: "runtime emits status transitions through `lifecycle.emit_status_transition()`"; "orchestrator reads WP lane state through `lifecycle.materialize(feature_dir)`"; "dashboard reads via `lifecycle.get_wp_lane()`".
- **Extraction sequencing notes**: Extracted by mission #614. Most cross-slice callers of any slice. Depends on all three safeguards (#393, #394, #395) being in place — the import-graph tool is material here.
- **Safeguard dependencies**: All three — #393, #394, #395 — required before #614 lands.

### `orchestrator_sync_tracker_saas` slice

- **Canonical package**: `src/orchestrator/` (forward-looking commitment; not extracted by this Mission)
- **Current state** — fragmented across seven subdirectories:
  - `src/specify_cli/orchestrator_api/` — external-consumer contract surface (REST-like API for remote orchestration)
  - `src/specify_cli/lanes/` — lane computation + worktree ownership (boundary shared with lifecycle)
  - `src/specify_cli/merge/` — merge executor, preflight, conflict forecast, state persistence
  - `src/specify_cli/sync/` — sync coordinator, background queue, body queue
  - `src/specify_cli/tracker/` — tracker connector gateway
  - `src/specify_cli/saas/` — SaaS readiness + rollout flags
  - `src/specify_cli/shims/` — orchestrator-internal shim registry
- **Adapter responsibilities**: `src/specify_cli/cli/commands/merge*.py`, `sync*.py`, `orchestrator*.py` — CLI argument parsing + Rich rendering for those subsystems.
- **Shims**: multiple (governed by the #615 rulebook); exact inventory deferred to #615.
- **Seams**: "CLI dispatches to merge executor via `merge.execute()`"; "orchestrator_api reads lifecycle state through `lifecycle.materialize()`"; "tracker gateway is invoked by sync coordinator".
- **Extraction sequencing notes**: Not extracted in the near term. The fragmented current state must be consolidated before extraction is tractable. No single downstream Mission covers the full slice; extraction is a multi-Mission initiative beyond #612–#615 scope. This map commits to a single canonical target (`src/orchestrator/`) so future work has a named destination.
- **Safeguard dependencies**: No immediate extraction; safeguards needed will be assessed when extraction is scheduled.

### `migration_versioning` slice

- **Canonical package**: `src/specify_cli/migration/` + `src/specify_cli/upgrade/` (stays for now; no near-term extraction planned)
- **Current state**: `src/specify_cli/migration/` — migration runner and registry; `src/specify_cli/upgrade/` — upgrade command, migration discovery, agent-dir management.
- **Adapter responsibilities**: `src/specify_cli/cli/commands/upgrade*.py` — CLI argument parsing + Rich rendering for `spec-kitty upgrade`.
- **Shims**: none active; the migration runner itself manages backward-compatibility for project-level config.
- **Seams**: "upgrade command reads agent config via `migration.get_agent_dirs_for_project()`"; "migration runner applies YAML frontmatter transformations via `ruamel.yaml`".
- **Extraction sequencing notes**: No extraction planned in the near term. Migration code is tightly coupled to the project-level config format (`.kittify/config.yaml`) and the agent directory topology. Extraction would require decoupling these first.
- **Safeguard dependencies**: None for the current planning horizon.

**Files**: `architecture/2.x/05_ownership_map.md` (appended).

**Validation**: Four H2 sections present; orchestrator section explicitly documents the 7-subdirectory fragmentation and names `src/orchestrator/` as the forward-looking target; lifecycle section names the `lanes/` boundary ambiguity.

---

## Subtask T006 — Write map closing sections: safeguards, downstream missions, change control

**Purpose**: Complete the map document with the three closing sections that frame the map in its broader context (FR-008, FR-009, C-002).

**Steps**:

Append to `05_ownership_map.md`:

### Safeguards and Direction

A table mapping each safeguard tracker to the slices it gates:

| Safeguard | Issue | Description | Blocks extraction of |
|-----------|-------|-------------|----------------------|
| Architectural tests | #393 | Import-boundary tests that fail when code crosses slice boundaries | runtime (#612), glossary (#613), lifecycle (#614) |
| Deprecation scaffolding | #394 | Tooling + process for creating shim modules with `__deprecated__`, `__canonical_import__`, `__removal_release__` | runtime (#612), glossary (#613), lifecycle (#614) |
| Import-graph tooling | #395 | CI-enforceable import graph checker for `may_call`/`may_be_called_by` rules | lifecycle (#614) — material; runtime (#612) — required; glossary (#613) — nice-to-have |
| Direction | #461 | Charter as Synthesis & Doctrine Reference Graph — the upstream epic that motivates the extraction series | Context for all slices; not a gate |

Narrative paragraph: explain that the extraction series implements the architectural direction in #461 by progressively moving domain logic out of `src/specify_cli/` into purpose-named top-level packages. Each slice extraction reduces the responsibilities of the `specify_cli` package and makes the architecture legible at a glance from `src/`.

### Downstream Missions

| Mission | Issue | Consumes from this map |
|---------|-------|------------------------|
| Shim ownership rules | #615 | Shim inventory across all 8 slices; the `shims[]` sub-entries define the input to the #615 rulebook |
| Runtime extraction | #612 | `runtime_mission_execution` slice entry — canonical package path, current state, dependency_rules, adapter responsibilities |
| Glossary extraction | #613 | `glossary` slice entry — canonical package path, current state, seams, safeguard requirements |
| Lifecycle extraction | #614 | `lifecycle_status` slice entry — canonical package path (umbrella `src/lifecycle/`), current state (fragmented), safeguard requirements |

### Change Control

Short paragraph: this map is a living document. Future changes land in-place via PRs. Each extraction PR confirms its slice entry is fully honoured in the PR description (see Audience B — Reviewer procedure above). Post-merge amendments to a slice entry are welcome; they do not require a new Mission unless the scope change is substantial.

**Files**: `architecture/2.x/05_ownership_map.md` (completed).

**Validation**: Three closing sections present; safeguards table maps all three tracker issues to their gating slices; downstream missions table has all four entries; change control paragraph states the living-document policy.

---

## Subtask T007 — Author `05_ownership_manifest.yaml` (all 8 slice keys)

**Purpose**: Create the machine-readable YAML manifest that CI tools, the #615 shim registry, and future scripts parse directly. Derive all field values from the completed map.

**Reference**: `kitty-specs/functional-ownership-map-01KPDY72/data-model.md` §1.1–§1.3 and §2 for the exact schema. The manifest schema contract is at `kitty-specs/functional-ownership-map-01KPDY72/contracts/` (if present) or defined inline in data-model.md.

**Steps**:

1. Create `architecture/2.x/05_ownership_manifest.yaml` with an opening comment block:
   ```yaml
   # architecture/2.x/05_ownership_manifest.yaml
   # Machine-readable ownership manifest for src/specify_cli/* functional slices.
   # Source: architecture/2.x/05_ownership_map.md
   # Schema validated by: tests/architecture/test_ownership_manifest_schema.py
   # DO NOT edit this file without also updating the Markdown map.
   ```

2. Write all 8 top-level keys **in this exact order** (order is validated by the schema test):
   `cli_shell`, `charter_governance`, `doctrine`, `runtime_mission_execution`, `glossary`, `lifecycle_status`, `orchestrator_sync_tracker_saas`, `migration_versioning`

3. For each slice entry, include all required fields from data-model §1.1:
   - `canonical_package` (string, non-empty)
   - `current_state` (list of strings, non-empty)
   - `adapter_responsibilities` (list of strings, may be empty)
   - `shims` (list of mappings, may be empty; each entry has `path`, `canonical_import`, `removal_release`, and optionally `notes`)
   - `seams` (list of strings, may be empty)
   - `extraction_sequencing_notes` (string, non-empty)

4. For `runtime_mission_execution` only, add `dependency_rules` (data-model §1.3):
   ```yaml
   dependency_rules:
     may_call:
       - charter_governance
       - doctrine
       - lifecycle_status
       - glossary
       - kernel
     may_be_called_by:
       - cli_shell
   ```

5. For `charter_governance`, `shims` must be **an empty list** (`shims: []`). This is assertion 7 in the schema test and the key marker that the shim has been deleted.

6. After writing all 8 keys, self-validate:
   - Every slice has all 6 required fields (plus `dependency_rules` for runtime only).
   - Every value in `dependency_rules.may_call` and `may_be_called_by` is a recognised slice key (one of the 8 top-level keys).
   - `charter_governance.shims` is `[]`.
   - `runtime_mission_execution` has `dependency_rules`; no other slice does.
   - Run `python -c "import yaml; m=yaml.safe_load(open('architecture/2.x/05_ownership_manifest.yaml')); assert len(m)==8; print('8 keys OK')"` to confirm.

**Files**:
- `architecture/2.x/05_ownership_manifest.yaml` (new, ~120 lines YAML)

**Validation**:
- File loads without error via `yaml.safe_load()`.
- Exactly 8 top-level keys, matching the canonical set.
- `runtime_mission_execution.dependency_rules` present and correct.
- `charter_governance.shims == []`.
- All `may_call`/`may_be_called_by` values are recognised slice keys.

---

## Branch Strategy

- **Planning/base branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: allocated by `spec-kitty agent action implement WP01 --agent <name>` via `lanes.json`. Work in the resolved worktree; do not branch manually.
- No feature branch is required. This is a standard-mode Mission (`change_mode: standard`).

---

## Definition of Done

- [ ] `architecture/2.x/05_ownership_map.md` exists and contains all 7 structural sections (front matter/legend, How to use, 8 slice entries, safeguards, downstream missions, change control).
- [ ] Each slice entry in the map contains all required fields: `canonical_package`, `current_state`, `adapter_responsibilities`, `shims`, `seams`, `extraction_sequencing_notes`.
- [ ] `runtime_mission_execution` slice entry in the map contains `dependency_rules` with both `may_call` and `may_be_called_by` lists.
- [ ] `charter_governance` slice entry reads as fully consolidated; `shims` is empty; exemplar callout box is present.
- [ ] `doctrine` slice entry documents `model_task_routing` as a **specialization of the `tactic` kind** with rationale.
- [ ] `architecture/2.x/05_ownership_manifest.yaml` exists and loads via `yaml.safe_load()` with exactly 8 top-level keys.
- [ ] Self-validation snippet exits 0.
- [ ] No other files modified (C-002, FR-015).
- [ ] Terminology: "Mission" and "Work Package" throughout; no "feature/task" language.

---

## Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Orchestrator slice description becomes speculative | Medium | Document current fragmented state factually (7 dirs); state the canonical target as a forward-looking commitment only. Do not invent a timeline. |
| `dependency_rules.may_call` list is incomplete | Low | Use R-003 safeguard mapping + research.md R-006 evidence; err on the side of being permissive (the schema test only validates structure, not completeness). |
| Map prose uses "feature" or "task" vocabulary | Low | Run a final grep before committing: `grep -E "\bfeature\b|\btask\b" architecture/2.x/05_ownership_map.md` (document uses "Mission" and "Work Package"). |

---

## Reviewer Guidance

- Confirm all 8 H2 slice sections exist in the map with required sub-fields present.
- Spot-check the runtime slice's `dependency_rules` — verify `may_call` and `may_be_called_by` are plausible given the codebase.
- Verify the charter exemplar callout box is visible under the `charter_governance` section.
- Verify the manifest's `charter_governance.shims` is `[]`.
- Check that the safeguards table correctly maps #393/#394/#395 to their gating slices (R-003 in research.md is the source of truth).
- Confirm no files outside `architecture/2.x/` are modified.

## Activity Log

- 2026-04-18T05:23:06Z – claude:opus-4-6:implementer:implementer – shell_pid=975030 – Ready for review: 05_ownership_map.md and 05_ownership_manifest.yaml created; all 8 schema assertions pass
- 2026-04-18T05:24:48Z – claude – shell_pid=980115 – Started review via action command
- 2026-04-18T05:25:46Z – claude – shell_pid=980115 – Review passed: all 8 schema assertions pass, charter shims=[], may_call correct, exemplar callout present
