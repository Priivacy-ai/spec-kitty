"""Integration test for SaaS join API with mocking."""

import pytest
import httpx
import respx

from specify_cli.collaboration.service import join_mission


@pytest.mark.respx(base_url="https://api.example.com")
def test_join_mission_integration(respx_mock: respx.MockRouter, clean_queue_and_session):
    """Test join_mission with mocked SaaS API."""
    # Mock join endpoint
    respx_mock.post("/api/v1/missions/mission-123/participants").mock(
        return_value=httpx.Response(
            200,
            json={
                "participant_id": "01HQRS8ZMBE6XYZABC0123ZZZZ",
                "session_token": "token123",
                "role": "developer",
            },
        )
    )

    # Mock health check for is_online (called by emit_event)
    respx_mock.get("/health").mock(return_value=httpx.Response(200))

    # Mock event batch endpoint for emit_event
    respx_mock.post("/api/v1/events/batch/").mock(
        return_value=httpx.Response(200, json={"accepted": [], "rejected": []})
    )

    result = join_mission(
        "mission-123", "developer", "https://api.example.com", "auth-token"
    )

    assert result["participant_id"] == "01HQRS8ZMBE6XYZABC0123ZZZZ"
    assert result["role"] == "developer"


@pytest.mark.respx(base_url="https://api.example.com")
def test_join_mission_404_error(respx_mock: respx.MockRouter, clean_queue_and_session):
    """Test join_mission handles 404 (mission not found)."""
    respx_mock.post("/api/v1/missions/unknown/participants").mock(
        return_value=httpx.Response(404)
    )

    with pytest.raises(httpx.HTTPStatusError):
        join_mission("unknown", "developer", "https://api.example.com", "auth-token")


@pytest.mark.respx(base_url="https://api.example.com")
def test_join_mission_401_unauthorized(respx_mock: respx.MockRouter, clean_queue_and_session):
    """Test join_mission handles 401 (unauthorized)."""
    respx_mock.post("/api/v1/missions/mission-123/participants").mock(
        return_value=httpx.Response(401)
    )

    with pytest.raises(httpx.HTTPStatusError):
        join_mission(
            "mission-123", "developer", "https://api.example.com", "invalid-token"
        )


@pytest.mark.respx(base_url="https://api.example.com")
def test_join_mission_500_server_error(respx_mock: respx.MockRouter, clean_queue_and_session):
    """Test join_mission handles 500 (server error)."""
    respx_mock.post("/api/v1/missions/mission-123/participants").mock(
        return_value=httpx.Response(500)
    )

    with pytest.raises(httpx.HTTPStatusError):
        join_mission("mission-123", "developer", "https://api.example.com", "auth-token")
