"""Per-project hosted-sync consent: the one resolver (#3030 WP05, FR-013/FR-019).

Consent used to be answerable only per *checkout*, keyed by absolute path in
machine-global config, while events carry a ``project_uuid``. That missing join is
what let a drain authorize at one scope and deliver at another. This module
supplies the join and is the **single** place the precedence chain is expressed.

Precedence — see spec.md "FR-013 × FR-019 reconciliation":

1. :attr:`ConsentLevel.PROJECT_LOCAL` — the project's own ``.kittify/config.yaml``,
   authoritative whenever readable. Version-controlled and reviewable in the repo
   it governs. A **refusal outranks a grant**: two checkouts can share a
   ``project_uuid`` through a committed file and disagree, and FR-013's rule is
   deny if any checkout of the project is opted out.
2. :attr:`ConsentLevel.MACHINE_INDEX` — the uuid-keyed machine-global index. This
   must exist: the dispatcher resolves consent for events carrying only a
   ``project_uuid``, and must still answer when the checkout has moved, been
   renamed or deleted. It is a **cache**, not a second source of truth — when a
   readable checkout disagrees, the file wins and the index is corrected.
3. :attr:`ConsentLevel.ENV` — ``SPEC_KITTY_ENABLE_SAAS_SYNC`` is machine-global
   *arming*, never per-project consent, and therefore **never a grant on its own**.
   The 2026-07-27 incident is exactly this: the var was exported and five
   projects with no record rode along on it.
4. Nothing recorded anywhere → **deny** (FR-002). Absence of a decision is not
   consent; the five leaked projects had no record at all.

Why one definition site: three consumers must agree — the drain's predicate, the
consent writers, and FR-015's report. A second copy is how the reported state and
the enforced state come to disagree, which is the same failure mode T011's identity
chain guards against.
"""
from __future__ import annotations

import enum
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from .config import ConfigReadFault

logger = logging.getLogger(__name__)

#: Key for project-local consent inside ``.kittify/config.yaml``: ``sync.enabled``.
#:
#: Canonicalised on ``enabled`` (2026-07-30). Three spellings of one invariant had
#: accumulated — ``sync.enabled`` (written by the acceptance pin, read by nothing),
#: ``sync.hosted`` (read here, written by nothing) and ``sync.auto_start`` — which is
#: exactly the "two representations of one invariant" C-003 forbids. ``enabled`` wins
#: because it is the spelling the acceptance pin and an operator would both reach for.
#:
#: ``sync.auto_start`` (``sync/runtime.py``) is deliberately NOT unified into this:
#: it answers "should the daemon start itself?", a runtime convenience, not "may this
#: project's data leave the machine?". Conflating them would let a daemon-autostart
#: preference grant hosted-sync consent.
PROJECT_CONFIG_SYNC_SECTION = "sync"
PROJECT_CONFIG_ENABLED_KEY = "enabled"

#: Marker retained on a path-keyed record whose checkout could not be resolved to
#: a uuid. The predicate ignores these; FR-015 renders them so reported state and
#: enforced state agree (US2 scenario 3).
UNRESOLVED_MARKER = "unresolved"


class ConsentLevel(enum.StrEnum):
    """Which level of the chain answered. Rendered by FR-015's report.

    Two members are *outcomes* rather than levels — :attr:`ABSENT` and
    :attr:`UNDETERMINED`. Neither appears in :data:`PROJECT_CONSENT_PRECEDENCE` or
    :data:`LEVEL_RESOLVERS`, so neither participates in dispatch; both are terminal
    answers the walk produces. Naming them here rather than as a separate flag on
    :class:`ConsentDecision` keeps "how was this answered" in one field instead of two
    that can disagree.
    """

    PROJECT_LOCAL = "project_local"
    MACHINE_INDEX = "machine_index"
    ENV = "env"
    ABSENT = "absent"
    #: Consent could not be determined because a consent record could not be *read*
    #: (#3030 FR-020) — distinct from :attr:`ABSENT`, which means nothing was
    #: recorded. It denies exactly as ABSENT does; what it changes is the report.
    #: An operator told "no consent record" for a project they opted in will go and
    #: opt it in again; one told "your consent index is unreadable" will fix the file.
    UNDETERMINED = "undetermined"


