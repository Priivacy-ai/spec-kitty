#!/usr/bin/env bash
# build-evidence-artifact.test.sh -- committed test for
# build-evidence-artifact.sh, the cross-job merge + reshape that produces
# spec.md's single `conformance/behavioral/evidence/<ISO-date>-<mid8>.json`
# Acceptance-Gate artifact from the two per-job evidence files
# .github/workflows/behavioral.yml's main-suite and control-suite jobs write.
#
# Every case below records BOTH an accepted run and the input it must
# reject. A validation with no recorded rejection run is not a validation.
#
# Usage: bash conformance/behavioral/scripts/build-evidence-artifact.test.sh
# Exits 0 if every case passes, 1 on any failing case.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUT="${SCRIPT_DIR}/build-evidence-artifact.sh"
FIXTURES="${SCRIPT_DIR}/fixtures/evidence"

failures=0
work_dir="$(mktemp -d)"
trap 'rm -rf "${work_dir}"' EXIT

out_dir="${work_dir}/out"
last_stdout=""
last_stderr=""
last_exit=0

# run_sut <main-fixture-or-__OMIT__> <control-fixture-or-__OMIT__> [extra args...]
run_sut() {
  local main="$1" control="$2"
  shift 2
  local args=()
  [ "${main}" != "__OMIT__" ] && args+=(--main "${FIXTURES}/${main}")
  [ "${control}" != "__OMIT__" ] && args+=(--control "${FIXTURES}/${control}")
  args+=(--mission 01KYW5XK --out-dir "${out_dir}" "$@")

  rm -rf "${out_dir}"
  mkdir -p "${out_dir}"
  set +e
  last_stdout="$(bash "${SUT}" "${args[@]}" 2>"${work_dir}/stderr")"
  last_exit=$?
  set -e
  last_stderr="$(cat "${work_dir}/stderr")"
}

fail() {
  echo "FAIL: $1"
  failures=$((failures + 1))
}

pass() {
  echo "PASS: $1"
}

# assert_rejects <label> <main> <control> <expected-exit>
# Also asserts the rejection wrote NO artifact: a script that emits a
# half-built file and then exits nonzero leaves a gate reviewer a file to
# find, which is worse than none.
assert_rejects() {
  local label="$1" main="$2" control="$3" expected_exit="$4"
  run_sut "${main}" "${control}"

  if [ "${last_exit}" -ne "${expected_exit}" ]; then
    fail "${label} -- expected exit ${expected_exit}, got ${last_exit} (stderr: '${last_stderr}')"
    return
  fi

  local emitted
  emitted="$(find "${out_dir}" -type f | wc -l)"
  if [ "${emitted}" -ne 0 ]; then
    fail "${label} -- exited ${last_exit} but still wrote ${emitted} file(s) into the output directory"
    return
  fi

  pass "${label} (exit ${last_exit})"
}

# --------------------------------------------------------------------------
# Case 0: the executable bit, in the filesystem AND in git's index.
# .github/workflows/behavioral.yml's merge-evidence job invokes this script
# by path, not via `bash <script>` (matching how main-suite invokes
# check-runs-errored.sh), so a 100644 mode is a live "Permission denied,
# exit 126" in CI that no amount of `bash script.sh` testing would ever
# surface. This was a genuine defect caught by executing the merge step, not
# by reading it.
# --------------------------------------------------------------------------
if [ ! -x "${SUT}" ]; then
  fail "executable bit -- ${SUT} is not executable; the merge job invokes it by path and would exit 126"
else
  pass "executable bit -- SUT is executable on disk"
fi

if command -v git >/dev/null 2>&1; then
  git_mode="$(cd "${SCRIPT_DIR}" && git ls-files -s -- "$(basename "${SUT}")" 2>/dev/null | cut -d' ' -f1)"
  if [ -n "${git_mode}" ] && [ "${git_mode}" != "100755" ]; then
    fail "executable bit -- git records mode ${git_mode} for $(basename "${SUT}"); the CI checkout would not be executable"
  else
    pass "executable bit -- git records mode ${git_mode:-<untracked>}"
  fi
fi

# --------------------------------------------------------------------------
# Case 1 (healthy): the real two-job inputs merge into one gate artifact.
# --------------------------------------------------------------------------
run_sut "main-live.json" "control-live.json"
if [ "${last_exit}" -ne 0 ]; then
  echo "FAIL: healthy merge -- expected exit 0, got ${last_exit} (stderr: '${last_stderr}')"
  echo "     remaining cases depend on this; aborting"
  exit 1
fi
pass "healthy merge -> exit 0"

merged="${out_dir}/2026-08-02-01KYW5XK.json"

