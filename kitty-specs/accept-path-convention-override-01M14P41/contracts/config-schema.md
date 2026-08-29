# Contract: `project.path_conventions` config schema

## Location
`.kittify/config.yaml` → `project.path_conventions` (new key under the existing `project:` block).

## Shape
```yaml
# round-trip: skip: illustrative .kittify/config.yaml shape sketch — the executable schema is enforced by the reader in src/specify_cli/config/path_conventions.py, exercised by tests/specify_cli/config/test_path_conventions_reader.py
project:
  # ... existing identity fields (uuid, slug, node_id) unchanged ...
  path_conventions:      # OPTIONAL. Absent ⇒ no override (today's behavior).
    workspace: apps/     # any subset of the canonical keys
    tests: tests/
    # deliverables / documentation / data also permitted
```

## Rules
- Keys outside `VALID_PATH_KEYS = {workspace, tests, deliverables, documentation, data}` (the shared
  constant, extracted from `MissionConfig`) → **reject** (typo; FR-007a).
- `deliverables` — and any key whose mission default value is an artifact token — is **excluded** from
  the override (C-010): overriding it would flip `feature_dir`↔`project_root` routing. An override for it
  → warn/ignore.
- Remap-only: an override key the mission's own `paths:` does not declare → warn/ignore; never adds a new
  required path (FR-007b, C-010).
- Values MUST be non-empty, repo-relative strings. A `path_conventions` that is present-but-not-a-mapping,
  or carries a non-string/null, **empty/blank, absolute, or `..`-traversing** value → **fail closed** with
  an actionable message naming the offending key (FR-008). (An empty/blank value would collapse to the repo
  root and an absolute/traversing value would escape it — both silently defeating strict enforcement.)
- **Scope of fail-closed = the section shape only.** Absent key ⇒ `{}`. A whole `config.yaml` that is
  unreadable/corrupt stays **lenient** (⇒ `{}`) to match the co-resident section readers — do NOT inherit
  the preflight reader's blanket `except→default`, but DO match its file-level leniency.
- Absent key or empty map ⇒ empty override ⇒ byte-for-byte current behavior (NFR-004).

## Reader contract
```python
def load_project_path_conventions(repo_root: Path) -> dict[str, str]:
    """Read ONLY the project.path_conventions subkey (NOT the whole project: block — that carries
    identity fields uuid/slug/node_id/build_id which must not be rejected; C-011).
    Return the validated remap-only override, or {} when absent/file-unreadable.
    Raise a typed, actionable error on a malformed section shape (FR-008). One config read; no per-key FS read."""
```
Plumbing modeled on `charter_runtime/preflight/config.py` (typed section reader; C-004) — but the
fail-closed section validation is **authored**, not inherited (that template is lenient).
