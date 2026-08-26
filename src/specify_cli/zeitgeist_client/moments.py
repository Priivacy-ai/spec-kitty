"""#190: per-developer moment settings — the off switch, the filters, and
the rate ceiling that decide which Zeitgeist status moments reach agent
context ("Moments in agent context", Robert 2026-08-26: "there needs to be a
way to filter or unsubscribe because some people will find this annoying").

Three facts fix this module's shape:

**Filtering is the reader's business.** The relay stays a per-team firehose
(``zeitgeist/managed.py`` fans every accepted frame out to every subscriber
of the frame's scope); nothing here is ever sent upstream. What this module
produces is a *predicate* over already-received :class:`~.live_frame.LiveFrame`
objects, which ``filtered_stream.FilteredStream`` applies client-side before a
frame is delivered — the exact seam EXPERIMENTAL-spec-kitty#190 names
("applied client-side in the stream client").

**Quiet by default.** ``[moments] agents`` defaults to ``mine``, never
``team``: an agent surfaces moments about missions the developer is working
on, not everything the team broadcasts. An unreadable or unknown mode value
fails closed to ``off`` — a typo in a config file must never widen what an
agent receives.

**One setting, two files.** The developer-global default lives in
``~/.kittify/config.toml`` (:func:`kernel.paths.get_kittify_home`), a repo
may override it in ``<repo>/.kittify/config.toml`` — the same two-file shape
every other per-developer preference uses (global home + project ``.kittify``
override). Per-key precedence is repo-over-global-over-default; there is no
deeper merge (a repo override replaces a whole list, it does not union it),
because "which moments do I want *here*" is one decision, not a diff.

The ``mine`` basis is deliberately cheap and honest about being a proxy:
spec-kitty has no hosted assignment model to ask, so "the missions the
developer is on" means the missions this checkout knows — its
``kitty-specs/<slug>/`` directories (:func:`local_missions`) — plus whatever
``[moments].missions`` adds. A moment whose mission matches neither is
dropped; a checkout with no ``kitty-specs/`` at all therefore surfaces
nothing under ``mine`` except explicitly configured missions, which is the
quiet-by-default reading of the requirement, not a gap.

Nothing here performs network I/O, so this module sits outside the egress
consent boundary by construction; and nothing here reads a credential —
mode/filters/rate are preference state, never auth state.
"""

from __future__ import annotations

import time
import tomllib

from collections import deque
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import tomli_w

from kernel.paths import get_kittify_home


class MomentsMode(StrEnum):
    """How much of the team's moment stream an agent surface may deliver.

    ``off``  — nothing; the MCP server refuses to start (#190 item 3).
    ``mine`` — moments about missions this developer is on (the default).
    ``team`` — everything the team's relay carries.
    """

    OFF = "off"
    MINE = "mine"
    TEAM = "team"


#: The documented default mode. "Never everything by default" (#190): a
#: developer who opts at nothing gets ``mine``, and only an explicit
#: ``agents = "team"`` widens the stream.
DEFAULT_AGENTS_MODE = MomentsMode.MINE

#: #190 item 4: "at most N moments per minute surfaced to an agent (default
#: small)". Small enough that a chatty team cannot flood an agent's context,
#: large enough that one developer's normal work is never summarised away.
DEFAULT_RATE_PER_MINUTE = 10

CONFIG_FILENAME = "config.toml"
REPO_CONFIG_DIRNAME = ".kittify"

#: The TOML table every aspect lives under, in both config files.
CONFIG_SECTION = "moments"

_WINDOW_S = 60.0


class MomentsDisabled(Exception):
    """Raised when a moment surface starts against ``[moments] agents =
    "off"``. Carries the human line its caller reports — one sentence, never
    a traceback — plus the config file that decided it."""

    def __init__(self, settings: MomentSettings) -> None:
        super().__init__(
            f"Zeitgeist moments to agents are switched off "
            f'([moments] agents = "{settings.agents.value}" per {settings.agents_source}); '
            "run `spec-kitty moments on` to re-enable."
        )
        self.settings = settings


