# Contract — repo-wide `status/` import boundary

Extends `tests/architectural/test_status_module_boundary.py` from the 6 WP03 packages to all of `src/specify_cli`.

## Rule

No module under `src/specify_cli/` outside `src/specify_cli/status/` may import a `status.*` **submodule** directly. Only `from specify_cli.status import <symbol>` (the facade) or `MissionStatus` usage is permitted.

```
DISALLOWED:  from specify_cli.status.emit import build_status_event
             from specify_cli.status.lane_reader import get_wp_lane
             import specify_cli.status.reducer as _reducer
ALLOWED:     from specify_cli.status import build_status_event, MissionStatus
```

## Exemptions (documented plumbing — C-004)

- `src/specify_cli/coordination/status_transition.py`
- `src/specify_cli/coordination/transaction.py`
- `src/specify_cli/workspace/context.py`

These are internal Mission-Management plumbing and legitimately reach `status/` internals; the test must identify and exempt them (not "fix" them).
`workspace/context.py` is a permanent import-time cycle breaker: `status/__init__` imports `status.emit`, which imports workspace context before the status facade has finished initializing.

## Pass condition

- `grep -rn "from specify_cli\.status\.\|import specify_cli\.status\." src/ --include=*.py | grep -v "src/specify_cli/status/"` returns only the exempted lines (target: 0 non-exempt).
- The AST-scan + pytestarch rule is green over all of `src/specify_cli`.
- A synthetic injected violation is caught (non-vacuous), mirroring the existing SR-3 injection proof.
- Scan completes ≤15 s (NFR-005).

## Symbol disposition (set during IC-05; see occurrence_map.yaml)

Each promoted symbol is added to `status/__init__.py` `__all__` (C-007 charter convention); each demoted symbol gets a `_` prefix and loses external import sites.
