# Tasks: Documentation Quality Hardening Gate

**Mission**: `doc-quality-hardening-2245-01KW9AKV` | **Branch**: `design/doc-quality-hardening-2245`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

8 work packages across 4 lanes. Lane A is one lane with a serial spine (WP01→WP02); WP02 is the **terminal** gate-flip gated on every other lane. See plan.md "Post-Plan Refinements" for the binding squad/brownfield corrections (decisions D-1…D-5, exact retirement scope, ownership splits).

**Post-rebase scope change (2026-06-30):** Upstream `ccd278061` retired the byte-invariance gate. Lane C is no longer a serial spine — WP05 (link repair) and WP06 (census widen) are now independent small WPs. FR-009, FR-010, and C-001 are withdrawn; no `adr_link_migration.py` module needed. See spec.md Scope Change section.

## Lane map & dependencies

| WP | Lane | Title | Depends on | Owns (authoritative) |
|----|------|-------|-----------|----------------------|
| WP01 | A1 | Gate strengthening (line output, non-vacuity, escape-guard, `--no-exclude`) | — | `relative_link_fixer.py` + its test |
| WP02 | A2 | **Terminal** gate-flip + checker unification + dry-run | WP01, WP03, WP04, WP05, WP06, WP07, WP08 | `relative_link_fixer.py` + its test + 2 retired-checker test files |
| WP03 | B1 | Repair 5 canonical-CHANGELOG body links | — | `docs/changelog/CHANGELOG.md` |
| WP04 | B2 | CHANGELOG canonical→root sync generator | WP03 | `sync_changelog.py` + root `CHANGELOG.md` + workflow |
| WP05 | C1 | ADR link repair (Lane C) | — | dated ADR bodies (`docs/adr/1.x/2*.md`, `docs/adr/2.x/2*.md`, `docs/adr/3.x/2*.md`) |
| WP06 | C2 | ADR census widen (Lane C) | — | `test_adr_content_invariance.py` |
| WP07 | D1 | Post-move prose triage | — | `docs/adr/**/README.md` |
| WP08 | D2 | Terminology-exemption policy doc | — | `terminology-exemptions.md` + guard test |

