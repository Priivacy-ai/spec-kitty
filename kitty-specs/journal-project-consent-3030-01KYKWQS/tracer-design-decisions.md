# Tracer: design decisions — journal-project-consent-3030

Charter standing order 3. Decisions whose rationale would otherwise live only in
commit messages.

## The root cause was mis-pinned, and the correction shaped everything

#3030 and `saas#585` both pinned the defect at `sync/batch.py:1064-1080`. That is
not the drain `sync now` uses. The real path is
`delivery/dispatcher.py:_select_undelivered` over `journal.read_all()`. A fix at
`batch.py:1064` would have passed its unit tests and leaked in production.

## Consent is a separate representation from `drain_blocked_reason` (C-003)

`drain_blocked_reason` is a machine-global gate snapshot taken at capture and
re-evaluated each tick; consent is a stable per-project decision. Collapsing them
would either strand every pre-login capture or make consent transient. Consent is
represented by the stored `project_uuid` plus `consent.py`'s resolver; the one
invariant (`delivered ⊆ consented`) is expressed once, in selection.

## T003's split is policy vs readiness, not null vs non-null

Excluding every non-null `drain_blocked_reason` would strand every capture taken
before login. Terminal = the operator's policy did not permit shipping
(`saas_disabled`). Transient = they consented but the machine was not ready
(`missing_auth`, `missing_team`, `private_teamspace_gate`, `daemon_lock`,
`network_unavailable`). An unrecognised token is terminal: a stranded event is
purgeable, an unconsented delivery is not.

## NFR-005 was reversed deliberately (T006)

Capture-first durability was unconditional for Teamspace-bound facts. That
invariant is what made the journal a machine-global pool of every local project's
payloads. It now applies to consenting projects only, and
`capture_teamspace_bound`'s contract was updated to say so. The gate lives at
`EventEmitter._capture_to_journal`, the single production entry point — gating
inside `capture_teamspace_bound` via its unused `skip_journal` parameter would
have greened a test while every real capture stayed unconditional.

## FR-013 × FR-019: both stores, project-local wins (operator, 2026-07-29)

FR-019 supersedes FR-013 on authority, not existence. The uuid-keyed index must
exist because the dispatcher resolves consent for events carrying only a uuid and
must answer when the checkout has moved or been deleted. The index is a cache: a
readable checkout that disagrees wins, and the index is corrected.

## `repo_slug` became a third identity column (operator, 2026-07-30)

Consent is stored repo-slug-keyed (`[sync.repo_defaults."owner/repo"]`) and the
acceptance pins deliberately record it that way, but rows carried only
`project_uuid`. Rather than weaken the pins, the row now carries `repo_slug` and
the resolver gained a `REPO_DEFAULT` level between the uuid index (project-specific)
and the env var (machine-wide arming).

## The filtered read takes no LIMIT, on purpose

`ledger.select_undelivered` fetches the full terminal-id set and slices an
already-filtered universe. Pushing a LIMIT into the journal SQL would let delivered
rows fill the window and be stripped afterwards — an empty selection with consented
rows behind it, which is NFR-002's starvation. The ledger is a separate SQLite
file, so no join can rescue it.

## C-004 moved to WP08 for a schema reason

Retiring `queue.remove_project_events` needs `disable_checkout_sync` to purge the
journal instead, and the journal had no `project_uuid` to purge by until WP04.

## The egress point owns its own refusal (M1-1, 2026-07-30)

`drain_blocked_reason` was derived from the **current working directory's** checkout
routing, so one project's grant published another project's envelope over the
WebSocket. Two facts settled the shape of the fix, and only one of them was the
reported bug.

The reported half is the leak. The unreported half is that the same read was
**simultaneously dead**: with no readable checkout, `resolve_checkout_sync_routing`
returns `None`, so every event of every project was stamped `sync_disabled` — the
WebSocket publish was broken for *consenting* projects too, which is the daemon's
normal case. This is why the fix could not be a gate at `_route_event` alone:
`test_an_index_grant_publishes_from_outside_any_checkout` would have stayed red
forever. `_classify_drain_blocked_reason` had to stop being cwd-derived.

