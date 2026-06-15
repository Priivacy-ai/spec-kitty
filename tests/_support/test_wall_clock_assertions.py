from __future__ import annotations

from pathlib import Path

import pytest

from tests._support.wall_clock_assertions import (
    find_wall_clock_assertion_violations,
    find_test_python_paths,
    format_wall_clock_assertion_violations,
)


@pytest.mark.parametrize(
    ("source", "expected", "expected_line"),
    [
        ("from datetime import datetime\n\ndef test_bad():\n    assert value == datetime.now().isoformat()\n", "datetime.now()", 4),
        ("from datetime import datetime\n\ndef test_bad():\n    assert value == datetime.utcnow().isoformat()\n", "datetime.utcnow()", 4),
        ("from datetime import datetime\n\ndef test_bad():\n    assert value == datetime.today().isoformat()\n", "datetime.today()", 4),
        ("from datetime import date\n\ndef test_bad():\n    assert value == date.today().isoformat()\n", "date.today()", 4),
        ("import datetime\n\ndef test_bad():\n    assert value == datetime.datetime.now().isoformat()\n", "datetime.datetime.now()", 4),
        ("import datetime\n\ndef test_bad():\n    assert value == datetime.date.today().isoformat()\n", "datetime.date.today()", 4),
        ("import datetime\n\ndef test_bad():\n    assert value == datetime.datetime.today().isoformat()\n", "datetime.datetime.today()", 4),
        ("import time\n\ndef test_bad():\n    assert value < time.time()\n", "time.time()", 4),
        ("from datetime import datetime as dt\n\ndef test_bad():\n    assert value == dt.now().isoformat()\n", "dt.now()", 4),
        ("from datetime import datetime as dt\n\ndef test_bad():\n    assert value == dt.today().isoformat()\n", "dt.today()", 4),
        ("import datetime as dt_mod\n\ndef test_bad():\n    assert value == dt_mod.datetime.now().isoformat()\n", "dt_mod.datetime.now()", 4),
        ("from time import time as wall_time\n\ndef test_bad():\n    assert value < wall_time()\n", "wall_time()", 4),
        ("from datetime import datetime\n\nwall_now = datetime.now\n\ndef test_bad():\n    assert wall_now().year == 2026\n", "wall_now()", 6),
        ("from datetime import datetime\n\nwall_today = datetime.today\n\ndef test_bad():\n    assert wall_today().year == 2026\n", "wall_today()", 6),
        ("from datetime import datetime\n\ndef test_bad():\n    wall_now = datetime.now\n    assert wall_now().year == 2026\n", "wall_now()", 5),
        ("from time import *\n\ndef test_bad():\n    assert time() > 0\n", "time()", 4),
        ("from datetime import *\n\ndef test_bad():\n    assert datetime.now().year == 2026\n", "datetime.now()", 4),
        ("import datetime\n\ndt = datetime.datetime\n\ndef test_bad():\n    assert dt.now().year == 2026\n", "dt.now()", 6),
        ("from datetime import datetime\n\ndt = datetime\n\ndef test_bad():\n    assert dt.now().year == 2026\n", "dt.now()", 6),
        ("from datetime import datetime\n\ndt = datetime\n\ndef test_bad():\n    assert dt.today().year == 2026\n", "dt.today()", 6),
        ("from datetime import date\n\nd = date\n\ndef test_bad():\n    assert d.today().year == 2026\n", "d.today()", 6),
        ("from datetime import *\n\ndt = datetime\n\ndef test_bad():\n    assert dt.now().year == 2026\n", "dt.now()", 6),
        ("import time\n\ntm = time\n\ndef test_bad():\n    assert tm.time() > 0\n", "tm.time()", 6),
        (
            "from datetime import datetime\n\n"
            "class Holder:\n"
            "    pass\n\n"
            "Holder.wall_now = datetime.now\n\n"
            "def test_bad():\n"
            "    assert Holder.wall_now().year == 2026\n",
            "Holder.wall_now()",
            9,
        ),
        (
            "from datetime import datetime\n\n"
            "class Holder:\n"
            "    wall_now = datetime.now\n\n"
            "def test_bad():\n"
            "    assert Holder.wall_now().year == 2026\n",
            "Holder.wall_now()",
            7,
        ),
        (
            "from datetime import datetime\n\n"
            "class Holder:\n"
            "    wall_now = datetime.now\n\n"
            "    def test_bad(self):\n"
            "        assert self.wall_now().year == 2026\n",
            "self.wall_now()",
            7,
        ),
        (
            "from datetime import datetime\n\n"
            "class Holder:\n"
            "    wall_now = datetime.now\n\n"
            "    @classmethod\n"
            "    def test_bad(cls):\n"
            "        assert cls.wall_now().year == 2026\n",
            "cls.wall_now()",
            8,
        ),
        (
            "from datetime import datetime\n\n"
            "class Holder:\n"
            "    wall_now = datetime.now\n\n"
            "    @staticmethod\n"
            "    def test_bad(self):\n"
            "        assert self.wall_now().year == 2026\n",
            "self.wall_now()",
            8,
        ),
        ("from datetime import datetime\n\nwall_now, other = datetime.now, object()\n\ndef test_bad():\n    assert wall_now().year == 2026\n", "wall_now()", 6),
        (
            "from datetime import datetime\n\n"
            "def test_bad(wall_now=datetime.now):\n"
            "    assert wall_now().year == 2026\n",
            "wall_now()",
            4,
        ),
        (
            "from datetime import datetime\n\n"
            "def test_bad():\n"
            "    assert (wall_now := datetime.now)().year == 2026\n",
            "wall_now()",
            4,
        ),
        (
            "from datetime import datetime\n\n"
            "def test_bad():\n"
            "    assert (dt := datetime).now().year == 2026\n",
            "dt.now()",
            4,
        ),
        (
            "from datetime import datetime\n\n"
            "class Holder:\n"
            "    wall_now = staticmethod(datetime.now)\n\n"
            "def test_bad():\n"
            "    assert Holder.wall_now().year == 2026\n",
            "Holder.wall_now()",
            7,
        ),
        (
            "from datetime import datetime\n\n"
            "class Holder:\n"
            "    wall_now = staticmethod(datetime.now)\n\n"
            "    def test_bad(self):\n"
            "        assert self.wall_now().year == 2026\n",
            "self.wall_now()",
            7,
        ),
        (
            "from datetime import datetime\n\n"
            "def setup_module():\n"
            "    global wall_now\n"
            "    wall_now = datetime.now\n\n"
            "def test_bad():\n"
            "    assert wall_now().year == 2026\n",
            "wall_now()",
            8,
        ),
        (
            "from datetime import datetime\n\n"
            "class TestClock:\n"
            "    def setup_method(self):\n"
            "        self.wall_now = datetime.now\n\n"
            "    def test_bad(self):\n"
            "        assert self.wall_now().year == 2026\n",
            "self.wall_now()",
            8,
        ),
        (
            "from typing import TYPE_CHECKING\n"
            "from datetime import datetime\n\n"
            "if TYPE_CHECKING:\n"
            "    from fake_datetime import datetime\n\n"
            "def test_bad():\n"
            "    assert datetime.now().year == 2026\n",
            "datetime.now()",
            8,
        ),
        (
            "from datetime import datetime\n\n"
            "if False:\n"
            "    from fake_datetime import datetime\n\n"
            "def test_bad():\n"
            "    assert datetime.now().year == 2026\n",
            "datetime.now()",
            7,
        ),
    ],
)
def test_find_wall_clock_assertion_violations_flags_direct_assert_calls(
    tmp_path: Path,
    source: str,
    expected: str,
    expected_line: int,
) -> None:
    test_file = tmp_path / "test_bad.py"
    test_file.write_text(source, encoding="utf-8")

    violations = find_wall_clock_assertion_violations([test_file])

    assert len(violations) == 1
    assert violations[0].call == expected
    assert violations[0].line == expected_line


