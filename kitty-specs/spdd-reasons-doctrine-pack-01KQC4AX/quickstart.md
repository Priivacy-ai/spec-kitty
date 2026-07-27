# Quickstart — Activating and Using the SPDD/REASONS Doctrine Pack

## Activation (charter)

1. Run `spec-kitty charter` (interview) or edit governance manually.
2. Select any one of:
   - paradigm `structured-prompt-driven-development`
   - tactic `reasons-canvas-fill`
   - tactic `reasons-canvas-review`
   - directive `DIRECTIVE_038`
3. Selecting the paradigm is the typical case; selecting the directive only is allowed for teams that want the change-boundary rule without explicit canvas tooling.
4. Re-run `spec-kitty charter context --action <action>` and confirm the output now contains an "SPDD/REASONS Guidance" subsection.

## Mission lifecycle (active project)

```bash
# 1. Specify (Requirements + Entities guidance appears in the prompt)
/spec-kitty.specify  <feature description>

# 2. Plan (Approach + Structure guidance)
/spec-kitty.plan

# 3. Tasks (Operations + WP boundary guidance)
/spec-kitty.tasks

# 4. (optional) Generate or update the canvas explicitly
#    Trigger: "use REASONS" or "generate a REASONS canvas"
#    The spec-kitty-spdd-reasons skill loads mission context and writes
#    kitty-specs/<mission>/reasons-canvas.md.

# 5. Implement (full WP-scoped canvas in implement prompt)
/spec-kitty.implement WP01

# 6. Review (canvas as comparison surface; drift gate active)
/spec-kitty.review WP01
```

## Inactive project (no behavior change)

A project that has NOT selected any SPDD pack artifact:

- sees no "SPDD/REASONS Guidance" subsection in `charter context --action`,
- sees no REASONS section in any command-template prompt,
- sees no review-gate change.

This is enforced by snapshot tests on the inactive baseline.

## When NOT to use this pack

- Tiny fixes (typo, dependency bump, single-line bug fix).
- Throwaway spikes you intend to discard.
- Emergency patches where post-hoc canvas authoring is more appropriate.
- Pure visual exploration where canvas authoring is overhead.

## Examples

### Lightweight mission (canvas is a 1-page sanity check)

A mission "rename `foo_v2` API surface to `foo`" benefits from:
- Requirements: explicit user impact statement.
- Operations: ordered rename steps (callers, docs, deprecation note).
- Safeguards: deprecation timeline, no breaking change to clients on the old name within the deprecation window.

Approach, Structure, Norms can be omitted or brief.

### High-risk multi-WP mission (DIRECTIVE_038 useful)

A mission "introduce new auth middleware" with WPs touching session storage, API ingress, and observability. Canvas:
- Requirements: explicit threat model coverage; SLOs.
- Entities: token, session, principal — with canonical glossary terms.
- Approach: chosen middleware and explicit rejection of alternatives.
- Structure: surface boundary — what middleware owns vs what handlers own.
- Operations: rollout plan with feature flag.
- Norms: structured logging keys, redaction rules.
- Safeguards: no plaintext token in logs; no session_id outside encrypted storage; no breaking change to OAuth callbacks.

Reviewer uses the canvas at every WP review to detect any of the listed safeguards being violated by a diff.
