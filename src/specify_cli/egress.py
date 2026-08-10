"""The one editable presentation of the project-egress refusal policy (#3110).

This module is owned by **neither transport**. Before it existed the same policy
was written twice — once for the tracker SaaS transport (#3030 FR-029) and once
for the widen-mode SaaS client (#3030 FR-030) — as two near-identical modules
that a future editor could change independently. FR-008 requires **exactly one
editable presentation**, and this is it: one sentence template shared by the
three refusal-member verdict branches (split from a former single ``DENIED``
by the egress-single-authority mission), two further verdict branches for the
undetermined causes, one ``None`` guard and one import-failure degradation.

**Each transport passes its own identifier-set fragment as an argument.** The two
sets are asymmetric on purpose: the tracker carries no ``decision_id`` and the
SaaS client carries no ``project_slug`` or issue titles, so a single string
naming the union would tell a tracker operator that a decision id was at stake.
The fragments are *arguments*, not second presentations — a "consolidation" that
left two templates and merely parameterised them would not satisfy FR-008.
Consolidating changed **no operator-visible text**: both refusal strings render
byte-for-byte as they did before.

Why this module asks ``invocation.adapters.resolve_egress_consent`` rather than
resolving consent itself — **FR-012**
--------------------------------------------------------------------------------

**FR-012 is High-impact and deliberately has no success criterion, so this
paragraph is the only thing standing between a future editor and a second
consent chain. It is written down here because nothing else would catch its
loss.**

C-003: project consent is represented **once**, and this module **must never
re-derive the checkout to project to consent chain locally**. The single
derivation lives in ``sync/__init__.py``'s ``_egress_consent_resolver``, which
reads the checkout's identity through
``routing.resolve_checkout_sync_routing_readonly`` and then asks
``sync.consent.resolve_project_consent``, whose ``granted`` verdict wraps the
same ``consented_project_uuids`` funnel the drain (``delivery/selection.py``),
the emitter, the daemon and ``local_commit`` all walk, over the one declared
precedence chain (project-local, machine index, env). Re-deriving it here would
be a second expression of one invariant, free to drift, which is the defect
class this mission keeps re-finding.

The seam is registered by ``sync`` into the CORE registry slot in
``invocation/adapters.py``, so reaching it costs one import and no new chain.
:class:`~specify_cli.invocation.adapters.EgressConsent` already carries the
fail-closed vocabulary this gate needs: **only** ``GRANTED`` permits egress, and
both undetermined causes (``NO_RESOLVER``, ``UNANSWERABLE``) refuse while staying
distinguishable for diagnosis.

Note the layering rule did **not** force this route.
``tests/architectural/test_integration_boundary.py`` forbids the CORE set
(``core/``, ``status/``, ``readiness/``, ``invocation/``) from importing the
INTEGRATION set with an allowlist ratcheted at zero. This module is classified
INTEGRATION (C-005, asserted by SC-025), so it may reach ``specify_cli.sync``.
The registry route is chosen on the single-chain ground above, not because a
gate demanded it.

What a refusal is **not** allowed to be
---------------------------------------

Not ``is_saas_sync_enabled()``. That flag is machine-global *arming*, which the
spec states is never a grant and which is the 2026-07-27 incident's own
mechanism — one exported ``SPEC_KITTY_ENABLE_SAAS_SYNC`` carried five
never-opted-in projects along with the intended one. Not the team scope, not the
current working directory, and not "we have a token". Only the project that owns
the data can consent for it.

Not a silent proceed when the project cannot be determined, either. An
unresolvable project is a **refusal** (FR-003 / NFR-001): inability to determine
consent is never consent. That same defect was found independently in four
places, most recently as ``if sync_enabled is False`` where the resolver returned
``None`` for two unrelated causes.

The attribution precondition — stated, because it is load-bearing
-----------------------------------------------------------------

The gate is handed a **checkout root**, and the funnel resolves it to that
checkout's ``project.uuid`` before asking consent. So consent is answered
per-*uuid*, not per-path — the root is an input to the resolution, not a
substitute for it. What the root *does* decide is **whose** consent gets asked,
and that is a real precondition:

    **Every construction site must pass the root of the project that owns the
    record the request will carry.**

If it ever passes some other root, the gate answers correctly for the wrong
project — which is this mission's entire bug class (cwd, ``repo_root``,
machine-global arming, daemon scope and a checkout-level grant were each a place
where consent was answered by *where the code was standing* rather than *whose
data was moving*). It is written down here rather than left implicit because an
unstated locality argument reads as obviously fine until someone adds the caller
that breaks it, and nothing tells them they broke it.

Two safety nets stand behind the precondition, and neither replaces it: a root
that is not a project root at all resolves to no uuid and therefore **denies**,
and a checkout that declares a *different* uuid than the one being asked about is
ignored by ``consent.py``'s level-1 vote. What neither net catches is the case
this precondition exists for: a *valid* root for the *wrong* project.

Tracker transport — the three construction sites that exist today
-----------------------------------------------------------------

1. :func:`~specify_cli.tracker.origin.bind_mission_origin` — **derived from the
   data, not from locality.** ``_resolve_repo_root(feature_dir)`` walks *up* from
   the very directory whose ``meta.json`` supplies the ``mission_id`` and
   ``mission_slug`` being sent. The **non-interactive** creation path closes the
   loop: ``core/mission_creation.py`` builds ``feature_dir = resolved_root /
   kitty-specs / <slug>`` and passes both, ``origin_consumer`` reads the issue
   ``title`` from ``resolved_root/.kittify/pending-origin.yaml``, and walking back
   up from ``feature_dir`` returns ``resolved_root``. Every field in the payload
   originates under the root the client is attributed to. This holds even when
   ``create_mission_core`` is given an explicit ``repo_root`` that differs from
   the cwd, because the dossier, the meta and the pending origin all live under
   *that* root — so a cwd/owner divergence cannot arise here. **This site fires
   during mission creation with no operator action required**, which is why it is
   listed first.
2. :class:`~specify_cli.tracker.saas_service.SaaSTrackerService` — an
   operator-invoked command's own checkout (``require_repo_root()`` ->
   ``locate_project_root(Path.cwd())``). A locality argument, in its benign form:
   the routing keys (``project_slug`` / ``binding_ref``) and the pushed items are
   read from *that same* root's config and store, so the subject of the command
   genuinely is the checkout the operator is standing in. Same ground on which the
   egress inventory rules ``cli/commands/sync.py:1107,1204`` correct rather than
   defective.
3. :func:`~specify_cli.tracker.origin.search_origin_candidates` — takes the root
   from its caller and has **no production caller today**. Whoever wires one owes
   this precondition.

What would falsify the tracker enumeration — check these before adding a caller:

* A **daemon, sweep or batch** that iterates projects: constructing one client
  and reusing it across projects, or building it from the sweep's own checkout
  while the payload comes from a different project's dossier, breaks the
  invariant without changing a line in this module. Such a caller must construct
  a client per project, from that project's root.
* Passing a ``feature_dir`` that is **not** under the ``repo_root`` whose
  ``pending-origin.yaml`` supplied the issue title — the two halves of the payload
  would then belong to different projects. Today ``mission_creation`` derives both
  from one root, so it cannot happen.
* Resolving the root from ``Path.cwd()`` at a call site whose data came from
  somewhere else.

Widen-mode SaaS client — the four construction sites that exist today
----------------------------------------------------------------------

All four reach the client through
:meth:`~specify_cli.saas_client.client.SaasClient.from_env`. What leaks on this
transport is subtler than a payload and no less disclosing: four of the five
endpoints are GETs that carry ``mission_id`` **in the URL path**, documented as
"ULID **or** slug" — and a mission slug is a client engagement name. A request
line is not a safer place to put one than a request body.

1. ``cli/commands/charter/interview.py``, 2. ``missions/plan/plan_interview.py``,
3. ``missions/plan/specify_interview.py`` — the interview's own ``repo_root``, and
   the data is read back from that same root: ``mission_id`` comes from
   ``_get_mission_id(repo_root, mission_slug)`` (i.e. ``kitty-specs/<slug>/meta.json``
   under that root) and the discussion ``decision_id``\\ s come from
   ``WidenPendingStore(repo_root, mission_slug)``. Owner and root agree by
   derivation.
4. ``cli/commands/decision.py`` (``spec-kitty decision widen``) — **the weakest of
   the four, and the only one whose subject is not derived from its root.** The
   root is ``locate_project_root() or Path.cwd()`` while ``decision_id`` is an
   operator-supplied CLI argument, so an operator can name a decision belonging to
   a different project than the checkout they are standing in, and consent is then
   answered for the checkout rather than for the decision's owner.

   **The argument that used to bound this entry was measured false and has been
   removed.** It claimed the exposure was benign because the id is a ULID and
   therefore carries no engagement name. There is **no validation anywhere on this
   path**: the value is interpolated raw into the request line exactly as supplied,
   so a slug — or any other text an operator types — reaches the wire unmodified.
   The narrowness of the POST body (``invited_user_ids`` only) bounds *that*
   request and nothing else; the id travels in the URL of every GET on the path.

   **What actually bounds this site is an ownership check before the request is
   built** — FR-001/FR-002/FR-003: establish from files under the acting root that
   this checkout owns the named decision, and refuse otherwise, so a divergence
   becomes a loud refusal rather than a silent cross-project send. Until that gate
   is in place on this path, treat the entry as *unbounded*, not as bounded by the
   id's shape. If the endpoint ever grows a slug-accepting form the exposure widens
   again, and the id must be resolved to its owning project first.

What would falsify the SaaS enumeration: a daemon, sweep or batch constructing
one client and reusing it across projects; a widen flow driven from a checkout
other than the mission's own; or any future endpoint that accepts an identifier
whose owner is not derivable from the root the client was built with. A root that
is not a project root resolves to no uuid and therefore denies — a safety net,
not a substitute, because it does not catch a *valid* root for the *wrong*
project.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only, never imported at runtime
    from specify_cli.invocation.adapters import EgressConsent

#: Refusal text for the case where no checkout was offered at all. Kept separate
#: from the resolver's own vocabulary because it is a *caller* fault — a transport
#: was constructed without being told whose data it carries — and the operator fix
#: differs from "this project has not opted in".
#:
#: Deliberately **not** in ``__all__`` (FR-011): only names with a real ``src/``
#: consumer are advertised, so the symbol-level dead-code ratchet stays honest.
UNDETERMINED_PROJECT_REFUSAL = (
    "the project that owns this data could not be determined, so its consent to "
    "hosted sync could not be resolved; refusing to transmit (an undetermined "
    "project is never a consenting one)"
)

#: **The shared sentence template** — the one editable presentation FR-008
#: requires. ``{identifiers}`` is the calling transport's own identifier-set
#: fragment; nothing else in this sentence varies by caller, and no identifier
#: kind may be hard-coded into it (that would hand one transport the other's
#: vocabulary, which US2-AS2 forbids).
_DENIED_TEMPLATE = (
    "the project at {project_root} has not consented to hosted sync, so its "
    "{identifiers} must not be transmitted; record a "
    "decision in the project's own .kittify/config.yaml (sync.enabled) or "
    "run `spec-kitty sync opt-in` for it"
)

#: Verdict branch: the INTEGRATION sync package was never loaded, so no resolver
#: is registered. Names the missing thing, because "denied" alone would send the
#: operator to check their consent record instead of their install.
_NO_RESOLVER_REFUSAL = (
    "no hosted-sync consent resolver is registered, so this project's "
    "consent could not be resolved; refusing to transmit"
)

#: Verdict branch: the resolver ran and could not answer. Distinguishable from
#: :data:`UNDETERMINED_PROJECT_REFUSAL` despite both containing "could not be
#: determined", because the operator fix differs — a faulting consent chain is
#: not the same problem as an unattributed transport.
_UNANSWERABLE_TEMPLATE = (
    "consent for the project at {project_root} could not be determined "
    "(the consent chain raised or returned an unrecognized answer); refusing to "
    "transmit, because inability to determine consent is not consent"
)

#: Verdict branch: a member added to :class:`EgressConsent` after this module was
#: written. ``permits_egress`` has already refused it; naming it here keeps the
#: operator message honest rather than silently reusing one of the three
#: refusal members' shared remedy.
_UNRECOGNISED_VERDICT_TEMPLATE = (
    "hosted-sync consent for the project at {project_root} resolved to "
    "{verdict!r}, which does not permit egress; refusing to transmit"
)

#: Degradation for an unimportable hosted-sync package (FR-013). Carries the
#: exception text so the operator can act on the actual failure.
_IMPORT_FAILURE_TEMPLATE = (
    "the hosted-sync package could not be loaded, so this project's consent "
    "could not be resolved; refusing to transmit ({exc})"
)

#: The Channel-1 diagnostic labels :func:`_egress_decision` produces
#: (egress-single-authority mission, data-model "Channel-1 diagnostic state").
#: Defined **here**, privately, rather than imported from
#: ``tracker/egress_verdict.py`` — that module imports *from* this one (see its
#: module docstring's C-004 note), so the dependency cannot run the other way.
#: The consumer there is expected to read these same string values back out of
#: :class:`EgressDecision` rather than recomputing them locally.
_CHANNEL1_STATE_GRANTED = "granted"
_CHANNEL1_STATE_NO_RECORD = "no_record"
_CHANNEL1_STATE_RECORDED_REFUSAL = "recorded_refusal"
_CHANNEL1_STATE_NOT_CONSENTABLE = "not_consentable"
#: The degraded, generic-rendering label — reached for ``NO_RESOLVER``,
#: ``UNANSWERABLE``, resolver-import-failure, and (as a fail-safe) any future
#: :class:`~specify_cli.invocation.adapters.EgressConsent` member this module
#: has not named yet. Always paired with ``generic=True``.
_CHANNEL1_STATE_UNCLASSIFIED = "unclassified"
#: Reserved for the ``project_root is None`` case only — never reused for a
#: degraded verdict. See :class:`EgressDecision`.
_CHANNEL1_STATE_UNDETERMINED = "undetermined"


@dataclass(frozen=True, slots=True)
class EgressDecision:
    """The one decision :func:`_egress_decision` computes, in full.

    ``permits`` always equals the obtained
    :class:`~specify_cli.invocation.adapters.EgressConsent` member's own
    ``permits_egress`` (or ``False`` when *project_root* was ``None``).
    ``refusal_message`` is ``None`` exactly when ``permits`` is ``True``, and
    otherwise the byte-identical operator-facing string
    :func:`project_egress_refusal` already returned. ``channel1_state`` and
    ``generic`` are the diagnostic pair ``tracker_egress_verdict`` composes into
    its own message (egress-single-authority mission Decision 3): a degraded
    verdict sets ``generic=True`` so a message composer keyed only on the three
    named refusal states can render generic wording instead of indexing a dict
    that does not have an entry for it.
    """

    permits: bool
    refusal_message: str | None
    channel1_state: str
    generic: bool


def _render_denied_refusal(project_root: Path, identifiers: str) -> str:
    """Render the shared template for *identifiers*, the caller's own fragment."""
    return _DENIED_TEMPLATE.format(project_root=project_root, identifiers=identifiers)


