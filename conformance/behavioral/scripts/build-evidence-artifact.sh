#!/usr/bin/env bash
# build-evidence-artifact.sh -- merge the cadence workflow's two per-job
# evidence files into the single committed gate artifact spec.md's Evidence
# Artifact section and Acceptance Gate item 2 both name:
# conformance/behavioral/evidence/<ISO-date>-<mid8>.json.
#
# Why a script and not inline workflow jq: .github/workflows/behavioral.yml's
# main-suite and control-suite run as two separate GitHub Actions jobs on two
# separate runners, so the merge can only happen in a third job that
# downloads both artifacts. Putting the reshape in a script makes it
# executable -- and therefore falsifiable -- outside CI; see
# build-evidence-artifact.test.sh, which drives every accept and reject path
# below against committed fixtures derived from real
# @garrison-hq/muster@1.2.2 runs.
#
# What the reshape is, precisely: a pure transform of data already present in
# the two inputs. Nothing here is invented.
#   perProfile.<profile-id>          <- basename of the case's own `manifest`
#                                       path, minus `.yaml`
#   perProfile.<id>.<axis>           <- the case's ruleId with its
#                                       `-<profile-id>` suffix removed, then
#                                       KEBAB-UPPER -> camelCase
#                                       (AVOIDANCE-BOUNDARY-architect-alphonso
#                                       -> avoidanceBoundary)
#   .{passCount,totalRuns,runsErrored} <- copied verbatim off the case's own
#                                       perCase entry
#   controlManifest                  <- copied verbatim from the control job
#   model/endpointHost/musterVersion/ranAt <- from the main job, after
#                                       asserting the control job agrees on
#                                       model and endpointHost
#
# Usage:
#   build-evidence-artifact.sh --main <main-suite-evidence.json>
#                              --control <control-suite-evidence.json>
#                              --mission <mid8>
#                              --out-dir <dir>
#                              [--require-axes <n>]
#
# Prints the absolute path of the written artifact to stdout. `--require-axes`
# is deliberately a call-site argument rather than a constant: the number of
# behavioral axes is spec.md's design (four -- FR-001..004), not this
# script's, and the workflow passes it where that knowledge lives.
#
# Exit code contract (every code below has a committed rejection test):
#   0  success -- artifact written, path printed.
#   1  usage error -- a required argument is missing, or an input path does
#      not exist / is not a regular file.
#   2  `jq` is not installed on PATH.
#   3  an input is not exactly one JSON document (zero-byte, whitespace-only,
#      malformed, or concatenated documents) -- same fail-closed rule, and
#      same `jq -s 'length'` mechanism, as check-runs-errored.sh.
#   4  an input is valid JSON but structurally unusable: a required key is
#      absent, `ranAt` is not an ISO-8601 date, zero profile cases were found
#      (which would emit an empty `perProfile` a gate reviewer could misread
#      as "the suite ran"), a ruleId does not carry its own profile-id suffix
#      (so the derived axis key would be plausible but wrong), a duplicate
#      profile id or axis key would silently overwrite a sibling, or
#      --require-axes was given and some profile does not have that many
#      axes.
#   5  the two jobs disagree on `model` or `endpointHost` -- merging them
#      would attribute one job's results to the other job's endpoint.
#
# On any nonzero exit, no file is written into --out-dir: the artifact is
# built into a temporary file and moved into place only after every check
# passes, so a failed merge never leaves a half-built artifact for a gate
# reviewer to find.
#
# Pin note: this script runs no muster invocation of its own; it only reshapes
# reports already produced by `muster sop run --json`. Callers must pin
# @garrison-hq/muster@1.2.2 (never @1.2.1 -- garrison-hq/muster#89) when
# producing those reports.
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "build-evidence-artifact.sh: jq is required but not found on PATH" >&2
  exit 2
fi

