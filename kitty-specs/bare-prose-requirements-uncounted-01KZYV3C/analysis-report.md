---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: bare-prose-requirements-uncounted-01KZYV3C
mission_id: 01KZYV3CT68WBACF0MJ323YF7X
generated_at: '2026-08-14T03:53:54.666169+00:00'
analyzer_agent: unknown
input_artifacts:
  spec.md:
    path: /home/jeroennouws/dev/SK-missions/3396/kitty-specs/bare-prose-requirements-uncounted-01KZYV3C/spec.md
    sha256: 4806a63b7d582ae056b4f4e5d9193e0cd5129ea190aff17506f63cc06a10648a
  plan.md:
    path: /home/jeroennouws/dev/SK-missions/3396/kitty-specs/bare-prose-requirements-uncounted-01KZYV3C/plan.md
    sha256: 7520e8e9a30cae470806b8c483ede6318a646f02dcb75dcb387573254aa1e381
  tasks.md:
    path: /home/jeroennouws/dev/SK-missions/3396/kitty-specs/bare-prose-requirements-uncounted-01KZYV3C/tasks.md
    sha256: 268a30facfffa78b2b064b2bf0fcdeb343809ebd6d3281635e0511b2f23747f8
  charter:
    path: /home/jeroennouws/dev/SK-missions/3396/.kittify/charter/charter.yaml
    sha256: b976bed223460ac3f4339da1c61c686c6ac96cf9baffdd501073b4e721a1442f
verdict: blocked
issue_counts:
  critical: 0
  medium: 1
  low: 0
  high: 2
  info: 0
findings:
- id: F1
  severity: high
  category: coverage
  summary: >-
    All 9 WP frontmatter files (tasks/WP01..WP09) carry an empty or absent
    requirement_refs field, even though tasks.md's own reviewed Coverage
    Matrix (tasks.md:845-859) and each WP's prose "Requirement Refs:" line
    already record a complete, R1-R6-reviewed FR->WP mapping.
    spec-kitty agent tasks map-requirements was never invoked, so the
    canonical field finalize-tasks/spec-kitty next trust remains blank.
    finalize-tasks's _validate_requirement_mapping (mission_finalize.py:621)
    is not vacuous-when-empty -- live reproduction on this checkout shows it
    is satisfied only because _resolve_dependencies_and_refs's tasks.md-text
    fallback (mission_finalize.py:508-520, gated on wps_manifest is None)
    regex-scans each WP's "Requirement Refs:" line and credits any FR/NFR/C
    token found there, including WP02's purely explanatory citation
    "(...prerequisite for WP06's FR-001 CLI wiring...)" -- crediting WP02
    with FR-001 though WP02 implements no FR itself. This is the SK-14
    citation-vs-declaration conflation recurring in the WP-level fallback
    parser (_parse_requirement_refs_from_tasks_md) rather than the
    already-patched spec.md parser, plus a second latent bug: that parser's
    regex has no DOTALL, so WP05's two-line Requirement Refs value silently
    truncates after the first line. Net effect: the one field this mission's
    own WP06 is titled to wire correctly stays empty on disk, and any future
    finalize-tasks run (once unblocked) would write back FALSE data for
    WP02 rather than the correct empty/no-FR mapping already implied by its
    own prose.
- id: F2
  severity: high
  category: coverage
  summary: >-
    spec-kitty agent mission finalize-tasks --mission
    bare-prose-requirements-uncounted-01KZYV3C fails on THIS checkout right
    now, both with and without --validate-only, before ever reaching the
    write phase: error WP owned_files cannot include paths under
    kitty-specs/, error_code INVALID_WP_OWNED_FILES_KITTY_SPECS,
    invalid_owned_files for WP01's two tracer file paths under
    kitty-specs/bare-prose-requirements-uncounted-01KZYV3C/. WP01's own
    frontmatter declares owned_files under kitty-specs/ (its tracer files),
    which _validate_owned_files_not_in_mission_specs categorically forbids.
    As authored, WP01 is unfinalizable through the sanctioned CLI path. I
    could not reproduce the previously-observed result success
    updated_wp_count 7 outcome on this checkout at this moment -- this
    gate now blocks first.
- id: F3
  severity: medium
  category: terminology
  summary: >-
    plan.md line 4 reads "Input: Feature specification from
    kitty-specs/.../spec.md" -- the prohibited term "Feature" (charter
    Terminology Canon / this mission's own C-004), inherited verbatim from
    the known-defective built-in software-dev plan template (ledger SK-11,
    packs/built-in/missions/software-dev/templates/plan-template.md line 4).
    plan.md's own Charter Check section (line 90) claims "PASS. Mission,
    never Feature (C-004)" -- a direct self-contradiction within the same
    artifact.
