# Phase 0 Research: Docs Quality Gate Hardening

Decisions consolidated from the pre-spec grounding squad and the post-spec adversarial squad. Each was verified against live code (file:line / executed counts).

## D1 — Slash-command gate: check-only + hand-authored backfill

- **Decision**: A check-only gate that diffs the documented heading set against `CONSUMER_SKILLS`; the three missing sections are hand-authored.
- **Rationale**: `docs/api/slash-commands.md` carries rich per-command prose and has **no generator** today; full generation would flatten it. `CONSUMER_SKILLS` (`src/specify_cli/shims/registry.py`) is the import-asserted single authority.
- **Alternatives rejected**: full generate-and-check (flattens prose; no generator precedent for this page); hybrid generated-inventory + prose (more moving parts, unneeded).

## D2 — New heading extractor (not `_HEADING_RE` reuse)

- **Decision**: Author a new extractor for the `## /spec-kitty.<name>` heading form; reuse only the *shape* (parse → diff → emit → non-zero exit) and test harness of `check_cli_reference_freshness.py`.
- **Rationale**: the sibling's `_HEADING_RE` matches the space form `spec-kitty foo` and will not match the slash+dot form (confirmed by two lenses).
- **Alternatives rejected**: reuse the regex (won't match); generalize the sibling regex (couples two unrelated docs).

## D3 — Publication non-vacuity at per-include-glob granularity, pre-exclusion

- **Decision**: Assert each declared docfx `files` markdown glob resolves to ≥1 page **before** exclusions are applied.
- **Rationale**: `docs/docfx.json` declares only **2** content entries; the real subtrees (`guides/`=76, `adr/`=152, `api/`=22, …) are globs inside the single root entry. Executed evidence: emptying `guides/` → 599 pages (in the 500–674 band) leaves both the aggregate floor and a per-*entry* guard GREEN. Pre-exclusion evaluation prevents the fully-excluded `archive` tree (14 raw → 0 post-exclusion) from false-failing.
- **Alternatives rejected**: per-content-entry (vacuous — the mission's original framing, corrected by the squad); post-exclusion evaluation (reds main on `archive`); replace floor with exact census (violates C-002, brittle to ±1 churn).

## D4 — docs-freshness item 3: assert in-repo safety structure, not the required-check setting

- **Decision**: FR-005 test asserts repo-readable properties — the `paths:` filter still excludes `tests/**`/`kitty-specs/**`, the unfiltered `push:main` backstop is present, and the documented invariant comment is present.
- **Rationale**: the required-status-check list lives only in the GitHub control plane (no repo diff on change; token cannot read it), so a test cannot observe the transition. The structural properties are what actually make the filter safe. Operator confirmed docs-freshness is non-required this session (C-003).
- **Alternatives rejected**: hardcode `required == {drift-detector}` (unobservable AND canonizes one of two conflicting in-repo sources — `docs-freshness.yml` vs `ui-e2e.yml`'s contract comment); remove the paths filter (risks #3147-style over-firing on untouched offenders).

## D5 — FR-006: cross-reference the existing invariant comment

- **Decision**: Cross-reference the already-present invariant comment in `docs-freshness.yml` to the FR-005 test (reusing the "Required-check contract" idiom); do not re-add existing content.
- **Rationale**: the residual-gap + non-required invariant is already documented in-file; the risk is a vacuous "add docs" WP. Value is prose↔test co-evolution.

## Open items carried into design

- None blocking. The only external unknown (live required-check list) is deliberately out of the testable surface by D4; operator-confirmed non-required (C-003).
