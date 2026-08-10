"""LocalCommit core: SyncState persistence and frame emission.

Implements the ``LocalCommit`` WebSocket frame lifecycle:
- ``SyncState`` dataclass: persists to ``.kittify/sync-state.json``
- ``emit_local_commit()``: stores frame + sends if WebSocket is connected
- ``flush_pending_local_commits()``: replays pending frames on connect
- ``record_local_commit_ack()``: removes acked entry; updates confirmed hash
- Amended-commit handling: same ``build_id`` → replace prior pending entry

No PII is stored: the frame contains only a git hash, ULID IDs, a project uuid,
file paths within the project, and an ISO timestamp.  No machine name, hostname,
or developer identity appears in any frame or state file.

FR-010–FR-017.

Per-project consent (#3030 T027, FR-002/NFR-001)
------------------------------------------------
``changed_files`` are repo-relative paths under ``kitty-specs/``, i.e. **mission
slugs**; for the 2026-07-27 incident's population those slugs are client engagement
names. This module therefore has the same egress duty as the drain, and until T027
had no consent check at all. Two gates now stand on the path, and both resolve the
answer through ``sync/consent.py`` — the *one* resolver (C-003):

* :func:`emit_local_commit` refuses to stage or send a frame for a project that has
  not consented, so nothing reaches ``sync-state.json`` for the flush to replay.
* :func:`flush_pending_local_commits` re-resolves consent **per frame** before each
  send, which is what covers residual frames staged before this gate existed and
  projects whose consent was revoked after staging.

The flush's gate reads identity from the **frame**, never from the working
directory. That is not a stylistic preference: the flush is called with
``WebSocketClient._repo_root``, which defaults to ``Path.cwd()`` because
``sync/runtime.py`` constructs the client without it. A cwd-derived check would
answer the question for whichever project the operator happens to be standing in
and authorize another project's egress on its grant — the defect T025 names for
body uploads and M1 names for capture. ``build_id`` cannot substitute: it is a
one-way uuid5 of ``(project_uuid, node_id)`` and degrades to a random uuid4 when
identity is incomplete, and ``mission_id`` is a repo-local slug. So the frame
carries ``project_uuid`` explicitly.

Operator purge (#3030 T022, FR-016/FR-017/NFR-006)
--------------------------------------------------
Withheld frames are retained, so the queue is a fourth store the operator's purge
must clear alongside the journal, the delivery ledger and the body-upload queue:
:func:`purge_pending_local_commits`, :func:`purge_all_pending_local_commits` and
:func:`census_pending_local_commits`. Dry-run by default, and never reachable from
an unattended path (C-002).

Unlike the other three, this store is **per-checkout** ``LOCAL_RUNTIME`` state, and
that locality is load-bearing rather than incidental: it is what makes the pre-fix
frames — written before ``project_uuid`` existed, i.e. the incident's own population —
attributable at all. See :func:`purge_pending_local_commits` for the decision and its
reasoning.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kernel.clock import UTC, datetime, parse_iso
from specify_cli.core.atomic import atomic_write

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SyncState dataclass
# ---------------------------------------------------------------------------


@dataclass
class SyncState:
    """Persistent local sync state for the ``LocalCommit`` frame pipeline.

    Attributes
    ----------
    last_saas_confirmed_hash:
        The most-recently acknowledged git hash from SaaS, or ``None`` if no
        acknowledgement has been received yet.
    pending_local_commits:
        Ordered list of ``LocalCommit`` frame dicts awaiting acknowledgement.
        Each entry mirrors the wire-format frame exactly.
    """

    last_saas_confirmed_hash: str | None = None
    pending_local_commits: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Path helper
# ---------------------------------------------------------------------------


def _sync_state_path(repo_root: Path) -> Path:
    return repo_root / ".kittify" / "sync-state.json"


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------


def load_sync_state(repo_root: Path) -> SyncState:
    """Load ``SyncState`` from ``.kittify/sync-state.json``.

    Returns an empty ``SyncState`` if the file does not exist or is malformed.
    Never raises.
    """
    path = _sync_state_path(repo_root)
    if not path.exists():
        return SyncState()
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return SyncState(
            last_saas_confirmed_hash=data.get("last_saas_confirmed_hash"),
            pending_local_commits=list(data.get("pending_local_commits", [])),
        )
    except Exception:  # noqa: BLE001
        logger.warning("sync-state.json is malformed; resetting to empty state")
        return SyncState()


def save_sync_state(repo_root: Path, state: SyncState) -> None:
    """Persist *state* atomically to ``.kittify/sync-state.json``."""
    path = _sync_state_path(repo_root)
    data: dict[str, Any] = {
        "last_saas_confirmed_hash": state.last_saas_confirmed_hash,
        "pending_local_commits": state.pending_local_commits,
    }
    atomic_write(path, json.dumps(data, indent=2), mkdir=True)


# ---------------------------------------------------------------------------
# Per-project consent gate (#3030 T027)
# ---------------------------------------------------------------------------


def _frame_project_uuid(frame: Mapping[str, Any]) -> str | None:
    """The project uuid the frame carries about **itself**.

    Blank normalizes to ``None``: NFR-001 is a subset invariant whose second half is
    ``None ∉ delivered``, and a blank key would otherwise become a groupable,
    consentable value that pools unrelated projects.
    """
    raw = frame.get("project_uuid")
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _checkout_project_uuid(repo_root: Path) -> str | None:
    """Read the emitting checkout's own declared project uuid. Never raises."""
    try:
        from specify_cli.identity.project import load_identity  # noqa: PLC0415

        identity = load_identity(Path(repo_root) / ".kittify" / "config.yaml")
    except Exception:  # noqa: BLE001 - an unreadable identity is absence, and absence denies
        logger.debug("Could not read project identity at %s", repo_root, exc_info=True)
        return None
    return str(identity.project_uuid) if identity.project_uuid else None


