# Quickstart / Validation — Doctrine, Glossary & Architecture Consolidation

How to verify the consolidated artefacts (maps to NFR-001…004 and the Success Criteria).

## Gate checks (run from repo root, on `feat/doctrine-glossary-consolidation-01KTNWFC`)

```bash
# Terminology canon (C-003) — must pass after any prose/glossary edit
pytest tests/architectural/test_no_legacy_terminology.py

# Glossary validity (NFR-003) — all touched seeds
spec-kitty glossary validate glossary/**/*.yaml .kittify/glossaries/*.yaml

# Doctrine health + DRG freshness (NFR-001) — after IC-04/IC-08
spec-kitty doctor doctrine --json        # healthy, no skipped profiles
# DRG regeneration is deterministic (IC-08): regenerate twice → identical graph.yaml

# Code quality (NFR-002) — changed paths only
ruff check src/charter src/glossary src/doctrine
mypy src/charter src/glossary src/doctrine

# Architecture (NFR-004) — new ADR follows template; C4 levels render
ls architecture/diagrams/{01_context,02_containers,03_components}
```

## Acceptance walkthroughs (Success Criteria)

- **SC-1 / SC-6:** apply the new procedure/styleguide to **#391** — split, reparent children, close superseded — using *only* the authored doctrine (IC-09). Record the run in `work/`.
- **SC-2:** re-run the epic↔architecture correlation (`work/EPIC_ARCHITECTURE_CORRELATION.md`) — zero gaps (Ops ADR landed, IC-05).
- **SC-3:** an `org-charter.yaml` with `extends:` resolves additively + validates (IC-07).
- **SC-4:** single DRG regeneration command → freshness gate passes deterministically (IC-08).
- **SC-5:** glossary content refreshed + validates; runtime-scope promotion explicitly deferred (IC-06).
- **SC-7 (C-005):** grep confirms a single source of truth per surface — no second glossary location, no parallel charter resolver, no duplicated architecture narrative.

## Reference-integrity check (bulk-edit IC-01/IC-02)

After the moves, verify no dangling references to old paths:
```bash
grep -rIn -e 'architecture/2.x/adr' -e 'architecture/glossary' -e '\.kittify/glossaries' src docs architecture .kittify/charter \
  | grep -v occurrence_map.yaml   # expect only intended/historical hits
```
Every old→new path must be in `occurrence_map.yaml` and verified post-move.
