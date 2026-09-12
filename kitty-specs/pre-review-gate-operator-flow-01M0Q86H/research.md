# Research: Responsive Pre-Review Gate Operator Flow

## Question and evidence base

This research asks what remains to close #2573 safely for 3.2.6, given the current code rather than the issue's original state. Sources inspected during specify/plan were the public issue and milestone discussion, `tasks_move_task.py`, `gate_registry.py`, `pre_review_gate.py`, `scope_source.py`, `baseline.py`, `verdict_aggregation.py`, `core/env.py`, and the exact public-entry observability tests.

Current dogfood evidence attached to #2573 records eight timeouts in eight invocations. Selected scopes took roughly 79–85 seconds under contention in smaller cases, while the full `tests/architectural/` target took about 26 minutes per leg. The current head-run timeout is the baseline constant `CAPTURE_BASELINE_TIMEOUT_SECONDS = 300` seconds. A scope that needs roughly 26 minutes cannot fit this interactive transition contract.

## Finding 1 — Most original controls have already landed

The current branch already contains:

- `--skip-pre-review-gate`, checked before workspace resolution or subprocess launch;
- canonical disable variables from `SYNC_DISABLE_ENV_VARS`, ordered `SPEC_KITTY_SYNC_DISABLE` then `SPEC_KITTY_SYNC_MINIMAL_IMPORT`;
- warn-by-default new-failure handling with `review.fail_on_pre_review_regression` as the explicit block policy;
- terminal timeout/cancellation outcomes that preserve the lane;
- POSIX process-group and Windows tree termination, bounded escalation, and child reaping;
- a lower-level progress callback in `_observe_process` every 30 seconds;
- a one-shot public start notice.

Therefore the mission must verify these surfaces and avoid rebuilding them. The clear live gap is that `TransitionGateContext` has no status/progress carrier, so the registered handler drops the already-supported runner signal; the explicit-override caller also omits its available callback. The exact public-entry test documents the registry omission and asserts only the start notice.

## Decision 1 — Use deterministic gate-owned metadata, not CI history

**Decision**: Create a small immutable budget policy beside the pre-review engine.

**Why**:

- clean machines and CI make the same decision;
- reviewers can see and approve every classification change;
- it requires neither mining/backfilling CI runs nor changing workflow scheduling;
- it stays within a 3.2.6 stabilization boundary.

**Rejected alternatives**:

- persisted observed timings: stateful, machine-dependent, cold-start ambiguous;
- runtime estimation from test counts or collection: heuristic and capable of refusing healthy scopes;
- placing metadata in `tests/architectural/_gate_coverage.py`: that module statically models CI topology, so it would blur interactive gate policy with CI authority;
- adding a new project configuration requirement: creates a migration and a second operator-owned policy surface.

## Decision 2 — Use a three-state assessment

`bounded`, `oversized`, and `unknown` are distinct:

- `oversized`: explicit reviewed evidence says the exact scope cannot fit; refuse before launch;
- `unknown`: no metadata match; warn and run under today's timeout;
- `bounded`: explicit reviewed evidence says the scope is suitable; supported by the model, but broad inference is not needed for 3.2.6.

Only `oversized` changes execution. Unknown fallback is necessary for compatibility with custom `pre_review_test_scope` values and non-Spec-Kitty repositories.

The first production rule is exact target-atom membership: any normalized target set containing `tests/architectural` is oversized. Membership matters because a multi-target scope still contains the known 26-minute full-directory work. Exact atoms also matter: a single file such as `tests/architectural/test_layer_rules.py` is not the full-directory scope and remains unknown unless separately classified. A broad suite encoded only inside arbitrary `test_command()` argv also remains unknown; parsing commands would be a larger heuristic redesign.

## Decision 3 — Refusal is a terminal gate verdict

**Decision**: model refusal as `GateOutcome.SCOPE_OVERSIZED`, carried through the normal verdict and aggregation seams.

**Why**:

- one outcome object drives human output, JSON metadata, transition integrity, and tests;
- the canonical terminal-precedence set remains the single authority for no-transition results;
- both auto-derived and explicit override scopes can share the pre-launch assessment;
- no CLI-only target matching or special exit path is introduced.

`SCOPE_OVERSIZED` joins timeout and cancellation as terminal for transition purposes, but differs operationally: no subprocess starts, `run_state` is `NOT_STARTED`, there is no test result, and recovery guidance must name bounded scope and explicit skip.

## Decision 4 — Carry typed status through the existing context and override path