def _frame_project_consents(frame: Mapping[str, Any], *, offered_roots: list[Path]) -> bool:
    """Does the project *this frame belongs to* consent to hosted sync?

    Delegates to ``consent.consented_project_uuids`` — the advertised seam over the
    one precedence chain — rather than re-deriving it here. A frame whose
    ``project_uuid`` is missing or blank is dropped by that helper, so an
    unidentifiable frame is permanently unsendable rather than unsent-for-now.

    ``offered_roots`` are checkouts the caller can offer for the project-local level.
    Offering the flush's cwd is safe by construction: ``_project_local_votes``
    ignores a root that declares a different uuid, so an extra root can never widen
    the answer — only supply the authoritative file when cwd *is* the frame's
    project.

    The resolver returns the consenting **subset** of its candidates, so the answer
    is checked for *this* uuid's membership rather than for the subset being
    non-empty. Emptiness is equivalent only while exactly one candidate is passed;
    the day anyone batches frames through here, one consenting project would
    authorize every other project in the batch — the "returned set not checked for
    the right element" shape T025 names for body uploads. Membership costs nothing
    and does not depend on a future editor reading this paragraph.

    Fails **closed** on any error. Everything else in this module swallows
    exceptions so a git hook is never interrupted; here that same instinct would
    turn an unanswerable consent question into egress, and inability to determine
    consent is not consent (FR-003's rule). This branch is pinned by a test rather
    than trusted: an ``except`` that quietly starts returning ``True`` is how a
    guard reports "clean" forever.
    """
    uuid = _frame_project_uuid(frame)
    try:
        from specify_cli.sync.consent import consented_project_uuids  # noqa: PLC0415

        granted = uuid in consented_project_uuids([uuid], checkout_roots=offered_roots)
    except Exception:  # noqa: BLE001 - unanswerable is not granted
        logger.warning(
            "Could not resolve hosted-sync consent for a LocalCommit frame; refusing to send it",
            exc_info=True,
        )
        return False
    if not granted:
        logger.debug(
            "LocalCommit frame withheld: project %s has not consented to hosted sync",
            uuid or "<unidentified>",
        )
    return granted


# ---------------------------------------------------------------------------
# emit_local_commit
# ---------------------------------------------------------------------------


