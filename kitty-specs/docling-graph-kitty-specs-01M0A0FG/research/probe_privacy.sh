#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 PYTHON PRIVACY_CANDIDATE OUTPUT_DIRECTORY" >&2
  exit 2
fi

umask 077
python_bin=$1
candidate=$2
output_dir=$3
mkdir -p "$output_dir"
output_dir=$(cd "$output_dir" && pwd -P)
probe_dir=$(mktemp -d "${TMPDIR:-/tmp}/docling-privacy.XXXXXX")
trap 'rm -rf "$probe_dir"' EXIT
chmod 700 "$probe_dir"
mkdir -m 700 "$probe_dir/tmp" "$probe_dir/cache" "$probe_dir/hf" "$probe_dir/docling-cache"

content_canary='SPK_CONTENT_CANARY_01M0A0FG'
path_canary='SPK_PATH_CANARY_01M0A0FG'
env_canary='SPK_ENV_CANARY_01M0A0FG'
network_status='UNKNOWN:no_sandbox_exec'
filesystem_status='UNKNOWN:no_sandbox_exec'
sandbox_prefix=()
if command -v sandbox-exec >/dev/null 2>&1; then
  sandbox_profile="$probe_dir/sandbox.sb"
  sed -e "s|@PROBE_DIR@|$probe_dir|g" -e "s|@OUTPUT_DIR@|$output_dir|g" >"$sandbox_profile" <<'EOF'
(version 1)
(allow default)
(deny network*)
(deny file-write*)
(allow file-write* (subpath "@PROBE_DIR@"))
(allow file-write* (subpath "@OUTPUT_DIR@"))
EOF
  chmod 600 "$sandbox_profile"
  sandbox_prefix=(sandbox-exec -f "$sandbox_profile")
  network_status='ENFORCED:sandbox_exec_deny_network'
  filesystem_status='ENFORCED:sandbox_exec_write_confinement'
fi

: >"$output_dir/execution-contract-failures.txt"

run_candidate() {
  local mode=$1
  local fixture_dir="$probe_dir/$path_canary-$mode"
  local fixture="$fixture_dir/canary.md"
  mkdir -m 700 "$fixture_dir"
  printf '%s\n' "# Privacy fixture" "$content_canary" >"$fixture"
  chmod 600 "$fixture"
  set +e
  env -i \
    PATH="$PATH" \
    TMPDIR="$probe_dir/tmp" \
    XDG_CACHE_HOME="$probe_dir/cache" \
    HF_HOME="$probe_dir/hf" \
    DOCLING_CACHE_DIR="$probe_dir/docling-cache" \
    NO_PROXY='' \
    HTTP_PROXY='http://127.0.0.1:9' \
    HTTPS_PROXY='http://127.0.0.1:9' \
    OPENAI_API_KEY='POISON_NO_REMOTE_PROVIDER' \
    ANTHROPIC_API_KEY='POISON_NO_REMOTE_PROVIDER' \
    SPEC_KITTY_RESEARCH_CANARY="$env_canary" \
    "${sandbox_prefix[@]}" "$python_bin" "$candidate" --input "$fixture" --mode "$mode" \
    >"$output_dir/$mode.stdout.txt" 2>"$output_dir/$mode.stderr.txt" &
  local child_pid=$!
  local ready_seen='no'
  if [[ "$mode" == "wait" ]]; then
    for _ in 1 2 3 4 5 6 7 8 9 10; do
      if rg -q 'READY_FOR_SIGTERM' "$output_dir/$mode.stdout.txt" 2>/dev/null; then
        ready_seen='yes'
        break
      fi
      sleep 1
    done
    kill -TERM "$child_pid" 2>/dev/null || true
  fi
  wait "$child_pid"
  local status=$?
  set -e
  printf '%s\n' "$status" >"$output_dir/$mode.exit-status.txt"
  if ! rg -q '"conversion_complete": true' "$output_dir/$mode.stdout.txt"; then
    printf '%s\n' "$mode:missing_conversion_complete" >>"$output_dir/execution-contract-failures.txt"
  fi
  case "$mode" in
    normal)
      if [[ "$status" -ne 0 ]]; then
        printf '%s\n' "$mode:unexpected_exit_$status" >>"$output_dir/execution-contract-failures.txt"
      fi
      ;;
    exception)
      if [[ "$status" -eq 0 ]]; then
        printf '%s\n' "$mode:expected_nonzero_exit" >>"$output_dir/execution-contract-failures.txt"
      fi
      ;;
    wait)
      if [[ "$ready_seen" != 'yes' ]]; then
        printf '%s\n' "$mode:missing_ready_marker" >>"$output_dir/execution-contract-failures.txt"
      fi
      if [[ "$status" -eq 0 ]]; then
        printf '%s\n' "$mode:expected_signal_exit" >>"$output_dir/execution-contract-failures.txt"
      fi
      ;;
  esac
  rm -f "$fixture"
  rmdir "$fixture_dir" 2>/dev/null || true
}

run_candidate normal
run_candidate exception
run_candidate wait

printf '%s\n' "$network_status" >"$output_dir/network-proof-status.txt"
printf '%s\n' "$filesystem_status" >"$output_dir/filesystem-proof-status.txt"
find "$probe_dir" -type f -perm -004 -print >"$output_dir/world-readable-residue.txt"
find "$probe_dir" -type f -print0 | xargs -0 stat -f '%Sp %N' >"$output_dir/residue-modes.txt"

: >"$output_dir/canary-residue-hits.txt"
scan_roots=("$probe_dir")
for mode in normal exception wait; do
  scan_roots+=("$output_dir/$mode.stdout.txt" "$output_dir/$mode.stderr.txt")
done
for value in "$content_canary" "$path_canary" "$env_canary"; do
  encoded=$($python_bin -c 'import base64,sys; print(base64.b64encode(sys.argv[1].encode()).decode())' "$value")
  url_encoded=$($python_bin -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$value")
  json_encoded=$($python_bin -c 'import json,sys; print(json.dumps(sys.argv[1])[1:-1])' "$value")
  for variant in "$value" "$encoded" "$url_encoded" "$json_encoded"; do
    rg -a -l --fixed-strings "$variant" "${scan_roots[@]}" >>"$output_dir/canary-residue-hits.txt" || true
  done
done
sort -u -o "$output_dir/canary-residue-hits.txt" "$output_dir/canary-residue-hits.txt"

if [[ -s "$output_dir/execution-contract-failures.txt" || -s "$output_dir/canary-residue-hits.txt" || -s "$output_dir/world-readable-residue.txt" ]]; then
  printf '%s\n' 'FAIL' >"$output_dir/privacy-gate-status.txt"
elif [[ "$network_status" == ENFORCED:* && "$filesystem_status" == ENFORCED:* ]]; then
  printf '%s\n' 'PASS' >"$output_dir/privacy-gate-status.txt"
else
  printf '%s\n' 'UNKNOWN' >"$output_dir/privacy-gate-status.txt"
fi
