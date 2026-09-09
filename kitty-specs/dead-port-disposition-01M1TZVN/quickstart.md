# Quickstart: Dead-Port Disposition

Repository root checkout, branch `missions/coreloop-proto-missions`. Venv: `uv sync --frozen --all-extras` once at the root; lane worktrees symlink `.venv` (pytest's `pythonpath = src` tests the worktree's `src/`).

## Mission-level gate (C-001)

Claim no WP until Mission A has merged into the branch:
```bash
spec-kitty agent tasks status --mission fsm-write-path-integrity-01M1TZV6     # all WPs done
git log --oneline -3                                                          # A's merge commit present
```

## The red-first ratchet (WP01, SC-001) — RED today

```bash
.venv/bin/python -c "import sys, specify_cli.mission_v1.events; print(sorted(m for m in sys.modules if m.split('.')[0] in ('transitions','six')))"
# today: ['six', 'transitions', 'transitions.core', ...]   after WP01: []
```

## Per-WP verification

| WP | Commands |
|---|---|
| WP01 | `.venv/bin/pytest tests/specify_cli/mission_v1 tests/missions tests/research tests/specify_cli/next/test_next_invocation_lifecycle_seam.py tests/specify_cli/test_wp_frontmatter_fold.py -q` · `.venv/bin/pytest tests/architectural -q -p no:cacheprovider` (once; pyproject touched) · `uv lock && git diff --stat uv.lock` · `make test-fast` |
| WP02 | `.venv/bin/pytest tests/doctrine -q` · SC-004 grep (see `contracts/glossary-bootstrap.md` §5) · `.venv/bin/pytest tests/architectural/test_no_legacy_terminology.py -q` |
| WP03 | `.venv/bin/pytest tests/architectural/test_layer_rules.py tests/architectural/test_no_dead_symbols.py tests/architectural/test_no_retired_subsystems.py tests/architectural/test_pyproject_shape.py tests/runtime/test_bridge_parity.py -q` · `make test-fast` |
| WP04 | `.venv/bin/pytest tests/next tests/runtime/next tests/architectural/test_layer_rules.py -q` · `grep -rn "derive_mission_state\|read_events" src` |

## Gate re-checks at tasks-finalize and PR assembly

```bash
unset GITHUB_TOKEN
gh pr view 3898 --repo Priivacy-ai/spec-kitty --json state,mergedAt -q '.state + " " + (.mergedAt // "unmerged")'   # emitter ADR
gh pr view 3899 --repo Priivacy-ai/spec-kitty --json files -q '.files[].path' | grep -E "mission_runtime|team_projection|test_no_dead_symbols" ; echo "expect: nothing"
```

## Decision records

```bash
spec-kitty agent decision verify --mission dead-port-disposition-01M1TZVN     # two deferred markers (OD2, OD6) expected until the operator answers
ls kitty-specs/dead-port-disposition-01M1TZVN/decisions/
```

## Next step

`/spec-kitty.tasks --mission dead-port-disposition-01M1TZVN` (four WPs; see `research.md` §8).
