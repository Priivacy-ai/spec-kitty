---
work_package_id: WP05
title: 'Docs: docs/context/charter.md + a new mission-dossier contracts-authority update (NFR-002-safe relocation)'
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-009
planning_base_branch: fix/spdd-reasons-activation-split-brain-3838
merge_target_branch: fix/spdd-reasons-activation-split-brain-3838
branch_strategy: Planning artifacts for this mission were generated on fix/spdd-reasons-activation-split-brain-3838. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/spdd-reasons-activation-split-brain-3838 unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
history: []
agent_profile: scribe-sally
authoritative_surface: docs/context/
create_intent:
- kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/contracts-activation-authority-update.md
execution_mode: planning_artifact
model: ''
owned_files:
- docs/context/charter.md
- kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/contracts-activation-authority-update.md
role: documentarian
tags: []
tracker_refs: []
---

# WP05 — Correct the stated activation authority in `docs/context/charter.md`; relocate the contract-doc correction into this mission's own live dossier

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `scribe-sally`
- **Role**: `documentarian`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ READ THIS BEFORE STARTING — one tooling note (exemption path), one ruled tension (relocation, not escalation)

This WP's own file scope was investigated ahead of time (during tasks authoring) against two specific
hazards the mission brief named. Both investigations are recorded here so the implementer does not have to
rediscover them.

### 1. `finalize-tasks`'s `owned_files`-under-`kitty-specs/` rejection (ledger SK-146) — a real, working
   exemption path WAS found; use it, but confirm it live before trusting this note

