"""
E2E tests for mission collaboration CLI against real SaaS dev environment.

Tests verify all 5 success criteria:
1. 0 warnings when focus differs (concurrent development)
2. 100% collision detection, < 500ms latency
3. < 30s handoff, 0 lock releases
4. 100% replay success for roster participants, < 10s latency
5. Adapter equivalence (verified in contract tests)

Prerequisites:
- SaaS dev environment with mission API deployed
- Set SAAS_DEV_URL and SAAS_DEV_API_KEY environment variables

Example:
    export SAAS_DEV_URL=https://dev.spec-kitty-saas.com
    export SAAS_DEV_API_KEY=<dev-api-key>
    pytest tests/e2e/test_collaboration_scenario.py -v
"""

import pytest
import os
import time
from unittest.mock import patch
import httpx
from pathlib import Path

from specify_cli.collaboration.service import join_mission, set_focus, set_drive
from specify_cli.collaboration.state import get_mission_roster
from specify_cli.events.store import read_pending_events
from specify_cli.events.replay import replay_pending_events


@pytest.fixture
def saas_env():
    """Load SaaS dev environment config."""
    url = os.getenv("SAAS_DEV_URL")
    api_key = os.getenv("SAAS_DEV_API_KEY")

    if not url or not api_key:
        pytest.skip("SAAS_DEV_URL and SAAS_DEV_API_KEY required for E2E tests")

    return {"url": url, "api_key": api_key}


@pytest.fixture
def test_mission(saas_env):
    """Create test mission via SaaS API."""
    response = httpx.post(
        f"{saas_env['url']}/api/v1/missions",
        json={"title": "E2E Test Mission"},
        headers={"Authorization": f"Bearer {saas_env['api_key']}"},
        timeout=10.0,
    )
    response.raise_for_status()

    mission_id = response.json()["mission_id"]
    yield mission_id

    # Cleanup
    try:
        httpx.delete(
            f"{saas_env['url']}/api/v1/missions/{mission_id}",
            headers={"Authorization": f"Bearer {saas_env['api_key']}"},
            timeout=10.0,
        )
    except httpx.HTTPError:
        pass  # Best effort cleanup


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    """
    Isolate HOME directory for each test to prevent session file contamination.

    Each test gets a fresh HOME directory in tmp_path, ensuring:
    - Separate session files for each participant
    - No cross-test state pollution
    - Clean queue storage
    """
    home_dir = tmp_path / "home"
    home_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home_dir))
    return home_dir


def test_concurrent_development(saas_env, test_mission, isolated_home, monkeypatch):
    """
    Success Criterion #1: Concurrent development without false-positive warnings.

    Scenario:
    - Participant A and B join mission
    - A sets focus=wp:WP01, drive=active
    - B sets focus=wp:WP02, drive=active
    - Verify: No collision warnings (different focus targets)
    """
    mission_id = test_mission

    # Create separate HOME directories for each participant
    home_a = isolated_home / "participant_a"
    home_b = isolated_home / "participant_b"
    home_a.mkdir(parents=True, exist_ok=True)
    home_b.mkdir(parents=True, exist_ok=True)

    # Participant A joins
    monkeypatch.setenv("HOME", str(home_a))
    result_a = join_mission(
        mission_id, "developer", saas_env["url"], f"{saas_env['api_key']}-a"
    )
    assert result_a["participant_id"]

    # A: focus=wp:WP01, drive=active
    set_focus(mission_id, "wp:WP01")
    result = set_drive(mission_id, "active")
    assert "collision" not in result  # No collision

    # Participant B joins (different HOME)
    monkeypatch.setenv("HOME", str(home_b))
    result_b = join_mission(
        mission_id, "developer", saas_env["url"], f"{saas_env['api_key']}-b"
    )
    assert result_b["participant_id"]

    # B: focus=wp:WP02, drive=active
    set_focus(mission_id, "wp:WP02")
    result = set_drive(mission_id, "active")
    assert "collision" not in result  # No collision

    # Verify status (from any participant's perspective)
    roster = get_mission_roster(mission_id)
    assert len(roster) == 2
    assert sum(1 for p in roster if p.drive_intent == "active") == 2