def emit_local_commit(
    repo_root: Path,
    git_hash: str,
    mission_id: str,
    build_id: str,
    changed_files: list[str],
    committed_at: str,
) -> None:
    """Build and dispatch a ``LocalCommit`` frame, if *repo_root*'s project consents.

    Storage is **not** unconditional. A project with no consent record gets no frame
    at all: staging it and relying on the flush to withhold it would leave the
    mission slug on disk and make the whole guarantee rest on one gate. Refusal is
    silent apart from a debug line — a local command must still succeed (FR-010).

    When consent is granted the frame is stored in ``sync-state.json`` as a pending
    entry. It is **not** sent from here: FR-032 removed the immediate-send path,
    which could never obtain a transport because nothing in ``src/`` ever assigned
    ``token_manager._ws_client``. The live egress route is the connect-time flush
    (``flush_pending_local_commits``, called from ``sync/client.py``), which applies
    its own per-frame consent gate. That is why the gate above is load-bearing: this
    function's refusal is what keeps a non-consenting project's mission slug off
    disk in the first place, rather than relying on the flush to withhold it.

    The pending entry is only removed once ``record_local_commit_ack`` receives the
    corresponding acknowledgement — this prevents frame loss when a send succeeds
    but the ack is never delivered.

    If an existing pending entry carries the same ``build_id`` (i.e. the commit
    was amended), it is replaced by the new frame so the list never contains two
    entries for the same build.

    The stored frame carries ``project_uuid`` so the on-connect flush can re-resolve
    consent from the frame's own identity instead of from its working directory.
    """
    frame: dict[str, Any] = {
        "type": "LocalCommit",
        "git_hash": git_hash,
        "mission_id": mission_id,
        "build_id": build_id,
        "project_uuid": _checkout_project_uuid(repo_root),
        "changed_files": changed_files,
        "committed_at": committed_at,
    }

    if not _frame_project_consents(frame, offered_roots=[Path(repo_root)]):
        return

    # Load state, replace any prior pending entry for the same build_id (amend),
    # append the new frame, then persist.
    state = load_sync_state(repo_root)
    state.pending_local_commits = [
        entry
        for entry in state.pending_local_commits
        if entry.get("build_id") != build_id
    ]
    state.pending_local_commits.append(frame)
    save_sync_state(repo_root, state)

    # There is deliberately no immediate send here (#3030 FR-032). This function used
    # to try one, via a local ``_get_saas_client()`` whose only client source was
    # ``getattr(token_manager, "_ws_client", None)`` — an attribute **nothing in
    # ``src/`` has ever assigned**. No ``=``, no ``setattr``, and ``specify_cli/auth/``
    # does not declare it; only tests injected it. The genuinely live WebSocket client
    # is a different attribute on a different owner (``SyncRuntime.ws_client``,
    # ``sync/runtime.py``), so the immediate send never executed in production. Its
    # deletion changes no observable behaviour and removes the standing hazard: an
    # innocuous-looking ``token_manager._ws_client = ...`` would have turned this path
    # — and two others reading the same phantom — live simultaneously.
    #
    # The frame is not lost. ``flush_pending_local_commits`` replays it on the next
    # WebSocket connect, and that path IS live because its client arrives as a
    # parameter from ``sync/client.py``. That is why WP12's per-frame gate on the
    # flush was the load-bearing half.
    #
    # The consent gate above is unaffected by this removal and must stay: it guards
    # *staging* into ``sync-state.json``, which the live flush reads, not the send
    # deleted here.


# ---------------------------------------------------------------------------
# flush_pending_local_commits
# ---------------------------------------------------------------------------


