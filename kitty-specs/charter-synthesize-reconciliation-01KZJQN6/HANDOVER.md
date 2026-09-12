# Handover — Charter Synthesize Reconciliation

**Mission**: `charter-synthesize-reconciliation-01KZJQN6` (mid8 `01KZJQN6`), software-dev.
**Branch**: `fix/charter-synthesize-reconciliation` (based on `upstream/main`, pushed to
`origin` = `stijn-dejongh/spec-kitty`). PRs into `main`.
**Issues**: #3270 (P0), folds #2777, #3052. Epic #2519. Milestone 3.2.x.

## State at handover

Planning is **complete and pushed**; **no implementation code written yet**.

- ✅ Triage applied on #3270 (Bug / P0 / milestone 3.2.x / parented under #2519).
- ✅ Red-first reproduction committed and failing:
  `tests/charter/synthesizer/test_synthesize_node_preservation.py` (node + edge preservation).
- ✅ `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/synthesize-seam.md`,
  `quickstart.md`, `tasks.md` + 7 WP prompts committed.
- ✅ Two adversarial squads run: **post-spec** (flipped the default to preserve-and-warn,
  re-anchored the ADR, added the manifest/conflict/heal FRs) and **post-tasks** (folded as
  "🔴 Post-tasks squad amendments" in the WP prompts — READ THEM).

## The confirmed contract (do not re-litigate)

**Preserve-and-warn** (ledger `01KZJV6H7TW63M6ZGNM05XKM2S`, supersedes the earlier
refuse-with-prune choice). Library seam `orchestrator.synthesize` preserves-and-succeeds
(reconciles, drops nothing, exit 0, returns a delta); `--prune` (CLI) removes; non-zero refusal
only for unpreservable cases (orphaned removal without `--prune`; unparseable overlay).
Doctrine anchor: ADR `2026-07-26-3` + `src/doctrine/drg/merge.py` conflict model (warn/report).

## Work packages & order

```
WP01 (foundation) ──┬── WP02 ── WP03 ── WP04 ── WP06 (#2777 fold, P2)
                    ├── WP05
                    └── WP07 (#3052 fold, P2)
```
Spine WP01–WP05 (P0) is independently landable from folds WP06–WP07 (P2). Start at **WP01** (the
MVP: it turns the committed red test green). All WPs assigned profile `python-pedro`/implementer/claude.

## Three blockers the implementer MUST heed (from the post-tasks squad)

1. **WP01**: drive the FR-009 post-condition (`apply_post_condition(has_project_graph=…)`) from the
   **merged** graph, not the fresh emit — else an empty/subset target set re-unlinks the preserved
   `graph.yaml` (the original P0 re-armed).
2. **WP01**: corrupt/unparseable on-disk overlay must fail closed **at the library seam** (not only
   the CLI) — the in-process `activate`/`deactivate` path bypasses the CLI.
3. **WP01→WP02 interface**: WP01 detects+classifies conflicts and populates `delta.conflicts`
   **in memory** on the returned `ReconciliationDelta`; WP02 widens `validate()` to take those
   classified conflicts and make only the suppress-vs-raise decision (no `validate_graph`
   string-parsing, no on-disk sidecar). The `duplicate_triple` / `preserved_dangling_endpoint`
   remediation vocab lives in `reconcile.py`, not `merge.py`.

## How to start implementing

```bash
# On this machine or a fresh clone:
git fetch origin && git checkout fix/charter-synthesize-reconciliation
pip install -e .          # editable install so `spec-kitty` reflects the branch

# REQUIRED gate before any WP: persists analysis-report.md (implement refuses without it)
/spec-kitty.analyze --mission charter-synthesize-reconciliation-01KZJQN6

# Then drive the loop (creates the per-lane worktree):
spec-kitty next --agent claude --mission charter-synthesize-reconciliation-01KZJQN6
#   → spec-kitty agent action implement WP01 --agent claude   (and so on per lane/deps)
```

## Environment / gotchas

- Tests: `PYTHONPATH=src PWHEADLESS=1 pytest tests/charter/ -n auto --dist loadfile -p no:cacheprovider`.
  The `FixtureAdapter` is inputs-hash-keyed — new synthesize scenarios need recorded fixtures.
- Gates: `ruff check . && mypy src/charter src/specify_cli/charter_runtime`; complexity ≤ 15; no new
  suppressions. Run `pytest tests/architectural/test_no_legacy_terminology.py` on doctrine/prose touches.
- A stale install reports false reds for `spec-kitty`-shelling code until `pip install -e .`.

## Local-only notes (do NOT travel to a clone)

- An unrelated `hardening/verdict-seam-facade-followup` change was parked in `git stash` on the
  origin machine during setup and has been restored there; a clone is unaffected.
- A scratch worktree `.worktrees/issue-3270-triage` (branch `fix/3270-...`) was used for analysis and
  is redundant (its test was cherry-picked here); safe to remove.
