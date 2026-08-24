---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: org-tier-expected-artifacts-unreachable-01M0RMBG
mission_id: 01M0RMBGAAZBNPBMQ9VA5ZZTMD
generated_at: '2026-08-24T03:26:58.298220+00:00'
analyzer_agent: claude-sonnet
input_artifacts:
  spec.md:
    path: /home/jeroennouws/dev/SK-missions/3703/kitty-specs/org-tier-expected-artifacts-unreachable-01M0RMBG/spec.md
    sha256: 62b14590dd242a13888316323e8b7ac72fe23fda942f701a85438ff4f85520db
  plan.md:
    path: /home/jeroennouws/dev/SK-missions/3703/kitty-specs/org-tier-expected-artifacts-unreachable-01M0RMBG/plan.md
    sha256: 97a4fbbe1d7ee92dd59b9b295a3b988df9b8770dffbccc01eba00ff6a4662b68
  tasks.md:
    path: /home/jeroennouws/dev/SK-missions/3703/kitty-specs/org-tier-expected-artifacts-unreachable-01M0RMBG/tasks.md
    sha256: e96eacb40522220df69917770e943d001e577ac59b27c6c63d60b99a6b5b7846
  charter:
    path: /home/jeroennouws/dev/SK-missions/3703/.kittify/charter/charter.yaml
    sha256: a90fa5d9fb0187d036a248af499643921f46773f96ad8a37e660a801ee60b641
verdict: ready
issue_counts:
  medium: 1
  low: 0
  critical: 0
  high: 0
  info: 0
findings:
- id: I1
  severity: medium
  category: inconsistency
  summary: spec.md:34 cites a nonexistent resolver.py function `_resolve_mission_config` (actual sibling function is `resolve_mission`, resolver.py:769); the identical error was already caught and fixed in plan.md by a prior review (PLAN-FRESH2-003) but spec.md and tracer-approach.md were never corrected.
---

## Specification Analysis Report

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| I1 | Inconsistency | MEDIUM | spec.md:34; cf. plan.md:11, tracer-approach.md:45 | spec.md's User Story 1 "Why this priority" paragraph cites `src/specify_cli/runtime/resolver.py` (`_resolve_asset` at line 378, `_resolve_mission_config` at line 817) as the sibling org-tier resolvers FR-001 must match. Verified against the actual file: no function named `_resolve_mission_config` exists anywhere in `resolver.py` (confirmed via `grep -n "_resolve_mission_config" src/specify_cli/runtime/resolver.py` -> zero matches). The function that actually occupies line 817 is `resolve_mission`, defined at line 769, whose org-tier check (`org_path = org_root / "missions" / name / filename`) sits at line 817 -- so the *substance* of the citation (this sibling resolver anchors at the `missions/` segment) is correct, only the cited function name is wrong. This exact defect was already found and fixed in `plan.md`'s Summary section by a prior plan-phase review (`kitty-specs/.../reviews/plan.fresh-2.yaml`, finding `PLAN-FRESH2-003`, severity 3, "Summary section cites a nonexistent function name, `_resolve_mission_config`, in resolver.py"), confirmed corrected in `plan.md` by the matching verify pass (`plan.verify-3.yaml`: "A full-file grep of the current plan.md for `_resolve_mission_config` returns zero matches, the Summary now cites `resolve_mission:769`"). `plan.md:11` today correctly reads "`_resolve_asset`, `resolve_mission:769`". But `spec.md:34` -- a separate core artifact, out of scope for that plan-phase review -- still carries the original, uncorrected citation verbatim, and the identical wording also survives in `tracer-approach.md:45` ("`_resolve_asset` and `_resolve_mission_config` myself (both check exactly"). | Correct `spec.md:34` to name `resolve_mission` (with a `:769`/`:817` citation for consistency with plan.md's fixed form) in place of `_resolve_mission_config`; optionally correct the same wording in `tracer-approach.md:45`. Does not block implementation -- WP01's T002 implementation steps quote the actual before/after code verbatim and never reference this function name -- but the citation should be fixed so a reader relying on spec.md's file:line citation discipline at its most load-bearing sentence (the mission's entire P1 justification) is not misled, and so this mission does not close with a previously-identified-and-partially-fixed defect still live in one of its three core artifacts. |

