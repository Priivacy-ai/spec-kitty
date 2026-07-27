# Implementation Plan: Documentation Quality Hardening Gate

**Branch**: `design/doc-quality-hardening-2245` | **Date**: 2026-06-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/doc-quality-hardening-2245-01KW9AKV/spec.md`

## Summary

Close the documentation-quality debt from the Common Docs move (#2245) and leave **one authoritative, blocking inline-body-link gate**. The gate engine already exists and blocks (`check_dead_body_links` in `scripts/docs/relative_link_fixer.py`, wired at `docs-freshness.yml:34-37` + `TestLiveTreeGate`); the work is (A1) strengthening it with `(file,line,target)` output + non-vacuity, (B) repairing + auto-syncing the two CHANGELOGs, (C) a C-002-waived ADR body-link migration with a comparator change + born-in-`docs/` census, (D) prose triage + terminology-policy doc, and (A2, terminal) widening `EXCLUDE_PREFIXES`, retiring three hidden hand-rolled checkers, and a pre-merge full-tree dry-run. Approach validated by a 4-lens adversarial squad that corrected the sizing (gate smaller than implied; unification + Lane C larger and coupled).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest (+ markers `fast`/`architectural`/`git_repo`/`contract`), `ruamel.yaml`/frontmatter split, existing `scripts/docs/` modules (`relative_link_fixer`, `adr_converter`, `redirect_stub_generator`), GitHub Actions (`docs-freshness.yml`, `ci-quality.yml`), `git` (blob recovery for the byte-invariance comparator)
**Storage**: Filesystem (`docs/` tree); git object store (merge-base + introduction-commit blobs as the invariance source) — no database
**Testing**: pytest, red-first; deliberate-breakage tests for the gate; divergence test for CHANGELOG sync; full-tree dry-run (`EXCLUDE_PREFIXES=()`) as the gate-unmask self-validation (C-007); marker discipline so each gate lands in the correct CI shard
**Target Platform**: CI (Linux runners) + local developer checkout
**Project Type**: single (Python CLI/tooling + test suite + CI workflows + docs)
**Performance Goals**: gate completes < 5 s over the full `docs/` tree (current `--check` ≈ 0.10 s)
**Constraints**: ~~preserve C-002 ADR byte-invariance except the sanctioned FR-008 waiver~~ (byte-invariance retired by ccd278061 — see Scope Change); **no new link-checker module** (C-003 — extend `check_dead_body_links`, do not build a parallel gate or `Resolver`-backed checker); zero `ruff`/`mypy` issues on new code; gate-unmask cannot self-validate → full-tree dry-run in acceptance (C-007); gate resolver stays `docs/`-scoped (kitty-specs links are delinked, not validated)
**Scale/Scope**: ~119 promoted ADRs; several hundred `docs/` files; 27 broken ADR-body links (12 files) + 5 broken canonical-CHANGELOG links to repair; 3 hidden parallel checkers to retire; ~8 WPs; Lane C is now two independent WPs (link repair + census bump), not a serial spine

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present (`.kittify/charter/charter.md`, compact mode). Applicable directives:

- **DIR-012** (tracker issue assigned to HiC before implementation): #2245 is assigned to stijn-dejongh ✓.
- **DIR-013** (pre-existing test failures must be filed as an issue before being treated as baseline): carried into implementation as a standing rule for all lanes.
- **DIR-010 / DIR-011** (ASCII slug sanitization + regression coverage): **N/A** — this mission adds no identifier/slug normalization.

No charter violations. The mission uses canonical surfaces only (C-003), adds no agent directories (C-005), and is not expected to touch `src/specify_cli/__init__.py` (no version bump). **Gate: PASS.** (Complexity Tracking left empty.)

## Project Structure

### Documentation (this mission)

```
kitty-specs/doc-quality-hardening-2245-01KW9AKV/
├── plan.md              # This file
├── research.md          # Phase 0 — resolves the 3 open architecture decisions
├── data-model.md        # Phase 1 — Unresolvable.line, EXCLUDE_PREFIXES, comparator, sync
├── quickstart.md        # Phase 1 — how to run the gate / dry-run / sync / invariance locally
├── contracts/           # Phase 1 — function/CLI contracts (gate, changelog-sync, adr-invariance)
└── tasks.md             # Phase 2 — /spec-kitty.tasks (NOT created here)
```

### Source Code (repository root)

```
scripts/docs/
├── relative_link_fixer.py        # IC-01/IC-05: check_dead_body_links (THE gate), Unresolvable, EXCLUDE_PREFIXES
└── sync_changelog.py             # IC-02 (NEW): canonical→root CHANGELOG generator
# adr_converter.py — read-only; no new module for ADR transforms (byte-invariance retired)

