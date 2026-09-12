# Data Model: Doctrine-Controlled Transition Gates (half A, epic #2535)

**Phase**: 1 · **Traces**: `spec.md` FR/NFR/C · **Companion**: `research.md`, `contracts/`

Every concrete surface below is named with its module home, fields, invariants, and
transitions, and traced to FR IDs. Signatures are design intent (Phase 1), not committed code.

---

## 1. `ScopeSource` (port) — `src/specify_cli/review/scope_source.py` (new)

A `typing.Protocol` (`@runtime_checkable`, mirroring `doctrine/sources/protocol.py:53`)
covering **only** the repo-shape-varying concerns. "Which files changed" is **not** on the
port; it is the shared canonical merge-base+diff input, passed to the gate. (FR-001)

```python
@runtime_checkable
class ScopeSource(Protocol):
    def test_command(self) -> list[str] | None:
        """Runnable argv the gate executes at head, or None when the repo
        declares no command (no-config → NO_COVERAGE warn, never a crash)."""

    def file_to_scope(self, path: str) -> tuple[str, ...]:
        """Map ONE changed file → zero+ test targets. () = contributes no
        scope (not an error). The internal impl narrows; the portable impl
        returns () (no narrowing → whole declared suite)."""

    def parse_results(self, raw: RawRunResult) -> tuple[BaselineFailure, ...]:
        """Turn a RAW (unparsed) run into per-failure identities. Internal impl
        parses JUnit XML from raw.output_artifact_path; portable impl parses the
        declared command's own stdout/stderr. RESTORED after the squad F1
        finding — without it the portable path is decorative (a failing suite
        collapses to NO_COVERAGE)."""
```

**`RawRunResult` (new)** — the port's parse input, produced by the engine running `test_command()`
**without parsing** (home: `src/specify_cli/review/scope_source.py`):

```python
@dataclass(frozen=True)
class RawRunResult:
    returncode: int
    stdout: str
    stderr: str
    output_artifact_path: Path | None   # e.g. the JUnit XML the internal impl wrote
```

**Why not `HeadRunResult`.** `HeadRunResult` (`pre_review_gate.py:398-408`) is **already parsed**
(it carries `current_failures` and has no raw-output field), so feeding it to `parse_results`
leaves the portable impl nothing to parse → it collapses to `NO_COVERAGE` (the exact decorative-gate
regression this mission kills). The port consumes `RawRunResult` (pre-parse); the engine builds
`HeadRunResult` **from** `parse_results(raw)` output, not the other way round.

**Invariants.**
- Never raises for environmental problems — surfaces via return value (the `OrgDoctrineSource`
  discipline, `protocol.py:16-17`). `test_command() -> None` is the no-config signal, not an
  exception.
- `changed_files: tuple[str, ...]` is **passed in** to the gate (shared SSOT from
  `core.vcs.git.merge_base_changed_files` via `tasks_move_task.py:927`), never a port method —
  the two impls cannot diverge on it. (FR-001)
- The port is the **sole** test-command authority, consumed by baseline capture **and** the
  head run (FR-011); it supersedes `resolve_pytest_command` (`_interpreter.py:32`) as a
  cross-repo concern and reconciles the third key `review.pre_review_test_command`
  (`tasks_move_task.py:785`).

### 1a. `GateCoverageScopeSource` (internal, behaviour-preserving) — FR-002

- **`test_command()`** → the incumbent pytest argv; injects `--junitxml`/`-q` **inside this
  impl** (moved from the shared runner, `pre_review_gate.py:656`), not on the port.
- **`file_to_scope(path)`** → today's `_gate_coverage` census narrowing:
  `_SRC_PACKAGE_PREFIX="src/specify_cli/"` (L104) composite routing + `_TESTS_PREFIX` targets.
- **`parse_results(raw)`** → parses JUnit XML from `raw.output_artifact_path` via
  `_parse_junit_xml` (`baseline.py:151`, imported into `pre_review_gate.py` at `:63`), reused
  unchanged.
- **Obligation.** Reproduces today's exact scope + pytest invocation + JUnit parsing on the
  Spec-Kitty tree — zero behaviour change (NFR-001). Owns `_load_gate_coverage_module`
  (`:167,185`) and the demoted `_is_spec_kitty_source_repo` (`:153`) as **private internals**;
  the `import_module` lives ONLY here (FR-009).

