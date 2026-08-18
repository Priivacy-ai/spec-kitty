# Tracer: Design Decisions

Seeded at planning per charter Standing Order #3 (mission tracer files). Records the two
binding operator decisions made before spec authoring (Decisions 1-2), with rationale, so a later
reader does not have to reconstruct "why" from the spec's prose alone. Decisions 3 and 4 were
added during the adversarial-review fix pass (2026-08-13, addressing confirmed findings
SPEC-ARCH-001 and SPEC-ARCH-005) — editorial calls the fixing agent was asked to make explicitly
and record here, not merely fix as inline caveats. Decision 3's caller-side scope was corrected
during a second fresh-eyes fix round (2026-08-13, addressing confirmed finding SPEC-FRESH-001,
which caught that Decision 3's own "the two real callers ... are updated" text — and the spec's
echoing "it touches only `manifest.py`" claim — contradicted each other and, on inspection of the
live call graph, both undersold and overstated the actual required change). Decision 3's "for
free" claim about the sync-pipeline path was corrected again during a third, final fix round
(2026-08-13, addressing confirmed finding SPEC-FRESH-002, recorded as Decision 5 below) — the
sync-pipeline path's internal fail-close prevents a crash but does not reach an operator, because
every real caller of `trigger_feature_dossier_sync_if_enabled` discards its return value.

## Decision 1 — authoring the new `plan` mission-type manifest

**Context**: Issue #3388 claim 1 says `plan` mission type ships no `expected-artifacts.yaml`
while the other three built-in types do. Investigation found `runtime_bridge_cores.py` has **no
`plan`-family guard branch at all** — `evaluate_guards()` dispatches `research` and
`documentation` to their own tables and routes everything else, including `plan`, to
`_evaluate_software_dev_guards`. That function's vocabulary
(`specify`/`plan`/`tasks_outline`/`tasks_packages`/`tasks_finalize`/`tasks` (composed)/
`implement`/`review`, 8 ids in total — `runtime_bridge_cores.py:554-566`) matches none of `plan`
mission type's own state names (`goals`/`research`/`structure`/`draft`/`review`/`done`, per
`packs/built-in/missions/plan/mission.yaml`) **except one: `review`**, which lexically collides
with software-dev's own `review` step id.

**Correction (post-review, R3 SPEC-VERIFY-001/SPEC-ARCH-002 confirmed findings)**: the original
framing above — "any `plan`-type step id falls to the function's bare `return []`" — is false for
`review`. The actual invocation path for every mission type, `plan` included, is
`_check_cli_guards` (`src/runtime/next/runtime_bridge.py:680-698`), which hardcodes
`mission_family="software-dev"` regardless of the mission's real type; the mission-family-aware
composed-action path (`_dn_composition_dispatch`) is reachable only when `mission ==
"software-dev"`. So a `plan` mission's `review` step is evaluated by
`_evaluate_software_dev_guards`'s `if step_id in ("implement", "review")` branch
(`runtime_bridge_cores.py:564-565`), which calls `_evaluate_wp_iteration_guard("review",
snapshot)` — not the bare `return []` fallback every OTHER `plan`-type step id
(`goals`/`research`/`structure`/`draft`/`done`) reaches. Today this coincidentally still returns
`[]`, because `wp_advance_ready` defaults `True` when a plan mission's directory has no `tasks/`
subdirectory (`_should_advance_wp_step`, `runtime_bridge.py:618-630`) — but it is a real,
reachable, mission-blind branch with a latent spurious-block risk, not a second no-op fallback.
In practice: no *dedicated* `plan`-family guard branch exists, and four of the five non-`review`
step ids genuinely fall to the bare `[]` — but `review` is evaluated by a real branch that
happens, by accident, to match.

