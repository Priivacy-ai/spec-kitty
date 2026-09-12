# Research — Lifecycle Gate Execution Context and Tool-Artifact Ownership

**Phase 0 output.** Findings were originally verified against `upstream/main` `a0b48867e` (and its
predecessor `eb06ca176`); the branch has since been rebased onto `8074107d7` and the load-bearing
claims re-verified there by reading code and running tests — not from issue prose.

---

## R-001 — Which of the briefed defects are actually live

**Decision**: Scope the mission to #1834's pending-invariant leg, #2885, #2795 (behind a
repro), and #2882. Exclude #2573, the #2160 residuals, and #2367 Mechanism B.

**Rationale**: Three of the four originally briefed P0s had their stated asks already
delivered. Verified:

| Item | Verified state | Evidence |
|---|---|---|
| #2573 ask (a) — skip flag | Landed | `cli/commands/agent/tasks.py:669`; commit `35f3a2206`; escape-hatch test green |
| #2573 ask (b) — daemon env | Landed | commit `f217d4272`; `tests/sync/test_daemon_sync_disable_env.py` — 2 passed |
| #2493 contention facet | Landed | commit `dd83e5b6f` — `_scoped_run_lock`, acquire timeout decoupled from run timeout |
| #1834 ask (c) — don't overwrite | Landed | commit `b918e66df`; `matrix.py::enforce_negative_invariants` returns non-`pending` untouched |
| #2367 Mechanism B | Fixed | #2786; `tests/regression/test_issue_2367_bake_strand.py` green |
| #2160 residuals ×5 | All closed | #2197/#2198/#2199/#2214 on 2026-06-28; #2167 on 2026-06-30 |

**Alternatives considered**: Specifying against the issue text as briefed. Rejected — it
would have produced work packages that re-deliver `main` and then "verify" them with
tests that were already green.

---

## R-002 — Is #1834 a coordination-topology defect?

**Decision**: No. Treat it as topology-independent and forbid any coord-conditioned fix
(C-004).

**Rationale**: `acceptance/gates_core.py:298` calls `enforce_negative_invariants(repo_root, …)`
with the bare repo root — no topology involved on the *execution* surface, even though the
matrix *read* is topology-routed. A flat `SINGLE_BRANCH` mission reaches `accept` with its
work on lane branches not yet consolidated, so a `grep_absence` invariant run from the repo root sees
the pre-consolidation tree and reports `still_present` identically. The coordination branch is
irrelevant to the mechanism.

**Alternatives considered**: Framing the whole cluster as coord-topology remediation.
Rejected — it would produce a fix that special-cases coord and leaves flat missions broken.

---

## R-003 — Is the landed #1834 fix sufficient?

**Decision**: No. Complete it with provenance + defer semantics (FR-002/FR-003).

**Rationale**: The landed guard preserves a *recorded non-`pending`* result. But `pending`
is the scaffolded default (`matrix.py`), so an invariant nobody hand-recorded during review
still executes against the pre-consolidation tree; the verdict then computes `pending` and
acceptance is blocked. **Corrected 2026-07-23:** a live probe through the real seam shows the
pending leg reproduces as verdict **`fail`** at `gates_core.py:313` — *"negative invariants or
criteria not satisfied"* — byte-identical in shape to the pre-`b918e66df` defect. It is NOT the
`pending` message at `:315`, which is reachable only for malformed invariants. A red-first test
written against the original wording would assert the wrong string and pass vacuously.
The failure mode was renamed, not removed. A design that requires a reviewer to remember to
hand-record a result is structurally incomplete.

**Live evidence, not theory**: the flagship mission merged immediately before this one
(`coord-commit-integrity-01KY5JS8`) ships `negative_invariants: []` — it adopted #1834's
documented workaround verbatim.

---

## R-004 — Direction for #1834: (a) post-consolidation, (b) workspace-aware cwd, or (c) don't overwrite