### 1b. `DeclaredCommandScopeSource` (portable default) — FR-003, FR-010

- **`test_command()`** → `shlex.split(review.test_command)` or `None` when unset.
- **`file_to_scope(path)`** → `()` always — **no per-file narrowing**; the declared command runs
  the whole suite (layout-agnostic; deliberately does not relocate #2330).
- **`parse_results(raw)`** → parses the declared command's own `raw.stdout`/`stderr` (or its
  `output_artifact_path`) into per-failure `BaselineFailure` identities so a failing suite yields
  blocking-capable `NEW_FAILURES` (NFR-004), not `NO_COVERAGE`.
- **Verdict is baseline-relative, NOT absolute.** `NEW_FAILURES` keeps its incumbent meaning:
  *new vs baseline*, not *any failure*. The portable path captures its baseline via the **same
  declared command through the port** (the same `test_command()` / `parse_results()`), persisted
  like the internal path's `baseline-tests.json`, and the gate diffs head vs that baseline. A
  naive `parse_results = returncode != 0` (ANY_FAILURES) is **rejected** — it would block a
  consumer with a pre-existing red suite on *every* transition (a false-positive gate). A failure
  present at baseline → pre-existing → does NOT block; a failure absent at baseline but present at
  head → new → blocks.
- **`parse_results` contract (explicit).** Input = a `RawRunResult` (exit code + stdout/stderr +
  optional `output_artifact_path`) — the **unparsed** run, NOT the post-parse `HeadRunResult`.
  Output = the set of failing test identities. Exit code alone is insufficient identity for the
  diff — the parser MUST yield per-failure identities so `diff_baseline` can classify pre-existing
  vs new. A non-zero exit with unparseable output → the whole run counts as failing (surfaced,
  never swallowed).
- **Obligation.** Never imports `_gate_coverage`; never assumes pytest/`src/`. No command
  declared → `test_command() -> None` → gate is a visible `NO_COVERAGE` warn (FR-012).
- **Regression fixture (NFR-004).** A pre-existing-failure fixture: a suite already red at
  baseline → transition NOT blocked; a newly-red test → transition blocked. This proves the
  baseline-relative semantics, not merely that the command ran.

---

## 2. `GateOutcome` — existing, `pre_review_gate.py:742` (unchanged)

Six members, preserved verbatim (FR-013, C-003, NFR-001):

| Member | Shape | Hard-stop? |
|---|---|---|
| `NO_COVERAGE` | empty scope / run didn't complete / no-config / **handler error** | warn |
| `NO_NEW_FAILURES` | ran, no new failures vs baseline | warn/pass |
| `NEW_FAILURES` | ran, ≥1 new failure | **block** iff `block_enabled AND not force` |
| `UNVERIFIED_BASELINE` | baseline uncomputable | warn |
| `TIMED_OUT` | head run exceeded timeout | **terminal interruption** |
| `CANCELLED` | head run interrupted (`KeyboardInterrupt`) | **terminal interruption** |

**Fail-open-on-error mapping.** Any handler *execution* exception (except `KeyboardInterrupt`,
which maps to the terminal `CANCELLED`) → a `NO_COVERAGE` verdict with a visible "unverified"
reason. The two hard-stops are the only non-completions (D-06).

---

## 3. `GateBinding` — contract-level schema on `MissionStepContract.gates`

New **contract-level** field `gates: list[GateBinding] = Field(default_factory=list)` on the legacy
`MissionStepContract` (`doctrine/missions/step_contracts.py:86`, frozen + `extra="forbid"` +
`schema_version`), authored in `built_in_step_contracts/review.step-contract.yaml`. It is
contract/action-level, NOT per-`MissionStepContractStep` — a gate binds an *action's* transition,
not an individual step. Adding to a frozen `extra="forbid"` model is a deliberate versioned
evolution (FR-005). This home is the runtime-wired, activation-filtered `mission_step_contract`
surface the executor consumes (`executor.py:22-24,160,188`), reconciling decisions #1 (attach to
the review step-contract) and #2 (reuse `mission_step_contract`). The unified `MissionStep`
(`models.py:109`) is **not** the home — `MissionType.steps` has no gate-time reader.

