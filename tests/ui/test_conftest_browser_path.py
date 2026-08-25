"""Unit coverage for tests/ui/conftest.py's Chromium-path resolution (#66).

``_chromium_is_installed`` decides whether the whole ``tests/ui/`` suite skips.
It used to probe the Linux cache path unconditionally, so on macOS — where
Playwright caches browsers under ``~/Library/Caches/ms-playwright`` — the check
saw an empty directory, reported Chromium missing, and silently skipped the
e2e regression guard that had just gone red on main (#66).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest import mock

import pytest

pytestmark = pytest.mark.fast


def _load_ui_conftest():
    """Import ``tests/ui/conftest.py`` as a plain module (no package __init__)."""
    spec = importlib.util.spec_from_file_location("_ui_conftest_under_test", Path(__file__).parent / "conftest.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("platform", "expected_tail"),
    [
        ("linux", (".cache", "ms-playwright")),
        ("darwin", ("Library", "Caches", "ms-playwright")),
        ("win32", ("AppData", "Local", "ms-playwright")),
    ],
)
def test_default_browsers_path_follows_playwright_per_platform(platform: str, expected_tail: tuple[str, ...]) -> None:
    conftest = _load_ui_conftest()
    with mock.patch.object(sys, "platform", platform):
        resolved = conftest._default_playwright_browsers_path()

    assert resolved.is_absolute()
    assert resolved.parts[-len(expected_tail) :] == expected_tail


def test_chromium_check_prefers_env_var_over_platform_default(tmp_path: Path) -> None:
    conftest = _load_ui_conftest()
    fake_cache = tmp_path / "browsers"
    (fake_cache / "chromium-1234").mkdir(parents=True)

    with mock.patch.dict("os.environ", {"PLAYWRIGHT_BROWSERS_PATH": str(fake_cache)}):
        assert conftest._chromium_is_installed() is True


def test_chromium_check_false_when_default_cache_has_no_chromium(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    conftest = _load_ui_conftest()
    empty_cache = tmp_path / "ms-playwright"
    empty_cache.mkdir()
    (empty_cache / "ffmpeg-1011").mkdir()  # a non-chromium browser build
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    monkeypatch.setattr(conftest, "_default_playwright_browsers_path", lambda: empty_cache)

    assert conftest._chromium_is_installed() is False
