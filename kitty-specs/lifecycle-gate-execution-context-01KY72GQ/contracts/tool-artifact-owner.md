# Contract — Tool-Artifact Owner

**Discharges**: FR-007, FR-008, FR-009, FR-012, FR-013, NFR-002, NFR-006, C-010
**Surfaces**: `coordination/transaction.py`, `merge/bookkeeping_projection.py`,
`merge/executor.py`, `mission_runtime/artifacts.py`, `status/__init__.py`,
`coordination/commit_router.py`, `cli/commands/implement_cores.py`, `bulk_edit/diff_check.py`,
`git/ref_advance.py`, `cli/commands/agent/tasks_move_task.py`, `merge/ordering.py`,
`lanes/merge.py`, `review/dirty_classifier.py`, `merge/git_probes.py`,
`cli/commands/agent/mission_record_analysis.py`, `acceptance/__init__.py`,
`coordination/coherence.py`, `cli/commands/implement.py`, `lanes/auto_rebase.py`

*(Corrected 2026-07-23: `merge/ordering.py` and `lanes/merge.py` are live
`COORD_OWNED_STATUS_FILES` consumers that the first surface list omitted, along with the other
consumer modules. Both are in the `merge/` package.)*

**C-001 ↔ IC-07(c) tension, resolved.** Retirement group (c) — `COORD_OWNED_STATUS_FILES` and its
consumers — is inseparable by C5 (retiring one consumer leaves the set alive), yet two of its
consumers (`merge/ordering.py`, `lanes/merge.py`) sit in the `merge/` package that C-001 gates.
The "merge-package work last" rule therefore cannot mean "split group (c) so the merge parts come
later" — the contract forbids that split. It means: **schedule the whole of group (c) after the
`merge/`-package rebase point**, as one work package. C-001's precondition (in-flight PRs landed,
branch rebased) is already discharged, so the residual requirement is only "re-fetch before
starting group (c)".

---

## C1 — Exactly one owner per generated write, bounded by a tool-derived inventory

*Rewritten 2026-07-23. "Any path spec-kitty writes" is an unbounded universal with no oracle.*

**Given** the **enrolment inventory** — a tool-derived list of generated-write sites that
self-asserts in BOTH directions (no discovered sink missing from it; no row without a live sink)
**When** the inventory is regenerated
**Then** every discovered write site is enrolled in exactly one transaction
**And** every inventory row still maps to a live site.

*Reuse, do not reinvent*: `tests/architectural/untrusted_path_audit/` already implements exactly
this mechanism — a tool-derived inventory with an undercount arm and an overcount/ghost arm, keyed
by a drift-proof composite key. Clone that shape. **Never hand-write the list**; a hand-derived
inventory is the same failure that produced three successive wrong exemption censuses.

---

## C2 — Committed or reverted, never orphaned

**Given** an enrolled generated write
**When** the step completes
**Then** the write is committed to its declared home
**When** the step fails or is interrupted
**Then** the write is restored to its pre-transaction bytes
**And** no third, partially-applied state is observable.

*Observable signal*: interrupt tests on each write path assert the artifact is byte-identical
to either its pre-state or its committed post-state.

---

## C3 — Subprocess byproducts are enrolled

**Given** a lifecycle step that spawns a child process which creates or modifies files
**When** the step completes or aborts
**Then** those bytes are committed or reverted like any other generated write
**And** they are not detected, warned about, and abandoned.

*Failure this prevents*: the current "Pre-review tests created or changed additional paths;
preserved without cleanup" behaviour, which manufactures precisely the orphan a later gate must
then be taught to ignore.

---

## C4 — One compensator (split into a behavioural arm and a negative arm)

*Rewritten 2026-07-23. "When rollback implementations are enumerated" needed an oracle nobody
had written.*

**C4a (behavioural).** **Given** each of the enumerated failure-injection scenarios, **when** the
step fails, **then** the bytes at every enrolled path are byte-identical to the pre-transaction
snapshot.

**C4b (negative, mission invariant).** A scoped `grep_absence` over `src/specify_cli/merge/` for
the **named** retired symbols (`_capture_bookkeeping_snapshots`,
`_restore_final_bookkeeping_snapshots`, and their confinement helpers). This is a source scan, but
a *negative* one over symbols the mission intends to delete — the refactor-stable form NFR-008
permits, unlike a positive count of implementations.

---

## C5 — Every enumerated retirement symbol is absent

**Given** the codebase after this mission
**When** each symbol on the retirement list is searched for in `src/`
**Then** every one is absent — verified **per named symbol**, not by counting.

