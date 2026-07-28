---
work_package_id: WP02
title: Ledger grammar, per-site index, and the read-side gate's terminal shape
dependencies: []
requirement_refs:
- FR-008
- FR-009
- FR-010
- FR-012
- FR-016
- FR-017
- FR-024
- NFR-004
- NFR-006
- NFR-008
planning_base_branch: fix/read-side-seam-primary-primitive-closure
merge_target_branch: fix/read-side-seam-primary-primitive-closure
branch_strategy: Planning artifacts for this mission were generated on fix/read-side-seam-primary-primitive-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/read-side-seam-primary-primitive-closure unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-read-side-seam-primary-primitive-closure-01KYKMMT
base_commit: 40fa5440891edc2957edd39e8815ab8765e1cea8
created_at: '2026-07-28T10:23:59.818094+00:00'
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
- T014
phase: Phase 1 - State the destination
history:
- at: '2026-07-28T09:27:08Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: docs/development/read-side-seam-classification.md
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- docs/development/read-side-seam-classification.md
- tests/architectural/test_no_read_side_bypass.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '3014'
---

# Work Package Prompt: WP02 – Ledger grammar, per-site index, and the gate's terminal shape

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---


## Objective

Two jobs, in this order:

1. **Make the ledger safe to extend.** Its parse is positional and heading-exact. The
   restructuring originally prescribed for multi-primitive rows was **executed** against the
   real parser and shown to read only the **first** table under a parsed heading — the second
   primitive's rows vanish while the reconciliation test stays **green**. That is a silently
   vacuous gate, the exact failure a previous landing pass had to repair on this same gate.
   Grammar comes before rows (C-009, hard gate).
2. **Census and classify the one resolver no gate covers** — `resolve_feature_dir_for_mission`,
   8 sites / 7 files — and land the read-side gate's **terminal** shape so every later WP only
   *satisfies* it and never edits it.

You are the **sole owner** of `docs/development/read-side-seam-classification.md` and
`tests/architectural/test_no_read_side_bypass.py` for the whole mission. Land their end state
here.

## ⚠ This WP deliberately leaves the census red

Growing the censused callees to their terminal set (T011) means the gate begins flagging the
~34 in-flight `primary_feature_dir_for_mission` sites — they are not routed yet. **That red is
the acceptance signal** (US8 / FR-023), not a defect, and WP08 is what greens it. Record it,
do not soften the gate to avoid it, and do **not** pre-populate 34 allow-list entries you
intend to delete (the allow-list is shrink-only; that would invert the ratchet).

## Context & Constraints

- **C-009 (hard gate)**: no classification row for a newly censused primitive may be written
  until T008/T009/T010 hold. See [contracts/ledger-grammar.md](../contracts/ledger-grammar.md)
  — it is binding, not advisory.
- **C-002**: one ledger, extended. No second authority document.
- **C-003**: allow-list entries are **per-site content descriptors**. No path-scoped blankets.
- **NFR-008**: reconciliation covers the **live residual/lenient** totals per primitive — the
  figures the gate parses — **not** the historical pre-migration totals, which are preserved
  and labelled as an audit record. Never rewrite a historical figure to satisfy a check.
- **NFR-006**: the gate keeps consuming the shared whole-tree scan scope. Do not fork a second
  scanner.
- The pinned scan-scope **prefix set is frozen** (C-005/FR-019 exclusions): seam-internal sites
  under it cannot be brought into scope. Accountability there is a per-file rationale plus the
  per-primitive non-vacuity assertion.

## Doctrine for this WP

- **`tactic:architectural-gate-non-vacuity`** — its four elements, **verbatim**: **concrete
  floor · self-mutation test · shrink-only allowlist · routed-count floor**. Its named failure
  mode "vacuous gate" is precisely what the executed ledger restructuring produced.
  `Run: spec-kitty charter context --include tactic:architectural-gate-non-vacuity`
  **When doing T010 and T011**, check your work against those four **as named** — do not
  substitute softer paraphrases. This census is where WP01's retired *routed-count floor* and
  *shrink-only allowlist* land, so all four must be live here or WP01's retirement is an
  unguarded relaxation.
- **`DIRECTIVE_043`** — `enforcement: required`. A gate that trivially passes at zero relevant
  call sites is non-compliant; it must have a concrete floor.
  `Run: spec-kitty charter context --include directive:DIRECTIVE_043`
  **When doing T011**, this is the receiving end of WP01's floor retirement: the guarantee
  transfers *here*, so this census must carry its own concrete floor. If it does not, WP01's
  retirement becomes an unguarded relaxation.
