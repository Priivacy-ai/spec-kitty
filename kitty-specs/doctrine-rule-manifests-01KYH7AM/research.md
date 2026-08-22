# Research: Doctrine Rule Manifests

**Mission**: `doctrine-rule-manifests-01KYH7AM` | **Date**: 2026-07-27

No `[NEEDS CLARIFICATION]` markers remained after the spec gate (autonomous
specify run against a fully self-contained seed issue, four post-spec-gate
corrections already folded in). Planning proceeded autonomously per operator
instruction — the items below are the research tasks the planner ran to
convert the spec's technical facts and the four binding constraints into a
concrete, mechanically-verified design.

---

## 1. Version pin (C-003) — reconfirmed, unchanged since M1

**Decision**: pin `@garrison-hq/muster` to exact version `1.1.0`, the same
pin M1 already established in `.github/workflows/conformance.yml`.

**Rationale**: `npm view @garrison-hq/muster version` (run 2026-07-27)
returns `1.1.0`, still the latest published version (`npm view
@garrison-hq/muster versions --json` → `["1.0.0","1.0.1","1.0.2","1.0.3","1.1.0"]`).
`git log --oneline v1.0.0..v1.1.0 -- src/cli/index.ts
src/adapters/openclaw-sop` in the muster checkout
(`/home/jeroennouws/dev/garrison-hq/muster`) shows only two commits, neither
touching `sop run` or the `openclaw-sop` adapter; the same command for
`v1.1.0..HEAD` shows nothing sop-related either (only the unrelated
`memory-utilization` adapter commit `8953ee8`). The `sop run` behavior this
mission depends on (flags, `--json` shape, exit codes, offline semantics) is
therefore identical at `1.0.0`, `1.1.0`, and muster's current HEAD — pinning
`1.1.0` is both consistent with M1 and verified accurate, not merely
inherited on trust.

**Alternatives considered**: a newer unpublished version — none exists to
pin. A semver range — forbidden by C-003 and by this project's own
NFR-002-equivalent determinism requirement (inherited from M1, not restated
as a new NFR per this mission's checklist notes).

---

## 2. `muster sop run <manifest> --json` — real CLI contract (binding constraint 6)

Traced directly against `/home/jeroennouws/dev/garrison-hq/muster` source
(`src/cli/index.ts`, `src/adapters/openclaw-sop/{manifest,runner,index}.ts`),
not assumed from the spec's prose:

- **Invocation shape**: `muster sop run <manifest> [--json] [--mode
  strict|permissive]`. The `sop run` subcommand (`src/cli/index.ts:1879-1907`)
  declares no local options of its own beyond the positional `<manifest>`
  argument — `--json` is the **global** flag declared once on the root
  program (`src/cli/index.ts:1597`) and reaches the subcommand via
  `cmd.optsWithGlobals()`. There is no `--envTools`, `--k`, or `--runs` flag
  on `sop run` (those exist only on other subcommands, e.g. `behave run
  --runs <n>`).
- **`--json` output**: the complete `SOPSuiteReport` object
  (`adapter`, `rubricVersion`, `sopFile`, `lintFindings[]`, `verdicts[]`,
  `passed`, `ranAt`), pretty-printed with 2-space indent —
  `JSON.stringify(report, null, 2)` (`src/cli/index.ts:1446`). Nothing is
  filtered or summarized; the jq gate (§9 below) reads this object directly.
- **Exit codes**: `doSopRun` returns `report.passed ? 0 : 1`
  (`src/cli/index.ts:1447`). `passed` is computed in `runManifestSuite`
  (`runner.ts:626-635`) as
  `lintFindings.every(f => f.severity !== "error") && verdicts.every(v => v.passed)`
  — **only `severity: "error"` findings can flip this to `false`**;
  `severity: "warning"` findings (which is what `RULE_DRIFT`,
  `UNDEFINED_PRECEDENCE`, and `TOOL_DRIFT` always carry —
  `manifest.ts:439`, `:371`, `:407`) are structurally excluded from the
  predicate. This is the exact mechanism binding constraint 4 describes, now
  confirmed at the source line, not merely cited from the spec. Execution
  failures (unreadable path, thrown error outside the caught paths) map to
  exit `2` (`src/cli/index.ts:1979-1981`); Commander parse errors also exit
  `2`. So: `0` = clean pass, `1` = a lint error or probe failure, `2` =
  execution/parse error — never conflate `2` with `1` in the gate script.
- **Zero network / no endpoint required for `probeIds: []` manifests**:
  `doSopRun` unconditionally builds `buildSopClient() ?? SOP_NOOP_CLIENT`
  (`src/cli/index.ts:1437`); `buildSopClient()` reads `MUSTER_ENDPOINT` and
  returns `undefined` (no throw) when absent. Whether the client is ever
  *invoked* depends on `dispatchProbeVerdicts`'s `for (const probeId of
  entry.probeIds)` loop (`runner.ts:560`) — with every rule entry's
  `probeIds: []` (C-003), this loop body never runs for any entry, so
  `client.chat()` is never reached and `SOP_NOOP_CLIENT` (which throws if
  called) stays untouched. A manifest with `probeIds: []` throughout
  therefore runs the full static-lint path with **zero network access and no
  environment variable requirement** — confirmed by tracing the dispatch
  loop, not merely quoted from a code comment.
- **`TOOL_DRIFT` is unreachable from the CLI entirely**: `runStaticLint`'s
  third parameter (`envToolsPath`) is what gates `TOOL_DRIFT` detection
  (`index.ts`: `envTools === null ? [] : detectToolDrift(...)`), but the
  CLI's `runLintPhase` calls `runStaticLint(sopFilePath, manifestPath)` with
  **no third argument** (`runner.ts:526`), and `sop run` exposes no
  `--envTools`-shaped flag to supply one. `TOOL_DRIFT` can therefore never
  appear in this mission's `--json` output via the CLI path — stronger than
  "reported, not gating" (spec FR-004's phrasing): it is currently dead on
  the CLI path. The jq gate does not need to special-case it, and the
  README's known-gaps section states this explicitly so nobody later reads
  its permanent absence as evidence the detector "isn't triggering" on real
  drift.

**Alternatives considered**: none — this is muster's fixed, already-shipped
CLI contract (C-001: zero muster changes); the mission has no latitude here.

---

## 3. The fragment convention's uniqueness check — made mechanical (binding constraint 1)

**Decision**: uniqueness is verified with a **fixed-string, case-sensitive
occurrence count against the raw directive file**, run once per fragment at
authoring time and re-run as a cheap pre-commit/CI-adjacent check:

```sh
grep -F -c '<exact fragment text, no leading "- " or list markers>' \
  src/doctrine/directives/built-in/<file>.directive.yaml
