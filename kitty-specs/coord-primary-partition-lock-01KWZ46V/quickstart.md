# Quickstart: Verifying the Coord/Primary Partition Lock

How a reviewer confirms the mission's outcome. All commands run from the repo root.

## 1. The seam is the single access point (C-001, SC-001)

```bash
# The extended ratchet must be green — no un-allow-listed placement bypass remains:
PWHEADLESS=1 pytest tests/architectural/test_no_write_side_rederivation.py -q
PWHEADLESS=1 pytest tests/architectural/test_resolution_authority_gates.py -q

# The new grammar catches a reintroduced bypass (should FAIL if you re-add one):
#   temporarily change mission_creation.py back to CommitTarget(ref=current_branch)
#   → the ratchet goes red. Revert.
```

Expect: allow-list at/below baseline; `coord_authority_baseline` shrunk from 7; the
adopted-module set includes every strangled surface.

## 2. One authority from any working directory (SC-002)

```bash
# The golden-path characterization test (added after PR #2429 lands):
PWHEADLESS=1 pytest tests/integration/test_placement_partition_golden_path.py -q   # (final path may differ)
```

Expect: `create → commit spec → setup-plan → tasks status → decision verify` plus a
lifecycle mutation resolve identical, partition-correct authority from the repo root and
from an unrelated CWD, across a coord-routing and a non-coord mission.

Manual smoke:

```bash
# planning artifact → primary surface; lifecycle → coordination surface (coord mission)
spec-kitty agent tasks status --mission <handle> --json        # from repo root
cd /tmp && spec-kitty agent tasks status --mission <handle> --json   # identical result
```

## 3. Bugs closed (SC-003)

```bash
# #2091 — empty-mid8 composition fails loudly, no exit-128 malformed branch:
PWHEADLESS=1 pytest tests/specify_cli/coordination/ -k "mid8 or workspace_guard" -q
# #2250 — never-created coord mission does not report COORDINATION_BRANCH_DELETED:
PWHEADLESS=1 pytest tests/specify_cli/coordination/test_coord_never_created.py -q
```

## 4. Docs & roadmap truth-up (SC-004)

```bash
# No "planning happens in main" for coord missions; terminology guard green:
PWHEADLESS=1 pytest tests/architectural/test_no_legacy_terminology.py -q
grep -rn "planning happens in" AGENTS.md CLAUDE.md || echo "retired ✓"
grep -n "1878" docs/release-goals/3.2.x.md    # whole strangler now under 3.2.x/G2
```

## 5. Quality gates

```bash
ruff check .
mypy src/
# full architectural safety net + affected suites:
PWHEADLESS=1 pytest tests/architectural/ -n auto --dist loadfile -q
```

## Done-when

- Ratchet green with shrunk allow-list + new grammar; characterization test green
  (post-#2429); #2091/#2250 regression tests green and issues closed; docs/roadmap
  updated; `ruff`/`mypy` clean. No new shadow path (SC-005).