**Coverage Summary Table:**

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| fr-001-correct-the-org-tier-path-join | Yes | T002 | Path-join fix, `org_expected_artifacts.py:82`; verified the cited line/content match the current file exactly. |
| fr-002-correct-the-module-function-docstring | Yes | T002 | Docstring corrections including the Contract C-4 staleness caveat sentence. |
| fr-003-update-test_org_expected_artifacts-fixture-helper | Yes | T001, T003 | RED-first new test case (T001) + helper/hand-built-path maintenance (T003); all five cited malformed-file test methods and their line numbers verified present and accurate in the current file. |
| fr-004-update-test_mission_type_profiles-fixture-helper | Yes | T004 | Duplicated helper correction; cited line numbers (996, 1014) verified accurate. |
| fr-005-update-tests-dossier-fixture-helpers | Yes | T005 | Three duplicated helpers across test_manifest.py, test_rebaseline.py, test_indexer.py; all cited line numbers verified accurate, including test_indexer.py's helper correctly having no docstring. |
| nfr-001-atdd-first | Yes | T001 (RED-first), T002 (GREEN) | RED-first mechanics independently verified against current code: case 1 (corrected anchor) is mechanically RED because the resolver still joins the old path at line 82; case 2 (old-anchor-only) is mechanically RED because the old path IS currently found. Both flip correctly once T002's one-line fix lands. |
| nfr-002-no-new-silent-failure-mode | Yes | T002 step 4, T006 | `_read_yaml_mapping` explicitly left untouched; verified its warning-logging logic is unchanged in the current file. |
| nfr-003-declared-order-precedence-preserved | Yes | T006 (verification via existing precedence tests) | Existing precedence test class confirmed present at spec.md's cited line (93). |
| c-001-through-c-007 (constraints) | Yes | T006 (six-file-set, gate verification), throughout WP guidance | All seven constraints have explicit WP guardrails (no-fallback, no-validator-gate, terminology grep, baseline discipline, frozen contract doc left untouched). |

**Charter Alignment Issues:** None found. ATDD-first (C-011) discipline is correctly modeled: NFR-001 pins two RED states before the T002 implementation commit, with the FR-003/004/005 maintenance corrections explicitly and correctly excluded from RED-first as "tracking already-passing coverage through the anchor move." The `__all__` convention (C-007 of charter.md) is already satisfied by the untouched `org_expected_artifacts.py` (`__all__ = ["resolve_org_expected_artifacts"]`, verified present at line 41). The C-003 "no validator gate" and PR-shape ("one PR") binding decisions named in this dispatch's operating constraints are correctly reflected as out-of-scope/single-PR throughout spec.md, plan.md, and WP01, and are not re-flagged here. No campsite-clean commit is charter-required and plan.md's Campsite-Clean Scope section states this verdict explicitly rather than skipping the topic, per Standing Order #2's expectation that a deferral be stated, not silent.

No conflict was found between `.kittify/charter/charter.md` and this repo's `CLAUDE.md` -- both agree that `main` is the base branch, that the charter is binding governance read first, and that direct pushes to `main`/origin are prohibited.

**Unmapped Tasks:** None -- all six subtasks (T001-T006) map to at least one FR/NFR/constraint, and every FR/NFR/constraint in spec.md has at least one subtask.

**CI Gate Claims Spot-Verified Against Live Config (not merely trusted):** `.github/workflows/ci-quality.yml`'s `diff-coverage` job's `critical_paths` array contains `'src/charter/*'` and does NOT contain `src/specify_cli/dossier/*`, exactly as plan.md's Gate Set section claims. The charter package's own coverage floor is `--cov-fail-under=55` (line 2297), not 90%, exactly as claimed. The `mypy` step is literally named `"[INFO] Run mypy report (advisory)"` with `id: mypy`, confirming plan.md's "advisory, not enforced" characterization. `.github/workflows/doctrine-charter-tests.yml` exists as cited.

**Metrics:**

- Total Requirements: 5 FR + 3 NFR + 7 Constraints = 15
- Total Tasks (subtasks): 6 (T001-T006)
- Coverage %: 100% (every FR/NFR/constraint maps to >=1 subtask)
- Ambiguity Count: 0 (no vague adjectives without measurable criteria; no unresolved placeholders found)
- Duplication Count: 0 (the five duplicated fixture-helper implementations are a deliberately-scoped, spec-acknowledged defect the mission itself exists to correct, not an artifact-authoring duplication)
- Critical Issues Count: 0
- High Issues Count: 0
- Medium Issues Count: 1 (I1)

## Next Actions

- No CRITICAL or HIGH issues exist; implementation is not blocked.
- One MEDIUM finding (I1) exists: a stale/fabricated function-name citation in `spec.md:34` (and `tracer-approach.md:45`), already fixed in `plan.md` by a prior review round. Recommend a small, low-risk spec.md touch-up (`_resolve_mission_config` -> `resolve_mission`, cf. `resolver.py:769`) before or alongside implementation -- this is documentation-only and does not touch any of the six code/test files C-001 scopes, so it carries no file-set or RED-first implications for WP01.
- No other cross-artifact gaps, duplications, charter conflicts, or coverage gaps were found across spec.md, plan.md, tasks.md, and WP01 in this pass.

## Offer Remediation

Should this finding be addressed before moving on to implementation? A concrete remediation edit (spec.md line 34, and optionally tracer-approach.md line 45) can be suggested for operator approval if desired. This report does not apply any edits automatically.