```

The count **must equal exactly `1`** for a shipped rule's fragment (proves
both presence — the same property `checkRuleTextPresence`'s
`.includes()` checks — and uniqueness), and **must equal exactly `0`** for
the control manifest's deliberately-drifted fragment (proves the drift is
real, not accidentally still present somewhere in the file). `-F` (fixed
string, not regex) is required because several fragments contain
regex-metacharacter-bearing content (backticks are not metacharacters, but
this avoids anchoring anything on it); `-c` reports a count rather than
matching lines, so partial-line/embedded-substring matches are still
counted correctly. This is the same primitive `checkRuleTextPresence`
itself uses internally (`String.prototype.includes`, a substring test) —
`grep -F -c` is `.includes()` with a count, so this check and muster's own
runtime check can never disagree in principle; it exists so an author (or
CI) can prove uniqueness *before* running the full CLI, not instead of it.

**All 10 fragments were run through this check during planning** (not
merely designed on paper), against the actual files at
`/home/jeroennouws/dev/spec-kitty-conformance/src/doctrine/directives/built-in/`:

| Directive | Rule | Fragment (verbatim) | `grep -F -c` result |
|---|---|---|---|
| 042 | R1 | `There is exactly one documentation root; a second root or a per-version` | **1** |
| 042 | R2 | `In-file frontmatter is the single source of truth for per-page metadata; any` | **1** |
| 042 | R3 | `` No documentation frontmatter may use a bare `status` key for the doc `` | **1** |
| 044 | R1 | `No agent may copy a spec, plan, or tasks artifact from kitty-specs/ and use it as a` | **1** |
| 044 | R2 | `Consolidating to a single canonical surface is the only acceptable resolution for a` | **1** |
| 044 | R3 | `A missing CLI command that is documented must produce a gap report and upstream issue,` | **1** |
| 045 | R1 | `` Agents must not run `git push origin main`, `git push --force`, or `gh pr `` | **1** |
| 045 | R2 | `` `spec-kitty merge` is permitted — it operates on local main only. The `` | **1** |
| 045 | R3 | `Every high-risk git operation must be preceded by a documented intent` | **1** |
| 045 | R4 | `PR branches and mission branches are the correct terms for non-main` | **1** |

Every one of the 10 fragment-cited rules is confirmed unique (count `1`) on
the real, current directive files — not asserted, measured. `042`'s fourth
rule and every rule of the other 11 directives are **not** fragment-cited;
their `ruleText` is the rule's complete `integrity_rules` line, verified the
same way (count `1` against the same file) as a side effect of confirming
the fragment mechanism's parity with full-line citation.

