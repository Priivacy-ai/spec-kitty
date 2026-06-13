# Post-merge architecture audit — name-vs-authority-remediation-01KTYGTE (#132)

**Auditor:** architect-alphonso (profile loaded) · **Date:** 2026-06-12
**Branch:** feat/name-vs-authority-remediation-01KTYGTE · **Head:** 4c028ebf8
**Basis:** my normative seam design (`research/research-authority-seams.md`) + `contracts/authority-seams.md` + spec/plan.
**Scope:** design-level fidelity audit; read-only; ran `pytest tests/architectural/ -q` once.

---

## Q1 — Seam fidelity (landed API vs §seam-API) — **ALIGNED**

The landed `coordination/surface_resolver.py` is a faithful, in-many-respects-improved realization of §1.2:

- **Semantics:** `WorktreeTopology{PRIMARY,COORD_WORKTREE,LANE_WORKTREE,UNREGISTERED}` matches the four design states (naming refined: `COORD_WORKTREE`/`LANE_WORKTREE` vs my `COORDINATION`/`LANE` — pure cosmetics, no contract change). `is_registered_coord_worktree` is the convenience boolean over `classify_worktree_topology`, exactly as designed (`is WorktreeTopology.COORD_WORKTREE`).
- **Injectability:** the `registry: frozenset[Path] | None` param landed on BOTH functions, and `read_worktree_registry()` is the single porcelain-parse authority callers cache and inject — the "never shell out per path" requirement from §1.2 is honored and documented.
- **Fail-closed ordering:** correct. `_enclosing_worktree_root` → PRIMARY short-circuit (no git) → registry read (or injected) → husk(UNREGISTERED) → coord/lane. When the registry is unreadable and not injected, it raises `WorktreeRegistryUnavailable` (stable `error_code`) rather than guessing — the NFR-003 posture, with a typed error I did not even specify (improvement).
- **Bonus surface — well-judged:** `is_under_worktrees_segment()` was added as the *blessed* home for the pure shape proposal (`".worktrees" in parts`), explicitly separated from routing. This is a sound refinement: it lets the status_service contract-*label* consistency check keep a shape read without re-growing a routing predicate, and the ratchet's AST scan treats the function body as the one blessed site. No contract drift — it sharpens the proposes/disposes split.

**One drift worth recording (non-blocking):** the §5 R2 short-circuit at `resolve_status_surface_with_anchor` L461-467 still uses a raw `any(part == _WORKTREES_SEGMENT ...)` inside the blessed module itself, rather than calling `classify_worktree_topology`. It is *inside* the authority so it is contract-legal and ratchet-allowlisted, and re-entering the classifier there would risk the #1772 re-resolution it guards against — so the choice is defensible. But the authority module now contains both the canonical classifier and a hand-rolled membership test for its own short-circuit; a future reader could mistake the latter for the pattern to copy. Cheap follow-up: a private `_is_under_worktrees(path)` helper used by both. Consumers build on the *public* API, which is clean — no consumer-facing contract risk.

---

## Q2 — NFR-005 boundary check — **ALIGNED, with one boundary observation**

- **surface_resolver = Execution/Runtime:** topology authority + the R3 `_coord_branch_exists` rev-parse + `CoordinationBranchDeleted` all live here. Correct C4 home.
- **branch_naming = Mission Management:** `mission_branch_name_required` + `BranchIdentityUnresolved` are pure naming grammar — correct home.
- **`resolve_transaction_mid8` in branch_naming — the load-bearing question.** This *is* a status-transaction concern (it names the on-disk transaction dir consumed by `status_transition.py` and `implement.py`). My design (§3) said those two sites should "route through FR-006's authority **or** fail closed", and §2.2 located the new fail-closed helper in `branch_naming`. The implementer generalized that into a dedicated `resolve_transaction_mid8` and placed it in branch_naming. **Verdict: right home, not a leak.** What the function actually computes is the mid8 *disambiguator* — pure identity-from-meta grammar (`meta.mid8 → mission_id[:8] → mid8_from_slug → raise/empty`). It does no transaction I/O, holds no lock, touches no filesystem; the transaction-dir *composition* (`_transaction_dir_name`) and the dir existence checks stay in `status_transition.py`. So the *naming* lives in Mission Management and the *transaction mechanics* stay in Runtime — the boundary is preserved, arguably sharpened. The only nit is the **name**: `resolve_transaction_mid8` imports a downstream-consumer concept ("transaction") into the grammar module's vocabulary. A name like `resolve_required_mid8` / `resolve_disambiguator_mid8` would describe what the function *is* (identity resolution) rather than where its caller *uses it*. Cosmetic; no boundary move; does not warrant a change now.
- No module was moved or merged; the A+B god-module merge I rejected did not happen.

