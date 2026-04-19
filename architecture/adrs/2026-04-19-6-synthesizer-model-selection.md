# ADR-6: Charter Synthesizer Model Selection

**Date**: 2026-04-19
**Status**: Accepted
**Deciders**: Robert Douglass
**Supersedes**: N/A

## Context

The charter synthesizer's production adapter calls an LLM to generate
project-local governance doctrine artifacts (directives, tactics, styleguides)
from interview answers and evidence inputs. The model selection affects:

- Output quality: doctrine should reflect nuanced judgment, not generic text.
- Cost: synthesis runs are infrequent (typically once per project setup or
  major change), so per-run cost matters more than per-request latency.
- Configurability: different projects have different quality/cost trade-offs.

## Decision

**Default model**: `claude-sonnet-4-6`

Rationale:
- Strong reasoning quality — sufficient for interpreting mixed evidence
  (code signals, URL references, corpus guidance) and generating coherent
  doctrine with appropriate project-specific nuance.
- Appropriate cost tier — synthesis is infrequent; the higher cost vs.
  Haiku is justified by the importance of the output.
- Not Opus — Opus is better reserved for exceptional cases; Sonnet is the
  right balance for a default that operators can upgrade.

## Override Mechanism

Operators can override the model per-project in `.kittify/config.yaml`:

```yaml
charter:
  synthesis:
    model: claude-opus-4-7   # override to Opus for higher quality
    timeout_seconds: 180     # optional: increase API timeout
```

Any `claude-*` model identifier is accepted. The adapter validates that the
string is non-empty and falls back to the default on any parse error.

## Cost Model (Advisory)

Approximate cost per full synthesis run (8–12 targets):

| Component | Estimate |
|-----------|----------|
| Input tokens per run | 15,000–40,000 |
| Output tokens per run | 2,000–4,000 |
| Sonnet 4.6 cost | ~$0.05–$0.25 per run |
| Opus 4.7 cost | ~$0.25–$1.25 per run |

These are approximate; actual cost depends on interview richness, evidence
volume, and target count.

## Alternatives Considered

- **`claude-haiku-4-5`**: Rejected — insufficient reasoning depth for the
  "interpret mixed evidence → coherent doctrine" task.
- **`claude-opus-4-7`**: Viable but higher cost; available as per-project
  override for projects that value maximum output quality.
- **Provider-neutral (OpenAI, Gemini)**: Deferred — the `SynthesisAdapter`
  protocol supports future providers; ADR-6 scopes to Claude for Phase 3.
- **Fixed hardcoded model**: Rejected — model families evolve; operators need
  the ability to update without a code change.

## Consequences

- `anthropic>=0.55.0` added to project runtime dependencies.
- `ANTHROPIC_API_KEY` environment variable required for production adapter.
- `ProductionAdapter` raises `ProductionAdapterUnavailableError` when the key
  is missing or when the API returns a timeout or error response.
- Future provider support: implement a new `SynthesisAdapter` in a separate
  file; no changes to `adapter.py` seam required (ADR-2026-04-17-1).
