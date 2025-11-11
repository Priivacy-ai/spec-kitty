#!/usr/bin/env bash

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: setup-sandbox.sh [options] <destination>

Bootstrap a fresh Specify sandbox using the local Spec Kitty CLI checkout.

Options:
  -a, --agents LIST       Comma or space separated AI agent keys (default: claude)
  -t, --script-type TYPE  Script variant to generate (sh or ps). Defaults to OS-appropriate.
  --skip-install          Skip reinstalling spec-kitty-cli via uv tool install
  --reset                 Remove the destination directory before bootstrapping
  -h, --help              Show this message and exit

Example:
  scripts/bash/setup-sandbox.sh --agents claude,copilot ~/Code/new_specify
EOF
}

DESTINATION=""
AGENTS="claude"
SCRIPT_TYPE=""
SKIP_INSTALL=false
RESET=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        -a|--agents)
            [[ $# -lt 2 ]] && { echo "Error: --agents requires a value" >&2; exit 1; }
            AGENTS="$2"
            shift 2
            ;;
        -t|--script-type)
            [[ $# -lt 2 ]] && { echo "Error: --script-type requires a value" >&2; exit 1; }
            SCRIPT_TYPE="$2"
            shift 2
            ;;
        --skip-install)
            SKIP_INSTALL=true
            shift
            ;;
        --reset)
            RESET=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
        *)
            if [[ -z "$DESTINATION" ]]; then
                DESTINATION="$1"
            else
                echo "Error: multiple destination paths provided" >&2
                usage
                exit 1
            fi
            shift
            ;;
    esac
done

if [[ -z "$DESTINATION" ]]; then
    echo "Error: destination is required" >&2
    usage
    exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is required but not found in PATH" >&2
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYPROJECT="$REPO_ROOT/pyproject.toml"
if [[ ! -f "$PYPROJECT" ]]; then
    echo "Error: pyproject.toml not found at $PYPROJECT" >&2
    exit 1
fi

if [[ -z "${UV_CACHE_DIR:-}" ]]; then
    export UV_CACHE_DIR="$REPO_ROOT/.uv-cache"
fi
mkdir -p "$UV_CACHE_DIR"

if [[ -z "${UV_TOOL_DIR:-}" ]]; then
    export UV_TOOL_DIR="$REPO_ROOT/.uv-tools"
fi
mkdir -p "$UV_TOOL_DIR"

# Determine CLI version from pyproject.toml to avoid stale cached wheels.
CLI_VERSION="$(grep -E '^version = \"' "$PYPROJECT" | head -n1 | sed -E 's/^version = \"([^\"]+)\"/\1/')"
if [[ -z "$CLI_VERSION" ]]; then
    echo "Error: could not parse version from pyproject.toml" >&2
    exit 1
fi

if [[ -z "$SCRIPT_TYPE" ]]; then
    case "${OSTYPE:-}" in
        msys*|cygwin*|win*)
            SCRIPT_TYPE="ps"
            ;;
        *)
            SCRIPT_TYPE="sh"
            ;;
    esac
fi

if [[ "$SCRIPT_TYPE" != "sh" && "$SCRIPT_TYPE" != "ps" ]]; then
    echo "Error: --script-type must be 'sh' or 'ps'" >&2
    exit 1
fi

DEST_ABS="$(cd "$(dirname "$DESTINATION")" && pwd)/$(basename "$DESTINATION")"

if [[ -e "$DEST_ABS" ]]; then
    if [[ "$RESET" == true ]]; then
        echo "Resetting existing destination: $DEST_ABS"
        if command -v chflags >/dev/null 2>&1; then
            chflags -R nouchg "$DEST_ABS" 2>/dev/null || true
        fi
        chmod -R u+w "$DEST_ABS" 2>/dev/null || true
        rm -rf "$DEST_ABS" 2>/dev/null || true
        if [[ -e "$DEST_ABS" ]]; then
            echo "Error: failed to remove $DEST_ABS. Check permissions or remove manually." >&2
            exit 1
        fi
    else
        echo "Error: $DEST_ABS already exists. Use --reset to remove it first." >&2
        exit 1
    fi
fi

mkdir -p "$(dirname "$DEST_ABS")"

if [[ "$SKIP_INSTALL" != true ]]; then
    echo "Installing spec-kitty-cli (version $CLI_VERSION) from $REPO_ROOT"
    set +e
    uv tool install --from "$REPO_ROOT" spec-kitty-cli --force
    install_status=$?
    set -e
    if [[ $install_status -ne 0 ]]; then
        if command -v spec-kitty >/dev/null 2>&1; then
            echo "Warning: spec-kitty-cli install failed (exit $install_status); existing installation will be reused." >&2
        else
            echo "Error: spec-kitty-cli install failed (exit $install_status) and no existing spec-kitty command was found. Re-run with --skip-install after installing manually." >&2
            exit 1
        fi
    fi
else
    echo "Skipping spec-kitty-cli installation per request"
fi

export SPEC_KITTY_TEMPLATE_ROOT="$REPO_ROOT"

if ! command -v spec-kitty >/dev/null 2>&1; then
    echo "Error: spec-kitty executable not found in PATH. Install spec-kitty-cli or rerun without --skip-install." >&2
    exit 1
fi

# Normalise agent list: allow comma or space separated values.
IFS=',' read -r -a agent_parts <<<"${AGENTS// /,}"
NORMALISED_AGENTS="$(printf "%s," "${agent_parts[@]}")"
NORMALISED_AGENTS="${NORMALISED_AGENTS%,}"

echo "Bootstrapping sandbox at $DEST_ABS (agents: $NORMALISED_AGENTS, script: $SCRIPT_TYPE)"
spec-kitty init "$DEST_ABS" --ai "$NORMALISED_AGENTS" --script "$SCRIPT_TYPE"

echo
echo "Sandbox ready at $DEST_ABS"
echo "Template root used: $SPEC_KITTY_TEMPLATE_ROOT"