---

## Q3 — Ratchet coverage holes & residual migration path — **ALIGNED (residuals correctly fenced); ONE follow-up seam recommended**

**The three C-002 residuals — each verified live and each mapped to its upstream surface:**

| Residual (allowlisted) | Live site | Upstream owner | Migration target when that work lands |
|---|---|---|---|
| coord-predicate | `status_transition.py:112/122/124` (`_WORKTREES_DIR_NAME in parts`, `endswith("-coord")`) | coord-merge-stabilization (status-write routing range) | swap `_is_coordination_feature_dir`/`_is_coord_worktree_feature_dir` to `is_registered_coord_worktree(...)` |
| legacy compose | `merge.py:1114` (`f"kitty/mission-{mission_slug}"`) | same (merge adjacent range) | `mission_branch_name_required(slug, mission_id)` |
| legacy compose | `preflight.py:86` (`mission_branch or f"kitty/mission-{slug}"`) | same | `mission_branch or mission_branch_name_required(slug, mission_id)` |

**Migration path is clear AND mechanically forced.** The ratchet's bidirectional check is the key safety: both assertions assert `stale = blessed/allowlist - actual` is empty with the message "the seam migration is one site closer to complete." So when the upstream coord-merge-stabilization mission migrates any of these sites, the predicate/compose *disappears* from `actual`, the allowlist entry goes stale, and **the ratchet fails until the now-dead allowlist line is removed.** Allowlist staleness is therefore enforced, not hoped-for — exactly the property I wanted. (Caveat: the staleness check fires per *file*, so as long as a residual predicate of the *same idiom class* remains anywhere in `status_transition.py`, that one allowlist entry stays live; the file-granular allowlist can't force removal of an *individual* line. Acceptable — the file is wholly reserved by C-002.)

**Convention-as-authority classes the ratchet does NOT cover (follow-up candidates):**
1. **Worktree DIR-name composition** — `.worktrees/<slug>-<mid8>...` and `-coord`/`-lane-<id>` dir names are composed via `CoordinationWorkspace.worktree_path` / `_compose_mission_dir`, but the ratchet only guards *branch* f-strings (`kitty/mission-`). A hand-rolled `.worktrees/{slug}-{mid8}` f-string elsewhere would pass all three assertions. This is the symmetric twin of seam 2 (branch grammar) on the filesystem side and is the **highest-leverage uncovered class** — recommend a 4th assertion or a sibling ratchet.
2. **Status-file path shapes** — `kitty-specs/<dir>/status.events.jsonl` is composed in a few places via `_STATUS_EVENTS_FILENAME` join; not currently a guarded compose. Lower risk (the dir comes from the resolved authority), but worth a note.
3. **mid8-caller-must-read-meta** — intentionally omitted per §4 (would over-fire on branch_naming internals); the implication holds via assertions 2+3. No action.

Recommend filing the worktree-dir-name grammar gap as the explicit follow-up (it is the cleanest next ratchet).

---

## Q4 — Decision-table completeness (R1/R2/R2′/R3/R4) — **ALIGNED for the status-surface authority; two states out of this seam's scope**