def _refusal_for_verdict(
    verdict: EgressConsent, project_root: Path, identifiers: str
) -> str | None:
    """Map a consent verdict to its operator-facing refusal, or ``None`` to permit.

    The verdict branches live here and nowhere else (FR-008/SC-015).
    ``permits_egress`` is asked rather than comparing against ``GRANTED``, so a
    future member cannot silently widen egress. All three refusal members split
    from the former ``DENIED`` (``NO_RECORD``, ``RECORDED_REFUSAL``,
    ``NOT_CONSENTABLE``) render the same shared template — no fall-through to
    the unrecognised-verdict branch for any of them.
    """
    from specify_cli.invocation.adapters import EgressConsent as _Verdict  # noqa: PLC0415

    if verdict.permits_egress:
        return None
    if verdict in (_Verdict.NO_RECORD, _Verdict.RECORDED_REFUSAL, _Verdict.NOT_CONSENTABLE):
        return _render_denied_refusal(project_root, identifiers)
    if verdict is _Verdict.NO_RESOLVER:
        return _NO_RESOLVER_REFUSAL
    if verdict is _Verdict.UNANSWERABLE:
        return _UNANSWERABLE_TEMPLATE.format(project_root=project_root)
    return _UNRECOGNISED_VERDICT_TEMPLATE.format(
        project_root=project_root, verdict=verdict.value
    )


