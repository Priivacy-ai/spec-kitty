"""Delivery Target Registry & identity (WP04, IC-03; FR-002, FR-012, C-002).

A **Delivery Target** is one endpoint identity: a canonical URL hash plus
user/team scope, enforced by ``UNIQUE(url_hash, team_slug, user_email)``
(**C-002**). Identity inputs are derived from WP01's
:class:`~specify_cli.sync.target_authority.ResolvedSyncTarget` — never
re-resolved here (that would re-introduce the split-brain the mission kills).

Design decisions (documented per the WP's validation checklist):

* **Hash algorithm** — ``url_hash`` is the SHA-256 hexdigest (64 ASCII hex
  chars) of the canonical URL. It is a one-way digest; the URL is not
  recoverable from it.
* **Canonicalization** — :func:`canonicalize_url` lowercases scheme + host,
  IDNA/ASCII-encodes a non-ASCII host, drops the default port (``:443``/``:80``),
  strips a trailing path slash, and **drops query + fragment**. For an
  events-batch endpoint the path is identity-significant but query/fragment are
  not, so two cosmetic spellings of the same endpoint hash identically.
* **Empty-scope normalization** — a ``None`` and an empty-string ``team_slug``
  (or ``user_email``) both normalize to ``""`` so the same anonymous (pre-auth)
  endpoint never forks into two identities.
* **Deployment metadata is provenance, never identity** (**C-002**):
  ``server_instance_id``/``deployment_id``/``environment_name``/``git_sha`` are
  recorded on the identity row and updated in place on re-register. The identity
  key excludes every deployment field.
* **Advisory reset detection** (**FR-012**): :meth:`SqliteDeliveryTargetRegistry.detect_reset`
  compares the stored *stable* fields against incoming metadata. A changed
  stable field (``server_instance_id``/``environment_name``/``git_sha``) returns
  a :class:`~specify_cli.delivery.interfaces.ResetSignal`; a ``deployment_id``-only
  change is normal Upsun redeploy noise and returns ``None``. Detection is
  read-only — it does no I/O, no identity fork, and no SaaS ``/health`` call
  (IC-09, out of scope — C-004).

Per **C-001** nothing here imports ``sync/queue.py`` or ``specify_cli.events``;
the only inbound dependency is WP01's ``ResolvedSyncTarget`` value object,
imported under ``TYPE_CHECKING`` so the domain stays import-light.
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import replace
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

from specify_cli.core.time_utils import now_utc_iso
from specify_cli.delivery.interfaces import (
    DeliveryTarget,
    DeploymentMetadata,
    ResetSignal,
    TargetIdentity,
)

if TYPE_CHECKING:  # pragma: no cover - typing-only import (C-001: no runtime edge)
    from specify_cli.sync.target_authority import ResolvedSyncTarget

# All recorded deployment-metadata fields (provenance only — never identity).
_METADATA_FIELDS: tuple[str, ...] = (
    "server_instance_id",
    "deployment_id",
    "environment_name",
    "git_sha",
)

# Fields whose change signals a possible environment reset (FR-012). Crucially
# excludes ``deployment_id``: Upsun re-stamps it on every push, so a
# ``deployment_id``-only change is redeploy noise, not a reset.
_STABLE_RESET_FIELDS: tuple[str, ...] = (
    "server_instance_id",
    "environment_name",
    "git_sha",
)

_RESET_RECOMMENDATION = (
    "Deployment identity changed under a stable URL; the target may have been "
    "reset. Consider re-draining retained events to this target."
)

# Explicit ASCII allowlist for human-readable identifier components (charter
# Identifier Safety). Compiled with ``re.ASCII`` so it never falls back to the
# Unicode ``\w`` semantics that would let accented input leak through.
_NON_IDENTIFIER_CHARS = re.compile(r"[^A-Za-z0-9_]", re.ASCII)

_DEFAULT_PORTS = {"https": 443, "http": 80}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS delivery_targets (
    target_id          TEXT PRIMARY KEY,
    canonical_url      TEXT NOT NULL,
    url_hash           TEXT NOT NULL,
    team_slug          TEXT NOT NULL,
    user_email         TEXT NOT NULL,
    server_instance_id TEXT,
    deployment_id      TEXT,
    environment_name   TEXT,
    git_sha            TEXT,
    first_seen_at      TEXT NOT NULL,
    last_seen_at       TEXT NOT NULL,
    UNIQUE(url_hash, team_slug, user_email)
);
"""


