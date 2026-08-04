"""The single tracker-egress verdict: two consent channels, one named destination (#3108).

**One function decides whether tracker data may leave the machine.**
:func:`tracker_egress_verdict` composes two independently-recorded consent channels and a
caller-supplied :class:`EgressDestination` into one :class:`TrackerEgressVerdict`. Both the
gates that raise (WP04, WP05) and the diagnostic surface that reports (WP06 ``sync doctor``)
call this same function, so the enforced answer and the reported answer cannot disagree --
that is the whole point of the module existing.

**Channel 1** (existing, unchanged) -- hosted-sync consent, resolved by
``project_egress_refusal`` -> ``resolve_egress_consent`` -> ``permits_egress``
(``tracker/egress_consent.py``). Absence denies. This module holds the **Mission's only
module-level import** of ``project_egress_refusal`` -- see "Import-form rules" below.

**Channel 2** (new, #3108) -- the project's own committed ``tracker.egress`` key in
``.kittify/config.yaml``: ``absent`` / ``refused`` / ``permitted`` / ``fault``. Decoded by
:func:`_resolve_channel2` from :class:`~specify_cli.tracker.config.TrackerProjectConfig`.

Polarity follows the destination, and this is deliberate, not a simplification
-----------------------------------------------------------------------------

``EgressDestination.LOCAL_SUBPROCESS`` (``beads``/``fp``): Channel 2 is **two-way** --
``refused`` refuses, and ``permitted`` **grants independently of Channel 1**. The subprocess
named there is the operator's own machine-global credential file
(``tracker/factory.py:56``); spec-kitty's hosted service is never involved, so a grant there
gives nothing to spec-kitty.

``EgressDestination.HOSTED_SERVICE`` (``jira``/``linear``/``github``/``gitlab``): Channel 2 is
**narrowing only** -- it may refuse, it may never grant. Channel 1 stays a hard prerequisite,
because ``SaaSTrackerClient._request``'s ``_base_url`` resolves from
``resolve_runtime_target().resolved_server_url`` (``saas_client.py:247``) and every endpoint is
``/api/v1/tracker/...`` with a bearer token -- that path sends to **spec-kitty's own hosted
service**. A config-derived grant there would ship engagement names to spec-kitty's SaaS while
hosted-sync consent is absent, reopening #3030's P0 boundary through the very key introduced to
protect it.

**Neither guard that exists for this Mission (G4, G5 -- WP07) decides this polarity for a third
transport.** G5 checks that every call site's ``destination`` argument is a literal
``EgressDestination`` attribute, not a config-derived name; it **passes** when a new transport
simply reuses ``HOSTED_SERVICE``. G4 only asserts the exact call-site count and count of enclosing
functions; adding a transport makes it fire, but only as a *prompt* whose obvious fix is to edit
the guard's expected count -- it does not force anyone to reconsider polarity. So: **a third
transport must not silently inherit one of these two polarities.** Whoever adds one must make an
explicit operator decision about that member's Channel-2 polarity (FR-004) and say so in
:class:`EgressDestination`'s own docstring, the same way this module documents the existing two.
This requirement lives here and nowhere else -- it is preconditions §1.6(7) of the parent
Mission's implementation handoff, and no test in this codebase can raise it back into view once
this comment is deleted.

The polarity map must stay exhaustive over Channel 2's legal values -- and this is a two-site
change, not a type error
------------------------------------------------------------------------------------------------

``EGRESS_REFUSED`` / ``EGRESS_PERMITTED`` (imported from ``tracker/config.py``, never re-spelled
here) close *duplicate spelling*: this module and ``TrackerProjectConfig.egress_fault`` cannot
disagree about how a legal value is written. They do **not** close *arity*. If a **third** legal
value is ever added to ``tracker/config.py``'s ``_EGRESS_LEGAL_VALUES``, that is a two-site
change -- this module's own :data:`_LEGAL_CHANNEL2_VALUES` and :data:`_JOIN` must be updated too,
deliberately, in the same change. FR-002's raw-value mandate (Channel 2 carries the raw loaded
value, never a narrowed ``enum``) rules out an ``enum`` + exhaustiveness-checked-by-``mypy``
treatment here, so this cannot be made a type error; it can only be made to fail safely if
forgotten. It is: :func:`_resolve_channel2` classifies **any** string outside its own two known
values as :data:`CHANNEL2_FAULT` -- deliberately, not as an incidental fallthrough -- which
``_JOIN`` maps to :data:`OUTCOME_REFUSE` at both destinations. So a legal-elsewhere-but-unmapped-
here value refuses rather than silently falling through to a permissive branch, matching §1.3's
"any other value is a fault that refuses." Pinned by a test that adds a third value to
``tracker/config.py``'s ``_EGRESS_LEGAL_VALUES`` (so ``egress_fault`` there reports "not a
fault") without updating this module, and asserts this module still refuses.

``destination`` is a parameter, never a derivation
---------------------------------------------------

Measured: ``TrackerService._resolve_saas_backend_for_provider`` (``service.py:84-98``) overrides
the on-disk provider **in memory only** -- ``tracker list-tickets --provider jira`` reaches
``SaaSTrackerService`` even when the committed config says ``beads``, and the file is never
rewritten. A verdict function that read the provider off disk to pick a destination would see
``beads`` on that call and apply the local (two-way) polarity to a request that is actually going
to spec-kitty's hosted service -- turning ``tracker.egress: permitted`` into exactly the grant
the previous paragraph says must never happen. So ``destination`` is supplied by the caller,
**required and keyword-only**, and this function never reads ``TrackerProjectConfig.provider``
anywhere in its body (guard G6, WP07).

Import-form rules -- both load-bearing, both fail loudly rather than silently
------------------------------------------------------------------------------

- **``EgressDestination`` must be imported under its own name** (``from ... import
  EgressDestination``), never aliased (``import ... as ED``). Guard G5 resolves an
  ``ast.Attribute`` node whose value is the name ``EgressDestination``; an aliased import turns
  every call-site argument into an ``Attribute`` on the alias, and G5 reports it as non-literal --
  a **false red**, not a silent hole, but a lost afternoon for anyone not told in advance.
- **This module holds no import-time dependency on ``specify_cli.sync``.** The Channel-1
  reporting classifier (see below) reaches ``specify_cli.sync.consent`` and
  ``specify_cli.sync.routing`` by a **call-time guarded import**, degrading to generic Channel-1
  wording if the import fails. An ``ImportError`` raised out of a gate that NFR-003 says must
  never raise is exactly the failure mode this closes. A test asserts the module imports cleanly
  with ``specify_cli.sync`` made unimportable.

The Channel-1 reporting classifier is recorded debt -- read this before touching it
-------------------------------------------------------------------------------------

(a) **Cause.** The registry contract this module's Channel-1 answer is ultimately funneled
    through is ``_egress_consent_resolver: Callable[[Path], bool] | None`` at
    **``invocation/adapters.py:81``**. That contract manufactures an ``EgressConsent`` member
    from a bare ``bool``, so *why* a project is refused is discarded at the boundary and has to
    be re-derived alongside it if anyone wants to report it. :func:`_classify_channel1` is that
    re-derivation. It is not a design choice; it is the shape of a missing return type on a port
    this module does not own and must not widen (C-004).
(b) **Retirement condition.** When sibling Bundle B's open **Q3** gives that resolver contract a
    decision-carrying return value instead of a bare ``bool``, :func:`_classify_channel1` --
    **and both of its non-authoritativeness pins** (see its own docstring) -- are **delete**d,
    **not migrate**d. There will be nothing to migrate: the decision value Q3 adds replaces the
    re-derivation this classifier exists only to perform.
(c) **Unregistered-consumer note.** :func:`_classify_channel1` reaches around the registry
    indirection straight to ``specify_cli.sync.consent.resolve_project_consent`` and
    ``specify_cli.sync.routing.resolve_checkout_sync_routing_readonly``, by call-time guarded
    import, rather than going through the ``invocation/adapters.py`` seam. This is a recorded,
    accepted exception to that boundary -- named here so a future boundary audit finds a known
    exception instead of a surprise -- and it retires on the same condition as (b).

Why this module exists at all, in one line: Bundle B's implementer opens
``src/specify_cli/tracker/`` and ``src/specify_cli/egress/``, not
``kitty-specs/tracker-egress-refusal-3108-01KYWF1R/``. Every fact above that only lived in the
dossier would be invisible to them.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from specify_cli.tracker.config import (
    EGRESS_ABSENT,
    EGRESS_PERMITTED,
    EGRESS_REFUSED,
    TrackerConfigError,
    load_tracker_config,
)

# This module holds the Mission's only module-level import of ``project_egress_refusal``
# (#3108 handoff §4.2). Bundle B HAS landed: the function moved to ``specify_cli.egress`` and
# ``specify_cli/tracker/egress_consent.py`` no longer exists. The handoff predicted this import
# would be the only line needing a change; that was almost right. Bundle B also made
# ``identifiers`` a REQUIRED second parameter -- deliberately not defaulted, so a transport that
# did not declare what it can put on the wire cannot render a refusal naming nothing -- so
# :func:`tracker_egress_verdict` now threads it through to Channel 1 as well.
from specify_cli.egress import (
    UNDETERMINED_PROJECT_REFUSAL,
    project_egress_refusal,
)

#: Empty until WP04/WP05 wire a call site: the symbol-level dead-code gate
#: (``tests/architectural/test_no_dead_symbols.py``) treats every name advertised here as
#: requiring a real ``src/`` consumer, and this WP creates **zero** call sites by design
#: (T015 step 6). Review round 1, MEDIUM-1: an earlier revision advertised
#: ``EgressDestination``/``TrackerEgressVerdict``/``tracker_egress_verdict`` here and turned
#: that gate red -- it is shrink-only, so it was already green at base and stays green only if
#: this list stays empty until a real caller lands. This WP's own test file imports these names
#: directly (never via ``from ... import *``), so an empty ``__all__`` breaks nothing here.
__all__: list[str] = []


class EgressDestination(enum.Enum):
    """The closed, caller-supplied set of transports a tracker-egress verdict is asked about.

    ``tracker_egress_verdict`` never derives this value -- it is a required, keyword-only
    parameter at every call site (C-002). Adding a member, or repointing an existing member at a
    new transport, **requires an explicit operator decision about that member's Channel-2
    polarity** (FR-004) -- neither guard G4 nor G5 (WP07) decides this for you: G5 passes when a
    new transport simply reuses ``HOSTED_SERVICE`` (the argument is still a literal ``Attribute``
    on this enum), and G4 fires only as a count-changed prompt whose obvious fix is to edit the
    guard's expected numbers, not to reconsider polarity. See the module docstring's "polarity
    follows the destination" section for the reasoning this decision must repeat.
    """

    #: An executable named by the operator's own **machine-global** tracker credential file
    #: (``tracker/factory.py:56`` -- the ``command`` key, defaulting to ``bd``/``fp``), invoked
    #: with issue fields (title, body, labels, assignees) as ``argv``. spec-kitty's hosted
    #: service is not involved anywhere on this path.
    LOCAL_SUBPROCESS = "local_subprocess"

    #: spec-kitty's own ``/api/v1/tracker/...`` endpoints -- bearer token plus ``X-Team-Slug``,
    #: base URL from ``resolve_runtime_target().resolved_server_url``
    #: (``tracker/saas_client.py:247``). This is spec-kitty's hosted service, relaying to the
    #: Jira/Linear connector it holds.
    HOSTED_SERVICE = "hosted_service"


#: Channel identifiers used in :attr:`TrackerEgressVerdict.refusing_channels`. Never just the
#: first refusing channel is named (FR-005) -- when both refuse, both appear here.
CHANNEL_1: Final = "channel_1"
CHANNEL_2: Final = "channel_2"

#: Channel-2's four-value state vocabulary (FR-005). Spelled exactly this way -- not
#: ``refuse``/``grant`` -- because these are also :data:`_JOIN`'s first key element, looked up
#: directly against :attr:`TrackerEgressVerdict.channel2_state`. ``EGRESS_REFUSED`` and
#: ``EGRESS_PERMITTED`` are imported from ``tracker/config.py``, never re-spelled: that module
#: exports them as the single canonical spelling precisely so a second spelling here cannot
#: drift from ``egress_fault``'s idea of what is legal.
CHANNEL2_ABSENT: Final = "absent"
CHANNEL2_FAULT: Final = "fault"

#: The legal Channel-2 values, built from the imported constants -- never a re-spelled literal.
_LEGAL_CHANNEL2_VALUES: Final[frozenset[str]] = frozenset({EGRESS_REFUSED, EGRESS_PERMITTED})

class _UnreadableConfigType:
    """Sentinel for "the project's tracker config could not be read at all" (unreadable file,
    unreadable enclosing directory, unparseable YAML) -- distinct from a present ``null``
    (which decodes to ``None``, a legitimate fault *value* to quote verbatim) and distinct from
    :data:`~specify_cli.tracker.config.EGRESS_ABSENT` (the key was simply missing from a config
    that *was* readable).

    Reachable from :attr:`TrackerEgressVerdict.channel2_raw` -- a WP06 ``sync doctor`` row or a
    log line may render it. Review round 1, LOW-5: an earlier revision's comment here claimed
    this sentinel was "never exported", which was false the moment it was stored on the public
    verdict object's ``channel2_raw`` field. Given a proper ``__repr__`` for exactly that
    reason, rather than the illegible default ``<object object at 0x...>`` a bare ``object()``
    would print if ever rendered.
    """

    def __repr__(self) -> str:
        return "<tracker config unreadable>"


#: The single instance of :class:`_UnreadableConfigType`.
_UNREADABLE: Final = _UnreadableConfigType()

#: The four named outcomes :data:`_JOIN` maps Channel-2 states + destinations to (FR-005). Four,
#: not two: ``permitted`` at ``HOSTED_SERVICE`` enforces exactly like ``absent`` (Channel 1
#: decides) but must be **reported** differently -- a recorded grant that does not apply here is
#: not the same fact as no grant being recorded at all (SC-014's checkout 6 needs to tell them
#: apart).
OUTCOME_REFUSE: Final = "refuse"
OUTCOME_PERMIT: Final = "permit"
OUTCOME_DEFER: Final = "defer"
OUTCOME_DEFER_REPORTED_NOOP: Final = "defer_reported_noop"

#: The total, enumerated 8-cell join (FR-005) -- **data, not a branch chain**, so the join
#: contributes zero cyclomatic complexity. ``len(_JOIN) == 8`` is a structural pin: it survives a
#: test being deleted, the way a parametrised behavioural test survives an entry being wrong.
#: Both are required (SC-015).
_JOIN: Final[dict[tuple[str, EgressDestination], str]] = {
    (CHANNEL2_FAULT, EgressDestination.LOCAL_SUBPROCESS): OUTCOME_REFUSE,
    (CHANNEL2_FAULT, EgressDestination.HOSTED_SERVICE): OUTCOME_REFUSE,
    (EGRESS_REFUSED, EgressDestination.LOCAL_SUBPROCESS): OUTCOME_REFUSE,
    (EGRESS_REFUSED, EgressDestination.HOSTED_SERVICE): OUTCOME_REFUSE,
    (EGRESS_PERMITTED, EgressDestination.LOCAL_SUBPROCESS): OUTCOME_PERMIT,
    (EGRESS_PERMITTED, EgressDestination.HOSTED_SERVICE): OUTCOME_DEFER_REPORTED_NOOP,
    (CHANNEL2_ABSENT, EgressDestination.LOCAL_SUBPROCESS): OUTCOME_DEFER,
    (CHANNEL2_ABSENT, EgressDestination.HOSTED_SERVICE): OUTCOME_DEFER,
}

#: The Channel-1 *reporting* triple (FR-012) -- never to be confused with Channel 2's *value*
#: vocabulary just above. These describe why the one true derivation
#: (``project_egress_refusal`` -> ``resolve_egress_consent`` -> ``permits_egress``) refused;
#: they never decide it. Returned **only** by :func:`_classify_channel1`, which is itself
#: invoked **only** when Channel 1 refuses (see :func:`_channel1_report`) -- review round 1,
#: HIGH-2: an earlier revision invoked the classifier unconditionally and reported
#: ``recorded_refusal`` for a project whose Channel 1 had, in fact, granted.
CHANNEL1_NO_RECORD: Final = "no_record"
CHANNEL1_RECORDED_REFUSAL: Final = "recorded_refusal"
CHANNEL1_NOT_CONSENTABLE: Final = "not_consentable"

#: Channel 1 actually **permits**. Set directly by :func:`_channel1_report` whenever
#: ``channel1_permits`` is ``True``, without ever asking :func:`_classify_channel1` -- none of
#: that function's three labels describe a grant, and asking it anyway is what produced HIGH-2.
CHANNEL1_GRANTED: Final = "granted"

#: Channel 1 refuses, but :func:`_classify_channel1` itself raised while determining which of
#: the three reasons applies. Deliberately **distinct** from :data:`CHANNEL1_NO_RECORD`: a
#: raised classification asserts nothing about *why* Channel 1 refused, and reporting one
#: specific (and possibly wrong) reason would be a confident-sounding lie -- review round 1,
#: LOW-4, the same class of defect as HIGH-2 applied to the classifier's own failure path.
CHANNEL1_UNCLASSIFIED: Final = "unclassified"

#: A sixth Channel-1 state, reachable **only** when ``root is None`` -- there is no checkout to
#: classify, so none of the labels above (which all describe *some* project's recorded state or
#: its absence) apply. Set directly, without calling :func:`_classify_channel1` or
#: :func:`_channel1_report` at all.
CHANNEL1_UNDETERMINED: Final = "undetermined"


@dataclass(frozen=True, slots=True)
class TrackerEgressVerdict:
    """The one value object both the enforcing gates and ``sync doctor`` read (FR-003).

    No ``binding_kind`` field, and no binding-kind derivation anywhere in this module: the
    caller states :attr:`destination`; the verdict never reads
    :class:`~specify_cli.tracker.config.TrackerProjectConfig.provider` to guess it.
    """

    #: The enforced answer, for the destination asked about. Never derived a second way anywhere
    #: else -- every raise site (WP04, WP05) and every ``sync doctor`` row (WP06) reads this
    #: field and nothing else to decide whether to refuse.
    refused: bool

    #: Which channel(s) refuse -- **never just the first**. Populated only when it actually
    #: refuses; empty when the verdict permits, even if one channel's answer alone would have
    #: refused (Channel 2's grant overriding Channel 1 at ``LOCAL_SUBPROCESS`` is the case this
    #: guards).
    refusing_channels: frozenset[str]

    #: Echoed back so a renderer cannot mislabel a row and a test can assert the enforced and
    #: reported verdicts were asked about the same destination.
    destination: EgressDestination

    #: One of :data:`CHANNEL1_GRANTED` (Channel 1 permits -- the classifier is never asked),
    #: :data:`CHANNEL1_NO_RECORD`, :data:`CHANNEL1_RECORDED_REFUSAL`,
    #: :data:`CHANNEL1_NOT_CONSENTABLE` (the classifier's own closed set of three, reachable
    #: only when Channel 1 refuses), :data:`CHANNEL1_UNCLASSIFIED` (Channel 1 refuses but the
    #: classifier itself raised), or :data:`CHANNEL1_UNDETERMINED` (``root is None`` only).
    #: Reporting-only and **not authoritative** -- see :func:`_classify_channel1` and
    #: :func:`_channel1_report`.
    channel1_state: str

    #: One of :data:`CHANNEL2_ABSENT`, ``EGRESS_REFUSED`` (``"refused"``), ``EGRESS_PERMITTED``
    #: (``"permitted"``), or :data:`CHANNEL2_FAULT`.
    channel2_state: str

    #: The raw value read from the project's own ``tracker.egress`` key -- verbatim, for a fault
    #: message to quote (C-020). :data:`~specify_cli.tracker.config.EGRESS_ABSENT` when the key
    #: was missing.
    channel2_raw: object

    #: The single composed operator-facing message. No raise site composes its own text (T019) --
    #: every one uses this field unchanged.
    message: str

    #: Ordered remedies. Empty when the verdict permits. **Raise sites must render these
    #: alongside `message`, never `message` alone** (review round 1, MEDIUM-3): at
    #: ``LOCAL_SUBPROCESS`` the Channel-2 grant remedy lives only here, not folded into
    #: `message`, because FR-012 places it as a remedy at that destination and as an
    #: in-message note (not a remedy) at ``HOSTED_SERVICE``. WP01's acceptance harness asserts
    #: on the combined rendered output of a CLI raise site, not on `message` in isolation.
    remedies: tuple[str, ...]


def _resolve_channel2(root: Path) -> tuple[str, object]:
    """Decode Channel 2 from *root*'s committed tracker config. Reads the file exactly once.

    Never raises (NFR-003): an unreadable or unparseable ``.kittify/config.yaml`` is itself a
    fault, not a crash. The ``isinstance`` guard runs before the membership test -- a bare
    ``raw in _LEGAL_CHANNEL2_VALUES`` raises ``TypeError: unhashable type`` for a mapping or a
    list at the key, both of which are members of this Mission's fault set, not of its crash set.

    Catches ``OSError`` alongside ``TrackerConfigError`` (review round 1, HIGH-1): the pre-check
    ahead of ``load_tracker_config``'s own guarded open/parse block --
    ``if not config_path.exists(): ...`` (``config.py``) -- calls ``Path.exists()``, which
    re-raises rather than swallows a ``PermissionError`` (``EACCES`` is not in pathlib's
    ``_ignore_error`` set). An unreadable *enclosing directory* (e.g. ``.kittify`` itself
    ``chmod 000``) therefore raises a bare ``PermissionError`` -- an ``OSError`` subclass, never
    a ``TrackerConfigError`` -- straight out of ``load_tracker_config``, before this function's
    own guarded block ever gets a chance to translate it. Catching only ``TrackerConfigError``
    left that one path able to propagate out of a function NFR-003 says must never raise.
    """
    try:
        config = load_tracker_config(root)
    except (TrackerConfigError, OSError):
        return CHANNEL2_FAULT, _UNREADABLE

    raw = config.egress
    if raw is EGRESS_ABSENT:
        return CHANNEL2_ABSENT, raw
    if isinstance(raw, str) and raw in _LEGAL_CHANNEL2_VALUES:
        return raw, raw
    # Deliberate, not an incidental fallthrough: this also covers a string that
    # ``tracker/config.py`` might one day add to its own ``_EGRESS_LEGAL_VALUES`` without this
    # module being updated to match (see the module docstring's "two-site change" section) --
    # ``_LEGAL_CHANNEL2_VALUES`` above is built from only the two names this module imports, so
    # an unmapped-here value refuses rather than silently falling through to a permit.
    return CHANNEL2_FAULT, raw


def _resolve_channel1(root: Path, identifiers: str) -> tuple[bool, str | None]:
    """The one true Channel-1 derivation (C-004): ``None`` -- and only ``None`` -- permits.

    Delegates entirely to :func:`~specify_cli.tracker.egress_consent.project_egress_refusal`,
    which itself performs the guarded ``specify_cli.sync`` import and never raises.
    """
    refusal = project_egress_refusal(root, identifiers)
    return refusal is None, refusal


def _classify_channel1(root: Path) -> str:
    """Reporting-only classifier over Channel 1's already-decided *refusal*. Recorded debt.

    Returns exactly one of :data:`CHANNEL1_NO_RECORD`, :data:`CHANNEL1_RECORDED_REFUSAL`, or
    :data:`CHANNEL1_NOT_CONSENTABLE` -- a closed set of three, and nothing else. It **never
    changes the enforced answer**, and it is invoked **only when Channel 1 refuses**:
    :func:`_channel1_report` checks ``channel1_permits`` first and never calls this function
    when that is ``True`` (review round 1, HIGH-2 -- an earlier revision called this function
    unconditionally and reported ``recorded_refusal`` for a project whose Channel 1 had, in
    fact, granted, because "any non-``ABSENT`` level answered" is not the same claim as "that
    level's answer was a refusal").

    It is pinned non-authoritative by two tests: one that proves this function is never even
    reached when Channel 1 permits (:data:`CHANNEL1_GRANTED` is assigned directly instead, so a
    forced wrong label from this function cannot leak into a permitting verdict), and one that
    makes this function itself raise while Channel 1 refuses (asserting the caller still
    produces a refusal with generic wording and the distinct :data:`CHANNEL1_UNCLASSIFIED`
    state -- never :data:`CHANNEL1_NO_RECORD`, which would assert a specific, unverified reason
    -- and never a propagated exception).

    Why this function exists, and why it is debt rather than a design element: the registry
    contract it ultimately reports on, ``_egress_consent_resolver: Callable[[Path], bool] | None``
    at ``invocation/adapters.py:81``, manufactures an ``EgressConsent`` member from a bare
    ``bool`` and therefore discards *why* a project is refused. This function is that
    information's re-derivation, reached by a call-time guarded import straight into
    ``specify_cli.sync.consent`` / ``specify_cli.sync.routing`` -- an unregistered, recorded
    exception to the usual registry indirection, retiring on the same condition named next.

    Retirement condition: when sibling Bundle B's open Q3 gives that resolver contract a
    decision-carrying return value instead of a bare bool, this function -- and both of its
    non-authoritativeness pins -- are deleted, not migrated. There will be nothing left to
    migrate onto.
    """
    try:
        from specify_cli.sync.consent import ConsentLevel, resolve_project_consent  # noqa: PLC0415
        from specify_cli.sync.routing import resolve_checkout_sync_routing_readonly  # noqa: PLC0415
    except Exception:  # noqa: BLE001 - NFR-003: degrade, never raise out of this gate
        return CHANNEL1_NO_RECORD

    routing = resolve_checkout_sync_routing_readonly(root)
    if routing is None or not routing.project_uuid:
        return CHANNEL1_NOT_CONSENTABLE

    decision = resolve_project_consent(routing.project_uuid, checkout_roots=[routing.repo_root])
    if decision.level is ConsentLevel.ABSENT:
        return CHANNEL1_NO_RECORD
    return CHANNEL1_RECORDED_REFUSAL


def _channel1_report(root: Path, *, channel1_permits: bool) -> tuple[str, bool]:
    """Compute :attr:`TrackerEgressVerdict.channel1_state`. Never raises, never authoritative.

    Branches on the enforced answer ``channel1_permits`` **before** ever asking
    :func:`_classify_channel1` (review round 1, HIGH-2): that function's own precondition
    restricts it to a path whose refusal is already decided, so a permitting Channel 1 gets
    :data:`CHANNEL1_GRANTED` directly -- never one of the three refusal-flavoured labels the
    classifier can return, and never by calling it at all. Callers on the permitting path
    cannot leak a wrong classifier answer they never asked for.

    Returns ``(state, generic)``. ``generic`` is ``True`` only when the classifier itself
    raised while Channel 1 refuses (second non-authoritativeness pin) -- in which case *state*
    is :data:`CHANNEL1_UNCLASSIFIED`, deliberately distinct from :data:`CHANNEL1_NO_RECORD`
    (review round 1, LOW-4): a raised classification is evidence of nothing, not evidence of
    "no record", and the caller must use generic message wording rather than the
    label-specific description in either case.
    """
    if channel1_permits:
        return CHANNEL1_GRANTED, False
    try:
        return _classify_channel1(root), False
    except Exception:  # noqa: BLE001 - NFR-003 + non-authoritativeness: never raise, never assert a specific label
        return CHANNEL1_UNCLASSIFIED, True


#: Literal channel-name prefixes. Every composed message names which channel it is talking
#: about by one of these two exact tokens -- WP04/WP05's acceptance harness asserts on them
#: directly, so they are named constants rather than prose that happens to read the same way.
_CHANNEL1_LABEL: Final = "Channel 1"
_CHANNEL2_LABEL: Final = "Channel 2"

_CHANNEL1_DESCRIPTIONS: Final[dict[str, str]] = {
    CHANNEL1_NO_RECORD: "no record of hosted-sync consent exists for this project",
    CHANNEL1_RECORDED_REFUSAL: "hosted-sync consent for this project is recorded as refused",
    CHANNEL1_NOT_CONSENTABLE: (
        "this project's identity has not been established, so hosted-sync consent cannot be recorded"
    ),
}

_CHANNEL1_REMEDIES: Final[dict[str, tuple[str, ...]]] = {
    CHANNEL1_NO_RECORD: (
        "record `sync.enabled: true` in this project's own .kittify/config.yaml",
        "or run `spec-kitty sync opt-in`",
    ),
    CHANNEL1_RECORDED_REFUSAL: (
        "change the recorded `sync.enabled` decision in this project's own .kittify/config.yaml",
    ),
    CHANNEL1_NOT_CONSENTABLE: (
        "run `spec-kitty init` in this checkout to mint a project identity, "
        "then record `sync.enabled: true` or run `spec-kitty sync opt-in`",
    ),
}

#: Destination-specific note on the Channel-2 grant, attached to every Channel-1-decided message
#: (FR-012): at ``LOCAL_SUBPROCESS`` it is offered as a remedy; at ``HOSTED_SERVICE`` the operator
#: is told plainly that it does not apply there, so a `tracker.egress: permitted` project is
#: never left believing its local grant did nothing.
_LOCAL_GRANT_REMEDY: Final = "or record `tracker.egress: permitted` in this project's own .kittify/config.yaml"

#: Two distinct hosted-service notes (review round 1, MEDIUM-2): an earlier revision showed the
#: "recorded" wording unconditionally, so a project with *no* tracker key at all was told about
#: "a recorded `tracker.egress: permitted`" it did not have, and a project that genuinely
#: recorded one got no distinguishing signal that *its* key specifically is the thing being
#: no-op'd. Selected by ``noop`` (``True`` only for the ``permitted``-at-``HOSTED_SERVICE``
#: cell, where a grant is actually on disk) in :func:`_channel1_decided_message`.
_HOSTED_GRANT_NOTE_RECORDED: Final = (
    "note: the recorded `tracker.egress: 'permitted'` does not apply to the hosted service -- "
    "it is a no-op here; only hosted-sync consent grants hosted-service egress"
)
#: There is deliberately no *prospective* counterpart to the note above. An earlier draft
#: appended one ("a grant would not apply...") to the Channel-2-absent hosted cell; FR-016
#: requires that cell to reproduce `#3030`'s shipped text byte for byte, so it now carries no
#: note at all -- it has nothing truthful to say about a key the operator has not recorded.
#: See ``decisions/DM-FR016-hosted-byte-identity.md``.


def _fault_message(destination: EgressDestination, raw: object) -> str:
    """Compose the Channel-2 fault message (C-020): names the offending value verbatim,

    names both legal values by their exact on-disk spelling, so an operator fixes a typo
    without reading source.
    """
    offending = "the project's tracker configuration could not be read" if raw is _UNREADABLE else repr(raw)
    return (
        f"tracker.egress is set to {offending}, which is not a legal value; refusing tracker "
        f"egress to {destination.value} (legal values are {EGRESS_REFUSED!r} and {EGRESS_PERMITTED!r})"
    )


def _refused_message(destination: EgressDestination) -> str:
    """Compose the plain Channel-2 ``refused`` message."""
    return (
        f"tracker.egress is recorded as {EGRESS_REFUSED!r} in this project's own "
        f".kittify/config.yaml; refusing tracker egress to {destination.value}"
    )


def _permit_message(destination: EgressDestination) -> str:
    """Compose the Channel-2 grant message (``LOCAL_SUBPROCESS`` + ``permitted`` only)."""
    return (
        f"tracker egress to {destination.value} is permitted by tracker.egress: "
        f"{EGRESS_PERMITTED!r}, recorded in this project's own .kittify/config.yaml, "
        "independently of hosted-sync consent"
    )


def _channel1_decided_message(
    *,
    destination: EgressDestination,
    channel1_permits: bool,
    channel1_label: str,
    channel1_generic: bool,
    noop: bool,
    channel1_refusal_text: str | None = None,
) -> tuple[str, tuple[str, ...]]:
    """Compose the message and remedies for a cell where Channel 1 decides the answer.

    ``noop`` is ``True`` only for the ``permitted``-at-``HOSTED_SERVICE`` cell -- the only one
    where a Channel-2 grant is actually recorded on disk.

    **FR-016 byte-identity at ``HOSTED_SERVICE`` (WP05 finding).** That path was already gated
    by `#3030`, and FR-016 requires its refusal text stay *byte-identical* to the shipped
    wording for the three measured outcomes -- absence, recorded ``false``, recorded ``true``
    -- all of which are Channel-2-**absent** cases: *"A Mission that closes the local gap while
    perturbing the shipped hosted gate has traded one leak for another."* So when Channel 1
    decides at ``HOSTED_SERVICE`` and Channel 2 is absent, ``project_egress_refusal``'s own
    string is returned **verbatim**, never recomposed. WP05 measured the recomposition and
    reported the divergence rather than accepting it.

    That also resolves review round 1's MEDIUM-2 more cleanly than the prospective note did.
    The original defect was the absent and recorded cases being byte-identical *and* the absent
    one asserting a recorded grant the operator does not have. Passing the raw text through
    fixes both at once: the absent case now carries no hosted note at all (it has nothing to
    say about a key that is not there), and only a genuinely recorded grant gets
    ``_HOSTED_GRANT_NOTE_RECORDED``. The two remain plainly distinct, and neither asserts a
    fact about the file that is untrue -- which is what MEDIUM-2 actually asked for.

    ``LOCAL_SUBPROCESS`` keeps the composed wording: it is a new gate with no shipped text to
    preserve, and WP01's harness pins its state tokens (``no record`` / ``refus`` / ``identity``)
    literally.
    """
    if channel1_permits:
        message = f"{_CHANNEL1_LABEL} permits: hosted-sync consent is granted for this project"
        if noop and destination is EgressDestination.HOSTED_SERVICE:
            message = f"{message}; {_HOSTED_GRANT_NOTE_RECORDED}"
        return message, ()

    if channel1_generic:
        detail = "hosted-sync consent for this project could not be determined in detail"
        remedies: tuple[str, ...] = ()
    else:
        detail = _CHANNEL1_DESCRIPTIONS[channel1_label]
        remedies = _CHANNEL1_REMEDIES[channel1_label]

    if destination is EgressDestination.LOCAL_SUBPROCESS:
        remedies = (*remedies, _LOCAL_GRANT_REMEDY)
        message = f"{_CHANNEL1_LABEL} refused: {detail}; refusing tracker egress to {destination.value}"
    elif noop:
        # A grant is genuinely recorded and is a no-op here. Not one of FR-016's three measured
        # outcomes (all Channel-2-absent), so the note may be attached: saying nothing would
        # leave the operator believing their key did something, which is FR-005's named failure.
        message = (
            f"{_CHANNEL1_LABEL} refused: {detail}; refusing tracker egress to {destination.value}. "
            f"{_HOSTED_GRANT_NOTE_RECORDED}"
        )
    elif channel1_refusal_text is not None:
        # FR-016: the shipped hosted refusal, byte-identical. No recomposition, no note.
        message = channel1_refusal_text
    else:  # pragma: no cover - Channel 1 refuses, so its text is never None here
        message = f"{_CHANNEL1_LABEL} refused: {detail}; refusing tracker egress to {destination.value}"
    return message, remedies


def _channel2_decided_message(
    *,
    destination: EgressDestination,
    channel2_state: str,
    channel2_raw: object,
    channel1_permits: bool,
    channel1_refusal_text: str | None,
) -> str:
    """Compose the message for a cell where Channel 2 alone refuses (fault or ``refused``)."""
    base = _fault_message(destination, channel2_raw) if channel2_state == CHANNEL2_FAULT else _refused_message(destination)
    message = f"{_CHANNEL2_LABEL} refused: {base}"
    if not channel1_permits and channel1_refusal_text is not None:
        message = (
            f"{message}; additionally, {_CHANNEL1_LABEL} also refuses (hosted-sync consent): "
            f"{channel1_refusal_text}"
        )
    return message


def _refusing_channels(
    *, channel2_refuses: bool, channel1_permits: bool, overall_refused: bool
) -> frozenset[str]:
    """Which channel(s) refuse, populated only when the overall verdict actually refuses."""
    if not overall_refused:
        return frozenset()
    channels = set()
    if channel2_refuses:
        channels.add(CHANNEL_2)
    if not channel1_permits:
        channels.add(CHANNEL_1)
    return frozenset(channels)


def tracker_egress_verdict(
    root: Path | None, *, destination: EgressDestination, identifiers: str
) -> TrackerEgressVerdict:
    """The one function both the enforcing gates and ``sync doctor`` call (FR-003). Never raises.

    ``destination`` is required and keyword-only -- there is no default, so no call site can
    inherit a polarity silently (C-002). Both channels are always evaluated (FR-005): this never
    short-circuits on Channel 1, because Channel 2's grant at ``LOCAL_SUBPROCESS`` must be able
    to satisfy the path even when Channel 1 alone would deny.

    ``root=None`` is a named exception, specified in full because it is reachable at **both**
    destinations (not only from the hosted client): there is no checkout to read a Channel-2 key
    out of, so this returns text byte-identical to
    :data:`~specify_cli.tracker.egress_consent.UNDETERMINED_PROJECT_REFUSAL` with no remedies,
    without consulting Channel 2 or the Channel-1 classifier at all.

    **Consumption coupling for raise sites (review round 1, MEDIUM-3):** a raise site must
    render :attr:`TrackerEgressVerdict.message` **and** :attr:`TrackerEgressVerdict.remedies`
    together -- never ``message`` alone. At ``LOCAL_SUBPROCESS`` the Channel-2 grant lives only
    in ``remedies`` (FR-012 places it as a remedy there, never folded into the message text).
    WP01's acceptance harness asserts on a CLI raise site's combined rendered output, and its
    ``LOCAL_SUBPROCESS`` assertions pass only when both fields are rendered. Do not "fix" this
    by duplicating the remedy into ``message`` --
    FR-012's placement is correct as specified.

    **FR-016 carve-out at ``HOSTED_SERVICE`` (WP05 review, MEDIUM-1).** That path is the one
    exception, and it is deliberate. FR-016 requires its Channel-1 refusal to reproduce
    `#3030`'s shipped string byte for byte, so nothing may be appended -- not a note, not a
    remedy. ``saas_client._request`` therefore raises with ``message`` alone and the
    ``remedies`` this function computes are **not shown** there:

    ==================  =========  ==========
    ``channel1_state``  carried    rendered
    ==================  =========  ==========
    no_record           2          0
    recorded_refusal    1          0
    not_consentable     1          0
    ==================  =========  ==========

    The dropped ``not_consentable`` remedy is the load-bearing one -- it tells an identity-less
    checkout to run ``spec-kitty init`` first, where the shipped text sends the operator to
    ``spec-kitty sync opt-in``, which FR-012 records as *not working* for that state. This is a
    spec-mandated trade, not an oversight: FR-016 forbids folding it into the message, and
    shipped behaviour is unchanged (the operator sees exactly what `#3030` showed them). The
    remedies resurface in ``sync doctor``'s renderer (FR-014, WP06), which reads the same
    verdict and is not bound by FR-016's byte-identity. See
    ``decisions/DM-FR016-hosted-byte-identity.md``.
    """
    if root is None:
        return TrackerEgressVerdict(
            refused=True,
            refusing_channels=frozenset({CHANNEL_1}),
            destination=destination,
            channel1_state=CHANNEL1_UNDETERMINED,
            channel2_state=CHANNEL2_ABSENT,
            channel2_raw=EGRESS_ABSENT,
            message=UNDETERMINED_PROJECT_REFUSAL,
            remedies=(),
        )

    channel2_state, channel2_raw = _resolve_channel2(root)
    channel1_permits, channel1_refusal_text = _resolve_channel1(root, identifiers)
    channel1_label, channel1_generic = _channel1_report(root, channel1_permits=channel1_permits)
    outcome = _JOIN[(channel2_state, destination)]

    if outcome == OUTCOME_PERMIT:
        return TrackerEgressVerdict(
            refused=False,
            refusing_channels=frozenset(),
            destination=destination,
            channel1_state=channel1_label,
            channel2_state=channel2_state,
            channel2_raw=channel2_raw,
            message=_permit_message(destination),
            remedies=(),
        )

    if outcome == OUTCOME_REFUSE:
        message = _channel2_decided_message(
            destination=destination,
            channel2_state=channel2_state,
            channel2_raw=channel2_raw,
            channel1_permits=channel1_permits,
            channel1_refusal_text=channel1_refusal_text,
        )
        return TrackerEgressVerdict(
            refused=True,
            refusing_channels=_refusing_channels(
                channel2_refuses=True, channel1_permits=channel1_permits, overall_refused=True
            ),
            destination=destination,
            channel1_state=channel1_label,
            channel2_state=channel2_state,
            channel2_raw=channel2_raw,
            message=message,
            remedies=(),
        )

    # OUTCOME_DEFER / OUTCOME_DEFER_REPORTED_NOOP: Channel 1 decides.
    noop = outcome == OUTCOME_DEFER_REPORTED_NOOP
    refused = not channel1_permits
    message, remedies = _channel1_decided_message(
        destination=destination,
        channel1_permits=channel1_permits,
        channel1_label=channel1_label,
        channel1_generic=channel1_generic,
        noop=noop,
        channel1_refusal_text=channel1_refusal_text,
    )
    return TrackerEgressVerdict(
        refused=refused,
        refusing_channels=_refusing_channels(
            channel2_refuses=False, channel1_permits=channel1_permits, overall_refused=refused
        ),
        destination=destination,
        channel1_state=channel1_label,
        channel2_state=channel2_state,
        channel2_raw=channel2_raw,
        message=message,
        remedies=remedies,
    )
