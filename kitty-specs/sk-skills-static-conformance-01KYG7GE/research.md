# Research: Skills Static Conformance Suite

**Mission**: `sk-skills-static-conformance-01KYG7GE` | **Date**: 2026-07-27

No `[NEEDS CLARIFICATION]` markers remained after the spec gate (autonomous
specify run against a fully self-contained seed issue). Planning proceeded
autonomously per operator instruction; the items below are the research
tasks the planner ran to convert the spec's technical facts into a concrete
design, not clarifications of an ambiguous spec. FR-007 (manifest
completeness) was added mid-plan by explicit operator decision — its own
research is included below (item 6).

---

## 1. Version pin (C-003)

**Decision**: pin `@garrison-hq/muster` to exact version `1.1.0`.

**Rationale**: `npm view @garrison-hq/muster version` (run 2026-07-27) returns
`1.1.0` — the currently published npm version, and the same version the spec
and issue both target. Pinning the published version (not a range, not
`latest`) satisfies C-003 and NFR-002 (byte-reproducible given a pinned
version).

**Alternatives considered**: pin to a semver range (`^1.1.0`) — rejected,
explicitly forbidden by C-003 and Acceptance Scenario 11. Pin to the git tag
`v1.1.0` directly via a git dependency — rejected; the mission consumes
muster as a published npm CLI via `npx`/`npm ci`, not as a source dependency,
and a registry version pin is simpler and is what `muster-action`'s own
`version` input expects (see item 5).

---

## 2. Citation re-derivation against the pinned version (binding constraint 4)

**Decision**: every `src/cli/index.ts` citation inherited from issue #22 and
carried into spec.md was independently re-derived against the muster repo's
actual `v1.1.0` git tag (commit `6bdb070`, verified via
`git rev-parse v1.1.0` in the muster checkout at
`/home/jeroennouws/dev/garrison-hq/muster`). The muster checkout's current
HEAD is `v1.1.0-4-gfc4dcba`, four commits past the tag — `git show
v1.1.0:<path>` was used throughout to read the exact tagged blob, not the
working tree.

Verified mapping (HEAD-computed citation → v1.1.0-exact citation):

