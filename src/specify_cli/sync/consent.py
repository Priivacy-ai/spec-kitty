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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
    """Which level of the chain answered. Rendered by FR-015's report."""

    PROJECT_LOCAL = "project_local"
    MACHINE_INDEX = "machine_index"
    ENV = "env"
    ABSENT = "absent"


#: The chain, highest authority first. Declared once; never re-derived.
#: ``ABSENT`` is not a level that can answer — it is the terminal default.
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


def _read_project_local(repo_root: Path) -> tuple[str | None, bool | None]:
    """Return ``(declared_uuid, hosted)`` from a checkout's config, or ``(None, None)``.

    Never raises: a missing, unreadable or malformed file is *absence*, which the
    caller degrades to the next level rather than treating as a decision.
    """
    config_path = Path(repo_root) / ".kittify" / "config.yaml"
    if not config_path.is_file():
        return (None, None)
    try:
        from ruamel.yaml import YAML

        with open(config_path, encoding="utf-8") as handle:
            data = YAML().load(handle) or {}
    except Exception as exc:  # noqa: BLE001 - malformed config is absence
        logger.debug("Unreadable project config at %s: %s", config_path, exc)
        return (None, None)
    if not isinstance(data, dict):
        return (None, None)

    project = data.get("project")
    declared = None
    if isinstance(project, dict):
        raw = project.get("uuid")
        declared = str(raw).strip() or None if raw is not None else None

    hosted = None
    section = data.get(PROJECT_CONFIG_SYNC_SECTION)
    if isinstance(section, dict):
        raw_hosted = section.get(PROJECT_CONFIG_ENABLED_KEY)
        if isinstance(raw_hosted, bool):
            hosted = raw_hosted

    return (declared, hosted)


def read_project_local_consent(repo_root: Path) -> bool | None:
    """Read *repo_root*'s own ``sync.enabled`` decision. ``None`` means no decision.

    The side-effect-free reader for level 1, for callers that resolve consent for the
    checkout in front of them and so do not need the uuid chain. Unlike
    :func:`resolve_project_consent` it never reconciles the machine-global index, so
    ``resolve_checkout_sync_routing_readonly`` can use it and keep its promise not to
    dirty any config.

    Deliberately does not check the declared uuid: the caller already knows which
    checkout it is asking about, and this file speaks for that checkout.
    """
    return _read_project_local(repo_root)[1]


def _project_local_votes(
    project_uuid: str, checkout_roots: list[Path]
) -> list[bool]:
    """Collect hosted-consent votes from checkouts that declare *project_uuid*.

    A checkout that declares a different uuid is ignored: its file speaks only for
    its own project. Letting it answer would be the fuzzy correspondence FR-013's
    conflict rule and #3031 Defect 2 both exist to eliminate.
    """
    votes: list[bool] = []
    for root in checkout_roots:
        declared, hosted = _read_project_local(root)
        if declared is None or declared != project_uuid or hosted is None:
            continue
        votes.append(hosted)
    return votes


# --- machine-global index (level 2) ---------------------------------------


def get_project_consent(project_uuid: str) -> bool | None:
    """Read the uuid-keyed index. ``None`` means no record."""
    from .config import SyncConfig

    return SyncConfig().get_project_consent(project_uuid)


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


def resolve_project_consent(
    project_uuid: str | None,
    *,
    repo_root: Path | None = None,
    checkout_roots: list[Path] | None = None,
) -> ConsentDecision:
    """Resolve hosted-sync consent for *project_uuid* down the one chain.

    ``repo_root`` / ``checkout_roots`` are the checkouts available to consult for
    level 1; when none are readable the answer degrades to the index, then to
    deny. An unresolvable *project_uuid* is never consentable (NFR-001).
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

    # Level 1 — the project's own file. Refusal outranks grant (FR-013's rule).
    votes = _project_local_votes(uuid, roots)
    if votes:
        granted = all(votes)
        _reconcile_index(uuid, granted)
        reason = (
            "granted by the project's own .kittify/config.yaml"
            if granted
            else "refused by the project's own .kittify/config.yaml"
            if len(votes) == 1
            else "at least one checkout of this project is opted out"
        )
        return ConsentDecision(
            granted=granted,
            level=ConsentLevel.PROJECT_LOCAL,
            project_uuid=uuid,
            reason=reason,
        )

    # Level 2 — the machine-global index.
    recorded = get_project_consent(uuid)
    if recorded is not None:
        return ConsentDecision(
            granted=recorded,
            level=ConsentLevel.MACHINE_INDEX,
            project_uuid=uuid,
            reason=(
                "granted by the machine-global consent index"
                if recorded
                else "opted out in the machine-global consent index"
            ),
        )

    # Level 3 — the env var, which cannot grant on its own. It is reached only to
    # be refused, so that the reason names the incident's actual mechanism.
    #
    # Nothing is consulted between the uuid index and here. In particular the
    # repo-slug-keyed ``[sync.repo_defaults]`` record is NOT a level of this chain:
    # it is keyed on a mutable git remote, so a fresh clone or a re-``git init``
    # inherits a decision that was never made about it (FR-019).
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
        declared, _hosted = _read_project_local(Path(raw_path))
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
# Notably absent: ``resolve_project_consent``. It has no production caller at all —
# the drain reaches it only through ``consented_project_uuids``, and no reporting
# surface calls it yet. That is a real finding, not a packaging detail; trimming the
# advertised surface records it honestly rather than hiding it behind an allowlist.
__all__ = [
    "consented_project_uuids",
    "read_project_local_consent",
    "set_project_consent",
]
