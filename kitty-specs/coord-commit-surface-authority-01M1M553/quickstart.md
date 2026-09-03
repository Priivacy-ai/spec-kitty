# Quickstart: reproduce the defects & verify the fixes

All repros use an isolated temp git repo + the installed `spec-kitty`. Never `uv run` (it re-syncs the venv).

## #2533 — redundant coord topology on `--start-branch` (WP-A)

```bash
git init -b main repo && cd repo && git commit --allow-empty -m init
spec-kitty init --ai claude --non-interactive && git add -A && git commit -m sk
spec-kitty agent mission create m --friendly-name M --purpose-tldr x --purpose-context xxxx \
  --json --pr-bound --branch-strategy already-confirmed --start-branch fix/m | grep -o '"topology": "[^"]*"'
```
- **Before**: `topology: coord` (redundant; coord branch stranded).
- **After (DD-2)**: `topology: single_branch`; no coordination branch minted; `git branch --list 'kitty/*'` empty.

## B16-c2 folded into #2533 — no stranded/mislabelled coord branch (WP-A regression)

Create two concurrent coord missions on an unprotected primary; assert no coord branch label sits on a sibling mission's commit. After DD-2 the missions are `SINGLE_BRANCH`, so no coord branch exists to strand. (Pre-fix evidence: `scratchpad/b16repro2`, research E-006.)

## #2300 — three-command skip-vs-refuse unification (WP-B)

On a coord + protected-`main` mission, run each command against a primary-kind artifact:
```bash
spec-kitty agent tasks move-task ...      # before: exit 0 (silent skip)
spec-kitty agent tasks mark-status ...    # before: exit 0 (swallowed warning)
spec-kitty agent tasks map-requirements ...  # before: exit 1 (refuse)
```
- **After (DD-1)**: all three exit 1 with the same real remedy; genuine no-ops still exit 0 with a typed `reason`. Verify via the golden characterization diff (`tests/.../characterization`).

## DD-3 — fail-loud on missing mid8 (WP-C)

Corrupt/truncate a mission's `meta.json` so `_resolve_mid8` returns None, then attempt a coord commit.
- **Before**: silent fallback to the primary checkout (wrong surface).
- **After**: fail-loud error naming the mission; no silent primary write.

## Gate before PR
```bash
PWHEADLESS=1 .venv/bin/python -m pytest tests/ -n auto --dist loadfile -p no:cacheprovider
pytest tests/architectural/test_no_legacy_terminology.py
ruff check . && mypy src/specify_cli/...(changed files)
```
