# Contract: `conformance/scripts/check-doctrine-manifest-completeness.mjs` (absence guard)

**Mission**: `doctrine-rule-manifests-01KYH7AM` | **Date**: 2026-07-27

This script is **author-added, not spec-mandated** — it closes the one gap
in the mission-brief's "absence lesson" table (research.md §8) that
muster's own error paths do not cover: a rule entry silently dropped from a
manifest produces no finding of any kind and a clean `exit 0`. It mirrors
M1's `check-manifest-completeness.mjs` in spirit (dependency-free Node,
same house convention) but compares **rule counts per directive**, not
skill-directory names.

## Invocation

```sh
node conformance/scripts/check-doctrine-manifest-completeness.mjs
```

- **Working directory**: repository root.
- **Arguments**: none. All paths (`src/doctrine/directives/built-in/`,
  `conformance/doctrine/`) are hardcoded relative to the current working
  directory, matching M1's script's own documented rationale (one job, one
  repository layout, no unused generality).
- **Environment variables**: none. No network access.

## Algorithm

1. **Expected rule count per in-scope directive** — read each of the 13
   directive files and count `integrity_rules` bullets via a line-based
   block scan (no YAML parser — same dependency-free rationale as M1's
   script):
   ```js
   // Enter the block at a line matching /^integrity_rules:/
   // Exit the block at the next line matching /^[A-Za-z_]+:/
   // Count lines inside the block matching /^\s*-\s/
   ```
   This exact algorithm was run against all 13 real directive files during
   planning (research.md, and independently cross-checked with an `awk`
   one-liner) and produced: 001→3, 010→2, 018→2, 028→3, 029→2, 030→3,
   033→2, 034→3, 035→3, 039→11, 042→4, 044→3, 045→4 — **summing to
   exactly 45**, matching FR-001's stated total. These 13 numbers are the
   script's ground truth on every run (recomputed fresh each time, never
   hardcoded as a lookup table — the whole point is to catch a *future*
   directive edit or manifest edit going out of sync, not to freeze today's
   count).
