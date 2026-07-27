---
cycle_number: 3
mission_slug: decompose-agent-tasks-god-module-01KVWVAR
reviewer_agent: claude:opus:reviewer-renata:reviewer
reviewed_at: '2026-06-24T16:30:00Z'
verdict: approved
wp_id: WP06
---

# WP06 Review — Cycle 3 (APPROVED)

Independent review of the WP06 code commit `1bdae87bc`
("extract tasks_parsing_validation seam + sub-split _validate_ready_for_review").

## Override of stale rejection artifact

`review-cycle-2.md` carries `verdict: rejected`, but it is **not** a code-quality
rejection: it documents an orchestration reset ("WP06 reset from blocked to planned
after orchestrator fixed the dependency-base merge … No code change required for WP06;
code unchanged"). The actual implementation was completed afterward and is what this
cycle reviews. Approving with `--skip-review-artifact-check` is therefore justified.

## The highest-risk check: validator sub-split is behavior-preserving

Compared the ORIGINAL `_validate_ready_for_review` (`1bdae87bc^:tasks.py`,
lines 1257–1604, 348 LOC) against the new orchestrator + 9 helpers:

- **Validation order — identical.** force short-circuit → research-artifacts
  (Check 1, all missions) → software-dev worktree-state: resolve workspace →
  `repo_root` short-circuit `(True, [])` → resolve worktree path (legacy lane-a
  fallback) → worktree-exists fall-through → husk → toplevel → detached-HEAD →
  in-progress merge/rebase/cherry-pick → behind-base currency (planning-only
  allowance) → uncommitted (staged/unstaged/untracked classification) →
  no-commit-beyond-base → kitty-specs contamination.
- **Error messages — byte-identical.** Extracted all 80 `guidance.append(...)`
  payloads from both old and new; the only textual delta is the contamination
  block using the `KITTY_SPECS_DIR` constant instead of the `"kitty-specs"`
  literal — and `KITTY_SPECS_DIR == "kitty-specs"`, so every interpolation
  renders the same string at runtime (a valid S1192 improvement).
- **Return shape — preserved.** `(bool, list[str])`; `_validate_worktree_state`
  returns `None` to mean "fall through to final `(True, [])`", `(True, [])` for
  the repo_root short-circuit, `(False, guidance)` for every blocking gate.
  Short-circuit semantics unchanged.

## Complexity (NFR-001)

`ruff check --select C901 --config lint.mccabe.max-complexity=15` on the seam:
**clean.** All 9 helpers (research-artifacts, resolve-worktree-path,
worktree-health, branch-currency, uncommitted, commit-present, contamination,
plus the two orchestrators) are ≤15 CC.

## One-way imports + thin wrapper

- No back-import to `agent.tasks` in the seam (grep empty). Seam imports only
  canonical sources + may reference outline/materialization (seam↔seam allowed).
- `tasks.py` keeps `_validate_ready_for_review` as a **thin wrapper** that
  delegates to `_seam_validate_ready_for_review`, injecting the `tasks`-resident
  collaborators (`get_main_repo_root`, `get_mission_type`,
  `get_feature_target_branch`, `resolve_workspace_for_wp`,
  `_review_currency_check_branch`, `_behind_commits_touch_only_planning_artifacts`,
  `_filter_runtime_state_paths`, `_list_wp_branch_specs_changes_for_guard`,
  `console`) from live module globals. This preserves all
  `@patch("...agent.tasks.<name>")` contracts. The wrapper duplicates **no**
  validation logic. Moved issue-matrix/verdict helpers are removed from
  `tasks.py` and re-exported via the seam import.

## Suites, coverage, tests

- `tests/specify_cli/cli/commands/agent/`: **467 passed, 2 xfailed** incl. the
  golden CLI contract (`test_tasks_cli_contract.py`, 27 passed).
- `mypy --strict` on the seam: clean.
- Seam coverage across the full agent suite: **90%** (dedicated unit file 84%;
  orchestrators exercised via integration). Remaining misses are
  defensive/fail-open BLE001 handlers and edge fallbacks.
- Test quality: per-sub-validator tests drive **real gate logic** (blocking +
  benign + clean for each gate), asserting exact first-line message strings and
  the in-mission approved-vs-done distinction. They would catch a flipped gate
  or a changed/dropped message. Not synthetic fixtures.

## Anti-pattern checklist

1. Dead code — PASS (seam consumed by `tasks.py` wrapper/import).
2. Synthetic-fixture test — PASS (tests invoke the real production parsers/gates).
3. Silent empty return — PASS (`return None`/`[]` are the documented gate-passthrough
   architecture; moved BLE001 handlers carry verbatim rationales).
4. FR coverage — PASS (FR-003/FR-004 sub-validators each directly tested).
5. Frozen surface — N/A (no frozen file touched).
6. Locked decision — PASS (no `--feature` flag introduced; one-way import respected).
7. Shared-file ownership — PASS (`tasks.py` is WP07-owned; minimal in-scope edit
   documented in commit + this record; coordination noted).
8. Production fragility — PASS (no new bare `raise` in a request/CLI path).

## Scope / deps

WP06 commit `1bdae87bc` touches exactly 3 files (`tasks.py` modified;
`tasks_parsing_validation.py` + `test_tasks_parsing_validation.py` new). No
`pyproject.toml`/`uv.lock` change. No stray `-` file. No new production
`# noqa`/`# type: ignore` (the 4 BLE001 in the seam are verbatim-moved with
existing rationales).

**Verdict: APPROVED.**