def test_collision_detection(saas_env, test_mission, isolated_home, monkeypatch):
    """
    Success Criterion #2: 100% collision detection, < 500ms latency.

    Scenario:
    - Participant A: focus=wp:WP01, drive=active
    - Participant B: focus=wp:WP01, drive=active (should trigger warning)
    - Verify: ConcurrentDriverWarning emitted within 500ms
    """
    mission_id = test_mission

    # Create separate HOME directories for each participant
    home_a = isolated_home / "participant_a"
    home_b = isolated_home / "participant_b"
    home_a.mkdir(parents=True, exist_ok=True)
    home_b.mkdir(parents=True, exist_ok=True)

    # Participant A joins and activates
    monkeypatch.setenv("HOME", str(home_a))
    join_mission(mission_id, "developer", saas_env["url"], f"{saas_env['api_key']}-a")
    set_focus(mission_id, "wp:WP01")
    set_drive(mission_id, "active")

    # Participant B joins (different HOME)
    monkeypatch.setenv("HOME", str(home_b))
    join_mission(mission_id, "developer", saas_env["url"], f"{saas_env['api_key']}-b")
    set_focus(mission_id, "wp:WP01")

    # Measure collision detection latency
    start = time.time()
    result = set_drive(mission_id, "active")
    latency_ms = (time.time() - start) * 1000

    # Assertions
    assert "collision" in result  # Collision detected
    assert result["collision"]["type"] == "ConcurrentDriverWarning"
    assert latency_ms < 500  # p99 latency < 500ms


def test_organic_handoff(saas_env, test_mission, isolated_home, monkeypatch):
    """
    Success Criterion #3: Organic handoff < 30s, 0 explicit lock releases.

    Scenario:
    - Participant A: focus=wp:WP01, drive=active
    - Participant A: focus=wp:WP02 (implicitly releases WP01)
    - Participant B: focus=wp:WP01, drive=active (no collision)
    - Verify: Handoff completes without explicit lock release
    """
    mission_id = test_mission

    # Create separate HOME directories for each participant
    home_a = isolated_home / "participant_a"
    home_b = isolated_home / "participant_b"
    home_a.mkdir(parents=True, exist_ok=True)
    home_b.mkdir(parents=True, exist_ok=True)

    # Participant A activates WP01
    monkeypatch.setenv("HOME", str(home_a))
    join_mission(mission_id, "developer", saas_env["url"], f"{saas_env['api_key']}-a")
    set_focus(mission_id, "wp:WP01")
    set_drive(mission_id, "active")

    # Participant B joins (different HOME)
    monkeypatch.setenv("HOME", str(home_b))
    join_mission(mission_id, "developer", saas_env["url"], f"{saas_env['api_key']}-b")

    # A switches to WP02 (implicit release)
    monkeypatch.setenv("HOME", str(home_a))
    start = time.time()
    set_focus(mission_id, "wp:WP02")

    # B claims WP01
    monkeypatch.setenv("HOME", str(home_b))
    set_focus(mission_id, "wp:WP01")
    result = set_drive(mission_id, "active")
    handoff_time = time.time() - start

    # Assertions
    assert "collision" not in result  # No collision after A released
    assert handoff_time < 30  # Handoff < 30s


