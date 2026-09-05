#!/usr/bin/env bash
# check-sop-extract-drift.sh — FR-007 SOP-extract drift gate.
#
# Mirrors FR-003's persona-drift pattern (see
# conformance/scripts/check-persona-drift.sh, lane-a): re-extract the same
# source sections from the shared, read-only repo-root AGENTS.md into a
# scratch file, then `git diff --exit-code` that fresh extraction against
# whatever is currently on disk at conformance/crosslayer/sop-extract.md.
#
# Deliberately does NOT overwrite the committed sop-extract.md before
# comparing: an overwrite-then-diff order would silently erase the exact
# drift (a hand-edit, or any other divergence) it is trying to detect,
# since the freshly regenerated content would already match AGENTS.md by
# construction and a subsequent `git diff` against the (now-overwritten)
# working tree would report clean regardless of what was there before.
# Comparing the untouched on-disk file against a separate fresh-extraction
# scratch copy (via `git diff --no-index`, which works on two arbitrary
# paths regardless of git-tracked/staged status) catches any divergence —
# first line, last line, or anywhere in between — without that self-healing
# blind spot.
#
#   - Clean (on-disk extract matches a fresh re-extraction of AGENTS.md):
#     exit 0.
#   - Drift (on-disk extract does not match): exit 1. AGENTS.md itself is
#     never written by this script — only read.
#
# The extraction rule below (heading list + boundary semantics) MUST match
# the "Extraction rule" comment documented in the header of
# conformance/crosslayer/sop-extract.md exactly — that header and this
# script are two views of the same mechanical rule, not independent
# judgment calls.
#
# Usage:
#   bash conformance/scripts/check-sop-extract-drift.sh            # default: read-only drift check (bare repo-root invocation, no arguments)
#   bash conformance/scripts/check-sop-extract-drift.sh --write     # regenerate sop-extract.md in place from AGENTS.md, then exit 0
#
# --write is the supported remedy for a legitimate AGENTS.md edit: it
# overwrites the committed extract with a fresh re-extraction and exits 0
# unconditionally (regenerating IS the point of this mode, so there is
# nothing left to report as drift). The default (no-argument) invocation
# is UNCHANGED by this flag's existence: it stays strictly read-only and
# never reaches the write branch below on its own. WP04's CI call site
# must keep invoking this script with no arguments — --write must never
# become reachable during a normal CI run, or the gate would silently
# repair drift instead of reporting it (the defect this design already
# avoided once, see the header note above).

set -euo pipefail

