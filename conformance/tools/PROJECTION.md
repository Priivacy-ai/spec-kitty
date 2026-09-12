# `profile2soul.py` — Field Mapping and Fidelity Loss

Mission: `crosslayer-composition-suite-01KYJA33` (M7), WP01, FR-002.

`conformance/tools/profile2soul.py` deterministically projects a spec-kitty
built-in agent profile (`packs/built-in/agent_profiles/*.agent.yaml`)
into an RFC-1-conformant `Soul.md` document. This document states exactly
what the projection carries, what it fabricates, and what it structurally
cannot carry at all.

**C-003 note (read before editing this file):** the fabricated-defaults
table below is purely descriptive — it records *that* these values are
invented and *what* the frozen values are. It never asserts, and must never
be edited to assert, that a fabricated value is "correct," or that a
check's pass/fail result depended on one. There is no correct value for a
field the source data has no opinion about; C-003 forbids grading these
fields at all.

## Field Mapping (carried fields)

These fields exist in the source profile and are mapped directly into the
projected `Soul.md`. None of them appear in the Fidelity Loss table below.

| Source field (`*.agent.yaml`) | Destination | Notes |
|---|---|---|
| `profile-id` | Front matter `id` | Direct copy. |
| `name` | Front matter `name`, and the body's top-level heading | Direct copy. |
| `description` | Body, `## Description` section | Direct copy. |
| `purpose` | Body, `## Purpose` section | Direct copy, whitespace-stripped (the source YAML uses a folded `>` scalar). |
| `initialization-declaration` | Body, `## Identity Declaration` section | Direct copy, whitespace-stripped. This is the profile's own first-person identity/boundary statement — instructional content, carried in full, never dropped. |
| `specialization.primary-focus` | Body, `## Specialization` / `### Primary Focus` | Direct copy. |
| `specialization.avoidance-boundary` | Body, `## Specialization` / `### Avoidance Boundary` | Direct copy. |

Per `composition.ts`'s `resolvePersonaLayer` (muster, pinned commit
`624edd6dddedb86fb89f13084510f02b5a2c7d25`), only the document's **body**
(everything after the closing `---` of the front matter) ever reaches
`layerTexts` — the map `contradiction-lint.ts` actually scans for
contradictions. The front-matter fields below (fabricated) are never seen
by that lint; they are only ever consulted, structurally (presence/shape,
not specific values), by RFC-1 strict-mode resolution.

## Fabricated Defaults (frozen table)

RFC-1's Soul.md front matter (Appendix E's JSON Schema, `kind: soul`
branch) requires a keyspace no spec-kitty agent profile carries any data
for at all: `soul_spec`, `locale`, an object `composition` block, a
`profiles` list that must include `"default"` (§9), an object
`profile_overrides`, an object `values` block, a `voice` block (four
required integers plus a required `formatting` enum), an `interaction`
block (four required enums), a `safety` block (three required enums), and
an object `extensions` block. `profile2soul.py` fabricates these from the
frozen table below — identical for every profile projected, never varied
per-profile, never re-derived. If this table is ever changed, both this
document and `profile2soul.py`'s own `FABRICATED_*` constants must be
updated together in the same change.