def flush_pending_local_commits(repo_root: Path, client: Any) -> None:
    """Send every consenting unacknowledged pending ``LocalCommit`` frame to *client*.

    Frames are sent in ascending ``committed_at`` (chronological) order.
    Entries whose ``git_hash`` matches ``last_saas_confirmed_hash`` are
    considered already acknowledged and skipped.

    This function is intended to be called once the WebSocket connection is
    established (on-connect replay), and in production *repo_root* is
    ``WebSocketClient._repo_root`` — which defaults to ``Path.cwd()``. It is
    therefore treated strictly as "where the queue file lives" and as one *offered*
    checkout for the project-local consent level. It is never the identity the
    decision is made from: each frame is judged on its own ``project_uuid``, so
    standing in a consenting project cannot authorize another project's frames
    (FR-002/NFR-001).

    Withheld frames are **retained**, not dropped. A frame from a project that later
    consents becomes sendable; one that carries no resolvable identity never does,
    and staying on disk keeps it available as evidence of what a pre-gate build
    queued. The operator's purge path is :func:`purge_pending_local_commits` in this
    module (WP08 T022) — a named function rather than the promise this docstring used
    to carry, which pointed at a work package whose surface did not include this file.
    """
    state = load_sync_state(repo_root)

    unacked = [
        entry
        for entry in state.pending_local_commits
        if entry.get("git_hash") != state.last_saas_confirmed_hash
    ]

    def _sort_key(entry: dict[str, Any]) -> datetime:
        ts: str = entry.get("committed_at", "")
        try:
            return parse_iso(ts)
        except (ValueError, TypeError):
            return datetime.min.replace(tzinfo=UTC)

    unacked.sort(key=_sort_key)

    offered_roots = [Path(repo_root)]
    sent = 0
    withheld = 0
    for frame in unacked:
        if not _frame_project_consents(frame, offered_roots=offered_roots):
            withheld += 1
            continue
        try:
            _send_event(client, frame)
            sent += 1
        except Exception:  # noqa: BLE001
            logger.debug("LocalCommit flush send failed for %s", frame.get("git_hash"), exc_info=True)

    logger.debug(
        "Flushed %d pending LocalCommit frame(s); withheld %d for lack of project consent",
        sent,
        withheld,
    )


# ---------------------------------------------------------------------------
# record_local_commit_ack
# ---------------------------------------------------------------------------


def record_local_commit_ack(repo_root: Path, git_hash: str) -> None:
    """Handle a ``LocalCommitAck`` from SaaS.

    Updates ``last_saas_confirmed_hash`` and removes the corresponding entry
    from ``pending_local_commits``.
    """
    state = load_sync_state(repo_root)
    state.last_saas_confirmed_hash = git_hash
    state.pending_local_commits = [
        entry
        for entry in state.pending_local_commits
        if entry.get("git_hash") != git_hash
    ]
    save_sync_state(repo_root, state)


# ---------------------------------------------------------------------------
# Operator purge of the pending queue (#3030 WP08 T022 — FR-016/FR-017/NFR-006)
# ---------------------------------------------------------------------------

#: Census key for frames carrying no resolvable ``project_uuid``. Mirrors
#: ``delivery.retention.IDENTITY_LESS_KEY`` — the journal and body-queue censuses
#: group blank identity under ``""`` — so one purge report can present all three
#: stores without a per-store special case. Defined here rather than imported: a
#: per-checkout JSON queue should not take an import dependency on the delivery
#: stores to borrow a one-character constant, and ``delivery/`` deliberately
#: reaches into ``sync/`` at call time only.
IDENTITY_LESS_FRAME_KEY = ""


def _frame_census_key(frame: Mapping[str, Any]) -> str:
    """The census bucket *frame* belongs to: its own uuid, or the identity-less key.

    Selection and census are both defined as this one function of a frame, so the two
    cannot disagree about which bucket a frame is in. A purge that deleted by one rule
    and counted by another would satisfy its own differential while moving frames
    nobody counted.
    """
    return _frame_project_uuid(frame) or IDENTITY_LESS_FRAME_KEY


