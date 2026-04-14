---
work_package_id: WP02
title: Strip inline reference fields from artifacts, schemas, models
dependencies:
- WP01
requirement_refs:
- FR-005
- FR-006
- FR-007
- FR-013
- FR-015
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
agent: "opencode:gpt-5:python-reviewer:reviewer"
shell_pid: "96242"
history:
- at: '2026-04-14T05:02:32Z'
  actor: claude
  event: created
authoritative_surface: src/doctrine/schemas/
execution_mode: code_change
owned_files:
- src/doctrine/directives/*.directive.yaml
- src/doctrine/paradigms/*.paradigm.yaml
- src/doctrine/procedures/*.procedure.yaml
- src/doctrine/schemas/directive.schema.yaml
- src/doctrine/schemas/paradigm.schema.yaml
- src/doctrine/schemas/procedure.schema.yaml
- src/doctrine/directives/models.py
- src/doctrine/paradigms/models.py
- src/doctrine/procedures/models.py
- src/doctrine/tactics/models.py
- src/doctrine/styleguides/models.py
- src/doctrine/toolguides/models.py
- src/doctrine/agent_profiles/models.py
- src/doctrine/graph.yaml
- src/charter/schemas.py
- tests/doctrine/directives/**
- tests/doctrine/paradigms/**
- tests/doctrine/procedures/**
- tests/doctrine/tactics/**
- tests/doctrine/test_artifact_compliance.py
- tests/doctrine/test_enriched_directives.py
- tests/doctrine/test_directive_consistency.py
- tests/doctrine/test_procedure_consistency.py
- tests/doctrine/test_tactic_compliance.py
tags: []
---

# WP02 — Strip inline reference fields from artifacts, schemas, models

**Tracks**: [Priivacy-ai/spec-kitty#477](https://github.com/Priivacy-ai/spec-kitty/issues/477)
**Depends on**: WP01 merged to `main`
**Merges to**: `main`

## Branch Strategy

- **Planning/base branch**: `main`
- **Merge target**: `main`
- **Execution mode**: lane-based worktree allocated by `finalize-tasks`. Run `spec-kitty agent action implement WP02 --agent <name> --mission excise-doctrine-curation-and-inline-references-01KP54J6` to resolve the actual workspace path and branch.
- **Do NOT start** until WP01 is merged to `main` (per spec C-007).

---

## Objective

Remove `tactic_refs`, `paradigm_refs`, and `applies_to` as valid fields from every doctrine artifact YAML, every JSON/YAML schema, every Pydantic model, and from `src/charter/schemas.py :: Directive`. Before stripping inline refs from YAMLs, audit `src/doctrine/graph.yaml` to confirm every inline relationship is ALSO encoded as a graph edge; if not, add the missing edges atomically in the same PR before the YAML stripping lands.

After this WP merges, the only source of truth for cross-artifact relationships is `src/doctrine/graph.yaml` edges.

## Context

- Inline `tactic_refs:` occurrences on `main` at planning: **13 shipped YAMLs** (8 directives, 3 paradigms, 2 procedures).
- `paradigm_refs:` and `applies_to:` are **NOT** currently used in any shipped YAML — but ARE declared in schemas and some models. This WP removes those field declarations so validators can cleanly reject them in WP03.
- Phase 0 (EPIC #461) extracted graph edges from inline refs, so `graph.yaml` SHOULD already cover every inline relationship. R-1 audit in T007 proves or refutes this.

## Authoritative files (read before starting)

- [spec.md](../spec.md) — FR-005, FR-006, FR-007; C-001, C-002, C-007
- [plan.md](../plan.md) — WP1.2 section + D-4 (test architecture)
- [research.md](../research.md) — R-1 (inline-vs-graph audit method)
- [data-model.md](../data-model.md) — E-6 (Shipped Artifact YAML post-Phase-1 shape)
- [contracts/occurrence-artifact.schema.yaml](../contracts/occurrence-artifact.schema.yaml) — artifact schema

---

## Subtask details

### T007 — Author `occurrences/WP02.yaml`; run R-1 inline-vs-graph audit

**Purpose**: Produce the WP02 occurrence-classification artifact AND prove that `graph.yaml` covers every inline relationship currently expressed in shipped YAMLs. Generates the missing-edges list (if any) consumed by T008.

**Steps**:

1. Author `kitty-specs/.../occurrences/WP02.yaml` per [contracts/occurrence-artifact.schema.yaml](../contracts/occurrence-artifact.schema.yaml).

   Categories for WP02:
   - `yaml_key`: `tactic_refs`, `paradigm_refs`, `applies_to` in `src/doctrine/**/*.yaml`
   - `symbol_name`: Pydantic field declarations of the three names in `src/doctrine/**/models.py` and `src/charter/schemas.py`
   - `docstring_or_comment`: schema comments referencing the three field names
   - `test_identifier`: test assertions that inline fields exist

   `requires_merged: [WP01]` — verifier refuses to pass unless WP01 is merged.

2. Create `scripts/r1_inline_vs_graph_audit.py` (ephemeral — deleted in T012):

   ```python
   #!/usr/bin/env python3
   """One-shot R-1 audit: every inline tactic_refs must have a matching graph edge.

   Runs once at WP02 start to produce missing_edges.yaml. Deleted at end of WP02.
   """
   from __future__ import annotations
   import sys
   from pathlib import Path
   from ruamel.yaml import YAML

   REPO_ROOT = Path(__file__).resolve().parents[1]
   DOCTRINE = REPO_ROOT / "src" / "doctrine"
   GRAPH = DOCTRINE / "graph.yaml"

   yaml_loader = YAML(typ="safe")

   # Build edge index
   graph = yaml_loader.load(GRAPH.read_text())
   edges = {(e["from"], e["to"], e["kind"]) for e in graph.get("edges", [])}

   missing: list[dict] = []
   total_inline = 0
   matched = 0

   for kind_dir in ("directives", "paradigms", "procedures", "tactics", "styleguides", "toolguides"):
       kd = DOCTRINE / kind_dir
       if not kd.is_dir():
           continue
       for yaml_path in kd.glob(f"*.{kind_dir[:-1]}.yaml"):  # e.g. *.directive.yaml
           data = yaml_loader.load(yaml_path.read_text())
           if not isinstance(data, dict):
               continue
           source_id = f"{kind_dir[:-1]}:{data.get('id', yaml_path.stem.split('.')[0])}"
           for ref in data.get("tactic_refs", []) or []:
               total_inline += 1
               edge_key = (source_id, f"tactic:{ref}", "uses")
               if edge_key in edges:
                   matched += 1
               else:
                   missing.append({
                       "from": source_id,
                       "to": f"tactic:{ref}",
                       "kind": "uses",
                       "source": str(yaml_path.relative_to(REPO_ROOT)),
                   })
           # handle procedure steps
           for step in data.get("steps", []) or []:
               if isinstance(step, dict):
                   for ref in step.get("tactic_refs", []) or []:
                       total_inline += 1
                       edge_key = (source_id, f"tactic:{ref}", "uses")
                       if edge_key in edges:
                           matched += 1
                       else:
                           missing.append({
                               "from": source_id,
                               "to": f"tactic:{ref}",
                               "kind": "uses",
                               "source": str(yaml_path.relative_to(REPO_ROOT)) + f"::steps[{step.get('id','?')}]",
                           })

   out = REPO_ROOT / "kitty-specs" / "excise-doctrine-curation-and-inline-references-01KP54J6" / "missing_edges.yaml"
   out.parent.mkdir(parents=True, exist_ok=True)
   YAML(typ="safe").dump({
       "total_inline": total_inline,
       "matched": matched,
       "missing": missing,
   }, out)
   print(f"R-1 audit: {total_inline} inline refs; {matched} matched; {len(missing)} missing")
   sys.exit(0 if len(missing) == 0 else 1)
   ```

3. Run it:
   ```bash
   python scripts/r1_inline_vs_graph_audit.py
   ```

   Inspect `kitty-specs/.../missing_edges.yaml`. If `missing` is empty, skip T008. If non-empty, T008 must patch `graph.yaml` before T009.

**Files**:
- Created: `kitty-specs/.../occurrences/WP02.yaml`
- Created: `scripts/r1_inline_vs_graph_audit.py` (ephemeral)
- Created: `kitty-specs/.../missing_edges.yaml` (ephemeral; deleted in T012)

**Validation**:
- [ ] Occurrence artifact YAML conforms to the schema
- [ ] R-1 audit runs and produces `missing_edges.yaml`
- [ ] The `total_inline` count matches the WP02 `to_change` count for `yaml_key: tactic_refs` (sanity cross-check)

---

### T008 — Patch `src/doctrine/graph.yaml` with any missing edges (additive-only)

**Purpose**: Ensure `graph.yaml` carries every cross-artifact relationship that any shipped YAML still expresses inline, BEFORE those inline fields are stripped. Guarantees atomicity: no commit in this PR loses a relationship.

**Steps**:

1. Open `kitty-specs/.../missing_edges.yaml` from T007. If `missing: []`, skip this subtask.

2. For each entry in `missing`:
   - Open `src/doctrine/graph.yaml`
   - Find the edges section
   - Add `{from: <from>, to: <to>, kind: <kind>}` preserving file formatting
   - Add a comment above the addition if the relationship is non-obvious: `# Promoted from inline tactic_refs on <source>; see WP02 for Phase 1 excision context`

