# Tasks: Charter & Sync Sonar Remediation

**Mission**: `charter-sync-sonar-remediation-01KZPPZW` | **Branch**: `fix/charter-sync-sonar-remediation`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Findings inventory (authoritative, per file:line)**: scratchpad `charter-sync-sonar-findings.txt`, or refetch
per WP via the Sonar API.

6 WPs, split by **file-group (disjoint owners)** — each WP fixes ALL Sonar findings in the files it owns,
so no two WPs touch the same file. All behavior-preserving; no new suppressions (NFR-002). 6 parallel lanes.

**Standard playbook (all WPs)** — reuse the #3232 doctrine-sweep discipline:
- `S1192` dup-literal → one descriptively-named `UPPER_SNAKE` module constant referenced at all sites.
- `S3776` complexity → extract deterministic tested helpers to reach ≤15 (ruff `C901`); read+run the
  function's existing tests before/after; add a characterization test first if coverage is thin; document a
  residual only if ≤15 is genuinely unreachable (inline rationale, NOT a suppression).
- `S7632` malformed suppression comment → fix its syntax (keep the code + a one-line rationale) if the
  suppression is genuinely needed; otherwise REMOVE it. Never leave a malformed/no-op suppression. Do NOT
  let an explanatory comment contain a `# noqa:` literal (ruff will re-flag it).
- `S1172` unused param → remove it (or `_`-prefix if a signature contract requires the slot).
- `S107` too-many-params → group into a small dataclass/params object or keyword-only, behavior-preserving.
- `S6353` → `\w` **with explicit `re.ASCII`** if the original was ASCII-only (see #3232 WP04).
- Every regex change (`S8786`, `S6353`) proven match-equivalent by a test.
- Gates per WP: `ruff check` (incl `C901`) + `mypy` + the touched modules' existing tests + new helper tests, all green.

## Subtask Index (per WP; tracked via `mark-status`)

| ID | WP | Scope |
|----|----|-------|
| T001 | WP01 | Simplify the `S8786` ReDoS regex in `token_budget.py:308` + characterization test; reduce its `S3776:365` (28) |
| T002 | WP02 | Charter complexity group A (6 files) → ≤15 + tested helpers; fold their S1192/S7632 |
| T003 | WP03 | Charter complexity group B (11 files) → ≤15 + tested helpers; fold their S1192/S7632/S3516/S1172 |
| T004 | WP04 | Charter mechanical (12 files): S1192 + S7632 + S1172 + S5890 |
| T005 | WP05 | Sync complexity (7 files) → ≤15 + tested helpers; fold their S7632/S1172/S8572 |
| T006 | WP06 | Sync mechanical (12 files): S1192 + S7632 + S107 + S5713 + S5779 + S6353 + S7503 + S1172 |

---

## WP01 — Charter ReDoS BLOCKER + token_budget
**Prompt**: [tasks/WP01-charter-redos-blocker.md](./tasks/WP01-charter-redos-blocker.md) | **Req**: FR-001, FR-002, NFR-001, NFR-003, C-001 | Priority P1 (the BLOCKER).

## WP02 — Charter complexity group A
**Prompt**: [tasks/WP02-charter-complexity-a.md](./tasks/WP02-charter-complexity-a.md) | **Req**: FR-002, FR-003, FR-004, NFR-001.

## WP03 — Charter complexity group B
**Prompt**: [tasks/WP03-charter-complexity-b.md](./tasks/WP03-charter-complexity-b.md) | **Req**: FR-002, FR-003, FR-004, FR-005, NFR-001.

## WP04 — Charter mechanical
**Prompt**: [tasks/WP04-charter-mechanical.md](./tasks/WP04-charter-mechanical.md) | **Req**: FR-003, FR-004, FR-005, NFR-002.

## WP05 — Sync complexity
**Prompt**: [tasks/WP05-sync-complexity.md](./tasks/WP05-sync-complexity.md) | **Req**: FR-006, FR-008, FR-009, NFR-001.

## WP06 — Sync mechanical
**Prompt**: [tasks/WP06-sync-mechanical.md](./tasks/WP06-sync-mechanical.md) | **Req**: FR-007, FR-008, FR-009, NFR-002.

## MVP scope
WP01 (the ReDoS BLOCKER) is the highest-value item. The rest is maintainability cleanup across 5 parallel lanes.
