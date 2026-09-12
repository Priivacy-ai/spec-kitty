# Contract — deprecation shim re-export surface (FR-002)

`specify_cli/dossier/manifest.py` must remain a valid import source for every
name consumers use today, after the loader relocates to
`charter/activation/manifest_loader.py` and the errors to
`charter/offering/missions/repository.py`.

## Required re-exports (all must import from the OLD path)

```python
from specify_cli.dossier.manifest import (
    ManifestRegistry,        # kept in specify_cli (thin delegate)
    load_manifest,           # re-exported from charter.activation.manifest_loader
    ManifestSchemaError,     # re-exported from charter.offering.missions.repository
    MalformedManifestError,  # re-exported from charter.offering.missions.repository
)
```

## Contract tests

- `import`-level: each of the four names resolves from
  `specify_cli.dossier.manifest` (regression against the 8+ importer sites:
  `sync/namespace.py:102`, `sync/dossier_pipeline.py:363`, 6 test modules).
- Identity: `specify_cli.dossier.manifest.ManifestSchemaError is
  charter.offering.missions.repository.ManifestSchemaError` (same object, not a
  copy) so `except ManifestSchemaError` at old-path catch sites still catches
  errors raised by the charter authority.
- Same for `MalformedManifestError`.
- `ManifestRegistry.load_manifest(...)` returns the SAME object the charter
  authority returns for identical inputs (delegate parity).

## Non-breaking guarantee

No consumer edits its import path in this mission. If a future mission removes the
shim, that is a separate, announced deprecation (documented in the ADR, C-005).
