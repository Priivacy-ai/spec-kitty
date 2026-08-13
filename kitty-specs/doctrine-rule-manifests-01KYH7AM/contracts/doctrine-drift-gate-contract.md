# Contract: `conformance/scripts/check-doctrine-drift-gate.sh` (FR-004/FR-005)

**Mission**: `doctrine-rule-manifests-01KYH7AM` | **Date**: 2026-07-27

CLI contract for the jq-based CI gate, so the workflow step (new job
`sop-doctrine-conformance`) and the script's implementation can be built
and reviewed independently. See research.md §9–10 for the design rationale.

## Invocation

```sh
bash conformance/scripts/check-doctrine-drift-gate.sh
```

- **Working directory**: repository root (same convention as M1's
  `check-manifest-completeness.mjs`).
- **Requires**: `jq` (pre-installed on `ubuntu-latest`) and network access to
  resolve `npx @garrison-hq/muster@1.1.0` (cache-warmed implicitly by the
  runner's normal npm registry access — no secret required, C-002).
- **Arguments**: none. Manifest paths are discovered by globbing
  `conformance/doctrine/*.yaml` (the 13 shipped manifests) and a single
  hardcoded path to the control manifest,
  `conformance/doctrine/control/045-drifted.yaml`.

## Behavior

**Phase 1 — FR-004, the main gate** (must find nothing, for every shipped manifest):

```sh
for manifest in conformance/doctrine/*.yaml; do
  set +e
  out=$(npx --yes @garrison-hq/muster@1.1.0 sop run "$manifest" --json)
  muster_exit=$?
  set -e
  # muster's own exit code: 0 = passed, 1 = lint error/probe failure, 2 = execution error
  # See "Failure handling" below: muster_exit and $out's JSON-ness are both
  # checked BEFORE the jq filter ever runs — jq is never the only gate.
  bad=$(printf '%s' "$out" | jq '[.lintFindings[] | select(.kind=="RULE_DRIFT" or .kind=="MISSING_SOURCE" or .kind=="MANIFEST_ERROR" or .kind=="STRUCTURAL_ABSENCE")]')
  count=$(printf '%s' "$bad" | jq 'length')
  # count MUST be 0 for every manifest
done
```

**Why `STRUCTURAL_ABSENCE` is in this filter — do not remove it.** It was
added post-plan (post-plan adversarial gate, binding operator decision) after
the gate reproduced it against the real built CLI: a missing `sopFile:`
target (a deleted or renamed directive file, or a typo'd path) produces
```json
{ "lintFindings": [{ "kind": "STRUCTURAL_ABSENCE", "severity": "error", ... }], "passed": false }
```
with real exit `1` (research.md §8, rows 2–3). Before this fix, the filter
selected only `RULE_DRIFT`/`MISSING_SOURCE`/`MANIFEST_ERROR`, so this exact
failure mode reported `count=0` — a false-clean gate pass — even though
muster's own `passed` field was already `false`. This is the third
recurrence of the absence-class defect in this programme (see M1's
retrospective and this mission's own "absence lesson," research.md §8); a
future edit that "simplifies" this filter back down to three kinds
reintroduces that exact defect. `STRUCTURAL_ABSENCE`'s presence here is
belt-and-suspenders with the exit-code capture in "Failure handling" below,
not a substitute for it: the exit-code check catches cases where muster
never emits JSON at all (exit `2`, see FIX 2 below), while this filter
entry catches cases where muster *does* emit valid JSON with `passed:
false` and the script must name the specific offending finding kind rather
than only report a bare "gate failed."

**Phase 2 — FR-005, the inverted control assertion** (must find at least one `RULE_DRIFT`):

```sh
set +e
out=$(npx --yes @garrison-hq/muster@1.1.0 sop run conformance/doctrine/control/045-drifted.yaml --json)
muster_exit=$?
set -e
# Same failure-handling rule as Phase 1 applies here (see below): $muster_exit
# and $out's JSON-ness are checked before the jq filter runs.
count=$(printf '%s' "$out" | jq '[.lintFindings[] | select(.kind=="RULE_DRIFT")] | length')
# count MUST be >= 1
```

The control's `ruleText` is `"Agents must never run \`git push origin main\`, \`git push --force\`, or \`gh pr"`
(one word changed from the real 045 directive's "must not run" →
"must never run"). Verified absent from the real file during planning:

```sh
$ grep -F -c "Agents must never run \`git push origin main\`, \`git push --force\`, or \`gh pr" \
    src/doctrine/directives/built-in/045-prs-only-and-read-intent.directive.yaml
0
```

This same `grep -F -c ... = 0` check should be re-run whenever the control's
`ruleText` is touched — a future edit that "softens" the mutation toward a
shorter, more generic string could silently start matching real content
again (count > 0), which would mean the control stops discriminating without
anyone noticing at review time by eye (the absence-lesson risk this mission
is explicitly instructed not to repeat).

## Failure handling — capturing muster's real exit code (hardened per post-plan gate)

**Corrected against the real built CLI.** The pseudocode above and
`research.md`'s absence table previously stated that a missing manifest
file produces `MANIFEST_ERROR` JSON and muster's own exit `1`, "no jq
needed." **This was wrong.** The gate ran it for real:

```
$ node dist/cli/index.js sop run conformance/doctrine/does-not-exist.yaml --json
muster: cannot read sop manifest "...": ENOENT: ...
REAL EXIT CODE: 2
```

`doSopRun` calls `readFileOrThrow(absManifestPath, "sop manifest")`
(`src/cli/index.ts:1436`) **before** it ever calls `runSopManifestSuite`.
`readFileOrThrow` throws an `ExecutionError` on `ENOENT`
(`src/cli/index.ts:150-156`), which is not caught by `doSopRun` itself and
propagates to `runCli`'s top-level catch (`src/cli/index.ts:1979-1982`),
which prints a plain `muster: cannot read sop manifest "...": ...` line to
**stderr** and returns exit **`2`** — **no JSON is ever produced** for this
case. The previously pseudocoded script never captured `$?` from the
`sop run` invocation and never checked whether `$out` was valid JSON before
piping it to `jq`; against this real case it would have fed an empty
string (only stdout is captured by `$(...)`; the ENOENT message went to
stderr) to `jq`, which is undefined/unspecified behavior for a gate script,
not a designed hard failure.

**The script MUST therefore, for every `sop run` invocation (Phase 1's loop
and Phase 2's control call)**:

1. Capture muster's real exit code (`muster_exit=$?`, with `set +e` around
   the invocation — shown inline in both phases above).
2. Before doing anything with `jq`, treat `muster_exit != 0` as an
   immediate, named hard gate failure for that manifest — independent of
   what `jq` would or wouldn't find — with a message distinguishing exit
   `1` ("muster ran, found a lint/probe failure") from exit `2` ("muster
   could not execute — see stderr above, e.g. an ENOENT on the manifest
   path or the resolved `sopFile` target").
3. Treat empty or non-JSON `$out` (e.g. `jq -e . >/dev/null 2>&1 <<<"$out"`
   failing) as its own named hard gate failure, even if `muster_exit`
   happened to be `0` — belt-and-suspenders against any future muster
   change that emits partial/malformed output on a code path this script
   doesn't yet know about.
4. Only run the `RULE_DRIFT`/`MISSING_SOURCE`/`MANIFEST_ERROR`/
   `STRUCTURAL_ABSENCE` `jq` filter (Phase 1) or the `RULE_DRIFT`-count
   filter (Phase 2) once steps 2–3 have both passed for that invocation.

**`jq` must never be the only thing standing between a broken run and a
green gate.** A script that skips steps 1–3 and only ever inspects `jq`'s
output would, on a real ENOENT (or any other exit-`2` case), either crash
opaquely on malformed `jq` input or — worse, if `jq` is invoked with a
lenient flag that swallows the parse error — silently report `count=0` and
pass. Both outcomes are exactly the "gate looks green, muster is actually
broken" failure this fix closes.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | All 13 shipped manifests are clean (zero `RULE_DRIFT`/`MISSING_SOURCE`/`MANIFEST_ERROR`/`STRUCTURAL_ABSENCE`, and muster itself exited `0` with valid JSON for every one) AND the control manifest produced at least one `RULE_DRIFT` (muster exit `0`, valid JSON). |
| `1` | At least one shipped manifest has a disallowed finding, OR muster itself exited non-zero or emitted non-JSON/empty output for any shipped manifest or the control ("Failure handling" above), OR the control manifest failed to discriminate (zero `RULE_DRIFT` findings) — the script names which manifest(s), which failure mode (disallowed finding / non-zero muster exit / unparseable output), and which finding(s) failed, never a bare count. |
| (never `2` from this script) | Reserved for "muster itself errored" (exit `2` from an underlying `sop run` invocation). This script's own exit code never reuses muster's `2` — a muster-side exit `2` (e.g. ENOENT on a manifest path) is one of the named hard-failure modes in "Failure handling" above and is reported as this script's own exit `1`, mirroring M1's `check-manifest-completeness-cli-contract.md`'s own non-goal note about not reusing muster's `2`. |

## Output shape

- **stdout, success**: one line per manifest confirming it is clean, then a
  confirmation line that the control discriminated, e.g.:
  ```
  checking: conformance/doctrine/001-architectural-integrity-standard.yaml — clean
  ...
  checking: conformance/doctrine/045-prs-only-and-read-intent.yaml — clean
  control OK: RULE_DRIFT present (1 finding) as expected
  ```
- **stdout/stderr, failure**: names the offending manifest and dumps the
  specific finding objects (not a bare count) via `jq .` on the filtered
  array, e.g.:
  ```
  GATE FAIL: conformance/doctrine/045-prs-only-and-read-intent.yaml — 1 disallowed finding(s):
  [ { "kind": "RULE_DRIFT", "location": "045-r1", ... } ]
  ```
  or, for a discriminated-control failure:
  ```
  GATE FAIL: control manifest did not produce a RULE_DRIFT finding — discrimination control is dead
  ```

## CI wiring

New job `sop-doctrine-conformance` in `.github/workflows/conformance.yml`
(research.md §9), step 2 of 3:

```yaml
# round-trip: skip: GitHub Actions workflow-step fragment showing how the drift gate is wired into conformance.yml — CI wiring, not a Pydantic payload; the executable coverage is the workflow file itself
- name: Run doctrine rule-manifest drift gate (FR-004/FR-005)
  run: bash conformance/scripts/check-doctrine-drift-gate.sh
```

## Non-goals

- Does not check `UNDEFINED_PRECEDENCE` or `TOOL_DRIFT` findings — both are
  reported-not-gating per FR-004, and `TOOL_DRIFT` is additionally
  unreachable via the CLI path at all (research.md §2) since `sop run`
  exposes no `--envTools` flag.
- Does not validate manifest YAML shape independently of what
  `loadAndValidateManifest` already validates — a `MANIFEST_ERROR` finding
  from a schema violation is caught by Phase 1's filter, not re-validated
  by this script.
- Does not independently validate that a manifest's `sopFile:` field
  resolves to an existing file —
  `contracts/doctrine-manifest-completeness-contract.md`'s script pairs
  directives to manifests by filename-stem convention only and never reads
  `sopFile:`. This script's Phase 1 `STRUCTURAL_ABSENCE` filter entry
  (above) is the **sole** guard against a deleted directive file or a
  typo'd `sopFile:` path — do not assume the completeness script covers
  this case too.
- Does not check rule *count* completeness (a manifest missing an entire
  rule entry produces no finding at all — see
  `contracts/doctrine-manifest-completeness-contract.md` for that guard).

---

## Amendment A1 — behavioral rules on the credential-free static path (mission `doctrine-behavioral-suite-01KYW5XK`, FR-005, 2026-08-02)

M4's FR-005 appends behavioral (judge-graded, inline-probe) rules to
`010`, `039` and `044` — same manifests, same `sopFile:`, same existing
rule IDs. That makes Phase 1's "must be clean" structurally unreachable for
those three, for two independent reasons, both reproduced against the real
pinned CLI before the gate was changed:

1. **No endpoint, no probe.** With `MUSTER_ENDPOINT` unset the CLI falls
   back to `SOP_NOOP_CLIENT`, whose `chat()` throws. Every run is recorded
   as errored, the verdict is `passed: false`, and muster exits 1. muster's
   own `sop run --help` says probes are "skipped gracefully when absent"
   and its source comment says errored verdicts "won't affect `passed`" —
   neither describes the shipped behaviour at 1.1.0 or 1.2.2.
2. **A behavioral rule's `ruleText` is authored, not quoted.**
   `checkRuleTextPresence()` requires every rule entry's `ruleText` to
   appear verbatim in the SOP file, regardless of grading class, so each
   behavioral rule emits one permanent `RULE_DRIFT` (severity `warning`).
   This one is **not** a credentials artifact: a live credentialed run of
   `010` at 1.2.2 exits 0 with `passed: true` and still carries the
   `RULE_DRIFT` finding, which Phase 1's jq filter would still reject.

**Amended Phase 1.** A finding or a failing verdict is set aside only when
it belongs to a behavioral rule, bounded four ways:

| Clause | Rule | Why |
|---|---|---|
| (a) | A rule is behavioral **iff muster's own report contains a probe verdict for it** (`.verdicts[].ruleId`). | Derived from the report under test, not a second manifest parse and not a name pattern. All 45 of M3's rules have `probeIds: []`, produce no verdict, and are never set aside. |
| (b) | The discriminator is never `gradingClass`. | 22 of M3's 45 quoted rules are judge-graded with no probes; filtering on grading class would stop drift-checking half the corpus, including `044`'s fragment `ruleText`s. |
| (c) | Only `RULE_DRIFT` is ever excused. `MISSING_SOURCE`, `MANIFEST_ERROR` and `STRUCTURAL_ABSENCE` still fail on every rule, behavioral ones included. | "`ruleText` is authored, not quoted" excuses verbatim-presence and nothing else. A malformed or unsourced behavioral rule is a real defect. |
| (d) | A failing verdict is excused only when **every** run errored with muster's no-endpoint marker, and a non-zero muster exit still fails unless at least one excused verdict accounts for it. | A behavioral probe that actually executes and fails still fails this gate; exit 1 with nothing to explain it is a named failure. If muster rewords the marker the match stops holding and the gate fails closed, never green. |

The complementary hole — a quoted directive rule buying a drift-lint
exemption by gaining a probe — is closed by
`contracts/doctrine-manifest-completeness-contract.md`'s Amendment A1, not
by this gate. The two are an interlock.

**Pin unchanged at `@garrison-hq/muster@1.1.0`.** This gate is
credential-free, so muster's live pass-k/k-of-n judge-threshold defect
(garrison-hq/muster#88, fixed in 1.2.2) cannot reach CI — no probe ever
executes here. It does reach a developer who runs the script locally with
`MUSTER_ENDPOINT` set: at 1.1.0 a verdict whose individual judge grades all
pass is still reported `passed: false` (reproduced against `gpt-4o-mini`:
5/5 runs graded PASS, verdict `passCount: 0`), and clause (d) correctly
refuses to excuse that.
