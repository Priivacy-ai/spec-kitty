# Phase 0 Research — Landing-Pass Campsite Follow-ups

All decisions below were verified against `upstream/main` @ `c6b70d22e` by the
pre-spec research squad (researcher-robbie, paula-patterns, architect-alphonso)
and stress-tested by the post-spec squad (reviewer-renata, planner-priti). Full
evidence: [`research-notes-csf-2670.md`](../../research-notes-csf-2670.md).

## D-01 — #2671 shard registration: Direction A (auto default fallback)

- **Decision**: Add a per-group opt-in `default_fallback` on `ShardGroup`;
  unregistered `tests/architectural/*.py` route via a stable hash-bucket
  (`sha1(relpath) % shard_count + 1`) in `shard_for()`; explicit
  `_ARCH_SHARD_*` entries still win; keep the GC-1 union invariant as the
  correctness net. Rewrite the load-bearing doctrine header (FR-011).
- **Rationale**: The gap has recurred across three registration incidents; a
  reminder-based fix (Direction B) has already failed against an existing but
  late/expensive double-red gate. Direction A makes the common case automatic
  while preserving the manual, duration-balanced bin-packing as an override.
- **Alternatives rejected**: (B) earlier tripwire / pre-commit — still requires
  the manual step and leans on fragile hook infra; "lightest shard" fallback —
  piles all fallbacks on one shard (they don't increment the counts that define
  "lightest").

## D-02 — #2673/#2638 isolation: Option (i) tmp copy + process-local monkeypatch

- **Decision**: Mutate an isolated tmp copy and monkeypatch `audit.SRC_ROOT`
  process-locally for the mutation window; xdist workers are separate processes,
  so a sibling scanner keeps reading the never-mutated real tree.
- **Rationale**: Removes the shared-mutable-state root cause, fixing both scanner
  victims at once and preserving what the battery proves (real detector code
  path, root-agnostic).
- **Alternatives rejected**: (ii) serialize via `xdist_group` — needs
  `--dist loadgroup` but the repo mandates `--dist loadfile` (ignored); a
  `filelock` fixes only the observed pair and leaves the hazard class standing.

## D-03 — #2672 hygiene: CliConsole deterministic seam

- **Decision**: Route the fix through `CliConsole`
  (`src/specify_cli/cli/console.py`, verified present) rather than `NO_COLOR`
  env mutation; stop mutating the real synthesis-manifest.
- **Rationale**: Operator-directed and architecturally correct — determinism as
  a property of the object, not the environment (the class docstring states
  this). Avoids env leakage across tests.

## D-04 — #2674: one remediation registry the guard scans

- **Decision**: Hoist all remedy prose to named constants; expose
  `ALL_REMEDIATION_TEXTS`; both `_REMEDIATION_HINTS` and `_build_remediation_lines`
  reference the constants; repoint the command-name guard at the registry.
- **Rationale**: One structural root (split surface + half-blind guard). Closes
  the S1192 duplication (semantic, not lexical — grep misses it) and the
  coverage gap together. Output stays byte-identical.

## D-05 — #2675: fix at 6 roots, decompose by file

- **Decision**: Cluster 1 (str→Lane ×4) → promote the legacy sentinel to a
  `Lane` member so `get_wp_lane` returns pure `Lane`. Cluster 2 (no-any-return
  ×2) → one typed `_locate_wp` wrapper. Cluster 3 (decision_id ×2) →
  de-duplicate the interview block into the shared helper, narrow once. Cluster 4
  (3 independent Optionals) → local narrowing each, no artificial shared seam.
  Plus 3 in-scope mechanical cast drops. Keep all `workflow_executor.py` edits in
  ONE work package.
- **Rationale**: The 17 errors collapse to 6 roots; scattered casts would be a
  whack-a-field smell (charter: fix the code, not suppress). `workflow_executor.py`
  carries three clusters — a by-error-category split manufactures a parallel-lane
  ownership collision (coord topology).
- **Deferred**: the three `charter/mission_type_profiles.py` casts are owned by
  the in-flight mission-type work — deferred to avoid a production-code
  cross-mission collision (they clear when that mission lands).

## D-06 — Sequencing under parallel #2651/S0

- IC-01 (#2671) is a soft enabler — land first; it also de-frictions the
  in-flight resolver-seam missions.
- IC-02 (#2673) contends sharply with #2651/S0 on
  `test_single_mission_surface_resolver.py` — land in a quiescent window or fold
  into that mission's lane (C-006). Not a free rebase.

## Open items carried to implementation

- Confirm the `Lane` sentinel-promotion caller blast radius (spec Assumption).
- Confirm the exact #2672 failing test and that `CliConsole` covers its output.
- File the SC-006 follow-up issue for the ~6 residual `_SourceMutation` sites.