**Decision (chosen: Option A)**: Author `plan/expected-artifacts.yaml` keyed on `plan` mission
type's **own** step vocabulary and real artifacts (`goals.md`, `research.md`, `plan.md` — no
`spec.md`, no `tasks.md`, no WP files), as documentation-only content consistent with this
mission's "content + schema only" scope. It explicitly does not claim any guard enforces it yet.
File a separate upstream issue naming the real defect: the hardcoded
`mission_family="software-dev"` in `_check_cli_guards` combined with the accidental `review`-step
vocabulary collision (latent spurious-block risk) — not merely "no branch recognizes plan step
ids." A real, independent defect this investigation surfaced, not named in #3388, and not fixed
in this mission.

**Rejected alternatives**:
- **Option B** — mirror `software-dev`'s manifest 1:1, since that's the guard chain a `plan`
  mission's steps literally (if incorrectly) fall through to today. Rejected: this would ship a
  manifest that reads as authoritative but describes a step vocabulary and artifact set `plan`
  missions don't actually use or produce — reproducing #3388's own "unreliable, unsafe to gate
  on" failure mode inside its own remedy.
- **Option C** — drop the `plan` manifest from this mission's scope entirely, since authoring it
  uncovered a second, independent, unnamed defect (no `plan`-family guard branch) that arguably
  deserves its own investigation first. Rejected: under-delivers against the issue's explicit
  claim 1 without flagging why, and the manifest can still be authored honestly (per Option A)
  without needing the guard gap resolved first.

**Why this matters downstream**: A reviewer or future maintainer reading
`plan/expected-artifacts.yaml` next to `plan/mission.yaml` should see internally consistent,
honest content — not a manifest that looks wired to enforcement but isn't. The follow-up issue
this decision requires filing is the actual fix for the guard gap; this manifest is descriptive
scaffolding for it, not a substitute.

