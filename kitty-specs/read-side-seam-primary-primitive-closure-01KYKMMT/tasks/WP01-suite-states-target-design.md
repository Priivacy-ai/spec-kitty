---
work_package_id: WP01
title: The suite states the target design
dependencies: []
requirement_refs:
- FR-001
- FR-007
- FR-014
- FR-016
- FR-023
- FR-024
- NFR-004
- NFR-005
- NFR-007
planning_base_branch: fix/read-side-seam-primary-primitive-closure
merge_target_branch: fix/read-side-seam-primary-primitive-closure
branch_strategy: Planning artifacts for this mission were generated on fix/read-side-seam-primary-primitive-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/read-side-seam-primary-primitive-closure unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-read-side-seam-primary-primitive-closure-01KYKMMT
base_commit: 69f891719b32b24838a714736e48494f20d30271
created_at: '2026-07-28T10:23:31.698944+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - State the destination
history:
- at: '2026-07-28T09:27:08Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/architectural/test_resolution_authority_gates.py
- tests/architectural/resolution_gate_allowlist.yaml
- tests/architectural/test_gate_read_literal_ban.py
- tests/architectural/test_trio_seam_only.py
- tests/architectural/test_coord_read_residuals_closeout.py
- tests/architectural/_gate_coverage_baseline.json
- tests/architectural/_golden_count_baseline.json
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – The suite states the target design

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

Rewrite the affected architectural gates so they describe the **target** design instead of
the structure this mission removes. When you are done, the suite *is* the specification: it
will be deliberately red, and each later WP's job is to turn specific nodes green.

This is deliberately the **first** WP, not a trailing cleanup, because two hazards dissolve
structurally when it lands first:

1. The routed-count floor is a **strict** bound. It breaks around the **fifth** routed site,
   mid-drain, with the census still moving. Retiring it here makes "the floors will not trip"
   a fact rather than a timing hope.
2. Two gates currently pass while covering nothing. Giving them positive assertions *before*
   any migration means nothing can slip past them in the interval.

## ⚠ The bar this WP is judged against

Your WP is **not** judged on a green run. It is judged on the shape of the reds it leaves:

- every remaining red is an **assertion** about behaviour, traceable to a named FR;
- **zero** collection errors are introduced by this WP (a red that is a missing symbol at
  import time is not red-first evidence at all — `DIRECTIVE_034`);
- no gate is left **weaker** than before: widenings are kind-discriminated, exemptions become
  positive assertions;
- no foreign honest-red P0 is touched (C-010);
- the expected-red node list is **recorded** so later WPs can demonstrate their intended
  red→green transitions.

A carelessly red-stated suite *hides* regressions instead of revealing them. That bar is the
whole reason this WP is safe.

## Context & Constraints

Four gates prescribe the shape being retired: two floors *count uses of the primitive*, one
blesses it as the sanctioned read anchor and tells contributors to route *through* it, one
asserts a pin **exists**, and one requires blessed names to be **currently used**. See
[plan.md](../plan.md)'s "⚠ Expected-Red Ledger" for the full 26-point census (M1–M8, M16) and
the load-bearing-vs-bookkeeping table.

- **C-008 — targeted verification only.** Never run the full `tests/architectural/` suite
  locally; it destabilises the session. Run the six named gates (tasks.md §5). CI owns the
  exhaustive sweep.
- **NFR-007 — honest floor accounting.** Any floor that moves records its before/after
  integers **and** the reason. Five prior shrinks are on record in the floor comment block,
  one of them for *exactly* this routing move, annotated "a genuine routing shrink, not a
  re-pin". Follow that precedent.
- **NFR-005 — no green-by-omission.** Widening a blessing set is a *loosening* unless paired
  with a bite test proving the gate still flags a bad read.
- This WP touches **no product code**. If you find yourself editing `src/`, stop — you are
  about to commit the mission's single most dangerous failure mode.

## Doctrine for this WP

Each citation resolves the full artefact body. The command exits non-zero on a bad id, so a
citation that does not resolve is a bug in this prompt — report it rather than guessing.

