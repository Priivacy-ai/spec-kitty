# Plan Review — reducer-randy (reduction / duplication / scope-tightness lens)

**Mission:** tooling-stability-guard-coherence-01KTRC04
**Reviewer:** reducer-randy · **Date:** 2026-06-10 · **Branch:** fixups/code-engine-stabilization
**Lens:** net-subtraction honesty, no-parallel-mechanism, scope tightness. Read-only.

---

## VERDICT: APPROVE-WITH-CUTS (severity: MEDIUM)

The mission is **honestly net-additive on net**, not net-subtractive — and that is *fine* for a
stability mission, but the data-model header ("Deletions (net subtraction)") and the spec's framing
oversell subtraction. **Say it out loud this time (per the last-mission lesson): this mission ADDS more
LOC than it removes.** The deletions ledger is *real* but small; the new mechanisms (`commit_guard.py`,
`GuardCapability`, `GuardVerdict`, `analysis-findings/v1`, `Provenanced[T]`) are the bulk of the LOC.

Three concrete reduction/duplication risks must be addressed before implement, and two scope cuts are
recommended. None are blocking the plan's architecture; all are tractable as task-level constraints.

---

## Q1 — New-mechanism audit (does each REPLACE or ACCRETE?)

| New mechanism | Replaces? | Verdict |
|---|---|---|
| `core/commit_guard.py` (`evaluate`) | Yes — absorbs the inline protection block in `safe_commit` (commit_helpers.py:965-995) + `_is_protected_branch_exception` + prefix list. | **NET-NEUTRAL-to-additive.** Legitimate extraction. The inline logic + `_is_protected_branch_exception` (~30 LOC) move out; the new module adds the value objects. Honest if the inline block is *deleted*, not left as a shim. |
| `GuardCapability` (enum) | Replaces the prefix-list channel (`_PROTECTED_BRANCH_COMMIT_EXCEPTIONS`, commit_helpers.py:358-363) + the two `allow_*_on_protected_branch: bool` flags on `safe_commit`. | **ACCRETION RISK (MEDIUM).** Plan adds the enum but does NOT list the two existing bool flags (`allow_protected_branch_in_test_mode`, `allow_completed_op_on_protected_branch`, commit_helpers.py:861-862) in the deletions ledger. A capability enum that lands *beside* two surviving boolean escape-hatches is exactly the parallel-mechanism smell C-002/NFR-003 forbids. **These two flags must fold INTO the capability vocabulary, not coexist with it.** |
| `GuardVerdict` (dataclass) | New. | **DUPLICATION RISK (MEDIUM).** An existing `GateVerdict` (StrEnum) + `GateResult` (frozen dataclass: name/verdict/details/blocking) already live in `src/specify_cli/policy/merge_gates.py:26,33`. `GuardVerdict{allowed, resolved_destination, reason}` is a near-twin of `GateResult`. Not identical (it carries a redirect ref), but the plan should explicitly justify why it is not a `GateResult`/`GateVerdict` variant or a shared base — otherwise we grow a *second* verdict vocabulary in the same `policy/`-adjacent space. |
| `analysis-findings/v1` + `severity` enum | Replaces `infer_verdict` + `infer_issue_counts` substring logic (analysis_report.py:157-183). | **DUPLICATION RISK (HIGH) — see Q1 detail below.** |
| `Provenanced[T]` | Replaces `object.__setattr__` sidecar in merge.py. | **NET-additive but small.** Legitimate. The "3-layer ripple" is OVERSTATED — see Q2/Q5. |

### Existing-module-that-half-does-the-job candidates (GREP-confirmed)

**Severity / Finding vocabulary — the codebase ALREADY has 8+ of these:**
- `src/specify_cli/status/doctor.py:26` — `class Severity(StrEnum)` + `:43 class Finding`
- `src/specify_cli/audit/models.py:47` — `class Severity(StrEnum)`
- `src/specify_cli/charter_runtime/lint/findings.py:11` — `SEVERITY_ORDER = {low,medium,high,critical}` (**exactly the IC-05 closed enum, minus `info`**) + a `Finding` with `.severity`
- `src/specify_cli/cli/commands/_auth_doctor.py:96,105` — `Severity` Literal + `Finding`
- `src/specify_cli/retrospective/schema.py:142` — `class Finding(BaseModel)`
- `src/glossary/models.py:69`, `src/kernel/glossary_types.py:70` — `class Severity(Enum)`
- `src/specify_cli/cli/commands/review/_issue_matrix.py:50` — `class IssueMatrixVerdict(StrEnum)`

  **Finding (HIGH):** IC-05 proposes a fresh `critical|high|medium|low|info` severity enum + a findings
  record. `charter_runtime/lint/findings.py:SEVERITY_ORDER` already encodes the ordered severity ladder
  with the *blocking* threshold semantics IC-05 needs (`>=high → block`). The plan introduces a **9th**
  severity vocabulary. **Reuse or promote one canonical `Severity` (the StrEnum form in `audit/models.py`
  or `status/doctor.py`) rather than minting `analysis-findings`'s own.** At minimum the plan/tasks must
  name which existing enum it reuses and justify any new one. This is the single biggest duplication
  hazard in the mission.