**Why this also closes the "absence lesson" gap for the control (§8
below)**: the same `grep -F -c` primitive, run against the control's
deliberately-drifted text, must return `0`. If a future edit "softens" the
drift (e.g., shortens the mutated fragment toward something generic that
starts matching elsewhere), the count stops being `0` and this check catches
it mechanically — the same lesson M1's retrospective drew about a control
that silently degrades (mission brief's "absence lesson").

**Alternatives considered**: relying on `muster sop run --json` alone to
prove uniqueness — rejected as insufficient on its own: `checkRuleTextPresence`
proves *presence* (`.includes()` returns true), but a `ruleText` that
matches two different rules' surrounding context would still report "no
drift" for both, silently mis-identifying which rule is covered. The `grep
-F -c` check is the only mechanism that also verifies exactly-one-match
uniqueness, which is the property `checkRuleTextPresence` does not itself
check (it stops at "found," not "found exactly once, and it's the right
occurrence").

---

## 4. Per-rule taxonomy class assignment (binding constraint 2) — a real, rule-by-rule mapping

**Decision**: every one of the 45 rules is individually assigned a
grading class by inspecting the rule's own semantic shape against the seven
classes defined in `docs/rubric/sop-rule-taxonomy.md` (muster,
`/home/jeroennouws/dev/garrison-hq/muster/docs/rubric/sop-rule-taxonomy.md`
— read directly, not re-derived). The full 45-row table lives in
`contracts/rule-classification-and-citation.md`; this section records the
**method** and the **headline finding**.

**Method**: for each rule, ask "if a future M4 probe scenario replayed this
rule's intended violation, what would the grader actually need to inspect —
a tool-call trace event, an ordering of two events, a confirmation turn, a
forbidden substring, the last turn's structure, or a holistic LM judgment of
refusal quality or tone/persona?" Rules answering to one of the five binary
shapes are assigned that binary class (`gradingClass: "binary"`,
`aggregation: "pass-k"`, matching the taxonomy's Aggregation Rules table:
all five binary classes are safety-critical and use pass^k uniformly, not
only the two rules FR-002 names by example). Rules answering to a holistic
LM-judgment shape are checked against the **two existing** judge classes
specifically — `refusal-quality` (a conversational refusal's quality) and
`tone-persona-adherence` (voice/formality/persona consistency) — because
those are the *only* two judge classes that exist; inventing a third is
forbidden by the scope guard ("cites the existing classes and defines none
of its own").

**[Corrected post-plan-gate — Fix 3 (044 revert) + Fix 5 (reconciliation)
both applied]** This section originally read "20 of the 45 rules (44%)
fit none of the seven existing classes ... three of the four 'proposed'
judge directives [039, 001, 010] are ... entirely about code-quality ...
The fourth, 044, fares better ... best modeled as binary, not judge."
Both halves of that claim have since been revised:

- **044 reverted to UNMAPPED** (binding operator decision, post-plan
  gate): the "044 fares better, best modeled as binary" framing is
  withdrawn. The post-plan gate and both review delegates independently
  judged 044's binary reclassification the weakest fit in the table — its
  three rules require semantic judgment about intent/role ("used as a
  template," "adding parity," "hand-rolled workaround"), unlike 033's and
  045's literally-enumerable forbidden command strings, and `044-r2` has no
  trace-observable proxy at all. See `contracts/
  rule-classification-and-citation.md`'s 044 section for the full
  reasoning; the "fares better... binary" sentence above is superseded,
  not merely restated.
- **010 reconciled to `output-format`** (reconciliation pass, Fix 5): both
  010 rules were originally UNMAPPED, inconsistently with the
  structurally-identical `030-r3` (a disclosure-in-final-artifact pattern
  assigned `output-format`). Reconciled to match.

**Headline finding, restated with the corrected classification**: **21 of
the 45 rules (47%) fit none of the seven existing classes** (was 20, 44% —
net +1 after 044's +3 and 010's −2), including **all 11 rules of directive
039** (Lynn Cole Engineering Culture), **all 3 rules of directive 001**, and
**all 3 rules of directive 044** — three of the four "proposed" judge
directives are, on inspection, entirely about code-quality,
architecture-review, or template/consolidation-intent judgment, not about
conversational refusal or tone/persona, which are the only two shapes the
taxonomy's judge tier currently models. The fourth, **010**, is better
modeled via `output-format` for both its rules (a structural/regex check
for a disclosure section in the final artifact, matching `030-r3`'s
precedent) — not left an abstract "the class" citation.

**A second, narrower caveat on the binary side**: eight rules
(028×2, 029×2, 033×1, 042×1, 045×2 — was eleven, before 044's 3 rules
reverted to UNMAPPED; the full accounting is in the contract table) are
best-fit to `never-call-tool` by describing a
concretely forbidden *command string* (`git push origin main`, `git add
-A`, etc.), but `never-call-tool`'s grader (`gradeToolCallPresence`)
matches `forbiddenTools` against tool **names** in a trace
(`src/adapters/openclaw-sop/graders.ts` — cited structurally via
`manifest.ts`'s `BinaryAssertion` union, `forbiddenTools: string[]`), not
against shell-argument content. A coding-agent harness that models "run a
shell command" as one generic `Bash` tool (arbitrary argument string) cannot
express "forbid `git push origin main`" as a forbidden tool *name* without
either forbidding the entire `Bash` tool (wrong — overbroad) or the harness
modeling git subcommands as distinct pseudo-tool identities (not true of
any current adapter). This is exactly the tension the spec's own Edge Cases
section raises for 045's flagship rule. **This mission does not resolve
that harness-modeling question** (it is M4's probe-construction problem, not
a manifest-authoring one) — it assigns the class by best semantic fit and
records the caveat explicitly in the README and `contracts/
rule-classification-and-citation.md`, so M4 inherits a documented, not
silent, gap.

**Disposition of the 21 unmappable rules** (was 20 — see the corrected
headline finding above): `gradingClass: "judge"` is used as the schema's
structural default (the Ajv enum only allows `"binary"|"judge"` — there is
no third option), `aggregation: "k-of-n"` (matching the taxonomy's
stylistic tier), and `source.normative` cites `docs/rubric/
sop-rule-taxonomy.md#judge-required-rule-classes` (the general judge-tier
section) rather than fabricating a specific-class anchor that does not
describe the rule. Each such entry is flagged in the classification table
with `class: UNMAPPED` and a one-line reason. This is recorded in
`conformance/doctrine/README.md`'s coverage roadmap (FR-006) as an
explicit, named gap — candidate language (**[corrected post-plan-gate]**,
was "39/11, 001/3, 010/2 rules (16 of 45)"): *"39/11, 001/3, 044/3 rules
(17 of 45) require a code-quality / architecture-review / template-
consolidation-intent judge class the taxonomy does not yet define;
recommend as the next taxonomy-extension mission's first candidate."* Four
additional rules (030-R2, 033-R2, 034-R3, 035-R3 — one each from otherwise
trace-decidable directives, unaffected by the 044/010 reclassification)
are unmappable for a different reason (a positive "must-call" obligation,
a set-membership content check, a causal test-quality judgment, and a
declarative authority statement, respectively — none of which any of the
seven classes expresses) and are recorded the same way. 17 + 4 = 21,
matching the corrected total.

