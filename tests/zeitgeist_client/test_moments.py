"""#190: ``moments.py`` — the per-developer moment settings, the client-side
predicate that applies them, and the agent rate cap.

Covers the whole decision matrix the setting promises: mode resolution across
the two config files (repo beats global beats default), fail-closed reading of
a broken value, the four allowlist filters, ``mine``'s cheap local-mission
basis, repo admission, and every branch of :class:`moments.MomentRateGate`.
The wire-level consequences (what an MCP tool actually delivers) are covered
in ``test_mcp_stdio.py``; what ``FilteredStream`` does with a predicate in
``test_filtered_stream.py``.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from specify_cli.zeitgeist_client import moments

pytestmark = pytest.mark.fast


@pytest.fixture()
def moments_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Module-local override of conftest's autouse ``moments_config``: the
    same redirected path, but EMPTY — these tests arrange config files
    themselves, so a pre-written ``team`` line would hide exactly the
    defaults they exist to pin down."""
    config_path = tmp_path / "kittify-global-config.toml"
    monkeypatch.setattr(moments, "global_config_path", lambda *, home=None: config_path)
    return config_path


def _settings(**overrides: Any) -> moments.MomentSettings:
    values: dict[str, Any] = {
        "agents": moments.MomentsMode.TEAM,
        "repos": (),
        "missions": (),
        "teammates": (),
        "kinds": (),
        "rate_per_minute": moments.DEFAULT_RATE_PER_MINUTE,
    }
    values.update(overrides)
    return moments.MomentSettings(**values)


def _event_frame(
    *,
    kind: str | None = "WPStatusChanged",
    user: str | None = "lynn",
    mission: str | None = None,
    ref: str | None = None,
    attrs: dict[str, str] | None = None,
) -> SimpleNamespace:
    """A minimal stand-in for one parsed ``event`` LiveFrame. The predicate
    reads only ``frame_type`` and ``payload``, so a plain namespace-shaped
    double keeps these tests about the rule, not about frame parsing (which
    ``test_live_frame.py`` owns)."""
    payload: dict[str, object] = {}
    if kind is not None:
        payload["kind"] = kind
    if user is not None:
        payload["actor"] = {"user": user}
    merged_attrs: dict[str, str] = dict(attrs or {})
    if mission is not None:
        merged_attrs["mission_slug"] = mission
    if merged_attrs:
        payload["attrs"] = merged_attrs
    if ref is not None:
        payload["ref"] = ref
    return SimpleNamespace(frame_type="event", payload=payload)


def _other_frame(frame_type: str) -> SimpleNamespace:
    return SimpleNamespace(frame_type=frame_type, payload={"observed_at": 0.0})


# --- settings resolution -----------------------------------------------------


