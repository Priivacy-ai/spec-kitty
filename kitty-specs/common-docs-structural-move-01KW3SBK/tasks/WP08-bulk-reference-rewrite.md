---
work_package_id: WP08
title: Bulk reference rewrite (~1299 occ rewrite target via occurrence map; kitty-specs excluded) + targeted-ref-updates + CHANGELOG alias refs
dependencies:
- WP03
- WP06
- WP16
requirement_refs:
- FR-005
- FR-009
tracker_refs: []
planning_base_branch: docs/2165-mission-b-structural-move
merge_target_branch: docs/2165-mission-b-structural-move
branch_strategy: Planning artifacts for this mission were generated on docs/2165-mission-b-structural-move. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-mission-b-structural-move unless the human explicitly redirects the landing branch.
subtasks:
- T046
- T047
- T048
- T049
- T050
- T051
- T052
- T053
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: scripts/docs/bulk_ref_rewrite.py
create_intent:
- scripts/docs/bulk_ref_rewrite.py
- tests/docs/test_bulk_ref_rewrite.py
execution_mode: code_change
owned_files:
- .github/workflows/ci-quality.yml
- .kittify/glossaries/spec_kitty_core.yaml
- pyproject.toml
- scripts/docs/anti_sprawl_ratchet.py
- scripts/docs/bulk_ref_rewrite.py
- tests/docs/test_bulk_ref_rewrite.py
role: implementer
tags: []
shell_pid: "1914509"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile: run `/ad-hoc-profile-load python-pedro` (or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it). State which directives apply, then proceed.

## Objective

Rewrite the **~1299 in-tree references** (rewrite target) to moved doc paths, driven by `occurrence_map.yaml` (the 8 categories + `moves:`), plus the **targeted-ref-updates** (the `ci-quality.yml` glob, the two glossary functional refs, the governance re-points, cosmetic comments) and the **CHANGELOG relocate-with-alias** reference handling. This is the IC-05b bulk-edit core. It also **drops the WP01 dual-read old branches** now that WP03/WP06 have landed the moves.

**Blast radius (corrected):** the repo-wide census is 2920 occ / 751 files, but **`kitty-specs/` (1621 occ / 453 files) is `do_not_change`** — immutable historical mission snapshots (Terminology Canon; the WP07 redirect stubs already preserve URL continuity, and kitty-specs/ is not published). So the **rewrite target is 1299 occ / 298 files** (2920−1621 / 751−453). Do **not** rewrite any reference under `kitty-specs/`.

## The bulk rewrite is TOOL-DRIVEN, not a manual sweep (build `bulk_ref_rewrite.py`)

The 1299-occ / 298-file sweep is **not** done by hand or by an ad-hoc `sed`. Author **`scripts/docs/bulk_ref_rewrite.py`** as the first step of the sweep (T049, before any rewriting): a deterministic rewriter that
- **reads `occurrence_map.yaml`** — the `moves:` path-pairs (old-prefix → new-prefix) are the substitution table; the `exceptions:` + per-category `action:` fields are the **filter**;
- **enforces the `do_not_change` filter**: skips every path matching a `do_not_change` exception (foremost `kitty-specs/**`, `docs/1x/**`, `docs/2x/**`) and every `do_not_change` category (`code_symbols`, `import_paths`, `cli_commands`, `logs_telemetry`); also skips `serialized_keys` (WP09) and frontmatter fields (WP12);
- **applies path substitutions per file** in the census areas it owns (`src/` non-runtime, `tests/`, `docs/` prose, `architecture/` residuals, `root_md`);
- is **idempotent + dry-run-able** (`--dry-run` prints the planned diff; a second real run is a no-op) so the reviewer can inspect the planned blast radius before it lands;
- is covered by **`tests/docs/test_bulk_ref_rewrite.py`** proving: (a) a `moves:` prefix is rewritten, (b) a `kitty-specs/` ref is left untouched, (c) a `do_not_change`-category literal (e.g. an import path) is left untouched, (d) the run is idempotent.

This is a committed migration tool (not throwaway) — it documents exactly what the sweep did and lets the reviewer re-run the dry-run to verify completeness.

## Context — this is a `bulk_edit` mission; `occurrence_map.yaml` GOVERNS the edits

