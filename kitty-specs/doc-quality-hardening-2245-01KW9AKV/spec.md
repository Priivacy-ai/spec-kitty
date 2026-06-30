# Specification: Documentation Quality Hardening Gate

**Mission slug**: `doc-quality-hardening-2245-01KW9AKV`
**Mission type**: software-dev
**Status**: Draft (post-squad revision)
**Closes**: [#2245](https://github.com/Priivacy-ai/spec-kitty/issues/2245) (sub-issue of [#2165](https://github.com/Priivacy-ai/spec-kitty/issues/2165) / [#651](https://github.com/Priivacy-ai/spec-kitty/issues/651))
**Refs**: PR #2225 (Common Docs structural move, Mission B)

## Scope Change (2026-06-30, post-rebase)

Upstream commit `ccd278061` (3.2.4 cycle) retired the byte-identity ADR invariance gate. The surviving `tests/docs/test_adr_content_invariance.py` (101 lines) now has only `TestCensus` — `_EXPECTED_CENSUS=117`, `_DATE_PREFIX` filter (excludes non-dated ADRs), `_adr_files_on_disk()`, `test_no_dangling_back_compat_symlinks`, and `test_every_adr_has_bare_madr_status_frontmatter`. There is no byte-invariance comparator, no `_EXPECTED_INVARIANT`, and no `_SANCTIONED_SELF_AMENDMENT` anymore.

Consequences:

- **The two former Lane-C requirements numbered 009 and 010 are WITHDRAWN as moot** (their table rows are removed; the numbers are retired, not reused). No comparator exists to update; no reconciliation-ADR amendment is needed; no C-002 waiver process applies.
- **FR-008 simplifies** to a plain link repair (no C-002 waiver needed — the byte-invariance gate no longer exists). See the rewritten FR-008 below.
- **FR-011 simplifies** to a census widen only (bring the 2 non-dated ADRs into `_adr_files_on_disk` + bump `_EXPECTED_CENSUS` 117→119; no invariance model to extend).
- **C-001 is WITHDRAWN** (it guarded C-002 byte-invariance, which is gone).
- **Lane C is no longer a serial spine.** WP05 (link repair) and WP06 (census widen) are now independent small WPs — they touch different files (WP05: ADR bodies; WP06: the test file). Both must still complete before the terminal WP02.

## Purpose

The Common Docs structural move (#2165, PR #2225) relocated hundreds of documentation files. The adversarial doc-alignment review of that move, plus its CI remediation, surfaced documentation-quality debt that did **not** block the merge (CI was green) but is real: inline body links that silently dangle inside the two trees the existing gate excludes, residual broken links left by the move, a manually-maintained changelog mirror, a census blind-spot, and stale post-move prose. This mission closes that debt and leaves **one authoritative, blocking gate** so broken in-doc links can no longer ship green.

## Background: the real state of doc-link gating today (post-reconnaissance)

A four-lens adversarial squad verified the following against the live code. This corrects the imprecise premise in #2245 ("no gate validates inline body links") and is load-bearing for sizing:

1. **The gate already exists and already blocks.** `scripts/docs/relative_link_fixer.py::check_dead_body_links` (≈line 423) is a pure on-disk body-link resolver (no `occurrence_map.yaml` / `Resolver` dependency). It is wired blocking in CI at `.github/workflows/docs-freshness.yml:34-37` (`relative_link_fixer.py --check`, exit 1 on any dead link) **and** runs in the fast shard via `tests/docs/test_relative_link_fixer.py::TestLiveTreeGate` (`pytestmark = pytest.mark.fast`, `_KNOWN_GAPS = frozenset()`). So FR-001 ("create/promote the gate") is **already done** — the lever is FR-002.
2. **It excludes exactly two trees.** `EXCLUDE_PREFIXES = ("docs/adr/", "docs/changelog/")` (`relative_link_fixer.py:93-96`). Those two trees carry the broken links #2245 names: a verified **27** dead links across 12 ADR files and **5** in `docs/changelog/CHANGELOG.md`.
3. **The "unify" claim is falsified by hidden parallel checkers.** Three *other* hand-rolled body-link resolvers already run blocking in CI, none named by #2245, with duplicate logic and overlapping scope: `tests/docs/test_architecture_docs_consistency.py::test_architecture_relative_links_resolve` (covers `docs/architecture/**` + `docs/adr/1.x` + `docs/adr/2.x`), `::test_user_journey_persona_links_resolve` (`docs/plans/user_journey/`), and `tests/docs/test_versioned_docs_integrity.py::test_versioned_docs_relative_links_resolve` (`docs/archive/**`, `docs/index.md`). A real unification must **retire these and route their scope through the one gate** — otherwise the mission ships four overlapping checkers.

**Consequence:** the gate engine is *smaller* than the spec first implied (toggle an exclusion, not build a checker), while the *true unification* and the *ADR-body migration* are *larger* and *coupled*. The gate cannot go green on `docs/adr/`+`docs/changelog/` until their links are fixed — so the exclusion-flip is the **terminal, serialized** step (see Sequencing).

## User Scenarios & Testing

### Primary scenario (happy path → enforced)
A contributor (human or AI agent) relocates/renames a doc or writes an inline link `[text](../path.md)`. On their PR, the single authoritative body-link gate resolves every inline body link under `docs/` against the on-disk tree. If any target does not exist, **CI fails** and the failure message enumerates every offending `(file, line, link target)`. Today this passes silently for `docs/adr/` and `docs/changelog/`.

### Exception A — changelog drift
A contributor updates one of the two CHANGELOG files but not the other. The new sync gate fails, naming the divergence, instead of letting them drift (they already diverge today in two ways — see FR-007).

### Exception B — census blind-spot
A promoted ADR is added without a `YYYY-MM-DD-` prefix. After this mission it is counted in the ADR census (FR-011), rather than silently escaping it.

## Domain Language

| Canonical term | Meaning | Avoid |
|---|---|---|
| **inline body link** | A Markdown link `[text](target)` in a doc body (not frontmatter `related:`). | "reference" (ambiguous with `related:`) |
| **the gate** | The single authoritative blocking body-link gate: `check_dead_body_links` in `relative_link_fixer.py`. | "link fixer" (the `--fix` remediation mode), "a new gate" (there is no new module) |
| **ADR census** | The exact count + enumeration of ADRs under `docs/adr/<era>/` tracked by `TestCensus`. | — |
| **byte-invariance comparator (C-002)** | ~~OBSOLETE (post-rebase ccd278061)~~ — retired upstream in 3.2.4. No longer exists in `test_adr_content_invariance.py`. | — |
| **born-in-`docs/` ADR** | ~~OBSOLETE (post-rebase ccd278061)~~ — term only applied to the retired invariance model. The 2 non-dated ADRs are simply brought into the census (FR-011). | — |
| **canonical / root CHANGELOG** | `docs/changelog/CHANGELOG.md` (canonical source) vs `CHANGELOG.md` (generated release-tooling copy, read by `extract_changelog.py`). | — |

## Requirements

### Functional Requirements

| ID | Requirement | Lane | Status |
|---|---|---|---|
| FR-001 | Confirm and document that `check_dead_body_links` (in `relative_link_fixer.py`, wired blocking at `docs-freshness.yml:34-37` and `TestLiveTreeGate`) is the single authoritative body-link gate. No new gate module is created (C-003). | A1 | Draft |
| FR-002 | Remove `docs/adr/` and `docs/changelog/` from `EXCLUDE_PREFIXES` so the gate covers the full `docs/` tree. This is the **terminal** gate-flip step, gated on FR-006 + FR-008 landing (their links resolved). The gate resolver remains `docs/`-scoped (repo-root-relative resolution of in-`docs/` targets); links pointing outside `docs/` are removed by FR-008's delink, not validated by widening the resolver. | A2 | Draft |
| FR-003 | The gate skips only legitimately-non-resolvable link shapes (`http(s)`, `mailto:`, `#anchor`, absolute `/…`, reference-style, raw HTML) and a **narrow, individually-justified** path exemption list. Current `is_bare_relative`/`_LINK` (≈lines 105, 157-166) do not parse reference-style/raw-HTML links — extend coverage or document them as out-of-scope shapes. | A1 | Draft |
| FR-004 | The gate is **non-vacuous**: it asserts the live tree contains doc pages and resolvable links to scan; an empty or zero-link scan is a failure. | A1 | Draft |
| FR-005 | **Unify the body-link checking surface to ONE gate.** Retire **exactly** the three hidden hand-rolled dead-link resolvers (`test_architecture_relative_links_resolve`, `test_user_journey_persona_links_resolve`, `test_versioned_docs_relative_links_resolve`) and route their scopes (`docs/architecture/**`, `docs/plans/user_journey/`, `docs/archive/**`) through `check_dead_body_links`. **Preserve the non-link assertions** in those modules (named in plan IC-05). **Port the repo-escape guard**: the retired checkers reject links escaping outside the repo/`docs/`; the gate must not silently lose this — report a link whose normalized target escapes `docs/` (a regression test pins the behavior). **Do NOT retire** the richer `test_glossary_link_integrity.py` (anchor-fragment validation the gate lacks) or `test_readme_governance.py` (non-`docs/` agent-skills file); log them as deliberate co-existing, different-concern gates. Net: exactly one `docs/`-body **dead-link** resolver in CI. | A2 | Draft |
| FR-006 | Repair the 5 broken historical-entry inline body links in the **canonical** `docs/changelog/CHANGELOG.md` (verified set: `docs/development/local-overrides.md`, `docs/migration/shared-package-boundary-cutover.md`, `architecture/2.x/adr/2026-04-25-1-shared-package-boundary.md`, `docs/architecture/05_ownership_map.md`, `docs/upgrading-to-0-11-0.md`). | B | Draft |
| FR-007 | Automate canonical↔root CHANGELOG sync with a **single direction**: canonical `docs/changelog/CHANGELOG.md` is the source; root `CHANGELOG.md` is the generated release-tooling copy. Define the shared region precisely (body after the canonical's YAML frontmatter; the files diverge today by that frontmatter **and** a stale `architecture/2.x/05_ownership_map.md` body line). Root must remain a valid Keep-a-Changelog file readable by `scripts/release/extract_changelog.py` (reads `CHANGELOG.md` at repo root, `utf-8-sig`). Ship a red-first divergence test that the current files fail, then converge. | B | Draft |
| FR-008 | Repair the 27 broken inline body links in ADR bodies under `docs/adr/` — 15 docs-internal rewrites (moved-dir: `docs/development/→docs/guides/`, `docs/how-to/→docs/guides/`, `docs/engineering_notes/→docs/plans/engineering-notes/`; plus nested-`adr/`/cross-era depth fixes) and the 12 `kitty-specs/` links delinked to a stable ref (merged-PR/commit URL or superseding doc) or removed. Plain edit — no waiver needed (byte-invariance gate was retired upstream by `ccd278061`). Acceptance is grep-to-zero: both `grep -rE '\]\([^)]*kitty-specs/' docs/adr/` and `grep -rE '\]\([^)]*docs/(development\|how-to\|engineering_notes)/' docs/adr/` must return empty. | C | Draft |
| FR-011 | Bring the 2 non-dated promoted ADRs (`docs/adr/3.x/adr-connector-auth-binding-separation.md`, `adr-github-app-installation-authority.md`) under the census: widen `_DATE_PREFIX`/`_adr_files_on_disk` to include them and bump `_EXPECTED_CENSUS` 117→119. They already satisfy `test_every_adr_has_bare_madr_status_frontmatter`. No invariance model. | C | Draft |
| FR-012 | Triage the ~27 files matching stale post-move `architecture/`/symlink prose; give each a disposition (fix stale claim / leave era-correct / leave exempt-immutable), and correct the stale ones (confirmed: `docs/adr/2.x/README.md:13-17` dropped-symlink claim — README files are outside the `_DATE_PREFIX` census filter and are plain edits with no byte-invariance concern). | D | Draft |
| FR-013 | Confirm and **document** (no scan-root change unless review finds the policy wrong) the terminology-exemption policy for the relocated tree (`docs/adr/`, the Unreleased-only `docs/changelog/CHANGELOG.md` scan, `docs/plans/{engineering-notes,initiatives,notes}/` — all already coded in `test_terminology_guards.py:63-152`). Write the policy to a named file (e.g. `docs/development/terminology-exemptions.md`) and link it from the guard test's comment. Lane D owns any edit to `test_terminology_guards.py`; Lane A's FR-003 exemption pattern consumes it read-only. | D | Draft |

### Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | The gate must not materially slow CI. | Completes in < 5 s over the full `docs/` tree (current `--check` ≈0.10 s; keep margin if scope widens). | Draft |
| NFR-002 | Gate output is deterministic and order-stable. | Identical broken-link list (same order) across repeated runs and machines. | Draft |
| NFR-003 | Gate failure output is actionable: it enumerates **every** offending link as `(file, line, target)`. Requires a data-model change: the `Unresolvable` dataclass (`relative_link_fixer.py:338-340`) has only `(file, link)` and no line number — add a `line: int` field and newline-position counting in `check_dead_body_links`, and update `TestLiveTreeGate` assertions to match. | On failure the message lists 100% of dangling links as `(file, line, target)`; verified by a deliberate-breakage test asserting ≥2 distinct offenders are all reported with correct line numbers. | Draft |
| NFR-004 | New code is clean and covered. | `ruff` + `mypy` zero issues on new/changed code; every new branch/helper has a focused test in the same PR (Sonar new-code coverage). | Draft |

### Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | **WITHDRAWN** — guarded byte-invariance (C-002), which was retired upstream by `ccd278061`. See Scope Change section. | Withdrawn |
| C-002 | FR-007 must not break release tooling: root `CHANGELOG.md` stays the valid Keep-a-Changelog file read by `scripts/release/extract_changelog.py`. | Draft |
| C-003 | Use canonical surfaces; the gate IS `check_dead_body_links` — do **not** build a new/parallel link-checker module or a `Resolver`-backed gate. The mission *reduces* the checker count to one. | Draft |
| C-004 | All new code/prose pass `tests/architectural/test_no_legacy_terminology.py`. | Draft |
| C-005 | No new agent directories. Version bump (`pyproject.toml` + `CHANGELOG.md`) required only if `src/specify_cli/__init__.py` changes; this mission touches `scripts/`, `tests/`, `.github/workflows/`, `docs/`. | Draft |
| C-006 | Gate exemptions (FR-003) are narrow and individually justified; narrowness is itself tested (mirroring `test_docs_adr_exemption_is_narrow`). No blanket suppressions. | Draft |
| C-007 | **Gate-unmask cannot self-validate.** The widened gate (FR-002) only runs after merge; within the mission PR the old `EXCLUDE_PREFIXES` runs, so the PR could go green without ever validating `docs/adr/`+`docs/changelog/`. Acceptance MUST include a pre-merge full-tree dry-run (`check_dead_body_links` with `EXCLUDE_PREFIXES=()`) over the integrated branch requiring zero dead links — not just per-lane green. | Draft |

## Success Criteria

| ID | Criterion | Verification |
|---|---|---|
| SC-001 | Zero inline body links dangle anywhere under `docs/`, including `docs/adr/` and `docs/changelog/`. | Full-tree `check_dead_body_links` (no exclusions) green. |
| SC-002 | A deliberately broken inline doc link fails CI with a message naming file, **line**, and broken target. | Red-first test with ≥2 known-bad links; assert all reported with line numbers. |
| SC-003 | Editing one CHANGELOG file without mirroring the other fails CI. | Red-first divergence test; assert sync gate fails, then converge. |
| SC-004 | The ADR census counts all 119 promoted ADRs (`TestCensus` green at 119); the 2 formerly-non-dated ADRs are included. | `TestCensus.test_exactly_117_unique_adrs` passes at 119; `test_every_adr_has_bare_madr_status_frontmatter` green. |
| SC-005 | Exactly **one** `docs/`-body dead-link resolver runs in CI; the 3 named hand-rolled checkers are retired (their non-link assertions preserved; escape-guard ported). | An executable sentinel test asserts no new hand-rolled dead-link loop appears under `tests/docs/`, **excluding** the documented different-concern loops (`version_leakage_check.py`, `frontmatter_backfill.py`, `related_validator.py`, `test_glossary_link_integrity.py`, `test_readme_governance.py`); gate visits the 3 absorbed subtrees. |
| SC-006 | No stale `architecture/`/dropped-symlink claims remain in non-exempt relocated nav/READMEs; terminology-exemption policy is documented and linked. | Triage list with per-file disposition resolved; policy file exists + linked from guard test. |
| SC-007 | The gate-unmask is self-validated before merge. | Pre-merge full-tree dry-run (C-007) green on the integrated branch. |

## Sequencing, Dependencies & Risk (squad-derived)

The 4 lanes are **not** 4-way parallel. Structure:

- **A1** (parallel): gate strengthening behind the *unchanged* `EXCLUDE_PREFIXES` — non-vacuity (FR-004), `(file,line,target)` data-model + output (NFR-003), link-shape/exemption coverage (FR-003), confirm/document the gate (FR-001). Owns `relative_link_fixer.py` + `test_relative_link_fixer.py`.
- **B** (parallel): FR-006 canonical link fixes; FR-007 generator + shared-region + divergence test. Owns both CHANGELOG files.
- **C** (parallel, **two independent small WPs** — no serial spine post-rebase): WP05 = FR-008 plain ADR link repair (edits ADR bodies); WP06 = FR-011 census widen (edits `test_adr_content_invariance.py` only). They touch different files and have no coupling — the byte-invariance gate and `migrate_adr_body_links` transform no longer exist. Both must complete before the terminal A2.
- **D** (parallel): FR-012 prose triage; FR-013 terminology policy doc. Owns `docs/adr/2.x/README.md` (a README, outside the census filter), the prose targets, and `test_terminology_guards.py`.
- **A2** (**serialized after B, C, D**): flip `EXCLUDE_PREFIXES` (FR-002), retire the 3 hidden checkers + route their scope (FR-005), invert `test_gate_excludes_immutable_subtrees` (`test_relative_link_fixer.py:264`), re-pin `_KNOWN_GAPS`, widen the `docs-freshness.yml` step scope, and run the C-007 full-tree dry-run.

**Single biggest risk (post-rebase):** FR-002's gate-flip reds the whole branch until B+C land. Lane C is now two lightweight independent WPs (link repair + census bump), not a serial spine. Make A2 the explicitly-gated terminal step.

**Realistic size:** ~8 WPs; the serial spine in Lane C collapsed to two independent WPs.

## Key Entities

- **The gate** — `check_dead_body_links` (`relative_link_fixer.py`), the one authoritative body-link resolver.
- **`Unresolvable`** — the gate's finding record; gains a `line` field (NFR-003).
- **`EXCLUDE_PREFIXES`** — the exclusion tuple whose narrowing (to empty) is the terminal gate-flip.
- **ADR census** — `TestCensus` in `test_adr_content_invariance.py`; count widens from 117 to 119 (FR-011).
- **CHANGELOG pair** — canonical source `docs/changelog/CHANGELOG.md` + generated root `CHANGELOG.md`.

## Assumptions

- Verified counts: **27** broken ADR-body links across 12 files; **5** broken canonical-CHANGELOG links; **2** non-dated promoted ADRs; **117** dated ADRs today (→119). Implementation enumerates the exact live set at execution time.
- The `kitty-specs/` ADR links are **delinked** (decision), so the gate resolver stays `docs/`-scoped — no repo-wide resolver extension is needed.
- The "unify" scope **includes retiring** the 3 hidden hand-rolled checkers (decision); the mission ends with exactly one body-link resolver.
- The byte-invariance comparator (`TestContentInvariance`, `_EXPECTED_INVARIANT`, `_SANCTIONED_SELF_AMENDMENT`) no longer exists (retired by `ccd278061`). The withdrawn Lane-C requirements (former numbers 009 and 010), the withdrawn C-001 constraint, and the `migrate_adr_body_links` transform are all moot.
- Per DIR-013, any pre-existing unrelated test failures hit during implementation are filed as a GitHub issue before being treated as baseline.

## Scope

**In scope:** the single authoritative gate (A1+A2), the hidden-checker unification (FR-005), CHANGELOG link fixes + one-direction sync (B), the C-002-waived ADR link migration/delink + comparator + born-in-`docs/` census (C), prose triage + terminology policy doc (D) — all seven #2245 items.

**Out of scope:** authoring new documentation content; the `related:` frontmatter graph (gated by `related_validator`); built-site redirect coverage (gated by `redirect_stub_generator`); extending the gate resolver outside `docs/`; any `docs/` layout restructure beyond correcting stale references.

## Dependencies

- Surfaces unified/extended: `scripts/docs/relative_link_fixer.py` (`check_dead_body_links`, `EXCLUDE_PREFIXES`, `Unresolvable`), `tests/docs/test_relative_link_fixer.py`, the 3 hidden checkers (`tests/docs/test_architecture_docs_consistency.py`, `tests/docs/test_versioned_docs_integrity.py`), `tests/docs/test_adr_content_invariance.py` (census only — `TestCensus`), `tests/contract/test_terminology_guards.py`.
- CI wiring: `.github/workflows/docs-freshness.yml`, `.github/workflows/ci-quality.yml` (fast + integration shards), `.github/workflows/docs-pages.yml`.
- Release consumer of root CHANGELOG: `scripts/release/extract_changelog.py`.