**The retirement registry (the enumerated rows).** The eight original symbols are listed below;
the four additions R-014 found (`ACCEPT_OWNED_PATHS`, the `dirty_classifier` bundle,
`_exclude_coord_owned`, the dead `ignores_primary_coord_residue`) are equally on the registry and
retired by IC-07 group (g). No count is normative — the registry, derived by rule (R-014), is the
authority, and IC-08 asserts it reaches zero rows. The original eight:

1. `is_self_bookkeeping_path` and its filename/suffix sets — 4 consumers
2. `is_coordination_artifact_residue_path` — 7 consumers
3. + 4. `COORD_OWNED_STATUS_FILES`, its `advance_branch_ref` parameter, **and** the coord-staging
   skip of the same set — **one mechanism with eight consumer sites; cannot be split across work
   packages**, since retiring one consumer leaves the set alive
5. `_drop_vcs_lock_only_meta`
6. `new_checkout_paths` "preserved without cleanup" — ~10 sites, `:1115-1632`
7. `RUNTIME_STATE_ALLOWLIST` / `_runtime_state_exemption`
8. `_drop_runtime_frontmatter_only_wp` + `_is_wp_filename` / `_WP_FILENAME_PATTERN` — the
   structural twin of #5; deduplicate rather than retiring one and leaving the other

**Explicitly NOT on this list**: the non-`pending` preservation branch in `acceptance/matrix.py`.
It is a *state* guard, not a filename or path match, and this mission **requires it to survive**
(NI-2 pins it; NFR-004 forbids regressing it). An earlier draft of this contract listed it as
retired while the provenance contract pinned it — a direct contradiction, now resolved. See
research R-012.

*Why enumerated and not counted*: the original count was hand-derived, wrong (nine mechanisms,
not eight), and needed an oracle nobody wrote. Per-symbol absence is decidable; a total is an
artefact of the list.

---

## C6 — Retirement preserves behaviour the exemption got right

**Given** an exemption that encoded genuinely correct behaviour
**When** it is retired
**Then** that behaviour is preserved through the owner
**And** no operation that previously succeeded now fails.

*This is the primary regression risk of the whole mission.* Each retirement lands in its own
work package specifically so a reintroduced false block is localisable (C-010, decision
`01KY7AKZBQCM7X4MV2C0101WKZ`).

---

## C7 — Cross-gate agreement (RED on the current base)

*Rewritten 2026-07-23 into a behavioural form that is falsifiable today.*

**Given** the same corpus of paths
**When** every gate that classifies toolchain churn is asked to classify it
**Then** all gates return the identical classification.

**This test goes red immediately on the mission base**, which is exactly what red-first discipline
wants: `merge/git_probes.py:173` **exempts** a tracked-modified `meta.json` via
`is_self_bookkeeping_path` (`_SELF_BOOKKEEPING_FILENAMES = {"meta.json"}`), while
`git/ref_advance.py` never consults that predicate and its `excluded_filenames` escape applies only
to untracked entries — so the same file is invisible to one gate and fatal at another. That
disagreement is FR-012 stated as a live defect rather than a design aspiration, and it is the
concrete repro for #2795.

---

## C8 — Rename-invariance (the clause that makes "by kind, not filename" mean something)

*Rewritten 2026-07-23. "Uses the declared kind and not a filename match" is a statement about
implementation; as written it would be quietly satisfied by one bigger filename list.*

**C8a.** **Given** a generated artifact of declared kind K classified as generated, **when** the
same bytes and kind are written to a path with a **different basename**, **then** the
classification is unchanged.

**C8b.** **Given** an operator-authored file whose basename **collides** with a generated
artifact's basename, **then** it is **not** classified as generated.

A filename-based classifier cannot pass either arm. Together they kill the mutant this contract
names by hand — replacing eight lists with one larger list — behaviourally rather than by
inspection.

---

## C9 — A ninth exemption is refused

**Given** a contributor adding a new filename-based exemption to any dirty-state gate
**When** the architectural suite runs
**Then** it fails
**And** the failure names the owner as the supported route.

*Constraint*: pin a behavioural invariant, not a literal source scan (NFR-008), so a later
refactor neither false-reds nor false-greens it.

---

## C10 — Size discipline

*Rewritten 2026-07-23. "Roughly 1500" is unmeasurable, and "split out **before** the
generalisation landed" asserts commit ordering — unassertable post-merge and erased by this
project's history-compression practice.*

**Given** the mission is complete
**When** `coordination/transaction.py` is measured
**Then** it is **≤ 1000 LOC** (measured baseline 1345; IC-12's extraction targets ~914, leaving
headroom for the owner's three new capabilities).

The sequencing requirement — extraction precedes generalisation — is a **plan constraint**
(IC-12 before IC-06), not an acceptance criterion. Recorded there, removed from here.
