---
work_package_id: WP05
title: 'Docs: contracts/activation.md, contracts/charter-context.md, docs/context/charter.md'
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
create_intent: []
execution_mode: planning_artifact
model: ''
owned_files:
- docs/context/charter.md
- kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/activation.md
- kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/charter-context.md
role: documentarian
tags: []
tracker_refs: []
---

# WP05 — Correct the stated activation authority in docs and contract files

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `scribe-sally`
- **Role**: `documentarian`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ READ THIS BEFORE STARTING — TWO REAL TOOLING TENSIONS FOUND FOR THIS WP, NEITHER SILENTLY RESOLVED

This WP's own file scope was investigated ahead of time (during tasks authoring) against two specific
hazards the mission brief named. **Both investigations are recorded here so the implementer does not have
to rediscover them, and BOTH must be surfaced again in the PR description — do not silently work around
either.**

### 1. `finalize-tasks`'s `owned_files`-under-`kitty-specs/` rejection (ledger SK-146) — a real, working
   exemption path WAS found; use it, but confirm it live before trusting this note

`finalize-tasks` rejects any WP's `owned_files` entry rooted under `kitty-specs/` UNLESS the WP is
`execution_mode: planning_artifact` AND every one of its `owned_files` entries is confined to the
`kitty-specs/` or `docs/` prefix (`src/specify_cli/cli/commands/agent/mission_parsing.py`'s
`_is_confined_planning_wp`/`_invalid_mission_specs_owned_files`, read in full for this WP's authoring).
This WP's frontmatter is set accordingly: `execution_mode: "planning_artifact"`, and `owned_files` is
exactly `docs/context/charter.md` (under `docs/`) plus the two contract docs (under `kitty-specs/`) — no
`src/`/`tests/` path is mixed in, which is required for the exemption to apply (a mislabeled
`planning_artifact` WP that ALSO owns a non-planning path is NOT exempted, by design). **The tasks-authoring
session ran `finalize-tasks --validate-only` against exactly this shape and confirmed it does NOT reject
these `owned_files` entries** — see this mission's own `tasks/` authoring report for the observed command
output. If your own `--validate-only` run (before you start editing) shows a DIFFERENT result than that,
STOP and record what actually happened in
`kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/tracer-tooling-friction.md` (create it if
absent) rather than hand-editing `wps.yaml`/frontmatter to route around it.

### 2. `tests/architectural/test_archive_root_byte_identical.py` — a REAL, CONFIRMED conflict with FR-009,
   NOT resolved by this WP, escalate to the operator

This architectural gate (module docstring: "Archive-root byte-identity gate... `kitty-specs/` — archived
mission dossiers... must not touch a single byte of any file that already existed under those roots at the
mission base") compares the working tree against a FIXED historical commit (`_MISSION_BASE_REV =
"fc4acaa897"`, from an unrelated mission, `charter-authority-flip-01M14RB3`) and fails if any file that
existed under `kitty-specs/` (among other roots) AT THAT REVISION is modified — ADD-only is allowed, Modify
or Delete of a pre-existing file is a real violation. **Confirmed by direct `git show` for this WP's
authoring**: both `kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/activation.md` and
`.../charter-context.md` ALREADY EXISTED at `fc4acaa897`, and neither is in this test's
`_APPEND_ONLY_SPINE_EXCEPTIONS` whitelist (which names exactly one file, an unrelated rename-reconcile
spine). **This means FR-009's required edits to these two contract docs WILL trip
`test_archive_root_byte_identical.py` in CI's always-on architectural pole** — even though this test is
NOT one of the two named architectural gates this mission's own NFR-005/plan.md section (f) scopes local
verification to, it still runs unconditionally on every PR (per its own header: "the always-on
arch-adversarial job on EVERY push/PR regardless of path").

**Do NOT resolve this tension yourself by**: editing `test_archive_root_byte_identical.py`'s exception list
(out of this mission's file scope, and belongs to a different mission's naming — extending it unilaterally
is a real, undiscussed policy change); silently dropping the two contract-doc edits from FR-009's scope;
or silently proceeding as if the conflict doesn't exist.

**What TO do**: make the edits FR-009 requires (Subtask T018 below) so the mission's actual documentation
deliverable is real and reviewable, but:
1. Record this finding in `kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/tracer-tooling-friction.md`
   (create it if absent — this file is explicitly not one of the four NFR-002 immutable roots, and per this
   mission's own Standing Order #3 the friction itself is what gets recorded here even though tracer files
   are normally orchestrator-seeded).
2. State plainly in the PR description that `test_archive_root_byte_identical.py` is expected to fail (or
   already known to fail, if you run it locally and confirm) against this mission's diff specifically
   because of these two contract-doc edits, and that this is a genuine, unresolved tension between FR-009
   (which requires the edits) and NFR-002's archive-root freeze (which forbids them) that needs an operator
   decision — NOT a mistake to quietly fix by picking a side.
3. Do not mark this WP's CI as unconditionally green if this specific test fails for this specific reason —
   name it explicitly as the one known, expected red, distinct from any other regression.

## Objective

Update `contracts/activation.md`, `contracts/charter-context.md`, and `docs/context/charter.md`'s three
glossary entries (plus add a new `activated_<kind>` entry) to state the corrected, current activation
authority (`activated_<kind>` via `PackContext`/INV-2 resolution) instead of the stale `governance.yaml`/
`directives.yaml`/`selected_<kind>`-as-sole-authority framing (FR-009). No ATDD test applies to this WP
(SC-005 explicitly exempts docs from a red-first test) — verified by review at PR time instead.

## Context

Both contract docs (read in full for this WP's authoring, see excerpts below) predate the IC-04
triad-retirement — they still name `governance.yaml`/`directives.yaml` as the read target, files already
retired independent of this mission. `docs/context/charter.md` (frontmatter `doc_status: active`, `updated:
'2026-08-28'` — the repo's canonical, actively-maintained Terminology-Canon glossary) currently defines
`selected_<kind>` as ITSELF the activation mechanism in three places, with `activated_<kind>`/`PackContext`
appearing nowhere in the document — directly contradicting this mission's corrected premise (spec FR-009).

**One-PR-shape note**: this WP is sequenced LAST (depends on WP01/WP02/WP03) specifically so the doc text
describes the FINAL, merged shape rather than an interim one (plan.md, "Phasing into Work Packages," WP5).
Do not start T018 until you can read WP01/WP02/WP03's actual landed behavior, not merely this prompt's
description of intended behavior — re-verify against the live code one more time before writing the doc
prose, per this mission's own citation-discipline rule (it has HALTed twice on citation drift already).

### Markdown lint

Both contract docs and `docs/context/charter.md` are Markdown; `markdownlint-cli2` runs against changed
Markdown files (plan.md section f) — run it locally before finalizing if available, or at minimum confirm
your edits preserve the existing heading/table structure and do not introduce trailing whitespace or
inconsistent list markers.

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

## Subtask T018: `contracts/activation.md` and `contracts/charter-context.md`

**Purpose**: Update both contract docs to state the new source of truth and the new failure modes
(FR-004/FR-005), per FR-009.

**Steps — `kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/activation.md`** (41 lines, read in
full for this WP's authoring):
1. **Output section** — unchanged in substance (the four-selector disjunction is still correct); no edit
   needed unless WP01's final implementation changed the selector set (it should not have — FR-001/Decision
   Record 1 preserve the four selectors verbatim).
2. **Failure modes section** — currently states "Missing `.kittify/charter/`: returns `False`," "Malformed
   governance.yaml: raises," "No paradigms section in governance.yaml: returns `False`." Rewrite to name
   the ACTUAL new source and failure modes per WP01's implementation: missing `.kittify/config.yaml` →
   `False` (FR-004's explicit, evidence-based carve-out — state it as deliberate, not full `PackContext`
   parity); malformed `.kittify/config.yaml` OR a dangling/malformed `charter:` pointer target → raises
   (FR-005); no `activated_*` keys present at all → `None` per-kind → treated as "all built-ins available"
   (matching the disjunction's own "selector satisfied" semantics for an absent key, per this mission's
   FR-001(d)) — this is a NEW failure-mode row relative to the old contract's "no paradigms section →
   False," since under `PackContext`'s three-state semantics an absent section is NOT the same outcome as
   an explicitly-empty one.
3. **Performance section** — currently "Reads at most two YAML files (`governance.yaml`, `directives.yaml`).
   Must complete in <50ms typical." Rewrite: "Reads at most two YAML files (`.kittify/config.yaml`, and the
   pointed `.kittify/charter/charter.yaml` when INV-2's `charter:` pointer is present). Must complete in
   <50ms typical" — same file COUNT, corrected file NAMES.
4. **Tests (acceptance) table** — rewrite each "Charter selection" column entry to name the
   `.kittify/config.yaml`/`activated_*`-based fixture shape instead of an unqualified "selected" framing;
   add a new row for the explicit-empty-vs-absent distinction (mirroring FR-002's fixture matrix / this
   mission's WP01 parity test) since the old table's 7 cases predate the three-state semantics entirely.

**Steps — `kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/charter-context.md`** (33 lines, read
in full for this WP's authoring):
1. **"Implementation seam" section** — currently names `src/doctrine/spdd_reasons/charter_context.py` as
   the helper's home and `src/charter/context.py`'s `_append_action_doctrine_lines()` (line 537) as the call
   site. **Already re-verified for this WP's authoring, live**: the real function is
   `append_spdd_reasons_guidance(lines, mission, action)`, defined in
   `src/charter/offering/spdd_reasons/charter_context.py:59` and re-exported from
   `src/charter/offering/spdd_reasons/__init__.py`. Its real call site is
   `src/charter/activation/context_renderers/bootstrap_text.py:333` (inside a module under
   `charter.activation.context_renderers`, not `src/charter/context.py` — that file/module no longer
   exists at that path or does not contain this call). Update the contract to name both the correct module
   path and the correct call site — re-confirm the exact line number one more time immediately before
   editing (it may have shifted again since this note was written), and prefer citing by symbol
   (`append_spdd_reasons_guidance`, `bootstrap_text.py`'s doctrine-bundle rendering block) over a bare line
   number where possible, per this mission's citation-discipline rule.
2. **"Behavior change"/"Inactive guarantee" sections** — the byte-identical-when-inactive contract is
   unaffected by this mission (a pure read-path fix, C-002) and needs no substantive change, but re-verify
   the cited test file (`tests/charter/test_charter_context_spdd_reasons.py`) still contains the described
   "inactive baseline" fixture after WP04's triage — it should (WP04 does not remove
   `TestCharterContextInactive`).
3. No change needed to "JSON shape (unchanged)" or "Performance" sections unless WP01/02/03's actual
   implementation changed a budget number (it should not have).

**Files**: `kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/activation.md` (~20-30 lines edited),
`kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/charter-context.md` (~5-10 lines edited)
**Validation**: Read the diff against the live `activation.py`/`context.py` (or wherever the seam actually
lives now) to confirm the doc no longer contradicts shipped behavior — "a doc/code disagreement is a doc
defect" (charter, Documentation structure section).

## Definition of Done

- `docs/context/charter.md`'s three named entries are corrected and a new `activated_<kind>` entry exists,
  cross-linked; `updated:` frontmatter bumped.
- `contracts/activation.md` and `contracts/charter-context.md` no longer name the retired
  `governance.yaml`/`directives.yaml` files as the read target, and state FR-004/FR-005's actual failure
  modes.
- The SK-146 exemption path was confirmed live (or, if it behaved differently, the discrepancy was recorded
  in `tracer-tooling-friction.md`, not silently routed around).
- The `test_archive_root_byte_identical.py` conflict is recorded in `tracer-tooling-friction.md` and stated
  explicitly in the PR description as an unresolved, operator-facing tension — not silently fixed or
  silently ignored.

## Risks

- **Silent drift-fix**: "correcting" a stale citation by guessing at the current line number instead of
  re-reading the live file reproduces this mission's own two prior citation-drift HALTs — always re-read
  before citing.
- **Treating the archive-root conflict as this WP's to resolve**: editing `test_archive_root_byte_identical.py`
  or its exception list is explicitly OUT OF SCOPE for this WP — flag, do not fix.
- **Losing cross-references**: renaming or restructuring a glossary entry's heading without updating every
  other entry's `[Term](#anchor)` reference elsewhere in `docs/context/charter.md` silently breaks intra-doc
  navigation.

## Reviewer Guidance

- Confirm `tracer-tooling-friction.md` actually exists and actually names the archive-root gate conflict,
  with the exact test file path and the exact two contract-doc paths.
- Confirm the PR description states the expected `test_archive_root_byte_identical.py` failure explicitly,
  distinct from any other CI red.
- Spot-check one or two citations in the rewritten contract docs against the live source they describe.
- Confirm this WP's `owned_files`/`execution_mode: planning_artifact` shape actually passed
  `finalize-tasks --validate-only` in practice (ask for the command output), not merely assumed from this
  prompt's SK-146 note.

Implementation command: `spec-kitty agent action implement WP05 --agent claude`
