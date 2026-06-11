# Plan Review — Architecture & Design Conformance (architect-alphonso)

**Mission:** tooling-stability-guard-coherence-01KTRC04 · **Reviewed:** 2026-06-10, post-plan
**Lens:** verify amendments A-1..A-8 are faithfully encoded in spec+plan; review the plan's own design quality;
adjudicate the three peer reviews (randy/pedro/debby) where they touch architecture.
**Code re-inspected this pass:** `git/commit_helpers.py:350-500,855-985`, `coordination/{transaction,status_transition,types,policy}.py`,
`status/bootstrap.py`, `cli/commands/agent/{workflow,mission}.py`, `invocation/executor.py:438`, `mission_runtime/context.py:51-130`,
`mission_runtime/resolution.py:494`, `cli/commands/implement.py:436` (`_resolve_placement_ref`), `policy/merge_gates.py:26-33`,
`charter_runtime/lint/findings.py:11`, ADR 2026-06-03-2 Decision 2.

---

## VERDICT: APPROVE-WITH-CONDITIONS (proceed to /spec-kitty.tasks)

The plan faithfully encodes A-1..A-8 and is the right architectural shape: spine = `safe_commit(CommitTarget)`,
policy in Shared Kernel, ATDD-first, strangler discipline, structured findings carrier, inventory-first DRG.
The two unifying anchors I asked for in intake (Strangler-Step-7 framing; capability-not-message principle)
are present and load-bearing. **Three conditions must land at tasks-time before IC-02 implements**, all flowing
from one root cause: *the plan's escape-hatch census is incomplete*. It models only the message-prefix channel
and treats `GuardCapability` as the whole privilege surface, but the live code carries **four more privilege
channels** the strangle must fold or the consolidation is cosmetic (recurrence of failure-mode 1). Details in Q2/Q3.

---

## Q1 — Are amendments A-1..A-8 faithfully encoded? (dilution check)

| Amendment | Encoded in | Faithful? |
|-----------|-----------|-----------|
| A-1 CommitTarget re-anchor + SK entry-point decision | FR-001, D1, plan Summary, IC-02 | **YES** — D1 settles SK policy module + entry-point-stays. No dilution. |
| A-2 no message-content privilege + #1334 permanent test | FR-008, C-GUARD-2, IC-01/IC-02, data-model GuardCapability | **YES** on the message-prefix channel. **PARTIAL** on the principle — see F-1: other content channels exist. |
| A-3 legitimacy = resolved placement, thread specify/plan/finalize | FR-003, C-GUARD-3, IC-04 | **YES** as written; **mechanism under-specified** — see F-2 (no `wp_id` pre-tasks). |
| A-4 fold #1330 (FR-002) + #1355 (SC-1/NFR-004) | FR-002, NFR-004, SC-1, issue-matrix rows | **YES** — both folded with matrix rows. |
| A-5 structured findings carrier + canonical severity enum | FR-004, D3, data-model §2, C-FIND-1/2 | **YES** — but severity enum **mints a 9th vocabulary**; see F-4. |
| A-6 narrow FR-006 to health-render extraction | FR-006, IC-07, C-DOC-1 | **YES** — full split explicitly out of scope. Clean. |
| A-7 FR-007 real surface + consumer-migration AC; shape→plan | FR-007, D2, IC-08, C-DRG-1 | **YES** — `Provenanced[T]` chosen, inventory-first, migration in AC. |
| A-8 ADR addendum (resolver home drift) | FR-009, IC-09 | **YES** — and should also capture the CommitTarget *shape* drift; see F-3. |

**No amendment is dropped.** Two are encoded but under-powered (A-2 principle, A-3 mechanism) — conditions below.

## Q2 — D1 mechanism/policy split + the GuardCapability authorization question (THE deep one)

**D1 split is coherent and correct.** Policy in `core/commit_guard.py` (Shared Kernel), mechanism/entry-point
in `git/commit_helpers.py`. Dependency direction is right (everything imports *down* into SK; an Execution-domain
home would force planning→runtime imports the boundary tests forbid). `evaluate(CommitTarget, protection_state,
capability) → GuardVerdict` is a pure function — exactly the OHS-facade shape doc-17 prescribes. Keep it.

**The authorization adjudication — ASSERT-AT-SURFACE vs DERIVE:**