#: The chain, highest authority first. Declared once; never re-derived.
#: ``ABSENT`` is not a level that can answer — it is the terminal default.
#:
#: This is the *only* expression of the order. :func:`resolve_project_consent` walks
#: this tuple and dispatches through :data:`LEVEL_RESOLVERS`, so reordering, adding or
#: removing an entry here changes what the resolver does. Until 2026-07-30 the same
#: ordering was also hardcoded in the resolver's if-chain and nothing read this
#: constant: two representations of one invariant, free to drift silently, in the
#: module written to be their single definition site (C-003).
#:
#: There is deliberately no repo-slug-keyed level. One was added on 2026-07-30 and
#: removed the same day: FR-019 exists to condemn that record precisely because it is
#: keyed on a *mutable git remote*, so it cannot speak for a project. It also broke
#: spec.md's recorded edge case that a re-``git init``ed repo "starts non-consented" —
#: the stale repo default for the unchanged remote granted instead.
PROJECT_CONSENT_PRECEDENCE: tuple[ConsentLevel, ...] = (
    ConsentLevel.PROJECT_LOCAL,
    ConsentLevel.MACHINE_INDEX,
    ConsentLevel.ENV,
)


@dataclass(frozen=True)
class ConsentDecision:
    """The resolved answer plus which level produced it."""

    granted: bool
    level: ConsentLevel
    project_uuid: str | None
    reason: str


@dataclass(frozen=True)
class UnresolvedConsentEntry:
    """A path-keyed record whose checkout no longer resolves to a uuid."""

    path: str
    enabled: bool


@dataclass(frozen=True)
class ConsentBackfillResult:
    """Outcome of one path-keyed → uuid-keyed backfill pass."""

    mapped: int
    unresolved: int
    unresolved_entries: list[UnresolvedConsentEntry] = field(default_factory=list)


# --- project-local (level 1) ----------------------------------------------


#: Sentinel distinguishing "the key is not there" from "the key is there and holds
#: ``None``". ``dict.get`` collapses the two, and that collapse is the whole of
#: FR-027's absence half: a *missing* ``enabled:`` is no record and must keep falling
#: through, while ``enabled:`` with nothing after it is a record that records nothing.
_MISSING = object()


def _declared_uuid_or_fault(project: Any) -> tuple[str | None, str | None]:
    """Return ``(canonical_uuid, fault)`` for a config's ``project`` section (FR-027).

    **Asks ``identity/project.py`` rather than deciding here.**
    :meth:`~specify_cli.identity.project.ProjectIdentity.from_dict` is the single
    parse site both identity directions already go through, and #3030 FR-024 made it
    the one place that decides whether a recorded value can be understood. Re-deciding
    that here — as ``str(raw).strip() or None`` did — is how two notions of the same
    file end up one function apart, which is C-003's concern and the reason this
    defect class keeps regenerating.

    Two consequences, both measured:

    1. **FR-024's residual closes.** ``uuid: not-a-uuid``, a merge-conflict marker,
       ``42``, a mapping, a list, and a non-text sibling such as ``slug: {a: b}`` all
       resolved to ``granted=True`` with ``project_uuid=None`` once FR-024 stopped
       them crashing — captured with no identity at all, i.e. exactly the population
       FR-011/FR-017 then have to clean up. They are now faults, and FR-022's fence
       fires for them.
    2. **A leak nobody reported closes too.** The returned uuid is *canonical*, from
       the parsed :class:`~uuid.UUID`. The raw text was compared against the canonical
       uuid the journal stores, so ``AAAAAAAA-…``, a dash-less 32-hex spelling, a
       ``urn:uuid:`` form or a braced form — all the same uuid, all legibly the same
       project — matched nothing, and the checkout's committed refusal was discarded
       as belonging to some other project. Measured granting at ``machine_index``.
       Comparing raw file text against a canonical string is a third representation of
       one value; parsing both sides removes it.

    ``(None, None)`` is **absence**, and it must stay absence for every shape
    ``identity/project.py`` mints over: no ``project`` key, an empty ``project:``, a
    ``project`` section that is not a mapping (``project: guard-suite`` — FR-023's
    recorded decision), a missing ``uuid`` key, and a ``uuid:`` with no value. Those
    are the ordinary pre-``init`` states of a checkout, not broken records.
    """
    if not isinstance(project, dict):
        # No ``project`` key, an empty section, or a scalar section. ``load_identity``
        # reads all three as absence and mints over them; disagreeing here would deny
        # every checkout that has not been initialised yet.
        return (None, None)
    from specify_cli.identity.project import ConfigNotUnderstoodError, ProjectIdentity

    try:
        identity = ProjectIdentity.from_dict(project)
    except ConfigNotUnderstoodError as exc:
        return (None, str(exc))
    return (str(identity.project_uuid) if identity.project_uuid else None, None)


