# Smells Discovered (boy-scout backlog) — execution-state-canonical-surface-01KTG6P9

Pre-existing code smells noticed in passing while implementing this mission, but
**out of scope** for the WP that touched the file. Recorded here, not fixed inline,
to avoid scope creep. **After mission completion**, walk this list and boy-scout the
cheap, low-risk ones (ideally folded into an unrelated touch of the same file, or a
small dedicated cleanup WP/PR).

Format per entry: location · tool/rule · description · why deferred · rough effort.

## Closeout boy-scout pass status (2026-06-08)

| Smell | Status | Note |
|-------|--------|------|
| S-01 unused `repo_root` param | ✅ RESOLVED | dropped param + shallow cascade + 3 test sites; ruff+mypy clean |
| S-02 CI path filter (FR-024) | ✅ RESOLVED | drop deleted path, add `mission_runtime/**` |
| S-03 mission_runtime docstrings | ✅ RESOLVED | fixed in `4b52a86d7` (during mission) |
| S-04 bootstrap env failures | ✅ RESOLVED | editable-install artifact (`pip install -e .`); not a code defect |
| S-05 non-hermetic walk-up test | ✅ RESOLVED | sentinel-marker monkeypatch; hermetic vs live `/tmp/.kittify` |
| S-06 stale review-cycle verdict | ⏭️ DEFERRED | behavioral review-flow change, not a tidy → file upstream |
| S-07 SR-1 docstring + rot guard | ✅ RESOLVED | docstrings corrected; rot guard strengthened (now has teeth) |
| S-08 dead `history_parser` | ✅ RESOLVED | module + tests deleted |

**Also evaluated, intentionally NOT touched:** 5 advisory ruff errors (1×C901, 3×ARG002, 1×SIM103) in three `m_3_2_0rc35_*` charter-pack/skill migration files. They are **pre-existing on `upstream/main`**, in files this mission never touched, from unrelated missions; the `ARG002` flags are on interface-mandated `can_apply`/`apply` override params (ruff is wrong about correct code). CI ruff is advisory (`continue-on-error`). Folding unrelated migration edits into this 155-file strangler PR would muddy the diff and risk migration behavior — they belong in a focused migration-cleanup PR.

---

## S-01 — Unused `repo_root` parameter in `_latest_review_feedback_reference` — **RESOLVED (boy-scout)**

- **Location:** `src/specify_cli/cli/commands/agent/workflow.py:688` (function `_latest_review_feedback_reference`, param `repo_root: Path`).
- **Tool/rule:** `ruff` — `ARG001` Unused function argument: `repo_root`.
- **Description:** The function accepts `repo_root: Path` but never uses it; the body resolves everything from `feature_dir` + `wp_id`.
- **Status:** **RESOLVED at closeout boy-scout pass (2026-06-08).** Dropped the unused param. The cascade was shallow and clean: `_resolve_review_feedback_context` only forwarded `repo_root` (its own `feedback_root` derives from `feature_dir.parent.parent`), so its param was dropped too; the second call site's local `repo_root = feature_dir.parent.parent` was removed (used only for the forward); the `repo_root=main_repo_root` kwarg at the `_resolve_review_feedback_context` call site was dropped. Updated 3 test call sites (`test_workflow_review_cycle_pointer.py` ×2, `test_implement_review_retrospect_smoke.py` ×1). `workflow.py` ruff + mypy clean; affected tests green (4 passed).

---

## S-02 — CI `execution_context` path filter goes stale once the relocation merges — **RESOLVED (FR-024 complete)**

- **Location:** `.github/workflows/ci-quality.yml` — the `execution_context` path filter: `src/specify_cli/core/execution_context.py`, `src/specify_cli/status/**`, `src/runtime/next/**`, `src/specify_cli/cli/commands/agent/**`, `tests/architectural/test_execution_context_parity.py`.
- **Tool/rule:** none (CI config drift; surfaced by the WP01 post-rebase re-review).
- **Description:** The filter still watches `src/specify_cli/core/execution_context.py` (which WP03 **deletes**) and does **not** watch the new `src/mission_runtime/**` package. FR-024 intended the ratchet to gate PRs touching `mission_runtime/` once it existed; WP01 legitimately deferred that because the module didn't exist yet.
- **Status:** **RESOLVED at closeout (2026-06-08).** Now that the relocation is merged to feat (`core/execution_context.py` is gone, `src/mission_runtime/` exists), dropped the deleted path and added `src/mission_runtime/**` to the `execution_context` filter. `test_ci_quality_path_filters.py` green. Completes FR-024.
- **Rough effort:** Done.

