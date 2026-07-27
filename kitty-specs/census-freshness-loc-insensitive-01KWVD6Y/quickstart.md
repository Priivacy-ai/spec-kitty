# Quickstart: verifying the LOC-insensitive census gate

All commands run from the repository root. Iterate with the venv python (avoids the
~75s `uv run` editable rebuild); `--emit-census` uses the module entry point.

## Verify the fix eliminates the tax (SC-001)

```bash
# green baseline
PWHEADLESS=1 .venv/bin/python -m pytest \
  tests/architectural/test_ci_topology_worklist.py -p no:cacheprovider -q -o addopts=""

# add lines to a worklist dir; gate must STAY GREEN (before the fix this reds)
printf '# probe\n\n\n' > src/specify_cli/bulk_edit/_zzz_probe.py
PWHEADLESS=1 .venv/bin/python -m pytest \
  tests/architectural/test_ci_topology_worklist.py -p no:cacheprovider -q -o addopts=""
rm -f src/specify_cli/bulk_edit/_zzz_probe.py
```

## Regenerate the census (canonical, never hand-edit)

```bash
uv run python -m tests.architectural._gate_coverage --emit-census
git diff tests/architectural/ci_topology_census.json   # worklist entries lose `loc`
```

## Confirm the teeth still bite (SC-002..SC-005, SC-007)

Run the self-mutation tests added by this mission:

```bash
PWHEADLESS=1 .venv/bin/python -m pytest \
  tests/architectural/test_ci_topology_worklist.py -p no:cacheprovider -q -o addopts="" -k "tooth or churn or rank or floor or tamper"
```

Each proves a mutation (drop a dir / phantom dir / edit a routing target / floor-cross
via `t_loc`) reds the comparison, and a rank-altering LOC churn stays green.

## Full gate before merge (SC-006)

```bash
PWHEADLESS=1 uv run python -m pytest tests/architectural/ -q
```