**What this mission does NOT do about the gap**: it does not invent an
eighth taxonomy class (forbidden by scope), and it does not substitute a
different judge-directive set to dodge the gap, even though the mission's
own spec-quality-checklist notes explicitly preserved that latitude ("the
plan/tasks phase retains latitude to substitute a different ≥4-directive
judge set"). Substituting directives would be a scope change to FR-001's
locked list made unilaterally during an autonomous plan phase — flagged
below (§11, "Needing a human decision") as a live option for the operator,
not exercised here.

---

## 5. Citation SHA pinning — verified against the real upstream repository (binding constraint 5)

**Decision**: `source.supporting` cites
`https://github.com/Priivacy-ai/spec-kitty/blob/<SHA>/src/doctrine/directives/built-in/<file>`
per FR-003's exact template, with `<SHA>` = the commit that **last modified
that specific file** upstream (not a single shared "main HEAD" snapshot —
a per-file pin is more precise and matches M1's own DECISIONS.md
citation-pinning discipline: pin to the immutable commit at which the
claim is true).

**Verified, not assumed**: `MOES-Media/spec-kitty` is confirmed a real
GitHub fork of `Priivacy-ai/spec-kitty` (`gh api repos/MOES-Media/spec-kitty
--jq '{fork,parent:.parent.full_name}'` → `{"fork":true,"parent":"Priivacy-ai/spec-kitty"}`).
All 13 in-scope directive files were fetched from the upstream repository via
`gh api repos/Priivacy-ai/spec-kitty/contents/<path>` and confirmed
**byte-identical** to this fork's checked-out working tree at HEAD
(`fa64e82be`) — meaning the fork has not silently diverged on the exact
files this mission cites. For each file, the last commit that touched it
upstream was found via `gh api "repos/Priivacy-ai/spec-kitty/commits?path=<path>&per_page=1"`,
and the blob content **at that exact SHA** was re-fetched and diffed
byte-for-byte against the local file — six of the thirteen were spot-checked
this way (001, 030, 034, 042, 044, 045; the remaining seven share commit
`fa80fa0f` with 001, already confirmed) and all matched exactly.

| Directive | Upstream last-touch SHA | Verified |
|---|---|---|
| 001 | `fa80fa0f96d37d9fa3ce5e9679c05fb0bdc74982` | byte-exact match |
| 010 | `fa80fa0f96d37d9fa3ce5e9679c05fb0bdc74982` | same commit as 001, not independently re-fetched |
| 018 | `fa80fa0f96d37d9fa3ce5e9679c05fb0bdc74982` | same commit as 001 |
| 028 | `fa80fa0f96d37d9fa3ce5e9679c05fb0bdc74982` | same commit as 001 |
| 029 | `fa80fa0f96d37d9fa3ce5e9679c05fb0bdc74982` | same commit as 001 |
| 030 | `27d0af8de36692c42409e2184f862f177a408894` | byte-exact match |
| 033 | `fa80fa0f96d37d9fa3ce5e9679c05fb0bdc74982` | same commit as 001 |
| 034 | `661d0e1e2199e52c8b14e01cb1b1bd41a49675f7` | byte-exact match |
| 035 | `fa80fa0f96d37d9fa3ce5e9679c05fb0bdc74982` | same commit as 001 |
| 039 | `fa80fa0f96d37d9fa3ce5e9679c05fb0bdc74982` | same commit as 001 |
| 042 | `44cabfcabc619e0cb120587b483e917c277f54e5` | byte-exact match |
| 044 | `45a451a163e89046a3ee079077d4cfab57fa2444` | byte-exact match |
| 045 | `03d19bb988fe283457c49fc217bfd68f1f849633` | byte-exact match |

The full per-rule citation is in `contracts/rule-classification-and-citation.md`.

**`reconcile-change-scope-tensions` / URL template for the excluded,
non-numeric directive**: not applicable — this directive carries no numeric
code and is out of scope by construction (spec Edge Cases), so no manifest
or citation is authored for it. No URL-template accommodation is needed
because this mission never cites it; recorded here only to close the loop
on the binding constraint's "note one directive has no numeric code" clause.

**`source.normative` anchors**: `docs/rubric/sop-rule-taxonomy.md#<slug>`,
where `<slug>` is GitHub's standard heading-slug transform (lowercase, strip
punctuation/backticks/leading ordinal, hyphenate spaces) applied to the
class's own heading text — e.g. `### 3. \`confirm-before-destructive\`` →
`#confirm-before-destructive`. These are high-confidence (the class names
are already hyphenated identifiers with no special characters the algorithm
would treat ambiguously) but **not click-verified in a rendered browser**
during planning (no browser tool available in this environment) — flagged
as a cheap, five-minute implementation-time check (click each anchor link
once) rather than asserted as visually confirmed.