`finalize-tasks` rejects any WP's `owned_files` entry rooted under `kitty-specs/` UNLESS the WP is
`execution_mode: planning_artifact` AND every one of its `owned_files` entries is confined to the
`kitty-specs/` or `docs/` prefix (`src/specify_cli/cli/commands/agent/mission_parsing.py`'s
`_is_confined_planning_wp`/`_invalid_mission_specs_owned_files`, read in full for this WP's authoring).
This WP's frontmatter is set accordingly: `execution_mode: "planning_artifact"`, and `owned_files` is
exactly `docs/context/charter.md` (under `docs/`) plus **this mission's own new
`contracts-activation-authority-update.md`** (under `kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/`
— this mission's own live dossier, not the frozen `spdd-reasons-doctrine-pack-01KQC4AX` archive) — no
`src/`/`tests/` path is mixed in, which is required for the exemption to apply (a mislabeled
`planning_artifact` WP that ALSO owns a non-planning path is NOT exempted, by design). **Re-run
`finalize-tasks --validate-only` live yourself (before you start editing) against this corrected
`owned_files` shape** — do not trust a prior round's result for the OLD `owned_files` shape (the two
frozen contract-doc paths), since the set has changed this round. If your own `--validate-only` run shows a
rejection, STOP and record what actually happened in
`kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/tracer-tooling-friction.md` (create it if
absent) rather than hand-editing `wps.yaml`/frontmatter to route around it.

### 2. `tests/architectural/test_archive_root_byte_identical.py` — RULED, not escalated: relocate, don't edit
   the frozen files

**Prior-round framing (superseded by the operator ruling, `reviews/tasks.ruling.md`):** an earlier version
of this WP instructed editing `kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/activation.md` and
`.../charter-context.md` directly and escalating the resulting `test_archive_root_byte_identical.py` CI red
to the operator as an unresolved tension between FR-009 and NFR-002. **That escalation is overruled.** The
operator ruling settles this from precedent: a sibling mission (`charter-authority-flip-01M14RB3`) hit the
identical trap and resolved it by ADDing new content under its OWN mission's archive dir
(`kitty-specs/charter-authority-flip-01M14RB3/`) rather than editing the frozen file — see this gate's own
module docstring, which documents the precedent directly: *"Editing an archived artifact to 'fix' a stale
line is forbidden... the correction belongs in the live mission dossier, not the archive."*

This architectural gate (module docstring: "Archive-root byte-identity gate... `kitty-specs/` — archived
mission dossiers... must not touch a single byte of any file that already existed under those roots at the
mission base") compares the working tree against a FIXED historical commit (`_MISSION_BASE_REV =
"fc4acaa897"`) and fails if any file that existed under `kitty-specs/` (among other roots) AT THAT REVISION
is modified — ADD-only is allowed, Modify or Delete of a pre-existing file is a real violation. **Confirmed
by direct `git show`**: both `kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/activation.md` and
`.../charter-context.md` ALREADY EXISTED at `fc4acaa897`, and neither is in this test's
`_APPEND_ONLY_SPINE_EXCEPTIONS` whitelist — so editing either one directly WOULD trip the gate.

**The corrected scope (T018 below) never touches either frozen file.** Both stay byte-identical to their
archived state; this WP does not read them for edit purposes at all beyond citation-checking the new
mission-dossier file's cross-reference pointers. The corrected activation-authority content that a prior
round would have written into those two contract docs is instead written to a NEW file — new path, never
existing before — under THIS mission's own live dossier
(`kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/contracts-activation-authority-update.md`, an ADD
relative to `_MISSION_BASE_REV`, so the gate never fires against this WP's own edits). **Do NOT resolve this
by**: editing `test_archive_root_byte_identical.py`'s exception list (out of this mission's file scope, and
belongs to a different mission's naming — extending it unilaterally is a real, undiscussed policy change);
or editing either frozen contract doc "just this once."

**What TO do (Subtask T018 below)**:
1. Run `pytest tests/architectural/test_archive_root_byte_identical.py -q` BEFORE committing this WP's work,
   against a `git status`/`git diff` that shows ZERO changes under
   `kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/` — confirm it passes clean. Under the
   corrected scope this test should never fire for this WP's own edits; a failure here means the scope was
   not followed and must be fixed before committing, not reported as an expected red.
2. Record the relocation decision (not an unresolved tension — a settled ruling) in
   `kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/tracer-tooling-friction.md` (create it if
   absent), naming the new file's path and the two frozen originals it supersedes/points to.

## Objective

Update `docs/context/charter.md`'s three glossary entries (plus add a new `activated_<kind>` entry) to
state the corrected, current activation authority (`activated_<kind>` via `PackContext`/INV-2 resolution)
instead of the stale `governance.yaml`/`directives.yaml`/`selected_<kind>`-as-sole-authority framing
(FR-009). The equivalent correction that FR-009 requires for `contracts/activation.md` and
`contracts/charter-context.md` is written to a NEW file under this mission's own live dossier —
`kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/contracts-activation-authority-update.md` — that
states the corrected facts and points back at the two frozen originals, per the operator ruling
(`reviews/tasks.ruling.md`): **restore any pre-existing archived file byte-identical and relocate the new
material into this mission's own live dossier**, mirroring the precedent
`tests/architectural/test_archive_root_byte_identical.py`'s own module docstring documents
(`charter-authority-flip-01M14RB3`, "the correction belongs in the live mission dossier, not the archive").
No ATDD test applies to this WP (SC-005 explicitly exempts docs from a red-first test) — verified by review
at PR time instead.

## Context

Both frozen contract docs (read in full for this WP's authoring — you still need to read them to know what
they currently say, even though you will not edit them) predate the IC-04 triad-retirement — they still
name `governance.yaml`/`directives.yaml` as the read target, files already retired independent of this
mission. `docs/context/charter.md` (frontmatter `doc_status: active`, `updated: '2026-08-28'` — the repo's
canonical, actively-maintained Terminology-Canon glossary) currently defines `selected_<kind>` as ITSELF the
activation mechanism in three places, with `activated_<kind>`/`PackContext` appearing nowhere in the
document — directly contradicting this mission's corrected premise (spec FR-009). `docs/context/charter.md`
is edited in place as before (T017, unchanged from prior rounds) — it is not under any frozen archive root
and NFR-002 does not apply to it.

**One-PR-shape note**: this WP is sequenced LAST (depends on WP01/WP02/WP03) specifically so the doc text
describes the FINAL, merged shape rather than an interim one (plan.md, "Phasing into Work Packages," WP5).
Do not start T017/T018 until you can read WP01/WP02/WP03's actual landed behavior, not merely this prompt's
description of intended behavior — re-verify against the live code one more time before writing the doc
prose, per this mission's own citation-discipline rule (it has HALTed twice on citation drift already).

### Markdown lint

`docs/context/charter.md` and the new mission-dossier file are both Markdown; `markdownlint-cli2` runs
against changed Markdown files (plan.md section f) — run it locally before finalizing if available, or at
minimum confirm your edits preserve the existing heading/table structure and do not introduce trailing
whitespace or inconsistent list markers.

## Subtask T017: `docs/context/charter.md` — 3 corrected entries + 1 new entry

**Purpose**: Correct the "Charter-Mediated Selection," "Global Selection," and "selected_&lt;kind&gt; /
required_&lt;kind&gt;" entries, and add a new `activated_<kind>` entry, per FR-009.

**Steps**:
1. **"Charter-Mediated Selection"** (currently, verified live: "Architectural pattern in which the project /
   org charter is the sole authority that decides which doctrine artifacts apply... Doctrine is the
   knowledge store; charter is the selector; runtime asks charter for the activated set rather than
   reaching into doctrine directly.") — this framing (charter as sole authority) is still broadly correct
   at the architectural level, but must be corrected to name `PackContext`/`activated_<kind>` as the
   MECHANISM by which the charter's activation decision is actually resolved today, not
   `selected_<kind>`/`governance.charter` alone. Add a sentence distinguishing the authoring record
   (`selected_<kind>`, what an interview/pack selected once) from the resolved activation authority
   (`activated_<kind>`, what `PackContext.from_config` resolves via the INV-2 two-file pointer chase) —
   cross-reference the new `activated_<kind>` entry (step 4).
2. **"Global Selection"** (currently: "Selection mode in which the charter declares an artifact is *always*
   active for every WP prompt regardless of action or mission type. Expressed via `selected_<kind>: [<id>,
   ...]` on the project charter or `required_<kind>: [<id>, ...]` on the org charter.") — this entry
   conflates "declares" with "activates." Correct it to state that `selected_<kind>`/`required_<kind>` are
   the AUTHORING/declaration surface, and that whether the declared artifact is actually delivered depends
   on the resolved `activated_<kind>` set (`PackContext`) — since (per this mission's own fix) `selected_*`
   is additive/unioned onto the `activated_*`-derived base in the surfaces this mission corrects
   (`resolve_project_governance`), not an independent activation source in its own right.
3. **"selected_&lt;kind&gt; / required_&lt;kind&gt;"** (currently defines the field-naming convention purely
   in terms of Global Selection, listing all eight `selected_*`/`required_*` field pairs) — keep the
   field-naming convention table (it is still accurate), but add a sentence clarifying these fields are the
   CHARTER-AUTHORED record, reclassified per this mission: not an independent activation source, but an
   additive project-local layer over the `activated_<kind>`-derived base (cross-reference the new
   `activated_<kind>` entry).
4. **New entry: `activated_<kind>`** — add a new glossary entry (matching the existing table format: |
   **Definition** | ... |, **Context**, **Status**, **Applicable to**, **Related terms** |) stating:
   the config/charter.yaml-resolved, three-state (`None` = all built-ins available / `[]` = explicit empty /
   non-empty = explicit set) per-kind activation authority, resolved via `PackContext.from_config`'s INV-2
   two-file pointer chase (`.kittify/config.yaml`, optionally pointing to `.kittify/charter/charter.yaml`).
   This is the field the compiler (`compile_charter`) and — after this mission — `is_spdd_reasons_active`,
   `_load_action_doctrine_bundle`, and `resolve_project_governance` all resolve activation from. Cross-link
   it from "Charter-Mediated Selection," "Global Selection," and "selected_&lt;kind&gt; /
   required_&lt;kind&gt;"'s **Related terms** rows.
5. Place the new entry adjacent to the three corrected entries (near line ~256-386 in the live file) so a
   reader moving through the section encounters the corrected concept immediately after the entries it
   corrects — re-verify the actual current line numbers before editing (this file may have shifted since
   this WP was authored).
6. Verify `updated:` frontmatter date is bumped to the date of this edit (Documentation structure /
   `docs-freshness-sla` doctrine — a page without a current freshness date is treated as stale).

**Files**: `docs/context/charter.md` (~4 entries touched/added, ~40-60 lines net)
**Validation**: Read the diff; confirm no other entry's cross-references were broken by the edit (grep for
`#global-selection`, `#charter-mediated-selection`, `#selected-kind--required-kind` elsewhere in the file
to confirm anchor text still matches if you changed any heading).

## Subtask T018: a NEW mission-dossier file supersedes/corrects the two frozen contract docs (neither is edited)

**Purpose**: FR-009 requires the activation-authority facts in `contracts/activation.md` and
`contracts/charter-context.md` to be corrected. Per the operator ruling, that correction is delivered by
ADDING a new file to this mission's own live dossier rather than editing either frozen contract doc (both
already existed at `test_archive_root_byte_identical.py`'s `_MISSION_BASE_REV`, so an edit to either is a
real NFR-002 violation — confirmed by `git show`, see the tooling note above).