- **`DIRECTIVE_041` (tests as scaffold, not friction)** — the disposition taxonomy every
  change here is justified by, plus *never retry-to-green*.
  `Run: spec-kitty charter context --include directive:DIRECTIVE_041`
  **When doing T003–T006** (retiring or rewriting any enforcement), state which disposition
  applies — STALE, PATCHWORK, or VALID — in the commit body.
- **`tactic:delete-the-assertion-not-the-test`** — re-point implementation-coupled assertions
  *in place*; reserve deletion for provably zero-coverage scaffolding.
  `Run: spec-kitty charter context --include tactic:delete-the-assertion-not-the-test`
  **When doing T004/T005** (before deleting any node), first ask what non-obvious coverage it
  carries. If the answer is "some", re-point instead of deleting.
- **`DIRECTIVE_034` (test-first)** — a red must manifest in an **assertion** about behaviour,
  not as a missing symbol at collection.
  `Run: spec-kitty charter context --include directive:DIRECTIVE_034`
  **When doing T004** — the closeout module's floor *import* is the exact hazard: deleting the
  constants without retiring the consumer errors ~20 tests at collection.
- **`tactic:architectural-gate-non-vacuity`** — its four elements, **verbatim**: **concrete
  floor · self-mutation test · shrink-only allowlist · routed-count floor**. Its named failure
  mode "vacuous gate" *is* M6 and M8.
  `Run: spec-kitty charter context --include tactic:architectural-gate-non-vacuity`
  **When doing T002 and T006**, apply those four as named. **Note the tension honestly**: T003
  retires a *routed-count floor* and an allow-list YAML block — two of the four elements. That is
  not licence; it is the transfer adjudicated under `DIRECTIVE_043` below, where the shrink-only
  allowlist and the routed-count floor both move to the read-side bypass census. Do not paraphrase
  the four elements into softer words (an earlier draft of this prompt did, and the two it dropped
  were exactly the two that police T003).
- **`tactic:frozen-baseline-shrink-only-ratchet`** — growth fails, shrink warns, baselines
  move only by human action with an inline justification naming before→after plus a tracker
  ref. `Run: spec-kitty charter context --include tactic:frozen-baseline-shrink-only-ratchet`
  **When doing T003 and T007.** ⚠ Its `notes` field references WP numbers (WP02/WP03/WP09) from a
  **different** mission. This mission also has a WP02, WP03 and WP09 — **ignore that numbering**;
  it is not about you.
- **`DIRECTIVE_043`** — `enforcement: required`. Read the adjudication in
  [plan.md](../plan.md) "Adjudication — FR-007 vs `DIRECTIVE_043`" **before** T003.
  `Run: spec-kitty charter context --include directive:DIRECTIVE_043`
  **When doing T003**, the retiring commit must state that non-vacuity is preserved by
  **transfer** to the read-side bypass census (which carries its own concrete floor,
  per-primitive non-vacuity, alias resistance and a shrink-only allow-list) — not abandoned.
  Silence here reads as violating a required directive.

## Subtasks

### T001 — Kind-discriminate the fold-prescription allow-sets (Ledger M7)

**Purpose**: Teach `test_gate_read_literal_ban.py` the tier-1 seam idiom so migrated sites are
**affirmatively** sanctioned — without turning the widening into a loosening.

Three allow/flag sets currently bless only the *blind* primitive: the sanctioned read-seam
functions, the primary-fold call shapes (`_PRIMARY_FOLD_CALLSHAPE_FUNCS`), and the write-side
primary anchor. A directory obtained from `placement_seam(...).read_dir(kind)` is in **neither**
the sanctioned nor the flagged set — so a migrated site would pass by omission (FR-001,
NFR-005).

**The defect to fix, not merely widen**: widening by **callee name** is kind-blind. It would
sanction `STATUS_STATE` reads through the same seam call — a genuine loosening — and it
propagates cross-file into `test_coord_read_residuals_closeout.py`'s no-STATUS-reroute check,
producing a **false NFR-001 regression** that invites a later implementer to "fix" a correct
STATUS leg. **Discriminate on the `kind` argument**: PRIMARY-partition kinds only.

