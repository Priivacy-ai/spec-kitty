# Issue Matrix — Org-Pack Subdir Source & Doctrine QoL (01KVSRJ6)

Driver: #2083. Doctrine-stack QoL mission bundling one P1 source-resolution bug,
one P1 doctrine-catalog reliability bug, and two doctrine quality improvements.
Issues actively implemented across this mission's WPs carry `in-mission`
(non-terminal — passes per-WP `approved`, MUST reach a terminal verdict before
mission `done`). Epic / deferred issues carry their terminal verdict now.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2083 | Org-pack git source can't consume packs in a subdirectory (no subdir/pack_path field) — the driver | in-mission | FR-001..FR-008 (effective-root seam at `OrgPackConfig`/registry + all-consumer resolution + containment validation + round-trip + fetch effective-root reporting + config-schema contract update) |
| #2092 | Doctrine catalog silently drops artifacts with `applies_to_languages: [any]` | in-mission | FR-012/FR-013 (validate-time fail-loud guard rejecting `any`/`all` tokens + `present-but-scope-filtered` MISSING_ARTIFACT diagnostic) |
| #707 | docs(charter): clarify ruamel.yaml vs PyYAML scope — frontmatter vs simple data YAML | in-mission | FR-009 (current-vs-aspirational rule verified against ≥3 named call sites; names known mixed-usage sites) |
| #2096 | Tiered coding standards (DDD) — doctrine-only slice: styleguide + DRG edge | in-mission | FR-010/FR-011. Child of #1843 (this mission's Thread C delivers epic slice ① "taxonomy+map artifact kind"). |
| #1843 | Tiered coding standards by domain importance (DDD) — epic | deferred-with-followup | Parent epic (itself a child of #1799). This mission delivers only slice ① via child #2096; slices ②–⑤ (CI per-tier gates, tool-config plumbing, agent-effort threading, repo tier-map dogfood) remain in the epic. SonarCloud per-path-gate feasibility (epic Q1) is the open blocker for the enforcement slices. |
| #2080 | Audit + remediate the DRG and doctrine artefacts (daphne-led) | deferred-with-followup | Follow-up: daphne-led audit epic whose deliverable is a remediation plan; NOT folded (would balloon scope). The Thread-C orphan-styleguide finding + asymmetric node-walking note (`research/post-spec-squad-findings.md`) are recorded as inputs. |
| #1799 | Epic: Charter & Doctrine — governance configuration & docs | deferred-with-followup | Follow-up: parent governance epic for #707 and #1843; this mission closes those two facets. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a WP in this mission; must reach a terminal verdict before mission `done`).

## Out-of-scope notes (do NOT fold)
- **#2080** daphne-led DRG/doctrine audit — its deliverable is a *remediation plan*, a curator-owned analysis mission categorically larger than a QoL fold. Operator decision 2026-06-23: follow-up mission. Folding it breaks the bounded-slice principle.
- **#1843 enforcement half** — CI per-tier gates + agent-effort routing are explicitly OUT (C-001); only the doctrine artifact + one DRG edge are in this mission.
- **doctrine fetch sparse-checkout** — optimization, not required for correctness (C-003); out of scope.

## Post-spec adversarial squad (alphonso + debbie + renata + priti, 2026-06-23)
- **CONVERGENT BLOCKER** (alphonso + debbie + priti): the original "single seam = `resolve_org_roots`" claim was FALSE — ≥6 consumers read `pack.local_path` directly (incl. the `doctor doctrine` health path `load_org_drg`→`load_org_pack`). Spec corrected: FR-001 moves the seam to `OrgPackConfig`/registry (`effective_root`); FR-004 enumerates consumers; C-007 mandates single normalization. Full evidence in `research/post-spec-squad-findings.md`.
- **Security** (debbie + renata): `ensure_within_directory()` is the right helper; split validation timing (string escapes at config-load, symlink at resolution); structured error must not be swallowed by the registry warning-degrade path → FR-003/NFR-002.
- **Fakeability** (renata + priti): Thread C orphan-styleguide + Thread B documenting a non-existent rule → FR-009/FR-010/FR-011 tightened; SC bound to named evidence.
- **Scope** (priti): config-schema contract + fetch UX added → FR-007/FR-008.
