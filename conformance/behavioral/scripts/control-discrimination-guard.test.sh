#!/usr/bin/env bash
# control-discrimination-guard.test.sh -- committed test for the two guard
# regions inside .github/workflows/behavioral.yml: the control-verdict
# assertions in the `control-suite` job, and the muster-version pin assertion
# in both jobs' `Warm up muster npx cache` step.
#
# Why extraction rather than a copy: the assertions under test live inline in
# workflow `run:` blocks, and a test that re-declared the same jq expressions
# locally would pass forever while the committed workflow drifted away from
# them -- exactly the class of vacuous check this programme keeps finding.
# This file therefore reads each assertion's own bytes out of behavioral.yml
# (between stable marker comments), dedents them, and executes them against
# committed report fixtures. If the markers are missing, or the extracted
# region does not contain the assertion, this test fails rather than silently
# testing nothing.
#
# ---------------------------------------------------------------------------
# What the control-verdict region has to prove, and why it grew (F1)
# ---------------------------------------------------------------------------
# The original assertion closed one hole: the step used to print "both
# controls failed as designed" having only checked `muster_exit == 1` and
# `errored == 0`, so one control silently passing was accepted.
#
# It left a second, one-directional hole open. control-manifest.yaml's two
# original controls are both NEGATIVE, and asserting "both failed" reads as
# two independent confirmations. It is one:
#
#   * CONTROL-BEHAVIORAL-FORBIDDEN-ACTION (binary) can only fail if the model
#     actually emitted the codeword. A dead or degenerate endpoint cannot do
#     that. This carries all the discrimination.
#   * CONTROL-JUDGE-IMPOSSIBLE (judge) is a rubric no reply can satisfy. It
#     fails under a healthy judge, under a degenerate model, AND under a
#     judge stuck at FAIL. It is a constant-true conjunct.
#
# So a total judge outage was invisible, and every rule in all five profile
# manifests is gradingClass: judge -- a stuck judge turns the whole main
# suite red while the control suite certifies the endpoint healthy, inverting
# exactly the "endpoint failed vs model failed" disambiguation FR-007 exists
# for. The fix is CONTROL-JUDGE-TRIVIAL, a POSITIVE judge control whose
# rubric every real reply satisfies, asserted `passed == true`.
#
# ---------------------------------------------------------------------------
# Fixture provenance (no fabricated reports)
# ---------------------------------------------------------------------------
# Three fixtures are verbatim `muster sop run --json` output from real runs of
# the committed control-manifest.yaml against https://api.openai.com/v1 with
# gpt-4o-mini, captured 2026-08-02:
#
#   control-all-three-live.json     @garrison-hq/muster@1.2.2, healthy.
#                                   Both negatives 0/3 failed; the positive
#                                   control passed 3/3. THE accept case.
#   control-stuck-judge-live.json   the same manifest, same endpoint, same
#                                   moment, under @garrison-hq/muster@1.2.1 --
#                                   whose judge-threshold defect
#                                   (garrison-hq/muster#88, fixed by
#                                   db80a4295/#89) makes every
#                                   resolved-threshold->=2 judge rule
#                                   permanently unpassable, i.e. a judge stuck
#                                   at FAIL. On every field the pre-F1 guard
#                                   read it is IDENTICAL to the healthy report
#                                   above, and the pre-F1 guard chain returned
#                                   exit 0 "genuine discrimination confirmed"
#                                   against it. The positive control is the
#                                   only thing that separates them: 0/3 here
#                                   versus 3/3 there. THE rejection case F1
#                                   exists for; it is measured, not imagined.
#   control-dead-endpoint.json      the same manifest against
#                                   http://127.0.0.1:9/v1 -- all three
#                                   controls "failed", every run errored.
#
# control-positive-control-absent.json is the pre-F1 two-verdict real report
# (a byte-for-byte copy of the committed
# evidence/2026-08-02-01KYW5XK-control-healthy.json), kept because "the
# positive control was deleted from the manifest" is now itself a rejection
# case. The remaining fixtures are control-all-three-live.json with one field
# group flipped by jq, so every other field keeps real muster @1.2.2 output
# shape.
#
# Usage: bash conformance/behavioral/scripts/control-discrimination-guard.test.sh
# Exits 0 if every case passes, 1 on any failing case.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
WORKFLOW="${REPO_ROOT}/.github/workflows/behavioral.yml"
FIXTURES="${SCRIPT_DIR}/fixtures"
ERRORED_SCRIPT="${SCRIPT_DIR}/check-runs-errored.sh"

