# Tasks: Governance at the deciding gate (#3685 + #3682)

Four work packages, folding the post-plan brownfield squad. Dependency shape:
`WP01`, `WP02` independent (parallel). `WP03` depends on `WP01` (reuses its rank + gate seam) and **co-lands with `WP04`** (C-004). All red-first (ATDD).

Files are disjoint across WPs (brownfield-verified) — no merge conflicts.

---

## WP01 — Enforcement lattice + reconciles-tension gate + reconcile promotion (IC-02, no implement-guard)
**Profile:** architect-alphonso · **Files:** `src/charter/offering/directives/models.py`, `src/charter/consistency_check.py`, `packs/built-in/directives/reconcile-change-scope-tensions.directive.yaml`, new gate tests.
**Depends:** none. **Independent.**

Tasks (red-first):
1. **T1 (red):** unit test asserting `Enforcement` compares by explicit **rank**, not lexical (rename-proof: a test that would break if a level were renamed out of alphabetical order). Then add a rank map + overridden `__lt__`/comparators on `Enforcement` (`models.py:22`) — single authority. Keep `StrEnum` value/JSON/`==` behavior intact (brownfield: only non-enum `sorted()` exists, safe).
2. **T2 (red):** gate test — seed a `reconciles_tension` directive→directive edge with `rank(source) < rank(target)` → gate fails naming the edge; a tactic-typed target edge is **skipped** (documented rule). Add the gate to `consistency_check.py`, **reusing `_tension_reconciled_urns`** (no second walk), joining endpoints to enforcement via `DoctrineService` (directive endpoints only).
3. **T3:** raise `reconcile-change-scope-tensions` to `lenient-adherence` (= max of directive operands 024/025) and **add the `explicit_allowances`** its level requires (else `validate_lenient_adherence` fails load — brownfield-confirmed). Bound: a reconciler is never promoted to `required` (assert in the gate).
4. **T4:** before/after corpus check — histogram `25/6/3 → 25/7/2`, no directive newly `required`; the promoted reconciler loads. (No existing histogram/advisory baseline pins this — brownfield-verified.)
**Done:** gate red-first proven; corpus green; `ruff`/`mypy` clean; terminology guard clean.

---

## WP02 — Deliver the arbiter as an arbiter (IC-03)
**Profile:** architect-alphonso · **Files:** `src/charter/offering/drg/query.py`, `src/charter/action_doctrine_bundle.py`, `contracts/tension-annotation.md`, tests.
**Depends:** none. **Independent.**

Tasks (red-first):
1. **T1 (red):** test — assemble a bundle whose scope pulls in `024`+`025`; assert new field `tension_arbiters` maps `reconcile-change-scope-tensions → (024,025)`; a declared reconciler-less pair appears in `unarbitrated_tensions`.
2. **T2:** add **trailing, defaulted, HASHABLE** fields to `ResolvedContext` (`query.py:49`) and `_ActionDoctrineBundle` (`action_doctrine_bundle.py:46`): `tension_arbiters: tuple[tuple[str, tuple[str,...]],...]` and `unarbitrated_tensions: tuple[tuple[str,str],...]` (NOT dict/list — preserves the frozen `__hash__`; brownfield constraint). Follow the existing defaulted-trailing-field precedent (`bridge_urns` etc.). No version bump.
3. **T3:** `resolve_context` populates them by walking `reconciles_tension`/`in_tension_with`, **reusing the progressive-disclosure traversal** (no second graph walk); bounded work only when tension edges are in scope (common-case latency unchanged).
4. **T4:** contract sketch `contracts/tension-annotation.md` documenting the field shapes.
**Done:** field additive-safe (existing constructors byte-valid); tests green; `ruff`/`mypy` clean.

---

## WP03 — Move DIRECTIVE_003 off `implement` → `review` + class-level implement guard (IC-01 + IC-02 guard)
**Profile:** architect-alphonso · **Files:** `packs/built-in/missions/software-dev/actions/implement/index.yaml`, `.../actions/review/index.yaml`, `src/specify_cli/calibration/walker.py`, `tests/calibration/test_walker.py`, `src/charter/consistency_check.py` (class-level guard), regen'd `packs/built-in/action.graph.yaml`, gate tests.
**Depends:** `WP01` (reuses its rank + `consistency_check` gate seam). **Co-lands with `WP04`** (C-004).