3. Re-run `python scripts/r1_inline_vs_graph_audit.py` — `missing` must now be empty (exit 0).

4. Run merged-graph validator as a sanity check:
   ```bash
   python -c "
   from pathlib import Path
   from doctrine.drg.loader import load_graph, merge_layers
   from doctrine.drg.validator import assert_valid
   shipped = load_graph(Path('src/doctrine/graph.yaml'))
   assert_valid(merge_layers(shipped, None))
   print('Graph valid.')
   "
   ```

**Files**:
- Modified: `src/doctrine/graph.yaml` (additive-only; no removals, no reorderings of existing edges)

**Validation**:
- [ ] R-1 audit now exits 0 with `missing: []`
- [ ] Merged-graph validator passes
- [ ] `git diff src/doctrine/graph.yaml` shows only additions (no line removed; comment additions OK)

**Escalation**: If the missing-edges list has more than ~5 entries, stop and comment on [#477](https://github.com/Priivacy-ai/spec-kitty/issues/477). That magnitude indicates a Phase 0 calibration gap that may need an upstream fix.

---

### T009 — Strip `tactic_refs:` from 13 shipped artifact YAMLs

**Purpose**: Remove inline cross-references from shipped artifacts. The graph now carries every relationship (per T008). This is a pure YAML-editing task.

**Steps**:

1. Target files (13 total, verified against `main` at planning):
   - **Directives (8 files)**:
     - `src/doctrine/directives/001-architectural-integrity-standard.directive.yaml`
     - `src/doctrine/directives/003-decision-documentation-requirement.directive.yaml`
     - `src/doctrine/directives/010-specification-fidelity-requirement.directive.yaml`
     - `src/doctrine/directives/018-doctrine-versioning-requirement.directive.yaml`
     - `src/doctrine/directives/024-locality-of-change.directive.yaml`
     - `src/doctrine/directives/025-boy-scout-rule.directive.yaml`
     - `src/doctrine/directives/030-test-and-typecheck-quality-gate.directive.yaml`
     - `src/doctrine/directives/034-test-first-development.directive.yaml`
   - **Paradigms (3 files)**:
     - `src/doctrine/paradigms/atomic-design.paradigm.yaml`
     - `src/doctrine/paradigms/c4-incremental-detail-modeling.paradigm.yaml`
     - `src/doctrine/paradigms/domain-driven-design.paradigm.yaml`
   - **Procedures (2 files)**:
     - `src/doctrine/procedures/refactoring.procedure.yaml`
     - `src/doctrine/procedures/situational-assessment.procedure.yaml`

2. For each YAML:
   - Load with `ruamel.yaml` round-trip mode to preserve comments and key order:
     ```python
     from ruamel.yaml import YAML
     yaml = YAML(typ="rt")
     yaml.preserve_quotes = True
     data = yaml.load(path.read_text())
     ```
   - Delete the top-level `tactic_refs` key: `if "tactic_refs" in data: del data["tactic_refs"]`
   - For procedures, also recurse into `steps[*]`: delete `tactic_refs` from each step entry if present
   - Write back: `yaml.dump(data, path)` (or use `StringIO` → write atomically)
   - Do NOT change any other field, comment, or key ordering

3. **Re-verify** the source list by greping BEFORE starting — inventory may have drifted slightly:
   ```bash
   grep -l "^tactic_refs:" src/doctrine/**/*.yaml 2>/dev/null
   grep -rln "tactic_refs:" src/doctrine/{directives,paradigms,procedures,tactics,styleguides,toolguides,agent_profiles}/ 2>/dev/null | grep -v schemas/
   ```

**Files affected**:
- Modified: 13 shipped YAML files (potentially 14-15 if drift; re-verify)

**Validation**:
- [ ] `grep -Rn "^tactic_refs:\|^  tactic_refs:\|  tactic_refs:" src/doctrine/{directives,paradigms,procedures,tactics,styleguides,toolguides,agent_profiles}/ 2>/dev/null` returns zero hits (outside schemas)
- [ ] Each modified YAML still loads cleanly: `python -c "from ruamel.yaml import YAML; YAML(typ='safe').load(open('<path>').read())"`
- [ ] `git diff` shows only `tactic_refs:` line deletions; no other structural churn

**Parallel opportunity**: T009 (YAML edits) and T010 (schema/model edits) touch disjoint file sets once T008 lands. Assign to separate agents if running in parallel.

---

### T010 — Remove inline ref fields from schemas + Pydantic models

**Purpose**: Strip `tactic_refs`, `paradigm_refs`, `applies_to` from the schema-layer declarations so that validators (in WP03) can reject them uniformly. Also strip `applies_to: list[str]` from `src/charter/schemas.py :: Directive`.

**Steps**:

1. **Schemas** — edit three YAML schema files:
   - `src/doctrine/schemas/directive.schema.yaml`: remove `tactic_refs` + `applies_to` entries from properties
   - `src/doctrine/schemas/paradigm.schema.yaml`: remove `tactic_refs` + `paradigm_refs` entries from properties (if either exists)
   - `src/doctrine/schemas/procedure.schema.yaml`: remove `tactic_refs` entries from both top-level and `steps[*]` properties

2. **Per-kind Pydantic models** — edit each model file to remove field declarations:
   ```
   src/doctrine/directives/models.py      # remove tactic_refs, applies_to
   src/doctrine/paradigms/models.py       # remove tactic_refs, paradigm_refs
   src/doctrine/procedures/models.py      # see special note below for ProcedureStep.tactic_refs
   src/doctrine/tactics/models.py         # remove tactic_refs, paradigm_refs if present
   src/doctrine/styleguides/models.py     # remove tactic_refs if present
   src/doctrine/toolguides/models.py      # remove tactic_refs if present
   src/doctrine/agent_profiles/models.py  # remove tactic_refs, paradigm_refs, applies_to if present
   ```

   For each model:
   - Remove the field declaration (e.g. `tactic_refs: list[str] = Field(default_factory=list)`)
   - Remove any `@field_validator("tactic_refs")` decorators
   - Remove any mentions in class docstrings if present

   **Procedures — special handling**:

   On current `main`, `src/doctrine/procedures/models.py` at **line 54** declares
   `tactic_refs: list[str] = Field(default_factory=list)` on the `ProcedureStep` class
   (inside `Procedure.steps[*]`). This is the step-level embedding that WP02 removes.
   Procedures also have `model_config = ConfigDict(frozen=True, extra="forbid", ...)`
   at the class level (line 49 for `ProcedureStep`, line 68 for `Procedure`), so once
   the field declaration is removed, any procedure YAML that still carries a
   step-level `tactic_refs:` will fail Pydantic validation with `extra_forbidden`.
   That is already a rejection, BUT WP03 adds a pre-Pydantic scan so the user gets
   the structured `InlineReferenceRejectedError` (with migration hint) instead of a
   bare Pydantic error message.

   WP02's job: remove `tactic_refs: list[str] = Field(default_factory=list)` from
   `ProcedureStep`. Leave the `extra="forbid"` config untouched.

   Also re-verify `ProcedureReference` (around line 36): it has a `type: ArtifactKind`
   field that is **not** one of the three forbidden names, so do not touch it.

3. **Charter schemas** — edit `src/charter/schemas.py`:
   - Locate the `Directive` class (around line 87)
   - Remove the `applies_to: list[str]` field declaration
   - Update class docstring if it mentions `applies_to`

4. **Do NOT** modify validators in this WP. Validator rejection is WP03 scope.

**Files affected** (10+ files):
- Modified: 3 schema YAML files
- Modified: 7 Pydantic model files
- Modified: `src/charter/schemas.py`

**Validation**:
- [ ] `grep -Rn "tactic_refs\|paradigm_refs\|applies_to" src/doctrine/schemas/ src/doctrine/**/models.py src/charter/schemas.py` returns zero hits outside docstring mentions that were explicitly carved out (list any in `permitted_exceptions`)
- [ ] `mypy --strict src/` passes

**Parallel opportunity**: Runs in parallel with T009.

---

### T011 — Update model and consistency tests to assert fields are absent

**Purpose**: Test files that asserted `tactic_refs` / etc. exist on model instances must now assert the opposite — that the fields are NOT declared. This prevents regression.

**Steps**:

1. Affected test files (7+ expected; re-grep to confirm):
   ```
   tests/doctrine/directives/test_models.py
   tests/doctrine/paradigms/test_models.py   # if exists
   tests/doctrine/procedures/test_models.py
   tests/doctrine/procedures/test_repository.py
   tests/doctrine/test_artifact_compliance.py
   tests/doctrine/test_artifact_kinds.py
   tests/doctrine/test_enriched_directives.py
   tests/doctrine/test_directive_consistency.py
   tests/doctrine/test_procedure_consistency.py
   tests/doctrine/test_tactic_compliance.py
   tests/doctrine/test_shipped_doctrine_cycle_free.py   # may touch tactic_refs
   ```

2. Update strategy per test:
   - If the test asserts `directive.tactic_refs == [...]`: rewrite to assert the attribute does NOT exist: `assert not hasattr(directive, "tactic_refs")`. Alternatively, remove the assertion entirely if it is the sole focus of the test and delete the test function.
   - If the test iterates artifact files and checks `tactic_refs` content: rewrite to verify the files do NOT carry `tactic_refs` on disk (grep-based or ruamel-load-based).
   - If the test verifies DRG edges derived from inline fields: rewrite to verify the edges exist in `graph.yaml` directly.

3. Do NOT delete these test files — they still provide value (they now test the absence-contract and the graph-driven relationship authority).

4. Check `tests/doctrine/drg/migration/test_extractor.py` — this is Phase 0 DRG extractor code. If its fixtures still carry `tactic_refs` (they may; the extractor was migration-time code), decide with the reviewer whether those fixtures should be updated or preserved as historical. Default: preserve, mark as permitted-exception in WP02.yaml with rationale "DRG extractor fixtures are migration-time inputs from pre-DRG state; retained for regression value."

**Files affected**: 7-12 test files updated in place.

**Validation**:
- [ ] `pytest tests/doctrine/` passes
- [ ] No test asserts the existence of `tactic_refs` / `paradigm_refs` / `applies_to` on any model instance
- [ ] Permitted-exception list in WP02.yaml and index.yaml covers any remaining DRG-extractor-fixture carve-outs

---

### T012 — Delete R-1 script, run gates, update `occurrences/index.yaml`

**Purpose**: Clean up ephemeral tooling, finalize the WP02 occurrence artifact's `to_change` list (must be empty), and ensure mission-level index covers WP02.

**Steps**:

1. Delete ephemeral artifacts:
   ```bash
   rm -f scripts/r1_inline_vs_graph_audit.py
   rm -f kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/missing_edges.yaml
   ```

2. Run full gates:
   ```bash
   pytest tests/
   mypy --strict src/
   python scripts/verify_occurrences.py kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/occurrences/WP02.yaml
   ```
   All three must be green. Verifier must report `VERIFIER GREEN` (empty `to_change` in post-edit run).

3. Update `kitty-specs/.../occurrences/index.yaml`:
   - Append `WP02` to `wps` list (now `[WP01, WP02]`)
   - Ensure `must_be_zero` covers the WP02-scoped strings:
     - `tactic_refs` (in `src/doctrine/`, `src/charter/schemas.py`, `src/doctrine/schemas/`)
     - `paradigm_refs` (in `src/doctrine/`, `src/charter/schemas.py`)
     - `applies_to` (in `src/doctrine/`, `src/charter/schemas.py`)
   - Add any permitted-exceptions discovered in T011 (e.g. DRG extractor fixtures)

4. Run the mission-level verifier:
   ```bash
   python scripts/verify_occurrences.py kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/occurrences/index.yaml
   ```
   Must be `VERIFIER GREEN` for the WP01+WP02 subset of `must_be_zero`.

5. Prepare PR body — paste all verifier outputs, pytest summary, mypy output, and a note that T008 either added N graph edges or found no missing edges. Reference [#477](https://github.com/Priivacy-ai/spec-kitty/issues/477).

**Validation**:
- [ ] Ephemeral script and missing-edges file deleted
- [ ] All three command gates green
- [ ] Verifier green for WP02.yaml and for WP01+WP02 subset of index.yaml
- [ ] Grep: `grep -R "tactic_refs\|paradigm_refs\|applies_to" src/doctrine src/charter/schemas.py` returns zero hits outside permitted exceptions

---

## Definition of Done

- All six subtasks (T007-T012) marked complete in tasks.md
- `kitty-specs/.../occurrences/WP02.yaml` exists; verifier reports green
- `kitty-specs/.../occurrences/index.yaml` updated for WP01 + WP02
- `src/doctrine/graph.yaml` carries every relationship that was previously inline (R-1 empty)
- 13+ shipped YAMLs no longer contain `tactic_refs:`
- 3 schemas no longer declare `tactic_refs`/`paradigm_refs`/`applies_to`
- 7 Pydantic model files no longer declare these fields
- `src/charter/schemas.py :: Directive.applies_to` removed
- All model/consistency tests updated; pytest green
- `mypy --strict src/` clean
- `scripts/r1_inline_vs_graph_audit.py` and `missing_edges.yaml` deleted
- PR opened against `main`, body references #477, includes verifier + pytest + mypy outputs

## Risks & Reviewer Guidance

**Reviewer must check**:

1. **Atomicity of graph-patch + YAML-strip**: `git log --oneline` on this branch should show the graph patch and YAML strips in the same PR (ideally in the same commit or adjacent commits). No intermediate state should leave a relationship orphaned.

2. **No semantic reorderings in YAML**: `ruamel.yaml` round-trip should preserve the non-target fields. `git diff src/doctrine/directives/001-*.directive.yaml` should be a clean single-block deletion of `tactic_refs:` lines.

3. **Pydantic model migrations are symmetric**: every field removed also has its `@field_validator` decorator (if any) removed, and class docstrings updated.

4. **DRG extractor fixtures**: any preserved fixture with `tactic_refs` is listed in `index.yaml` permitted_exceptions with rationale.

5. **No validator changes**: `src/doctrine/**/validation.py` should be unmodified by this PR. Validator rejection is WP03 scope.

**Common mistakes to avoid**:

- Using `YAML(typ="safe")` instead of `YAML(typ="rt")` — safe mode destroys comments and key order
- Deleting `tactic_refs` from `graph.yaml` itself — the FIELD name lives in graph edge definitions only as part of the edge-kind naming; verify no accidental deletion in graph.yaml
- Forgetting to recurse into `procedure.steps[*]` for `tactic_refs` stripping
- Modifying agent profiles outside `src/doctrine/agent_profiles/models.py` — agent-profile YAML files under `src/doctrine/agent_profiles/*.yaml` do not currently carry the three forbidden fields, but verify with grep before claiming WP02 complete

## Escalation criteria

Stop and comment on [#477](https://github.com/Priivacy-ai/spec-kitty/issues/477) if:
- R-1 missing-edges list has >5 entries (Phase 0 calibration gap)
- A schema change breaks an OtheR_KIND artifact in a way not covered by the known inventory
- `assert_valid()` on the merged graph fails after T008's graph patch (cycle introduced?)
- A model-test-deletion cascades into a broader test failure not caught in the specify-phase inventory

## Activity Log

- 2026-04-14T06:29:32Z – claude:opus-4.6:python-implementer:implementer – shell_pid=50403 – Started implementation via action command
- 2026-04-14T06:53:09Z – claude:opus-4.6:python-implementer:implementer – shell_pid=50403 – WP02 complete: 14 shipped/legacy YAMLs stripped (12 top-level tactic_refs + 6 procedure step-level); 3 schemas + 3 models (Directive/Paradigm/ProcedureStep) + charter/schemas.py::Directive.applies_to stripped; graph.yaml patched additive-only with 25 new procedure-step requires edges (TEST_FIRST legacy directive not a graph node — inline refs stripped from its YAML without promotion); affected WP02-scoped tests rewritten to assert fields are absent; WP02 + index verifiers GREEN; graph assert_valid() passes; WP02-scoped pytest 396 passed. Expected inter-WP failures in WP03 scope: tests/doctrine/drg/migration/test_extractor.py, tests/doctrine/test_shipped_doctrine_cycle_free.py (3 cases), tests/merge/test_profile_charter_e2e.py — WP03 rewrites reference_resolver.
- 2026-04-14T06:54:33Z – opencode:gpt-5:python-reviewer:reviewer – shell_pid=96242 – Started review via action command
