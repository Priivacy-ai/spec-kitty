"""Checkout/auth: local bearer-credential storage (Z1.md §3.2 item 7).

``<runtime_state_root>/zeitgeist-credentials`` — a sibling of, deliberately
NOT sharing, ``tracker/credentials.py``'s ``<root>/credentials`` file
(Z1.md decision 3: different trust domains, coupling them would make Z1-T1 a
co-owner of an unrelated file format). TOML, ``filelock``-guarded (decision
4: the existing declared-but-unused dependency, ``pyproject.toml:85``,
rather than tracker's hand-rolled ``fcntl``/``msvcrt``).

Keyed by the hosted identity :func:`resolution.store_key` derives from the
checkout's origin remote — ``host/owner/repo``, e.g. ``github.com/acme/widget``
(spec-kitty#129/#132) — so two projects, or two differently-hosted repos
sharing a name, hold independent tokens. The key is still a plain
caller-supplied string to this module: storage stays independent of how the
caller derived it. But a key with no ``/`` — the pre-#132 bare-NAME shape —
is refused on every door: ``store()``/``store_negative()`` raise,
``load()``/``load_negative()`` read as "nothing stored", and ``revoke()`` is
a no-op, while every successful write prunes bare-name entries already on
disk (spec-kitty#137: #132 deliberately abandoned those entries rather than
migrate them, so a live-shaped bearer left under an old name must never again
answer a lookup, and should not outlive the next legitimate write). Callers
derive the key with :func:`resolution.store_key_for_checkout` (from cwd) or
:func:`resolution.parse_store_key` (from user input).

This module owns only the *storage* primitive. The network canary-offer
probe (``spec-kitty zeitgeist checkout <relay-url>``, "refresh re-derives",
"revoke issues session.revoke then deletes") is the CLI adapter's job — not
yet implemented (see ``docs/plans/zeitgeist-client-wp01-remaining.md``) —
and will call ``store()``/``revoke()`` here as its last step.
``resolution.py`` (E3 credential resolution) is the other consumer: it mints
through Team Kitty's capability endpoint and persists what comes back via
``store()`` here. ``revoke()``
here is the client-side wipe half only:
"never fails to wipe locally even if the offer drops" (N10) is satisfied
trivially by revoke() never attempting network I/O at all.

This module never imports ``specify_cli.auth.*`` (the SaaS OAuth credential
system Z1's criterion explicitly forbids reusing, Z1.md §2.6/N22) — this is
the local, shared-team, self-hosted-relay bearer credential Z1 owns.

FIX-M2-15: ``StoredCredential``/``store()`` gained a second, optional
field, ``capability_credential`` — a real per-team relay
(``ZEITGEIST_TOKEN``/``ZEITGEIST_CAPABILITY_KEY`` minted as two
independent secrets, e.g. by ``apps.live_capability.provisioning_docker``)
needs a per-actor ``X-Zeitgeist-Capability`` JWT distinct from ``token``,
the deployment-wide ``Authorization`` bearer; see ``transport.py``'s
``ClientConfig``/``filtered_stream.py``'s ``TeamStreamConfig`` for the
identical field and the identical "``None`` falls back to the other
credential" precedence both apply. Every existing on-disk config (no
``capability_credential`` key at all) round-trips unchanged: ``load()``
reads a missing key as ``None``, and every caller downstream already
treats ``None`` as "use ``token`` for both gates" — the exact single-
credential behaviour this store always had.

E3 credential resolution (``resolution.py``) adds two more optional aspects,
both round-trip compatible with every entry already on disk:

- ``expires_at`` — an optional ISO stamp recording when the stored
  credential stops working. ``store()`` writes it only when the caller has
  one (a capability mint reports one; a manual checkout never did), and
  ``load()`` reads a missing key as ``None``. This module never *interprets*
  the stamp — expiry policy is the caller's, the store just keeps the bytes.
- negative entries — a repo Team Kitty will not issue a capability for
  (no admitted team) is remembered under its key with
  ``token_kind = "not_admitted"``, so the next transition does not re-ask
  the network for the same no. A negative entry deliberately does NOT have
  ``relay_url``/``token`` keys, so :func:`load` reads it as ``None`` — every
  existing caller sees exactly "not checked out" — and it is written and
  read only through :func:`store_negative`/:func:`load_negative`. Storing a
  negative answer replaces any positive entry for that repo: a mint denial
  after a stored credential means the stored credential can no longer be
  valid.

Squad finding on spec-kitty#123: the store key was the bare repo NAME, which
two differently-hosted repos can share, so ``store()``/``load()`` also
carry optional ``host``/``repo_slug`` — the full identity a credential was
minted for. This module stores and returns them verbatim; revalidating a
cache hit against the checkout it is about to be used for is
``resolution.py``'s job (:func:`resolution._same_scope`), not this
storage primitive's. Both round-trip as ``None`` for every entry stored
before this fix, same as ``expires_at``. And since spec-kitty#129,
``resolution.resolve_credentials`` derives its key from that same pair
(:func:`resolution.store_key`, ``host/owner/repo``) instead of the bare
name, so same-named repos no longer share an entry at all.

EXPERIMENTAL-spec-kitty#10 adds one last optional aspect, ``team`` — the
slug of the team whose admission pre-flight answered "admitted" just before
this capability was minted (``resolution._resolve`` has it in hand and
would otherwise drop it). ``spec-kitty routes`` displays it; nothing else
reads it. Like every aspect above it round-trips as ``None`` for entries
stored before it existed (a manual checkout never learns a team).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from kernel.clock import now_utc_iso

import tomllib
import tomli_w
from filelock import FileLock

from kernel.paths import get_runtime_state_root

CREDENTIALS_FILENAME = "zeitgeist-credentials"
_LOCK_SUFFIX = ".lock"

# E3 resolution: the token_kind a negative (no-admitted-team) answer is
# stored under. A negative entry carries no relay_url/token at all, so
# load() reports it as None and only load_negative() ever hands it back.
# noqa S105: a TOML discriminator literal, not a credential.
NEGATIVE_TOKEN_KIND = "not_admitted"  # noqa: S105


def _is_legacy_name_key(repo: str) -> bool:
    """Whether ``repo`` is a pre-#132 bare-NAME store key, which this module
    no longer serves. Since #132 every writer keys by
    :func:`resolution.store_key`'s ``host/owner/repo``, and no such key can
    lack the ``/`` — even a degenerate empty-host key is ``/owner/repo`` —
    so "no slash" identifies exactly the abandoned shape."""
    return "/" not in repo


@dataclass(frozen=True)
class StoredCredential:
    relay_url: str
    token: str
    token_issued_at: str
    token_kind: str
    # FIX-M2-15: the SEPARATE X-Zeitgeist-Capability credential -- see
    # module docstring. `None` means "single-credential checkout" (every
    # entry stored before this fix, and every self-hosted deployment that
    # still hands out one value): callers fall back to `token`.
    capability_credential: str | None = None
    # E3 resolution: when the mint reported an expiry, the ISO stamp it gave
    # -- verbatim, uninterpreted; expiry policy is the caller's. `None` for
    # every entry whose issuer did not report one (all entries stored before
    # this field existed), which callers treat as "no recorded expiry".
    expires_at: str | None = None
    # squad finding on #123: the store key is the bare repo NAME
    # (`repo_identity.repo_name`), which two differently-hosted repos can
    # share (a same-name hostile checkout would otherwise read a cached
    # admitted credential minted for someone else's repo). `host`/
    # `repo_slug` record the full identity `resolution.py` minted this
    # credential for, so a caller can revalidate a cache hit against the
    # checkout it is about to use it for. `None` for every entry stored
    # before this field existed (a manual `zeitgeist checkout`, or any
    # pre-fix mint) -- callers treat that as "no scope recorded", the same
    # backward-compatible reading `expires_at` already gets.
    host: str | None = None
    repo_slug: str | None = None
    # #10: the admitting team's slug, recorded verbatim from the admission
    # pre-flight that preceded this mint. `None` for every entry stored
    # before this field existed, and for a manual checkout (no admission
    # was ever asked).
    team: str | None = None


@dataclass(frozen=True)
class NegativeEntry:
    """The stored answer to "is this repo admitted anywhere?" being no.
    ``expires_at`` is verbatim ISO, uninterpreted here."""

    reason: str
    stored_at: str | None = None
    expires_at: str | None = None


def credentials_path() -> Path:
    return get_runtime_state_root() / CREDENTIALS_FILENAME


def _lock_path() -> Path:
    return credentials_path().with_suffix(credentials_path().suffix + _LOCK_SUFFIX)


def _locked() -> FileLock:
    """The store's lock, taken only after the state root exists owner-only.

    Everything in this module goes through one lock, and filelock creates
    missing parent directories *itself* on acquire — at the ambient umask
    (0o755 measured), which would otherwise always beat any mode passed to
    ``_write_all``'s later ``mkdir``. Creating the root here first, at
    0o700, is what actually makes the directory holding the tokens
    owner-only.
    """
    credentials_path().parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    return FileLock(str(_lock_path()))


def _read_all() -> dict[str, dict[str, str]]:
    path = credentials_path()
    if not path.exists():
        return {}
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except (tomllib.TOMLDecodeError, OSError):
        # A corrupt/unreadable file is treated as "nothing stored" rather
        # than raised — a checkout-storage read failure must never crash a
        # caller that only wants to know "am I checked out". Writers still
        # overwrite it cleanly (atomic replace below).
        return {}


def _write_all(data: dict[str, dict[str, str]]) -> None:
    """Atomically replace the store. Every entry this file holds is a
    secret (relay bearer, per-actor capability JWT), so the write is
    owner-only regardless of the process's umask — E3 turned this store
    from opt-in into something auto-populated on every status transition,
    so "the user happened to have a loose umask" would otherwise publish
    every minted token to group/other. (The directory's mode is
    :func:`_locked`'s job.)

    Every write also prunes pre-#132 bare-name entries (spec-kitty#137):
    they can no longer be written, and none can be read back, but dropping
    them here means a live-shaped bearer left under an abandoned name does
    not outlive the next legitimate write."""
    for stale in [key for key in data if _is_legacy_name_key(key)]:
        del data[stale]
    path = credentials_path()
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as fh:
        tomli_w.dump(data, fh)
    # os.open's mode only applies at creation: re-assert in case a looser
    # temp file survived an earlier crash mid-write.
    os.chmod(tmp_path, 0o600)
    tmp_path.replace(path)  # atomic on POSIX and Windows (same volume)


def store(
    *,
    repo: str,
    relay_url: str,
    token: str,
    token_kind: str,
    capability_credential: str | None = None,
    expires_at: str | None = None,
    host: str | None = None,
    repo_slug: str | None = None,
    team: str | None = None,
) -> None:
    if not repo:
        raise ValueError("repo must be non-empty")
    if not relay_url:
        raise ValueError("relay_url must be non-empty")
    if not token:
        raise ValueError("token must be non-empty")
    if capability_credential is not None and not capability_credential:
        raise ValueError("capability_credential must be non-empty when provided")
    if expires_at is not None and not expires_at:
        raise ValueError("expires_at must be non-empty when provided")
    if host is not None and not host:
        raise ValueError("host must be non-empty when provided")
    if repo_slug is not None and not repo_slug:
        raise ValueError("repo_slug must be non-empty when provided")
    if team is not None and not team:
        raise ValueError("team must be non-empty when provided")
    if _is_legacy_name_key(repo):
        raise ValueError("repo must be a host/owner/repo credential-store key (resolution.store_key), not a bare repo name")
    lock = _locked()
    with lock:
        data = _read_all()
        entry: dict[str, str] = {
            "relay_url": relay_url,
            "token": token,
            "token_issued_at": now_utc_iso(),  # kernel.clock single door (M2 canonical integration)
            "token_kind": token_kind,
        }
        # FIX-M2-15 / E3 resolution: omitted entirely (never written as "")
        # when not provided -- `load()` reads a missing key back as `None`,
        # TOML has no null literal to round-trip instead.
        if capability_credential is not None:
            entry["capability_credential"] = capability_credential
        if expires_at is not None:
            entry["expires_at"] = expires_at
        if host is not None:
            entry["host"] = host
        if repo_slug is not None:
            entry["repo_slug"] = repo_slug
        if team is not None:
            entry["team"] = team
        data[repo] = entry
        _write_all(data)


def store_negative(*, repo: str, reason: str = "", expires_at: str | None = None) -> None:
    """Store a "no team admits this repo" answer under ``repo``'s key.

    Replaces whatever the key held (positive credential included): an
    admission/mint denial after a stored credential means that stored
    credential can no longer be valid, and keeping it would only earn 403s.
    The negative answer carries no ``relay_url``/``token``, so every
    :func:`load` caller sees plain "not checked out".

    ``reason`` is the denial reason verbatim (diagnostic only); ``expires_at``
    is the caller's own TTL stamp, uninterpreted here.
    """
    if not repo:
        raise ValueError("repo must be non-empty")
    if _is_legacy_name_key(repo):
        raise ValueError("repo must be a host/owner/repo credential-store key (resolution.store_key), not a bare repo name")
    lock = _locked()
    with lock:
        data = _read_all()
        entry: dict[str, str] = {
            "token_kind": NEGATIVE_TOKEN_KIND,
            "token_issued_at": now_utc_iso(),  # kernel.clock single door
            "reason": reason,
        }
        if expires_at is not None:
            entry["expires_at"] = expires_at
        data[repo] = entry
        _write_all(data)


def load(*, repo: str) -> StoredCredential | None:
    if _is_legacy_name_key(repo):
        return None
    lock = _locked()
    with lock:
        data = _read_all()
    entry = data.get(repo)
    if entry is None:
        return None
    # A negative answer (store_negative) shares the key but has no
    # relay_url/token -- to load() it is exactly "not checked out".
    try:
        return StoredCredential(
            relay_url=entry["relay_url"],
            token=entry["token"],
            token_issued_at=entry["token_issued_at"],
            token_kind=entry["token_kind"],
            capability_credential=entry.get("capability_credential"),
            expires_at=entry.get("expires_at"),
            host=entry.get("host"),
            repo_slug=entry.get("repo_slug"),
            team=entry.get("team"),
        )
    except KeyError:
        return None


def load_negative(*, repo: str) -> NegativeEntry | None:
    """The stored negative answer for ``repo``, or ``None`` when there is
    none (including when the key holds a positive credential, or when
    nothing is stored at all). The caller owns the expiry decision. A bare
    pre-#132 name reads as "nothing stored", like :func:`load`."""
    if _is_legacy_name_key(repo):
        return None
    lock = _locked()
    with lock:
        data = _read_all()
    entry = data.get(repo)
    if entry is None or entry.get("token_kind") != NEGATIVE_TOKEN_KIND:
        return None
    return NegativeEntry(
        reason=entry.get("reason", ""),
        stored_at=entry.get("token_issued_at"),
        expires_at=entry.get("expires_at"),
    )


def revoke(*, repo: str) -> None:
    """Delete the local token for ``repo``. Never raises on a missing entry
    — revoking an already-revoked/never-checked-out repo is a no-op, not an
    error (N10: a subsequent status() must report "not checked out", never a
    stale token, regardless of whether the caller's network canary offer
    against the relay succeeded). A bare pre-#132 name is the same no-op:
    nothing servable lives under such a key any more, so there is nothing
    to wipe."""
    if _is_legacy_name_key(repo):
        return
    lock = _locked()
    with lock:
        data = _read_all()
        if repo in data:
            del data[repo]
            _write_all(data)