@dataclass(frozen=True)
class PendingCommitPurgeResult:
    """Observable outcome of one purge over a checkout's ``pending_local_commits``.

    Carries the **whole census** before and after rather than only the target's
    number, for the same reason
    :class:`~specify_cli.delivery.retention.BodyQueuePurgeResult` does: NFR-006 is a
    differential ("0% of any other project's entries"), and a result that reports only
    what it removed cannot substantiate that claim. Callers should still measure
    independently where they can — a purge reporting its own arithmetic proves only
    that it is self-consistent.
    """

    selector: str
    dry_run: bool
    removed: int
    before: Mapping[str, int] = field(default_factory=dict)
    after: Mapping[str, int] = field(default_factory=dict)
    #: ``True`` for FR-017's total purge over this checkout's queue. A flag rather
    #: than a sentinel selector, because :data:`IDENTITY_LESS_FRAME_KEY` is already
    #: the empty string and any other sentinel could collide with a stored uuid.
    all_frames: bool = False
    #: Whether the identity-less bucket was in scope — i.e. whether this checkout's
    #: own declared identity vouched for its unattributable frames. Part of the
    #: result because it changes what "100% of the target" means, and the operator
    #: needs to see whether the pre-fix population was covered.
    unattributed_in_scope: bool = False

    @property
    def scope_keys(self) -> frozenset[str]:
        """The census buckets this purge claims. Empty for a selector matching nothing."""
        if self.all_frames:
            return frozenset(self.before) | frozenset(self.after)
        if not self.selector:
            return frozenset()
        keys = {self.selector}
        if self.unattributed_in_scope:
            keys.add(IDENTITY_LESS_FRAME_KEY)
        return frozenset(keys)

    @property
    def target_before(self) -> int:
        return sum(self.before.get(key, 0) for key in self.scope_keys)

    @property
    def target_after(self) -> int:
        return sum(self.after.get(key, 0) for key in self.scope_keys)

    @property
    def selected(self) -> int:
        """Entries the selection covers — what a real run *will* remove.

        Distinct from :attr:`removed`, which is ``0`` on a dry run because a dry run
        removes nothing. A preview that could only ever report ``0`` would tell the
        operator nothing, and WP08's definition of done requires the preview's count
        to equal what the real run then deletes.
        """
        return self.target_before

    @property
    def other_project_differential(self) -> int:
        """Absolute entry-count change across every bucket **not** in scope.

        Over the union of both censuses, so a bucket that *appeared* counts as a
        difference too — a purge must neither remove nor create another project's
        entries. NFR-006 requires ``0``. For a total purge there is no "other" and
        this is ``0`` by definition; the load-bearing check there is
        ``target_after == 0``.
        """
        keys = (set(self.before) | set(self.after)) - self.scope_keys
        return sum(abs(self.after.get(key, 0) - self.before.get(key, 0)) for key in keys)

    @property
    def is_exact(self) -> bool:
        """100% of the selection gone, 0% of anything else moved (SC-006 / NFR-006)."""
        expected_after = self.target_before if self.dry_run else 0
        return self.target_after == expected_after and self.other_project_differential == 0


def census_pending_local_commits(repo_root: Path) -> dict[str, int]:
    """Per-project counts of the frames queued in *repo_root*'s ``sync-state.json``.

    Unattributable frames are grouped under :data:`IDENTITY_LESS_FRAME_KEY`, so the
    pre-fix population is **visible** rather than silently folded into some project's
    number. An operator cannot ask for the erasure of entries the report never shows
    them.

    Total-preserving by construction: every frame maps to exactly one bucket via
    :func:`_frame_census_key`. That is a correctness property, not tidiness — every
    NFR-006 differential subtracts this census, so a population counted in no bucket
    could be moved by a purge that still reported "0% of any other project's entries".
    The journal census had exactly that hole for non-NULL blank uuids.
    """
    census: dict[str, int] = {}
    for frame in load_sync_state(Path(repo_root)).pending_local_commits:
        key = _frame_census_key(frame)
        census[key] = census.get(key, 0) + 1
    return census


def _checkout_vouches_for(repo_root: Path, target: str) -> bool:
    """Is *repo_root* the store of project *target*, by its own declaration?

    The question locality attribution rests on. Compared case-insensitively, because a
    uuid hand-written in upper case in ``config.yaml`` must not silently leave the
    incident's frames behind; answered ``False`` for an unreadable or absent identity,
    because absence must no more authorise deletion than it authorises egress.
    """
    declared = _checkout_project_uuid(Path(repo_root))
    if not declared or not target:
        return False
    return declared.strip().casefold() == target.strip().casefold()