**Structural correction (post-approval remediation)**: the previous
revision of this table fabricated `composition`, `profiles`,
`profile_overrides`, `values`, and `extensions` as empty lists (`[]`), and
fabricated `voice`/`interaction`/`safety` with keys that do not match
Appendix E's `required` arrays for those blocks. Appendix E's schema
requires `composition`/`profile_overrides`/`values`/`extensions` to be
**objects**, not arrays; `voice` requires `formality`/`warmth`/`verbosity`/
`jargon` (integers) and `formatting` (enum); `interaction` requires
`clarifying_questions`/`uncertainty`/`disagreement`/`confirmations`
(enums); `safety` requires `refusal_style`/`privacy`/`speculation`
(enums); and §9 requires `profiles` to include `"default"`. None of this
was checked against muster's real parser before this correction — see the
`tests/cross_cutting/test_crosslayer_wp01_persona_rfc1_conformance.py` test
(originally authored under `tests/conformance/`, relocated so a CI gate
actually selects it — see that module's own docstring), which runs each
committed persona through `muster check --json` and would have caught this.
The table below is the corrected, structurally-valid version.

| Front-matter field | Frozen value | Fabricated because |
|---|---|---|
| `soul_spec` | `"1.0"` | RFC-1 format-version tag; no source-profile equivalent. |
| `locale` | `en-US` | No spec-kitty agent profile carries a locale field. |
| `composition.extends` | `[]` (empty list) | RFC-1 structural requirement only; this mission never populates persona composition. |
| `composition.mixins` | `[]` (empty list) | Same. |
| `composition.merge_policy` | `standard` (enum) | Appendix E requires this key; `standard` is the schema's only enum member. |
| `profiles` | `["default"]` | §9 requires `profiles` to include `"default"`; no source-profile equivalent exists to derive a value from. |
| `profile_overrides` | `{}` (empty object) | No source-profile override data exists. |
| `values.priorities` | `[]` (empty list) | Appendix E requires this key inside the `values` object; no source-profile equivalent exists. |
| `voice.formality` | `50` (0-100 int) | RFC-1 requires this integer; no source equivalent exists. |
| `voice.warmth` | `50` (0-100 int) | Same. |
| `voice.verbosity` | `50` (0-100 int) | Same. |
| `voice.jargon` | `50` (0-100 int) | Same. |
| `voice.formatting` | `plain` (enum) | RFC-1 requires this enum; no source equivalent exists. |
| `interaction.clarifying_questions` | `when_ambiguous` (enum) | RFC-1 requires this enum; no source equivalent exists. |
| `interaction.uncertainty` | `explicit` (enum) | Same. |
| `interaction.disagreement` | `neutral` (enum) | Same. |
| `interaction.confirmations` | `implicit` (enum) | Same. |
| `safety.refusal_style` | `explain` (enum) | RFC-1 requires this enum; no source-profile safety block exists. |
| `safety.privacy` | `normal` (enum) | Same. |
| `safety.speculation` | `mark` (enum) | Same. |
| `extensions` | `{}` (empty object) | RFC-1 structural requirement only; this mission never populates extensions. |

## Generated-header contract

Every projected `Soul.md` begins with a literal `---` line (RFC-1 §3.1.1
requires the document's first line to be exactly `---` — a leading comment
before it is not tolerated by muster's front-matter extractor, in either
mode), immediately followed by exactly one header comment line matching
the pattern `^#.*generated:\s*true`:

```
---
# generated: true, source-hash: sha256:<hex-digest-of-source-profile-bytes>
soul_spec: "1.0"
...
```

**Structural correction**: the previous revision of this projector emitted
the `# generated: true, ...` line *before* the opening `---`, which fails
RFC-1 §3.1.1 (the document's literal first line must be `---`) against
muster's real, shipped parser (both `src/adapters/rfc1/frontmatter.ts`'s
`extractFrontMatter` and `src/crosslayer/composition.ts`'s
`parseSoulDocumentFromText` require this, with no branch that tolerates a
leading comment). The corrected placement — the comment as the front
matter block's own first line, immediately after the opening `---` — is a
YAML comment (ignored by any YAML parser processing the block) and
satisfies §3.1.1 while still exposing the same provenance information.

`<hex-digest-of-source-profile-bytes>` is a SHA-256 hash of the *source*
profile YAML file's raw bytes — a pure function of that file's content,
never of wall-clock time. This exact shape is C-003's own textual-audit
anchor (spec.md): the reviewer-facing `grep` pattern that excludes this
line from a fabricated-field-citation scan depends on it. Do not vary this
shape (e.g. do not reorder the comment's fields, drop the leading `#`, or
change `generated: true`'s spacing) without checking spec.md's C-003
verification command still matches.

## Fidelity Loss

These fields exist in the source `*.agent.yaml` profile but have **no
RFC-1 Soul.md key to carry them into at all** — the projection structurally
cannot preserve them, not merely chooses not to:

- `capabilities` — RFC-1 has no capability-list concept.
- `routing-priority` — RFC-1 has no dispatch/routing concept.
- `context-sources` — RFC-1 has no doctrine-layer/context-source concept.
- `directive-references` — RFC-1 has no directive-citation concept.
- `tactic-references` — RFC-1 has no tactic-citation concept.

The fields carried by the mapping above (the profile's own identity/purpose/
description/specialization prose — see the "Field Mapping (carried fields)"
table at the top of this document) are **not** listed here — they are
mapped into the body, not dropped. Their absence from this table is
intentional and load-bearing, checked verbatim by FR-002's own verification
command.