The data-model has `GuardCapability.kind ∈ {standard, release_flow, upgrade_bookkeeping, merge_bookkeeping}`
*supplied explicitly by the calling surface*. The deep question: an in-process LLM-agent following instructions
can construct `GuardCapability(kind=release_flow)` as trivially as it can craft a `release:` commit message.
So does asserting-at-surface actually buy anything over the message-prefix channel we're deleting?

**Adjudication: ASSERT-AT-SURFACE is correct, but only because of *where* the assertion lives — and the plan
must make that explicit (currently it does not).** The threat model is NOT "malicious code"; against in-process
malicious code no in-process guard wins, and that's out of scope. The real threat is **failure-mode 1: an
agent/operator takes the path of least resistance and the privilege leaks to a surface that shouldn't have it.**
A commit *message* is caller-controlled *free text on every single commit* — the privilege rides data that flows
through the whole toolchain, so any caller anywhere trivially trips it (that is literally #1334). A capability
*parameter* is different in kind: it is **named, typed, greppable, and defaults to `standard`**. The privilege
is now visible at exactly the ~6 call sites that pass a non-standard value, and the #1355 import-boundary ratchet
+ IC-10 review can *enumerate and defend each one*. That is the whole game: not cryptographic unforgeability, but
**reducing the privilege surface from "every commit message" to "an auditable handful of explicit call sites."**

DERIVE-from-`CommitTarget.kind` is **insufficient and must be rejected as the sole source.** `CommitTarget.kind`
is `{primary, coordination, flattened}` — a *topology* classification, not an *operation-intent* classification.
The legitimate privileged flows (release tagging, upgrade bookkeeping, merge done-transitions) are orthogonal to
topology: a release commit and a merge-bookkeeping commit can both target a `primary` ref. You cannot derive
"this is the release flow" from "the ref is the primary branch." So capability MUST be asserted. **Recommended
refinement (condition C-A):** the verdict should be a function of *both* — `evaluate` derives the *baseline*
allow/deny from `CommitTarget` (is this ref the resolved placement?) and consults `capability` ONLY to authorize
the narrow bookkeeping exceptions. Capability can never *expand* reach beyond placement for the protected-push
invariant (data-model already states "no capability can grant direct-push-to-origin/main" — good; keep it as a
hard invariant in code, not a policy branch).

**F-1 (HIGH) — the capability model under-counts the live privilege channels.** I inventoried the actual escape
hatches in the code; the plan names ONE (message-prefix). There are **five**:
1. `_is_protected_branch_exception` message-prefix channel (`commit_helpers.py:466`) — plan covers this. ✓
2. `allow_completed_op_on_protected_branch: bool` (`commit_helpers.py:862`) — used by `invocation/executor.py:448`
   (op-record auto-commit). **Plan's GuardCapability has `merge_bookkeeping` but does NOT map this flow.**
3. `allow_protected_branch_in_test_mode: bool` (`commit_helpers.py:861`) — **propagates through 6 modules**
   (`status/bootstrap.py`, `coordination/{transaction,status_transition,types,policy}.py`) and is passed
   **`=True` at PRODUCTION call sites**, not just tests: `agent/workflow.py:415,1476`, `agent/mission.py:776,2989,3171`.
   This is a far wider rim than "two surviving bool escape-hatches in commit_helpers." It is the single biggest
   blast-radius item in IC-02 and the plan does not surface it.
4. `_is_completed_op_record_exception` (`commit_helpers.py:~487`) — a **second content-derived privilege channel**:
   it reads the op-record *file contents* off `worktree_root` to decide the exception. The plan's "no privilege
   from message content" (FR-008) does not name *file-content*-derived privilege. Same anti-pattern, different field.
5. `SPEC_KITTY_TEST_MODE` / `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS` env hatches (`_test_mode_allows_protected_branch`).
   These are env-controlled, not caller-identity — they belong as an explicit `test_mode` capability, not an ambient env read.

**Condition C-A (HIGH, tasks-time):** IC-02's caller census task MUST inventory ALL FIVE channels (not just the
prefix list) and the `GuardCapability` enum + the FR-008 acceptance criteria MUST be widened to: *no privilege
derived from any caller-controlled data — message text, op-record file content, OR ambient env — except an
explicit typed capability defaulted to `standard`.* Otherwise IC-02 deletes the prefix channel, passes SC-1
verbatim, and four privilege channels survive (exact recurrence of intake failure-mode 1). This is debby's
"capability grants must wire atomically" finding, sharpened: the wiring set is 5 channels across ~8 modules.

