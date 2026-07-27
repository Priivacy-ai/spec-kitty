# Mission Specification: Doctrine-Controlled Transition Gates

**Mission Branch**: `feat/doctrine-controlled-transition-gates`
**Created**: 2026-07-22
**Status**: Draft (post-spec squad amendments applied)
**Input**: Half A of epic #2535 — replace the pre-review transition gate hardcoded to Spec Kitty's own repo shape with a gate declared by the repo's active doctrine. Closes the **pre-review facet** of #2534 (consumer-repo `_gate_coverage` import leak) and #2330 (pytest-layout papercut) by construction. Executable third-party gate assets (#2599 / Mission D, half B) are OUT.

## Overview & Context

When a work package advances through its lifecycle (for example, moving to `for_review`), Spec Kitty runs **transition gates** — checks that must pass before the move is allowed. The flagship gate is the scoped pre-review regression check: it derives which tests prove the changed files, runs them, and blocks (opt-in) on new failures.

Today that gate is welded to Spec Kitty's **own** repository shape. The pre-review engine assumes a `src/specify_cli/` source layout, assumes the test runner is pytest (it injects `--junitxml`/`-q` and parses JUnit XML only), and imports an internal test-tree module (`tests.architectural._gate_coverage`) as its authority. A project that adopted Spec Kitty via `spec-kitty init` — a Go service, an npm package, any non-pytest or differently-laid-out repo — cannot carry that internal module, so the gate degrades or papercuts. The internal import is a **consumer-repo leak** (#2534); the pytest/`src/` assumption is a **layout papercut** (#2330).

This mission inverts the relationship for the **`for_review` pre-review gate specifically**: that gate becomes a **named handler** which the repo's **active doctrine** decides to run, resolved through the existing charter-activation machinery. Spec Kitty's own scoped-regression check becomes just one activated handler among a repo's active doctrine. A consumer repo that does not activate that handler never reaches the internal import — the leak disappears **by construction** for this gate, not by being caught-and-worded.

**Scope honesty (added post-review).** This mission inverts **only** the `→ for_review` pre-review gate as the reference cut of epic #2535's strangler. Sibling lifecycle gates retain repo-shape coupling and are explicitly out of scope (see C-006). The #2534 and #2330 closures are therefore scoped to the **pre-review facet** — the surrounding prose must not imply the whole *class* of repo-shape coupling is closed.

This is a **strangler refactor**: the observable behaviour on the Spec Kitty repository itself must not change (all six gate outcomes and both legitimate hard-stops preserved). New capability (portable gates, doctrine-declared bindings) is added underneath; the current pre-review verdicts are preserved exactly.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consumer project runs its own gates, never Spec Kitty's internals (Priority: P1)

A maintainer of a project that adopted Spec Kitty (non-pytest, non-`src/specify_cli/` layout) advances a work package to `for_review`. The pre-review gate runs only what that project's active doctrine declares — it never attempts to import Spec Kitty's internal `tests.architectural._gate_coverage` module, and it never assumes pytest. If the project declares a test command, the gate runs that command **and parses its result into a real verdict** (a failing suite yields a blocking-capable `NEW_FAILURES`, not a silent `NO_COVERAGE`). If it declares none, the transition proceeds with a visible "not verified" notice rather than a crash. This holds **even if the project erroneously activates the Spec-Kitty handler** — the internal module is still never imported.

**Why this priority**: This is the mission's reason to exist — it closes both consumer-facing defects for the pre-review gate. Without it, the other stories have no external payoff.

**Independent Test**: In a simulated consumer checkout with no `tests/architectural/_gate_coverage.py` and a non-pytest layout: (a) with a declared `review.test_command` whose suite **fails**, assert the gate produces a blocking-capable `NEW_FAILURES` verdict (proving results are parsed, not just that the process ran) and never imports the internal module; (b) with no command declared, assert a visible `NO_COVERAGE` warning and no crash; (c) with the Spec-Kitty handler force-activated in the consumer's config, assert the internal module is still never imported.

**Acceptance Scenarios**:

