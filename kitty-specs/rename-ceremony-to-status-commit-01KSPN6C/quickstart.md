# Quickstart: Rename Ceremony Commit to Status Commit

**Mission**: `rename-ceremony-to-status-commit-01KSPN6C`
**Date**: 2026-05-28
**Audience**: The agent executing the implement phase of this mission.

This runbook covers everything you need to land the rename from a clean checkout through accepted merge.

---

## 0. Prerequisites

- Repository root checkout at `/Users/robert/spec-kitty-dev/ceremony/spec-kitty` on branch `main` w/ latest changes pulled.
- `spec-kitty` CLI available on `$PATH` (verify w/ `spec-kitty --version`; expected `3.2.0rc28` or newer).
- `ripgrep` or GNU `grep` for occurrence verification.
- `uv` or `pip` for the project's existing Python environment.

---

## 1. Run `/spec-kitty.tasks`

Plan ends here. The next user invocation is `/spec-kitty.tasks`. That command will:

1. Read `spec.md`, `plan.md`, `occurrence_map.yaml`.
2. Materialize work packages, likely shaped as:
   - **WP01**: Glossary edit (add canonical + 2 deprecated entries).
   - **WP02**: Reconcile `commit_helpers.py` status-writing phrasings to status commit.
   - **WP03**: Rename test fixtures + identifiers (`E2E_CEREMONY_BRANCH`, `_checkout_e2e_ceremony_branch`, `mission-merge-ceremony`) and update callers.
   - **WP04**: Doctrine + skills semantic rewrite (per R2 in the contract).
   - **WP05**: Docs + engineering notes rewrite incl. F-09 finding doc.
   - **WP06**: Add `tests/architectural/test_no_legacy_terminology.py` regression guard.
   - **WP07**: Update `tests/architectural/_baselines.yaml` comment.
   - (Granularity is the tasks command's call; this is illustrative.)

---

## 2. Implement phase

For each WP, run:

```bash
spec-kitty implement WP## --mission rename-ceremony-to-status-commit-01KSPN6C
```

This resolves the lane workspace (`.worktrees/rename-ceremony-to-status-commit-01KSPN6C-lane-X/`) and prints the path. Do all WP-specific edits in that workspace.

Apply each edit by consulting `occurrence_map.yaml` — every code change should map to one (or more) occurrence rows. The implement-review loop will compare your diff to the occurrence map.

### Critical rules during implement

- **Do not** introduce new occurrences of "ceremony" or "status-writing" anywhere in `src/`, `tests/`, `docs/`.
- **Do not** rewrite git history.
- **Do not** touch `kitty-specs/` historical mission artifacts.
- **Do** rename Python identifiers consistently across all callers — `mypy --strict` will catch stragglers.
- **Do** preserve quote style and surrounding punctuation in string literals.

---

## 3. Per-WP verification

After each WP, from the lane workspace:

```bash
# Lint + types
ruff check .
mypy --strict src/

# Targeted test selection (replace pytest path per WP)
pytest tests/e2e/ -k status_commit          # for WP03 (renamed identifiers)
pytest tests/doctrine/                       # for WP01/WP04
pytest tests/architectural/                  # for WP06/WP07
```

Stage and commit via the mission lane (lane branches accept safe-commit; `main` does not).

---

## 4. Acceptance gates (end of mission)

Before requesting merge, run from the lane workspace:

```bash
# Gate 1: zero "ceremony" hits in active surface
grep -rn 'ceremony' src/ tests/ docs/ --include='*.py' --include='*.md' --include='*.yaml'
# expected: empty output, exit code 1

# Gate 2: zero "status-writing" hits in active surface
grep -rn 'status-writing' src/ tests/ docs/ --include='*.py' --include='*.md' --include='*.yaml'
# expected: empty output, exit code 1

# Gate 3: full test suite passes (incl. new regression guard)
PWHEADLESS=1 pytest tests/

# Gate 4: mypy strict
mypy --strict src/

# Gate 5: ruff
ruff check .

# Gate 6: glossary loads cleanly + contains all three entries
python -c "
import ruamel.yaml
y = ruamel.yaml.YAML(typ='safe')
data = y.load(open('.kittify/glossaries/spec_kitty_core.yaml'))
surfaces = {t['surface']: t for t in data['terms']}
assert 'status commit' in surfaces and surfaces['status commit']['status'] == 'active', 'missing canonical'
assert 'ceremony commit' in surfaces and surfaces['ceremony commit']['status'] == 'deprecated', 'missing deprecation 1'
assert 'status-writing operation' in surfaces and surfaces['status-writing operation']['status'] == 'deprecated', 'missing deprecation 2'
print('Glossary OK')
"
```

If all six gates pass, the mission is acceptance-ready. Run `/spec-kitty.accept` to finalize, then `spec-kitty merge` to land on `main`.

---

## 5. Common pitfalls

| Pitfall | Detection | Fix |
|---|---|---|
| Renamed `E2E_CEREMONY_BRANCH` but left `"e2e-ceremony"` literal | `git grep '"e2e-ceremony"'` returns a hit | Update both the constant name (cs-001) and its value (sk-003) in the same edit |
| Mechanically substituted "ceremony" in `SKILL.md` and produced "full status commit" | Reviewer flag during review WP | Apply R2 (semantic rewrite — see occurrence_map.yaml dd-003..dd-006) |
| Missed a doctrine occurrence that grep would have caught | acceptance Gate 1 fails | Re-run plan-time grep against the lane workspace; cross-check against occurrence_map.yaml |
| Glossary YAML loses key sort order | `ruff` is fine but glossary reviewers complain | ruamel.yaml preserves order by default; if you used `yaml.dump`, switch back |
| Architectural test fails on its own existence | `test_no_legacy_terminology.py` scans itself and the mention of "ceremony" in error messages fails the test | Test must use string-construction tricks (e.g., `"".join(["cere", "mony"])`) or exclude `tests/architectural/test_no_legacy_terminology.py` from its own scan |

---

## 6. Rollback (if needed mid-mission)

```bash
# Abandon lane workspace, return to main
git worktree remove .worktrees/rename-ceremony-to-status-commit-01KSPN6C-lane-X
git checkout main
git branch -D kitty/mission-rename-ceremony-to-status-commit-01KSPN6C-lane-X
spec-kitty agent mission delete --mission rename-ceremony-to-status-commit-01KSPN6C  # if you also want to drop the kitty-specs/ artifacts
```

A pure terminology rename has near-zero risk to roll back — no schema, no data, no behavior.