```yaml
# authored in review.step-contract.yaml (action: review), alongside the contract's steps
gates:
  - on_transition: "in_progress->for_review"   # "<from_lane>-><to_lane>" edge key
    handler: "spec-kitty-pre-review"           # NAMED; a GATE_REGISTRY key only
                                               # (NOT a DRG candidate; activation keys on the contract URN)
    handler_kind: "mission_step_contract"      # default; inert-in-half-A discriminator
    schema_version: "1.0"                       # per-entry, versioned
    fail_open: true                             # default; unresolved/inactive => advisory
    provenance: "built-in"                      # optional
```

| Field | Type | Default | Rule |
|---|---|---|---|
| `on_transition` | `str` | required | `"<from>-><to>"` lane-edge key; both sides valid lanes |
| `handler` | `str` | required | `GATE_REGISTRY` key only, resolved by plain dict lookup at dispatch; NOT a DRG candidate (activation keys on the owning contract URN) |
| `handler_kind` | `Literal["mission_step_contract","asset"]` | `"mission_step_contract"` | **inert** in half A; `asset` round-trips byte-stable, never executed (FR-005, C-002, NFR-004) |
| `schema_version` | `str` | required | versioned; unversioned/malformed → loud reject |
| `fail_open` | `bool` | `true` | unresolved/inactive binding → advisory (never hard-fail) |
| `provenance` | `str \| None` | `None` | optional marker; round-trips byte-stable |

**Validation invariants (FR-005, US3 AS3/AS4).**
- `model_config = ConfigDict(frozen=True, extra="forbid")` — an unknown key is rejected **loudly**
  at load, never silently dropped.
- `schema_version` required — an unversioned binding is rejected.
- `handler_kind: asset` load→serialize is **byte-stable** and inert (no asset execution attempt).
- `provenance` round-trips byte-stable (NFR-004).

---

## 4. `GateHandler` / `GATE_REGISTRY` — `src/specify_cli/review/gate_registry.py` (new)

Mirrors `mission_v1/guards.py:270` `GUARD_REGISTRY` (dict of name → entry). `GateHandler` is a
**frozen dataclass**, NOT a bare callable, so dispatch is uniform across WP04/WP06/WP09:

```python
@dataclass(frozen=True)
class GateHandler:
    name: str
    edge: str                                    # e.g. "in_progress->for_review"
    run: Callable[[TransitionGateContext], GateVerdict]

GATE_REGISTRY: dict[str, GateHandler] = {
    "spec-kitty-pre-review": GateHandler(
        name="spec-kitty-pre-review",
        edge="in_progress->for_review",
        run=_spec_kitty_pre_review_handler,      # first registered
    ),
}

def get_gate_handler(name: str) -> GateHandler: ...   # KeyError on miss = misconfig
```

- **Dispatch form.** The hook calls `get_gate_handler(b.handler).run(ctx)` — never a bare
  `GATE_REGISTRY[name](ctx)`. WP06/WP09 must consume this exact shape, not invent a variant.
- **`TransitionGateContext` single home** = `gate_registry.py` (WP04-owned); WP06/WP09 import it,
  never redeclare it.
- **Named-handler contract.** A `run` receives a `TransitionGateContext` (the changed-files SSOT,
  resolved `ScopeSource`, baseline, repo_root, force flag) and returns a `GateVerdict`
  (`pre_review_gate.py:754`). It must be pure-ish and self-contained; it never `Exit`s — the hook
  owns exit/aggregation. (FR-004)
- **First handler.** `_spec_kitty_pre_review_handler` wraps the **post-WP03**
  `evaluate_pre_review_gate` — after WP03 that function takes an **injected `ScopeSource`**
  (`evaluate_pre_review_gate(scope_source, *, repo_root, baseline, ...)`), NOT the pre-WP03
  `changed_files` + `filter_groups` positional shape (`pre_review_gate.py:853`). WP04's handler and
  WP09's parity path bind to this one post-WP03 contract. Registry membership is the callable
  source; **activation** (on the owning contract URN) decides whether it runs (D-04). (FR-004)

