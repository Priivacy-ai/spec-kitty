---
work_package_id: WP08
title: Reconcile records stranded under divergent paths
dependencies:
- WP01
- WP04
requirement_refs:
- FR-008
planning_base_branch: pr/review-verdict-write-integrity-01KZ1CGF
merge_target_branch: pr/review-verdict-write-integrity-01KZ1CGF
branch_strategy: Planning artifacts for this mission were generated on pr/review-verdict-write-integrity-01KZ1CGF. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/review-verdict-write-integrity-01KZ1CGF unless the human explicitly redirects the landing branch.
created_at: '2026-08-03T08:13:56Z'
subtasks:
- T035
- T036
- T037
- T038
- T039
agent: claude
history:
- at: '2026-08-03T08:13:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- src/specify_cli/cli/commands/_review_cycle_reconcile_doctor.py
- tests/architectural/census/verdict_seam_IC08.yaml
- tests/specify_cli/cli/commands/test_review_cycle_reconcile_doctor.py
- tests/architectural/test_verdict_seam_census.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/doctor.py
- src/specify_cli/cli/commands/_review_cycle_reconcile_doctor.py
- docs/api/cli-commands.md
- tests/architectural/census/verdict_seam_IC08.yaml
- tests/specify_cli/cli/commands/test_review_cycle_reconcile_doctor.py
- tests/architectural/test_verdict_seam_census.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP08 - Reconcile records stranded under divergent paths

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

## Objective

WP04 introduces `MissionArtifactKind.REVIEW_CYCLE` and moves review-cycle
artifacts onto the COORD partition under coordination topology (ADR
2026-08-03-1). WP13 (a later WP, not in this file) will subsequently **narrow**
the fan-out that today tolerates records living under multiple divergent
paths, resolving to exactly one location per WP. Between those two events sits
a real hazard this WP exists to close: **records already written under a path
WP13's narrowing will stop resolving must be found and reconciled before that
narrowing lands, or the merge gate opens a fail-open window** — a standing
rejection could silently become invisible to the gate the moment the fan-out
that used to (accidentally) find it is removed.

**This WP must land before WP13's narrowing.** That is not a scheduling
preference; it is the correctness property this WP's `dependencies` field
encodes and the reason FR-008 is P1 rather than P3 cleanup.

**"Retired path" is not this implementer's call.** FR-008 states it plainly:
*"'Retired path' is defined by the FR-007 census, not chosen by the
implementer."* WP01's census (the architectural check enumerating verdict
writers, location resolvers, and frontmatter readers) marks certain resolvers
`retire`. For **every** resolver the census marks `retire`, a reconciliation
pass must exist, and its test must seed a record at that specific resolver's
output *before* consolidation lands. **A reconciliation that finds nothing
because it was pointed at no resolver — or at the wrong one — is a census
failure, not a pass.** Do not write a reconciliation detector against a
guessed set of "likely stranded" paths; read WP01's actual census output and
build the detector against the resolvers it names.

**The migration shape is measured, and it is exception absorption, not an
empty-directory check.** From ADR 2026-08-03-1: 102 missions in this
repository carry review cycles; 45 of those declare a `coordination_branch` in
their `meta.json`; and of those 45, **zero still have that branch existing in
git** — `spec-kitty merge` deletes the mission branch, the coordination branch
*is* the mission branch, and nothing clears the stale `meta.json` key. The
seam (`coordination/surface_resolver.py`) therefore raises
`CoordinationBranchDeleted` **before any read happens**, for every one of
those 45 missions, unconditionally. This is fail-loud by contract
(`test_deleted_coord_branch_raises_fail_loud` pins it) — it is not a "read
finds nothing at the expected directory" case, and a reconciliation detector
built as an empty-directory check will never fire for any of these 45 real
missions. **The detector must catch and absorb `CoordinationBranchDeleted`
(and `StatusReadPathNotFound`) to reach the PRIMARY directory instead**, in
one owner function — not per consumer, and not inside the seam itself, which
resolves a directory per kind and never independently probes for artifact
existence.

## Context & Constraints

Read in full before starting:

- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/spec.md` — FR-008,
  User Story 3 (Acceptance Scenario 2), the Edge Cases section's "A pre-ADR
  mission has its review cycles on the primary surface" entry (the exact 45/0
  numbers restated).
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/plan.md` — IC-07
  ("Reconcile records stranded under divergent paths") and the "Resolved: the
  COORD/PRIMARY partition — ADR 2026-08-03-1" section's migration paragraph.
