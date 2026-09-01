---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: custom-mission-guard-failure-blocking-inert-01M0STY0
mission_id: 01M0STY03DZZJFMXHVQ5FJX6VS
generated_at: '2026-08-24T15:34:30.024579+00:00'
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
    sha256: 626cebae7e711b54ec31baac050576598a2db20d1e28fb99e736ab20350aae1b
  charter:
    path: /home/jeroennouws/dev/SK-missions/3704/.kittify/charter/charter.yaml
    sha256: a90fa5d9fb0187d036a248af499643921f46773f96ad8a37e660a801ee60b641
verdict: ready
issue_counts:
  medium: 0
  low: 0
  critical: 0
  high: 0
  info: 0
findings: []
---

# Cross-Artifact Analysis (fix round 2 re-run): Custom Mission Guard Failure Blocking Inert

**Mission**: `custom-mission-guard-failure-blocking-inert-01M0STY0`
**Scope**: spec.md, plan.md, tasks.md, `tasks/WP01-04-*.md`, cross-checked against
`.kittify/charter/charter.md` and, where a claim was verifiable, against live source
(`src/specify_cli/dossier/manifest.py`, `src/charter/org_expected_artifacts.py`,
`src/specify_cli/runtime/resolver.py`, `src/doctrine/missions/repository.py`).
**Trigger for this re-run**: a fresh-eyes lens (`reviews/analyze-fresh.yaml`,
**ANALYZE-FRESH-001**, severity 3) found that the previous fix round's T010b text
instructed re-raising `ManifestSchemaError(mission_type, config.origin)` "for both the
built-in and the T010-added org-tier branch." That is correct only for the built-in
branch — the org-tier branch's `config` is `resolve_org_expected_artifacts`'s return
value, a bare `Mapping[str, Any] | None` with no `.origin` attribute, so the literal
instruction would raise `AttributeError` on exactly the org-tier schema-invalid-manifest
path FR-010 exists to close.

## ANALYZE-FRESH-001 — verified fixed

