# Data Model: Read-Side Seam: Placement-Authority Closure

This mission adds no persisted runtime entity. Its "data model" is (a) the **layer model**
the architecture page must state, and (b) the **schemas** of the two machine-parsed
artifacts the gates consume. Both are normative for implementation.

---

## 1. The layer model (verified against the live tree)

The decision "where does this artifact live?" passes through distinct layers. Each has one
owner. A caller that reaches past its own layer is the defect this mission removes.

| Layer | Question answered | Owning surface | Aware of? |
|---|---|---|---|
| **L0 — entry** | *what* am I reading? | the artifact-kind enum + the seam object (`write_target` / `read_dir` projections) | kind only |
| **L1 — partition classification** | which partition does this **kind** belong to? | the kind frozensets + partition invariant assertion in the artifacts module | kind; **topology-blind** |
| **L2a — declared decision** | where does this fact **architecturally** live? | the declared-read-surface function | kind + topology; **materialization-blind** |
| **L2b — affirmative decision** | where does this read resolve **right now**? | the surface-classification function, consuming coord-state probing | kind + topology + **materialization** |
| **L3 — candidate discovery / assembly** | which concrete directories exist for this handle? | the path-resolver module's constructors | filesystem + handle form |
| **L4 — translation** | given a chosen surface, **which** discovered location is it? | the surface-translation function over the locations record | neither — it *selects*, and **refuses** when the requested location is absent |
| **Composition roots** | — | read root and write root, both reached through one seam | — |

### Invariants the page must state

- **INV-1 (authority)**: only L1–L2 decide the surface. L0 declares a kind; L3 assembles
  paths; L4 selects among already-discovered locations. A caller performing L1's job by
  choosing a surface-specific helper is **semi-compliant**.
- **INV-2 (the L2 split is deliberate)**: L2a is materialization-blind *so that it can
  disagree with an already-resolved stamp*. Collapsing L2a and L2b into "the decision
  module" erases the reason an existing surface-cannot-hold guard can fire at all.
- **INV-3 (L4 does not assemble)**: translation reads the requested field off the locations
  record and raises when it is absent. Believing otherwise leads a reader to strangle
  through L4 and re-add discovery at the call site — the misappropriation this page exists
  to prevent.
- **INV-4 (two roots, one seam)**: the read root and the write root are separate
  composition roots reached through the same seam object. Documenting one invites
  re-derivation of the other.
- **INV-5 (honest bounds)**: the surface enum has members with **no production producer**;
  only two are wired. One frozenset still carries a retired word as residual rename debt.
  Both are named, not laundered.

### Compliance taxonomy (the page's central table)

| Shape | Form | Verdict |
|---|---|---|
| **Compliant (tier-1)** | caller names a kind, seam resolves the surface, fail-loud | target state |
| **Delegating-but-lenient** | kind named, surface delegated, but the leaf never supplies the fail-closed input | censused as a bypass on the *leniency* axis |
| **Semi-compliant** | canonical handle, **caller-chosen surface** | this mission's subject; invisible to a handle-hygiene gate |
| **Non-compliant** | raw/unrecognised handle, or hand-assembled path | reds the census (or should — one site currently passes by omission) |

---

## 2. Classification ledger — row and section schema

The ledger is **machine-parsed**; its shape is a contract, not formatting.

### 2.1 Parse constraints (prerequisite — C-009)

| Constraint | Why |
|---|---|
| Exactly **one** markdown table under each machine-parsed heading | the reader takes the *first* table and stops; a second sub-table is silently dropped |
| Headings verbatim, never reworded | located by exact full-line match |
| Verdict / path / qualname stay at their **existing leading column positions** | parsers read positionally; a mid-inserted column silently skips rows |
| Any `primitive` discriminator is **appended as a trailing column** | leading insertion changes the positional contract; appending is safe and makes the parse red loudly if mis-specified |
| No duplicated key in a counts table | duplicate keys silently overwrite, last-wins |

