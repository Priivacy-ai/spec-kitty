---
work_package_id: WP06
title: Run the 117-unique ADR conversion → docs/adr/<era>/ (drop 47 mirrors, close flat shim)
dependencies:
- WP05
requirement_refs:
- FR-002
- FR-003
- C-002
- NFR-001
tracker_refs: []
planning_base_branch: docs/2165-mission-b-structural-move
merge_target_branch: docs/2165-mission-b-structural-move
branch_strategy: Planning artifacts for this mission were generated on docs/2165-mission-b-structural-move. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-mission-b-structural-move unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
- T035
- T036
- T037
- T038
- T039
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: docs/adr
create_intent:
- tests/docs/test_adr_content_invariance.py
execution_mode: code_change
owned_files:
- architecture/1.x/adr/**
- architecture/2.x/adr/**
- architecture/3.x/adr/**
- architecture/adrs/**
- docs/adr/**
- tests/docs/test_adr_content_invariance.py
role: implementer
tags: []
shell_pid: "1656577"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile: run `/ad-hoc-profile-load python-pedro` (or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it). State which directives apply, then proceed.

## Objective

Run the WP05 converter over the **117 unique** ADRs: convert each to `docs/adr/<era>/` with bare-`status` frontmatter, migrate the **20 era-less** flat ADRs to `docs/adr/3.x/` by their **deterministically-pinned** dated filenames, **drop the 47 byte-identical flat mirrors** as the flat shim closes, and **prove content-invariance** for all 117 (C-002, NFR-001 — a merge-blocker). This is IC-04b.

## Context

`occurrence_map.yaml` `adr_census` + `moves:` (ADR block) + `era_less_pinned` is the authority:
- `architecture/1.x/adr` → `docs/adr/1.x`, `2.x/adr` → `docs/adr/2.x`, `3.x/adr` → `docs/adr/3.x` (97 era ADRs).
- `architecture/adrs` → `docs/adr/3.x` — the **20 era-less** ADRs (the 21 **real files** in `architecture/adrs/`, minus the README), landing at the **pinned filenames** in `era_less_pinned.filenames` (20 entries).
- `using_yaml_frontmatter: 0` today — every one of the 117 **unique real** ADRs is converted.

### ⚠️ The "47 mirrors" are SYMLINKS — dereference, do NOT double-convert (71 total)

The live tree has **71 back-compat symlinks** under `architecture/`, NOT byte-identical file copies:
- **47 symlinks in `architecture/adrs/`** → each points at an era original (`../2.x/adr/…`, `../1.x/adr/…`). These are the "47 mirrors".
- **24 symlinks in `architecture/2.x/adr/`** → each points at `../../3.x/adr/…` (the #2160/#2115 back-compat shim, e.g. the dash-bullet ADR).

**Handling (critical):** the converter + move operate on **canonical real files only, deduped by `realpath`**. Every symlink is **dereferenced and the link dropped** — it carries no unique content (its target is a real ADR that IS converted), and the WP07 redirect stubs supersede the old-URL continuity the shim provided. **Never convert a symlink as a distinct ADR**: doing so would (a) create a *dangling* link (the `2.x/adr → ../../3.x/adr` relative target breaks once both dirs move under `docs/adr/`), and (b) inflate the unique census **past 117** with duplicates. The census-117 check (T037) is by **realpath-unique real files**.

The **`era_less_pinned` block decouples this WP from WP08**: because the 20 destination filenames are pinned, WP08's ADR-reference rewrites + WP07's ADR redirect-stubs consume the **final** paths without waiting for this conversion to finish (the IC-04 ∥ IC-05 parallelism).

**C-002 / NFR-001 (merge-blockers):** body-minus-header bytes byte-identical pre/post for every ADR; count of unique ADRs post-move == **117** (a count < 117 is itself a failure); the 47 mirrors are proven byte-identical to their originals *before* the drop (so "dropped" is provably "not lost").

**The reconciliation ADR self-amendment (FR-013) is OUT of this invariance scope** — it is WP15's sanctioned prose edit; scope the invariance check to *moved* ADRs.

## Requirement refs (hints for the orchestrator's map-requirements)

FR-002 (97 era + 20 era-less migrated, 47 mirrors dropped, all 117 preserved), FR-003 (frontmatter conversion via WP05's converter), C-002 (no decision-content mutation), NFR-001 (0 lost, 0 altered; the count-117 census check).

## Subtasks

### T033 — Prove each of the 71 symlinks resolves to a converted canonical ADR, THEN drop the links
Enumerate the **71 back-compat symlinks** (47 in `architecture/adrs/`, 24 in `architecture/2.x/adr/`). Assert each is a **symlink whose `realpath` resolves to an in-tree canonical ADR** that IS in the conversion set. Only on that proof, **drop the links** (and `architecture/adrs/README.md`). Record the 71-link proof so "dropped" is auditable as lossless (the target real file is preserved + converted) — NFR-001. (These are symlinks, not byte-copies: the proof is link-resolution, not byte-identity.)

### T034 — Convert + move the 97 era ADRs (real files only, realpath-deduped) → `docs/adr/<era>/`
Run the WP05 converter over the **real ADR files** in `architecture/{1.x,2.x,3.x}/adr/` → `docs/adr/{1.x,2.x,3.x}/`, **skipping the 24 symlinks in `2.x/adr/`** (dereferenced + dropped per T033 — converting them would dangle and duplicate the 3.x targets). Each real ADR gains bare-`status` frontmatter; the body is verbatim. **Converter-failure is a HARD BLOCKER:** any ADR none of the 3 parsers can parse must be surfaced immediately and halt the run — never silently skipped (a skipped ADR silently drops below 117). The `architecture/2.x/adr/` back-compat (#2160/#2115) is preserved by WP01's dual-read until WP08 drops the old branch.

### T035 — Migrate the 20 era-less ADRs → `docs/adr/3.x/` at pinned filenames
Convert the 20 era-less `architecture/adrs/` ADRs and place them at the **exact** `era_less_pinned.filenames` under `docs/adr/3.x/`. Do not re-derive filenames — the pin is the deterministic contract WP07/WP08 depend on. (The README and the 47 mirrors are NOT in this set.)

### T036 — Run content-invariance over all 117 (non-vacuous)
Run WP05's invariance check (reuse WP05's `invariant()` — do NOT fork a second comparator) over every converted ADR: body-minus-header byte-identity for all 117. **Non-vacuous proof:** the check must assert the number of ADRs it actually compared **== 117** — a check that silently ran over 0 files (e.g. a glob that matched nothing post-move) is a false-green and itself a blocker. Any byte-mismatch is a blocker. Exclude the reconciliation ADR's self-amendment scope (that is WP15).

### T037 — Census check: count == 117
Assert the post-move unique-ADR count under `docs/adr/<era>/` is exactly **117** (97 era + 20 era-less). A count < 117 is an NFR-001 failure (a lost ADR). A count > 117 means a mirror wasn't dropped or a dup leaked. Wire this as a test so it re-runs in CI.

### T038 — Close the flat shim
Confirm `architecture/adrs/` is empty/removed (shim closed) and `architecture/{1.x,2.x,3.x}/adr/` content has moved to `docs/adr/`. Append the ADR move-pairs to the representation in `occurrence_map.yaml` `moves:` (already declared) so WP07 emits redirect stubs for the old ADR URLs.

### T039 — Verify + suite green
Run the full content-invariance + census tests green. Run the terminology guard. Confirm WP01's resolution tests (ADR-default read) still resolve against `docs/adr/3.x/`.

## Surfaces & Loci (from `occurrence_map.yaml` `adr_census` + `moves:`)

| From | To | Count | Notes |
|------|----|-------|-------|
| `architecture/1.x/adr` (real) | `docs/adr/1.x` | (part of 97 era) | content-invariant + frontmatter |
| `architecture/2.x/adr` (real, non-symlink) | `docs/adr/2.x` | (part of 97 era) | 24 entries here are symlinks → dropped, not moved |
| `architecture/3.x/adr` (real) | `docs/adr/3.x` | (part of 97 era) | current authority default (#2160/#2115) |
| `architecture/adrs` (21 real, minus README) | `docs/adr/3.x` | 20 | at `era_less_pinned.filenames` |
| `architecture/2.x/adr` (24 symlinks) | — | 24 | dereferenced → **link dropped** (target is a converted 3.x ADR) |
| `architecture/adrs` (47 symlinks) | — | 47 | dereferenced → **link dropped** (target is a converted era ADR) |
| `architecture/adrs/README.md` | — | 1 | dropped, not converted |

**Census (live):** 117 **realpath-unique** ADRs = 97 era + 20 era-less. **71 back-compat symlinks** (24 in `2.x/adr/` + 47 in `adrs/`) are dereferenced + dropped, NOT counted as unique. `using_yaml_frontmatter: 0`. The 20 era-less filenames are pinned in `occurrence_map.yaml` `adr_census.era_less_pinned.filenames` (use verbatim).

## Requirement → Subtask Traceability

| Requirement | Subtasks |
|-------------|----------|
| FR-002 (97 era + 20 era-less; 47 mirrors dropped; all 117 preserved) | T033, T034, T035, T037, T038 |
| FR-003 (frontmatter conversion via WP05's converter) | T034, T035 |
| C-002 (no decision-content mutation) | T036 |
| NFR-001 (0 lost — census == 117; 0 altered) | T033, T036, T037 |

## Branch Strategy

Planning + final merge target: `docs/2165-mission-b-structural-move`. Depends on WP05 (the converter) and WP03 (the move landed the era trees under `docs/`). **Parallel-safe with WP08** via the `era_less_pinned` filenames.

## Definition of Done

- [ ] All **117 realpath-unique** ADRs present under `docs/adr/<era>/` with bare-`status` frontmatter; **census check asserts count == 117** (NFR-001) — count via realpath-unique real files, symlinks excluded.
- [ ] The **71 back-compat symlinks** (24 in `2.x/adr/` + 47 in `adrs/`) each proven to resolve to a converted canonical ADR, then the **links dropped** (with the flat README); drop is auditable as lossless. **No dangling symlink remains** anywhere under `docs/adr/` (verify: `find docs/adr -xtype l` is empty).
- [ ] The 20 era-less ADRs land at the **pinned `era_less_pinned.filenames`** under `docs/adr/3.x/`.
- [ ] **No ADR silently skipped:** any parser-failure halted the run (hard blocker); the count-117 census + the invariance "compared == 117" assertion together prove nothing was dropped or skipped.
- [ ] **Content-invariance passes for all 117, non-vacuously** (reuses WP05's `invariant()`; asserts it compared exactly 117 files) — C-002 / NFR-001 merge-blockers satisfied; the reconciliation-ADR self-amendment is excluded (WP15 scope).
- [ ] **Redirect/back-compat in place so no reference/URL breaks**: ADR move-pairs represented in `occurrence_map.yaml` `moves:` (WP07 stubs the old ADR URLs); WP01 dual-read keeps old ADR references resolving until WP08.
- [ ] Flat shim closed (`architecture/adrs/` removed); terminology guard clean.

## Risks & Reviewer Guidance

- **Reviewer (merge-blocker focus):** confirm the census count is exactly 117 and the invariance check is the real byte-comparison (not a re-render) — these two are the NFR-001/C-002 gates.
- **Dropping a mirror that is NOT byte-identical** would lose content — T033's per-file proof is mandatory before any drop.
- **Filename drift on the 20 era-less ADRs** breaks WP07/WP08's pinned-path assumption — use `era_less_pinned.filenames` verbatim.

## Activity Log

- (populated at implement time)
- 2026-06-27T14:35:24Z – claude:opus:python-pedro:implementer – shell_pid=1517523 – Assigned agent via action command
- 2026-06-27T14:56:21Z – user – shell_pid=1517523 – Moved to planned
- 2026-06-27T15:21:08Z – claude:opus:python-pedro:implementer – shell_pid=1603906 – Started implementation via action command
- 2026-06-27T15:33:29Z – claude:opus:python-pedro:implementer – shell_pid=1603906 – 117 ADRs converted via extended WP05 converter (0 hard-errors; Accepted 93/Proposed 13/Superseded 11), 71 symlinks dereferenced (no dangling), invariance compared==117 raw-byte, flat shim closed, census==117
- 2026-06-27T15:33:43Z – claude:opus:reviewer-renata:reviewer – shell_pid=1629367 – Started review via action command
- 2026-06-27T15:40:17Z – user – shell_pid=1629367 – Moved to planned
- 2026-06-27T15:41:31Z – claude:opus:python-pedro:implementer – shell_pid=1647095 – Started implementation via action command
- 2026-06-27T15:46:59Z – claude:opus:python-pedro:implementer – shell_pid=1647095 – cycle 3: exempt docs/adr/ from terminology guard (historical ADRs immutable, mirrors kitty-specs/) + narrowness regression test; guard green, invariance/census/resolution intact
- 2026-06-27T15:47:01Z – claude:opus:reviewer-renata:reviewer – shell_pid=1656577 – Started review via action command
- 2026-06-27T15:50:44Z – user – shell_pid=1656577 – Cycle-3 approved (reviewer-renata): resolves the sole cycle-2 blocker (terminology guard RED). docs/adr/ added to _EXCLUDED_PATH_FRAGMENTS mirroring kitty-specs/ historical-artifact precedent with NFR-001/C-002 rationale comment; narrow regression test test_docs_adr_exemption_is_narrow proves docs/adr/ exempt while docs/guides|architecture|top-level still scanned (verified it FAILS under a blanket docs/ exemption). Guard GREEN (3 passed, was RED). Fidelity intact: census 117 realpath-unique, content-invariance + census suite 4 passed, no dangling symlinks, ruff/mypy clean. Only out-of-map touch is the guard test (justified leeway, documented in commit + comment).
