#!/usr/bin/env bash
# check-runs-errored.test.sh -- committed test for check-runs-errored.sh
# (T010/FR-007).
#
# check-runs-errored.sh is this WP's only executable artifact and, before
# this file, had zero committed tests: its four verification cases plus the
# zero-errors-but-failing rejection fixture existed only in commit message
# fe95eaf15, with the fixtures themselves discarded after that commit.
# `tests/cross_cutting/test_check_sop_extract_drift.py` is the repo's own
# precedent for testing a sibling conformance script this way; `tests/` is
# outside this WP's owned_files, so this test lives under
# `conformance/behavioral/scripts/`, which is, alongside its `fixtures/`
# subdirectory holding the committed report fixtures each case runs against.
#
# Usage: bash conformance/behavioral/scripts/check-runs-errored.test.sh
# Exits 0 if every case passes, 1 on the first failing case.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUT="${SCRIPT_DIR}/check-runs-errored.sh"
FIXTURES="${SCRIPT_DIR}/fixtures"

failures=0

# assert_case <label> <fixture-file-or-none> <expected-exit> [<expected-stdout>]
assert_case() {
  local label="$1" fixture="$2" expected_exit="$3" expected_stdout="${4:-}"
  local actual_stdout actual_exit

  set +e
  if [ "${fixture}" = "__NO_ARG__" ]; then
    actual_stdout="$(bash "${SUT}" 2>/dev/null)"
  else
    actual_stdout="$(bash "${SUT}" "${FIXTURES}/${fixture}" 2>/dev/null)"
  fi
  actual_exit=$?
  set -e

  if [ "${actual_exit}" -ne "${expected_exit}" ]; then
    echo "FAIL: ${label} -- expected exit ${expected_exit}, got ${actual_exit} (stdout: '${actual_stdout}')"
    failures=$((failures + 1))
    return
  fi

  if [ -n "${expected_stdout}" ] && [ "${actual_stdout}" != "${expected_stdout}" ]; then
    echo "FAIL: ${label} -- expected stdout '${expected_stdout}', got '${actual_stdout}'"
    failures=$((failures + 1))
    return
  fi

  echo "PASS: ${label}"
}

# Case 1: healthy control run -- zero errored runs, genuinely reachable
# endpoint, controls fail as designed. Expect count 0, exit 0.
assert_case "healthy report -> 0 errored runs, exit 0" "healthy.json" 0 "0"

# Case 2: dead-endpoint run -- every run recorded an error. Expect count 3
# (matches this fixture's 3 error entries), exit 0.
assert_case "dead-endpoint report -> 3 errored runs, exit 0" "dead-endpoint.json" 0 "3"

# Case 3 (the rejection case): a genuinely non-compliant-but-reachable run
# (passed: false, passCount 1/3) with zero runs[].error at any level. Must
# report 0, not a nonzero count -- proving the script counts errors, not
# failures.
assert_case "zero-errors-but-failing report -> 0 (counts errors, not failures)" "zero-errors-but-failing.json" 0 "0"

# Case 4: missing report path argument -- usage error, exit 1.
assert_case "missing report path argument -> exit 1" "__NO_ARG__" 1

# Case 5 (F3, F9): zero-byte report -- fail closed, exit 3, never a silent 0.
assert_case "zero-byte report -> exit 3 (fail closed, F3)" "zero-byte.json" 3

# Case 6: malformed (non-JSON) report -- fail closed, exit 3.
assert_case "malformed report -> exit 3 (fail closed, F3)" "malformed.json" 3

# Case 7 (F9): valid JSON missing the expected verdicts[].runs[] shape --
# jq's own runtime-error exit code (5), propagated unchanged.
assert_case "missing verdicts key -> exit 5 (jq's own runtime error)" "missing-verdicts.json" 5

# Case 8: whitespace-only report -- the original `jq empty` guard treated
# zero JSON documents as vacuously valid (exit 0, empty stdout) on this
# exact shape, silently contradicting the header's own fail-closed contract.
# Must fail closed (exit 3), same as a true zero-byte file.
assert_case "whitespace-only report -> exit 3 (fail closed, not vacuously valid)" "whitespace-only.json" 3

# Case 9: two concatenated JSON documents -- `jq empty` also treated this as
# vacuously valid (exit 0, stdout "0\n0"), and the un-slurped final `jq`
# query would have printed one count per document rather than failing.
# Must fail closed (exit 3): a report is exactly one document or it is not
# trustworthy.
assert_case "concatenated JSON documents -> exit 3 (fail closed, not two valid reports)" "concatenated.json" 3

# Case 10: `jq` absent from PATH -- the one documented exit path (2) with no
# prior committed test case. Run with a PATH containing no `jq` binary.
set +e
actual_stdout="$(PATH=/nonexistent-bin "$(command -v bash)" "${SUT}" "${FIXTURES}/healthy.json" 2>/dev/null)"
actual_exit=$?
set -e
if [ "${actual_exit}" -ne 2 ]; then
  echo "FAIL: jq absent from PATH -> expected exit 2, got ${actual_exit} (stdout: '${actual_stdout}')"
  failures=$((failures + 1))
else
  echo "PASS: jq absent from PATH -> exit 2"
fi

if [ "${failures}" -gt 0 ]; then
  echo "check-runs-errored.test.sh: ${failures} case(s) failed"
  exit 1
fi

echo "check-runs-errored.test.sh: all cases passed"