### 2.2 Per-site row (both axes — FR-007/FR-010)

| Field | Meaning | Derivation |
|---|---|---|
| `primitive` | which censused callee this row is about | mechanical |
| `rel_path` | repo-relative module path | mechanical |
| `qualname` | enclosing function/method | mechanical (AST) |
| `token` | the frozen code-token comparand for the site | mechanical |
| `root_arg` | the verbatim first argument expression | mechanical (unparse) |
| `root_class` | its semantic class (callee-normalized / caller-main-anchored / cwd-derived / worktree / coord-worktree) | **reviewer-asserted**, with a one-line provenance citation |
| `handle_form` | folded intra-function / dir-name provenance / raw | mechanical |
| `raise_or_degrade` | the **exception** axis | reviewer-asserted |
| `target_kind` | the artifact kind for a routed site | reviewer-asserted |
| `idempotent_under_seam_output` | does a composed-vs-bare handle round-trip? | test-pinned |
| `disposition` | `migrate-fail-loud` \| `stay-lenient` \| `sanction-infra` (exactly these three names) | reviewer-asserted |
| `cluster` | which work package owns it | planning |
| `rationale` | why; for preserved sites, the existing production comment is the rationale of record | reviewer-asserted |

Only `root_class`, the axis verdicts and `rationale` require human judgement; everything
else is machine-derivable, and the machine-derivable fields are what the gate reconciles.

### 2.3 Section-level records

- **Per-primitive census counts** — reconciled against a fresh AST census (live residual /
  lenient totals only; the historical pre-migration totals are preserved and **labelled as
  an audit record**, never rewritten).
- **Per-disposition counts** — published so a zero-fail-loud outcome is an explicit finding
  rather than a silently satisfied requirement.
- **Known-gap section** — for each primitive not censused by the read-side gate: which gate
  does cover it, on which axis, and the sized residual.

---

## 3. Gate state (the enforcement model)

| Element | Rule |
|---|---|
| Censused callees | the set of kind-blind primitives the AST census flags; grows from **2 to 4** this mission (the newly policed kind-blind resolver, plus the primary primitive inheriting the retired floors' guarantee) |
| Sanctioned modules | asserted-sanctioned with rationale, **never silently skipped**; non-vacuity proven **per primitive**. `core/paths.py` and `core/git_ops.py` are NOT currently sanctioned and need explicit per-site allow-list entries (FR-005 / C-003) |
| Allow-list entries | per-site content descriptors (no path blankets); **shrink-only** |
| Staleness twin-guard | an entry whose site is routed or gone **reds** until deleted |
| Alias resolution | an aliased import must not defeat the census |
| Ledger reconciliation | the ledger is **parsed**, and parsed row count equals the summed per-primitive census |
| Use-count floors | **retired** this mission (guarantee transferred); if instead re-pinned, before/after integers recorded with the reason |
| Honest bounds | wrong-kind arguments, wrapper laundering, unwired surface members, the zero-site latent sibling, foundation and seam-internal sites — each named with a size |

---

## 4. State transitions

The only lifecycle here is the migration's own sequence, and it is gated:

```text
assembler extracted (IC-00) ─┐
gates fixed (IC-01) ─────────┼─> delegation verified (IC-04) ─> callers declare kinds (IC-05)
grammar+index (IC-02) ───────┴─> sites classified (IC-03) ────┘   └─> public wrapper DELETED,
                                                                      canonicalizer drained,
                                                                      floors retired (IC-05/06)
```

- **No ledger row** may be written before the grammar/index prerequisite lands (C-009).
- **No call site** may be rewritten before the delegation is verified (C-005).
- **Floors are retired at the START of the call-site migration** — their bound is strict and breaks mid-drain — with recorded before/after (NFR-007).
- **No delegation** before the terminal assembler is extracted and the seam's PRIMARY leg re-pointed (C-005 Step 0) — otherwise the delegation recurses.
