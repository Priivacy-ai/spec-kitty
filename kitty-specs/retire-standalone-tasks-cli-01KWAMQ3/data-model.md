# Data Model: Retire Standalone Tasks CLI

This mission introduces no data entities, schemas, or persisted state. It is a code-removal mission plus one opt-in CLI flag. The "model" is the inventory of artifacts removed, edited, and added.

## Removed surfaces (modules)

| Artifact | Kind | Note |
|----------|------|------|
| `scripts/tasks/{tasks_cli.py,task_helpers.py,acceptance_support.py}` | repo-root standalone CLI | dead at product runtime |
| `.kittify/overrides/scripts/tasks/` (3 files) | override snapshot | spec-kitty-repo-only |
| `src/specify_cli/scripts/tasks/` (3 files + package) | packaged copy | test-only; leaves the wheel |

## Added surface (behavior)

| Artifact | Kind | Shape |
|----------|------|-------|
| `spec-kitty accept --normalize-encoding/--no-normalize-encoding` | typer flag (default off) | On `ArtifactEncodingError`: off → exit 1 (existing); on → `normalize_feature_encoding(repo_root, feature) -> list[Path]`, report repaired paths, re-collect, proceed. |

## Reused canonical surface (unchanged)

- `specify_cli.acceptance.normalize_feature_encoding(repo_root: Path, feature: str) -> list[Path]` — the encoding-repair workhorse FR-005 delegates to (C-003).
- `specify_cli.acceptance._read_text_strict` / `ArtifactEncodingError` — the existing without-flag error path.
- `specify_cli.task_utils.support.{set_scalar,split_frontmatter,build_document,append_activity_log}` — the canonical helpers `tests/utils.py::write_wp` repoints to.
- `specify_cli.upgrade.legacy_detector.is_legacy_format` and the migration/dashboard paths — **out of scope, unchanged** (C-005).

## Ratchet state transitions (FR-007)

Allowlist frozensets shrink to their post-deletion live sizes (burn-down, C-002): `test_no_dead_symbols` −34 symbols, `test_no_dead_modules._CATEGORY_3` 4→1, plus in-file removals in `test_gate_read_literal_ban.py` and `resolution_gate_allowlist.yaml`. No allowlist grows.
