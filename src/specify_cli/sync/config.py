"""Sync configuration management.

Target authority (WP02, contract §1): ``get_server_url`` / ``set_server_url``
are the **config-file accessors** the canonical resolver consumes — they read
and write ``[sync].server_url`` only and never apply env precedence. Callers
that need the *live runtime target* must obtain a
:class:`~specify_cli.sync.target_authority.ResolvedSyncTarget` via
:meth:`SyncConfig.resolve_runtime_target` (which folds in ``SPEC_KITTY_SAAS_URL``
precedence and derives the queue scope) rather than treating the raw
``get_server_url`` value as the target.
"""
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import toml

from specify_cli.core.atomic import atomic_write
from specify_cli.paths import get_runtime_root

from .queue import DEFAULT_MAX_QUEUE_SIZE

if TYPE_CHECKING:
    from .target_authority import ResolvedSyncTarget


class BackgroundDaemonPolicy(StrEnum):
    """Policy controlling how the background sync daemon is started."""

    AUTO = "auto"
    MANUAL = "manual"


_BACKGROUND_DAEMON_VALUES: dict[str, BackgroundDaemonPolicy] = {
    "auto": BackgroundDaemonPolicy.AUTO,
    "manual": BackgroundDaemonPolicy.MANUAL,
}


#: The **whole** fault vocabulary, declared once and shared by both producers
#: (``sync/config.py`` and ``sync/consent.py``) — #3030 C-003.
#:
#: Until 2026-07-30 the two modules used the same two tokens for different states, one
#: module apart: ``config.py`` tagged a TOML *syntax* error ``unparseable`` and an
#: ``OSError`` ``unreadable``, while ``consent.py`` tagged an *open-or-parse* failure
#: ``unreadable`` and a *non-mapping top level* ``unparseable``. So ``unreadable`` meant
#: "could not open" on one surface and "could not open **or** parse" on the other, and
#: ``unparseable`` meant "bad syntax" on one and "parsed fine, wrong shape" on the
#: other. It had already produced a false operator message — ``sync doctor`` advised
#: *"it parsed, but its top level is not a mapping"* over a ``not valid TOML`` fault —
#: and the wrong text passed the suite, because an ``or`` across two acceptable
#: wordings let either satisfy the assertion.
#:
#: **Four kinds, not three.** The set is cut by *the operator action that resolves the
#: fault*, and no two of these share one:
#:
#: * ``unreadable``  — the file could not be opened at all. Fix its mode or ownership.
#: * ``unparseable`` — it opened, and its syntax does not parse. Repair the syntax.
#: * ``wrong_shape`` — it parsed, and its top level is not a mapping (a list, a bare
#:   scalar, a merge-conflict marker). Make the document a mapping.
#: * ``unusable``    — the shape is fine and a *field* holds a value that cannot be
#:   understood as that field (#3030 FR-027). Correct that value.
#:
#: Three would mean collapsing a pair. Collapsing the first two is what the old
#: ``consent.py`` did, and it forced the doctor's ``unreadable`` advice to name two
#: remedies — "a permission error means fix the mode; a parse error means repair the
#: syntax" — so it was half wrong for every reader. Collapsing the middle two is the
#: divergence itself: "your YAML has a syntax error" and "your YAML is valid and its
#: top level is a list" are different edits to different bytes.
#:
#: ``config.py`` mints only three of the four: TOML's top level is a table by
#: construction, so ``toml.load`` cannot return a non-mapping and a ``wrong_shape``
#: branch here would be unreachable code asserting a state that cannot occur.
#: ``config.py`` keeps both of its original tokens with their original meanings — they
#: were already the coherent pair — and ``consent.py`` moved onto them.
CONFIG_FAULT_KINDS: tuple[str, ...] = (
    "unreadable",
    "unparseable",
    "wrong_shape",
    "unusable",
)


