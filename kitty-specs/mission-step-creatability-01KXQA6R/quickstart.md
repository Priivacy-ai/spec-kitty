# Quickstart / Validation — Mission-Type Creatability (S-C)

Manual + automated validation scenarios proving the mission's outcomes. Run from repo root with `uv run` (lane clones import primary `src/` on bare `python`).

## 1. Creatability (SC-001, the #2689 fix)
```bash
# Each must succeed (today they hard-fail with TemplateConfigurationError):
for t in documentation research plan; do
  spec-kitty agent mission create "qs-$t" --mission-type "$t" --json | python3 -c "import sys,json;print('$t', json.load(sys.stdin).get('result'))"
done
# Then advance one to /plan setup to exercise the "plan" artifact_kind.
```

## 2. Behavior preservation (SC-005, NFR-001)
```bash
# software-dev template resolution unchanged; --json key order canonicalizes to sequence_index order.
uv run pytest tests/doctrine/missions/test_softwaredev_roundtrip.py -q      # TestSoftwareDevProjectionParity green
uv run python -c "from doctrine.missions.mission_type_repository import MissionTypeRepository as R; print(R.default().get('software-dev') is not None)"
```

## 3. Split-brain closed (SC-002)
```bash
# A mission_types/*.yaml (or pack) authoring `template_set:` must FAIL LOUD (ValidationError), not be honored/dropped.
uv run pytest -q -k "pack_template_set_fails_loudly or template_set_forbidden"
```

## 4. Genuine content (SC-003)
```bash
uv run pytest tests/doctrine/missions/test_prompt_emptiness.py -q   # scaffold retired → positive non-empty assertion
# Substance is a reviewer-checklist gate (NFR-004), verified in review, not by the detector.
```

## 5. Graph-backed chain (SC-004)
```bash
spec-kitty doctrine regenerate-graph --check          # freshness green
uv run pytest tests/doctrine/drg/ tests/doctrine/drg/migration/test_extractor_projection.py -q
# Asserts: 280+N nodes / 757+N edges / orphans=10; positive instantiates-edge assertion; by-URN==by-name + override-wins.
```

## 6. Gates
```bash
uv run ruff check .
uv run mypy --strict src/
uv run pytest tests/architectural/test_no_legacy_terminology.py -q
```

## Definition of Done (mission)
All of §1-§6 green + the `traces/verification.md` ledger fully ticked + `research/plan` scaffolds authored (not placeholder) + `#2751` remains the sole deferred item.
