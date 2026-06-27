# Calibration Report Template

Each per-mission calibration report documents the §4.5.1 inequality check
(R-005) for every step in the mission.  Reports are created by WP10 and
updated whenever calibration is re-run.

## Column Shape

| Column | Notes |
|---|---|
| Step id | The mission step under calibration. |
| Action id | Resolved action URN (e.g. `action:software-dev/implement`). |
| Profile id | Agent-profile URN assigned to this step. |
| Resolved DRG artifact URNs | Output of the DRG `resolve_context` call (direct scope + transitive requires/suggests). |
| Scope edges involved | Direct `scope` edges from the action node that seed the resolution. |
| Missing context | URNs in `RequiredScope` but absent from `ResolvedScope` — a half-1 violation. |
| Irrelevant / too-broad context | URNs in `ResolvedScope` that are neither required nor in `known_irrelevant` — a half-2 violation. |
| Recommended DRG edge changes | Structured `add_edge` / `remove_edge` / `rewire_edge` proposals. |
| Before/after evidence | `ResolvedScope` snapshot before the recommended fix; expected scope after the fix. |

## Overlay Files

Project-local DRG mutations go to:

```
.kittify/doctrine/overlays/calibration-<mission>.yaml
```

Supported keys: `add_edge`, `remove_edge`, `nodes`.

The runtime DRG resolver reads these overlays via
`specify_cli.calibration.walker._build_graph()` which calls
`doctrine.drg.loader.merge_layers()` followed by
`_apply_remove_edges()`.

## Reports

- [software-dev.md](software-dev.md)
- [research.md](research.md)
- [documentation.md](documentation.md)
- [erp-custom.md](erp-custom.md)
