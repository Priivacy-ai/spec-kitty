# Contract: Kind-Filtered Node Reporting

The output contract for structurally non-activatable (kind-filtered) nodes encountered during a
charter cascade. Its whole purpose is **C-002 symmetry**: three independent consumers report the
same fact, and they must never diverge in wording.

Issue #3705. Policy authority: ADR 2026-08-20-1 (the exclusion of `TEMPLATE` and `ASSET` from
`CHARTER_ACTIVATABLE_KINDS` stands; this contract governs *visibility*, never the policy).

## The collection seam

`charter.cascade._referenced_artifacts` returns
`tuple[list[ReferencedArtifact], list[ReferencedArtifact]]` — `(activatable, kind_filtered)`.

A node whose kind is not in `CHARTER_ACTIVATABLE_KINDS` lands in the second list. It is **never
dropped**, never capped, never truncated, never sampled (NFR-002). This is the single place the
partition happens; all three consumers read from it.

## The rendered line

One line per kind-filtered node, emitted through the single shared helper
`charter.activate._render_kind_filtered_line`, never re-coined at a call site (FR-009):

```text
Not cascaded: {kind_token}/{config_id} (kind not charter-activatable)
```

- `kind_token` is `ArtifactKind(...).operator_token` — the operator-facing spelling, not the raw
  enum value.
- `config_id` is the **config-stem id**, resolved via `resolve_config_id(...)`, falling back to
  the URN tail (`urn.partition(":")[2]`) when the id cannot be resolved. Never the raw bare id.
- Nodes are rendered in sorted order.

## The three consumers

| Consumer | Field carrying the nodes | Shape |
|---|---|---|
| `charter activate --cascade` report | `CascadeActivationResult.not_cascaded_kind_filtered` | `dict[str, list[str]]` |
| `charter activate` no-cascade warning | `NoCascadeReport.not_cascaded_kind_filtered` | `dict[str, list[str]]` |
| `charter deactivate --cascade` | `DeactivationPlan.not_cascaded_kind_filtered` | `list[str]` |

The deactivation-side shape divergence is **deliberate and pre-authorized** (`plan.md:242-259`):
`deactivate._render_cascade_deactivation` partitions URNs itself, so the flat list is what it
needs. Nothing consumes the three fields generically. Symmetry is a property of the **rendered
output**, not of the field shapes — and it is pinned by a test asserting activate and deactivate
emit byte-identical lines for the same fixture.

## The zero-activatable message

Printed **once, never per-node**, when the cascade resolved zero activatable targets **and** at
least one referenced node was specifically kind-filtered:

```text
Cascade resolved zero activatable targets (every referenced node was kind-filtered; see the lines above).
```

It is deliberately **not** printed for:

- a source with zero referenced nodes at all;
- a pure scope-narrowing case, where nodes were excluded by `CascadeScope.selects()` rather than
  by kind.

## Invariants

- **C-006** — a kind-filtered node never passes through `CascadeScope.selects()`. Kind filtering
  and scope narrowing are independent, and the two are reported by distinct, mutually exclusive
  lines (`Not cascaded:` vs `Skipped (out of scope)`).
- **NFR-002** — every kind-filtered node is reported; no cap, truncation or sampling.
- **NFR-004** — pre-existing line shapes are unchanged; this contract only adds lines.
