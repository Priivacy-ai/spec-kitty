"""Production adapter for charter synthesis using the Anthropic Claude API."""
from __future__ import annotations

import datetime
import os
from typing import Any

import anthropic

from charter.synthesizer.adapter import AdapterOutput
from charter.synthesizer.errors import ProductionAdapterUnavailableError
from charter.synthesizer.request import SynthesisRequest

_DEFAULT_MODEL = "claude-sonnet-4-6"
_DEFAULT_TIMEOUT = 120
_DEFAULT_MAX_TOKENS = 8192


class ProductionAdapter:
    """SynthesisAdapter implementation backed by Anthropic Claude."""

    id: str = "production"

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        timeout_seconds: int = _DEFAULT_TIMEOUT,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        api_key: str | None = None,
    ) -> None:
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise ProductionAdapterUnavailableError(
                adapter_id="production",
                reason="ANTHROPIC_API_KEY environment variable is not set",
                remediation=(
                    "Set the ANTHROPIC_API_KEY environment variable to your Anthropic "
                    "API key and retry."
                ),
            )
        self.version: str = model
        self._model = model
        self._timeout = timeout_seconds
        self._max_tokens = max_tokens
        self._client = anthropic.Anthropic(api_key=resolved_key)

    def generate(self, request: SynthesisRequest) -> AdapterOutput:
        """Call Claude to produce a single artifact body for the given request."""
        prompt = _build_synthesis_prompt(request)
        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                timeout=self._timeout,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APITimeoutError as exc:
            raise ProductionAdapterUnavailableError(
                adapter_id="production",
                reason=f"Claude API call timed out after {self._timeout}s",
                remediation=(
                    "Increase charter.synthesis.timeout_seconds in .kittify/config.yaml."
                ),
            ) from exc
        except anthropic.APIError as exc:
            raise ProductionAdapterUnavailableError(
                adapter_id="production",
                reason=f"Claude API error: {exc}",
                remediation="Check your API key and retry.",
            ) from exc

        body_text = "".join(
            block.text for block in message.content if hasattr(block, "text")
        )
        # AdapterOutput.body is Mapping[str, Any]; wrap text in a dict
        body: dict[str, Any] = {"text": body_text}
        return AdapterOutput(
            body=body,
            generated_at=datetime.datetime.now(datetime.timezone.utc),
        )

    def generate_batch(
        self, requests: list[SynthesisRequest]
    ) -> list[AdapterOutput]:
        """Produce outputs for a batch of requests (sequential implementation)."""
        return [self.generate(r) for r in requests]


def _build_synthesis_prompt(request: SynthesisRequest) -> str:
    """Build the synthesis prompt for a single target."""
    target = request.target
    parts: list[str] = [
        f"You are generating a {target.kind} artifact for a software project's governance doctrine.",
        f"Artifact: {target.slug}",
        f"Title: {target.title}",
        "",
        "## Interview Context",
        _format_interview(request.interview_snapshot),
    ]

    if request.evidence is not None and not request.evidence.is_empty:
        parts += ["", "## Project Evidence", _format_evidence(request.evidence)]

    parts += [
        "",
        "## Task",
        f"Write the {target.kind} content as valid YAML following the doctrine schema for {target.kind} artifacts.",
        "Be specific to the project context. Avoid generic filler.",
    ]
    return "\n".join(parts)


def _format_interview(snapshot: dict[str, Any]) -> str:
    lines = []
    for key, value in sorted(snapshot.items()):
        if value:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) or "(no interview data)"


def _format_evidence(evidence: Any) -> str:
    sections = []
    if evidence.code_signals:
        cs = evidence.code_signals
        sections.append(f"Stack: {cs.stack_id}")
        if cs.representative_files:
            files = ", ".join(cs.representative_files[:5])
            sections.append(f"Representative files: {files}")
    if evidence.url_list:
        sections.append("Reference URLs (please read these for additional context):")
        for url in evidence.url_list:
            sections.append(f"  - {url}")
    if evidence.corpus_snapshot:
        snap = evidence.corpus_snapshot
        sections.append(f"Best-practice corpus ({snap.snapshot_id}):")
        for entry in snap.entries[:3]:
            sections.append(f"  [{entry.topic}] {entry.guidance[:200]}")
    return "\n".join(sections)
