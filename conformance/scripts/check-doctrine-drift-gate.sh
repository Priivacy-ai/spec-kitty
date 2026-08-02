#!/usr/bin/env bash
#
# check-doctrine-drift-gate.sh (FR-004/FR-005)
#
# Contract: kitty-specs/doctrine-rule-manifests-01KYH7AM/contracts/doctrine-drift-gate-contract.md
#
# Invocation: bash conformance/scripts/check-doctrine-drift-gate.sh
#   (no arguments, run from the repository root)
#
# Phase 1 (FR-004): every shipped manifest under conformance/doctrine/*.yaml
#   must be clean -- muster must exit 0 with valid JSON and zero findings of
#   kind RULE_DRIFT, MISSING_SOURCE, MANIFEST_ERROR, or STRUCTURAL_ABSENCE.
#
# Phase 2 (FR-005): the control manifest, conformance/doctrine/control/
#   045-drifted.yaml, is EXCLUDED from Phase 1 (its deliberately drifted
#   ruleText is not matched by the conformance/doctrine/*.yaml glob) and is
#   instead asserted, inverted-polarity, to PRODUCE at least one RULE_DRIFT
#   finding -- proof the drift detector itself actually fires.
#
# Why STRUCTURAL_ABSENCE is in the Phase 1 filter -- DO NOT REMOVE IT.
# It was added post-plan (binding operator decision) after this gate was
# reproduced against the real built muster CLI: a missing/renamed/typo'd
# `sopFile:` target produces
#   { "lintFindings": [{ "kind": "STRUCTURAL_ABSENCE", "severity": "error" }],
#     "passed": false }
# with real exit 1. Before this fix, the filter selected only
# RULE_DRIFT/MISSING_SOURCE/MANIFEST_ERROR, so this exact failure mode
# reported count=0 -- a false-clean gate pass -- even though muster's own
# `passed` field was already false. This is the third recurrence of the
# absence-class defect in this programme; a future edit that "simplifies"
# this filter back to three kinds reintroduces that exact defect.
#
# Exit-code / JSON-validity discipline (mandatory, not optional pseudocode):
# for EVERY `sop run` invocation below (Phase 1's loop and Phase 2's single
# call), this script:
#   1. Captures muster's real exit code via command substitution + `set +e`
#      (never a bare `$?` after a pipe -- `cmd | tee f; echo $?` reports
#      tee's exit status, not muster's, and would always read 0).
#   2. Treats a non-zero muster exit as an immediate, named hard failure --
#      independent of what jq would or wouldn't find -- distinguishing exit 1
#      ("muster ran, found a lint/probe failure") from exit 2 ("muster could
#      not execute -- e.g. an ENOENT on the manifest path or the resolved
#      sopFile target; ANOTHER mission's task file reproduced a MISSING
#      manifest exiting 2 with a plain stderr line and NO JSON on stdout").
#   3. Treats empty/non-JSON stdout as its own named hard failure, even if
#      muster's exit code happened to be 0.
#   4. Only runs the jq finding-kind filter once steps 2-3 have both passed.
# jq is never the only thing standing between a broken run and a green gate.
#
# Exit codes for THIS script: 0 = fully clean + control discriminates;
# 1 = any named failure (disallowed finding, non-zero muster exit, invalid
# JSON, or a non-discriminating control); this script's own exit code never
# reuses muster's 2 -- a muster-side exit 2 is reported as this script's 1.
#
# ---------------------------------------------------------------------------
# BEHAVIORAL RULES ON THE CREDENTIAL-FREE STATIC PATH
# (amendment: mission doctrine-behavioral-suite-01KYW5XK, FR-005)
# ---------------------------------------------------------------------------
# FR-005 appends behavioral (judge-graded, inline-probe) rules to three of the
# manifests this gate checks -- same sopFile, same rule IDs, not a new
# manifest. That makes "the manifest must be clean" structurally unreachable
# for those three under a credential-free gate, for two independent reasons,
# BOTH reproduced against the real pinned CLI before this code was written:
#
#   1. No endpoint -> no probe can run. With MUSTER_ENDPOINT unset, muster
#      falls back to SOP_NOOP_CLIENT, whose chat() throws. Every probe run is
#      recorded as errored, the verdict is `passed: false`, the report's
#      `passed` is false, and muster exits 1. (muster's own CLI help says
#      probes are "skipped gracefully when absent" and its source comment says
#      errored verdicts "won't affect `passed`" -- neither is true of the
#      shipped behaviour at 1.1.0 or 1.2.2. Do not trust those statements;
#      trust the reproduction.) This gate is credential-free by design
#      (C-002), so this is permanent, not transient.
#   2. A behavioral rule's ruleText is an authored assertion, not a quotation.
#      muster's checkRuleTextPresence() requires every manifest rule's
#      ruleText to appear verbatim in the SOP file and emits RULE_DRIFT
#      (severity warning) when it does not. It applies to every rule entry
#      regardless of grading class, so each behavioral rule produces one
#      permanent RULE_DRIFT the jq filter below would treat as disallowed.
#      This one is NOT a credentials artifact: a live credentialed run of 010
#      at 1.2.2 exits 0 with `passed: true` and STILL carries the RULE_DRIFT
#      finding, which the unamended filter would still have rejected.
#
# So Phase 1 scopes "clean" to the rules the drift lint can actually speak
# about: a finding or a failing verdict is set aside ONLY when it belongs to a
# behavioral rule. Everything else keeps failing exactly as before. The
# narrowing is deliberately small and is bounded four ways:
#
#   a. WHAT COUNTS AS BEHAVIORAL is taken from muster's own report, not from a
#      second parse of the manifest and not from a name pattern: a rule is
#      behavioral iff this report contains a probe verdict for it
#      (`.verdicts[].ruleId`). A rule with `probeIds: []` -- all 45 of M3's --
#      never produces a verdict and is therefore never set aside.
#   b. NOT gradingClass, and NOT every finding kind. `gradingClass: judge` is
#      the WRONG discriminator and must not be substituted here: 22 of M3's
#      45 quoted rules are judge-graded with no probes (all 3 of 001's, all
#      11 of 039's, 3 of 044's, one each in 030/033/034/035/045), so filtering
#      on grading class would silently stop drift-checking half the corpus,
#      including 044's hand-picked fragment ruleTexts. And only RULE_DRIFT is
#      ever set aside: MISSING_SOURCE, MANIFEST_ERROR and STRUCTURAL_ABSENCE
#      still fail on behavioral rules too -- "ruleText is authored, not
#      quoted" excuses verbatim-presence and nothing else.
#   c. A FAILING VERDICT IS EXCUSED ONLY WHEN NOTHING RAN. Every run in it
#      must carry an error containing "no-op client" -- i.e. the failure is
#      the absence of credentials and nothing else. A behavioral probe that
#      actually executes and fails still fails this gate. If muster ever
#      changes that message the match stops holding and the gate fails
#      closed (loud), never green.
#   d. A NON-ZERO MUSTER EXIT STILL FAILS unless at least one excused verdict
#      exists to account for it. Exit 1 with nothing to explain it is a named
#      failure, so this can never become "ignore muster's exit code".
#
# The matching hole -- a quoted directive rule buying a drift-lint exemption
# by gaining a probe -- is closed by the OTHER gate, not by this one:
# check-doctrine-manifest-completeness.mjs counts only rules with
# `probeIds: []` against the directive's integrity_rules, so attaching a probe
# to one of M3's rules drops that manifest's count and fails completeness.
# The two gates are an interlock; do not weaken either half alone.