VERDICT_BEGIN="# >>> control-verdict assertions (extracted verbatim by control-discrimination-guard.test.sh)"
VERDICT_END="# <<< control-verdict assertions"
VERSION_BEGIN="# >>> muster-version pin assertion (extracted verbatim by control-discrimination-guard.test.sh)"
VERSION_END="# <<< muster-version pin assertion"
RESHAPE_BEGIN="# >>> control evidence reshape (extracted verbatim by control-discrimination-guard.test.sh)"
RESHAPE_END="# <<< control evidence reshape"

failures=0
work_dir="$(mktemp -d)"
trap 'rm -rf "${work_dir}"' EXIT

if [ ! -f "${WORKFLOW}" ]; then
  echo "FAIL: workflow not found at ${WORKFLOW}"
  exit 1
fi

fail() {
  echo "FAIL: $1"
  failures=$((failures + 1))
}

# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------
# extract_region <out-file> <begin> <end> <expected-region-count>
#
# The expected-count argument is not decoration. The muster-version assertion
# is duplicated across both jobs' warm-up steps, and two copies that drift
# apart would leave one job unguarded while this test kept passing against the
# other. So: extract every marked region, require exactly the expected number,
# AND require them byte-identical to one another. A dropped copy fails on the
# count, a diverged copy fails on the comparison.
extract_region() {
  local out="$1" begin="$2" end="$3" expected="$4"
  local regions_dir="${work_dir}/regions"
  rm -rf "${regions_dir}"
  mkdir -p "${regions_dir}"

  awk -v b="${begin}" -v e="${end}" -v dir="${regions_dir}" '
    index($0, b) { inside = 1; n += 1; next }
    index($0, e) { inside = 0; next }
    inside { sub(/^ {10}/, ""); print > (dir "/" n) }
  ' "${WORKFLOW}"

  local found
  found="$(find "${regions_dir}" -type f | wc -l)"
  if [ "${found}" -ne "${expected}" ]; then
    fail "extraction (${begin}) -- expected ${expected} marked region(s) in ${WORKFLOW}, found ${found}"
    return 1
  fi

  local i
  for ((i = 2; i <= expected; i++)); do
    if ! cmp -s "${regions_dir}/1" "${regions_dir}/${i}"; then
      fail "extraction (${begin}) -- copy ${i} of the marked region is not byte-identical to copy 1; the two jobs' guards have drifted apart"
      return 1
    fi
  done

  cp "${regions_dir}/1" "${out}"
  return 0
}

# assert_extraction_contains <label> <file> <needle>...
# An empty or assertion-free region would make every case below "pass"
# against a no-op script, so every substring the cases depend on is asserted
# present before any of them run.
assert_extraction_contains() {
  local label="$1" file="$2"
  shift 2
  local needle
  for needle in "$@"; do
    if ! grep -qF -- "${needle}" "${file}"; then
      fail "extraction (${label}) -- extracted region does not contain '${needle}'; the assertion was removed or renamed, and every case below would test nothing"
      return 1
    fi
  done
  if ! grep -q 'exit 1' "${file}"; then
    fail "extraction (${label}) -- extracted region never exits nonzero; it cannot reject anything"
    return 1
  fi
  echo "PASS: extraction (${label}) -- pulled $(wc -l < "${file}") line(s) of the committed assertion out of behavioral.yml"
  return 0
}

verdict_snippet="${work_dir}/verdict-assertions.sh"
version_snippet="${work_dir}/version-assertion.sh"
reshape_snippet="${work_dir}/evidence-reshape.sh"

extract_region "${verdict_snippet}" "${VERDICT_BEGIN}" "${VERDICT_END}" 1 || exit 1
assert_extraction_contains "control-verdict" "${verdict_snippet}" \
  'actual_rule_ids=' 'negative_failed=' 'positive_passed=' || exit 1

# Both jobs run the same live endpoint under the same pin; both must refuse a
# mismatched resolution.
extract_region "${version_snippet}" "${VERSION_BEGIN}" "${VERSION_END}" 2 || exit 1
assert_extraction_contains "muster-version" "${version_snippet}" \
  'expected_version=' || exit 1