**Protection/policy helper:** `src/specify_cli/policy/merge_gates.py` is an existing *policy* package with
its own verdict types. The plan parks the new guard at `core/commit_guard.py` (D1 = Shared Kernel). D1's
dependency-direction rationale (everything imports down into `core/`) is sound and `policy/` imports
`status`+`mission_metadata` (would invert), so `core/` is the right home — **but the GuardVerdict shape
should still align with `policy.GateResult`'s shape to avoid two verdict idioms.** (severity: LOW once the
shape is reconciled.)

**Provenance carrier:** no existing `Provenanced[T]`; closest is per-domain provenance *fields* on
retrospective/charter/glossary models — none reusable here (those are domain fields, not a generic
sidecar wrapper). `Provenanced[T]` is justified as new. (severity: LOW.)

---

## Q2 — Deletion-ledger completeness

The data-model ledger lists 5 deletions. **It is INCOMPLETE.** Missing dead-once-ICs-land surfaces:

| Missing from ledger | Location | Severity |
|---|---|---|
| `_PROTECTED_BRANCH_COMMIT_EXCEPTIONS` prefix tuple + `_MERGE_BOOKKEEPING_PREFIX` const | commit_helpers.py:353-363 | **MEDIUM** — ledger names `_is_protected_branch_exception + prefix list` together, but the constants and the `chore(`/`release:`/`chore: release ` literals are a distinct deletable surface; call them out so review confirms zero residue. |
| `safe_commit(allow_protected_branch_in_test_mode, allow_completed_op_on_protected_branch)` bool params | commit_helpers.py:861-862, used at :974-987 | **MEDIUM** — these are message/flag-driven escape hatches that the capability model is meant to subsume. If they survive, FR-008's "no parallel privilege channel" is violated. NOT in ledger. |
| `_is_completed_op_record_exception` + `_test_mode_allows_protected_branch` helpers | commit_helpers.py:479, ~ | **LOW-MEDIUM** — become dead/absorbed once capabilities replace the bool flags. |
| `SPEC_KITTY_INFER_DESTINATION_REF` env handling | safe_commit_cmd.py:38 (`SPEC_KITTY_INFER_ENV`) + 4 test refs in test_safe_commit_cli.py | **MEDIUM** — IC-03 says "fixed OR retired"; if retired, the env const + its 3 dedicated tests are deletions that belong in the ledger. (See Q3 — resolve the ambiguity.) |
| `ProtectedBranchCommitError` (legacy, "retained for backward compat", commit_helpers.py:339) | | **LOW** — flag for review: does the consolidation finally let this legacy error class die? |
| Callers/tests of `infer_verdict`/`infer_issue_counts` | analysis_report.py + tests | **LOW** — ledger says "delete substring logic"; confirm the public functions + their tests go too (not left as dead exports). |

**`object.__setattr__` sidecar (ledger row 5):** correctly listed. But the ledger's IC-08 framing ("3
consumer layers") is **dishonest about scale**: GREP finds exactly **ONE** real read consumer outside
merge.py — `src/glossary/entity_pages.py:164` (`getattr(node, "provenance", None)`). The only other
`getattr(...,"provenance")` hit is inside merge.py's own docstring. So IC-08's "migrate all consumers
across 3 layers" is really *one* call site + the merge.py writes. Good news for reduction — but the plan
should **right-size IC-08** (it currently reads as a large ripple; it is small). (severity: MEDIUM —
overstated scope, not a correctness problem.)

---

## Q3 — Scope tightness (where would I cut?)

1. **IC-03 env-var "fix OR retire" ambiguity (CUT toward RETIRE).** Carrying both an explicit `--to-branch`
   *and* a `SPEC_KITTY_INFER_DESTINATION_REF` inference path is two destination-resolution mechanisms —
   the exact parallel-mechanism the mission exists to kill. **Decide RETIRE in tasks:** once CommitTarget
   threading (IC-02/IC-04) lands, destination is context-resolved or explicit; the env-var inference is
   redundant. Retiring it *adds* to the deletion ledger and removes a footgun. Leaving it "fixed" keeps a
   second resolver alive. (severity: MEDIUM)

2. **IC-05 template/prompt update (KEEP but FENCE).** "Update the analyze command template (SOURCE under
   `src/doctrine/`) so agents emit the frontmatter" is necessary for the carrier to be populated, but it is
   doctrine-prose scope creeping into a tooling mission. Keep it, but **fence it to the minimal frontmatter
   block** and run the terminology guard (`tests/architectural/test_no_legacy_terminology.py`) per CLAUDE.md
   before push. Do not let it grow into an analyze-command redesign. (severity: LOW)