2. **Actual rule count per shipped manifest** — read each of the 13
   manifest files as plain text and count lines matching `/^\s*- ruleId:/`
   (the same line-based convention M1's script uses for `- id:`).
3. **Manifest existence** — confirm all 13 expected manifest files exist at
   `conformance/doctrine/<directive-stem>.yaml` (paired 1:1 by filename
   stem, per `contracts/doctrine-rule-manifest-shape.md`'s naming
   convention) and that the control manifest exists at
   `conformance/doctrine/control/045-drifted.yaml` with exactly 1 rule
   entry.

   **This filename-stem pairing is the entire extent of what this script
   checks about a manifest's identity — it never reads or validates a
   manifest's `sopFile:` field.** A manifest can exist at the right path,
   with the right rule count, and still point its `sopFile:` at a deleted
   directive file or a typo'd path; this script would report `OK` for that
   manifest regardless. That specific failure mode (a dangling/typo'd
   `sopFile:` target) is guarded exclusively by
   `contracts/doctrine-drift-gate-contract.md`'s Phase 1 jq filter, which
   selects muster's own `STRUCTURAL_ABSENCE` finding — added there
   specifically because this script cannot see it. The division of labor
   is deliberate and is recorded here so it is not silently assumed to be
   double-covered: **filename-stem pairing** is this script's job;
   **`sopFile:` target existence** is the jq gate's job; neither script
   re-implements the other's guard.
4. **Compare and report** — for each directive, assert
   `actualManifestRuleCount === expectedDirectiveRuleCount`. On any
   mismatch (including a manifest file being entirely absent, treated as
   an actual count of `0`), print every offending directive by name and
   both counts; exit `1`. On full agreement across all 13 directives plus
   the control's existence, print a one-line confirmation and exit `0`.

## Output shape

- **stdout, success** (exit `0`):
  ```
  doctrine manifest completeness: OK (13 manifests, 45 rules, 1 control)
  ```
- **stdout, failure** (exit `1`), naming every mismatch explicitly — a bare
  "45 != 44" is not sufficient (same explicit-naming requirement as M1's
  FR-007 script):
  ```
  doctrine manifest completeness: MISMATCH
    045-prs-only-and-read-intent: directive has 4 integrity_rules, manifest has 3 rule entries (missing: 1)
  ```
  or, for a missing manifest file entirely:
  ```
    029-agent-commit-signing-policy: manifest file conformance/doctrine/029-agent-commit-signing-policy.yaml not found (expected 2 rules, found 0)
  ```
  or, for a missing/empty control:
  ```
    control manifest conformance/doctrine/control/045-drifted.yaml not found or has 0 rule entries (expected exactly 1)
  ```

## Exit codes

| Code | Meaning |
|---|---|
| `0` | All 13 directive/manifest rule counts match exactly, and the control manifest exists with exactly 1 rule. |
| `1` | Any per-directive mismatch, missing manifest file, or missing/empty control manifest — every offender named. |
| (never `2`) | Reserved for "muster itself errored" — this script never invokes muster, so `2` never applies to it. |

## CI wiring

Step 3 of 3 in the new `sop-doctrine-conformance` job:

```yaml
# round-trip: skip: GitHub Actions workflow-step fragment showing how the completeness check is wired into conformance.yml — CI wiring, not a Pydantic payload; the executable coverage is the workflow file itself
- name: Verify doctrine manifest rule-count completeness (absence guard)
  run: node conformance/scripts/check-doctrine-manifest-completeness.mjs
```

Placed after the drift gate so both a drift failure and a completeness
failure are visible in one job's log (order between the two does not
otherwise matter — disjoint checks, same pattern as M1's step ordering).

## Non-goals

- Does not validate `ruleText` content, `gradingClass`/`aggregation`
  correctness, or citation shape — those are muster's own Ajv/semantic
  checks (via the drift gate) plus manual review against
  `contracts/rule-classification-and-citation.md`.
- Does not validate `sopFile:` targets. Pairing is by filename-stem
  convention only (Algorithm §3 above) — a manifest whose `sopFile:` points
  at a missing or misspelled path still reports `OK` here. The drift gate's
  `STRUCTURAL_ABSENCE` filter entry (`contracts/
  doctrine-drift-gate-contract.md`) is the sole guard against that failure
  mode; this script does not duplicate it.
- Does not detect a rule entry whose `ruleId` was duplicated **and** whose
  count still happens to match (e.g., one entry deleted, another
  copy-pasted twice) — muster's own loader already throws on duplicate
  `ruleId` (`MANIFEST_ERROR`, caught by the drift gate), so this script
  does not re-implement that check.

---

## Amendment A1 — behavioral rule entries (mission `doctrine-behavioral-suite-01KYW5XK`, FR-005, 2026-08-02)

M3 shipped this contract when every manifest rule entry was
directive-derived and `probeIds:` was `[]` everywhere (C-003). M4's FR-005
appends behavioral rules — judge-graded entries carrying an inline
`probes:` scenario — to `010`, `039` and `044`, in the same manifests, with
the same `sopFile:` and the same existing rule IDs. A behavioral rule has
no corresponding `integrity_rules` bullet, so under the unamended Algorithm
§2 the three manifests reported `missing: -1`: the guard was counting a
category it was never written to count.

**Amended Algorithm §2.** The actual count is the number of
**directive-derived** rule entries — those whose `probeIds:` is the empty
list. Behavioral entries (non-empty `probeIds:`) are counted separately and
reported, never compared against the directive's bullet count.

Everything else is unchanged, deliberately:

- The comparison stays **exact**, not `>=`. A dropped directive integrity
  rule still lands as `actual < expected` and still fails. Verified by
  mutation on both the M3 tree and the M4 tree.
- The discriminator is **`probeIds`, never `gradingClass`**. 22 of M3's 45
  directive-derived rules are `gradingClass: judge` with `probeIds: []`
  (all 3 of `001`'s, all 11 of `039`'s, 3 of `044`'s, one each in `030`,
  `033`, `034`, `035`, `045`); excluding judge-graded entries would drop
  `001` to expected-3/actual-0 and blind the guard across half the
  corpus.
- An entry whose `probeIds:` cannot be classified is a **named failure**,
  never defaulted to either class.

**Interlock with the drift gate (new, load-bearing).** The drift gate
excuses a behavioral rule from the verbatim-`ruleText` lint (see that
contract's Amendment A1). Attaching a probe to one of M3's quoted rules
would therefore buy it a drift-lint exemption — except that doing so also
removes it from this guard's directive-derived count, which then fails with
`actual < expected`. Neither half may be weakened alone.
