# Contract: Doctrine-Integrity Gates (acceptance)

The landed set must satisfy every gate below. These are the executable DoD for WS1 + the
validation half of WS2. Run from the repo root with the isolated env active.

## G-1 — Surface (SC-001, C-001)

- **Assert:** `git ls-files 'src/doctrine/*/built-in/*'` returns **empty**; all 16 YAML + 5
  asset pairs + READMEs exist under `packs/built-in/…` at the paths in `data-model.md §1`.
- **Command:** `find packs/built-in -path '*writing*' -o -name 'comms-cleo.agent.yaml'` … (spot-check) + `git grep -l 'built-in/built-in' || true` (must be empty).

## G-2 — Validation (SC-002, NFR-003)

- **Assert:** every new artifact passes schema validation; the `type: asset` tactic reference
  resolves once assets are in place.
- **Command:** `spec-kitty doctrine validate <each new artifact>` → 0 errors; and
  `spec-kitty doctrine pack validate packs/built-in` → OK.

## G-3 — Doctor health (SC-002, NFR-001)

- **Assert:** `spec-kitty doctor doctrine --json` → `profile_health.healthy == true`, builtin
  pack `discovered_count == valid_count == 25`, `invalid_profiles == []`,
  `skipped_profiles` contains none of the 7 new ids, `org_drg.errors == []`, exit 0.

## G-4 — Shipped-profiles gate (SC-002, D-04)

- **Assert:** `EXPECTED_PROFILE_IDS` contains the 7 new ids (25 total); all 7 satisfy the
  6-field contract (canonical-verbs, output-artifacts, mode-defaults+use-case, doctrine-layers,
  directive-references) + ≥1 role; both profile READMEs list exactly the 25 shipped ids.
- **Command:** `pytest tests/doctrine/test_shipped_profiles.py -q` → green.

## G-5 — DRG freshness & reachability (SC-003, NFR-001, C-002)

- **Assert:** committed fragments are fresh; every new node is reachable (no new orphan).
- **Command:** `spec-kitty doctrine regenerate-graph --check` → exit 0 (no staleness);
  `pytest tests/doctrine/drg/test_reachability.py -q` → green (frozensets recomputed
  empirically; a moved pin carries a ledger row).

## G-6 — Pack relocation doctor gate (SC-001, D-05)

- **Assert:** `EXPECTED_PROFILE_COUNT == 25`; the `(node_count, edge_count)` tuple equals the
  post-regenerate measured values; glossary term count still 108.
- **Command:** `pytest tests/doctrine/test_pack_relocation_doctor_gate.py -q` → green.

## G-7 — Terminology & no-greenwash (C-004)

- **Assert:** new prose obeys the Terminology Canon; assets stay `asset` (no relabel).
- **Command:** `pytest tests/architectural/test_no_legacy_terminology.py -q` → green.

## G-8 — Full suite on CI (SC-006)

- The targeted gates above run locally per-WP (charter Testing Requirements — targeted only).
  The **full** `tests/` suite is the CI release authority and must be green before the operator
  merges. Not run in-session.
