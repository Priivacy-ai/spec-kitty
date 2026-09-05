# Data Model: Skills Static Conformance Suite

**Mission**: `sk-skills-static-conformance-01KYG7GE` | **Date**: 2026-07-27

Refined from spec.md §Key Entities and §Requirements. Every entity here is
**data**, not code — this mission ships YAML, Markdown, and one dependency-
free Node script under `conformance/**`. Nothing modifies `src/doctrine/**`
(spec-kitty runtime) or any muster source file (C-001).

---

### SkillsManifest

The single file `conformance/skills/manifest.yaml`. Top-level shape (fixed by
muster, not by this mission — `research.md` §3):

```yaml
cases:
  - id: <string>              # unique across the manifest
    type: static               # this mission emits only "static" cases
    skillDir: <string>         # relative to this file's own directory
    profile: base               # this mission uses "base" for every case
    expectations:
      ok: <boolean>
      violations: []            # documentation only — never compared by muster
```

**Invariants:**
- Exactly 54 cases: one `StaticCase` per built-in skill (53) + one
  `ControlCase` (1) — FR-001, FR-007.
- Every `id` is unique (muster does not enforce this — a duplicate `id`
  would silently produce two result rows with the same label; authoring
  discipline only).
- Every `skillDir` is expressed relative to `conformance/skills/` (this
  file's own directory) and resolves, textually, to either
  `../../src/doctrine/skills/<name>` (the 53 `StaticCase` entries) or
  `control/<name>` (the one `ControlCase`) — never an absolute path, never a
  path resolving above the repository root (Acceptance Scenario 1).
- `profile` is `base` for every case — no case in this mission opts into the
  `anthropic` profile (out of scope; the Anthropic profile is a
  skills-adapter concept unrelated to this suite's purpose).
- Manifest authoring convention the FR-007 completeness check depends on
  (documented here and in the `"$comment"` clause of
  `contracts/skills-manifest-case.schema.json`, not the schema's structural
  fields): each case's `- id:` line and its `skillDir:` line appear as
  siblings inside one list item, at consistent indentation, so a line-based
  scan can recover `(id, skillDir)` pairs without a YAML parser.

---

### StaticCase

One manifest entry for a built-in skill, expected to be conformant.

| Field | Value |
|---|---|
| `id` | Derived from the skill directory name, e.g. `sk-skills-static-conformance-01KYG7GE` is a mission slug, not a case id — case ids instead mirror the skill name itself, e.g. `id: ad-hoc-profile-load` for `src/doctrine/skills/ad-hoc-profile-load/`. One-to-one with `src/doctrine/skills/*` (53 entries). |
| `type` | `"static"` |
| `skillDir` | `../../src/doctrine/skills/<name>` |
| `profile` | `"base"` |
| `expectations` | `{ ok: true, violations: [] }` |

**Invariant**: every `StaticCase`'s `<name>` exists as a real directory under
`src/doctrine/skills/` at the time the manifest is authored (pre-verified:
all 53 pass muster's three hard static gates — spec Dependencies &
Assumptions). FR-007's completeness check re-verifies this invariant on
every CI run rather than trusting it as a one-time fact.

---

### ControlCase

The one manifest entry for the FR-005 discrimination fixture.

| Field | Value |
|---|---|
| `id` | `control-name-mismatch` |
| `type` | `"static"` |
| `skillDir` | `control/name-mismatch` |
| `profile` | `"base"` |
| `expectations` | `{ ok: false, violations: [] }` |

Backing fixture: `conformance/skills/control/name-mismatch/SKILL.md`, whose
frontmatter `name` field is deliberately **not** equal to `name-mismatch`
(the parent directory's basename) — tripping the name-must-equal-directory
static gate (research.md §4). This is the only manifest entry excluded from
the FR-007 completeness check's `src/doctrine/skills/` comparison (its
`skillDir` does not point under that tree).

**Control-case regression invariant** (spec edge case): if a future edit
"fixes" the fixture's name/directory mismatch without updating this case's
declared `expectations.ok` to match, the case will report `ok: true` against
a declared `ok: false` expectation, `passed` becomes `false` by
`passed = ok === expectations.ok`, and the suite fails loudly — this is the
intended fail-safe, not a defect (spec Edge Cases).

---

### DecisionRecordEntry (D1–D5)

`conformance/DECISIONS.md` carries five entries, one per programme decision,
each with: a decision statement, the options considered, the evidence
(file:line citations against muster `v1.1.0` exactly — research.md §2), and
the recommendation. This mission's own D1–D5 text is inherited **verbatim in
substance** from issue #22 §11 (the programme plan), with citations
re-derived per research.md §2 before commit (binding constraint 4).

**Invariant**: every file:line citation in `DECISIONS.md` that points into
`src/cli/index.ts` must resolve, byte-for-byte, against `git show
v1.1.0:src/cli/index.ts` — not muster's HEAD, not any other ref. Citations
into `src/adapters/skills/*` and `src/adapters/rfc1/*` are confirmed
unaffected by the HEAD-vs-tag drift (research.md §2) and are carried as-is.

---

### CompletenessCheckResult (FR-007)

The runtime output shape of `conformance/scripts/check-manifest-
completeness.mjs`, run as a CI step and locally.

```typescript
interface CompletenessCheckResult {
  actualSkillCount: number;       // src/doctrine/skills/* directory count
  manifestStaticCaseCount: number; // total `type: static` cases in the manifest
  missing: string[];               // skill dirs with no manifest case
  extra: string[];                 // manifest-referenced names with no matching dir
  ok: boolean;                     // true iff missing and extra are both empty
                                    // AND manifestStaticCaseCount == actualSkillCount + 1
}
```

**Invariants:**
- Exit code `0` iff `ok === true`; exit code `1` otherwise (never `2` —
  reserved by muster's own convention for internal/tooling errors, not
  reused here to avoid a false "muster errored" reading in CI logs).
- On failure, the printed message names every entry in `missing` and `extra`
  by skill/case name — a bare count mismatch (e.g. "expected 54, got 53") is
  not sufficient (FR-007's explicit requirement).
- The +1 control-case offset is a named constant in the script
  (`CONTROL_CASE_COUNT = 1`), not an inline magic number, and is documented
  at its declaration site (coordinator directive: "must be documented at the
  point of implementation, not left as a magic number").
- The check is independent of, and runs in addition to, muster's own
  `skills run` exit code — a manifest can be complete (FR-007 passes) while
  individual cases still fail their static gates (FR-002 fails), and vice
  versa is impossible by construction (an incomplete manifest cannot make
  `skills run` itself report `ok:true` for a skill it never checks — that
  silent gap is exactly what FR-007 closes).

---

### ConformanceWorkflow

`.github/workflows/conformance.yml` — the GitHub Actions job.

**Trigger**: `pull_request` (any branch) and `push` to `main` (spec
Acceptance Scenario 3).

**Steps** (in order):
1. Checkout (`actions/checkout@v6`, matching this fork's existing workflow
   convention — `research.md` did not need to research this further; it is
   read directly off `.github/workflows/*.yml` in this checkout).
2. `garrison-hq/muster-action@v1` with `command: 'skills run'`,
   `args: 'conformance/skills/manifest.yaml'`, `version: '1.1.0'` — gates on
   muster's own exit code (FR-002, FR-003).
3. `node conformance/scripts/check-manifest-completeness.mjs` — gates on the
   script's own exit code (FR-007). Runs after step 2 so a completeness
   failure and a static-gate failure are both visible in one job's logs
   (order between the two does not otherwise matter — they check disjoint
   things).

**Invariants:**
- No `secrets:` reference anywhere in the file (C-002); no `if:` fork-PR
  guard is needed because nothing here is secret-gated — the whole workflow
  is the "clean, ungated" path the `muster-github-action.md` briefing
  describes for consumers with no behavioral/endpoint inputs set.
- `version: '1.1.0'` is a quoted exact string, never `^1.1.0`, `~1.1.0`, or
  `latest` (C-003, Acceptance Scenario 11).

---

## Invariants Summary

| Invariant | Source | Enforced in |
|---|---|---|
| No `src/doctrine/**` (spec-kitty runtime) file is modified | C-001 | Diff review at merge; scope guard |
| No muster or muster-action source file is modified | C-001 | Diff review at merge; scope guard |
| `skills run` exits 0 fully offline against the real 53+1 manifest | FR-002, AC-1 | Real-CLI verification step (plan.md Verification Strategy) — not unit-test-only |
| Control case flips the suite's exit code both ways | FR-005, AC-2, SC-003 | Manual documented check in README; exercised once during implementation as proof, not re-run every CI job |
| Manifest completeness check both passes on the true tree and fails (by name) on an induced mismatch | FR-007, SC-006 | Real-script verification step (plan.md Verification Strategy), exercised both ways during implementation |
| Workflow requires no secrets, passes on fork PRs | C-002, AC-3 | `garrison-hq/muster-action@v1` static path is inherently secret-free; verified by a real fork-PR-shaped run if feasible, else by inspection (no `secrets:` token in the file) |
| `version` input is an exact string, never a range | C-003, Acceptance Scenario 11 | Code review of `conformance.yml`; grep for `version:\s*['"]?1\.1\.0['"]?$` with no `^`/`~`/`latest` |
| Every `DECISIONS.md` `src/cli/index.ts` citation resolves against `v1.1.0` exactly | Binding constraint 4 | WP02 re-derivation using research.md §2's verified table before commit |
| CI wall-clock is recorded from a real run, never asserted as a ceiling | NFR-001 | `conformance/README.md` timing entry, filled in after the first real green workflow run |