**Decision**: (c) completed with provenance, plus (a) as a post-consolidation verification. **Reject (b).**

**Rationale**: (b) requires resolving "the integrated lane/mission tree" pre-consolidation. For a
multi-lane mission that tree **does not exist** — lanes are independent branches and the
integration only materialises at merge. Implementing (b) would mean designating one lane's
worktree as "the integrated tree", i.e. fabricating an authority. That is the exact
silent-wrong-surface evaluation this mission exists to eliminate, and the mirror image of
the fallback #2874 explicitly refused.

**Alternatives considered**: (b) alone — rejected as a fiction; (a) alone — rejected because
it discards the honest lane-surface judgement already made during review.

---

## R-005 — Resolver shape: fallback vs total

**Decision**: Resolvers become **total**. Each topology's declared home is returned
affirmatively; `None` means only *"a coord home was declared and is unresolvable"* and raises.
Decision record `01KY7AKYGKZFK202NQ37094T34`.

**Rationale**: `_acceptance_matrix_read_dir` currently ends `return resolved if resolved is not None else feature_dir`,
whose docstring says it falls back "so flat / `SINGLE_BRANCH` / `LANES` missions read exactly
where they do today". That conflates two cases — one legitimate (flat: the primary dir *is*
the home), one a silent degradation (coord declared but not materialised). A total resolver
separates them without a special case.

**Operator directive folded in**: `flattened` is pre-topology residue and should be steadily
removed as a load-bearing property, not reinforced — *do not strengthen ducttape*. This
mission therefore adds **no new dependence** on `flattened` and makes every resolver it
touches total. Full de-ducttaping of the ~66 `flattened` sites in `src/` (the topology-bearing
ones cluster in `transaction.py`, `commit_router.py`, `surface_resolver.py`,
`mission_creation.py`) is a separate track.

**Alternatives considered**: scoping NFR-001 to "coord-resolved paths only" and blessing the
flat fallback as a legitimate leg. Rejected on the operator directive — it codifies the
ducttape rather than shrinking it.

---

## R-006 — #2795's stated mechanism

**Decision**: Do not write a fix against the reported mechanism. Require a live reproduction
first (FR-011, IC-01).

**Rationale**: The issue asserts the VCS lock is written into the **coordination** worktree's
`meta.json` at claim time. On this base it is not: `implement.py:1166` resolves
`feature_dir = placement_seam(...).read_dir(MissionArtifactKind.SPEC)` and `:1760` feeds that
same dir to `_ensure_vcs_in_meta`. `SPEC` is a PRIMARY-partition kind whose declaration states
these artifacts *"live with their mission on the primary target_branch for EVERY topology and
NEVER transit the coordination branch"*, behaviourally pinned by
`tests/architectural/test_write_surface_placement_guard.py`.

**But this reframes rather than dissolves the defect.** The same declaration continues:
*"so a stale primary copy is a REAL dirty-tree blocker — not residue."* So an uncommitted lock
write plausibly still blocks a merge — on the primary checkout, with a different fix.
`implement_cores.py::_drop_vcs_lock_only_meta` compounds it: its docstring states it
*stop-gates* a lock-only diff, leaving the lock uncommitted.

**Corroborating observation from this mission's own lifecycle**: within minutes of
`mission create`, this mission's `meta.json` was left carrying an uncommitted `pr_bound: true`
write — the same shape (tool metadata written at a lifecycle step, not committed).

---

## R-007 — Recurrence: how many times has this class been patched?

**Decision**: Treat the exemption pattern as a class to close, not a set of sites to patch.

**Rationale**: Nine independent mechanisms exist in `main`, each teaching exactly one gate to
ignore spec-kitty's own bytes; none commits or reverts anything:

