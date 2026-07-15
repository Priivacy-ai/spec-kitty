"""Single-source driver + import-time-I/O regression guard for charter (WP02, #2669).

Covers (T006):

1. **RED-first single-source driver** — a synthetic mission-type YAML injected
   via a monkeypatched ``MissionTypeRepository.default`` root (C-010 test
   seam) must flow through to ``PackContext.from_config``'s default
   ``activated_mission_types`` set. Before T008, ``pack_context.py`` derives
   its default from a hardcoded ``_BUILTIN_MISSION_TYPE_IDS`` literal that
   ignores the accessor entirely, so this test is genuinely RED until the
   Roster B lazy-derivation lands.

2. **Import-time-I/O regression guard (green-stays-green)** — importing the
   two "hot" charter modules (``charter.mission_type_profiles``,
   ``charter.pack_context``) must trigger ZERO reads of the doctrine
   ``mission_types/`` directory (NFR-001). This passes today (both modules
   only carry literals at import time) and must keep passing once Roster B's
   accessor call moves inside ``_read_activated_mission_types`` — the call
   must stay function-local, never fire at module scope. Run in a subprocess
   so the spy observes a genuine fresh import, not a module already cached in
   this test session's ``sys.modules``.

   ``charter.activations`` / ``charter.interview_mapping`` are explicitly
   NOT covered here — those two derive their own rosters at module scope by
   design (C-012 carve-out); a ``<=1`` cached read there is expected and is
   not this WP's concern.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import textwrap
from collections.abc import Iterator
from pathlib import Path

import pytest

from charter.pack_context import PackContext
from doctrine.missions.mission_type_repository import (
    MissionTypeRepository,
    builtin_mission_type_ids,
)

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

_SHIPPED_MISSION_TYPES_DIR = (
    Path(__file__).resolve().parents[2] / "src" / "doctrine" / "missions" / "mission_types"
)

_SYNTHETIC_ANALYSIS_YAML = (
    "schema_version: 1\n"
    "id: analysis\n"
    'display_name: "Analysis"\n'
    "action_sequence:\n"
    "  - specify\n"
    "  - plan\n"
)

_MINIMAL_CONFIG = """\
vcs:
  type: git
agents:
  available:
    - claude
"""


@pytest.fixture(autouse=True)
def _clear_builtin_mission_type_ids_cache() -> Iterator[None]:
    """Reset the process-wide ``functools.cache`` before and after each test.

    Mirrors the C-010 seam fixture in
    ``tests/doctrine/missions/test_builtin_mission_type_ids.py`` — a
    monkeypatched root must not leak a cached value into another test
    (including other modules under ``-n auto``).
    """
    builtin_mission_type_ids.cache_clear()
    yield
    builtin_mission_type_ids.cache_clear()


def _write_config(project_root: Path, content: str) -> None:
    kittify = project_root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "config.yaml").write_text(content, encoding="utf-8")


def _patch_default_root(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    """Monkeypatch ``MissionTypeRepository.default`` to load from *root* (C-010)."""

    def _fake_default(cls: type[MissionTypeRepository]) -> MissionTypeRepository:
        return cls(root)

    monkeypatch.setattr(MissionTypeRepository, "default", classmethod(_fake_default))


# ---------------------------------------------------------------------------
# 1. RED-first single-source driver
# ---------------------------------------------------------------------------


class TestDefaultActivationSetIsSingleSourced:
    """``PackContext``'s default activation set derives from the WP01 accessor."""

    def test_default_activated_mission_types_includes_synthetic_type(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A synthetic mission-type injected via the accessor root flows through
        to ``PackContext.from_config``'s default set (no ``mission_type_activations``
        key in config.yaml).

        RED before T008: today's ``_BUILTIN_MISSION_TYPE_IDS`` is a hardcoded
        4-tuple literal in ``pack_context.py`` that never consults
        ``MissionTypeRepository`` at all, so the monkeypatched synthetic type
        cannot appear in the result no matter what the accessor root is.
        """
        mission_types_root = tmp_path / "mission_types"
        mission_types_root.mkdir()
        for shipped_yaml in _SHIPPED_MISSION_TYPES_DIR.glob("*.yaml"):
            shutil.copy(shipped_yaml, mission_types_root / shipped_yaml.name)
        (mission_types_root / "analysis.yaml").write_text(
            _SYNTHETIC_ANALYSIS_YAML, encoding="utf-8"
        )

        _patch_default_root(monkeypatch, mission_types_root)
        builtin_mission_type_ids.cache_clear()

        project_root = tmp_path / "project"
        _write_config(project_root, _MINIMAL_CONFIG)

        ctx = PackContext.from_config(project_root)

        assert "analysis" in ctx.activated_mission_types


# ---------------------------------------------------------------------------
# 2. Import-time-I/O regression guard (green-stays-green)
# ---------------------------------------------------------------------------


_IMPORT_SPY_SCRIPT = textwrap.dedent(
    """\
    import sys

    from doctrine.missions.mission_type_repository import MissionTypeRepository

    _calls: list[int] = []
    _orig_default = MissionTypeRepository.default.__func__

    def _spy(cls):
        _calls.append(1)
        return _orig_default(cls)

    MissionTypeRepository.default = classmethod(_spy)

    import charter.mission_type_profiles  # noqa: F401
    import charter.pack_context  # noqa: F401

    if _calls:
        print(f"MissionTypeRepository.default() called {len(_calls)} time(s) at import time", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
    """
)


class TestHotModulesTriggerZeroImportTimeIo:
    """Importing the two hot charter modules must not read ``mission_types/``.

    Runs in a subprocess so the spy observes a genuine fresh import — pytest
    collection has already imported both modules by the time this test body
    runs, so an in-process ``importlib.reload`` would not reliably surface a
    module-scope accessor call cached from an earlier import in the same
    session.
    """

    def test_import_charter_mission_type_profiles_and_pack_context_is_io_free(self) -> None:
        result = subprocess.run(
            [sys.executable, "-c", _IMPORT_SPY_SCRIPT],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, (
            "importing charter.mission_type_profiles / charter.pack_context "
            f"triggered mission_types/ I/O (NFR-001):\nstdout={result.stdout}\nstderr={result.stderr}"
        )
