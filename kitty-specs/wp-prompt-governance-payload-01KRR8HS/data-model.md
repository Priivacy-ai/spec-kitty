# Data Model — WP-Prompt Governance Payload Completeness

**Mission**: `wp-prompt-governance-payload-01KRR8HS` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

This document specifies the new and amended data shapes the mission introduces. All
shapes are additive; existing producers and consumers that do not know about the
new fields continue to behave exactly as today (NFR-005).

---

## 1. `ResolverInputDeclaration` — fenced YAML block in `charter.md`

**Producer**: charter maintainer (human) writes the block into
`.kittify/charter/charter.md`.
**Consumer**: `charter.extractor.Extractor._merge_doctrine_selection` extends
`GovernanceConfig.doctrine` with the parsed values.

### Schema (YAML)

```yaml
template_set: software-dev-default          # required for the FR-009 contract
available_tools:                            # required for the FR-009 contract
  - git
  - spec-kitty
  - pytest
  - mypy
  - ruff
authority_paths:                            # optional (FR-008); extends defaults
  - glossary/contexts/
  - architecture/2.x/adr/
  - docs/runbooks/
```

### Where it lives in the charter body

Inside a fenced ```` ```yaml ```` block under a heading such as
`## Charter Resolution Hints` (matching the test fixture at
`tests/specify_cli/next/test_wp_prompt_governance_contract.py:114-119`). The
extractor scans every section's `yaml_blocks`, so the heading name is not
load-bearing — only the keys are.

### Field semantics

| Field | Type | Required | Meaning |
|---|---|---|---|
| `template_set` | string | yes (for FR-009) | The doctrine template set the project consumes (e.g. `software-dev-default`). Suppresses the `Template set not selected in charter; fallback … applied` diagnostic. |
| `available_tools` | list[string] | yes (for FR-009) | The CLI tool registry the project intends to expose to agents. Suppresses the `No available_tools selection provided; using runtime tool registry fallback` diagnostic. |
| `authority_paths` | list[string] | no (FR-008) | Repository-relative directories surfaced as authority pointers in the prompt's "Project authority paths" block, additive to the defaults `glossary/contexts/` and `architecture/2.x/adr/`. |

### Pydantic mapping

`charter.schemas.DoctrineSelectionConfig` gains:

```python
class DoctrineSelectionConfig(BaseModel):
    selected_paradigms: list[str] = []
    selected_directives: list[str] = []
    selected_tactics: list[str] = []
    available_tools: list[str] = []        # already present
    template_set: str | None = None         # already present
    authority_paths: list[str] = []        # NEW
```

---

## 2. `CatalogReference` — cross-link field on a `Directive`

**Producer**: `charter.extractor.Extractor._extract_directives` detects citations
of `DIRECTIVE_\d{3}` and tactic-id slugs inside a directive's `description` body
and lifts them into a structured field.
**Consumer**: `charter.context.build_charter_context` resolves the catalog IDs
via `DoctrineService.directives.get(id)` / `tactics.get(id)` and surfaces the
catalog body (or fetch + when-doing) when the charter-side `DIR-NNN` is included
in a resolved action context.

### Schema (YAML, added to existing `Directive` entries in `.kittify/charter/directives.yaml`)

```yaml
directives:
  - id: DIR-005
    title: "Code Review Checklist (terminology alignment)"
    description: "Terminology in code and docs aligns with the project glossary (DIRECTIVE_032 — Conceptual Alignment)."
    severity: warn
    references:                       # NEW
      - DIRECTIVE_032                 # catalog directive cited inline above
```

### Pydantic mapping

`charter.schemas.Directive` gains:

```python
class Directive(BaseModel):
    id: str                            # e.g. "DIR-005"
    title: str
    description: str
    severity: Literal["info", "warn", "error"] = "warn"
    references: list[str] = []         # NEW — catalog IDs cited by description
```

### Detection regex