| # | Mechanism | Location |
|---|---|---|
| 1 | `is_self_bookkeeping_path` + filename/suffix sets | `mission_runtime/artifacts.py` |
| 2 | `is_coordination_artifact_residue_path` | `mission_runtime/artifacts.py` |
| 3 | `COORD_OWNED_STATUS_FILES` → `advance_branch_ref(coord_owned_filenames=)` | `status/__init__.py`, `git/ref_advance.py` |
| 4 | coord-staging skip of the same set | `coordination/commit_router.py` |
| 5 | `_drop_vcs_lock_only_meta` | `cli/commands/implement_cores.py` |
| ~~6~~ | ~~non-`pending` preservation~~ — **RECLASSIFIED OUT**, see below | `acceptance/matrix.py` |
| 7 | `new_checkout_paths` "preserved without cleanup" | `cli/commands/agent/tasks_move_task.py` |
| 8 | `RUNTIME_STATE_ALLOWLIST` / `_runtime_state_exemption` | `bulk_edit/diff_check.py` |
| 9 | `_drop_runtime_frontmatter_only_wp` + `_is_wp_filename` / `_WP_FILENAME_PATTERN` — **uncounted until 2026-07-23** | `cli/commands/implement_cores.py:410` |

Plus **two parallel implementations of the same compensating transaction**:
`coordination/transaction.py::_rollback` versus `merge/bookkeeping_projection.py`'s
snapshot capture/restore pair with `coordination/coherence.py::repair_coord_strand`.

Supporting signal: 44 distinct `#NNNN` issue references are embedded as in-code rationale (counted; an earlier "~79" figure was an overcount, corrected after the second independent review re-counted)
across the nine files in scope — a boundary renegotiated one caller at a time for roughly
eighty tickets.

**Guardrail adopted**: if this mission's plan ever contains "add an allowlist so gate G stops
complaining", the mission has failed its own thesis.

---

## R-008 — Retirement strategy

**Decision**: Strangler. Owner first, then one small WP per exemption, `merge/`-package ones
last. Decision record `01KY7AKZBQCM7X4MV2C0101WKZ`.

**Rationale**: Some exemptions encode genuinely correct behaviour (C-010). A retirement that
reintroduces a false block is a regression, and in a single nine-file diff it would be very
hard to localise. Per-exemption WPs are independently revertible and independently reviewable.

**Alternatives considered**: Big-bang, to avoid a half-migrated interval where some gates
consult the owner and others consult a list. Rejected — the interval is tolerable and
observable; an unlocalisable regression is not.

---

## R-009 — Post-consolidation verification hook location

**Decision**: New `acceptance/post_consolidation.py` seam with a narrow call-in from
`merge/executor.py`. Decision record `01KY7AKXNJZCB2J2W411YM3B9F`.

**Rationale**: Keeps invariant logic in the acceptance package, minimises footprint on the
1433-LOC merge executor, and — decisively — lets the post-consolidation verification WP and the
merge-exemption-retirement WP own **disjoint files**, which they must.

**Alternatives considered**: Implementing inline in `merge/executor.py`. Rejected — it
concentrates more change in the duplicate-compensator crime scene and forces two WPs to share
a file.

---

## R-010 — Should this mission dogfood coordination topology?

**Decision**: Yes (operator decision), with IC-01 sequenced first as the mitigation.

**Rationale**: The operator chose live field evidence over fixture-only evidence. The
countervailing risk is real and is handled structurally rather than argued away: #2795 is
still live, so under coord topology the mission would be blocked at merge by the very defect
it is fixing. C-002 therefore requires IC-01 to be reproduced and fixed before any work
package reaches its terminal step.

**Alternatives considered**: Flat/`LANES` with coord evidence from the shared test fixture
(`tests/integration/test_merge_cluster_coord_read.py`). This was the pre-spec squad's
recommendation; the operator overrode it deliberately.

---

## R-011 — Concurrent-mission collision

**Decision**: Sibling mission `scopesource-gate-followup-01KY6S9P` lands first;
`review/pre_review_gate.py` leaves this mission's scope entirely.

