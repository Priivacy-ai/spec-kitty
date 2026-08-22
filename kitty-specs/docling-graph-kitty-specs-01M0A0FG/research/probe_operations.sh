#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 DOCLING_GRAPH_SOURCE OUTPUT_DIRECTORY" >&2
  exit 2
fi

source_dir=$(cd "$1" && pwd)
output_dir=$2
mkdir -p "$output_dir"
probe_dir=$(mktemp -d "${TMPDIR:-/tmp}/docling-operations.XXXXXX")
trap 'rm -rf "$probe_dir"' EXIT

uname -a >"$output_dir/uname.txt"
sw_vers >"$output_dir/sw-vers.txt"
python3 --version >"$output_dir/system-python.txt" 2>&1
uv --version >"$output_dir/uv-version.txt"

/usr/bin/time -lp uv venv --python 3.11 "$probe_dir/env" 2>"$output_dir/venv-time.txt"
before_bytes=$(du -sk "$probe_dir/env" | awk '{print $1 * 1024}')
/usr/bin/time -lp uv pip install --python "$probe_dir/env/bin/python" "$source_dir" \
  >"$output_dir/install-stdout.txt" 2>"$output_dir/install-time.txt"
after_bytes=$(du -sk "$probe_dir/env" | awk '{print $1 * 1024}')
printf '%s\n' "$before_bytes" >"$output_dir/venv-before-bytes.txt"
printf '%s\n' "$after_bytes" >"$output_dir/venv-after-bytes.txt"
printf '%s\n' "$((after_bytes - before_bytes))" >"$output_dir/install-delta-bytes.txt"
uv pip list --python "$probe_dir/env/bin/python" --format json >"$output_dir/packages.json"

for run in 1 2 3 4 5; do
  /usr/bin/time -lp "$probe_dir/env/bin/python" -c 'import docling_graph' \
    >"$output_dir/import-${run}.stdout.txt" 2>"$output_dir/import-${run}.time.txt"
  /usr/bin/time -lp "$probe_dir/env/bin/docling-graph" --version \
    >"$output_dir/version-${run}.stdout.txt" 2>"$output_dir/version-${run}.time.txt"
done

env -i PATH="$PATH" NO_PROXY='*' HTTP_PROXY='http://127.0.0.1:9' HTTPS_PROXY='http://127.0.0.1:9' \
  "$probe_dir/env/bin/docling-graph" --version >"$output_dir/offline-version.txt" 2>&1

uvx --from pip-audit pip-audit --path "$probe_dir/env/lib/python3.11/site-packages" \
  --format json >"$output_dir/pip-audit.json" 2>"$output_dir/pip-audit.stderr.txt" || true
uvx --from pip-licenses pip-licenses --python "$probe_dir/env/bin/python" --format=json \
  >"$output_dir/licenses.json" 2>"$output_dir/licenses.stderr.txt" || true

uv pip uninstall --python "$probe_dir/env/bin/python" docling-graph \
  >"$output_dir/uninstall.txt" 2>&1
find "$probe_dir/env" -iname '*docling_graph*' -o -iname '*docling-graph*' \
  >"$output_dir/uninstall-residue.txt"
