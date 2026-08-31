"""Regression tests for contributors API pagination."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest

pytestmark = [pytest.mark.fast, pytest.mark.unit]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "sync_all_contributors.py"


def _load_script_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sync_all_contributors", _SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot build an import spec for {_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sync_all_contributors = _load_script_module()


def _page_command(repo: str, page: int) -> list[str]:
    return ["gh", "api", f"repos/{repo}/contributors?per_page=100&page={page}"]


def test_load_contributors_api_paginates_past_100(monkeypatch: pytest.MonkeyPatch) -> None:
    pages: dict[int, list[dict[str, str]]] = {
        1: [{"login": f"contributor-{index:03d}", "type": "User"} for index in range(100)],
        2: [{"login": "contributor-100", "type": "User"}],
    }
    calls: list[list[str]] = []

    def fake_run_json(cmd: list[str]) -> object:
        calls.append(cmd)
        page = int(cmd[-1].rsplit("page=", 1)[1])
        return pages.get(page, [])

    monkeypatch.setattr(sync_all_contributors, "run_json", fake_run_json)
    result = sync_all_contributors.load_contributors_api("owner/repo", re.compile(sync_all_contributors.DEFAULT_DENY_REGEX, re.IGNORECASE))

    assert calls == [_page_command("owner/repo", 1), _page_command("owner/repo", 2)]
    assert result == {f"contributor-{index:03d}" for index in range(101)}


def test_load_contributors_api_continues_past_all_bot_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages: dict[int, list[dict[str, str]]] = {
        1: [{"login": f"bot-{index:03d}", "type": "Bot"} for index in range(100)],
        2: [],
    }
    calls: list[list[str]] = []

    def fake_run_json(cmd: list[str]) -> object:
        calls.append(cmd)
        page = int(cmd[-1].rsplit("page=", 1)[1])
        return pages.get(page, [])

    monkeypatch.setattr(sync_all_contributors, "run_json", fake_run_json)
    result = sync_all_contributors.load_contributors_api("owner/repo", re.compile(sync_all_contributors.DEFAULT_DENY_REGEX, re.IGNORECASE))

    assert calls == [_page_command("owner/repo", 1), _page_command("owner/repo", 2)]
    assert result == set()
