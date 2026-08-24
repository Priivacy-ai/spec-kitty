---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: custom-mission-guard-failure-blocking-inert-01M0STY0
mission_id: 01M0STY03DZZJFMXHVQ5FJX6VS
generated_at: '2026-08-24T15:21:41.886692+00:00'
analyzer_agent: unknown
input_artifacts:
  spec.md:
    path: /home/jeroennouws/dev/SK-missions/3704/kitty-specs/custom-mission-guard-failure-blocking-inert-01M0STY0/spec.md
    sha256: ad6ea4f3f765d68ee69a69f909668d1696d570ffd141df687dbf334c87a46567
  plan.md:
    path: /home/jeroennouws/dev/SK-missions/3704/kitty-specs/custom-mission-guard-failure-blocking-inert-01M0STY0/plan.md
    sha256: b7ca8dd4bfc833a27eb8916e4690a5388d38a2e60ad4ecb40f19f0c1a70fc0e6
  tasks.md:
    path: /home/jeroennouws/dev/SK-missions/3704/kitty-specs/custom-mission-guard-failure-blocking-inert-01M0STY0/tasks.md
    sha256: 05a317e8c6ea5459a16c62a42fe9145c85fa44d61df029edefad9b086ffb5ba0
  charter:
    path: /home/jeroennouws/dev/SK-missions/3704/.kittify/charter/charter.yaml
    sha256: a90fa5d9fb0187d036a248af499643921f46773f96ad8a37e660a801ee60b641
verdict: ready
issue_counts:
  high: 0
  low: 0
  medium: 0
  critical: 0
  info: 0
findings: []
---

# Cross-Artifact Analysis (re-run): Custom Mission Guard Failure Blocking Inert

**Mission**: `custom-mission-guard-failure-blocking-inert-01M0STY0`
**Scope**: spec.md, plan.md, tasks.md, `tasks/WP01-04-*.md`, cross-checked against
`.kittify/charter/charter.md` and, where a claim was verifiable, against live source.
**Trigger for this re-run**: a post-record-analysis adversarial squad (two independent
subagents) confirmed one finding the prior self-check pass (committed
`23191cd0c`, verdict: ready, findings: []) missed: **ANALYZE-ARCH-001** (severity 4),
recorded in `reviews/analyze.confirmed.yaml`. That finding has now been remediated; this
report re-verifies the fix and re-runs every detection pass from scratch, not just the
one that missed it.

## ANALYZE-ARCH-001 — verified fixed

**Original claim (false).** spec.md's FR-010/Edge Cases asserted that (1) built-in-tier
YAML-syntax manifest failures "degrade to no manifest silently... exactly as
`MissionTemplateRepository.get_expected_artifacts`... already do[es] today" and (2) schema
failures "raise `ManifestSchemaError` loudly... matching the precedent
`ManifestRegistry.load_manifest` already established... for both built-in and org tiers."
Both were false: (1) `get_expected_artifacts` raises `MalformedManifestError` loudly by
design (pinned by the live, passing
`tests/doctrine/missions/test_repository.py::test_malformed_manifest_fails_loud_distinct_from_absent`);
(2) `ManifestSchemaError` is raised only by `specify_cli.dossier.manifest.ManifestRegistry.load_manifest`,
a module this mission's blast radius never calls — `resolver.py::_load_expected_artifact_manifest`
called `ExpectedArtifactManifest.model_validate(...)` with zero exception handling, so a
schema-invalid manifest raised a bare, uncaught `pydantic.ValidationError`. WP02's own new
org-tier lookup was the first change to make that crash reachable for org manifests, at the
exact moment the spec claimed (incorrectly) it was already covered.

