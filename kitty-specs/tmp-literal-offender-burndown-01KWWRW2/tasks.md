# Work Packages: Burn down the 99 grandfathered /tmp-literal test offenders

**Mission**: `tmp-literal-offender-burndown-01KWWRW2` | **Issue**: Closes #1842 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

## Subtask Format: `[Txxx] Description (WP)`

## Path Conventions
Repo-root-relative. 7 parallel conversion WPs (disjoint file ownership, partitioned by directory) + 1 dependent gate WP. Conversion WPs never touch `tmp_ratchet_baseline.txt` (WP08 owns it). See plan.md "Critical sequencing".

| Subtask | Description | WP | Requirement |
| --- | --- | --- | --- |
| T0101 | Convert `specify_cli` group A (15 files) off literal `/tmp` (tmp_path/sentinels) | WP01 | FR-001, FR-002, FR-007 |
| T0201 | Convert `specify_cli` group B (14 files) off literal `/tmp` | WP02 | FR-001, FR-002, FR-007 |
| T0301 | Convert `sync` (13 files) off literal `/tmp` | WP03 | FR-001, FR-002, FR-007 |
| T0401 | Convert `charter` + `status` (11 files) off literal `/tmp` | WP04 | FR-001, FR-002, FR-007 |
| T0501 | Convert `doctrine` + `agent` (12 files) off literal `/tmp` | WP05 | FR-001, FR-002, FR-007 |
| T0601 | Convert `next/runtime/unit/integration/cli/dossier/contract` (18 files) off literal `/tmp` | WP06 | FR-001, FR-002, FR-007 |
| T0701 | Convert `adversarial/audit/auth/core/git_ops/glossary/kernel/paths/architectural` (14 files) off literal `/tmp` | WP07 | FR-001, FR-002, FR-007 |
| T0801 | Empty `tmp_ratchet_baseline.txt` | WP08 | FR-003 |
| T0802 | Make the gate file genuinely literal-free (all 14 lines) + `__file__` self-exclude | WP08 | FR-004 |
| T0803 | Replace the `>50` floor with a positive self-test | WP08 | FR-004, FR-006 |
| T0804 | Add the FR-007 evasion-vector / isolation-adoption check | WP08 | FR-007 |

---

## Work Package WP01: specify_cli group A (Priority: P1)
**Prompt**: `/tasks/WP01-wp01-specify-cli-group-a.md`
### Included Subtasks
- [x] T0101 Convert specify_cli group A (15) (WP01)
### Dependencies
None.

## Work Package WP02: specify_cli group B (Priority: P1)
**Prompt**: `/tasks/WP02-wp02-specify-cli-group-b.md`
### Included Subtasks
- [x] T0201 Convert specify_cli group B (14) (WP02)
### Dependencies
None.

## Work Package WP03: sync (Priority: P1)
**Prompt**: `/tasks/WP03-wp03-sync.md`
### Included Subtasks
- [x] T0301 Convert sync (13) (WP03)
### Dependencies
None.

## Work Package WP04: charter + status (Priority: P1)
**Prompt**: `/tasks/WP04-wp04-charter-status.md`
### Included Subtasks
- [x] T0401 Convert charter + status (11) (WP04)
### Dependencies
None.

## Work Package WP05: doctrine + agent (Priority: P1)
**Prompt**: `/tasks/WP05-wp05-doctrine-agent.md`
### Included Subtasks
- [x] T0501 Convert doctrine + agent (12) (WP05)
### Dependencies
None.

## Work Package WP06: next/runtime/unit/integration/cli/dossier/contract (Priority: P1)
**Prompt**: `/tasks/WP06-wp06-next-runtime-unit-integration-.md`
### Included Subtasks
- [x] T0601 Convert the 18-file group off /tmp (WP06)
### Dependencies
None.

## Work Package WP07: adversarial/audit/auth/core/git_ops/glossary/kernel/paths/architectural (Priority: P1)
**Prompt**: `/tasks/WP07-wp07-adversarial-audit-auth-core-gi.md`
### Included Subtasks
- [x] T0701 Convert the 14-file group off /tmp (WP07)
### Dependencies
None.

## Work Package WP08: Gate flip — empty baseline + self-consistent hard gate (Priority: P1)
**Prompt**: `/tasks/WP08-gate-flip.md`
### Included Subtasks
- [ ] T0801 Empty the baseline (WP08)
- [ ] T0802 Literal-free gate file + __file__ self-exclude (WP08)
- [ ] T0803 Floor → positive self-test (WP08)
- [ ] T0804 FR-007 evasion-vector check (WP08)
### Dependencies
WP01, WP02, WP03, WP04, WP05, WP06, WP07 (baseline can only empty after all files are converted).
### Risks & Mitigations
- Self-reference false-green → make the gate file genuinely literal-free (not just `__file__` exclude). A conversion WP missing a file → WP08 STOPS and reports (never re-baselines to force green, C-003).
