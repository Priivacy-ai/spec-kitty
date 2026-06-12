# Architect Review — Spec vs Emergent Design (architect-alphonso)

**Mission:** tooling-stability-guard-coherence-01KTRC04 · **Reviewed:** 2026-06-10, pre-plan
**Inputs:** spec.md (FR-001..007); tickets #1819/#1820/#1821/#1796/#1334/#1777/#1784/#1631/#1623/#1624 + parent #1619;
design corpus: doc-17 consolidated domain model (bounded domains, per-domain Contexts, Shared Kernel, OHS-facade
entry points), ADR 2026-06-03-2 (ExecutionContext owner + **CommitTarget**), 01KTPKST outcome (fragments built).
Code surfaces inspected: `git/commit_helpers.py` (1,126 LOC, 15 guard caller-files), `cli/commands/doctor.py`
(3,271 LOC), `doctrine/drg/merge.py` (494 LOC), `analysis_report.py` (313 LOC), `status/aggregate.py`.

**Verdict: the spec is directionally right and well-bounded, but it is missing its single unifying design
anchor — and without it, FR-001/FR-003 can be "satisfied" in ways that violate the emergent architecture.**

---

## 1. The high-leverage finding: this mission IS "Strangler Step 7"

ADR 2026-06-03-2, Decision 2 (ratified): *"`CommitTarget` is a self-validating value type pairing
`(worktree_root, destination_ref)`. It will replace the two-argument calling convention of `safe_commit`
with a single atomic argument."* — explicitly planned, explicitly deferred ("Strangler Step 7").

01KTPKST **built** `CommitTarget` (`mission_runtime.context`, carried on `BranchRefFragment.destination_ref`
and `ArtifactPlacementFragment.placement_ref`). What it did NOT do is make `safe_commit` consume it.

**That one change is the consolidation FR-001 asks for, and it closes the ticket cluster as a corollary:**

| Ticket | How CommitTarget-consumption resolves it |
|--------|------------------------------------------|
| #1820 dir-args / `--to-branch` | paths validate against `worktree_root`; `destination_ref` is explicit, no env-var inference |
| #1334 message-prefix bypass | privilege becomes **structural** (the resolved target), the message-content channel is deleted |
| #1777 specify-on-protected-main | the guard *asks the context* where planning artifacts go (`placement_ref`) instead of refuse-and-advise |
| #1784 finalize-tasks catch-22 | specify/plan/finalize all resolve placement from the SAME fragment → no branch disagreement |
| #1631 "protected branch nonsense" | guard messages can state the *correct* destination instead of advising a lane that doesn't exist yet |

**Guidance (binding for plan):** Re-anchor FR-001 as *"the consolidated guard consumes the resolved
`CommitTarget`/`ArtifactPlacementFragment` from the `MissionExecutionContext` (ADR 2026-06-03-2 Step 7)"*
— NOT "build one coherent guard" in the abstract. An abstract reading invites a new ad-hoc mechanism,
which is the C-005 anti-pattern this whole epic exists to kill.

## 2. Design-conformance gaps in the spec

### G-1 (HIGH) — Capability-vs-message principle is absent
#1334's root cause is the precise design rule: *privilege is encoded in caller-controlled data (the commit
message) rather than caller identity/capability.* FR-003 says "no contradictory guards" but does not outlaw
the message-content privilege channel. **Failure mode:** an implementer "consolidates" the prefix exceptions
into one tidy module — passing SC-1 verbatim while preserving the vulnerability.
**Fix:** add an explicit requirement + negative AC: *the guard MUST NOT derive any privilege from commit-message
content; the #1334 live repro becomes a permanent regression test.* The legitimate cases the prefixes served
(release flow, upgrade bookkeeping, merge done-transitions) must be re-expressed as **capabilities**
(caller-identity flags or, better, the resolved CommitTarget kind).

### G-2 (HIGH) — Guard's bounded-context home + entry-point shape undecided
Doc-17: each domain is a *bounded module with API entry points* (OHS facades); cross-domain artefacts pass
through entry points. Today the guard is **sprinkled at the rim** — `assert_not_protected_branch` at the CLI,
`_is_protected_branch_exception` inside the helper, ad-hoc checks at some of the **15 caller files** — which
is exactly how #1334 happened (hardening the CLI but not the helper). **Principle: enforce at the facade,
not at the rim.** The plan must decide the guard's home: the **Shared Kernel** (it is a path/identity/ref
resolver concern consumed cross-domain — my recommendation) with `safe_commit(CommitTarget, …)` as the
single entry point, every caller passing through it.
**Failure mode if undecided:** consolidation lands in an arbitrary module and becomes a *new* rim.

### G-3 (MED) — #1777/#1784 are placement problems wearing a guard costume
The catch-22 is not "the guard is too strict"; it is "the commit path doesn't know where planning artifacts
belong." 01KTPKST solved this *structurally* for implement/record-analysis via `ArtifactPlacementFragment`.
The right fix is to thread the SAME placement resolution into the specify/plan/finalize-tasks commit paths.
**Failure mode:** treating these tickets as guard-*relaxation* — which weakens protection and violates C-003.
FR-003's "no longer blocks legitimate commits" must define legitimacy: *legitimate = the resolved
CommitTarget/placement says this ref is the intended destination.*

### G-4 (MED) — Missing intake: #1796's other children
#1796 lists **#1330** (safe-commit path handling for directory/bulk commits — directly overlaps FR-002's
dir-args) and **#1355** (tighten `test_safe_commit_import_boundary` once callers are fixed — literally this
mission's exit criterion). Neither is in the spec or issue-matrix. **Fix:** fold #1330 into FR-002 and #1355
into SC-1/NFR-004 (or defer each with explicit rationale); add issue-matrix rows.

