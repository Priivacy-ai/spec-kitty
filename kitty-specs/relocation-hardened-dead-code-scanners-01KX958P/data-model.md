# Data Model: Relocation-Hardened Dead-Code Scanners

Test-infra "entities" — in-memory value objects the key + gate operate on. No storage.

## SymbolKey (value object)

The relocation-tolerant identity produced by `_symbol_key.py`.

| Field | Type | Notes |
|-------|------|-------|
| `bare_name` | `str` | the symbol's unqualified name (e.g. `ArtifactKind`) |
| `body_hash` | `str` | hash of `anchoring.code_tokens_by_line` over the definition span (interpreter-independent) |
| `module_path` | `str \| None` | present ONLY for collision-tier keys (≥2 live locations); `None` for content-tier |
| `tier` | `"content" \| "module_path"` | derived; recomputed live per run (D-2) |

- **Invariant**: a content-tier key (`module_path is None`) MUST resolve to exactly one
  live `__all__` location. Resolving to 0 → dangling (prune, D-4). Resolving to ≥2 →
  **fail-closed** or escalated to module_path tier (D-3).
- **Undecidable**: the resolver returns `None` (not a `SymbolKey`) for a shape it cannot
  span → fail-closed at load (FR-009). No silent exemption.
- **Body-sensitivity**: editing the definition body changes `body_hash` → the key no
  longer matches → exactly one signal (offender-refresh), reconciled with dangling (D-4).

## AllowlistEntry

A hand-curated sanctioned dead symbol, re-keyed off `module::Name`.

| Field | Type | Notes |
|-------|------|-------|
| `key` | `SymbolKey` | replaces the old `module::Name` string |
| `rationale` | `str` | preserved from the existing category frozenset context |
| `category` | `str` | one of the 19 category frozensets (e.g. `GRANDFATHERED_LEGACY`) |

- **Population**: 394 live (across 19 frozensets); 2 stale dropped (FR-006:
  `charter_activate_app` / `charter_deactivate_app`).
- **Keyability invariant** (DoD k): all 394 resolve to a `SymbolKey` (0 un-keyable).

## CollisionSet (recomputed, not stored)

The `bare_name`s whose content resolves to ≥2 live locations — **rebuilt every gate run**
(D-2). Today's set = the ArtifactKind trio (+ any future byte-identical same-name pair).
Members are denied relocation tolerance (module_path tier or fail-close).

## DanglingEntry (transient, ratchet input)

An allow-list entry whose `SymbolKey` no longer resolves to a live `__all__` declaration.
Tier-specific detection (D-4):

| Tier | Dangling test |
|------|---------------|
| content | `(bare_name, body_hash)` → 0 live locations |
| module_path | `(bare_name, module_path)` → no live `__all__` decl |

→ pruned by the third ratchet direction (FR-008).

## AutoExemptCategory (symbol-granular, FR-010)

Auto-derived exemptions, computed per-symbol (never per-module):

| Category | Rule |
|----------|------|
| registered migration | `@MigrationRegistry.register`-decorated **class only** (~96 `m_*.py`; dead helpers still caught) |
| re-export shim | by definition-shape (docstring/`__all__`-only re-export) |
| Typer sub-app | by call/decorator parse |

- **Invariant** (disjointness meta-test): `auto_exempt ∩ hand_allowlist = ∅`.

## Preserved surfaces (byte-unchanged — C-005/FR-012)

Not modified; listed so ownership treats them as read-only:
`known_modules`, `_record_*_edges`, `_imports_by_target` (caller-graph / anti-re-blind),
the 4 T004 dynamic-dispatch detectors, test-not-caller semantics, the bidirectional
stale-entry ratchet + its 4 T004 tests.
