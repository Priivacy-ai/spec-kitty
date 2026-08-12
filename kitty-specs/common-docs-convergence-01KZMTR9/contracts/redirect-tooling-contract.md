# Contract — Redirect / Move Tooling (FR-021, C-010, NFR-010)

- **Move spine**: this mission's `occurrence_map.yaml`. Every file move is a `moves:` entry.
- **Invocation**: `redirect_stub_generator.py` and `relative_link_fixer.py` are driven with
  `--occurrence-map kitty-specs/common-docs-convergence-01KZMTR9/occurrence_map.yaml` (NOT the
  hardcoded closed-mission default). Parameterizing/removing that hardcode is part of IC-02.
- **`redirect_map.yaml`**: DERIVED artifact — regenerated from `baseline + moves`, never hand-edited.
- **`redirect_baseline_urls.json`**: IMMUTABLE input — the coverage denominator; never edited per move.
- **Cumulative coverage (NFR-010)**: regeneration MUST preserve the prior closed mission's 149 entries
  (cumulative spine or additive merge); `coverage` and `check-map` subcommands pass; `moves:` ⊆ map.
- **Stubs**: every generated redirect stub carries `description: "Redirect stub: …"` (FR-022) so the
  structural lint's `shadow_tree_basename` skips it.
- **Cross-mission**: single-writer ownership of `redirect_map.yaml` (WP07 of the closed structural-move
  mission) is reconciled — see #2358. IC-11 is this mission's single writer.
