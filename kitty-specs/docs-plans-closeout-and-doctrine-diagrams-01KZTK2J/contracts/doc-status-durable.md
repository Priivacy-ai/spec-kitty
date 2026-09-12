# Contract: `doc_status: durable`

**Requirement**: FR-002, NFR-001, C-004, C-005

## Authority chain (edit in this order)

1. **directive `042-common-docs.directive.yaml`** — the AUTHORITATIVE closed vocabulary
   (currently draft/active/deprecated/superseded). Add `durable` here first.
2. **`scripts/docs/frontmatter_backfill.py:DocStatus`** — the enum **mirrors** the directive. Add `DURABLE`.
3. **`common-docs.styleguide.yaml`** — the `structural_lint_config` (`point_in_time_markers`) + vocabulary prose; ensure `durable ∉ point_in_time` (durable is the semantic opposite of point-in-time / never-retire).
4. **`docs-freshness-sla.styleguide.yaml`** — the freshness/retire gate; `durable` is never-stale.
5. **`src/doctrine/styleguides/models.py`** + regenerated schema — only if `durable` is encoded structurally (then `tests/doctrine/test_schema_generation_integrity.py` is the gate that reds).

## Guarantees (testable)

1. A domain plan with `doc_status: durable` passes the full `tests/docs/` suite **and** the `tests/doctrine/` schema-integrity test (NFR-001).
2. `durable` is accepted at **every** site enumerated above — proven by a single test that runs a `durable` fixture through each gate (red-first per C-011).
3. `durable` is classified as never-point-in-time / never-retire by the structural lint.
4. No existing `doc_status` value's behaviour changes.

## Non-guarantees (corrected)

- There is **no automated retire-sweep tool** in the tree; retirement (FR-001) is a manual,
  evidence-gated curation process. So "the sweep skips durable" is **not** an executable
  guarantee — the testable property is that the doc **gates** (freshness/structural-lint) accept
  `durable` and never flag it stale. Do not spec a phantom sweep tool.
- `closeout` is **not** a `doc_status` value — it is a point-in-time-marker / archive-directory
  convention mapping to `deprecated`. Do not add it to the enum (C-004).

## Bulk-edit note

Adding `durable` is an **additive** frontmatter value, not a same-string rename, so it is out of
`occurrence_map.yaml` (which covers only the domains/ migration).
