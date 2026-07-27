# Phase 1 Data Model

## OrgPackConfig (extended) — `src/doctrine/drg/org_pack_config.py`

Existing pydantic model (`extra="forbid"`, frozen=False). New field + derived accessor.

| Field | Type | Notes |
|-------|------|-------|
| `name` | `str` | non-empty (existing validator) |
| `local_path` | `Path` | tilde-expanded (existing); the clone/cache location |
| `source_type` | `"git"\|"https"\|"api"\|None` | existing |
| `url` | `str\|None` | existing |
| `ref` | `str\|None` | existing |
| **`subdir`** | **`str\|None`** | **NEW.** Relative POSIX path beneath `local_path`. `None`/`""`/`.` ≡ no subdir. |

**New validator (`subdir`, string-level, at model validation)**:
- Reject absolute paths (POSIX `/…`, Windows `C:\`, UNC).
- Reject any `..` component.
- Normalize `.`/empty → `None`.
- Failure raises a structured error that must surface to the operator (must NOT be downgraded to a warning by `load_pack_registry`).

**New accessor `effective_root(repo_root: Path) -> Path`** (the single seam, FR-001/C-007):
- Resolve `local_path` relative to `repo_root` when relative (retires the raw-vs-relative split).
- Join `subdir` when present.
- Symlink-containment check (`ensure_within_directory(effective, resolved_local_path)`) applied here, at resolution time (FR-003 symlink arm / NFR-002).

**Round-trip**:
- `_pack_to_yaml_dict`: emit `subdir` only when not `None` (FR-005 — no empty key).
- `_build_legacy_single_pack`: read `subdir` from the inline `doctrine.org` block (FR-006).

## Effective Pack Root (value object)

The path all consumers treat as the pack root. Computed only via `OrgPackConfig.effective_root`. Consumers that must adopt it (FR-004): `charter/drg.py`, `charter/pack_context.py`, `specify_cli/doctrine/org_charter.py`, `specify_cli/cli/commands/doctor.py` (`_build_pack_entries`), `charter/context.py`, `charter_runtime/lint/checks/org_layer.py`.

## Language Scope semantics (Thread D) — `src/doctrine/shared/scoping.py`

- `applies_to_languages` omitted ≡ always-applicable (unchanged).
- `[any]` / `[all]` are **rejected tokens** at `doctrine validate` (FR-012), not literal languages and not (canonically) wildcards.
- Diagnostic (`src/charter/_catalog_miss.py`): a referenced-but-scope-filtered artifact is reported as "present but scope-filtered", distinct from "missing/malformed" (FR-013).

## Tier Taxonomy (Thread C) — doctrine artifact, not a Python model

A `*.styleguide.yaml` declaring:
- **Tiers**: at least `core` and `glue` (names per the #1843 epic taxonomy; may extend), each mapped to **named existing `src/` areas**.
- **Per-tier rigour table**: coverage, duplication, smell, lint, typing expectations per tier.
- **DRG**: registered via generator; ≥1 inbound `suggests`/`requires` edge (non-orphan, FR-011).
- Explicitly **no** CI gate or agent-effort binding (C-001).
