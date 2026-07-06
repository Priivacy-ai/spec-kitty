# Issue matrix — cmd-output-file-leak-guard-01KWVZX7

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2169 | Test isolation: SPEC_KITTY_CMD_OUTPUT_FILE-unset run leaks a literal invalid-Windows-path junk file | fixed | Lane commit 64ca24fd — both `--output=` parsers in `test_capture_baseline_custom_test_runner_label` remediated (wired fake writes to the env path; dead twin deleted; env-independent, verified by scratch-cwd repro), plus a new `tests/architectural/test_no_invalid_windows_filenames.py` (Windows-illegal + shell-telltale sets) registered in `_arch_shard_map.py`. reviewer-renata mutation-verified + the `café.txt` false-positive was fixed (`git ls-files -z`) with a regression test. |
| #2397 | matrix-shard the arch-adversarial pole | verified-already-fixed | #2397 landed (the arch pole is sharded via `tests/_arch_shard_map.py`); this mission *consumes* it — the new guard is registered in `_ARCH_SHARD_1_FILES` so it earns an `arch_shard_1` marker and `test_arch_shard_marker_completeness.py` stays green. No #2397 code changed. |
| #1842 | Test-suite state leaks: tests must be atomic, idempotent, and self-cleaning | deferred-with-followup | Follow-up: #1842 (separate mission). This mission is scoped to the one #2169 leak instance (distinct mechanism/files); the broader 8-class sweep + reaper remains under #1842 (frozen `/tmp` ratchet already landed via #2181). |
| #1634 | Test runs leak test-feature-* scratch missions into live mission state | deferred-with-followup | Follow-up: #1842 (folded there — #1634 is #1842's instance #1). Out of scope for this #2169 leak-guard mission. |
| #2161 | PR incident: the `"${SPEC_KITTY_CMD_OUTPUT_FILE}"` junk file was swept in by `git add -A`, breaking Windows CI (run 28224079685) | verified-already-fixed | The specific #2161 junk file is long gone from main; this mission fixes the root-cause leak (both `--output=` parsers) and adds the always-on filename guard that prevents recurrence of the class that broke #2161's Windows checkout. No #2161 change needed. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
