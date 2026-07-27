# Research: Runtime-Bridge God-Module Decomposition (#2531)

**Mission**: runtime-bridge-degod-01KX8M1C · **FR-002 hard-gate deliverable (SC-008).**
Produced by the FR-002 research pass (Op 01KX8NPN) from the post-spec squad's code grounding. This artifact fixes the seam boundaries, the parity contract, the fixture matrix, and the compat strategy **before** any extraction WP is authored. Full working tables: scratchpad `rbresearch-{A-seams,B-parity,C-compat}.md` + `rbspec-{1..4}.md`.

---

## §Seams — final module boundaries, interfaces, import DAG, extraction order

### Module tree (flat responsibility-named, C-003 sibling convention; `runtime.next.runtime_bridge` import path preserved)
| Module | Responsibility | Key moved symbols |
|--------|----------------|-------------------|
| `runtime_bridge.py` (thin residual) | 4-phase `decide_next_via_runtime`, `query_current_state`, `answer_decision`, `DecideNextContext`, the FR-012 guarded compat re-export block, `__all__`, #2531 pointer | orchestrator only |
| `runtime_bridge_engine.py` (FR-013 adapter) | **sole** home of `_internal_runtime` private access (`.engine` privates + `.planner` `plan_next`) | `_read_snapshot`, `_load_frozen_template`, `plan_next`, `_append_event`, `_write_snapshot` — **grep-complete site list**: `:1322`/`:1375` (both `_load_frozen_template`) + `:1800`/`:1840`/`:2606`/`:3261`/`:3416`. `_advance_run_state_after_composition:1800` (CC23) is **adapter-owned** (body in adapter, thin residual compat delegate) |
| `runtime_bridge_cores.py` (pure) | tasks.md parse (zero-dep leaf `:343–473`); `ArtifactPresenceSnapshot`+`evaluate_guards` (FR-009); `DecisionEnvelope`+`step_or_blocked` materializer (FR-011) | parse family, guard-decision, 29 `Decision(` sites |
| `runtime_bridge_io.py` (ports) | feature-runs index, template/pack discovery, run lifecycle, OC builder, `gather_artifact_presence` fact-port, **`resolve_commit_target`** (lifted pure, see refinement 3) | `_load/_save_feature_runs`, discovery, run-lifecycle |
| `runtime_bridge_composition.py` | dispatch + run-state advance + **FR-008 selection seam** (`_should_dispatch_via_composition`) | composition cluster |
| `runtime_bridge_retrospective.py` | self-contained learning-capture | retrospective cluster |
| `runtime_bridge_identity.py` | hot identity/coord port — **cut LAST** (scar debt #2091/#1978/#1918/#1814/#2069) | identity/coord resolution |

### Key interfaces
- **FR-009**: `gather_artifact_presence(feature_dir, …) -> ArtifactPresenceSnapshot` (port) + `evaluate_guards(snapshot) -> list[str]` (pure; **preserves the fail-closed default**, guard-failure list identical incl. order — SC-007).
- **FR-011**: `DecisionEnvelope` + `step_or_blocked(...) -> Decision` collapsing the 29 open-coded constructions + the 4× `_state_to_action → _build_prompt_or_error → step-or-blocked` triad.
- **FR-010**: `DecideNextContext` (~14-field frozen dataclass) + `decide_next_via_runtime` as a **bootstrap / dependency-gate / composition-dispatch / decision-materialize** early-return chain (each phase `Decision | None`), residual ≤15.
- **FR-013**: `engine_adapter` wraps **all** `_internal_runtime` privates at a **grep-complete** site list (incl. `_load_frozen_template` at `:1322`/`:1375`, not just the 5-site sample); `_advance_run_state_after_composition` (which duplicates the engine's own `next_step` success branch, CC23) is adapter-owned logic with a thin residual compat delegate, never a core.
- **FR-011 (purity nuance)**: `step_or_blocked`'s blocked/query/terminal branch is pure; its **step branch is port-injected** via a `prompt_exists` predicate because `Decision.__post_init__` (`decision.py:129`) stats disk (`Path(prompt).is_file()`) for `kind="step"`.

### Import DAG (acyclic)
`cores` (stdlib/`Lane`/decision types only) ← `io`/`engine` ← `composition`/`retrospective`/`identity` ← thin residual. The `decision.py:428` → orchestrator edge stays **lazy** because `decide_next_via_runtime` remains defined in the parent module (C-007 — no new top-level cycle).

### Extraction order (~10–11 WPs, risk-gated; WP-0 split into WP-0a + WP-0b)
1. **WP-0a parity oracle** (3 entries, capture-and-assert, coverage floor asserted) + **WP-0b compat guard** (per-entry sentinel) — both C-004 blocking gates, proven green on unmodified source → 2. engine-adapter → 3. retrospective → 4. clean `_io` ports → 5. cores + guard-inversion (FR-009) → 6. Decision-builder (FR-011) → 7. composition dispatch (FR-008) → 8. `decide_next` phase-split (FR-010) → 9. **identity/coord port LAST** (its own self-contained WP).

### Refinements to carry into /plan
1. Split ports into `_io` + `_identity` so the hottest fracture is the final isolated WP.
2. **FR-012 count correction: the live patch surface is ~50 symbols, not ~15** (see §Compat) — spec FR-012 number updated.
3. Lift `_wrap_with_decision_git_log`'s commit-target selection (`:226–261`) into a pure `resolve_commit_target` core — the one port interleaving a pure decision inside I/O.

---

## §Parity — the characterization safety net (NFR-001)

### Scope — ALL 3 public entry points (per-entry sub-ledgers)
The refactor touches three public entries and the 29 `Decision(...)` sites are **partitioned** across them — an oracle driving `decide_next_via_runtime` alone leaves ~14 sites (incl. the CC33 `_map_runtime_decision` cluster) unexercised → false-green WP-0. Owning entries: `decide_next_via_runtime:2524` (~15 sites; own sync emit `:2556` + coord commit `:2563`), `query_current_state:3199` (the 4 `_build_*_query_decision` sites, reached exclusively here; no side effects), `answer_decision_via_runtime:3355` (the remaining sites incl. the 10 `_map_runtime_decision` sites; its **own** sync emitter `:3410` + coord commit `:3427`). Oracle drives all three with **per-entry fixture sub-ledgers**. Full table: contracts/parity-oracle.md.

### Normalization/masking contract (over `Decision.to_dict()`, `decision.py:82-166`)
- **MASK** (drop before compare, but preserve None-vs-present so a kind-shape change isn't blinded): `timestamp` (`bridge:2542`), `run_id`, `decision_id` (ULIDs).
- **PATH-NORMALIZE** (relativize to **each run's own repo_root** — copytree tempdirs differ per fixture, so never a shared constant): `workspace_path`, `prompt_file`, **`reason`** (non-obvious carrier — embeds `feature_dir`/`exc` paths), `origin.mission_path` (`bridge:2575`; note `origin.mission_tier` stays STABLE).
- **STABLE** (compare as-is): everything else (kind, agent, mission identity, state, action, wp_id, step_id, `guard_failures`, progress, question/options, is_query, …).
- Test shape: `canonical(decision, root)` then `assert_parity(before, after, root)`, plus a **`reason`-normalizer meta-test** proving masking collapses path noise but NOT a semantic `reason`/field delta.

### Side-effect isolation — CAPTURE-and-assert (BINDING)
Each fixture runs **once against a fresh `copytree` of a frozen snapshot** with a fixed per-run `repo_root`. Run create/advance (`get_or_start_run`) runs **real** on the throwaway copy (its ULID masked). Because a refactor can change WHAT is emitted while returning an identical Decision, the affected seams are **CAPTURE-and-assert (binding equality before/after), not merely stubbed**: the sync emitter (`bridge:2556`), the coord-branch `DecisionGitLog` commit (`bridge:2563`), the retrospective `Confirm.ask` gate, **the answer-path emitter + coord commit (`:3410`/`:3427`), and the IC-02 engine mutations `_append_event`/`_write_snapshot`**. The runtime planner (`next_step`) is **never** stubbed — it is the logic under test.

### Enumerated fixture matrix + coverage floor
**29 `Decision(...)` sites** (19 blocked / 4 step / 4 query / 1 terminal / 1 decision_required) across 7 orchestrator phases (feature-resolve → retrospective), **partitioned by owning entry** (above). Both guards fully branched: `_check_cli_guards` (`:1057`, ~10 branches incl. requirement-ref cross-check) and `_check_composed_action_guard` (`:1515`) across **three** mission families (software-dev / research / documentation) — including **both fail-closed defaults** (the v1 P1 silent-pass fixes) and the 4-way `tasks` `legacy_step_id` union. **Coverage floor (binding): every Decision site ≥1× AND every guard branch ≥1×, each reached from its owning entry — asserted as a checkable count (a hollow oracle is also green on unmodified source).** Ledger ≈ **22–26 fixtures** across the three sub-ledgers → sizes WP-0a.
Highest-risk relocation fixtures (name explicitly): the two fail-closed defaults + the `tasks` legacy-union guard, each asserting identical `guard_failures` **content and order**.

---

## §Compat — monkeypatch preservation (the biggest land-ability risk) + engine-adapter

### Symbol inventory: **50 distinct private symbols** bound by tests
Across all four idioms (`from …runtime_bridge import _x`, `monkeypatch.setattr`, `mocker.patch`, bare `runtime_bridge._x`). Heaviest: `_check_cli_guards` (26 imports), `_state_to_action` / `_compute_wp_progress` (10 patches each), `_build_prompt_or_error` (9), `_advance_run_state_after_composition` (8 patch + 9 attr). Full table with per-symbol counts + decision (RE-EXPORT / KEEP-IN-PLACE / LAZY-ACCESSOR) in `rbresearch-C-compat.md`.

### The false-green minefield (grounded, not hypothesized)
A plain re-export silently makes `patch("runtime_bridge._x")` a **no-op** when the patched leaf is called by another function that moves into the *same* seam (intra-seam call resolves via the seam's own global, not the shim → test passes by coincidence).
- 🔴 `_primary_runtime_feature_dir` — patched 6× (`test_runtime_bridge_identity.py:71-222`) while an unpatched `_resolve_mission_ulid` calls it internally.
- 🔴 `_build_discovery_context` — patched (`test_query_mode_unit.py:751`), reached only via intra-seam movers.
- ⚠ SPLIT-flag: `_state_to_action` / `_compute_wp_progress` / `_build_prompt_or_error` / `_is_wp_iteration_step` (patchable via residual path, dead via render-seam path).
- Mitigation: **KEEP-IN-PLACE** `_wrap_with_decision_git_log` + `_advance_run_state_after_composition` in the residual (also neutralizes the identity-trio + retrospective-pair risks). Names a sibling module *calls* need re-export **AND** the `_wf`-style lazy accessor.

### Guard test (FR-012 / SC-006) — `tests/runtime/test_bridge_compat_surface.py`, two guards
- **(A) behavioral sentinel** — patch each symbol on `runtime_bridge`, drive **the public entry that reaches it**, `pytest.raises` on a sentinel; a no-op patch never fires the sentinel → test fails (catches false-green). **Per-entry reach mapping is binding**: a single-entry sentinel (all patches through `decide_next`) is itself false-green for symbols reached only via `query_current_state` (e.g. `_build_*_query_decision`) or `answer_decision_via_runtime` (e.g. `_map_runtime_decision`) — map each of the 50 symbols to its reaching entry and drive that entry.
- **(B) static AST guard** — identity re-export check (`rb.x is seam.x`) + **forbid function-scope re-imports of compat names** (the structural signature of false-green shadowing).

### Engine-adapter (FR-013) + `__all__`
Single `runtime_bridge_engine.py` owns all `_internal_runtime` privates at a **grep-complete** site list (incl. `_load_frozen_template` at `:1322`/`:1375`) + an arch guard (no core touches engine internals). Introduce `__all__` for the **8 public names** (sibling `merge.py` parity) — nuance: `__all__` governs only `import *`; the 50 privates are preserved by the explicit guarded compat re-export block, **not** by `__all__`.

---

## FR-002 gate status: SATISFIED
All four hard-gate deliverables (seam boundaries, parity contract, fixture matrix, monkeypatch strategy) are fixed above. `/plan` may proceed; WP-0 (characterization lock) is the first, blocking WP.