1. **Given** a consumer repo (no internal gate-coverage module, non-pytest layout) with a declared `review.test_command` whose suite fails, **When** a WP moves to `for_review`, **Then** the declared command runs, its output is parsed, and the gate yields a blocking-capable `NEW_FAILURES` — the internal module is never imported.
2. **Given** a consumer repo that declares no `review.test_command`, **When** a WP moves to `for_review`, **Then** the transition succeeds with a visible `NO_COVERAGE` warning and no crash.
3. **Given** a consumer repo whose active doctrine binds no gate to the `for_review` transition, **When** a WP moves to `for_review`, **Then** no gate runs and no Spec Kitty internal path is referenced.
4. **Given** a consumer repo that erroneously activates the Spec-Kitty pre-review handler, **When** a WP moves to `for_review`, **Then** the internal `_gate_coverage` module is still never imported (closure does not depend on activation being correctly configured).

---

### User Story 2 - Spec Kitty's own gate verdicts are unchanged, through the inverted hook (Priority: P1)

A Spec Kitty maintainer relies on the scoped pre-review regression gate. After this refactor, that gate must produce **identical** results on the Spec Kitty repository for the same inputs — across **all six** outcome shapes (`NO_COVERAGE`, `NO_NEW_FAILURES`, `NEW_FAILURES`, `UNVERIFIED_BASELINE`, `TIMED_OUT`, `CANCELLED`) **and** both legitimate hard-stops (opt-in `NEW_FAILURES` block; terminal `TIMED_OUT`/`CANCELLED` interruption). Parity must be proven **through the inverted transition hook**, not only against the engine in isolation — including the transition metadata payload, block/exit behaviour, and operator-facing console output.

**Why this priority**: A strangler refactor that silently changes the incumbent's behaviour is a regression. Behaviour preservation is the safety contract that lets the mission land — and the riskiest change is the hook itself, so parity must cover it.

**Independent Test**: A golden comparison routing the same changed-file inputs through both the pre-refactor path and the refactored handler-plus-hook path, asserting identical `(outcome, scope, transition_applied metadata, block/exit, console surface)` across a scenario set that exercises all six outcomes and both hard-stops.

**Acceptance Scenarios**:

1. **Given** any of the six outcome-producing changed-file scenarios on the Spec Kitty tree, **When** the refactored gate runs through `_mt_run_transition_gates`, **Then** the outcome, scope, and transition metadata match the pre-refactor path exactly.
2. **Given** a `NEW_FAILURES` scenario under opt-in blocking, **When** the refactored hook runs, **Then** it blocks with the same exit and message.
3. **Given** a `TIMED_OUT` or `CANCELLED` scenario, **When** the refactored hook runs, **Then** it hard-stops exactly as the incumbent does (the interruption behaviour is preserved, not converted to a warn).

---

### User Story 3 - Gates are declared and toggled through doctrine, not Python (Priority: P2)

A Spec Kitty maintainer declares which named gate handler fires on which status-transition edge through a doctrine binding, and activates or deactivates that gate through the charter — changing which gates run **without editing Python**. A binding names an `on_transition` edge and a `handler`, carries an (initially inert) `handler_kind` discriminator so a future executable-asset handler can be named without a breaking schema change, is versioned, and defaults to fail-open until activated. The binding's home model, the lane-edge→binding mapping, and the URN→binding resolution join are all explicitly defined so the mechanism mechanically closes.

**Why this priority**: This is the durable capability the mission delivers (the declarative registry + binding). It is P2 because P1 stories can be demonstrated with the pre-review handler alone, but this is what makes gates doctrine-controlled rather than merely portable.

**Independent Test**: Add a gate binding for the `for_review` edge, activate its handler in doctrine, observe the handler run on that transition; deactivate it and observe the handler no longer run — with no code change between the two states. Separately assert a binding carrying `handler_kind: asset` round-trips through load/serialize unchanged even though it is unconsumed in half A.

**Acceptance Scenarios**:

1. **Given** a gate binding whose handler is activated in the repo's doctrine, **When** the bound transition occurs, **Then** the named handler runs and contributes its verdict (resolved via the defined URN→binding join).
2. **Given** the same binding with its handler **not** activated, **When** the bound transition occurs, **Then** the handler does not run, and this non-resolution is detectable (a resolution test with a negative control), not silent.
3. **Given** a binding with an unknown/malformed shape or an unversioned schema, **When** the doctrine is loaded, **Then** it is rejected loudly (the schema is `extra`-forbidding and versioned), not silently dropped.
4. **Given** a binding with `handler_kind: asset` (a half-B shape), **When** doctrine is loaded and re-serialized in half A, **Then** the field round-trips unchanged and is treated as inert (no attempt to execute an asset).

