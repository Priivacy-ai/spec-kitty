# Quickstart — expected-artifacts-loader-unification

How to witness the bug, run the gates, and verify the fix.

## 1. Witness the #3412 launder RED on upstream/main (before fix)

The failure is an org-tier YAML-syntax fault for a CUSTOM family, laundered into a
green guard. The repro constructs an ACTUAL broken YAML (not a typo'd key):

```
# In a tmp org root: missions/<custom-family>/expected-artifacts.yaml
required_always:
  - path_pattern: "spec.md
    # ^ unterminated quote / bad indent — a real ruamel.yaml YAMLError
```

Drive it through the real composed-action guard entry point (`repo_root` threaded
at `runtime_bridge_composition.py:637-638`). On `upstream/main`:
- Expected (buggy) today: guard returns `[]` (silent green).
- After fix: raises `MalformedManifestError` naming the file + parse error.

Note: the built-in-tier equivalent already fails loud (`1763bf2ae3`) — do NOT
write the red-first repro against a broken built-in manifest; it would be GREEN.

## 2. Run the behavioral tests

```bash
# org fail-loud + non-mapping + unreadable (both tiers)
PWHEADLESS=1 .venv/bin/python -m pytest tests/charter/ tests/dossier/test_manifest.py -q
# launder-seam propagation through the composed guard
PWHEADLESS=1 .venv/bin/python -m pytest tests/runtime/ -k "malformed or launder or composed_guard" -q
```

## 3. Run the structural gates

```bash
# bare model_validate / bare construction arch-gate (non-vacuous)
PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/ -k "expected_artifact or model_validate" -q
# shim re-export surface (old-path imports still resolve, same object identity)
PWHEADLESS=1 .venv/bin/python -m pytest tests/dossier/test_manifest.py -k "reexport or shim" -q
# cache characterization via delegate (NFR-002)
PWHEADLESS=1 .venv/bin/python -m pytest tests/dossier/test_manifest.py -k "OrgTier or cache" -q
```

## 4. Full-sweep verify (pre-handoff)

```bash
# terminology + arch shards (some run only in CI's integration job)
PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/ -q
ruff check src/charter src/specify_cli src/runtime
mypy src/charter/activation/manifest_loader.py src/specify_cli/dossier/manifest.py
```

## 5. Consolidation checklist (before the DRAFT PR)

- [ ] exactly ONE `model_validate` load implementation (grep proof)
- [ ] `from_yaml_file` gone; its 3 tests migrated
- [ ] shim re-exports the 4 names with object identity
- [ ] `composition.py:504` pinned to `UnregisteredMissionFamilyError` only
- [ ] ADR for the relocation committed (C-005)
- [ ] stale `load_manifest` docstring corrected (FR-014)
- [ ] CHANGELOG entry; version bump only if `__init__.py` touched