- **`DIRECTIVE_041`** — also prescribes anchoring ratchet keys on **qualname + normalised
  token, never `file.py:NNN`**, which is exactly T009's discriminator design.
  `Run: spec-kitty charter context --include directive:DIRECTIVE_041`
  **When doing T009**, do not key the index on a line number — it drifts on every unrelated
  edit and produces exactly the stale references T014 is cleaning up.
- **`tactic:frozen-baseline-shrink-only-ratchet`** — growth fails, shrink warns, movement needs
  an inline justification with before→after and a tracker ref.
  `Run: spec-kitty charter context --include tactic:frozen-baseline-shrink-only-ratchet`
  **When doing T011/T013** (allow-list and staleness twin-guard).
- **`tactic:canonical-source-unification`** — one authority; step 5: *"do not leave a
  non-canonical copy as a fallback — fallbacks revive the split-brain silently."*
  `Run: spec-kitty charter context --include tactic:canonical-source-unification`
  **When doing T013/T014**, resist adding a second summary table "for clarity" — that is the
  fallback shape, and the parser reads only the first one.

## Subtasks

### T008 — Constrain the ledger's machine-parse grammar (FR-008)

**Purpose**: make a multi-primitive ledger structurally unable to parse silently-empty.

**Normative rules** (from [contracts/ledger-grammar.md](../contracts/ledger-grammar.md) G1 —
each prevents a specific silent failure):

| Rule | Failure it prevents |
|---|---|
| Exactly **one** table under each machine-parsed heading | the second table is silently dropped |
| Parsed headings kept **verbatim** (located by exact full-line match) | section not found → parses empty |
| Verdict / `rel_path` / `qualname` stay at their **current leading column positions** | positional readers silently skip or mis-read rows |
| A `primitive` discriminator **appended as a trailing column** | a leading/middle insertion breaks the positional contract; appending fails loudly if mis-specified |
| No duplicate key within a counts table | duplicate keys overwrite silently, last-wins |
| Non-numeric cells in count columns are an **error**, not a skip | silent row skipping |

**Steps**: read the markdown-table reader and the summary-count parser in
`test_no_read_side_bypass.py` first — the grammar is whatever they actually accept. Then shape
the ledger sections to comply, and make each rule above **enforced** rather than merely
documented.

**Validation**: append a second table under a parsed heading in a scratch copy → the gate
**reds** (today it silently ignores it). Insert a column mid-table → reds.

### T009 — Give the stay-lenient index a per-site discriminator (FR-009)

**Purpose**: the index is keyed per **site**, not per function, and must address several
censused sites inside one qualname. A known case carries **four** —
`status/aggregate.py::_find_meta_path` — one existing primitive plus three of the newly
censused one. That is your acceptance fixture (SC-015).

**Steps**:
1. Add the discriminator: trailing `primitive` + site token, or an equivalent composite. Anchor
   on **qualname + normalised token**, never a line number (`DIRECTIVE_041`).
2. Update the **uniqueness assertion in the same change** — otherwise it reds by construction.
3. Coordinate the spelling with WP07, which routes that module: it must be able to express
   those four sites without inventing a second convention.

**Validation**: the four-site qualname is representable and the uniqueness assertion passes.

### T010 — Add the two assertions that make the grammar enforceable (NFR-004)

Without these, T008 is documentation.

1. **Row-count reconciliation** — parsed row count **equals** the summed per-primitive census.
   A dropped table or shifted column then reds *loudly* instead of parsing empty.
2. **Per-primitive mutation** — mutating a row belonging to **each** primitive independently
   MUST red. A single-primitive mutation test passes happily while a second primitive is
   entirely unenforced — that is the vacuity being closed.
3. **Counts scoping** (NFR-008) — reconciliation covers the **live residual/lenient** totals.
   Preserve the historical pre-migration figures, **labelled as an audit record**.
   **Resolve the "live" ambiguity explicitly: the parsed count columns carry the POST-MIGRATION
   END STATE.** "Live" is ambiguous between as-of-WP02 (≈30 unrouted primary sites) and
   end-state (0), and the two have opposite consequences. As-of-WP02 counts go green now and red
   the moment WP05 lands — with no owner able to fix them, since WP05–WP07 may not edit
   `tests/architectural/` and the ledger is not in WP08's map. So write end-state counts,
   record the resulting reconciliation red in your `## WP02` section of
   `research/expected-reds.md`, and name **WP08** as its greening owner.