**Do NOT edit, in this subtask or anywhere else in this WP**:
`kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/activation.md` or
`kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/charter-context.md`. Read both in full (you need
their current content to write the correction against), but do not open either in an editor with intent to
save a change. `git status`/`git diff` scoped to
`kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/` must show ZERO changes when this subtask is
done.

**Steps**:
1. Read both frozen contract docs in full (`kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/activation.md`,
   41 lines; `.../charter-context.md`, 33 lines) so the new file's corrections are grounded in what they
   currently, actually say — not a paraphrase from this prompt.
2. Create `kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/contracts-activation-authority-update.md`
   (a NEW path — this file must not already exist; if it does, something is wrong, stop and investigate
   rather than overwriting). Open with a short header stating plainly: this file supersedes/corrects the
   activation-authority facts in the two frozen contract docs below (link both by their real repo-relative
   paths) because those files are under a byte-frozen archive root
   (`tests/architectural/test_archive_root_byte_identical.py`) and cannot be edited directly; this file is
   the live, current-authority pointer a future reader should trust over the frozen originals for the facts
   named here.
3. Write the SAME corrected content a prior round would have put directly into
   `contracts/activation.md`'s **Failure modes**, **Performance**, and **Tests (acceptance table)**
   sections, each as its own clearly-labeled subsection of the new file, structured so a reader can tell
   which frozen section each subsection corrects:
   - **Failure modes** (corrects `contracts/activation.md`'s "Missing `.kittify/charter/`: returns `False`,"
     "Malformed governance.yaml: raises," "No paradigms section in governance.yaml: returns `False`" rows):
     name the ACTUAL source and failure modes per WP01's landed implementation — missing
     `.kittify/config.yaml` → `False` (FR-004's explicit, evidence-based carve-out — state it as
     deliberate, not full `PackContext` parity); malformed `.kittify/config.yaml` OR a dangling/malformed
     `charter:` pointer target → raises (FR-005); no `activated_*` keys present at all → `None` per-kind →
     treated as "all built-ins available" (per FR-001(d)) — a NEW failure-mode row relative to the frozen
     doc's "no paradigms section → False," since under `PackContext`'s three-state semantics an absent
     section is NOT the same outcome as an explicitly-empty one.
   - **Performance** (corrects `contracts/activation.md`'s "Reads at most two YAML files (`governance.yaml`,
     `directives.yaml`). Must complete in <50ms typical."): "Reads at most two YAML files
     (`.kittify/config.yaml`, and the pointed `.kittify/charter/charter.yaml` when INV-2's `charter:`
     pointer is present). Must complete in <50ms typical" — same file COUNT, corrected file NAMES.
   - **Tests (acceptance) table** (corrects `contracts/activation.md`'s 7-case table, which predates the
     three-state semantics): name the `.kittify/config.yaml`/`activated_*`-based fixture shape instead of
     the old unqualified "selected" framing, and add a row for the explicit-empty-vs-absent distinction
     (mirroring FR-002's fixture matrix / this mission's WP01 parity test).
