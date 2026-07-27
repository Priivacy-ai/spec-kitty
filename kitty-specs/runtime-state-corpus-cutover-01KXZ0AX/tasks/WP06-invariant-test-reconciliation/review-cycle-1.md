---
affected_files: []
cycle_number: 1
mission_slug: runtime-state-corpus-cutover-01KXZ0AX
reproduction_command: null
reviewed_at: '2026-07-20T13:40:00Z'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP06
---

# WP06 Review — APPROVED (IC-05 invariant harden + ~33-file reconcile + fail-closed fix)

Two implementation cycles (b94c0ca95 + 221a78df3). Verified: 25 crux tests + 218 emit-door consumer tests pass, ruff clean.

- **T025 detector extension — NON-VACUOUS (proven two ways):** call-chain arm matches `read_wp_frontmatter(...).<runtime_field>` attribute reads (robust D-09 anchor; deliberately not naive name-based, to avoid false-flagging the legitimate authored read at scanner:1000). Durable co-located poison-tests (attr-read → RED, snapshot mirror → GREEN, authored → GREEN) PLUS a live-tree reproduction (injected a frontmatter read into the scanner → detector went RED → reverted). SC-009 met.
- **T024:** `_SANCTIONED_READER_MODULES` → `frozenset()`; the vacuous gate-identity arm rewritten to "zero reader-authority gates remain" (SC-002/003).
- **T026 ~33-file reconciliation — NO assertion weakened to green:** documented table; flag-OFF twins deleted, flag-ON assertions made unconditional to the true snapshot-authority end-state; compat-surface + facade reconciled. Spot-verified.
- **T027 baselines regenerated** via the sanctioned `--freeze-baselines` (3 E3 node-id baselines + gate-coverage); test_gate_coverage 31 pass. T028 no-op (byte-stability + INV-5 already covered — no duplication).
- **Fail-closed fix (cycle 2, #2510):** the implementer REFUSED to weaken the orchestrator-api fail-closed test and routed it back — correctly diagnosed as WP04 over-reach (the emit door `_infer_subtasks_complete` went fully snapshot-only while the CLI door kept the C-001 silent-slot fallback). Fix restores the fallback (`_wp_tasks_md_has_unchecked_rows` over the SAME `iter_wp_section_subtask_rows` the CLI door uses) so both fail-closed doors are symmetric; the test blocks VIA the restored fallback, not a weakened assertion. Also fixed 3 bonus reds in `test_wp_header_regex_depth.py` (also broken by WP04's over-reach; verified red-on-base, green now). C-010: WP13 removes both doors' fallbacks when checkboxes retire — restoring consistency, not permanent debt.
- ruff clean; only pre-existing mypy `_feature_status_lock_root` (base-confirmed). Zero new suppressions.
- `_mt_commit_wp_file` FOLD correctly DEFERRED to WP07 (true dead closure is 9 fns spanning WP07-owned tests + a source-SHA-pin; not needed for green).
- **Corpus-on-feat:** `test_dogfood_corpus_backfilled.py` fails on lane-f (seeds are on feat only), verified at merge — not chased.

**Verdict: APPROVED.** WP06 reconciles the Phase-1 merge unit honestly and hardens the single-authority invariant non-vacuously; the fail-closed door-symmetry fix is a genuine correctness improvement the reconciliation surfaced.
