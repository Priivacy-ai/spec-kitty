# Approach Trace — loop-friction-quickwins-2-01KXBWA4

The methodology of this mission — to assess post-hoc what paid off. Seed → append → assess. (#2095)

## Seed (planning)

**Front-loaded research.** A 4-lens pre-spec research squad (self-writing guards / authority-split+dedup
/ gate-subprocess / papercuts) ran read-only against fresh `upstream/main` in the gate-doctrine clone,
each lens returning code-grounded root causes (file:line), fix sketches, blast radius, and dedup
verdicts. Synthesis: `../research-synthesis.md`.

**Decisive lens = de-duplication.** It separated genuine residual from work already shipped (merged
partition-lock #168; `create_rejected_review_cycle` for #2493.2) or in flight (draft
`implement-loop-coord-authority-completion`; unmerged `loop-friction-fastfollow` quick-wins I). This
prevented specing a duplicate and defined the exclusion boundary (C-003).

**Scope hypothesis to test:** the cluster splits cleanly into 5 independent, mostly-S-blast-radius
concerns, each with existing prior art to mirror. WP sizing = one concern per WP (5 WPs); IC-05 is the
only high-coordination concern (coord-adjacency, C-002).

**Bet:** mirroring existing seams (`_drop_vcs_lock_only_meta`, `_manifest_source_path`,
`_normalize_tasks_md`) keeps blast radius small and review cheap, vs. bespoke fixes.

## Append (implement)

- [2026-07-12][plan] **Post-plan 4-lens squad ROI (high).** renata(dedup)/priti(sizing)/alphonso(coord)/
  daphne(canonical), profile-loaded, read-only vs live code. Caught, pre-tasks: (1) 2 undersized concerns
  (FR-006 manifest is M not a papercut — `project_root` threading + keying invariant; IC-02 lock is M —
  async/sync mismatch + lock-wait-vs-timeout); (2) IC-04 mis-apportioned (specify twin already shipped);
  (3) the coord collision C-002 feared was already MERGED (#2194/#2545) → include de-risked; (4) IC-05
  must narrow (drop `commit_guard` exemption — WP commits already route to primary); (5) 3 folds/links
  (#2580/#1862/#2583) + FR-008 single-HIGH true-positive hole. Net: 5→7 concerns, before any WP was cut.
  The dedup+sizing lenses paid for themselves (would have surfaced as rework mid-implement otherwise).

- [2026-07-12][tasks] **Post-tasks 4-lens squad ROI (high, pre-implement).** renata(executability)/pedro(sonar-
  campsite)/priti(completeness)/alphonso(SSOT), profile-loaded, vs live code + the actual WP files. Caught
  before any WP ran: (1) **WP06 wrong-consumer** — setup-plan `result` doesn't flow through `next --result`'s
  fixed `_VALID_RESULTS`; reworked to mirror the shipped specify twin (`success`+`scaffold_only`), avoiding a
  dead engine.py edit + an under-owned `next_cmd.py`; (2) **WP05 complexity breach** — `_issue_matrix_approval_blocker`
  at 13 would exceed 15 inline → route via existing `_issue_matrix_diagnostic_lines` + hoist literals; (3)
  **WP04/WP03 SSOT** — reuse one relativize helper / one canonical `_interpreter.py`, not a 2nd copy; (4) two
  MED unpinned branches (WP04 out-of-tree, WP03 uv-no-pyproject); (5) the WP07↔WP08 boundary + same-path pin.
  A 4th lens (alphonso SSOT) was added mid-run at operator request and produced the highest-value finding
  (WP07↔WP08 read/write authority boundary). Net: WP06 rework + 5 WP patches + WP08 added, all pre-implement.
  Lesson forming: the post-tasks squad's executability+SSOT lenses catch anchor/consumer/complexity errors
  that would otherwise surface as mid-lane rework or a Sonar-gate red.

## Assess (close)

<!-- ROI of the front-loaded 4-lens squad: findings that survived to code vs. discarded; time saved vs. a cold start -->