Tasks (red-first):
1. **T1 (red — the load-bearing test):** the COMBINED assertion — `charter context --action implement --json` lacks `DIRECTIVE_003` **AND** `--action review --json` still delivers it. (Brownfield: the standalone "review has 003" is vacuous — the calibrator already delivers it; the real proof is del-only-vs-del+add.)
2. **T2:** delete the `003-decision-documentation-requirement` line from `implement/index.yaml`; add it to `review/index.yaml`. (Brownfield: the review add is load-bearing because the calibrator copies *from* implement — removing it from implement strips review's calibrated copy.)
3. **T3:** add `directive:DIRECTIVE_003` to review's `_REQUIRED_SCOPE` in `calibration/walker.py` (~:184) + the byte-stability expected set in `test_walker.py:132-148` — turns 003-on-review from tolerated-extra into a required positive guard.
4. **T4:** `spec-kitty doctrine regenerate-graph`; verify `--check` / orphan-lint / reachability-ledger green; 003 still reachable from retained `plan/specify/tasks/retrospect`.
5. **T5 (red):** class-level gate in `consistency_check.py` — no `enforcement: required` decision-documentation directive is scoped on `implement`; seed a violation fixture → fails; shipped corpus (post-T2) passes. (Brownfield: this gate can only be green AFTER 003 leaves implement — hence it lives here, co-landed.)
**Done:** combined red-first proven; regen clean; class-level gate non-vacuous; `ruff`/`mypy`/terminology clean.

---

## WP04 — Deciding gates capture the decision evidence (IC-04)
**Profile:** reviewer-renata (author) — implementation by a sonnet implementer · **Files:** `src/specify_cli/cli/commands/agent/tasks_move_task.py`, `tasks_verdict_persistence.py`, `src/specify_cli/acceptance/{matrix.py,gates_core.py,__init__.py}`, tests incl. `tests/specify_cli/cli/commands/agent/test_tasks_move_task_seam.py`.
**Depends:** **Co-lands with `WP03`** (C-004). Parent epic #3044.

Task 0: re-derive current-main state vs #3235 (brownfield did this — use the DONE/PARTIAL/OPEN table). Reference #3243 / #3451 in notes (same path) — **do not fix them**.

Tasks (red-first):
1. **T1 (red):** approve a WP first-pass → assert `approved` event carries non-null `policy_metadata` (tool/profile/model/shell_pid) + `review_ref`. Add an `APPROVED` arm to `_mt_hop_policy_metadata` (`tasks_move_task.py:~2189`) and `_binding_role_for_lane`; **re-resolve the reviewer binding with `action="review"`** (brownfield: APPROVED currently resolves with `action="implement"` → wrong profile/model) or source from `effective_reviewer` (`:808-820`); set `review_ref` on the forward approve.
2. **T2 (red):** first-pass approve writes `tasks/<WP>/review-cycle-1.md` (verdict `approved`, `reproduction_command`). Flip the **slot-absent guard at `:850`** in `_persist_approved_review_cycle` to WRITE via `create_rejected_review_cycle(..., verdict="approved")`; **preserve** the `:852` already-approved idempotency no-op and the `_persist_review_cycle_with_queue` wrapper + `next_cycle_number`. **Invert the pinning test** `test_tasks_move_task_seam.py:521 test_persist_approved_review_cycle_noop_when_no_prior_cycle`; **preserve** `:544` (idempotency) and `:563` (flip). Do **not** rename the flagship `test_review_cycle_rejection_only.py` test (pinned by `test_verdict_name_truthfulness`).
3. **T3 (red):** after `spec-kitty accept`, matrix criterion rows are populated from recorded evidence (via the existing `agent mission acceptance-verdict` seam / status+review-cycle artifacts) instead of perpetual `pending`; forward-only (historical matrices untouched — `_is_empty_scaffold` exemption preserved). Block-on-pending already works; this adds population.
**Done:** all three red-first; #3235-landed behavior preserved; `ruff`/`mypy` clean; the flagship truthfulness gate green.

---

## Consolidation / landing (orchestrator)
After WP review-approval: cherry-pick WP commits onto the mission branch (WP01+WP02, then WP03+WP04 co-landed), clean history, rebase onto `upstream/main`, add changelog + docs, run a pre-merge adversarial review squad, fold, open a draft PR (operator merges).
