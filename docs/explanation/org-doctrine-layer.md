---
title: Understanding the Org Doctrine Layer
description: How the three-layer doctrine model resolves built-in, org, and project artifacts, how provenance tracking works, and how org charter policy composes with the project charter.
---

# Understanding the Org Doctrine Layer

Spec Kitty resolves governance doctrine through three layers: a **built-in** layer shipped
with the CLI, an optional **org** layer fetched from one or more remote packs, and a
**project** layer maintained in the repository's own `.kittify/doctrine/`. This document
explains the model, the resolution rules, the provenance tags you will see in tooling
output, and the architectural boundary that keeps the three layers cleanly separated.

For step-by-step instructions on producing a pack, see [How to create an org doctrine
pack](../how-to/create-an-org-doctrine-pack.md). For migration guidance from a local
overlay, see [Migrating shared doctrine to the org layer](../migration/doctrine-local-overlay-to-org-layer.md).

---

## The three-layer model

```
┌────────────────────────────────────────────────────────────┐
│  Project layer:   .kittify/doctrine/                       │  ← highest precedence
│  (project-local artifacts and exceptions)                  │
├────────────────────────────────────────────────────────────┤
│  Org layer:       configured packs (e.g. ~/.kittify/org/*) │
│  (company-wide directives, profiles, tactics)              │
├────────────────────────────────────────────────────────────┤
│  Built-in layer:  shipped with the spec-kitty package      │  ← lowest precedence
│  (sane defaults for every spec-kitty project)              │
└────────────────────────────────────────────────────────────┘
```

Each layer is a structured set of YAML artifacts — directives, tactics, styleguides,
toolguides, paradigms, procedures, agent profiles, mission step contracts, and DRG
graph extensions. Layers share the same schemas. Their only difference is **where they
live** and **how they are produced**.

| Layer | Source | Owned by | Activation |
|-------|--------|----------|------------|
| Built-in | spec-kitty package | CLI maintainers | Always active |
| Org | Remote pack(s) declared in `.kittify/config.yaml` | Org governance teams | Opt-in per project |
| Project | `.kittify/doctrine/` in the repository | Project maintainers | Always active when present |

The org layer is **purely additive**. Projects that do not declare an org pack are
unaffected by this feature — the built-in plus project model continues to work exactly
as it did before.

---

## Why the org layer exists

Before the org layer, an organisation that wanted to share governance across many
projects had two unattractive options:

1. **Fork the CLI** to embed company-specific directives into the built-in layer.
2. **Copy/paste** governance artifacts into every project's `.kittify/doctrine/`.

Both approaches drift over time. Fork maintenance is painful; copy/paste means each
project carries a stale snapshot of the policy.

The org layer solves this by giving organisations a versioned, PR-governed,
independently-released home for their doctrine that any number of projects can consume
without per-project bookkeeping. A security team can ship `security-v2.1.0`, an
architecture team can ship `architecture-v1.4.0`, and a project consumes both by
listing them in its config.

---

## Precedence and resolution

When resolution traverses the three layers, it walks them in order — built-in first,
then each configured org pack in declaration order, finally project — and applies
**full-replace semantics on ID collision**.

> **Full-replace means**: if an artifact ID exists in a higher-precedence layer, that
> artifact entirely replaces the lower-precedence one. There is no field-level merging
> across layers. The higher-layer artifact stands or falls on its own.

### Within the org layer

If you configure multiple org packs, declaration order determines precedence within
the org layer. The **last entry has the highest precedence** — the convention is
"later wins."

```yaml
doctrine:
  org:
    packs:
      - name: architecture     # lower precedence
        local_path: ~/.kittify/org/architecture/
      - name: security         # higher precedence (declared later)
        local_path: ~/.kittify/org/security/
```

If both packs define `acme-001-secret-handling`, the `security` pack's version wins.

### Across layers

Project beats org. Org beats built-in. The project layer is always free to override
an org artifact for legitimate exceptions. When a project artifact has the same ID as
a higher layer (org or built-in), `spec-kitty charter lint` surfaces an advisory so
the team can confirm the override is intentional.

---

## DRG composition

The Doctrine Reference Graph (DRG) is the typed graph that the runtime traverses to
select context for a given action. Each layer can contribute graph **fragments**, and
they merge additively:

- Built-in DRG nodes and edges are always present.
- Org packs contribute additional nodes and edges via `drg/*.graph.yaml` fragments.
- Project DRG fragments compose on top.

DRG fragments from the org layer are **additive only** — they may add new nodes and
new edges, but they must not remove or modify nodes from a lower layer. `spec-kitty
doctrine pack validate` enforces this and rejects packs whose DRG references dangle
or whose extensions try to delete shipped graph state.

This rule is what keeps the three-layer composition safe: org packs cannot
silently weaken the built-in graph, and projects cannot accidentally weaken org
graph state without a visible override.

---

## Source attribution (provenance)

Every artifact and DRG node carries a `source` tag once it is resolved:

| Tag | Meaning |
|-----|---------|
| `builtin` | Shipped with the CLI |
| `org` | Loaded from a configured org pack |
| `project` | Loaded from `.kittify/doctrine/` in the repository |

Provenance shows up in two places you can inspect directly:

