# Contract — Built-In Location Authority & Anti-Regression Ratchet

Behavioural contract for the seam (`built_in_dir`) and the CI gate. Written as
assertions the implementation and its tests must satisfy.

## C1 — `built_in_dir(kind)` resolution

| # | Given | When | Then |
|---|-------|------|------|
| C1.1 | any shipped built-in kind K (≠ carve-out) | `built_in_dir(K)` | returns `resolve_pack_root("built-in") / K.plural`, a path inside `packs/built-in/<plural>/` |
| C1.2 | the pack root is locatable | `built_in_dir(K)` then load | loads the same artefacts production loads today (graph identity unchanged) |
| C1.3 | the pack root cannot be located | `resolve_pack_root("built-in")` | raises `PackRootNotFound` — no empty-set substitute |
| C1.4 | K ∈ the derived complement `{MISSION_STEP_CONTRACT, TEMPLATE, ANTI_PATTERN}` (the kinds with NO `packs/built-in/<plural>/` content dir) | `built_in_dir(K)` | raises a named error (no silent path to a non-existent dir); the set is DERIVED from "has a content dir", not hand-listed |
| C1.5 | a test needs a synthetic tier | set `SPEC_KITTY_PACKS_ROOT=<tmp>` | `resolve_pack_root("built-in")` resolves under `<tmp>`; no nested-path param needed |
| C1.6 | a caller needs the built-in ROOT (not a kind dir) — DRG loader/extractor, reference-pointer walk, `doctrine regenerate-graph` | `built_in_root()` | returns `resolve_pack_root("built-in")`; these route through the seam, not a bare `resolve_pack_root` call scattered across modules |

## C2 — DoctrineService (fail-open removal)

| # | Given | When | Then |
|---|-------|------|------|
| C2.1 | `DoctrineService(...)` construction | inspect its API | there is no `built_in_root` parameter and no nested `_built_in_dir` |
| C2.2 | any production caller | build the service, access a repo | repos self-resolve via `built_in_dir(kind)`; behaviour unchanged |
| C2.3 | (regression) org pack shadows a built-in styleguide | load styleguides | `DoctrineLayerCollisionWarning` fires (the collision test, resolved at the real root) |

## C3 — Anti-regression architectural ratchet (`tests/architectural/`)

| # | Given | When | Then |
|---|-------|------|------|
| C3.1 | the `src/` tree | AST scan (joins only) | only the two `pack_paths.py` authorities construct a built-in **path join** — a `resolve_pack_root("built-in") / …` BinOp, its variable-indirected form (`x = resolve_pack_root("built-in"); x / …`), or a `<path> / "built-in"` filesystem join; any other join site fails the gate, named |
| C3.1b | a bare `resolve_pack_root("built-in")` root call (via `built_in_root()`) OR a bare `"built-in"` string used as a layer/provenance marker (~20 legitimate sites) | AST scan | is PERMITTED (not flagged) — the gate is join-only, not a constant-scan |
| C3.2 | every kind WITH a content dir (the 9) | resolve via authority | lands in an existing `packs/built-in/<plural>/`, asserted through `resolve_pack_root(...)` (not a raw repo-relative `.exists()`, cf. #3036); the derived complement `{mission_step_contract, template, anti_pattern}` is the `#3091`-marked exemption |
| C3.3 | the shipped `agent_profiles` set | count | is non-empty (anti-vacuity — a stale/empty root fails the gate instead of passing vacuously) |
| C3.4 | existing forbidden-pattern guards + the new ratchet | run | the ratchet lives in its OWN file (not folded into `test_no_dead_doctrine_paths.py`, cf. #3039); existing guards' old-path literals are NOT repointed |

## C4 — Activation-vocabulary derivation

| # | Given | When | Then |
|---|-------|------|------|
| C4.1 | `charter_yaml_io._ACTIVATION_KEYS` and the finalize migration `ACTIVATION_KEYS` | compare to `YAML_KEY_MAP` | both are set-equal to the derived authority (guard test) |
| C4.2 | a project with an activated glossary pack | run the finalize migration | `activated_glossary_packs` is carried onto `charter.yaml` (no silent drop) |