**Validation**: scratch-copy mutation **per primitive**, each expected red. Confirm the
historical figures are still present and labelled.

### T011 — Grow the censused callees 2 → 4, with end-state sanctions (FR-012)

**Purpose**: police the resolver nothing covers, and receive the guarantee WP01 transfers off
the retired floors.

**Steps**:
1. Add `resolve_feature_dir_for_mission` (kind-blind **and topology-routed** — which is exactly
   why it can hand a caller the husk) to the censused callees.
2. Add the **primary primitive** as the second new callee, receiving the retired floors'
   guarantee. See [contracts/gate-extension.md](../contracts/gate-extension.md) E2 — including
   the recorded *superseded* framing, so you do not re-derive the earlier exclusion decision.
3. **Alias resolution must hold**: an aliased import cannot defeat the census.
4. **Sanctions are asserted, never silently skipped**: per-file rationale for each sanctioned
   module, and **per-primitive** non-vacuity — the meta-test must prove a sanctioned module
   carries a real finding **for the newly censused primitive**, not merely for a
   previously-censused one. Otherwise the new primitive's sanctions are vacuously "proved".
5. Note that `core/paths.py` and `core/git_ops.py` are **not** currently sanctioned and need
   explicit per-site allow-list entries (FR-005 / C-003). WP07 records them by name; make the
   gate able to hold them.
6. Land the **end-state** sanction set, not an in-flight one: resolver-internal sites **plus
   per-site descriptors for the four named FR-005 foundation sites** (`core/paths.py` ×2,
   `core/git_ops.py`, `coordination/surface_resolver.py`). Those two `core/` modules are **not**
   currently sanctioned, so they need explicit entries — WP07 verifies them against its census
   and reports gaps back to you rather than editing this module.
7. **Dump the flagged finding set** into `research/expected-reds.md` as a `## WP02` section
   (append-only; WP01 owns the `## WP01` section in a parallel lane). Enumerate the
   `(rel_path, qualname)` composite keys, not just the node id — the gate fails once with the
   whole set, so an enumerated set is what lets WP04–WP07 prove *zero additions* instead of
   staring at a red that never moves.

**Validation**: planted direct call reds; planted **aliased** call reds; a prose mention stays
green; the per-primitive non-vacuity assertion passes for the *new* primitive on its own merits.

### T012 — AST-census and classify `resolve_feature_dir_for_mission` (FR-010)

**Purpose**: establish per site what it is actually doing, on **both** axes. Single-axis
classification is what let a silent wrong answer through last time.

The 8 sites / 7 files, confirmed by census on this base — **re-derive, do not trust**:
`agent_tasks_ports.py`, `cli/commands/decision.py`, `cli/commands/mission_type.py` (**×2**),
`context/resolver.py`, `decisions/emit.py`, `lanes/recovery.py`, `widen/state.py`.

**Record per site**: disposition (exactly one of **`migrate-fail-loud`** / **`stay-lenient`** /
**`sanction-infra`** — use these three names only, NFR-011 applies inward), the
raise-or-degrade axis, the anchoring root (verbatim argument **plus** its semantic class with a
one-line provenance citation), handle form, target kind, and idempotence under the seam's
output.

**Vacuity guard (this is how the first spec draft died)**: record the **count per
disposition**. If the census yields **zero** `migrate-fail-loud` sites, that is an explicit
recorded finding under FR-017 — not a silently satisfied requirement. SC-005's zero-case
discharge then applies: the husk guarantee is pinned by a synthetic-site regression instead
(WP04 T025).

Several sites carry production comments asserting the topology-routed answer is *required*.
Those comments become the **rationale of record** for a `stay-lenient` verdict — not a reason
to skip classifying the site.

**Validation**: the census script in [quickstart.md](../quickstart.md) §1 reproduces your site
count exactly; every site has both axes and a disposition.

### T013 — Write the rows, the honest bounds, and the corrected Known-gap text (FR-017)

**Steps**:
1. Write the classification rows under the T008 grammar, with the trailing `primitive`
   discriminator. Publish the per-disposition counts (SC-016).
2. **Honest bounds**, each named **with a size**: the wrong-`kind` argument class
   (census-invisible by construction), **wrapper laundering** (`resolve_subtasks_gate_dir`
   wraps a censused primitive with a pinned kind — invisible to a callee-name census), the
   zero-site latent sibling `resolve_feature_dir_for_slug` (would re-open the gap the moment it
   is imported), the sanctioned foundation and resolver-internal sites, and artifacts with **no
   kind** (`gap-analysis.md` anchors on a resolved directory rather than being routed).
