# Tooling Friction Log

> Log every place the tooling fought you so it can feed the tooling-gap backlog (#2095).
> **Implementers: append a dated entry the moment a command, gate, or workflow fights you** —
> in-the-moment capture, 1–3 sentences. Do NOT reconstruct at close.

**Prompting questions**
- What tooling or command did you have to work around?
- What blocked you unexpectedly, and how long did it take to unblock?
- Was this a known issue or something discovered fresh?

---

## Entries

- **2026-07-08 — [planning] Known: planning surfaces don't prompt the tracer procedure.**
  Carried over from the sibling mission — `/specify`, `/plan`, `/tasks` do not seed or enforce
  `mission-tracer-files`. Mitigated here by seeding manually at the post-plan point-cut. Still a
  process gap worth surfacing (it feeds #2095).
- **2026-07-08 — [planning] Census line-refs drift on every merge — pin on tokens.** The
  landed `resolution_gate_allowlist.yaml` pins Thread-A review write sites at STALE line
  locators (2633/2670) that no longer match the source; they are token-authoritative only.
  Any WP re-running the census MUST scan by construct/token, not frozen line numbers.
- **2026-07-08 — [planning] Watch shared test helper `tests/lane_test_utils.py`.** #2462's CI
  fix rewrote it to mint production-shaped `mission_id`/`mid8`; a meta-less / empty-mid8 fixture
  now hard-fails. Thread B/#2100 WPs reusing this helper must match the new minted-identity
  contract (realistic ids, not placeholders).
- **2026-07-08 — [planning] CI caveat #2475: arch marker gate is vacuous under `.worktrees/`.**
  When verifying this mission's own architectural ratchet tests locally from an execution
  worktree, the marker gate may not fire — verify arch tests from the primary checkout or with
  an explicit path, not by trusting a green marker run inside `.worktrees/`.
- **2026-07-08 — [WP05] Routing a single A-site silently red-failed 5 architectural gate tests
  in TWO files until traced.** `tests/architectural/test_resolution_authority_gates.py` scans
  `src/` for the pre-fix `resolve_feature_dir_for_mission`/`primary_feature_dir_for_mission`
  call-site patterns and asserts a shrink-only floor (`CANONICALIZER_FLOOR`,
  `COORD_AUTHORITY_WRITE_FLOOR`) plus a `resolution_gate_allowlist.yaml` entry per pre-sweep
  site. Draining `implement.py`'s ONE A-site simultaneously dropped BOTH counters (its own
  `coord_authority` allowlist entry going stale, AND the `primary_feature_dir_for_mission` call
  inside its deleted fallback cascade counting toward the separate `canonicalizer` census) — AND
  a completely different, unrelated PAST mission's test
  (`test_coord_read_residuals_closeout.py::test_routed_canonicalizer_floor_matches_recorded_census`)
  independently hardcoded the same `CANONICALIZER_FLOOR == 45` as a "recorded census" sanity pin.
  A routing WP for this mission is NOT "route the call + run pytest -k implement" — it needs the
  FULL `pytest tests/architectural/` run (the `-k "implement or identity_audit"` filter used for
  the ticket's own tests does not collect either gate file by name), plus a repo-wide grep for
  `CANONICALIZER_FLOOR`/`COORD_AUTHORITY_WRITE_FLOOR` usages before assuming one gate file is the
  only twin needing a re-pin. Worth calling out prominently in WP prompts for the remaining
  Thread A/B WPs — every drained site likely needs the SAME twin-gate (or triple-gate) re-pin.
- **2026-07-08 — [WP05] Monkeypatching a routed-away symbol fails LOUD, not silently.**
  `unittest.mock.patch("...implement.resolve_feature_dir_for_mission", ...)` on a module that no
  longer imports that name raises `AttributeError: module ... does not have the attribute` at
  test collection/run time — a clear, fast signal (not a silent no-op), but still needed a
  manual sweep (`grep -rn "<module>.resolve_feature_dir_for_mission"` across `tests/`) since the
  test importing the patched module (`tests/agent/test_implement_command.py`) is not co-located
  with the implementation file and wasn't caught by the diff-scoped lint/mypy pass.
- **2026-07-08 — [WP05] `kitty-specs/` trace-file edits on a lane branch are silently
  committed, then BLOCK `move-task` at the end.** `git commit` on the lane worktree succeeds with
  only a `[spec-kitty guard] WARNING: Protected path` line (not an error, easy to miss in scroll-
  back) when the diff touches `kitty-specs/`; the hard block only surfaces later, at
  `move-task --to for_review`, with a much more informative error naming the exact remediation
  (`git restore --source <mission-branch> ...` or a scoped `git checkout <mission-branch> -- <path>`,
  then commit the removal, then re-apply the trace content on the primary checkout — which is the
  actual `design/<slug>` worktree in this topology). Cheaper to write trace-file entries directly
  on the primary checkout from the start rather than the lane worktree and revert-and-redo.