| Citation kind | Regex | Example match |
|---|---|---|
| Doctrine-catalog directive | `\bDIRECTIVE_(\d{3})\b` | `DIRECTIVE_032` |
| Tactic id (kebab-case slug) | `\b([a-z][a-z0-9]*(?:-[a-z0-9]+){1,4})\b` filtered against `DoctrineService.tactics` registry | `language-driven-design` |

The tactic-id detection is registry-filtered (a match only counts as a reference
if `DoctrineService.tactics.get(slug)` returns a record), preventing false
positives on incidental kebab-case words.

### Backward compatibility

When the directive body contains no citation, `references: []` (or omitted on
serialization). Existing consumers that do not know `references:` ignore the
field and behave exactly as today (NFR-005).

---

## 3. `CharterContextResult.text` — required sections when `profile=` is passed

`CharterContextResult` (dataclass at `src/charter/context.py:36-45`) is
unchanged in shape; only the rendered `text` field gains structure. When
`build_charter_context(repo_root, action=<bootstrap-action>, profile=<id>)` is
called with a known profile against a project whose charter and doctrine catalog
are present, `result.text` MUST contain the following sections in order:

| # | Section header | Required content | Source data |
|---|---|---|---|
| 1 | `Charter Context (Bootstrap):` | Source path + first-load guidance. | `charter.md` path + state-bundle. |
| 2 | `Policy Summary:` | Up to 8 bullet items from the `## Policy Summary` section. | `_extract_policy_summary(charter_content)`. |
| 3 | `Project authority paths:` | At minimum `glossary/contexts/` and `architecture/2.x/adr/` when those directories exist; additionally every path in `governance.doctrine.authority_paths`. Each line carries a one-sentence "When you …, …" conditional. | Filesystem scan + `DoctrineSelectionConfig.authority_paths`. |
| 4 | `Action-Critical Charter Sections (<action>):` | For each section in the action-critical set (defaults for `software-dev`: Terminology Canon, Code Review Checklist, Regression Vigilance), either the verbatim body or the fetch + when-doing stanza (when token-budget triggered). | `charter.md` body, sliced by heading. |
| 5 | `Profile-Cited Directives (<profile-id>):` | For each `DIRECTIVE_NNN` in `profile.directive_references`, an entry of the form `- DIRECTIVE_NNN: <title> — <rationale or intent>`. Verbatim body inlined when under budget; otherwise replaced with the fetch + when-doing stanza. | `AgentProfileRepository` + `DoctrineService.directives`. |
| 6 | `Profile-Cited Tactics (<profile-id>):` | Same shape as section 5, for `profile.tactic_references`. | `AgentProfileRepository` + `DoctrineService.tactics`. |
| 7 | `Action Doctrine (<action>):` | Existing resolver-driven `Directives:` / `Tactics:` lists. May overlap section 5/6 by ID; that is intentional and harmless. | DRG resolver. |
| 8 | `Reference Docs:` | Up to 10 entries from `.kittify/charter/references.yaml`, filtered for the action. | Existing reference loader. |

Sections 3, 4, 5, 6 are new. Sections 1, 2, 7, 8 exist today.

When `profile=None` (or unknown), sections 5 and 6 are omitted entirely. Section
3 still appears (it is profile-independent). Section 4 still appears (it is
action-driven, profile-independent).

### Fetch + when-doing stanza format

A consistent, parseable shape so the executing agent can grep for it:

```
Run: spec-kitty charter context --include <selector>
When you <action-verb conditional>, run this command and apply the returned rule.
```

`<selector>` is one of:

- `directive:DIRECTIVE_NNN`
- `tactic:<tactic-id>`
- `section:<kebab-cased-heading-slug>`

`<action-verb conditional>` derives from the section/directive/tactic kind:

- Directive — derived from the directive's `applies-when` or, when missing,
  a default `apply a code change` clause.
- Tactic — derived from the tactic's `when` field.
- Charter section — keyword map (e.g. `Terminology Canon` → "rename or
  introduce a term", `Regression Vigilance` → "perform a terminology cutover",
  `Code Review Checklist` → "prepare a WP for review").