---

## 5. Binding resolution join — `resolve_active_gate_bindings(...)` (name)

Home: `src/specify_cli/review/gate_bindings.py` (new). Named the **activation ⋈ binding join**.
(FR-007, NFR-005)

**Pure-function extraction (complexity ≤ 15, NFR-006).** `resolve_active_gate_bindings(
activated_msc_urns, owning_contract_urn, bindings, edge_key) -> list[GateBinding]` is a
**standalone pure function** —
inputs in, active-binding list out, no I/O — with its own focused unit tests (positive +
negative-control arms, NFR-003). The hook (`_mt_run_transition_gates`) stays a **thin
orchestrator**: it performs the I/O (config read, graph load, contract load, dispatch) and
delegates the join and the aggregation (§7) to pure functions it merely calls. This keeps each
function at complexity ≤ 15 and testable in isolation.

**The named binding loader.** `load_gate_bindings(repo_root, mission, action) ->
list[GateBinding]` reads the review contract's `gates` off the `MissionStepContract` model — the
DRG carries no binding payload (`drg/models.py:292-311`). It delegates to
`MissionStepContractRepository.get_by_action(mission, action)` (`step_contracts.py:160`) — the same
repository the executor already uses (`executor.py:160`) — and returns that contract's `gates`.
The `mission` param is **required** and load-bearing: `get_by_action` keys on `(mission, action)`,
and only `software-dev` ships a `review` action contract (research → gathering/methodology/output/
scoping/synthesis; documentation → accept/audit/design/discover/generate/publish/validate). The
hook resolves the mission type from `st.mission_slug` → the mission's `meta.json` (mission type
field), NOT hardcoded. This is the "named loader" FR-007 requires, on the runtime-wired legacy
contract surface.

**No-contract / no-binding path (mission-type-axis coupling guard).** All missions share the
9-lane FSM and hit `for_review`, so a research / documentation / consumer WP resolves to **no**
`(mission, review)` contract — or a `software-dev` contract with no `for_review` binding. This
MUST NOT silently vanish the gate. It resolves to a **visible `NO_COVERAGE` warn that is
distinguishable** from "handler not activated": the reason string names the missing-contract /
no-binding cause (e.g. `no gate binding for (<mission>, review→for_review)`), NOT the generic
inactive-advisory wording. The two conditions are separate branches, separately worded (FR-008,
FR-012).

**The join (two keys, FR-007).** The activation gate is the **owning review contract's URN**, NOT
the handler. The handler is a `GATE_REGISTRY` name (a plain dict key), never a DRG candidate.
1. **Activated URN set** — `PackContext.from_config(repo_root)` (`pack_context.py:184`,
   fail-**closed** on `OrgPackEnvVarUnsetError`/`OrgPackSubdirEscapeError` per the copied
   `_resolve_pack_context` pattern, `executor.py:275`) → `filter_graph_by_activation(
   load_validated_graph(repo_root), pack_context)` (`drg.py:433`) → the surviving
   `mission_step_contract` node URNs.
2. **Owning-contract URN** — the URN of the contract `get_by_action(mission, action)` located,
   in the canonical form `mission_step_contract:<mission-type>/<id>` (e.g.
   `mission_step_contract:software-dev/review`, verified `drg.py:271`). This URN being among the
   survivors is **what gates whether the review contract's bindings fire at all**.
3. **Retain** — `resolve_active_gate_bindings` keeps a binding iff
   `b.on_transition == edge_key AND owning_contract_urn ∈ activated_msc_urns`. The handler is then
   resolved by a plain `GATE_REGISTRY[b.handler]` dict lookup at dispatch (KeyError on miss =
   misconfig, surfaced) — it is **not** matched against a DRG URN.

> **Why not gate on the handler URN.** `spec-kitty-pre-review` is a registry name; there is no
> `mission_step_contract:.../spec-kitty-pre-review` node, so `_candidate_urn(handler)` would return
> `None`, membership would always fail, and `active` would be permanently empty → permanent
> `NO_COVERAGE` (a decorative gate). Gating on the owning-contract URN is the only join that both
> fires and satisfies the NFR-003 positive arm without a self-fulfilling mock.

