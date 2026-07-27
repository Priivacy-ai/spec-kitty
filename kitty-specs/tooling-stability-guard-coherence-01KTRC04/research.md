# Research — Tooling Stability & Guard Coherence (01KTRC04)

**Primary intake research:** `research/architect-review-spec-vs-design.md` (architect-alphonso, binding) —
spec reviewed against doc-17 bounded-domain model, ADR 2026-06-03-2, and the live code surfaces; produced
gaps G-1..G-8, failure modes 1–5, and amendments A-1..A-8 (all applied to spec.md). This file records the
resolved plan decisions + the code facts that anchor the ICs.

## Resolved decisions (Decision Moment Protocol)

### D1 — Guard policy home: Shared Kernel policy module (01KTRFSF2S8CAPX6YD6QYF3MM6)
- **Decision:** `safe_commit` in `git/commit_helpers.py` remains the single entry point (mechanism; zero
  caller import churn). The protection **policy** is extracted to an owned SK module `core/commit_guard.py`:
  `evaluate(CommitTarget, protection_state, capability) → verdict`.
- **Rationale:** dependency direction (everything imports downward into SK; Execution-domain placement would
  force planning→runtime imports the boundary tests forbid); mechanism/policy separation (independently
  testable; stops `commit_helpers.py` god-module growth); doc-17 ownership settled.
- **Alternatives:** Execution domain (rejected — boundary violations); keep-inline-in-git (rejected —
  policy unowned, defers the architecture question).

### D2 — FR-007 shape: Provenanced[T] wrapper (01KTRFSFWZWYRDWM3TF72AY8HB)
- **Decision:** typed generic carrier (model + provenance); provenance never pollutes the domain model.
- **Rationale:** cleanest separation; operator accepted the 3-layer consumer ripple with the safeguard that
  the consumer inventory comes FIRST and migration is in the AC (IC-08).
- **Alternatives:** declared optional field on DRGNode/DRGEdge (lighter, rejected by operator in favor of
  the cleaner shape).

### D3 — FR-004 carrier: frontmatter block (01KTRFSGQ3W8YE5CD1WNSQKG0A)
- **Decision:** schema-validated YAML frontmatter `analysis-findings/v1` on `analysis-report.md`; verdict +
  counts computed from frontmatter only; body prose is presentation; malformed/missing → loud failure.
- **Rationale:** `write_analysis_report` already emits frontmatter (smallest delta); structured > parsed
  prose; schema validation fails loudly on drift.
- **Alternatives:** validated markdown-table contract (markdown parsing remains the foundation — brittle);
  both/cross-check (more robust, more work — can be a later hardening).

## Code facts anchoring the ICs (verified 2026-06-10)

| Fact | Value | IC |
|------|-------|-----|
| `git/commit_helpers.py` size | 1,126 LOC; `_is_protected_branch_exception` at :466; prefix list at :360-362 (`release: `, merge-bookkeeping, upgrade) | IC-02 |
| Guard caller files (`safe_commit\|assert_not_protected_branch`) | ~15: decision_log, git/__init__, orchestrator_api/commands, coordination/{policy,transaction,types}, invocation/executor, acceptance/__init__, cli/commands/{accept,agent/workflow,agent/tasks,safe_commit_cmd,implement,upgrade} | IC-02 census |
| ADR 2026-06-03-2 Decision 2 | `CommitTarget` planned as Step 7 to replace `safe_commit`'s 2-arg convention; forensic pass: 7 direct call sites, all already-consistent pairs | IC-02 |
| `CommitTarget` exists | `mission_runtime.context` (01KTPKST): `{ref, kind ∈ primary/coordination/flattened}`; carried on `BranchRefFragment.destination_ref` + `ArtifactPlacementFragment.placement_ref` | IC-02/IC-04 |
| ADR home drift | ADR names `specify_cli/core/execution_context.py`; actual = `src/mission_runtime/resolution.py` | IC-09 |
| `analysis_report.py` | 313 LOC; `infer_issue_counts` (substring fallback) + `infer_verdict` ("BLOCK"/"READY FOR IMPLEMENTATION" magic strings) — delete after cutover | IC-05 |
| `doctor.py` | 3,271 LOC; #1623 scopes ONLY the doctrine health-render extraction (I-10: pure extraction) | IC-07 |
| `doctrine/drg/merge.py` | 494 LOC; `_tag_source` uses `object.__setattr__` sidecar; generic TypeVar already landed (I-3 done) | IC-08 |
| #1796 children | #1631 (P0), #1334, #1355 (ratchet), #1330 (dir/bulk paths) — all folded | IC-02/03/09 |
| #1784 repro shape | planning artifacts land on coord branch (guard refusal on main) → finalize-tasks reads target branch → "spec.md not found" catch-22 | IC-04 |

## Failure modes designed against (from the architect review; encoded in ICs)
1. **Rim-hardening recurrence** (#1334 pattern) → IC-02 caller census first; #1355 ratchet (IC-09).
2. **Relaxation-as-coherence** → IC-01 protection-preserved suite authored FIRST (NFR-005); C-003 explicit SC.
3. **GuardV2 beside old** → strangler: one live guard; prefix channel deleted only after conversion.
4. **Verdict-parser brittleness** → D3 schema validation, loud failure; legacy reports → `unknown`, never fabricated.
5. **DRG ripple underestimate** → IC-08 inventory-first; STOP-and-escalate if larger than inventoried.

## Open items (deliberately deferred to tasks/implement)
- Exact capability vocabulary for the re-expressed prefix privileges (release/upgrade/merge-bookkeeping) —
  IC-02 design detail; candidate: an explicit `capability` enum parameter supplied by the calling surface
  (NOT derived from message text), with the orchestration flows passing their identity.
- Legacy-report fallback wording for IC-05 (`verdict: unknown` + remediation hint).