# The filename is the gate's first sub-bullet verbatim: <ISO-date>-<mid8>.json,
# with the date taken from the run's own ranAt, not from wall-clock time at
# merge time.
if [ ! -f "${merged}" ]; then
  fail "artifact filename -- expected ${merged}, found: $(find "${out_dir}" -type f)"
else
  pass "artifact filename -> <ISO-date>-<mid8>.json derived from ranAt"
fi

if [ "${last_stdout}" != "${merged}" ]; then
  fail "stdout -- expected the written path '${merged}', got '${last_stdout}'"
else
  pass "stdout -> the written artifact path (so CI can hand it to upload/commit)"
fi

# assert_jq <label> <jq-filter> <expected>
# jq's own failure is reported as a failed case, never allowed to abort the
# suite under `set -e`: a filter that errors because the key it reads is
# absent is precisely the regression these cases exist to catch, and an
# aborted suite hides every case after it.
assert_jq() {
  local label="$1" filter="$2" expected="$3" actual
  set +e
  actual="$(jq -c "${filter}" "${merged}" 2>&1)"
  local jq_exit=$?
  set -e
  if [ "${jq_exit}" -ne 0 ]; then
    fail "${label} -- jq exited ${jq_exit} reading the artifact: ${actual}"
    return
  fi
  if [ "${actual}" != "${expected}" ]; then
    fail "${label} -- expected ${expected}, got ${actual}"
    return
  fi
  pass "${label}"
}

# spec.md's Evidence Artifact shape: perProfile keyed by profile id, then by
# camelCase axis, each {passCount, totalRuns, runsErrored}.
assert_jq "perProfile keyed by profile id" \
  '.perProfile | keys' '["architect-alphonso","reviewer-renata"]'

assert_jq "perProfile.<id> keyed by camelCase axis (all four)" \
  '.perProfile["architect-alphonso"] | keys' \
  '["avoidanceBoundary","canonicalVerbs","capabilityContainment","handoffDiscipline"]'

assert_jq "axis entry carries exactly passCount/totalRuns/runsErrored" \
  '.perProfile["architect-alphonso"].avoidanceBoundary | keys' \
  '["passCount","runsErrored","totalRuns"]'

# Values must be the live run's own, not a template. The live
# architect-alphonso run graded 4/5 on avoidance-boundary and 5/5 on
# capability-containment; if the reshape lost the mapping, these would swap
# or collapse.
assert_jq "avoidanceBoundary values carried from the live run" \
  '.perProfile["architect-alphonso"].avoidanceBoundary' \
  '{"passCount":4,"totalRuns":5,"runsErrored":0}'

assert_jq "capabilityContainment values carried from the live run" \
  '.perProfile["architect-alphonso"].capabilityContainment' \
  '{"passCount":5,"totalRuns":5,"runsErrored":0}'

assert_jq "handoffDiscipline values carried from the live run" \
  '.perProfile["architect-alphonso"].handoffDiscipline' \
  '{"passCount":0,"totalRuns":5,"runsErrored":0}'

# FR-006's `runs >= 5` is what the gate reads off totalRuns.
assert_jq "every axis of every profile records totalRuns >= 5" \
  '[.perProfile[][] | .totalRuns] | map(. >= 5) | all' 'true'

# The control-suite half must survive the merge intact (gate item 2's third
# bullet reads passed:false + runsErrored:0 off it).
assert_jq "controlManifest.judgeControl merged in" \
  '.controlManifest.judgeControl | {passed, passCount, totalRuns, runsErrored}' \
  '{"passed":false,"passCount":0,"totalRuns":3,"runsErrored":0}'

assert_jq "controlManifest.behavioralControl merged in" \
  '.controlManifest.behavioralControl | {passed, runsErrored}' \
  '{"passed":false,"runsErrored":0}'

# F1: the positive judge control. The two controls above are both NEGATIVE,
# and the impossible-rubric one fails under a stuck-FAIL judge exactly as it
# does under a healthy one -- so a gate artifact carrying only those two
# cannot distinguish a healthy run from a total judge outage, which is the
# condition that turns every judge-graded rule in perProfile red.
assert_jq "controlManifest.judgePositiveControl merged in (passed: true)" \
  '.controlManifest.judgePositiveControl | {passed, passCount, totalRuns, runsErrored}' \
  '{"passed":true,"passCount":3,"totalRuns":3,"runsErrored":0}'

assert_jq "all three controls survive the merge" \
  '.controlManifest | keys' \
  '["behavioralControl","judgeControl","judgePositiveControl"]'