class TestLoadSettings:
    def test_no_files_anywhere_is_the_documented_default(self, moments_config: Path) -> None:
        settings = moments.load_settings(project_root=None, home=moments_config.parent)
        assert settings.agents is moments.MomentsMode.MINE
        assert settings.agents_source == "default"
        assert not settings.repos and not settings.missions and not settings.teammates and not settings.kinds
        assert settings.rate_per_minute == moments.DEFAULT_RATE_PER_MINUTE

    def test_global_file_sets_mode_and_provenance(self, moments_config: Path) -> None:
        moments_config.write_text('[moments]\nagents = "off"\n')
        settings = moments.load_settings(project_root=None, home=moments_config.parent)
        assert settings.agents is moments.MomentsMode.OFF
        assert settings.agents_source == str(moments_config)

    def test_repo_override_beats_global(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "checkout"
        (root / ".kittify").mkdir(parents=True)
        (root / ".kittify" / "config.toml").write_text('[moments]\nagents = "team"\n')
        global_path = tmp_path / "global-config.toml"
        global_path.write_text('[moments]\nagents = "off"\n')
        monkeypatch.setattr(moments, "global_config_path", lambda *, home=None: global_path)

        settings = moments.load_settings(project_root=root)
        assert settings.agents is moments.MomentsMode.TEAM
        assert settings.agents_source == str(root / ".kittify" / "config.toml")

    def test_lists_merge_per_key_repo_wins_whole_list(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A repo override replaces a list wholesale — it never unions with
        the global one ("which moments do I want here" is one decision)."""
        root = tmp_path / "checkout"
        (root / ".kittify").mkdir(parents=True)
        (root / ".kittify" / "config.toml").write_text('[moments]\nrepos = ["github.com/acme/widget"]\nkinds = ["MissionCreated"]\n')
        global_path = tmp_path / "global-config.toml"
        global_path.write_text('[moments]\nrepos = ["github.com/acme/other"]\nkinds = ["WPStatusChanged", "MissionClosed"]\n')
        monkeypatch.setattr(moments, "global_config_path", lambda *, home=None: global_path)

        settings = moments.load_settings(project_root=root)
        assert settings.repos == ("github.com/acme/widget",)
        assert settings.kinds == ("MissionCreated",)

    @pytest.mark.parametrize("raw", ['"TEAM"', '" team "'])
    def test_mode_value_normalisation(self, moments_config: Path, raw: str) -> None:
        moments_config.write_text(f"[moments]\nagents = {raw}\n")
        assert moments.load_settings(home=moments_config.parent).agents is moments.MomentsMode.TEAM

    @pytest.mark.parametrize("raw", ['"everything"', "7"])
    def test_unknown_mode_fails_closed_to_off(self, moments_config: Path, raw: str) -> None:
        """A mistyped value narrows the stream, it never widens it."""
        moments_config.write_text(f"[moments]\nagents = {raw}\n")
        settings = moments.load_settings(home=moments_config.parent)
        assert settings.agents is moments.MomentsMode.OFF
        assert "(invalid" in settings.agents_source

    def test_corrupt_global_file_reads_as_unset(self, moments_config: Path) -> None:
        moments_config.write_text("[moments\nnot toml ===")
        assert moments.load_settings(home=moments_config.parent).agents is moments.MomentsMode.MINE

    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            ("rate_per_minute = 3", 3),
            ("rate_per_minute = 0", 0),  # honoured literally: surface nothing
            ("rate_per_minute = -2", moments.DEFAULT_RATE_PER_MINUTE),
            ('rate_per_minute = "many"', moments.DEFAULT_RATE_PER_MINUTE),
            ("", moments.DEFAULT_RATE_PER_MINUTE),
        ],
    )
    def test_rate_coercion(self, moments_config: Path, line: str, expected: int) -> None:
        body = f"[moments]\n{line}\n" if line else ""
        moments_config.write_text(body)
        assert moments.load_settings(home=moments_config.parent).rate_per_minute == expected

    def test_filter_lists_are_stripped_deduped_and_shape_checked(self, moments_config: Path) -> None:
        moments_config.write_text(
            '[moments]\nrepos = [" github.com/acme/w ", "", "github.com/acme/w", 42]\nmissions = "034-demo"\n'  # a bare string is a typo, not a singleton
        )
        settings = moments.load_settings(home=moments_config.parent)
        assert settings.repos == ("github.com/acme/w",)
        assert settings.missions == ()


class TestWriteAgentsMode:
    def test_global_write_round_trips(self, moments_config: Path) -> None:
        written = moments.write_agents_mode(moments.MomentsMode.OFF, scope="global")
        assert written == moments_config
        with moments_config.open("rb") as fh:
            assert tomllib.load(fh)["moments"]["agents"] == "off"

    def test_write_preserves_every_other_key_in_the_file(self, moments_config: Path) -> None:
        moments_config.write_text('[moments]\nagents = "team"\nkinds = ["WPStatusChanged"]\n[other]\nkeep = true\n')
        moments.write_agents_mode(moments.MomentsMode.OFF, scope="global")
        with moments_config.open("rb") as fh:
            document = tomllib.load(fh)
        assert document["moments"] == {"agents": "off", "kinds": ["WPStatusChanged"]}
        assert document["other"] == {"keep": True}

    def test_repo_scope_writes_into_the_checkout(self, tmp_path: Path) -> None:
        root = tmp_path / "checkout"
        (root / ".kittify").mkdir(parents=True)
        written = moments.write_agents_mode(moments.MomentsMode.MINE, scope="repo", project_root=root)
        assert written == root / ".kittify" / "config.toml"
        assert written.exists()

    def test_repo_scope_creates_a_missing_kittify_dir(self, tmp_path: Path) -> None:
        root = tmp_path / "fresh-checkout"
        root.mkdir()
        written = moments.write_agents_mode(moments.MomentsMode.OFF, scope="repo", project_root=root)
        assert written.exists()

    def test_repo_scope_without_root_refuses(self) -> None:
        with pytest.raises(ValueError, match="project_root"):
            moments.write_agents_mode(moments.MomentsMode.OFF, scope="repo", project_root=None)

    def test_unknown_scope_refuses(self, moments_config: Path) -> None:
        with pytest.raises(ValueError, match="scope"):
            moments.write_agents_mode(moments.MomentsMode.OFF, scope="session")


# --- the mine basis ----------------------------------------------------------


class TestLocalMissions:
    def test_no_root_yields_nothing(self) -> None:
        assert moments.local_missions(None) == frozenset()

    def test_lists_kitty_specs_directories_skipping_dot_dirs(self, tmp_path: Path) -> None:
        specs = tmp_path / "kitty-specs"
        (specs / "034-demo").mkdir(parents=True)
        (specs / ".hidden").mkdir()
        (specs / "notes.txt").write_text("not a mission")
        assert moments.local_missions(tmp_path) == frozenset({"034-demo"})

    def test_missing_kitty_specs_yields_nothing(self, tmp_path: Path) -> None:
        assert moments.local_missions(tmp_path) == frozenset()


# --- event-field extraction --------------------------------------------------


class TestEventExtraction:
    def test_event_kind_reads_the_kind_field(self) -> None:
        assert moments.event_kind({"kind": "WPStatusChanged"}) == "WPStatusChanged"

    def test_event_kind_absent_or_empty_is_none(self) -> None:
        assert moments.event_kind({}) is None
        assert moments.event_kind({"kind": ""}) is None

    def test_event_actor_reads_the_attested_user(self) -> None:
        assert moments.event_actor({"actor": {"user": "lynn"}}) == "lynn"

    def test_event_actor_without_a_user_is_none(self) -> None:
        assert moments.event_actor({"actor": {"session_ref": "abc"}}) is None
        assert moments.event_actor({}) is None

    def test_event_mission_prefers_the_attr(self) -> None:
        payload = {"attrs": {"mission_slug": "034-demo"}, "ref": "other/WP01"}
        assert moments.event_mission(payload) == "034-demo"

    def test_event_mission_falls_back_to_the_ref_prefix(self) -> None:
        assert moments.event_mission({"ref": "034-demo/WP01"}) == "034-demo"

    def test_event_mission_of_a_bare_ref_is_whole_ref(self) -> None:
        assert moments.event_mission({"ref": "034-demo"}) == "034-demo"

    def test_event_mission_absent_is_none(self) -> None:
        assert moments.event_mission({"attrs": {"note": "hi"}}) is None


# --- the predicate -----------------------------------------------------------


class TestFramePredicate:
    def test_non_event_frames_pass_even_when_off(self) -> None:
        predicate = moments.frame_predicate(_settings(agents=moments.MomentsMode.OFF))
        for frame_type in ("presence", "focus", "signal"):
            assert predicate(_other_frame(frame_type)) is True

    def test_off_drops_every_event(self) -> None:
        predicate = moments.frame_predicate(_settings(agents=moments.MomentsMode.OFF))
        assert predicate(_event_frame()) is False

    def test_team_admits_events_with_no_filters_set(self) -> None:
        predicate = moments.frame_predicate(_settings())
        assert predicate(_event_frame()) is True

    def test_mine_admits_a_local_mission(self) -> None:
        predicate = moments.frame_predicate(_settings(agents=moments.MomentsMode.MINE), local_missions=["034-demo"])
        assert predicate(_event_frame(mission="034-demo")) is True

    def test_mine_admits_a_configured_mission_not_known_locally(self) -> None:
        predicate = moments.frame_predicate(_settings(agents=moments.MomentsMode.MINE, missions=("999-other",)), local_missions=["034-demo"])
        assert predicate(_event_frame(mission="999-other")) is True

    def test_mine_drops_an_unknown_mission(self) -> None:
        predicate = moments.frame_predicate(_settings(agents=moments.MomentsMode.MINE), local_missions=["034-demo"])
        assert predicate(_event_frame(mission="999-someone-elses")) is False

    def test_mine_drops_a_moment_that_names_no_mission(self) -> None:
        """Quiet by default: a moment without a mission cannot be shown to be
        mine, so it does not surface."""
        predicate = moments.frame_predicate(_settings(agents=moments.MomentsMode.MINE))
        assert predicate(_event_frame()) is False

    def test_kinds_allowlist_applies_in_every_mode(self) -> None:
        predicate = moments.frame_predicate(_settings(kinds=("WPStatusChanged",)))
        assert predicate(_event_frame(kind="WPStatusChanged")) is True
        assert predicate(_event_frame(kind="MissionCreated")) is False
        assert predicate(_event_frame(kind=None)) is False

    def test_teammates_allowlist_needs_an_attested_user(self) -> None:
        predicate = moments.frame_predicate(_settings(teammates=("lynn",)))
        assert predicate(_event_frame(user="lynn")) is True
        assert predicate(_event_frame(user="elio")) is False
        assert predicate(_event_frame(user=None)) is False

    def test_missions_allowlist_applies_even_in_team_mode(self) -> None:
        predicate = moments.frame_predicate(_settings(missions=("034-demo",)))
        assert predicate(_event_frame(mission="034-demo")) is True
        assert predicate(_event_frame(mission="999-other")) is False

    def test_filters_compose(self) -> None:
        predicate = moments.frame_predicate(_settings(kinds=("WPStatusChanged",), teammates=("lynn",)))
        assert predicate(_event_frame(kind="WPStatusChanged", user="lynn", mission="x")) is True
        assert predicate(_event_frame(kind="MissionCreated", user="lynn", mission="x")) is False
        assert predicate(_event_frame(kind="WPStatusChanged", user="elio", mission="x")) is False


# --- repo admission ----------------------------------------------------------


class TestAllowsRepo:
    def test_unset_repos_allows_every_credentialed_repo(self) -> None:
        assert moments.allows_repo(_settings(), "github.com/acme/widget") is True

    def test_repos_allowlist_is_exact_on_the_store_key(self) -> None:
        settings = _settings(repos=("github.com/acme/widget",))
        assert moments.allows_repo(settings, "github.com/acme/widget") is True
        assert moments.allows_repo(settings, "github.com/acme/other") is False
        assert moments.allows_repo(settings, "acme/widget") is False


# --- the rate cap ------------------------------------------------------------


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestMomentRateGate:
    def test_up_to_the_limit_is_admitted_inside_one_window(self) -> None:
        clock = FakeClock()
        gate = moments.MomentRateGate(3, clock=clock)
        assert [gate.admit() for _ in range(3)] == [True, True, True]

    def test_beyond_the_limit_is_suppressed_within_the_window(self) -> None:
        clock = FakeClock()
        gate = moments.MomentRateGate(2, clock=clock)
        gate.admit()
        gate.admit()
        assert gate.admit() is False
        assert gate.suppressed == 1

    def test_window_slides_so_old_moments_stop_counting(self) -> None:
        clock = FakeClock()
        gate = moments.MomentRateGate(1, clock=clock)
        assert gate.admit() is True
        clock.advance(59)
        assert gate.admit() is False  # 59s in: still inside the rolling minute
        clock.advance(2)
        assert gate.admit() is True  # 61s in: the first moment left the window

    def test_zero_limit_surfaces_nothing(self) -> None:
        gate = moments.MomentRateGate(0, clock=FakeClock())
        assert gate.admit() is False

    def test_take_summary_reports_then_resets(self) -> None:
        clock = FakeClock()
        gate = moments.MomentRateGate(1, clock=clock)
        gate.admit()
        gate.admit()
        gate.admit()
        assert gate.take_summary() == "+2 more moments withheld (agent rate cap: 1/min)"
        assert gate.suppressed == 0
        assert gate.take_summary() is None

    def test_take_summary_singularises_one_moment(self) -> None:
        gate = moments.MomentRateGate(1, clock=FakeClock())
        gate.admit()
        gate.admit()
        assert gate.take_summary() == "+1 more moment withheld (agent rate cap: 1/min)"

    def test_limit_exposed_for_reporting(self) -> None:
        assert moments.MomentRateGate(7, clock=FakeClock()).limit == 7


# --- the disabled fault -------------------------------------------------------


class TestMomentsDisabled:
    def test_message_names_the_deciding_file_and_the_way_back(self, moments_config: Path) -> None:
        moments_config.write_text('[moments]\nagents = "off"\n')
        settings = moments.load_settings(home=moments_config.parent)
        exc = moments.MomentsDisabled(settings)
        assert 'agents = "off"' in str(exc)
        assert str(moments_config) in str(exc)
        assert "`spec-kitty moments on`" in str(exc)
