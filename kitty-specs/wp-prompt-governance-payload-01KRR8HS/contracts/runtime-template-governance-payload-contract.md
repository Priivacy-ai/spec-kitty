# Contract: `## Governance Payload Contract` section in runtime templates

**Mission**: `wp-prompt-governance-payload-01KRR8HS`
**Surface**: `src/specify_cli/missions/software-dev/command-templates/implement.md`, `src/specify_cli/missions/software-dev/command-templates/review.md`
**FRs covered**: FR-005
**ATDD anchors**: `TestImplementTemplateForbidClauseIsHonest::test_template_either_drops_forbid_or_guarantees_governance_payload`

---

## 1. Purpose

The runtime `implement.md` template at lines 68-71 today says:

> The output of `spec-kitty agent action implement ...` is the authoritative
> work package prompt and execution context. Do **not** separately call
> `spec-kitty charter context` or rummage through unrelated files looking
> for a "newer" prompt unless the command output tells you to.

That clause is defensible only when the prompt actually carries the governance
bodies it implicitly claims. The mission preserves the clause (per C-003 option
b — "the forbid clause remains but is paired with a Governance Payload Contract
section") and adds the contract section so the clause becomes honest. The
review template (`review.md`) gains the parallel section for reviewer surfaces.

---

## 2. Section schema

The section MUST be added as a top-level `## Governance Payload Contract`
heading. It MUST appear after the forbid clause and before
`## Execution Steps`. The body has four fixed blocks in this order:

```markdown
## Governance Payload Contract

The prompt above is guaranteed to carry the following surfaces. Trust the prompt;
do not consult external governance sources unless explicitly cited by a fetch
command + when-doing rule in the prompt.

**Guaranteed bodies** (verbatim in the prompt when under the token budget):

- Terminology Canon — from `.kittify/charter/charter.md`
- Code Review Checklist — from `.kittify/charter/charter.md`
- Regression Vigilance — from `.kittify/charter/charter.md`
- (any additional action-critical sections the mission declares)

**Guaranteed citations** (catalog IDs always present in the prompt):

- Every `DIRECTIVE_NNN` declared in the loaded agent profile's
  `directive-references` list.
- Every tactic-id declared in the loaded agent profile's `tactic-references`
  list.

**Guaranteed authority pointers** (path + when-doing conditional):

- `glossary/contexts/` — canonical terminology (consult when you encounter
  a domain term in the diff).
- `architecture/2.x/adr/` — architectural intent (consult when you change a
  structural boundary).
- (any additional paths declared in the charter's `authority_paths:` block).

**Fetch commands** (the prompt may substitute these for bodies that exceed the
token budget; when a fetch command appears, an accompanying
`When you <verb>, run this and apply` line specifies the trigger):

- `spec-kitty charter context --include directive:DIRECTIVE_NNN`
- `spec-kitty charter context --include tactic:<id>`
- `spec-kitty charter context --include section:<slug>`
```

---

## 3. Block-by-block requirements

| Block | Required keys | Source of truth |
|---|---|---|
| Guaranteed bodies | Bulleted list of action-critical section names. Minimum three for `software-dev`: Terminology Canon, Code Review Checklist, Regression Vigilance. | Mission action-critical section configuration; defaults documented in [data-model.md](../data-model.md). |
| Guaranteed citations | Two bullets describing the two profile-cited surfaces (directives, tactics). | `AgentProfile.directive_references` / `AgentProfile.tactic_references`. |
| Guaranteed authority pointers | Bulleted list naming each authority path + a one-sentence "consult when …" conditional. Minimum two: `glossary/contexts/`, `architecture/2.x/adr/`. | `DoctrineSelectionConfig.authority_paths` + filesystem defaults. |
| Fetch commands | Bulleted list of the three canonical fetch-command forms. | The resolver's fetch-stanza format documented in [charter-context-resolver.md](charter-context-resolver.md). |

---

## 4. Detection regex (acceptance gate)

The architectural test
`tests/architectural/test_template_governance_payload_contract.py` (new, added
in WP06) MUST detect the section presence using this regex:

```python
re.compile(
    r"##\s+Governance\s+Payload\s+Contract\b",
    re.IGNORECASE,
)
```

The ATDD test at
`tests/specify_cli/next/test_wp_prompt_governance_contract.py::TestImplementTemplateForbidClauseIsHonest::test_template_either_drops_forbid_or_guarantees_governance_payload`
already accepts any of three phrasings:

```python
re.compile(
    r"governance\s+payload\s+contract|"
    r"the\s+prompt\s+is\s+guaranteed\s+to\s+include|"
    r"governance\s+sections?\s+below\s+contain\s+the\s+rule\s+bodies",
    re.IGNORECASE,
)
```

The chosen heading text `Governance Payload Contract` matches the primary
phrasing.

---

## 5. Review template adaptation

The review template's section uses the same four-block structure with reviewer-
oriented guaranteed-citations:

| Block | Reviewer-specific content |
|---|---|
| Guaranteed bodies | Same three sections (Terminology Canon, Code Review Checklist, Regression Vigilance). |
| Guaranteed citations | Every `DIRECTIVE_NNN` and tactic-id declared by the loaded **reviewer** profile (e.g. `reviewer-renata` declares DIRECTIVE_032 — Conceptual Alignment, and `language-driven-design`). |
| Guaranteed authority pointers | Same as implement. |
| Fetch commands | Same as implement. |

The text MUST also include a sentence in the "Guaranteed citations" block such
as:

> When you assess a WP that renames identifiers or terms, the prompt cites
> DIRECTIVE_032 (Conceptual Alignment) by ID; consult its rule body inline or
> via the paired fetch command and apply.

This satisfies the journey-2 user story and gives the reviewer-template's
fetch-with-conditional check a deterministic anchor.

---

## 6. Failure modes

| Failure | Behaviour |
|---|---|
| Section is missing from the template | Architectural test fails; ATDD test 5 fails. WP06 is the gate. |
| Section is present but a block is missing or empty | Architectural test fails with the specific block name. |
| Section is present but the guaranteed-bodies list does not include the action-critical sections the resolver actually emits | Architectural test fails (mismatch between template-promised and resolver-emitted surfaces). |
| Charter resolver emits a new section not listed in the template | Architectural test fails; template must be updated in the same change. |

---

## 7. Drift prevention

To prevent template drift from resolver behaviour, the architectural test
parses both:

1. The template's `## Governance Payload Contract` section (the promise).
2. The resolver's output for a fixture mission with a known profile (the
   reality).

It asserts every guaranteed surface listed in the template is present in the
resolver output. The reverse is intentionally not enforced — the resolver may
emit additional surfaces (e.g. action-doctrine list) without forcing a template
update.