**Rationale**: The sibling is TASKED while this mission was only SPECCED, and its diff in the
shared files is dominantly subtractive (~450 LOC deletion). Threading execution-context
plumbing through code about to be deleted is waste and would convert a clean deletion into a
conflicted one. None of this mission's live defects lives in that file. Full detail and the
shared watch items (compat golden re-baselining 157→156; `TransitionGateContext` ripple) are
recorded in `research/sibling-mission-coordination.md`.

---

## Open items carried into implementation

- **Subprocess byproduct enrolment mechanism** (IC-06) — `BookkeepingTransaction` has no
  concept of "bytes a child process created". Whether enrolment happens by pre/post dirty-set
  diffing at the call site or by a scoped context manager around the subprocess is a design
  choice for the owner WP.
- **`transaction.py` size budget** — generalisation must not push it past ~1500 LOC; split
  acquire/legacy-resolution helpers first (campsite-first).
- **Exact `LifecyclePhase` membership** — `REVIEW | ACCEPT | POST_CONSOLIDATION` is the working set;
  whether `IMPLEMENT` needs representation depends on IC-01's findings.


---

## R-012 — Census correction: nine mechanisms, one reclassified out (2026-07-23)

**Decision**: retire an **enumerated list of named symbols**, not "a count". Correct the census to
nine, and remove the non-`pending` preservation branch from the retirement set entirely.

**Rationale**: two independent audits found the original census of eight both wrong and
unmeasurable.

- **A ninth was missed.** `cli/commands/implement_cores.py:410 _drop_runtime_frontmatter_only_wp`
  is filename-keyed via `_is_wp_filename` / `_WP_FILENAME_PATTERN`, applied on the same two lines
  as counted mechanism #5, and its own docstring calls it a *"structural analogue of
  `_drop_vcs_lock_only_meta`"*. A ratchet pinned to "8 → 0" would not have caught it. The two
  bodies are near line-for-line parallel — a `_drop_if(paths, predicate)` extraction collapses
  both, closing the class properly rather than counting it.
- **Mechanism 6 is not a filename or path exemption at all.** It is a *state* guard
  (`if ni.result != "pending"`), and the mission **requires it to survive**: NI-2 pins it as a
  ratchet, spec User Story 1 scenario 2 depends on it, and NFR-004 forbids regressing it. Listing
  it as "retired" while another contract pinned it was a direct contradiction in this mission's
  own artifacts. It is reclassified as a preserved correctness invariant.
- **A count needs an oracle nobody wrote.** The census was hand-derived and already missed one.
  Per-symbol absence is decidable with scoped `grep_absence`; a total is an artefact of the list.

**Consequence**: NFR-006 and SC-004 are restated as enumerated-symbol absence. The retirement set
is **eight symbols** (nine mechanisms minus the reclassified state guard), and mechanisms 3 and 4
are one set with eight consumer sites, so they cannot be separate work packages.

**Alternatives considered**: keep the count and add the ninth. Rejected — it preserves an
unmeasurable success criterion and leaves the contradiction with NI-2 unresolved.


---

## R-013 — Acceptance-matrix schema migration (2026-07-23)

**Decision**: ship a **one-time backfill migration**, plus an **archive escape hatch** for
missions whose recorded state will not migrate cleanly. Operator decision.

**The measured problem** (verified, not estimated): across `kitty-specs/*/acceptance-matrix.json`
there are **153 matrices, 40 non-`pending` negative invariants in 14 missions, and zero carrying
provenance**. Making provenance mandatory (NI-1 / provenance contract C1) turns every one of
those into a validation error, so `accept` or `--diagnose` on any of those 14 missions starts
failing. A second, forward-facing break: `deferred_to_consolidation` is not in
`NEGATIVE_INVARIANT_RESULTS`, so an older spec-kitty reading a new matrix computes verdict
`fail`.

**Rationale for migration over grandfathering**: a version-gated "provenance required only from
schema version N forward" rule is cheap now and permanent later — two validity regimes coexisting
indefinitely, which is precisely the kind of retained past mistake this codebase already carries
too many of. A migration converges on one regime.

