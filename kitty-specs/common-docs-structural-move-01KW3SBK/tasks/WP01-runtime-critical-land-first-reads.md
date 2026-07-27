---
work_package_id: WP01
title: Land-first runtime-critical reads (6 reads, dual-read + resolution tests, BEFORE any move)
dependencies: []
requirement_refs:
- FR-005
- NFR-005
- C-003
tracker_refs: []
planning_base_branch: docs/2165-mission-b-structural-move
merge_target_branch: docs/2165-mission-b-structural-move
branch_strategy: Planning artifacts for this mission were generated on docs/2165-mission-b-structural-move. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-mission-b-structural-move unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/context_renderers/authority_paths.py
create_intent:
- tests/docs/test_runtime_read_resolution.py
execution_mode: code_change
owned_files:
- src/charter/context_renderers/authority_paths.py
- src/specify_cli/compat/doctor.py
- src/specify_cli/compat/registry.py
- src/specify_cli/cli/commands/doctor.py
- scripts/generate_contextive_glossaries.py
- .kittify/charter/charter.md
- tests/docs/test_runtime_read_resolution.py
role: implementer
tags: []
shell_pid: "1284515"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile: run `/ad-hoc-profile-load python-pedro` (or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it). State which directives apply, then proceed.

## Objective

Re-point the **six land-first runtime-critical reads** — the `src/` and non-`src/` code/config that *resolve a real file at runtime* — onto their post-move doc paths, **each with a resolution test proving the new path resolves**, and stage every one as a **dual-read (old ∪ new)** so nothing breaks **before** the tree moves in WP03. This is the C-003 / NFR-005 spine head: a read that dereferences a not-yet-moved path, or a not-yet-rewritten read after the move, is a **runtime break**, not a dead link.

