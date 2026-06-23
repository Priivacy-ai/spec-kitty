# Phase 0 Research — Design Decisions

Most analysis was front-loaded into the post-spec adversarial squad; the full cited evidence is in [`research/post-spec-squad-findings.md`](research/post-spec-squad-findings.md). This file records the resulting **decisions**.

## D-1 — Resolution seam at `OrgPackConfig.effective_root`, not `resolve_org_roots`

- **Decision**: Compute the effective pack root once, as an `OrgPackConfig` property/helper `effective_root(repo_root)` that normalizes `local_path` relative to repo root and joins `subdir`. Every consumer reads through it.
- **Rationale**: The squad (alphonso+debbie+priti, convergent) proved `resolve_org_roots` is a thin `[pack.local_path …]` map that ≥6 consumers bypass — including the `doctor doctrine` health path (`load_org_drg`→`load_org_pack`). A single property is inherited by all and retires the pre-existing raw-vs-relative inconsistency (C-007).
- **Alternatives rejected**: (a) patch only `resolve_org_roots` — leaves `doctor doctrine` RED (debbie's trace); (b) patch each consumer independently — N fragile sites, regression-prone.

## D-2 — Containment via `ensure_within_directory`, validation timing split

- **Decision**: Reuse `specify_cli/core/utils.py:ensure_within_directory` (strict `.resolve()`, symlink-safe). String-level escapes (absolute incl. Windows/UNC, `..`) rejected at config-load with a structured, operator-visible error; symlink-escape checked at effective-root **resolution** time. `.`/empty → "no subdir".
- **Rationale**: `OrgPackConfig` is validated before the clone exists, so a symlink the clone plants can only be caught at resolution. The error must not be swallowed by `load_pack_registry`'s warning-and-degrade path (`org_pack_config.py:128`), else Scenario A1's "structured error" contract breaks.
- **Alternatives rejected**: `is_relative_to` without `.resolve()` (misses symlink); validate-time-only check (can't see a not-yet-cloned symlink).

## D-3 — Thread D: validate-time fail-loud guard (preferred over query-time wildcard)

- **Decision**: `spec-kitty doctrine validate` rejects `applies_to_languages: [any]`/`[all]` with an actionable message ("omit the field to mean always-applicable"). `scoping.py:applies_to_languages_match` may optionally treat them as wildcard as defense-in-depth, but the **guard is canonical**.
- **Rationale**: The bug is *silent* drop with no authoring signal (`scoping.py:24` — `any`/`all` are literal tokens, never overlap a concrete active set). Failing at validate time surfaces it where the author writes it (issue #2092 stated preference; C-006).
- **Alternatives rejected**: query-time wildcard only — still silent at authoring; the next author re-trips it.

## D-4 — Thread C: `styleguide` kind + mandatory inbound DRG edge

- **Decision**: Ship one `*.styleguide.yaml` under `src/doctrine/styleguides/built-in/`; add ≥1 inbound `suggests`/`requires` edge from an existing directive/paradigm; regenerate `graph.yaml` via the generator; add a non-orphan test.
- **Rationale**: The generator auto-discovers styleguides + directives; orphan nodes are permitted (graph accepts bare nodes), so FR-009-original "resolvable" was satisfiable by an inert stub. The inbound edge + test make it real — still doctrine-only (a `suggests` edge is not CI/agent-effort).
- **Alternatives rejected**: directive kind (styleguide is the right kind for standards); leave orphan (doctrine theater, renata+priti).

## D-5 — Thread B: document current-vs-aspirational, name the mixed-usage sites

- **Decision**: The YAML-library doc declares whether it states current or aspirational practice, is verified against ≥3 named sites, and explicitly names the mixed-usage sites (same `config.yaml` ruamel-round-tripped in `org_pack_config.py` and `safe_load`-ed in `org_pack_loader.py:38`; 3 dual-use modules).
- **Rationale**: Usage is genuinely ad-hoc; a single "rule" sentence would be provably false (renata). Honesty beats a fabricated invariant.
- **Alternatives rejected**: assert a clean rule (false); silently ignore the contradictions (papers over the real state).
