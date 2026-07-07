# Research: test-suite state-leak re-audit (#1842 / #1634) — HEAD `d63ec2152`

Fresh re-audit (2026-07-06, researcher profile) because Stijn's 2026-06-11 8-class audit is ~4 weeks / 100+ commits stale. Method: static verification + two empirical runs (mission-creating slice: 48 passed; e2e slice: 7 passed), then re-check `git status` / `kitty-specs` / branches / `.worktrees` / `/tmp`.

## Per-class verdicts (current)

| LC | Status | Evidence |
| --- | --- | --- |
| LC-1 (#1634) | **FIXED (masked)** | After all mission-creating tests: `git status` 0 lines, no `test-feature-*` dirs/branches, `.worktrees/` empty. Tests chdir to `tmp_path` (`test_feature_slug_validation.py:47-49`); e2e uses `capture_source_pollution_baseline`. **But** `.gitignore:143-144` masks `test-feature-*` from git — a regression is invisible. |
| LC-2 | FIXED | `test_status.py` (both copies) grep-clean for `/tmp`. |
| LC-3 | **PARTIAL/RUNTIME** | **Correction (post-spec squad):** the composed writer is LIVE — only the literal `composed-accept` *name* is gone. THREE flat-`/tmp` writers remain: `prompt_builder.py:479` (`spec-kitty-next-*`, ULID → unbounded), `decision.py:610/656` (`mkstemp("spec-kitty-composed-{action}-")`, **unbounded — unique suffix per call**, no cleanup), `workflow.py:704` (`implement|review`, bounded overwrite). |
| LC-4 | **LEAKS** (subset of LC-3) | e2e run left `/tmp/spec-kitty-next-...golden-path-demo-...research.md`. |
| LC-5 | FIXED (git-visibility) | `.pytest_cache` + `.worktrees/` gitignored; no post-remove hook but no live husks. |
| LC-6 | **RUNTIME-CHANGE-NEEDED** | **Correction (post-spec squad):** `.kittify/workspaces/*.json` is written by `workspace/context.py:305 save_context`, from `lanes/implement_support.py:127,167` AND `lanes/recovery.py:732` — NOT `context/resolver.py:270` (which calls the *other* `save_context` in `context.store`, writing the separate `.kittify/runtime/contexts/` MissionContext surface). No completion/cancel tombstone; `cleanup_orphaned_contexts` gates on `worktree_path.exists()` → **no-op on cancel while the worktree lives** (cancel needs targeted `delete_context(workspace_name)`); merge hook must run AFTER `executor.py`'s worktree removal (~:749). **14 committed orphans** for merged 059/060. |
| LC-7 | FIXED (#959) | `prompt_metadata.py:95-123` namespaces under `spec-kitty-review-prompts/{repo}-{sha256[:12]}/`. Residual: within-repo retention (no cross-repo collision). |
| LC-8 | FIXED | `out/` gitignored except `.gitkeep`; no test writes REPO_ROOT `out/`. |
| **N1 (new)** | **LEAKS** | `/tmp/spec-kitty-test-homes/<run_uid>/` (per-worker HOME, `conftest.py:100-108`) never removed. **166 dirs / 144 MB**, +1/run. No sessionfinish teardown. Biggest disk leak, cheap fix. |

## #2181 ratchet backlog
`tests/architectural/tmp_ratchet_baseline.txt` = **99** grandfathered `/tmp` files, **spread across 21 dirs** (not a cheap single-file sweep). Hotspots: `specify_cli` (30) + `sync` (13) = 43%. Anti-vacuity floor = 50 (healthy). **Defer full burn-down**; cheap first tranche = `specify_cli`+`sync`.

## Reaper surface
**No session/teardown reaper exists** (zero `pytest_sessionfinish/sessionstart/unconfigure` under `tests/`). Existing: root `conftest.py` autouse **function-scoped** HOME isolation; `tests/e2e/conftest.py` `assert_no_source_pollution` (opt-in detector, asserts but doesn't clean). Recommended design:
- **`pytest_sessionfinish` hook** in root `tests/conftest.py`, **controller-gated** (`session.config.workerinput is None`) so workers don't race on shared REPO_ROOT.
- **Snapshot-delta**: snapshot at `sessionstart` (existing `kitty-specs/*`, `kitty/*` branches, `.worktrees/*`, `.kittify/workspaces/*.json`); reap only the delta matching test patterns.
- **git-unregistered `.worktrees/`**: `git worktree prune` (clears registered-but-missing) THEN `rmtree` any `.worktrees/*` absent from `git worktree list --porcelain`.
- **/tmp sweep**: current-run `spec-kitty-next-*`, `spec-kitty-implement|review-*`, `spec-kitty-review-prompts/<this-repo-hash>/`, `spec-kitty-test-homes/<run_uid>/` (N1).
- Key on REPO_ROOT (shared), not HOME (per-worker, auto-discarded).

## Recommended bounded scope (→ this mission)
Fix now: **session reaper** (headline; self-heals LC-1, lets us retire the `.gitignore` masks) + **LC-3/LC-4 `/tmp` prompt-namespacing** + **N1** + **LC-6 tombstone** (folded in per operator). Defer: ratchet burn-down (99 files), LC-7 within-repo retention, LC-3 `workflow.py` bounded-overwrite. Already-fixed (guards only): LC-2/5/7/8.