assert_jq "model/endpointHost/ranAt carried to the top level" \
  '{model, endpointHost, ranAt}' \
  '{"model":"gpt-4o-mini","endpointHost":"api.openai.com","ranAt":"2026-08-02T09:15:00Z"}'

# The three FR-005 doctrine manifests main-suite also runs are NOT profiles
# and must not appear under perProfile -- but discarding them entirely would
# make the merge lossy, so they get their own key.
assert_jq "doctrine manifests excluded from perProfile" \
  '[.perProfile | keys[] | select(startswith("0"))] | length' '0'

assert_jq "doctrine manifests preserved under their own key (merge is lossless)" \
  '[.doctrineManifests[].manifest]' \
  '["conformance/doctrine/010-specification-fidelity-requirement.yaml"]'

# --------------------------------------------------------------------------
# Case 2 (the runsErrored rejection the whole artifact exists for): a
# dead-endpoint main-suite run must surface a NONZERO runsErrored per axis,
# never the placeholder 0 that this mission's own postmortem history
# (0/24 re-measuring at 4/24) is about.
# --------------------------------------------------------------------------
run_sut "main-dead-endpoint.json" "control-live.json"
if [ "${last_exit}" -ne 0 ]; then
  fail "dead-endpoint merge -- expected exit 0, got ${last_exit} (stderr: '${last_stderr}')"
else
  merged_dead="${out_dir}/2026-08-02-01KYW5XK.json"
  actual="$(jq -c '.perProfile["architect-alphonso"].avoidanceBoundary' "${merged_dead}")"
  if [ "${actual}" != '{"passCount":0,"totalRuns":5,"runsErrored":5}' ]; then
    fail "dead-endpoint runsErrored -- expected 5 errored runs recorded, got ${actual}"
  else
    pass "dead-endpoint main-suite -> runsErrored: 5 recorded per axis, not a placeholder 0"
  fi
fi
merged="${out_dir}/2026-08-02-01KYW5XK.json"

# --------------------------------------------------------------------------
# Rejection cases.
# --------------------------------------------------------------------------

# A main-suite evidence file that matched zero profile manifests would
# otherwise produce `perProfile: {}` -- a syntactically valid artifact the
# gate reviewer would read as "the suite ran", having exercised no profile.
assert_rejects "main-suite evidence with zero profile cases -> rejected" \
  "main-doctrine-only.json" "control-live.json" 4

# A ruleId that does not carry its own profile-id suffix means the naming
# convention the axis key is derived from has drifted; deriving an axis name
# anyway would emit a plausible-looking but wrong key.
assert_rejects "profile case whose ruleId lacks the profile-id suffix -> rejected" \
  "main-ruleid-drift.json" "control-live.json" 4

# Two jobs that hit different endpoints must never be merged under one
# endpointHost -- the merged artifact would attribute one job's results to
# the other job's endpoint.
assert_rejects "main and control disagree on endpointHost -> rejected" \
  "main-live.json" "control-other-host.json" 5

assert_rejects "main and control disagree on model -> rejected" \
  "main-live.json" "control-other-model.json" 5

# Structural rejections.
assert_rejects "main-suite evidence missing mainSuiteCases -> rejected" \
  "main-missing-cases-key.json" "control-live.json" 4

assert_rejects "control evidence missing controlManifest -> rejected" \
  "main-live.json" "control-missing-key.json" 4

assert_rejects "control evidence missing behavioralControl -> rejected" \
  "main-live.json" "control-half.json" 4

# F1: a control evidence file carrying only the two NEGATIVE controls is
# exactly the pre-fix shape. It is structurally valid and reads as a complete
# discrimination record, and it is the one shape a stuck-FAIL judge produces
# indistinguishably from a healthy endpoint -- so the merge must refuse it
# rather than hand the gate reviewer an artifact that cannot answer the
# question it exists to answer.
assert_rejects "control evidence missing judgePositiveControl -> rejected" \
  "main-live.json" "control-no-positive.json" 4

assert_rejects "ranAt that is not an ISO date -> rejected (filename would be garbage)" \
  "main-bad-ranat.json" "control-live.json" 4

# Two ruleIds whose axis names camel-collapse to the same key (a case-only
# drift such as CANONICAL-VERBS vs canonical-verbs) would be silently
# de-duplicated by jq's from_entries, dropping one axis from the artifact
# while leaving it looking complete.
assert_rejects "two ruleIds collapsing to the same axis key -> rejected" \
  "main-axis-collision.json" "control-live.json" 4

# Two cases with the same profile basename would overwrite each other in
# perProfile the same way.
assert_rejects "duplicate profile id across cases -> rejected" \
  "main-duplicate-profile.json" "control-live.json" 4

assert_rejects "zero-byte main evidence -> rejected" \
  "main-zero-byte.json" "control-live.json" 3

