# Quickstart — Verifying the Resolution & Activation Foundation

How a reviewer confirms the foundation is in place. All commands run through the clone-local CLI
with isolated state, and architectural checks run from the **primary checkout** (not a worktree).

```bash
# Shadow-clone preamble (every command)
export SPEC_KITTY_HOME="$PWD/.spec-kitty-home"
export PATH="$PWD/.venv/bin:$PATH"
```

## 1. One resolution door (C-R1 / SC-001)

```bash
# exactly one implementation body; home.py delegates
pytest tests/architectural -k "built_in_location or single_door" -q
grep -rn "def get_package_asset_root" src/          # expect ONE def in kernel/paths.py
grep -rn "def _find_relocated_missions_ancestor" src/  # expect ONE def
```

## 2. Missions honor SPEC_KITTY_PACKS_ROOT + precedence (C-R2/C-R3 / SC-002)

```bash
pytest tests/doctrine -k "missions_root and packs_env" -q     # the new regression (was missing)
# both-vars precedence case is included: PACKS_ROOT wins for missions
```

## 3. Activation authority, no implicit backfill (C-A1/C-A2 / NFR-001)

```bash
pytest tests/charter/test_pack_context.py tests/charter/test_mission_type_activation_gating.py -q
# absent key on a provisioned project -> provisioned set; authored [] -> empty; no all-four backfill site
```

## 4. Fresh-init provisioning + fail-closed (C-A3/C-A4 / SC-003)

```bash
# fresh init writes an explicit, non-empty mission_type_activations
tmp=$(mktemp -d); (cd "$tmp" && spec-kitty init --ai claude . >/dev/null 2>&1)
python -c "import yaml,sys; d=yaml.safe_load(open('$tmp/.kittify/config.yaml')); \
  a=d.get('mission_type_activations'); assert a, 'empty/absent activation set'; print('OK:', sorted(a))"
```

## 5. Behavior parity + scope fence (C-A6/C-S1 / SC-004/SC-005)

```bash
pytest tests/architectural -k "terminology or layer" -q      # NFR-002/NFR-005
# scope-fence: mission-type still not an ArtifactKind; availability readers unchanged
python -c "from doctrine.artifact_kinds import ArtifactKind, MissionTypeNotAnArtifactKind; \
  import pytest; \
  ok=False; \
  \nfrom doctrine import artifact_kinds; print('MissionTypeNotAnArtifactKind present:', bool(MissionTypeNotAnArtifactKind))"
```

## 6. Full gate sweep (from the primary checkout)

```bash
pytest tests/architectural/ -q                 # layer rules, terminology, built-in-location authority
ruff check . && mypy src/                       # zero issues, zero new suppressions
```

**Done** when: one door, missions relocate via PACKS_ROOT (new test green), no implicit backfill,
fresh-init provisions explicitly, provisioned-project behavior is unchanged, and the scope-fence
guards prove the kind-promotion / availability-reader work was NOT touched.
