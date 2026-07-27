# Adversarial Scope Review — "Already Done" Claims (python-pedro)

**Mission:** `naming-identity-routing-rider-01KV7SFD`
**Reviewer lens:** python-pedro, anti-laziness / scope-understatement focus
**Date:** 2026-06-16
**Method:** every claim refuted against actual `src/` code (file:line evidence). Default posture: "the planner shrank scope lazily; prove the claim false."

---

## Claim 1 — "`coordination/workspace.py` already routes through the seam — no action."

### VERDICT: **UPHELD** (for `workspace.py`); with a **scope-boundary caveat** the planner stated honestly.

`coordination/workspace.py` is genuinely clean. Every compose/parse delegates to the seam:

- `worktree_path` → `_seam_coord_dir_name` (`coordination/workspace.py:167`).
- `branch_name` → `_seam_coord_reconstruct_branch` (`coordination/workspace.py:179`).
- `_compose_mission_dir` → `_seam_coord_mission_dir_name` (`coordination/workspace.py:111`).
- `lane_sparse_checkout_patterns` → `_compose_mission_dir` → seam (`coordination/workspace.py:290`).
- The seam imports are explicit at `coordination/workspace.py:38-42`; there is **no residual inline `f"kitty/mission-…"` or `f"{slug}-{mid8}-coord"` literal** anywhere in the file.

I tried to refute it and could not. There is no parallel grammar in `workspace.py`.

**Caveat (NOT a refutation of Claim 1, but worth recording):** the claim is narrowly about `workspace.py`, and the planner correctly *bounded* it that way (research Decision 2; C-005 defers all write-side/coord topology to 3.2.2). I scanned the rest of `coordination/` for shadow composes to be sure the planner did not wave off a sibling:
- `coordination/transaction.py:772` — `f"{safe_mission_slug}-{safe_mid8}: {exc}"` is an **error-message interpolation of an already-derived `safe_mid8`**, not a new derivation. Not a violation.
- `coordination/surface_resolver.py` and `status_transition.py` derive topology **from path shape** (`endswith("-coord")`), not by composing identity. Both carry explicit "NOT a local `[:8]` slice" comments (`surface_resolver.py:370`, `status_transition.py:270`). Not violations.

`coordination/` is honestly out of scope and honestly clean for the part the claim covers. **Claim survives.**

---

## Claim 2 — "`locate_project_root` (#1971-tail) is already consolidated — verify-and-close."

### VERDICT: **UPHELD** — the delegation chain is real and intact. One **signature divergence** exists but is benign and must be documented, not "fixed."

The three definitions form a single-authority chain, exactly as research claims:

- `core/paths.py:48` — **authoritative** (Tier 1 `SPECIFY_REPO_ROOT` env / Tier 2 worktree-pointer / Tier 3 `.kittify` walk). Signature: `locate_project_root(start: Path | None = None)`.
- `core/project_resolver.py:8` — **thin deferred-import delegate** to `paths`. Body is literally `from specify_cli.core.paths import locate_project_root as _authoritative; return _authoritative(start)` (`core/project_resolver.py:23-25`). Same signature.
- `__init__.py:52` — deferred-import delegate to `project_resolver` (`__init__.py:53-55`). **Signature differs: no `start` parameter** — it is a no-arg convenience wrapper, `return _locate_project_root()`.

**The one divergence — and why it is NOT drift:**
- `__init__.py:52` takes no `start` arg; the other two take `start: Path | None = None`. This is **not** behavioral drift (no-arg → `start=None` → both default to `Path.cwd()` inside `paths.py:97`). It is a deliberately reduced surface used (a) internally at `__init__.py:125`, and (b) as a **monkeypatch seam in tests** (e.g. `tests/runtime/test_bootstrap_unit.py` patches `specify_cli.locate_project_root`). Consumers in `src/` overwhelmingly call the `start`-taking form via `core.paths`/`core.project_resolver` (e.g. `tracker/origin.py:439`, `sync/routing.py:43/53`, `cli/helpers.py:298`). I found **no** `src/` consumer that imports the `__init__` no-arg variant for resolution — it is an entrypoint/test seam only.

So "verify-and-close" is **honest**: there is no real consolidation work; the correct deliverable is FR-006's regression test confirming all three converge and the deferred-import shims stay (reverting either shim to a module-level import is the documented #1971 regression — `core/project_resolver.py:18-21`). **Claim survives.** The WP must, however, add a test asserting the `__init__` no-arg form and the two `start`-taking forms resolve identically from cwd, so the divergence is pinned and cannot silently grow.

---

## Claim 3 — "0 genuine fragment-adopt sites — nobody re-derives while holding an `ExecutionContext`."