def _purge_frames(
    repo_root: Path,
    *,
    selector: str,
    scope_keys: frozenset[str] | None,
    dry_run: bool,
    all_frames: bool = False,
    unattributed_in_scope: bool = False,
) -> PendingCommitPurgeResult:
    """Shared core: census, (optionally) drop the selected frames, census again.

    The **only** path that removes an entry from ``pending_local_commits`` other than
    an ack, so every selector composes onto it (C-003). ``scope_keys=None`` means
    "every frame" — FR-017's total purge — and is deliberately distinct from the empty
    set, which means "nothing matched" and must never degrade into "match everything".

    The second census is a fresh read even on a dry run rather than a copy of the
    first. "Nothing changed" is precisely the claim a dry run has to earn, and this is
    the only place a dry run that quietly mutated could still be caught.
    """
    root = Path(repo_root)
    before = census_pending_local_commits(root)

    removed = 0
    if not dry_run and (scope_keys is None or scope_keys):
        state = load_sync_state(root)
        retained = [
            frame
            for frame in state.pending_local_commits
            if not (scope_keys is None or _frame_census_key(frame) in scope_keys)
        ]
        removed = len(state.pending_local_commits) - len(retained)
        if removed:
            # Write only when something is actually removed: reporting zero must not
            # materialise a queue file for a checkout that never had one.
            state.pending_local_commits = retained
            save_sync_state(root, state)

    return PendingCommitPurgeResult(
        selector=selector,
        dry_run=dry_run,
        removed=removed,
        before=before,
        after=census_pending_local_commits(root),
        all_frames=all_frames,
        unattributed_in_scope=unattributed_in_scope,
    )


def purge_pending_local_commits(
    repo_root: Path,
    project_uuid: str,
    *,
    dry_run: bool = True,
) -> PendingCommitPurgeResult:
    """Remove one project's queued ``LocalCommit`` frames — the fourth purge store (T022).

    Dry-run by **default**, matching FR-016's ``sync purge`` contract and
    :func:`~specify_cli.delivery.retention.purge_project_body_uploads`: the census is
    taken either way, so a preview reports exactly what a confirmed run will remove
    without removing it. What it reports as :attr:`~PendingCommitPurgeResult.selected`
    is what a real run then deletes.

    Why this store belongs to the purge at all: ``changed_files`` are repo-relative
    paths under ``kitty-specs/``, i.e. **mission slugs**, and for the 2026-07-27
    incident's population those slugs are client engagement names. WP12 gates the
    egress path and *retains* the frames it withholds; without this function an
    operator would purge the journal and the ledger, be told the project was erased,
    and still have those names sitting on disk.

    **The pre-fix population is attributed by store locality, and that is the
    decision T022 had to make.** WP12 added ``project_uuid`` to the frame
    *additively*, so frames written before it — precisely the set the incident
    produced — carry no such key and cannot be matched by uuid. They are still
    purgeable here, because this store is per-checkout rather than machine-global:
    ``.kittify/sync-state.json`` lives in the checkout whose commits wrote it
    (:func:`_sync_state_path`), and ``safe_commit`` calls :func:`emit_local_commit`
    with that same checkout's root, so an unattributable frame in project X's file is
    X's own content — its ``changed_files`` are paths in X's repository. Attributing
    it to X therefore cannot reach another project's entries, which is what keeps
    NFR-006's "0% of any other project's" true.

    The vouching is **checked, not assumed**: the identity-less bucket is in scope
    only when this checkout declares *project_uuid* as its own
    (:func:`_checkout_vouches_for`). A checkout that declares a different project, or
    declares none, vouches for nothing, and its unattributable frames stay for
    :func:`purge_all_pending_local_commits`. The rejected alternative was matching the
    mission slug inside ``changed_files``: the slug is not a project-scoped
    identifier, no project→slug mapping exists at purge time, and it would make the
    operator hand-type the client engagement name they are trying to erase — while
    still reducing, in the end, to this same locality argument.

    A blank *project_uuid* selects nothing. Sharper here than in the journal purge:
    :data:`IDENTITY_LESS_FRAME_KEY` *is* the empty string, so a selector that reached
    the matcher unstripped would silently vacuum the unattributable population.

    ``last_saas_confirmed_hash`` is deliberately left alone. It is the ack watermark,
    not a census key: clearing it would make already acknowledged frames eligible to
    send again. It holds a git hash of the operator's own checkout and no mission
    slug, so retaining it takes nothing away from FR-016's claim.

    **C-002**: this deletes, so it may only ever run as the operator's explicit act.
    Nothing in ``src/`` calls it from an unattended path — in particular
    :func:`flush_pending_local_commits`, which runs on every WebSocket connect,
    retains what it withholds instead of purging it.
    """
    target = str(project_uuid or "").strip()
    if not target:
        return _purge_frames(repo_root, selector="", scope_keys=frozenset(), dry_run=dry_run)

    vouches = _checkout_vouches_for(repo_root, target)
    scope = {target} | ({IDENTITY_LESS_FRAME_KEY} if vouches else set())
    return _purge_frames(
        repo_root,
        selector=target,
        scope_keys=frozenset(scope),
        dry_run=dry_run,
        unattributed_in_scope=vouches,
    )


