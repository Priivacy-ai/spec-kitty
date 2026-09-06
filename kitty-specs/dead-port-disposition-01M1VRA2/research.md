# Research: Dead-Port Disposition

**Mission**: `dead-port-disposition-01M1VRA2` · **Date**: 2026-09-06
**Purpose**: resolve every Technical Context unknown and every domain rule before design. All findings were re-derived from source at `main` (`3a4f92b41`), not taken from the ADR text.

## R-1. Is the concrete class load-bearing anywhere?

- **Decision**: No. It is safe to delete once the two capabilities the bridge uses are promoted.
- **Rationale**: Production importers are exactly `runtime_bridge.py:195` (binding) and `runtime_bridge_engine.py:80` (`TYPE_CHECKING` only). The bridge uses two members beyond the eight `emit_*` methods: `for_feature` (`:1552`, `:2739`) and `seed_from_snapshot` (`:1614`, `:2745`, plus `runtime_bridge_engine.py:344`). The resolved `mission_id` is stored but never read (`event_emitter.py:40,51`). Tests: one live import (`tests/specify_cli/events/test_decision_log_coord.py:17`), 14 patch sites on the bridge-module attribute, two reservation comments.
- **Alternatives considered**: keep the concrete class renamed `NullRuntimeEventEmitter` (ADR transitional form) — rejected; the two-class state the ADR names as target has one name, and no transition is needed because all callers are in-repo.

## R-2. Should `for_mission` / `seed_from_snapshot` be added to the Protocol?

- **Decision**: No. Add them to `NullEmitter` (and keep them on `_BufferingRuntimeEmitter`, which already has `seed_from_snapshot`); leave the Protocol at the eight `emit_*` methods.
- **Rationale**: The engine types its `emitter` parameter against the Protocol (`_internal_runtime/engine.py:191,251,513,775`) and only calls `emit_*`. Seeding and construction are bridge-side concerns on the object the factory returned. Widening the Protocol would force every structural adapter — including `DecisionGitLog`, which today implements only the emit surface — to implement seeding, and would make the `MagicMock(spec=Protocol)` fixtures in `test_decision_log_coord.py` grow methods they never exercise. A future producer that needs seeding implements it; the factory contract (`contracts/emitter-seam.md`) says the returned object *may* expose `seed_from_snapshot` and the bridge calls it inside its existing `try` (`runtime_bridge.py:1611-1616`, `:2744-2751`).
- **Consequence for fix two**: `DecisionGitLog` must gain a `seed_from_snapshot` pass-through, because `advance_run_state_after_composition` seeds whatever emitter it receives (`runtime_bridge_engine.py:344`) and after the fix it receives the wrap. One delegating method; no behavior.
- **Alternatives considered**: widen the Protocol (rejected above); special-case the composition path to seed `ctx.sync_emitter` and emit via `ctx.emitter_for_engine` (rejected — two emitter references on one path is the defect class being closed).

## R-3. What exactly is the flush-target defect, and what is the right red-first fixture?

- **Decision**: The defect is on strict-policy `decision_required` advances (and, independently of policy, on composition dispatch). The red-first fixture is a `decision_required` advance, never a terminal one.
- **Rationale**: `DecisionGitLog` persists only `emit_decision_input_requested` / `emit_decision_input_answered` (`decision_log.py:147-160`); every other emit is pass-through. The engine's `decision_required` and `terminal` branches are mutually exclusive (`runtime_bridge_engine.py:299-305`; engine `:448,476`). Under strict policy the buffer is installed for **every** advance (`runtime_bridge.py:2129-2150`) and flushed into the plain seam (`:2187`), so a `DecisionInputRequested` raised on the gated path is dropped; a terminal advance buffers only `MissionRunCompleted`, which the log ignores. The composition path passes `ctx.sync_emitter` outright (`:1976`), so its `_emit_decision_required` (`runtime_bridge_engine.py:226`) bypasses the log regardless of policy.
- **Strict policy shape for tests**: `_retrospective_blocks_completion` is true iff `enabled and timing == "before_completion" and failure_policy == "block"` (`runtime_bridge_retrospective.py:384-390`). Tests monkeypatch `_resolve_retrospective_policy_for_runtime` (pattern already used at `tests/runtime/test_bridge_retrospective.py:200-204`).
- **Ordering / double-emit**: the terminal gate (`:2178-2181`) runs before the flush and discards on refusal; `flush` is one-shot (`runtime_bridge_retrospective.py:138-149`); on the gated path the engine wrote only into the buffer, so the flush is the first and only `DecisionGitLog` write. Rollback is preserved.
- **Alternatives considered**: flush into the plain seam *and* replay decision events into the wrap (rejected: double bookkeeping); make `DecisionGitLog` the engine emitter even under strict policy and drop the buffer (rejected: re-opens the unretractable `MissionRunCompleted` problem the buffer exists to solve).