4. Add an **Implementation seam** subsection (corrects `contracts/charter-context.md`'s "Implementation
   seam" section, which names the stale `src/doctrine/spdd_reasons/charter_context.py` +
   `src/charter/context.py`'s `_append_action_doctrine_lines()`): re-verify live, immediately before
   writing this section (it may have shifted since this prompt was authored), that the real function is
   `append_spdd_reasons_guidance(lines, mission, action)`, defined in
   `src/charter/offering/spdd_reasons/charter_context.py` and re-exported from
   `src/charter/offering/spdd_reasons/__init__.py`, with its real call site inside
   `src/charter/activation/context_renderers/bootstrap_text.py` (a module under
   `charter.activation.context_renderers`, not `src/charter/context.py`, which no longer contains this
   call). Name both the correct module path and the correct call site; prefer citing by symbol
   (`append_spdd_reasons_guidance`, `bootstrap_text.py`'s doctrine-bundle rendering block) over a bare line
   number, per this mission's citation-discipline rule.
5. Add a short **Unaffected by this mission** subsection noting: `contracts/charter-context.md`'s "Behavior
   change"/"Inactive guarantee" sections (the byte-identical-when-inactive contract, unaffected — a pure
   read-path fix, C-002) and "JSON shape (unchanged)" — re-verify the cited test file
   (`tests/charter/test_charter_context_spdd_reasons.py`) still contains the described "inactive baseline"
   fixture after WP04's triage (it should — WP04 does not remove `TestCharterContextInactive`) and state
   that confirmation in this subsection rather than silently assuming it.
6. Close with a short **Pointer** section repeating both frozen originals' paths and a one-line note that
   they remain byte-identical to their archived state by design (NFR-002) — this file is the corrected
   reading, not a replacement artifact that retires them.

**Files**: `kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/contracts-activation-authority-update.md`
(new, ~60-100 lines)
**Validation**: Read the new file's content against the live `activation.py`/`bootstrap_text.py` (or
wherever the seam actually lives now) to confirm it does not contradict shipped behavior — "a doc/code
disagreement is a doc defect" (charter, Documentation structure section) applies to this new file exactly
as it would to an edited one. Then run `git status`/`git diff` scoped to
`kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/` and confirm it is empty, and run
`pytest tests/architectural/test_archive_root_byte_identical.py -q` and confirm it passes clean — do this
BEFORE committing this WP's work, not after.