`occurrence_map.yaml` is the classification authority. **Ownership note (bulk_edit leeway):** the ~1299-occ rewrite spans `src/`, `tests/`, and `docs/` prose (**`kitty-specs/` is `do_not_change` — out of scope entirely**), but those broad globs are **deliberately NOT declared in `owned_files`** — the static no-overlap guard would otherwise false-flag them against the move WPs (WP03/WP06) and the frontmatter WP (WP12) that legitimately create/own those same files. `owned_files` here lists the **bulk-rewrite tool** this WP authors (`bulk_ref_rewrite.py` + its test) plus the **sole targeted-ref surfaces** this WP exclusively edits (`ci-quality.yml`, the `spec_kitty_core.yaml` glossary refs, `pyproject.toml`, `anti_sprawl_ratchet.py`); the cross-cutting reference rewrite is **occurrence-map-governed**, not glob-governed. Where the rewrite touches files also owned by WP09 (`docs/**/toc.yml`, `docfx.json`) and WP12 (`docs/**/*.md` frontmatter), the **occurrence-map category partition** disjoints the real edits:
- **WP08** edits `user_facing_strings` + `filesystem_paths` references (prose links, path literals) and the dual-read old-branch drops.
- **WP09** edits `serialized_keys` (`docfx.json` globs, `toc.yml` href values) — a different category.
- **WP12** edits frontmatter **fields** (`doc_status`/`description`/`related`) — not path references.

These are sequenced (WP09 after WP03; WP12 after WP11) and category-disjoint; flag the `docs/**/*.md` co-tenancy to the orchestrator as an **expected, occurrence-map-governed bulk overlap**, not a true conflict.

**Per-area census** (`occurrence_map.yaml` `status.live_census.per_area`): src 84/49, tests 125/81, **kitty-specs 1621/453 → `do_not_change` (NOT rewritten — immutable snapshots)**, docs 743/75, architecture 284/69, root_md 35/4. Repo-wide 2920/751; **rewrite target 1299 occ / 298 files** (kitty-specs excluded).

**Targeted-ref-updates (surgical, reviewed — NOT heuristic path-rewrites):**
- `.github/workflows/ci-quality.yml` (~line 411): re-point the changed-markdown glob `'architecture/*.md' 'architecture/**/*.md'` onto `docs/**` — **CRITICAL: gate-silent-death risk** (once `architecture/` is gone the consistency gate stops firing).
- `.kittify/glossaries/spec_kitty_core.yaml` (~lines 375, 482): two refs to `architecture/2.x/04_implementation_mapping/code-patterns.md` → `docs/architecture/code-patterns.md`.
- `.kittify/charter/governance.yaml` authority_paths: already re-pointed in WP01 (land-first) — verify, do not double-edit.
- `pyproject.toml` + `anti_sprawl_ratchet.py` docstring: cosmetic, low-priority.

**CHANGELOG relocate-with-alias:** root `CHANGELOG.md` persists (release tooling reads it). Rewrite *prose references* that should point at the canonical `docs/changelog/`, but do **not** re-point the out-of-relocate-scope release tooling (`scripts/release/`, `pyproject.toml`, `.github/release-readiness.yml`) — they read root by contract.

## Requirement refs (hints for the orchestrator's map-requirements)