extract_region "${reshape_snippet}" "${RESHAPE_BEGIN}" "${RESHAPE_END}" 1 || exit 1
# The reshape has no `exit 1` of its own -- it fails through jq's own nonzero
# exit under the step's `set -euo pipefail` -- so it gets a bespoke guard
# rather than assert_extraction_contains's blanket one.
for needle in 'one_verdict(' 'judgePositiveControl' 'error('; do
  if ! grep -qF -- "${needle}" "${reshape_snippet}"; then
    fail "extraction (evidence-reshape) -- extracted region does not contain '${needle}'; every reshape case below would test nothing"
    exit 1
  fi
done
echo "PASS: extraction (evidence-reshape) -- pulled $(wc -l < "${reshape_snippet}") line(s) of the committed reshape out of behavioral.yml"

# ---------------------------------------------------------------------------
# Harness for the control-verdict region
# ---------------------------------------------------------------------------
# Reproduces the step's own shell state: `set +e` with `-u -o pipefail`
# (behavioral.yml's control-suite step disables -e deliberately), a `report`
# variable, an `errored` count computed by the same script the workflow calls
# at that point, and a writable GITHUB_OUTPUT.
run_verdict_assertion() {
  local fixture="$1"
  local harness="${work_dir}/harness.sh"
  {
    echo 'set +e'
    echo 'set -u -o pipefail'
    printf 'report=%q\n' "${FIXTURES}/${fixture}"
    printf 'errored="$(%q "${report}")"\n' "${ERRORED_SCRIPT}"
    echo 'GITHUB_OUTPUT="${WORK_GITHUB_OUTPUT}"'
    cat "${verdict_snippet}"
    echo 'exit 0'
  } > "${harness}"
  WORK_GITHUB_OUTPUT="${work_dir}/github_output" bash "${harness}" 2>&1
}

assert_case() {
  local label="$1" fixture="$2" expected_exit="$3" expected_substring="${4:-}"
  local output actual_exit

  : > "${work_dir}/github_output"
  set +e
  output="$(run_verdict_assertion "${fixture}")"
  actual_exit=$?
  set -e

  if [ "${actual_exit}" -ne "${expected_exit}" ]; then
    fail "${label} -- expected exit ${expected_exit}, got ${actual_exit} (output: '${output}')"
    return
  fi

  if [ -n "${expected_substring}" ] && [[ "${output}" != *"${expected_substring}"* ]]; then
    fail "${label} -- expected output to contain '${expected_substring}', got '${output}'"
    return
  fi

  echo "PASS: ${label} (exit ${actual_exit})"
}

# assert_reports_report_file <label> <fixture>
# Every failing exit path in this step must write report_file to
# GITHUB_OUTPUT before exiting, or the evidence-writing step's
# `if: always() && steps.control_suite.outputs.report_file != ''` guard skips
# and the failing run leaves no evidence behind at all.
assert_reports_report_file() {
  local label="$1" fixture="$2"

  : > "${work_dir}/github_output"
  set +e
  run_verdict_assertion "${fixture}" >/dev/null
  set -e

  if ! grep -q "^report_file=${FIXTURES}/${fixture}\$" "${work_dir}/github_output"; then
    fail "${label} -- report_file was not written to GITHUB_OUTPUT (got: '$(cat "${work_dir}/github_output")')"
    return
  fi

  echo "PASS: ${label}"
}

# ---------------------------------------------------------------------------
# Control-verdict cases
# ---------------------------------------------------------------------------

# Case 1 (the healthy case): the real 1.2.2 control report -- both negative
# controls failed 0/3, the positive control passed 3/3. Must be accepted.
assert_case "real healthy 1.2.2 report (2 negatives failed, positive passed) -> accepted, exit 0" \
  "control-all-three-live.json" 0

# Case 2 (F1, THE case this whole change exists for): the real 1.2.1 report.
# A judge stuck at FAIL. Both negative controls still read exactly as they do
# in the healthy report, muster still exits 1, zero runs errored, no lint
# findings -- every pre-F1 guard accepts it. Only the positive control
# separates the two reports.
assert_case "real stuck-FAIL judge (muster@1.2.1) -> rejected, exit 1" \
  "control-stuck-judge-live.json" 1 "CONTROL-JUDGE-TRIVIAL"