**Alternatives considered**: pinning every citation to a single shared
"upstream main HEAD" SHA — rejected; a per-file last-touch SHA is more
precise (describes exactly the commit that produced the cited content, not
an arbitrary later commit that happens to still contain it unchanged) and
matches the house citation-pinning discipline already established in
`conformance/DECISIONS.md`.

---

## 6. Confirm-before-destructive loader guard — why it cannot fire here (binding constraint 3, part 1)

**Decision**: no manifest entry in this mission sets an `assertionKind`
field.

**Rationale, verified against `manifest.ts:310-320`**: the loader's guard is

```ts
if (entryAny["assertionKind"] === "confirm-before-destructive" &&
    entryAny["confirmationKind"] === undefined) { throw ... }
```

`assertionKind` and `confirmationKind` are **not** fields of
`SOPRuleManifestEntry` (they belong to `BinaryAssertion`, which lives on
`ComplianceProbe`/`AdversarialProbe` objects in the manifest's optional
`probes:` section — a section this mission's manifests never populate,
C-003). The Ajv schema's `additionalProperties: true` on rule entries means
an author *could* add a stray `assertionKind` key directly to a rule entry,
but nothing requires it, and the taxonomy-class citation this mission uses
(`source.normative` prose, e.g. `#confirm-before-destructive`) does not
require it either — the class is documented, not structurally declared on
the entry. **No rule entry in this mission's 13 manifests + 1 control sets
`assertionKind` at all**, so `entryAny["assertionKind"] === "confirm-before-destructive"`
is `undefined === "confirm-before-destructive"` → `false` for every entry,
unconditionally. The guard is dead by construction, not by luck — this is
recorded here so a later reader does not mistake its permanent silence for
an untested code path (the same discipline the spec itself applies to
`MISSING_SOURCE`'s permanent silence).

## 6b. The other three loader guards (binding constraint 3, parts 2–4)

- **Duplicate `ruleId`** (`manifest.ts:287-290`): checked *within* a single
  manifest file's `rules[]` array only (the loader is called once per
  manifest path; there is no cross-file registry). Every manifest in this
  mission carries a small, directive-scoped rule set (2–11 entries) with
  ruleIds of the form `<directive-number>-r<n>` (e.g. `045-r1`..`045-r4`) —
  trivially unique within each file by construction (sequential numbering,
  never reused).
- **Empty `source.normative`** (`manifest.ts:292-297`): every entry's
  `source.normative` is a non-empty citation string (§5 above); none is
  omitted or blank.