**Fix verified (commit `3e1d4766b`).**
- `spec.md` Edge Cases (lines 217-241) and FR-010 (lines ~460-490): rewritten to state the
  true, asymmetric current behavior (built-in raises `MalformedManifestError` loudly,
  already fixed; org tier degrades silently via `resolve_org_expected_artifacts`, a
  pre-existing out-of-scope asymmetry; neither tier raises `ManifestSchemaError` on this
  mission's call path today) and makes an explicit, non-vacuous Option A design decision
  (close the crash risk) with stated rationale over Option B (scope-out), re-read in full —
  confirmed no residual "already implemented"/"matches existing precedent" phrasing remains
  for this claim (`grep` for the phrase across spec.md/plan.md/tasks.md/WP02 file returned
  only my own corrective annotation, not a live false claim).
- `plan.md`'s Seam/module-placement table (line 109): the `_load_expected_artifact_manifest`
  row now explicitly carries FR-010's `try/except pydantic.ValidationError` →
  `ManifestSchemaError` re-raise, for both tiers, with the import-precedent rationale
  (`specify_cli.sync.namespace`/`specify_cli.sync.dossier_pipeline` already cross the same
  `specify_cli.runtime` ↔ `specify_cli.dossier` seam for this exact type — re-confirmed live
  via `grep` against both files). FR-010 is no longer silently absent from the plan's own
  architecture table; the WP02 phasing-table row (line 481) was updated to match.
- `tasks.md`'s WP02 section: the false "already implemented by the functions this WP calls
  through" Implementation Note is replaced with the corrected record plus two new,
  properly-sequenced subtasks — **T009b** (ATDD-RED: schema-invalid-manifest cases, both
  tiers) and **T010b** (wraps `model_validate(...)`, re-raises `ManifestSchemaError`,
  lands with/immediately after T010, before T011) — reflected consistently in the Included
  Subtasks list, the commit-ordering note, the coverage-exemption note, the Subtask Index
  table, and the FR→WP traceability table (both re-checked by `grep` for stray/missing
  T009b or T010b references — none found).
- `tasks/WP02-org-tier-manifest-resolution-and-campsite-clean.md`: frontmatter `subtasks`
  list, the Goal section (new item 3), T009 (unchanged content, new T009b inserted after
  it), the corrected T010 (which now explicitly disclaims the false docstring-precedent
  claim rather than repeating it) and new T010b, T015's regression-scope line, the Gates
  section's `patch()`-target and coverage-exemption notes, and a new Risks bullet were all
  updated consistently. Re-read in full end to end after editing — no orphaned reference to
  the old (pre-fix) T010 text remains.

## Re-run detection passes

**Duplication.** No problematic duplication. The FR-010 rationale is stated once in
spec.md (canonical) and referenced, not restated in full, from tasks.md/WP02's
Implementation Notes and the WP02 prompt file — consistent with this mission's existing
pattern of deliberate, load-bearing cross-references (e.g. `planning_base_branch`).

**Ambiguity.** None found. The Option A vs. Option B decision is explicit and justified in
spec.md, not left implicit; T010b's landing constraint ("no later than T010") removes the
one sequencing ambiguity a reviewer could otherwise raise about the two new subtasks.

**Underspecification.** None found for the fixed area: T010b names the exact wrap
(`try/except pydantic.ValidationError`), the exact re-raise
(`ManifestSchemaError(mission_type, config.origin)`), the exact import source
(`specify_cli.dossier.manifest`), and the exact precedent that makes the import direction
architecturally sound.

**Charter alignment.** Re-checked ATDD-first (C-011): T009b is explicitly RED-first,
sequenced before T010b, matching every other WP02 subtask pair. Locality-of-change /
smallest-viable-diff reconciliation: the fix adds zero new files to WP02's `owned_files`
and stays inside the one function plan.md already commits to editing for FR-008 — the
spec.md rationale note explicitly ties the Option A choice to this reconciliation.
Single-canonical-authority: `ManifestSchemaError` is reused, not re-invented; no second,
softer exception type is introduced anywhere in the fix.

**Coverage gaps (FR/AC → WP traceability).** FR-010 now has a real, non-vacuous WP
attribution (`WP02 (T009b/T010b)`) in tasks.md's Requirements Coverage Summary table,
replacing the previous "mirrors existing precedent" row that named no subtask at all.
Every other FR/AC/NFR/C row in that table was re-scanned; no new orphan was introduced by
this fix (the only rows touched are FR-010's own summary line and the two new Subtask
Index rows for T009b/T010b, both correctly attributed to WP02/P1).

**Inconsistency.** Cross-checked spec.md's FR-010 text against plan.md's Seam-table row and
tasks.md/WP02-file's T009b/T010b text for the same set of facts (which tiers raise what,
which import is used, which function is edited, Option A vs. B and why): all four
locations state the same facts, in different levels of detail appropriate to each
artifact's role (spec = requirement + rationale, plan = seam/architecture, tasks = subtask
mechanics), with no contradiction.

**Terminology canon / glossary.** No new user-facing term introduced by this fix
(`ManifestSchemaError`, `pydantic.ValidationError`, `_load_expected_artifact_manifest` are
all pre-existing internal identifiers, not new domain vocabulary). No `feature*` alias
language introduced.

## Spot-check: same failure pattern (unverified "already implemented"/"matches precedent"
## claims) elsewhere in spec.md/plan.md/tasks.md

Per the fix-round brief's instruction to check the defect CLASS, not just the cited
instance, 2 additional load-bearing "already implements"/"already established" claims were
spot-checked directly against live source (beyond the one already fixed):

1. spec.md FR-004 (~line 323): "`resolve_org_expected_artifacts` already implements"
   last-existing-match-wins precedence and whole-file (never field-merged) replacement.
   **Verified TRUE** against `src/charter/org_expected_artifacts.py:86-92` — the function's
   loop keeps overwriting `result` only on a real match (`if parsed is not None: result =
   parsed`), which is exactly last-match-wins, whole-file replacement.
2. spec.md FR-004 (~line 324): "the parameter shape... `ManifestRegistry.load_manifest`'s
   FR-008/WP05 fix already established: an optional `repo_root: Path | None = None`".
   **Verified TRUE** against `src/specify_cli/dossier/manifest.py`'s `load_manifest`
   signature (`mission_type: str, repo_root: Path | None = None`).

No other false claim of this class was found. Both spot-checked claims hold against live
source; no further fix was needed or made beyond ANALYZE-ARCH-001 itself.

## Conclusion

ANALYZE-ARCH-001 is resolved: spec.md/plan.md/tasks.md/WP02 file no longer assert the
false "already handled" claim, state the true asymmetric current behavior, make an
explicit non-vacuous Option A design decision with rationale, and add two correctly
sequenced, ATDD-red-first WP02 subtasks (T009b/T010b) that will actually close the
crash risk when implemented. Every other detection pass was re-run clean, and a
class-level spot-check of 2 similar claims elsewhere found no further defect. **Verdict:
ready.**
