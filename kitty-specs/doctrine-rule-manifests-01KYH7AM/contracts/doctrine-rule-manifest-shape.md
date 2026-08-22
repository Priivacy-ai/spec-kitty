# Contract: Doctrine Rule Manifest Shape

**Mission**: `doctrine-rule-manifests-01KYH7AM` | **Date**: 2026-07-27

This is a **descriptive** contract — the shape is fixed by muster's own
`SOP_RULE_MANIFEST_SCHEMA` (Ajv) and `loadAndValidateManifest`'s semantic
checks (`/home/jeroennouws/dev/garrison-hq/muster/src/adapters/openclaw-sop/manifest.ts:200-324`,
C-001: zero muster changes). This document exists so WP authors can build
each of the 14 manifest files (13 shipped + 1 control) against one written
reference, and so the CI job's steps and the manifest-authoring work can
proceed without either reading the other's source.

## File shape

```yaml
# round-trip: skip: manifest shape sketch with <placeholder> tokens and a 'binary' | 'judge' enum alternation — deliberately not a valid instance, so there is nothing to round-trip; the executable shape check is conformance/scripts/check-doctrine-manifest-completeness.mjs
version: "1.0.0"                      # required, non-empty string
sopFile: "../../src/doctrine/directives/built-in/<directive-file>"  # required, path relative to THIS file's directory
rules:
  - ruleId: "<directive-number>-r<n>"  # required, non-empty, unique WITHIN this file
    ruleText: "<verbatim or fragment>" # required, non-empty; see Rule Text below
    probeIds: []                      # required array; ALWAYS empty in this mission (C-003)
    gradingClass: "binary" | "judge"  # required enum
    aggregation: "pass-k" | "k-of-n"  # required enum
    k: 3                              # required integer >= 1
    passThreshold: 3                  # OPTIONAL, but this mission always sets it explicitly
    source:
      normative: "docs/rubric/sop-rule-taxonomy.md#<class-anchor>"  # required, non-empty
      supporting: "https://github.com/Priivacy-ai/spec-kitty/blob/<SHA>/src/doctrine/directives/built-in/<file>"  # optional, always present in this mission
```

**Deliberate deviation from the taxonomy's own citation-format spec, stated
explicitly (not silently redefined).** `sop-rule-taxonomy.md`'s own
"Citation Format for Manifest Entries" section (muster,
`docs/rubric/sop-rule-taxonomy.md:224-238`) specifies `source.normative` as
the **literal string** `"docs/rubric/sop-rule-taxonomy.md"`, with **no
anchor fragment**. Every manifest in this mission instead appends
`#<class-anchor>` (e.g. `#1-never-call-tool`, `#judge-required-rule-classes`).
This is harmless to muster's own loader (`loadAndValidateManifest`'s guard
only checks that `source.normative` is a non-empty string —
`manifest.ts:292-297` — it does not compare against the literal path) and
is arguably more precise for a human reader jumping to the exact class
section rather than the top of a long document. But it is still an
undocumented deviation from a normative document this mission cites rather
than redefines, so it is recorded here explicitly rather than left for a
future reader to notice and wonder whether it was intentional: **this
mission deviates deliberately, for readability, and the deviation does not
change any loader-observable behavior.** A future mission wanting strict
literal conformance to the taxonomy's citation format would need to strip
every `#<anchor>` suffix; this mission does not do so.

No `probes:` section is present in any of this mission's 14 files —
`loadManifestProbes` (runner.ts) treats an absent `probes` key as
`{ complianceProbes: {}, adversarialProbes: {} }`, which is exactly the
behavior an empty `probeIds: []` array on every entry requires (C-003).

## Rule Text — verbatim vs. fragment (binding constraint 1)

- **Full-line rules (35 of 45)**: `ruleText` is the rule's complete
  `integrity_rules` bullet text, copied byte-for-byte from the directive
  file (including any non-ASCII punctuation — see directive 039's Unicode
  apostrophes in `contracts/rule-classification-and-citation.md`). Never
  retype; always copy from the source file.