---

## 4. `GovernancePayloadContract` — schema of the runtime-template section

A new section the runtime command templates carry (`implement.md`, `review.md`).
This is a documentation schema (not a Pydantic model); it pins what the prompt
guarantees so the forbid clause becomes honest.

### Template-side schema

```markdown
## Governance Payload Contract

The prompt above is guaranteed to carry the following surfaces. Trust the prompt;
do not consult external governance sources unless explicitly cited by a fetch
command + when-doing rule in the prompt.

**Guaranteed bodies** (verbatim in the prompt when under the token budget):

- Terminology Canon (from `.kittify/charter/charter.md`)
- Code Review Checklist (from `.kittify/charter/charter.md`)
- Regression Vigilance (from `.kittify/charter/charter.md`)

**Guaranteed citations** (catalog IDs always present):

- Every `DIRECTIVE_NNN` in the loaded agent profile's `directive-references`.
- Every tactic-id in the loaded agent profile's `tactic-references`.

**Guaranteed authority pointers** (path + when-doing conditional):

- `glossary/contexts/` — canonical terminology
- `architecture/2.x/adr/` — architectural intent
- (any additional paths from charter `authority_paths:`)

**Fetch commands** (the prompt may substitute these for bodies that exceed the
token budget):

- `spec-kitty charter context --include directive:DIRECTIVE_NNN`
- `spec-kitty charter context --include tactic:<id>`
- `spec-kitty charter context --include section:<slug>`

When a fetch command appears, an accompanying `When you <verb>, run this and
apply` line specifies the trigger condition.
```

The schema is enforced by a new architectural test
(`tests/architectural/test_template_governance_payload_contract.py`) that
verifies the template section lists every guaranteed surface the resolver in
fact emits.

### Field order

Order is contractual:

1. Guaranteed bodies (verbatim sections from charter).
2. Guaranteed citations (profile-cited catalog IDs).
3. Guaranteed authority pointers.
4. Fetch commands (the fall-back surface).

Implementer and reviewer templates carry the same four-block structure; only the
specific guaranteed-bodies / guaranteed-citations lists differ.

---

## 5. WP frontmatter — `agent_profile` field (existing, newly load-bearing)

The `agent_profile:` field already exists in WP frontmatter (see
`tests/specify_cli/next/test_wp_prompt_governance_contract.py:130-148` for
canonical examples). The mission makes it load-bearing in the prompt-build path.
No schema change; only the read site at
`src/specify_cli/next/prompt_builder.py:125` (`wp_meta, _ = read_wp_frontmatter(wp_files[0])`)
now also extracts `wp_meta.agent_profile` and threads it through.

| Field | Type | Producer | Consumer |
|---|---|---|---|
| `agent_profile` | string \| null | `/spec-kitty.tasks` and `agent profile` selection at finalize time. | `_build_wp_prompt` → `_governance_context` → `build_charter_context`. |

When `agent_profile` is null or missing, the prompt build proceeds with
`profile=None`; sections 5 and 6 of the resolved context are omitted.

---

## 6. Backwards-compatibility envelope

The mission's changes form a single envelope of additive shapes:

| Shape | Change kind | Pre-mission behaviour on missing data |
|---|---|---|
| Charter fenced YAML block | additive | Same fallback diagnostic emitted today. |
| `Directive.references` | additive field on existing entry | Empty list. |
| `DoctrineSelectionConfig.authority_paths` | additive field | Empty list; defaults still surface in the prompt. |
| `build_charter_context(profile=)` | load-bearing on a parameter already in the signature | When `profile=None`, output is byte-identical to today. |
| Template `## Governance Payload Contract` section | additive section in a markdown file | Pre-mission templates lack the section; existing agents ignore unknown sections. |

No producer is removed; no consumer is forced to upgrade. NFR-005 is satisfied
by construction.