def _consent_value_or_fault(section: Any) -> tuple[bool | None, str | None]:
    """Return ``(hosted, fault)`` for a config's ``sync`` section (FR-027).

    **Only a YAML ``bool`` records a decision.** Every other *present* value is a
    fault, and no string form is accepted in either direction. The reasoning, because
    the two directions are not symmetric:

    * Accepting ``"false"`` as a refusal buys nothing — a fault already denies — while
      the same lookup table would have to rule on ``"true"``, ``1``, ``"yes"`` and
      ``"on"``, and those become **grants**. A truthy table on a consent key is a new
      leak surface with no upside.
    * ``no``/``off``/``yes``/``on`` are strings only because ruamel's round-trip loader
      is YAML 1.2. Accepting them would mean re-implementing the YAML 1.1 implicit
      typing that loader deliberately dropped, in a module that does not own it — so
      the accepted set would drift with a dependency this module cannot see.
    * A fault is *reportable*: :class:`ConfigReadFault` names the file, the key and
      the value, so an operator who mis-spelled their refusal is told. Silently
      honouring ``"false"`` would leave ``enabled: "true"`` broken and silent, which
      is the worse half — and ``enabled: False`` and ``enabled: "False"`` are one
      quote apart in a diff.

    Absence stays absence: no ``sync:`` section, an empty one, ``sync: {}``, and a
    missing ``enabled:`` key all mean "no record". Nothing in production writes this
    section (``identity/project.py`` preserves it as a foreign key), so a checkout
    with ``sync.auto_start`` and no ``enabled`` has recorded no consent decision, and
    denying on that would deny every delivery on the machine.
    """
    if section is None:
        # No ``sync:`` key at all, or ``sync:`` with nothing under it.
        return (None, None)
    if not isinstance(section, dict):
        return (
            None,
            f"{PROJECT_CONFIG_SYNC_SECTION} is not a mapping "
            f"(got {type(section).__name__})",
        )
    raw = section.get(PROJECT_CONFIG_ENABLED_KEY, _MISSING)
    if raw is _MISSING:
        return (None, None)
    if isinstance(raw, bool):
        return (raw, None)
    return (
        None,
        f"{PROJECT_CONFIG_SYNC_SECTION}.{PROJECT_CONFIG_ENABLED_KEY} is not a "
        f"boolean (got {raw!r})",
    )


