# Phase 1 Data Model: Pack-Path Portability & Language-Scope Authority

## WP1 — `OrgPackConfig` (extended, not replaced)

**Entity**: `OrgPackConfig` (`src/doctrine/drg/org_pack_config.py`) — existing pydantic value object.

| Field | Type | Change | Validation rule |
|---|---|---|---|
| `local_path` | `Path` | Validator behavior changes; field type/shape unchanged | Stored value MUST remain the literal author-written template (e.g. `${SPEC_KITTY_PACK_HOME}/org-pack`, `~/.spec-kitty/pack`, or a plain absolute path). No expansion happens at construction/validation time. |
| `subdir` | `Path \| None` | No change | Continues to be validated as a literal relative path — no `..`, no absolute form — independent of any expansion. |

**New/changed behavior — `effective_root()`**:

- **Invariant**: `effective_root()` is the single point where `local_path` is expanded (`os.path.expandvars` then `os.path.expanduser`) before the existing `is_absolute()` classification, `subdir` join, and symlink-containment check run. No other code path performs expansion.
- **Invariant**: An unset or empty referenced variable raises a named error (extending the existing `OrgPackMissingError` family) identifying the missing variable name and the configured pack name. Resolution never returns a path containing a literal, unexpanded `${...}` token, and never silently degrades to an empty org layer.
- **Invariant**: A save→load round-trip (`save_pack_registry` → reload) MUST preserve the literal `local_path` string exactly as authored. This is a property of *not* mutating the field at construction, not an additional check.

**Legacy shape**: `_registry_from_legacy_organisation_packs` / `_build_legacy_single_pack` construct the same `OrgPackConfig`, so they inherit the corrected behavior automatically — no parallel implementation.

## WP2 — Compiled charter language set (new structured field)

**Entity**: Compiled charter language artefact (new).

| Field | Type | Owner | Description |
|---|---|---|---|
| `languages` (or equivalent structured field, exact name/location TBD by implementer within `src/charter/compiler.py`'s existing output shape) | `list[str]` | Charter compiler | The resolved, canonical set of governed languages, computed once at `charter generate`/`charter sync` time from the interview answers available at that moment, and persisted alongside/within the compiled charter output. |

**State transition**:

```
[no charter] --(interview)--> [interview answers only]
                                   |
                                   | charter generate / charter sync
                                   v
[compiled charter WITHOUT languages field]  (pre-existing projects, until first recompile under this change)
                                   |
                                   | charter generate / charter sync (post-change)
                                   v
[compiled charter WITH languages field]  <-- canonical runtime source from here on
```

**Runtime resolution invariant** (`infer_repo_languages` / its replacement):

1. If the compiled charter has a structured `languages` field → return it. This is authoritative; the interview transcript is never consulted once this exists, even if it disagrees.
2. Else (no structured field yet — pre-recompile projects) → fall back to today's extraction logic (interview transcript, then `charter.md` free-text as a secondary fallback), preserving current behavior for projects that have not yet recompiled under this change.

**Consumers (read-path only, no logic change expected)**:
- `src/charter/context.py:1320,1326` — `active_languages` population, feeding `_diagnose_catalog_miss`/`classify_scope_filtered_miss` (`context.py:2188-2207`).
- `src/charter/compact.py:195` — display-only footnote, wrapped in a defensive exception handler.

**Test contract change**: `tests/charter/test_language_scope.py::test_infer_repo_languages_prefers_interview_answers` — inverted to assert charter-authoritative resolution when interview and compiled charter disagree, plus a new case exercising the structured-field path directly.
