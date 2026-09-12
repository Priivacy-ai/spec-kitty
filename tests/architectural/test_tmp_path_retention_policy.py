"""``tmp_path_retention_policy = failed`` in ``pytest.ini`` is #63's actual fix.

pytest's ``all`` default keeps every test's ``tmp_path`` alive for the whole
session; across ``make test-full``'s tens of thousands of tests that alone
exhausts the runner's temp filesystem (#63). ``failed`` frees a passing
test's ``tmp_path`` at its own fixture teardown instead of waiting for
session end -- see ``tests/_support/run_basetemp.py``'s module docstring.

Before this file, nothing in the test tree asserted the ini value
programmatically (only prose mentions in ``tests/conftest.py``,
``tests/_support/run_basetemp.py``, and
``tests/architectural/test_home_pin_scan_limbs.py``). A revert of that one
line would pass every test with zero failures to notice, and CI would only
rediscover the regression as a pre-summary disk-exhaustion crash on
``make test-full`` (#86, from squad pass 2 on PR #72).
"""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural]

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _pytest_ini_value(option: str) -> str | None:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(_REPO_ROOT / "pytest.ini", encoding="utf-8")
    return parser.get("pytest", option, fallback=None)


def test_tmp_path_retention_policy_is_failed() -> None:
    assert _pytest_ini_value("tmp_path_retention_policy") == "failed", (
        "pytest.ini's `tmp_path_retention_policy` must stay `failed` -- this is #63's "
        "actual disk/inode exhaustion fix (pytest's `all` default keeps every passing "
        "test's tmp_path alive for the whole session). A revert would pass every test "
        "with zero failures and only be rediscovered by CI as a disk-exhaustion crash. "
        "See tests/_support/run_basetemp.py's module docstring."
    )