**Steps**:
1. Read the three sets and their current failure messages. Note which sets are consumed
   *cross-module* by the closeout gate — those are the propagation path.
2. Extend each set to recognise the tier-1 idiom, gated on the `kind` argument being a
   PRIMARY-partition kind. Resolve the partition from `artifacts.py`'s kind frozensets — do
   not hardcode a kind list in the test.
3. Add a **bite test**: a planted non-compliant read inside a module whose reads now come
   from the seam is **still flagged**. Also assert the negative case: a `STATUS_STATE` read
   through the same call shape is **not** sanctioned by the widened set.

**Validation**: the bite test reds on the planted read; the STATUS negative case holds; the
closeout module's no-STATUS-reroute node does not acquire a new failure from this change.

### T002 — Give the write-arm node a positive assertion (Ledger M8)

**Purpose**: `test_write_arm_resolvers_anchor_meta_on_primary` *claims* that `meta.json` must
anchor on the primary primitive — but it **discards** its `reads_via_primary` signal and only
asserts the negative. A routed site therefore stays green **by omission**, and the wrapper
deletion will additionally make its anchor literal match nothing.

**Steps**:
1. Confirm the discard by reading the node: the positive signal is computed and dropped.
2. Assert the **positive** — the write arm anchors on the sanctioned assembly authority (or
   its post-migration seam equivalent) — while keeping the existing negative assertion.
3. Track the post-migration spelling: after WP08 the public name is gone, so anchor the
   assertion on the surviving private leaf, not on the deleted wrapper.

**Validation**: mutate the write arm so it anchors on something else → the node **reds**. It
does not today; that is the whole point.

### T003 — Retire both use-count floors, with recorded before/after (FR-007)

**Purpose**: Stop a gate from **obliging the primitive to keep being used**. After the
migration the floors' subject population is only resolver-internal and named-sanctioned sites,
where a raw handle is correct by contract — the floors would guard nothing and invert their
own purpose.

**Steps**:
1. Read the floor comment block in `test_resolution_authority_gates.py`. It records five prior
   shrinks; find the one that routed exactly this composition onto `read_dir(...)` and lowered
   the floor by one. That is your precedent and your annotation template.
2. Re-derive the live counts **now**, with the census recipe in
   [quickstart.md](../quickstart.md) §1 — do not trust any written figure, including the ones
   in this prompt.
3. Retire `test_routed_count_floor` and `test_canonicalizer_gate_floor`, and the corresponding
   block in `resolution_gate_allowlist.yaml`. Retire the margin's two-sided bound with them.
4. In the commit body record: the before/after integers, the reason (**a routing shrink**, not
   a re-pin), and the `DIRECTIVE_043` adjudication — the guarantee **transfers** to the
   read-side bypass census, which WP02 lands with its own concrete floor and per-primitive
   non-vacuity.
5. **Mechanical fallback** (only if retirement proves larger than expected): re-pin to the
   honest post-migration numbers respecting the existing margin rule, and say so explicitly.
   Retirement is preferred.

**Validation**: no test in the tree asserts the primitive must remain in use. Grep for the
retired constant names — every consumer must be handled by T004.

### T004 — Retire the closeout module's floor import and equality pins (Ledger M3)

**Purpose**: The floor values are **an import plus two `==` pins across two modules** — not
"bare literals in one file". Deleting the constants without retiring their consumer raises
`ImportError` **at collection**, erroring the whole ~780-line module (~20 tests). That reads
as collateral damage and will be misattributed.

**Steps**:
1. Find the import of the retired constants in `test_coord_read_residuals_closeout.py` and its
   two equality assertions.
2. Retire them **in the same commit as T003**. Judge each with `DIRECTIVE_041`: the
   floor-honesty assertions are STALE (their subject is gone). If any carries non-obvious
   coverage beyond the integers, re-point it rather than deleting it.
3. Keep the module's **site floor** — that is its non-vacuity and it is unrelated to the
   use-count floors.

