# Quickstart: CI Health: Charter-Path Hotfix + Arch-Adversarial Shard

## Verify Concern A (docs charter-path)

```bash
pytest tests/docs/test_current_charter_paths.py -q
```
Expect: green, zero offenders. (Also re-grep the four guarded roots directly
as a sanity check: `grep -rn "memory/charter.md" docs/context docs/guides
docs/api spec-driven.md` should return nothing.)

## Reproduce a single arch-adversarial shard locally (Concern B)

Full pre-split selection (today, one shard):
```bash
pytest tests/adversarial tests/architectural tests/architecture tests/lint \
  -m 'not windows_ci and (git_repo or integration or architectural)' \
  -q --tb=short -n auto --dist loadfile
```

Post-split, a single shard (e.g. shard 2) reproduces exactly what CI runs for
that matrix leg:
```bash
pytest tests/adversarial tests/architectural tests/architecture tests/lint \
  -m 'arch_shard_2 and not windows_ci and (git_repo or integration or architectural)' \
  -q --tb=short -n auto --dist loadfile
```

Docs-only trim, per shard (mirrors the existing full-suite docs-only
narrowing, PR #2391):
```bash
pytest tests/adversarial tests/architectural tests/architecture tests/lint \
  -m 'arch_shard_2 and docs_scoped and not windows_ci' \
  -q --tb=short -n auto --dist loadfile
```

## Verify the partition invariants

```bash
pytest tests/architectural/test_arch_shard_marker_completeness.py -q   # new — total partition, no gaps/dupes
pytest tests/architectural/test_shard_universe_bounded.py -q            # generalized — union = full universe
pytest tests/release/test_coverage_topology_ownership.py -q             # per-shard coverage artifact naming
```

## Verify the workflow still stays de-serialized/group-less

```bash
pytest tests/architectural/test_arch_pole_deserialized.py -q
pytest tests/architectural/test_docs_scoped_arch_coverage.py -q
```
