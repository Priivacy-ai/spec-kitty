# Quickstart — verify the four outcomes locally

All commands run from the repository root checkout with `uv run` (bare `python` imports the wrong `src` in
this layout).

## SC-001 — single-source pickup (#2669)

```bash
# The single-source guard test adds a synthetic mission type and asserts universal pickup:
uv run python -m pytest tests/charter -k "single_source or roster" -q
# Manual smoke: every roster derives from the same ids
uv run python -c "from doctrine.missions.mission_type_repository import builtin_mission_type_ids; print(builtin_mission_type_ids())"
```

## SC-005 — no import-time filesystem I/O in charter (#2669 NFR-001)

```bash
uv run python -m pytest tests/charter -k "import_time or no_io" -q
```

## SC-002 — fail-loud action index (#2667)

```bash
uv run python -m pytest tests/doctrine/missions/test_action_index.py -q
```

## SC-003 — cross-grain scan loud outside pytest (#2666)

```bash
# Runtime surface:
uv run spec-kitty doctor doctrine --json          # RC=0 healthy on a clean tree
# CLI + structural gate tests:
uv run python -m pytest tests/specify_cli/cli/commands -k doctrine -q
uv run python -m pytest tests/doctrine/drg/test_cross_grain_integrity.py -q
```

## SC-004 — public built-in-root accessor (#2668)

```bash
uv run python -m pytest tests/charter/test_action_grain.py -q
# Assert zero SLF001 bypasses of the accessor remain:
grep -rn "_default_built_in_dir()  # noqa: SLF001" src/charter/ && echo "STILL PRESENT (fail)" || echo "clean"
```

## SC-006 — CI-only gates before hand-off

```bash
# Arch shard 1 pole (dead-symbol + terminology + layer rules):
uv run python -m pytest tests/adversarial tests/architectural tests/architecture tests/lint \
  -m 'arch_shard_1 and not windows_ci and (git_repo or integration or architectural) and not timing' \
  -q -n auto --dist loadfile
# Terminology guard (fast):
uv run python -m pytest tests/architectural/test_no_legacy_terminology.py -q
# DRG freshness (if mission-type discovery / graph changed):
uv run spec-kitty doctrine regenerate-graph --check
```