def test_find_wall_clock_assertion_violations_allows_injected_now(tmp_path: Path) -> None:
    test_file = tmp_path / "test_good.py"
    test_file.write_text(
        "from datetime import UTC, datetime\n\n"
        "def test_good():\n"
        "    now = datetime(2026, 4, 22, 12, 0, tzinfo=UTC)\n"
        "    result = build_payload(now=now)\n"
        "    assert result['created_at'] == now.isoformat()\n",
        encoding="utf-8",
    )

    assert find_wall_clock_assertion_violations([test_file]) == []


def test_find_wall_clock_assertion_violations_allows_freshness_bounds(tmp_path: Path) -> None:
    test_file = tmp_path / "test_bounds.py"
    test_file.write_text(
        "from datetime import UTC, datetime\n\n"
        "def test_bounds():\n"
        "    before = datetime.now(UTC)\n"
        "    event = make_event()\n"
        "    after = datetime.now(UTC)\n"
        "    assert before <= event.timestamp <= after\n",
        encoding="utf-8",
    )

    assert find_wall_clock_assertion_violations([test_file]) == []


@pytest.mark.parametrize(
    "source",
    [
        (
            "from datetime import datetime\n\n"
            "class FakeDateTime:\n"
            "    @classmethod\n"
            "    def now(cls):\n"
            "        return 1\n\n"
            "def test_good():\n"
            "    datetime = FakeDateTime\n"
            "    assert datetime.now() == 1\n"
        ),
        (
            "from datetime import datetime\n\n"
            "def helper():\n"
            "    wall_now = datetime.now\n"
            "    return wall_now\n\n"
            "def test_good():\n"
            "    wall_now = lambda: 1\n"
            "    assert wall_now() == 1\n"
        ),
        (
            "from datetime import datetime\n\n"
            "class Holder:\n"
            "    wall_now = datetime.now\n\n"
            "    def test_good(self):\n"
            "        wall_now = lambda: 1\n"
            "        assert wall_now() == 1\n"
        ),
        (
            "from datetime import datetime\n"
            "from fake_datetime import datetime\n\n"
            "def test_good():\n"
            "    assert datetime.now() == 1\n"
        ),
        (
            "from datetime import datetime as dt\n"
            "from fake_datetime import datetime as dt\n\n"
            "def test_good():\n"
            "    assert dt.now() == 1\n"
        ),
        (
            "from datetime import datetime\n"
            "from fake_datetime import *\n\n"
            "def test_good():\n"
            "    assert datetime.now() == 1\n"
        ),
        (
            "from datetime import datetime\n\n"
            "class Holder:\n"
            "    pass\n\n"
            "Holder.wall_now = datetime.now\n\n"
            "class Fake:\n"
            "    @staticmethod\n"
            "    def wall_now():\n"
            "        return 1\n\n"
            "Holder = Fake\n\n"
            "def test_good():\n"
            "    assert Holder.wall_now() == 1\n"
        ),
        (
            "from datetime import datetime\n\n"
            "class FakeDateTime:\n"
            "    @staticmethod\n"
            "    def now():\n"
            "        return 1\n\n"
            "def test_good():\n"
            "    assert (lambda datetime: datetime.now())(FakeDateTime) == 1\n"
        ),
        (
            "from datetime import datetime\n\n"
            "values = [type('FakeDateTime', (), {'now': staticmethod(lambda: 1)})]\n\n"
            "def test_good():\n"
            "    assert [datetime.now() for datetime in values] == [1]\n"
        ),
        (
            "from datetime import datetime\n\n"
            "wall_now = lambda: 1\n\n"
            "def helper():\n"
            "    global wall_now\n"
            "    wall_now = datetime.now\n\n"
            "def test_good():\n"
            "    assert wall_now() == 1\n"
        ),
        (
            "from datetime import datetime\n\n"
            "class TestClock:\n"
            "    def setup_method(self):\n"
            "        self.wall_now = datetime.now\n"
            "        self.wall_now = lambda: 1\n\n"
            "    def test_good(self):\n"
            "        assert self.wall_now() == 1\n"
        ),
        (
            "from datetime import datetime\n\n"
            "class TestClock:\n"
            "    def setup_method(self):\n"
            "        def helper():\n"
            "            self.wall_now = datetime.now\n\n"
            "    def test_good(self):\n"
            "        self.wall_now = lambda: 1\n"
            "        assert self.wall_now() == 1\n"
        ),
    ],
)
def test_find_wall_clock_assertion_violations_respects_local_shadowing(tmp_path: Path, source: str) -> None:
    test_file = tmp_path / "test_good.py"
    test_file.write_text(source, encoding="utf-8")

    assert find_wall_clock_assertion_violations([test_file]) == []


def test_find_test_python_paths_includes_helper_modules(tmp_path: Path) -> None:
    tests_root = tmp_path / "tests"
    helper_file = tests_root / "helpers" / "bad_helper.py"
    test_file = tests_root / "test_uses_helper.py"
    helper_file.parent.mkdir(parents=True)
    helper_file.write_text("def helper():\n    pass\n", encoding="utf-8")
    test_file.write_text("def test_uses_helper():\n    pass\n", encoding="utf-8")

    assert find_test_python_paths(tests_root) == [helper_file, test_file]


def test_format_wall_clock_assertion_violations_names_injection_pattern(tmp_path: Path) -> None:
    test_file = tmp_path / "test_bad.py"
    test_file.write_text(
        "from datetime import datetime\n\n"
        "def test_bad():\n"
        "    assert datetime.now().year == 2026\n",
        encoding="utf-8",
    )
    violations = find_wall_clock_assertion_violations([test_file])

    message = format_wall_clock_assertion_violations(violations)

    assert "Inject a stable `now=`/clock" in message
    assert "test_bad.py:4: datetime.now()" in message
