# Contract: `test_no_dead_doctrine_paths.py` Split + Fixture Decoupling (FR-001, FR-002)

Not an HTTP/API contract — this is the pass/fail contract the split gate modules and the redriven NFR-002 proof must satisfy, so `/spec-kitty.tasks` and implementation have an unambiguous Definition of Done.

## Pre-state (verified against the current file, 841 lines)

| Gate | Function | Scope | Discriminator-proof tests |
|---|---|---|---|
| A | `scan_graph_monolith_paths`/`_shipped` | `src/` (all of it) | `test_project_tier_graph_path_would_false_red_without_its_discriminator` |
| B | `scan_shipped_pack_paths`/`_shipped` | `src/` (all of it — **not** doctrine-scoped) | `test_shipped_prose_would_false_red_without_the_path_shape_discriminator`, `test_frozen_seed_mirror_would_false_red_without_its_discriminator` |
| C | `scan_doctrine_cross_links`/`_shipped` | `src/doctrine/` (the only doctrine-scoped gate) | `test_code_example_links_would_false_red_without_their_discriminator`, `test_placeholder_links_would_false_red_without_their_discriminator` |
| D | `test_no_live_doc_names_a_pre_move_builtin_path` | `docs/` | (self-contained) |

Currently, Gate C's discriminator-proof (`test_forbidding_mention_would_false_red_without_its_discriminator`) is pinned to the **live** artifact `packs/built-in/agent_profiles/doctrine-daphne.agent.yaml`'s `src/doctrine/graph.yaml` mention (line 136) — the exact contradiction #3036 tracks. (This is the *current* path — the profile was relocated from `src/doctrine/agent_profiles/built-in/` by an earlier, already-merged mission.)

All three gate functions (A, B, C) share a common set of helpers today: the `Site` dataclass, `_rel`, `_read_lines`, `_text_files` (an `lru_cache`-backed reader), and the `_REPO_ROOT`/`_SRC_ROOT`/`_DOCTRINE_ROOT`/`_PACKS_ROOT`/`_TEXT_SUFFIXES` constants.

## Post-state contract (FR-001)

1. Three (or more, if the implementer finds a reason) modules exist, each scoped to exactly the gates named above, grouped as: {A, B} together (both `src/`-wide), {C} alone (doctrine-scoped), {D} alone (`docs/`-scoped).
2. Every assertion present in the pre-state file is present in exactly one post-state module — none dropped, none duplicated.
3. No module's scan root is narrower than its pre-state scope (specifically: the module hosting Gate B must still scan `src/`, not `src/doctrine/`, even though it now lives alongside Gate C's module or separately — whichever the implementer chooses, as long as scope is preserved).
4. The shared helpers (`Site`/`_rel`/`_read_lines`/`_text_files`/root constants) are extracted into one common module both post-split modules import — not duplicated into each, matching this directory's existing convention of underscore-prefixed shared modules (`_gate_coverage.py`, `_sole_door_scan.py`).

## Post-state contract (FR-002)

1. `test_forbidding_mention_would_false_red_without_its_discriminator` (or its post-split equivalent) is redriven against a `tmp_path`-planted synthetic fixture, not `doctrine-daphne.agent.yaml`.
2. The fixture-based proof still fails (reds) if the discriminator's effect set is empty, or if it silently swallows a new, unexpected exclusion (the anti-widening property) — i.e. it is provably equivalent in strength to the pre-state live-artifact proof, just decoupled from *which* artifact demonstrates it.
3. `src/doctrine/agent_profiles/built-in/doctrine-daphne.agent.yaml`'s `avoidance-boundary` no longer mentions `src/doctrine/graph.yaml` (the "daphne cleanup"), and the full gate suite is green with that removal in place.
4. Gate C's cross-link case receives the same fixture-decoupling treatment for its own on-disk-resolution requirement (per US2-AS3).

## Falsification

This contract is falsified if, after implementation: (a) removing the `doctrine-daphne.agent.yaml` repo-local reference fails the gate suite, (b) a planted violation against the new fixture does NOT fail the gate suite, or (c) any pre-state assertion is missing from the post-state modules.
