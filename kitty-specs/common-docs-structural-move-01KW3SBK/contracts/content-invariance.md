# Contract: ADR Content-Invariance Check (FR-003, C-002, NFR-001)

The 117-unique-ADR conversion changes **only location and header format** — never decision content
(C-002). This check is the proof. It is the gate that distinguishes a safe header-format change from a
content mutation, and it must be **false-green-proof** (a re-render comparison would pass on
whitespace normalisation and miss a real edit).

---

## Method: body-minus-header byte-identity

For each ADR being converted:

1. **Pre-image:** read the original ADR file; strip the original header block — one of **three**
   formats the **three parsers** consume: (a) markdown-table, (b) bold-inline `**Status:** …`,
   (c) **dash-bullet `- Status:` / `- Date:`** (e.g.
   `architecture/2.x/adr/2026-04-15-2-explicit-empty-charter-selections-remain-empty.md`) — and the
   leading title line; retain the remaining **decision body** verbatim. **The dash-bullet boundary:**
   the header block ends at the last consecutive `- Status:`/`- Date:`/`- Deciders:`-style bullet at
   the top of the file; the decision body begins at the first non-bullet, non-blank line after it.
   Bullets *inside the body* (after a blank line / heading) are body, not header.
2. **Post-image:** read the converted ADR file; strip the new YAML frontmatter block **by reusing
   `_inventory.parse_frontmatter`** (do NOT fork a second frontmatter parser — the post-image strip
   must use the same canonical parser the inventory uses); retain the remaining **decision body**
   verbatim.
3. **Assert:** `bytes(pre_body) == bytes(post_body)` — **byte-identical**, not re-rendered, not
   normalised.

```
invariant(adr):  body_minus_header(pre)  ==  body_minus_frontmatter(post)   # byte-for-byte
```

## Scope

| In scope | Out of scope |
|----------|--------------|
| All **117 unique** ADRs (97 era + 20 era-less migrated to `adr/3.x/`) | The **reconciliation ADR self-amendment** (FR-013) — a **sanctioned** prose edit of its own Neutral note; explicitly excluded from this check (C-002 protects *moved decision-records*, not this self-amendment) |
| Header → bare-`status` YAML frontmatter (`title`/`status`/`date`) | The 47 **byte-identical flat mirrors** — dropped losslessly (identical to their era originals), not converted |

## Coupling

- **Three parsers** (markdown-table + bold-inline + **dash-bullet**) produce the post-image header;
  the body they leave untouched is what this check guards. **Live census: 70 bold-inline / 46 table /
  1 dash-bullet = 117** (the spec's "~12 table / ~34 bold" was wrong and missed the dash-bullet
  format — a missing 3rd branch would convert that ADR status-less and block the ratchet).
- **Census pairing:** the check runs over the full 117 — a missing ADR (count < 117) is itself a
  failure (NFR-001: 0 lost). The 47 mirrors are proven byte-identical to their originals *before* the
  drop, so "dropped" is provably "not lost".

## Invariant

> **Content-invariance:** for every converted ADR, the decision body is byte-identical pre/post; the
> count of unique ADRs post-move == **117**; **0 lost, 0 content-altered** (NFR-001, SC-002).