def _read_project_local(
    repo_root: Path,
) -> tuple[str | None, bool | None, ConfigReadFault | None]:
    """Return ``(declared_uuid, hosted, fault)`` from a checkout's config.

    Never raises: a fault is *carried*, not thrown.

    The third element is #3030 FR-020, and it closes a **leak**, not a silence. A
    missing file is absence and yields ``fault=None``, exactly as before. But an
    unreadable or malformed file used to yield absence too, and absence falls through
    to the machine index — so a committed ``sync.enabled: false`` that a YAML error
    made unreadable was silently replaced by whatever the index happened to hold.
    Measured before the fix, with the index carrying a grant: ``granted=True,
    level=machine_index``. FR-013's refusal-outranks-grant rule, voided by a syntax
    error, on the record type that survives a clone or a rename — so a stale grant is
    precisely what is sitting there.

    A malformed *shape* (top-level not a mapping) is treated as a fault for the same
    reason: it is a file that exists and cannot be understood, not a file that says
    nothing.

    **Which fault, though, is one vocabulary shared with ``sync/config.py``** — see
    :data:`~specify_cli.sync.config.CONFIG_FAULT_KINDS`, which declares all four kinds
    and why there are four. This function used to mint two of those tokens with
    meanings the other producer did not share: an open-*or*-parse failure as
    ``unreadable`` and a non-mapping top level as ``unparseable``, where ``config.py``
    meant "could not open" and "bad syntax" by the same two words. The three branches
    below now separate cannot-open, opened-but-unparseable and parsed-but-wrong-shape,
    and the field-level branch further down keeps ``unusable``.

    **FR-027 extends that one notion from the file to the field**, because stopping at
    the file left FR-021's own defect open one level down. This function defined a
    fault as unreadable-or-wrong-shape and *not* as an unusable **value**, so a
    present-but-unusable ``sync.enabled`` was discarded as absence and fell through to
    the stale grant. Measured with the index granting, every one of these granted at
    ``machine_index``: ``"false"``, ``"true"``, ``no``, ``yes``, ``off``, ``on``, ``0``,
    ``1``, ``0.0``, ``1.5``, ``null``, a bare ``enabled:``, a list, a nested mapping,
    ``"False"``, ``"FALSE"``, ``"  false  "``, ``sync: disabled`` and a list-shaped
    ``sync:`` — nineteen shapes, not the four that were reported. ``enabled: False``
    unquoted is the one that already denied, because it is a real YAML bool.

    Why it is the *expected* failure mode: nothing in production writes this key, so
    it is hand-authored and committed, and ``no`` — the spelling an operator reaches
    for first — is a **string** under ruamel's YAML 1.2 loader.

    Every fault is reported, not just the first: a hand-merged config tends to carry
    more than one, and an operator who fixes the uuid only to be denied again for the
    consent key learns the tool is guessing. Same reasoning as
    ``identity/project.py``'s ``_identity_from_mapping``.
    """
    config_path = Path(repo_root) / ".kittify" / "config.yaml"
    try:
        exists = config_path.is_file()
    except OSError as exc:
        # An unreadable *enclosing directory* (e.g. ``.kittify`` itself chmod 000)
        # makes even the existence probe raise: pathlib re-raises ``PermissionError``
        # (EACCES) out of ``is_file()`` rather than swallowing it. Carry it as the
        # same ``unreadable`` fault as an unopenable file below (same operator remedy
        # -- chmod, not an edit), honouring this function's "never raises" contract.
        # #3291: previously this propagated a full traceback to stderr while the
        # verdict still refused correctly -- the answer was right, the noise was not.
        logger.debug("Unreadable project config directory for %s: %s", config_path, exc)
        return (
            None,
            None,
            ConfigReadFault(
                kind="unreadable",
                detail=f"{config_path}: could not be accessed ({exc})",
            ),
        )
    if not exists:
        # Absence, and the common case: the drain and the capture path both offer
        # whatever checkout they stand in, and most have no project config at all.
        # Calling this a fault would deny every delivery on the machine.
        return (None, None, None)
    try:
        from ruamel.yaml import YAML

        with open(config_path, encoding="utf-8") as handle:
            data = YAML().load(handle) or {}
    except OSError as exc:
        # Could not be *opened*: a permission or ownership problem, or a vanished
        # file. Split out from the parse failure below because the operator action is
        # different — chmod, not an edit — and one token covering both forced the
        # ``sync doctor`` advice to name two remedies and be wrong about one of them
        # every time it printed (#3030 C-003).
        logger.debug("Unopenable project config at %s: %s", config_path, exc)
        return (
            None,
            None,
            ConfigReadFault(
                kind="unreadable",
                detail=f"{config_path}: could not be opened ({exc})",
            ),
        )
    except Exception as exc:  # noqa: BLE001 - carried as a fault, never raised
        # It opened and its syntax does not parse. In practice this is a
        # ``ruamel.yaml.YAMLError``; the catch stays broad because this function's
        # contract is to answer rather than raise, and anything else escaping the
        # loader is still "opened, and could not be turned into a document".
        logger.debug("Unparseable project config at %s: %s", config_path, exc)
        return (
            None,
            None,
            ConfigReadFault(
                kind="unparseable",
                detail=f"{config_path}: could not be parsed ({exc})",
            ),
        )
    if not isinstance(data, dict):
        # It parsed, and the document is not a mapping — ``- a\n- list``, a bare
        # scalar, a merge-conflict marker. Its own kind rather than ``unparseable``,
        # which this branch used to borrow: telling an operator with a valid YAML list
        # to repair their syntax sends them to look for a fault that is not there.
        return (
            None,
            None,
            ConfigReadFault(
                kind="wrong_shape",
                detail=f"{config_path}: top-level content is not a mapping",
            ),
        )

    declared, identity_fault = _declared_uuid_or_fault(data.get("project"))
    hosted, consent_fault = _consent_value_or_fault(
        data.get(PROJECT_CONFIG_SYNC_SECTION)
    )
    field_faults = [f for f in (identity_fault, consent_fault) if f is not None]
    if field_faults:
        logger.debug("Unusable project config at %s: %s", config_path, field_faults)
        return (
            None,
            None,
            ConfigReadFault(
                kind="unusable",
                detail=f"{config_path}: {'; '.join(field_faults)}",
            ),
        )

    return (declared, hosted, None)