die_usage() {
  echo "build-evidence-artifact.sh: $1" >&2
  echo "usage: build-evidence-artifact.sh --main <file> --control <file> --mission <mid8> --out-dir <dir> [--require-axes <n>]" >&2
  exit 1
}

die_shape() {
  echo "build-evidence-artifact.sh: $1" >&2
  exit 4
}

main_file=""
control_file=""
mission=""
out_dir=""
require_axes=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --main) main_file="${2:-}"; shift 2 || die_usage "--main needs a value" ;;
    --control) control_file="${2:-}"; shift 2 || die_usage "--control needs a value" ;;
    --mission) mission="${2:-}"; shift 2 || die_usage "--mission needs a value" ;;
    --out-dir) out_dir="${2:-}"; shift 2 || die_usage "--out-dir needs a value" ;;
    --require-axes) require_axes="${2:-}"; shift 2 || die_usage "--require-axes needs a value" ;;
    *) die_usage "unknown argument '$1'" ;;
  esac
done

[ -n "${main_file}" ] || die_usage "--main is required"
[ -n "${control_file}" ] || die_usage "--control is required"
[ -n "${mission}" ] || die_usage "--mission is required"
[ -n "${out_dir}" ] || die_usage "--out-dir is required"
[ -f "${main_file}" ] || die_usage "--main path '${main_file}' does not exist or is not a regular file"
[ -f "${control_file}" ] || die_usage "--control path '${control_file}' does not exist or is not a regular file"
[ -d "${out_dir}" ] || die_usage "--out-dir '${out_dir}' does not exist or is not a directory"
if [ -n "${require_axes}" ] && [[ ! "${require_axes}" =~ ^[0-9]+$ ]]; then
  die_usage "--require-axes must be a non-negative integer, got '${require_axes}'"
fi

# Same fail-closed single-document guard as check-runs-errored.sh: `jq empty`
# treats zero documents (zero-byte, whitespace-only) AND two concatenated
# documents as vacuously valid, so slurp-and-count instead.
assert_one_document() {
  local label="$1" path="$2" doc_count
  doc_count="$(jq -s 'length' "${path}" 2>/dev/null || echo "invalid")"
  if [ "${doc_count}" != "1" ]; then
    echo "build-evidence-artifact.sh: ${label} '${path}' is not exactly one valid JSON document (got: ${doc_count}) -- zero-byte, whitespace-only, malformed, or multiple concatenated documents" >&2
    exit 3
  fi
}

assert_one_document "--main" "${main_file}"
assert_one_document "--control" "${control_file}"

# jq_bool <filter> <file> -- evaluates a boolean filter, treating any jq
# runtime error as false rather than letting it decide the exit status. A jq
# error on a missing key coincidentally exits 1, which would otherwise
# satisfy a status-based check for the wrong reason.
jq_bool() {
  local result
  result="$(jq -r "$1" "$2" 2>/dev/null || echo "false")"
  [ "${result}" = "true" ]
}

jq_bool '(.mainSuiteCases | type) == "array"' "${main_file}" \
  || die_shape "--main '${main_file}' has no .mainSuiteCases array (not a main-suite evidence file?)"
jq_bool '(.model | type) == "string" and (.endpointHost | type) == "string" and (.ranAt | type) == "string"' "${main_file}" \
  || die_shape "--main '${main_file}' is missing a string .model, .endpointHost or .ranAt"
jq_bool '(.controlManifest.judgeControl | type) == "object"' "${control_file}" \
  || die_shape "--control '${control_file}' has no .controlManifest.judgeControl object"
jq_bool '(.controlManifest.behavioralControl | type) == "object"' "${control_file}" \
  || die_shape "--control '${control_file}' has no .controlManifest.behavioralControl object"