@dataclass(frozen=True)
class ConfigReadFault:
    """Why a config file could not be read (#3030 FR-020).

    Carried, never raised. ``kind`` is a stable token for programmatic handling, drawn
    from :data:`CONFIG_FAULT_KINDS`, which declares the vocabulary and the reasoning
    for its size; ``detail`` names the file and the underlying error, because an
    operator told "consent is undetermined" with no path cannot act.

    Deliberately one type shared by both producers rather than a vocabulary per
    module: two modules independently deciding what a broken config means is how this
    defect class regenerates (C-003), and it is exactly what happened to the two
    file-level tokens before they were unified.

    A **missing** file is not a fault and produces ``None`` — absence of a record is a
    legitimate, common state that denies under FR-002, and collapsing it into this
    would bury the ordinary case under a fault nobody has.
    """

    kind: str
    detail: str


class ConfigNotReadableError(RuntimeError):
    """A write refused because the existing config could not be read (#3030).

    Every setter on :class:`SyncConfig` is a whole-file read-modify-write over
    :meth:`SyncConfig._load`, which returns ``{}`` for a file it cannot read. Writing
    from that ``{}`` re-emits the file from an empty document, so a single unrelated
    write discards every other project's consent record — measured, on seven of the
    eight setters, including ``set_server_url``, which has nothing to do with consent.
    The eighth (``mark_checkout_records_unresolved``) survived only because its input
    is ``_load()``-derived too and it therefore found nothing to mark.

    Worse, the same destruction was reachable from a **read**: ``_reconcile_index``
    corrects the cache as a side effect of ``resolve_project_consent``, so merely
    asking whether one project consents flattened the index to that project's single
    entry.

    This is FR-022's rule applied to the machine-global store — *a write refuses when
    the existing record cannot be read* — and it is refused **loudly** rather than
    skipped: an operator whose opt-in silently did nothing is in the same position as
    one told "no consent record", which is the FR-020 defect over again. The fault is
    carried so the message and ``sync doctor`` describe one fault the same way.

    Absence is not a fault and never reaches here: :meth:`SyncConfig.read` returns
    ``fault=None`` for a missing file, so a first-run opt-in on a fresh machine writes
    normally. That line is drawn in ``read`` alone, not restated here.
    """

    def __init__(self, fault: ConfigReadFault) -> None:
        self.fault = fault
        super().__init__(
            f"Refusing to write: the existing configuration could not be read "
            f"({fault.kind}) and writing would rebuild it from an empty document, "
            f"discarding every record it holds. Repair the file first — {fault.detail}"
        )


@dataclass(frozen=True)
class ConfigRead:
    """The outcome of one ``config.toml`` read: its data, and any fault."""

    data: dict[str, Any]
    fault: ConfigReadFault | None

    @property
    def readable(self) -> bool:
        return self.fault is None


@dataclass(frozen=True)
class ProjectConsentRead:
    """One project's recorded consent, together with the index's readability.

    ``enabled`` is ``None`` for *no record* and also ``None`` when ``fault`` is set —
    so a caller that ignores ``fault`` still sees "no record" and still denies. The
    fail-closed default survives being ignored, which is the property that lets this
    ship without auditing every consumer.
    """

    enabled: bool | None
    fault: ConfigReadFault | None

    @property
    def undetermined(self) -> bool:
        return self.fault is not None


def _project_consent_entry(
    config: dict[str, Any], project_uuid: str
) -> tuple[bool | None, str | None]:
    """Decode one uuid's consent entry: ``(enabled, fault_detail)``.

    Shared by :meth:`SyncConfig.get_project_consent` and
    :meth:`SyncConfig.read_project_consent` so the two cannot disagree about what a
    malformed entry means — a second copy of this decode is how a reported state and
    an enforced state drift apart.

    **The fault half is #3030 FR-027**, and it is honesty rather than a leak. An entry
    that exists but records no usable decision — a hand-edited ``enabled = "true"``, or
    an entry that is not a table — decoded to ``None``, which the resolver reports as
    ``ConsentLevel.ABSENT``: *"no consent record for this project"*, the one message
    FR-020 exists to stop sending, because the action it implies is the one the
    operator already took. It already denied (there is no level below the index but the
    env var, which never grants), so nothing shipped that should not have; what was
    wrong is what the operator was told. Fixed here rather than reported because
    leaving it would make this the third module with its own idea of a broken record.

    An entry is a record whose *only* purpose is to carry ``enabled``, so an entry
    present with that key missing is a record that records nothing, and is a fault.
    That is the opposite call from the project-local ``sync:`` section, deliberately:
    that section is shared with unrelated keys such as ``auto_start``, so a missing
    ``enabled`` there is genuine absence.

    A missing ``[sync]`` table, a missing ``project_consent`` table, and a missing
    entry all stay plain **absence** — an unconfigured machine, which denies under
    FR-002 and is not a fault to repair.
    """
    section = config.get("sync", {})
    if not isinstance(section, dict):
        return (None, None)
    consent = section.get("project_consent", {})
    if not isinstance(consent, dict):
        return (None, None)
    if project_uuid not in consent:
        return (None, None)
    entry = consent[project_uuid]
    if not isinstance(entry, dict):
        return (
            None,
            f"[sync.project_consent.{project_uuid!r}] is not a table "
            f"(got {type(entry).__name__})",
        )
    enabled = entry.get("enabled")
    if isinstance(enabled, bool):
        return (enabled, None)
    return (
        None,
        f"[sync.project_consent.{project_uuid!r}].enabled is not a boolean "
        f"(got {enabled!r})",
    )


