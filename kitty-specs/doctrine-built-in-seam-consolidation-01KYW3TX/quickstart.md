# Quickstart — Verify the Built-In Doctrine Seam

How to verify each contract locally. Run from the repo root on
`feat/relocate-builtin-doctrine-packs`. Use `uv run` (lane/clone `python` imports the wrong src).

## 1. The seam resolves fail-closed (C1)

```bash
uv run python -c "
from doctrine.pack_paths import built_in_dir, PackRootNotFound
from doctrine.artifact_kinds import ArtifactKind
p = built_in_dir(ArtifactKind.DIRECTIVE)
print('directives ->', p); assert p.name == 'directives' and 'packs/built-in' in str(p)
try:
    built_in_dir(ArtifactKind.MISSION_STEP_CONTRACT); raise SystemExit('carve-out did NOT raise')
except Exception as e:
    print('carve-out raises OK:', type(e).__name__)
"
```

## 2. Graph identity is unchanged (NFR-001 / SC-004)

```bash
# The relocation baseline already pins 324 nodes / 892 edges:
PWHEADLESS=1 uv run pytest -p no:cacheprovider -q \
  tests/doctrine/test_pack_relocation_identity.py \
  tests/doctrine/test_pack_relocation_preflight.py
```

## 3. The 7 owned reds pass (FR-007/008)

```bash
PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 uv run pytest -p no:cacheprovider -q \
  tests/glossary/test_gate_terms.py \
  tests/integration/test_org_pack_artifact_lifecycle.py::test_case_2_org_styleguide_collision_with_builtin_warns \
  tests/doctrine/test_profile_inheritance.py
```

## 4. The anti-regression ratchet bites (NFR-002/003)

```bash
# The new gate (path TBD in IC-04); it must FAIL when a non-pack_paths module
# joins resolve_pack_root("built-in"), and PASS on the consolidated tree.
PWHEADLESS=1 uv run pytest -p no:cacheprovider -q tests/architectural/ -k "built_in or pack_root or seam"
```

## 5. Vocabulary set-equality + drift fix (FR-010 / SC-005)

```bash
uv run python -c "
from charter.pack_manager import YAML_KEY_MAP
from charter.charter_yaml_io import _ACTIVATION_KEYS
# after IC-05, the finalize migration constant must include activated_glossary_packs
print('glossary in vocab:', 'activated_glossary_packs' in set(YAML_KEY_MAP.values()))
"
# plus the set-equality guard test added in IC-05.
```

## 6. Full gate sweep before hand-off

```bash
uv run ruff check .
PWHEADLESS=1 uv run pytest -p no:cacheprovider -q tests/architectural/test_no_legacy_terminology.py
# CI owns the full tests/architectural/ sweep; run targeted node-ids locally.
```