# --help is deliberately NOT special-cased here: it falls into the
# unknown-argument branch below and exits 1 (fail-closed) rather than
# printing usage and exiting 0. Left this way on purpose — this is a
# narrow, one-flag internal remediation script, not a general CLI, and
# the fail-closed default for any unrecognized argument is one of the
# guards this WP's review already exercised and accepted (bare `--help`
# among the twelve accidental-invocation attempts verified to fail
# closed). Making --help a documented success path would be a new,
# untested behavior change for no required benefit; the usage message
# is still printed either way, just on a nonzero exit.
WRITE_MODE=0
if [[ $# -gt 0 ]]; then
  if [[ "$1" == "--write" ]]; then
    WRITE_MODE=1
    shift
  else
    echo "check-sop-extract-drift: unknown argument: $1" >&2
    echo "Usage: $(basename "${BASH_SOURCE[0]}") [--write]" >&2
    exit 1
  fi
fi
if [[ $# -gt 0 ]]; then
  echo "check-sop-extract-drift: unexpected extra argument(s): $*" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AGENTS_FILE="${REPO_ROOT}/AGENTS.md"
EXTRACT_FILE="${REPO_ROOT}/conformance/crosslayer/sop-extract.md"

# Ordered list of AGENTS.md "## " headings this extract covers. Order here
# is the order sections appear in the regenerated sop-extract.md.
HEADINGS=(
  "## ⚠️ CRITICAL: Git Workflow — No Direct Pushes to origin/main"
  "## Branch Protection and CI"
)

if [[ ! -r "${AGENTS_FILE}" ]]; then
  echo "check-sop-extract-drift: source file not found or not readable: ${AGENTS_FILE}" >&2
  exit 1
fi

if [[ ! -f "${EXTRACT_FILE}" ]]; then
  echo "check-sop-extract-drift: committed extract not found: ${EXTRACT_FILE}" >&2
  exit 1
fi

# Extract one section: every line from the exact heading line (inclusive)
# through the line immediately before the next line that is exactly "---"
# (AGENTS.md's own horizontal-rule section separator), exclusive of that
# "---" line itself.
#
# Fails loudly (non-zero, message naming the missing heading) if the heading
# never matches a line in AGENTS.md — e.g. it was renamed. Without this
# check, a renamed heading silently produces an empty section: `awk` prints
# nothing when `$0 == heading` never fires, and callers (both the default
# check and --write's `regenerate`) would otherwise have no way to tell
# "heading not found" apart from "heading found, section legitimately
# empty".
extract_section() {
  local heading="$1"
  if ! awk -v heading="${heading}" '
    $0 == heading { inside = 1; found = 1 }
    inside {
      if ($0 == "---") { exit }
      print
    }
    END { exit (found ? 0 : 1) }
  ' "${AGENTS_FILE}"; then
    echo "check-sop-extract-drift: heading not found in ${AGENTS_FILE}: ${heading}" >&2
    return 1
  fi
}

regenerate() {
  cat <<'HEADER_EOF'
<!--
SOP policy extract (FR-007, OQ-6 option (b)).

This file is a bounded, verbatim subset of the repo-root AGENTS.md's
operating-policy sections — small enough to sit alongside a persona and a
skill in a composed context window without the small-model risk the full
file (35,933 bytes at this mission's base commit) would pose. AGENTS.md
itself is a shared, read-only input; neither this extract nor its drift
check ever modifies it.

Extraction rule (must match conformance/scripts/check-sop-extract-drift.sh
exactly, mechanical and re-run-able by that script, not a judgment call
re-made by hand): for each AGENTS.md heading listed below, in order, every
line from the heading (inclusive) through the line immediately before the
next line that is exactly "---" (AGENTS.md's own section-separator
convention) is extracted verbatim, excluding that "---" line itself.

Sections extracted (in AGENTS.md heading order):
  1. "## ⚠️ CRITICAL: Git Workflow — No Direct Pushes to origin/main"
  2. "## Branch Protection and CI"

Regenerate with: bash conformance/scripts/check-sop-extract-drift.sh --write
-->

HEADER_EOF
  local first=1
  for heading in "${HEADINGS[@]}"; do
    if [[ ${first} -eq 0 ]]; then
      printf '\n'
    fi
    extract_section "${heading}"
    first=0
  done
}

if [[ "${WRITE_MODE}" -eq 1 ]]; then
  # --write is the only branch that ever touches EXTRACT_FILE. It is reached
  # solely via the explicit `--write` argument parsed above — the default,
  # argument-less invocation (WP04's CI call site) can never take this path.
  #
  # regenerate() is built into a scratch temp file first, and only moved
  # over EXTRACT_FILE on success. This matters because a redirect straight
  # into EXTRACT_FILE (`regenerate > "${EXTRACT_FILE}"`) truncates the
  # destination the moment the redirection opens, before `regenerate` has
  # produced a single byte — so if extract_section fails partway (e.g. a
  # renamed heading, see above), the committed extract would be left
  # half-overwritten instead of merely reporting an error. Building in a
  # scratch file first means a failure here leaves EXTRACT_FILE completely
  # untouched.
  #
  # The scratch file is created BESIDE EXTRACT_FILE (same directory, hence
  # same filesystem) rather than under ${TMPDIR:-/tmp}, so the final `mv` is
  # a real same-device `rename(2)` — an atomic pointer swap — instead of a
  # cross-device copy-then-unlink. A cross-device `mv` is not atomic: a
  # process killed mid-copy can leave EXTRACT_FILE truncated or partially
  # written, which the scratch-file approach above is specifically meant to
  # prevent. `chmod --reference` restores EXTRACT_FILE's existing mode onto
  # the scratch file before the move regardless of filesystem: `mktemp`
  # always creates its file `0600`, and since `mv`/`rename(2)` never changes
  # the mode of the inode being moved, that `0600` would otherwise carry
  # straight onto the destination on every successful --write — silently
  # regressing a git-tracked-644 extract to 600 (invisible to `git status`,
  # since git tracks only the executable bit) even though nothing here is
  # cross-device.
  WRITE_TMP_FILE="$(mktemp "${EXTRACT_FILE}.XXXXXX")"
  trap 'rm -f "${WRITE_TMP_FILE}"' EXIT
  regenerate > "${WRITE_TMP_FILE}"
  chmod --reference="${EXTRACT_FILE}" "${WRITE_TMP_FILE}"
  mv "${WRITE_TMP_FILE}" "${EXTRACT_FILE}"
  echo "check-sop-extract-drift: regenerated ${EXTRACT_FILE} from AGENTS.md" >&2
  exit 0
fi

TMP_FILE="$(mktemp "${TMPDIR:-/tmp}/sop-extract-fresh.XXXXXX")"
trap 'rm -f "${TMP_FILE}"' EXIT

regenerate > "${TMP_FILE}"

git diff --no-index --exit-code -- "${EXTRACT_FILE}" "${TMP_FILE}"