**Rationale for the archive hatch**: a migration that must invent provenance for results whose
originating surface is genuinely unknowable would be fabricating evidence — unacceptable in a
mission whose thesis is that gates must not fabricate authority. Rather than guess, an operator
can archive the legacy mission: its recorded state is preserved as an immutable snapshot, marked
legacy, and excluded from live validation. Nobody is blocked on current work by an old mission
that will not migrate honestly.

**Serialisation care**: `to_dict` uses `asdict`, so new `None` fields would emit as `null` into
all 153 matrices on next write. Follow the omit-if-`None` precedent already set for `scope`, or
the mission generates 153 files of toolchain churn — from the mission whose thesis is that the
toolchain must own its own writes.

**Alternatives considered**: grandfather by schema version (rejected above); soft-warn for one
release (rejected — adds a deprecation cycle to an already-wide mission and still ends in a
migration).


---

## R-014 — The census needs a DERIVATION RULE, not a longer list (2026-07-23)

**Decision**: stop hand-enumerating. Define the class by a mechanically decidable rule, generate
the registry from it, and make the ratchet a negative structural scan with a monotonically
shrinking registry.

**Why**: this is the third census. Eight → nine (R-012) → **at least eleven** now. Two independent
second-opinion audits each found mechanisms the previous "corrected" list had missed, using the
same method that produced the original wrong count. R-012's own conclusion — *"a count needs an
oracle nobody wrote"* — applies with equal force to an enumeration produced by hand.

**Newly found, on no prior list:**

| Mechanism | Location | Why it qualifies |
|---|---|---|
| `ACCEPT_OWNED_PATHS` | `acceptance/__init__.py:112`, consumed `:142`, `:212-216` | A filename frozenset excluding paths from the accept git-dirty gate. Commits and reverts nothing. **The accept gate ignoring the accept pipeline's own writes** — the most on-thesis instance in the codebase, in a package this mission already opens. |
| `review/dirty_classifier.py` bundle | `_BENIGN_EXACT_NAMES`, `_BENIGN_PATH_PREFIXES`, `_WP_TASK_PATTERN`, `_ROOT_TASKS_MD_PATTERN` (`:34-58`) | Four mechanisms feeding the review-handoff gate. `_WP_TASK_PATTERN` is a **third** copy of the "is this a WP file" regex — R-012 caught the pair and missed the triple. |
| `_exclude_coord_owned` | `cli/commands/implement_cores.py:195-206` | A third `_drop`/filter sibling alongside the two R-012 already pairs. The same `_drop_if(paths, predicate)` extraction applies. |
| `ignores_primary_coord_residue` | `mission_runtime/artifacts.py:87`, set at `:246/:261/:270` | An exemption-shaped field on the artifact-home contract with **zero consumers outside its defining module** — residue of a previous consolidation attempt. Campsite candidate, and a warning about what "collapse onto the owner" leaves behind. |

**Under-enumerated consumers** for mechanism 3/4: `merge/ordering.py:471` and `lanes/merge.py:680,715`
are **`merge/`-package** files absent from the plan's structure map and from the owner contract's
Surfaces list. A work package sized against the documented surfaces under-sizes and collides with
the `merge/`-package sequencing rule.

**The derivation rule** (to be pinned by the ratchet): *every frozenset, tuple, or compiled regex
of filenames, basenames, suffixes, or path prefixes that is consulted by a dirty-state or
churn-classification predicate.* Mechanically decidable by AST scan; would have caught the ninth,
tenth and eleventh without an audit.

**Consequence for NFR-006 / SC-004 / FR-013**: the ratchet is a **negative structural scan** with
an explicit registry of known-remaining mechanisms and a budget that only decreases. This
deliberately resolves the NFR-008 tension in favour of shipping: "no new filename list feeds a
dirty gate" is genuinely a structural property and cannot be observed behaviourally — asserting
both in owner contract C9 was incoherent. Negative structural invariants over a shrinking registry
are the refactor-stable form this project already sanctions.

