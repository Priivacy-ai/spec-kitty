# Mission Spec: mission_type backfill migration (rc3 program gate M0)

> **Program gate for rc3.** This mission must land AND be run against real projects
> **before M3 and M5 reach them.** M5 drops legacy `{"mission":…}` resolution and M3
> makes a type-unresolvable (typeless or profile-less) `mission_type` hard-fail; together,
> an unmigrated legacy mission carrying only `{"mission":…}` goes from silently-resolving →
> **type-unresolvable** (M5) → hard-fail (M3). Backfilling a **profile-resolving**
> `mission_type` first is what makes that combined change safe. Hoisted out of M5 (was
> M5/FR-007) into its own mission-0 gate per the integration check.
>
> Terminology note: "type-unresolvable" is the *runtime* sense (a mission that resolves to
> no usable type). The mission-type **audit's** `typeless` state is a distinct, narrower
> *static* shape (a present-but-blank/null/non-string `mission_type` value). This spec
> reserves `typeless` for the audit state and uses "type-unresolvable" for the runtime
> sense, per the charter "name the sense" footgun discipline.

## Problem & impact (BLUF)

Legacy missions store their type in the deprecated `mission` field of `meta.json`;
newer missions use `mission_type`. Several readers still fall back to `mission`.
Missions **M3** (`rc3-charter-gate-predicate-inversion-01M0GGT1` — #3598 §B inverts the
governance-slot probe: a type is tolerated iff a per-type `governance-profile.yaml`
resolves, id-matched, at **any** layer, **independent of charter activation**; otherwise
it hard-fails) and **M5** (`rc3-canonical-mission-type-reader-01M0GGWM` — canonical reader;
legacy `mission` resolution dropped entirely) remove the legacy fallback. Without a
backfill, any project whose `kitty-specs/` carries `mission`-only `meta.json` files breaks
on upgrade: those missions stop resolving and then hard-fail. **M5's own spec delegates
this backfill to M0.** This mission mints a **profile-resolving** `mission_type` for every
eligible legacy mission so the M3+M5 change is non-breaking, and ships the census gate the
release pipeline uses to prove a project is safe before it upgrades.

### Why the tolerance predicate is profile-resolution, NOT charter activation (squad-2 finding)

M3's hard-fail predicate is **activation-independent** (per-type `governance-profile.yaml`
existence at any layer, via `MissionTypeProfileRepository`). The mission-type **audit**'s
`resolved` state, by contrast, is `activated ∧ roster` — the *pre-M3* predicate. Keying M0
on the audit's `resolved` would refuse to backfill valid-but-**unactivated** built-in types
(e.g. a legacy `{"mission":"research"}` in a project that has not activated `research` — and,
because an unprovisioned legacy project has an **empty** activated set, *every* legacy type
including `software-dev`), leaving exactly M0's target population to break at M3. M0
therefore keys the writer on **profile-resolution** (`MissionTypeProfileRepository` — the
same authority M3 §B consumes; it exists today and M3 only relocates its call site). A
built-in type always resolves via its shipped profile regardless of activation, so an
unprovisioned legacy repo backfills cleanly.

## In scope

- A deterministic, idempotent backfill that, for every mission under `kitty-specs/` whose
  `meta.json` has **no `mission_type` key** but carries a legacy `mission` value **that
  resolves to a governance-profile at any layer** (`MissionTypeProfileRepository
  .for_project(repo_root).get(canonical_key) is not None`), writes
  `mission_type = canonical_mission_type_key(mission)`.
- **Honest handling of non-resolving legacy values.** A legacy `mission` value that
  canonicalizes to a non-blank key but resolves **no** profile at any layer (a genuine typo
  like `"sofware-dev"`, or a custom type shipping no `governance-profile.yaml`) is **not
  written** — it is reported `needs_manual_resolution`. The backfill never masks such a
  mission (it stays `legacy-key-only`, so the gate keeps reding it).
- An audit/dry-run mode (`--dry-run`, `--json`, `--mission <slug>`) reporting
  `wrote` / `skip` / `needs_manual_resolution` / `error` counts and per-mission before→after.