**Parallel set**: WP01, WP03, WP05, WP06, WP07, WP08 start immediately; WP04 after WP03; **WP02 last** (after all). WP05 and WP06 are independent (different files, no transform coupling).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Add `line:int` to `Unresolvable`; count newline offset in `check_dead_body_links`; update both construction sites + `_print_report` | WP01 | | [D] |
| T002 | Non-vacuity guard (FR-004): fail if zero files or zero links scanned | WP01 | [D] |
| T003 | Port repo-escape guard (D-1): report a link whose normalized target escapes `docs/`; regression test | WP01 | [D] |
| T004 | Add `--no-exclude` CLI flag (D-3) that empties `EXCLUDE_PREFIXES` for the C-007 dry-run | WP01 | [D] |
| T005 | Reference-style/raw-HTML link-shape coverage or documented exclusion (FR-003) + narrowness test (C-006) | WP01 | [D] |
| T006 | Keep `_KNOWN_GAPS` as `(file,link)`; project gate findings to 2-tuple for the set-difference (D-2); update `TestLiveTreeGate` | WP01 | | [D] |
| T007 | Performance-regression test (NFR-001): full `docs/` scan < 5 s | WP01 | [D] |
| T008 | Actionable `(file,line,target)` failure output (NFR-003) + deliberate-breakage test asserting ≥2 offenders reported with line numbers (SC-002) | WP01 | | [D] |
| T009 | Repair the 5 canonical-CHANGELOG body links, rewriting repo-root paths to `../`-relative (F4) so they resolve from `docs/changelog/` | WP03 | | [D] |
| T010 | Verify the repaired links resolve on disk (no dangling) | WP03 | | [D] |
| T011 | Create `scripts/docs/sync_changelog.py` (`generate_root`, `--check`/`--write`, **utf-8-sig** write per D-5) | WP04 | | [D] |
| T012 | Regenerate root `CHANGELOG.md` from canonical; confirm Keep-a-Changelog-valid for `extract_changelog.py` | WP04 | | [D] |
| T013 | Red-first divergence test (SC-003): current files diverge → `--check` fails → converge | WP04 | | [D] |
| T014 | Wire `sync_changelog.py --check` step into `.github/workflows/docs-freshness.yml` | WP04 | | [D] |
| T015 | Enumerate broken ADR links: `grep -rEl '\]\([^)]*kitty-specs/' docs/adr/` + moved-dir greps; record authoritative live set | WP05 | | [D] |
| T016 | Apply docs-internal rewrites (moved-dir and depth classes); may use `relative_link_fixer.py --fix` for moved-dir | WP05 | [D] |
| T017 | Delink the `kitty-specs/` ADR links to a stable ref or remove | WP05 | [D] |
| T020 | Widen `_DATE_PREFIX`/`_adr_files_on_disk` to include the 2 non-dated ADRs (`adr-connector-auth-binding-separation.md`, `adr-github-app-installation-authority.md`) | WP06 | | [D] |
| T021 | Bump `_EXPECTED_CENSUS` 117→119; confirm `TestCensus` + `test_every_adr_has_bare_madr_status_frontmatter` green | WP06 | | [D] |
| T022 | Triage the ~27 stale-prose hits → per-file disposition table (fix / era-correct / exempt-immutable); record in WP notes | WP07 | | [D] |
| T023 | Fix `docs/adr/2.x/README.md:13-17` dropped-symlink claim + other confirmed-stale README/nav prose | WP07 | | [D] |
| T024 | Write `docs/development/terminology-exemptions.md` documenting the exemption policy (adr/, Unreleased-only changelog, plans/ subdirs) | WP08 | | [D] |
| T025 | Link the policy doc from `test_terminology_guards.py`; confirm the exemptions are intended (no scan-root change unless review finds the policy wrong) | WP08 | | [D] |
| T026 | Flip `EXCLUDE_PREFIXES` → `()` (FR-002); invert `test_gate_excludes_immutable_subtrees`; re-pin `_KNOWN_GAPS` | WP02 | | [D] |
| T027 | Retire EXACTLY the 3 named link-resolution functions; preserve the 6 named non-link tests; do NOT retire glossary/readme-governance gates (FR-005) | WP02 | | [D] |
| T028 | `tel:` semantic check: verify no `tel:` links under `docs/archive/` (or add `tel:` to `is_bare_relative` skip set) | WP02 | | [D] |
| T029 | SC-005 sentinel test: no new hand-rolled dead-link loop under `tests/docs/`, excluding the documented different-concern loops | WP02 | | [D] |
| T030 | C-007 pre-merge full-tree dry-run (`--no-exclude`) green on the integrated branch (SC-007) | WP02 | | [D] |

---

## WP01 — Gate strengthening (Lane A1)

**Goal**: Make the existing `check_dead_body_links` gate emit actionable, non-vacuous, deterministic output and gain a `--no-exclude` mode — without changing its scope yet (`EXCLUDE_PREFIXES` untouched).
**Priority**: P1 (foundation for A2). **Independent test**: `pytest tests/docs/test_relative_link_fixer.py` green; deliberate-breakage test reports `(file,line,target)`.
**Subtasks**: T001, T002, T003, T004, T005, T006, T007, T008
**Depends on**: none. **Prompt**: `tasks/WP01-gate-strengthening.md` (~320 lines)
**Risk**: 500-LOC file near complexity ceiling; `_KNOWN_GAPS` tuple-format is a correctness trap (D-2).

## WP02 — Terminal gate-flip + checker unification + dry-run (Lane A2)