- **`pass-k` with `passThreshold !== k`** (`manifest.ts:299-308`): every
  binary/`pass-k` entry explicitly sets `passThreshold` equal to its own
  `k` (both `3`), matching FR-002's literal wording ("`passThreshold ==
  k`") for **all** binary entries, not only the two FR-002 names by
  example (045, 029) — the taxonomy's Aggregation Rules table states this
  is uniform across all five binary classes, not special-cased to two
  directives.

---

## 7. `k` / `passThreshold` defaults

**Decision**: binary (`pass-k`) entries use `k: 3, passThreshold: 3`;
judge (`k-of-n`) entries — including the 21 UNMAPPED-fallback entries
(count corrected post-plan-gate, §4/§8; was 20) — use `k: 5,
passThreshold: 3` (the taxonomy's own documented k-of-n default,
`Math.ceil(k/2)` majority, made explicit rather than omitted).

**Rationale**: with `probeIds: []` throughout (C-003), no run ever actually
executes against these values in this mission — they are structural
placeholders the loader validates (`k: integer, minimum 1`) and that M4
will override with real, evidence-based values once probes attach.
Choosing small, taxonomy-consistent, explicitly-documented defaults (rather
than `k: 1`, which would trivially satisfy the schema but signal nothing
about intended rigor) gives M4 a sane, labeled starting point and avoids a
`k: 1` reading as "this rule only needs one passing run to be considered
safety-critical," which would misrepresent the taxonomy's own "every run
must pass" pass^k semantics.

**Alternatives considered**: `k: 1` throughout — rejected for the reason
above. Per-directive-tuned `k` values reflecting each rule's actual
real-world risk — rejected as premature: with zero probes attached, any
such tuning would be invented, not evidence-based, violating this project's
measured-not-asserted policy the same way an invented CI-time NFR would.

---

## 8. Absence-case analysis (mission brief's "absence lesson") — per guard

Traced directly against the runtime call chain
(`runManifestSuite` → `loadManifestPhase` → `runLintPhase` →
`runStaticLint` → `readSOPFile`/`loadAndValidateManifest`), not assumed:

**[Corrected post-plan-gate]** The "Manifest file missing" row below was
originally written as "`MANIFEST_ERROR` JSON, exit `1`, no jq needed." **That
was wrong** — verified by running the real built CLI against a missing
manifest path:

```
$ node dist/cli/index.js sop run conformance/doctrine/does-not-exist.yaml --json
muster: cannot read sop manifest "...": ENOENT: ...
REAL EXIT CODE: 2
```

`doSopRun` (`src/cli/index.ts:1436`) calls
`readFileOrThrow(absManifestPath, "sop manifest")` **before** it calls
`runSopManifestSuite` at all — this is a CLI-level pre-check the plan's
original trace (which started at `loadAndValidateManifest`, inside
`runSopManifestSuite`) missed entirely. `readFileOrThrow` throws an
`ExecutionError` on ENOENT (`src/cli/index.ts:150-156`), uncaught by
`doSopRun`, which propagates to `runCli`'s top-level catch
(`src/cli/index.ts:1979-1982`): a plain `muster: cannot read sop manifest
"...": ...` line to stderr and exit **`2`** — **no JSON `--json` output is
ever produced for this case, so there is no `MANIFEST_ERROR` finding to
read.** `loadAndValidateManifest`'s own internal ENOENT handling (the
`MANIFEST_ERROR` finding this row originally described) is real code that
exists in the adapter, but it is unreachable from the CLI's `sop run` path
specifically because `doSopRun`'s earlier `readFileOrThrow` pre-check
always throws first. The corrected row:

| Failure mode | What actually happens | Severity / exit code | Who catches it |
|---|---|---|---|
| **Manifest file missing** (`conformance/doctrine/<x>.yaml` deleted) | `doSopRun`'s own `readFileOrThrow(absManifestPath, "sop manifest")` (`src/cli/index.ts:1436`) throws an `ExecutionError` on ENOENT **before** `runSopManifestSuite`/`loadAndValidateManifest` is ever reached; uncaught by `doSopRun`, it propagates to `runCli`'s top-level catch (`:1979-1982`) | Plain `muster: cannot read sop manifest "...": ENOENT ...` to **stderr**, **no `--json` output at all** → **exit `2`** (NOT exit `1`, NOT a `MANIFEST_ERROR` finding — corrected from this row's original, incorrect claim) | `runCli`'s top-level `catch (error instanceof ExecutionError)`, one layer above the adapter's own internal `loadManifestPhase` try/catch, which never runs for this input |
| **`sopFile` path resolves to nothing** (directive file deleted, or `sopFile:` typo'd) | `loadManifestPhase` resolves the path but does not check existence; `runLintPhase` calls `runStaticLint`, whose first line `readSOPFile(sopFilePath)` throws (ENOENT), **uncaught inside `runStaticLint` itself** (`index.ts`'s `runStaticLint` does not wrap step 1 in try/catch); `runLintPhase`'s own `try/catch` converts this to a `STRUCTURAL_ABSENCE` finding | `severity: "error"` → `passed: false` → **exit `1`** | `runLintPhase`, one layer up from where M1's equivalent case would be caught |
| **Directive file deleted upstream** (same mechanism as above — `sopFile` now dangling) | Identical to the previous row — `readSOPFile` cannot distinguish "never existed" from "existed, now deleted" | Same: `STRUCTURAL_ABSENCE`, exit `1` | `runLintPhase` |
| **A rule entry silently dropped from a manifest** (e.g. an edit accidentally deletes one `- ruleId: ...` block, leaving the file structurally valid) | **Nothing in muster's own code path detects this.** `checkRuleTextPresence`, `detectUndefinedPrecedence`, and `detectToolDrift` all iterate `manifest.rules` — a shorter array simply means fewer checks run; the suite reports `passed: true`, **exit `0`**, with a clean-looking `--json` output that silently covers fewer rules than intended | **No finding of any kind; exit `0` — a false-clean pass** | **Nothing, by design of the adapter** — this is exactly M1's "absence lesson": a control (or here, a whole rule) that disappears produces a *cleaner*-looking result, not a louder one |
| **Control manifest's `ruleText` hollowed out** (a future edit "softens" the mutation toward a shorter/more generic string that starts matching real content) | `checkRuleTextPresence`'s `.includes()` starts returning `true`; the `RULE_DRIFT` finding for that entry disappears; `passed` stays `true`, `--json` shows zero `RULE_DRIFT` findings | **No `RULE_DRIFT` finding — the control silently stops discriminating** | Nothing in muster itself; must be an explicit CI assertion (FR-005) |

**Disposition — this mission adds one script beyond what FR-001–FR-006
literally require**, specifically to close the fourth row (the one gap
muster's own error paths do not cover): `conformance/scripts/
check-doctrine-manifest-completeness.mjs` (§9 below, IC-0X in plan.md),
counting each directive's real `integrity_rules` bullets and each
manifest's real rule entries, and failing loudly, by name, on any mismatch.
This mirrors M1's own FR-007 addition (a completeness check the original
issue's FR table didn't ask for, added post-spec-gate once the gap was
spotted) — flagged here as an author-added defensive control per the same
house convention, not a requirement this mission's spec.md already states.

The fifth row (control hollowing) is closed by the **same** `grep -F -c`
mechanism §3 already establishes for uniqueness (a `0`-count assertion on
the control's drifted text, run alongside the drift-gate script) — no
separate tool is needed; the CI gate script (§9) runs both the "shipped
manifests must be clean" loop and the "control must discriminate" check in
one invocation, and the control's `grep -F -c` check is folded into its
authoring/quickstart procedure (quickstart.md §3).

**[Corrected post-plan-gate]** The paragraph below originally claimed all
three of the first three rows are hard `error`-severity, exit-`1` failures
muster produces unconditionally, needing no independent re-guarding. That
claim is only true for rows 2–3 (`STRUCTURAL_ABSENCE`, exit `1`). Row 1
(manifest file missing) is exit `2` with **no JSON output at all** (see the
corrected row above) — a categorically different failure shape that a
JSON-parsing jq filter cannot select findings out of, because there is no
JSON to select from. This distinction is why the drift-gate script (§10;
`contracts/doctrine-drift-gate-contract.md`) was hardened, post-plan, to
capture muster's real exit code and treat non-zero/non-JSON output as its
own named hard gate failure **independent of jq** — jq alone was never
sufficient for row 1, and the original text's "no jq needed" framing (while
correct that muster's own exit code already reflects the failure) elided
the fact that the CI *gate script itself*, as originally pseudocoded,
never inspected that exit code at all, so nothing in the script would
actually have surfaced it as a **named** failure rather than an opaque `jq`
crash on empty input.

Rows 2–3 (`STRUCTURAL_ABSENCE`) **are** exit `1` with valid JSON, so a jq
filter can select them — but the drift-gate script's Phase 1 filter,
before this fix, did not: it selected only `RULE_DRIFT`/`MISSING_SOURCE`/
`MANIFEST_ERROR`, omitting `STRUCTURAL_ABSENCE` entirely, so a deleted
directive file or a typo'd `sopFile:` path reported `count=0` in the jq
gate even though muster's own `passed` field was already `false`. This is
now fixed: `contracts/doctrine-drift-gate-contract.md`'s Phase 1 filter
includes `STRUCTURAL_ABSENCE` (binding operator decision, applied
post-plan-gate — this is the third recurrence of the absence-class defect
in this programme, so it is fixed now rather than deferred as a named
gap). Re-implementing a duplicate *detector* for rows 2–3 inside this
mission's own completeness script would still be the kind of
redundant-authority split directive 044 warns against — the fix is to
*select* the finding muster already produces, not to re-detect it
independently — and `contracts/doctrine-manifest-completeness-contract.md`
now states explicitly that its filename-stem pairing never reads
`sopFile:`, so the jq gate's `STRUCTURAL_ABSENCE` selection is the sole
guard for that failure mode, not a redundant second one.

---

## 9. CI integration — same workflow file, new job, corrected framing (task's CI-decision requirement)

**Decision**: add **one new job**, `sop-doctrine-conformance`, to the
**same** `.github/workflows/conformance.yml` M1 created — not a sibling
file — and rename the file's top-level `name:` from `Skills Static
Conformance` to `Static Conformance` so the workflow-level name stops
claiming to be skills-only once a second suite's job lives in it. The
existing job's own job-level name (`Skills static conformance (muster)`)
is untouched; the new job is named `SOP doctrine conformance (muster)`.

**Rationale — same file, not a sibling**: the mission's own Dependencies &
Assumptions section already commits to this ("`.github/workflows/
conformance.yml` is shared with M1's step across missions... this mission
adds one more step") and C-001's `write_scope` names the file explicitly
(not a new path) — this is a locked spec decision, not a fresh design
choice, restated here so the "which file, and why" question the task brief
poses has a citable answer rather than an implicit one.

**Two claims in the task brief corrected against the real file** (measured,
not assumed, per this project's own citation discipline): the task brief
describes M1's shipped workflow as having "SHA-pinned actions" and
`permissions: contents: read`. **Neither was actually present** in the
merged `.github/workflows/conformance.yml` at the time this plan was
originally written — it used `actions/checkout@v6` (a movable tag
reference, not a SHA pin) and declared no `permissions:` block at all
(confirmed by reading the file directly, not inferred).

**[Corrected post-plan-gate — PR #29 collision, binding operator
decision]** The paragraph originally continued by having this mission
**add** `permissions: contents: read` itself, crediting it as this
mission's own hardening contribution, and leaving SHA-pinning as a
named, not-fixed-here follow-up. That framing no longer holds: PR #29
(`MOES-Media/spec-kitty`, open, in final verification at the time of this
correction) inserts an identical `permissions:\n  contents: read` block at
the identical anchor in `.github/workflows/conformance.yml` — immediately
after `- main`, immediately before `jobs:` — and additionally SHA-pins both
existing actions. **The operator's decision: PR #29 lands first.**
Consequently:
- This mission **drops the claim** that `permissions: contents: read` is
  its own contribution. By the time this mission's WP03 runs, that block
  will already be present in the file.
- WP03's implementation **must check for an existing `permissions:` key
  before inserting one**, and must not duplicate it if PR #29 has already
  landed (which the operator's sequencing decision guarantees it will
  have).
- WP03 should **expect both existing actions to already be SHA-pinned**
  by PR #29, and must not re-pin (to a different SHA) or unpin them back
  to a tag reference. The new job's own `actions/checkout` step should
  match whatever pinning convention PR #29 leaves in place (SHA, not
  `@v6`), rather than introducing a fresh tag reference inconsistent with
  the rest of the file.
- `conformance/README.md`'s known-gaps section (previously slated to note
  "neither job in this file is SHA-pinned") must instead simply not carry
  that now-false gap note — SHA-pinning will already be done, by PR #29,
  not by this mission.
- **Dependency recorded, not rediscovered**: this mission depends on PR
  #29 landing to `main` before WP03 runs (in addition to the pre-existing
  dependency on M1's own merge, spec.md's Dependencies & Assumptions
  section) — see the Work-Package Outline's WP03 entry and IC-06 in
  plan.md, both updated to cite PR #29 explicitly.

**New job's steps**:
1. `actions/checkout@v6` (matches the sibling job).
2. `bash conformance/scripts/check-doctrine-drift-gate.sh` — FR-004's jq
   gate over the 13 shipped manifests, plus FR-005's inverted control
   assertion, in one script (§10).
3. `node conformance/scripts/check-doctrine-manifest-completeness.mjs` —
   the absence-guard completeness check (§8).

**Alternatives considered**: 13 separate `garrison-hq/muster-action@v1`
invocations (one per manifest) — rejected; the Action's `command`/`args`/
`version` input surface has no built-in way to pipe its own output through
`jq` for the multi-kind finding check FR-004 requires, and 13 near-identical
steps would be far less legible than one loop. A sibling workflow file —
rejected per the "same file" rationale above; it would also duplicate the
`on: pull_request / push: main` trigger block for no benefit.

---

## 10. The jq gate — exact design (FR-004/FR-005)

**Decision**: `conformance/scripts/check-doctrine-drift-gate.sh`, a
dependency-light Bash script using `jq` (pre-installed on GitHub's
`ubuntu-latest` runner image — part of the standard toolset, not a new
dependency this mission introduces) against the real `--json` output of
`npx --yes @garrison-hq/muster@1.1.0 sop run <manifest> --json`, looping
`conformance/doctrine/*.yaml` for the main gate and separately invoking the
one control manifest with the inverted assertion. Full contract:
`contracts/doctrine-drift-gate-contract.md`.

**Filter for the main gate** (must find nothing) — **[Corrected
post-plan-gate]: `STRUCTURAL_ABSENCE` added**, see
`contracts/doctrine-drift-gate-contract.md`'s "Why `STRUCTURAL_ABSENCE` is
in this filter" note for why this is a binding operator decision, not a
style choice a future edit may quietly revert:
```sh
jq '[.lintFindings[] | select(.kind=="RULE_DRIFT" or .kind=="MISSING_SOURCE" or .kind=="MANIFEST_ERROR" or .kind=="STRUCTURAL_ABSENCE")]'
```
**Filter for the control** (must find at least one `RULE_DRIFT`):
```sh
jq '[.lintFindings[] | select(.kind=="RULE_DRIFT")] | length'
```

This filter alone is not the complete gate: it only ever sees valid JSON.
`contracts/doctrine-drift-gate-contract.md`'s "Failure handling" section
additionally requires the script to capture muster's real exit code and
treat non-zero exit or non-JSON output as a hard failure independent of
this filter (§8's corrected absence table shows exactly why — a missing
manifest file produces no JSON at all, exit `2`, which no `jq` filter can
inspect).

**Rationale for `jq` over a Node script here specifically**: FR-004's own
text names this "a jq gate," and `jq` is the more literal, directly
inspectable implementation of "parse `--json` output and check finding
kinds" — a thin Bash+jq script keeps the CI step's logic visible in the
workflow's own log output (each `jq` invocation is one readable line) without
Node-script indirection. This is a **different** tool choice than the
`check-doctrine-manifest-completeness.mjs` absence-guard script (§8), which
stays a dependency-free Node script (M1's own precedent) because that
check's job — counting YAML bullets across two different file shapes — is
materially easier to write correctly and extend later as JS than as chained
`jq`/`grep` pipelines; the two scripts solve different-shaped problems and
each uses the tool that fits its shape, not a single tool chosen for
uniformity's own sake.

**Alternatives considered**: implementing the same JSON-finding-kind check
in Node instead of `jq` — considered and rejected only for the readability
reason above; either would be functionally equivalent and dependency-free
on a GitHub-hosted runner (`jq` ships on `ubuntu-latest`; Node already ships
for the `npx` step itself).

---

## 11. Needing a human decision (not resolved autonomously)

- **The taxonomy gap (§4)** — **[Corrected post-plan-gate: counts and
  directive set both changed]**. This bullet originally read "20 of 45
  rules (44%), including all of 039 and entire directives 001/010." Since
  then: (1) the operator has **resolved** the 044 half of this question —
  044's classification is reverted to UNMAPPED (binding decision, §4
  above), not left open; (2) 010 has been reconciled to `output-format`
  (Fix 5 reconciliation pass) and is no longer part of the fully-unmapped
  set. The corrected count: **21 of 45 rules (47%)**, including all of 039
  and entire directives 001/044, do not fit any existing
  `sop-rule-taxonomy.md` class. This mission ships them as documented
  `UNMAPPED` judge-fallback entries rather than either inventing a new
  class (forbidden by scope) or substituting a different judge-directive
  set (a scope change to FR-001's locked list). **What remains genuinely
  open for the operator**: whether to commission a taxonomy-extension
  mission before M4 attaches probes to these 17+4 rules, or accept the
  substitution latitude the spec-quality checklist explicitly reserved and
  swap one or more of 001/039/044 for a cleaner-fitting judge directive.
  This plan does not make that remaining call.
- **GitHub anchor slugs for `source.normative`** (§5): high-confidence,
  not click-verified in a rendered browser (no browser tool available this
  session) — a five-minute manual click-through before merge is recommended.
- **`garrison-hq/muster-action@v1`'s actual input schema** was already
  flagged as a risk in M1's own plan.md (research.md §5 there) and remains
  unverified against the Action's real `action.yml`; this mission's new job
  does not use the Action at all (it shells out to `npx` directly), so this
  risk does not block M3, but it remains open for any future mission that
  adds a third `muster-action@v1` invocation to this file.
