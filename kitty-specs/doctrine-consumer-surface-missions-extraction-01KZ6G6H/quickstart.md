# Quickstart: Verifying This Mission's Deliverables

How a maintainer verifies each Success Criterion locally, once implementation lands. All commands run from the repository root, `PYTHONPATH=src` per this repo's convention.

## SC-001 — `missions/` relocated

```bash
test ! -d src/doctrine/missions && echo "OK: old location gone"
test -d packs/built-in/missions && echo "OK: new location exists"
# Editable-checkout resolution:
PYTHONPATH=src python -c "from kernel.paths import get_package_asset_root; print(get_package_asset_root())"
# Installed-wheel resolution (build + install into a scratch venv, then re-run the same import):
python -m build --wheel -o /tmp/dist . && python -m venv /tmp/scratch-venv && /tmp/scratch-venv/bin/pip install /tmp/dist/*.whl && /tmp/scratch-venv/bin/python -c "from kernel.paths import get_package_asset_root; print(get_package_asset_root())"
```

## SC-002 — Kernel holds no doctrine/specify_cli string; new gate proves it

```bash
grep -n "doctrine\|specify_cli\|software-dev" src/kernel/paths.py  # expect: no match (or only in comments explaining WHY it was removed)
PYTHONPATH=src python -m pytest tests/architectural/test_kernel_*.py -q  # name TBD by implementer
```

## SC-003 — `UnknownMissionTypeError` message fixed

```bash
# NOTE: the existing test_unknown_type_raises_unknown_mission_type_error does NOT
# exercise this defect (it only covers an id absent from existing_mission_types()).
# A new reproduction test for the actual activated-but-unresolvable-profile scenario
# must exist first (red), then pass after the fix:
PYTHONPATH=src python -m pytest tests/charter/test_mission_type_profiles.py -k activated_but_unresolvable -q
```

## SC-004 — TIER-1 override templates refreshed

```bash
grep -n "constitution context\|AgentProfileRepository(\|DoctrineService(" .kittify/overrides/missions/software-dev/command-templates/implement.md .kittify/overrides/missions/software-dev/command-templates/review.md
# expect: no match
```

## SC-005 / SC-006 — Gate split + fixture decoupling

```bash
PYTHONPATH=src python -m pytest tests/architectural/ -k "dead_doctrine or dead_cli or forbidding_mention or cross_link" -q
# Remove the live daphne-profile repo-local reference (current path, post relocation)
# and confirm the suite is still green:
git stash -- packs/built-in/agent_profiles/doctrine-daphne.agent.yaml  # or manual edit
PYTHONPATH=src python -m pytest tests/architectural/ -k "forbidding_mention" -q  # expect: pass, not fail
```

## SC-007 — Reader inventory committed

```bash
# Confirm the inventory artifact exists, every row has a decision + rationale, AND
# specifically includes MissionTemplateRepository.default_missions_root() and the
# DRG extractor's _missions_root() by name (both already identified pre-implementation).
test -f kitty-specs/doctrine-consumer-surface-missions-extraction-01KZ6G6H/research.md  # or wherever FR-003 lands it
grep -l "default_missions_root\|_missions_root" kitty-specs/doctrine-consumer-surface-missions-extraction-01KZ6G6H/research.md
```

## SC-008 — DRG fragments regenerated

```bash
PYTHONPATH=src python -m pytest tests/doctrine/drg/test_regen_roundtrip.py -q
```

## Full regression sweep (NFR-001, NFR-002, NFR-003, NFR-004)

```bash
PYTHONPATH=src python -m pytest tests/charter tests/doctrine tests/architectural tests/kernel -q
```