@dataclass(frozen=True)
class MomentSettings:
    """The effective moment preferences for one developer in one checkout.

    The four tuple-valued fields are allowlists: empty means "no restriction"
    (the mode alone governs), non-empty means "only these". ``agents_source``
    records where the effective mode came from — ``"default"``, the winning
    config file's path, or that path marked invalid when the stored value was
    unreadable — so ``status`` can say *why* rather than just *what*.

    ``invalid_filters`` names which of ``repos``/``missions``/``teammates``/
    ``kinds`` were PRESENT in the deciding config but not a list — the shape
    :func:`_string_list` quietly empties to the same tuple an unset key
    produces. That collapse is the bug this field exists to prevent: an unset
    filter means "no restriction" (intentional), but a malformed one means
    the developer asked for a restriction and typo'd it, so it must never
    read as "no restriction" too — :func:`frame_predicate` and
    :func:`allows_repo` fail that dimension closed (admit nothing) instead.
    """

    agents: MomentsMode = DEFAULT_AGENTS_MODE
    repos: tuple[str, ...] = ()
    missions: tuple[str, ...] = ()
    teammates: tuple[str, ...] = ()
    kinds: tuple[str, ...] = ()
    rate_per_minute: int = DEFAULT_RATE_PER_MINUTE
    agents_source: str = "default"
    invalid_filters: frozenset[str] = frozenset()

    def as_dict(self) -> dict[str, Any]:
        """JSON-safe projection (StrEnum members serialise as their values;
        ``invalid_filters`` as a sorted list — a frozenset is not JSON-safe)."""
        payload = asdict(self)
        payload["invalid_filters"] = sorted(self.invalid_filters)
        return payload


def global_config_path(*, home: Path | None = None) -> Path:
    """The developer-global config file holding the default ``[moments]``
    table. ``home`` exists for callers that must pin the root (tests); the
    production door is :func:`kernel.paths.get_kittify_home`."""
    return (home if home is not None else get_kittify_home()) / CONFIG_FILENAME


def repo_config_path(project_root: Path) -> Path:
    """The per-repo override file inside ``project_root``."""
    return project_root / REPO_CONFIG_DIRNAME / CONFIG_FILENAME


def locate_repo_root(cwd: Path | None = None) -> Path | None:
    """The Spec Kitty checkout containing ``cwd``, or ``None`` when there is
    none. Function-scoped import: the resolver drags in a large
    ``specify_cli.core`` graph no other reader of this module should pay for
    (same lazy-import discipline ``cli/commands/zeitgeist.py`` records)."""
    from specify_cli.core.paths import locate_project_root  # noqa: PLC0415

    return locate_project_root(cwd if cwd is not None else Path.cwd())


def _read_section(path: Path) -> dict[str, Any]:
    """The ``[moments]`` table of one config file, or ``{}`` when there is
    no file, no table, or an unreadable one. Read failures read as unset —
    the same tolerance ``credentials._read_all`` applies to its store —
    because a broken config must never crash a surface that only wanted to
    know what to surface."""
    try:
        with path.open("rb") as fh:
            document = tomllib.load(fh)
    except (FileNotFoundError, IsADirectoryError, PermissionError, tomllib.TOMLDecodeError, OSError):
        return {}
    section = document.get(CONFIG_SECTION)
    return dict(section) if isinstance(section, Mapping) else {}


def _coerce_mode(raw: Any, source: str) -> tuple[MomentsMode, str]:
    """A stored ``agents`` value as ``(mode, provenance)``. Anything but the
    three spelled modes fails CLOSED to ``off``: a mistyped value narrows the
    stream, it never widens it."""
    if isinstance(raw, str):
        try:
            return MomentsMode(raw.strip().lower()), source
        except ValueError:
            pass
    return MomentsMode.OFF, f"{source} (invalid value {raw!r}; failing closed to off)"