## R-4. Factory + registry: which idiom, and where does the env gate live?

- **Decision**: Module-level `runtime_emitter_for_mission(...)`, `register_runtime_emitter_factory(f)`, `reset_runtime_emitter_factory()` in `_internal_runtime/events.py`; the `SPEC_KITTY_SYNC_MINIMAL_IMPORT` check runs **at call time** inside the factory. (Decision Moment `01M1VSEWHJM4WAQD7EGN5PA4XJ`.)
- **Rationale**: Mirrors the one proven registration idiom in the tree, `status/adapters.py:201-214` (`ensure_zeitgeist_moment_handlers` / `reset_handlers`), which the ADR names as the pattern. Call-time env read lets tests toggle the gate with `monkeypatch.setenv` without reloading modules and costs one dict lookup. A bridge-module name to patch keeps the 14 rewrites mechanical (`monkeypatch.setattr(rb, "runtime_emitter_for_mission", ...)`) and the oracle's spy wrapping unchanged in shape (`_bridge_oracle.py:471-481` wraps the real callable and returns a `_RecordingProxy`).
- **Alternatives considered**: registry-only (rejected: forces every test to go through the registry and the oracle to grow a registry adapter for no production benefit); class-shaped attribute for compatibility (rejected: violates ADR (a) and preserves the collision).

## R-5. Layer rules: can `_internal_runtime/events.py` import `specify_cli.mission_metadata`?

- **Decision**: Yes.
- **Rationale**: The enforced direction is `kernel <- charter <- {glossary, runtime, mission_runtime} <- specify_cli` (CLAUDE.md §Modularity SSOT), i.e. `runtime` may import `specify_cli` but not `specify_cli.cli` / `specify_cli.next` (`tests/architectural/test_layer_rules.py:323-340`). `_internal_runtime/planner.py:46` already imports `specify_cli.mission_metadata.load_meta`, and `mission_metadata` is on the runtime outbound ledger (`test_layer_rules.py:132,192`). Moving `resolve_mission_identity` (`mission_metadata.py:234`) into `events.py` adds no new ledger entry.

## R-6. Supply chain (`051-supply-chain-install-safety`)

- **Decision**: Not applicable — no dependency is added, upgraded, or removed. `spec_kitty_events` 9.1.6 stays pinned and untouched; the six `mission_next` moment types it provisions are consumed as today.
- **Adversarial evidence**: no security-impacting dependency decision exists, so no challenge pass is required. Recorded here so silence is not mistaken for compliance.

## R-7. Terminology

- **Decision**: Promote as `for_mission`; do not rename the `feature_dir` keyword parameter.
- **Rationale**: The Terminology Canon forbids minting new `feature*` aliases for the Mission domain object; the constructor is a new public surface. `feature_dir` is a pre-existing parameter name used across the bridge (`:1553`, `:2740`, `resolve_mission_identity(feature_dir)`) and the engine adapter; renaming it is a cross-module bulk edit outside this mission's boundary (DIRECTIVE_035). The terminology guard (`tests/architectural/test_no_legacy_terminology.py`) scans docs prose, not identifiers; NFR-006 is therefore enforced by the PR's added-lines grep, recorded in the PR body.

## R-8. Existing tests that constrain the change

| Test | Constraint it imposes |
|---|---|
| `tests/next/test_internal_runtime_coverage.py:173-174` | `emitter.py` re-export identity and exact `__all__` — must be extended with the factory/registry names |
| `tests/runtime/test_bridge_engine.py:408-427` | `advance_run_state_after_composition` seeds the emitter it is given and emits step-issued on it — the wrap must accept `seed_from_snapshot` |
| `tests/runtime/test_bridge_parity.py:1140-1166` | answer-path sync sink records calls via the oracle spy — spy must wrap the factory's return |
| `tests/runtime/test_bridge_retrospective.py:88-147` | buffer records/flushes in order, discard drops, flush tolerates missing target methods — unchanged |
| `tests/specify_cli/next/test_runtime_bridge_composition.py:55-68` | composition tests substitute a `NullEmitter` subclass with `seed_from_snapshot` — becomes a factory patch |
| `tests/status/test_producer_conformance.py`, `tests/contract/test_identity_contract_matrix.py` | reserve the seam by comment only — comments updated, assertions untouched |

## Adversarial evidence

The governing ADR was itself challenged by a pre-merge adversarial squad (architect / debugger / reviewer) before acceptance; the MAJOR finding (terminal-advance framing of the bug) was `changed` in the ADR before this mission was specified. Plan-level contested findings: none raised; the seam design (R-4) was put to the operator as a three-option Decision Moment and `accepted`.