class SyncConfig:
    """Manage sync configuration"""

    def __init__(self) -> None:
        # Resolve lazily per instance (not at import) so ``SPEC_KITTY_HOME``
        # and test ``HOME`` monkeypatching are honoured. On POSIX with the env
        # var unset this is ``~/.spec-kitty`` — byte-identical to the legacy
        # path (WP01 / NFR-001). ``get_runtime_root`` is seen as ``Any`` here
        # (mypy follow_imports=skip for ``specify_cli.*``); coerce at the typed
        # boundary.
        self.config_dir: Path = get_runtime_root().base
        self.config_file = self.config_dir / 'config.toml'

    def read(self) -> ConfigRead:
        """Load config.toml, reporting *why* it is empty (#3030 FR-020).

        The fault-preserving read. :meth:`_load` is the lossy projection of this and
        keeps its exact contract; use this one whenever "no record" and "could not
        read the records" must not be the same answer.

        Why this exists: ``_load`` returns ``{}`` for a file that is missing **and**
        for one that is corrupt or unreadable, and that conflation is destroyed here,
        below every consumer. It made a machine fault indistinguishable from an
        unconfigured machine — for consent specifically, an unreadable index reported
        every project on the box as "no consent record", which is a per-project fact
        an operator would act on by recording consent they had already recorded.

        Never raises: a fault is *carried*, not thrown. The callers on this path
        include a delivery gate, and converting an unreadable file into a traceback
        out of a drain is not an improvement over converting it into a wrong answer.
        """
        if not self.config_file.exists():
            # Absence is not a fault. This is the overwhelmingly common case on a
            # fresh machine and must stay distinguishable from the two below.
            return ConfigRead(data={}, fault=None)
        try:
            data: dict[str, Any] = toml.load(self.config_file)
        except toml.TomlDecodeError as exc:
            return ConfigRead(
                data={},
                fault=ConfigReadFault(
                    kind="unparseable",
                    detail=f"{self.config_file}: not valid TOML ({exc})",
                ),
            )
        except OSError as exc:
            return ConfigRead(
                data={},
                fault=ConfigReadFault(
                    kind="unreadable",
                    detail=f"{self.config_file}: could not be read ({exc})",
                ),
            )
        # No ``wrong_shape`` branch, and its absence is deliberate rather than an
        # omission: TOML's top level is a table by construction, so ``toml.load``
        # cannot return a non-mapping. A branch here would be unreachable code
        # asserting a state that cannot occur. ``sync/consent.py`` mints that kind
        # because YAML's top level *can* be a list or a bare scalar.
        return ConfigRead(data=data, fault=None)

    def _load(self) -> dict[str, Any]:
        """Load config.toml, returning empty dict when missing or invalid.

        Contract deliberately unchanged (#3030 FR-020): fourteen readers in this
        module plus the accessors they back depend on "empty dict on any problem",
        and widening that to a tuple or an exception would touch every one of them for
        the benefit of a single caller. :meth:`read` is the narrow addition; this stays
        the lossy projection of it so there is still exactly one place that opens the
        file.

        **Read-only.** Every write goes through :meth:`_load_for_update` instead —
        "empty dict on any problem" is a safe answer to a question and a catastrophic
        basis for a whole-file rewrite.
        """
        return self.read().data

    def _load_for_update(self) -> dict[str, Any]:
        """Load config.toml for a read-modify-write, refusing an unreadable file.

        The one seam every setter in this class goes through, because every setter is
        a whole-file read-modify-write and they all read *this* file — the one holding
        the uuid-keyed consent index. On an unreadable file :meth:`_load` answers
        ``{}``, and re-emitting the config from ``{}`` discards every record it held.
        Measured before the fix, with a bystander project's grant and a checkout
        override planted alongside: seven of the eight setters destroyed both, silently
        and with no error, ``set_server_url`` and ``set_max_queue_size`` among them —
        writers with no connection to consent at all. The eighth,
        :meth:`mark_checkout_records_unresolved`, survived only because its input is
        ``_load()``-derived too, so it found nothing to mark and never reached its
        save; it refuses here with the rest, because that accident is one edit from
        ending.

        The same destruction was reachable from a **read**: ``consent._reconcile_index``
        corrects the cache as a side effect of ``resolve_project_consent``, so resolving
        one project's consent rewrote the index down to that project's single entry.

        This is FR-022's rule applied to the machine-global store — *a write refuses
        when the existing record cannot be read* — which FR-022 recorded for the
        project-local store on the reasoning that otherwise "the natural remedy for the
        new denial would manufacture exactly the stale grant the fix stops honouring".
        Here the natural remedy did something worse: it destroyed the records of
        projects nobody was asking about.

        **Absent is not unreadable.** The distinction is inherited from :meth:`read`,
        which draws it in exactly one place — a missing file is ``fault=None`` — and is
        not restated here, because two definitions of "absent" one function apart is
        the shape this mission keeps closing. A first-run opt-in on a fresh machine, an
        empty ``config.toml``, and a config with no ``[sync]`` table all write normally.

        Refusing *loudly* rather than skipping the write: a silent no-op leaves an
        operator exactly where FR-020 found them — having taken an action that appeared
        to work and changed nothing.
        """
        read = self.read()
        if read.fault is not None:
            raise ConfigNotReadableError(read.fault)
        return read.data

    def read_project_consent(self, project_uuid: str) -> ProjectConsentRead:
        """Read one project's recorded consent **and** the index's readability.

        One file read answers both, deliberately. Asking
        :meth:`get_project_consent` and then separately asking whether the file was
        readable would be two ``_load`` calls that can disagree — the file may be
        repaired or corrupted between them — and the pair "no record, index healthy"
        is precisely the false-clean combination that must not be constructible.
        """
        read = self.read()
        if read.fault is not None:
            return ProjectConsentRead(enabled=None, fault=read.fault)
        enabled, entry_fault = _project_consent_entry(read.data, project_uuid)
        if entry_fault is not None:
            # A per-project fact, deliberately NOT a machine-level one: the file read
            # fine, so ``consent_index_health()`` must keep reporting the index
            # healthy. One broken entry is not a broken index.
            return ProjectConsentRead(
                enabled=None,
                fault=ConfigReadFault(
                    kind="unusable", detail=f"{self.config_file}: {entry_fault}"
                ),
            )
        return ProjectConsentRead(enabled=enabled, fault=None)

    def _save(self, config: dict[str, Any]) -> None:
        """Write config dict back to config.toml atomically."""
        content = toml.dumps(config)
        atomic_write(self.config_file, content, mkdir=True)

    def get_server_url(self) -> str:
        """Get server URL from config"""
        config = self._load()
        url = config.get('sync', {}).get('server_url', 'https://spec-kitty-dev.fly.dev')
        return str(url)

    def set_server_url(self, url: str) -> None:
        """Set server URL in config"""
        config = self._load_for_update()
        if 'sync' not in config:
            config['sync'] = {}
        config['sync']['server_url'] = url
        self._save(config)

    def resolve_runtime_target(
        self,
        *,
        user_id: str | None = None,
        team_slug: str | None = None,
    ) -> "ResolvedSyncTarget":
        """Resolve the single canonical runtime sync target (contract §1, FR-016).

        This is the resolver-backed entry point every runtime surface should use
        to learn "what target are we actually hitting?" — as opposed to
        :meth:`get_server_url`, which is the low-level ``config.toml`` accessor
        the resolver itself consumes. The resolver folds in the
        ``SPEC_KITTY_SAAS_URL`` env precedence, fails-closed on an ambiguous
        split-brain before any network call, and *derives* the queue scope from
        the resolved URL (never an independent selector).

        Imported lazily because
        :mod:`specify_cli.sync.target_authority` imports :class:`SyncConfig`;
        a module-level import would create a cycle.
        """
        from .target_authority import resolve_sync_target

        return resolve_sync_target(user_id=user_id, team_slug=team_slug)

    def get_max_queue_size(self) -> int:
        """Get maximum offline queue size from config.

        Config key: [sync] max_queue_size = <int>
        Default: 100,000
        """
        config = self._load()
        try:
            value = config.get("sync", {}).get("max_queue_size")
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            pass
        return DEFAULT_MAX_QUEUE_SIZE

    def set_max_queue_size(self, size: int) -> None:
        """Set maximum offline queue size in config."""
        config = self._load_for_update()
        if "sync" not in config:
            config["sync"] = {}
        config["sync"]["max_queue_size"] = size
        self._save(config)
        print(f"Max queue size set to: {size:,}")

    def get_background_daemon(self) -> BackgroundDaemonPolicy:
        """Get background daemon policy from config.

        Config key: [sync] background_daemon = "auto" | "manual"
        Default: BackgroundDaemonPolicy.AUTO (when key or [sync] table is absent)
        """
        config = self._load()
        raw = config.get("sync", {}).get("background_daemon")

        if raw is None:
            return BackgroundDaemonPolicy.AUTO

        if not isinstance(raw, str):
            print(
                f"[sync].background_daemon has a non-string value {raw!r}; defaulting to 'auto'",
                file=sys.stderr,
            )
            return BackgroundDaemonPolicy.AUTO

        stripped = raw.strip()

        if stripped == "":
            raise ValueError(
                "[sync].background_daemon must be 'auto' or 'manual', not an empty string"
            )

        folded = stripped.casefold()
        policy = _BACKGROUND_DAEMON_VALUES.get(folded)
        if policy is None:
            print(
                f"[sync].background_daemon value {raw!r} is unknown; defaulting to 'auto'",
                file=sys.stderr,
            )
            return BackgroundDaemonPolicy.AUTO

        return policy

    def set_background_daemon(self, policy: BackgroundDaemonPolicy) -> None:
        """Set background daemon policy in config."""
        config = self._load_for_update()
        if "sync" not in config:
            config["sync"] = {}
        config["sync"]["background_daemon"] = policy.value
        self._save(config)

    def get_repository_sync_enabled(self, repo_slug: str) -> bool | None:
        """Return the remembered default sync preference for a repository.

        Preferences are stored under:

            [sync.repo_defaults."<repo-slug>"]
            enabled = true | false

        Returns ``None`` when no preference has been recorded.
        """
        config = self._load()
        repo_defaults = config.get("sync", {}).get("repo_defaults", {})
        if not isinstance(repo_defaults, dict):
            return None
        entry = repo_defaults.get(repo_slug)
        if not isinstance(entry, dict):
            return None
        enabled = entry.get("enabled")
        if isinstance(enabled, bool):
            return enabled
        return None

    def set_repository_sync_enabled(self, repo_slug: str, enabled: bool) -> None:
        """Persist the default sync preference for future checkouts of a repo."""
        config = self._load_for_update()
        if "sync" not in config:
            config["sync"] = {}
        repo_defaults = config["sync"].setdefault("repo_defaults", {})
        if not isinstance(repo_defaults, dict):
            repo_defaults = {}
            config["sync"]["repo_defaults"] = repo_defaults
        repo_defaults[repo_slug] = {"enabled": bool(enabled)}
        self._save(config)

    def get_checkout_sync_enabled(self, repo_root: Path) -> bool | None:
        """Return the remembered sync preference for one local checkout path."""
        config = self._load()
        checkout_overrides = config.get("sync", {}).get("checkout_overrides", {})
        if not isinstance(checkout_overrides, dict):
            return None
        entry = checkout_overrides.get(str(repo_root.resolve()))
        if not isinstance(entry, dict):
            return None
        enabled = entry.get("enabled")
        if isinstance(enabled, bool):
            return enabled
        return None

    def set_checkout_sync_enabled(self, repo_root: Path, enabled: bool) -> None:
        """Persist the sync preference for one local checkout path only."""
        config = self._load_for_update()
        if "sync" not in config:
            config["sync"] = {}
        checkout_overrides = config["sync"].setdefault("checkout_overrides", {})
        if not isinstance(checkout_overrides, dict):
            checkout_overrides = {}
            config["sync"]["checkout_overrides"] = checkout_overrides
        checkout_overrides[str(repo_root.resolve())] = {"enabled": bool(enabled)}
        self._save(config)

    # --- uuid-keyed consent index (#3030 FR-013) --------------------------
    #
    # Events carry a ``project_uuid``; the records above are keyed by absolute
    # path. This section is the join, and it is a *cache* whose authority is the
    # project's own ``.kittify/config.yaml`` — see ``sync/consent.py``, which owns
    # the precedence chain. Nothing here decides consent; it only stores it.

    def get_project_consent(self, project_uuid: str) -> bool | None:
        """Return the recorded consent for *project_uuid*, or ``None`` if absent.

        ``None`` conflates "no record" with "index unreadable" — and, since #3030
        FR-027, with "the entry exists but records nothing usable"; callers that must
        tell them apart use :meth:`read_project_consent`. Kept as-is because ``None``
        denies either way, so existing callers stay correct without change.
        """
        return _project_consent_entry(self._load(), project_uuid)[0]

    def get_all_project_consent(self) -> dict[str, bool]:
        """Return every recorded uuid → consent pair."""
        records: dict[str, bool] = {}
        for uuid, entry in self._project_consent_section().items():
            if isinstance(entry, dict) and isinstance(entry.get("enabled"), bool):
                records[str(uuid)] = entry["enabled"]
        return records

    def set_project_consent(self, project_uuid: str, enabled: bool) -> None:
        """Record consent for one project."""
        self.set_project_consent_bulk({project_uuid: enabled})

    def set_project_consent_bulk(self, entries: dict[str, bool]) -> None:
        """Record consent for many projects in a **single** file write.

        Batched on purpose: these setters are unlocked whole-file
        read-modify-writes and the daemon writes this file concurrently with an
        interactive ``sync enable``. Since #3030 a lost record is a silent
        delivery denial, not a cosmetic loss, so a backfill over N paths must not
        be N read-modify-write cycles.
        """
        if not entries:
            return
        config = self._load_for_update()
        section = config.setdefault("sync", {})
        if not isinstance(section, dict):
            section = {}
            config["sync"] = section
        consent = section.setdefault("project_consent", {})
        if not isinstance(consent, dict):
            consent = {}
            section["project_consent"] = consent
        for uuid, enabled in entries.items():
            consent[str(uuid)] = {"enabled": bool(enabled)}
        self._save(config)

    def mark_checkout_records_unresolved(self, paths: list[str]) -> None:
        """Flag path-keyed records whose checkout no longer resolves to a uuid.

        The record is **retained**: dropping it would lose the operator's
        decision, and leaving it unmarked would imply it is enforced when the
        uuid-keyed predicate cannot see it. WP07 renders these as "consented but
        unresolvable" (US2 scenario 3).
        """
        if not paths:
            return
        config = self._load_for_update()
        overrides = config.get("sync", {}).get("checkout_overrides", {})
        if not isinstance(overrides, dict):
            return
        changed = False
        for path in paths:
            entry = overrides.get(path)
            if isinstance(entry, dict) and not entry.get("unresolved"):
                entry["unresolved"] = True
                changed = True
        if changed:
            self._save(config)

    def get_all_checkout_sync_records(self) -> dict[str, bool]:
        """Return every path-keyed sync record as ``{resolved_path: enabled}``."""
        records: dict[str, bool] = {}
        overrides = self._load().get("sync", {}).get("checkout_overrides", {})
        if not isinstance(overrides, dict):
            return records
        for path, entry in overrides.items():
            if isinstance(entry, dict) and isinstance(entry.get("enabled"), bool):
                records[str(path)] = entry["enabled"]
        return records

    def _project_consent_section(self) -> dict[str, Any]:
        section = self._load().get("sync", {})
        if not isinstance(section, dict):
            return {}
        consent = section.get("project_consent", {})
        return consent if isinstance(consent, dict) else {}
