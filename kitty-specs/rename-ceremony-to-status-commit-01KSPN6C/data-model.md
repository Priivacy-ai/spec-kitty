# Phase 1 Data Model: Rename Ceremony Commit to Status Commit

**Mission**: `rename-ceremony-to-status-commit-01KSPN6C`
**Date**: 2026-05-28

A terminology rename has no runtime data model. The "entities" are the glossary terms themselves. This file defines those terms and the relationships among them, so the glossary YAML edit and the regression-guard test have a single source of truth.

---

## Term Entities

### Canonical

| Field | Value |
|---|---|
| `surface` | `status commit` |
| `definition` | An auto-commit created by spec-kitty to record workflow state changes (task status transitions, lane metadata, WP claims). Status commits target lane branches, not protected branches. |
| `status` | `active` |
| `confidence` | `0.95` |
| `synonyms_to_avoid` | `[ceremony commit, ceremony, ceremony write, status-writing operation, status-writing command]` |

### Deprecated 1

| Field | Value |
|---|---|
| `surface` | `ceremony commit` |
| `definition` | "DEPRECATED. Replaced by `status commit`. This term obscures intent and is forbidden in active source. See the canonical `status commit` entry." |
| `status` | `deprecated` |
| `confidence` | `1.0` |

### Deprecated 2

| Field | Value |
|---|---|
| `surface` | `status-writing operation` |
| `definition` | "DEPRECATED. Replaced by `status commit`. This phrasing landed during a partial rename; it is forbidden in active source. See the canonical `status commit` entry." |
| `status` | `deprecated` |
| `confidence` | `1.0` |

---

## Relationships

```
status commit (canonical)
  ▲
  │ resolves_to
  │
  ├── ceremony commit (deprecated)         — also covers "ceremony", "ceremony write", "ceremony command"
  └── status-writing operation (deprecated) — also covers "status-writing command"
```

Term-resolution invariants:

1. Exactly one entry in `.kittify/glossaries/spec_kitty_core.yaml` has `surface: "status commit"` with `status: active`.
2. Both deprecated entries exist with `status: deprecated` and a definition that names `status commit` as the replacement.
3. No active-source file (under `src/`, `tests/`, `docs/`) contains the literal strings `ceremony` or `status-writing` (case-insensitive). `kitty-specs/` historical artifacts are explicitly out of scope of this invariant.

---

## State Transitions

None. A terminology rename is not a state machine.

---

## Validation Rules

The architectural test `tests/architectural/test_no_legacy_terminology.py` enforces invariant #3 at CI time. The glossary file structure is validated by the existing glossary loader (no schema change introduced).

---

## External Visibility

- **User-facing error message**: the protected-branch guard's error string is the only runtime user-visible artifact affected. Pre-rename: `"Run status-writing operations from the mission lane branch/worktree."` Post-rename: `"Run status commit operations from the mission lane branch/worktree."`
- **Doctrine readers**: contributors reading doctrine, skills, and engineering notes encounter the canonical term consistently.
- **Future term-checkers**: any tool that loads `.kittify/glossaries/spec_kitty_core.yaml` can detect a regression on either deprecated term by surface key.