---

### User Story 4 - A failing gate degrades safely, never crashes or silently passes (Priority: P2)

An operator running a transition must never have a gate handler crash the transition or silently let it pass. Any handler that **errors during execution** degrades to a **visible "unverified" warning**. The only legitimate non-completions are (1) the deliberate opt-in block on genuine new failures and (2) the incumbent terminal-interruption hard-stop (`TIMED_OUT`/`CANCELLED`). When multiple handlers fire, their verdicts aggregate deterministically and one faulting handler never suppresses another's verdict.

**Why this priority**: The fail-open-on-error invariant already protects today's single gate; extending gates to a registry of handlers must preserve it for **every** handler, with defined aggregation, or the mission introduces a new class of transition-blocking bug.

**Independent Test**: Fault-inject an exception into one registered handler while another returns a normal verdict; assert the transition still completes, the faulting handler surfaces exactly one visible "unverified" warning, and the other handler's verdict is unaffected.

**Acceptance Scenarios**:

1. **Given** a registered handler that raises during execution, **When** the bound transition occurs, **Then** the transition completes and that handler surfaces exactly one visible "unverified" warning.
2. **Given** two activated handlers that both return warn-shaped outcomes, **When** the transition occurs, **Then** each surfaces exactly one warning and the transition is never blocked by them.
3. **Given** one handler returning `NEW_FAILURES` (blocking enabled, no `--force`) and a second handler that raises, **When** the transition occurs, **Then** the block still fires (the faulting handler does not suppress the block) and the fault degrades to a warning.
4. **Given** a `TIMED_OUT`/`CANCELLED` handler outcome, **When** the transition occurs, **Then** the incumbent terminal hard-stop is preserved (this is the second legitimate non-completion, distinct from a handler-execution error).

### Edge Cases

