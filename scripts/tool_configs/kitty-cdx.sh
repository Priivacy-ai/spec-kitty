#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

export CODEX_HOME="${REPO_ROOT}/.codex"
CODEX_BIN="$(type -P codex || true)"

if [[ -z "${CODEX_BIN}" ]]; then
  echo "codex executable was not found in PATH" >&2
  exit 127
fi

# Shared Python environment setup for launchers in this repository.
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/python_environment.sh"
activate_python_environment "${REPO_ROOT}"

exec "${CODEX_BIN}" "$@"
