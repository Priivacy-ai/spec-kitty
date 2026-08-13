# Contract: `conformance/scripts/check-manifest-completeness.mjs` (FR-007)

**Mission**: `sk-skills-static-conformance-01KYG7GE` | **Date**: 2026-07-27

This is a CLI contract for a script this mission authors, not a muster
contract — it exists so the CI step in `.github/workflows/conformance.yml`
(lane-b) and the script's implementation (lane-a) can be built independently
without either lane reading the other's source, resolving the lane
straddle flagged when FR-007 was added (research.md §6).

---

## Invocation

```sh
node conformance/scripts/check-manifest-completeness.mjs
```

- **Working directory**: repository root. GitHub Actions' default
  `working-directory` after `actions/checkout` already satisfies this; local
  developers run it from the repo root per `conformance/README.md`.
- **Arguments**: none. All paths (`src/doctrine/skills/`,
  `conformance/skills/manifest.yaml`) are hardcoded relative to the current
  working directory — deliberately, since this script has exactly one job in
  exactly one repository layout, and an argument surface would be unused
  generality.
- **Environment variables**: none required. No network access, no
  credentials (matches C-002's offline-and-secret-free posture even though
  C-002 is written about the muster step specifically).
- **Directory scan**: `src/doctrine/skills/` entries are filtered by type —
  `fs.readdirSync(dir, {withFileTypes:true}).filter(e=>e.isDirectory())` —
  mirroring `src/specify_cli/skills/registry.py`'s `discover_skills()` —
  never by excluding known filenames such as `README.md`, which would
  silently regress if a second non-skill file is later added.

## Output

- **stdout, success** (exit `0`): a single confirmation line stating the
  matched count, e.g. `manifest completeness: OK (53 skills + 1 control = 54 cases)`.
- **stdout or stderr, failure** (exit `1`): a message that names every
  offending skill explicitly, in this shape (exact wording is an
  implementation choice; the *content* obligation below is the contract):
  ```
  manifest completeness: MISMATCH
    missing from manifest (present under src/doctrine/skills/, no case found): <name>[, <name>...]
    extra in manifest (case present, no matching src/doctrine/skills/<name> directory): <name>[, <name>...]
  ```
  If the mismatch is a pure count divergence with no name-level difference
  detectable (should not occur given the algorithm in research.md §6, but
  guarded defensively), the message still states the expected vs. actual
  counts rather than only "count" with no further detail.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Manifest is complete: static-case count == skill directory count + 1, and the two name sets match exactly. |
| `1` | Manifest is incomplete or over-complete: names the specific missing/extra skill(s). |
| (never `2`) | Reserved by muster's own CLI convention for internal/tooling errors (`src/cli/index.ts` exit-code contract, per `briefings/muster-github-action.md` §1) — this script deliberately does not reuse `2` for its own failures, so a `2` in this job's logs always means "muster itself errored," never "the completeness check found a problem." A genuine script bug (e.g. `src/doctrine/skills/` missing entirely) should still surface as a non-zero exit, but the script SHOULD attempt to distinguish "structural error reading the tree/manifest" from "counted mismatch" in its message text even where both currently exit `1`. |

## CI wiring (the lane-b side of this contract)

`.github/workflows/conformance.yml` adds exactly one step:

```yaml
# round-trip: skip: GitHub Actions workflow-step fragment showing the single step conformance.yml adds — CI wiring, not a Pydantic payload; the executable coverage is the workflow file itself
- name: Verify manifest completeness (FR-007)
  run: node conformance/scripts/check-manifest-completeness.mjs
```

placed after the `garrison-hq/muster-action@v1` step. Lane-b's WP (workflow
authoring) needs nothing about the script's internals beyond this file:
invocation, working directory, and exit-code meaning. Lane-a's WP (script
authoring) needs nothing about the workflow beyond the same three facts, in
reverse. Neither lane's `write_scope` includes a file the other lane writes
(see `plan.md`'s Work-Package Outline).

## Non-goals

- This script does not validate the manifest's YAML shape against
  `skills-manifest-case.schema.json` — that is a distinct, deferred concern
  (a real schema-validation step would be a muster-side fix per FR-006's
  scope guard, not this script's job).
- ~~This script does not inspect `expectations.ok`/`violations` values, skill
  frontmatter content, or anything muster's own `skills run` already
  checks~~ — **superseded by the addendum below.** As of the discrimination-
  control redesign, this script *does* inspect muster's own `--json`
  `violations[]` output for the control case and every real skill case; the
  claim above was accurate for the original FR-007-only implementation and
  is struck through, not deleted, so this contract's history stays legible.
  What remains true unchanged: this script does not validate manifest YAML
  shape against a schema, and does not re-implement any static rule muster
  itself already enforces (e.g. the `^[a-z0-9-]+$` charset check) — it only
  *observes* muster's own conclusion for the two properties described in the
  addendum.

## Addendum: discrimination-control redesign (post-merge, PR #29)

The original contract above described an FR-007-only script: pure Node
stdlib, no network, no process exec, checking manifest/tree *completeness*
only. Three rounds of property-based patching to that script's control-
discrimination logic (added post-merge, outside this contract's original
FR-007 scope) found seven distinct bypasses that left the script at exit
`0` against a control fixture that no longer discriminated anything (see
`conformance/README.md`'s "Proving the suite discriminates" §History for
the full list). The property-based approach was replaced, not patched
further:

- **Environment/network** (supersedes "Environment variables: none
  required. No network access" above): the script now execs
  `npx --offline @garrison-hq/muster@1.1.0 skills run <manifest> --json`
  as a child process. This requires no *credentials* (still true — no
  C-002 regression) but does require the pinned muster package to already
  be warm in the local npm cache; see `conformance/README.md`'s "Local
  prerequisite" note. If the CLI cannot be run, the script exits `1` with
  an actionable message (the cache-warm command to run) rather than
  propagating a raw `child_process` stack trace.
- **New behavior**: the script asserts (a) the control case's muster
  `--json` `violations[]` contains `{ path: "name", message: /must equal
  the parent directory name/ }`, and (b) every real skill case's
  `violations[]` contains zero `severity === "error"` entries. Both are
  read from a single muster invocation per script run, keyed by case `id`.
- **Exit codes**: unchanged in meaning (`0` = fully conforming, `1` =
  problem found, named explicitly) but the set of conditions that can
  produce `1` now also includes "muster CLI unavailable" and "control/skill
  case's observed violations don't match the expected shape," in addition
  to the original count/name-set mismatch conditions.
- **CI wiring**: unchanged — `.github/workflows/conformance.yml` still adds
  exactly the one step named in "CI wiring" above, with no new step
  required, because the preceding `garrison-hq/muster-action@v1` step
  already warms the same npm cache this script's own `npx --offline` call
  reads from.