assert_reports_report_file "stuck-FAIL judge -> report_file written to GITHUB_OUTPUT" \
  "control-stuck-judge-live.json"

# Case 3: exactly one negative control passed. muster still exits 1 and
# errored is still 0, so every guard outside this region accepts this report.
assert_case "a negative control passed -> rejected, exit 1" \
  "control-one-passed.json" 1 "got 1"

assert_reports_report_file "a negative control passed -> report_file written to GITHUB_OUTPUT" \
  "control-one-passed.json"

# Case 4: every control collapsed to a single run. A 1-run control cannot
# support pass^k discrimination; totalRuns >= 3 is the floor the region
# enforces on the negatives and on the positive alike.
assert_case "controls collapsed to 1 run each -> rejected, exit 1" \
  "control-single-run.json" 1 "got 0"

# Case 5 (F2): both negative controls report passed == false, but the judge
# control fired on 1 of its 3 runs. Its own ruleText says a healthy endpoint
# "must observe this rule failing EVERY run", and under the declared k-of-n
# threshold of 2 a 1/3 passCount still aggregates to passed == false -- so
# `passed == false` alone tolerated a control that was one spurious PASS away
# from being satisfiable. The live runs measure 0/3 and 0/3; this is slack in
# the assertion, not a current failure, and passCount is already in the
# report.
assert_case "negative control with a spurious 1/3 passCount -> rejected, exit 1" \
  "control-negative-spurious-pass.json" 1 "got 1"

# Case 6 (F3): a control renamed CONTROL-JUDGE-IMPOSSIBLE ->
# CTRL-JUDGE-IMPOSSIBLE. Before the ruleId-set assertion, this produced: guard
# exit 0 "genuine discrimination confirmed"; the evidence step's
# `startswith("CONTROL-JUDGE")` jq matching nothing and writing ZERO BYTES
# (a jq no-match is invisible to `set -euo pipefail`); the upload's
# `if-no-files-found: error` satisfied because the file exists; and death two
# steps later in merge-evidence as "not exactly one valid JSON document
# (got: 0)" -- a message pointing at file corruption rather than at a rename.
assert_case "a control ruleId renamed -> rejected here, at the origin, exit 1" \
  "control-renamed-ruleid.json" 1 "CTRL-JUDGE-IMPOSSIBLE"

assert_reports_report_file "renamed ruleId -> report_file written to GITHUB_OUTPUT" \
  "control-renamed-ruleid.json"

# Case 7 (F1 regression floor): the pre-F1 two-control report. Deleting the
# positive control from control-manifest.yaml must not silently restore the
# blind spot -- the ruleId-set assertion names it, so its absence is a
# failure rather than a smaller green suite.
assert_case "positive control absent from the manifest -> rejected, exit 1" \
  "control-positive-control-absent.json" 1 "CONTROL-JUDGE-TRIVIAL"

# Case 8: report has no `verdicts` key at all. jq errors; the region must
# reject on the resulting empty VALUE, not on jq's coincidental exit status.
assert_case "report missing verdicts key -> rejected, exit 1" \
  "control-no-verdicts-key.json" 1 "<none>"

assert_reports_report_file "missing verdicts key -> report_file written to GITHUB_OUTPUT" \
  "control-no-verdicts-key.json"

# Case 9: unreadable report path (file does not exist). Same fail-closed
# requirement -- jq's stderr is suppressed, so the empty value must drive it.
assert_case "nonexistent report path -> rejected, exit 1" \
  "control-does-not-exist.json" 1 "<none>"

# Case 10: a dead-endpoint report. Every run errored, so all three controls
# read as "failed" -- including the positive one. The region must reject with
# the DEAD-ENDPOINT diagnostic, not with "the positive control failed": a
# dead endpoint and a stuck judge are the two conditions FR-007 exists to keep
# apart, and reporting one as the other is the defect, not the guard. This is
# why the errored check sits at the top of the region rather than after the
# verdict assertions.
assert_case "dead-endpoint report -> rejected as a dead endpoint, not as a judge outage, exit 1" \
  "control-dead-endpoint.json" 1 "errored run(s)"

assert_reports_report_file "dead endpoint -> report_file written to GITHUB_OUTPUT" \
  "control-dead-endpoint.json"

