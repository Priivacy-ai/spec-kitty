# Contract: decide_next() Parity Oracle (the characterization safety net)

The load-bearing safety net for the whole behavior-preserving refactor. Built in WP-0a, proven green on **unmodified** source at the full coverage floor, then re-run as the acceptance gate of every extraction WP. Full derivation: research.md §Parity.

## Scope — ALL THREE public entry points (not just `decide_next`)
The refactor touches three public entries, and the 29 `Decision(...)` sites are **partitioned across them** — an oracle driving `decide_next_via_runtime` alone leaves ~half the sites (including the CC33 `_map_runtime_decision` cluster) unexercised and WP-0 falsely green.
| Public entry | Site | Owns (Decision sites) | Own side effects |
|--------------|------|-----------------------|------------------|
| `decide_next_via_runtime` | `:2524` | ~15 sites reachable here (11 constructed directly `:2545–3015` + the WP-iteration path) | sync emit `:2556`, coord commit `:2563` |
| `query_current_state` | `:3199` | the **4 `_build_*_query_decision`** sites — `_build_finalized_override_query_decision:3059`, `_build_initial_query_decision:3111`, `_build_decision_required_query:3136`, `_build_runtime_query_decision:3166` — reached **exclusively** from here | none (read-only query) |
| `answer_decision_via_runtime` | `:3355` | the remaining sites incl. the **10 `_map_runtime_decision` sites** (`:3582–3798`, CC33) + `_build_wp_iteration_decision` (`:3468–3536`) | its **OWN** sync emitter (`:3410`), snapshot seed via `_read_snapshot` (`:3418`), coord-branch commit via `_wrap_with_decision_git_log`/`DecisionGitLog` (`:3427`) |

The oracle carries **per-entry fixture sub-ledgers**. Coverage floor is scoped per owning entry: every Decision site reached ≥1× **from its owning entry**, every guard branch reached ≥1×. Driving `decide_next` alone can never reach the query/answer-only sites.

## Equality contract — `canonical(decision, repo_root)`
Over `Decision.to_dict()` (`decision.py:82-166`):
- **MASK** (drop before compare, but keep None-vs-present so a kind-shape change isn't blinded): `timestamp` (`bridge:2542`), `run_id`, `decision_id` (ULIDs).
- **PATH-NORMALIZE** (relativize to **each run's own `repo_root`** — the copytree temp dirs differ per fixture run, so the normalizer takes the run's root, never a shared constant): `workspace_path`, `prompt_file`, **`reason`** (non-obvious carrier — embeds `feature_dir`/`exc` paths), `origin.mission_path` (`bridge:2575`). NB `origin.mission_tier` stays STABLE.
- **STABLE** (compare as-is): everything else — `kind`, `agent`, mission identity, `state`, `action`, `wp_id`, `step_id`, `guard_failures` (content **and order**), `progress`, `question`/`options`, `is_query`, …

`assert_parity(before, after, repo_root)` = `canonical(before, root) == canonical(after, root)`.

### `reason` normalizer meta-test (binding — guards against self-blinding)
Path-relativizing free text can swallow a genuine `reason`/field change. WP-0a MUST ship a **normalizer meta-test** proving `canonical()`:
- COLLAPSES pure path noise (two runs under different copytree roots with the same logical decision → equal), AND
- does NOT collapse a **semantic** delta (a changed `reason` phrase, or any STABLE field flip) → the two must compare **unequal**.

## Side-effect isolation — CAPTURE-and-assert (BINDING, not optional)
Comparing `Decision.to_dict()` alone is behavior-change-blind: a refactor that changes **what** is emitted/committed can still return an identical Decision and pass. Therefore the affected seams are **captured and asserted**, not merely stubbed.
Each fixture runs **once** against a fresh `copytree` of a frozen repo snapshot with a fixed per-run `repo_root`:
- Run create/advance (`get_or_start_run`) runs **REAL** on the throwaway copy (its ULID is masked).
- **CAPTURE-and-assert** (binding equality on the recorded payloads before/after): the sync emitter (`bridge:2556`), the coord-branch `DecisionGitLog` commit (`bridge:2563`), the retrospective `Confirm.ask` gate, **and the answer-path emitter + coord commit** (`bridge:3410`/`:3427`) plus the engine mutations relocated in IC-02 (`_append_event`/`_write_snapshot`). A change to emitted/committed content = a parity break = reject.
- The runtime planner (`next_step`) is **never** stubbed — it is the logic under test.

## Fixture matrix + coverage floor (binding, per-entry)
- **29 `Decision(...)` sites** (19 blocked / 4 step / 4 query / 1 terminal / 1 decision_required) across 7 orchestrator phases, **partitioned by owning entry** as above.
- Both guards fully branched: `_check_cli_guards` (`:1057`, ~10 branches incl. requirement-ref cross-check) and `_check_composed_action_guard` (`:1515`) across **3 mission families** (software-dev / research / documentation), including **both fail-closed defaults** and the 4-way `tasks` `legacy_step_id` union.
- **Coverage floor: every Decision site ≥1× AND every guard branch ≥1× — each reached from its owning entry.** Ledger ≈ 22–26 fixtures spread across the three entry sub-ledgers.
- **Named highest-risk fixtures**: the two fail-closed defaults + the `tasks` legacy-union — each asserts identical `guard_failures` content **and order** before/after.

## Gate semantics
- WP-0a done ⇔ oracle green on unmodified source at full coverage-floor across all 3 entries. **The coverage floor itself is a checkable assertion** (site/branch reach tallied and asserted ≥ floor) — a hollow oracle is also green on unmodified source, so green-on-unmodified is necessary but not sufficient.
- Every subsequent extraction WP: oracle stays green (its acceptance gate). A parity break — Decision inequality OR a captured side-effect delta — = the extraction changed behavior = reject.