### VERDICT: **UPHELD** — I could not find a single counterexample.

I inventoried every one of the 10 route-sites and grepped each for `resolve_action_context` / `ActionContext` / `ExecutionContext` / `IdentityFragment` / `.mid8` in its module. None of the 10 derivation sites holds an `ExecutionContext`/`ActionContext` at the point it slices `mission_id[:8]`:

- `runtime/.../retrospective_terminus.py:69` (`_mid8`) — pure helper over a `str`; no context.
- `status/aggregate.py:250` — operates on a `meta.json`-loaded `mission_id` (`_read_meta`), no context object; the carried-fragment path is a *separate* method (`aggregate.py:677-699`) that already reads `self.mid8`, not re-deriving.
- `git/sparse_checkout.py:286` — derives from a `raw` dict read off disk; no context.
- `dashboard/scanner.py:438` — derives from `_read_mission_identity(feature_dir)`; no context.
- `cli/commands/doctor.py:3070` & `:3162` — both derive from a `mission_id` read off `meta.json`; no context.
- `doctrine_synthesizer/apply.py:745` & `:831` — derive from a `mission_id` parameter; no context.
- `cli/commands/implement.py:386` — derives from a `mission_meta` **dict**, and the canonical `resolve_action_context` call is a *different, later* code path (`implement.py:531-550`). The dict-fallback at :386 is not context-held.
- `context/mission_resolver.py:163` — builds a `ResolvedMission` from `meta.json`; no context.

`IdentityFragment` is consumed read-only where a context exists (e.g. `status/aggregate.py` uses `self.mid8` at `:699`), and the only authoritative `mission_id[:8]` derivations are the seam internals (`branch_naming.py:139/192/408`, `mission_runtime/context.py`). FR-002 genuinely collapses to a verification. **Claim survives.**

---

## Claim 4 — Verification-by-deletion feasibility (the deletion landmines)

### VERDICT: **NOT a refutation, but a hard correction** — naive "delete the slice, call `mid8()`" **breaks byte-parity (NFR-001) at 4–5 of the 10 sites.** The route is correct; the *naive* route is wrong. These need a None/empty/short guard wrapper, not a bare substitution.

The seam has **two** different None/empty contracts, and the 10 sites are split across both — they are NOT interchangeable:

| Seam fn | Short/None `mission_id` behavior |
|---------|----------------------------------|
| `mid8(mission_id)` (`branch_naming.py:122`) | **RAISES `ValueError`** if `len < 8`; type is `str` (no `None` accepted). |
| `resolve_mid8(slug, mission_id=…)` (`branch_naming.py:169`) | Returns `""` when `mission_id` is `None`/`<8`; **also declines an embedded slug tail** when `mission_id` is absent. |

### Landmines (sites where naive verification-by-deletion changes behavior):

1. **`status/aggregate.py:250`** — current: `mission_id[:8] if mission_id else ""`. Returns `""` for `None`/empty.
   - Naive `mid8(mission_id)` → **`ValueError`** on `None`/short → **behavior change / crash**. NFR-001 violation.
   - `resolve_mid8(mission_slug, mission_id=mission_id)` returns `""` for `None` — but **DIVERGES for a non-None mission_id whose slug tail is absent/mismatched** is fine (declared id governs), HOWEVER `resolve_mid8` returns `""` when `mission_id is None` *even if the slug embeds a real tail* (decline). Current code also returns `""` there, so for `None` they match. **Use `resolve_mid8`, not `mid8`.** Requires the slug, which is available. Confirm byte-parity test covers the empty-`mission_id` legacy-mission case.

2. **`dashboard/scanner.py:438`** — current: `None if is_pseudo else (mission_id[:8] if mission_id else None)`. Returns **`None`** (not `""`) for falsy `mission_id`, and unconditionally `None` for pseudo (legacy/orphan) keys.
   - `mid8()` raises on `None` → crash. `resolve_mid8()` returns **`""`, not `None`** → type/value drift (`mid8: str | None` field would get `""` where consumers expect `None`).
   - **This site needs a None-preserving wrapper**, e.g. `resolve_mid8(...) or None` *and* keep the `is_pseudo` short-circuit. Naive routing breaks the `mid8 is None` contract the dashboard registry relies on (`scanner.py:444`). NFR-001 violation if not wrapped.

