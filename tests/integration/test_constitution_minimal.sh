#!/usr/bin/env bash
set -euo pipefail

cat <<'MSG'
Manual Test: Constitution Minimal Path

1) Create a fresh project:
   mkdir -p /tmp/test-minimal
   cd /tmp/test-minimal
   git init
   spec-kitty init

2) Run /spec-kitty.constitution in your agent session.
   Choose: B (minimal)
   Answer Phase 1 questions (4 total)
   Confirm: A (write it)

3) Verify output:
   wc -l .kittify/memory/constitution.md
   Expected: ~50-80 lines

4) Record elapsed time (target: < 120s)
MSG

exit 0
