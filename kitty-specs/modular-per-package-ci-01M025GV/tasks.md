# Tasks: Modular per-package CI + automated asset/prompt regeneration

**Mission**: `modular-per-package-ci-01M025GV` | **Branch**: `mission/modular-per-package-ci`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

Work-package prompt files live in [`tasks/`](./tasks/). Status is tracked in `status.events.jsonl`.

## Work packages

| WP | Title | Phase | Dependencies | Requirements |
|----|-------|-------|--------------|--------------|
| [WP01](./tasks/WP01-kernel-reusable-workflow-poc.md) | Kernel reusable-workflow POC + coverage-aggregation proof | Phase 1 – POC | — | FR-001, FR-002, NFR-001/002, C-004/005 |
| [WP02](./tasks/WP02-regen-tool-shared-version-pins.md) | Standalone regen tool + shared version pins | Phase 1 – Tooling | — | FR-003/004/005, NFR-004/005, C-006 |
| [WP03](./tasks/WP03-doctrine-packs-workflows-guards.md) | Doctrine + packs reusable workflows + CI-model guard updates | Phase 2 – Generalize | WP01 | FR-006/007/008, NFR-001, C-004 |
| [WP04](./tasks/WP04-regen-ci-automation.md) | Trust-tiered regen CI automation | Phase 2 – Automation | WP02 | FR-009/010/011, NFR-003, C-003 |
| [WP05](./tasks/WP05-narrow-drift-gates.md) | Narrow the drift gates to structural invariants + canonical snapshot | Phase 3 – Gate reshape | WP02 | FR-012 |
| [WP06](./tasks/WP06-rehome-completeness-baselines.md) | Re-home completeness baselines to the module partition | Phase 3 – Consolidation | WP03, WP05 | FR-013 |

## Dependency graph

```
WP01 ──▶ WP03 ──┐
                ├─▶ WP06
WP02 ──▶ WP05 ──┘
   └───▶ WP04
```

WP01 and WP02 are the parallel roots. Kernel POC (WP01) is the first slice — prove coverage-into-aggregation
end-to-end before generalizing to doctrine + packs (WP03). The regen tool (WP02) is independently valuable and
gates the automation (WP04) and gate narrowing (WP05). Baseline re-homing (WP06) lands last, once the module
partition (WP03) and gate shape (WP05) are final.

## Work package sections

### WP01 — Kernel reusable-workflow POC + coverage-aggregation proof
Dependencies: none. See [tasks/WP01-kernel-reusable-workflow-poc.md](./tasks/WP01-kernel-reusable-workflow-poc.md).

### WP02 — Standalone regen tool + shared version pins
Dependencies: none. See [tasks/WP02-regen-tool-shared-version-pins.md](./tasks/WP02-regen-tool-shared-version-pins.md).

### WP03 — Doctrine + packs reusable workflows + CI-model guard updates
Dependencies: WP01. See [tasks/WP03-doctrine-packs-workflows-guards.md](./tasks/WP03-doctrine-packs-workflows-guards.md).

### WP04 — Trust-tiered regen CI automation
Dependencies: WP02. See [tasks/WP04-regen-ci-automation.md](./tasks/WP04-regen-ci-automation.md).

### WP05 — Narrow the drift gates to structural invariants + canonical snapshot
Dependencies: WP02. See [tasks/WP05-narrow-drift-gates.md](./tasks/WP05-narrow-drift-gates.md).

### WP06 — Re-home completeness baselines to the module partition
Dependencies: WP03, WP05. See [tasks/WP06-rehome-completeness-baselines.md](./tasks/WP06-rehome-completeness-baselines.md).

## Execution notes

- Every WP follows ATDD red-first (charter C-011): a failing-first test committed before implementation.
- Each WP declares its targeted test surface (validation section) — run those packages, not the full suite.
- No new merge-blocking gate lands red (ADR 2026-07-17-1); the WP04 PAT-push path ships disabled until the
  NFR-003 security sign-off.
- The operator merges; agent work is opened as a draft PR once green (charter Collaboration Strategy).
