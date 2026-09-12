# Data Model: Responsive Pre-Review Gate Operator Flow

## 1. BudgetClassification

Immutable string enum owned by `specify_cli.review.gate_budget`.

| Value | Meaning | Execution consequence |
|---|---|---|
| `bounded` | Explicit metadata says the selected scope is suitable for the interactive budget. | Run normally. |
| `oversized` | Explicit metadata says the selected scope cannot fit. | Return terminal refusal before launch. |
| `unknown` | No deterministic rule matches. | Warn and run under the existing timeout. |

There is no inferred or learned value.

## 2. ScopeIdentity

Immutable value derived from, but never substituted for, the runner's target arguments.

| Field | Type | Invariant |
|---|---|---|
| `normalized_targets` | `tuple[str, ...]` | POSIX-normalized, de-duplicated, sorted, non-mutating projection of `ScopeResult.test_targets`. |
| `policy_namespace` | `str` | Fixed versioned namespace for the preflight budget policy. |
| `value` | `str` | `budget-v1:sha256:<lowercase hex>` over the canonical bytes defined below. |

Canonical identity encoding is deliberately fixed rather than delegated to Python object hashing or representation:

1. `policy_namespace` is exactly `spec-kitty.pre-review-budget/v1`.
2. Serialize `{"namespace": <policy_namespace>, "targets": [<normalized targets>]}` as UTF-8 JSON with sorted keys, `ensure_ascii=True`, and separators `(",", ":")` (no whitespace).
3. Hash those bytes with SHA-256 and prefix the lowercase hexadecimal digest with `budget-v1:sha256:`.

Pinned vector: normalized targets `("tests/architectural",)` serialize to `{"namespace":"spec-kitty.pre-review-budget/v1","targets":["tests/architectural"]}` and produce `budget-v1:sha256:10c1e7475c72e48b83e4910e24437646d6ecd55052ca9a3a4f413b17153946fe`.

Identity equality must be independent of input order, duplicate target entries, process, and `PYTHONHASHSEED`. Executed argv remains unchanged. This is deliberately separate from `scope_source_identity()`, which requires completed raw output and remains the sole baseline/head parse-comparability authority.

## 3. ScopeBudgetRule

Immutable source-controlled metadata record.

| Field | Type | Invariant |
|---|---|---|
| `rule_id` | `str` | Stable, reviewable identifier. |
| `required_target_atoms` | `tuple[str, ...]` | Already normalized exact atoms that must be members of the selected target set; never a hidden prefix/glob. |
| `classification` | `BudgetClassification` | Production rules initially use `oversized`; `bounded` is supported. |
| `evidence` | `str` | Human-readable issue/evidence reference. |
| `guidance` | `str` | Recovery or maintainer guidance. |

Initial production record:

```text
rule_id: spec-kitty-architectural-full-directory
required_target_atoms: [tests/architectural]
classification: oversized
evidence: issue #2573 dogfood, approximately 26 minutes per leg
```

The table is an immutable tuple. No runtime update function exists. The rule matches a singleton or multi-target set containing the exact atom, while a descendant such as `tests/architectural/test_layer_rules.py` remains unknown. Arbitrary `ScopeSource.test_command()` argv is not parsed for policy; a suite encoded only there remains unknown for compatibility.

## 4. ScopeBudgetAssessment

Result of applying the canonical rules to one resolved scope.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `classification` | `BudgetClassification` | yes | `bounded`, `oversized`, or `unknown`. |
| `scope_identity` | `ScopeIdentity` | yes | Stable identity and readable normalized targets. |
| `effective_budget_seconds` | `float` | yes | Configured timeout budget governing the candidate-head run. |
| `matched_rule_id` | `str \| None` | yes | Present only on deterministic match. |
| `evidence` | `str \| None` | yes | Reviewed evidence for a match. |
| `guidance` | `str` | yes | Operator/maintainer next action. |

Validation rules:

- `oversized` and `bounded` require `matched_rule_id`;
- `unknown` requires `matched_rule_id is None`;
- budget must be positive;
- assessment is computed before any launch attempt.

## 5. GateVerdict extension

Existing `GateVerdict` gains compatible optional evidence:

| Field | Type | Default |
|---|---|---|
| `budget_assessment` | `ScopeBudgetAssessment \| None` | `None` for legacy/direct constructors |
| `classification_candidate` | `bool` | `False` |
| `observed_elapsed_seconds` | `float \| None` | `None` |

New `GateOutcome.SCOPE_OVERSIZED` has:

- `run_state = NOT_STARTED` because no runner was started;
- `budget_assessment.classification = oversized`;
- `classification_candidate = false`;
- no failures and no subprocess output.

Unknown timeout has:

- `outcome = TIMED_OUT`;
- `budget_assessment.classification = unknown`;
- `classification_candidate = true`;
- `observed_elapsed_seconds` is measured from the observer's monotonic start to terminal deadline detection and is reported separately from `effective_budget_seconds`;
- terminal no-transition semantics.

## 6. Gate status events and TransitionGateContext extension

Renderer-neutral events:

```text
ScopeAssessed(assessment)
Heartbeat(phase="candidate_head", observed_elapsed_seconds)
```

`ScopeAssessed` is emitted after scope resolution and before any launch. The engine adapts the existing runner `Callable[[float], None]` into `Heartbeat`; the runner itself stays presentation-free.

The shared registry context gains:

```python
status_observer: Callable[[GateStatusEvent], None] | None = None
```

Invariants:

- human `move-task`: observer exists and renders assessment plus elapsed liveness;
- JSON `move-task`: observer is `None`;
- registry handler delegates unchanged;
- explicit override evaluation receives the same observer;
- observer never decides a verdict or mutates lane state.

## 7. Structured pre_review_gate metadata

Existing fields remain. Additive fields:

| Field | Type | Presence |
|---|---|---|
| `budget_classification` | string | All assessed runs/refusals |
| `scope_identity` | string | All assessed runs/refusals |
| `effective_budget_seconds` | number | All assessed runs/refusals |
| `matched_budget_rule` | string/null | All assessed runs/refusals |
| `classification_candidate` | boolean | All assessed runs/refusals |
| `observed_elapsed_seconds` | number/null | Timeout diagnostic |
| `recovery_choices` | array[string] | Oversized refusal: bounded scope and explicit skip |
| `classification_guidance` | string/null | Unknown timeout candidate or matched rule guidance |

`test_targets` already exists and remains the readable selected-target authority.

The existing top-level `transition_applied` field is authoritative. If a nested `pre_review_gate.transition_applied` mirror is retained for backward compatibility, it is present only where existing output already supplies it and MUST equal the top-level value whenever both occur; it is not a second authority.

## 8. State transitions

```text
scope resolved
  -> assessed.oversized
       -> verdict.scope_oversized
       -> aggregate.terminal
       -> lane unchanged

scope resolved
  -> assessed.unknown|bounded
       -> process running
       -> completed -> existing warn/block/pass semantics
       -> timed_out -> process reaped -> lane unchanged
       -> cancelled -> process reaped -> lane unchanged
```

Only `unknown + timed_out` sets `classification_candidate=true`. Neither that transition nor retrospective review mutates runtime metadata; any new rule is a later reviewed source change.

## 9. Retrospective observation

Each **operational** delivery candidate is appended immediately at its point of observation through `spec-kitty agent tracer-append --category approach`, producing the mission-owned `traces/approach.md`. Synthetic controlled-clock/timeout fixtures remain automated-test evidence and are not classification evidence. Every tracer entry records `provenance: operational`; the retrospective consumes that durable tracer, not terminal scrollback. For each observed candidate it records:

- scope identity and targets;
- environment/context sufficient to avoid treating host contention as structural proof;
- disposition: `follow_up` with owner/reference, or `no_action` with reason.

Before acceptance, `retrospective-handoff.md` inventories durable operational entries (or explicitly records none) and requires their disposition by the canonical post-merge retrospective. After merge, the automatic retrospective terminus or `spec-kitty retrospect create --mission <slug> --json` produces `retrospective.yaml`; that record must state `follow_up` with owner/reference or `no_action` with reason for each candidate, or `no candidates observed`. Absence is not inferred silently.
