# Smells Discovered (boy-scout backlog) — execution-state-canonical-surface-01KTG6P9

Pre-existing code smells noticed in passing while implementing this mission, but
**out of scope** for the WP that touched the file. Recorded here, not fixed inline,
to avoid scope creep. **After mission completion**, walk this list and boy-scout the
cheap, low-risk ones (ideally folded into an unrelated touch of the same file, or a
small dedicated cleanup WP/PR).

Format per entry: location · tool/rule · description · why deferred · rough effort.

---

## S-01 — Unused `repo_root` parameter in `_latest_review_feedback_reference`

- **Location:** `src/specify_cli/cli/commands/agent/workflow.py:688` (function `_latest_review_feedback_reference`, param `repo_root: Path`).
- **Tool/rule:** `ruff` — `ARG001` Unused function argument: `repo_root`.
- **Description:** The function accepts `repo_root: Path` but never uses it; the body resolves everything from `feature_dir` + `wp_id`.
- **Why deferred:** Noticed while fixing the F-02 review base-ref bug in the same file (see [findings.md](findings.md) F-02). It is pre-existing and unrelated to the coordination fix. Removing the param changes the signature and every call site, so it is real scope creep on a function this mission didn't otherwise touch.
- **Rough effort:** Low. Either drop the param and update call sites, or (if a uniform helper signature is intentional) rename to `_repo_root` / add a one-line justified `# noqa: ARG001`. Prefer dropping it unless a sibling helper shares the signature for dispatch uniformity.

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
- **Status (2026-06-08 closeout):** Confirmed environmental, **NOT a merge blocker**. `/tmp/.kittify` is a live operator scratch dir created today (a `spec-kitty do` lightweight-dispatch artifact: `mission-brief.md`, `brief-source.yaml`, `charter/interview/`). The test only fails on this dev box; CI has no such stray dir. `locate_project_root` is untouched by this mission. **Not deleting** the operator's in-use scratch dir; the durable fix (make the test hermetic by capping the walk-up ceiling) belongs to a focused runtime-test cleanup, not this mission's relocation surface.
- **Rough effort:** Low. Either make the test hermetic (build the temp tree outside any `/tmp/.kittify` ancestor, e.g. monkeypatch the walk-up ceiling) or remove the stray `/tmp/.kittify` from the dev box.

---

## S-06 — review-cycle artifact verdict goes stale across re-review cycles

- **Location:** `spec-kitty agent action review` / `move-task --to approved` review-artifact check; `tasks/<WP>/review-cycle-N.md`.
- **Tool/rule:** review workflow (cross-cycle artifact naming/verdict).
- **Description:** On WP07's cycle-2 re-review (after a cycle-1 rejection + fix), the approval was blocked because a `review-cycle-2.md` artifact carried `verdict: rejected` — the cycle-1 rejection content had been written under the cycle-2 filename. The reviewer had to pass `--skip-review-artifact-check` with a rationale to approve a genuinely-resolved finding. The cycle index / artifact verdict didn't advance cleanly with the re-review.
- **Why deferred:** workflow tooling friction, not mission code; the reviewer handled it correctly (documented skip, not an arbiter override).
- **Rough effort:** Medium (tooling). The review-artifact check should key off the CURRENT cycle's verdict, and re-claiming review for a fixed WP should supersede/clear the prior cycle's rejection artifact rather than leaving a stale `rejected` that blocks the next approval. Worth filing upstream alongside the codependent-lanes epic.

---

## S-07 — status-boundary test: misleading SR-1 docstring + file-existence-only allow-list rot guard

- **Location:** `tests/architectural/test_status_module_boundary.py` (added by WP09).
- **Tool/rule:** doc accuracy + test-completeness (surfaced by the WP09 review, non-blocking).
- **Description:** Two minor issues: (a) the `SR-1` section header + class docstring say the rule was "widened to ALL of `src/specify_cli`", but SR-1's pytestarch rule still asserts only against the 6 WP03-fixed packages — the repo-wide gate is exclusively SR-2 (architecturally fine, but the doc misleads). (b) `test_ast_scan_allow_list_covers_known_residuals` only checks that allow-listed files EXIST on disk — it will NOT catch a stale `_WP10_DEFERRED_FILES` entry once WP10 migrates a file's imports but forgets to remove it from the allow-list.
- **Why deferred:** non-blocking doc/robustness polish; WP09 met its spec.
- **Rough effort:** Low. (a) Correct the SR-1 header/docstring to say SR-1 = regression-lock on the 6 clean packages, SR-2 = repo-wide gate. (b) Strengthen the rot guard to assert each allow-listed file STILL contains a deep status import (so a migrated-but-not-delisted file fails the guard) — ideally land this WITH WP10 so the shrinking ledger self-polices. **Action for WP10:** as it routes each ROUTE-deferred symbol, remove that file from `_WP10_DEFERRED_FILES`; the WP10 reviewer must confirm the allow-list shrank to only the permanent cycle-breaker + C-004 exemptions.

---

## S-08 — `status.history_parser` is now a DEAD module (orphaned by WP08 inlining) — **RESOLVED (module deleted)**

- **Location:** `src/specify_cli/status/history_parser.py`; failing test `tests/architectural/test_no_dead_modules.py` (or equivalent).
- **Tool/rule:** architectural dead-module gate (RED).
- **Description:** `history_parser` was classified PRIVATE/migration-only in the occurrence map. WP08's T031 inlined its last external consumer (`extract_done_evidence` → inlined into `merge.py`), leaving the module with **zero consumers** → the dead-module ratchet now fails. This is **mission-introduced** (WP08), not truly pre-existing — surfaced by the WP10 implementer.
- **Status:** **RESOLVED at closeout (2026-06-08, commit 35db0271a).** Confirmed zero src callers (`grep -rn history_parser src/` → only the inline comment in `merge.py`); deleted `src/specify_cli/status/history_parser.py` and its unit test `tests/status/test_history_parser.py`. Removed the two stale `history_parser.extract_done_evidence` mock-patches in `test_merge_status_commit.py` and `test_merge.py` (the function is now inlined in `merge.py`, no patch target), and dropped the module from the lane-regression-guard excluded list. `test_no_dead_modules` + `test_no_dead_symbols` now GREEN. Randy-Reducer dead-weight elimination — cleanest option taken.
- **Rough effort:** Done.