def _string_list(raw: Any) -> tuple[str, ...]:
    """A stored list-of-strings filter as stripped, de-duplicated, order-
    preserving strings. Any other shape (a bare string among them — half a
    list is a typo, not an implicit singleton) reads as "no restriction",
    because silently interpreting a malformed entry as an allowlist entry
    could widen the stream instead of narrowing it."""
    if not isinstance(raw, (list, tuple)):
        return ()
    seen: list[str] = []
    for entry in raw:
        if not isinstance(entry, str):
            continue
        value = entry.strip()
        if value and value not in seen:
            seen.append(value)
    return tuple(seen)


#: The four allowlist keys a config's ``[moments]`` table may set.
_FILTER_KEYS = ("repos", "missions", "teammates", "kinds")


def _malformed_filter_keys(merged: Mapping[str, Any]) -> frozenset[str]:
    """Which of :data:`_FILTER_KEYS` are PRESENT in ``merged`` but not a
    list/tuple — the shape :func:`_string_list` quietly empties to "unset".
    A key that is simply absent is not malformed; a key that is present with
    the wrong shape (a typo'd bare string in place of a one-item list) is,
    and must fail its dimension closed rather than silently disappear."""
    return frozenset(key for key in _FILTER_KEYS if key in merged and not isinstance(merged[key], (list, tuple)))


def _coerce_rate(raw: Any) -> int:
    """A stored ``rate_per_minute`` as a usable cap. Absent/negative/non-int
    falls back to the default; zero is honoured literally (surface no
    moments), since that is what a developer writing 0 asked for."""
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        return DEFAULT_RATE_PER_MINUTE
    return raw


def load_settings(
    *,
    project_root: Path | None = None,
    home: Path | None = None,
) -> MomentSettings:
    """The effective settings for one developer in one checkout: the global
    file's ``[moments]`` table overlaid by the repo file's, per key, repo
    winning.

    ``project_root=None`` discovers the checkout from the process working
    directory (:func:`locate_repo_root`); ``None`` found simply means no repo
    override exists. Both paths are optional parameters rather than globals
    so tests can pin them without touching the real home.
    """
    if project_root is None:
        project_root = locate_repo_root()
    global_section = _read_section(global_config_path(home=home))
    repo_section = _read_section(repo_config_path(project_root)) if project_root is not None else {}

    merged: dict[str, Any] = {**global_section, **repo_section}
    invalid_filters = _malformed_filter_keys(merged)
    if "agents" not in merged:
        # Neither file says anything: the documented default, honestly labelled.
        return MomentSettings(
            repos=_string_list(merged.get("repos")),
            missions=_string_list(merged.get("missions")),
            teammates=_string_list(merged.get("teammates")),
            kinds=_string_list(merged.get("kinds")),
            rate_per_minute=_coerce_rate(merged.get("rate_per_minute")),
            invalid_filters=invalid_filters,
        )
    # ``repo_section`` is empty whenever ``project_root`` is None, so an
    # agent key found there guarantees the repo path below is real.
    deciding_file = repo_config_path(project_root) if "agents" in repo_section else global_config_path(home=home)
    mode, agents_source = _coerce_mode(merged["agents"], str(deciding_file))
    return MomentSettings(
        agents=mode,
        repos=_string_list(merged.get("repos")),
        missions=_string_list(merged.get("missions")),
        teammates=_string_list(merged.get("teammates")),
        kinds=_string_list(merged.get("kinds")),
        rate_per_minute=_coerce_rate(merged.get("rate_per_minute")),
        agents_source=agents_source,
        invalid_filters=invalid_filters,
    )


