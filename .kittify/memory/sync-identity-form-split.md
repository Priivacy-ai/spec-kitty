# Sync/Dossier Producer–Consumer Identity-Form Split

**Why it's here:** the mismatch below has already caused at least one silent-miss bug
(fixed by the alias-set match this note describes); the fix pattern is non-obvious
enough — and easy to regress by reintroducing a naive equality compare — that it is
worth recording as a standing gotcha rather than re-discovering it from a stack trace.

## The fact

On the sync/dossier/charter-lint surface, mission identity is produced and consumed in
**two different forms** that do not compare equal:

- **Consumer side** — dossier-sync namespacing keys by the **canonical directory name**
  (`feature_dir.name`), not the raw human-typed slug. `cli/commands/research.py` and
  `cli/commands/agent/mission_record_analysis.py` both deliberately re-key
  `mission_slug = feature_dir.name` for this reason.
- **Producer side** — `charter lint --mission <X>` stores whatever handle the operator
  typed **verbatim** as `feature_scope` (`sync/lint_report_staging.py`); `<X>` may be a
  bare mid8, a numeric prefix, or a slug — any of which can differ from
  `feature_dir.name`.

A naive `feature_scope == mission_slug` compare therefore silently misses matches.

## The seam

The canonical fix is to match `feature_scope` against the mission's full **alias set**, not a
single field. `specify_cli.mission_metadata.resolve_mission_identity(feature_dir)` returns the
core identity (`mission_slug`, `mission_number`, `mission_type`, `mission_id`); the full alias
set — adding `feature_dir.name` and deriving `mid8 = mission_id[:8]` — is assembled by
`specify_cli.sync.lint_report_staging._mission_alias_set` (which calls `resolve_mission_identity`
as its component). Match against that alias set. These seams already exist and are reused across
the sync surface (e.g. `sync/events.py:_resolve_mission_id_for_slug` uses
`resolve_mission_identity(feature_dir).mission_id`) — do not hand-roll a new resolver; extend
callers to use them.

Related, not restated here: `src/doctrine/missions/*/expected-artifacts.yaml` vs
`src/specify_cli/missions/*/expected-artifacts.yaml` carry a similar split-brain risk
(only the `specify_cli` tree is load-bearing for dossier `ManifestRegistry` lookups).
