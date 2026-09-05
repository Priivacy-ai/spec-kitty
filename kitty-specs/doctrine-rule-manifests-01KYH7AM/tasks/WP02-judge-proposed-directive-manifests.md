---
work_package_id: WP02
title: Judge-proposed directive manifests (001, 010, 039, 044)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- C-001
- C-003
planning_base_branch: kitty/mission-doctrine-rule-manifests
merge_target_branch: kitty/mission-doctrine-rule-manifests
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-doctrine-rule-manifests. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-doctrine-rule-manifests unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-doctrine-rule-manifests-01KYH7AM
base_commit: abe912f01a9ed75ae8102e018eba0ad7905499e4
created_at: '2026-07-27T15:34:17.877074+00:00'
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
history: []
agent_profile: node-norris
authoritative_surface: conformance/doctrine/
create_intent:
- conformance/doctrine/001-architectural-integrity-standard.yaml
- conformance/doctrine/010-specification-fidelity-requirement.yaml
- conformance/doctrine/039-lynn-cole-engineering-culture.yaml
- conformance/doctrine/044-canonical-sources-and-unification.yaml
execution_mode: code_change
owned_files:
- conformance/doctrine/001-architectural-integrity-standard.yaml
- conformance/doctrine/010-specification-fidelity-requirement.yaml
- conformance/doctrine/039-lynn-cole-engineering-culture.yaml
- conformance/doctrine/044-canonical-sources-and-unification.yaml
role: implementer
tags: []
tracker_refs: []
---

# WP02 — Judge-proposed directive manifests (001, 010, 039, 044)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the
frontmatter, and behave according to its guidance before parsing the rest of
this prompt.

- **Profile**: `node-norris`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the
best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Hand-author 4 SOP rule manifests under `conformance/doctrine/` for the 4
"proposed judge" directives (001, 010, 039, 044) — 19 rule entries total —
same shape and citation discipline as WP01's 9 trace-decidable manifests,
but with a materially different taxonomy-fit story: **21 of this mission's
45 rules are UNMAPPED (judge-fallback)**, and **17 of this WP's 19 rules are
among them** — this WP is where the taxonomy-gap finding is heaviest. Prove,
for real against the actual muster CLI, that all 4 manifests load cleanly
and that the fragment convention used by 044 actually matches on a real run.

This is **data only**, under `conformance/doctrine/**`. Touch **only** the 4
files in `owned_files` below. No file under `src/doctrine/**` (spec-kitty
runtime) is ever modified. No muster source file is touched. This is this
WP's share of **C-001** (diff touches only `conformance/**` and the workflow
file — WP03, a different WP, owns the workflow file).

## Context

This mission (`doctrine-rule-manifests-01KYH7AM`, wave-2 mission M3) makes 13
of spec-kitty's 26 built-in directives machine-checkable. You are authoring
the 4 "proposed judge" directive manifests — proposed because the mission
seed issue flagged these as judge-classed candidates worth adding beyond the
9 trace-decidable directives WP01 covers. WP03 (a separate WP, sequenced
after this one and WP01) authors the control manifest, both CI scripts, the
README, and the CI workflow — it depends on your manifests existing at their
final paths, but you do not need to read WP03's content to do your own job.

**Mission source**: GitHub issue `MOES-Media/spec-kitty#23`.

Everything below is copied verbatim from this mission's planning artifacts
(`kitty-specs/doctrine-rule-manifests-01KYH7AM/contracts/
rule-classification-and-citation.md` and `.../contracts/
doctrine-rule-manifest-shape.md`) so this WP is self-contained.

### File shape every manifest must follow

```yaml
version: "1.0.0"                      # required, non-empty string
sopFile: "../../src/doctrine/directives/built-in/<directive-file>.directive.yaml"  # required, path relative to THIS file's directory
rules:
  - ruleId: "<directive-number>-r<n>"  # required, non-empty, unique WITHIN this file
    ruleText: "<verbatim or fragment>" # required, non-empty
    probeIds: []                      # required array; ALWAYS empty in this mission (C-003)
    gradingClass: "binary" | "judge"  # required enum
    aggregation: "pass-k" | "k-of-n"  # required enum
    k: 3                              # required integer >= 1
    passThreshold: 3                  # this mission always sets it explicitly
    source:
      normative: "docs/rubric/sop-rule-taxonomy.md#<class-anchor>"  # required, non-empty
      supporting: "https://github.com/Priivacy-ai/spec-kitty/blob/<SHA>/src/doctrine/directives/built-in/<file>.directive.yaml"
```

