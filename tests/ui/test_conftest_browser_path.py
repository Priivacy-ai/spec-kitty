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
    expected = fake_cache / "chromium_headless_shell-1234"
    expected.mkdir(parents=True)

    with (
        mock.patch.dict("os.environ", {"PLAYWRIGHT_BROWSERS_PATH": str(fake_cache)}),
        mock.patch.object(conftest, "_expected_chromium_headless_shell_dir", return_value=expected),
    ):
        assert conftest._chromium_is_installed() is True


def test_chromium_check_false_when_default_cache_has_no_chromium(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    conftest = _load_ui_conftest()
    empty_cache = tmp_path / "ms-playwright"
    empty_cache.mkdir()
    (empty_cache / "ffmpeg-1011").mkdir()  # a non-chromium browser build
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    monkeypatch.setattr(conftest, "_default_playwright_browsers_path", lambda: empty_cache)
    monkeypatch.setattr(conftest, "_expected_chromium_headless_shell_dir", lambda _path: None)

    assert conftest._chromium_is_installed() is False


def test_chromium_check_false_on_stale_build_with_wrong_revision(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression for #84: a differently-numbered cached build must not pass.

    Reproduced on sk-squad-spec-kitty-79: the cache held
    ``chromium_headless_shell-1217`` while the lockfile-pinned Playwright wanted
    1228. The old bare ``chromium-*`` glob accepted the stale build and the suite
    HARD-ERRORed mid-run at browser launch instead of skipping.
    """
    conftest = _load_ui_conftest()
    cache = tmp_path / "ms-playwright"
    (cache / "chromium_headless_shell-1217").mkdir(parents=True)  # stale build
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    monkeypatch.setattr(conftest, "_default_playwright_browsers_path", lambda: cache)
    monkeypatch.setattr(
        conftest,
        "_expected_chromium_headless_shell_dir",
        lambda _path: cache / "chromium_headless_shell-1228",  # pinned build, absent
    )

    assert conftest._chromium_is_installed() is False


def test_expected_chromium_headless_shell_dir_parses_dry_run_install_location(
    tmp_path: Path,
) -> None:
    conftest = _load_ui_conftest()
    dry_run_output = (
        "Chrome for Testing 149.0.7827.55 (playwright chromium v1228)\n"
        f"  Install location:    {tmp_path}/chromium-1228\n"
        "  Download url:        https://cdn.playwright.dev/...\n"
        "\n"
        "Chrome Headless Shell 149.0.7827.55 (playwright chromium-headless-shell v1228)\n"
        f"  Install location:    {tmp_path}/chromium_headless_shell-1228\n"
        "  Download url:        https://cdn.playwright.dev/...\n"
    )
    fake_result = mock.Mock(returncode=0, stdout=dry_run_output)

    with mock.patch.object(conftest.subprocess, "run", return_value=fake_result) as run:
        resolved = conftest._expected_chromium_headless_shell_dir(tmp_path)

    assert resolved == Path(f"{tmp_path}/chromium_headless_shell-1228")
    run.assert_called_once()


def test_expected_chromium_headless_shell_dir_none_on_cli_failure(tmp_path: Path) -> None:
    conftest = _load_ui_conftest()
    fake_result = mock.Mock(returncode=1, stdout="")

    with mock.patch.object(conftest.subprocess, "run", return_value=fake_result):
        assert conftest._expected_chromium_headless_shell_dir(tmp_path) is None


def test_expected_chromium_headless_shell_dir_none_when_cli_raises(tmp_path: Path) -> None:
    conftest = _load_ui_conftest()

    with mock.patch.object(conftest.subprocess, "run", side_effect=OSError("no node")):
        assert conftest._expected_chromium_headless_shell_dir(tmp_path) is None
