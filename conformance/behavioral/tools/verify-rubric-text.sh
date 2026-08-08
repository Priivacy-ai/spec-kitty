#!/usr/bin/env bash
# verify-rubric-text.sh -- byte-identity check of one profile manifest's
# rubricText against muster's spec-kitty-profile behavioral-axes rubric doc,
# using extract-rubric-section.sh's corrected, line-anchored extraction.
#
# Guards against a vacuous pass: an out-of-range axis number or a
# non-matching ruleId prefix can otherwise produce 0 bytes on both sides,
# which `diff` reports as identical (exit 0) even though neither side ever
# extracted real content. This script requires both extracted files to be
# non-empty (`test -s`) before diffing.
#
# Usage: verify-rubric-text.sh <n> <rule-id-prefix> <profile-manifest> <muster-checkout>
#   n                axis number, 1-4 (see extract-rubric-section.sh)
#   rule-id-prefix   one of AVOIDANCE-BOUNDARY, CAPABILITY-CONTAINMENT,
#                    HANDOFF-DISCIPLINE, CANONICAL-VERBS
#   profile-manifest path to a conformance/behavioral/profiles/<id>.yaml file
#   muster-checkout  path to a muster checkout containing
#                    docs/rubric/spec-kitty-behavioral-axes.md
#
# Exits 0 and prints nothing on a byte-identical match. Exits non-zero (with
# a diagnostic on stderr and, when applicable, the diff on stdout) on any
# mismatch, missing rule, empty extraction on either side, or missing files.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

n="${1:?usage: verify-rubric-text.sh <n:1-4> <rule-id-prefix> <profile-manifest> <muster-checkout>}"
rule_id_prefix="${2:?usage: verify-rubric-text.sh <n:1-4> <rule-id-prefix> <profile-manifest> <muster-checkout>}"
manifest="${3:?usage: verify-rubric-text.sh <n:1-4> <rule-id-prefix> <profile-manifest> <muster-checkout>}"
checkout="${4:?usage: verify-rubric-text.sh <n:1-4> <rule-id-prefix> <profile-manifest> <muster-checkout>}"

test -f "$manifest" || { echo "verify-rubric-text.sh: manifest not found: $manifest" >&2; exit 1; }

rubric_tmp="$(mktemp)"
manifest_tmp="$(mktemp)"
trap 'rm -f "$rubric_tmp" "$manifest_tmp"' EXIT

"$script_dir/extract-rubric-section.sh" "$n" "$checkout" > "$rubric_tmp"

yq -r ".rules[] | select(.ruleId | test(\"^${rule_id_prefix}\")) | .rubricText" \
  "$manifest" > "$manifest_tmp"

if [ ! -s "$rubric_tmp" ]; then
  echo "verify-rubric-text.sh: muster rubric extraction for axis $n was empty" >&2
  exit 1
fi

if [ ! -s "$manifest_tmp" ]; then
  echo "verify-rubric-text.sh: manifest rubricText for ruleId prefix ${rule_id_prefix} was empty (no matching rule in $manifest?)" >&2
  exit 1
fi

diff "$rubric_tmp" "$manifest_tmp"
