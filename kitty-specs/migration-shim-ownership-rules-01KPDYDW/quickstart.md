# Quickstart — Registering a Shim

**Mission**: `migration-shim-ownership-rules-01KPDYDW`
**Audience**: Authors of future extraction PRs (#612 runtime, #613 glossary, #614 lifecycle, model-discipline doctrine port).
**Reading time**: 5 minutes.

---

## Scenario

You just extracted a slice from `specify_cli` into a canonical top-level package (e.g. `runtime/`, `glossary/`). You need to leave a compatibility shim at the old import path so external importers do not break. Here is the end-to-end recipe.

## Step 1 — Author the shim module

Create `src/specify_cli/<legacy_name>.py` (single-module shim) OR `src/specify_cli/<legacy_name>/__init__.py` (package shim) with exactly this shape:

```python
"""Compatibility shim — re-exports from canonical.runtime.

Deprecated: import from canonical.runtime instead. Scheduled for removal in 3.3.0.
"""
from __future__ import annotations

import warnings

# Re-exports (replace with your actual canonical module's public API)
from canonical.runtime import *  # noqa: F401, F403 — shim re-export
from canonical.runtime import __all__  # if the canonical defines __all__

__deprecated__ = True
__canonical_import__ = "canonical.runtime"
__removal_release__ = "3.3.0"
__deprecation_message__ = (
    "specify_cli.runtime is deprecated; import from canonical.runtime. "
    "Scheduled for removal in 3.3.0."
)

warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)
```

Mandatory pieces (FR-003):

- Module docstring mentions `Deprecated:` and the canonical import.
- `__deprecated__ = True` — used by the FR-010 scanner.
- `__canonical_import__` matches the registry's `canonical_import` field.
- `__removal_release__` matches the registry's `removal_target_release` field.
- `__deprecation_message__` is the exact text of the warning.
- `warnings.warn(..., DeprecationWarning, stacklevel=2)` — `stacklevel=2` is mandatory.

## Step 2 — Add a registry entry

Edit `architecture/2.x/shim-registry.yaml`:

```yaml
shims:
  # ... existing entries ...
  - legacy_path: specify_cli.runtime
    canonical_import: canonical.runtime
    introduced_in_release: "3.2.0"
    removal_target_release: "3.3.0"
    tracker_issue: "#612"
    grandfathered: false
    notes: "Runtime extraction per mission #612."
```

Rules:

- `introduced_in_release` = the release that will ship your shim.
- `removal_target_release` = the **next minor release** after `introduced_in_release` by default (FR-004 one-release window). If you need longer, add `extension_rationale: "..."` with reviewer sign-off.
- `grandfathered: false` — always, for new shims.
- `tracker_issue` is the GitHub issue for your extraction mission.

## Step 3 — Verify locally

```bash
spec-kitty doctor shim-registry
```

You should see your new entry in the table with status `pending`. If you see `overdue`, your `removal_target_release` is behind the current project version — fix the target.

If you see a schema error, check the contract in `kitty-specs/migration-shim-ownership-rules-01KPDYDW/contracts/shim-registry-schema.yaml`.

## Step 4 — Verify the architectural tests pass

```bash
pytest tests/architectural/test_shim_registry_schema.py -v
pytest tests/architectural/test_unregistered_shim_scanner.py -v
```

Both must pass before your PR is mergeable.

## Step 5 — Ship

Your PR lands. Your shim is in place. The clock starts: your `removal_target_release` is ticking down.

---

## When it's time to remove the shim (later release)

Follow the removal-PR contract (FR-005):

1. Delete `src/specify_cli/<legacy_name>.py` (or the package directory).
2. Remove the entry from `architecture/2.x/shim-registry.yaml` (or mark it `status: removed` if you prefer to keep historical entries — the doctor check treats a missing module file with an overdue target as `removed`).
3. Add a `CHANGELOG.md` entry under **Removed** naming the legacy path and the tracker issue.
4. Close the tracker issue.
5. CI's `spec-kitty doctor shim-registry` now passes without advisory for that entry.

## Extending a removal window

If external importers need more notice:

```yaml
  - legacy_path: specify_cli.glossary
    canonical_import: glossary.api
    introduced_in_release: "3.2.0"
    removal_target_release: "3.4.0"   # was 3.3.0, now 3.4.0
    tracker_issue: "#613"
    grandfathered: false
    extension_rationale: "External downstream importers (2 known) need a full release of lead time; extended per review discussion in PR #NNN."
```

Extension requires: (a) the registry edit in a PR, (b) a non-empty `extension_rationale`, (c) the same reviewer bar as any architecture change (FR-004, ADD-4).

---

## Cheat sheet: the 6 mandatory shim-module attributes

| Attribute | Example |
|-----------|---------|
| module docstring with "Deprecated:" | `"""Compatibility shim — re-exports from canonical.runtime. Deprecated..."""` |
| `__deprecated__` | `True` |
| `__canonical_import__` | `"canonical.runtime"` (or list for umbrella) |
| `__removal_release__` | `"3.3.0"` |
| `__deprecation_message__` | `"specify_cli.runtime is deprecated; ..."` |
| `warnings.warn(..., stacklevel=2)` | `warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)` |

And the 7 required + 2 optional registry fields:

| Field | Required | Notes |
|-------|----------|-------|
| `legacy_path` | yes | |
| `canonical_import` | yes | str or list[str] |
| `introduced_in_release` | yes | semver |
| `removal_target_release` | yes | semver |
| `tracker_issue` | yes | `#NNN` or URL |
| `grandfathered` | yes | bool, `false` for new shims |
| `extension_rationale` | conditional | required when target_release is extended |
| `notes` | optional | free text |

## Reference mission

The `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` mission is the canonical worked example — see section 7 of `architecture/2.x/06_migration_and_shim_rules.md` for the rule-by-rule mapping.
