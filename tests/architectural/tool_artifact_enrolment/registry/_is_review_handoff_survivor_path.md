# Exemption mechanism -- `_is_review_handoff_survivor_path`

<!-- Machine-readable exemption-registry row (R-014). Parsed by
     tests/architectural/test_exemption_registry_ratchet.py. ONE mechanism per
     file, so a retirement WP deletes ONLY its own row and never collides with a
     sibling retirement editing a shared file (squad-mandated design; the plan's
     stated reason for rejecting golden-count mode). -->


- mechanism: `_is_review_handoff_survivor_path`
- module: `src/specify_cli/review/dirty_classifier.py`
- literals: `(none)`
- symbol: `_is_review_handoff_survivor_path`
- retirement-wp: `WP17`
- retirement-ref: `IC-07g`
- owner-route: `is_toolchain_generated_churn`
- status: `justified-survivor`

**Justified survivor** (mirrors the WP15 precedent `_is_review_lifecycle_basename`).
The former `dirty_classifier` bundle (`_BENIGN_EXACT_NAMES` / `_BENIGN_PATH_PREFIXES`
/ `_WP_TASK_PATTERN` / `_ROOT_TASKS_MD_PATTERN`) was retired against the owner: the
status/self-bookkeeping arm (`status.events.jsonl`, `status.json`, `meta.json`) now
routes through `is_toolchain_generated_churn` with no independent literal. The
remaining four patterns — `lanes.json`, the `.kittify/` prefix, any WP's
`tasks/WP##-*.md`, and the mission-root `tasks.md` — cannot route onto the owner
without changing ITS answer for the merge/accept gates that also consult it: all
four are either not `kitty-specs/<slug>/` mission artifacts at all (`.kittify/`, no
`MissionArtifactKind`) or are PRIMARY-partition kinds (`LANE_STATE`,
`WORK_PACKAGE_TASK`, `TASKS_INDEX`) whose stale primary copy IS real dirt for
merge/accept by design — only review handoff treats an in-flight toolchain rewrite
of them as benign. The four patterns are function-local (not module-level
collections), so the R-014 collection/regex scan does not independently discover
them; this row is the explicit enumeration the plan requires instead of a silent
survivor, held accountable by the symbol-presence arm.