---

## S-03 — mission_runtime docstrings said "shim" for a deleted module — **FIXED**

- **Location:** `src/mission_runtime/{resolution.py, __init__.py, context.py}`.
- **Tool/rule:** none (doc accuracy; surfaced by the WP02+WP03 post-rebase re-review).
- **Description:** Docstrings described `core/execution_context.py` as a "thin re-export shim", but WP03 deleted it outright (no importers remained). Stale wording.
- **Status:** **Remediated** in `4b52a86d7` (docstring-only; ruff/mypy clean). Reworded to state the module was removed and the historical names are re-exported from the package root. Listed here for the audit trail.
- **Note:** `.contextive/execution.yml:21` (a glossary string referencing `core/execution_context.py` as owner) is absent in the lanes but may exist on other branches — verify/update at merge if present.

---

## S-04 — pre-existing environmental test failures on the lane base — **RESOLVED (editable-install artifact)**

- **Location:** `tests/runtime/test_bootstrap_unit.py` (≈14 failures); also seen earlier: `test_agent_utils_status` (×2), `test_internal_runtime_parity` snapshot drift.
- **Tool/rule:** pytest (environmental, not lint).
- **Description:** `test_bootstrap_unit.py` fails because `SPEC_KITTY_TEMPLATE_ROOT` / `get_package_asset_root` expects a real checkout asset layout not present in the lane/test env. The WP04 + WP02/03 re-reviews both proved these are **pre-existing and unrelated** to this mission's changes (the relevant `src/` files are byte-identical to the WP base; reproduced on a pure-feat baseline).
- **Status:** **RESOLVED at closeout (2026-06-08).** Root cause was that the active dev interpreter (`pyenv 3.11.15`) had no editable install of `specify_cli`, so the subprocess-spawning tests (`sys.executable -m specify_cli`) and asset-root lookups failed with `No module named specify_cli`. Running `python -m pip install -e .` into the active env fixed it: `test_bootstrap_unit.py` → **42 passed**, `test_execution_context_parity.py` → **9 passed**. Not a code defect and not a branch RED in a correctly-provisioned env (CI installs the package). No source change required.
- **Rough effort:** Done — environment provisioning, not code.

---

## S-05 — `test_locate_project_root_no_marker` is non-hermetic (walks up into a stray `/tmp/.kittify`)

- **Location:** `tests/runtime/test_paths_unit.py::test_locate_project_root_no_marker`; root cause in `locate_project_root()` walk-up + an operator scratch dir `/tmp/.kittify` (contains `charter/`, `mission-brief.md`).
- **Tool/rule:** pytest (test hermeticity).
- **Description:** The test creates a markerless temp dir under `/tmp` and asserts `locate_project_root()` returns `None`, but the walk-up finds `/tmp/.kittify` and returns `/tmp`. Surfaced + proven by the WP06 reviewer (moving the stray dir makes it pass); `locate_project_root` was unchanged by any WP here.
- **Why deferred:** environmental + a pre-existing test-isolation weakness, unrelated to this mission's surface.
- **Status:** **RESOLVED at closeout boy-scout pass (2026-06-08).** Made the test hermetic without mutating the operator's live `/tmp/.kittify` scratch dir and without a production signature change: the test now monkeypatches `specify_cli.core.paths.KITTIFY_DIR` to a guaranteed-absent sentinel, so the "no marker found anywhere up the tree → None" path is exercised deterministically regardless of any real `.kittify` above `tmp_path`. Test passes despite the live `/tmp/.kittify` (root cause of the original flake). `locate_project_root` itself unchanged.
- **Rough effort:** Done.

---

## S-06 — review-cycle artifact verdict goes stale across re-review cycles