**Decision**: add an optional renderer-neutral observer for `ScopeAssessed` and `Heartbeat` events to `TransitionGateContext`, delegate it through the registered handler, and pass the same observer through the explicit-override evaluation path.

**Why**:

- the engine can emit assessment before launch, while the runner already calculates elapsed time at the required cadence and can be adapted into heartbeat events;
- the registry context is the intentional cross-boundary carrier;
- rendering remains at the CLI edge;
- `None` preserves existing handler and test behavior.

Human mode constructs one Rich observer. JSON mode supplies `None` on both handler and override paths, preserving one final JSON document rather than introducing NDJSON or mixed stdout.

## Decision 5 — Unknown timeout produces evidence, not policy

An unknown-budget timeout must add:

- `budget_classification: "unknown"`;
- stable normalized `scope_identity`;
- selected `test_targets`;
- configured `effective_budget_seconds` and separately measured `observed_elapsed_seconds` from the monotonic observer;
- `classification_candidate: true`;
- `transition_applied: false` and unchanged-lane evidence;
- guidance that a maintainer may propose a reviewed deterministic rule.

One timeout does not prove structural oversize: contention, downloads, a slow host, or a hung test can cause it. Runtime code therefore has no metadata write API. Every candidate observed during delivery is manually appended through the canonical Mission approach tracer. The Mission/sprint retrospective inspects `traces/approach.md` and records a follow-up owner, explicit no action, or explicit absence of candidates.

## Decision 6 — Normalize scope identity without changing test argv

The classifier operates on a normalized copy while the runner continues receiving the original targets. Normalization:

1. converts `\\` to `/`;
2. removes leading `./` and redundant trailing `/`;
3. preserves pytest node selectors after `::`;
4. deduplicates and sorts targets.

The preflight identity includes a fixed budget-policy namespace and the normalized tuple. It deliberately does not reuse `scope_source_identity()`, whose parse mode cannot exist until after a completed run and whose authority remains baseline/head result comparability. A stable digest may be used for compactness, but structured output must retain the readable target list. No normalization may rewrite the executed command.

## Decision 7 — Test through the public command

Low-level callback tests are necessary but insufficient. The defect exists at the handler/context/public-entry wire. Acceptance evidence therefore invokes the Typer `move-task` command and asserts:

- deterministic-clock start plus continuing heartbeats in human mode, with start ≤1 second, heartbeat gaps ≤30 seconds, and none after terminal output;
- no progress frames and exactly one JSON document in structured mode;
- pre-launch oversized refusal and untouched launch spy;
- unchanged lane/event state for refusal, timeout, and cancellation;
- configured/observed diagnostic candidate fields for unknown timeout;
- preserved skip/env/warn/block precedence.

Real process-tree evidence remains split by platform: actual POSIX child/group behavior and deterministic Windows `taskkill /T` contract tests. A separate POSIX real-CLI parent-`SIGKILL` acceptance test independently proves lane/event state remains unchanged and intentionally makes no orphan-cleanup assertion. Cleanup after uncatchable parent death remains #2762, not #2573.

The comparison baseline used by `move-task` is captured earlier during implementation. This Mission's liveness and budget contracts apply to the candidate-head process launched by review submission; adding baseline capture or baseline progress to `move-task` would be an unrelated workflow expansion.

## Release dependency

The current 3.2.6 execution DAG places #2573 downstream of #3127. Work may be prepared independently, but final release-ready status is gated on #3127 merging, rebasing this Mission onto the resulting `main`, and rerunning trustworthy required checks. This is a finalization dependency, not a product-code dependency.

## Planning infrastructure note

`setup-plan` was run with the user-authorized `SPEC_KITTY_ENABLE_SAAS_SYNC=0` override to bypass the known unauthenticated SaaS gate. The first scaffold invocation then self-deadlocked opening the local project sync database through two connections; no other process owned that database, so the single hung process was interrupted after the scaffold write. Final substantive-plan runs added `SPEC_KITTY_SYNC_MINIMAL_IMPORT=1`, completed successfully, committed the plan, and returned a fully matching branch contract. This is planning-tool behavior, not part of #2573's product design.

## Resolved unknowns

All material questions are resolved. There is no `NEEDS CLARIFICATION` item:

- metadata authority: deterministic source;
- unknown fallback: warn and run;
- refusal semantics: terminal before launch, lane unchanged;
- timeout feedback: diagnostic candidate, no automatic promotion;
- retrospective: mandatory inspection and disposition;
- output: typed pre-launch assessment plus human heartbeats, one final JSON document;
- release finalization: #3127 merged, rebase, required checks rerun;
- async and hard-parent-kill cleanup: out of scope.