FR-005 (rewrite ALL doc-path references via the occurrence map, 8 categories; `src/` non-runtime refs after WP01's runtime-critical set; then doctrine/`kitty-specs/`/tests/docs), FR-009 (CHANGELOG/glossary/journeys mapping references).

## Subtasks

### T046 — Drop the WP01 dual-read OLD branches
Now that WP03/WP06 landed the moves, remove the old-path branches staged in WP01 (`architecture/2.x/shim-registry.yaml`, `glossary/contexts/`, `architecture/3.x/adr/` old literals) so the readers point only at the new homes. Re-run `tests/docs/test_runtime_read_resolution.py` — still green (new path resolves; old path is gone).

### T047 — Rewrite the remaining `src/` references (the ~39 non-runtime)
Per the occurrence map `filesystem_paths` + `user_facing_strings`, rewrite the remaining `src/` doc-path references (module-docstring prose, the `events/adapter.py "docs/development/ssh-deploy-keys.md"` literal, etc.). `code_symbols`/`import_paths` are `do_not_change` (no symbol/import encodes a doc path).

### T048 — Rewrite `tests/` fixtures + assertions
Per `tests_fixtures: rename`, update the ~125 occurrences across ~81 test files that hard-code old doc paths to the new layout. (The runtime resolution tests are WP01's — do not duplicate.)

### T049 — Build `bulk_ref_rewrite.py`, then rewrite `docs/` prose references
**First** author `scripts/docs/bulk_ref_rewrite.py` + `tests/docs/test_bulk_ref_rewrite.py` (see "tool-driven" section above) — the occurrence-map-driven, `do_not_change`-filtering, idempotent, `--dry-run`-able rewriter. **Then** run it over the `docs/` prose: ~743 occurrences (prose links, llms.txt mentions → new locations, `user_facing_strings: rename_if_user_visible`). **`kitty-specs/` is `do_not_change` — DO NOT rewrite its 1621 refs** (immutable historical snapshots; WP07 stubs cover URL continuity). Exclude `serialized_keys` (WP09) and frontmatter fields (WP12).

### T050 — Targeted-ref-update: `ci-quality.yml` glob (CRITICAL)
Re-point the `ci-quality.yml` changed-markdown glob from `architecture/*.md`/`architecture/**/*.md` onto `docs/**`. This is the gate-silent-death fix — without it the markdown consistency gate stops firing once `architecture/` is gone. (The consistency TEST `tests/docs/test_architecture_docs_consistency.py` is rewritten under T048.)

### T051 — Targeted-ref-update: glossary functional refs + governance verify
Re-point the two `.kittify/glossaries/spec_kitty_core.yaml` refs to `docs/architecture/code-patterns.md`. Verify `.kittify/charter/governance.yaml` authority_paths (WP01-edited) is correct; do not double-edit. Handle `pyproject.toml` + `anti_sprawl_ratchet.py` cosmetic comments (optional/low-priority).

### T052 — CHANGELOG reference rewrite (alias-aware)
Rewrite prose references that should point at canonical `docs/changelog/`, while leaving the out-of-relocate-scope release tooling (root `CHANGELOG.md` readers) untouched. Confirm the root alias still exists (WP03 kept it).

### T053 — Verify the sweep + suite green
Confirm no live reference points at a removed `architecture/` path (a residual `architecture/<era>/adr` reference is a dead link, or a runtime break if in `src/`). Run `ruff`/`mypy` on touched `src/`+`tests/`+`bulk_ref_rewrite.py`, the terminology guard, and a repo-wide grep for stale `architecture/` doc-path references (excluding `docs/architecture/`, **`kitty-specs/` (do_not_change immutable snapshots)**, and intentional historical snapshots). Capture the **pre-sweep** stale-ref count too, to prove the grep is non-vacuous.

## Surfaces & Loci (per-area census + targeted-ref-updates)

| Area | Occurrences / files | Occurrence-map action |
|------|---------------------|-----------------------|
| `src/` (non-runtime) | 84 / 49 (minus WP01's set) | `filesystem_paths` / `user_facing_strings` rename |
| `tests/` | 125 / 81 | `tests_fixtures: rename` |
| `kitty-specs/` | 1621 / 453 | **`do_not_change` — immutable snapshots, NOT rewritten** |
| `docs/` | 743 / 75 | prose refs (excl. WP09 serialized + WP12 frontmatter) |
| `architecture/` | 284 / 69 | residual refs post-move |
| root_md | 35 / 4 | CHANGELOG alias-aware |
| **rewrite target** | **1299 / 298** | repo-wide 2920/751 minus kitty-specs 1621/453 |

| Targeted-ref-update | Locus | Severity |
|---------------------|-------|----------|
| `.github/workflows/ci-quality.yml` | ~L411 glob `architecture/*.md` → `docs/**` | **CRITICAL (gate-silent-death)** |
| `.kittify/glossaries/spec_kitty_core.yaml` | ~L375, ~L482 → `docs/architecture/code-patterns.md` | functional |
| `.kittify/charter/governance.yaml` | authority_paths (WP01-edited — verify only) | critical |
| `pyproject.toml`, `anti_sprawl_ratchet.py` | docstring/comment path mention | cosmetic |

## Requirement → Subtask Traceability

| Requirement | Subtasks |
|-------------|----------|
| FR-005 (rewrite ALL references via the 8 categories; drop dual-read) | T046, T047, T048, T049, T053 |
| FR-009 (CHANGELOG/glossary mapping references) | T051, T052 |

## Branch Strategy

Planning + final merge target: `docs/2165-mission-b-structural-move`. Depends on WP03 (moves) + WP06 (ADR names pinned in the occurrence map → **parallel-safe** with WP06 via `era_less_pinned`). Bulk-edit: the occurrence map governs; coordinate the `docs/**/*.md` co-tenancy with WP09/WP12 (category-disjoint, sequenced).

## Definition of Done

- [ ] `scripts/docs/bulk_ref_rewrite.py` authored + `tests/docs/test_bulk_ref_rewrite.py` proves: a `moves:` prefix IS rewritten, a `kitty-specs/` ref is **left untouched**, a `do_not_change`-category literal is left untouched, and the run is **idempotent**.
- [ ] WP01 dual-read **old branches dropped**; resolution tests still green (new path only).
- [ ] The **~1299 rewrite-target references** rewritten per the occurrence map's 8 categories; `code_symbols`/`import_paths`/`cli_commands`/`logs_telemetry` left `do_not_change`; **`kitty-specs/` (1621/453) NOT rewritten** (immutable snapshots). Confirm with `git diff --stat` that **zero `kitty-specs/` files changed**.
- [ ] **Targeted-ref-updates done**: `ci-quality.yml` glob re-pointed (CRITICAL gate-silent-death fix), glossary functional refs, CHANGELOG alias-aware refs.
- [ ] **Completeness teeth (not vacuous):** the post-sweep stale-reference grep is shown to be **non-empty before the sweep** (it would have caught the residual refs) and **empty after** — paste both counts. A grep that is empty both before and after proves nothing.
- [ ] **Redirect/back-compat in place so no reference or runtime read breaks**: no live reference (outside `kitty-specs/` + intentional historical snapshots) points at a removed `architecture/` path; the root `CHANGELOG.md` alias persists for release tooling.
- [ ] `ruff` + `mypy` clean on touched `src/`+`tests/` + `bulk_ref_rewrite.py`; terminology guard clean; repo-wide stale-reference grep clean (kitty-specs/ excluded).

## Risks & Reviewer Guidance

- **Reviewer (CRITICAL):** the `ci-quality.yml` glob re-point — confirm the markdown consistency gate still fires on `docs/**` (a silent-dead gate is the worst failure mode here).
- **Blast-radius undersizing** — the occurrence map is the floor; if the live grep finds references the map missed, that is an IC-01 gap to surface, not to silently extend.
- **Bulk overlap with WP09/WP12** — confirm WP08 did not touch `toc.yml`/`docfx.json` serialized keys (WP09) or frontmatter fields (WP12); the category partition must hold.
- **Dropping the dual-read before WP03/WP06 landed** would be a runtime break — confirm the moves are in before T046.

## Activity Log

- (populated at implement time)
- 2026-06-27T15:51:46Z – claude:opus:python-pedro:implementer – shell_pid=1667144 – Assigned agent via action command
- 2026-06-27T16:49:12Z – claude:opus:python-pedro:implementer – shell_pid=1667144 – bulk rewrite: 1054 occ/282 files via occurrence-map tool (landing-aware), stale-ref 938→57 (0 in-scope misses), kitty-specs+docs/adr 0 changed, ci-quality gate fires on docs/**, CHANGELOG alias intact, dual-read dropped, 16 tool tests; flags: code-patterns IC-01 + relative-link debt
- 2026-06-27T16:54:33Z – claude:opus:reviewer-renata:reviewer – shell_pid=1816194 – Started review via action command
- 2026-06-27T17:05:12Z – user – shell_pid=1816194 – Moved to planned
- 2026-06-27T17:06:31Z – claude:opus:python-pedro:implementer – shell_pid=1842672 – Started implementation via action command
- 2026-06-27T17:37:55Z – claude:opus:python-pedro:implementer – shell_pid=1842672 – cycle 2: era-twin resolution — 31 dead docs/adr/2.x refs rerouted to surviving 3.x (resolve on disk), teeth check find_dead_twinned_adr_links (0 dead-twinned), 27 tests, do_not_change preserved
- 2026-06-27T17:37:58Z – claude:opus:reviewer-renata:reviewer – shell_pid=1914509 – Started review via action command
- 2026-06-27T17:44:03Z – user – shell_pid=1914509 – Cycle-2 approved (override prior cycle-1 rejection artifact): era-twin resolution heals dead docs/adr/2.x refs -> surviving 3.x; all 11 rerouted 3.x targets + all real 2.x file refs verified on-disk; generalized via on-disk _adr_era_dirs (no hardcoded list); teeth find_dead_twinned_adr_links non-vacuous (RED+GREEN, excludes relative/absolute via anchored lookbehind) returns 0 on real tree; 27 tests green; ruff clean; do_not_change (kitty-specs 0, docs/adr untouched by sweep) + terminology + ci-quality docs/** glob intact; idempotent
