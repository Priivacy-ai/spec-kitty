# Data Model: Docs Site IA & Onboarding Overhaul

This mission's "data model" is a content/metadata model, not a runtime database — every entity
below is expressed as a markdown file, frontmatter field, or YAML config entry.

## DocsPage

A markdown file under `docs/`.

| Field | Type | Notes |
|---|---|---|
| `path` | string | Relative path under `docs/`. |
| `zone` | enum {`end-user`, `contributor`} | Required for every retained page after IC-01 (FR-003). |
| `group` | `NavigationGroup` reference | The nested `toc.yml` parent this page sits under (FR-015). |
| `divio_type` | enum {`tutorial`, `how-to`, `reference`, `explanation`} | Frontmatter `type:` field. Internal editorial use only — never rendered as nav vocabulary (C-002). |
| `disposition` | enum {`keep`, `merge`, `rewrite`, `remove`, `new`} | Recorded in `gap-analysis.md` during the audit (FR-009); `new` for pages this mission creates. |

**Validation rules**:
- Every `DocsPage` retained after restructuring has a non-null `zone` and `group` (NFR-006 — no orphans).
- `divio_type` frontmatter is present and valid on every page in `docs/guides/` post-restructure and on every newly authored page (NFR-005).
- A page whose `disposition` is `remove` must have a corresponding `redirect_map.yaml` entry if any external or internal link targeted its old path.

## NavigationZone

One of two top-level segregated areas.

| Field | Type | Notes |
|---|---|---|
| `id` | enum {`end-user`, `contributor`} | Fixed set of exactly two (FR-003). |
| `label` | string | Display name in `toc.yml` (e.g. "Using Spec Kitty" / "Contributing"). |
| `top_level_group_count` | int | Must be ≤6 (NFR-003). |

**Invariant**: No `DocsPage` with `zone: contributor` is reachable via a navigation path that
starts inside `zone: end-user` (C-005) — checked structurally by walking `toc.yml`'s nested tree
from each end-user top-level group and asserting no contributor-zone page appears.

## NavigationGroup

A nested `toc.yml` parent entry (`items:` list) that collapses related pages under one
expandable top-level item.

| Field | Type | Notes |
|---|---|---|
| `name` | string | The `toc.yml` `name:` value shown before expansion. |
| `zone` | `NavigationZone` reference | Exactly one. |
| `children` | list of `DocsPage` or nested `NavigationGroup` | DocFX supports arbitrary nesting depth (precedent: `docs/toc.yml`'s existing "Historical Archive" entry). |

**Validation rule**: Each `NavigationZone` has ≤6 `NavigationGroup` (or ungrouped top-level
`DocsPage`) entries visible before expansion (NFR-003/FR-015).

## DoctrineArtifactKind

A fixed enumeration, not mission-authored data — sourced from
`charter.kind_vocabulary.from_operator_token`.

| Value |
|---|
| `directive` |
| `tactic` |
| `styleguide` |
| `toolguide` |
| `paradigm` |
| `procedure` |
| `agent_profile` |
| `mission_step_contract` |

`template` and `asset` are related but distinct, non-charter-activatable kinds — not among the
8. Corrected during WP06 implementation against live source (`src/charter/kind_vocabulary.py`,
`src/doctrine/artifact_kinds.py`) and the installed CLI's own `charter list --all` output; the
CLAUDE.md table this mission originally sourced the list from was stale.

**Validation rule**: `docs/doctrine/doctrine-kinds.md` (FR-007) must contain exactly these 8
values, each with a purpose statement and an example — no more, no fewer (single canonical
authority per Charter Check).

## GlossaryTerm

An entry in `.kittify/glossaries/spec_kitty_core.yaml` (104 terms today; this mission does not
change the count, only makes existing terms linkable).

| Field | Type | Notes |
|---|---|---|
| `surface` | string | The canonical display form (existing field). |
| `definition` | string | Existing field; becomes tooltip content (FR-011). |
| `confidence` | float | Existing field; unused by this mission. |
| `status` | string | Existing field; unused by this mission. |
| `anchor_id` | string | **NEW field this mission adds** — a stable, unique, URL-safe id generated from `surface` (e.g. slugified), added to `glossary_page()`'s rendered output (FR-012). |

**Validation rule**: `anchor_id` is unique across all 104 terms and stable across regenerations
(same `surface` always produces the same `anchor_id`) — required for FR-012's "individually
addressable" guarantee and for the glossary linker (below) to have a stable target.

## GlossaryLink

Not a stored entity — a runtime output of `scripts/docs/glossary_linker.py`, computed at build
time per rendered HTML page.

| Field | Type | Notes |
|---|---|---|
| `page` | `DocsPage` reference | The page the link was inserted into. |
| `term` | `GlossaryTerm` reference | Matched via longest-match-first on `surface`. |
| `occurrence_index` | int | Always `0` — first-mention-only (NFR-004); the linker tracks per-page state to prevent a second link to the same term. |
| `href` | string | `kitty-specs/glossary.html#{anchor_id}`. |
| `tooltip` | string | Copied from `GlossaryTerm.definition` at link-insertion time. |

**Validation rules**:
- Never inserted inside a `<code>`/`<pre>` block (Edge Case in spec.md).
- Longest matching `surface` string wins when two terms overlap as substrings (Edge Case in spec.md).
- At most one `GlossaryLink` per `(page, term)` pair (NFR-004).

## Get Started Path

Not a data entity — the confirmed sequence of `DocsPage`s a first-time visitor traverses
(FR-002): homepage (`docs/index.md`) → one Get Started landing page → install how-to →
`getting-started.md` → `your-first-mission.md` (renamed from `your-first-feature.md` per
FR-014). Modeled here only to make the acceptance chain for NFR-001/NFR-002 traceable to
concrete files during tasks/implement.
