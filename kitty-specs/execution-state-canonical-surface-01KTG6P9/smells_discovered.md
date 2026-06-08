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
