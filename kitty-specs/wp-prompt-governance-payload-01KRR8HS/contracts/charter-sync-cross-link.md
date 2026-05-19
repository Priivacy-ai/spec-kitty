# Contract: `charter sync` cross-link emission

**Mission**: `wp-prompt-governance-payload-01KRR8HS`
**Surface**: `charter.sync.sync` (via `charter.extractor.Extractor._extract_directives`)
**FRs covered**: FR-006
**ATDD anchors**: `TestCharterDirectiveNamespaceCrossLink::test_charter_sync_emits_cross_link_when_body_cites_catalog_id`

---

## 1. Input

The input is the raw markdown body of a charter section that the extractor
classifies as a directive section (any section whose heading lower-cased
matches one of `directive`, `constraint`, `rule` via
`Extractor._classify_section`).

Each numbered item inside such a section becomes a `Directive`. The extractor's
job in this mission is to detect, **inside that numbered-item body**, citations
to:

| Citation kind | Detection regex | Filter |
|---|---|---|
| Doctrine-catalog directive ID | `\bDIRECTIVE_(\d{3})\b` | None — every match counts. |
| Tactic ID (kebab-case slug) | `\b([a-z][a-z0-9]*(?:-[a-z0-9]+){1,4})\b` | Match counts ONLY when `DoctrineService.tactics.get(slug)` returns a non-None record. |

The tactic-id filter prevents false positives on incidental kebab-case words
(e.g. `pre-commit-hooks` is not a tactic ID; `language-driven-design` is).

---

## 2. Output

The generated `.kittify/charter/directives.yaml` entry MUST gain a structured
`references:` list when the body contained at least one catalog citation.

### Example input charter body

```markdown
### Code Review Checklist

- The WP diff respects the agent profile's directive-references.
- Terminology in code and docs aligns with the project glossary
  (DIRECTIVE_032 — Conceptual Alignment).
- Reviewers detect terminology drift early using the language-driven-design tactic.
```

### Example output `directives.yaml` entry

```yaml
directives:
  - id: DIR-005
    title: "Code Review Checklist (terminology alignment)"
    description: |
      Terminology in code and docs aligns with the project glossary
      (DIRECTIVE_032 — Conceptual Alignment).
    severity: warn
    references:
      - DIRECTIVE_032
      - language-driven-design
```

### Field ordering

When `references:` is emitted, IDs MUST appear in the order they appeared in the
body (first occurrence wins; duplicates are de-duplicated while preserving
position). This makes diffs deterministic and reviewable.

When the body contains no citation, `references:` is omitted entirely (not
emitted as an empty list) so existing serialized fixtures stay byte-identical.

---

## 3. Failure modes

| Failure | Behaviour |
|---|---|
| Body contains a malformed citation (e.g. `DIRECTIVE_12` without three digits) | No match; no entry added to `references:`. |
| Tactic-id-like slug appears but `DoctrineService.tactics.get(slug)` returns None | Slug is not added to `references:`. Tactic-id filter does its job. |
| `DoctrineService` cannot be constructed (e.g. shipped catalog missing) | Detection regex for directives still runs; the tactic-id detector silently emits no tactic references. `charter sync` does not error. |
| Multi-line citation across a numbered-item body | Detection runs on the joined body string of each numbered item; line breaks are not significant to the regex. |
| Charter sync run on a charter that pre-dates this mission (no inline citations) | `references:` field is never emitted; output is byte-identical to today (NFR-005). |

---

## 4. Backward compatibility

- Pre-mission `directives.yaml` files load identically (the new `references:`
  field is optional with `default=[]`).
- A charter body that contains no citation produces output byte-identical to
  pre-mission output.
- A consumer that does not know about `references:` (e.g. an older spec-kitty
  install) ignores the field — Pydantic's `model_validate` accepts unknown
  fields by default for `Directive`.

---

## 5. Downstream consumption

`build_charter_context` consumes the `references:` field as follows: when a
`DIR-NNN` entry is included in the resolved action context (by being in
`governance.doctrine.selected_directives` or by matching the action's directive
canon), the resolver iterates `directive.references` and additionally surfaces
the catalog body — either inline or via the fetch + when-doing stanza — in
section 4 ("Action-Critical Charter Sections") or section 5 ("Profile-Cited
Directives") of the rendered text. The same applies to tactic-id references,
which are surfaced via `DoctrineService.tactics`.

This downstream consumption is documented in
[charter-context-resolver.md](charter-context-resolver.md).
