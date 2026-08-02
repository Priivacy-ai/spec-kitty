#!/usr/bin/env bash
# extract-rubric-section.sh -- line-anchored extraction of one
# <RUBRIC>...</RUBRIC> block's *body* (the tags themselves are never
# printed) from muster's spec-kitty-profile behavioral-axes rubric doc.
#
# Supersedes the broken substring-counting form
# (`awk '/<RUBRIC>/{c++} c==n && ... {print} /<\/RUBRIC>/{if(c==n) exit}'`)
# that appears only in this suite's commit history (`cbc4851e3`) and in
# WP01's own task-file Validation section -- never as a committed, runnable
# artifact. That form over-counts: muster's rubric doc mentions the literal
# substring "<RUBRIC>" nine times in its Introduction/Integration-Contract
# prose before the four real fenced blocks even start (prose always embeds
# the substring mid-sentence, e.g. "...between <RUBRIC> tags..."), so
# counting *occurrences of the substring* lands inside prose, not inside the
# Nth real block, for every n. This form instead anchors on the tag
# appearing ALONE on its own line (`^<RUBRIC>$` / `^</RUBRIC>$`), which
# holds for all four real fenced blocks and never for a prose mention.
#
# Usage: extract-rubric-section.sh <n> <muster-checkout>
#   n               axis number, 1-4:
#                     1 = Avoidance-Boundary Adherence
#                     2 = Domain-Scope Containment
#                     3 = Handoff Discipline
#                     4 = Canonical-Verb Usage
#   muster-checkout path to a muster checkout (or worktree) containing
#                   docs/rubric/spec-kitty-behavioral-axes.md
#
# Prints the Nth <RUBRIC>...</RUBRIC> block's body to stdout. Exits non-zero
# if the doc is missing, unreadable, or fewer than n blocks are found.
set -euo pipefail

n="${1:?usage: extract-rubric-section.sh <n:1-4> <muster-checkout>}"
checkout="${2:?usage: extract-rubric-section.sh <n:1-4> <muster-checkout>}"
doc="$checkout/docs/rubric/spec-kitty-behavioral-axes.md"

if [ ! -f "$doc" ]; then
  echo "extract-rubric-section.sh: rubric doc not found: $doc" >&2
  exit 1
fi

output="$(awk -v n="$n" '
  /^<RUBRIC>$/   { c++; next }
  /^<\/RUBRIC>$/ { if (c == n) { found = 1; exit } next }
  c == n         { print }
  END            { if (!found) exit 1 }
' "$doc")"

if [ -z "$output" ]; then
  echo "extract-rubric-section.sh: block $n not found or empty in $doc" >&2
  exit 1
fi

printf '%s\n' "$output"