def _channel1_state_for_verdict(verdict: EgressConsent) -> tuple[str, bool]:
    """Map a consent verdict to its ``(channel1_state, generic)`` diagnostic pair.

    Mirrors :func:`_refusal_for_verdict`'s branches so the two can never
    disagree about which members are the three named refusal states versus
    degraded. The permit branch asks ``permits_egress`` (not ``is GRANTED``),
    exactly as :func:`_refusal_for_verdict` does, so the two provably co-vary: a
    future permitting member cannot make one report ``granted`` while the other
    still refuses. Only the degraded members — ``NO_RESOLVER``, ``UNANSWERABLE``,
    and (as a fail-safe) any future member this module has not named — set
    ``generic = True`` (egress-single-authority mission Decision 3).
    """
    from specify_cli.invocation.adapters import EgressConsent as _Verdict  # noqa: PLC0415

    if verdict.permits_egress:
        return _CHANNEL1_STATE_GRANTED, False
    if verdict is _Verdict.NO_RECORD:
        return _CHANNEL1_STATE_NO_RECORD, False
    if verdict is _Verdict.RECORDED_REFUSAL:
        return _CHANNEL1_STATE_RECORDED_REFUSAL, False
    if verdict is _Verdict.NOT_CONSENTABLE:
        return _CHANNEL1_STATE_NOT_CONSENTABLE, False
    return _CHANNEL1_STATE_UNCLASSIFIED, True