3. **`cli/commands/doctor.py:3070`** — current code **already calls `mid8()` inside `try/except ValueError`** and **falls back to `mission_id[:8]`** on failure (`doctor.py:3066-3070`). The inline slice is the *tolerance path* for a malformed/short `mission_id`.
   - FR-009 says "delete the shadow implementation." Deleting the `except ValueError: short = mission_id[:8]` fallback **removes a deliberate tolerance** and turns a today-survivable short id into an uncaught `ValueError` in a `doctor` command. That is a behavior change. Either keep the try/except (the fallback is the same byte value, so it is not a *shadow grammar* — it is a defensive duplicate of the seam's own first-8), or replace with `resolve_mid8` which returns `""` instead of raising. **Decide explicitly; do not blindly delete the except.**

4. **`cli/commands/doctor.py:3162`** — identical pattern to #3 (`try: mid8() except ValueError: mission_id[:8]`, `doctor.py:3158-3162`). Same landmine, same decision.

5. **`cli/commands/implement.py:386`** — current: `mission_meta.get("mid8") or (mission_id[:8] if isinstance(mission_id, str) and len(mission_id) >= 8 else None)`. Prefers the **stored `meta.mid8`**, falls back to a length-guarded slice, else `None`.
   - The correct seam here is `resolve_mid8(mission_slug, mission_id=mission_id)` (declared-identity authority), but note the current code prefers `meta["mid8"]` first. `resolve_mid8` derives from `mission_id` and would **ignore a stored `meta.mid8` that diverges from `mission_id[:8]`** — which is arguably *more* correct (declared id governs) but is a **behavior change** if any on-disk `meta.mid8` ever diverged. Returns `None` today on the empty path; `resolve_mid8` returns `""`. Needs a `or None` wrapper to preserve the `None` contract.

### Sites that ARE safe for direct `mid8()` substitution (mission_id guaranteed `>= 8`):

- `git/sparse_checkout.py:286` — guarded by `len(mission_id) >= 8` at `sparse_checkout.py:283` before the slice. `mid8(mission_id)` is byte-identical and cannot raise. **Safe.**
- `doctrine_synthesizer/apply.py:745` & `:831` — `mission_id` is a required non-empty param on the retrospective path; emit a characterization test, then `mid8()`. **Safe** (confirm the upstream never passes `< 8`).
- `context/mission_resolver.py:163` — guarded by `if not mission_id: continue` at `mission_resolver.py:154` before the slice. **Safe** for `mid8()`.
- `runtime/.../retrospective_terminus.py:69` — `_mid8(mission_id: str)`; callers pass a full id. Replace with seam `mid8`; add a characterization test pinning the caller's id length. **Safe**, but delete the local `_mid8` helper (FR-009) only after confirming no other caller depends on its non-raising behavior.

### Net deletion-feasibility finding
**`mid8()` is the wrong target for 4–5 of the 10 sites** because it raises on short/None where the current inline returns `""`/`None`. Those sites must route to **`resolve_mid8`** (returns `""`) — and `dashboard/scanner.py` + `implement.py` additionally need a `... or None` wrapper to preserve a `None` (not `""`) contract. The two `doctor.py` sites carry a deliberate `except ValueError` tolerance whose deletion is a behavior change and must be a conscious decision, not a mechanical FR-009 sweep. The research's per-site "guard empty" note for `aggregate.py:250` is correct but **understated**: it is not one site, it is **five** sites with None/empty/short sensitivity, two of which want `None` not `""`.

---

## Summary verdict

| Claim | Verdict |
|-------|---------|
| 1 — `coordination/workspace.py` already routed | **UPHELD** (clean; rest of `coordination/` honestly deferred) |
| 2 — `locate_project_root` consolidated | **UPHELD** (chain intact; one benign signature divergence to pin with a test) |
| 3 — 0 genuine fragment-adopt sites | **UPHELD** (no site re-derives while holding a context) |
| 4 — verification-by-deletion feasible | **CORRECTED** — feasible, but 4–5 sites break byte-parity under naive `mid8()` routing |

**Overall scope honesty:** the three "already done" claims are **HONEST** — none was lazy scope-reduction; all three survive adversarial verification. The mission is correctly bounded.

**BUT the deletion approach UNDERSTATES per-site work:** the plan/research treat None/empty handling as a single footnote on `aggregate.py:250`, when in fact **five** sites are None/empty/short-sensitive and split across two seam contracts (`mid8` raises vs `resolve_mid8` returns `""`), with two sites (`dashboard/scanner.py`, `implement.py`) needing `None`-preserving wrappers and two (`doctor.py:3070/3162`) carrying a deliberate `except ValueError` tolerance. IC-02 must do per-site contract analysis, not a mechanical substitution.

**Recommendation:** add to IC-02 an explicit per-site None/empty contract table (which seam fn, whether a `or None` wrapper is needed, whether an `except` tolerance is being removed) and a characterization test per site pinning the current empty/None output **before** substitution. Otherwise FR-009's "delete the shadow implementation" will silently break NFR-001 at the dashboard and the doctor commands.