**Validation**: `uv run pytest tests/architectural/test_coord_read_residuals_closeout.py -q`
**collects cleanly**. Zero collection errors is the hard bar (`DIRECTIVE_034`).

### T005 — Retire the `#2214` pin with its pin-existence test; fix the off-by-one census

**Purpose**: The allow-list entry pinned as `#2214` exempts the unrouted
`_run_documentation_wiring` reads. Removing it here makes the gate assert the **target**
design — the reads routed — and WP04's routing is what turns it green. Deleting the pin
*without* retiring the test that asserts the pin exists reds by construction (FR-014).

**Steps**:
1. Remove the `#2214` allow-list entry **and** the test asserting that entry exists —
   together, in one commit.
2. Correct the module's recorded census **off-by-one** (FR-016). Re-derive it; do not adjust
   the number to make a check pass.
3. Record the resulting reds on the expected-red list (T007): the closeout gate now flags
   `mission_setup_plan.py`'s two unrouted reads. That is WP04's target.

**Validation**: the module collects and runs; the only new reds are the two unrouted reads,
recorded as expected. `git log` shows pin and pin-existence test removed in the same commit.

### T006 — Trio gate: shrink the blessed set and replace the self-nullifying exemption (M5/M6)

**Purpose**: `_SEAM_ALLOWED_READ_PATH_RESOLVER_NAMES` blesses three names, two of which this
mission drains. `test_allowed_read_path_resolver_names_are_currently_used` requires blessed
names to be **currently imported** by a trio file — so both go unused and it fails, with the
fix in its own message ("Drop them … to keep the allowlist precise"): a **tightening**.

**The trap (M6)**: after the shrink the set reduces to a single name which a later line
**subtracts** — leaving the gate **vacuously green**. It would then stay green if the trio
regressed. That is a VALID-fix-the-gate, not a shrink.

**Steps**:
1. Drop `primary_feature_dir_for_mission` and `_canonicalize_primary_read_handle` from the
   blessed set. Record the shrink as a tightening.
2. Replace the exemption with a **positive assertion**: the trio imports the seam idiom and
   nothing else from the resolver module — an assertion that reds if a trio file reacquires a
   leaf primitive, and cannot be satisfied by an empty set.
3. Record on the expected-red list: this gate stays red until WP05 routes all four trio
   rewrite targets.

**Validation**: plant a leaf-primitive import in a trio file → the gate **reds**. Empty out
the blessed set → the positive assertion still has teeth (it does not go green).

### T007 — Refreeze the gate-coverage baselines and record the expected-red set

**Purpose**: Retiring node-ids drifts the gate-coverage baselines, and the expected-red set is
this WP's deliverable — without it, later WPs cannot demonstrate a red→green transition and
reviewers cannot distinguish your reds from regressions.

**Steps**:
1. Refreeze the affected baselines with provenance. Two distinct mechanisms exist and they are
   not interchangeable: the **orphan** baseline takes `--update-baseline`; the **selection**
   baseline takes `--freeze-baselines`. Use the one the failure message names.
2. If a golden-count assertion moves, follow the in-repo convention (`# golden-count`
   annotation) rather than editing the integer silently.