- **No `review.test_command` configured** → gate is a visible `NO_COVERAGE` warning, never a crash and never a silent green pass ("empty is never clean").
- **A binding whose handler resolves to no activated node** → detectable via a non-vacuous resolution check with a negative control (guards the silent-invisibility trap); treated as fail-open advisory.
- **Consumer repo with no gate bindings at all** → transition proceeds with no gate and no internal-path reference.
- **Blocking mode** → a block fires only when blocking is enabled AND a handler reports `NEW_FAILURES` AND `--force` is not set.
- **Terminal interruption** (`TIMED_OUT`/`CANCELLED`) → preserves the incumbent hard-stop; this is a legitimate non-completion, NOT subject to the fail-open-on-error rule.
- **Pack-context resolution failure** (unset org-pack env var / subdir escape) → fail **closed** on that specific misconfiguration (mirrors the existing executor contract), distinct from the fail-open handler-execution invariant.
- **Non-pytest declared command produces non-JUnit output** → the port's result parser turns it into a real verdict; a failing suite must not collapse to `NO_COVERAGE`.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Scope resolved behind a port scoped to what varies by repo shape | As a maintainer, I want a `ScopeSource` port covering only the repo-shape-varying concerns — `test_command()`, `file_to_scope()`, and `parse_results()` — while "which files changed" stays the single canonical merge-base+diff input passed to the gate (not a per-impl method), so the gate is layout-agnostic without two implementations diverging on the changed-file SSOT. | High | Open |
| FR-002 | Internal scope implementation preserves current behaviour | As a Spec Kitty maintainer, I want a `GateCoverageScopeSource` that reproduces today's exact scope derivation, pytest invocation (`--junitxml`/`-q` injected *inside this impl*, not the shared runner), and JUnit parsing on the Spec Kitty tree so the incumbent gate is unchanged. | High | Open |
| FR-003 | Portable default scope implementation with real, baseline-relative verdicts | As a consumer maintainer, I want a `DeclaredCommandScopeSource` that runs the doctrine-declared `review.test_command` over the whole suite (no per-file narrowing) and parses its output into a real **baseline-relative** verdict — a failure newly present versus the captured baseline yields `NEW_FAILURES`; a pre-existing baseline failure does NOT block — so a non-pytest repo is genuinely gated (blocking-capable) without false-positive-blocking a repo with a pre-existing red suite. | High | Open |
| FR-004 | Named gate handler registry | As a maintainer, I want a registry of named gate handlers, with today's pre-review engine registered as the first handler keyed to the `for_review` edge, so gates are addressed by name rather than a hardcoded call. | High | Open |
| FR-005 | Versioned declarative gate-binding schema with half-B-ready discriminator | As a maintainer, I want a versioned gate binding `{on_transition, handler, handler_kind, schema_version, fail_open, provenance?}` that is explicit and `extra`-forbidding, where `handler_kind` defaults to `mission_step_contract` and is **inert in half A** but lets a later executable-asset handler be named without a breaking schema change. | High | Open |
| FR-006 | Bindings resolve through the existing activatable kind | As a maintainer, I want half-A gate handlers bound and resolved through the existing `mission_step_contract` kind (no new `gate` ArtifactKind), so the binding rides current activation with no new enumeration surfaces. | High | Open |
| FR-007 | Explicit binding resolution join and loader | As a maintainer, I want the hook to resolve bindings by (1) computing the activated URN set via `filter_graph_by_activation`, then (2) loading the gate bindings for the active mission type from a named loader (the DRG graph does **not** carry the binding payload), then (3) retaining only bindings whose `handler` resolves to an activated URN — so the mechanism mechanically closes instead of assuming the graph carries bindings it does not. | High | Open |
| FR-008 | Lane-edge → (mission type, action) → binding ownership and precedence | As a maintainer, I want the WP-lane hook to deterministically resolve the **mission type** (from `meta.json` via the transition's mission slug) and map the target lane to its owning action and step-contract (e.g. `for_review` → the active mission's review contract) to locate the applicable bindings, with a defined precedence/conflict rule when more than one binding matches the same `on_transition` edge, so binding ownership across the two state machines (mission-action FSM vs WP-lane FSM) is unambiguous. When the resolved `(mission, action)` has no contract or no matching binding, the gate surfaces a visible `NO_COVERAGE` warning that is **distinguishable from "handler not activated"** — never a silent skip (guards the mission-type-axis coupling for non-`software-dev` missions). | High | Open |
| FR-009 | Consumer-repo internal-import leak removed, activation is sole selector | As a consumer maintainer, I want the hardcoded import of `tests.architectural._gate_coverage` removed from the always-on transition path, with the internal `GateCoverageScopeSource` (and that import) reachable **only** when the Spec-Kitty handler is the activated handler — `_is_spec_kitty_source_repo` retired or demoted to a private internal of `GateCoverageScopeSource` and forbidden from gating impl selection — so the pre-review facet of #2534 is closed structurally even under misconfigured activation. | High | Open |
| FR-010 | Layout-agnostic gating for non-pytest repos | As a consumer maintainer, I want a non-`src/specify_cli/`, non-pytest project gated by its own declared test command, with results parsed into a verdict, so the pytest-layout papercut (#2330 pre-review facet) no longer applies. | High | Open |
| FR-011 | Single test-command authority | As a maintainer, I want the `ScopeSource` to be the sole authority for "what command proves the change," consumed by **both** baseline capture and the head run, and the third override key `review.pre_review_test_command` reconciled (re-pointed at the port or deprecated), so the command is not resolved in three uncoordinated places. | High | Open |
| FR-012 | No-config baseline is a visible warning | As an operator, I want a repo that declares no test command to yield a visible `NO_COVERAGE` warning on transition, never a silent pass and never a crash. | High | Open |
| FR-013 | Fail-open on handler error, with two enumerated hard-stops | As an operator, I want every handler **execution error** to degrade to a visible "unverified" warning, with exactly two legitimate non-completions: the opt-in `NEW_FAILURES` block and the incumbent terminal interruption (`TIMED_OUT`/`CANCELLED`). | High | Open |
| FR-014 | Deterministic verdict aggregation | As an operator, I want multiple activated handlers' verdicts aggregated deterministically: a fixed dispatch order, a block iff `block_enabled AND any handler NEW_FAILURES AND not force`, each handler contributing at most one warning, and a faulting handler never suppressing another handler's verdict. | High | Open |
| FR-015 | Gate terminology registered against the overloaded glossary | As a maintainer, I want `transition gate`, `gate handler`, and `gate binding` registered as canonical terms (in **both** the glossary pack and `docs/context/orchestration.md`) with "Do NOT confuse with" guards against the five existing senses — `dependency gate`, `merge dependency gate`, `branch strategy gate`, `diff compliance gate`, `sonar quality gate` — so the new terms don't fragment the (now first-order, enforced) glossary. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Behaviour-preservation parity through the hook | The refactored gate reproduces identical `(outcome, scope, transition metadata, block/exit, console)` to the pre-refactor gate across 100% of a scenario set that exercises **all six** `GateOutcome` members and **both** legitimate hard-stops, run **through** `_mt_run_transition_gates`. The golden's expected values MUST be **captured from the base commit against the incumbent hook before the refactor** (a committed fixture, red-first against the OLD function) — never regenerated from the new implementation (which would be a circular oracle). | Reliability | High | Open |
| NFR-002 | Fail-open under fault injection, per handler | Under injected handler execution exceptions, 0 transitions crash and 0 transitions are blocked by the failing handler; **each** faulting handler surfaces exactly one visible "unverified" warning, and co-firing handlers' verdicts are unaffected. | Reliability | High | Open |
| NFR-003 | Non-vacuous resolution guard | Binding-resolution tests must include a positive arm (a binding resolves to a loaded/activated node) AND a negative-control arm (a non-activated binding does not resolve); a resolution test that would pass against an empty graph is rejected in review. | Testability | High | Open |
| NFR-004 | Portable-path verdict fidelity | Two fixtures prove baseline-relative semantics: a non-pytest/non-JUnit consumer with a **newly** failing test yields a blocking-capable `NEW_FAILURES` (not `NO_COVERAGE`); a consumer with a **pre-existing** baseline failure does NOT block. Separately, the inert `handler_kind: asset` / `provenance` fields round-trip through load→serialize byte-stable, and adding the `gates` field does not reintroduce `gates: []` into previously-clean contracts on re-save. | Correctness | High | Open |
| NFR-005 | Bounded resolution cost per transition | The inverted hook loads the doctrine graph **and** the mission-type binding set at most once each per transition (not once per candidate handler); binding resolution performs no per-node re-resolution. | Performance | Medium | Open |
| NFR-006 | Code quality gates | New/changed code passes `mypy --strict` and `ruff` with zero issues, cyclomatic complexity ≤ 15 per function, and ≥ 90% line coverage on new code. | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No new `gate` ArtifactKind — content-vs-relationship principle | Gate handlers bind through the existing `mission_step_contract` kind; no new activatable `gate` ArtifactKind. Rationale is the durable principle (not merely the #2468 cost): **promote** to a first-class kind when introducing a new distributable *content* artefact with its own files/repository/provenance (e.g. glossary pack); **reuse/attach** when declaring a *relationship/configuration* on an existing artefact — a gate binding is a field, not a standalone repository. This principle is to be recorded in a short ADR at plan time (paralleling the glossary-first-order ADR). | Technical | High | Open |
| C-002 | Native handlers only — no executable assets | Executable / third-party gate assets (the execution-trust boundary, #2599 / Mission D, half B) are OUT; this mission ships native named handlers only. The `handler_kind` discriminator (FR-005) is the forward-compatible seam so half B needs no breaking schema change. | Technical | High | Open |
| C-003 | Two enumerated hard-stops; fail-open otherwise | The only transition non-completions are (1) the opt-in `NEW_FAILURES` block and (2) the incumbent terminal interruption (`TIMED_OUT`/`CANCELLED`). Every other handler-execution failure must degrade to a visible warning. No new hard-stop may be introduced. | Technical | High | Open |
| C-004 | PR-bound landing | All changes land via pull request to upstream; no direct pushes to `origin/main`. | Process | High | Open |
| C-005 | ATDD red-first with regression guards | Every work package is authored red-first and carries the mission's non-negotiable regression guards (parity-through-hook, per-handler fail-open, non-vacuous resolution, portable-verdict fidelity, and the #2534/#2330 pre-review-facet closure proofs including the erroneous-activation case). | Process | High | Open |
| C-006 | Scope boundary — only the `for_review` pre-review gate | Half A inverts **only** the `→ for_review` pre-review gate as the reference cut. Sibling surfaces retain repo-shape coupling and are explicitly out of scope, tracked as follow-up: the `mission accept` `src/`+`tests/` path-convention gate (#2330 item 1), the mission-review Python-only gates (#2330 item 2), `post_merge/stale_assertions.py` (`tests/**/*.py` / ast), `acceptance/gates_core.py` C7 (GitHub-Actions evidence), and the remaining ~34 hardcoded transition gates across `implement.py` / `accept.py` / `policy/merge_gates.py`. | Technical | High | Open |

### Key Entities

- **ScopeSource** (port): the injectable contract for the repo-shape-varying concerns — `test_command()`, `file_to_scope()`, `parse_results()`. "Which files changed" is NOT on the port; it is the shared canonical merge-base+diff input.
- **GateCoverageScopeSource / DeclaredCommandScopeSource**: internal (behaviour-preserving, pytest+JUnit) and portable (declared-command, result-parsing) implementations.
- **Gate binding**: a versioned doctrine declaration attaching a named handler to a status-transition edge (`on_transition`, `handler`, `handler_kind`, `schema_version`, `fail_open`, optional `provenance`).
- **Gate handler / registry**: named, dispatchable checks; today's pre-review engine is the first registered handler.
- **Binding resolution join**: activated-URN-set (from `filter_graph_by_activation`) ⋈ mission-type binding set (from the named loader) → active bindings for an edge.
- **Gate verdict / outcome**: the existing six-member `GateOutcome` contract, preserved.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A consumer project on a non-pytest, non-`src/specify_cli/` layout can advance a work package to `for_review` with its own declared test command running as the gate, its output **parsed into a real blocking-capable verdict**, and **zero** references to Spec Kitty's internal test-tree module — even when the Spec-Kitty handler is erroneously activated — closing the pre-review facet of #2534 and #2330 (proven by dedicated closure tests).
- **SC-002**: On the Spec Kitty repository, the pre-review gate produces **identical** results before and after the change across 100% of a scenario set covering all six outcomes and both hard-stops, measured **through the inverted hook** (verdict + metadata + block/exit + console).
- **SC-003**: Toggling a gate binding's activation in doctrine changes whether that gate runs on the transition, with **no Python edit** between the active and inactive states; and a `handler_kind: asset` binding round-trips inert.
- **SC-004**: Under fault injection, **100%** of handler execution failures produce a visible "unverified" warning and **0** transitions crash or are silently passed; multi-handler aggregation is deterministic.

## Assumptions

- The existing charter-activation machinery (`PackContext.from_config` → `filter_graph_by_activation`) and the #2843 stem→URN resolution fix are the substrate the inverted hook mirrors (a pattern to copy, not a seam to ride — the DRG carries no binding payload, so a separate mission-type binding load + join is required).
- The canonical merge-base + diff changed-files surface is the single source of truth for "which files changed" and is reused, not re-derived per implementation. As a behaviour-preserving strangler, this mission **inherits** the known P1 bug #2741 (the gate diffs the working tree, not the WP commit range, so a pre-transition commit silently yields `no_coverage`) unchanged — fixing it is out of scope and tracked separately; parity-through-hook explicitly preserves this behaviour rather than fixing it.
- The mission-scoped tracker items for the strangler steps are epic #2535's sub-issues: **#2595** (ScopeSource port, IC-02), **#2596** (register first handler, IC-03), **#2598** (invert the hook, IC-05). Adjacent gate seams #2801/#2573 (skip-flag/disable-env) and #2803 (`review.test_command` resolution) are out of scope and must not be re-opened as regressions of this work.
- The `for_review` edge is the first and reference transition to be gated; the binding schema (`on_transition`) enables `in_review` / `approved` edges but gating them is not required for this mission's acceptance.
- Reusing `mission_step_contract` (rather than promoting a `gate` kind) does not foreclose Mission D/#2599: half B's axis is making the ASSET kind executable+activatable, orthogonal to the gate kind — with FR-005's `handler_kind` discriminator as the forward-compatible seam.