tests/docs/
├── test_relative_link_fixer.py            # IC-01/IC-05: TestLiveTreeGate, test_gate_excludes_immutable_subtrees (inverted)
├── test_adr_content_invariance.py         # IC-03 (WP06): TestCensus only — census widen 117→119 (_DATE_PREFIX + _EXPECTED_CENSUS)
├── test_architecture_docs_consistency.py  # IC-05: retire link-resolution fn (keep non-link assertions)
└── test_versioned_docs_integrity.py       # IC-05: retire link-resolution fn (keep non-link assertions)

tests/contract/test_terminology_guards.py  # IC-04: exemption policy (owned by Lane D)

docs/
├── adr/**                        # IC-03: 27 link migrations/delinks; IC-04: 2.x/README.md prose
├── changelog/CHANGELOG.md        # IC-02: canonical source (link fixes)
└── development/terminology-exemptions.md  # IC-04 (NEW): the documented policy

CHANGELOG.md                       # IC-02: generated root copy (release-tooling consumer)
.github/workflows/docs-freshness.yml  # IC-05: widen the gate step scope
```

**Structure Decision**: Single-project Python tooling. All edits land in `scripts/docs/`, `tests/docs/`, `tests/contract/`, `.github/workflows/`, and `docs/`. No `src/specify_cli/` changes ⇒ no version bump.

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are architectural areas, not work packages. `/spec-kitty.tasks` will translate these into executable WPs (Lane C and IC-05 will each fan out into several). The lane letters map to the spec's Sequencing section.
>
> **CRITICAL lane-modeling note (squad F1):** IC-01 and IC-05 both edit `relative_link_fixer.py` + `test_relative_link_fixer.py`, so they are **ONE lane "Lane A" with an internal serial order A1→A2** — NOT two parallel lanes (two parallel lanes co-owning those files would be rejected by the allocator). "A1 runs alongside B/C/D" means Lane-A-as-a-whole; A2 is its gated terminal WP. See the Post-Plan Refinements section below for the full set of squad/brownfield corrections that `/spec-kitty.tasks` MUST honor.

### IC-01 — Gate strengthening (Lane A1)

- **Purpose**: Make the existing gate emit actionable, deterministic, non-vacuous output without changing its scope yet.
- **Relevant requirements**: FR-001, FR-003, FR-004, NFR-002, NFR-003.
- **Affected surfaces**: `scripts/docs/relative_link_fixer.py` (`Unresolvable` gains `line: int`; `check_dead_body_links` counts newline position; non-vacuity guard; reference-style/raw-HTML link-shape handling or documented exclusion), `tests/docs/test_relative_link_fixer.py` (assertions for line numbers + non-vacuity).
- **Sequencing/depends-on**: none (fully parallel; `EXCLUDE_PREFIXES` untouched here).
- **Risks**: data-model change ripples to every `Unresolvable` consumer + existing `TestLiveTreeGate` assertions; line-counting must be correct for multi-link lines.

### IC-02 — CHANGELOG repair + one-direction sync (Lane B)

- **Purpose**: Fix the 5 broken canonical-CHANGELOG links and make root a generated copy so the two files cannot drift.
- **Relevant requirements**: FR-006, FR-007, C-002.
- **Affected surfaces**: `docs/changelog/CHANGELOG.md` (canonical source — link fixes), `CHANGELOG.md` (generated root), a new `scripts/docs/sync_changelog.py` generator + a divergence/assertion test. Must keep root readable by `scripts/release/extract_changelog.py` (root, `utf-8-sig`).
- **Sequencing/depends-on**: none (owns both CHANGELOG files exclusively).
- **Risks**: files already diverge two ways (canonical frontmatter + a stale body line); "shared region" must be defined precisely (body-after-frontmatter, normalized).

### IC-03 — ADR link repair + census widen (Lane C, two independent WPs)

*Post-rebase (ccd278061): byte-invariance gate retired upstream; the serial spine and comparator/transform/waiver work are moot. Lane C is now two small independent WPs.*

- **Purpose**: Repair the 27 broken ADR-body links (plain edits, no waiver), and bring the 2 non-dated ADRs under the census count.
- **Relevant requirements**: FR-008, FR-011 (no longer FR-009, FR-010, or C-001).
- **Affected surfaces**: WP05 = dated ADR bodies under `docs/adr/1.x/`, `docs/adr/2.x/`, `docs/adr/3.x/` (docs-internal rewrites and `kitty-specs/` delinks); WP06 = `tests/docs/test_adr_content_invariance.py` (`_DATE_PREFIX`/`_adr_files_on_disk` widen + `_EXPECTED_CENSUS` 117→119). No comparator, no `adr_link_migration.py` module, no reconciliation-ADR amendment.
- **Sequencing/depends-on**: WP05 and WP06 are independent — they own disjoint files (ADR bodies vs. the test). Both must complete before A2 (WP02).
- **Risks**: The 27-link count is a planning estimate; enumerate the authoritative live set via grep at execution time (grep-to-zero is the DoD, not a fixed count). Census widen: `_DATE_PREFIX` regex must be widened so both `adr-*.md` files pass `_adr_files_on_disk`; verify `test_every_adr_has_bare_madr_status_frontmatter` stays green for the two new files.

### IC-04 — Prose triage + terminology policy (Lane D)

- **Purpose**: Correct stale post-move prose and document the terminology-exemption policy as intended.
- **Relevant requirements**: FR-012, FR-013, C-004.
- **Affected surfaces**: ~27 prose-hit files (per-file disposition: fix / era-correct / exempt-immutable), confirmed `docs/adr/2.x/README.md:13-17` (a README — outside the census filter, safe to edit), a new `docs/development/terminology-exemptions.md`, and `tests/contract/test_terminology_guards.py` (doc-link comment only; Lane D owns any edit here).
- **Sequencing/depends-on**: none; Lane A's FR-003 consumes the exemption pattern read-only.
- **Risks**: many hits are legitimately era-correct or exempt-immutable — triage needs a disposition rule, not a blanket rewrite.

### IC-05 — Gate-flip + checker unification + gate-unmask dry-run (Lane A2, terminal)

- **Purpose**: Flip the gate to full-`docs/` scope, collapse the four overlapping body-link checkers to one, and self-validate the unmask before merge.
- **Relevant requirements**: FR-002, FR-005, C-007.
- **Affected surfaces**: `scripts/docs/relative_link_fixer.py` (`EXCLUDE_PREFIXES` → `()`), `tests/docs/test_relative_link_fixer.py` (invert `test_gate_excludes_immutable_subtrees`, re-pin `_KNOWN_GAPS`), retire the link-resolution functions in `test_architecture_docs_consistency.py` + `test_versioned_docs_integrity.py` (+ the `user_journey` persona-link test), `.github/workflows/docs-freshness.yml` (widen step scope), and the C-007 full-tree dry-run in acceptance.
- **Sequencing/depends-on**: **IC-02, IC-03, IC-04** (B/C link fixes must land first or the widened gate reds; the IC-04 edge is shared-`docs/adr/`-scope — A2 widens the gate over the ADR READMEs Lane D writes last); consumes IC-01's strengthened gate.
- **Risks**: the gate-unmask cannot validate itself within its own PR (C-007) — the pre-merge full-tree dry-run is mandatory; retiring the hidden checkers must preserve their non-link assertions.

## Post-Plan Refinements (squad + brownfield — `/spec-kitty.tasks` MUST honor)

A 2-lens IC-map squad (architect-alphonso, paula-patterns) + a planner-priti brownfield check produced these corrections. They are binding inputs to task decomposition.

### Lane / ownership corrections

- **R-F1 (CRITICAL):** Lane A = ONE lane, internal serial **A1 (IC-01) → A2 (IC-05)** — same files (`relative_link_fixer.py`, `test_relative_link_fixer.py`). Never two parallel lanes. A2 also depends on B+C+D.
- **R-F3:** Lane C and Lane D both write under `docs/adr/` but are **disjoint by filename pattern** — C owns dated `docs/adr/**/YYYY-MM-DD-*.md`; D owns `docs/adr/**/README.md`. WP `owned_files` must encode this split precisely (not a directory-level `docs/adr/` claim) or the allocator sees an overlap. (The reconciliation-ADR amendment is moot post-rebase — FR-009 withdrawn.)
- **LOC guard:** `relative_link_fixer.py` is 500 LOC (near the complexity ceiling). Do NOT let one WP own both the `Unresolvable.line` change and the `EXCLUDE_PREFIXES` flip. ~~In Lane C do NOT land the comparator change (FR-010) and the born-in-`docs/` census (FR-011) in the same commit~~ — **OBSOLETE post-rebase (ccd278061 retired byte-invariance)**: FR-010 comparator/WP05↔WP06 transform-coupling guard no longer apply; WP05 and WP06 are independent with no shared transform.
- **`_EXPECTED_INVARIANT` is DERIVED, never tuned** — ~~compute it as `census − len(sanctioned_self_amendment_set)` with a guard test~~. **OBSOLETE post-rebase (ccd278061 retired byte-invariance)**: `_EXPECTED_INVARIANT` and `_SANCTIONED_SELF_AMENDMENT` no longer exist in the test file.

### Concrete decisions (made now; record in WPs)

- **D-1 (escape-guard, alphonso F5):** Porting wins over silent loss. `check_dead_body_links` must **report a link whose normalized target escapes `docs/`** (the retired checkers' `relative_to` guard). Add a regression test. This preserves a load-bearing invariant ("unify, don't drop").
- **D-2 (`_KNOWN_GAPS` trap, paula):** Keep `_KNOWN_GAPS` as `frozenset[tuple[str, str]]` keyed on `(file, link)`; project the gate's findings to `(file, link)` for the `dead - _KNOWN_GAPS` set-difference. `line` is **display-only** (NFR-003 output), never a gap key. Write this into IC-01's DoD; it is a correctness trap otherwise.
- **D-3 (SC-007 dry-run mechanism):** Add a `--no-exclude` (empty-`EXCLUDE_PREFIXES`) CLI flag to `relative_link_fixer.py` in **A1 (IC-01)**. The C-007 pre-merge full-tree dry-run runs `relative_link_fixer.py --check --no-exclude`; a `fast` test also uses it. No more "(or test)" ambiguity.
- **D-4 (`migrate_adr_body_links` home):** ~~New pure-stdlib module `scripts/docs/adr_link_migration.py`~~. **OBSOLETE post-rebase (ccd278061 retired byte-invariance)**: no shared transform module is needed; WP05 applies link repairs directly (or via `relative_link_fixer.py --fix` for the moved-dir class).
- **D-5 (`sync_changelog.py`):** Pure-stdlib; writes root `CHANGELOG.md` as **`utf-8-sig`** (matches `extract_changelog.py:76` `read_text(encoding="utf-8-sig")`). IC-02 also wires its `--check` step into `.github/workflows/docs-freshness.yml` (add to IC-02 affected surfaces).

### IC-05 retirement scope — EXACTLY three functions

Retire only: `test_architecture_relative_links_resolve` + `test_user_journey_persona_links_resolve` (`test_architecture_docs_consistency.py`), `test_versioned_docs_relative_links_resolve` (`test_versioned_docs_integrity.py`).
- **Preserve by name** (delete only the link functions, keep the modules): `test_architecture_required_paths_exist`, `test_architecture_adr_directories_are_not_empty`, `test_adr_filename_follows_naming_convention`, `test_adr_contains_required_sections`, `test_versioned_docs_required_files_exist`, `test_versioned_docs_exclude_out_of_scope_terms`.
- **Do NOT retire** (deliberate co-existing, different-concern gates): `tests/doctrine/test_glossary_link_integrity.py` (anchor-fragment validation the gate lacks — file a follow-up to maybe extend the gate with anchor checks), `tests/specify_cli/docs/test_readme_governance.py` (non-`docs/` agent-skills file).
- **`tel:` semantic gap:** the retired versioned checker skips `tel:` links; `is_bare_relative` does not. Before flipping, verify no `tel:` links exist under `docs/archive/`, or add `tel:` to the skip set.

### Orphan requirements — assign IC homes

- **NFR-001 (<5 s):** owned by **IC-01** — add a minimal performance-regression test (generous threshold).
- **C-006 (narrowness tested):** owned by **IC-01** — a deliberate too-broad exemption must fail a test (mirror `test_docs_adr_exemption_is_narrow`).
- **NFR-004 (ruff/mypy + same-PR tests):** applies to every IC; call it out explicitly in IC-01 (data-model change). ~~IC-03 new module~~ — **OBSOLETE post-rebase**: no new `adr_link_migration.py` module.

### Marker/shard discipline (brownfield 3d)

`test_relative_link_fixer.py` → `fast`; ~~new `adr_link_migration` unit tests → `fast`~~ (**OBSOLETE post-rebase**); `test_adr_content_invariance.py` stays `architectural + git_repo` (census-only tests); `sync_changelog` test → `fast` (use `tmp_path`); `test_terminology_guards.py` → `contract + fast`.

### Issue-matrix (all REFERENCE — none fold)

| Issue | Disposition | Why |
|---|---|---|
| #2227 (Mission B residuals: ~25 historical `architecture/<era>` prose + HELP-DRIFT) | `reference` (`in-mission: no`) | The ~25 prose mentions are intentional provenance, NOT stale errors — **out of scope for IC-04 triage**. HELP-DRIFT is CLI-reference freshness. |
| #2215 (distil era-suffixed READMEs into living-design pages) | `reference` | Content decision; mission doesn't touch `docs/architecture/README*.md`. |
| #584 (doc-code consistency audit, 28 items) | `reference` | Doc-code semantic drift, not dead body links. |
| #1644 (stale `.codex/` path guidance) | `reference` | Stale prose, not dead links; IC-04 may pick up opportunistically only where it co-occurs with a dead link. |

### Pre-implement note

Coord branch `kitty/mission-doc-quality-hardening-2245-01KW9AKV` is currently behind `design/...` (plan artifacts are on the design branch). Normal `tasks` + `implement` flow synchronizes them — expected, no action.