3. **IC-08 (TIGHTEN, don't cut).** Given the true 1-consumer reality (Q2), the "inventory-first / STOP-and-
   escalate if larger" guard is good, but the WP should be sized small and **must not** introduce
   `Provenanced[T]` as a *parallel* representation that coexists with the surviving sidecar — full replace
   or don't ship (the ledger says REPLACE; hold it to that). (severity: LOW)

4. **IC-10 deep-review WP (KEEP).** Justified given the architect review's three failure modes; not scope
   creep.

No IC smuggles *gratuitous* scope; the ambiguity in IC-03 is the only real over-breadth.

---

## Q4 — Honest LOC forecast (add vs delete)

| IC | Adds | Deletes | Net |
|---|---|---|---|
| IC-01 negative suite | +++ (new tests) | 0 | **+** (tests; expected) |
| IC-02 guard spine | ++ (`commit_guard.py` ~80-120) | -- (`_is_protected_branch_exception`, prefix list, inline block, 2 bool flags ~50-70) | **≈ neutral / slightly +** |
| IC-03 ergonomics | + (dir/bulk expansion + report) | - (env-var path IF retired) | **+** |
| IC-04 placement threading | ++ (thread fragment through 3 commit paths) | ~0 | **+** |
| IC-05 findings carrier | ++ (schema + validation + verdict-from-structure) | - (`infer_*` substring ~40) | **+** |
| IC-06 status threading | + (param threading) | - (local coord compositions) | **≈ neutral** |
| IC-07 doctor extraction | 0 net (MOVE) | 0 net | **neutral** (pure relocation) |
| IC-08 Provenanced[T] | + (~15 LOC wrapper + 1 consumer edit) | - (`object.__setattr__` site) | **≈ neutral / slightly +** |
| IC-09 ratchet + ADR | + (test tighten + ADR prose) | 0 | **+** |

**Honest bottom line: NET-ADDITIVE.** This is a stability/hardening mission; tests + a new policy module +
a findings schema + placement threading dominate. The deletions are real but modest (~150-200 LOC across
the ledger). **State this in the spec up front** instead of headlining "(net subtraction)" on the
data-model ledger — that header is misleading and will draw the same refutation the last mission earned.

---

## Q5 — Duplication risk between ICs (destination resolution)

**IC-02 (guard) vs IC-04 (placement threading) — MEDIUM risk of two half-implementations of destination
resolution.** Both touch the commit path; both reason about "the resolved destination ref":
- IC-02's `GuardVerdict.resolved_destination` (what the commit *should* target, for messaging/redirect).
- IC-04 threads `ArtifactPlacementFragment.placement_ref` / `CommitTarget` as the *input* destination.

If IC-02 computes/derives a destination independently of the fragment IC-04 threads, we get **two
destination authorities** — precisely the split-brain this mission inherits from #1619. **Mitigation
(make it a binding task constraint):** `commit_guard.evaluate` must treat the resolved `CommitTarget` as
*given input*, never re-derive a destination; `GuardVerdict.resolved_destination` must be *echoed from* the
passed `CommitTarget.ref`, not independently computed. Sequence IC-04's fragment threading so IC-02's
`evaluate` consumes it — the plan already orders IC-02 before IC-04 on the spine, which is the right
direction, but the contract (single destination authority = the threaded CommitTarget) must be written
into the WP DoD, not left implicit. **Also: IC-03's `--to-branch` is a THIRD destination input** — it must
resolve *into* the same CommitTarget, not bypass it.

Secondary (LOW): IC-02 + IC-06 both delete "local coord compositions" in adjacent surfaces
(commit path vs status path) — no overlap, but both depend on the same `mission_runtime` fragments;
keep the fragment-as-sole-source assertion consistent across both ratchets.

---

## Recommended cuts / constraints (decisive)

1. **[MEDIUM] Fold the two `safe_commit` bool escape-hatches into `GuardCapability`** — do not let them
   survive beside the capability enum. Add them to the deletions ledger.
2. **[HIGH] Reuse an existing `Severity` enum** (`audit/models.py` or `status/doctor.py` StrEnum;
   `charter_runtime/lint/findings.SEVERITY_ORDER` already has the blocking ladder) for `analysis-findings/v1`
   instead of minting the 9th severity vocabulary. Name the chosen canonical enum in tasks.
3. **[MEDIUM] Reconcile `GuardVerdict` with the existing `policy.GateResult`/`GateVerdict` shape** — justify
   in plan why it is a new type, or align it.
4. **[MEDIUM] IC-03: decide RETIRE for `SPEC_KITTY_INFER_DESTINATION_REF`** (+ its env const + 3 tests →
   deletion ledger). Two destination resolvers is the mechanism this mission kills.
5. **[MEDIUM] Right-size IC-08** — the "3-layer ripple" is ONE consumer (`glossary/entity_pages.py:164`).
   Don't budget it as large; full-replace the sidecar.
6. **[MEDIUM] Complete the deletions ledger** (Q2 table) and **re-label the header** — drop
   "(net subtraction)"; this mission is honestly net-additive.
7. **[MEDIUM] Bind the single-destination-authority contract** into IC-02/IC-03/IC-04 WP DoD: `evaluate`
   echoes `CommitTarget.ref`, never re-derives; `--to-branch` resolves into the same CommitTarget.