| Citation subject | Issue #22 / spec.md citation (muster HEAD, `v1.1.0-1-g8953ee8`) | Re-derived v1.1.0 citation | Verified content at that line |
|---|---|---|---|
| Manifest-relative path resolution (FR-001, D4's rationale) | `src/cli/index.ts:1316` | `src/cli/index.ts:993` | `const baseDir = dirname(absManifestPath);` — directly below the comment "Skills manifest paths (skillDir, querySetPath) resolve against the manifest's own directory" |
| Static case pass/fail rule (FR-005) | `src/cli/index.ts:1279` | `src/cli/index.ts:956` | `const passed = ok === c.expectations.ok;` |
| Bare-cast manifest parsing, no schema validation (FR-006 known gap) | `src/cli/index.ts:1319` | `src/cli/index.ts:996` | `const parsed = parseYaml(raw) as { cases: SkillsManifestCase[] };` |
| Behavioral cases unconditionally skipped, no client built (correction #4) | `src/cli/index.ts:1330-1334` | `src/cli/index.ts:1010` | `results.push({ id: c.id, type: "behavioral", passed: true, skipped: true });` (the multi-line HEAD statement collapsed to one line by v1.1.0) |

`src/adapters/skills/*` citations are confirmed **unaffected** by the
HEAD-vs-tag drift, spot-checked directly against the `v1.1.0` tag:
- `src/adapters/skills/schema.ts:18-33` (frontmatter Ajv schema,
  `additionalProperties: true`) — byte-identical at v1.1.0.
- `src/adapters/skills/validate.ts:18-24` (agentskills.io SHA constant +
  per-field `§...@<SHA>` section strings) — byte-identical at v1.1.0.

**Action for WP02**: use the re-derived table above as the verified starting
point for `conformance/DECISIONS.md`'s D1–D5 evidence citations and the
correction-#4 note. Because `v1.1.0` is an immutable git tag, these line
numbers cannot drift further — WP02 does not need to re-verify from scratch,
only to confirm no new citations were introduced beyond this set and to
carry these four re-derived lines into the decision record text.

**Alternatives considered**: leave the HEAD-computed citations as-is and
footnote the drift — rejected; binding constraint 4 requires the decision
record itself to carry correct citations, not a footnote explaining they
might be wrong.

---

## 3. Manifest case shape (data model source of truth)

**Decision**: the manifest's `cases:` list items follow muster's own
`SkillsManifestStaticCase` / `SkillsManifestBehavioralCase` TypeScript union,
read directly from `src/cli/index.ts` at the `v1.1.0` tag:

```typescript
interface SkillsManifestStaticCase {
  id: string;
  type: "static";
  skillDir: string;
  profile: SkillProfile;              // "base" | "anthropic"
  expectations: { ok: boolean; violations: unknown[] };
}

interface SkillsManifestBehavioralCase {
  id: string;
  type: "behavioral";
  skillDir: string;
  profile: SkillProfile;
  querySetPath: string;
  runsPerQuery: number;
  threshold: number;
  isControl: boolean;
}
```

The manifest document itself is `{ cases: SkillsManifestCase[] }` — parsed
via `parseYaml(raw) as { cases: SkillsManifestCase[] }` (the bare cast,
FR-006's first known gap: no Ajv/schema validation of this shape at runtime).

This mission emits **only** `SkillsManifestStaticCase` entries (54 total: 53
skills + 1 control) — no `type: behavioral` entries, consistent with the
spec's static-only scope and the fact that `doSkillsRun` unconditionally
records behavioral cases as skipped without constructing a client.

**`skillDir` resolution**: `resolvePath(baseDir, c.skillDir)` where
`resolvePath` is Node's `path.resolve` and `baseDir = dirname(absManifestPath)`
— i.e., resolution is against the manifest file's own directory, confirmed at
`src/cli/index.ts:948` (the call site) and `:993` (the `baseDir` derivation).
`path.resolve` performs **no traversal guard** — it will resolve
`../../anything` from `baseDir` even above the repository root with no error.
This confirms the spec's own clarification (Acceptance Scenario 1) that
"`../..`-free" is a semantic constraint on the plan's authored paths, not a
runtime-enforced boundary in muster itself.

**Alternatives considered**: none — this is muster's fixed, already-shipped
contract; the mission has no latitude here by design (C-001: zero muster
changes).

---

## 4. Discrimination control design (FR-005)

**Decision**: one fixture directory `conformance/skills/control/name-mismatch/`
containing a `SKILL.md` whose frontmatter `name` field does not equal its
parent directory's basename (`name-mismatch`). This trips the one static
gate that is purely structural and requires no content heuristics: the
name-must-equal-directory-basename rule (case-sensitive per the reference
skills-adapter mission's own data-model.md invariant #7). The manifest case
declares `expectations: {ok: false, violations: []}` (the `violations` array
is documentation only — FR-006's second known gap, never itself compared by
muster, per `passed = ok === c.expectations.ok`).

**Rationale**: a name/directory mismatch is unambiguous, requires no judgment
call about description length or charset edge cases, and is trivially
demonstrated to a reviewer by reading two lines (the directory name and the
frontmatter `name:` value side by side).

**Alternatives considered**: an oversized `description` (>1024 chars) —
rejected as the control mechanism because it is a less legible fixture (a
reviewer has to count characters rather than eyeball a mismatch); a bad-charset
`name` — rejected for the same legibility reason, though either would work
mechanically. Any of the three hard gates satisfies FR-005's requirement;
name/directory mismatch was chosen purely for reviewability.

---

## 5. `muster-action@v1` input surface

**Decision**: the workflow step targets:

```yaml
- uses: garrison-hq/muster-action@v1
  with:
    command: 'skills run'
    args: 'conformance/skills/manifest.yaml'
    version: '1.1.0'
```

**Rationale**: `garrison-hq/muster-action` is a separate repository this
mission does not have local access to inspect the shipped `action.yml` of.
The best available written specification is the design briefing
`briefings/muster-github-action.md` (muster repo, `/home/jeroennouws/dev/
garrison-hq/muster`), which documents the composite action's input surface
verbatim: `command` (required, the muster subcommand, e.g. `'skills run'`),
`args` (positional target, e.g. a manifest path), `version` (npm
version/range of `@garrison-hq/muster`, default pinned-and-tested), plus
behavioral-only inputs (`endpoint`, `token`, `health-url`, `health-timeout`)
that are irrelevant here because this suite is fully static — leaving them
unset is itself the documented "clean skip" path for anything endpoint-gated
(D5 of that briefing), and matches C-002 (no secrets required).

**Risk flagged, not blocking**: the briefing is a design document, not a
guarantee of the exact shipped `action.yml` schema. **WP03 must verify the
actual input names against the real `garrison-hq/muster-action@v1` tag** (its
`action.yml`) before finalizing `.github/workflows/conformance.yml`, and
adjust field names if the shipped action differs from the briefing (e.g. if
`args` is instead a positional `manifest` input). This is a verification
step, not a design decision this mission controls (C-001 boundary: this
mission cannot change muster-action, only consume it "exactly as shipped,"
per spec Overview).

**Alternatives considered**: hand-rolling the install (`npm install
--no-save @garrison-hq/muster@1.1.0 && npx muster skills run ...` as raw
shell steps, no Action) — rejected; FR-003 explicitly requires
`garrison-hq/muster-action@v1`, and the whole M1 seam-proof purpose (spec
Overview, user story 2) is exercising the shipped Action, not bypassing it.

---

## 6. Manifest completeness check (FR-007 — added post-spec-gate by operator decision)

**Decision**: a dependency-free Node script,
`conformance/scripts/check-manifest-completeness.mjs`, run as a CI step
after the muster `skills run` step (and available for local pre-PR use). It:

1. Reads `src/doctrine/skills/` and lists directory basenames (the actual
   skill set). Filter directory entries by type:
   `fs.readdirSync(dir, {withFileTypes:true}).filter(e=>e.isDirectory())` —
   mirroring `src/specify_cli/skills/registry.py`'s `discover_skills()` —
   never by excluding known filenames such as `README.md`, which would
   silently regress if a second non-skill file is later added.
2. Reads `conformance/skills/manifest.yaml` as plain text and extracts, per
   case, the `id:` and `skillDir:` values using the manifest-authoring
   invariant this mission itself establishes (every case is a `- id: ...`
   line at a fixed list indent, with a sibling `skillDir:` line) — documented
   in `contracts/skills-manifest-case.schema.json` and enforced by
   authoring discipline, not by a YAML parser dependency.
3. Filters manifest cases whose `skillDir` resolves under
   `src/doctrine/skills/` (i.e., excludes the one FR-005 control case, whose
   `skillDir` points at `conformance/skills/control/...`) and compares that
   filtered set's basenames against the actual directory list.
4. Asserts `(total manifest case count) == (actual skill directory count) + 1`
   **and** that the two basename sets are identical; on either failure, prints
   the specific missing and/or extra skill names and exits `1`. On success,
   prints a one-line confirmation and exits `0`.

**Rationale — language choice**: Node, not Python, even though spec-kitty's
own runtime is Python. This CI job already has a hard Node/npx dependency
for the muster step itself (FR-002); adding a second-language toolchain
(Python + PyYAML) purely for a count check would need its own `setup-python`
/ dependency-install step, adding CI surface for zero benefit. Node's stdlib
(`fs`, `path`) is sufficient — **no new npm package** is introduced, so this
does not create a project dependency of any kind (spec-kitty's own
`pyproject.toml` is untouched, and there is no `package.json` dependency
either — the script runs via bare `node <script>.mjs`, using only builtins).

**Rationale — line-based parsing over a real YAML parser**: `conformance/`
is spec-kitty-side data that this same mission authors in full, so the
manifest's exact layout is a controlled invariant, not an unknown external
input. A regex/line-based extraction keyed to a documented authoring
convention is sufficient, avoids a `js-yaml` (or similar) npm dependency, and
mirrors muster's own pragmatism (muster itself parses the manifest with a
bare cast and no schema validation — FR-006's first known gap). The
convention this check relies on is written down in the `"$comment"` clause
of `contracts/skills-manifest-case.schema.json` (the schema's structural
fields alone say nothing about line order, key order, or indentation) so a
future manifest edit that violates it fails loudly in the completeness check
itself (a malformed or reformatted manifest either miscounts, which fails
obviously, or the script's own unit-level smoke test in `quickstart.md` step
3 catches it before merge).

**Alternatives considered**:
- A Python script using `pyyaml` (already a spec-kitty runtime dependency) —
  rejected on the "second toolchain for one job" ground above; also would
  blur the C-001 boundary by pulling `conformance/`'s logic into the same
  dependency graph as spec-kitty's own runtime, which the mission's Overview
  says stays untouched.
- Extending `conformance/skills/manifest.yaml` itself with a self-describing
  `expectedSkillCount` field the script merely reads — rejected; that just
  relocates the drift vector (the field itself could go stale) rather than
  computing ground truth from the actual `src/doctrine/skills/` tree, which
  is what FR-007 requires.
- A `bash` one-liner (`grep -c` + `find` + `diff`) — considered and close;
  rejected only because naming the *specific* missing/extra skills cleanly
  (FR-007's explicit requirement) is materially easier to read and maintain
  as a ~40-line Node script than as chained shell pipelines, for a script two
  future missions (M3, M6, M7) may need to extend.

**Lane/write-scope resolution**: FR-007 spans two files that must not
collide across the issue's two lanes — resolved by keeping the check's
*logic* entirely inside `conformance/scripts/check-manifest-completeness.mjs`
(added to lane-a's write scope, alongside the manifest it inspects) and
limiting lane-b's change to a single added step in
`.github/workflows/conformance.yml` that *invokes* the script by its stable
path and exit-code contract (`0` = complete, `1` = mismatch — matching
muster's own `0`/`1` pass/fail convention, deliberately not `2`, which muster
reserves for internal errors). No file is written by both lanes. See
`plan.md`'s Work-Package Outline for the corrected `write_scope` lists.

---

## 7. CI timing measurement (NFR-001)

**Decision**: no wall-clock ceiling is asserted in `conformance.yml` or
anywhere in this mission's requirements. `conformance/README.md` records the
actual `run_id` and wall-clock minutes from the first real GitHub Actions run
of the workflow, following the exact "measured, not asserted" pattern this
project already uses for CI budgets — see `docs/plans/testing/
ci-job-timings.md` (a committed E4 timings artifact citing a specific
`run_id` and per-job minutes, explicitly "budgets here are measured and
recorded, never asserted live") and the governing policy at
`docs/development/testing-flakiness.md`. This mission's README timing entry
is a first-class, mandatory implementation step (see plan.md's Verification
Strategy), not a documentation nice-to-have.

**Alternatives considered**: assert a fixed ceiling (e.g. "<2 minutes") at
spec time — explicitly rejected by the spec's own NFR-001 wording and by
project-wide precedent; a static-only muster run against 54 tiny YAML/
Markdown fixtures is expected to be fast, but "expected" is not "measured,"
and this project's own policy forbids asserting the former as if it were the
latter.
