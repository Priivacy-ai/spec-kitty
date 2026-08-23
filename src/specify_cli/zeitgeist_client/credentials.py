"""Checkout/auth: local bearer-credential storage (Z1.md §3.2 item 7).

``<runtime_state_root>/zeitgeist-credentials`` — a sibling of, deliberately
NOT sharing, ``tracker/credentials.py``'s ``<root>/credentials`` file
(Z1.md decision 3: different trust domains, coupling them would make Z1-T1 a
co-owner of an unrelated file format). TOML, ``filelock``-guarded (decision
4: the existing declared-but-unused dependency, ``pyproject.toml:85``,
rather than tracker's hand-rolled ``fcntl``/``msvcrt``).

Keyed by canonical ``repo`` (from ``repo_identity.identity()``, Z6-C), so two
projects on one machine hold independent tokens (N-row precedent: two repos,
two entries). This module's own ``store()``/``load()``/``revoke()`` still
take ``repo`` as a plain caller-supplied string — a general storage primitive
independent of how the caller derived it; the not-yet-implemented CLI
adapter (see ``docs/plans/zeitgeist-client-wp01-remaining.md``) is expected
to pass ``repo_identity.identity(cwd).repo`` rather than a literal.

This module owns only the *storage* primitive. The network canary-offer
probe (``spec-kitty zeitgeist checkout <relay-url>``, "refresh re-derives",
"revoke issues session.revoke then deletes") is the CLI adapter's job — not
yet implemented (see ``docs/plans/zeitgeist-client-wp01-remaining.md``) —
and will call ``store()``/``revoke()`` here as its last step. ``revoke()``
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
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kernel.clock import now_utc_iso

import tomllib
import tomli_w
from filelock import FileLock

from kernel.paths import get_runtime_state_root

CREDENTIALS_FILENAME = "zeitgeist-credentials"
_LOCK_SUFFIX = ".lock"


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


def credentials_path() -> Path:
    return get_runtime_state_root() / CREDENTIALS_FILENAME


def _lock_path() -> Path:
    return credentials_path().with_suffix(credentials_path().suffix + _LOCK_SUFFIX)


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
    path = credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("wb") as fh:
        tomli_w.dump(data, fh)
    tmp_path.replace(path)  # atomic on POSIX and Windows (same volume)


def store(
    *,
    repo: str,
    relay_url: str,
    token: str,
    token_kind: str,
    capability_credential: str | None = None,
) -> None:
    if not repo:
        raise ValueError("repo must be non-empty")
    if not relay_url:
        raise ValueError("relay_url must be non-empty")
    if not token:
        raise ValueError("token must be non-empty")
    if capability_credential is not None and not capability_credential:
        raise ValueError("capability_credential must be non-empty when provided")
    lock = FileLock(str(_lock_path()))
    with lock:
        data = _read_all()
        entry: dict[str, str] = {
            "relay_url": relay_url,
            "token": token,
            "token_issued_at": now_utc_iso(),  # kernel.clock single door (M2 canonical integration)
            "token_kind": token_kind,
        }
        # FIX-M2-15: omitted entirely (never written as "") when not
        # provided -- `load()` reads a missing key back as `None`, TOML has
        # no null literal to round-trip instead.
        if capability_credential is not None:
            entry["capability_credential"] = capability_credential
        data[repo] = entry
        _write_all(data)


def load(*, repo: str) -> StoredCredential | None:
    lock = FileLock(str(_lock_path()))
    with lock:
        data = _read_all()
    entry = data.get(repo)
    if entry is None:
        return None
    return StoredCredential(
        relay_url=entry["relay_url"],
        token=entry["token"],
        token_issued_at=entry["token_issued_at"],
        token_kind=entry["token_kind"],
        capability_credential=entry.get("capability_credential"),
    )


def revoke(*, repo: str) -> None:
    """Delete the local token for ``repo``. Never raises on a missing entry
    — revoking an already-revoked/never-checked-out repo is a no-op, not an
    error (N10: a subsequent status() must report "not checked out", never a
    stale token, regardless of whether the caller's network canary offer
    against the relay succeeded)."""
    lock = FileLock(str(_lock_path()))
    with lock:
        data = _read_all()
        if repo in data:
            del data[repo]
            _write_all(data)