This WP **does not move any file**. It edits target literals in place and adds resolution tests. The actual tree move lands in WP03; the dual-read old branches are dropped after WP03 (the drop is scheduled in WP08's reference sweep, not here).

## Context

`authority_paths.py` lives at **`src/charter/context_renderers/authority_paths.py`** (not `src/specify_cli/charter/...`) and already reflects the #2160/#2115 ADR-default flip (`architecture/3.x/adr/` default with `architecture/2.x/adr/` back-compat). The occurrence map (`occurrence_map.yaml` → `status.runtime_critical_reads`) is the authority for the exact files, literals, and line numbers. Read it before touching anything.

**The 6 reads (re-derived live, C-003):**

1. `authority_paths.py` → `architecture/3.x/adr/` — the ADR-default read (already 3.x via #2160/#2115; verify it still resolves after `architecture/` folds into `docs/adr/3.x/`).
2. `authority_paths.py` → `glossary/contexts/` — **becomes runtime-critical** when the glossary moves to `docs/context/` (FR-009 / C-006). This is the **4th read the spec's "~3" snapshot missed**.
3. `src/specify_cli/compat/doctor.py:~69` → `architecture/2.x/shim-registry.yaml` (`check_shim_registry()`).
4. `src/specify_cli/compat/registry.py:~51` → the same shim-registry read.
5. `scripts/generate_contextive_glossaries.py:~30` → `GLOSSARY_CONTEXTS_DIR = REPO_ROOT / "glossary" / "contexts"` — the **C-006 doctrine-extraction source** (merge-blocker).
6. `.kittify/charter/governance.yaml` `authority_paths` block (~lines 33–36) → `glossary/contexts/`, `architecture/3.x/adr/`, `architecture/adrs/`.

**Shim-registry destination DECLARED:** `architecture/2.x/shim-registry.yaml` → **`docs/migrations/shim-registry.yaml`** (the stable section that pairs with `06_migration_and_shim_rules.md`). The paired user-facing **remediation string** at `src/specify_cli/cli/commands/doctor.py:509` re-points in lock-step (it is `user_facing_strings` in the occurrence map, but it must stay coherent with the readers, so it lives in this WP).

**Glossary destination:** `glossary/contexts/` → **`docs/context/`** (FR-009). The dashboard `GlossaryHandler` reads `.kittify/glossaries/<scope>.yaml` **seed files** via `load_seed_file()` — that seed read-path is **not** moved (C-006); only the human markdown relocates and the extraction-source literal re-points.

## Requirement refs (hints for the orchestrator's map-requirements)

FR-005 (the `src/`-first reference rewrites), NFR-005 (resolution tests prove the new path resolves), C-003 (runtime-critical rewrites land + tested first, before any tree move), C-006 (glossary read-path preserved — partially; the extraction-source literal is here, the seed read-path lives in WP03).

## Subtasks

### T001 — Read the occurrence map's runtime-read contract
Read `occurrence_map.yaml` `exceptions:` + `status.runtime_critical_reads` + `targeted_ref_updates`. Confirm the 6 files, their literals, the declared destinations (`docs/migrations/shim-registry.yaml`, `docs/context/`, `docs/adr/3.x/`), and that `.kittify/` + `scripts/` are out-of-relocate-scope (literals re-pointed in place, files NOT moved). Record any drift between the map and the live tree as a blocker — do not improvise.

### T002 — Author the resolution-test harness (RED-first)
Create `tests/docs/test_runtime_read_resolution.py`. For each of the 6 reads, write a test that asserts the **new** path resolves (i.e. that the reader, given the post-move layout, finds a real file). Seed the new-path fixtures so the test is meaningful **before** WP03 moves the real tree (use a tmp fixture tree mirroring `docs/migrations/`, `docs/context/`, `docs/adr/3.x/`). Prove the test is RED against the pre-edit code (the readers still point only at the old path), then green after the dual-read edit. Red-first through the pre-existing reader entry point, not the new literal.

### T003 — `authority_paths.py`: dual-read ADR + glossary literals
In `src/charter/context_renderers/authority_paths.py`, stage `DEFAULT_AUTHORITY_PATHS` to resolve **`architecture/3.x/adr/` ∪ `docs/adr/3.x/`** and **`glossary/contexts/` ∪ `docs/context/`**. Mirror the existing #2160/#2115 back-compat pattern (3.x default + 2.x fallback) — add the new `docs/` home as an additional candidate, do not delete the old yet. The glossary literal is the missed 4th read: it is inert today and becomes live when WP03 moves the glossary; the dual-read makes WP03 safe.

### T004 — Shim-registry readers: dual-read to `docs/migrations/`
In `src/specify_cli/compat/doctor.py` (`check_shim_registry()`, ~line 69) and `src/specify_cli/compat/registry.py` (~line 51), stage the read as `architecture/2.x/shim-registry.yaml` **∪** `docs/migrations/shim-registry.yaml` (prefer the new home, fall back to old). Keep the two readers byte-coherent (same resolution helper if one exists; otherwise the same candidate order).

### T005 — Remediation string lock-step (`cli/commands/doctor.py:509`)
Re-point the user-facing remediation string at `src/specify_cli/cli/commands/doctor.py:509` to name `docs/migrations/shim-registry.yaml` (the new canonical home), coherent with T004's readers. This is `user_facing_strings` per the occurrence map but must not drift from the readers.

### T006 — Non-`src/` read 5: `generate_contextive_glossaries.py`
In `scripts/generate_contextive_glossaries.py` (~line 30), re-point `GLOSSARY_CONTEXTS_DIR` to resolve `glossary/contexts/` **∪** `docs/context/`. The script is out-of-relocate-scope (NOT moved); only its target literal updates. This is the C-006 doctrine-extraction source — a break here is a merge-blocker.

### T007 — Non-`src/` read 6: `governance.yaml` authority_paths
In `.kittify/charter/governance.yaml` `authority_paths` block (~lines 33–36), re-point `glossary/contexts/` → `docs/context/`, `architecture/3.x/adr/` → `docs/adr/3.x/`, `architecture/adrs/` → `docs/adr/3.x/`. Config is out-of-relocate-scope (NOT moved); only the authority-path VALUES update. This is also the `targeted_ref_updates` critical entry — same edit, resolution-tested.

### T008 — Prove all 6 reads resolve + suite green
Run `tests/docs/test_runtime_read_resolution.py` (all 6 green against the new-path fixtures) and the touched-module unit suites. Run `ruff check` + `mypy` on every touched `src/` file (zero issues, zero new ignores). Confirm the dual-read leaves the OLD path still resolving (so the tree is not yet broken — WP03 has not run).

## Surfaces & Loci (from `occurrence_map.yaml` `runtime_critical_reads` + `targeted_ref_updates`)

| Surface | Locus | Old literal | New literal | Move kind |
|---------|-------|-------------|-------------|-----------|
| `src/charter/context_renderers/authority_paths.py` | `DEFAULT_AUTHORITY_PATHS` | `architecture/3.x/adr/` | `docs/adr/3.x/` (∪ old) | dual-read (verify post-fold) |
| `src/charter/context_renderers/authority_paths.py` | `DEFAULT_AUTHORITY_PATHS` | `glossary/contexts/` | `docs/context/` (∪ old) | dual-read (4th read, spec-missed) |
| `src/specify_cli/compat/doctor.py` | `check_shim_registry()` ~L69 | `architecture/2.x/shim-registry.yaml` | `docs/migrations/shim-registry.yaml` (∪ old) | dual-read |
| `src/specify_cli/compat/registry.py` | ~L51 | `architecture/2.x/shim-registry.yaml` | `docs/migrations/shim-registry.yaml` (∪ old) | dual-read |
| `src/specify_cli/cli/commands/doctor.py` | remediation string ~L509 | `architecture/2.x/shim-registry.yaml` | `docs/migrations/shim-registry.yaml` | `user_facing_strings`, lock-step |
| `scripts/generate_contextive_glossaries.py` | `GLOSSARY_CONTEXTS_DIR` ~L30 | `glossary/contexts/` | `docs/context/` (∪ old) | in-place literal (file NOT moved) |
| `.kittify/charter/governance.yaml` | `authority_paths` ~L33–36 | `glossary/contexts/`, `architecture/3.x/adr/`, `architecture/adrs/` | `docs/context/`, `docs/adr/3.x/` | in-place values (file NOT moved) |

The seed read-path `.kittify/glossaries/<scope>.yaml` (dashboard `GlossaryHandler` / `load_seed_file()`) is **NOT** a literal in this WP and **must not change** (C-006).

## Requirement → Subtask Traceability

| Requirement | Subtasks |
|-------------|----------|
| FR-005 (`src/`-first reference rewrites, runtime set first) | T001, T003, T004, T005 |
| NFR-005 (resolution tests prove the new path resolves) | T002, T008 |
| C-003 (runtime-critical rewrites land + tested before any move; dual-read) | T002–T008 |
| C-006 (glossary extraction-source literal re-points without break) | T006, T007 |

## Branch Strategy

Planning + final merge target: `docs/2165-mission-b-structural-move`. This is the **spine head** — it gates WP02 and every move WP. The dual-read old branches are intentionally retained; they are dropped in WP08's reference sweep after WP03 lands the move.

## Definition of Done

- [ ] All **6 land-first reads** re-pointed as dual-read (old ∪ new); no old branch dropped here.
- [ ] `tests/docs/test_runtime_read_resolution.py` exists, was **RED-first** through the pre-existing reader entry point, and is green for all 6 reads against new-path fixtures.
- [ ] The shim-registry destination is `docs/migrations/shim-registry.yaml` across all 3 readers + the remediation string, coherently.
- [ ] **Redirect/back-compat in place so no reference or runtime read breaks** — the old path still resolves (tree not yet moved); the new path resolves (proven by test). This is the C-003 dual-read invariant.
- [ ] C-006 extraction-source (`generate_contextive_glossaries.py`) re-points without breaking; the `.kittify/glossaries/<scope>.yaml` seed read-path is untouched (it is not a literal in this WP).
- [ ] `ruff` + `mypy` clean on all touched `src/` files; terminology guard clean.
- [ ] Full unit suite green.

## Risks & Reviewer Guidance

- **Reviewer (merge-blocker focus):** verify C-006 — confirm `generate_contextive_glossaries.py` and the dashboard `GlossaryHandler`/`load_seed_file()` path are not broken by the literal change (the seed read-path must remain `.kittify/glossaries/<scope>.yaml`).
- **Dropping the dual-read too early** (before WP03) is a runtime break — confirm both old AND new branches resolve at end of this WP.
- **Mis-identifying the runtime set** — trust `occurrence_map.yaml` `runtime_critical_reads`, not the stale "~3 reads" snapshot; the glossary literal (read #2) and the governance config (read #6) are the two the spec missed.
- The resolution test must exercise the **reader**, not just assert a string equals a path — a string-equality test is a false-green.

## Activity Log

- (populated at implement time)
- 2026-06-27T12:06:12Z – claude:opus:python-pedro:implementer – shell_pid=1233974 – Assigned agent via action command
- 2026-06-27T12:26:36Z – claude:opus:python-pedro:implementer – shell_pid=1233974 – Ready: 6 runtime reads dual-read + resolution-tested (15 passed; RED-first proven 9-fail on reverted source). ruff=0 mypy=0 on changed src; compat regression 110 passed. IC-01: read#6 re-pointed in canonical .kittify/charter/charter.md (governance.yaml is gitignored/generated; scope-warning expected).
- 2026-06-27T12:31:15Z – claude:opus:reviewer-renata:reviewer – shell_pid=1284515 – Started review via action command
- 2026-06-27T12:38:40Z – user – shell_pid=1284515 – Review passed: 6 dual-reads verified; 15 resolution tests pass non-vacuous (real readers; spot-check reds on reverting docs/context candidate); C-006 seed read-path untouched; zero file renames (move deferred WP03); ruff 0, mypy 0 on src (script yaml import-untyped pre-existing); manual_review sound (doctor.py 1-line string; governance.yaml gitignored so charter.md edit correct). issue-matrix set in-mission (spine head).
