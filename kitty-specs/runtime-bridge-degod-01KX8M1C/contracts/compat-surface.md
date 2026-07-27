# Contract: Private-Symbol Compat Surface (FR-012 — the land-ability net)

The biggest land-ability risk. Tests bind to **50 distinct private symbols** on `runtime_bridge` (imports + monkeypatches); relocating a symbol naively **silently** breaks patching (false-green). Full inventory + per-symbol decisions: research.md §Compat / `rbresearch-C-compat.md`.

## The false-green mechanism (why re-export alone is insufficient)
A plain re-export makes `monkeypatch.setattr(runtime_bridge, "_x", …)` a **no-op** when `_x`'s leaf is called by another function that moved into the *same* seam — the intra-seam call resolves via the seam module's own global, not the shim. The test then passes by coincidence, not isolation.

## Per-symbol preservation decision (three strategies)
- **KEEP-IN-PLACE** — symbol stays in the thin residual. Mandatory for `_wrap_with_decision_git_log` (also neutralizes the identity-trio + retrospective-pair risks). **`_advance_run_state_after_composition` is the reconciled case**: its CC23 body is **adapter-owned** (moves to `runtime_bridge_engine.py`, reduced ≤15 for FR-004), but a **thin residual delegate** stays reachable at `runtime_bridge._advance_run_state_after_composition` for its heavy patch (8×) + attr (9×) compat surface — logic in the adapter, compat shim in the residual.
- **RE-EXPORT** — symbol moves to a seam, re-imported into `runtime_bridge` + added to the guarded compat block. Sufficient only when NO intra-seam caller reaches it.
- **LAZY-ACCESSOR** (`_wf`-style, per #2464/merge.py) — required for names a **sibling module calls** through the shim; re-export alone is false-green for these.
- 🔴 grounded high-risk: `_primary_runtime_feature_dir` (patched 6×, intra-seam caller `_resolve_mission_ulid`), `_build_discovery_context`. ⚠ SPLIT-flag: `_state_to_action`, `_compute_wp_progress`, `_build_prompt_or_error`, `_is_wp_iteration_step`.

## `__all__`
Introduce `__all__` for the **8 public names** (sibling `merge.py` parity). It governs `import *` ONLY — it does **not** preserve the 50 private symbols; those live in the explicit guarded compat re-export block.

## The guard test — `tests/runtime/test_bridge_compat_surface.py` (two guards, FR-012/SC-006)
- **(A) behavioral sentinel** — for each of the 50 symbols, patch it on `runtime_bridge`, drive **the public entry that reaches it**, and `pytest.raises` on a sentinel the patch injects. If the patch is a no-op the sentinel never fires → the test FAILS (catches false-green).
  - **Per-entry reach mapping is BINDING.** A single-entry sentinel (all patches driven through `decide_next_via_runtime`) is itself false-green for symbols reached only via `query_current_state` or `answer_decision_via_runtime` — the patched leaf is never executed, so the sentinel never fires and the guard passes vacuously. Each of the 50 symbols MUST be mapped to its reaching entry (`decide_next` / `query` / `answer` — several are reached from more than one; drive each reaching entry), and the sentinel driven through that entry. Symbols on the query/answer-only path (e.g. the `_build_*_query_decision` family via `query_current_state`; the `_map_runtime_decision` cluster via `answer_decision_via_runtime`) MUST have their sentinel driven through query/answer, not `decide_next`.
- **(B) static AST guard** — assert identity re-export (`rb.x is seam.x`) for every relocated symbol, **and forbid function-scope re-imports of compat names** (the exact structural signature of false-green shadowing).

## Gate semantics
This guard is built in WP-0b (its own deliverable, alongside the WP-0a parity oracle) and stays green through every extraction WP that relocates a patched symbol. A false-green (sentinel doesn't fire) or a broken identity check = reject the extraction.