def test_offline_replay(saas_env, test_mission, isolated_home, monkeypatch):
    """
    Success Criterion #4: Offline work replays successfully in < 10s.

    Scenario:
    - Participant C joins online
    - C works offline (4 commands)
    - C reconnects and replays events
    - Verify: All 4 events accepted, < 10s replay latency
    """
    mission_id = test_mission

    # Create separate HOME directory for participant C
    home_c = isolated_home / "participant_c"
    home_c.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home_c))

    # C joins online
    join_mission(mission_id, "developer", saas_env["url"], f"{saas_env['api_key']}-c")

    # Simulate offline work (mock is_online to return False)
    with patch("specify_cli.events.store.is_online", return_value=False):
        set_focus(mission_id, "wp:WP01")
        set_drive(mission_id, "active")
        # 2 more commands (focus change and drive deactivate)
        set_focus(mission_id, "wp:WP02")
        set_drive(mission_id, "inactive")

    # Verify events queued
    pending = read_pending_events(mission_id)
    assert len(pending) >= 4  # At least 4 commands (may include join event)

    # Reconnect and replay
    start = time.time()
    result = replay_pending_events(
        mission_id, saas_env["url"], f"{saas_env['api_key']}-c"
    )
    replay_time = time.time() - start

    # Assertions
    assert len(result["accepted"]) >= 4  # All offline commands accepted
    assert len(result["rejected"]) == 0  # No rejections (C in roster)
    assert replay_time < 10  # Replay < 10s


@pytest.mark.slow
def test_full_scenario(saas_env, isolated_home, monkeypatch):
    """
    Combined scenario: All success criteria in one test.

    This test runs all sub-tests sequentially to verify end-to-end workflow.
    All 4 success criteria are tested (criteria #5 is in contract tests).
    """
    # Create fresh missions for each test to avoid state pollution

    # Test #1: Concurrent development
    response = httpx.post(
        f"{saas_env['url']}/api/v1/missions",
        json={"title": "E2E Test Mission - Concurrent"},
        headers={"Authorization": f"Bearer {saas_env['api_key']}"},
        timeout=10.0,
    )
    response.raise_for_status()
    mission_id_concurrent = response.json()["mission_id"]
    test_concurrent_development(saas_env, mission_id_concurrent, isolated_home, monkeypatch)

    # Test #2: Collision detection
    response = httpx.post(
        f"{saas_env['url']}/api/v1/missions",
        json={"title": "E2E Test Mission - Collision"},
        headers={"Authorization": f"Bearer {saas_env['api_key']}"},
        timeout=10.0,
    )
    response.raise_for_status()
    mission_id_collision = response.json()["mission_id"]
    test_collision_detection(saas_env, mission_id_collision, isolated_home, monkeypatch)

    # Test #3: Organic handoff
    response = httpx.post(
        f"{saas_env['url']}/api/v1/missions",
        json={"title": "E2E Test Mission - Handoff"},
        headers={"Authorization": f"Bearer {saas_env['api_key']}"},
        timeout=10.0,
    )
    response.raise_for_status()
    mission_id_handoff = response.json()["mission_id"]
    test_organic_handoff(saas_env, mission_id_handoff, isolated_home, monkeypatch)

    # Test #4: Offline replay
    response = httpx.post(
        f"{saas_env['url']}/api/v1/missions",
        json={"title": "E2E Test Mission - Offline"},
        headers={"Authorization": f"Bearer {saas_env['api_key']}"},
        timeout=10.0,
    )
    response.raise_for_status()
    mission_id_offline = response.json()["mission_id"]
    test_offline_replay(saas_env, mission_id_offline, isolated_home, monkeypatch)


def test_adapter_equivalence_reference(saas_env, test_mission):
    """
    Success Criterion #5: Adapter equivalence (reference to contract tests).

    This is a placeholder test that verifies adapter equivalence is tested
    in the contract tests. The actual equivalence testing happens in:
    - tests/specify_cli/adapters/test_gemini.py
    - tests/specify_cli/cli/commands/test_mission_collaboration.py

    This test simply documents that criterion #5 is covered elsewhere.
    """
    # Adapter equivalence is verified in contract tests (WP07, WP08, WP09)
    # This test serves as a reference point for E2E validation
    assert True, "Adapter equivalence verified in contract tests (see WP07, WP08, WP09)"
