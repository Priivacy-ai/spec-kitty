# Pre-Merge Review Squad — PR #3693

**Date:** 2026-08-23. **Branch:** `pr/doctrine-drg-silent-drop-boundary` (final PR state,
base upstream/main). **Squad (profile-loaded, read-only):** architect-alphonso (seams),
python-pedro (implementer correctness), reviewer-renata (anti-laziness + CI readiness).
Sharp question: is the branch merge-ready, esp. the two post-fidelity-audit commits no
prior squad reviewed (guard removal `f16193035d`, docs `b07288d7cb`).

## Convergent verdict: MERGE-READY (one trivial fix folded)

All three lenses independently confirmed the guard removal is sound (org-tier fail-loud
genuinely fires via edge-minting → `validate_dangling_references` → `DRGValidationError`
on both production paths; removed symbols fully gone; rewritten test drives the real
path), the `_drg_helpers` seam is correctly untouched, SSOT consistent, migration
idempotent/lossless, golden byte-fresh, no coupling with the 4 new upstream commits.

## Findings & dispositions

| # | Finding (lens) | Sev | Disposition |
|---|----------------|-----|-------------|
| P1 | **Net-new mypy --strict reexport error**: `executor.py` imported `load_org_pack` from the `charter.drg` facade, not in its `__all__` → `no_implicit_reexport` attr-defined. CI-advisory only (mypy step is `continue-on-error`), but violates DIR-006 and the PR body claimed "no new issues". (renata) | MED | **fixed** → commit `9b8a0ae8ad`: import `load_org_pack` from its true home `doctrine.drg.org_pack_loader` (no facade `__all__` change). mypy --strict now **0 errors** across src/specify_cli, src/charter, src/doctrine (full-package run; the earlier single-file "pre-existing no-any-return" and BaseMigration=Any artifacts do not appear on the full-package CI-equivalent run). PR body claim now accurate. |
| P2 | Migration doesn't migrate a `context-sources:` key whose **value is non-dict** (null/list/scalar); `extra="forbid"` still rejects it → would stay unloadable after upgrade with no signal. Unusual authoring shape. (python-pedro) | LOW | **noted** — follow-up candidate to make the lockstep guarantee airtight (treat any present `context-sources` key as removable). Not a blocker; no shipped profile has this shape. |
| P3 | Injected-graph path (`executor._graph`) is now wholly unvalidated for governance scope (the removed guard was its sole escalation). Test-only today (no production caller injects a graph); path never ran `assert_valid` even pre-PR. (architect) | LOW | **noted** — no production regression; flag if a future production caller injects a graph. |
| P4 | `topic_resolver.py:175 no-any-return` (architect) / migration `BaseMigration=Any` (pedro) | INFO | **not introduced** — pre-existing single-file mypy artifacts; full-package run is clean (0 errors after P1 fix). |
| P5 | CI-gate sweep: terminology, golden-count, shared-package-boundary, pyproject-shape, schema-drift (generate_schemas --check), DRG-regen freshness — all green (renata ran the CI-equivalent gates). | INFO | **confirmed** — no hard CI-gate risk. |

## Gate evidence (renata, CI-equivalent)

terminology 10 passed · golden-count + shared-package + pyproject-shape 17 passed ·
schema-drift exit 0 (not stale) · DRG regen/roundtrip 22 passed · 15 changed test files
618 passed/1 skipped · shipped-profiles 350 passed · charter facades 162 passed · ruff
clean · mypy --strict 0 errors (after P1).

## Net effect

One trivial fix commit (`9b8a0ae8ad`, P1). P2/P3 recorded as follow-up candidates,
not blockers. Branch is merge-ready pending the operator's merge; no hard CI-gate risk.
