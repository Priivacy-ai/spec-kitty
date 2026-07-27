# Quickstart — Verifying Mission-Type Doctrine Authority

How to confirm the mission's behaviour once implemented. All commands run in the
`spec-kitty-gate-doctrine` clone with `uv run` (clone isolation).

## 1. Non-software governance is correct (SC-001, FR-002)

Resolve governance for a documentation mission and confirm it contains documentation
doctrine and **no** software-dev-only doctrine:

```bash
uv run pytest tests/doctrine -k "mission_type_governance and (documentation or research or plan)" -q
uv run pytest tests/integration -k "non_software_governance" -q
```

Expect: each non-software type resolves its own doctrine; the software-dev-only
denylist is disjoint (non-leakage), and the non-vacuity twin proves software-dev
*does* resolve the denylist through a shared action name.

## 2. Software-dev is unchanged (SC-003, NFR-001)

While the transitional parity scaffold exists (before its removal):

```bash
uv run pytest tests/ -k "software_dev_parity" -q     # transitional; deleted before merge
```

Expect: resolved governance + resolved gate set for software-dev identical
before/after. After merge, the enduring check is behavioural (software-dev resolves
its known doctrine), not a byte snapshot.

## 3. Unknown type fails loudly; typeless degrades (SC-002, FR-003/FR-003a)

```bash
uv run pytest tests/doctrine -k "unknown_mission_type or mission_less_degrade" -q
```

Expect: an unrecognised *typed* mission raises a clear, remediable error on every
governance path; a typeless/mission-less caller degrades neutrally (never
software-dev).

## 4. Determinism (NFR-007)

```bash
uv run pytest tests/doctrine -k "resolved_governance_deterministic" -q
```

Expect: two resolutions of identical inputs render byte-identical.

## 5. Reduced specify_cli dependence (SC-005, NFR-004)

```bash
uv run spec-kitty doctor doctrine --json | python3 -c "import sys,json; print(json.load(sys.stdin).get('healthy'))"
grep -rl "specify_cli/missions/.*expected-artifacts" src/ || echo "no readers of the specify_cli gate copies"
```

Expect (when the detachable flip has landed): dossier reads the doctrine tree; no
readers of the `specify_cli` gate copies; those copies deleted. If the flip deferred
on deep drift, the reconciliation has still landed and the deferral is recorded.

## 6. Gates stay green

```bash
uv run ruff check .
PWHEADLESS=1 uv run pytest tests/architectural/ -q          # layer rules, terminology, non-leakage
uv run python -m mypy --strict src/charter src/doctrine     # (scope to changed modules)
uv run spec-kitty doctrine regenerate-graph --check         # DRG freshness after authoring
```