## Definition of Done

- `docs/context/charter.md`'s three named entries are corrected and a new `activated_<kind>` entry exists,
  cross-linked; `updated:` frontmatter bumped.
- `kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/contracts-activation-authority-update.md` exists
  (new file), states the corrected FR-004/FR-005 failure modes, performance section, acceptance-table
  shape, and implementation-seam citation that would otherwise have gone into `contracts/activation.md`/
  `contracts/charter-context.md`, and points back at both frozen originals by path.
- `kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/activation.md` and `.../charter-context.md` are
  BYTE-IDENTICAL to their state before this WP — confirmed via `git status`/`git diff` scoped to
  `kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/` showing zero changes.
- `pytest tests/architectural/test_archive_root_byte_identical.py -q` was actually run against this WP's
  finished diff and passes clean — not merely assumed, and not reported as an expected/known red.
- The SK-146 exemption path was confirmed live against the CORRECTED `owned_files` shape (the new
  mission-dossier path, not the two frozen contract-doc paths) via `finalize-tasks --validate-only` (or, if
  it behaved differently, the discrepancy was recorded in `tracer-tooling-friction.md`, not silently routed
  around).
- The relocation decision (new file supersedes the two frozen contract docs) is recorded in
  `tracer-tooling-friction.md`, naming the new file's path and the two originals it points back to.

## Risks

- **Silent drift-fix**: "correcting" a stale citation by guessing at the current line number instead of
  re-reading the live file reproduces this mission's own two prior citation-drift HALTs — always re-read
  before citing.
- **Editing a frozen file "just this once"**: touching either
  `kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/activation.md` or `.../charter-context.md`,
  even a whitespace-only or "obviously safe" edit, is a real NFR-002 violation this round exists to avoid —
  if you find yourself with an open diff against either file, stop and move that content into the new
  mission-dossier file instead.
- **Treating the archive-root gate itself as this WP's to fix**: editing
  `test_archive_root_byte_identical.py` or its exception list is explicitly OUT OF SCOPE for this WP.
- **Losing cross-references**: renaming or restructuring a glossary entry's heading without updating every
  other entry's `[Term](#anchor)` reference elsewhere in `docs/context/charter.md` silently breaks intra-doc
  navigation.

## Reviewer Guidance

- Confirm `tracer-tooling-friction.md` actually exists and actually names the relocation decision, with the
  new file's path and the two frozen originals it supersedes.
- Confirm `git status`/`git diff` scoped to `kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/`
  shows zero changes, and that the PR description states `test_archive_root_byte_identical.py` was run and
  passed — not reported as an expected/known CI red (that framing is superseded this round).
- Spot-check one or two citations in the new mission-dossier file against the live source they describe.
- Confirm this WP's `owned_files`/`execution_mode: planning_artifact` shape (the corrected set: `docs/
  context/charter.md` plus the new mission-dossier path) actually passed `finalize-tasks --validate-only`
  in practice (ask for the command output), not merely assumed from this prompt's SK-146 note.

Implementation command: `spec-kitty agent action implement WP05 --agent claude`