---

## Specification Analysis Findings

Mission: bare-prose-requirements-uncounted-01KZYV3C (issue #3396)
Phase: analyze (cross-artifact consistency, post-tasks)
Base: PR #3395's branch op/3394-requirement-citation-scope @ ab15225ea (binding, per operator ruling; NOT main)
Checkout: pr/bare-prose-requirements-uncounted @ 79516ee8e

### Scope of this pass

1. The named defect -- zero FR coverage in WP frontmatter despite a previously-observed finalize-tasks success -- investigated from the code, live-reproduced against this exact checkout.
2. A full cross-artifact pass: spec.md vs plan.md vs tasks.md vs WP frontmatter consistency, FR->WP->test traceability, terminology canon, charter alignment.

### F1 -- FR coverage never reaches WP frontmatter; finalize-tasks's gate is satisfied by a citation-blind fallback, not by design

Mechanism, read from code and confirmed live on this checkout (not inferred):

- tasks/WP01..WP09-*.md frontmatter: 7 WPs (WP02,03,05,06,07,08,09) carry requirement_refs: [] explicitly; WP01/WP04 carry no requirement_refs key at all. Confirmed by direct read of every file.
- tasks.md (the human/agent-reviewed, R1-R6-PASSED artifact) already carries the correct mapping twice over: a prose "Requirement Refs:" line inside every WP section (tasks.md:145,215,279,353,410,520,648,702,774) and an explicit Coverage Matrix table (tasks.md:845-859) listing every WP against every FR/NFR. map-requirements -- the sanctioned command whose own module docstring says it "writes requirement_refs directly into each WP file's YAML frontmatter" (src/specify_cli/requirement_mapping.py:1-6) -- was never invoked to transcribe that record into frontmatter.
- _validate_requirement_mapping (mission_finalize.py:621-675) is NOT vacuous-when-empty: for every wp_id, an empty refs list is unconditionally appended to missing_requirement_refs_wps, and the function raises Exit(1) unless that list, unknown_requirement_refs, and unmapped_functional_requirements are ALL empty. It is called unconditionally at mission_finalize.py:1920, before any write.
- What actually satisfies it: _resolve_dependencies_and_refs (mission_finalize.py:485-533) reads WP frontmatter PRIMARY (empty, as above), then -- because wps_manifest is None (no wps.yaml for this mission, confirmed) and tasks.md exists -- falls back to _parse_requirement_refs_from_tasks_md (mission_parsing.py:64-109), which regex-matches any line starting "Requirement(s)? (Refs)?:" and pulls every FR|NFR|C-\d+ token out of it, with NO distinction between "this WP implements this ID" and "this WP merely names this ID in explanatory prose." This is the same citation-vs-declaration conflation ledger SK-14 already named for parse_requirement_ids_from_spec_md (fixed for spec.md by PR #3395) -- it was never fixed for this second, WP-level parser.
- Live reproduction (_resolve_dependencies_and_refs invoked directly against this checkout's current tasks.md + WP files) returns non-empty, fallback-derived refs for all 9 WPs, whose union covers all 9 declared functional requirements -- so _validate_requirement_mapping would in fact pass today, purely via this fallback. Concretely, WP02 is credited with FR-001 solely because its Requirement Refs: line reads "(behaviour-preserving prerequisite for WP06's FR-001 CLI wiring; ...)" -- an explanatory aside, not a declaration; WP02 implements no FR of its own.
- A second, distinct bug in the same fallback: its capturing regex (mission_parsing.py:100-101) has no DOTALL, so a Requirement Refs: value that wraps onto a second line (WP05's does, tasks.md:410-411) is silently truncated after the first line.
- Net effect: the canonical field is empty on disk; what looks like "full coverage" when the tool is asked comes from a parser reading citations as declarations. If finalize-tasks completes a write today (once F2 is cleared), it will concretize that wrong data -- e.g. write requirement_refs: [FR-001] into WP02 -- rather than the correct mapping already implied by tasks.md's own reviewed text.

Severity ruling: high. The mission's own carefully-produced, reviewed coverage record never reached the field the tooling and spec-kitty next's readiness gates actually consume, and the gate that should have caught the gap passes for the wrong reason.

Sanctioned remedy (do NOT hand-edit WP frontmatter): run spec-kitty agent tasks map-requirements to populate requirement_refs from the already-reviewed tasks.md Coverage Matrix (tasks.md:845-859) as the source of truth, BEFORE re-running finalize-tasks -- not after, since a finalize-tasks run today would otherwise write the fallback-parser's incorrect values first. F2 (below) must also be cleared, since it blocks finalize-tasks earlier in the pipeline regardless of F1's state.

The fallback parser's citation/declaration conflation (_parse_requirement_refs_from_tasks_md) and its DOTALL gap are themselves candidate defects in spec-kitty's own machinery, out of this mission's stated scope (FR-001 here targets spec.md's declared-id extraction, not this second, WP-level parser) -- flagged for a follow-up ledger entry, not fixed here.

### F2 -- finalize-tasks is currently blocked outright by an unrelated gate

Reproduced twice, live, on this exact checkout (spec-kitty agent mission finalize-tasks --mission bare-prose-requirements-uncounted-01KZYV3C --json, with and without --validate-only):

error: WP owned_files cannot include paths under kitty-specs/, error_code: INVALID_WP_OWNED_FILES_KITTY_SPECS, invalid_owned_files: WP01's two tracer file paths under kitty-specs/bare-prose-requirements-uncounted-01KZYV3C/.

Neither invocation touched disk (git status --porcelain empty after both runs) -- this gate fires (_validate_owned_files_not_in_mission_specs, mission_finalize.py:943-962) after _validate_requirement_mapping already passed via F1's fallback, but before any frontmatter flush. I could not reproduce a "result: success, updated_wp_count: 7" outcome on this checkout right now -- whatever produced commit 79516ee8e's frontmatter values, this exact command, run today, does not return success. WP01's history entry (unchanged by that commit) still reads "Prompt authored during tasks-authoring pass (not run via /spec-kitty.tasks)" for all 9 WPs, which is consistent with those bootstrap-shaped fields having been authored to imitate the tool's output rather than genuinely produced by it -- I could not confirm this either way from the artifacts alone, and it does not change F1's live-reproducible mechanism.

Severity ruling: high -- blocks the sanctioned finalize-tasks/map-requirements remedy path for F1 outright. WP01's owned_files needs correcting (or the gate needs an operator ruling) before F1's remedy can be executed.

### F3 -- plan.md self-contradicts its own Terminology Canon pass claim

plan.md line 4: "Input: Feature specification from kitty-specs/bare-prose-requirements-uncounted-01KZYV3C/spec.md" -- uses the charter-prohibited term "Feature" (C-004: "Mission," never "Feature"). plan.md line 90's own Charter Check section claims "PASS. Mission, never Feature (C-004)" for the same document. Root cause is the known-defective built-in template (ledger SK-11, packs/built-in/missions/software-dev/templates/plan-template.md line 4) -- this mission's plan.md inherited it verbatim rather than overriding it, and the R1-R6 gov lens (which owns terminology per the review overlay) did not catch it.

Severity ruling: medium -- a real, in-artifact terminology violation and a self-contradiction, but confined to one boilerplate line with no downstream code/behavior impact.

### Independent-discovery assessment

Would I have found F1/F2 without being pointed at them? Partial. A standard FR->WP frontmatter traceability check (comparing WP frontmatter requirement_refs against tasks.md's own Coverage Matrix) would have surfaced the symptom -- every WP's requirement_refs empty/absent next to a fully-populated Coverage Matrix -- on its own; that mismatch is the kind of thing a cross-artifact consistency pass is specifically for. I would NOT, on my own initiative, have traced it all the way into _resolve_dependencies_and_refs's tasks.md-text fallback, discovered the WP02 citation misattribution, or live-executed finalize-tasks to find F2 -- that required the specific direction to determine the mechanism from the code and reproduce it. F3 was found independently, via a routine terminology-canon grep during this pass, with no prior pointer.

### Other cross-artifact checks (no findings)

- Spec Requirements table (FR-001..FR-005, FR-007..FR-010, 9 functional; FR-006 legitimately removed by arbiter ruling -- confirmed present in reviews/spec.confirmed.yaml) matches tasks.md's Coverage Matrix and every WP's stated FR set 1:1.
- WP dependency graph (WP01:[], WP02:[WP01], WP03:[WP01], WP04:[], WP05:[WP01], WP06:[WP02], WP07:[WP03], WP08:[WP03], WP09:[WP02,WP03,WP05,WP06,WP08]) is acyclic and consistent between tasks.md and WP frontmatter (where present).
- plan.md's Gate Set section is concrete per-gate (triggered/not, floor/advisory, with reasons) -- meets the design-pipeline's "not 'we'll run the tests'" bar.
- Terminology elsewhere in spec.md/tasks.md (outside F3) correctly uses "Mission."
- No unknown/clean/silent-success language found describing this mission's own gate design -- the spec's Story 5/FR-007/FR-008/NFR-002 explicitly forbid the failure class this analyze pass is itself checking for.