def _egress_decision(project_root: Path | None, identifiers: str) -> EgressDecision:
    """Compute the single decision this module owns (egress-single-authority C-004).

    **Obtains** the :class:`~specify_cli.invocation.adapters.EgressConsent`
    member via :func:`~specify_cli.invocation.adapters.resolve_egress_consent`
    and derives every :class:`EgressDecision` field from that one member. This
    function performs **no** local consent/routing resolution and imports
    neither ``specify_cli.sync.consent`` nor ``specify_cli.sync.routing`` — the
    single derivation and the split-mapping both live once, in the registered
    resolver (``sync/__init__.py``'s ``_egress_consent_resolver``); see the
    module docstring's "Why this module asks
    ``invocation.adapters.resolve_egress_consent``" section (FR-012).

    *project_root* / *identifiers* have the same contract as
    :func:`project_egress_refusal`, which is a thin wrapper over this function
    returning only its ``refusal_message`` field.
    """
    if project_root is None:
        return EgressDecision(
            permits=False,
            refusal_message=UNDETERMINED_PROJECT_REFUSAL,
            channel1_state=_CHANNEL1_STATE_UNDETERMINED,
            generic=True,
        )

    # Importing ``specify_cli.sync`` is what *registers* the resolver into the CORE
    # slot (``sync/__init__.py::register_default_handlers``). Without it a process
    # that never loaded the sync package would get ``NO_RESOLVER`` and refuse every
    # send — fail-closed, but a false denial for a project that has genuinely opted
    # in. Deliberately not suppressed into a permit: if sync cannot be imported at
    # all there is no consent chain to consult, and that is an undetermined answer.
    #
    # This import stays **lazy and inside the function** (FR-013). A module-level
    # form would execute ``specify_cli/sync/__init__.py`` at transport-import time
    # and defeat the degradation structurally. Note this module is separately
    # routed into the ``sync`` CI filter group **by WP02, which lands alongside
    # this one** — that is job selection, not an import edge, and the two must
    # not be "tidied" to match each other. (Stated as a forward reference rather
    # than as present fact: nothing gates the claim, so if WP02 were dropped this
    # comment would silently lie.)
    try:
        import specify_cli.sync  # noqa: F401, PLC0415  (imported for registration)
    except Exception as exc:  # noqa: BLE001 - degrades to a refusal, never a permit
        return EgressDecision(
            permits=False,
            refusal_message=_IMPORT_FAILURE_TEMPLATE.format(exc=exc),
            channel1_state=_CHANNEL1_STATE_UNCLASSIFIED,
            generic=True,
        )

    from specify_cli.invocation.adapters import resolve_egress_consent  # noqa: PLC0415

    root = Path(project_root)
    verdict = resolve_egress_consent(root)
    channel1_state, generic = _channel1_state_for_verdict(verdict)
    return EgressDecision(
        permits=verdict.permits_egress,
        refusal_message=_refusal_for_verdict(verdict, root, identifiers),
        channel1_state=channel1_state,
        generic=generic,
    )