def write_agents_mode(
    mode: MomentsMode,
    *,
    scope: str = "global",
    project_root: Path | None = None,
    home: Path | None = None,
) -> Path:
    """Persist ``[moments] agents = <mode>`` to the global or repo config
    file, preserving every other key in that file, and return the path
    written.

    The rewrite is whole-file (``tomllib`` in, ``tomli_w`` out): comments in
    a hand-edited config are not preserved. That is the accepted cost of one
    writer for both scopes — the alternative is a second TOML dependency for
    a table this CLI owns.
    """
    if scope == "repo":
        if project_root is None:
            raise ValueError("scope='repo' requires project_root")
        path = repo_config_path(project_root)
    elif scope == "global":
        path = global_config_path(home=home)
    else:
        raise ValueError(f"unknown scope {scope!r} (expected 'global' or 'repo')")
    try:
        with path.open("rb") as fh:
            document: dict[str, Any] = tomllib.load(fh)
    except (FileNotFoundError, tomllib.TOMLDecodeError, OSError):
        document = {}

    section = document.get(CONFIG_SECTION)
    section = dict(section) if isinstance(section, Mapping) else {}
    section["agents"] = mode.value
    document[CONFIG_SECTION] = section

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("wb") as fh:
        tomli_w.dump(document, fh)
    tmp_path.replace(path)  # atomic on POSIX and Windows (same volume)
    return path


def local_missions(project_root: Path | None) -> frozenset[str]:
    """The mission slugs this checkout resolves — the cheap, local stand-in
    for "missions this developer is on".

    Routed through :class:`~specify_cli.context.mission_resolver.FsMissionResolver`
    (the sanctioned mission-discovery boundary — a raw ``kitty-specs/`` walk
    here would bypass it), so exactly its semantics apply: identity-bearing
    missions only; legacy directories whose ``meta.json`` lacks a
    ``mission_id``, and non-directory entries, are invisible to it. A missing
    root yields the empty set.

    Under ``mine``, a checkout that resolves nothing therefore surfaces no
    moments beyond explicitly configured missions (quiet by default), never
    everything.
    """
    if project_root is None:
        return frozenset()

    from specify_cli.context.mission_resolver import FsMissionResolver  # noqa: PLC0415

    try:
        return frozenset(mission.mission_slug for mission in FsMissionResolver(project_root).all_missions())
    except OSError:
        # An unreadable checkout reads as "no known missions" — quiet, never
        # everything (the same tolerance _read_section applies to config).
        return frozenset()


# --- #190: the client-side predicate ----------------------------------------


def event_kind(payload: Mapping[str, Any]) -> str | None:
    """An event payload's ``kind`` — the volatile vocabulary's event type
    (``WPStatusChanged``, ``MissionCreated``, …) — or ``None`` when absent."""
    kind = payload.get("kind")
    return kind if isinstance(kind, str) and kind else None


def event_actor(payload: Mapping[str, Any]) -> str | None:
    """An event payload's attested actor label (``actor.user`` — the identity
    the relay derives from the capability credential), or ``None``."""
    actor = payload.get("actor")
    if not isinstance(actor, Mapping):
        return None
    user = actor.get("user")
    return user if isinstance(user, str) and user else None


def event_mission(payload: Mapping[str, Any]) -> str | None:
    """The mission an event moment is about: the ``mission_slug`` attr the
    volatile codec rides on every mission-scoped family, falling back to the
    frame ``ref`` (that codec's aggregate field verbatim). ``None`` when the
    moment names no mission at all."""
    attrs = payload.get("attrs")
    if isinstance(attrs, Mapping):
        slug = attrs.get("mission_slug")
        if isinstance(slug, str) and slug:
            return slug
    ref = payload.get("ref")
    if isinstance(ref, str) and ref:
        return ref.split("/", 1)[0]
    return None