**Goal**: Flip the gate to full-`docs/` scope, collapse the body-link checkers to one (retire 3, preserve 6, keep 2 different-concern gates), and self-validate the unmask.
**Priority**: P1 (terminal). **Independent test**: full-tree gate green; SC-005 sentinel green; `--no-exclude` dry-run green.
**Subtasks**: T026, T027, T028, T029, T030
**Depends on**: WP01, WP03, WP04, WP05, WP06, WP07, WP08. **Prompt**: `tasks/WP02-gate-flip-unify.md` (~300 lines)
**Risk**: gate-unmask cannot self-validate (C-007) — the dry-run is mandatory; retiring must preserve the 6 named non-link tests.

## WP03 — Repair canonical-CHANGELOG body links (Lane B1)

**Goal**: Fix the 5 broken historical-entry body links in `docs/changelog/CHANGELOG.md`.
**Priority**: P2. **Independent test**: the 5 links resolve from `docs/changelog/`.
**Subtasks**: T009, T010
**Depends on**: none. **Prompt**: `tasks/WP03-changelog-link-repair.md` (~180 lines)
**Risk**: bare repo-root paths must be rewritten `../`-relative (gate reads them file-relative — F4).

## WP04 — CHANGELOG canonical→root sync generator (Lane B2)

**Goal**: Make root `CHANGELOG.md` a generated copy of canonical; block drift.
**Priority**: P2. **Independent test**: divergence test red→green; root stays `extract_changelog.py`-readable.
**Subtasks**: T011, T012, T013, T014
**Depends on**: WP03. **Prompt**: `tasks/WP04-changelog-sync.md` (~250 lines)
**Risk**: must write `utf-8-sig` (D-5); root must stay Keep-a-Changelog-valid (C-002).

## WP05 — ADR link repair (Lane C)

**Goal**: Repair the 27 broken inline body links in dated ADR bodies — docs-internal rewrites (moved-dir and depth) and `kitty-specs/` delinks. Plain edits; no waiver, no shared transform, no new module.
**Priority**: P1. **Independent test**: grep-to-zero — both `grep -rE '\]\([^)]*kitty-specs/' docs/adr/` and `grep -rE '\]\([^)]*docs/(development|how-to|engineering_notes)/' docs/adr/` return empty.
**Subtasks**: T015, T016, T017
**Depends on**: none (independent of WP06). **Prompt**: `tasks/WP05-adr-link-migration.md`
**Risk**: live count may differ from the 27-link estimate; enumerate at execution time and trust grep-to-zero, not a fixed count.

## WP06 — ADR census widen (Lane C)

**Goal**: Bring the 2 non-dated promoted ADRs under the ADR census by widening `_DATE_PREFIX`/`_adr_files_on_disk` and bumping `_EXPECTED_CENSUS` 117→119.
**Priority**: P1. **Independent test**: `TestCensus` green at 119; `test_every_adr_has_bare_madr_status_frontmatter` green for all 119.
**Subtasks**: T020, T021
**Depends on**: none (independent of WP05 — different files, no comparator coupling). **Prompt**: `tasks/WP06-comparator-census.md`
**Risk**: widened predicate must not accidentally include README files; verify `_adr_files_on_disk` excludes READMEs after the change.

## WP07 — Post-move prose triage (Lane D1)

**Goal**: Triage the ~27 stale-`architecture/`/symlink prose hits and fix the genuinely-stale ones.
**Priority**: P3. **Independent test**: disposition table complete; no stale symlink claim in non-exempt READMEs.
**Subtasks**: T022, T023
**Depends on**: none. **Prompt**: `tasks/WP07-prose-triage.md` (~200 lines)
**Risk**: many hits are era-correct or exempt (out of scope) — #2227's ~25 historical prose mentions are intentional provenance, NOT targets.

## WP08 — Terminology-exemption policy doc (Lane D2)

**Goal**: Document the terminology-exemption policy and link it from the guard test.
**Priority**: P3. **Independent test**: policy doc exists; guard test references it; terminology suite green.
**Subtasks**: T024, T025
**Depends on**: none. **Prompt**: `tasks/WP08-terminology-policy.md` (~170 lines)
**Risk**: documentation-only — no scan-root change unless review finds the policy wrong.