**Sequencing consequence**: the ratchet lands EARLY — immediately after the owner, before the
first retirement — pre-populated with every known mechanism. Each retirement deletes its own row.
A mission that stops at 4-of-8 then leaves a codebase strictly better than it found: smaller
registry, closed door. Under the original "ratchet last" ordering, the same stall would leave the
owner PLUS the surviving exemptions PLUS the ones nobody counted — one more compensating
mechanism than we started with, arrived at by executing the plan faithfully.

**NOT golden-count mode.** An earlier proposal had each retirement decrement a golden integer.
Rejected: it reinstates the exact hand-derived oracle this finding repudiates, makes every
retirement work package co-own the ratchet file, and collides with the golden-count ban gate.
Enumerated-row deletion gives the same early-landing benefit with conflict-cheap per-WP diffs.


---

## R-015 — Enforcement of post-consolidation deferral is EXTERNAL (2026-07-23)

**Decision (operator)**: the mission loop does not enforce post-consolidation verification. A CI
**consistency check**, at the front of the quality run, fails any pull request that still carries
a dangling `deferred_to_consolidation` element. The deferral is **disclosed to the operator at
assignment time** so downstream repositories know they need an equivalent gate.

**Why the loop cannot do it — measured, not argued.** `overall_verdict` has exactly one consumer
in `src/` (`acceptance/gates_core.py:311`), inside the accept gate. `read_acceptance_matrix` is
consumed only by `acceptance/gates_core.py` and `acceptance/summary_core.py`. Both run
**pre-consolidation**. `grep -rn "accept" src/specify_cli/merge/` returns no real coupling.
Nothing reads the acceptance matrix after `spec-kitty merge`. The previously recommended enforcer
— "the matrix cannot reach a terminal verdict while deferrals remain" — would therefore block at
the only gate that reads it, which is the gate that *created* the deferral and which by design
must not block on it. It was circular, and is withdrawn.

**Why CI-on-PR is the right home.** The PR is the first point where the consolidated tree and the
acceptance artifact are both present and something automated reads them. It needs no new abort
path inside consolidation (preserving the C7 decoupling), no new CLI verb, and no reliance on an
agent remembering to dispatch an Op. It also matches where the blast-radius argument already
pointed: a violation blocks the PR.

**Why disclosure is a requirement and not a nicety.** Spec Kitty ships to other people's
repositories. This project's CI check will not exist there. An enforcement model that works only
upstream, applied silently, would export precisely the failure this mission exists to remove — a
gate that looks authoritative and verifies nothing. FR-017 therefore makes the tool state the
contract at the moment it assigns the status: *the loop will not verify this; here is the gate you
need.*

**Accepted trade-off**: between assignment and the PR check, a deferred invariant is genuinely
unverified, and a repository that never adds the gate never verifies it. That is honest and
visible, rather than false and invisible. The prior design asserted a constraint no code could
express; this one states a limitation and tells the user how to close it.

**Alternatives considered**: fire it from `post_merge/retrospective_terminus.py` (already runs
automatically post-consolidation, outside the consolidation transaction) — a reasonable second home, but
it enforces only for missions that reach the retrospective, and it is invisible to downstream
repos in the same way. Rejected in favour of a gate the user can see and own.


---

## R-016 — Four scope decisions (operator, 2026-07-23)

**IC-04 has zero `merge/` footprint.** The post-consolidation Op reads the consolidated tree and
the matrix; nothing in `merge/` changes. Now that enforcement is an external CI check (R-015),
consolidation does not need to know the Op exists. This is what actually delivers the disjoint
`owned_files` that decision `DM-01KY7AKXNJZCB2J2W411YM3B9F` claimed — that claim held only under
the no-call-in reading, and the plan had been carrying both readings simultaneously. Supersedes
the "narrow call-in" shape in that record and in `tracers/design-decisions.md`; both are
historical logs and are left unedited.