def read_project_local_consent(repo_root: Path) -> bool | None:
    """Read *repo_root*'s own ``sync.enabled`` decision. ``None`` means no decision.

    The side-effect-free reader for level 1, for callers that resolve consent for the
    checkout in front of them and so do not need the uuid chain. Unlike
    :func:`resolve_project_consent` it never reconciles the machine-global index, so
    ``resolve_checkout_sync_routing_readonly`` can use it and keep its promise not to
    dirty any config.

    Deliberately does not check the declared uuid: the caller already knows which
    checkout it is asking about, and this file speaks for that checkout.

    **Signature and semantics deliberately unchanged by #3030 FR-020**, including the
    fault-becomes-``None`` conflation. Its only production caller is
    ``sync/routing.py``, whose own chain then falls through ``local_sync_enabled`` and
    ``repo_default_sync_enabled`` before default-deny — so an unreadable project file
    can still be overridden by a checkout-level grant there. That is the same defect
    this function's own level-1 fix closes for the uuid chain, but the fall-through
    lives in ``routing.py`` and cannot be repaired from here. Reported, not silently
    half-fixed by changing this return value under a caller that is not expecting it.
    Use :func:`project_local_consent_fault` to ask about readability.

    #3030 FR-027 widens *which* shapes reach that conflation — a present-but-unusable
    ``sync.enabled`` or ``project.uuid`` is now a fault, so this returns ``None`` for
    them where it previously returned ``None`` for a different reason (absence). The
    signature and the conflation are still deliberately unchanged, and the denial is
    still delivered by ``routing.py``'s fence, which consults
    :func:`project_local_consent_fault` **before** this function's value is used.
    """
    return _read_project_local(repo_root)[1]


def project_local_consent_fault(repo_root: Path) -> ConfigReadFault | None:
    """Return why *repo_root*'s project config could not be read, or ``None``.

    The readability half of :func:`read_project_local_consent`, split out so
    ``sync/routing.py`` can adopt it without that function changing shape under its
    other callers (FR-020; the routing wiring is owed).
    """
    return _read_project_local(repo_root)[2]


def _project_local_votes(
    project_uuid: str, checkout_roots: list[Path]
) -> tuple[list[bool], list[ConfigReadFault]]:
    """Collect hosted-consent votes, and read faults, from the offered checkouts.

    A checkout that declares a different uuid is ignored: its file speaks only for
    its own project. Letting it answer would be the fuzzy correspondence FR-013's
    conflict rule and #3031 Defect 2 both exist to eliminate.

    Faults cannot be attributed that way, and that is the point (#3030 FR-020): an
    unreadable file does not disclose which uuid it declares, so it can neither be
    matched to this project nor excluded from it. It is therefore returned for the
    caller to treat fail-closed. The alternative — dropping it, as before — is what
    let a stale index grant stand in for an unreadable committed refusal.
    """
    votes: list[bool] = []
    faults: list[ConfigReadFault] = []
    for root in checkout_roots:
        declared, hosted, fault = _read_project_local(root)
        if fault is not None:
            faults.append(fault)
            continue
        if declared is None or declared != project_uuid or hosted is None:
            continue
        votes.append(hosted)
    return votes, faults


# --- machine-global index (level 2) ---------------------------------------


def get_project_consent(project_uuid: str) -> bool | None:
    """Read the uuid-keyed index. ``None`` means no record."""
    from .config import SyncConfig

    return cast("bool | None", SyncConfig().get_project_consent(project_uuid))


def set_project_consent(project_uuid: str, enabled: bool) -> None:
    """Write the uuid-keyed index."""
    from .config import SyncConfig

    SyncConfig().set_project_consent(project_uuid, enabled)


# --- the resolver ---------------------------------------------------------