## Q3 — IC sequencing + hidden coupling

**Sequencing is sound.** IC-01 first (ATDD), IC-02 spine, IC-03/04 ride it, IC-05..08 independent lanes, IC-09
closes, IC-10 reviews. The strangler ordering (delete prefix channel only after conversion + green suite) is
explicit and correct (Charter Check Burn-down PASS is real, not aspirational).

**F-2 (HIGH) — IC-02↔IC-04 destination-authority coupling + pedro's `resolve_placement_only`.** I verified the
mechanism gap pedro flagged. `resolve_action_context(repo_root, action, feature, wp_id, …)` (`resolution.py:494`)
assembles `ArtifactPlacementFragment.placement_ref` from `branch_ref` — but the planning phase (specify / plan /
finalize-tasks) **has no `wp_id`** (no WPs exist yet) and today resolves its destination via
`_resolve_planning_branch` → `load_mission_target_branch(meta.json)` (`agent/mission.py:627`), a *separate*
authority from the placement fragment. So IC-04 cannot simply "thread the same `ArtifactPlacementFragment`" — the
implement-side fragment is WP-scoped and doesn't exist pre-tasks.

There is already a precedent helper: `implement.py:436 _resolve_placement_ref` calls the full resolver and falls
back to `None`. Pedro's `resolve_placement_only()` proposal is the right shape for the *planning* phase: a
WP-less placement resolution that returns the `CommitTarget` for planning artifacts.

