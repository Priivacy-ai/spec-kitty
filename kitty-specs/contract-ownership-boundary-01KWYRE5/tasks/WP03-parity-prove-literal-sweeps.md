---
work_package_id: WP03
title: Parity-prove the literal sweeps — WITHOUT retiring the enforcing gates
dependencies:
- WP01
- WP02
requirement_refs:
- FR-006
tracker_refs: []
planning_base_branch: feat/contract-ownership-boundary
merge_target_branch: feat/contract-ownership-boundary
branch_strategy: Planning artifacts for this mission were generated on feat/contract-ownership-boundary. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/contract-ownership-boundary unless the human explicitly redirects the landing branch.
subtasks:
- T005
agent: "reviewer-renata"
shell_pid: "4064996"
history:
- Created for mission contract-ownership-boundary-01KWYRE5
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_contract_registry_parity.py
execution_mode: code_change
owned_files:
- tests/architectural/test_contract_registry_parity.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load your assigned profile (`python-pedro`) via `/ad-hoc-profile-load` before reading anything else.

## Objective
Demonstrate the advisory sweep driver **subsumes the detection** of the literal `test_no_legacy_*` sweeps — WITHOUT removing the merge-blocking gates (that would downgrade enforcement). **FR-006, NFR-001, NFR-004.** Depends on WP01 (records) + WP02 (driver).

## ⚠️ Hard constraint — NO enforcement downgrade (NFR-004)
`test_no_legacy_terminology.py` (`pytest.fail`, line ~124) and the CLI-tree literal-grep in `test_no_legacy_path_literals.py` (`assert`, line ~74) are **merge-blocking today**. Do **NOT** remove, neuter, or convert them. Retiring a blocking gate behind an advisory driver silently downgrades it to report-only — the exact anti-pattern this mission's own NFR forbids. The actual delete-the-assertion retirement is a deferred follow-up (needs an enforcing driver mode). This WP only **proves parity**.

## Guidance (T005)
`tests/architectural/test_contract_registry_parity.py`:
- The literal-sweep records (seeded in WP01) exist for the terminology terms + the CLI-tree path literals.
- **Parity = real set-equality over shared input** (NOT just "both catch one violation" — that's over-flag-blind, a trivially-over-flagging driver passes): (1) a **planted-violation** fixture tree → both the driver AND the old sweep flag it; (2) a **benign-but-similar-looking control** (e.g. the term inside an exempted `docs/adr/` path, or a legitimate use) → both **IGNORE** it (proves no over-flag — the exemptions/scan_roots envelope matches); (3) assert the two detection **sets are equal** over the same fixture tree.
- **Feasibility — the old sweeps have NO injection seam**: `test_no_legacy_terminology.py::_grep_for` hardcodes `_repo_root()` (git grep the live tree); the CLI path-grep hardcodes `root=.../src/specify_cli/cli`. So run the old sweep against your fixture via a **fabricated-repo subprocess / temp-tree git-grep** (build a tiny repo with the planted + benign files; run the sweep's actual grep logic against it). **Do NOT** degrade to a source-grep for the string `pytest.fail` — that's fakeable and proves nothing.
- **Assert the enforcing gates still BLOCK**: run `test_no_legacy_terminology.py` (+ the path assert) against a planted-violation fixture and assert it **exits non-zero / raises** — so a future regression that neuters the gate reds THIS test. Not a source-grep.

## Definition of Done
- Parity demonstrated (driver detection == enforcing-gate detection on the same input).
- The enforcing terminology + path gates are unchanged and still merge-blocking (asserted).
- `ruff`+`mypy` clean; no suppression; nothing removed.

## Reviewer guidance
Confirm NO enforcing assertion was removed/neutered (diff touches only the new parity test), the parity is a real same-input comparison (not a tautology), and the "gates still block" assertion would red if someone later neutered them.

## Activity Log

- 2026-07-07T20:05:49Z – python-pedro – shell_pid=4018787 – Assigned agent via action command
- 2026-07-07T20:28:05Z – python-pedro – shell_pid=4018787 – Ready for review: parity proven (real set-equality planted+benign; fabricated-repo subprocess, not source-grep; gates-still-block asserted). Enforcing gates unchanged (NFR-004). ruff+mypy clean; routed to arch_shard_3.
- 2026-07-07T20:29:33Z – reviewer-renata – shell_pid=4064996 – Started review via action command