def _normalize_uuid(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _answer_project_local(uuid: str, roots: list[Path]) -> ConsentDecision | None:
    """The project's own file. Refusal outranks grant (FR-013's rule).

    Order of the three branches below is the FR-020 fix, and each is chosen for the
    fail-closed direction:

    1. **A readable refusal wins outright**, faults or not. The answer is already
       known and attributable; a sibling root nobody could read cannot make a denial
       *less* certain, and downgrading it to UNDETERMINED would lose the attribution
       an operator needs.
    2. **A fault then outranks a grant.** An unreadable file may have refused, and
       falling through to the machine index means a stale grant answers for a
       committed refusal — the leak measured before this fix. Denying here is the
       only direction that cannot leak.
    3. Otherwise the readable votes decide, or the level abstains.
    """
    votes, faults = _project_local_votes(uuid, roots)

    if votes and not all(votes):
        _reconcile_index(uuid, False)
        return ConsentDecision(
            granted=False,
            level=ConsentLevel.PROJECT_LOCAL,
            project_uuid=uuid,
            reason=(
                "refused by the project's own .kittify/config.yaml"
                if len(votes) == 1
                else "at least one checkout of this project is opted out"
            ),
        )

    if faults:
        # No index reconciliation: we do not know what the file says, so writing a
        # verdict into the cache would launder a fault into a recorded decision.
        return ConsentDecision(
            granted=False,
            level=ConsentLevel.UNDETERMINED,
            project_uuid=uuid,
            reason=(
                "a checkout's own .kittify/config.yaml could not be read, so a "
                "committed refusal cannot be ruled out; refusing rather than "
                f"deferring to the machine index ({faults[0].detail})"
            ),
        )

    if not votes:
        return None
    granted = all(votes)
    _reconcile_index(uuid, granted)
    reason = "granted by the project's own .kittify/config.yaml"
    return ConsentDecision(
        granted=granted,
        level=ConsentLevel.PROJECT_LOCAL,
        project_uuid=uuid,
        reason=reason,
    )


def _answer_machine_index(uuid: str, _roots: list[Path]) -> ConsentDecision | None:
    """The uuid-keyed machine-global index — a cache, not a second source of truth.

    Reads through :meth:`SyncConfig.read_project_consent` so an *unreadable* index is
    answered as :attr:`ConsentLevel.UNDETERMINED` rather than falling through to the
    terminal "no consent record" default (#3030 FR-020). Both deny; only one of them
    tells the operator something true. One file read yields both the record and the
    readability, so "no record, index healthy" cannot be assembled from two reads that
    disagree.
    """
    from .config import SyncConfig

    read = SyncConfig().read_project_consent(uuid)
    if read.fault is not None:
        return ConsentDecision(
            granted=False,
            level=ConsentLevel.UNDETERMINED,
            project_uuid=uuid,
            reason=(
                "the machine-global consent index could not be read, so this "
                "project's recorded decision is unknown; refusing rather than "
                f"treating it as unrecorded ({read.fault.detail})"
            ),
        )
    if read.enabled is None:
        return None
    return ConsentDecision(
        granted=read.enabled,
        level=ConsentLevel.MACHINE_INDEX,
        project_uuid=uuid,
        reason=(
            "granted by the machine-global consent index"
            if read.enabled
            else "opted out in the machine-global consent index"
        ),
    )


def _answer_env(_uuid: str, _roots: list[Path]) -> ConsentDecision | None:
    """``SPEC_KITTY_ENABLE_SAAS_SYNC`` — arming, never per-project consent.

    Returns ``None`` unconditionally, and that *is* the invariant rather than a stub:
    a machine-global flag carries no per-project decision, so this level can never
    answer, in any position of the chain. It stays a declared level because FR-013's
    reconciliation records it as consulted-and-refused, and because a level that is
    silently absent from the dispatch is how someone re-adds it as a grant. The
    2026-07-27 incident is exactly this var granting: it was exported, and five
    projects with no record of their own rode along on it.
    """
    return None


#: One resolver per level of :data:`PROJECT_CONSENT_PRECEDENCE`. Each answers with a
#: :class:`ConsentDecision`, or ``None`` for "this level cannot answer — fall through".
#:
#: The tuple owns the *order*; this table owns *how* a level answers. The two are held
#: in bijection at import (:func:`_check_chain_is_dispatchable`) and pinned by
#: ``test_every_declared_level_has_exactly_one_resolver``, so neither can grow a level
#: the other does not know about.
LEVEL_RESOLVERS: dict[ConsentLevel, Callable[[str, list[Path]], ConsentDecision | None]] = {
    ConsentLevel.PROJECT_LOCAL: _answer_project_local,
    ConsentLevel.MACHINE_INDEX: _answer_machine_index,
    ConsentLevel.ENV: _answer_env,
}


def _check_chain_is_dispatchable() -> None:
    """Fail at import if the chain and the dispatch table disagree.

    A declared level with no resolver would be walked past in silence — the enforced
    chain would then be shorter than the documented one, which is the divergence this
    module exists to prevent. Cheaper to refuse to load than to under-enforce consent.
    """
    missing = [level for level in PROJECT_CONSENT_PRECEDENCE if level not in LEVEL_RESOLVERS]
    orphaned = [level for level in LEVEL_RESOLVERS if level not in PROJECT_CONSENT_PRECEDENCE]
    if missing or orphaned:
        raise RuntimeError(
            "consent precedence chain and its dispatch table disagree: "
            f"declared levels with no resolver={missing}, "
            f"resolvers for undeclared levels={orphaned}"
        )


_check_chain_is_dispatchable()


def resolve_project_consent(
    project_uuid: str | None,
    *,
    repo_root: Path | None = None,
    checkout_roots: list[Path] | None = None,
) -> ConsentDecision:
    """Resolve hosted-sync consent for *project_uuid* down the one chain.

    ``repo_root`` / ``checkout_roots`` are the checkouts available to consult for
    the project-local level; when none are readable the answer degrades to the next
    declared level, then to deny. An unresolvable *project_uuid* is never consentable
    (NFR-001).

    The order is not written here. It is read from
    :data:`PROJECT_CONSENT_PRECEDENCE` on every call and dispatched through
    :data:`LEVEL_RESOLVERS`, so the declared chain and the enforced chain are the same
    object. Nothing is consulted outside it — in particular the repo-slug-keyed
    ``[sync.repo_defaults]`` record is not a level, because it is keyed on a mutable
    git remote and a fresh clone or a re-``git init`` would inherit a decision nobody
    made about it (FR-019).
    """
    uuid = _normalize_uuid(project_uuid)
    if uuid is None:
        return ConsentDecision(
            granted=False,
            level=ConsentLevel.ABSENT,
            project_uuid=None,
            reason="project identity did not resolve; not consentable",
        )

    roots = list(checkout_roots or [])
    if repo_root is not None:
        roots.append(Path(repo_root))

    for level in PROJECT_CONSENT_PRECEDENCE:
        decision = LEVEL_RESOLVERS[level](uuid, roots)
        if decision is not None:
            return decision

    # Terminal default (FR-002): absence of a decision is not consent. The reason
    # names the env var because that is the incident's actual mechanism — the chain
    # reaches its arming level only to be refused by it.
    return ConsentDecision(
        granted=False,
        level=ConsentLevel.ABSENT,
        project_uuid=uuid,
        reason=(
            "no consent record for this project in the checkout or the "
            "machine-global index; SPEC_KITTY_ENABLE_SAAS_SYNC arms the machine "
            "but never grants per-project consent"
        ),
    )


def _reconcile_index(project_uuid: str, granted: bool) -> None:
    """Correct the cache when the authoritative file disagrees with it.

    Without this, a later lookup made without the checkout available would
    resurrect a stale grant, and the reported state would contradict the enforced
    one. Best-effort: a write failure must not turn an answered question into an
    error.

    **This is the most dangerous writer of the consent index, because it is reached
    from a read.** Nothing here is an operator action: ``resolve_project_consent``
    calls it on any drain tick that consults a checkout. On an unreadable index
    :func:`get_project_consent` answers ``None``, which differs from every verdict, so
    the correction always fired — and the write rebuilt the file from an empty
    document. Measured before the fix: resolving one project's consent left the index
    holding that project's single entry, with a bystander project's grant and an
    unrelated checkout override gone.

    ``SyncConfig`` now refuses that write
    (:class:`~specify_cli.sync.config.ConfigNotReadableError`) and the refusal lands in
    the ``except`` below, which is the right place for it: the authoritative file *was*
    read, the verdict is known and returned, and only the cache correction is declined.
    That is precisely the "a write failure must not turn an answered question into an
    error" contract this function already had — the swallow is not hiding the refusal,
    it is the refusal's intended landing.
    """
    try:
        if get_project_consent(project_uuid) != granted:
            set_project_consent(project_uuid, granted)
    except Exception as exc:  # noqa: BLE001 - the decision stands regardless
        logger.debug("Could not reconcile consent index for %s: %s", project_uuid, exc)


def consented_project_uuids(
    candidates: list[str | None],
    *,
    checkout_roots: list[Path] | None = None,
) -> frozenset[str]:
    """Return the subset of *candidates* that consent — the drain's seam.

    ``None`` and blank entries are dropped rather than passed through: NFR-001 is
    a subset invariant whose second half is ``None ∉ delivered``, and an event
    whose project cannot be identified can never be shown to belong to a
    consenting project.

    ``checkout_roots`` are the checkouts the caller can offer for level 1. The drain
    passes the checkout it is running in; a root that declares a *different* uuid is
    ignored by :func:`_project_local_votes`, so offering extra roots can never widen
    the answer.
    """
    granted: set[str] = set()
    for candidate in candidates:
        uuid = _normalize_uuid(candidate)
        if uuid is None or uuid in granted:
            continue
        decision = resolve_project_consent(uuid, checkout_roots=checkout_roots)
        if decision.granted:
            granted.add(uuid)
    return frozenset(granted)


# --- FR-020: the machine-level readability question (SC-004's seam) --------


@dataclass(frozen=True)
class ConsentIndexHealth:
    """Whether the machine-global consent index can be read at all.

    The question ``sync doctor`` must ask **once**, rather than inferring a machine
    fault from N projects that each came back undetermined. SC-004 requires the doctor
    to name every project present with its consent state; on an unreadable index every
    one of those states is unknown for a single shared reason, and reporting the reason
    once is the difference between an operator fixing a file and an operator opting
    twenty projects in again.

    Deliberately *not* consulted by :func:`resolve_project_consent`. A pre-flight
    readability check followed by a separate per-project read is two reads that can
    disagree; the resolver gets its fault from the same read that produced the record
    (:meth:`SyncConfig.read_project_consent`). This type is for reporting only.
    """

    readable: bool
    fault: ConfigReadFault | None

    @property
    def summary(self) -> str:
        """One operator-facing line. Names the file, because it must be fixed."""
        if self.fault is None:
            return "consent index readable"
        return f"consent index UNREADABLE — every project resolves as undetermined and nothing will be delivered: {self.fault.detail}"


def consent_index_health() -> ConsentIndexHealth:
    """Report whether the machine-global consent index is readable (FR-020).

    A **missing** index is healthy: an unconfigured machine has recorded no consent,
    which denies under FR-002 and is not a fault to repair.
    """
    from .config import SyncConfig

    read = SyncConfig().read()
    return ConsentIndexHealth(readable=read.readable, fault=read.fault)


# --- T016: backfill path-keyed records into the uuid index ----------------


def backfill_uuid_consent_index() -> ConsentBackfillResult:
    """Map today's path-keyed consent records onto the uuid index.

    One batched write, deliberately: every ``SyncConfig`` setter is an unlocked
    whole-file read-modify-write, the daemon writes the same file as an
    interactive ``sync enable``, and a lost record is now a *silent delivery
    denial* rather than a cosmetic loss. N per-path cycles would widen that window
    N times.

    Idempotent: a converged index reports ``mapped == 0``.

    A path that no longer resolves to a uuid keeps its path-keyed entry and is
    reported as unresolved (:data:`UNRESOLVED_MARKER`). Dropping it would lose the
    operator's decision; silently leaving it unmarked would imply it is enforced
    when the predicate cannot see it (US2 scenario 3).
    """
    from .config import SyncConfig

    config = SyncConfig()
    path_records = config.get_all_checkout_sync_records()

    votes: dict[str, list[bool]] = {}
    unresolved: list[UnresolvedConsentEntry] = []

    for raw_path, enabled in path_records.items():
        # A read fault lands in the same bucket as a missing uuid: *unresolved*, which
        # is marked and reported rather than dropped (:data:`UNRESOLVED_MARKER`). That
        # is already the fail-closed answer here — an unmappable record contributes no
        # vote, so it can never manufacture a grant — and unlike the resolver, the
        # backfill has no next level to defer to, so it needs no UNDETERMINED branch.
        declared, _hosted, _fault = _read_project_local(Path(raw_path))
        if declared is None:
            unresolved.append(UnresolvedConsentEntry(path=raw_path, enabled=enabled))
            continue
        votes.setdefault(declared, []).append(enabled)

    # FR-013's conflict rule, applied once here as well as in the resolver: any
    # opted-out checkout denies the whole project.
    resolved = {uuid: all(v) for uuid, v in votes.items()}
    existing = config.get_all_project_consent()
    pending = {u: g for u, g in resolved.items() if existing.get(u) != g}

    if pending:
        config.set_project_consent_bulk(pending)
    if unresolved:
        config.mark_checkout_records_unresolved([e.path for e in unresolved])

    return ConsentBackfillResult(
        mapped=len(pending),
        unresolved=len(unresolved),
        unresolved_entries=unresolved,
    )


# Only names with a real ``src/`` consumer are advertised — the symbol-level
# dead-code gate (``tests/architectural/test_no_dead_symbols.py``) is a shrink-only
# ratchet, and widening its allowlist to carry an aspirational surface is how a
# module's ``__all__`` stops describing anything. Everything else in this module
# stays importable; the list regrows as consumers actually land.
#
# This list is the UNION of the two sides of the #3030 lane-f rebase, recomputed from
# the merged tree rather than taken from either branch — each side had trimmed against
# a different set of live callers, so both were correct locally and wrong merged.
# Verified importers: ``consented_project_uuids`` (emitter, selection, background,
# local_commit), ``read_project_local_consent`` / ``project_local_consent_fault`` /
# ``set_project_consent`` (routing), ``resolve_project_consent``
# (delivery/status_report).
#
# ``resolve_project_consent`` is advertised, and the note that previously stood here
# claiming it "has no production caller at all" is deleted rather than reworded: it is
# now false. ``delivery/status_report.build_per_project_store_report`` — FR-015's
# per-project report — is its first production caller, reached from ``sync doctor``,
# ``sync status`` and ``sync migrate``.
#
# Still genuinely unwired, and recorded here rather than allowlisted:
# ``consent_index_health`` (#3030 FR-020). It exists for SC-004's ``sync doctor``,
# which still cannot tell an operator their consent index is unreadable. The name
# stays importable and unadvertised until that consumer lands.
__all__ = [
    "consented_project_uuids",
    "project_local_consent_fault",
    "read_project_local_consent",
    "resolve_project_consent",
    "set_project_consent",
]
