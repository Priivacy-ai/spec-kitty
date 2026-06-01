# Contracts Index

Behavioral/interface contracts for the mission. This is a CLI + library mission (no HTTP API), so contracts are expressed as **testable Given/When/Then assertions** against module interfaces and CLI surfaces. Each contract maps to FRs and a WP wave. ATDD-first (charter C-011): these contracts become acceptance/contract tests authored before implementation.

| File | Wave | Covers (FRs) |
|------|------|--------------|
| [wave0-foundation.md](wave0-foundation.md) | 0 | kind/ID resolver (FR-027), `SPECIALIZES_FROM` + silent-drop (FR-001/002/003), merge relocation + layer rule (C-009/OQ-2-ii) |
| [wave1-diagnostics.md](wave1-diagnostics.md) | 1 | profile diagnostics (FR-005..007, NFR-002/005), doctor health report (FR-008..010, NFR-001), dead-symbol wiring (FR-035/036/020) |
| [wave2-authoring-migration.md](wave2-authoring-migration.md) | 2 | fragment-authoring validation (FR-028/029), augmentation single-source + parity (FR-030/031/032), field-retirement migration (NFR-007), lineage via DRG (FR-002/004) |
| [wave3-activation.md](wave3-activation.md) | 3 | plan/commit non-mutation (FR-011/012, NFR-003), cascade scope (FR-013/014), shared-reference deactivation (FR-015/016, C-005) |
| [wave4-runtime-catalog.md](wave4-runtime-catalog.md) | 4 | OperationalContext (FR-017..020, C-006, NFR-004), `list --all` + `--include` (FR-022..026), templates (FR-033/034) |

## Cross-cutting contracts (apply to every WP)

- **CC-1 Layer rule**: no `import` from a higher layer (`kernel ← doctrine ← charter ← specify_cli`). `tests/architectural/test_layer_rules.py` passes; specifically `doctrine` imports neither `charter` nor `specify_cli` after the merge relocation.
- **CC-2 Quality gate** (`DIRECTIVE_030`): `ruff check .`, `mypy`, and `pytest` pass per WP.
- **CC-3 ATDD** (C-011): an acceptance/contract test exists and fails before the implementation WP, passes after.
- **CC-4 Canonical kinds** (I-K1): no module re-declares the kind set; all derive from `ArtifactKind` + `from_operator_token`.
- **CC-5 Bulk-edit gate** (`DIRECTIVE_035`): WPs in the field-retirement surface comply with `occurrence_map.yaml`; `implement` refuses an unclassified occurrence.
