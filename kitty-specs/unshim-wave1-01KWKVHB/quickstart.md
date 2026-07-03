# Quickstart — unshim-wave1-01KWKVHB validation

```bash
export PATH="$PWD/.venv/bin:$PATH"
```

## Per-WP gate (run after every deletion batch — C-006 atomicity check)

```bash
PWHEADLESS=1 pytest tests/architectural/test_no_dead_modules.py tests/architectural/test_no_dead_symbols.py -q
ruff check .
python -m mypy src/ 2>&1 | tail -2   # must stay: Success, 0 issues
```

## Re-anchor interception proof (IC-02, per rewritten patch() site)

Either the site carries `assert_called*`, or record a red-first flip:

```bash
# 1. point the rewritten patch at a bogus target -> test MUST fail
# 2. restore the correct consumer-namespace target -> test green
PWHEADLESS=1 pytest <re-anchored test file> -q
```

## Deleted-module import check (NFR-002 — run at merge time; must return empty)

```bash
grep -rnE "(from specify_cli(\.core)?(\.sync)?(\.retrospective)? )?import .*(tasks_support|acceptance_matrix|identity_aliases|doc_generators|doc_state|gap_analysis|state_contract|workspace_context|task_profile)\b|from specify_cli\.(tasks_support|acceptance_matrix|doc_generators|doc_state|gap_analysis|state_contract|workspace_context|task_profile|core\.identity_aliases|sync\.(replay|tracker_client_glue)|retrospective\.lifecycle) import" src/
```

## C-001 boundary check (every WP diff)

```bash
git diff --name-only <base>..HEAD | grep -E 'auth/transport\.py|test_auth_transport_singleton' && echo "C-001 VIOLATION" || echo "C-001 clean"
```

## Mission-level closing sweep (merged branch)

```bash
PWHEADLESS=1 pytest tests/architectural/ -q -p no:cacheprovider
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider
PWHEADLESS=1 pytest tests/architectural/test_no_legacy_terminology.py -q   # pre-push guard
```

Expected final counts: `_CATEGORY_4_BACKCOMPAT_SHIMS == frozenset()`, `_CATEGORY_7` has exactly 2 rows (auth.transport, policy.audit), `_baselines.yaml`: category_4 0 / category_7 2 / category_b 224.