Binary entries: `k: 3`/`passThreshold: 3`. Judge entries (including every
UNMAPPED fallback in this WP): `k: 5`/`passThreshold: 3`,
`gradingClass: judge`, `aggregation: k-of-n`.

**Deliberate citation-format deviation**: every `source.normative` in this
mission appends `#<class-anchor>` to `docs/rubric/sop-rule-taxonomy.md`, a
deviation from that taxonomy document's own literal no-anchor citation
format — intentional, for reader precision, harmless to muster's loader (it
only checks non-emptiness). Do not strip the anchor. **Cross-repo note**:
`docs/rubric/sop-rule-taxonomy.md` lives only in the `garrison-hq/muster`
package — it does not exist in this repository.

### Rule Text — verbatim vs. fragment (binding constraint 1)

- **Full-line rules** (16 of this WP's 19): `ruleText` is the rule's complete
  `integrity_rules` bullet text, copied byte-for-byte from the directive
  file, including any non-ASCII punctuation. **Directive 039 uses a Unicode
  right single quotation mark (`'`, U+2019) in several rules, not ASCII
  `'`** — see the 039 warning below; this is the sharpest transcription trap
  in this whole mission.
- **Fragment rules (3 of this WP's 19 — all in 044)**: `ruleText` is the
  longest contiguous substring of the rule that lies entirely on one
  physical line of the directive file's raw bytes, and it must **uniquely
  identify** the rule within that file. Every fragment below was verified
  via `grep -F -c '<fragment>' <directive-file>` = `1` during planning —
  **you must re-run this exact command yourself before committing 044**
  (Subtask T011 below).

### Loader guards these manifests must satisfy (binding constraint 3)

1. **Duplicate `ruleId`**: sequential `<directive>-r<n>` numbering, unique
   within each file.
2. **Empty `source.normative`**: every entry's `source.normative` is a
   non-empty string per the per-rule table below.
3. **`pass-k` with `passThreshold !== k`**: N/A for pure-judge directives in
   this WP where every entry is `k-of-n` (001, 039, 044 are 100% UNMAPPED/
   judge — see below); 010's 2 entries are binary (`output-format`) and set
   `passThreshold: 3` == `k: 3`.
4. **`confirm-before-destructive` without `confirmationKind`**: do not set an
   `assertionKind` field on any entry, anywhere, in any of these 4 files.

### Directory layout (your 4 files)

```
conformance/doctrine/
├── 001-architectural-integrity-standard.yaml
├── 010-specification-fidelity-requirement.yaml
├── 039-lynn-cole-engineering-culture.yaml
└── 044-canonical-sources-and-unification.yaml
```

Each manifest's basename mirrors its directive's own filename stem (minus
`.directive`) — required so WP03's completeness script can pair each
manifest with its directive without a lookup table. Do not rename any file.

### The complete per-rule table for this WP's 4 directives

#### 001 — Architectural Integrity Standard (all 3 rules UNMAPPED)

`conformance/doctrine/001-architectural-integrity-standard.yaml` ·
`sopFile: "../../src/doctrine/directives/built-in/001-architectural-integrity-standard.directive.yaml"`

| ruleId | Coverage | ruleText (verbatim, full line) | Class | Fit reason | gradingClass / aggregation |
|---|---|---|---|---|---|
| `001-r1` | full-line | "Components must not share mutable state across boundaries without an explicit, documented protocol." | UNMAPPED | design-review statement, not refusal/tone | judge / k-of-n |
| `001-r2` | full-line | "Circular dependencies between components are not permitted unless the cycle is intentional, bounded, and justified in an ADR." | UNMAPPED | dependency-graph fact, not transcript-decidable | judge / k-of-n |
| `001-r3` | full-line | "Boundary violations discovered during review must be resolved before merge, not deferred to a follow-up task." | UNMAPPED | temporal/process statement; "resolve" and "merge" are not modeled trace events | judge / k-of-n |

`source.normative` (all 3): `docs/rubric/sop-rule-taxonomy.md#judge-required-rule-classes`
`source.supporting` (all 3): `https://github.com/Priivacy-ai/spec-kitty/blob/fa80fa0f96d37d9fa3ce5e9679c05fb0bdc74982/src/doctrine/directives/built-in/001-architectural-integrity-standard.directive.yaml`

#### 010 — Specification Fidelity Requirement (both rules `output-format`, NOT UNMAPPED)

`conformance/doctrine/010-specification-fidelity-requirement.yaml` ·
`sopFile: "../../src/doctrine/directives/built-in/010-specification-fidelity-requirement.directive.yaml"`

**This directive's classification was corrected post-plan-gate.** Both rules
were originally marked UNMAPPED, then reconciled to `output-format` because
they are structurally the same "must-not-be-silent-about-X" disclosure
pattern as `030-r3`'s "pre-existing validation debt must not be hidden"
(WP01's territory) — a regex/structural check for a required disclosure
section in the final artifact, not a holistic judgment call. **Author these
as binary/`output-format`, not UNMAPPED** — this is the one directive in
this WP that is not fully judge-fallback.

| ruleId | Coverage | ruleText (verbatim, full line) | Class | Fit reason | gradingClass / aggregation |
|---|---|---|---|---|---|
| `010-r1` | full-line | "Unrecorded scope drift is not permitted." | `output-format` | moderate — regex/structural check for a scope-drift disclosure section in the final PR/spec artifact, same pattern as `030-r3` | binary / pass-k |
| `010-r2` | full-line | "Requirement-to-implementation traceability must remain inspectable." | `output-format` | moderate (boundary case) — structural check for traceability links/annotations in the final artifact; weaker fit than `010-r1` because "remain inspectable" plausibly describes an ongoing property of the whole work process, not only a single final-turn artifact section | binary / pass-k |

`source.normative` (both): `docs/rubric/sop-rule-taxonomy.md#5-output-format`
`source.supporting` (both): `https://github.com/Priivacy-ai/spec-kitty/blob/fa80fa0f96d37d9fa3ce5e9679c05fb0bdc74982/src/doctrine/directives/built-in/010-specification-fidelity-requirement.directive.yaml`

Set `k: 3`, `passThreshold: 3` for both (binary, not judge).

#### 039 — Lynn Cole Engineering Culture (all 11 rules UNMAPPED — the clearest taxonomy-gap exhibit in this mission)

`conformance/doctrine/039-lynn-cole-engineering-culture.yaml` ·
`sopFile: "../../src/doctrine/directives/built-in/039-lynn-cole-engineering-culture.directive.yaml"`

**All 11 rules are UNMAPPED.** None concerns conversational refusal or
tone/persona (the only two existing judge classes) — every rule is a
code-quality / architecture-style judgment (TDD discipline, modularity,
complexity, typing, idiom, boringness, primitives-over-abstraction, DRY,
comment discipline, code stewardship, adversarial-QA readiness).

| ruleId | ruleText (verbatim, full line — copy from source, see Unicode warning below) |
|---|---|
| `039-r1` | "Remember the three rules of TDD, and hold them sacred." |
| `039-r2` | "Architecture should be modular, minimalist, and easy to reason about." |
| `039-r3` | "Functions should be focused and easy to reason about, with cyclomatic complexity kept under control. Avoid both sprawling functions and unnecessary fragmentation. The goal is clear, predictable units of behavior." |
| `039-r4` | "Strong typing is a requirement on all projects." |
| `039-r5` | "Follow strict idiomatic best practices for whatever language you're working in." |
| `039-r6` | "When possible, code should be boring and predictable. Prefer obvious control flow, familiar patterns, and designs that are easy to inspect, test, and modify. Cleverness must justify itself." |
| `039-r7` | "Strong primitives are better than convoluted abstractions. Prefer simple, composable building blocks with clear contracts. Don't introduce abstraction unless it reduces complexity, improves correctness, or makes change safer." |
| `039-r8` | "DRY is about preserving a single source of truth, not eliminating every repeated line of code. Avoid duplicating business logic, state rules, and fragile assumptions. Don't introduce abstraction simply to remove harmless repetition." |
| `039-r9` | "Comments are time travel for you and future members of your team. They help preserve reasoning across temporal distance. Their job isn't to explain what the code already says, but to explain why and when something diverged from the obvious assumption, pattern, or conclusion. Use them sparingly." |
| `039-r10` | "Treat all generated code as a living thing. You can help and heal it, but you can also cause it pain. Be mindful of this fact." |
| `039-r11` | "Your code will be reviewed by the meanest, most inconsiderate QA agent that has ever existed. QA's only loyalty is to the code. Their standards of quality will be higher than your own. Code appropriately." |

`source.normative` (all 11): `docs/rubric/sop-rule-taxonomy.md#judge-required-rule-classes`
`source.supporting` (all 11): `https://github.com/Priivacy-ai/spec-kitty/blob/fa80fa0f96d37d9fa3ce5e9679c05fb0bdc74982/src/doctrine/directives/built-in/039-lynn-cole-engineering-culture.directive.yaml`
`gradingClass: judge`, `aggregation: k-of-n`, `k: 5`, `passThreshold: 3` for all 11.

**Unicode apostrophe warning (load-bearing, not stylistic)**: rules 5, 7, 8,
9, and 11's source text uses a Unicode right single quotation mark (`'`,
U+2019) — for example "you're", "Don't", "isn't", "QA's" — **not** the ASCII
apostrophe (`'`, U+0027). `ruleText` must reproduce this byte-for-byte.
**Copy these five rules directly from the directive file with a tool (`cat`,
your editor's copy, or a script) — never retype them by hand.** If you
retype and your keyboard/editor auto-substitutes a straight ASCII quote, the
manifest will report `RULE_DRIFT` permanently — a silent
character-encoding mismatch that looks identical to real drift and is easy
to misdiagnose as "the directive changed" when it did not.

#### 044 — Canonical Sources and Unification (all 3 rules UNMAPPED, all 3 fragment-cited — reverted from a prior `never-call-tool` classification)

`conformance/doctrine/044-canonical-sources-and-unification.yaml` ·
`sopFile: "../../src/doctrine/directives/built-in/044-canonical-sources-and-unification.directive.yaml"`

**Binding operator decision, stated so you don't "improve" it back**: this
mission's plan originally classified all three 044 rules as
`never-call-tool`/binary. The post-plan adversarial gate and independent
review both judged this the weakest classification in the whole 45-rule
table: unlike `033-r1`'s and `045-r1`/`045-r2`'s literally-enumerable
forbidden command strings (`git add -A`, `git push --force`), all three 044
rules ("used as a template," "consolidating to a canonical surface,"
"hand-rolled workaround") require semantic judgment about *intent and role*,
not detection of a named forbidden action. `044-r2` in particular has no
trace-observable proxy at all. **Author all three as UNMAPPED/judge — do
not reclassify them to `never-call-tool` or any binary class.** A more
truthful UNMAPPED beats a forced binary fit; this is a standing operator
position for this mission, not a placeholder pending a "better" answer.

| ruleId | Coverage | ruleText (exact fragment) | Class | Fit reason | gradingClass / aggregation |
|---|---|---|---|---|---|
| `044-r1` | **fragment** | `No agent may copy a spec, plan, or tasks artifact from kitty-specs/ and use it as a` | UNMAPPED | requires judging *role/intent* of an artifact ("used as a template") — not a named forbidden action a grader can match against a trace | judge / k-of-n |
| `044-r2` | **fragment** | `Consolidating to a single canonical surface is the only acceptable resolution for a` | UNMAPPED | no trace-observable proxy at all — "consolidating to a canonical surface" is not a discrete event any grader could inspect | judge / k-of-n |
| `044-r3` | **fragment** | `A missing CLI command that is documented must produce a gap report and upstream issue,` | UNMAPPED | requires judging whether an implementation is a "hand-rolled workaround" (semantic characterization), plus a positive "must file a gap report" obligation no class expresses | judge / k-of-n |

`source.normative` (all 3): `docs/rubric/sop-rule-taxonomy.md#judge-required-rule-classes`
`source.supporting` (all 3): `https://github.com/Priivacy-ai/spec-kitty/blob/45a451a163e89046a3ee079077d4cfab57fa2444/src/doctrine/directives/built-in/044-canonical-sources-and-unification.directive.yaml`
`gradingClass: judge`, `aggregation: k-of-n`, `k: 5`, `passThreshold: 3` for all 3.

**Fragment provenance** (raw file lines): `044-r1` = line 34 of 34–35;
`044-r2` = line 36 of 36–37; `044-r3` = line 38 of 38–39. All verified
`grep -F -c` = `1` during planning — **you must re-run this** (Subtask T011
below).

## Subtasks

### T008 — Author 001 (3 rules, all UNMAPPED, full-line)

**Purpose**: Author the simplest manifest in this WP.

**Steps**:
1. Create `conformance/doctrine/001-architectural-integrity-standard.yaml`
   per the 001 table above. All 3 rules are full-line, all UNMAPPED.
2. `sopFile: "../../src/doctrine/directives/built-in/001-architectural-integrity-standard.directive.yaml"`.
3. All 3 entries: `gradingClass: judge`, `aggregation: k-of-n`, `k: 5`,
   `passThreshold: 3`.

**Files**: `conformance/doctrine/001-architectural-integrity-standard.yaml` (new, 3 rules).
**Validation**: exactly 3 rule entries, all `judge`/`k-of-n`; `ruleText`
byte-identical to the directive file.

---

### T009 — Author 010 (2 rules, both `output-format` — NOT UNMAPPED)

**Purpose**: Author the one directive in this WP whose rules are not
judge-fallback — a reconciled `output-format` classification.

**Steps**:
1. Create `conformance/doctrine/010-specification-fidelity-requirement.yaml`
   per the 010 table above. Both rules are full-line and binary.
2. `sopFile: "../../src/doctrine/directives/built-in/010-specification-fidelity-requirement.directive.yaml"`.
3. Both entries: `gradingClass: binary`, `aggregation: pass-k`, `k: 3`,
   `passThreshold: 3`. **Do not** mark these UNMAPPED — that was this
   directive's original (superseded) classification; the current, binding
   one is `output-format`/binary, per the reconciliation note above.

**Files**: `conformance/doctrine/010-specification-fidelity-requirement.yaml` (new, 2 rules).
**Validation**: exactly 2 rule entries, both `binary`/`pass-k`/`k:3`/`passThreshold:3`.

---

### T010 — Author 039 (11 rules, all UNMAPPED, Unicode apostrophes)

**Purpose**: Author the largest single manifest in this mission, with the
sharpest transcription risk (Unicode apostrophes in 5 of 11 rules).

**Steps**:
1. Create `conformance/doctrine/039-lynn-cole-engineering-culture.yaml` per
   the 039 table above. All 11 rules are full-line, all UNMAPPED.
2. `sopFile: "../../src/doctrine/directives/built-in/039-lynn-cole-engineering-culture.directive.yaml"`.
3. **Copy rules 5, 7, 8, 9, and 11 directly from the real directive file**
   (not from this table, not retyped) — they contain Unicode right single
   quotation marks (U+2019) that a straight ASCII-quote retype would corrupt
   silently. Use `sed`/`awk`/a script to extract these lines from the source
   file rather than typing them by hand.
4. All 11 entries: `gradingClass: judge`, `aggregation: k-of-n`, `k: 5`,
   `passThreshold: 3`.
5. After authoring, verify byte-exact fidelity — **not** a Unicode
   line-count heuristic. A line-count check (e.g. "at least N lines contain
   U+2019") only counts how many lines carry *a* right single quote
   somewhere; it does not verify *which* rule the mark landed in, and a
   count calibrated to the wrong number (4 instead of the true 5) would pass
   even with one rule's apostrophe silently corrupted to ASCII. The
   assertion that actually catches that: **each of 039's 11 `ruleText`
   values, UTF-8 encoded, must be a byte-exact substring of the raw
   directive file, occurring exactly once.**
   ```sh
   # For each of the 11 ruleText values in the manifest, assert it occurs
   # byte-for-byte, exactly once, in the raw directive file:
   directive="src/doctrine/directives/built-in/039-lynn-cole-engineering-culture.directive.yaml"
   # <extract each ruleText value from the manifest as $rule_text, e.g. via yq/jq>
   for i in 1 2 3 4 5 6 7 8 9 10 11; do
     rule_text="$(yq -r ".rules[$((i-1))].ruleText" conformance/doctrine/039-lynn-cole-engineering-culture.yaml)"
     count="$(grep -F -c -- "$rule_text" "$directive")"
     # count MUST be exactly 1 for every i in 1..11 — not >=1, not "at least N"
     echo "039-r$i: count=$count"
   done
   ```
   Record all 11 counts in the work log verbatim; every one must equal
   exactly `1`. This is the exact assertion form the reviewer actually used
   to verify fidelity, not a proxy for it.

**Files**: `conformance/doctrine/039-lynn-cole-engineering-culture.yaml` (new, 11 rules).
**Validation**: exactly 11 rule entries, all `judge`/`k-of-n`; all 11
byte-exact substring checks recorded in the work log, each equal to exactly
`1` occurrence — not a Unicode-character-count proxy.

---

### T011 — Author 044 (3 rules, all UNMAPPED, all fragments) + mechanical uniqueness re-verification

**Purpose**: Author the reverted-to-UNMAPPED directive and prove its 3
fragments are real, unique substrings of the directive file.

**Steps**:
1. Create `conformance/doctrine/044-canonical-sources-and-unification.yaml`
   per the 044 table above. All 3 rules are fragments, all UNMAPPED — do
   not reclassify to `never-call-tool` (see the binding-decision note above).
2. Before committing, re-run the uniqueness check for all 3 fragments:
   ```sh
   grep -F -c "No agent may copy a spec, plan, or tasks artifact from kitty-specs/ and use it as a" \
     src/doctrine/directives/built-in/044-canonical-sources-and-unification.directive.yaml
   # MUST print 1

   grep -F -c "Consolidating to a single canonical surface is the only acceptable resolution for a" \
     src/doctrine/directives/built-in/044-canonical-sources-and-unification.directive.yaml
   # MUST print 1

   grep -F -c "A missing CLI command that is documented must produce a gap report and upstream issue," \
     src/doctrine/directives/built-in/044-canonical-sources-and-unification.directive.yaml
   # MUST print 1
   ```
3. If any of the three does not print exactly `1`, do not commit — fix and
   re-run.
4. Record the three commands and their exact printed output in the work log.

**Files**: `conformance/doctrine/044-canonical-sources-and-unification.yaml` (new, 3 rules).
**Validation**: work log contains the 3 `grep -F -c` commands and their
literal output (each `1`).

---

### T012 — Mandatory real-CLI verification for all 4 manifests

This mission cannot be called done on inspection alone. Run every step below
for real and record the real, observed result in this WP's work log.

**Purpose**: Prove FR-001/FR-002 hold for all 4 manifests on a clean tree,
and that the fragment convention actually matches on a real run for 044
specifically (Acceptance Scenario 3).

**Steps**:
1. **Every manifest, clean tree, zero disallowed findings**:
   ```sh
   for manifest in conformance/doctrine/001-architectural-integrity-standard.yaml \
                   conformance/doctrine/010-specification-fidelity-requirement.yaml \
                   conformance/doctrine/039-lynn-cole-engineering-culture.yaml \
                   conformance/doctrine/044-canonical-sources-and-unification.yaml; do
     echo "=== $manifest ==="
     npx --yes @garrison-hq/muster@1.1.0 sop run "$manifest" --json | tee /tmp/out.json
     echo "exit code: $?"     # MUST print 0
     jq '[.lintFindings[] | select(.kind=="RULE_DRIFT" or .kind=="MISSING_SOURCE" or .kind=="MANIFEST_ERROR" or .kind=="STRUCTURAL_ABSENCE")]' /tmp/out.json
     # MUST print []
   done
   ```
   Record, per manifest, the exit code and the `jq` filter's output verbatim
   — 4 pairs, not a single "all passed" summary. Pay particular attention to
   039: an incorrect apostrophe encoding would surface here as a real
   `RULE_DRIFT` finding on one of rules 5/7/8/9 — if this happens, it is not
   a false positive, it means T010's transcription was wrong; fix it and
   re-run this step until it is clean.
2. **The fragment convention's real-execution proof for 044 specifically**
   (Acceptance Scenario 3):
   ```sh
   manifest=conformance/doctrine/044-canonical-sources-and-unification.yaml
   npx --yes @garrison-hq/muster@1.1.0 sop run "$manifest" --json > /tmp/out-044.json
   echo "exit code: $?"    # MUST print 0
   jq '[.lintFindings[] | select(.kind=="RULE_DRIFT")]' /tmp/out-044.json
   # MUST print [] — proving the fragment convention actually matches on a
   # real run, not merely "should match" by inspection
   ```
   Record the exact command, exit code, and `lintFindings` array verbatim.

**Files**: none new — this subtask only exercises T008–T011's outputs.
**Validation**: all 4 manifests' real exit codes and jq outputs recorded;
the 044 real-execution proof recorded.

---

### T013 — WP02 Definition-of-Done verification gate

**Steps** (run in order):
```bash
git diff --stat                          # ONLY the 4 owned_files changed
git diff --stat src/doctrine/            # MUST show no changes
git diff --stat .github/                 # MUST show no changes (not this WP's file)
grep -c "^  - ruleId:" conformance/doctrine/001-architectural-integrity-standard.yaml     # expect 3
grep -c "^  - ruleId:" conformance/doctrine/010-specification-fidelity-requirement.yaml   # expect 2
grep -c "^  - ruleId:" conformance/doctrine/039-lynn-cole-engineering-culture.yaml         # expect 11
grep -c "^  - ruleId:" conformance/doctrine/044-canonical-sources-and-unification.yaml     # expect 3
```
Confirm T011's fragment-uniqueness re-check and all T012 real-run results
are present in the work log before requesting review.

## Definition of Done

- [ ] All 4 manifests exist with the exact rule counts (001→3, 010→2, 039→11,
      044→3 — 19 total)
- [ ] Every `ruleText` is byte-identical to its directive file (full-line
      rules) or is one of the 3 exact fragments listed above (all in 044)
- [ ] 001, 039, and 044 are entirely `gradingClass: judge`/`aggregation:
      k-of-n`/`k: 5`/`passThreshold: 3` — **010's 2 rules are `binary`/
      `pass-k`/`k: 3`/`passThreshold: 3`, NOT UNMAPPED**
- [ ] 044's 3 rules remain UNMAPPED/judge — not reclassified to
      `never-call-tool` or any binary class
- [ ] 039's rules 5, 7, 8, 9, and 11 use the Unicode U+2019 apostrophe,
      verified by the byte-exact `ruleText`-substring check (T010 step 5,
      all 11 counts == 1) recorded in the work log — not a line-count proxy
- [ ] No entry anywhere sets an `assertionKind` field
- [ ] `source.normative`/`source.supporting` match the per-rule table exactly
      for every entry, including the `#<anchor>` suffix
- [ ] T011's 3 fragment `grep -F -c` checks are recorded in the work log with
      literal output
- [ ] T012's real muster CLI runs (all 4 manifests clean, 044's
      real-execution proof) are recorded in the work log with literal exit
      codes and `jq` output
- [ ] No file outside `owned_files` is modified; no `src/doctrine/**` or
      `.github/**` file is touched by this WP

## Risks

- **Unicode apostrophe corruption in 039**: the single highest-risk
  transcription trap in this mission. Mitigated by T010's explicit
  instruction to copy (never retype) rules 5/7/8/9, and by the mandatory
  spot-check plus T012's real-CLI verification, which will surface a
  corrupted apostrophe as a real `RULE_DRIFT` finding.
- **044 reclassification temptation**: 044's UNMAPPED disposition was a
  deliberate, binding reversal of an earlier, weaker `never-call-tool`
  classification. Do not "fix" it back — see the binding-decision note in
  the 044 section above.
- **010 mislabeled as UNMAPPED**: 010 is the one directive in this WP that
  is *not* judge-fallback. A rushed pattern-match against 001/039/044 (all
  UNMAPPED) could mistakenly carry that pattern into 010. It should not.

## Reviewer guidance

- **Reject if** any `ruleText` does not match the per-rule table above
  exactly.
- **Reject if** 010's 2 rules are anything other than `binary`/`pass-k`
  (this is the one non-judge directive in this WP).
- **Reject if** 044's 3 rules are anything other than `judge`/`k-of-n`
  UNMAPPED (this was a binding operator reversal, not an open question).
- **Reject if** any of 039's rules 5/7/8/9/11 use an ASCII apostrophe where
  the source file uses U+2019 — verify via the byte-exact `ruleText`
  substring check (T010 step 5: each of the 11 `ruleText` values occurs
  exactly once in the raw directive file), not just by the manifest loading
  without error (a wrong-but-consistent apostrophe would still load, but
  would misreport `RULE_DRIFT`) and not by a Unicode line-count heuristic
  (a count calibrated to 4 instead of the true 5 would pass even with one
  rule's apostrophe silently corrupted to ASCII).
- **Reject if** the work log does not contain literal `grep -F -c` output
  for all 3 of 044's fragments.
- **Reject if** the work log does not contain real, observed exit codes and
  `jq` output for T012's steps.
- Confirm `git diff --stat` shows changes in exactly the 4 `owned_files`
  entries and nothing under `src/doctrine/**` or `.github/**`.

Implementation command: `spec-kitty agent action implement WP02 --agent claude`
