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

## S-02 — CI `execution_context` path filter goes stale once the relocation merges

- **Location:** `.github/workflows/ci-quality.yml` — the `execution_context` path filter: `src/specify_cli/core/execution_context.py`, `src/specify_cli/status/**`, `src/runtime/next/**`, `src/specify_cli/cli/commands/agent/**`, `tests/architectural/test_execution_context_parity.py`.
- **Tool/rule:** none (CI config drift; surfaced by the WP01 post-rebase re-review).
- **Description:** The filter still watches `src/specify_cli/core/execution_context.py` (which WP03 **deletes**) and does **not** watch the new `src/mission_runtime/**` package. FR-024 intended the ratchet to gate PRs touching `mission_runtime/` once it existed; WP01 legitimately deferred that because the module didn't exist yet.
- **Why deferred:** On `feat`'s *current* state the filter is still correct (`core/execution_context.py` exists; `mission_runtime/` does not). It only goes stale when the lane relocation **merges to feat**. So this is a **merge-time** remediation, not a feat edit now.
- **Rough effort:** Low. At/after the mission merge: add `src/mission_runtime/**` to the `execution_context` filter and drop the deleted `core/execution_context.py` path. Completes FR-024.

---

## S-03 — mission_runtime docstrings said "shim" for a deleted module — **FIXED**

- **Location:** `src/mission_runtime/{resolution.py, __init__.py, context.py}`.
- **Tool/rule:** none (doc accuracy; surfaced by the WP02+WP03 post-rebase re-review).
- **Description:** Docstrings described `core/execution_context.py` as a "thin re-export shim", but WP03 deleted it outright (no importers remained). Stale wording.
- **Status:** **Remediated** in `4b52a86d7` (docstring-only; ruff/mypy clean). Reworded to state the module was removed and the historical names are re-exported from the package root. Listed here for the audit trail.
- **Note:** `.contextive/execution.yml:21` (a glossary string referencing `core/execution_context.py` as owner) is absent in the lanes but may exist on other branches — verify/update at merge if present.

---

## S-04 — pre-existing environmental test failures on the lane base (must clear before merge)

- **Location:** `tests/runtime/test_bootstrap_unit.py` (≈14 failures); also seen earlier: `test_agent_utils_status` (×2), `test_internal_runtime_parity` snapshot drift.
- **Tool/rule:** pytest (environmental, not lint).
- **Description:** `test_bootstrap_unit.py` fails because `SPEC_KITTY_TEMPLATE_ROOT` / `get_package_asset_root` expects a real checkout asset layout not present in the lane/test env. The WP04 + WP02/03 re-reviews both proved these are **pre-existing and unrelated** to this mission's changes (the relevant `src/` files are byte-identical to the WP base; reproduced on a pure-feat baseline).
- **Why deferred:** Not caused by any WP here, and out of the residue-routing/relocation scope. But they are real RED tests on the branch.
- **Rough effort:** Unknown until triaged. **Action required before mission merge / for CI green:** triage whether these are (a) genuinely environmental (need a fixture/asset-root setup or a skip marker for non-checkout envs) or (b) a real regression on `feat` from another mission (e.g. the session_presence merge). Do NOT let the mission merge with these RED — either fix, mark xfail/skip with rationale, or confirm CI's env provides the asset layout so they pass there.