def purge_all_pending_local_commits(
    repo_root: Path,
    *,
    dry_run: bool = True,
) -> PendingCommitPurgeResult:
    """Remove **every** queued frame from *repo_root*'s ``sync-state.json`` (FR-017).

    Dry-run by default, like every other selector. The confirmation FR-017 requires
    belongs to the operator-facing CLI, alongside the one already guarding the
    journal/ledger total purge: a second confirmation prompt per store would train the
    operator to type the token without reading it.

    **This store bounds ``--all`` differently from the other three, and a caller must
    not paper over that.** The journal, the ledger and the body queue are
    machine-global, so one call erases the machine. ``pending_local_commits`` is
    per-checkout ``LOCAL_RUNTIME`` state (``state/contract.py``:
    ``sync_local_commit_state``), so this clears *this* checkout's queue only —
    another checkout's frames live in another file this function never sees. Reporting
    a machine-wide "all frames purged" from one call would be a false attestation.
    """
    return _purge_frames(
        repo_root,
        selector="all",
        scope_keys=None,
        dry_run=dry_run,
        all_frames=True,
    )


# ---------------------------------------------------------------------------
# Internal helpers (mirrors invocation/propagator.py)
# ---------------------------------------------------------------------------


# ``_get_saas_client()`` used to live here and was deleted for #3030 FR-032: its only
# client source was the phantom ``token_manager._ws_client``, which ``src/`` never
# assigns, so it could only ever return ``None``. Its sole caller was
# ``emit_local_commit``'s immediate send, deleted with it. ``_send_event`` below
# stays — ``flush_pending_local_commits`` is a live sender and receives its client as
# a parameter.


def _send_event(client: Any, event_dict: dict[str, Any]) -> None:
    """Send *event_dict* via *client*.

    Uses ``asyncio.create_task`` when a loop is running, otherwise falls back to
    ``asyncio.run``.
    """
    import asyncio  # noqa: PLC0415

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = asyncio.create_task(client.send_event(event_dict))
            _PENDING_SEND_TASKS.add(task)
            task.add_done_callback(_PENDING_SEND_TASKS.discard)
            return
        loop.run_until_complete(client.send_event(event_dict))
    except RuntimeError:
        asyncio.run(client.send_event(event_dict))


# Keep scheduled tasks alive until completion (prevents premature GC).
_PENDING_SEND_TASKS: set[Any] = set()


# The census + purge names join this list now that WP08's ``sync purge`` command
# imports them, on the reasoning ``delivery/retention.py`` records for its own purge
# symbols: the symbol-level dead-code gate
# (``tests/architectural/test_no_dead_symbols.py``) is a shrink-only ratchet over
# ``__all__``, so a name goes in when it has a production caller and not before.
#
# ``IDENTITY_LESS_FRAME_KEY`` and ``PendingCommitPurgeResult`` stay off it: the CLI
# takes its own raw census of ``sync-state.json`` — deliberately, so its NFR-006
# differential does not share a read with the thing it measures — and consumes the
# result object without naming its type. They remain importable.
#
# ``sync/__init__``'s lazy re-exports are NOT extended here: that file belongs to
# another lane in flight, and the CLI imports from this module directly.
__all__ = [
    "SyncState",
    "census_pending_local_commits",
    "load_sync_state",
    "save_sync_state",
    "emit_local_commit",
    "flush_pending_local_commits",
    "purge_all_pending_local_commits",
    "purge_pending_local_commits",
    "record_local_commit_ack",
]