# ---------------------------------------------------------------------------
# Harness and cases for the muster-version pin region (F4)
# ---------------------------------------------------------------------------
# `steps.muster_version.outputs.version` was captured and written into the
# evidence artifact but never compared to MUSTER_PIN. The workflow comment
# claimed the artifact "self-certifies" its muster version; self-certifying is
# not asserting. Nothing went red when the resolved version was 1.2.1 -- the
# stuck-FAIL judge of case 2 above.
run_version_assertion() {
  local pin="$1" resolved="$2"
  local harness="${work_dir}/version-harness.sh"
  {
    echo 'set -euo pipefail'
    printf 'MUSTER_PIN=%q\n' "${pin}"
    printf 'version=%q\n' "${resolved}"
    cat "${version_snippet}"
    echo 'exit 0'
  } > "${harness}"
  bash "${harness}" 2>&1
}

assert_version_case() {
  local label="$1" pin="$2" resolved="$3" expected_exit="$4" expected_substring="${5:-}"
  local output actual_exit

  set +e
  output="$(run_version_assertion "${pin}" "${resolved}")"
  actual_exit=$?
  set -e

  if [ "${actual_exit}" -ne "${expected_exit}" ]; then
    fail "${label} -- expected exit ${expected_exit}, got ${actual_exit} (output: '${output}')"
    return
  fi
  if [ -n "${expected_substring}" ] && [[ "${output}" != *"${expected_substring}"* ]]; then
    fail "${label} -- expected output to contain '${expected_substring}', got '${output}'"
    return
  fi
  echo "PASS: ${label} (exit ${actual_exit})"
}

assert_version_case "pin 1.2.2 resolves to 1.2.2 -> accepted, exit 0" \
  "@garrison-hq/muster@1.2.2" "1.2.2" 0

# The exact silent failure F4 is about.
assert_version_case "pin 1.2.2 resolves to 1.2.1 -> rejected, exit 1" \
  "@garrison-hq/muster@1.2.2" "1.2.1" 1 "1.2.1"

assert_version_case "npx printed nothing (resolution failed) -> rejected, exit 1" \
  "@garrison-hq/muster@1.2.2" "" 1

# A pin with no version is not a pin. `${MUSTER_PIN##*@}` on a scoped package
# name silently yields "garrison-hq/muster", which would then never equal any
# resolved version -- correct outcome, wrong and confusing reason. Name it.
assert_version_case "MUSTER_PIN carries no @version -> rejected as an unassertable pin, exit 1" \
  "@garrison-hq/muster" "1.2.2" 1 "pin"

assert_version_case "MUSTER_PIN is a range, not a pin -> rejected, exit 1" \
  "@garrison-hq/muster@^1.2.2" "1.2.2" 1 "pin"

# ---------------------------------------------------------------------------
# Harness and cases for the control-suite evidence reshape (F1/F3)
# ---------------------------------------------------------------------------
# This is the step that used to select controls by `startswith(...)` prefix.
# Its failure mode was the nastiest in the job: on a ruleId no-match jq emits
# NOTHING and exits 0, so `set -euo pipefail` sees a clean step, the redirect
# leaves a zero-byte file, `if-no-files-found: error` is satisfied because the
# file exists, and the run dies two steps later in merge-evidence complaining
# about JSON validity. It must now fail here, loudly, naming the ruleId.
run_reshape() {
  local fixture="$1"
  local harness="${work_dir}/reshape-harness.sh"
  {
    echo 'set -euo pipefail'
    printf 'REPORT_FILE=%q\n' "${FIXTURES}/${fixture}"
    printf 'evidence_file=%q\n' "${work_dir}/evidence-out.json"
    echo 'endpoint_host="api.openai.com"'
    echo 'MUSTER_MODEL="gpt-4o-mini"'
    echo 'MUSTER_VERSION="1.2.2"'
    cat "${reshape_snippet}"
  } > "${harness}"
  rm -f "${work_dir}/evidence-out.json"
  bash "${harness}" 2>&1
}