# F1: the positive judge control is required, not optional. judgeControl and
# behavioralControl are both NEGATIVE controls, and the impossible-rubric one
# fails identically under a healthy judge and under a judge stuck at FAIL --
# measured, by running the committed control-manifest.yaml against a real
# endpoint under @garrison-hq/muster@1.2.1 (judge-threshold defect
# garrison-hq/muster#88) and getting a report indistinguishable from the
# healthy @1.2.2 one on every field the guard read. A gate artifact carrying
# only those two therefore cannot tell a reviewer whether perProfile's judge
# results mean the model failed or the grader did, which is the whole of
# FR-007. Accepting the two-key shape would let a future revert pass silently.
jq_bool '(.controlManifest.judgePositiveControl | type) == "object"' "${control_file}" \
  || die_shape "--control '${control_file}' has no .controlManifest.judgePositiveControl object -- the two negative controls alone cannot distinguish a healthy judge from one stuck at FAIL"
jq_bool '(.model | type) == "string" and (.endpointHost | type) == "string"' "${control_file}" \
  || die_shape "--control '${control_file}' is missing a string .model or .endpointHost"

ran_at="$(jq -r '.ranAt' "${main_file}")"
run_date="${ran_at:0:10}"
if [[ ! "${run_date}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  die_shape "--main '${main_file}' .ranAt ('${ran_at}') does not start with an ISO-8601 date -- the gate artifact's <ISO-date>-<mid8>.json filename cannot be derived from it"
fi

# The gate artifact carries ONE model and ONE endpointHost. If the two jobs
# actually ran against different ones, the merged file would misattribute
# half its own contents.
main_model="$(jq -r '.model' "${main_file}")"
control_model="$(jq -r '.model' "${control_file}")"
main_host="$(jq -r '.endpointHost' "${main_file}")"
control_host="$(jq -r '.endpointHost' "${control_file}")"
if [ "${main_model}" != "${control_model}" ]; then
  echo "build-evidence-artifact.sh: main-suite ran model '${main_model}' but control-suite ran '${control_model}' -- refusing to merge two different runs into one gate artifact" >&2
  exit 5
fi
if [ "${main_host}" != "${control_host}" ]; then
  echo "build-evidence-artifact.sh: main-suite ran against endpoint host '${main_host}' but control-suite ran against '${control_host}' -- refusing to merge two different runs into one gate artifact" >&2
  exit 5
fi

# --------------------------------------------------------------------------
# The reshape itself. Split into a validation pass and a build pass so a
# convention violation names the offending ruleId instead of silently
# emitting a wrong-but-plausible axis key.
# --------------------------------------------------------------------------

# A "profile case" is one whose manifest lives in the directory the workflow
# globs (conformance/behavioral/profiles/*.yaml) -- that glob is the
# authoritative definition of a profile manifest, so selection follows it
# rather than guessing from ruleId shape. The ruleId convention is then
# ASSERTED for every selected case, not assumed.
JQ_COMMON='
  def profile_id: (.manifest | split("/") | last | sub("\\.yaml$"; ""));
  def is_profile_case: (.manifest | split("/") | .[0:-1] | join("/")
                        | endswith("conformance/behavioral/profiles"));
  def to_camel: ascii_downcase | split("-")
                | .[0] + (.[1:] | map((.[0:1] | ascii_upcase) + .[1:]) | join(""));
'

violations="$(jq -r "${JQ_COMMON}"'
  [ .mainSuiteCases[] | select(is_profile_case) as $case
    | $case | profile_id as $pid
    | ($case.perCase // [])
    | if length == 0 then
        ["profile manifest \($case.manifest) contributed zero cases -- an empty axis set would be indistinguishable from a profile that was never graded"]
      else
        [ .[] | select((.ruleId | endswith("-" + $pid)) | not)
          | "ruleId \"\(.ruleId)\" in \($case.manifest) does not end with \"-\($pid)\" -- the axis key derived from it would be wrong"
        ]
        + [ .[] | select(.ruleId == ("-" + $pid) or (.ruleId | length) <= ($pid | length) + 1)
            | "ruleId \"\(.ruleId)\" in \($case.manifest) has no axis part before the \"-\($pid)\" suffix"
          ]
      end
    | .[]
  ] | .[]
' "${main_file}" 2>&1)" || die_shape "--main '${main_file}' could not be walked for profile cases: ${violations}"

if [ -n "${violations}" ]; then
  die_shape "profile ruleId convention violated:${violations//$'\n'/; }"
fi

profile_case_count="$(jq "${JQ_COMMON}"'[.mainSuiteCases[] | select(is_profile_case)] | length' "${main_file}")"
if [ "${profile_case_count}" -eq 0 ]; then
  die_shape "--main '${main_file}' contains zero cases from conformance/behavioral/profiles/ -- perProfile would be an empty object, which a gate reviewer would read as a suite that ran"
fi

distinct_profiles="$(jq "${JQ_COMMON}"'[.mainSuiteCases[] | select(is_profile_case) | profile_id] | unique | length' "${main_file}")"
if [ "${distinct_profiles}" -ne "${profile_case_count}" ]; then
  die_shape "--main '${main_file}' has ${profile_case_count} profile case(s) but only ${distinct_profiles} distinct profile id(s) -- a duplicate would silently overwrite a sibling in perProfile"
fi

tmp_artifact="$(mktemp)"
# shellcheck disable=SC2064 # expand tmp_artifact now, not at trap time
trap "rm -f '${tmp_artifact}'" EXIT

# jq has no "two named file inputs" flag, so pass both through --argjson
# (each already validated as exactly one JSON document above).
jq -n "${JQ_COMMON}"'
  ($main.mainSuiteCases | map(select(is_profile_case))) as $profileCases
  | {
      model: $main.model,
      endpointHost: $main.endpointHost,
      musterVersion: ($main.musterVersion // ""),
      ranAt: $main.ranAt,
      perProfile: ($profileCases
        | map(profile_id as $pid
              | {
                  key: $pid,
                  value: (.perCase
                    | map({
                        key: (.ruleId | .[0:(length - ($pid | length) - 1)] | to_camel),
                        value: {passCount: .passCount, totalRuns: .totalRuns, runsErrored: .runsErrored}
                      })
                    | from_entries)
                })
        | from_entries),
      controlManifest: $control.controlManifest,
      doctrineManifests: ($main.mainSuiteCases | map(select(is_profile_case | not)))
    }
' --argjson main "$(cat "${main_file}")" --argjson control "$(cat "${control_file}")" \
  > "${tmp_artifact}"

# from_entries silently keeps the last of any duplicate key, so two rules
# whose axis names collide (e.g. CANONICAL-VERBS and CANONICAL_VERBS) would
# quietly drop one axis. Compare the emitted axis count against the input
# case count per profile.
axis_loss="$(jq -r "${JQ_COMMON}"'
  [ ($built.perProfile | to_entries[]) as $entry
    | ($input.mainSuiteCases[] | select(is_profile_case) | select(profile_id == $entry.key) | .perCase | length) as $expected
    | select(($entry.value | length) != $expected)
    | "profile \($entry.key): \($expected) case(s) collapsed to \($entry.value | length) axis key(s) -- an axis name collision dropped data"
  ] | .[]
' --argjson built "$(cat "${tmp_artifact}")" --argjson input "$(cat "${main_file}")" -n)"

if [ -n "${axis_loss}" ]; then
  die_shape "axis key collision:${axis_loss//$'\n'/; }"
fi

if [ -n "${require_axes}" ]; then
  short="$(jq -r --argjson n "${require_axes}" '
    [ .perProfile | to_entries[] | select((.value | length) != $n)
      | "\(.key) has \(.value | length) axis/axes" ] | .[]
  ' "${tmp_artifact}")"
  if [ -n "${short}" ]; then
    die_shape "--require-axes ${require_axes} not met:${short//$'\n'/; }"
  fi
fi

artifact_path="${out_dir%/}/${run_date}-${mission}.json"
mv "${tmp_artifact}" "${artifact_path}"
trap - EXIT
echo "${artifact_path}"