- Reuse of the existing census gate. Two gate roles (R-5):
  - **Backfill-completeness:** `spec-kitty doctor mission-type --fail-on legacy-key-only`.
  - **Release-safety (M3/M5 non-breakage):** `spec-kitty doctor mission-type --fail-on
    legacy-key-only,typeless,error`. These three states are the unambiguous M3-breakers:
    a legacy-key-only mission becomes type-unresolvable under M5; a typeless
    (blank/missing-both) mission has no type; an `error` mission is unreadable. The
    activation-dependent `unknown` / `activated-unresolvable` states are **deliberately
    excluded** — they are activation-misses that M3 *tolerates* (a profile exists), so
    reding on them would false-block legitimately-M3-safe projects (squad-2 BLOCKER-2).
- Coordination with the existing identity backfill: a new, independently runnable
  `migrate backfill-mission-type` command (R-1) touching a field disjoint from
  `backfill-identity`'s `mission_id`; the two compose order-independently.

## Out of scope (deferred / owned elsewhere)

- The resolution/reader changes themselves (M3 owns the per-type hard-fail; M5 owns the
  reader convergence and the legacy-resolution drop). Converging the two remaining
  `software-dev`-default-substituting readers (`dashboard/handlers/features.py:68`,
  `charter/interview.py:225`) is **M5's** scope.
- **The audit classifier's `unknown`/`activated-unresolvable` re-derivation against M3's
  inverted predicate.** The mission-type audit's `resolved` split is activation-based
  (pre-M3). A pre-existing, hand-authored, present-but-**profile-less** `mission_type`
  (e.g. a typo already written into the field) classifies audit-`unknown` and is therefore
  **not** caught by M0's narrowed release-safety gate — M3's runtime hard-fail catches it.
  M0 never *creates* this state (it only ever writes profile-resolving values). Re-deriving
  the audit against the profile-resolution predicate is a **shared-authority change owned by
  M3** (its spec inverts the runtime probe but does not touch `_mission_type_audit.py`); M0
  flags this drift as an explicit M3 coordination item (see Risks).
- Manual correction of `needs_manual_resolution` / `typeless` residue → operator / later mission.
- Retiring the legacy `mission` field from the `meta.json` schema → later migration.

## Functional requirements

- **FR-001** — Detect candidate missions: `meta.json` where the `mission_type` **key is
  absent** and the legacy `mission` key holds a **non-blank string**
  (`isinstance(raw, str)` guarded, then `canonical_mission_type_key(raw) is not None`).
  This is exactly the canonical audit's `legacy-key-only` state — the backfill's *candidate*
  set. A non-string legacy value never reaches `canonical_mission_type_key` (it is not a
  candidate; it classifies typeless, matching the audit).
- **FR-002** — For a candidate whose `canonical_mission_type_key(mission)` **resolves to a
  governance-profile at any layer** (`MissionTypeProfileRepository.for_project(repo_root)
  .get(key) is not None` — the M3 §B tolerance authority, activation-independent, id-matched;
  the repository is built **once per run**), write `mission_type = canonical_mission_type_key
  (mission)` through the single `charter.mission_type_key.canonical_mission_type_key`
  canonicalizer. Leave any mission that already has a `mission_type` key untouched.
- **FR-003** — Non-resolving candidate: a candidate whose canonical value resolves **no**
  profile at any layer is **skipped** and reported `needs_manual_resolution` (never written,
  never masked).
- **FR-004** — Idempotent: a second run is a no-op (`wrote=0`); a written mission has a
  `mission_type` key and is no longer a candidate.
- **FR-005** — Robust walk: an unreadable/malformed `meta.json`, or **any** per-mission
  failure (including a non-string legacy value that slips a guard), classifies that single
  mission as `error` and never aborts the whole walk (mirrors the audit's
  `classify_mission_type` broad-catch posture).
- **FR-006** — Dry-run/audit mode with `--json` machine output (`wrote` / `skip` /
  `needs_manual_resolution` / `error` counts, per-mission before→after incl. the offending
  slug+reason on error) and a `--mission <slug>` scope. The `--json` schema (keys/shape) is
  **identical** between `--dry-run` and live runs, differing only in count values.
- **FR-007** — Command exit-code contract: a live run exits non-zero iff `error > 0`; a
  `--dry-run` always exits `0`; a clean live run exits `0`. `needs_manual_resolution` does
  **not** by itself fail the command (it is surfaced; the release-safety gate is what blocks
  the release). When the run produces any `needs_manual_resolution`, emit a distinct,
  actionable diagnostic (which missions, and that the fix is a valid mission type / profile,
  not necessarily a typo).