**Addendum (WP03/T017, filed)**: the follow-up issue for the guard gap named above is
[Priivacy-ai/spec-kitty#3407](https://github.com/Priivacy-ai/spec-kitty/issues/3407), assigned
to the HiC (`MOES-Media`). It names the precise mechanism (the hardcoded
`mission_family="software-dev"` in `_check_cli_guards` plus the `review`-step lexical
collision) and cross-references this mission and this decision. It is distinct from, but
related to, the broader #3386 ("Unknown mission_type silently executes under software-dev
guard tables"), discovered a day earlier in a separate investigation; #3407's body notes the
relationship. Neither #3386 nor #3407 is fixed by this mission.

## Decision 2 — `manifest_version` on reconciliation

**Context**: `sync.namespace.resolve_manifest_version()` reads `manifest.manifest_version`
directly off the same YAML this mission edits. That value is one of 5 fields forming
`NamespaceRef`'s identity tuple for hosted-SaaS sync body uploads
(`f"|{self.mission_type}|{self.manifest_version}"`), consumed by `sync/dossier_pipeline.py`. This
repository cannot see `spec-kitty-saas`'s internal state or verify what happens to already-synced
artifact bodies if the namespace key changes.

**Decision (chosen: Option A)**: Do not bump `manifest_version` — keep it `"1"` on all four
manifests (three reconciled + the new `plan` manifest). Nothing in this tree branches on its
numeric value beyond string equality inside the namespace tuple. Treat this reconciliation as a
**corrective patch to the existing version**, not a new version. Record the rationale as an
inline YAML comment in each of the four manifest files, not only in the spec — so a future
reader who reasons "content changed materially, so the version should bump" sees explicitly why
that instinct was deliberately overridden here.

**Rejected alternative**:
- **Option B** — bump `manifest_version` to `"2"` on the manifests whose `required_by_step`
  shape materially changes (documentation, software-dev). More semantically honest (the
  manifest's *meaning* did change), but this would change a live sync identity key in a system
  (`spec-kitty-saas`) this PUBLIC repo has no visibility into, with no migration path visible
  from here for orphaned or duplicated synced bodies. Rejected as an uninvestigated cross-repo
  side effect, not a content fix — exactly the kind of change that belongs in a scoped follow-up
  with the SaaS side able to verify the blast radius, not silently absorbed into a "content +
  schema only" mission.

**Why this matters downstream**: Anyone touching `expected-artifacts.yaml` content in the future
should not reflexively bump `manifest_version` just because content changed. The version field's
actual contract in this codebase is a sync-namespace identity key, not a content-freshness
counter — conflating the two is the mistake this decision heads off.

## Decision 3 — completing FR-009's schema hardening through `load_manifest()`

**Context** (SPEC-ARCH-001, sev 4): User Story 3's motivation is that a typo'd manifest key
should raise a validation error immediately. FR-009's `extra="forbid"` does make direct Pydantic
construction of `ExpectedArtifactSpec`/`ExpectedArtifactManifest` raise — but the sole production
loading path, `ManifestRegistry.load_manifest()` (`src/specify_cli/dossier/manifest.py:207-215`),
wraps `model_validate` in a bare `except Exception as e: logger.error(...); return None`. Every
real reader (the dossier indexer, `resolve_manifest_version()`, and — via a separate bypass path
not through this method — `_resolve_expected_artifacts_slot()`) goes through this method, not
direct model construction. Without a further change, a typo'd real YAML file is still silently
converted to `None` — identical to "manifest not found," merely logged at ERROR level — through
every real consumer. The mission's own acceptance bar (SC-001: "reconciled against observed
artifacts, not merely schema-valid") and the issue's own claim 3 ("schema drops typos silently")
both point at the loaded, real-file path, not merely at direct construction in a test.

**Decision (chosen: Option A of the finding's two offered readings)**: Add FR-016, changing
`load_manifest()`'s exception handling to let `pydantic.ValidationError` propagate to the caller
instead of being caught by the bare `except Exception`. The earlier `config is None` branch
(absence — no manifest file present) is unchanged and continues to return `None`.

**Correction (second fix round, SPEC-FRESH-001 confirmed)**: the original text here said "the two
real `load_manifest()` callers (the dossier indexer's call sites, `resolve_manifest_version()`)
are updated to handle a raised `ValidationError` explicitly" — echoing the spec's own now-corrected
"it touches only `manifest.py`" claim in User Story 3's motivation, which was false against this
very sentence. Reading the actual call graph (not just naming the two callers) shows the needed
change is smaller and asymmetric between the two:

- **The dossier indexer's four `load_manifest()` call sites (`dossier/indexer.py:123,176,355,407`)
  need no code change at all.** Every production caller of `Indexer.index_feature()` already
  wraps that call in its own dedicated, fail-closed `except Exception`: the `reconcile` CLI command
  (`cli/commands/reconcile.py:151-160`, comment "fail-closed: any rebuild failure is an ERROR"),
  the rebaseline backlog sweep (`dossier/rebaseline.py:162-170`, comment "one bad mission must not
  abort the backlog sweep"), and `sync/dossier_pipeline.py`'s `sync_feature_dossier()`, which has
  its *own* dedicated `except Exception` at lines 243-250 around its `Indexer.index_feature()` call
  at line 245 (independent of that function's separate outer catch at line 368). A raised
  `ValidationError` therefore already surfaces as `ReconciliationResult(status=ERROR, error=...)`
  from `reconcile`, a per-mission `error="reindex_failed: ..."` skip from the rebaseline sweep, and
  `DossierSyncResult(dossier=None, errors=[str(e)])` from the sync pipeline — all via pre-existing
  code that prevents an unhandled-exception crash. **Correction (third fix round, SPEC-FRESH-002
  confirmed)**: for `reconcile` and `rebaseline`, this genuinely is the "fails loudly" outcome User
  Story 3 wants — both are human-facing. For the sync pipeline it is not: `sync_feature_dossier()`'s
  wrapping function, `trigger_feature_dossier_sync_if_enabled`, has its returned `DossierSyncResult`
  discarded by every real production caller (verified: `merge/executor.py`,
  `cli/commands/research.py`, `cli/commands/agent/tasks_mark_status.py`, `sync/__init__.py`'s
  default event handler, and further fire-and-forget call sites), so a typo routed through that
  path alone is silently absorbed exactly as it was before this fix — see Decision 5 below for why
  this mission does not close that gap. Adding redundant `except` blocks inside `indexer.py` itself
  would still only duplicate handling that already exists one layer up, regardless.
- **`sync.namespace.resolve_manifest_version()` is the one real exception.** It has no dedicated
  catch of its own — its only protection today is the *unrelated* outer `except Exception` at
  `dossier_pipeline.py:368`, inside its sole production caller,
  `trigger_feature_dossier_sync_if_enabled` — and its own docstring commits to "the manifest_version
  from the registry if available, otherwise ... '1'" for every input, a promise a raised, uncaught
  `ValidationError` would break for any future caller that trusts the docstring and does not add its
  own try/except. FR-016 therefore adds one narrow, explicit line here: `except
  pydantic.ValidationError: return "1"` around its `load_manifest()` call, falling back exactly as
  it already does for a genuinely-absent manifest. Its return value for a malformed manifest is
  unchanged (`"1"`), so `NamespaceRef`'s sync-identity tuple is unaffected.

**Blast radius, stated precisely (replacing "it touches only `manifest.py`")**: this decision
touches `manifest.py` (the raise) and, narrowly, `sync/namespace.py` (one output-preserving
defensive line inside `resolve_manifest_version()`). It does **not** touch
`dossier/indexer.py` — verified by direct read of `reconcile.py`, `rebaseline.py`, and
`sync/dossier_pipeline.py`, every one of which already fail-closes around the indexer call. The
`sync/namespace.py` touch does not violate C-002/Decision 2: `resolve_manifest_version()`'s return
value for every input, including a malformed manifest, stays `"1"`, so `NamespaceRef`'s identity
tuple and the sync pipeline's observable behavior are unaffected.

**Why this is in scope, not scope creep**: C-001 forbids changes to
`src/runtime/next/runtime_bridge_cores.py`, `runtime_bridge_composition.py`, and
`runtime_bridge_io.py` — it says nothing about `src/specify_cli/dossier/manifest.py`, which is
exactly the file FR-009 already changes for the schema itself, nor about the one-line defensive
catch in `sync/namespace.py` described above. NFR-001's "no runtime consumer behavior change"
guarantee is scoped explicitly to `runtime_bridge_cores.py`'s guard tables, not to
`ManifestRegistry` or `resolve_manifest_version()`. This is read as completing FR-009's own promise
so it reaches production, not as a new guard-behavior change — the alternative reading (rewrite
User Story 3 to scope the loud-failure guarantee to direct model construction / test tooling only)
was rejected because it would leave the mission's own stated acceptance bar unmet for the one path
that matters in practice.

**Rejected alternatives**:
- **Option B — narrow User Story 3's claim to "direct model construction raises `ValidationError`;
  `load_manifest()`'s behavior is unchanged and out of scope."** Rejected: this technically
  satisfies the letter of "content + schema only" but concedes the actual, practical failure mode
  (a hand-edited manifest with a typo, loaded normally) is still silently swallowed — which is the
  literal scenario User Story 3 exists to prevent. Choosing this would have been the easier,
  smaller diff, but would not have honestly closed the defect class the review flagged.
- **Option C — accept the callers' current behavior as-is everywhere, including
  `resolve_manifest_version()` raising uncaught.** This is the remediation's literal "option (a)":
  declare the caller-side consequence accepted and reviewed, with no code changes beyond
  `manifest.py`. Rejected specifically for `resolve_manifest_version()`: its docstring promises a
  string for every input regardless of caller, and its only protection today comes from an
  unrelated caller's blanket catch, not from any contract of its own. Leaving it able to raise
  would be an avoidable, un-reviewed break of that function's own promise for the sake of a diff
  that is barely smaller — a one-line fix away from being both smaller *and* contract-safe.
- **Option D — treat `dossier/indexer.py` as in-scope and add explicit per-call-site `except`
  blocks there too**, per the remediation's literal "option (b)" instruction to name every touched
  file including the indexer. Rejected after reading the actual call graph: every production caller
  of `Indexer.index_feature()` already fail-closes on any exception (see above), so adding
  redundant `except` blocks inside `indexer.py` itself would duplicate handling that already
  exists one layer up, growing the diff with no change in observable behavior — the opposite of
  `change-apply-smallest-viable-diff`.

**Why this matters downstream**: A future typo in any of the four `expected-artifacts.yaml`
files will now surface as a raised exception through `ManifestRegistry.load_manifest()`, which the
dossier indexer's own callers already convert into a visible, structured failure with no new code,
while `resolve_manifest_version()` degrades it to `"1"` exactly as it already degrades absence — so
the sync pipeline's observable behavior for this new failure mode is identical to its existing
absence-handling, by design, not by accident of an unrelated caller's blanket catch. Any *new*
caller of `ManifestRegistry.load_manifest()` should still expect it to raise on a malformed (not
merely absent) manifest and handle that explicitly, rather than assuming `None` covers both cases —
that expectation is unchanged by this correction.

## Decision 4 — the dead `.kittify/overrides/` manifest copies: deprecate, don't refresh

**Context** (SPEC-ARCH-005, sev 3): The spec's own "second-order finding" section establishes
that `.kittify/overrides/missions/{research,documentation,software-dev}/expected-artifacts.yaml`
are consumed by zero readers in this repository (`_expected_artifacts_path()` composes only the
built-in pack path, with no override tier at all). The original FR-014 proposed refreshing these
dead copies to match the reconciled built-in content "as drift hygiene," without weighing this
against the charter's DIRECTIVE_044 ("chase unification, not parity with a dead quirk").

**Decision (chosen: mark deprecated/inert, do not refresh content)**: FR-014 now marks each
override copy as explicitly deprecated/inert via a header comment, rather than refreshing its
content to parity with the canonical built-in copies. Refreshing dead content to keep it "in
sync" is the literal shape of parity-with-a-dead-quirk — it would restate, dressed up as
maintenance, the exact single-canonical-authority violation the second-order finding just
diagnosed. The header comment states plainly that the file is not consumed by any resolver for
this asset type and points at the override-tier-wiring follow-up issue as where a future
correction belongs.

**Rejected alternatives**:
- **Option B — refresh content to keep "in sync,"** as originally drafted. Rejected per
  DIRECTIVE_044: this is the anti-pattern by name, not a defensible exception to it — there is no
  reader this benefits, only the appearance of upkeep.
- **Option C — delete the override files outright.** Considered seriously (it is arguably the
  purest application of DIRECTIVE_044: dead content, remove it). Rejected in favor of marking
  deprecated in place because (a) deletion removes the historical starting point a future
  override-tier-wiring mission might want as a reference, and (b) a present-but-marked-dead file
  is discoverable by a maintainer browsing the directory tree; a deleted file requires git
  archaeology to learn it ever existed. Marking deprecated in place gets the same "stop investing
  in dead content" outcome as deletion while staying more legible to the next reader.

**Why this matters downstream**: A maintainer who finds `.kittify/overrides/missions/software-dev/
expected-artifacts.yaml` and (correctly, for every *other* doctrine asset type in this same
directory) assumes it takes precedence over the built-in copy will now be told directly, at the
top of the file, that this assumption is wrong for this specific file type — instead of
discovering it only by tracing `_expected_artifacts_path()` themselves.

## Decision 5 — FR-016/Decision 3's "for free" claim: soften the claim, don't widen scope

**Context** (SPEC-FRESH-002, sev 3): The round-2 revision to FR-016 and this file's Decision 3
claimed the sync-pipeline path (`sync/dossier_pipeline.py`'s `sync_feature_dossier()`, which
already fail-closes on a raised `ValidationError` at lines 243-250, returning
`DossierSyncResult(dossier=None, errors=[str(e)])` instead of propagating the exception)
"satisfies the 'fails loudly' goal ... for both human-facing paths, for free." That claim is true
only up to "does not crash the process" — it is false as a claim about operator-visible failure.
Re-reading the actual call graph (fresh, not re-trusting the earlier draft's framing): every real
production caller of the wrapping function `trigger_feature_dossier_sync_if_enabled` discards its
return value. Confirmed by direct read across the tree (10 call sites total, more than the 4
originally named in the finding): `merge/executor.py:1300` (a bare, unwrapped call — return value
simply not assigned), `cli/commands/research.py:195` (`try: ... except Exception: pass`),
`cli/commands/agent/tasks_mark_status.py:399` (`contextlib.suppress(Exception)`),
`sync/__init__.py`'s registered default event handler `_dossier_sync_handler` (~lines 184-196),
and further fire-and-forget call sites under `cli/commands/agent/`
(`workflow_executor.py:877`, `mission_record_analysis.py:372`, `mission_finalize.py:1763`,
`mission_setup_plan.py:773`) plus `migration/backfill_identity.py:290` and
`migration/normalize_mission_lifecycle.py:111` (which log the *exception* message on the rare path
where `sync_feature_dossier()` itself raises, but still never read a successfully-returned
`DossierSyncResult.errors`). **None** of the 10 call sites reads `.errors`. So a typo'd manifest
routed through the sync-pipeline path alone produces the exact same operator-visible outcome
before and after FR-016: nothing. The spec's own FR-016 text (pre-fix) was self-inconsistent on
this point: it named reconcile/rebaseline as "both human-facing paths" in the same sentence
claiming the sync-pipeline path also "satisfies ... for free" — visible and not-human-facing
cannot both be true of the same fire-and-forget call chain.

**Decision (chosen: remediation option (a) — soften the claim, name the gap)**: FR-016 and this
file's Decision 3 are corrected to state precisely what changed: the sync-pipeline path's internal
fail-close (a struct with `.errors` populated, instead of an uncaught exception propagating out of
`sync_feature_dossier()`) prevents a crash but does not make the underlying typo operator-visible,
because every real caller of `trigger_feature_dossier_sync_if_enabled` discards the returned
`DossierSyncResult`. This residual gap is named explicitly in both places as a known limitation /
follow-up candidate — not silently dropped from the spec's language, and not claimed as solved.

**Rejected alternative**:
- **Option (b) — widen FR-015/FR-016's scope to add visible logging** (e.g.
  `logger.warning`/`logger.error` on a non-empty `DossierSyncResult.errors`) at the
  `trigger_feature_dossier_sync_if_enabled` layer, plus a new acceptance scenario proving the typo
  produces a logged/observable signal through this path. Rejected for this mission: Decision 2
  (C-002) already refused to touch this exact pipeline (`sync/dossier_pipeline.py` and its
  callers) for a *value-only* change (the `manifest_version` bump), specifically because this
  repository cannot verify `spec-kitty-saas`'s blast radius for changes rippling through the sync
  path. Adding logging behavior at the `trigger_feature_dossier_sync_if_enabled` layer is a smaller
  change than a namespace-key bump, but it is still a *behavior* change to a widely-fanned-out
  fire-and-forget code path (10 call sites, several in hot CLI command paths — `research.py`,
  `tasks_mark_status.py`, `merge/executor.py`, the default sync event handler) that this "content +
  schema only" mission has not scoped, staffed, or tested for. Widening it here would inherit scope
  from FR-016's existing (already-corrected-once, per Decision 3's own correction history) boundary
  rather than being independently justified — exactly what the remediation instructions warned
  against. A future mission that wants `trigger_feature_dossier_sync_if_enabled`'s callers to
  observe sync failures should scope and test that change on its own terms (which caller(s) should
  log, at what level, with what rate-limiting given it fires on every mutation), not receive it as
  an unplanned rider on a manifest-content-and-schema mission.

**Why this matters downstream**: A future reader of FR-016 or Decision 3 should not conclude that a
hand-edited manifest typo is guaranteed to be noticed just because it is routed through
`sync_feature_dossier()`. The reconcile and rebaseline paths remain genuinely fail-loud; the
sync-pipeline path does not, and this gap is real, is not fixed by this mission, and is named here
so it does not get silently rediscovered as a "new" bug later. If it is ever prioritized, the
natural next step is a scoped follow-up widening `trigger_feature_dossier_sync_if_enabled` (or a
caller of its own choosing) to log a non-empty `DossierSyncResult.errors`.
