# Contract — Gate-Artifact Write Surface (#2804 / #2404 — FR-009 / SC-005)

**Owner**: `accept` acceptance-matrix home resolver + `merge/executor.py` + `merge_driver.py` + `init.py`.

## Guarantees

- **G1 (single write surface, #2404)**: no code path authors a PRIMARY-partition `acceptance-matrix.json`
  under a coordination topology. `accept` fills it on the COORD surface only, so there is no add/add
  divergence for the merge to mis-resolve. Verified by a **write-side** check (greps the write path,
  not just the merge outcome). *(SC-005)*
- **G2 (driver registration, defense-in-depth)**: the merge executor guarantees the row-aware
  `spec-kitty-acceptance-matrix` / `spec-kitty-issue-matrix` drivers are registered/active in the repo
  **before** the squash, so `-X theirs` never clobbers a filled matrix.
- **G3 (legacy retired)**: `issue-matrix.md` is retired; the `.md`→`.json` driver seed drift
  (`m_3_2_6_gate_artifact_merge_drivers.py` seeding the retired `.md` pattern) is fixed so the
  issue-matrix driver is not inert.

## Independence

This concern (IC-06) touches none of the verdict-seam files and no census yaml — it runs on a
**parallel lane**.

## Verified by

Green the existing red-first pin `tests/regression/test_issue_2804_merge_resets_gate_artifacts.py`
(a filled acceptance + issue matrix survives a real merge) + the G1 write-side check.
