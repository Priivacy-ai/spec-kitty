# Data Model: docs/plans Tier 3 Closeout (Scope A)

Docs + a small vocabulary change. Entities and invariants:

## `doc_status` vocabulary

- **Represents**: the documentation-lifecycle controlled vocabulary.
- **Authority**: directive `042-common-docs` (closed set: draft/active/deprecated/superseded); the
  `DocStatus` StrEnum (`scripts/docs/frontmatter_backfill.py`) **mirrors** it.
- **New member**: `durable` — reserved, never-retire.
- **Invariant**: every validation site accepts the full set; `durable ∉ point_in_time_markers`;
  `closeout` is NOT a member (it is a point-in-time / archive-directory convention → `deprecated`).

## Domain plan (throughline)

- **Represents**: a durable, version-spanning plan for one domain.
- **Fields**: frontmatter (`title`, `description` ≤180, `doc_status: durable`, `updated`, `related:`);
  body in the canonical §1–§6 shape.
- **Location invariant**: under `docs/plans/domains/`; reachable in one hop from `docs/plans/index.md`.
- **Instances**: `saas-hosted-sync`, `doctrine-charter` (migrated), `packs-extraction`, `api-dashboard` (new).
- **Boundary invariant**: packs-extraction non-goals doctrine-charter §3.2; api-dashboard non-goals §3.6.

## Retire candidate

- **Represents**: a `docs/plans` document/cluster proposed for retirement.
- **Fields**: path; backing-evidence citation; retire mechanism (`deprecated`-in-place | move-to-archive);
  status (`retired` | `deferred` | `not-retireable`).
- **Invariant (NFR-002)**: content is never deleted; retirement preserves it + carries evidence. The
  roadmap is `deferred` (C-001).