3. Write `kitty-specs/read-side-seam-primary-primitive-closure-01KYKMMT/research/expected-reds.md`
   — a **mission research artifact**, written as **one `## WP01` section** (WP02 appends its own
   `## WP02` section in a parallel lane, so keep to your own section: append-only, no shared
   lines, no lane conflict). It is deliberately outside `owned_files`
   (`finalize-tasks` rejects `owned_files` entries under `kitty-specs/`; the ownership map
   covers code surfaces only), so commit it with your WP. Per red, record: the **node id**, the
   FR it traces to, the WP expected to green it, and one line of why. Include a short **foreign honest-red P0** section naming
   `tests/sync/test_sync_consent_default_deny.py` (#3031) explicitly as not-ours.
4. **Record the read-side census red as an enumerated FINDING SET, not a node id.** This is the
   one place the acceptance model could go blind: the bypass gate collects every unsanctioned
   finding and fails **once** with the whole set, so that node is red before *and* after every
   routing WP — it yields no signal for WP05/WP06/WP07, and a genuinely new bypass (30 → 31
   findings) is indistinguishable from the recorded expectation. The gate already emits
   `(rel_path, qualname)` composite keys, so dump the **flagged set** rather than the node name.
   That converts a one-bit red into a per-site ratchet at no cost.
5. Run the six C-008 gates and reconcile the actual reds against your list. A red you did not
   predict is either a regression you caused or a gap in your understanding — resolve it, do
   not append it silently.

**Validation**: every observed red appears on the list with a named FR and a target WP; the
list contains **zero** collection errors; the count of expected reds is stated.

## Branch Strategy

- Planning/base branch: **`fix/read-side-seam-primary-primitive-closure`**
- Final merge target: **`fix/read-side-seam-primary-primitive-closure`**
- Your execution worktree is allocated **per computed lane** from `lanes.json` by
  `spec-kitty agent action implement WP01 --agent <name>` — the canonical entry point. Do not
  construct a worktree path by hand, and do not `git stash` inside a lane worktree (the stash
  stack is shared across worktrees).

## Test Strategy

Run the six C-008 gates (tasks.md §5) plus:

```bash
uv run ruff check <changed files>
uv run python -m mypy --strict src/specify_cli src/charter src/doctrine   # project mode = CI
```

Project-mode `mypy` is authoritative; a single-file `mypy <file>` spuriously reports `Any` for
cross-package imports and must never be used to justify a cast.

## Definition of Done

- All three gate *defects* fixed as fixes, not widenings: kind-discriminated fold sets (T001),
  positive write-arm assertion (T002), positive trio assertion (T006).
- Both use-count floors retired with before/after integers, the reason, and the
  `DIRECTIVE_043` adjudication in the commit body (T003).
- The closeout module **collects cleanly** — zero collection errors (T004).
- `#2214` pin and its pin-existence test removed in one commit; off-by-one census corrected
  (T005).
- Baselines refrozen with provenance; `research/expected-reds.md` written and reconciled against an
  actual run (T007).
- `ruff` and project-mode `mypy` report zero new findings.
- **Zero changes under `src/`.**
- Finish: commit, `spec-kitty agent tasks mark-status T001 T002 T003 T004 T005 T006 T007
  --status done`, then `spec-kitty agent tasks move-task WP01 --to for_review` and **wait**
  for the synchronous pre-review gate.

## Risks

- **The suite will be red when you hand off.** That is correct. Reviewers must read
  `research/expected-reds.md`, not a green run.
- **Cross-module propagation** (T001): the fold sets are consumed by the closeout gate. A
  callee-name widening produces a false NFR-001 regression three files away.
- **Collection errors are the failure mode**, not assertion failures — two of this WP's
  targets fail at import time (T004's floor import; the descriptor is WP03's).
- **Do not touch** `tests/sync/test_sync_consent_default_deny.py` or anything else on the
  `sync/routing.py` surface. Different sense of "routing" entirely (C-010).

## Reviewer Guidance

Review this WP against `research/expected-reds.md`, not against a green test run. Specifically check:

1. Is **every** widening kind-discriminated? A callee-name widening is a silent loosening.
2. Do T002's and T006's new assertions actually **bite**? Mutate the subject and confirm the
   red. A positive assertion that cannot fail is the same defect it replaced.
3. Does the retiring commit carry before/after integers, the reason, **and** the
   `DIRECTIVE_043` adjudication?
4. Are there **zero** new collection errors, and **zero** `src/` changes?
5. Is any red on the list actually a foreign honest-red P0 mislabelled as ours (or vice
   versa)? Classification is by **surface**.

## Activity Log

> **CRITICAL**: entries MUST be chronological — **append** new entries at the END, never
> prepend or insert. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`, timestamp in
> UTC (`date -u "+%Y-%m-%dT%H:%M:%SZ"`). The acceptance system reads the LAST entry as the
> current state, so out-of-order entries fail acceptance even when the work is complete.

- 2026-07-28T09:27:08Z – system – Prompt created.