set -uo pipefail

# Pin unchanged at 1.1.0: this gate is credential-free, so muster's live
# pass-k/k-of-n judge-threshold defect (garrison-hq/muster#88, fixed in 1.2.2)
# cannot reach it -- no probe ever executes here. It DOES reach anyone who runs
# this script locally with MUSTER_ENDPOINT set: at 1.1.0 a behavioral verdict
# whose individual judge grades all pass is still reported `passed: false`
# (reproduced against gpt-4o-mini: 5/5 runs graded PASS, verdict passCount 0),
# and this gate correctly refuses to excuse that. Export credentials only with
# a >=1.2.2 pin, or not at all. The live cadence workflow already pins 1.2.2.
MUSTER_PKG="@garrison-hq/muster@1.1.0"
CONTROL_MANIFEST="conformance/doctrine/control/045-drifted.yaml"
DISALLOWED_KINDS='.kind=="RULE_DRIFT" or .kind=="MISSING_SOURCE" or .kind=="MANIFEST_ERROR" or .kind=="STRUCTURAL_ABSENCE"'
# Substring of muster's no-endpoint error. Matched, never assumed: see (c).
NOOP_CLIENT_MARKER="no-op client"

fail=0
manifest_count=0

# Run `muster sop run <manifest> --json`, returning via globals:
#   RUN_EXIT   -- muster's real exit code
#   RUN_OUT    -- muster's stdout (may be empty)
#   RUN_VALID  -- "1" if RUN_OUT parsed as JSON, else "0"
run_muster() {
  local manifest="$1"
  set +e
  RUN_OUT=$(npx --yes "$MUSTER_PKG" sop run "$manifest" --json 2>/tmp/doctrine-drift-gate-stderr.$$)
  RUN_EXIT=$?
  set -e
  if [ -n "$RUN_OUT" ] && printf '%s' "$RUN_OUT" | jq -e . >/dev/null 2>&1; then
    RUN_VALID=1
  else
    RUN_VALID=0
  fi
}

