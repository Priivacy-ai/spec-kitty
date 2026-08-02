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

set -uo pipefail

MUSTER_PKG="@garrison-hq/muster@1.1.0"
CONTROL_MANIFEST="conformance/doctrine/control/045-drifted.yaml"
DISALLOWED_KINDS='.kind=="RULE_DRIFT" or .kind=="MISSING_SOURCE" or .kind=="MANIFEST_ERROR" or .kind=="STRUCTURAL_ABSENCE"'

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

echo "=== Phase 1: shipped manifests must be clean (FR-004) ==="

for manifest in conformance/doctrine/*.yaml; do
  manifest_count=$((manifest_count + 1))
  run_muster "$manifest"

  if [ "$RUN_EXIT" -ne 0 ]; then
    if [ "$RUN_EXIT" -eq 2 ]; then
      echo "GATE FAIL: $manifest -- muster exited 2 (could not execute; ENOENT on the manifest path or its sopFile target). stderr:"
    else
      echo "GATE FAIL: $manifest -- muster exited $RUN_EXIT (ran, found a lint/probe failure). stderr:"
    fi
    cat /tmp/doctrine-drift-gate-stderr.$$ >&2
    rm -f /tmp/doctrine-drift-gate-stderr.$$
    fail=1
    continue
  fi
  rm -f /tmp/doctrine-drift-gate-stderr.$$

  if [ "$RUN_VALID" -ne 1 ]; then
    echo "GATE FAIL: $manifest -- muster exited 0 but produced empty or non-JSON output (unparseable)."
    fail=1
    continue
  fi

  bad=$(printf '%s' "$RUN_OUT" | jq "[.lintFindings[] | select($DISALLOWED_KINDS)]")
  count=$(printf '%s' "$bad" | jq 'length')

  if [ "$count" -ne 0 ]; then
    echo "GATE FAIL: $manifest -- $count disallowed finding(s):"
    printf '%s' "$bad" | jq .
    fail=1
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
