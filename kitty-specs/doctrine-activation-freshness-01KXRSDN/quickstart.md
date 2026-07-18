# Quickstart / Validation — Doctrine-activation freshness integrity

Manual + automated validation for the seam. Run from repo root; use `uv run` in lanes/clones.

## 0. Acceptance signal (IC-01, un-pin) — run first
```bash
spec-kitty doctrine regenerate-graph --check          # green after IC-01 regen
uv run pytest tests/doctrine/drg/migration/test_extractor_projection.py -q
uv run pytest -k "test_no_new_charter_reference_danglers or test_check_reports_committed_graph_fresh" -q
# the 4 formerly-@regression tests pass WITHOUT the marker
grep -rn "pytest.mark.regression" tests/doctrine tests/architectural   # → none of the 4 remain
```

## 1. Activation-visibility (IC-03; CT-01 / SC-002)
```bash
# On a fresh project with a fresh bundle+DRG:
spec-kitty charter activate directive <some-id>
spec-kitty charter status            # (or the freshness computation) → synthesized_drg = STALE
# reconcile:
spec-kitty charter generate && spec-kitty charter synthesize
spec-kitty charter status            # → FRESH
```
Automated: `uv run pytest tests/specify_cli/charter_runtime/ -k freshness_activation -q`

## 2. references.yaml fail-closed (IC-02; CT-02 / SC-003)
```bash
# Synced but not generated (references.yaml absent):
rm -f .kittify/charter/references.yaml
spec-kitty charter synthesize        # → fails closed: "run `spec-kitty charter generate` first"
#   (NOT a silent permanent-stale None)
```
Automated: `uv run pytest tests/charter/ -k "references_missing_preflight or bundle_complete_hash_stable" -q`

## 3. One-pass prerequisite gate (IC-04; CT-03 / SC-004)
```bash
# With several charter-owed prerequisites stale, the implement preflight lists them ALL at once:
spec-kitty agent action implement WP01 --mission <slug>   # preflight enumerates the full owed-set
```
Automated: `uv run pytest tests/specify_cli/charter_runtime/ -k preflight_one_pass -q`

## 4. Hot-path + --resynthesize (IC-05; CT-04 / NFR-001/003)
```bash
spec-kitty charter activate directive <id> --resynthesize   # signal FRESH immediately
spec-kitty charter activate directive <id>                  # signal STALE; zero synthesis subprocess
```
Automated: `uv run pytest tests/specify_cli/cli/commands/charter/ -k "resynthesize or activate_no_synthesis_subprocess" -q`

## 5. #2732 preserve (CT-06 / NFR-002)
```bash
uv run pytest tests/charter/ -k content_hash -q            # unchanged-bundle hash stable
```

## Full gate sweep (pre-handoff)
```bash
PWHEADLESS=1 uv run pytest tests/charter/ tests/specify_cli/charter_runtime/ tests/doctrine/drg/ tests/architectural/ -n auto --dist loadfile -q
ruff check src/charter src/specify_cli/charter_runtime
uv run mypy --strict src/charter src/specify_cli/charter_runtime
pytest tests/architectural/test_no_legacy_terminology.py     # if prose touched
```
