#!/usr/bin/env bash
set -euo pipefail

# Activate a repository-local Python virtual environment when available.
# Usage:
#   source scripts/tool_configs/python_environment.sh
#   activate_python_environment "/path/to/repo"
activate_python_environment() {
  local repo_root="${1:-$(pwd)}"
  local venv_dir="${repo_root}/.venv"
  local activate_script="${venv_dir}/bin/activate"

  if [[ -f "${activate_script}" ]]; then
    # shellcheck disable=SC1090
    set +u
    . "${activate_script}"
    set -u
  fi
}