# Partition one muster report into what this gate must still fail on and what
# the credential-free static path structurally cannot reach. Emits one JSON
# object on stdout:
#   badFindings         -- disallowed lint findings this gate must still fail
#                          on (the full objects, for the log). Only ONE kind is
#                          ever set aside -- a RULE_DRIFT whose location is a
#                          behavioral rule -- because "ruleText is authored,
#                          not quoted" excuses verbatim-presence and nothing
#                          else. MISSING_SOURCE, MANIFEST_ERROR and
#                          STRUCTURAL_ABSENCE keep failing on every rule,
#                          behavioral ones included: a malformed or
#                          unsourced behavioral rule is a real defect.
#   badCount            -- their number
#   excusedCount        -- failing verdicts explained solely by the absence of
#                          an endpoint (every run errored with the no-op
#                          client marker) on a rule that has a probe verdict
#   unexplainedVerdicts -- ruleIds of every other failing verdict
# See the "BEHAVIORAL RULES" block in the header for why each clause is here.
classify_report() {
  printf '%s' "$1" | jq --arg marker "$NOOP_CLIENT_MARKER" '
    ([.verdicts[]?.ruleId] | unique) as $behavioral
    | [.lintFindings[]?
        | select('"$DISALLOWED_KINDS"')
        | select(.kind != "RULE_DRIFT"
                 or (.location as $l | $behavioral | index($l)) == null)] as $badFindings
    | [.verdicts[]? | select(.passed == false)] as $failed
    | [$failed[]
        | select((.ruleId as $r | $behavioral | index($r)) != null)
        | select(((.runs // []) | length) > 0)
        | select((.runs // []) | all(((.error // "") | contains($marker))))
        | (.probeId // .ruleId)] as $excusedIds
    | {
        badFindings: $badFindings,
        badCount: ($badFindings | length),
        excusedCount: ($excusedIds | length),
        unexplainedVerdicts: [$failed[]
          | select(((.probeId // .ruleId) as $p | $excusedIds | index($p)) == null)
          | (.ruleId // "<unnamed>")]
      }'
}

echo "=== Phase 1: shipped manifests must be clean (FR-004) ==="

for manifest in conformance/doctrine/*.yaml; do
  manifest_count=$((manifest_count + 1))
  run_muster "$manifest"

  if [ "$RUN_EXIT" -eq 2 ]; then
    echo "GATE FAIL: $manifest -- muster exited 2 (could not execute; ENOENT on the manifest path or its sopFile target). stderr:"
    cat /tmp/doctrine-drift-gate-stderr.$$ >&2
    rm -f /tmp/doctrine-drift-gate-stderr.$$
    fail=1
    continue
  fi
  stderr_text=$(cat /tmp/doctrine-drift-gate-stderr.$$ 2>/dev/null || true)
  rm -f /tmp/doctrine-drift-gate-stderr.$$

  if [ "$RUN_VALID" -ne 1 ]; then
    echo "GATE FAIL: $manifest -- muster exited $RUN_EXIT and produced empty or non-JSON output (unparseable). stderr:"
    printf '%s\n' "$stderr_text" >&2
    fail=1
    continue
  fi

  report=$(classify_report "$RUN_OUT" 2>/dev/null || true)
  # jq is never the only thing standing between a broken run and a green gate:
  # if the partition itself did not produce a usable object, that is its own
  # named failure, not a silent zero.
  if ! printf '%s' "$report" | jq -e 'has("badCount") and has("excusedCount")' >/dev/null 2>&1; then
    echo "GATE FAIL: $manifest -- could not partition muster's report (classify_report produced no usable object)."
    fail=1
    continue
  fi

  count=$(printf '%s' "$report" | jq '.badCount')
  excused=$(printf '%s' "$report" | jq '.excusedCount')
  unexplained=$(printf '%s' "$report" | jq '.unexplainedVerdicts | length')

  if [ "$count" -ne 0 ]; then
    echo "GATE FAIL: $manifest -- $count disallowed finding(s):"
    printf '%s' "$report" | jq '.badFindings'
    fail=1
    continue
  fi

  if [ "$unexplained" -ne 0 ]; then
    echo "GATE FAIL: $manifest -- $unexplained failing verdict(s) not attributable to the absent endpoint:"
    printf '%s' "$report" | jq -r '.unexplainedVerdicts[] | "  - " + .'
    fail=1
    continue
  fi

  # Clause (d): a non-zero exit must be accounted for by an excused verdict.
  if [ "$RUN_EXIT" -ne 0 ] && [ "$excused" -eq 0 ]; then
    echo "GATE FAIL: $manifest -- muster exited $RUN_EXIT but the report shows no disallowed finding and no failing verdict to explain it. stderr:"
    printf '%s\n' "$stderr_text" >&2
    fail=1
    continue
  fi

  if [ "$excused" -ne 0 ]; then
    echo "checking: $manifest — static rules clean ($excused behavioral verdict(s) unexecuted: no endpoint on the static path)"
  else
    echo "checking: $manifest — clean"
  fi
done

echo ""
echo "=== Phase 2: control manifest must discriminate (FR-005, inverted polarity) ==="

run_muster "$CONTROL_MANIFEST"

if [ "$RUN_EXIT" -ne 0 ]; then
  if [ "$RUN_EXIT" -eq 2 ]; then
    echo "GATE FAIL: $CONTROL_MANIFEST -- muster exited 2 (could not execute). stderr:"
  else
    echo "GATE FAIL: $CONTROL_MANIFEST -- muster exited $RUN_EXIT unexpectedly. stderr:"
  fi
  cat /tmp/doctrine-drift-gate-stderr.$$ >&2
  rm -f /tmp/doctrine-drift-gate-stderr.$$
  fail=1
elif [ "$RUN_VALID" -ne 1 ]; then
  rm -f /tmp/doctrine-drift-gate-stderr.$$
  echo "GATE FAIL: $CONTROL_MANIFEST -- muster exited 0 but produced empty or non-JSON output (unparseable)."
  fail=1
else
  rm -f /tmp/doctrine-drift-gate-stderr.$$
  drift_count=$(printf '%s' "$RUN_OUT" | jq '[.lintFindings[] | select(.kind=="RULE_DRIFT")] | length')
  if [ "$drift_count" -ge 1 ]; then
    echo "control OK: RULE_DRIFT present ($drift_count finding(s)) as expected"
  else
    echo "GATE FAIL: control manifest did not produce a RULE_DRIFT finding — discrimination control is dead"
    fail=1
  fi
fi

echo ""
echo "=== Summary: $manifest_count shipped manifest(s) checked, plus 1 control ==="

if [ "$fail" -ne 0 ]; then
  echo "doctrine drift gate: FAIL"
  exit 1
fi

echo "doctrine drift gate: OK"
exit 0