**Original defect.** T010b (tasks.md's "Included Subtasks" list and
`tasks/WP02-org-tier-manifest-resolution-and-campsite-clean.md`'s full subtask body) used
a single origin expression, `config.origin`, and applied it to "both" branches. The
precedent it claims to mirror, `ManifestRegistry.load_manifest`
(`src/specify_cli/dossier/manifest.py:274-340`), actually uses TWO DIFFERENT origin
expressions: `config.origin` in the built-in branch (`config` is a real `ConfigResult`,
lines 326-340) and a synthesized descriptive string (mission type + org roots checked,
lines ~283-301) in the org-tier branch, precisely because
`resolve_org_expected_artifacts` (`src/charter/org_expected_artifacts.py:54-92`) returns
only a bare parsed `Mapping`, with no `.origin` field anywhere on it. Re-verified this
live: `resolve_org_expected_artifacts`'s return type and body confirm no `.origin`
attribute exists on its result; `MissionTemplateRepository.get_expected_artifacts`
(`src/doctrine/missions/repository.py:385`) confirms `.origin` is a `ConfigResult`-only
field.

**Fix applied (commit `de2bac388`).**
- `tasks.md`'s T010b entry (Included Subtasks list) rewritten to state both origin
  expressions explicitly: `ManifestSchemaError(mission_type, config.origin)` for the
  built-in branch only (`config` is a real `ConfigResult` there); a synthesized
  descriptive origin string (mission type + org roots checked, mirroring
  `manifest.py:283-291`'s org-tier except-block) for the org-tier branch, because
  `resolve_org_expected_artifacts` returns a bare `Mapping` with no `.origin` attribute.
  Explicitly warns against reusing `config.origin` in the org-tier branch (AttributeError
  risk) and against masking that risk with a broad `except Exception`.
- `tasks/WP02-org-tier-manifest-resolution-and-campsite-clean.md`'s T010b subtask body
  rewritten with the same two-branch split, spelled out with the exact synthesized
  `origin = f"org-tier expected-artifacts.yaml for mission type {mission_type!r} ..."`
  expression and `raise ManifestSchemaError(mission_type, origin) from exc` for the
  org-tier branch, and `raise ManifestSchemaError(mission_type, config.origin) from exc`
  for the built-in branch. Both files now state the fix precisely — "the actual
  expression/technique," not "handle appropriately" — matching the finding's
  remediation instruction.
- `tasks.md`'s and the WP02 file's T009b RED-test descriptions were also strengthened:
  the org-tier schema-invalid test case now must additionally assert
  `ManifestSchemaError.origin` is a non-empty descriptive string naming the org tier +
  mission type, not just that the exception type is `ManifestSchemaError`. This closes a
  secondary gap: the pre-fix T009b text would have caught the `AttributeError` crash (a
  different exception type than `pytest.raises(ManifestSchemaError)` expects) but would
  not have positively pinned that the org-tier branch's origin is correctly derived
  (versus, e.g., an implementer taking a shortcut like a hardcoded placeholder string).
- No bare `except Exception` was introduced anywhere in the corrected text — the fix
  explicitly calls out that this would reintroduce a silent-failure hazard, per this
  fix round's own brief.
- `spec.md` and `plan.md` were re-checked and require NO change: neither commits to the
  specific `config.origin` expression for both branches — spec.md's FR-010 rationale and
  plan.md's Seam-table row both say "re-raising `ManifestSchemaError`... for both the
  built-in and the new org-tier branch" without naming a single shared origin
  expression, so they were never the locus of this defect (confirmed via `sha256sum`:
  both files' hashes are unchanged from the prior round's recorded report). This also
  keeps the fix inside `tasks.md`/WP02's file only, per Locality-of-Change /
  smallest-viable-diff (charter reconciliation order): only the two files the finding
  named were touched.

## Re-run detection passes

**Duplication.** No new duplication. The two origin expressions are each stated once
per file (compact form in tasks.md, full form with the code snippet in the WP02 file) —
consistent with the mission's existing summary/detail split between the two artifacts.

**Ambiguity.** None found. T010b now names the concrete Python expression for each
branch rather than a single ambiguous phrase applied to "both."

**Underspecification.** Resolved for the fixed area: T010b in both files now states the
exact variable in scope per branch (`config` for built-in, `org_parsed`/`org_roots` for
org-tier), the exact synthesized-origin expression (a verbatim code block in the WP02
file), and an explicit prohibition on both the wrong shortcut (`config.origin` in the
org-tier branch) and the unsafe workaround (`except Exception`).

**Charter alignment.** ATDD-first (C-011): T009b remains RED-first, sequenced before
T010b; the strengthened origin assertion still lands in the RED test, not deferred.
Locality-of-change / smallest-viable-diff: only `tasks.md` and the one WP02 subtask file
named by the finding were edited; no new files, no change to spec.md/plan.md/other WP
files. Single-canonical-authority: still reuses `ManifestSchemaError`, still mirrors
`ManifestRegistry.load_manifest`'s existing precedent exactly (now correctly, per-branch)
rather than inventing a new pattern.

**Coverage gaps (FR/AC → WP traceability).** FR-010's traceability row (`WP02
(T009b/T010b)`) is unchanged and still correct — this fix corrects a subtask's
implementation-detail text, not its FR/WP attribution. No new orphan introduced.

**Inconsistency.** Cross-checked tasks.md's compact T010b text against the WP02 file's
full T010b text: both now state the same two per-branch origin expressions, the same
prohibition on `config.origin` in the org-tier branch, and the same prohibition on a
broad `except Exception` — no drift between the two artifacts. Also cross-checked
against spec.md/plan.md (both artifact-level, deliberately non-committal on the exact
origin expression) — no contradiction, since neither ever asserted a single shared
expression to begin with.

**Terminology canon / glossary.** No new user-facing term introduced. No `feature*`
alias language. No version numbers added to scope.

**Fresh-eyes re-check.** Re-read `src/specify_cli/dossier/manifest.py:274-340` end to
end again (not just the previously-cited line ranges) to confirm the two except-blocks
really do use two different `origin` expressions and that no third branch/edge case in
that precedent was missed. Confirmed: exactly two `except` blocks in the org-tier path
(`ValidationError` → synthesized origin; broad `Exception` → tolerant swallow-to-`None`,
explicitly NOT touched or mirrored by this fix, since T010b's scope is only the
`ValidationError`/`ManifestSchemaError` re-raise, not the separate tolerant-swallow
behavior for non-schema org-tier failures) and one `except ValidationError` block in the
built-in path using `config.origin`. The corrected T010b text matches this shape exactly
for the `ValidationError` case in both tiers.

## Not re-litigated (per this round's scope)

**ANALYZE-ARCH-001** — already fixed in the prior round and independently verified
resolved; not re-opened or re-examined here beyond confirming (via unchanged spec.md/
plan.md hashes and the surrounding T010/T009b text still reading correctly) that this
round's edit did not disturb that fix.
**SK-97** — out of scope for this round; not touched.

## Conclusion

ANALYZE-FRESH-001 is resolved: T010b in both `tasks.md` and
`tasks/WP02-org-tier-manifest-resolution-and-campsite-clean.md` now states two distinct,
concrete, branch-specific `ManifestSchemaError` origin expressions — `config.origin` for
the built-in branch (a real `ConfigResult` attribute) and a synthesized descriptive
string for the org-tier branch (mirroring `ManifestRegistry.load_manifest`'s own
precedent) — closing the `AttributeError` risk the finding identified, without
introducing a silent `except Exception` swallow. T009b's RED-test description was
strengthened to assert on the org-tier origin's content, not just the exception type.
Every other detection pass was re-run clean; spec.md and plan.md required no change and
are confirmed unchanged (hash-verified). **Verdict: ready.**