class InvalidTargetUrlError(ValueError):
    """Raised when a target URL is empty or has no scheme/host to canonicalize."""


# ---------------------------------------------------------------------------
# Pure helpers (no I/O) — T022 canonicalization + hashing, identifier safety
# ---------------------------------------------------------------------------


def _ascii_token(value: str) -> str:
    """Sanitize *value* to an ASCII-only deterministic token (Identifier Safety).

    Uses an explicit ``[A-Za-z0-9_]`` allowlist (``re.ASCII``); every other code
    point — including accented Latin — is replaced with ``_`` so the result is
    always ``.isascii()``.
    """
    return _NON_IDENTIFIER_CHARS.sub("_", value)


def _sha256_hex(text: str) -> str:
    """Return the SHA-256 hexdigest of *text* (always ASCII)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()  # noqa: TID251 - production raw SHA-256 owner (delivery-target identity digest, not the charter freshness hash)


def _canonical_host(host: str) -> str:
    """Lowercase *host* and guarantee an ASCII rendering (IDNA, then escape).

    A non-ASCII host (IDN) is IDNA-encoded to its punycode form; if that fails
    the host is sanitized via the ASCII allowlist so the canonical URL — a
    storage-facing identifier — is always ``.isascii()``.
    """
    lowered = host.lower()
    if lowered.isascii():
        return lowered
    try:
        return lowered.encode("idna").decode("ascii")
    except (UnicodeError, ValueError):
        return _ascii_token(lowered)


def canonicalize_url(raw_url: str) -> str:
    """Canonicalize an endpoint URL deterministically (T022). Pure, no I/O.

    Lowercases scheme + host, ASCII-encodes a non-ASCII host, drops the default
    port and a trailing path slash, and drops query + fragment. Raises
    :class:`InvalidTargetUrlError` on empty/malformed input rather than hashing
    garbage.
    """
    if not raw_url or not raw_url.strip():
        raise InvalidTargetUrlError("target URL must be a non-empty string")
    parts = urlsplit(raw_url.strip())
    if not parts.scheme or not parts.hostname:
        raise InvalidTargetUrlError(f"target URL is missing scheme or host: {raw_url!r}")
    scheme = parts.scheme.lower()
    netloc = _canonical_host(parts.hostname)
    try:
        port = parts.port
    except ValueError as exc:  # malformed port component
        raise InvalidTargetUrlError(f"target URL has an invalid port: {raw_url!r}") from exc
    if port is not None and _DEFAULT_PORTS.get(scheme) != port:
        netloc = f"{netloc}:{port}"
    path = parts.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, "", ""))


def compute_url_hash(canonical_url: str) -> str:
    """Return the one-way SHA-256 ``url_hash`` of an already-canonical URL."""
    return _sha256_hex(canonical_url)


def _normalize_scope(value: str | None) -> str:
    """Normalize a scope value: ``None`` and ``""`` both collapse to ``""`` (C-002)."""
    return value or ""


def _derive_target_id(identity: TargetIdentity) -> str:
    """Build a deterministic ASCII surrogate id for *identity*.

    The id embeds a sanitized scope token (Identifier Safety) plus a digest of
    the full identity tuple, so distinct identities never collide and the result
    is always ``.isascii()`` even for accented scope input.
    """
    digest = _sha256_hex(
        "\x00".join((identity.url_hash, identity.team_slug, identity.user_email))
    )[:32]
    scope = _ascii_token(identity.team_slug) or "anon"
    return f"tgt_{scope}_{digest}"


def _select_metadata(deployment_metadata: DeploymentMetadata | None) -> dict[str, str | None]:
    """Project *deployment_metadata* onto the known fields that are present.

    Only keys present in the incoming mapping are returned, so a partial update
    overwrites just those fields and leaves the rest of the stored provenance
    intact (T023: partial metadata is storable).
    """
    if not deployment_metadata:
        return {}
    return {
        field: deployment_metadata[field]
        for field in _METADATA_FIELDS
        if field in deployment_metadata
    }


def _stable_changes(
    stored: DeliveryTarget, incoming: dict[str, str | None]
) -> tuple[str, ...]:
    """Return the stable fields that meaningfully changed (FR-012).

    A field counts as changed only when both the stored and incoming values are
    present (non-``None``) and differ — so first-appearing or disappearing
    metadata never trips a false reset. ``deployment_id`` is excluded entirely.
    """
    changed: list[str] = []
    for field in _STABLE_RESET_FIELDS:
        new_value = incoming.get(field)
        old_value = getattr(stored, field)
        if new_value is None or old_value is None:
            continue
        if new_value != old_value:
            changed.append(field)
    return tuple(changed)


# ---------------------------------------------------------------------------
# SQLite-backed registry (T021/T023/T024)
# ---------------------------------------------------------------------------


def _row_to_target(row: sqlite3.Row) -> DeliveryTarget:
    """Build a :class:`DeliveryTarget` from a ``delivery_targets`` row."""
    identity = TargetIdentity(
        url_hash=_as_str(row["url_hash"]),
        team_slug=_as_str(row["team_slug"]),
        user_email=_as_str(row["user_email"]),
    )
    return DeliveryTarget(
        target_id=_as_str(row["target_id"]),
        canonical_url=_as_str(row["canonical_url"]),
        identity=identity,
        server_instance_id=_as_opt_str(row["server_instance_id"]),
        deployment_id=_as_opt_str(row["deployment_id"]),
        environment_name=_as_opt_str(row["environment_name"]),
        git_sha=_as_opt_str(row["git_sha"]),
        first_seen_at=_as_str(row["first_seen_at"]),
        last_seen_at=_as_str(row["last_seen_at"]),
    )


def _as_str(value: object) -> str:
    return str(value)


def _as_opt_str(value: object) -> str | None:
    return None if value is None else str(value)


class SqliteDeliveryTargetRegistry:
    """SQLite-backed :class:`~specify_cli.delivery.interfaces.DeliveryTargetRegistry`.

    Pass ``":memory:"`` (default) for an isolated in-process registry or a file
    path for a persistent one. Implements the C-002 identity model and FR-012
    advisory reset detection.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # -- lifecycle ---------------------------------------------------------
    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> SqliteDeliveryTargetRegistry:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- identity helpers --------------------------------------------------
    def _identity(self, url: str, team_slug: str | None, user_email: str | None) -> TargetIdentity:
        canonical = canonicalize_url(url)
        return TargetIdentity(
            url_hash=compute_url_hash(canonical),
            team_slug=_normalize_scope(team_slug),
            user_email=_normalize_scope(user_email),
        )

    # -- registry surface --------------------------------------------------
    def register(
        self,
        *,
        url: str,
        team_slug: str | None,
        user_email: str | None,
        deployment_metadata: DeploymentMetadata | None = None,
    ) -> DeliveryTarget:
        """Idempotently register a target on its ``(url_hash, scope)`` identity.

        Canonicalizes *url*, normalizes scope, and upserts on the UNIQUE identity
        key. A second register of the same identity updates provenance + the
        ``last_seen_at`` timestamp on the existing row (no fork). Returns the
        stored :class:`DeliveryTarget`.
        """
        canonical = canonicalize_url(url)
        identity = TargetIdentity(
            url_hash=compute_url_hash(canonical),
            team_slug=_normalize_scope(team_slug),
            user_email=_normalize_scope(user_email),
        )
        now = now_utc_iso()
        provided = _select_metadata(deployment_metadata)
        existing = self.get(identity.url_hash, identity.team_slug, identity.user_email)
        if existing is None:
            target = DeliveryTarget(
                target_id=_derive_target_id(identity),
                canonical_url=canonical,
                identity=identity,
                server_instance_id=provided.get("server_instance_id"),
                deployment_id=provided.get("deployment_id"),
                environment_name=provided.get("environment_name"),
                git_sha=provided.get("git_sha"),
                first_seen_at=now,
                last_seen_at=now,
            )
            self._insert(target)
            return target
        merged = {field: getattr(existing, field) for field in _METADATA_FIELDS}
        merged.update(provided)
        target = replace(existing, last_seen_at=now, **merged)
        self._update_provenance(target)
        return target

    def register_from_resolved(
        self,
        resolved: ResolvedSyncTarget,
        *,
        deployment_metadata: DeploymentMetadata | None = None,
    ) -> DeliveryTarget:
        """Register the identity carried by WP01's :class:`ResolvedSyncTarget`.

        Derives the canonical URL from ``resolved_server_url`` and the scope from
        ``team_slug`` and ``user_id`` (an email in practice). This is the only
        sanctioned identity-input source (C-007/SC-008: no second resolver).
        """
        return self.register(
            url=resolved.resolved_server_url,
            team_slug=resolved.team_slug,
            user_email=resolved.user_id,
            deployment_metadata=deployment_metadata,
        )

    def get(
        self, url_hash: str, team_slug: str | None, user_email: str | None
    ) -> DeliveryTarget | None:
        """Return the target for a normalized identity, or ``None`` if unknown."""
        cursor = self._conn.execute(
            "SELECT * FROM delivery_targets "
            "WHERE url_hash = ? AND team_slug = ? AND user_email = ?",
            (url_hash, _normalize_scope(team_slug), _normalize_scope(user_email)),
        )
        row = cursor.fetchone()
        return None if row is None else _row_to_target(row)

    def detect_reset(
        self,
        *,
        url: str,
        team_slug: str | None,
        user_email: str | None,
        new_deployment_metadata: DeploymentMetadata | None,
    ) -> ResetSignal | None:
        """Advisory reset detection on deployment-metadata change (**FR-012**).

        Read-only: compares the stored stable fields for the matched identity
        against *new_deployment_metadata*. Returns a :class:`ResetSignal` when a
        stable field changed, else ``None`` (including the first-registration,
        no-prior-metadata, absent-incoming, and ``deployment_id``-only cases).
        Never forks identity, mutates state, or calls a ``/health`` endpoint.
        """
        identity = self._identity(url, team_slug, user_email)
        stored = self.get(identity.url_hash, identity.team_slug, identity.user_email)
        if stored is None:
            return None
        incoming = _select_metadata(new_deployment_metadata)
        changed = _stable_changes(stored, incoming)
        if not changed:
            return None
        previous = {field: getattr(stored, field) for field in changed}
        current = {field: incoming.get(field) for field in changed}
        return ResetSignal(
            target_id=stored.target_id,
            changed_fields=changed,
            previous=previous,
            current=current,
            recommendation=_RESET_RECOMMENDATION,
        )

    def list_targets(self) -> list[DeliveryTarget]:
        """Return every registered target (ordering: first-seen, then id)."""
        cursor = self._conn.execute(
            "SELECT * FROM delivery_targets ORDER BY first_seen_at, target_id"
        )
        return [_row_to_target(row) for row in cursor.fetchall()]

    # -- persistence -------------------------------------------------------
    def _insert(self, target: DeliveryTarget) -> None:
        self._conn.execute(
            "INSERT INTO delivery_targets ("
            "target_id, canonical_url, url_hash, team_slug, user_email, "
            "server_instance_id, deployment_id, environment_name, git_sha, "
            "first_seen_at, last_seen_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                target.target_id,
                target.canonical_url,
                target.url_hash,
                target.team_slug,
                target.user_email,
                target.server_instance_id,
                target.deployment_id,
                target.environment_name,
                target.git_sha,
                target.first_seen_at,
                target.last_seen_at,
            ),
        )
        self._conn.commit()

    def _update_provenance(self, target: DeliveryTarget) -> None:
        self._conn.execute(
            "UPDATE delivery_targets SET "
            "server_instance_id = ?, deployment_id = ?, environment_name = ?, "
            "git_sha = ?, last_seen_at = ? WHERE target_id = ?",
            (
                target.server_instance_id,
                target.deployment_id,
                target.environment_name,
                target.git_sha,
                target.last_seen_at,
                target.target_id,
            ),
        )
        self._conn.commit()