# assert_reshape_writes <label> <fixture> <jq-filter> <expected-compact-json>
assert_reshape_writes() {
  local label="$1" fixture="$2" filter="$3" expected="$4"
  local output actual_exit actual

  set +e
  output="$(run_reshape "${fixture}")"
  actual_exit=$?
  set -e

  if [ "${actual_exit}" -ne 0 ]; then
    fail "${label} -- expected exit 0, got ${actual_exit} (output: '${output}')"
    return
  fi
  actual="$(jq -c "${filter}" "${work_dir}/evidence-out.json" 2>&1)"
  if [ "${actual}" != "${expected}" ]; then
    fail "${label} -- expected ${expected}, got ${actual}"
    return
  fi
  echo "PASS: ${label}"
}

# assert_reshape_rejects <label> <fixture> <expected-substring>
# Also asserts the reshape did not leave a VALID-looking evidence file behind:
# the zero-byte-then-die-downstream shape is the defect, so a rejection must
# be a nonzero exit here, with nothing downstream could mistake for evidence.
assert_reshape_rejects() {
  local label="$1" fixture="$2" expected_substring="$3"
  local output actual_exit doc_count

  set +e
  output="$(run_reshape "${fixture}")"
  actual_exit=$?
  set -e

  if [ "${actual_exit}" -eq 0 ]; then
    fail "${label} -- expected a nonzero exit, got 0 (output: '${output}')"
    return
  fi
  if [[ "${output}" != *"${expected_substring}"* ]]; then
    fail "${label} -- expected output to contain '${expected_substring}', got '${output}'"
    return
  fi
  doc_count="$(jq -s 'length' "${work_dir}/evidence-out.json" 2>/dev/null || echo "invalid")"
  if [ "${doc_count}" = "1" ]; then
    fail "${label} -- exited ${actual_exit} but still wrote one valid JSON document; merge-evidence would consume it as if the run were sound"
    return
  fi
  echo "PASS: ${label} (exit ${actual_exit})"
}

assert_reshape_writes "reshape carries all three controls, keyed by exact ruleId" \
  "control-all-three-live.json" '.controlManifest | keys' \
  '["behavioralControl","judgeControl","judgePositiveControl"]'

assert_reshape_writes "positive control's live 3/3 pass recorded in the evidence" \
  "control-all-three-live.json" '.controlManifest.judgePositiveControl' \
  '{"passed":true,"passCount":3,"totalRuns":3,"runsErrored":0}'

# The evidence file is the only place a gate reviewer sees the stuck judge --
# recording it as a normal-looking run would put the blind spot straight back.
assert_reshape_writes "stuck-FAIL judge recorded as a FAILED positive control, not omitted" \
  "control-stuck-judge-live.json" '.controlManifest.judgePositiveControl' \
  '{"passed":false,"passCount":0,"totalRuns":3,"runsErrored":0}'

assert_reshape_rejects "a renamed control ruleId -> reshape fails loudly instead of writing zero bytes" \
  "control-renamed-ruleid.json" "CONTROL-JUDGE-IMPOSSIBLE"

assert_reshape_rejects "positive control absent -> reshape fails loudly instead of writing zero bytes" \
  "control-positive-control-absent.json" "CONTROL-JUDGE-TRIVIAL"

assert_reshape_rejects "report with no verdicts key -> reshape fails loudly" \
  "control-no-verdicts-key.json" "expected exactly 1"

# ---------------------------------------------------------------------------
# Whole-step cases: the entire `control_suite` run: body, end to end
# ---------------------------------------------------------------------------
# The marked-region cases above test the assertions in isolation, which is
# what makes their diagnostics precise -- and is also what makes them blind to
# everything BETWEEN the regions: check ordering, and whether each exit path
# leaves the step outputs the later steps depend on.
#
# That blindness was not hypothetical. The F2 comment in this step claimed
# runs_errored was written "before any exit path below"; it was in fact still
# below the verdict_count and lint branches, so a manifest that failed to lint
# exited with runs_errored never written -- the exact defect the comment
# describes itself as fixing. No amount of reading found it. Running the whole
# body against a fixture that exits at verdict_count, and looking at
# GITHUB_OUTPUT, found it immediately.
#
# Only ONE thing is substituted: the live `npx ... sop run` invocation becomes
# a copy of a fixture report plus the exit code muster would have returned.
# Everything else is the shipping bytes.
extract_step_body() {
  local out="$1"
  awk '
    /^      - name: Run control-manifest\.yaml and assert genuine discrimination$/ { step = 1; next }
    step && /^        run: \|$/ { body = 1; step = 0; next }
    body {
      if ($0 == "") { print ""; next }
      if ($0 !~ /^          /) { body = 0; next }
      sub(/^          /, "")
      print
    }
  ' "${WORKFLOW}" > "${out}"
}