**Bounded cost (NFR-005).** One graph load + one filter + one contract-bindings load per
transition. The survivors are computed by a single set-membership test of the owning-contract URN
— **no per-node re-resolution, no per-candidate re-load**.

**Sequence (per transition).**
```
target lane edge (from->to)
  └─ mission = resolve_mission_type(st.mission_slug -> meta.json)                # mission-type axis
  └─ map edge → owning action → (mission, review) contract (§6)                  # 1 table lookup
  └─ pack = PackContext.from_config(repo_root)           # fail-closed on env/escape
  └─ graph = filter_graph_by_activation(load_validated_graph(repo_root), pack)   # 1 load + 1 filter
  └─ contract = get_by_action(mission, action)                                   # review contract (+ its URN)
  │    (no contract / no for_review binding -> distinguishable NO_COVERAGE warn)
  └─ bindings = contract.gates                                                    # 1 load (review contract .gates)
  └─ active = resolve_active_gate_bindings(activated_msc_urns,                    # PURE fn
               owning_contract_urn=contract.urn, bindings=bindings, edge_key=f"{from}->{to}")
               #  retain iff on_transition == edge_key AND owning_contract_urn in activated_msc_urns
  └─ for b in active: GATE_REGISTRY[b.handler].run(ctx)  →  aggregate_verdicts (§7)   # plain dict lookup
```

**Negative control (NFR-003).** When the **owning review contract's URN** is not in the activated
set (its mission type deactivated), every binding on it is absent from `active` — detectable, not
silent. The resolution test carries a positive arm (contract URN activated → binding fires) and a
negative-control arm (contract URN deactivated → binding does not fire); because the gate keys on
a real graph URN (not the handler name), a test cannot be greened by a self-fulfilling mock — a
test that would pass against an empty graph is rejected in review.

---

## 6. Lane-edge → (mission, action) → contract mapping (FR-008)

Explicit, deterministic table joining the WP-**lane** FSM edge to its owning
**(mission-type, action)** and that action's step-contract (the binding home, D-01/D-05). The
mission-type axis is required because `get_by_action` keys on `(mission, action)` and only
`software-dev` ships a `review` contract:

| Lane edge (`on_transition`) | Owning (mission, action) → contract | Gated in half A? |
|---|---|---|
| `in_progress->for_review` | `(<resolved mission>, review)` → `review.step-contract.yaml` `.gates` | **Yes** (reference cut) |
| `for_review->in_review` | `(<resolved mission>, review)` → review contract `.gates` | schema-enabled; not required |
| `in_review->approved` | `(<resolved mission>, review)` → review contract `.gates` | schema-enabled; not required |

- `<resolved mission>` = mission type resolved from `st.mission_slug` → `meta.json`, never
  hardcoded. A `(mission, review)` that has no contract (research/documentation/consumer) or a
  contract with no matching `for_review` binding → **distinguishable `NO_COVERAGE` warn** (§5), not
  a silent vanish.
- Half A gates **only** `in_progress->for_review` (C-006). The schema (`on_transition`) admits
  the other edges but the mission does not require gating them (Assumptions §).
- The lane FSM is `status/wp_state.py` (State-Pattern); the edge is observed at the CLI hook
  (`tasks_move_task.py`), generalizing the existing `in_progress->for_review` special-case in
  `coordination/status_transition.py::_prepare_event` (L436-530).

**Precedence / conflict rule (FR-008).** When **more than one** activated binding matches the
same `on_transition` edge on the same step, **all** fire — there is no last-wins override.
Dispatch order is a **stable sort** by `(declaration_index_within_step, handler)` so the order is
deterministic (NFR-001 requires a fixed dispatch order for parity). Their verdicts aggregate per
§7; a conflict is a union, never a silent drop.

---

## 7. Verdict aggregation — `aggregate_verdicts(verdicts, *, block_enabled, force) -> AggregateVerdict` (FR-014, NFR-002, C-003)

