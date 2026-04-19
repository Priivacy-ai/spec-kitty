"""Unit tests for ProductionAdapter.

All tests mock the Anthropic client — no live API calls.
Live-API tests are decorated @pytest.mark.live_adapter and skipped by default.
"""
from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch

import pytest

from charter.synthesizer.adapter import AdapterOutput, SynthesisAdapter
from charter.synthesizer.errors import ProductionAdapterUnavailableError
from charter.synthesizer.production_adapter import ProductionAdapter, _DEFAULT_MODEL


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def minimal_request():
    from charter.synthesizer.request import SynthesisRequest, SynthesisTarget

    return SynthesisRequest(
        target=SynthesisTarget(
            kind="tactic",
            slug="how-we-work",
            title="How We Work",
            artifact_id="how-we-work",
            source_section="testing_philosophy",
            source_urns=("urn:drg:directive:DIRECTIVE_010",),
        ),
        interview_snapshot={"testing_philosophy": "We test everything."},
        doctrine_snapshot={},
        drg_snapshot={},
        run_id="test-run",
    )


# ---------------------------------------------------------------------------
# Instantiation tests
# ---------------------------------------------------------------------------


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ProductionAdapterUnavailableError) as exc_info:
        ProductionAdapter()
    # The error string must mention ANTHROPIC_API_KEY
    assert "ANTHROPIC_API_KEY" in str(exc_info.value)


def test_adapter_id_is_production():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("anthropic.Anthropic"):
            adapter = ProductionAdapter()
    assert adapter.id == "production"


def test_adapter_version_defaults_to_default_model():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("anthropic.Anthropic"):
            adapter = ProductionAdapter()
    assert adapter.version == _DEFAULT_MODEL


def test_version_reflects_custom_model():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("anthropic.Anthropic"):
            adapter = ProductionAdapter(model="claude-opus-4-7")
    assert adapter.version == "claude-opus-4-7"


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_protocol_conformance():
    """ProductionAdapter must satisfy SynthesisAdapter protocol at runtime."""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("anthropic.Anthropic"):
            adapter = ProductionAdapter()
    assert isinstance(adapter, SynthesisAdapter)


# ---------------------------------------------------------------------------
# generate() tests
# ---------------------------------------------------------------------------


@patch("anthropic.Anthropic")
def test_generate_returns_adapter_output(mock_cls, minimal_request):
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Generated content")]
    mock_client.messages.create.return_value = mock_message

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        adapter = ProductionAdapter()
    output = adapter.generate(minimal_request)

    assert isinstance(output, AdapterOutput)


@patch("anthropic.Anthropic")
def test_generate_body_contains_text(mock_cls, minimal_request):
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Generated content")]
    mock_client.messages.create.return_value = mock_message

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        adapter = ProductionAdapter()
    output = adapter.generate(minimal_request)

    # AdapterOutput.body is Mapping[str, Any]
    assert "text" in output.body
    assert output.body["text"] == "Generated content"


@patch("anthropic.Anthropic")
def test_generate_sets_generated_at(mock_cls, minimal_request):
    import datetime

    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="some output")]
    mock_client.messages.create.return_value = mock_message

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        adapter = ProductionAdapter()
    output = adapter.generate(minimal_request)

    assert isinstance(output.generated_at, datetime.datetime)
    assert output.generated_at.tzinfo is not None  # must be timezone-aware


@patch("anthropic.Anthropic")
def test_generate_concatenates_multiple_content_blocks(mock_cls, minimal_request):
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_message = MagicMock()
    block1 = MagicMock(text="Hello ")
    block2 = MagicMock(text="World")
    mock_message.content = [block1, block2]
    mock_client.messages.create.return_value = mock_message

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        adapter = ProductionAdapter()
    output = adapter.generate(minimal_request)

    assert output.body["text"] == "Hello World"


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


@patch("anthropic.Anthropic")
def test_timeout_raises_unavailable_error(mock_cls, minimal_request):
    import anthropic as anthropic_module

    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.messages.create.side_effect = anthropic_module.APITimeoutError(
        request=MagicMock()
    )

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        adapter = ProductionAdapter()
    with pytest.raises(ProductionAdapterUnavailableError) as exc_info:
        adapter.generate(minimal_request)
    assert "timed out" in str(exc_info.value)


@patch("anthropic.Anthropic")
def test_api_error_raises_unavailable_error(mock_cls, minimal_request):
    import anthropic as anthropic_module

    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_client.messages.create.side_effect = anthropic_module.APIStatusError(
        message="Unauthorized",
        response=mock_response,
        body={"error": {"type": "authentication_error", "message": "Unauthorized"}},
    )

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        adapter = ProductionAdapter()
    with pytest.raises(ProductionAdapterUnavailableError) as exc_info:
        adapter.generate(minimal_request)
    assert "Claude API error" in str(exc_info.value)


# ---------------------------------------------------------------------------
# generate_batch() tests
# ---------------------------------------------------------------------------


@patch("anthropic.Anthropic")
def test_generate_batch_returns_list(mock_cls, minimal_request):
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="output")]
    mock_client.messages.create.return_value = mock_message

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        adapter = ProductionAdapter()
    outputs = adapter.generate_batch([minimal_request, minimal_request])

    assert len(outputs) == 2
    for output in outputs:
        assert isinstance(output, AdapterOutput)


# ---------------------------------------------------------------------------
# Seam lint tests (adapter.py must remain unchanged)
# ---------------------------------------------------------------------------


def test_adapter_seam_has_synthesis_adapter():
    from charter.synthesizer import adapter as seam_module

    assert hasattr(seam_module, "SynthesisAdapter")


def test_adapter_seam_has_adapter_output():
    from charter.synthesizer import adapter as seam_module

    assert hasattr(seam_module, "AdapterOutput")


def test_adapter_seam_has_batch_capable():
    from charter.synthesizer import adapter as seam_module

    assert hasattr(seam_module, "BatchCapableSynthesisAdapter")


def test_adapter_seam_generate_signature():
    from charter.synthesizer import adapter as seam_module

    sig = inspect.signature(seam_module.SynthesisAdapter.generate)
    assert "request" in sig.parameters


# ---------------------------------------------------------------------------
# Live adapter test — skipped in CI
# ---------------------------------------------------------------------------


@pytest.mark.live_adapter
def test_live_generate(minimal_request):  # pragma: no cover
    """Live integration test — skipped unless -m live_adapter is passed."""
    adapter = ProductionAdapter()  # requires ANTHROPIC_API_KEY in env
    output = adapter.generate(minimal_request)
    assert output.body
    assert output.generated_at
