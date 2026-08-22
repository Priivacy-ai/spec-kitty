# Mission Specification: Cascade Org Inert

**Mission Branch**: `pr/up-cascade-org-inert`
**Created**: 2026-08-17
**Status**: Draft
**Input**: GitHub issue [#3527](https://github.com/Priivacy-ai/spec-kitty/issues/3527) — `charter activate/deactivate --cascade` loads its DRG org-inert (org-pack `requires`/`suggests` never cascade-activate)

## Base-Branch Drift *(mandatory — read before reviewing anything else in this spec)*

This mission's branch, `pr/up-cascade-org-inert`, is **not** based on `main`. It is based on
`origin/pr/up-org-doctrine-consumers-01M05YAB` (PR #3520, head commit `5a8fc1b74`, green CI,
currently awaiting operator merge).

Verified: `git merge-base pr/up-cascade-org-inert origin/pr/up-org-doctrine-consumers-01M05YAB`
= `5a8fc1b74d2214c18369dd0e2822b4ca2e88c30f`, which is the head of PR #3520. `git log --oneline`
on this branch shows PR #3520's commits (`5a8fc1b74`, `b79b500cf`, `ba16bce15`, `2abbb95a5`,
`31512c9bf`, `1906c5303`, …) immediately below this mission's own scaffold commit (`4e266b2c0`).

Reason for the dependency: the fix this issue prescribes threads
`doctrine.drg.org_pack_config.resolve_existing_org_roots` into three call sites. That
module/function is **verified absent** from `src/doctrine/drg/org_pack_config.py` on `main`
(confirmed via `git show main:src/doctrine/drg/org_pack_config.py`, which does not define
`resolve_existing_org_roots`) — it is introduced by #3520/#3525's commits. `src/charter/_drg_helpers.py`
(which *consumes* the symbol, and is where `load_validated_graph` and `_resolve_org_root` live)
also changes substantially between `main` and this branch, so both files are worth diffing — but
only `org_pack_config.py` is where the symbol itself is missing. This mission cannot be built
against `main` as it stands today.

Three consequences, stated explicitly so no reviewer or future agent has to rediscover them:

1. **This PR cannot merge before #3520 merges.** Its diff is only meaningful, and its target
   commit history is only clean, once #3520 has landed on `main`. Opening this PR against `main`
   before that point would either fail to apply or silently re-introduce #3520's changes as if
   they were this mission's own work.
2. **Reviewers will see #3520's five (plus) commits in this branch's diff** until #3520 lands.
   This is expected and is not scope creep by this mission — do not ask the implementer to
   "trim" those commits out; they are the dependency, not part of this mission's authored change.
3. **If #3520 is rejected or substantially reworked, this mission's base disappears** and this
   mission needs to be re-planned from whatever new base carries (or fails to carry)
   `resolve_existing_org_roots` and the multi-pack DRG chain support. The plan phase must
   re-verify the base is still valid immediately before starting implementation, not assume this
   spec's snapshot of the dependency graph is still accurate.

## Out of Scope