The decision therefore lands in **two** places deliberately, which is a considered
exception to C-003 and not an oversight: `_classify_drain_blocked_reason` resolves
through the one consent chain with an explicit `project_uuid`, **and** `_route_event`
re-checks consent independently immediately before publish. The reasoning is M1-1's
own lesson — the finding *was* the failure of resting a confidentiality boundary on a
field whose docstring calls it a diagnostic. Both sites must reach the same resolver;
two sites that could disagree about consent would be the C-003 violation this avoids.

Structural rather than test-enforced: `emitter.py` no longer imports
`routing.is_sync_enabled_for_checkout` at all, so the cwd-derived substitution cannot
creep back by someone re-reaching for the convenient helper.

## `queue_event` is deliberately not gated, and what would flip that

Three grounds, in descending durability. (1) It is **not egress** — every
`drain_queue`/`process_batch_results` call site was enumerated and verified, not
assumed, and `tests/sync/test_no_queue_drain_constructed_3030.py` pins that no code
path constructs the drain. Assuming "nothing reads this" is the exact mistake M1-1
corrected, so this ground was re-derived rather than inherited. (2) Gating it would
be **data loss, not confidentiality**: the local outbox is documented unconditional
(#1072), and refusing the write converts "not opted in to hosted sync" into "local
event history discarded". (3) The residual at-rest pooling is C-006's recorded open
collection surface, remediated by FR-016's purge rather than by refusing to write.

**Precondition, not a follow-up ticket:** if a queue-backed sender is ever restored,
this write becomes egress and must be gated *before* the sender lands. Recorded here
because the WP02 removal is what makes ground (1) true, and a future WP re-opening
`batch.py` for FR-014 will not otherwise know that.

## Two cwd-derived reads survive, both inert, both with the same trigger

`batch.py` retains a second one alongside `queue_event`'s at-rest pooling:
`_is_checkout_sync_enabled_for_batch` (`:335`) reads consent from the current working
directory. Reachability was traced rather than inferred from the anchor test's name —
`batch_sync` (`:990`) is its only caller, `sync_all_queued_events` (`:1374`) is
`batch_sync`'s only caller, and neither has a production reference outside `batch.py`.

Both residues share one trigger: **FR-014 re-opening `batch.py` to restore a
queue-backed sender.** That single change would simultaneously make `queue_event` an
egress write and make this read a live cross-project consent decision. Neither is
filed as an issue, because an issue in a tracker is not read by the person editing
`batch.py`; both are recorded at the code and in the WP that would be re-opened.

The general rule this mission keeps re-deriving: **cwd is not the bug.** A
human-invoked command whose subject is "this checkout" is right to read cwd —
`cli/commands/sync.py:1107,1204` are correct as written. The bug is cwd answering a
question about a *specific event's* project, which is why the fix everywhere was to
thread the event's own `project_uuid` rather than to purge `Path.cwd()` from the
codebase.

## Derive projections from `ORDERED_COLUMNS` — but judge per site (H6 class closure)

H6 was one symptom of a class: four hand-maintained column projections that a new
column silently falsifies. Closed in `6c48815fbd` by deriving them from
`ORDERED_COLUMNS` / `IDENTITY_COLUMNS`, proven by mutation rather than by argument.

**Mutation A** (a hypothetical 12th non-identity column `tenant_id`, created in the DDL
and written by `SET_IDENTITY_SQL`) made `test_backfill_preserves_all_non_identity_columns`
**pass pre-fix while the backfill damaged that column** — the class was open exactly as
the reviewer claimed. Post-fix it fails and names the column.
**Mutation B** (drop `repo_slug` from the ALTER loop) produced, pre-fix, a single failure
in an *unrelated* test via `read_all()` raising `no such column`, while all four C-001
pins passed. Post-fix, four failures including the pins.

**One site was deliberately not derived.** `_read_raw` exists to prove the migration did
not disturb values that existed *before* it ran, so it must keep asking about the
historical eight columns as the schema grows — deriving it would make it select the
columns the migration just added and compare them against themselves, which is the
tautology class. Resolved by naming the literal `_PRE_MIGRATION_COLUMNS` and asserting it
**equals** `ORDERED_COLUMNS - IDENTITY_COLUMNS`, so drift fails loudly without losing the
freeze. Blanket-deriving is the wrong lesson; the rule is *derive where the projection
should track the schema, freeze where it should track history, and assert the relationship
between them either way.*

Two guards were added on the derivations themselves, because **a derived projection fails
by going silent rather than by returning a wrong answer**: `PRESERVED_COLUMNS` must be
non-empty and disjoint from `IDENTITY_COLUMNS`, and every column must be classified as
either written-by-the-backfill or preserved. Same reasoning as the shrink-only ratchet — a
computed guard that quietly computes to nothing asserts nothing.

## An unpinned MINOR, recorded rather than asserted

A differing payload `repo_slug` overwriting a stored one on a `project_uuid IS NULL` row
is **permitted**: it is NFR-004's letter, and `repo_slug` is never an authorization key
(FR-019), so there is no confidentiality consequence. It is deliberately **not pinned**,
and the reason is the more important half — the behaviour was reasoned about but never
observed, and a pin asserting what an author believes rather than what they measured is
this mission's recurring failure mode. If the pin is wanted it needs a red-first cycle
commissioned as work, not a comment claiming knowledge nobody has.

## `--all` cannot compose from the per-project purges, and the reason is measured

FR-017's `purge_all_events` (`d2ad9c8b5f`) is deliberately **its own read of both tables**
rather than a loop over `distinct_project_uuids()` plus `purge_identity_less_events`. The
strongest available union was run against a store seeded with every population, and three
survived:

```
surviving journal : ['E-blank', 'E-whitespace']
surviving ledger  : ['E-ghost']
```

1. **`project_uuid = ''`** — `distinct_project_uuids()` *returns* it (it is not NULL), but
   `read_identity_projection` filters falsy uuids and `purge_project_events` blanks a falsy
   selector to select-nothing, while `iter_rows_missing_identity` is `IS NULL`-only.
   Measured: `purge('')` → `purged=0`.
2. **`project_uuid = '   '`** — the worse one, and nobody predicted it. The projection *can*
   return it (`projection(['   ']) → ['E-whitespace']`), but the purge strips its selector to
   `''` and selects nothing. **Visible in the census, unreachable by any purge.**
3. **A ledger row whose `event_id` has no journal row** — the union only ever collects ids
   *from the journal*. Not hypothetical: `gc_payloads` in this same module deletes journal
   rows while preserving ledger history **by design** (FR-010), so **every machine that has
   run `sync gc` is in this state.**

C-003 is respected because only *selection* differs — deletion still goes through the one
shared `_purge` core, so there is no second DELETE path. The non-composability is **pinned**,
so if a later change makes the union total, that test fails and the decision is revisited
rather than silently outliving its reason.

## NFR-006's differential was vacuous for one population

`_journal_census` read its identity-less bucket from `count_missing_identity()` (`IS NULL`)
while attributing every other row through a projection that **drops falsy uuids**. A
`''`-uuid row was therefore counted in **neither** bucket: measured, `census sum = 5` against
`count() = 6`.

This matters far beyond a wrong total. **Every NFR-006 differential subtracts this census**,
so a population absent from both buckets has a differential of zero *by construction* — a
purge could move those rows and still report, truthfully by its own arithmetic, "0% of any
other project's rows affected". The mission's own success metric was blind to the exact
population most likely to be malformed.

Fixed by deriving the bucket as `count() - attributed`. For the ordinary case the derived
number equals `count_missing_identity()` exactly, so no existing report changes — the fix
adds a population rather than restating one.

## Two stores, deliberately not one transaction

A failure injected between the two deletes leaves the **ledger** delete committed and the
journal untouched. That is the recoverable direction — the ordering `_purge` already
documents — and a re-run converges. Recorded as a **pinned observation** rather than a
comment, because "this falls the safe way" is a claim that should fail loudly if the
ordering is ever reversed.

## One deliberate omission, recorded as a decision

`purge_identity_less_events` still cannot remove a `''`-uuid row; only `--all` can. Widening
it would mean widening `iter_rows_missing_identity`, whose `IS NULL` restriction is exactly
what makes the backfill **idempotent** (NFR-004/SC-007). It therefore needs its own selector
rather than a widened one, and belongs to whoever owns FR-011. The census fix above turns
those rows from *invisible* into *observable-but-only-removable-by-`--all`*, which is
strictly better and does not pretend to be complete.

## Pre-fix local-commit frames are attributed by store locality, not by slug

WP08's brief offered two ways to purge frames written before WP12 added `project_uuid`:
`--all`-shaped, or match the mission slug in `changed_files`. The implementer took
**neither** and grounded a third better (`b6b3598ecc`).

`pending_local_commits` is **per-checkout** state — `_sync_state_path` puts the file inside
the checkout, and `git/commit_helpers.py:1150` calls `emit_local_commit(repo_root=repo_root)`
for that same checkout. So an unattributable frame in project X's file **is X's own content**:
its `changed_files` are paths in X's repository. Attributing it to X therefore cannot reach
another project's entries, which is exactly what keeps NFR-006's "0% of any other project's"
true, and it needs no new operator input.

The vouching is checked rather than assumed: `_checkout_vouches_for` admits the
identity-less bucket only when the checkout declares the target as its own uuid
(case-insensitively). A checkout declaring a *different* project, or none, vouches for
nothing and its frames remain for the `--all` selector.

Slug-matching was rejected on four grounds: the slug is not a project-scoped identifier,
no project→slug map exists at purge time, it would make the operator hand-type the
engagement name they are trying to erase, and it reduces to the same locality argument
anyway.

One sharp detail: blank selectors must select nothing, and this matters **more** here than
in the journal, because `IDENTITY_LESS_FRAME_KEY` *is* `""` — an unstripped selector would
silently vacuum precisely the population at issue.

## `_ws_client` is dead; the connect-time flush is the live path

Settled independently while building the frame purge, and it answers the question left open
after WP12: four occurrences of `_ws_client` in `src/`, **all reads or comments**
(`sync/local_commit.py:683`, `sync/__init__.py:354,358,373`), with no writer and no
`setattr`. So `emit_local_commit`'s **immediate send cannot fire in production**, and the
**connect-time flush is the live egress route**.

Consequence for WP12's gate: it is right that T027 gated the flush and not only the
steady-state send — had it gated only the immediate send, it would have gated the dead half
and left the live one open. The gate's placement was correct for a reason nobody had
established at the time it was written, which is worth recording as luck converted into
evidence rather than as vindication.

## The egress inventory was incomplete, and the mutants that proved M1-1 also proved a gap

An independent re-review of the four consent-gate commits **approved all four** and then found
two egress paths the dossier never named (FR-025, FR-026), plus FR-021's defect still open at
field level (FR-027). Recording what generalises.

**The bug class is narrower than "cwd" and wider than "the journal".** Every path found so far
fails the same test: *does it reach a consent answer through something other than the data's
own `project_uuid`?* FR-025 reaches it through `repo_root`; FR-026 through machine-global
arming plus daemon scope. Neither involves cwd, and neither touches the journal — which is why
searching for cwd-derived reads in `sync/` and `delivery/` could not have found them.
`invocation/` was never searched because it was never listed.

**`is False` is not `not`.** FR-025's guard reads `if sync_enabled is False: return`, and its
resolver returns `None` for *both* "no resolver registered" and "the resolver raised". A
tri-state where two of the three states mean "unknown" and the guard only tests one of them is
FR-003's defect with different syntax. Worth grepping for as a pattern, not a one-off.

**M1-1's two-place gate is vindicated by measurement, not argument.** Both sites call the same
`_project_consents_to_capture` funnel, so there is one chain and C-003 holds; and `_route_event`
composes them **conjunctively** (`drain_blocked_reason is None` AND consent), so any
disagreement can only narrow egress, never widen it — structural rather than lucky. Both sites
are load-bearing for *different* invariants: site 1 for the stored `drain_blocked_reason` column
that `delivery/selection.py` treats as terminal, site 2 for the network. Proven by mutation:
stripping site 1 leaves all 9 anchor pins green and is killed only by
`test_lifecycle_readiness.py`; stripping site 2 is killed by 2 anchor pins with the leak text
`published_uuids == [A,B,A,B]`.

**An honest coverage gap inside a passing verdict:** M1-1's own anchor file does not pin site 1.
That coverage lives in a file the commit only touched incidentally.

## The `queue_event` precondition must be a test, because the existing guard is name-shaped

The judgement that `queue_event` is not egress was independently re-verified — every live
reader traced by hand (`sync diagnose` → local validation, `_unauthenticated_sync_result` →
local classification, `drain_queue` non-mutating, `batch_sync`/`sync_all_queued_events` with
zero callers in `src/`). The substance holds.

The **enforcement** does not. `RETIRED_DRAIN_NAMES` is two literal names, probed directly
against synthetic sources:

| fed to `_offending_references` | result |
|---|---|
| `from .batch import batch_sync` | CAUGHT |
| `batch_sync(queue=q)` | CAUGHT |
| `queue.drain_queue(...)` then `urllib.request.urlopen(...)` | **MISSED** |
| `for e in queue.drain_queue(...): await ws.send_event(e)` | **MISSED** |

So the guard is non-vacuous for a *literal restoration* and blind to **any new queue-backed
sender** — precisely the shape that flips the recorded precondition. Prose says "if a
queue-backed sender is ever restored this must be gated first"; enforcement covers two names.
It should key on `drain_queue`/`process_batch_results` readers reaching a network sink.

## Nothing is currently decoration — verified file by file

The filename-matched conftest guard was checked against **every** pin file rather than argued
about. Protected by token: seven files. Unprotected but provably unmasked: `test_routing.py`
(the fixture patches the `batch`/`runtime` re-exports, never `sync.routing`'s own function),
`test_background_body.py` / `test_body_integration.py` (body path, not patched),
`test_target_authority_wiring.py` (records real consent). Unprotected and steering its own
predicate: `test_lifecycle_readiness.py` — proven live, it is what killed the site-1 mutant.
`tests/specify_cli/sync/` is a different package the conftest does not reach.

So the guard is a latent hazard, not an active one. The durable fix is to key on **what a test
patches**, not on its filename — `test_events.py` already rides the blanket grant with 85
suppressed installs, so a negative per-project publish pin added *there* later would be
silently masked.

## FR-017's `--all` is per-checkout, and the CLI must say so (operator decision, 2026-07-30)

For `pending_local_commits`, one `--all` call clears **only the invoking checkout's** queue.
There is no registry of checkouts, so other `sync-state.json` files cannot be enumerated.

**Decided: per-checkout, named honestly.** The CLI must not present this as machine-wide
erasure. A registry was rejected as new capability and new state to keep correct; a
best-effort filesystem scan was rejected because it can never prove completeness, which
would leave the erasure claim unprovable while sounding total — the worst of the three.

This matters more than a wording choice. An operator purging a client engagement needs to
know the scope of what they just did; "erased" that silently means "erased here" is the same
class of defect as a gate that reports success for having done nothing.

## Only a YAML `bool` records a consent decision (FR-027, `34e4e16496`)

19 non-bool `enabled` shapes granted before the fix, not the four reported — `enabled: False`
unquoted was the only one that already denied. Isolated properly rather than trusted: the probe
was re-run in a clean HEAD worktree with only the three changed source files copied in, giving a
byte-identical table, so the result is attributable and not another agent's in-flight work in the
shared tree.

**Decision: only a YAML `bool` records a decision; every other present value is a fault. No
string form is accepted in either direction.** Three grounds, and the second is the decisive one:

1. Accepting `"false"` buys nothing, since a fault already denies.
2. The same table would then have to rule on `"true"`, `1`, `"yes"`, `"on"` — which become
   **grants**. A leak surface with no upside. The two directions are not symmetric, so a rule
   that looks even-handed is not.
3. `no`/`off`/`yes`/`on` are strings only because ruamel is YAML 1.2. Accepting them means
   re-implementing implicit typing this module does not own.

A fault is also **reportable**, whereas silently honouring `"false"` would leave
`enabled: "true"` broken *and* silent.

**Absence stays absence, with a sentinel.** `dict.get` collapses "key missing" with "key holds
null", so an explicit `enabled: null` is a fault (the key was written; nothing usable recorded)
while a *missing* key is not. This **deliberately diverges** from `identity/project.py`'s
`None → absence`, and the reason is worth keeping: identity's absence **mints** a uuid, which is
harmless; consent's absence **defers to a possibly-stale grant**. Same shape, opposite safe
direction. A considered non-uniformity, not an inconsistency — the C-003 rule is one
representation of one invariant, and these are two invariants.

**The FR-024 residual was closed by asking, not re-deciding.** It delegates to
`ProjectIdentity.from_dict`, the single parse site FR-024 made authoritative, so there is one
notion rather than a fourth. `routing.py` needed no logic change at all: it already consumes
`project_local_consent_fault`, so widening the notion reached the gate for free — which is the
payoff for having put that seam in one place.

## A valid uuid spelled non-canonically discarded its own project's refusal

Found by probing the set rather than the reported cases, and **measured granting**. Raw file
text was compared against the canonical uuid the journal stores, so an UPPERCASE, dash-less or
`urn:uuid:`-prefixed spelling of the project's *own* uuid read as *some other project* — and the
committed refusal beside it was discarded. Now parsed on both sides.

This is the same lesson as FR-024's padded-uuid decision, one layer out: two places compared
representations of the same identity without agreeing on the representation. Worth remembering
that `str == str` on an identifier is a comparison of *spellings*, not of identities.

## The machine-wide-denial finding is real but far less reachable than it looked

A reviewer measured that one unreadable sibling config denies every project on the machine, and
noted it contradicts FR-020's own recorded rationale. FR-027 makes *more* file contents qualify
as a fault, so the surface grows — direction unchanged and fail-closed.

But the reachability is much narrower than "any sibling checkout", and this was measured:
**every production supplier of `checkout_roots` offers at most one root — the cwd's project
root** (`selection.py:101`, `background.py:298`, `runtime.py:151`, `local_commit.py:330`,
`sync/__init__.py:373`). So the trigger is **the drain's own checkout being broken**, not an
arbitrary sibling's. That is a materially different defect: annoying and self-inflicted rather
than a machine-wide outage caused by an unrelated project. The contradiction with FR-020's
rationale stands and is not resolvable from within `consent.py`/`config.py`/`routing.py`.

## Two residual holes, both with a stated reason for not closing them

- **Mis-spelling the *key*** (`enabledd: false`) still voids the refusal, and is indistinguishable
  from a missing key without a closed whitelist of `sync.*` keys — which would break forward
  compatibility with any newer key an older CLI has not heard of. Recorded rather than fixed.
- **Genuine identity absence plus a grant** still captures with `project_uuid=None`. Not fixable
  without denying every pre-`init` checkout. Reachability is low because `enable_checkout_sync`
  refuses to write a grant without a uuid, so the grant must be a leftover from a config that
  once had identity and lost it.

## FR-025's severity, settled by tracing rather than by preferring one report

Two agents appeared to contradict each other and did not. The FR-025 implementer measured **1
envelope with verbatim `request_text`** in a clean pre-fix worktree "with the real sync-side
registration — no stubbed resolver". The egress enumerator reported the same path **dead in
production**. Resolved by tracing the transport, which neither claim covered:

`propagator._get_saas_client` → `adapters.get_saas_client` → the factory registered at
`sync/__init__.py:411` → `getattr(token_manager, "_ws_client", None)` → **no writer anywhere in
`src/`**. So the factory returns `None` and `_propagate_one` early-returns before sending.

Both statements were true. "No stubbed **resolver**" is a claim about the *consent* seam, not the
*transport*; the leak measurement supplied a client by other means. The lesson is about reading
reports, not about either agent: **two accurate reports can look contradictory when each is
precise about a different half of the same path.** The resolution came from tracing the half
neither had claimed.

**What stands, and what is corrected.** The guard defect was real and is fixed, together with
three siblings on the same payload. Its *reachability* argument also stands on its own terms —
`cli/commands/dispatch.py` takes `repo_root` from `find_repo_root()`, whose comment reads
"Fallback: support plain git repositories that do not contain `.kittify` yet", while consent
resolution needs a `.kittify` root, so in any plain git checkout the two disagree and the
undetermined branch is taken **with nothing misconfigured**. What is corrected is the leak's
*consequence*: with the transport dead, the undetermined branch reached a `None` client rather
than the network. "Critical / measured leaking" overstated it; the fix is correct
defence-in-depth, and it is now in place *before* the transport could be wired, which is the
right order.

## Three permissive defaults on one payload, found only by assuming the report was a sample

FR-025 was reported as one guard. The implementer found three more of the **same shape** on the
same egress payload, all in its own scope, all fixed in the same commit:

- `_coerce_event_kind` — an unclassifiable `event` fell to `EventKind.STARTED`, whose rule is the
  permissive one. Now: unclassifiable ⇒ not projected.
- `_coerce_mode` — **absent** and **malformed** `mode_of_work` both became `None` ⇒
  `task_execution`, which includes the body. Now split: absence keeps its documented default
  (every completed event legitimately has no mode); malformation refuses. The absent/malformed
  distinction is the same one FR-027 needed for `enabled: null` versus a missing key.
- `projection_policy.py:80` — `POLICY_TABLE.get(key, _DEFAULT_RULE)` where the default arm was
  **the most permissive rule**, so a pair with no row disclosed the body. Now `_NO_POLICY_RULE`,
  pinned by deleting a table row at runtime.

**Generalisation worth carrying:** a `dict.get(key, DEFAULT)` on a policy table is a fail-open
guard wearing different syntax. The "unknown state treated as a definite answer" invariant covers
`is False`, a truthiness test on a legitimately-falsy value, a `match` with no default arm, **and
a lookup whose default is the permissive row.** Grepping for `is False` alone would have found one
of these four.

## The `sync/__init__.py` change was unavoidable, and the rename was deliberate

`tests/architectural/test_integration_boundary.py` forbids `invocation/` from importing
`specify_cli.sync.*` in **any** form — full-AST walk including lazy function-body imports, with an
empty `ALLOWLIST` ratcheted at `== 0`. So the consent funnel can only reach CORE through a
registry slot that `sync` fills, and the contested edit was the only way to satisfy "resolve from
the consent chain".

`register_sync_routing_resolver` was **renamed** to `register_egress_consent_resolver` rather than
a second slot added, on the implementer's reasoning: an additive slot would have left the old one
registered and production-dead, **and a seam named "sync routing" that answers a consent question
is the naming lie that caused this bug.** Recorded because a prior mission's dossier
(`kitty-specs/integration-boundary-01KW0PBE/`) documents the old names, and that divergence should
not later read as drift.

## `project_uuid` is not on the Op envelope — reported, not invented

Neither `OpStartedEvent` nor `OpCompletedEvent` carries a `project_uuid`
(`invocation/record.py:45,72`). Rather than invent a fallback, the fix reuses the mission's single
checkout→project derivation on the ground that an Op's owning project *is* the checkout it was
recorded in — the same locality argument WP08 made for `pending_local_commits` and E6. Putting a
`project_uuid` on the envelope is a schema change (`record.py`, the writer,
`contracts/op-record-events.md`) and remains an open operator decision.

## An Op's project is derived from its checkout, not carried on the envelope (operator, 2026-07-30)

Neither `OpStartedEvent` nor `OpCompletedEvent` carries a `project_uuid`
(`invocation/record.py:45,72`). FR-025's implementer declined to invent a fallback and
escalated the schema question rather than deciding it.

**Decided: keep the locality derivation.** An Op's owning project *is* the checkout it was
recorded in, and that derivation reuses the mission's single checkout→project seam rather than
adding a second source of truth. No schema change, no migration of existing `kitty-ops` records
during a P0 mission.

This is the **third** time this mission has reached for the same argument, which is why it is
worth naming as a pattern rather than a one-off: WP08 used it to attribute pre-fix
`pending_local_commits` frames (a frame in project X's per-checkout file is X's own content, since
its `changed_files` are paths in X's repository), and the egress enumeration accepted it for E6.

**Its precondition, stated so the derivation is falsifiable:** it holds only while both
`InvocationSaaSPropagator` construction sites pass the *invoking* checkout, and while the Op
records read are that checkout's own `kitty-ops/`. If either ever becomes true of a different
checkout — a daemon sweeping other projects' Op records, say — the derivation silently becomes a
cross-project substitution of exactly the kind this mission exists to close, and the envelope
schema change becomes mandatory. The enumeration flagged that this locality argument was "nowhere
written down"; it is now.

## `--all` must reach the body-upload queue (operator, 2026-07-30)

The purge CLI found that `--all` cannot empty the body-upload store: there is no
`purge_all_body_uploads`, and `remove_project_tasks` strips its argument, so a blank or
whitespace `project_uuid` row is reachable by **no selector at all**. The implementer reported it
rather than calling `remove_project_tasks` directly, which would have been a second deletion path
outside the primitives — the right call.

**Decided: add the missing primitive.** One deletion path per store, and `--all` means all four.
Widening `remove_project_tasks` was rejected: it is shared by other callers, and a blank selector
that matches everything is precisely the hazard the frame purge had to guard against
(`IDENTITY_LESS_FRAME_KEY` *is* `""`, so an unstripped selector would vacuum the population at
issue).

## Two non-egress fail-open permission decisions, folded in (operator, 2026-07-30)

FR-025's pattern census found the consent surface fails closed everywhere except the seam it
fixed — a genuinely reassuring result. It also found two **non-egress** permission decisions that
lean permissive on "unknown":

- ~~`sync/owner.py:503,730` — a swallowed exception permits `remove_owner_record` and reports a
  successful kill.~~ **This bullet was WRONG in two places and is corrected 2026-07-30.** Measured
  end to end: `True` is the **refusing** answer — `is_orphan` True yields
  `daemon_status == "orphan"`, `BoundaryFailureSet.ok is False`, and every mutating sync command
  refuses at preflight. **No caller of `is_orphan`/`list_orphan_records` calls
  `remove_owner_record`**; the only `src/` call is the daemon's own pid/port-guarded shutdown hook,
  and the "cleanup" is a `rm <owner.json>` **hint printed for a human to type**. `:730` points at an
  `except TypeError` test-double branch, not a swallowed-exception permission. **Flipping it would
  have been the actual fail-open**: an unverifiable daemon would report `present`, the orphan row
  would vanish, and the preflight would pass. Left alone deliberately.

  A third reason it must stay, which nobody anticipated: **the guard is interpreter-dependent.**
  Measured on three interpreters — Python 3.11.15 and 3.12.13 (**CI's version**) propagate `EACCES`
  out of `Path.exists()`, so `except OSError` is the only thing stopping a documented *pure
  predicate* from raising `PermissionError` through `sync status`/`doctor`/preflight. Python 3.14.4
  delegates to `os.path.exists`, swallows it, and reaches the same verdict by another route.
  Deleting the guard breaks 3.11/3.12 **only** — green locally, red on CI.
- `invocation/executor.py:474` `_read_started_mode` — **absent** and **malformed**
  `mode_of_work` both collapse to `None` and skip FR-009 evidence-mode enforcement, so a
  hand-edited `kitty-ops` line buys evidence promotion on an advisory or query Op. The remedy is
  the same absent/malformed split FR-027 needed for `enabled: null` versus a missing key, and
  FR-025 needed for `_coerce_mode`. **Three occurrences of one distinction in one mission.**

Folded in rather than filed: both are the fail-open shape this mission exists to close, and the
audit that found them is already done — refiling costs more than fixing.