- `docs/adr/3.x/2026-08-03-1-review-cycle-artifacts-are-coord-partition.md` —
  the full "Migration: exception absorption, not empty-directory fallback"
  section, and "What the first draft got wrong" (the second row — "a read
  that finds nothing at COORD falls back to PRIMARY" is explicitly marked
  **False** as a characterization of the failure mode; do not reintroduce
  that misreading here).
- `src/specify_cli/coordination/surface_resolver.py` — read the module
  docstring (line ~34) and `CoordinationBranchDeleted`'s definition (line 181,
  subclassing `StatusReadPathNotFound`) and the raise site (line ~839). This
  is the exception this WP's reconciliation and doctor command must catch —
  trace exactly what triggers it and what information (mission id, expected
  branch name) it carries, since the doctor report should surface that detail
  to the operator, not just "reconciliation failed".
- `src/specify_cli/cli/commands/doctor.py` — **read the module docstring in
  full first.** It states explicitly: *"⚠️ ORCHESTRATION SHIM (#2059 de-godding
  complete — do NOT add new responsibilities here). ... New subcommand logic
  belongs in a sibling, not here; this file stays a thin shim of command
  shells + the re-export block."* This is binding, not advisory — the former
  ~3300 LOC god-module was deliberately decomposed and a mission exists
  tracking that decomposition (#2059). Follow the exact existing pattern:
  pick any existing sibling (e.g. `_coordination_doctor.py`, imported at
  `doctor.py` lines ~127-137, with its thin `@app.command(name="coordination")`
  shell at line ~1248) as your template. Your new subcommand gets:
  1. A new sibling module, `_review_cycle_reconcile_doctor.py`, owning all
     actual detection/reporting/fix logic.
  2. A thin `@app.command(name="...")` shell added to `doctor.py` that
     imports the sibling's entry-point function and does nothing but call it
     and handle the `--json` output convention (see `_json_output_guard`,
     imported from `_doctor_shared` at the top of `doctor.py`).
- `docs/api/cli-commands.md` — this is a **regenerated** reference document
  (5214 lines), not hand-authored prose. Locate the existing `doctor`
  subcommand entries (search for `## spec-kitty doctor <existing-subcommand>`
  headings, e.g. `coordination`, `sparse-checkout`) to find the pattern your
  new subcommand's entry must match, then find and run whatever generation
  command produces this file (check for a `regenerate`/`--check` command
  analogous to `spec-kitty doctrine regenerate-graph --check`, referenced
  around line 1927 of this same file, as a sibling example of the
  regenerate-into-temp-and-diff pattern this repo already uses elsewhere) —
  do not hand-edit this file's prose to add your entry if a generator owns it.
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/spec.md`'s
  **Definitions** section, "Affected suites" list — confirm whether your new
  test paths need explicit inclusion, or whether they fall under an existing
  glob already in scope.

**Constraints (binding)**:
- `doctor.py` gains **zero new logic** — only a thin `@app.command` shell plus
  the sibling-module import, exactly matching the existing decomposition
  pattern. Any detection, reconciliation, or reporting code you write that
  lands directly in `doctor.py` is a defect, not a stylistic preference.
- Do not build a second reconciliation mechanism duplicating the already-
  chartered but deferred `migrate backfill-runtime-state` CLI — before
  writing the detector, check whether that deferred command already covers
  this corpus (search for it in `src/specify_cli/` and any tracked issue
  referencing it) and record in this WP's Activity Log whether this is a
  genuinely distinct reconciliation target or an overlapping one that should
  instead extend that command.
- `docs/api/cli-commands.md` regeneration is a **required deliverable**, not
  an optional nice-to-have — the docs-freshness workflow's `REF-MISSING` check
  reds on a new, unnamed visible CLI path. The visible-count band is 222–272
  (baseline 247); adding one new subcommand brings the count to 248, which
  does **not** trip the band — confirm this arithmetic yourself against the
  live count rather than trusting this restated figure, since other WPs in
  this mission may also add visible surface concurrently.

## Subtask T035 — Build the reconciliation detector over the census's retired resolvers

- **Purpose**: Detect every verdict record living under a path WP01's census
  marks `retire`, so WP13's later narrowing does not silently orphan any of
  them.
- **Steps**:
  1. Read WP01's actual census output (the architectural check's produced
     artifact — `tests/architectural/census/verdict_seam_IC01.yaml` per
     plan.md's per-concern fragmentation scheme, or the check's own
     structured output if it emits one) and extract the list of resolvers
     marked `retire`, with their
     retiring FR cited (a `retire` row with no retiring FR is itself a census
     failure per WP01's own rules — if you find one, that is a WP01 defect to
     flag, not something to work around here).
  2. For each retired resolver, write a detection function in the new sibling
     module that: given a mission's `feature_dir`, computes what that
     specific (now-retired) resolver would have returned as a directory, and
     checks whether a review-cycle artifact exists there.
  3. Wrap each detection call in a handler that catches
     `CoordinationBranchDeleted` and `StatusReadPathNotFound` (imported from
     `specify_cli.coordination.surface_resolver`) and, on catching either,
     falls through to checking the **PRIMARY** directory instead — this is
     the exception-absorption mechanism the ADR requires, implemented once
     here, not per-resolver.
  4. Aggregate findings across all missions in the repository (or, for a
     single-mission invocation mode, across the target mission only — decide
     the CLI's invocation shape in T036 and make this function accept either
     scope) into a structured report: mission id, WP id, retired resolver
     name, resolved-fallback directory, and whether a record was actually
     found there.
- **Files**: `src/specify_cli/cli/commands/_review_cycle_reconcile_doctor.py`,
  `tests/specify_cli/cli/commands/test_review_cycle_reconcile_doctor.py`
- **Validation checklist**:
  - [ ] The detector's resolver list comes from WP01's census output, not a
        hand-typed guess — verified by importing/reading the census artifact
        directly, not by re-deriving it independently.
  - [ ] The detector catches `CoordinationBranchDeleted` and
        `StatusReadPathNotFound` and falls through to PRIMARY, rather than
        propagating the exception or treating "raises" as "not found".
  - [ ] A test seeds a record at a real, measured stranded case (the 45
        coord-topology, deleted-coordination-branch shape) and confirms the
        detector finds it via the fallback, not via a direct read.
  - [ ] A test seeds a mission with **no** stranded records and confirms the
        detector reports a clean result (no false positives from the
        exception-absorption path itself).
- **Edge Cases**: A resolver the census marks `retire` for a reason unrelated
  to the COORD/PRIMARY partition split (e.g., a bare-`wp_id` vs. `wp_slug`
  divergence, which plan.md's IC-09 risk note identifies as a *different*
  stranding cause than the ADR's partition migration) still needs a detector
  entry — do not scope this WP's detector to "only the ADR's partition-move
  cases" if the census names other retired resolvers too; FR-008 covers every
  census-named retired resolver, not only the partition one.

## Subtask T036 — Add the `doctor` subcommand shim and its sibling module

- **Purpose**: Expose T035's detector to an operator through the standard
  `spec-kitty doctor` surface, following the mandatory shim/sibling split.
- **Steps**:
  1. In `_review_cycle_reconcile_doctor.py`, add the public entry-point
     function `doctor.py`'s shell will call (match the naming convention of
     the existing siblings — e.g. `run_coordination_health` in
     `_coordination_doctor.py` — with a name like
     `run_review_cycle_reconciliation`), accepting `json_output: bool` and
     whatever scope/fix flags T037/T039 require.
  2. In `doctor.py`, add the import block following the exact pattern at
     lines ~127-137 (a comment naming this WP and what it extracts, then the
     `from ._review_cycle_reconcile_doctor import run_review_cycle_reconciliation`
     line).
  3. Add the thin `@app.command(name="review-cycle-reconcile")` shell (or
     whatever name reads best against the existing subcommand naming
     convention — check `coordination`, `sparse-checkout`, `identity` for the
     house style: short, hyphenated, noun-ish) that declares the CLI options
     (`--json`, `--fix` if T039 needs it, `--mission`/scope selector) and
     does nothing but call the sibling's entry point and print/return its
     result, matching `coordination_health`'s shell (`doctor.py` line ~1249)
     as the direct template.
  4. Confirm the new subcommand appears in `spec-kitty doctor --help` and
     `spec-kitty doctor review-cycle-reconcile --help` with sensible option
     descriptions.
- **Files**: `src/specify_cli/cli/commands/doctor.py`,
  `src/specify_cli/cli/commands/_review_cycle_reconcile_doctor.py`
- **Validation checklist**:
  - [ ] `doctor.py`'s diff adds only an import block and a thin
        `@app.command` shell — no detection/reporting logic.
  - [ ] `spec-kitty doctor review-cycle-reconcile --json` and the
        human-output form both work end-to-end against a real fixture repo.
  - [ ] The new subcommand's `--help` text is present and matches the house
        style of sibling subcommands.
- **Edge Cases**: If the sibling module needs anything from `merge.py` (the
  existing `_coordination_doctor.py` precedent notes a function-local import
  of `merge.path_is_under_worktrees` specifically to avoid a `doctor <->
  merge` module-load cycle, per its own docstring's H2/I-6 note) — apply the
  same function-local-import discipline here if an analogous need arises;
  do not hoist such an import to module scope.

## Subtask T037 — Absorb `CoordinationBranchDeleted` for the 45 stranded missions

- **Purpose**: This is the specific, measured migration case the ADR names —
  45 real missions in this repository, each with a `coordination_branch` key
  in `meta.json` pointing at a branch that no longer exists in git. This
  subtask is the exception-absorption mechanism's dedicated proof, distinct
  from T035's general detector plumbing.
- **Steps**:
  1. Reproduce the measured count yourself before writing the fix: scan the
     repository's `kitty-specs/*/meta.json` files for a populated
     `coordination_branch` key, and for each, check
     `git show-ref --verify --quiet refs/heads/<branch>` (or the equivalent
     via whatever git-ops helper this codebase already uses, e.g.
     `_has_branch_ref` in `merge/git_probes.py`) to confirm it's actually
     gone. Record your own reproduced count in this WP's Activity Log
     alongside the ADR's stated 45/0 — if your count differs, investigate
     why before proceeding (the repository may have changed since the ADR
     was written).
  2. Confirm the detector built in T035 correctly resolves each of these 45
     real missions to their PRIMARY directory via the exception-absorption
     path, and correctly reports whether a review-cycle record exists there.
  3. This subtask should not require any *new* absorption code beyond what
     T035 already built, if T035 was implemented against the general case
     correctly — treat a need for special-casing here as a signal that T035's
     detector was built too narrowly (e.g., only handling
     `CoordinationBranchDeleted` but not other permutations these 45 real
     missions might also exhibit — verify against the real corpus, not just
     synthetic fixtures).
- **Files**: `src/specify_cli/cli/commands/_review_cycle_reconcile_doctor.py`
  (verification/hardening only, if T035 needs it),
  `tests/specify_cli/cli/commands/test_review_cycle_reconcile_doctor.py` (the
  real-mission integration fixture required below)
- **Validation checklist**:
  - [ ] The reproduced 45/0 count (or your own updated count, with
        explanation if it differs) is recorded in this WP's Activity Log.
  - [ ] Running the doctor subcommand against this actual repository (not a
        synthetic fixture) reports on all 45 real missions without raising
        `CoordinationBranchDeleted` uncaught.
  - [ ] At least one of the 45 real missions is used as a literal integration
        test fixture (not merely synthesized), proving the absorption works
        against real, messy, historical data.
- **Edge Cases**: A mission among the 45 that has **since** been reconciled
  by some other means, or whose `meta.json` was hand-edited to remove the
  stale key — the detector must not crash on a mission that no longer
  exhibits the pattern; it should simply report "no stranded record found",
  which is a legitimate clean result, not a bug.

## Subtask T038 — Regenerate `docs/api/cli-commands.md`

- **Purpose**: The new `doctor review-cycle-reconcile` subcommand is new
  visible CLI surface; the docs-freshness workflow's `REF-MISSING` check reds
  if it is not reflected in the generated reference doc.
- **Steps**:
  1. Locate the generator that produces `docs/api/cli-commands.md` (search
     for a script or command target — check `Makefile`, `pyproject.toml`
     `[project.scripts]`, or a `docs/` build script; the file's own header/
     structure and the sibling `doctrine regenerate-graph --check` pattern at
     line ~1927 are your starting clues) rather than assuming none exists.
  2. Run it in its check/diff mode first (if one exists) to confirm the
     *current* file is stale only in the way you expect (missing your new
     subcommand), not for unrelated reasons that would indicate the doc was
     already out of sync before this WP touched anything.
  3. Regenerate the file for real and diff it — confirm the only change is
     the addition of your new subcommand's entry (plus any incidental
     reordering the generator itself performs, which is not this WP's
     concern to avoid).
  4. Confirm the resulting visible-subcommand count. The stated baseline is
     247, with a 222–272 tolerance band; verify the post-regeneration count
     against whatever check enforces that band (search for it in
     `tests/architectural/` or a docs-freshness test) and confirm it does not
     trip — do not simply trust the "248 does not trip" arithmetic stated in
     this mission's plan without checking it against the live count, since
     other WPs landing concurrently may also add visible surface.
- **Files**: `docs/api/cli-commands.md`
- **Validation checklist**:
  - [ ] The regeneration command (not a hand-edit) produced the diff.
  - [ ] The new subcommand's entry matches the format of neighboring
        `doctor` subcommand entries.
  - [ ] The docs-freshness / `REF-MISSING` check passes post-regeneration.
  - [ ] The visible-subcommand count is verified against the live count, not
        assumed from the plan's stated arithmetic.
- **Edge Cases**: If no automated generator can be found for this file after
  a genuine search, do not silently hand-edit 5214 lines of generated
  content — stop and record in this WP's Activity Log that the assumed
  generator does not exist or could not be located, and flag this as an
  upstream gap per this repository's "trace the source, file an upstream gap"
  discipline, rather than improvising a substitute that risks drifting from
  whatever mechanism actually owns this file.

## Subtask T039 — Report, never silently ignore, cross-branch coord records

- **Purpose**: FR-008's open question — "whether cross-branch records under
  coord topology are in scope" — is answered **yes** by the partition change
  (plan.md IC-07's risk note): pre-ADR records on PRIMARY under a coord
  mission are a *new* stranded class this WP owns, distinct from the
  45-missions/deleted-branch case. This subtask ensures the doctor command's
  final output makes every finding visible to the operator — never a silent
  count, never a swallowed exception, never a "0 found" that is actually "the
  detector didn't look".
- **Steps**:
  1. Confirm the detector (T035) also covers the case where a **currently
     live** coord-topology mission has a review-cycle record sitting on
     PRIMARY from before the ADR landed (i.e., the coordination branch still
     exists, so `CoordinationBranchDeleted` is never raised for this case —
     it's a genuinely different code path than T037's absorption case, and
     needs its own explicit check: does a PRIMARY-side record exist for a WP
     whose mission is coord-topology and whose coord branch is alive and
     well?).
  2. Ensure the doctor command's report format names every finding
     explicitly — mission id, WP id, which stranded class it falls under
     (deleted-coord-branch absorption, vs. live-coord-branch-but-pre-ADR-
     PRIMARY-record), and the resolved directory where the record actually
     lives.
  3. Under `--json`, ensure the full finding list is present in the payload
     (not summarized to a bare count) — mirror whatever existing doctor
     subcommand's `--json` shape (e.g. `_json_output_guard`'s convention) is
     closest to this report's shape.
  4. Add a `--fix` mode only if T036's design calls for one and the fix is
     genuinely safe (e.g., copying the stranded record to the resolved
     target directory) — if a safe automatic fix is not obviously correct
     (e.g., because two divergent copies both exist and need operator
     judgment about which wins), the command should default to report-only
     and require an explicit flag, never silently "fix" by discarding data.
- **Files**: `src/specify_cli/cli/commands/_review_cycle_reconcile_doctor.py`,
  `tests/specify_cli/cli/commands/test_review_cycle_reconcile_doctor.py`
- **Validation checklist**:
  - [ ] A test seeds a live-coord-branch, pre-ADR PRIMARY record and confirms
        the detector reports it (this is the T039-specific case, distinct
        from T037's deleted-branch case).
  - [ ] A test confirms `--json` output includes the full per-finding detail,
        not a bare count.
  - [ ] If `--fix` exists, a test confirms it never overwrites/discards data
        without an explicit opt-in when two divergent records both exist.
- **Edge Cases**: A mission with **both** stranded classes present
  simultaneously for different WPs (some WPs stranded via the
  deleted-coord-branch path, others via the live-coord-branch pre-ADR path)
  — the report must correctly classify each finding independently, not
  collapse them into one undifferentiated "stranded" bucket that would make
  T037's specific migration story unverifiable from the report alone.

## Branch Strategy

Planning artifacts for this mission were generated on
`pr/review-verdict-write-integrity-01KZ1CGF`. This WP depends on WP01 (the
verdict-seam census) and WP04 (the `REVIEW_CYCLE` kind and partition
plumbing) and branches from their landed base. Completed changes merge back
into `pr/review-verdict-write-integrity-01KZ1CGF` unless the human explicitly
redirects the landing branch — and this WP must land **before** WP13, per the
sequencing risk stated throughout this file.

## Definition of Done

- The reconciliation detector's resolver set is derived from WP01's actual
  census output, not a hand-guessed list.
- `CoordinationBranchDeleted` and `StatusReadPathNotFound` are caught and
  absorbed to PRIMARY in one owner function, proven against the real,
  measured 45-mission corpus (or an honestly-updated count, recorded in the
  Activity Log if it differs from the ADR's stated figure).
- The `doctor.py` diff is a thin shim addition only — no detection/reporting
  logic landed directly in that file.
- The new sibling module (`_review_cycle_reconcile_doctor.py`) owns all
  actual logic and is independently tested by
  `tests/specify_cli/cli/commands/test_review_cycle_reconcile_doctor.py`, this
  WP's own owned test module.
- The live-coord-branch, pre-ADR PRIMARY record case (T039) is detected and
  reported distinctly from the deleted-coord-branch absorption case (T037).
- `docs/api/cli-commands.md` is regenerated (via its actual generator, not
  hand-edited) and the docs-freshness / `REF-MISSING` check passes.
- The visible-subcommand count is verified against the live band, not
  assumed.
- `mypy --strict` and `ruff` clean; ≥90% diff-coverage on new code.
- [ ] **NFR-002** — every function this WP touches ends at cyclomatic complexity ≤15: `uv run ruff check --select C901 <touched files>` is clean. Extract helpers rather than leaving a function at 16+.

## Risks & Mitigations

- **Reconciliation pointed at the wrong resolver set**: FR-008 explicitly
  calls this failure mode "a census failure, not a pass." Mitigate by
  building the detector directly from WP01's produced census artifact, with
  a test that would fail if the census's retired-resolver list and this WP's
  detector's coverage ever diverge.
- **Empty-directory-check misreading**: the first draft of the governing ADR
  itself made this exact mistake ("a read that finds nothing at COORD falls
  back to PRIMARY") and was corrected by a second adversarial pass. Mitigate
  by explicitly testing the exception-absorption path against real
  `CoordinationBranchDeleted`-raising fixtures, not synthetic "directory
  doesn't exist" ones — the two look similar but are not the same code path.
- **`doctor.py` scope creep**: the temptation to add "just one helper
  function" directly to the shim file, given how much detection logic this
  WP needs, is real. Mitigate by treating the module docstring's "do NOT add
  new responsibilities here" as a hard gate, checked at review time by
  diffing `doctor.py` in isolation.
- **Silent docs staleness**: skipping the regeneration step (or hand-editing
  instead of running the generator) produces a file that looks plausible but
  drifts from whatever the generator would have actually produced, and fails
  the freshness check downstream, possibly attributed to an unrelated WP.
- **Sequencing violation**: if this WP lands after WP13's narrowing instead of
  before it, the fail-open window it exists to close opens for real, even
  briefly. Flag any indication that implementation order is being reshuffled
  away from this WP's `dependencies`/sequencing before proceeding.

## Reviewer Guidance

- Confirm the detector's resolver list is traced to WP01's actual census
  output, not to this WP's own reading of plan.md's prose.
- Confirm at least one test uses a real fixture reproducing
  `CoordinationBranchDeleted` (not a mocked "returns empty" stand-in) for the
  absorption path.
- Confirm `doctor.py`'s diff is genuinely thin — flag any detection/reporting
  logic that landed there instead of in the sibling module.
- Confirm the two stranded classes (deleted-coord-branch vs.
  live-coord-branch-pre-ADR-PRIMARY-record) are both covered and
  independently tested, not conflated.
- Confirm `docs/api/cli-commands.md` was regenerated via its real generator
  (ask to see the generation command's output/diff) rather than hand-edited.
- Confirm this WP's Activity Log records the reproduced 45/0 count (or an
  honest update if it differs) rather than only citing the ADR's number.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-03T08:13:56Z – system – lane=planned – Prompt created.

---

### Updating Lane Status

Use: `spec-kitty agent tasks move-task WP08 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