assert_rejects "malformed (non-JSON) control evidence -> rejected" \
  "main-live.json" "control-malformed.json" 3

assert_rejects "two concatenated JSON documents -> rejected" \
  "main-concatenated.json" "control-live.json" 3

# Usage rejections.
assert_rejects "--control omitted -> usage error" "main-live.json" "__OMIT__" 1
assert_rejects "--main omitted -> usage error" "__OMIT__" "control-live.json" 1
assert_rejects "--main points at a nonexistent file -> usage error" \
  "no-such-file.json" "control-live.json" 1

# --------------------------------------------------------------------------
# --require-axes: the workflow passes 4 (spec.md's FR-001..004 axis count).
# Both directions are exercised -- a flag that only ever accepts is not a
# check.
# --------------------------------------------------------------------------
run_sut "main-live.json" "control-live.json" --require-axes 4
if [ "${last_exit}" -ne 0 ]; then
  fail "--require-axes 4 on the live four-axis run -- expected exit 0, got ${last_exit} (stderr: '${last_stderr}')"
else
  pass "--require-axes 4 on the live four-axis run -> accepted"
fi

run_sut "main-live.json" "control-live.json" --require-axes 5
if [ "${last_exit}" -ne 4 ]; then
  fail "--require-axes 5 on a four-axis run -- expected exit 4, got ${last_exit}"
elif [ "$(find "${out_dir}" -type f | wc -l)" -ne 0 ]; then
  fail "--require-axes 5 -- rejected but still wrote an artifact"
else
  pass "--require-axes 5 on a four-axis run -> rejected, no artifact written"
fi

run_sut "main-live.json" "control-live.json" --require-axes notanumber
if [ "${last_exit}" -ne 1 ]; then
  fail "--require-axes with a non-integer -- expected usage exit 1, got ${last_exit}"
else
  pass "--require-axes with a non-integer -> usage error (exit 1)"
fi

# --------------------------------------------------------------------------
# Workflow contract: these fixtures were generated by the main-suite step's
# OWN jq expressions. If that step's shape changes, the fixtures go stale and
# every case above would keep passing against a shape CI no longer produces.
# Re-run the committed expression against the committed raw muster report and
# assert the key set this script consumes.
# --------------------------------------------------------------------------
workflow="$(cd "${SCRIPT_DIR}/../../.." && pwd)/.github/workflows/behavioral.yml"
per_case_jq="$(sed -n "s/^ *'\(\[\.verdicts\[\] | {ruleId.*\)' *\\\\$/\1/p" "${workflow}")"
if [ -z "${per_case_jq}" ]; then
  fail "workflow contract -- could not extract main-suite's per_case_errored jq from ${workflow}"
else
  actual_keys="$(jq -c "${per_case_jq} | map(keys) | unique" "${SCRIPT_DIR}/fixtures/raw/architect-alphonso.json")"
  if [ "${actual_keys}" != '[["passCount","ruleId","runsErrored","totalRuns"]]' ]; then
    fail "workflow contract -- main-suite's own perCase jq now emits ${actual_keys}; the committed evidence fixtures are stale"
  else
    pass "workflow contract -- main-suite's perCase jq still emits {ruleId,passCount,totalRuns,runsErrored}"
  fi
fi

# --mission is what supplies <mid8>; without it the filename cannot be built.
rm -rf "${out_dir}"; mkdir -p "${out_dir}"
set +e
bash "${SUT}" --main "${FIXTURES}/main-live.json" --control "${FIXTURES}/control-live.json" \
  --out-dir "${out_dir}" >/dev/null 2>&1
rc=$?
set -e
if [ "${rc}" -ne 1 ]; then
  fail "--mission omitted -> expected usage exit 1, got ${rc}"
else
  pass "--mission omitted -> usage error (exit 1)"
fi

# jq absent from PATH.
rm -rf "${out_dir}"; mkdir -p "${out_dir}"
set +e
PATH=/nonexistent-bin "$(command -v bash)" "${SUT}" \
  --main "${FIXTURES}/main-live.json" --control "${FIXTURES}/control-live.json" \
  --mission 01KYW5XK --out-dir "${out_dir}" >/dev/null 2>&1
rc=$?
set -e
if [ "${rc}" -ne 2 ]; then
  fail "jq absent from PATH -> expected exit 2, got ${rc}"
else
  pass "jq absent from PATH -> exit 2"
fi

if [ "${failures}" -gt 0 ]; then
  echo "build-evidence-artifact.test.sh: ${failures} case(s) failed"
  exit 1
fi

echo "build-evidence-artifact.test.sh: all cases passed"