**Adjudication — does `resolve_placement_only` violate C-CTX-1 (one resolver)?** **NO, provided it is implemented
as a thin projection over the SAME resolver, not a parallel one.** C-CTX-1 forbids a *second resolution authority*,
not a *narrower entry point*. The legitimate framing: `resolve_placement_only(repo_root, feature)` lives in
`mission_runtime/resolution.py` beside `resolve_action_context`, shares `_resolve_mission_slug` +
`get_feature_target_branch` + `_assemble_artifact_placement_fragment`, and returns just the `CommitTarget`. It is
an **op-composite / convenience projection**, exactly like `_resolve_placement_ref` already is on the implement
side. The violating alternative — which the plan must explicitly forbid — is IC-04 re-deriving the destination
from `meta.json`/git *inside the planning commit path* (that is the C-005 anti-pattern and the #1784 catch-22 root:
`_resolve_planning_branch` reading one authority while placement reads another). **Condition C-B (HIGH, tasks-time):**
IC-04 must (1) add `resolve_placement_only` (or equivalent WP-less projection) **in `mission_runtime/resolution.py`,
sharing the internal helpers** — NOT a new authority; (2) retire `_resolve_planning_branch`'s independent
meta.json read in favor of the projection so finalize-tasks and specify/plan read the SAME `CommitTarget` (this
is the literal #1784 fix); (3) IC-02 and IC-04 must agree the guard's input is this `CommitTarget` BEFORE IC-04
implements — flag the dependency as IC-04 depends-on IC-02 *and* a shared resolution-API task. Plan currently lists
IC-04 depends-on IC-02 only; the shared-resolver task is the hidden coupling.

**F-3 (MED) — CommitTarget shape drift vs the guard's needs.** ADR 2026-06-03-2 Decision 2 specifies
`CommitTarget = (worktree_root: Path, destination_ref)`. The **as-built** `CommitTarget` (`context.py:67`) is
`(ref: str, kind: CommitTargetKind)` — **no `worktree_root`**. But `safe_commit`'s protection decision needs
`worktree_root` (it is a current parameter, and `_is_spec_kitty_project(repo_path)` gates the whole guard). So
`evaluate(CommitTarget, …)` as specced in data-model cannot get `worktree_root` from the `CommitTarget` alone.
Either `protection_state` carries it, or IC-02 passes `worktree_root` alongside. This is fine **but must be
decided explicitly**, and the FR-009 ADR addendum must record BOTH drifts (home path AND the `(ref,kind)` vs
`(worktree_root, destination_ref)` shape change), or the next implementer trusts a dead ADR signature.
**Condition C-C (MED, tasks-time):** IC-02 task spec states the exact `evaluate` signature incl. where
`worktree_root` enters; IC-09's FR-009 addendum records the shape drift, not just the path drift.

**IC-08 ripple — pedro says 2 consumers, not 3 layers.** Plan/spec/data-model all say "3 layers." I did not
fully re-census the `getattr(node, "provenance", None)` consumers this pass, but the design already mandates
inventory-FIRST with STOP-and-escalate (IC-08 risk line) — so the count is empirically gated at implement time
regardless of whether the prose says 2 or 3. **Low concern**; recommend the tasks doc say "inventory-determined
(prose estimate: 2–3)" rather than asserting 3, to avoid a false ratchet. Architecturally `Provenanced[T]` (D2)
is the right call over a declared optional field: it keeps provenance *out* of the domain model (DRGNode/DRGEdge
stay pure), which is the doc-17 separation. Endorse D2.

## Q4 — Contracts complete / testable? Missing negative cases?

Contracts are behavioural, testable, and cover the spine well (C-GUARD-1..5, C-FIND-1/2, C-STAT-1, C-DRG-1,
C-DOC-1). C-GUARD-4 (the C-003 ratchet) is the crown jewel and correctly authored-first. **Missing negatives:**

- **N-1 (HIGH):** no contract covers the `allow_*` bool / op-record-content / env channels (F-1 items 2–5). Add a
  C-GUARD-2 clause: *a commit to a protected ref carrying ONLY a bool flag / op-record file content / test-mode env
  but NO explicit capability is refused* — and a positive: *the op-record done-transition flow succeeds via an
  explicit `merge_bookkeeping`/`completed_op` capability.* Without this, the bool channels survive uncontracted.
- **N-2 (MED):** C-FIND-2 covers `counts≠tally` and unknown severity, but not **`verdict_hint` disagreeing with the
  computed verdict** (data-model says hint is "cross-checked"). Add: *hint says `ready` but a `critical` finding is
  present → verdict is `blocked` AND a hint-mismatch warning is emitted* (or define silent-override). Testable, currently ambiguous.
- **N-3 (MED):** C-GUARD-3 asserts the success path but not the **finalize-tasks read-side** negative: *finalize-tasks
  resolving a DIFFERENT ref than specify committed to → loud error, not silent "spec.md not found."* That IS #1784;
  contract should assert the failure is diagnosable, not just that the happy path works.
- **N-4 (LOW):** no contract for IC-05's legacy-report write-path. debby's point is right: `verdict: unknown` should
  apply to the **write/record path only** — a legacy report being *read* for display shouldn't hard-fail. Add a
  C-FIND clause scoping the loud failure to record-time.

## Q5 — Adjudicate randy's reuse findings (architectural)

**R-1 (HIGH) — Severity vocabulary: REUSE `charter_runtime/lint/findings.py::SEVERITY_ORDER`, do NOT mint a 9th.**
I confirmed `SEVERITY_ORDER = {"low":0,"medium":1,"high":2,"critical":3}` already exists and already encodes the
blocking ladder. The findings/v1 enum in data-model is `critical|high|medium|low|info`. The **only** delta is
`info` (a non-blocking presentational level). Adjudication: extend/import the existing ordering rather than declare
a parallel enum. Concretely — define the analysis-findings severity as `{critical,high,medium,low}` reusing the
lint ordering for the blocking decision (`any sev with SEVERITY_ORDER[sev] >= SEVERITY_ORDER["high"] → blocked`),
and treat `info` as an explicitly-non-ordered presentational tag OR fold it to `low`. Minting a 9th Severity model
is the exact "parallel mechanism" NFR-003/C-002 forbids; randy is correct and this is **architecturally binding**.
**Condition C-D (HIGH, tasks-time):** IC-05 imports the canonical ordering; the blocking ladder is not re-declared.
(Caveat: `lint/findings` is the *charter-lint* domain; if a true cross-domain import is awkward, promote
`SEVERITY_ORDER` to a shared kernel constant and have BOTH consume it — but do not duplicate the ladder.)

**R-2 (MED) — GuardVerdict vs GateVerdict/GateResult: do NOT reuse; they are different concepts. Endorse the new
GuardVerdict.** I inspected `policy/merge_gates.py:26-33`: `GateVerdict = {pass,fail,skip}` and `GateResult` model
a *merge-gate evaluation* (gate_name, blocking, MergeGateEvaluation aggregate) — a different bounded context
(merge policy), a different shape (`allowed`/`resolved_destination`/`reason` vs `verdict`/`blocking`/`gate_name`),
and a different lifecycle. Forcing GuardVerdict onto GateResult would couple the commit-guard SK module to the
merge-policy domain — a worse coupling than the modest duplication. randy's "near-twins" observation is real at the
*name* level but the concepts are genuinely distinct. **Keep GuardVerdict**, but: (a) name it unambiguously
(`CommitGuardVerdict`) to avoid future confusion with GateVerdict; (b) IC-10 should confirm no *third* verdict type
creeps in. Low-cost divergence accepted.

**R-3 — retire `SPEC_KITTY_INFER_DESTINATION_REF` rather than fix it:** Endorse. The plan already offers this
(IC-03: "or that env-var path retired in favor of explicit/context-resolved destination"). Make it the *default*
choice, not the alternative — env-inferred destination is precisely the ambient-data privilege anti-pattern (it's
a cousin of F-1 item 5). Resolve destination from the `CommitTarget`/placement, full stop.

## Peer-finding adjudication summary
- **randy** — Severity reuse: **UPHELD/binding** (C-D). GuardVerdict≠GateVerdict: **OVERRULED on reuse, upheld on
  naming** (rename to CommitGuardVerdict). Bool escape-hatches: **UPHELD and EXPANDED** — there are 5 channels, not 2 (F-1).
  Retire INFER_DESTINATION_REF: **UPHELD, make it the default**.
- **pedro** — `resolve_placement_only`: **UPHELD as a shared-resolver projection, NOT a parallel resolver** (C-B);
  it does not violate C-CTX-1 if it shares the internal helpers. setup-plan/finalize bypass `resolve_action_context`:
  **CONFIRMED in code** (`_resolve_planning_branch` reads meta.json directly) — this is the IC-04 hidden coupling.
  IC-08 "2 not 3 consumers": **LOW — let inventory decide** (relabel prose estimate).
- **debby** — atomic capability wiring: **UPHELD and SHARPENED** (5 channels / 8 modules, F-1/C-A). Defer prefix-channel
  deletion to IC-09: **partially overruled** — the plan correctly deletes it in IC-02 *after* conversion+green-suite
  (strangler), which is the right granularity; what must be atomic is *capability wiring before deletion*, and that's
  within IC-02. Legacy-report loud-failure = write-path only: **UPHELD** (N-4).

## Recommended plan/tasks-time actions (ranked)
1. **C-A (HIGH):** Widen IC-02 census + GuardCapability + FR-008 AC to all 5 privilege channels (message-prefix,
   `allow_completed_op`, `allow_protected_branch_in_test_mode` across 8 modules, op-record-file-content, env hatches).
   Add contract N-1. This is the make-or-break condition.
2. **C-B (HIGH):** IC-04 adds `resolve_placement_only` as a shared projection in `mission_runtime/resolution.py`,
   retires `_resolve_planning_branch`'s independent meta.json authority, and depends on a shared IC-02/IC-04
   resolution-API agreement task. Add contract N-3.
3. **C-D (HIGH):** IC-05 reuses `SEVERITY_ORDER` (no 9th vocabulary); promote to shared kernel if cross-domain import
   is awkward. Make INFER_DESTINATION_REF retirement the default in IC-03.
4. **C-C (MED):** Pin the exact `evaluate(...)` signature incl. `worktree_root` source; FR-009 addendum records the
   `(ref,kind)` vs `(worktree_root,destination_ref)` CommitTarget shape drift, not just the resolver-home path drift.
5. **N-2 / N-4 (MED):** Add `verdict_hint` disagreement contract; scope IC-05 loud-failure to record/write path only.
6. **Naming (LOW):** `GuardVerdict` → `CommitGuardVerdict`. Relabel IC-08 ripple estimate as inventory-determined.

None of these is a re-spec; all are tasks-time tightenings. The plan's bones are correct — these conditions keep
IC-02 from shipping a cosmetic consolidation and IC-04 from reintroducing the dual-authority that caused #1784.
