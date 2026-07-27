# Quickstart / Dev Verification: Implement-Loop Coord-Authority Completion

How to reproduce the defect, verify a fix, and run the mission's gates.

## 1. Reproduce (the latent bug)

The defect is latent on existing repo missions (they predate #2106 and still carry coord
`tasks/`). To witness it you must synthesize the post-#2106 coordination shape:

- A mission with `meta.json` declaring a coordination topology (`coordination_branch` set).
- A materialized `-coord` worktree carrying STATUS artifacts only (no `tasks/`,
  no `lanes.json`, no `meta.json`).
- The `tasks/WP*.md` and `lanes.json` on the **primary** checkout.

Then, against that mission:
```bash
spec-kitty agent tasks status --mission <coord-mission>   # FR-001: today → "Tasks directory not found"
spec-kitty agent tasks list   --mission <coord-mission>   # FR-001: same defect
# review auto-find (no WP arg), claimable preview, workspace WP index → husk → degraded/None
```
This shared fixture (FR-014) is the RED-first oracle — **it must not patch the
topology-resolution stack** (the `test_done_bookkeeping_seam.py:353` anti-pattern).

## 2. Verify a routed site

Each routed call site must read PRIMARY and keep its STATUS leg on coord:
```bash
# per-site test: RED against pre-fix code, GREEN after; asserts BOTH legs
PWHEADLESS=1 pytest tests/integration/test_coord_topology_loop_reads.py -q   # (new, FR-014)
```

## 3. Run the architectural gates (the ratchet)

```bash
PWHEADLESS=1 pytest tests/architectural/test_gate_read_literal_ban.py \
                    tests/architectural/test_resolution_authority_gates.py -q
```
Expect: scanner self-test green (inline-shape flagged), `_DIR_READ_KNOWN_RESIDUALS`
in-loop residuals drained / out-of-scope residuals pinned-and-ticketed, routed-canonicalizer
floor raised (strictly below live), permanent allowlist 7→3.

## 4. Full local pre-PR sweep (CI-only shards run locally)

```bash
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider
PWHEADLESS=1 pytest tests/architectural/ tests/integration/ tests/git/ -q   # CI-only shards
pytest tests/architectural/test_no_legacy_terminology.py                     # terminology guard
ruff check . && mypy src/specify_cli
```

## 5. Pre-merge gate-unmask dry-run (NFR-005 — mandatory)

After `spec-kitty merge` (local), BEFORE `gh pr create`, on the **merged** branch:
```bash
PWHEADLESS=1 pytest tests/architectural/test_gate_read_literal_ban.py \
                    tests/architectural/test_resolution_authority_gates.py -v
```
Paste the **verbatim** output into the PR body. The scan widening + floor raises only bite
post-merge, so this is the only place they self-validate (gate-unmask-cannot-self-validate).

## 6. Close-out

- Confirm #2115, #2140, #2183 issue-matrix verdicts terminal.
- Confirm the two FR-015 tracking issues filed under #2160 (sibling mission for the
  merge/lanes `lanes.json` cluster; identity-read-routing ticket) and referenced in their
  `_DIR_READ_KNOWN_RESIDUALS` pins.
