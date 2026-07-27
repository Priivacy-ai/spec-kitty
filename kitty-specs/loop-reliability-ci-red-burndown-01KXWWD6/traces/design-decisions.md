# Design Decisions

> Capture the rationale that would otherwise evaporate.

## Entries

<!-- YYYY-MM-DD — Decision: [what]. Alternatives: [what else]. Rationale: [why this one]. -->
- 2026-07-19 — Decision: #2534 = rebase the ready `fix/2534` branch, not re-derive. Alternatives: fold #2598
  (by-construction fix) or re-solve fresh. Rationale: #2598 is epic-blocked under #2535 (won't land in the P0
  window); the branch is tested + small; the two fixes don't conflict (post-#2598 the calm path is unreached).
- 2026-07-19 — Decision: #2807 evidence fix = a 2-line isinstance guard; DEFER the url_list→charter.yaml re-wire.
  Alternatives: re-plumb url_list now. Rationale: url_list has no live config home post-#2773 — re-wiring is
  scope expansion, not CI-red work; the guard clears 3 reds and returns () correctly.
- 2026-07-19 — Decision: test_upgrade auth red = skip-when-logged-out env-guard, not blanket xfail. Rationale:
  NFR-002 (real fix over suppression); mirrors the charter-mission auth-skip.