### G-5 (MED) — FR-004 should parse *structure*, not better-parse *prose*
The analysis report is a **communication artefact** crossing into Mission Management; verdict derivation
belongs behind the MM facade with a **declared schema**. `write_analysis_report` already emits YAML
frontmatter — the verdict/counts should be computed from structured input at record time (or a declared
findings-table contract with a canonical severity vocabulary), not from smarter markdown scraping.
**Failure mode of "just parse the table":** column-reorder/severity-vocab drift re-breaks it silently.
Specify the canonical severity enum + the structured carrier in plan.

### G-6 (LOW) — FR-006 scope-creep risk
`doctor.py` is 3,271 LOC, but ticket #1623 scopes ONLY the doctrine health-render extraction (adversarial
finding I-10: pure extraction beside `_doctrine_health.py`, no behavior change). FR-006's "split the
god-module" reads broader. **Fix:** tighten FR-006 to the ticketed extraction; declare the full split
explicitly out of scope (it remains tracked by #1623's parent debt).

### G-7 (LOW) — FR-007 precision + real blast radius
`_tag_source` lives in **`src/doctrine/drg/merge.py`** (Governance domain), not the merge command. Per the
ticket, the generic TypeVar already landed; the remaining work — a typed `Provenanced[T]` carrier — **changes
the public `DRGNode`/`DRGEdge` shape and ripples through every `getattr(node, "provenance", None)` consumer
across 3 layers.** This is a public-shape change in a bounded context, not a small typing chore. The ticket
itself offers the lighter alternative (a declared optional field on the models). **Plan decision required:**
wrapper vs declared-field; AC must include the consumer migration either way.

### G-8 (LOW) — ADR drift
ADR 2026-06-03-2 names `src/specify_cli/core/execution_context.py` as `resolve_action_context`'s home; the
actual post-boundary home is `src/mission_runtime/resolution.py`. Cheap fix: an ADR addendum in this mission
prevents the next implementer from anchoring on a dead path.

## 3. Failure modes to design against (plan-time)

1. **Rim-hardening recurrence** (the #1334 pattern): fixing the CLI/most-visible caller while the helper or
   another of the 15 caller files keeps the old behavior. → Mandate a **caller census** (all 15 files) as the
   first WP task, like 01KTPKST's seam inventory; the import-boundary test (#1355) is the ratchet.
2. **Guard relaxation disguised as coherence** (G-3): protection weakened to make #1777/#1784 pass. → C-003's
   negative tests (direct-push-to-origin/main still blocked; non-placement commits to protected refs still
   refused) must be written FIRST (ATDD, as 01KTPKST did with the parity ratchet).
3. **A second guard mechanism**: building "GuardV2" beside the old one and migrating "later". → Strangler
   discipline: convert callers onto the single entry point, then delete the message-prefix channel; never
   two live guards.
4. **Verdict-parser brittleness** (G-5): if FR-004 ships as regex-on-markdown, it WILL silently regress. →
   structured carrier or declared table contract with schema validation.
5. **DRG public-shape ripple** (G-7): under-scoped typing change breaking doctrine consumers. → inventory the
   `provenance` consumers before choosing wrapper-vs-field.

## 4. High-leverage moves (ranked)

1. **Make `safe_commit(CommitTarget)` the single guard entry point** (ADR Step 7). One value object closes
   five tickets and realizes "API as anti-corruption layer" for the commit path. This is the mission's spine.
2. **Write the C-003 negative suite first** — the protection-preserved ratchet (mirror of 01KTPKST's parity
   ratchet). Cheap, prevents failure modes 1–2 permanently.
3. **Thread `ArtifactPlacementFragment` into the planning-phase commit paths** (specify/plan/finalize-tasks)
   — completes the context-as-passable-object story for the lifecycle's *front half* (01KTPKST did the back half).
4. **Structured analysis-findings carrier** (G-5) — small now, compounding payoff (every future mission's
   analyze gate).
5. Fold #1330/#1355; tighten FR-006; decide G-7's shape; ADR addendum (G-8).

## 5. What the spec gets right (keep)

- FR-005 (#1821) is exactly the context-as-passable-object continuation; correctly framed as threading, not building.
- C-003 ("coherence ≠ removing protection") names the central tension explicitly — rare and valuable.
- The issue-matrix-at-specify-time discipline, per-ticket regression-test NFR-004, and the bounded Out-of-Scope
  (01KTPKST seams, #1738) are all sound.
- Bundling #1623/#1624 as code-health alongside the guard work is fine *provided* G-6/G-7 scoping lands —
  they are independent lanes and won't contend with the guard WPs.

## 6. Recommended spec amendments (for the operator to approve before /spec-kitty.plan)

| # | Amendment |
|---|-----------|
| A-1 | FR-001: re-anchor on CommitTarget consumption (ADR 2026-06-03-2 Step 7); name the Shared-Kernel entry-point decision for plan |
| A-2 | New FR (or FR-003 clause): guard MUST NOT derive privilege from commit-message content; #1334 repro = permanent negative test |
| A-3 | FR-003: define "legitimate" via resolved placement (`ArtifactPlacementFragment`/CommitTarget), threading it through specify/plan/finalize-tasks |
| A-4 | FR-002: fold #1330; SC-1/NFR-004: fold #1355 (import-boundary ratchet); add both to issue-matrix |
| A-5 | FR-004: require a structured findings carrier (frontmatter/schema + canonical severity enum), not prose re-parsing |
| A-6 | FR-006: narrow to the ticketed health-render extraction; full doctor split out of scope |
| A-7 | FR-007: name the real surface (`doctrine/drg/merge.py`), require the consumer-migration AC, defer wrapper-vs-field to plan |
| A-8 | Add task: ADR 2026-06-03-2 addendum (resolver home path drift) |