**Malformed-org-pack degrade behavior (formerly "Item 4", scoped as a fourth functional requirement in an earlier draft and since retired) is explicitly
NOT this mission's responsibility.** An earlier draft of this spec scoped a fourth item: the
asymmetry in `src/charter/_drg_helpers.py::load_validated_graph` between the project branch's
lenient `has_graph_files` pre-check and the org branch's bare `.exists()` guard, and the resulting
whole-bundle silent collapse when a configured org pack has no loadable graph (live-reproduced
during this mission's own investigation: `directive_ids=0, tactic_ids=0, styleguide_ids=0,
toolguide_ids=0, procedure_ids=0`, all five doctrine-kind counts, from a single malformed org
pack). **That defect is real, but it is already fixed in open PR
[#3401](https://github.com/Priivacy-ai/spec-kitty/pull/3401)** ("fix(charter): guard org-pack DRG
root load and surface malformed org content", mission `org-pack-drg-root-graph-guard-01KZY0QT`,
closes [#3384](https://github.com/Priivacy-ai/spec-kitty/issues/3384)) — verified OPEN via `gh pr
view 3401`; its own description states "An org pack with no loadable graph now degrades to 'no org
DRG layer' instead of raising a swallowed `DRGLoadError` — the same guard the project layer already
applied," and its implementation touches exactly `src/charter/_drg_helpers.py` and
`src/charter/action_doctrine_bundle.py` (comment-only) — the same seam this mission's now-retired
fourth requirement would have touched.

**Deliberately not duplicated here**, per this mission's own Governing Principles (single canonical
authority — reconcile, don't add a second fix for the same defect on the same lines, which would
conflict with #3401 rather than complement it). This mission's remaining three FRs (FR-001, FR-002,
FR-003) thread `resolve_existing_org_roots` into call sites that previously carried NO org roots at
all — a **different, orthogonal** defect class from #3401's "org root present but its graph content
is malformed" case. Concretely: before this mission's fix, a malformed org pack was invisible to
the three cascade sites and the context JSON path (org root was always `None`/`[]`, so
`load_validated_graph`'s org branch never ran at all) — after this mission's fix threads a real org
root in, a malformed pack becomes REACHABLE for the first time at these sites, and will exhibit
whatever `load_validated_graph`/`_load_action_doctrine_bundle` do TODAY on this branch (raises
`DRGLoadError`, uncaught by these call sites) until #3401 merges — **exactly the same behavior
every other current caller of `load_validated_graph` already has** (e.g. `gate_bindings.py`, which
already threads `resolve_existing_org_roots` and has the same exposure). This is not a regression
this mission introduces relative to the rest of the codebase's current state; it is the honest,
disclosed status quo of the DRG-loading subsystem, and #3401 is the tracked, in-flight fix for it —
not this mission's job to duplicate. Every acceptance criterion below that touches the
"malformed pack" case states this explicitly rather than silently assuming graceful degrade.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operator runs `charter activate --cascade` with org-pack doctrine (Priority: P1)

An operator running a project with one or more org doctrine packs configured (`.kittify/config.yaml`
org-pack entries) runs `spec-kitty charter activate <kind> <id> --cascade all`, expecting every
artifact the activated one `requires`/`suggests` — wherever it lives in the doctrine chain,
built-in, project, or org-pack — to cascade-activate along with it, and expecting
`referenced_but_not_cascaded` to warn about anything the scope excluded.

Today, because the three cascade call sites walk `load_validated_graph(repo_root)` with no org
roots, any `requires`/`suggests` edge that lives in (or targets) an org pack is invisible to the
cascade engine. The operator's cascade activation silently under-activates: dependent org-pack
artifacts are neither activated nor flagged as skipped-by-scope, because the DRG the cascade
engine walks never contained them in the first place.

**Why this priority**: This is the exact defect class PR #3520 already fixed for the
`review/gate_bindings` runtime seam — leaving `activate`/`deactivate` (themselves runtime operator
commands, not charter-build-time) unfixed means an operator's own explicit `--cascade` request is
silently incomplete, with no error, no warning, and no reduced-scope notice. It directly
undermines the primary reason the command exists.

**Independent Test**: Configure a project with one org pack containing an artifact `A` with a
`requires` edge to artifact `B` (also in the org pack). Run `charter activate <kind-of-A> <A>
--cascade all`. Before the fix: `B` is not activated and does not appear in the
`referenced_but_not_cascaded` report. After the fix: `B` is activated as part of the same cascade
run.

**Acceptance Scenarios**:

1. **Given** a project with a single healthy org pack and an artifact `A` in that pack with a
   `requires` edge to artifact `B` in the same pack, **When** the operator runs `charter activate
   <kind-of-A> <A> --cascade all`, **Then** `B` is activated in the same run and reported as
   activated (not skipped).
2. **Given** a project with two chained org packs (pack 1 → pack 2, per #3525's multi-pack DRG
   support) where artifact `A` (pack 1) `requires` artifact `C` (pack 2), **When** the operator
   runs `charter activate <kind-of-A> <A> --cascade all`, **Then** `C` is activated — proving the
   fix walks the *full* chain, not just the first configured org root.
3. **Given** a project with no org pack configured at all, **When** the operator runs `charter
   activate <kind> <id> --cascade all` over built-in/project-only doctrine, **Then** behavior is
   unchanged from today (no regression for the org-inert case — `resolve_existing_org_roots`
   returns an empty list and `load_validated_graph` proceeds project/built-in-only exactly as
   before).
4. **Given** an org pack directory that is configured but malformed (exists on disk, has no
   `graph.yaml`/`*.graph.yaml` fragment), **When** the operator runs `charter activate --cascade`,
   **Then** this mission does NOT change today's behavior for that case — see "Out of Scope" above.
   `--cascade` will raise `DRGLoadError` uncaught, the same as every other current
   `load_validated_graph` caller with org roots threaded in (e.g. `gate_bindings.py`); this is a
   disclosed, accepted status-quo exposure this mission's own fix newly makes reachable at this
   call site (previously unreachable because org roots were never threaded), not a regression this
   mission is required to prevent. PR #3401, once merged, fixes this for every caller including
   this one — this mission does not duplicate that fix.

---

### User Story 2 - Operator runs `charter deactivate --cascade` with org-pack doctrine (Priority: P1)

The deactivate mirror of User Story 1: an operator deactivating an artifact with `--cascade`
expects exclusive dependents anywhere in the doctrine chain (including org packs) to be
deactivated too, and shared dependents (still referenced by another active artifact) to be
reported and kept — never silently removed, per the existing C-005 shared-reference-safety
contract.

**Why this priority**: Same defect class and same call-site pattern as User Story 1
(`deactivate.py:139`); an incomplete deactivate cascade leaves orphaned org-pack artifacts active
that the operator believed were being cleaned up together.

**Independent Test**: Configure a project with one org pack; activate artifact `A` and its
exclusive dependent `B` (org pack) together. Run `charter deactivate <kind-of-A> <A> --cascade
all`. Before the fix: `B` stays active (untouched, unreported). After the fix: `B` is deactivated
in the same run.

**Acceptance Scenarios**:

1. **Given** a single healthy org pack with `A` requiring `B` (both active, `B` exclusively
   referenced by `A`), **When** the operator runs `charter deactivate <kind-of-A> <A> --cascade
   all`, **Then** `B` is deactivated in the same run.
2. **Given** a two-pack chain where `A` (pack 1) exclusively requires `C` (pack 2), **When** the
   operator deactivates `A` with `--cascade all`, **Then** `C` is deactivated too.
3. **Given** `B` (org pack) is required by both `A` (being deactivated) and another still-active
   artifact `D`, **When** the operator deactivates `A` with `--cascade all`, **Then** `B` is
   reported as a kept shared dependent (naming `D` as the still-referencing source) and is **not**
   deactivated — the existing C-005 contract must continue to hold once org roots are threaded in.
4. **Given** no org pack configured, **When** the operator deactivates with `--cascade all` over
   built-in/project-only doctrine, **Then** behavior is unchanged from today.

---

### User Story 3 - Operator resolves a cascade-engine bare ID back to a config-stem ID across a multi-pack chain (Priority: P2)

`_drg_id_to_config_id` (used by both `activate.py` cascade renderers) needs `resolve_layer_roots`'s
`"org"` slot to map a cascade-engine bare ID back to the config-stem ID the activation seam
expects. Today `resolve_layer_roots` takes only the *first* org root (`break` after one iteration)
into a single-value `dict[str, Path]` slot, so ID-mapping for any artifact whose owning pack is
pack #2 or later in a configured chain is silently wrong or fails.

**Third consumer, verified live**: `resolve_layer_roots` has a THIRD call site beyond the two
cascade renderers — `src/specify_cli/cli/commands/charter/list_cmd.py:165` (inside `charter list
--all-layers`), which feeds `layer_roots["org"]` into both `_template_tier_roots` (list_cmd.py:64,
77) and `CharterPackManager.list_available_detailed(..., layer_roots=layer_roots)`
(`src/charter/pack_manager.py:784`, documented signature `layer_roots: dict[str, Path] | None` —
one `Path` per layer, not a list). This mission does **not** widen `charter list --all-layers`'s
own multi-pack display — that is a separate, display-only concern (pack-2+ availability rendering
in `charter list`, not cascade-activation correctness) and out of issue #3527's filed scope; fixing
it would require touching `pack_manager.list_available_detailed`'s consumption contract too, which
is a larger, separately-reviewable change. Explicitly scoped out here, not silently discovered
later: **the plan phase's chosen shape for `resolve_layer_roots`'s widened return value MUST keep
the existing `roots["org"]` key holding a single representative `Path` (pack 1, unchanged) for
`list_cmd.py`'s continued back-compat consumption**, and add the full chain under a NEW key (e.g.
`roots["org_chain"]: list[Path]`) that only the two cascade call sites and `_drg_id_to_config_id`
consume. This mirrors the established `effective_org_root` (back-compat single value) /
`effective_org_roots` (full chain) dual-field pattern already used by
`charter.action_doctrine_bundle._resolve_action_bundle`. A follow-up issue should be filed by the
plan or implementation phase to widen `charter list --all-layers` to the full chain later; this
mission's SC list and regression tests do not cover `list_cmd.py`'s own multi-pack *display*, only
that it does not regress (still shows pack 1, same as before).

**Why this priority**: This is a distinct mechanism from Item 1's cascade-graph-visibility gap
(User Stories 1–2) — even once the DRG walk sees pack 2..N, the ID-mapping step that turns a
resolved cascade target back into an activatable config ID still only consults pack 1. Both must
be fixed together for a multi-pack chain to cascade-activate correctly end to end.

**Independent Test**: Configure a two-pack chain where an artifact whose config-stem ID lives only
in pack 2 is reached via cascade from an artifact in pack 1. Confirm `_drg_id_to_config_id`
resolves it correctly (not `None`/wrong) only once `resolve_layer_roots` stops breaking after the
first org root. Separately, confirm `charter list --all-layers` over the same two-pack chain still
renders (pack-1-only, unchanged) without a type error or crash — the back-compat regression check
for the third consumer.

**Acceptance Scenarios**:

1. **Given** a two-pack org chain, **When** `resolve_layer_roots(repo_root)` is called, **Then**
   its returned org-root data reflects the full chain via a NEW field (not just pack 1) — the
   exact key/shape is left to the plan phase, but "pack 2's roots are reachable through some field"
   is the falsifiable requirement, and the existing `roots["org"]` key's value (a single `Path`)
   is unchanged, for `list_cmd.py`'s back-compat.
2. **Given** a single-pack config, **When** `resolve_layer_roots` is called, **Then** behavior for
   pack 1 alone is unchanged (no regression for the already-working single-org-pack case).
3. **Given** no org pack configured, **When** `resolve_layer_roots` is called, **Then** it returns
   the same project-only (or empty) result as today.
4. **Given** a two-pack org chain, **When** `charter list --all-layers` is run (the third,
   out-of-scope consumer), **Then** it does not crash or raise a type error — `roots["org"]` still
   resolves to a single `Path` exactly as before the fix (regression-only check; pack-2 display
   in `charter list` itself is explicitly NOT required by this mission).

---

### User Story 4 - Operator runs `charter context` (both the plain-text AND JSON paths) with org-pack doctrine (Priority: P2)

An operator or automation caller invoking `spec-kitty charter context --action <name>` (plain text)
or `--json` (structured) expects the returned action-doctrine bundle to reflect the *full*
org-pack chain, matching the already-fixed behavior of the sibling self-resolving wrapper
`_resolve_action_bundle`.

**Corrected scope (was wrong in an earlier draft of this spec)**: the truncation is NOT
JSON-output-only. It originates in the CLI command itself —
`src/specify_cli/cli/commands/charter/context.py:84-85` computes ONE truncated `org_root =
org_roots[0] if org_roots else None` and passes that SAME truncated value into **both**
`build_charter_context` (plain-text, line 117) and `build_charter_context_json` (JSON, line 132).
`build_charter_context` already routes through `_resolve_action_bundle`
(`src/charter/context.py:270`) — the established self-resolving wrapper — but `_resolve_action_bundle`
only self-resolves the full chain when its caller passes `org_root=None`; an *explicit*
(already-truncated) `org_root` is "honoured verbatim and does not widen into the chain"
(`src/charter/action_doctrine_bundle.py:96-99`, docstring). So **the plain-text path is truncated
to pack 1 today too**, by the same root cause, despite already using the "correct" wrapper.
`build_charter_context_json` has a SECOND, independent defect on top of this: it calls the
private `_load_action_doctrine_bundle` directly (bypassing `_resolve_action_bundle` entirely), so
even if the CLI stopped truncating, the JSON path would still need its own fix to route through
`_resolve_action_bundle` (or replicate its self-resolution) for the widening to take effect.

**Why this priority**: Lower priority than Item 1 because it is not the issue's own filed scope
(it surfaced in the issue's comment thread), but it affects BOTH the plain-text and JSON `charter
context` paths (see correction above) and is the same defect class as Item 1, with a small fix.

**Independent Test**: Configure a two-pack chain where doctrine content relevant to `--action
specify` lives only in pack 2. Call `build_charter_context_json(..., action="specify", ...)` AND
separately `build_charter_context(..., action="specify", ...)` (the plain-text path, reached via
the `context()` CLI command with no `--json`). Before the fix: pack-2 content is absent from
BOTH. After the fix: present in both.

**Acceptance Scenarios**:

1. **Given** a single healthy org pack, **When** `context()`/`build_charter_context`
   (plain-text) or `build_charter_context_json` (JSON) builds the doctrine bundle for an action,
   **Then** org-pack doctrine for that action is included in both (already works today for pack 1
   — must not regress).
2. **Given** a two-pack chain, **When** either call is made, **Then** doctrine content owned by
   pack 2 is present — in the JSON bundle's `directive_ids`/`tactic_ids`/etc. AND in the plain-text
   rendered output.
3. **Given** no org pack configured, **When** either call is made, **Then** behavior is
   unchanged (`org_root=None`, `org_roots=None` or `[]`, built-in/project doctrine only).
4. **Given** a malformed org pack in the chain, **When** either call is made, **Then** this mission
   does NOT change today's whole-bundle-collapse behavior for that case — see "Out of Scope" above.
   `_load_action_doctrine_bundle`'s existing `except DRGLoadError` catch (which already logs a
   WARNING but discards the entire bundle, not just the org tier) is unchanged by this mission;
   PR #3401 is the tracked, in-flight fix for that collapse, and this mission does not duplicate
   it. FR-002's own fix (threading the full org-pack chain instead of truncating to pack 1) neither
   worsens nor improves this pre-existing behavior — a malformed pack still collapses the whole
   bundle exactly as it does today, before and after FR-002 lands.
5. **Given** the CLI command `context()` itself, **When** it resolves `org_roots` for a multi-pack
   chain, **Then** it no longer pre-truncates to `org_roots[0]` before calling
   `build_charter_context`/`build_charter_context_json` — it passes `org_root=None` through so the
   charter-layer self-resolution (`_resolve_action_bundle`'s `if effective_org_root is None`
   branch) performs the widening, while the separately-computed full `org_roots` list is still used
   unchanged for `load_org_charter_json_block(org_roots)` (a different, already-correct consumer).

---

### User Story 5 - Dossier rebaseline stays correct when org doctrine is configured (Priority: P3)

An operator running `spec-kitty migrate rebaseline` (or any future caller of
`rebaseline_recorded_snapshots`) over a project with org-pack doctrine configured expects the
rebaseline to be aware of that org configuration, consistent with every other doctrine-consuming
surface in the codebase, rather than silently falling back to "no org lookup, built-in manifest
tree only" — the current default for every caller that does not supply `repo_root` to `Indexer`.

**Why this priority**: Lowest priority of the five items — it is not in the issue's filed scope
either (also surfaced in the comment thread), has exactly one production caller today
(`migrate_cmd.py`), and is not on the operator's cascade-activation critical path. Included because
the issue explicitly asked for it and because leaving it silently org-blind is the same defect
class as the rest of this mission.

**Independent Test**: Configure a project with an org pack that affects manifest/doctrine
resolution. Record a snapshot, then run rebaseline. Confirm the org pack is consulted (per FR-003's
chosen derivation) rather than silently ignored.

**Acceptance Scenarios**:

1. **Given** a single-repo project with a healthy org pack, snapshots recorded under
   `kitty-specs/<slug>/.kittify/dossiers/<slug>/snapshot-latest.json`, **When**
   `rebaseline_recorded_snapshots(repo_root, ...)` runs via `migrate_cmd.py`'s
   `locate_project_root()`-derived `repo_root`, **Then** the org pack is consulted during
   reindexing (not silently skipped).
2. **Given** no org pack configured, **When** rebaseline runs, **Then** behavior is unchanged from
   today (org-agnostic reindex, matching pre-fix behavior for the org-inert case).
3. **Given** a malformed org pack, **When** rebaseline runs, **Then** it does not crash the
   operator's `migrate` command outright — degrade behavior deferred to the plan phase, but must
   not be an unhandled exception surfaced as a stack trace to the operator.

Note (not a numbered acceptance scenario — see FR-003's Design Notes / Recommendations for the
full statement): whether a snapshot recorded inside a spec-kitty execution worktree resolves
`repo_root` correctly is an open question the plan phase must investigate and resolve before
implementing FR-003, not a pass/fail assertion this spec can state as a scenario.

---

### Edge Cases

- What happens when `--cascade` is run in a project with **zero** org packs configured? Every
  fixed call site must be a no-op change in this case — `resolve_existing_org_roots(repo_root)`
  returns `[]`, and `load_validated_graph` proceeds exactly as it does today (project + built-in
  only). This is a required regression check for every FR in this spec, not just a nice-to-have.
- How does the system handle a **malformed** org pack (directory exists, no graph fragment) mid-
  cascade or in a context-bundle load? Out of scope for this mission — see "Out of Scope" above.
  Behavior is unchanged from today (raises `DRGLoadError` uncaught at the cascade sites now that
  org roots are threaded; collapses the whole action-doctrine bundle at the context path, exactly
  as it already does for every other current caller). PR #3401 is the tracked fix; not duplicated
  here.
- What happens to a mission that already ran `charter activate --cascade` under the old
  (org-inert) behavior, before this fix ships? See the Reflexivity section below — answered
  explicitly, not left implicit.
- What happens when the *first* org root in a chain is malformed but a *later* root in the same
  chain is healthy? Out of scope for this mission (same "Out of Scope" note) — today, the whole
  bundle/walk is affected by the one malformed root regardless of position in the chain; this
  mission does not change that, and #3401 is the tracked fix for it, not this mission's job.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Thread org roots into the three cascade `load_validated_graph` call sites and widen `resolve_layer_roots` past its first-match break (back-compat-preserving for its third, out-of-scope consumer `charter list --all-layers`) | As an operator running `charter activate/deactivate --cascade`, I want cascade to see `requires`/`suggests` edges that live in or target any configured org pack (not just none, not just the first of a chain), so that `--cascade` does not silently under-activate/under-deactivate doctrine. | High | Open |
| FR-002 | Stop `context.py`'s CLI command from pre-truncating `org_root` to pack 1, and route `build_charter_context_json`'s internal call through `_resolve_action_bundle` (both changes required — neither alone fixes the chain) | As an operator or automation caller of `spec-kitty charter context` (plain-text) or `--json`, I want the returned action-doctrine bundle to reflect the full configured org-pack chain (not just the first pack), consistent with every other doctrine-context consumer, so that doctrine content owned by pack 2..N is not silently invisible to either call path. | Medium | Open |
| FR-003 | Make dossier rebaseline org-aware, deriving `repo_root` per-snapshot | As an operator running `migrate rebaseline` on a project with org-pack doctrine configured, I want the reindex to consult the org pack (not silently fall back to built-in-only), derived independently for each snapshot so a future multi-repo backlog caller cannot get one snapshot's org config applied to another's. | Medium | Open |

**The fourth functional requirement is retired.** An earlier draft numbered a fourth FR here for the malformed-org-pack
whole-bundle-collapse defect. That defect is real but already fixed in open PR #3401 (see
"Out of Scope" above); this mission does not duplicate it. The ID is retired, not reused, so no
later FR silently inherits stale cross-references to it. The retired identifier is
deliberately not spelled out anywhere in this document — see the note below.

> **Why the retired identifier is not written out.** `finalize-tasks`' requirement-coverage
> check extracts requirement IDs with a single document-wide regex, so any literal mention of
> a retired ID — even inside a notice explaining that it is retired — is counted as an active,
> unmapped requirement and hard-blocks finalization. The retirement is recorded here in prose,
> and the real handles (#3401, #3384) are unaffected. Tracked as ledger SK-51; same defect class
> as #3519.


#### FR-001 Acceptance Criteria

1. **Healthy single-pack config**: with one org pack configured and healthy, `charter activate
   <kind> <id> --cascade all` and `charter deactivate <kind> <id> --cascade all` both see and act
   on `requires`/`suggests` edges into/out of that pack. Regression baseline: behavior for
   built-in/project-only edges is unchanged.
2. **Multi-pack chain**: with a two-pack chain configured, both commands see and act on edges that
   only resolve through pack 2 (not just pack 1). This requires both the `load_validated_graph`
   org-roots threading *and* `resolve_layer_roots`'s ID-mapping fix (User Story 3) — a test must
   cover an artifact whose config-stem ID lives only in pack 2, cascaded from pack 1.
3. **Malformed pack — explicitly out of scope, not a regression to prevent**: with a
   configured-but-malformed org pack (exists, no graph fragment) in the chain, `--cascade` MAY
   raise an unhandled `DRGLoadError` to the operator's terminal — this mission does not change that
   behavior (see "Out of Scope"). No test asserting graceful degrade is required for this AC; a
   test MAY assert the malformed-pack case does not silently succeed with wrong data (i.e., loud
   failure is acceptable, silent wrong-data is not), consistent with NFR-002.
4. **No org pack at all**: with zero org packs configured, both commands' cascade behavior is
   byte-for-byte unchanged from pre-fix behavior (this is a required regression test, not merely
   an assumption).
5. `_render_no_cascade_warning`'s `referenced_but_not_cascaded` report correctly names org-pack
   artifacts that were referenced but excluded by scope — proving the DRG it warns from now
   contains org-pack nodes at all (pre-fix, it structurally could not, since org roots were never
   loaded).
6. `_resolve_org_root` in `src/charter/_drg_helpers.py` is **not modified** by this fix — it
   remains intentionally inert per its own docstring and the architectural boundary enforced by
   `tests/architectural/test_layer_rules.py`. The fix is entirely in the three CLI-layer callers
   and `resolve_layer_roots`.
7. **Third consumer regression (`charter list --all-layers`)**: `resolve_layer_roots`'s widened
   return value preserves the existing `roots["org"]` key as a single `Path` (pack 1) so
   `list_cmd.py:165` and `CharterPackManager.list_available_detailed`/`_template_tier_roots` keep
   working unchanged — `charter list --all-layers` over a multi-pack chain does not crash or
   type-error post-fix (User Story 3, Acceptance Scenario 4). Widening `charter list --all-layers`'s
   own display to show pack 2+ availability is explicitly OUT of this mission's scope; a follow-up
   tracker issue should be filed for it, not silently left undiscovered.

#### FR-002 Acceptance Criteria

1. **Healthy single-pack config**: `context()` → `build_charter_context` (plain-text) AND →
   `build_charter_context_json` (JSON) both include org-pack-1 doctrine for the requested action
   (already works today for pack 1 — regression check, both paths).
2. **Multi-pack chain**: BOTH calls include doctrine owned by pack 2 (currently absent from
   both — see the corrected User Story 4 scope note). This requires TWO changes together, verified
   empirically, not just asserted individually:
   (a) `src/specify_cli/cli/commands/charter/context.py:84-85` stops precomputing `org_root =
   org_roots[0] if org_roots else None` for the values passed to `build_charter_context` /
   `build_charter_context_json`, and instead passes `org_root=None` through (the separately-held
   full `org_roots` list is still passed unchanged to `load_org_charter_json_block(org_roots)`,
   which is unaffected by this change and already correct); AND
   (b) `src/charter/context.py::build_charter_context_json` swaps its internal call from the
   private `_load_action_doctrine_bundle` to `charter.action_doctrine_bundle._resolve_action_bundle`
   (mirroring what `build_charter_context`, the plain-text path, already does).
   Change (a) alone fixes the plain-text path (since it already routes through
   `_resolve_action_bundle`, whose self-resolution only engages when it receives `org_root=None`)
   but NOT the JSON path (still calling `_load_action_doctrine_bundle` directly, which does not
   self-resolve at all). Change (b) alone fixes nothing while the CLI still hands in a pre-truncated
   `org_root`, since `_resolve_action_bundle`'s self-resolution also only engages on `org_root=None`.
   **Both changes are required together; a test asserting pack-2 content appears in BOTH the
   plain-text and JSON outputs is the correctness proof — do not accept a fix that only changes
   one of the two call sites.**
3. **Malformed pack — explicitly out of scope, not a regression to prevent**: this mission does
   not change `_load_action_doctrine_bundle`'s existing whole-bundle collapse behavior for a
   malformed org pack, for either call path (see "Out of Scope"). No test asserting graceful
   degrade is required for this AC.
4. **No org pack at all**: `org_root=None` and the chain-threading path resolves to an empty/`None`
   `org_roots`, matching pre-fix behavior exactly, for both call paths.

**FR-002 Design Notes / Recommendations** *(not acceptance criteria — guidance for the plan phase, not independently testable pass/fail assertions)*

- This mission recommends routing `build_charter_context_json`'s call path through
  `charter.action_doctrine_bundle._resolve_action_bundle` instead of calling the private
  `_load_action_doctrine_bundle` directly. Rationale: (a) it is the charter's own
  reconcile-don't-duplicate / single-canonical-authority principle — `_resolve_action_bundle`
  already *is* the established self-resolving wrapper for exactly this "caller did not supply an
  explicit org_root" case, and it already threads both `org_root` (for backward-compatible
  single-value consumers) and `org_roots` (the full chain); (b) replicating its self-resolution
  logic inline in `context.py` would create a second, divergent copy of the same "resolve the full
  declaration-ordered chain of existing org packs" logic, which is exactly the kind of duplicate
  authority the charter's governing principles flag for reconciliation, not duplication. The plan
  phase may reconsider only if it finds a concrete reason `_resolve_action_bundle`'s contract does
  not fit `context.py`'s call shape (e.g., a parameter `context.py` needs that the wrapper does not
  expose) — if so, that reason must be stated explicitly in the plan, not silently defaulted to
  inline replication.
- The plan phase must verify the combined fix empirically (e.g. a live repro or a focused unit
  test run before the AC test suite is written) rather than trusting that swapping one function
  call is sufficient — this exact class of "plausible fix that measurably does nothing" is what
  SPEC-ARCH-002 (this spec's own review trail, `reviews/spec-arch.findings.yaml`) caught in an
  earlier draft of this FR.

#### FR-003 Acceptance Criteria

1. **Healthy single-pack config, single-repo case (today's only real caller)**: `migrate
   rebaseline` via `migrate_cmd.py`'s `locate_project_root()`-derived `repo_root` reindexes with
   the org pack consulted.
2. **No org pack at all**: rebaseline behavior is unchanged from today (org-agnostic reindex).
3. **Multi-pack chain — expected to be inherited, not separately implemented**: verified live —
   `ManifestRegistry.load_manifest` (`src/specify_cli/dossier/manifest.py:253`) already calls the
   PLURAL `_resolve_existing_org_roots(repo_root)` (not a first-match-only resolver) whenever
   `repo_root is not None`. Once FR-003's fix threads a real `repo_root` into `Indexer.__init__`,
   multi-pack chain support for rebaseline is expected to come for free through this existing call
   — no separate multi-pack mechanism should be needed. This is a stated scoping decision, not a
   silent omission: **the plan phase must add its own two-pack regression test to confirm this
   inheritance actually holds**, and if it does not, must implement multi-pack support explicitly
   rather than leaving the gap undocumented.
4. Malformed org pack during rebaseline: does not raise an unhandled exception to the operator's
   `migrate` command; degrade behavior specifics are deferred to the plan phase but must be a
   deliberate, documented choice (not an accidental stack trace).
5. **Worktree open question resolved before implementation, not deferred silently**: the plan
   phase must investigate and resolve the worktree question in the Design Notes below BEFORE
   `Indexer(repo_root=...)` is threaded in — if snapshots can live under an execution-worktree path,
   `derivation (B)` (below) needs a worktree-aware correction; if they cannot, the plan phase must
   say so explicitly, with evidence, not merely assume it.

**FR-003 Design Notes / Recommendations** *(not acceptance criteria — guidance and an open question for the plan phase, not independently testable pass/fail assertions)*

- **Recommendation**: this mission recommends **derivation (B)** — deriving `repo_root`
  per-snapshot inside `rebaseline_snapshot_file`, from `feature_dir.parent.parent` (equivalently
  `snapshot_path.parents[5]` given the fixed `<repo_root>/kitty-specs/<slug>/...` layout),
  independent of the `root` argument passed to `rebaseline_recorded_snapshots`. Rationale:
  derivation (A) — threading the single `root` argument straight through to
  `Indexer(repo_root=root)` — is simpler and correct for today's one real caller, but is *wrong*
  for the anticipated (per the function's own docstring: "repo root or backlog directory") but
  currently unexercised multi-repo backlog case, where a single `root` argument cannot be the
  correct `repo_root` for every snapshot under it. Derivation (B) is correct for both cases because
  each snapshot's own path determines its own owning repo, and costs no more than (A) to implement.
  The plan phase should implement (B) unless it finds a concrete flaw in this reasoning, in which
  case it must document the flaw and may fall back to (A) with an explicit "rebaseline assumes
  single-repo `root` only" decision recorded — not silently defaulted.
- **Open question, explicitly flagged, not resolved by this spec**: for a mission worked in a
  spec-kitty execution worktree (`.worktrees/<slug>-<mid8>-lane-<id>/`), does that worktree carry
  its own duplicated `kitty-specs/<slug>/` and hence its own worktree-local `.kittify/config.yaml`
  (wrong org-pack answer), or does dossier snapshotting only ever happen against the primary/coord
  checkout? If recorded snapshots can ever live under a worktree path, `feature_dir.parent.parent`
  resolves to the worktree root, not the project's real org-pack-configured root, and derivation
  (B) needs a worktree-aware correction — e.g. resolving up to the git common-dir / superproject
  root instead of two fixed parent hops. **The plan phase must investigate and resolve this before
  implementing FR-003** — do not assume single-checkout-only without checking. This is FR-003
  Acceptance Criterion 5's binding requirement; the investigation and its answer are not themselves
  a testable pass/fail statement, which is why they live here rather than in the numbered AC list.

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No cascade performance regression | `charter activate/deactivate --cascade` over a typical project (per the charter's existing "<2s for typical projects" CLI performance standard) does not measurably regress from threading org roots through — the DRG merge work was already happening for other callers (e.g. `gate_bindings.py`) at comparable cost. | Performance | Medium | Open |
| NFR-002 | Silent success is prohibited | Every fixed code path must, on failure to fully do its job, either raise, log a WARNING naming the specific dropped/failed root, or otherwise surface the degradation to the operator — never return `None`/empty and call it success without any signal. This is the charter's and this mission's dominant reliability requirement, applying to FR-001/002/003. (It does NOT require this mission to build the malformed-org-pack per-root degrade itself — that remains #3401's territory per "Out of Scope"; this NFR governs the org-roots-threading defect class this mission actually fixes, not the separate malformed-content defect class it does not.) | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | `_resolve_org_root` stays inert | `src/charter/_drg_helpers.py::_resolve_org_root` must NOT be modified to resolve org roots itself. It is intentionally inert by design (its own docstring) to keep the `charter` package free of `specify_cli` imports, enforced by `tests/architectural/test_layer_rules.py`. All fixes belong in the `specify_cli`-layer callers. | Technical | High | Open |
| C-002 | Shared-reference safety preserved | Cascade deactivation must continue to skip (never remove) artifacts still referenced by another active artifact (existing C-005 contract), now correctly extended across the full org-pack chain rather than accidentally correct only because org packs were invisible before. | Technical | High | Open |
| C-003 | No stale/unverifiable numbers in spec or plan artifacts | Do not cite specific doctrine counts (e.g. "21 directives / 69 tactics") from any unrelated, unverifiable probe. Only the mechanism and defect class demonstrated by this mission's own live repro (see Grounding) may be cited with numbers, and only the `0 0 0 0 0` result that repro actually produced. | Technical | Medium | Open |
| C-004 | D2 stays closed | R&D finding D2 (`charter/kind_vocabulary.py::_org_scan_dirs` scanning a legacy `<root>/<plural>/built-in` path) is confirmed fixed upstream on this branch. This mission must not resurrect or re-file it. | Technical | Low | Open |
| C-006 | Item 4 (retired fourth FR) not duplicated | The malformed-org-pack whole-bundle-collapse defect (formerly this mission's Item 4) is confirmed fixed in open PR #3401 (`org-pack-drg-root-graph-guard-01KZY0QT`, closes #3384), touching `src/charter/_drg_helpers.py` and `src/charter/action_doctrine_bundle.py`. This mission must NOT independently implement per-root-degrade logic for that defect anywhere it touches `load_validated_graph`/`_load_action_doctrine_bundle` — doing so would create a second, conflicting fix on the same lines #3401 already owns. See "Out of Scope". NOTE: numbered C-006, not C-005 — this spec's User Story 2 / C-002 already use "C-005" to refer to an external, pre-existing shared-reference-safety contract from elsewhere in the codebase, unrelated to this mission's own Constraints table; reusing "C-005" here would collide with that reference within this same document. | Technical | High | Open |

### Key Entities

- **DRG (Doctrine Reference Graph)**: the merged graph of doctrine artifact nodes and
  `requires`/`suggests`/`specializes_from` edges, assembled per-call by `load_validated_graph`
  from built-in, project, and (when threaded) org-pack layers. This mission's core defect is that
  three cascade call sites and one context call site build this graph without the org layer.
- **Org root / org-pack chain**: the declaration-ordered list of configured org doctrine pack
  directories (`resolve_org_roots`, plural) versus the existence-filtered subset
  (`resolve_existing_org_roots`). A chain may have 0, 1, or N packs; each pack may be healthy or
  malformed (exists but has no graph fragment).
- **Cascade activation/deactivation plan**: the `charter.cascade` module's computed set of
  artifacts to activate/deactivate/skip, derived by walking the DRG from a source/target URN. Its
  correctness is entirely downstream of whether the DRG it walks contains the org-pack nodes.
- **Action-doctrine bundle**: the per-action set of `directive_ids`/`tactic_ids`/`styleguide_ids`/
  `toolguide_ids`/`procedure_ids` assembled by `_load_action_doctrine_bundle`, consumed by
  `charter context` (both paths) and other doctrine-context callers. Its separate
  whole-bundle-collapse-on-malformed-org-pack defect (formerly this mission's "Item 4") is fixed by
  PR #3401, not by this mission — see "Out of Scope".
- **Dossier snapshot / rebaseline**: a recorded `snapshot-latest.json` under
  `<feature_dir>/.kittify/dossiers/<slug>/`, reindexed by `Indexer` during `migrate rebaseline`.
  Currently built with no `repo_root`, so org config is never consulted.

## Reflexivity — missions that already ran `--cascade` under the old (org-inert) behavior

**Explicit answer, not left implicit**: yes, re-activation may be needed. Any mission that ran
`charter activate --cascade` against a project with org-pack doctrine configured, before this fix
ships, may have under-activated — some org-pack `requires`/`suggests` dependents were silently
never activated and never appeared in the `referenced_but_not_cascaded` warning (because the
warning itself was computed from the same org-inert graph). That mission's `.kittify/config.yaml`
`activated_*` state is a legitimate record of *what the tool did*, but it is not a complete record
of *what the cascade should have activated* had org roots been visible.

Consequence for operators: after this fix ships, an operator who previously ran `--cascade` on an
org-pack project should **re-run** `charter activate <same target> --cascade all` (idempotent —
already-activated artifacts are unaffected, newly-visible dependents get activated) if they want
their project's activation state to reflect what a correct cascade would have produced. This
mission does not add an automatic re-activation sweep or a migration step — that is out of scope
here — but the plan/tasks phase should record this as an operator-facing note (e.g. a CHANGELOG
entry or release note pointing affected operators at a re-run), so the gap is disclosed rather than
silently inherited by every project that activated doctrine before this fix landed.

No prior `SPEC-KITTY-LEDGER.md` entry (as far as this mission's grounding could determine) predates
this specific defect class. If the plan or implementation phase discovers one while working, it
must be named explicitly in that phase's own artifacts rather than silently ignored — this mission
does not append to the ledger itself (per the ledger-discipline instruction under which it was
authored).

## Grounding — evidence for the retired "Item 4" scope (why it was dropped, not why this mission fixes it)

This mission's investigation confirmed the whole-bundle-collapse mechanism with a real, working
repro on this branch (not inferred from prose): a fake org-pack directory with a `directives/`
subdir but no `graph.yaml`/`*.graph.yaml` fragment, passed to
`charter.action_doctrine_bundle._load_action_doctrine_bundle`, produced
`directive_ids=0, tactic_ids=0, styleguide_ids=0, toolguide_ids=0, procedure_ids=0` — all five
doctrine-kind counts collapsed to zero, with only a WARNING-level log line, no exception surfaced
to the caller. Per C-003, no other doctrine counts (e.g. from an unrelated probe) are cited
anywhere in this spec. This repro is kept here as evidence that the "Out of Scope" section's
description of the defect is accurate, NOT as grounding for a fix this mission implements — the
fix is PR #3401's, already in flight, confirmed OPEN.

Separately, `load_validated_graph` itself does **not** silently zero anything on a malformed org
root — `load_graph_or_dir` raises `DRGLoadError` when a directory exists but has no graph
fragments, confirmed by a second live repro. The asymmetry between the project branch's lenient
`has_graph_files` pre-check and the org branch's bare `.exists()` guard is real, but it fails
*loud* (raises) at that layer — the *silent* collapse happens one level up, in
`_load_action_doctrine_bundle`'s unconditional `except DRGLoadError` catch with no re-raise. Both
mechanisms are #3401's scope, confirmed by that PR's own description ("An org pack with no
loadable graph now degrades to 'no org DRG layer' instead of raising a swallowed `DRGLoadError`"),
touching exactly the same two files (`_drg_helpers.py`, `action_doctrine_bundle.py`) this repro
exercised.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `charter activate --cascade all` and `charter deactivate --cascade all`, run against
  a project with a 2-pack org chain and cross-pack `requires` edges, activate/deactivate every
  in-scope target across the full chain — verified by an automated test asserting on the resulting
  activation state, not by operator inspection.
- **SC-002**: `charter context --json`'s action-doctrine bundle for a 2-pack chain includes IDs
  contributed by pack 2, verified by an automated test asserting on `directive_ids`/`tactic_ids`/
  etc. contents.
- **SC-003 retired** — it measured the malformed-org-pack per-root-degrade behavior that was
  the retired fourth requirement's, now out of scope (see "Out of Scope"). The ID is retired, not reused.
- **SC-004**: Zero regressions for the org-inert case (no org pack configured) across all three
  fixed call sites — verified by running the existing pre-fix test suite for
  `activate.py`/`deactivate.py`/`context.py`/`rebaseline.py` unchanged and green post-fix.
  **Baseline-red disclosure (mandatory before this SC can be marked satisfied)**: `main` carries a
  known, tracked baseline-red condition — issue #3284 (verified OPEN via `gh issue view 3284`:
  "main full suite has 23 untracked failures and 2 errors after bootstrap prewarm"), consistent
  with CLAUDE.md's "Test-run baseline-red gotcha" instruction to classify every red result
  (pre-existing / introduced / environment) before attributing it to this mission's own change.
  "Green post-fix" in this SC means: every test in the targeted files that was green on this
  branch's base commit (`5a8fc1b74`, see Base-Branch Drift) stays green after this mission's fix;
  any test in `tests/charter/test_context*.py`, `tests/dossier/test_rebaseline.py`, or the
  `activate.py`/`deactivate.py` test files that is ALREADY red on the base commit (whether or not
  it is one of #3284's 23+2) is a pre-existing failure this mission does not need to fix and must
  NOT be misattributed as its own regression — the implementer/reviewer must check each red result
  against the base commit before treating it as introduced by this mission.
- **SC-005**: `migrate rebaseline`, run on a project with a healthy org pack, reindexes with the
  org pack consulted — verified by an automated test asserting the `Indexer` received a non-`None`
  `repo_root` matching the project root, not the pre-fix default of `None`.
