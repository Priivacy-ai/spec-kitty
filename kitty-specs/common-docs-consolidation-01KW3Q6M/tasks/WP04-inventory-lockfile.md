---
work_package_id: WP04
title: Inventory lockfile generator + freshness inversion (ruler 2, report-only)
dependencies:
- WP01
requirement_refs:
- FR-006
- NFR-004
- SC-006
tracker_refs: []
planning_base_branch: docs/2165-consolidation-research
merge_target_branch: docs/2165-consolidation-research
branch_strategy: Planning artifacts for this mission were generated on docs/2165-consolidation-research. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-consolidation-research unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: scripts/docs/inventory_lockfile.py
create_intent:
- scripts/docs/inventory_lockfile.py
- tests/docs/test_inventory_lockfile.py
execution_mode: code_change
owned_files:
- scripts/docs/inventory_lockfile.py
- scripts/docs/check_docs_freshness.py
- scripts/docs/_inventory.py
- tests/docs/test_inventory_lockfile.py
role: implementer
tags: []
shell_pid: "615447"
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load python-pedro` (or read the profile YAML and adopt it). State which directives apply, then proceed.

## Objective

Make in-file frontmatter the metadata SSOT: build the **frontmatter→inventory lockfile generator** and **invert** `check_docs_freshness.py` from "every page must be in the sidecar" to "the committed inventory must equal a fresh generation." Prove it with the **linchpin tamper self-test** — this is the test that makes the whole SSOT thesis non-fakeable.

## Context

Depends on WP01 (the ADR records Candidate A + dropping `citation_refs`). Read `scripts/docs/check_docs_freshness.py` + `docs/development/3-2-page-inventory.yaml` (568 rows) first. **Report-only here** (the inventory is not yet authoritative — the backfill is Mission B); the generator + the inverted check exist and run, but do not block. **Do NOT delete `LEAK-FRONTMATTER-MISMATCH` until the new gate is proven red live** (T019). No doc-tree mutation, no new deps.

## Subtasks

### T016 — `scripts/docs/inventory_lockfile.py`
Walk `docs/**/*.md`, parse frontmatter, and emit the page-inventory rollup (schema: `path/tag/divio_type/owning_workstream/current_target/notes` + `doc_status` if surfaced). **Drop `citation_refs`** (only 6/568 populated; 562 empty). **Reuse `scripts/docs/_inventory.py`'s `PageInventoryEntry`** — do not redefine the schema. Preserve the rollup invariants: completeness (every `.md` present), ownership, deterministic alphabetical-by-path diff (byte-stable).

### T017 — Drop `citation_refs`
Drop `citation_refs`: edit `scripts/docs/_inventory.py`'s `_REQUIRED_KEYS` + the frozen `PageInventoryEntry` field (it currently *hard-requires* `citation_refs`), and ensure the generator + comparison omit it. (This is why `_inventory.py` is in owned_files.)

### T018 — Invert `check_docs_freshness.py` to generate-and-compare
Add a mode that regenerates the inventory from frontmatter and asserts **`generated == committed`** (drift = finding). Keep it **report-only** here (print the diff, exit 0); Mission B makes it blocking.

### T019 — LINCHPIN self-test
`tests/docs/test_inventory_lockfile.py`: (a) regenerate the inventory **before and after** mutating one *in-rollup* frontmatter field (e.g. `divio_type`/`doc_status`); assert **`generated(before) != generated(after)`** (this fails any echo/no-op generator that copies committed→generated) AND the returned drift result is non-empty (`has_drift is True`). **"RED" is the returned drift object, not an exit code** — the tool stays exit-0 report-only (add a wired-but-off `--strict` for symmetry with WP03/WP05). (b) hand-edit the committed lockfile alone (frontmatter untouched) → assert the same drift signal flips to rejected. **Red-first:** record evidence the test was RED against a no-op stub before the real generator made it green. NOTE: `LEAK-FRONTMATTER-MISMATCH` lives in `scripts/docs/version_leakage_check.py` (NOT owned here) — **Mission A leaves it untouched** (grep confirms it still fires); its retirement is Mission B's job.

### T020 — Report-only baseline
Run generate-and-compare over the live tree; confirm exit 0; record the drift baseline.

## Branch Strategy

Planning + merge target: `docs/2165-consolidation-research`. Worktree per `lanes.json` (Lane C, after WP01; parallel to WP03).

## Definition of Done

- [ ] Generator emits a deterministic lockfile (byte-identical on re-run), no `citation_refs`, rollup invariants preserved.
- [ ] Freshness check has a report-only generate-and-compare mode (exit 0 here).
- [ ] **Linchpin self-test reds** on the frontmatter tamper and **rejects** a lockfile-only hand-edit.
- [ ] `version_leakage_check.py` (`LEAK-FRONTMATTER-MISMATCH`) is **untouched** in Mission A (grep confirms it still fires); retirement deferred to Mission B.
- [ ] `ruff`/`mypy` clean; no new deps; no doc-tree mutation.

## Risks & Reviewer Guidance

- **The fakeable trap (renata's #1):** a no-op/echo generator that copies `committed → generated` passes `generated==committed` forever while reading nothing from frontmatter. The reviewer MUST confirm T018(a) — a frontmatter mutation actually changes the generated output and reds the gate — and T018(b) — a lockfile-only edit is rejected. Without both, the SSOT story is unfalsifiable.

## Activity Log

- 2026-06-27T06:56:13Z – claude:opus:python-pedro:implementer – shell_pid=559234 – Assigned agent via action command
- 2026-06-27T07:12:00Z – claude:opus:python-pedro:implementer – shell_pid=559234 – Ready for review: frontmatter->inventory lockfile generator + report-only freshness inversion + linchpin tamper self-test (red-first proven). citation_refs dropped. version_leakage_check.py untouched.
- 2026-06-27T07:12:58Z – claude:opus:reviewer-renata:reviewer – shell_pid=615447 – Started review via action command
- 2026-06-27T07:19:37Z – user – shell_pid=615447 – Review passed: linchpin tamper-test BITES (forced frontmatter={} reds the echo trap at test:98 'assert before_render != after_render'); clean revert verified. lockfile-only hand-edit rejected via changed-fingerprint. citation_refs dropped at _inventory.py source (_REQUIRED_KEYS + frozen field + validation block) and generator REUSES PageInventoryEntry (no schema fork). version_leakage_check.py UNTOUCHED (empty diff vs base) and LEAK-FRONTMATTER-MISMATCH still fires (test_detects_all_five_rules + test_main_dirty green). 2 removed parametrize cases (citation_refs not-a-list/[1,2]) tested the now-deleted _validate_row requirement, NOT the LEAK rule — honest stale deletion, no overlap. Large drift baseline (284 gen vs 568 committed, removed=252 changed=284) is DESIGNED + report-only exit 0 (Mission B converges). Determinism byte-stable. ruff clean; mypy --strict clean (3 files). No doc-tree mutation (C-006). Suites: test_inventory_lockfile 14/14, test_version_leakage_check 49/49, test_check_docs_freshness 39/39.
