# Quickstart — MissionResolver port

The value this mission delivers, in one snippet: **build a mission execution context in a unit test with
no filesystem**. That is the `#1619` unblock.

## Before (today) — the builder needs a real `kitty-specs/` tree

```python
# Not unit-testable: _assemble_core_fragments walks kitty-specs/ on disk.
ctx = build_execution_context(repo_root=some_real_repo_with_missions)
```

## After (this mission) — inject a FakeMissionResolver

```python
from specify_cli.context.mission_resolver import ResolvedMission, FakeMissionResolver

fake = FakeMissionResolver([
    ResolvedMission(
        mission_id="01KX1C051X4JT9VZE6NA3HEPXT",
        mission_slug="mission-resolver-port-01KX1C05",
        feature_dir=Path("/virtual/kitty-specs/mission-resolver-port-01KX1C05"),
        mid8="01KX1C05",
    ),
])

# FS-free: no kitty-specs/ tree required.
ctx = build_execution_context(repo_root=Path("/virtual"), resolver=fake)
assert ctx.mission_id == "01KX1C051X4JT9VZE6NA3HEPXT"
```

## Cold-miss / ambiguity are loud

```python
with pytest.raises(MissionNotFoundError, match="backfill-identity"):
    fake.resolve("nope")           # cold-miss → structured, names the recovery command

with pytest.raises(AmbiguousHandleError):
    ambiguous_fake.resolve("01")   # prefix matches >1 → never first-match-wins
```

## Production path is unchanged

```python
# No resolver passed → real FsMissionResolver, same behavior as today (uncached).
ctx = build_execution_context(repo_root=Path.cwd())
```

## Guard rails you will hit
- Adding a raw `kitty-specs/` `iterdir()` outside `FsMissionResolver` → `test_mission_resolver_walker_gate.py` fails.
- Storing the resolver on `MissionExecutionContext` → `test_mission_runtime_surface.py` / builder purity test fails.
- Run `tests/architectural/` from the **primary checkout** (not a worktree) and grep floor constants repo-wide before assuming one gate owns a pin.