def project_egress_refusal(project_root: Path | None, identifiers: str) -> str | None:
    """Return why *project_root*'s project may not transmit, or ``None`` to permit.

    ``None`` — and only ``None`` — is permission. Every other outcome, including
    every future :class:`~specify_cli.invocation.adapters.EgressConsent` member, is
    a refusal string suitable for an operator: these are interactive commands, and
    a silent no-op would leave someone running ``sync push`` believing their data
    shipped.

    *project_root* is the checkout that **owns the data being sent** — the
    mission's own repository, resolved from the mission's ``feature_dir`` or from
    the tracker config being pushed — never the process's current working
    directory. Passing ``None`` refuses. See the module docstring for the
    attribution precondition this rests on, and for the per-site enumeration of
    every construction site that must satisfy it.

    *identifiers* is the calling transport's **own** identifier-set fragment, and
    it is required rather than defaulted: a transport that did not say what it can
    put on the wire must not be able to render a refusal that quietly names
    nothing. Its bar is scoped (ruling PB-3) to the identifiers of *the project
    whose consent was refused* — not the destination team and not recipient ids.
    Corollary: nobody may "fix" this string by appending the destination team's
    name; that would *add* an identifier to an operator-facing message rather than
    remove one.

    A thin wrapper over :func:`_egress_decision` (egress-single-authority mission
    contract §3) — this function's ``str | None`` contract is unchanged; both of
    its consumers (``saas_client/client.py``, ``tracker/egress_verdict.py``) see
    no difference.
    """
    return _egress_decision(project_root, identifiers).refusal_message


# Only names with a real ``src/`` consumer are advertised — the symbol-level
# dead-code gate (``tests/architectural/test_no_dead_symbols.py``) is a shrink-only
# ratchet and does not count tests as callers. ``UNDETERMINED_PROJECT_REFUSAL`` stays
# importable and unadvertised (the idiom ``sync/consent.py`` uses for
# ``consent_index_health``) until a production reader for it lands.
__all__ = ["project_egress_refusal"]
