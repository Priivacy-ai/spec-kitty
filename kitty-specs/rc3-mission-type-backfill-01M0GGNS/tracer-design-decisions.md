# Tracer — Design Decisions (M0 mission_type backfill)

Seeded at planning; appended during implement; assessed at closeout (#2095).

## D1 — Single authority anchor: `canonical_mission_type_key`
- M5's `read_mission_type()` does **not exist yet** on `upstream/main` (M5 unshipped).
  The real single authority today is `charter.mission_type_key.canonical_mission_type_key`
  (`src/charter/mission_type_key.py:24`) — pure, no baked default, `None` for typeless.
- Backfill derives the value through the **same** `canonical_mission_type_key`, so the
  backfill and every future reader agree by construction (charter: single canonical authority).

## D2 — FR-005 census gate ALREADY EXISTS — reuse, do not duplicate
- `spec-kitty doctor mission-type --fail-on legacy-key-only` (impl:
  `src/specify_cli/cli/commands/_mission_type_audit.py`, wired at `doctor.py:533`) is a
  six-state classifier (resolved / activated-unresolvable / unknown / typeless /
  **legacy-key-only** / error), built on `canonical_mission_type_key`, with a `--fail-on`
  gate that exits non-zero while any mission is in the named state(s).
- `legacy-key-only` = "no `mission_type` key at all, but retired `mission` key holds a real
  string" — exactly the M0 backfill target. FR-005/AC-4 are satisfied by this existing gate;
  M0 only needs to WRITE the fix and verify the gate reds-then-greens around it.

## D3 — Dedicated `migrate backfill-mission-type` command (open decision RESOLVED)
- Dedicated command (not folded into `backfill-identity`) so it is independently runnable
  as the FR-005 release gate. Mirrors `migrate backfill-identity` structure exactly
  (`migrate_cmd.py` + `migration/backfill_identity.py`): BackfillResult dataclass,
  per-mission + repo-walk fns, atomic `json.dumps(..., sort_keys=True)` write, `--dry-run`,
  `--json`, `--mission` scope, exit codes.

## D4 — Detection boundary = audit's `legacy-key-only` (construction-agreement)
- Backfill target = `mission_type` key ABSENT **and** `canonical_mission_type_key(mission)`
  is not None. This is exactly the audit's `legacy-key-only` state → backfill fixes exactly
  what `--fail-on legacy-key-only` reds on; re-run greens the gate (AC-3 idempotent, AC-4).
- **Deferred edge:** a present-but-blank `mission_type` (`""`) alongside a legacy `mission`
  classifies as `typeless` in the audit, not `legacy-key-only`. It is NOT a natural legacy
  shape (legacy missions omit the key entirely); treated as a separate corrupt-metadata
  concern, out of scope for this legacy-shape migration. To be pressure-tested by squad #1/#2.

## D5 — Cross-mission contract confirmed (pre-planning census)
- **M5** (`rc3-canonical-mission-type-reader-01M0GGWM`) In-Scope explicitly delegates the
  backfill to M0: *"provide/verify a `mission_type` backfill … verify whether `migrate
  backfill-identity` covers this (it currently does not — it mints `mission_id` only) and
  stand up a `mission_type` backfill if needed."* → M0 is the OWNER; no duplication.
- M5 introduces `read_mission_type(meta) -> str | None` = canonical `mission_type` →
  `canonical_mission_type_key` → `None` (no legacy fallback). Confirms the anchor: M5's
  reader delegates to `canonical_mission_type_key`, the exact symbol M0 writes through.
- Current blessed reader today: `src/specify_cli/mission.py:_canonical_meta_mission_type`
  (~L542) still honors legacy `mission`; M0's write of `mission_type` is read-compatible now
  and after M5 drops the legacy path.
- **M3** (`rc3-charter-gate-predicate-inversion-01M0GGT1`) = #3596/#3598 per-type hard-fail on
  typo/typeless. M0 must land+run before M3+M5 so unmigrated `mission`-only missions don't
  go silently-resolving → typeless (M5) → hard-fail (M3).

## D6 — Squad #1 brownfield refinements (lens B / paula-patterns)
- **Structural template = `backfill_topology.py`, NOT `backfill_identity.py`.** topology is a
  clean single-field backfill; identity juggles mission_id + mission_number → tangled action
  logic M0 doesn't need. Keep the write decision a flat 3-branch (has `mission_type` key → skip;
  legacy key present + canonical → write; neither → skip).
- **Detection reproduced from `charter.mission_type_key` ONLY** (never import the CLI classifier
  `_mission_type_audit.classify_mission_type` into `migration/` — that's a `migration→cli.commands`
  layer smell). Boundary: `"mission_type" not in meta and canonical_mission_type_key(meta.get("mission")) is not None`.
- **Agreement pin = a CROSS-AUTHORITY test** (imports both `audit_mission_types` and the writer's
  selector over ONE fixture corpus; keeps the migration→cli edge in the test only). Corpus MUST
  include a blank-type `typeless` mission (`{"mission_type":"","mission":"software-dev"}`) and assert
  the writer SKIPS it while the audit reports `typeless` (not `legacy-key-only`) — else the agreement
  is vacuously green.
- **Dossier rehash fires** on `action=="wrote" and not dry_run` via the existing
  `trigger_feature_dossier_sync_if_enabled` wrapper (reuse, don't re-implement) — backfill mutates
  meta.json exactly as the sibling backfills do.
- **FR-002 wording softened**: "every canonical/typeless-aware reader" (two sites —
  `dashboard/handlers/features.py:68`, `charter/interview.py:225` — still default-substitute
  `software-dev` reading legacy `mission`; harmless to M0, convergence owned by M5).
- Layer edge `specify_cli.migration → charter.mission_type_key` confirmed allowed (precedent:
  `migration/rewrite_opposed_by.py`, `rewrite_shims.py`). No pre-existing backfill_mission_type.

## D7 — Squad #1 lens A (analyst) BLOCKER fold → R-4 + R-5
- **BLOCKER**: `canonical_mission_type_key` is strip-only (no roster check). A naive verbatim
  write of a typo'd legacy value (`{"mission":"sofware-dev"}`) moves a `legacy-key-only`
  mission to `unknown` — the narrow `--fail-on legacy-key-only` gate GREENS, but M3 still
  hard-fails it. The backfill would *manufacture* a gate-green-but-broken mission.
- **R-4 (resolve-before-write)**: writer writes ONLY when the derived key RESOLVES in the
  layered roster (`resolve_layered_mission_types`, mirrored from the audit's
  `_resolve_layered_roster`, resolved once/run). Non-resolvable candidates → skipped +
  reported `needs-manual-resolution`, never masked. Writer target = {legacy-key-only ∧ resolves}.
- **R-5 (two gate roles)**: narrow `--fail-on legacy-key-only` = completeness; BROAD
  `--fail-on legacy-key-only,typeless,unknown,activated-unresolvable,error` (all-but-`resolved`)
  = release-safety (mirrors M3 hard-fail set + M5 legacy-drop). Release pipeline uses BROAD.
- Missing-AC fixes folded: split AC-2→2a(skip=byte-identical)/2b(write=JSON-semantic+sort_keys);
  AC-7 dry/live --json shape identity; AC-8 backfill exit codes (nonzero iff error>0; dry-run=0);
  AC-9 unknown --mission slug → structured error (NOT identity's silent empty-list/exit-0);
  AC-10 mixed ≥3-mission partition.
- Lens C wording: header "typeless"→"type-unresolvable" (reserve typeless for audit state);
  dropped phantom "canonical JSON writer" authority (it's the sibling-backfill sort_keys idiom).

## D8 — Anti-pattern to avoid in implementation (from identity)
- `backfill_identity.backfill_repo` returns `[]` + logs a warning for an unknown `--mission`
  slug → exit 0 (a latent false-green). `backfill-mission-type` must instead raise a
  structured error / exit non-zero for unknown slug (AC-9). Do NOT copy identity's silent path.

## D9 — Squad #2 BLOCKER: predicate was wrong; operator chose B (profile-resolution + corrected gate)
- Squad #2 (release-gate + blast-radius lenses) proved `registered ∧ roster` (= audit's current
  `resolved`) encodes PRE-M3 (activation-gated) tolerance. M3's #3598 tolerance DROPS the
  `registered` conjunct: tolerate iff a per-type governance-profile (id-matched) resolves at ANY
  layer. So the old predicate REFUSED valid-but-unactivated legacy types (e.g. `{"mission":"research"}`
  unactivated; and EVERY type on an unprovisioned legacy repo where activated set = ∅) → left them
  `mission`-only → M5 typeless → M3 hard-fail = the exact breakage M0 prevents. Reused broad gate
  false-blocked the same missions forever.
- **Operator decision = B**: re-key the WRITER on M3's real tolerance —
  `MissionTypeProfileRepository.for_project(repo_root).get(canonical_key) is not None`
  (activation-INDEPENDENT, id-matched across builtin→org→project; EXISTS today; M3 only relocates
  its call site). Release-safety GATE = the SAME reused `doctor mission-type --fail-on
  legacy-key-only,typeless,error` (drop the activation-dependent unknown/activated-unresolvable
  states that caused the false-block). NO audit-classifier change (R-2 preserved).
- **Big win of B**: built-in types (software-dev/research/…) always resolve via their built-in
  profiles regardless of activation → the catastrophic unprovisioned-legacy-repo case DISAPPEARS.
  Only genuine typos / profile-less custom types → needs_manual_resolution.
- **Residual gap (documented + flag to M3)**: a pre-existing hand-authored present-but-typo'd
  `mission_type` classifies audit-`unknown` and is NOT caught by M0's narrowed gate; M3's runtime
  catches it. M0 never CREATES this state (it only writes profile-resolving values). The audit
  classifier will drift from M3's inverted predicate — cross-mission coordination item for M3.
- Drops `registered ∧ roster` / `existing_mission_types` / `resolve_layered_mission_types` from the
  writer → seam MAJOR-2 (roster-helper duplication) is MOOT.

## D10 — Squad #2 robustness folds (all choices)
- Non-string legacy value (`{"mission":123}`): `canonical_mission_type_key` does `raw.strip()` →
  AttributeError. MUST guard `isinstance(raw, str)` in detection (mirror audit `_classify_absent_key`)
  + broad per-mission `except Exception → error` so one weird mission can't abort the walk. Corpus row.
- Unknown `--mission` slug: `MissingMissionError` does NOT exist (invented). Reuse an existing
  structured error or define one; raise from the repo-walk (NOT the sibling silent warn+return-[]).
- `MissionTypeBackfillResult` gains a `dossier_warning` field (parity w/ identity) for --json visibility.
- Structure from `backfill_topology.py` (single-field) but LIFT dossier rehash from `backfill_identity`
  (topology has none). Document double-rehash/run-order + large canonical-rewrite git diff in changelog.

## D11 — Squad #3 campsite census (folded into WP01/WP02)
- WP02 fold-now: hoist `_NO_PROJECT_ROOT` (5 exact copies at migrate_cmd.py:267/382/676/872/939 +
  WP02's 6th) → one constant; reuse existing `_DRY_RUN_FLAG`/`_MISSION_FLAG`/`_MISSION_METAVAR`
  ("HANDLE")/`_JSON_FLAG` constants (56-71) for the new command. FREEZE retrofitting old commands +
  the shared-printer dedup (separate mission). Leave migrate() `# noqa: C901`.
- WP01 born-clean: topology one-return-per-outcome (no identity ternary tangle); DROP the coord-probe;
  copy `_write_meta_canonical` verbatim; hoist `MISSION_TYPE_KEY`; reasons inline (below S1192).
- m5 REJECTED: keep skip-on-key-presence (`MISSION_TYPE_KEY in meta`) — matches legacy-key-only; a
  valid-set skip guard would wrongly write over the deferred present-but-blank typeless case.

## D12 — Squad #3 anti-laziness (all 11 ACs mapped; supporting-FR coverage added)
- Confirmed: every AC-1..11 → named red-first test through a real entry point; AC-5 genuinely REDs vs
  `registered∧roster`; R-3 corpus non-vacuous (blank-type + non-string rows).
- Added tests: FR-005 error-isolation (corrupt meta between two candidates; B1); dossier-rehash +
  dossier_warning (monkeypatch raising/non-raising; M1); AC-2a fixture NON-canonical (M2);
  FR-007 needs_manual-only exit-0 + diagnostic (M3); AC-8 dry-run-with-error exits 0 (m3);
  R-4 fixture unactivated-built-in within WP01 (m1); AC-5 single-mission fixture (m2).