- **FR-008** — `--mission <slug>` naming a directory that does not exist exits non-zero with
  a **structured** "no such mission" error — never a silent `wrote=0` / exit-0 (explicitly
  NOT the sibling backfills' warn-and-return-empty path).
- **FR-009** — The census gate is the existing `spec-kitty doctor mission-type --fail-on`
  (reused, not rebuilt). This mission adds regression coverage proving (a) the
  backfill-completeness gate (`legacy-key-only`) reds before and greens after the backfill,
  and (b) the release-safety gate (`legacy-key-only,typeless,error`) reds while any such
  mission remains and greens once the census is clean — including that a written
  **unactivated** built-in type does NOT keep the release-safety gate red.

## Acceptance criteria

- **AC-1** — After a live backfill over a repo of legacy candidates with profile-resolving
  values, every such mission carries `mission_type`; no `legacy-key-only` mission with a
  resolving value remains.
- **AC-2a** — A mission that already has a `mission_type` key is **skipped**: the writer
  never runs on it and its `meta.json` is byte-for-byte unchanged.
- **AC-2b** — A candidate with a profile-resolving value gains `mission_type: "<key>"`; every
  pre-existing field is preserved (JSON-semantic equality), the file re-serialized via the
  sorted-key `json.dumps` idiom the sibling backfills use (`indent=2, ensure_ascii=False,
  sort_keys=True`) — a canonicalized serialization, not a byte-preserving one.
- **AC-3** — Re-running the backfill reports `wrote=0` (idempotent).
- **AC-4** — A candidate whose value resolves **no** profile (`{"mission":"sofware-dev"}`) is
  **not written** (its `mission_type` key stays absent), is reported
  `needs_manual_resolution`, and — still `legacy-key-only` — keeps both gates red.
- **AC-5** — **The predicate-correctness regression (squad-2 MAJOR-4):** an
  **unactivated-but-profile-bearing** built-in legacy type — `{"mission":"research"}` where
  `research` is NOT in the project's `mission_type_activations` — is **written**
  (`mission_type: "research"`), and the **release-safety** gate
  (`--fail-on legacy-key-only,typeless,error`) **greens** for it. This test fails against the
  rejected `registered ∧ roster` predicate and pins the profile-resolution predicate.
- **AC-6** — Non-string legacy value (`{"mission":123}`) is not a candidate: the walk does not
  crash, that mission classifies `typeless`-equivalently (skipped, never written), and one bad
  mission never aborts the run.
- **AC-7** — `--dry-run --json` and live `--json` payloads carry identical keys/schema,
  differing only in count values.
- **AC-8** — Command exit codes: live run non-zero iff `error > 0`; `--dry-run` always `0`;
  clean live run `0`. `needs_manual_resolution > 0` alone exits `0` (with the FR-007 diagnostic).
- **AC-9** — `--mission <nonexistent-slug>` exits non-zero with a structured error, never
  `wrote=0` / exit-0.
- **AC-10** — Over a mixed repo (≥4 missions: one profile-resolving candidate, one already-typed,
  one non-resolving candidate, one non-string legacy value) a single run reports the correct
  `wrote` / `skip` / `needs_manual_resolution` / `error`-safe partition with per-mission
  before→after.
- **AC-11** — Backfill-completeness gate (`--fail-on legacy-key-only`) reds before backfill,
  greens after (for resolving candidates), proven red→backfill→green through the real
  `doctor mission-type` entry point over a synthetic temp repo.

## Key design decisions

- **One canonicalizer:** `canonical_mission_type_key` (`src/charter/mission_type_key.py`) —
  the same authority every canonical/typeless-aware reader (incl. M5's `read_mission_type()`)
  and the audit consume.
- **One tolerance authority:** `MissionTypeProfileRepository` — the same per-type,
  id-matched, cross-layer profile resolver M3 §B uses. The writer's write-vs-skip decision
  agrees with M3 by construction, not with the activation-based audit split.
- **Reused gate, corrected states:** the release-safety predicate is `legacy-key-only,
  typeless,error` (the M3-breakers M0 can guarantee), NOT the activation-dependent
  `all-but-resolved` (which false-blocks).

## Resolved decisions

- **R-1 — Dedicated `migrate backfill-mission-type` command** in a new
  `src/specify_cli/migration/backfill_mission_type.py` domain module + a `migrate_cmd.py`
  command, structured after the **single-field** `backfill_topology.py` sibling (NOT the
  two-dimension `backfill_identity.py`). It must NOT copy topology's coordination-branch git
  probe (irrelevant here) and MUST lift `backfill_identity`'s dossier-rehash pass (topology
  has none): rehash written missions via the existing `trigger_feature_dossier_sync_if_enabled`
  wrapper, gated on `action == "wrote" and not dry_run`, capturing failures as a
  `dossier_warning` result field (never aborting). Independently runnable; composes
  order-independently with `backfill-identity` (disjoint field, whole-file canonical rewrite
  preserves the other's field on sequential runs).
- **R-2 — Reuse the existing census gate; no second gate, no audit-classifier change.** The
  gate is `spec-kitty doctor mission-type --fail-on <states>`
  (`src/specify_cli/cli/commands/_mission_type_audit.py`, `doctor.py:533`). M0's contribution
  is regression proof + the documented release-safety predicate. The audit's activation-based
  `unknown`/`activated-unresolvable` split is left to M3 (see Out of scope / Risks).
- **R-3 — Detection authority = the audit's `legacy-key-only` boundary, reproduced from the
  charter canonicalizer only** — `MISSION_TYPE_KEY not in meta and isinstance(meta.get(
  LEGACY_MISSION_KEY), str) and canonical_mission_type_key(meta[LEGACY_MISSION_KEY]) is not
  None` — importing only `charter.mission_type_key`, never the CLI classifier. A
  **cross-authority test** (test layer) pins agreement over a corpus that **includes** a
  present-but-blank `typeless` mission AND a **non-string** legacy value, asserting the writer
  skips both while the audit reports `typeless` (non-vacuous).
- **R-4 — Resolve-before-write via the profile-resolution authority; never manufacture an
  M3-breaker.** The writer writes only when `MissionTypeProfileRepository.get(key)` resolves a
  profile; genuine typos / profile-less types → `needs_manual_resolution`. The write decision
  is pinned by a test against the profile repository (the M3 authority), and by AC-5 (the
  unactivated-built-in regression).
- **R-5 — Two gate roles, one gate, corrected states.** Completeness = `legacy-key-only`;
  release-safety = `legacy-key-only,typeless,error`. Documented in the changelog/PR as the
  predicate the M3/M5 release pipeline runs, with the residual `unknown`-typo gap called out.

## Risks / blast-radius

- Consumer projects must run this before upgrading to the rc that carries M3+M5 — document
  the ordering and the release-safety predicate (R-5) in the release notes.
- Must not alter a mission that already has a `mission_type` key (AC-2a byte-identity guard).
- Must not manufacture an M3-breaker (AC-4 / AC-5 / R-4).
- **Audit-classifier drift (M3 coordination).** The audit's `unknown`/`activated-unresolvable`
  states encode pre-M3 (activation) tolerance; after M3 §B inverts runtime tolerance to
  profile-resolution, the audit will over-predict hard-fail for unactivated-but-profile-bearing
  types. M0's narrowed gate side-steps this for its own release-safety role, but the audit
  should be re-derived against the profile-resolution predicate **in M3** (which owns #3598).
  Flagged as an explicit M3 coordination item; M0 does not edit the shared classifier.
- **Whole-file canonical rewrite** re-orders/reformats every written `meta.json` (sorted keys)
  → a large but semantically-null git diff; JSON-semantic equality of pre-existing fields is
  preserved (stdlib `json` round-trip). One changelog sentence so consumers aren't surprised.
- **`error > 0` from unrelated legacy dirs.** A single corrupt/hand-edited `meta.json` in an
  archived mission makes the whole command exit non-zero (correct fail-closed); the `--json`
  `results[]` names the offending slug+reason, and the changelog notes `--mission` scoping.

## Issues

- **Program gate for:** M3 (`rc3-charter-gate-predicate-inversion-01M0GGT1`; #3596 / #3598)
  and M5 (`rc3-canonical-mission-type-reader-01M0GGWM`; #3598 dec#2, reader convergence).
- **M3 coordination:** re-derive the mission-type audit's `unknown`/`activated-unresolvable`
  split against #3598's profile-resolution predicate (audit-classifier drift, above).
- **Related:** `migrate backfill-identity` (mission_id only, today).

## See also

- rc3 program overview / approach: `docs/plans/initiatives/rc3-friction-burndown/`.