**FR-014 writes a truthful sentinel.** Migration sets `provenance_origin: legacy_unrecorded` (a separate nullable field — NOT a `verified_surface_kind` value, since `TopologySurface`'s anti-phantom rule forbids an unresolvable member; corrected after the first delta review)
for the 40 pre-schema results, meaning *"recorded before provenance existed; the originating
surface is unknown"*. This is the one option that is neither grandfathering (two regimes forever)
nor fabrication (inventing a surface we cannot know). The sentinel is enumerable, so the debt is
visible rather than hidden, and one validity regime holds from the migration forward.

**FR-015 becomes a first-class lifecycle operation, not a migration escape hatch.** Archiving a
completed or abandoned mission is independently useful; scoping it as "the thing you do when
migration fails" would have made it an ungoverned exemption reachable from the migration's own
failure path. As a general capability it still carries guards — refused for a non-terminal
mission, refused while any invariant is `still_present`, recorded with operator/timestamp/reason,
and archived missions stay enumerable. Note this is a deliberate scope *expansion*, accepted
because the guarded general form is safer than the narrow ungoverned one. Priority set to Medium:
with FR-014's sentinel, no mission is blocked by an unmigratable matrix, so archiving is no longer
on the critical path.

**The translation seam is consolidating, not additive (IC-11).** It consumes the existing
`probe_coord_state` / `CoordState` classifier rather than writing a new one beside it, and
repoints or demolishes every translator it touches in the same pass, registering survivors in the
ratchet registry. The failure mode being avoided is documented in this very codebase:
`_resolve_review_cycle_read_dir` was added by a prior consolidation-shaped fix (#2646/#2275) and
directly produced #2885. A seam that leaves twelve translators alive gives the next contributor a
thirteenth precedent instead of removing twelve.

---

## R-017 — Mission stop-line: one mission, ratchet-first (operator, 2026-07-23)

**Decision**: keep this as ONE mission. Land the exemption registry + ratchet **second**,
immediately after the tool-artifact owner and before the first retirement.

**The risk being answered**: an architecture-scout review named the single most likely failure —
not producing something wrong, but producing two thirds of something right and stopping. The plan
is back-loaded and largely serial: 18 FRs, 13 concerns, ~18 work packages, ≥26 production modules,
two external dependencies, a schema migration over 153 files, and a mission that dogfoods coord
topology so its own lifecycle friction sits on the critical path.

Under the original "ratchet last" ordering, a stall leaves the codebase carrying the owner **plus**
the surviving exemptions **plus** the ones nobody counted — one more compensating mechanism than
it started with, reached by executing the plan faithfully, and the next contributor finds *more*
precedents for "add it to the list" rather than fewer.

**Why ratchet-first dissolves that rather than mitigating it**:

1. The class is closed against **new** additions from week one — which is the actual content of
   User Story 5, currently scheduled last.
2. The registry becomes the machine oracle R-012 said nobody had written, so the census stops
   being hand-derived. Three successive hand counts produced 8, then 9, then ≥11.
3. Every retirement work package gains a pre-existing red to turn green — red-first discipline,
   which the original ordering structurally denied them.
4. A stall at **any** point leaves a strictly better codebase: smaller registry, closed door.

**Alternatives considered**: split into a seam mission and a retirement mission (rejected — the
exemption class stays open across a mission boundary, which is how it grew to eleven); split by
deferring everything touching the `merge/` package (rejected — retirement group (c) is inseparable
by contract, so this fractures a mechanism the contract forbids splitting); build the owner and
ratchet but retire nothing (rejected as unnecessary once ratchet-first makes partial delivery safe).

**Accepted trade-off**: the mission stays large, and a stall is still possible. What changes is
that a stall is no longer *harmful* — the door is shut before the retirements begin.