A **standalone pure function** (home: `src/specify_cli/review/gate_bindings.py`), not logic inlined
in the hook. It takes the ordered verdict list + `block_enabled`/`force` flags and returns the
aggregate decision (terminal / block / warn-pass + the per-handler warnings). Its own focused unit
tests cover the **full outcome × precedence matrix** (all six outcomes × terminal/block/warn ×
single/multi-handler), independent of any real handler.

**Half-A reality (say it plainly).** FR-014 multi-handler aggregation ships with **only one
production binding** (the Spec-Kitty pre-review handler). The N-handler paths are therefore a
**seam exercised by synthetic handlers in tests only** — `aggregate_verdicts` and
`resolve_active_gate_bindings` are unit-tested with fabricated verdicts/handlers; no second real
handler exists in half A. This is deliberate forward-compatibility, not dead code, and the tests
are the sole exercise of the multi-handler branches.

Given verdicts `V = [v1..vn]` gathered in the §6 dispatch order:

**Deterministic precedence (highest first).**
1. **Terminal interruption** — if **any** `vi.outcome in {TIMED_OUT, CANCELLED}`: hard-stop,
   set `transition_applied=False`, `Exit(1)` — preserving the incumbent order (checked before the
   block, `tasks_move_task.py:1285` before `:1298`).
2. **Block** — else block **iff** `block_enabled AND any(vi.outcome == NEW_FAILURES) AND not
   force`. `Exit(1)`.
3. **Warn/pass** — else the transition completes; each `vi` contributes at most one console
   warning.

**Invariants.**
- **≤1 warning per handler** — a handler surfaces exactly one visible line, even on error
  (NFR-002).
- **No cross-suppression** — a faulting handler (degraded to `NO_COVERAGE`) never removes another
  handler's `NEW_FAILURES` from the block computation (US4 AS3). Aggregation reads every verdict.
- **Fail-open per handler** — each handler dispatch is wrapped in try/except:
  `KeyboardInterrupt → CANCELLED` (terminal); any other `Exception` /
  `GateAuthoritiesUnavailable → NO_COVERAGE` "unverified" warn (mirrors the incumbent three-catch
  at `tasks_move_task.py:1241/1248`). (FR-013, NFR-002)

---

## 8. `TransitionGateContext` — hook↔handler payload (home: `gate_registry.py`, WP04-owned)

Frozen dataclass passed to each `GateHandler.run`, carrying the shared, per-transition inputs so a
handler resolves nothing itself (NFR-005). Single home = `gate_registry.py`; WP06/WP09 import it,
never redeclare it:

| Field | Type | Source |
|---|---|---|
| `changed_files` | `tuple[str, ...]` | merge-base+diff SSOT (`tasks_move_task.py:927`) |
| `scope_source` | `ScopeSource` | impl chosen by activation, not by `_is_spec_kitty_source_repo` |
| `baseline` | `BaselineTestResult \| None` | `baseline-tests.json` (`tasks_move_task.py:1212`) |
| `repo_root` | `Path` | worktree or main repo root |
| `force` | `bool` | `--force` flag |
| `from_lane` / `to_lane` | `Lane` | the edge being gated |

---

## FR trace summary

| Surface | FR/NFR/C |
|---|---|
| `ScopeSource` port (3 methods, shared `changed_files`) | FR-001, FR-011 |
| `GateCoverageScopeSource` | FR-002, FR-009, NFR-001 |
| `DeclaredCommandScopeSource` | FR-003, FR-010, FR-012, NFR-004 |
| `GATE_REGISTRY` / first handler | FR-004 |
| `GateBinding` schema + `handler_kind` | FR-005, C-002, NFR-004 |
| Reuse `mission_step_contract` kind | FR-006, C-001 |
| `resolve_active_gate_bindings` (pure) + `load_gate_bindings(repo_root, mission, action)` | FR-007, NFR-003, NFR-005 |
| `aggregate_verdicts` (pure) — full outcome × precedence matrix | FR-014, NFR-002, NFR-006 |
| Lane→(mission,action)→contract mapping + precedence + distinguishable no-contract warn | FR-008, FR-012 |
| Retire dual selector / delete always-on import | FR-009 |
| Aggregation + two hard-stops + fail-open | FR-013, FR-014, C-003, NFR-002 |
| `GateOutcome` six members (unchanged) | FR-013, NFR-001 |