```bash
# Per-action charter context (shows which artifacts apply)
uv run spec-kitty charter context --action implement --json
```

```bash
# Pack inventory (shows what is installed and where it came from)
uv run spec-kitty doctor doctrine --json
```

When you see an artifact tagged `source: org`, it tells you the artifact resolved
from one of the packs in your `doctrine.org.packs` config — not from the project
overlay or the shipped defaults. That signal is what lets a team lead audit "is our
security directive actually live in this project?" without having to grep file trees.

---

## Org charter composition

In addition to artifacts and DRG fragments, an org pack may include an
`org-charter.yaml` at its root. This is a small, structured policy document that
composes with the project charter at interview time.

The `org-charter.yaml` schema has three meaningful fields:

| Field | Purpose |
|-------|---------|
| `interview_defaults` | Pre-fill answers for the project charter interview. The user can still override during the interview. |
| `required_directives` | Directive IDs that the project charter is expected to honour. Surfaced as advisories during lint. |
| `governance_policies` | Free-form policy entries (e.g. minimum test coverage). Advisory-only in this release. |

The merge across multiple packs follows the same "later wins" rule as artifacts:

- `interview_defaults`: dict update; later packs overwrite earlier values.
- `required_directives`: union, preserving first-seen order.
- `governance_policies`: concatenated and deduplicated by `(field, value)`, keeping
  the last occurrence.

Empty packs (no `org-charter.yaml`) contribute no policy — they are doctrine-only.

> **Enforcement note**: In this release, `enforcement` values on
> `governance_policies` are read but treated uniformly as advisory. Only the literal
> string `"advisory"` is honoured today; other values parse and surface as advisories.
> Future releases may add stronger enforcement modes; pack authors should write
> `enforcement: advisory` explicitly to remain forward-compatible.

---

## The fetch model

Org packs are not resolved over the network at runtime. The `doctrine fetch` command
downloads or refreshes a **local snapshot** under each pack's configured `local_path`,
and every subsequent resolution reads from that snapshot.

This shape was chosen deliberately:

- **CI/CD safety**: pipelines do not depend on remote availability or auth.
- **Determinism**: a project produces the same context on every machine that has
  fetched the same ref.
- **Auditability**: the on-disk snapshot is the record of "what governance ran here."

`doctrine fetch` is an explicit install/update step, not a background operation. If
your org publishes a new ref, you re-run `doctrine fetch` (or your IT system does)
to pick it up. This is the same shape as `npm install` or `pip install` — fetch is
the install step; resolution is offline.

For git-managed packs, the local path is a normal working tree of the git clone
(`.git/` present). For HTTPS bundles and HTTP APIs, the snapshot is an atomic
replace of the directory with a `pack-manifest.yaml` recording the fetched version.

---

## Architectural boundary

The org layer respects a strict layer rule:

```
kernel  ←  doctrine  ←  charter  ←  specify_cli
```

The `charter` package implements DRG composition (`load_validated_graph`) and accepts
an explicit `org_root` argument when present. It must not import from
`specify_cli`. The actual config-aware resolution — reading `.kittify/config.yaml`
and turning it into a list of pack paths — lives one layer up in
`specify_cli.doctrine.config.resolve_org_roots`.

To preserve the boundary, `charter._drg_helpers._resolve_org_root()` is an **inert
stub** that always returns `None`. Real callers in `specify_cli` resolve the path
themselves and pass it explicitly. This pattern is documented in the source and
enforced by `tests/architectural/test_layer_rules.py` so that no future change can
silently introduce a circular dependency.

If you encounter `_resolve_org_root` in the codebase and wonder why it is empty:
that is the intentional design. The real logic is one layer up.

---

## Frequently asked questions

**Can I have multiple org layers?**
Yes — list any number of packs in `doctrine.org.packs`. Within the org layer,
declaration order determines precedence (later wins).

**Can a project override an org artifact?**
Yes. The project layer always wins. Use the override when you have a genuine
project-level exception; `charter lint` will surface an advisory so the
override remains visible.

**What if the org snapshot is missing on disk?**
Resolution gracefully falls back to built-in + project. The org layer is additive;
its absence does not break the project. `spec-kitty doctor doctrine` will report
the configured-but-not-fetched pack so you know to run `doctrine fetch`.

**Is it safe to gitignore the snapshot directory?**
Yes — and that is the recommended pattern. `doctrine fetch` is the install step;
treating the snapshot as cache rather than source-controlled artifacts keeps the
repository small and ensures all consumers pull the same way.

**Does the org layer change how shipped doctrine is loaded?**
No. The built-in layer is unchanged. The org layer composes on top.

**Where do I see which layer an artifact came from?**
`uv run spec-kitty charter context --action <action> --json` lists every resolved
artifact with its `source` tag. `uv run spec-kitty doctor doctrine --json` lists
installed pack contents.

---

## See also

- [How to create an org doctrine pack](../how-to/create-an-org-doctrine-pack.md)
- [Migrating shared doctrine to the org layer](../migration/doctrine-local-overlay-to-org-layer.md)
- [How to set up project governance](../how-to/setup-governance.md)
- [Understanding Charter: Synthesis, DRG, and Governed Context](charter-synthesis-drg.md)
