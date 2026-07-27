# Adversarial scope-review synthesis — Naming/Identity Routing Rider

**Date:** 2026-06-16. **Squad:** paula-patterns (missed paths) · python-pedro (refute already-done) ·
planner-priti (ticket focus) · architect-alphonso (scope boundary). All opus, profile-loaded, adversarial.
Inputs: `paula-missed-paths.md`, `pedro-refute-already-done.md`, `priti-ticket-focus.md`,
`alphonso-scope-boundary.md`.

## Headline

The **routing core is sound and honest** — pedro upheld all three "already done" claims; alphonso
confirmed the out-of-scope fence is real (no route-site can surface the deferred builder split-brain).
But the squad found **one wrong architectural bet (#1993/IC-03), a mis-scoped ticket set, 5 missed
route-sites, an undersized ratchet, and 5 byte-parity landmines.** These are plan-revision items, caught
exactly where they should be — before tasks.

## What converged (high confidence — multiple independent agents)

### 1. IC-03 / #1993 is WRONG — re-scope it (paula + priti + alphonso all hit this)
- The planned "extract `resolve_lanes_dir` + adopt ~10 inline `feature_dir / "lanes.json"` sites" rests on
  a **false inventory**: the lanes-path join is **already encapsulated** in `persistence.py`
  (`read_lanes_json`/`require_lanes_json`/`write_lanes_json`). Only ~2 literal composes exist, both inside
  the seam itself; the other named files have **zero** inline joins.
- A standalone `resolve_lanes_dir` would create a **second path-authority for the same concept — a direct
  C-001 violation** (the very prohibition this mission exists to honor). [alphonso]
- #1993's **real** ask is the coord-aware `_lanes_feature_dir` topology fallback in `implement()` (the
  12-mock thing) — which lives in the **deferred coord/topology zone** (#1716/#1832, 3.2.2). [priti]
- **Resolution:** DROP the lanes-dir extraction. **Defer #1993's real target to 3.2.2**; the pure
  lanes.json path is already centralized (note it, no build). This also removes the only real two-WP file
  collision (`lanes/recovery.py` was double-claimed by IC-03/IC-04). [alphonso]

### 2. Ticket set is mis-scoped — correct it (priti, tracker-verified)
| Ticket | Plan claimed | Truth | Action |
|--------|-------------|-------|--------|
| **#1899-tail** | addressed | **PHANTOM** — #1899 CLOSED (PR #2001); residual *is* #2000 (double-count) | **DROP** |
| **#1900** | addressed | severance fiction — different ratchet, 2/3 sites migrated, remaining site is coord write-side (deferred by C-005) | **DROP** (→ 3.2.2) |
| **#1993** | extract+adopt lanes-dir | real target is coord-aware `_lanes_feature_dir` in `implement()` (deferred zone) | **DEFER to 3.2.2** |
| **#2000** | ~2 composes in recovery.py/detection.py | right intent, **wrong files** — real sites `core/mission_creation.py:321`, `core/worktree.py:367/370`; defect is the *compose* (needs `mission_dir_name`/`worktree_dir_name`), already in the ratchet allow-list | **FIX file list + frame as compose-routing** |
| **#1888** | "verify-and-close, no build" | **real P1 bug** — no existence check in `ownership/validation.py`; validation passes phantom paths silently | **RE-DISPOSITION as real fix** (code + test) |
| **#1971-tail** | verify-and-close | UPHELD — but the regression test must disprove the `SPECIFY_REPO_ROOT`/worktree split-brain the ticket asserts + pin the `__init__.py` no-arg signature divergence | **verify-and-close (with the right test)** |

**Net addressable set this rider:** #2000 (corrected) · #1971-tail (verify-and-close) · #1888 (real fix) ·
the broader mid8-routing class (advances #1868/#1619). **Dropped/deferred:** #1899-tail, #1900, #1993.

### 3. 5 missed route-sites — the grep AND the ratchet share the blind spot (paula)
The `\b\w*_id\[0?:8\]` idiom misses var-name-independent shapes. Genuinely-missed in-scope mid8 sites:
- `mission_runtime/resolution.py:171` — `str(raw_mission_id)[:8]` (**core read-path producer**, `_mid8_from_primary_meta`)
- `cli/commands/agent/mission.py:772` — `raw_mid[:8]` (load-bearing; feeds `CoordinationWorkspace.resolve`)
- `cli/commands/mission_type.py:643` — `mission_id_meta[:8]`
- `cli/commands/agent/workflow.py:292` — `mid[:8]`
- `retrospective/generator.py:112` — `mid[:8]`
→ **IC-02 grows from 10 to ~15 sites.**

## What was corrected on execution (single-agent, high value)

### 4. Ratchet (IC-01) is undersized + a NEW detector, not a tweak (paula + alphonso)
- `test_no_worktree_name_guess.py` has **no short-id detector today** (it detects name *composes*). FR-004
  is a **genuinely new AST slice detector**, not a one-liner. The plan mislabels the ratchet "syntax-level"
  — it is AST-based. [alphonso corrects the plan's wording]
- AST can't structurally tell `mission_id` from `invocation_id`, so it's forced onto a **name allow-list**
  — which means the `str(x)[:8]`/`mid[:8]`/`raw_mid[:8]` shapes are hard to catch. **The real correctness
  guarantee is verification-by-deletion, not the ratchet** — SC-001's "cannot silently regrow" is
  overstated. The honesty note must also **name the deferred `feature_dir.parent.parent` repo-root class
  (~9 sites)** so SC-001 isn't over-read. (Leaving semantic/AST-semantic checks out of scope is defended.)

### 5. Verification-by-deletion has 5 byte-parity landmines (pedro)
The seam has **two contracts**: `mid8()` **raises** on short/None; `resolve_mid8()` returns `""`. Naive
"delete the slice, call `mid8()`" breaks NFR-001 at:
- `status/aggregate.py:250` (`""` today → must use `resolve_mid8`)
- `dashboard/scanner.py:438` (`None`, not `""`; needs `resolve_mid8(...) or None`)
- `doctor.py:3070` & `:3162` (already wrap `try/except ValueError: mission_id[:8]` — deleting that turns a
  deliberate short-id tolerance into a crash; conscious decision required)
- `implement.py:386` (prefers `meta["mid8"]`, returns `None`; `resolve_mid8` ignores `meta.mid8`)

Safe for direct `mid8()`: `git/sparse_checkout.py`, `doctrine_synthesizer/apply.py:745/831`,
`context/mission_resolver.py:163`, `retrospective_terminus.py:69`.
→ **IC-02 needs a per-site contract table + characterization test before substitution.**

## What was UPHELD (the scope is honest where it claims to be)
- `coordination/workspace.py` genuinely routes through the seam — no residual grammar (pedro swept the rest of `coordination/`).
- `locate_project_root` genuinely consolidated — real single-authority chain (pedro).
- 0 genuine fragment-adopt sites — FR-002 legitimately collapses to verification (pedro).
- Out-of-scope fence is REAL — all route-sites derive `mid8` from a raw `mission_id` string; none touch `ExecutionContext`/`branch_ref`, so the rider cannot surface the deferred builder split-brain (alphonso bet-4).

## Proposed revised IC map
- **IC-01 — ratchet (resized):** build the NEW AST short-id slice detector (best-effort, name-allow-list),
  cover `dashboard/scanner.py`, shrink the allow-list; honesty note names the deferred repo-root class +
  the indirection limit; verification-by-deletion is the real guarantee.
- **IC-02 — short-id routing (~15 sites):** route via `mid8()`/`resolve_mid8` with a **per-site contract
  table** (raise vs `""` vs `None`) + characterization tests; delete shadows (FR-009); the 4 None/empty
  sites use `resolve_mid8`(+`or None`); the 2 doctor try/except sites are a conscious decision.
- **IC-03 — #2000 compose-routing (re-targeted):** route `core/mission_creation.py:321` +
  `core/worktree.py:367/370` through `mission_dir_name`/`worktree_dir_name`; drop the lanes-dir extraction.
- **IC-04 — verify-and-close + the #1888 fix:** #1971-tail (convergence + split-brain-disproving test);
  **#1888 real existence-check fix + test** (not verify-close).
- **Deferred to 3.2.2:** #1993 (coord-aware `_lanes_feature_dir`), #1900 (coord write-side).

## One-line verdict
**Routing core SOUND & severable; ticket mapping & IC-03 NEED REVISION before `/spec-kitty.tasks`.** The
mission stays a low-risk rider — but a *correctly-targeted* one: +5 sites, a real (not tweak) ratchet
detector, a byte-parity contract table, #2000 re-pointed at its true compose sites, #1888 promoted to a
real fix, and #1993/#1900/#1899-tail dropped/deferred.