All five rows landed in `resolve_status_surface_with_anchor`: R1 (coord-inside short-circuit), R2 (compose-once, not-materialized), R2′ (materialized root, missing mission dir → `StatusReadPathNotFound`), R3 (branch deleted → `CoordinationBranchDeleted`, the net-new row, gated on `_coord_branch_exists`), R4 (undeclared → primary). The R3 disambiguation is exactly the one-rev-parse design and correctly fails closed treating a non-repo context as "present" (won't fabricate a deleted-branch error from a tmp dir).

**States the table does not model — and why that is correct here:**
- **"Registered worktree present but its branch checked out elsewhere"** — git forbids the same branch in two worktrees, so this maps to either R1 (worktree present) or R3 (branch gone); the registry membership test (not branch identity) is what the resolver keys on, so the state is absorbed. Not a hole.
- **"Detached HEAD in the coord worktree"** — the resolver routes on *worktree-dir registration*, not on the worktree's HEAD ref, so a detached coord worktree still classifies COORD_WORKTREE and resolves its on-disk mission dir. The `coordination_branch` ref check (R3) is about the *declared* branch existing, independent of what HEAD points at. So a detached coord HEAD is correctly R1/R2′ by dir presence. **Genuine but out-of-seam:** if the coord worktree's HEAD has drifted off `coordination_branch` (detached or rebased away), the surface still resolves but a *subsequent write* could land on the wrong ref — that is a status-*write*/commit-target concern (CommitTarget/guard, ADR 2026-06-03-2), not a surface-*resolution* concern. The decision table governs resolution; it should not grow a write-time HEAD-drift row. Note it as a write-path follow-up, not a table gap.

Table is complete for what this seam owns.

---

## Q5 — Epic positioning / next highest-leverage slice (#1868/#1666)

**Next slice: "Worktree-directory grammar seam + C-002 residual sweep."** Two cohesive halves:
1. Extend `lanes/branch_naming` (or a sibling) with the canonical `.worktrees/<slug>-<mid8>[-coord|-lane-<id>]` *directory* composer/decomposer + a 4th ratchet assertion — closing the filesystem twin of seam 2 (Q3 gap #1).
2. Land the upstream coord-merge-stabilization migration of the three C-002 residuals (`status_transition.py` predicates, `merge.py:1114`, `preflight.py:86`) so the ratchet allowlist drains to empty — proving the seam complete end-to-end.
Both are pure strangler continuations on the same authority modules; no new architecture. Highest leverage because the dir-name class is currently *unratcheted* and is where the next split-brain would silently grow.

---

## OVERALL VERDICT — **ALIGNED (with one landed test-marker regression to fix before release)**

Both seams landed inside their C4-assigned modules with the designed semantics, injectability, and fail-closed posture; the decision table is complete for the resolution authority; the ratchet enforces all three decision points and *forces* allowlist drain. The implementer's additions (`is_under_worktrees_segment`, `WorktreeRegistryUnavailable`, generalized `resolve_transaction_mid8`, typed `CoordinationBranchDeleted`) sharpen rather than blur the design.

**Blocking-for-release nit (not a seam-design defect):** `pytest tests/architectural/ -q` is **2 failed, 351 passed**. Both failures are caused by THIS mission's two new test files — `tests/specify_cli/coordination/test_worktree_topology.py` and `test_worktree_topology_decision_table.py` — which exercise the real `git worktree list` registry via subprocess but carry the `fast` marker and lack the required `git_repo` marker (`test_pytest_marker_correctness.py::test_subprocess_git_users_must_carry_git_repo_marker` and `::test_fast_marker_must_not_apply_to_subprocess_users`). SC-4 ("full architectural suite green") is therefore not met on this head. Fix is mechanical (swap `fast` → `git_repo` on the subprocess-using tests); the topology ratchet itself (`test_topology_resolution_boundary.py`) and all seam behavior pass.

**Follow-ups to file:** (1) worktree-dir-name grammar seam + 4th ratchet assertion (Q3/Q5); (2) optional cosmetic — rename `resolve_transaction_mid8` → identity-vocabulary name; (3) optional — private `_is_under_worktrees` helper to dedupe the in-module R2 membership test.