def frame_predicate(
    settings: MomentSettings,
    *,
    local_missions: Iterable[str] = (),
) -> Callable[[Any], bool]:
    """Build the client-side predicate ``filtered_stream.FilteredStream``
    applies to each received frame.

    Non-event frames (presence/focus/signal) always pass — the setting governs
    *moments*, never liveness. An event passes only when BOTH hold:

    * every configured filter admits it — ``kinds``, ``teammates``, and
      ``missions`` are allowlists that apply in every mode;
    * the mode admits it — ``team`` admits all, ``off`` admits nothing, and
      ``mine`` admits moments whose mission is one of this checkout's own
      (:data:`local_missions`) or of the configured ``missions``.

    An event that names no mission fails ``mine`` (quiet by default); the
    same moment passes ``team`` subject to the filters alone.

    A ``kinds``/``teammates``/``missions`` value present in config but not a
    list (e.g. a typo'd bare string, see ``settings.invalid_filters``) fails
    ITS dimension closed: every event is refused, never admitted, so a
    malformed allowlist narrows the stream to nothing instead of silently
    reading as "no restriction" and widening it (EXPERIMENTAL-spec-kitty#190
    squad follow-up, PR #201). ``repos`` is not one of these — it gates
    subscriptions, not frames — and is checked by :func:`allows_repo` instead.
    """
    kinds = frozenset(settings.kinds)
    teammates = frozenset(settings.teammates)
    configured_missions = frozenset(settings.missions)
    my_missions = configured_missions | frozenset(local_missions)
    predicate_relevant_invalid = settings.invalid_filters & {"kinds", "teammates", "missions"}

    def predicate(live_frame: Any) -> bool:
        if getattr(live_frame, "frame_type", None) != "event":
            return True
        if settings.agents is MomentsMode.OFF:
            return False
        if predicate_relevant_invalid:
            return False
        payload = getattr(live_frame, "payload", None)
        if not isinstance(payload, Mapping):
            return False
        if kinds:
            kind = event_kind(payload)
            if kind is None or kind not in kinds:
                return False
        if teammates:
            actor = event_actor(payload)
            if actor is None or actor not in teammates:
                return False
        mission = event_mission(payload)
        if configured_missions and (mission is None or mission not in configured_missions):
            return False
        # mine: a moment with no mission cannot be shown to be this
        # developer's, so it stays quiet rather than surfacing by default.
        return not (settings.agents is MomentsMode.MINE and (mission is None or mission not in my_missions))

    return predicate


def allows_repo(settings: MomentSettings, store_key: str) -> bool:
    """Whether moments for the credential-store key ``store_key``
    (``host/owner/repo``) may be surfaced at all. An unset ``repos`` filter
    allows every repo this developer holds a credential for; a set one is an
    exact-match allowlist — the store key is the only repo identity a moment
    surface has, since one subscription is bound to exactly one credential.

    A ``repos`` value present in config but not a list fails closed here —
    every repo is refused, never every repo admitted — matching
    :func:`frame_predicate`'s treatment of the other three filters."""
    if "repos" in settings.invalid_filters:
        return False
    return not settings.repos or store_key in settings.repos


class MomentRateGate:
    """#190 item 4: at most ``limit_per_minute`` moments surfaced to an agent
    in any rolling 60-second window; everything beyond the cap is counted so
    the caller can summarise it as "+k more".

    One gate belongs to one agent session (one stdio server instance), not to
    one call — a client polling every two seconds must not earn a fresh quota
    each poll. The clock is injected so tests advance time instead of
    sleeping; ``time.monotonic`` is the production default (elapsed-time
    measurement, matching ``budget.py``'s idiom — never wall-clock datetimes).
    """

    def __init__(
        self,
        limit_per_minute: int,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit = limit_per_minute
        self._clock = clock
        self._window: deque[float] = deque()
        self._suppressed_since_read = 0

    def admit(self) -> bool:
        """Whether one more moment may surface right now. Rejected moments
        are counted, never queued — they are summarised, not delayed (#190:
        "the rest summarised")."""
        now = self._clock()
        while self._window and self._window[0] <= now - _WINDOW_S:
            self._window.popleft()
        if len(self._window) >= self._limit:
            self._suppressed_since_read += 1
            return False
        self._window.append(now)
        return True

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def suppressed(self) -> int:
        """Moments rejected since the last :meth:`take_summary`."""
        return self._suppressed_since_read

    def take_summary(self) -> str | None:
        """The "+k more" line for everything suppressed so far, or ``None``
        when nothing was; reading resets the counter so one watch call's
        report says what THAT call withheld, not the session's lifetime total."""
        count, self._suppressed_since_read = self._suppressed_since_read, 0
        if not count:
            return None
        return f"+{count} more moment{'s' if count != 1 else ''} withheld (agent rate cap: {self._limit}/min)"
