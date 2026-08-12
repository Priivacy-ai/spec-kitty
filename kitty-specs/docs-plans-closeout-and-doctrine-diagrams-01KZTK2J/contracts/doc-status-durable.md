# Contract: `doc_status: durable`

**Requirement**: FR-002, C-005, NFR-004

## Interface

- **Enum**: add `DURABLE = "durable"` to `scripts/docs/frontmatter_backfill.py:DocStatus`.
- **Validation**: every site that validates/enumerates `doc_status` accepts `durable`:
  - the styleguide frontmatter contract (`packs/built-in/styleguides/common-docs.styleguide.yaml`)
  - the structural-lint asset frontmatter check
  - the docs tests asserting on doc_status values
- **Retire semantics**: the retire sweep and freshness/structural gates treat `durable` as never-retire.

## Guarantees (testable)

1. A domain plan with `doc_status: durable` passes the full `tests/docs/` suite (NFR-004).
2. The retire sweep skips any page with `doc_status: durable` (FR-002).
3. No existing doc_status value's behaviour changes (regression: existing pages unaffected).

## Bulk-edit note

Applying `durable` to the four domain plans + wiring it through the validation sites is an
occurrence-mapped change (see `occurrence_map.yaml`, categories `serialized_keys` + `code_symbols`).
