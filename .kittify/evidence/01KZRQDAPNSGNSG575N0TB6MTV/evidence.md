# Core #3328 WP01 fix-cycle implementer evidence

- Governed Op: `01KZRQDAPNSGNSG575N0TB6MTV`
- Resolved profile: `python-pedro` (direct dedicated implementation subagent)
- Cycle-1 base commit: `2d1721c24c4394aee5cbf8b02cd28377fe0be100`
- Fix commit: `549bb2af8be4e2872d865839495022648850d069` (`fix(WP01): require exact checkout roots`, unsigned)
- State: `WP01` moved `in_progress` → `for_review`; `T001`–`T005` done

## RED

Before production edits, two real-git tests for primary and linked-worktree subdirectories both failed because `is_worktree_of(...)` returned `True` instead of `False`: 2 failed in 50.32s, exit 1.

- `/tmp/core-3328-wp01-fix-red.txt`
- SHA-256 `11c267adbbf7f0baae418288d36d8692d3de41fafd0d66c4aa7716477f65322a`

## GREEN

- Focused adversarial subdirectory tests: 2 passed (final rerun 51.20s)
- Full checkout ownership: 21 passed
- Safe-commit integration: 16 passed
- Runtime paths: 25 passed
- Architecture/import fences: 27 passed
- Ruff: pass
- Focused strict mypy with `core/errors.py`: pass
- Import smoke and `git diff --check`: pass
- Canonical pre-review scoped regression gate: no new failures

- `/tmp/core-3328-wp01-fix-checks.txt`
- SHA-256 `057029d0a03ca221baac6ac9ff9c4cddc4b7411794784ac9d642ed9fc4f5bd6e`

## Profile/governance correlation

- Resolved profile JSON: `/tmp/core-3328-python-pedro-profile.json`, SHA-256 `eb9096e0425f3cb573430a7bf21a3c7953cb7ca75982b93cebdf1c3109769d74`
- Implement governance JSON: `/tmp/core-3328-python-pedro-implement-governance.json`, SHA-256 `fd8362c85474e6637fd4cde3cd43318816bff44154264d91173c9d01534d770c`

Only runtime-owned `kitty-specs/worktree-owned-root-3328-01KZRG01/.kittify/encoding-provenance/global.jsonl` remains untracked. It was preserved through a reversible temporary relocation during the canonical transition; no `--force` or deletion.
