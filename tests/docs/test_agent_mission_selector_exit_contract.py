from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_AGENT_REFERENCE = _REPO_ROOT / "docs" / "api" / "agent-subcommands.md"


def test_agent_mission_ambiguous_exit_contract_is_documented() -> None:
    text = _AGENT_REFERENCE.read_text(encoding="utf-8")

    assert 'error_code: "MISSION_AMBIGUOUS_SELECTOR"' in text
    assert "exit `1`" in text
    assert "human mode, they print the ambiguity diagnostic and exit `2`" in text
    assert "deliberately changed this human-mode case from the earlier generic exit code `1` to `2`" in text
