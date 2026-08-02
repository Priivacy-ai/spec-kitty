#!/usr/bin/env bash
# check-persona-drift.sh — FR-003 persona-drift gate (WP01/T005, lane-a owned).
#
# Regenerates both committed personas from their source built-in agent
# profiles into a throwaway temp directory (never touching the working
# tree's committed copies), then uses `git diff --no-index --exit-code` to
# compare each regenerated file against its committed counterpart under
# conformance/crosslayer/personas/. Exits 0 when both personas are
# drift-free; exits non-zero the moment either persona differs from what
# profile2soul.py would produce right now from the same source profile.
#
# Invocation contract: no arguments, no environment variables. Must work
# from a bare `bash conformance/scripts/check-persona-drift.sh` run from
# any directory (WP04's crosslayer.yml calls it exactly this way, from the
# repo root). This script never mutates the working tree — the committed
# persona files under conformance/crosslayer/personas/ are only ever read.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"
cd "${repo_root}"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "${tmp_dir}"' EXIT

personas=(
  "architect-alphonso"
  "reviewer-renata"
)

status=0
for persona in "${personas[@]}"; do
  source_profile="packs/built-in/agent_profiles/${persona}.agent.yaml"
  committed="conformance/crosslayer/personas/${persona}.Soul.md"
  regenerated="${tmp_dir}/${persona}.Soul.md"

  python3 conformance/tools/profile2soul.py "${source_profile}" > "${regenerated}"

  if ! git diff --no-index --exit-code "${committed}" "${regenerated}"; then
    echo "DRIFT DETECTED: ${committed} differs from a fresh profile2soul.py regeneration" >&2
    status=1
  fi
done

exit "${status}"
