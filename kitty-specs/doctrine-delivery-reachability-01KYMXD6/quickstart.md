# Quickstart — Doctrine Delivery Reachability

**Mission**: `doctrine-delivery-reachability-01KYMXD6` | **Date**: 2026-07-28

How to reproduce the defects, run the right gates, and avoid the traps that cost the discovery pass
several wrong numbers.

---

## Reproduce the defects before changing anything

Per C-006 every requirement lands red-first. These are the reproductions.

### The steady-state zero

```bash
# The first load is rich; every load after is empty.
rm -f .kittify/charter/context-state.json          # simulate a fresh project
spec-kitty charter context --action implement --mission-type software-dev --json \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['mode'], d['first_load'], len(d['text']))"
# expect: bootstrap True ~31000

spec-kitty charter context --action implement --mission-type software-dev --json \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['mode'], d['first_load'], len(d['text']))"
# expect: compact False ~6000
```

**There is no `--depth` flag.** Depth is inferred from first-load state. This is why the original
assessment measured zero and concluded activation was inert — it was reading the compact rail.

### Styleguides and toolguides resolved, then dropped

```bash
PYTHONPATH=src python3 - <<'PY'
# the bundle resolves them; the render emits none of them
PY
```
Compare `styleguide_ids` / `toolguide_ids` on the resolved bundle against literal id occurrences in
the rendered text. Expect non-empty resolution and zero occurrences.

### The unguarded writer

```bash
# Break project_drg._serialize_graph (drop a field), then:
PWHEADLESS=1 pytest tests/charter/synthesizer/test_project_drg.py -q
# expect: 23 passed — identical to baseline. Nothing pins it.
```

### The reference cap

```bash
# Change BOTH [:10] sites in src/charter/activation/context.py to [:1], then:
PWHEADLESS=1 pytest tests/charter/test_context.py tests/charter/test_compact.py -q
# expect: unchanged counts. No test pins the cap.
```

---

## Measure reachability correctly

**Call `resolve_context`. Do not reimplement the walk.** Four independent lenses produced four
different unreachability numbers (91 / 88 / 78 / 59) precisely because each wrote its own BFS.

`resolve_context` walks `scope` at depth 1, then `requires` transitively **from directly-scoped
artefacts only**, then `suggests` capped at depth. It never follows `instantiates`. Any hand-rolled
`{scope, requires, suggests, instantiates}` traversal will disagree with it.

Two named sets, both required:

| set | depth | why |
|---|---|---|
| compact | `d=1` | the steady state — what every agent gets after first load, and the stricter measure |
| bootstrap | `d=2` | what the action-doctrine bundle calls |

Seeds are **action nodes and activated agent profiles** (D2).

---

## Run the right tests

```bash
# Parallel, per CLAUDE.md
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider

# Named gate files for this mission — NOT the full architectural suite
PWHEADLESS=1 pytest \
  tests/doctrine/drg/migration/test_extractor_projection.py \
  tests/doctrine/drg/test_model_strictness_roundtrip.py \
  tests/doctrine/drg/test_kind_mapping_totality.py \
  tests/architectural/test_layer_rules.py \
  tests/architectural/test_runtime_charter_doctrine_boundary.py -q

# Before pushing anything under src/doctrine/ or user-facing prose (~0.1s, CI-only gate otherwise)
pytest tests/architectural/test_no_legacy_terminology.py
```

**Baseline-red discipline.** A broad run shows red that is not yours. Classify before fixing:
known-P0 reds on main, CI-environment failures (auth, sync toggles), and stale-install false reds
(`pip install -e .` after touching anything that shells out to `spec-kitty`). Confirm against the
merge-base before folding a failure into your work.

**Baseline for this mission** (all green at `ed470756e`): `test_extractor_projection.py` +
`test_runtime_charter_doctrine_boundary.py` → 10 passed; `test_template_asset_e2e.py` +
`test_extractor_asset.py` + `test_artifact_kinds.py` → 50 passed; `test_docs_structural_lint.py` →
29 passed; `test_layer_rules.py` → 17 passed.

---

## Verify the asset path the way SC-003 requires

In-repo verification **cannot fail** — `resolve_doctrine_root()` falls back to the dev layout. The
criterion needs a built wheel in a clean environment with the repository root absent from resolution
inputs:

```bash
uv build --wheel
python3 -m venv /tmp/sc003 && /tmp/sc003/bin/pip install dist/spec_kitty_cli-*.whl
cd /tmp && /tmp/sc003/bin/spec-kitty doctrine asset path common-docs-structural-lint
```

---

## Traps that already cost time

| Trap | What happens |
|---|---|
| **`charter_file:`** | Does not exist. The pointer is **`charter:`** and already ships. Introducing the other name mints a competing pointer — the defect FR-017 removes |
| **Deleting the mirror first** | `_charter_activated_urns` reads `config.yaml`'s `activated_*`. Delete it before repointing and the gate's floor assertion fails while its stray guard goes **vacuously true** |
| **Fixing `resolver.py` alone** | Changes nothing observable. `_render_text` never reads those four fields; the drop is in `_render_bootstrap_text` |
| **Trusting `rewrite_opposed_by` is unguarded** | It is guarded (`test_model_strictness_roundtrip.py:520/557`) and goes red when B1 lands. `project_drg` is the unguarded one |
| **Adding `asset` to some kind maps** | Two of the four `_PROJECT_KIND_DIRS` copies are *exempted from the totality guard*, so a partial fix goes green and the scaffold writes where the resolver never reads |
| **Non-recursive overlay glob** | `BaseDoctrineRepository._project_scan` uses `glob`, not `rglob`. Org-pack assets at the ADR-mandated nested path are never discovered |
| **Anchor asymmetry** | Built-in blob paths anchor at the *parent* of `assets/built-in`; org/project anchor at the dir. One shared rule yields `.../built-in/built-in/...` |
| **Counting id normalization as progress** | Normalizing the directive id form swings the unreachable count ~20 with zero reachability change. C-009 excludes it from SC-005 |
| **Line numbers from the discovery docs** | Four anchors in the fix-sizing table drifted. Function names are correct — **grep by symbol** |

---

## Landing order

**IC-01 first and alone.** It is the B1 unblock and must carry no inbound dependency (C-005). Land it
even if everything else takes review rounds.

Then: IC-02 and IC-04 (independent) → IC-03 (needs IC-02) and IC-05 (needs IC-04) → IC-06 (needs
IC-04, IC-05) → IC-07 and IC-08 (need IC-06) → IC-09 (needs IC-03, IC-05).

**C-005's limit:** the independence is a *build-order* claim only. Once IC-06 lands, the project-tier
graph is merged into the graph every agent's context traverses, so IC-01's tests must cover the
merged-graph **read** path, not only the write path.