- **Location:** `spec-kitty agent action review` / `move-task --to approved` review-artifact check; `tasks/<WP>/review-cycle-N.md`.
- **Tool/rule:** review workflow (cross-cycle artifact naming/verdict).
- **Description:** On WP07's cycle-2 re-review (after a cycle-1 rejection + fix), the approval was blocked because a `review-cycle-2.md` artifact carried `verdict: rejected` — the cycle-1 rejection content had been written under the cycle-2 filename. The reviewer had to pass `--skip-review-artifact-check` with a rationale to approve a genuinely-resolved finding. The cycle index / artifact verdict didn't advance cleanly with the re-review.
- **Why deferred:** workflow tooling friction, not mission code; the reviewer handled it correctly (documented skip, not an arbiter override).
- **Status (2026-06-08 closeout boy-scout pass):** **DEFERRED — file upstream (not a boy-scout cleanup).** Unlike S-01/S-05/S-07, this is a *behavioral change* to the review move-task flow (cross-cycle artifact verdict tracking + superseding stale rejection artifacts on re-claim), not a docstring/dead-param/test-hermeticity tidy. It needs its own design (cycle-index advancement, artifact supersession semantics) and touches the sensitive review/approval gate — out of scope for a closeout boy-scout. Recommend filing alongside the codependent-lanes epic (see findings.md SYNTHESIS).
- **Rough effort:** Medium (tooling). The review-artifact check should key off the CURRENT cycle's verdict, and re-claiming review for a fixed WP should supersede/clear the prior cycle's rejection artifact rather than leaving a stale `rejected` that blocks the next approval. Worth filing upstream alongside the codependent-lanes epic.

---

## S-07 — status-boundary test: misleading SR-1 docstring + file-existence-only allow-list rot guard — **RESOLVED (boy-scout)**

- **Location:** `tests/architectural/test_status_module_boundary.py` (added by WP09).
- **Tool/rule:** doc accuracy + test-completeness (surfaced by the WP09 review, non-blocking).
- **Description:** Two minor issues: (a) the `SR-1` section header + class docstring say the rule was "widened to ALL of `src/specify_cli`", but SR-1's pytestarch rule still asserts only against the 6 WP03-fixed packages — the repo-wide gate is exclusively SR-2 (architecturally fine, but the doc misleads). (b) `test_ast_scan_allow_list_covers_known_residuals` only checks that allow-listed files EXIST on disk — it will NOT catch a stale `_WP10_DEFERRED_FILES` entry once WP10 migrates a file's imports but forgets to remove it from the allow-list.
- **Status:** **RESOLVED at closeout boy-scout pass (2026-06-08).** (a) Rewrote the module docstring, SR-1 section header, and `TestStatusModuleBoundary` class/method docstrings to state plainly: **SR-1 = regression-lock on the 6 WP03 clean packages; SR-2 = the repo-wide gate**. (b) Strengthened `test_ast_scan_allow_list_covers_known_residuals` — in addition to the file-exists check, it now re-scans each `_WP10_DEFERRED_FILES` entry with `scan_for_bypass_imports([p])` (no exemptions) and fails if any entry produces **zero** bypass violations (i.e. was migrated onto the facade but left in the allow-list). The shrinking ledger now self-polices. Guard confirmed to have teeth (passes only because the sole remaining entry, `workspace/context.py`, still carries its cycle-breaker deep import). 5 boundary tests green.
- **Rough effort:** Done.

---

## S-08 — `status.history_parser` is now a DEAD module (orphaned by WP08 inlining) — **RESOLVED (module deleted)**

- **Location:** `src/specify_cli/status/history_parser.py`; failing test `tests/architectural/test_no_dead_modules.py` (or equivalent).
- **Tool/rule:** architectural dead-module gate (RED).
- **Description:** `history_parser` was classified PRIVATE/migration-only in the occurrence map. WP08's T031 inlined its last external consumer (`extract_done_evidence` → inlined into `merge.py`), leaving the module with **zero consumers** → the dead-module ratchet now fails. This is **mission-introduced** (WP08), not truly pre-existing — surfaced by the WP10 implementer.
- **Status:** **RESOLVED at closeout (2026-06-08, commit 35db0271a).** Confirmed zero src callers (`grep -rn history_parser src/` → only the inline comment in `merge.py`); deleted `src/specify_cli/status/history_parser.py` and its unit test `tests/status/test_history_parser.py`. Removed the two stale `history_parser.extract_done_evidence` mock-patches in `test_merge_status_commit.py` and `test_merge.py` (the function is now inlined in `merge.py`, no patch target), and dropped the module from the lane-regression-guard excluded list. `test_no_dead_modules` + `test_no_dead_symbols` now GREEN. Randy-Reducer dead-weight elimination — cleanest option taken.
- **Rough effort:** Done.
