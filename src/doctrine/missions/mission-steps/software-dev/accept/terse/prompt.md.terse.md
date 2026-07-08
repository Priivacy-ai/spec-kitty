<!-- tersifier:source-sha256=d64095852e6334d9ca59f96db27e9ee936b7638222a5100332f0a707b2163a7e -->
---
description: Validate an approved mission before merge
---
# /spec-kitty.accept - Validate Mission Readiness

**Version**: 0.12.0+

## Purpose

Validate every WP complete + mission ready to merge: run acceptance gate, surface blocking diagnostics, clear path to merge once gate passes.

---

## 📍 WORKING DIRECTORY: Run from the MAIN repository

**IMPORTANT**: run from primary repo checkout root, NOT a work-package worktree.

```bash
# If you are inside a worktree, return to the main checkout first:
cd $(git rev-parse --show-toplevel)
```

Multi-mission repos: always pass `--mission <handle>` to every spec-kitty command. `<handle>` = mission_id (ULID), mid8 (first 8 chars), or mission_slug. Resolver disambiguates by mission_id; ambiguity -> structured `MISSION_AMBIGUOUS_SELECTOR` error, no silent fallback.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Steps

### 1. Run the Acceptance Gate

From repo root:

```bash
spec-kitty accept --mission <handle>
```

Validates all WPs `approved`/`done`, checks readiness gates, reports what still blocks merge.

### 2. Inspect Acceptance Diagnostics

Read output:

- Gate **passes** -> confirms ready to merge + prints merge instructions.
- Gate **fails** -> lists each outstanding category (unapproved WPs, failing checks, unresolved review feedback). Every outstanding item = blocker.

### 3. Resolve Any Gate Failures

Per blocker:

- Route affected WP back through implement/review.
- Re-run relevant tests/checks until pass.
- Re-run `spec-kitty accept --mission <handle>`; confirm gate clean. Do **not** force acceptance past an unresolved blocker.

### 4. Proceed to Merge

Only after gate passes:

```bash
spec-kitty merge --mission <handle>
```

Follow merge instructions printed by acceptance command (+ any cleanup steps).

## Output

After this step:

- Acceptance gate passed for `<handle>`.
- Blocking diagnostics resolved (or none present).
- Merge instructions surfaced to operator.

**Next step**: `spec-kitty next --agent <name>` advances to merge, or run `spec-kitty merge --mission <handle>` directly.