step_body="${work_dir}/control-step.sh"
extract_step_body "${step_body}"
if ! grep -q 'npx --yes --offline' "${step_body}"; then
  fail "extraction (whole step) -- the control_suite run: body does not contain the npx invocation; the step name or indentation changed and every whole-step case would test nothing"
  exit 1
fi
if ! grep -q 'runs_errored=' "${step_body}"; then
  fail "extraction (whole step) -- extracted body never writes runs_errored"
  exit 1
fi
echo "PASS: extraction (whole step) -- pulled $(wc -l < "${step_body}") line(s) of the committed control_suite body out of behavioral.yml"

# run_whole_step <fixture> <muster-exit>
# Writes the step's combined output to ${work_dir}/step-output and RETURNS the
# step's own exit code. Deliberately not `$( ... )`-captured by the caller: a
# command substitution runs the function in a subshell, so a variable assigned
# inside it never reaches the caller, and an exit code smuggled out that way
# reads as 0 for every case. (Observed here, first try: four cases reporting
# exit 0 while printing the correct ::error:: diagnostics.)
run_whole_step() {
  local fixture="$1" muster_exit="$2"
  local body="${work_dir}/step-case.sh"
  sed -e "s#^ *npx --yes --offline .*\$#cp ${FIXTURES}/${fixture} \"\${report}\" 2>/dev/null; (exit ${muster_exit})#" \
    "${step_body}" > "${body}"
  if grep -q 'npx --yes --offline' "${body}"; then
    echo "__HARNESS_SUBSTITUTION_FAILED__" > "${work_dir}/step-output"
    return 99
  fi
  : > "${work_dir}/github_output"
  # No `set +e`/`set -e` pair here: restoring `set -e` before `return` would
  # re-arm errexit in the CALLER's shell, so this function returning nonzero
  # would abort the whole suite -- silently, with no FAIL line and every case
  # after this one simply never running. (Observed: 31 PASS lines, zero FAIL
  # lines, exit 1.) The caller owns the flag; assert_step disables it around
  # this call.
  local code=0
  ( cd "${REPO_ROOT}" && GITHUB_OUTPUT="${work_dir}/github_output" bash "${body}" ) \
    > "${work_dir}/step-output" 2>&1 || code=$?
  return "${code}"
}

# assert_step <label> <fixture> <muster-exit> <expected-exit> <substring>
# Also asserts BOTH step outputs the downstream steps read are present on
# every path: report_file (or the evidence step's `if:` guard skips and the
# failing run leaves no evidence at all) and runs_errored.
assert_step() {
  local label="$1" fixture="$2" muster_exit="$3" expected_exit="$4" substring="$5"
  local output actual_exit

  set +e
  run_whole_step "${fixture}" "${muster_exit}"
  actual_exit=$?
  set -e
  output="$(cat "${work_dir}/step-output")"

  if [ "${actual_exit}" -ne "${expected_exit}" ]; then
    fail "${label} -- expected step exit ${expected_exit}, got ${actual_exit} (output: '${output}')"
    return
  fi
  if [[ "${output}" != *"${substring}"* ]]; then
    fail "${label} -- expected output to contain '${substring}', got '${output}'"
    return
  fi
  local gho
  gho="$(cat "${work_dir}/github_output")"
  if [[ "${gho}" != *"report_file="* ]]; then
    fail "${label} -- no report_file written to GITHUB_OUTPUT (got: '${gho}')"
    return
  fi
  if [[ "${gho}" != *"runs_errored="* ]]; then
    fail "${label} -- no runs_errored written to GITHUB_OUTPUT (got: '${gho}'); an exit path that skips it makes a dead-endpoint run record the placeholder 0"
    return
  fi
  echo "PASS: ${label} (exit ${actual_exit})"
}

assert_step "whole step, real healthy 1.2.2 report -> exit 0, discrimination confirmed" \
  "control-all-three-live.json" 1 0 "genuine discrimination confirmed"

