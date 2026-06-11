# Data Model — Tooling Stability & Guard Coherence (01KTRC04)

## 1. Commit-guard (IC-02, D1)

### CommitTarget (EXISTS — 01KTPKST, `mission_runtime.context`; consumed, not redefined)
| Field | Type | Notes |
|-------|------|-------|
| `ref` | str | the destination branch/ref |
| `kind` | enum `{primary, coordination, flattened}` | topology classification |

### GuardCapability (NEW — value object, SK policy module)
| Field | Type | Notes |
|-------|------|-------|
| `kind` | enum `{standard, release_flow, upgrade_bookkeeping, merge_bookkeeping, test_mode}` | **asserted-at-the-surface** parameter (adjudicated over derive: `CommitTarget.kind` is topology, not operation intent). Defaults `standard`. NEVER derived from message text, file content, or ambient env (FR-008). Its value is **auditability** (named/typed/greppable) for the LLM-agent threat model — not unforgeability. |

**Channel consolidation (FR-008 / split review F-1):** GuardCapability subsumes ALL FIVE live privilege
channels — message-prefix list, `allow_protected_branch_in_test_mode` (bool, with `=True` production call
sites), `allow_completed_op_on_protected_branch` (bool), the op-record file-content exception, env hatches.
After IC-02 no second privilege channel exists; a per-channel refusal test guards each deleted path.

### GuardVerdict (NEW — return of `commit_guard.evaluate`)
| Field | Type | Notes |
|-------|------|-------|
| `allowed` | bool | |
| `resolved_destination` | str | the ref the commit should target (for messaging + redirect) |
| `reason` | str | actionable refusal text naming the resolved destination (never "switch to lane branch" pre-lanes) |

**Invariants:**
- `evaluate(target: CommitTarget, protection_state, capability: GuardCapability) → GuardVerdict` is pure
  (no I/O beyond provided state) and the ONLY protection decision in the codebase.
- Legitimacy: `allowed` ⇐ the resolved placement (CommitTarget) names this ref as the intended destination,
  OR an explicit capability authorizes the bookkeeping flow. Message content NEVER participates.
- Direct-push-to-origin/main protection is outside `allowed`'s reach (cannot be granted by any capability).

## 2. Findings carrier (IC-05, D3) — `analysis-findings/v1`

YAML frontmatter on `analysis-report.md`:
```yaml
---
schema: analysis-findings/v1
findings:
  - id: A1            # stable finding id
    severity: low     # REUSES the existing canonical severity vocabulary (charter_runtime/lint/findings.py
                      # SEVERITY_ORDER) — binding: no 9th Severity model is minted (the codebase has 8+)
    category: coverage
    summary: "…"
counts: {critical: 0, high: 0, medium: 1, low: 4, info: 0}   # MUST equal the findings[] tally
verdict_hint: ready   # optional author hint; recorder COMPUTES the verdict; hint disagreement → loud error
---
```
**Invariants:**
- Verdict = f(findings[].severity) only: any `critical|high` → `blocked`; else → `ready`. Prose never read.
- `counts` must equal the `findings[]` tally (schema validation; mismatch → loud error).
- Missing/malformed carrier → structured error + `verdict: unknown` for LEGACY reports (pre-v1), never fabricated.
- Severity vocabulary is closed (enum); unknown severities fail validation.

## 3. Provenanced[T] (IC-08, D2)
```python
@dataclass(frozen=True)
class Provenanced(Generic[ModelT]):
    value: ModelT          # the DRG model (DRGNode / DRGEdge), unpolluted
    provenance: str        # source pack/layer tag (what _tag_source used to monkey-patch)
```
**Invariants:** replaces the `object.__setattr__(obj, "provenance", …)` sidecar entirely; no
`getattr(node, "provenance", None)` consumer remains post-migration (grep gate); `mypy --strict` clean.

## 4. StatusSurfaceFragment threading (IC-06)
No new model — `MissionStatus.load` + `status_transition` gain a `surface: StatusSurfaceFragment` input
(from the resolved context) and delete their local coord-path compositions. Parity-ratchet assertion added:
the fragment is the source (no re-derivation).

## 5. Deletions ledger
*(Honesty note, per split review: this mission is **net-additive** overall — new policy module, schema, wrapper.
The ledger below is the duplication/privilege-channel burn-down, ~150–200 LOC, not a net-subtraction claim.)*

| Surface | Disposition | IC |
|---------|-------------|-----|
| `commit_helpers._is_protected_branch_exception` + prefix-list constants | DELETE (after conversion; #1334) | IC-02 |
| `allow_protected_branch_in_test_mode` bool param + `_test_mode_allows_protected_branch` + its ~8-module propagation + `=True` production call sites | FOLD into GuardCapability, DELETE channel | IC-02 |
| `allow_completed_op_on_protected_branch` bool param + `_is_completed_op_record_exception` (file-content channel) | FOLD into GuardCapability, DELETE channel | IC-02 |
| env-var privilege hatches on the commit path | FOLD into GuardCapability or retire | IC-02 |
| `SPEC_KITTY_INFER_DESTINATION_REF` env path (+ const + its tests) | RETIRE (explicit `--to-branch` / context-resolved destination only — two destination resolvers is what this mission kills) | IC-03 |
| `_resolve_planning_branch` meta.json second destination authority | RETIRE (replaced by `resolve_placement_only` projection) | IC-04 |
| `analysis_report.infer_verdict` / `infer_issue_counts` substring logic | DELETE (after carrier cutover) | IC-05 |
| local coord-path compositions in `MissionStatus.load` / `status_transition` | DELETE (threaded) | IC-06 |
| doctrine health-render bodies in `doctor.py` | MOVE to `_profile_health_render.py` (pure extraction) | IC-07 |
| `object.__setattr__` provenance sidecar | REPLACE with `Provenanced[T]` (2 real consumers: `drg/merge.py:480`, `glossary/entity_pages.py:164`) | IC-08 |

**Naming note:** `GuardVerdict` is intentionally distinct from the existing `GateVerdict`/`GateResult`
(`policy/merge_gates.py:26,33`) — near-twin shape, different domain (commit protection vs merge gating);
the distinction is documented here to preempt a future "duplicate" flag.
