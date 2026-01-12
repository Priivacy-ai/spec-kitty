#!/usr/bin/env bash
set -euo pipefail

cat <<'MSG'
Manual Test: Constitution Comprehensive Path

1) Create a fresh project:
   mkdir -p /tmp/test-comprehensive
   cd /tmp/test-comprehensive
   git init
   spec-kitty init

2) Run /spec-kitty.constitution in your agent session.
   Choose: C (comprehensive)
   Complete all phases (8-12 questions)
   Confirm: A (write it)

3) Verify output:
   wc -l .kittify/memory/constitution.md
   Expected: ~150-200 lines

4) Record elapsed time (target: < 300s)
MSG

exit 0
