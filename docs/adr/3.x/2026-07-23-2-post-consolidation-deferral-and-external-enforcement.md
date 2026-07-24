---
title: Post-Consolidation Deferral and External Enforcement of Negative Invariants
status: Accepted
date: '2026-07-23'
---

## Context and Problem Statement

ADR [2026-04-03-3](./2026-04-03-3-feature-acceptance-runs-on-the-integrated-mission-branch.md)
decided that *"Feature QA and `accept` MUST happen on the mission integration branch"*, and
specified the negative-invariant verifier model down to its result vocabulary.

**That decision was never enforced in code, and this ADR does not enforce it literally either —
it addresses the narrower failure the gap produces.** `spec-kitty accept` executes each negative
invariant's `verification_command` from the pre-merge **primary repository root**
(`src/specify_cli/acceptance/gates_core.py:298`, passing a bare `repo_root`). Pre-merge, the
primary tree cannot contain the mission's changes — they live on unmerged lane branches. An
honest invariant whose subject is something the mission *adds* therefore evaluates against a tree
where it structurally cannot be true, is recorded `still_present`, and blocks acceptance
(issue #1834).

The operator-visible consequence is documented and measurable:

* The workaround is to declare no invariants at all. The flagship mission merged immediately
  before this one (`coord-commit-integrity-01KY5JS8`) ships `negative_invariants: []`.
* Across the repository: **153 acceptance matrices, 40 non-`pending` negative invariants in 14
  missions, zero carrying any record of which surface established them.**

A partial fix landed in `b918e66df`: a *recorded* non-`pending` result is preserved rather than
re-judged. But `pending` is the scaffolded default, so an invariant nobody hand-recorded during
review still executes against the wrong tree. The failure was renamed, not removed.

Two further problems block a naive fix:

1. **There is no pre-merge integrated tree to run against.** For a multi-lane mission, lanes are
   independent branches; integration materialises only at lane consolidation. Making the
   verification `cwd` "workspace-aware" would require designating one lane's worktree as the
   integrated tree — fabricating exactly the authority this class of defect is about.
2. **`merge` is a three-sense overloaded term here** (lane consolidation / branch integration /
   publish to origin), so "defer it to merge" does not say which event is being waited on.

## Decision Drivers

* **Honour the existing ADR** — 2026-04-03-3 is Accepted; the gap is enforcement, not intent.
* **Never fabricate an evaluation surface** — a gate must judge a real tree or refuse.
* **Do not add abort paths to consolidation** — the merge executor's compensating-transaction
  machinery is being consolidated concurrently; a new abort trigger inside it is unsafe.
* **Terminology precision** — the name must state which event is awaited.
* **Honest enforcement** — an enforcer that cannot fire is worse than an admitted gap, because it
  reads as a guarantee.
* **Downstream truthfulness** — Spec Kitty runs in repositories that do not share this project's
  CI.

## Considered Options

* **Option 1:** Workspace-aware verification `cwd` — resolve an integrated tree pre-merge.
* **Option 2:** Never overwrite a recorded result (the `b918e66df` half-fix), and stop there.
* **Option 3:** Defer unjudgeable invariants to a **post-consolidation** phase, verified on the
  consolidated mission tree, enforced externally in CI and disclosed at assignment time.

## Decision Outcome

**Chosen option: Option 3.**

Option 1 is rejected as a fiction: the tree it depends on does not exist pre-merge for a
multi-lane mission. Option 2 is already landed and demonstrably insufficient — it protects only
invariants a reviewer remembered to record by hand, and a design that requires a discipline
reminder to enforce a constraint is structurally incomplete.

### Core Decision

1. **`post-consolidation` is the canonical name** for the phase, the surface (`CONSOLIDATED`), and
   the verification that runs there. The bare word *merge* is never used for it. This is the same
   disambiguation discipline already applied to `primary` / `main` / `base`, and is why the
   surface member is `CONSOLIDATED` rather than `MERGED` (see ADR
   [2026-07-23-1](./2026-07-23-1-surface-vocabulary-two-domains-and-topology-surface-rename.md)).

2. **A `pending` invariant whose subject cannot exist in the current surface is recorded
   `deferred_to_consolidation`** with a stated reason — never `still_present`. Deferral is a
   scheduled follow-up, not an absence of information.

3. **Every recorded judgement carries provenance** — the ref and the `TopologySurface` it was
   established against. A judgement without provenance is a validation error. This operationalises
   2026-04-03-3's requirement that evidence *"distinguish absence from verifier failure"*: it also
   distinguishes absence-here from absence-anywhere.

4. **`overall_verdict` gains a fourth value, `pass_pending_consolidation`.** The existing three
   have no assignment satisfying both "must not block acceptance" and "must not silently pass":
   allowing the deferred value yields `pass`, disallowing it yields `fail`, and grouping it with
   `pending` reproduces the block being removed.

5. **Verification runs after consolidation completes, as an ordinary governed Op**, and a violation
   fails **that Op** — not the consolidation. No new CLI verb: it is dispatched through the
   canonical surface (`spec-kitty dispatch`, closed via `profile-invocation complete`), single-agent
   or squad-based like any other. What distinguishes it is when it runs and what it checks.

6. **Enforcement is EXTERNAL to the mission loop.** A CI consistency check, at the front of the
   quality run, fails any pull request still carrying a dangling `deferred_to_consolidation`
   element.

7. **The deferral discloses its own contract at assignment time.** When Spec Kitty assigns
   `deferred_to_consolidation` it must state that the mission loop will not verify it and name the
   gate the operator needs.

### Why enforcement cannot live in the loop — measured

`overall_verdict` has exactly **one** consumer in `src/` (`acceptance/gates_core.py:311`), inside
the accept gate. `read_acceptance_matrix` is consumed only by `acceptance/gates_core.py` and
`acceptance/summary_core.py`. Both run **pre-consolidation**. Nothing reads the acceptance matrix
after `spec-kitty merge`.

An earlier candidate enforcer — *"the matrix cannot reach a terminal verdict while deferrals
remain"* — is therefore **circular**: it blocks at the only gate that reads the artifact, which is
the gate that created the deferral and which by design must not block on it. It is withdrawn and
recorded here so it is not re-proposed.

The pull request is the first point at which the consolidated tree and the acceptance artifact are
both present and something automated reads them. That is where the gate belongs.

### Why disclosure is a requirement, not a courtesy

Spec Kitty ships into other people's repositories, where this project's CI check does not exist.
An enforcement model that works only upstream, applied silently, would export the exact failure
this ADR removes: a gate that looks authoritative and verifies nothing. The tool must therefore
state the contract at the moment it assigns the status.

## Consequences

### Positive

* ADR 2026-04-03-3's intent is finally enforceable: acceptance judges the integrated product,
  because unjudgeable invariants wait for the integrated tree instead of failing against the wrong
  one.
* Command-verified negative invariants become usable, removing the incentive to ship
  `negative_invariants: []`.
* Consolidation gains no new abort path, so the concurrent consolidation of the merge executor's
  two compensating transactions is unaffected.
* Every judgement states its surface, so a reader can tell whether it is still meaningful.

### Negative / accepted trade-offs

* **Between assignment and the PR check, a deferred invariant is genuinely unverified**, and a
  repository that never adds the gate never verifies it. This is accepted as honest and visible,
  in preference to a constraint no code can express.
* Feedback arrives later than acceptance. Late-but-honest is preferred to early-but-wrong; the
  blast radius is bounded because the consolidated tree is the mission/PR branch, not the primary
  branch.
* A fourth verdict value and five new invariant fields require a one-time backfill migration
  across 153 existing matrices, plus an archive path for missions whose recorded state cannot
  migrate honestly — a migration that invented provenance for unknowable surfaces would itself be
  fabricating evidence.

### Neutral

* `deferred_to_consolidation` is not in older readers' `NEGATIVE_INVARIANT_RESULTS`, so an older
  Spec Kitty reading a new matrix computes `fail`. `pass_pending_consolidation` does **not** have
  this problem — `overall_verdict` is excluded from deserialisation and recomputed.

## More Information

* Supersedes nothing, and does **not** implement 2026-04-03-3 literally. That ADR's instruction
  is to relocate the whole `accept` step onto the mission integration branch; this ADR keeps
  `accept` where it is and defers only the **subset of judgements that cannot be true** on the
  pre-consolidation surface. It therefore realises 2026-04-03-3's *intent* — that acceptance
  judges the integrated product rather than an isolated slice — by a narrower mechanism, and
  leaves the relocation question open. Relationship: **inherits the intent of** ADR
  [2026-04-03-3](./2026-04-03-3-feature-acceptance-runs-on-the-integrated-mission-branch.md); does
  not discharge it.
* Surface vocabulary: ADR
  [2026-07-23-1](./2026-07-23-1-surface-vocabulary-two-domains-and-topology-surface-rename.md).
* Issues: #1834 (the live leg), #2885, #2795, #2882.
* Mission: `kitty-specs/lifecycle-gate-execution-context-01KY72GQ/`.
* User-facing guide: [accept-and-merge](../../guides/accept-and-merge.md).