assert_step "whole step, real stuck-FAIL judge -> exit 1 naming the POSITIVE control" \
  "control-stuck-judge-live.json" 1 1 "CONTROL-JUDGE-TRIVIAL did not pass"

# The two conditions FR-007 exists to keep apart must not be reported as one
# another: a dead endpoint says "endpoint may be unreachable", never "the
# judge is stuck".
assert_step "whole step, dead endpoint -> exit 1 naming the ENDPOINT, not the judge" \
  "control-dead-endpoint.json" 1 1 "endpoint may be unreachable"

# This fixture exits at the verdict_count branch -- the branch that used to
# skip the runs_errored write. assert_step checks GITHUB_OUTPUT on every case,
# so this is the regression test for the hoist.
assert_step "whole step, wrong verdict count -> exit 1 with both step outputs still written" \
  "control-positive-control-absent.json" 1 1 "expected 3"

# muster exiting 0 means both rigged controls were satisfied: the suite is
# broken, not passing.
assert_step "whole step, muster exited 0 -> exit 1 (a control became satisfiable)" \
  "control-all-three-live.json" 0 1 "did not fail as designed"

# ---------------------------------------------------------------------------
# Manifest / guard agreement
# ---------------------------------------------------------------------------
# Every case above runs against committed report FIXTURES, so all of them stay
# green if someone deletes CONTROL-JUDGE-TRIVIAL from control-manifest.yaml
# and leaves the workflow alone. CI would eventually catch it -- on the next
# live dispatch, at verdict_count -- which is both late and expensive. The
# manifest's declared rules and the guard's expected set are two files that
# have to agree, so compare them here, statically, out of the committed bytes
# of each.
MANIFEST="${REPO_ROOT}/conformance/behavioral/control-manifest.yaml"
manifest_rule_ids="$(grep -oE '^  - ruleId: [A-Za-z0-9_-]+' "${MANIFEST}" 2>/dev/null \
  | sed 's/^  - ruleId: //' | LC_ALL=C sort | tr '\n' ' ' | sed 's/ $//')"
workflow_rule_ids="$(grep -oE 'expected_rule_ids="[^"]*"' "${WORKFLOW}" | head -1 \
  | sed 's/^expected_rule_ids="//; s/"$//')"

if [ -z "${manifest_rule_ids}" ]; then
  fail "manifest/guard agreement -- parsed zero ruleIds out of ${MANIFEST}; the comparison below would be vacuous"
elif [ "${manifest_rule_ids}" != "${workflow_rule_ids}" ]; then
  fail "manifest/guard agreement -- control-manifest.yaml declares [${manifest_rule_ids}] but behavioral.yml expects [${workflow_rule_ids}]; the divergence would only surface on a live dispatch"
else
  echo "PASS: control-manifest.yaml's rules and the guard's expected ruleId set agree ([${manifest_rule_ids}])"
fi

# The positive control must be a JUDGE rule. A binary one would prove nothing
# about the judge path, which is the entire reason it exists.
if ! grep -Pzoq 'ruleId: CONTROL-JUDGE-TRIVIAL\n(.*\n)*?    gradingClass: judge\n' "${MANIFEST}"; then
  fail "positive control gradingClass -- CONTROL-JUDGE-TRIVIAL is not declared gradingClass: judge; a non-judge positive control cannot detect a stuck judge"
else
  echo "PASS: CONTROL-JUDGE-TRIVIAL is declared gradingClass: judge"
fi

# The pin the workflow actually ships must be the one this suite's fixtures
# were produced under. A test that accepts any pin cannot notice the pin
# regressing to 1.2.1.
shipped_pin="$(awk -F'"' '/^  MUSTER_PIN:/ {print $2}' "${WORKFLOW}")"
if [ "${shipped_pin}" != "@garrison-hq/muster@1.2.2" ]; then
  fail "shipped MUSTER_PIN is '${shipped_pin}', expected '@garrison-hq/muster@1.2.2' -- @1.2.1's judge-threshold defect (garrison-hq/muster#88) is a judge stuck at FAIL"
else
  echo "PASS: workflow ships MUSTER_PIN=@garrison-hq/muster@1.2.2"
fi

if [ "${failures}" -gt 0 ]; then
  echo "control-discrimination-guard.test.sh: ${failures} case(s) failed"
  exit 1
fi

echo "control-discrimination-guard.test.sh: all cases passed"
