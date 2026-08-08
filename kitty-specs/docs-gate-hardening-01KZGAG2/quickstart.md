# Phase 1 Quickstart: Docs Quality Gate Hardening

Run the gates and verify the red-first evidence locally (clone-local venv).

## Run the gates

```bash
# GATE-1 — slash-command reference vs registry (after IC-01 lands)
.venv/bin/python scripts/docs/check_slash_command_freshness.py

# GATE-2 — published-page resolver (per-glob non-vacuity)
.venv/bin/python -c "from scripts.docs._published_pages import resolve_published_pages; from pathlib import Path; print(len(resolve_published_pages(docs_root=Path('docs'))))"

# GATE-3 + targeted tests
.venv/bin/pytest tests/docs/test_check_slash_command_freshness.py \
                 tests/docs/test_published_pages.py \
                 tests/docs/test_description_length_check_propagation.py \
                 tests/docs/test_related_validator.py \
                 tests/docs/test_docs_freshness_invariant.py -q
```

## Verify red-first (C-006)

- **FR-002 (backfill)**: on the base branch the doc is 12/15, so GATE-1's test is genuinely RED before backfill; GREEN after. Capture the base-branch failing run.
- **FR-001/FR-003/FR-005 (new gate + test together)**: the negative test imports gate code that does not exist on base (import error, not a clean assertion RED). Land the test in a first commit against a demonstrable gap, or capture the failing run, then add the gate — record the evidence in the WP.

## Guardrails

- Targeted test surface only (per charter Testing Requirements): `tests/docs/`. Do NOT run the full suite (~1h) in-session.
- `ruff check scripts/docs/ tests/docs/` and `mypy` must be clean; keep new/changed functions ≤15 complexity.
- Terminology guard before pushing doc/prose changes: `.venv/bin/pytest tests/architectural/test_no_legacy_terminology.py`.
