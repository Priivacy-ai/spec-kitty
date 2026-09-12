# Research: Annoying Bugs Sweep

## R1 - Resolve C-002 at seed construction

**Decision**: Clamp every backfill seed for an already-active WP below that WP's earliest existing
transition or annotation under the reducer's exact `(at, event_id)` comparator. Keep the global
reducer unchanged.

**Rationale**: Transitions determine the lane, while annotations fold in a later dedicated pass and
determine runtime slots. A safe migration seed must precede both histories. This fixes the defect at
its owner, applies uniformly to all five `cutover_mission` callers, and preserves rollback precedence.

**Alternatives considered**:

- Seed suppression: rejected because it drops `shell_pid`, `shell_pid_created_at`, and `agent`.
- Reducer precedence for migration actors: rejected because it changes every mission's state machine
  for a migration-only fault and still needs separate annotation reasoning.
- Verify-only hardening: rejected because cutover writes before verify; verification cannot prevent
  the transient corrupt reduction.

## R2 - Keep verification independent enough to detect builder mistakes

**Decision**: Continue exact deterministic-row verification, but add legacy-reader-derived,
per-slot snapshot witnesses for the three claim-borne values.

**Rationale**: `_has_snapshot_runtime` succeeds when any of twelve slots is present, and expected
seed rows are rebuilt by the same builder that writes them. Exact checks for the three legacy values
give the verifier an independent witness without rejecting later legitimate annotations for other
slots.

**Alternatives considered**:

- Treat `verify_backfill.ok` as sufficient: rejected as near-tautological.
- Require the whole snapshot to equal legacy state: rejected because later runtime state is valid.

## R3 - Pure-Python dead-code reference search

**Decision**: Replace external `grep` with deterministic Python file traversal and text search. Keep
the existing substring exclusion (`"test" not in path`) and relative-path comparison semantics.

**Rationale**: This works on Windows, outside Git for the reference-search phase, and includes
untracked/ignored Python files as the current filesystem scan does. It can preserve the existing
symbol result set on this repository.

**Alternatives considered**:

- `git grep`: rejected as the primary because it misses untracked/ignored files, needs submodule
  handling, and exits outside a work tree. It also does not fix vacuous symbol discovery.
- `shutil.which("grep")` plus fallback: rejected because parallel raw subprocess calls can bypass the
  guard and the test would not prove portability.

## R4 - Honest discovery verdict

**Decision**: Separate `clean`, `findings`, and `undeterminable`. A failed Git diff, an unsupported
source layout/language, or a discovery set that cannot establish its denominator emits a structured
finding and never prints the clean-zero message.

**Rationale**: Zero public symbols is a valid clean result only after successful examination of a
supported change set. This distinction directly closes FR-015.

**Alternatives considered**:

- Scan only `src/**/*.py`: rejected because it preserves the false clean on other layouts.
- Universal polyglot symbol extraction: rejected as unbounded scope for this bug mission.

## R5 - Canonical profile mechanics live in references

**Decision**: Keep `spk-doctrine-profile-load/SKILL.md` below the canonical skill length ceiling and
place detailed mechanics in `references/`, using the existing `CanonicalSkill.references` mechanism.
Legacy `ad-hoc-profile-load` points toward the canonical skill; it does not remain the sole detailed
authority.

**Rationale**: This fixes the authority direction without a 13-alias convention migration.

## R6 - Help epilog, not a new command

**Decision**: Add the `spec-kitty dispatch` opener pointer to the `profile-invocation` Typer epilog.

**Rationale**: The completion manifest excludes epilog data, so discoverability improves without
minting an alias or regenerating unrelated command metadata.

## R7 - Mission classification

**Decision**: Normal mission; no `occurrence_map.yaml`.

**Rationale**: The similarly worded status examples have different meanings and require per-site
judgment. The mission is five bounded defect fixes, not a uniform occurrence migration.