3. **Correct the Known-gap section** (FR-016): it currently claims the primary primitive is
   "policed by nothing". It is policed on the **anchoring** axis by
   `test_resolution_authority_gates.py`. Name the gate **and the axis**. This false claim is
   what manufactured #3014 — correcting it is what stops a third re-derivation.

**Validation**: the bounds enumeration matches the live tree item-for-item, with sizes.

### T014 — Correct every stale count and drifted reference (FR-016)

**Steps**:
1. The stale site figure appears in **both** the ledger and the gate **docstring** — fix both.
   Re-derive; do not copy a number from this prompt or from #3014 (its figure is stale).
2. Update the drifted definition-line reference.
3. Post the corrected finding to **#3014** and close it with that evidence — it is the issue
   whose false premise manufactured this mission.

**Validation**: every count claimed in the ledger or the gate docstring matches a fresh census
(SC-008).

## Branch Strategy

- Planning/base branch: **`fix/read-side-seam-primary-primitive-closure`**
- Final merge target: **`fix/read-side-seam-primary-primitive-closure`**
- Claim and prepare the workspace with the canonical entry point:
  `spec-kitty agent action implement WP02 --agent <name>`
- Your execution worktree is allocated **per computed lane** from `lanes.json` by that
  command. Never hand-construct the path; never `git stash` in a lane
  worktree.

## Test Strategy

The six C-008 gates (tasks.md §5), plus scratch-copy mutation runs for T010, plus:

```bash
uv run ruff check <changed files>
uv run python -m mypy --strict src/specify_cli src/charter src/doctrine
PWHEADLESS=1 uv run pytest tests/architectural/test_no_legacy_terminology.py -q   # ledger is prose
```

## Definition of Done

- The grammar's six rules are **enforced**, and a second table / shifted column reds (T008).
- The four-site qualname is representable; the uniqueness assertion passes (T009).
- Row-count reconciliation and **per-primitive** mutation both bite; historical totals
  preserved and labelled (T010).
- Censused callees are at their **terminal** set of 4, with alias resistance, per-file
  rationale, and **per-primitive** non-vaciuty (T011).
- All 8 sites classified on both axes with per-disposition counts published (T012).
- Honest bounds named with sizes; Known-gap text names the real gate **and axis** (T013).
- Every count matches a fresh census; #3014 closed with the corrected finding (T014).
- The ~34 in-flight sites are recorded as **expected red** (cross-reference WP01's
  `research/expected-reds.md`), not suppressed.
- `ruff`, project-mode `mypy`, and the terminology guard are clean.
- Finish: commit, `spec-kitty agent tasks mark-status T008 T009 T010 T011 T012 T013 T014
  --status done`, then `spec-kitty agent tasks move-task WP02 --to for_review` and **wait** for the synchronous
  pre-review gate.

## Risks

- **The parser is the specification.** Read it before shaping the ledger; a rule you document
  but do not enforce is worse than none, because it reads as covered.
- **A duplicated verdict key overwrites silently, last-wins.** Check for collisions explicitly.
- **Do not add a second summary table** "for readability" — the parser reads only the first.
- **Do not rewrite a historical figure** to make reconciliation pass (NFR-008). Preserve and
  label it.
- The `#3011` rekey script is **not round-trip-safe** — WP08 hand-edits the second census
  inventory. Do not reach for it here either.

## Reviewer Guidance

1. **Mutate, do not read.** For each of the six grammar rules, mutate a scratch copy and
   confirm the red. A documented-but-unenforced rule is the failure mode.
2. Does the **per-primitive** non-vacuity assertion pass for the *new* primitive on its own
   merits, or is it riding on a previously-censused one?
3. Is the index keyed on **qualname + token** rather than a line number?
4. Are the per-disposition counts published, including a zero if that is the honest answer?
5. Do the honest bounds carry **sizes**, and does the Known-gap text name a gate **and an
   axis** rather than "policed by nothing"?
6. Confirm the ~34 in-flight reds are recorded as expected and **not** allow-listed away.

## Activity Log

> **CRITICAL**: entries MUST be chronological — **append** new entries at the END, never
> prepend or insert. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`, timestamp in
> UTC (`date -u "+%Y-%m-%dT%H:%M:%SZ"`). The acceptance system reads the LAST entry as the
> current state, so out-of-order entries fail acceptance even when the work is complete.

- 2026-07-28T09:27:08Z – system – Prompt created.
