---
work_package_id: WP03
title: 'charter.yaml writer + #2772 clobber guard (partial/merge emit)'
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-007
- FR-011
tracker_refs:
- '#2773'
- '#2772'
planning_base_branch: feat/consolidate-charter-bundle
merge_target_branch: feat/consolidate-charter-bundle
branch_strategy: Planning artifacts for this mission were generated on feat/consolidate-charter-bundle. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/consolidate-charter-bundle unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- tests/charter/test_compiler_charter_yaml.py
execution_mode: code_change
owned_files:
- src/charter/compiler.py
- src/specify_cli/cli/commands/charter/generate.py
- src/specify_cli/cli/commands/charter/_synthesis.py
- src/specify_cli/cli/commands/charter_bundle.py
- tests/charter/test_compiler_charter_yaml.py
- tests/charter/test_compiler.py
- tests/charter/test_generator.py
- tests/specify_cli/cli/commands/test_charter_generate_autotrack.py
- tests/agent/cli/commands/test_charter_cli.py
role: implementer
tags: []
shell_pid_created_at: "1784383657.86"
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "430495"
---

## ⚡ Do This First: Load Agent Profile
Load `/ad-hoc-profile-load python-pedro` (implementer). Load the YAML.

## Objective
Make the compile pipeline emit `charter.yaml` as a **PARTIAL / MERGE write** (refresh only the DERIVED `catalog` + `metadata`; preserve AUTHORED `governance`/`directives`/`activation`/`overrides` byte-for-byte), **remove the `charter.md` clobber** (folds #2772), and retire the `references.yaml` writer.

**Authoritative**: [`data-model.md`](../data-model.md) **Landmine 3** + INV-9, [`contracts/charter-yaml-schema.md`](../contracts/charter-yaml-schema.md) G5. Consumes WP01's shared write helper.

## Context / grounding
- `src/charter/compiler.py:393-421 write_compiled_charter` — the full-file overwrite (`charter_path.write_text(compiled.markdown)` at `:421` = the #2772 clobber). `_write_references_yaml:1218` — the references writer to retire. `:367 _render_charter_markdown` feeds the clobber.
- `generate.py:344-352` autotrack/gitignore; `charter_bundle.py:68-78 _OUT_OF_SCOPE_WARNINGS` (references special-case).

## Subtasks

### T011 — Emit charter.yaml via a partial/merge write
- Compile emits/refreshes `charter.yaml`'s **derived** `catalog` (from the resolved references) + `metadata.generated_at` **through WP01's shared write helper**, preserving the authored sections byte-for-byte. Treat `activation` as **read-only input** (never round-trip it through a derive step — this dissolves the catalog←activation circularity).
- ⚠ **Landmine 3**: do NOT reconstruct the whole file from `CompiledCharter` state (that is the internal clobber). Only the derived sections change.

### T012 — Remove the charter.md clobber + retire references writer
- Remove/guard `compiler.py:421 charter_path.write_text(...)` so no generate/compile path writes `charter.md` (it is a curated companion now). Retire `_write_references_yaml:1218` (references.yaml no longer emitted).

### T013 — generate.py autotrack + charter_bundle.py + #2758 preflight message
- Update `generate.py` autotrack so `charter.yaml` is git-tracked (not gitignored); remove the four bundle files from the autotrack/gitignore surface (`generate.py:346` hardcodes `.kittify/charter/references.yaml` — remove). Update `charter_bundle.py` `_OUT_OF_SCOPE_WARNINGS` (references special-case now moot).
- **#2758 preflight (paula/renata)**: `_synthesis.py:519-527 _charter_bundle_preflight` calls `first_missing_bundle_file` (kept by WP01 — it auto-narrows to a charter.yaml existence check once `BUNDLE_CONTENT_HASH_FILES=("charter.yaml",)`). Update its message from "run charter generate first (references.yaml)" to a "charter.yaml missing — run the migration/generate" fail-loud guard (C-003). Do NOT delete the guard — it becomes the desired fail-loud check.
- ⚠ **Campsite (carla)**: `generate.py:205 generate()` is at complexity **15** (ceiling). If the autotrack edit adds any branch, extract a helper to stay ≤15 (C901/S3776). `charter_bundle.py:264` (cx14) / `:194` (cx12) — don't add branches.

### T014 — Regenerate spec-kitty's own charter.yaml + MINT the config pointer
- Run the compile to produce THIS repo's `.kittify/charter/charter.yaml` and commit it — otherwise WP04's re-pointed consumers fail on spec-kitty itself. (Seed governance/directives/catalog/activation from the current triad + config; see WP07 migration for the fold shape.)
- ⚠ **Close the init-pointer gap (WP02 review):** `_bootstrap_charter_yaml` (or the generate path) must ALSO **mint the `charter: .kittify/charter/charter.yaml` pointer into `config.yaml`** when it creates charter.yaml. Otherwise a project that never ran the WP07 migration (esp. a NEW `spec-kitty init` project) falls to the config-activation branch permanently — turning WP02's *transitional* dual-branch into a permanent split-brain. This + WP07's migration together guarantee every active project gets the pointer. (Do NOT touch `init.py` — that's the fenced #2519 init surface; minting at first-generate covers new projects.) Commit this repo's own config.yaml pointer as part of T014.

### T014b — Own + fix the retired-contract tests (orphan-assigned)
- WP03's write-contract change (no charter.md write, no references.yaml, force is a no-op) breaks tests asserting the OLD contract. Update the now-owned `tests/charter/test_compiler.py` (5) + `tests/charter/test_generator.py::test_write_compiled_charter_rejects_symlink_even_with_force` to the new charter.yaml partial-write world. (The cross-cutting `tests/merge/test_profile_charter_e2e.py` is assigned to WP07's final sweep.)

### T015 — Invert the clobber tests
- Update `test_charter_generate_autotrack.py` + `tests/agent/cli/commands/test_charter_cli.py`: assert a curated `charter.md` and authored `charter.yaml` governance/activation **survive** `charter generate --force` (the #2772 guard, now on charter.yaml). New `tests/charter/test_compiler_charter_yaml.py`: partial write refreshes only catalog/metadata.

## ATDD (red-first)
Red-first through `charter generate --force`: author a governance value in `charter.yaml`, run generate, assert it survives (RED until T011/T012 partial-write lands).

## Branch Strategy
Base `feat/consolidate-charter-bundle` per `lanes.json` (dep WP01); merges back to `feat/consolidate-charter-bundle`.

## Definition of Done
- Compile emits charter.yaml via the shared helper (partial/merge); clobber removed; references writer retired; spec-kitty's own charter.yaml regenerated + committed; clobber tests inverted.
- ruff + mypy --strict clean; complexity ≤15.

## Reviewer guidance
- Verify a recompile does NOT overwrite authored governance/activation (the internal-clobber guard).
- Verify `charter.md` is never written by generate/compile.
- Verify `references.yaml` is no longer emitted.

## Activity Log

- 2026-07-18T13:11:10Z – claude:sonnet:python-pedro:implementer – shell_pid=298325 – Assigned agent via action command
- 2026-07-18T13:47:49Z – claude:sonnet:python-pedro:implementer – shell_pid=298325 – charter.yaml partial-write emit implemented (T011-T015): write_compiled_charter refreshes ONLY catalog+metadata via the shared INV-9 write helper, authored governance/directives/activation/overrides survive byte-for-byte; charter.md never written; references.yaml writer retired; spec-kitty's own charter.yaml regenerated+committed. Gates: ruff clean, mypy --strict clean (2 pre-existing unrelated errors verified), 40 owned tests pass (1 skip, no symlink support). Collateral: non-owned tests/charter/test_compiler.py, test_generator.py, tests/merge/test_profile_charter_e2e.py, tests/next/test_prompt_builder_unit.py assert the old charter.md/references.yaml write contract and are now stale (not fixed, outside owned_files). tests/charter/test_references_missing_failclosed.py was already broken by WP01's BUNDLE_CONTENT_HASH_FILES narrowing before this WP.
- 2026-07-18T13:55:42Z – user – Moved to planned
- 2026-07-18T13:56:00Z – claude:sonnet:python-pedro:implementer – shell_pid=411869 – Started implementation via action command
- 2026-07-18T14:07:03Z – claude:sonnet:python-pedro:implementer – shell_pid=411869 – cycle2: T014b retired-contract tests fixed (test_compiler.py x4 re-pinned, symlink test re-pinned in test_generator.py) + config charter: pointer minted on charter.yaml bootstrap (closes WP02-review split-brain gap), this repo's own config.yaml pointer committed. Gates: ruff clean, mypy --strict clean, 86 passed/1 skipped across owned tests.
- 2026-07-18T14:07:40Z – claude:opus:reviewer-renata:reviewer – shell_pid=430495 – Started review via action command
- 2026-07-18T14:17:14Z – user – shell_pid=430495 – APPROVE cycle-2. Landmine 3 internal-clobber PREVENTED (partial refresh of catalog+metadata via WP01 helper; authored governance/directives/activation/overrides survive byte-for-byte, pinned by test_authored_*_survive_refresh). #2772 clobber removed (no charter.md write, references writer retired, force no-op). T014 bootstrap+pointer-mint VERIFIED: this repo's config.yaml pointer minted comment-preservingly + charter.yaml committed/tracked with activation seeded verbatim. #2758 preflight re-messaged, guard kept. Gates: ruff clean, mypy=2 pre-existing zero-diff, 86 passed/1 skipped. Scope clean, init.py untouched. Symlink-guard: acceptable narrowing (partial in-place write follows symlink to target preserving authored content + symlink; NOT rename-based; dir-guard remains) -> follow-up not regression. Unblocks WP04+WP08. Full detail in review-cycle-2.md.
