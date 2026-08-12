# Data Model — Common Docs Convergence

The "entities" here are documentation-structure schemas and the closed enumerations the acceptance
gates assert against. No runtime database.

## Documentation page frontmatter (Common Docs)
| Field | Required | Rule |
|-------|----------|------|
| `title` | yes (non-README) | short human title |
| `doc_status` | yes (non-README, non-ADR) | `draft \| active \| deprecated \| superseded` |
| `updated` | yes (non-README, non-ADR) | `YYYY-MM-DD` |
| `description` | yes (in-scope) | 50–180 chars (SEO band) |
| `type` | yes (guides/development in-scope) | Divio: `tutorial \| how-to \| reference \| explanation` |
| `related` | optional | list of resolvable repo-relative `.md` paths |
| `audience` | touched pages only (C-012) | resolvable repo-relative `.md` path(s) into `docs/context/audience/`; NOT added to `frontmatter_required_fields` |
| ADR `status` | ADR only | MADR: `Proposed \| Accepted \| Deprecated \| Superseded` (the sole `status` exemption) |

**Invariant**: a page uses `doc_status` (never bare `status`) unless it is an ADR. Redirect stubs carry `description: "Redirect stub: …"`.

## Audience persona (existing catalog — SSOT)
- Location: `docs/context/audience/{internal,external}/<persona>.md` (+ README landing pages).
- Existing internal: maintainer, lead-developer, system-architect, ai-collaboration-agent, spec-kitty-cli-runtime, project-codebase. Existing external: architect-evaluator, tech-lead-evaluator, product-manager-evaluator, project-owner.
- `audience:` on a page resolves to one of these files. New personas authored from `src/doctrine/templates/architecture/stakeholder-persona-template.md`. Files kebab-cased (FR-013).

## Occurrence map (`occurrence_map.yaml`) — the move spine
- Cumulative `moves:` list of `{from, to, kind}` entries driving `redirect_stub_generator.py` and `relative_link_fixer.py`.
- Classifies every affected string across the 8 DIRECTIVE_035 categories (see `occurrence_map.yaml`).
- **Invariant (NFR-010)**: `moves:` ⊆ regenerated `redirect_map.yaml`; the prior closed mission's baseline coverage is preserved.

## Redirect artifacts
- `scripts/docs/redirect_map.yaml` — DERIVED from `baseline + moves`; do-not-hand-edit; regenerated.
- `scripts/docs/redirect_baseline_urls.json` — IMMUTABLE pre-move URL baseline; the coverage denominator.

## Sanctioned enumerations (closed sets — gate targets)
- **Content sections**: `index, context, architecture, adr, plans, api, configuration, integrations, security, guides, operations, migrations, changelog, development`.
- **Non-content dirs**: `assets/`, `templates/spec-kitty/`.
- **Root allowlist**: `README.md, LICENSE, CHANGELOG.md, CONTRIBUTING.md, CLAUDE.md, AGENTS.md, CODE_OF_CONDUCT.md, SECURITY-POSITION.md, CONTRIBUTORS.md, RELEASE_CHECKLIST.md, .all-contributorsrc, ascii-art.txt`.
- **Concern→section routing** (updated, FR-009): `how_to`→ audience-split (`development/` for contributor, `guides/` for user), `reference_policy`→`development/`, `ops_runbook`→`operations/`, `point_in_time`→`plans/engineering-notes/`, `generated_nav`→pinned, `doctrine_artifact`→`src/doctrine/`.

## Charter authority paths (must resolve — FR-019)
- Live: `docs/context/`, `docs/adr/3.x/` (+ `glossary/contexts/` repair). Dead to repair/remove: `glossary/contexts/`, `architecture/3.x/adr/`, `architecture/adrs/`.
