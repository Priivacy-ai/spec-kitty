# Implement-loop observations — 01KTNWFC resume (2026-06-11)

Dogfood findings from running the full loop on the freshly-installed rc43+fixes CLI. Legend: 🟢 fixed-in-session · 🟡 worked-around · ⚪ upstream-ticket candidate.

| ID | Finding | Status |
|----|---------|--------|
| L-01 | `move-task --mission <mid8>` fails "WP has no canonical status" — the mid8 HANDLE feeds a raw path constructor somewhere on the transactional read path; the FULL SLUG works. Hit by 3 independent agents. | ⚪ file upstream (resolution-divergence family, #1831-33 adjacent) |
| L-02 | `finalize-tasks --validate-only` SWITCHES the git checkout to the recorded planning branch (meta target_branch) — not non-mutating; cost a confusing "data loss" scare. | ⚪ file upstream |
| L-03 | Implement gate hashes tasks.md wholesale, so routine mark-status checkbox ticks re-stale the analysis report after every WP — required 3 same-body re-records mid-loop. Gate conflates planning content with progress surface. | ⚪ file upstream |
| L-04 | `safe-commit --to-branch X` from branch Y commits correctly but returns the checkout to Y — surprising; reads as lost work until the reflog clears it. | ⚪ UX note, fold into L-02 ticket or #1820 family |
| L-05 | DRG extractor walks `references` only on directives/tactics/paradigms/procedures/profiles — styleguides/toolguides cannot self-wire (WP10 routed edges through the owning procedure; 27 pre-existing orphans remain). | ⚪ file upstream (renata-verified at source) |
| L-06 | record-analysis carrier: `severity: info` invalid in findings[] (counts-only) — analyzer self-corrected; vocabulary asymmetry worth a docstring note. | 🟡 noted |
| L-07 | `mutants/kitty-specs/test-feature-*` leak resurfaced STAGED at primary mid-loop (blocked a move-task; reviewer unstaged). | ⚪ evidence for #1842 |
| L-08 | Doctrine gaps from the WP11 dogfood (renata-routed): legacy triage-snapshot labels → WP05 styleguide follow-up; protected/canonical-tree carve-out → WP04 procedure follow-up; provisional-priority default → WP05 styleguide follow-up. | ⚪ 3 doctrine-refinement tickets |
| L-09 | Planning-artifact gate correctly blocked a kitty-specs commit on a lane (WP01 occurrence_map) — relocated to planning branch; WP prompt T001 wording invited the violation. | 🟢 handled; prompt-template hint upstreamable |
| L-10 | Contract round-trip convention caught REAL planning-vs-implementation drift (extends list→str) — fixed against shipped model. Convention earning its keep. | 🟢 fixed (planning branch) |