- **Fragment rules (10 of 45 — 042×3, 044×3, 045×4)**: `ruleText` is the
  longest contiguous substring of the rule that lies entirely on one
  physical line of the directive file's raw bytes, satisfying all four
  properties of the mission spec's fragment convention (spec.md Edge Cases:
  raw-byte substring, uniqueness, semantic identification, honest partial
  coverage). Every fragment used in this mission is listed with its exact
  text and provenance line numbers in `contracts/rule-classification-and-citation.md`,
  and each was verified via `grep -F -c '<fragment>' <directive-file>` = `1`
  during planning (research.md §3) — this exact command must be re-run and
  re-confirmed at implementation time (files are read-only inputs, but
  re-verification catches any transcription error when the fragment is
  typed into the manifest).

## Loader guards this contract must satisfy (binding constraint 3)

| Guard (`manifest.ts` line) | How this mission's manifests satisfy it |
|---|---|
| Duplicate `ruleId` (`:287-290`) | Sequential `<directive>-r<n>` numbering, unique within each file by construction; checked per-file only (the loader never sees two manifests at once). |
| Empty `source.normative` (`:292-297`) | Every entry's `source.normative` is a non-empty `docs/rubric/sop-rule-taxonomy.md#<anchor>` string (`contracts/rule-classification-and-citation.md`). |
| `pass-k` with `passThreshold !== k` (`:299-308`) | Every binary entry sets `passThreshold: 3` and `k: 3` — always equal. |
| `confirm-before-destructive` without `confirmationKind` (`:310-320`) | **No entry in any of this mission's manifests sets an `assertionKind` field at all** — the guard's condition (`entryAny["assertionKind"] === "confirm-before-destructive"`) is `undefined === "confirm-before-destructive"` → always `false`. The `confirm-before-destructive` *taxonomy class* is cited in `source.normative` prose for `034-r2`/`035-r2`, but that is a documentation string, not the structural `assertionKind` field the guard inspects (research.md §6). |

## Control manifest — the one exception to "13 shipped manifests"

`conformance/doctrine/control/045-drifted.yaml` — same shape as above, one
entry, `sopFile` pointing at the **real** `045-prs-only-and-read-intent.directive.yaml`
(three directory levels up: `../../../src/doctrine/directives/built-in/...`),
with a **deliberately mutated** `ruleText` ("must never run" in place of the
real file's "must not run" — see `contracts/doctrine-drift-gate-contract.md`
for the exact string and its `grep -F -c` = `0` verification). This manifest
is excluded from FR-004's "must be clean" gate and is instead asserted, by
CI, to **contain** a `RULE_DRIFT` finding (FR-005/AC-3, inverted polarity).

## Directory layout

```
conformance/doctrine/
├── 001-architectural-integrity-standard.yaml
├── 010-specification-fidelity-requirement.yaml
├── 018-doctrine-versioning-requirement.yaml
├── 028-search-tool-discipline.yaml
├── 029-agent-commit-signing-policy.yaml
├── 030-test-and-typecheck-quality-gate.yaml
├── 033-targeted-staging-policy.yaml
├── 034-test-first-development.yaml
├── 035-bulk-edit-occurrence-classification.yaml
├── 039-lynn-cole-engineering-culture.yaml
├── 042-common-docs.yaml
├── 044-canonical-sources-and-unification.yaml
├── 045-prs-only-and-read-intent.yaml
├── README.md                         # FR-006: mapping table + coverage roadmap
└── control/
    └── 045-drifted.yaml              # FR-005: discrimination control
```

Every shipped manifest's basename mirrors its directive's own filename stem
(minus `.directive`), a deliberate 1:1 naming convention so
`check-doctrine-manifest-completeness.mjs` (`contracts/
doctrine-manifest-completeness-contract.md`) can pair each manifest with
its directive without a lookup table.
