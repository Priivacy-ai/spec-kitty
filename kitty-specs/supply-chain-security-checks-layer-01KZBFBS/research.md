# Research: Supply Chain Security Checks Layer

## Inputs

- Spec: `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/spec.md`
- Charter context (`plan`): `spec-kitty charter context --action plan --json`
- Decision record: `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/decisions/DM-01KZBMQ8WBDZMQS9CFKTGARRJA.md`

## Decision Log

### Decision 1: Where adversarial-squad evidence is mandatory in v1

- **Decision**: Require adversarial-squad evidence in **plan/research plus review-facing artifacts**.
- **Rationale**: This catches security assumptions before implementation lock-in and also ensures review outcomes reference challenged findings.
- **Alternatives considered**:
  - Plan/research only: rejected because review approval could still omit contested findings.
  - Full hard runtime gating: rejected for v1 because charter cadence is advisory and current mission scope avoids new fail-closed runtime behavior.

### Decision 2: Security rollout mode

- **Decision**: Advisory-by-default doctrine layer in v1; no new fail-closed transition gate handler.
- **Rationale**: Matches standing-order cadence and preserves compatibility across repositories with different validator maturity.
- **Alternatives considered**:
  - New fail-closed security gate in review transitions: deferred to later ratchet once machine-checkable controls are standardized.

### Decision 3: Profile strategy

- **Decision**: Enhance existing built-in profiles rather than creating a new built-in AppSec persona.
- **Rationale**: Existing reviewer/implementer profiles are the active operating surface and can absorb the new controls without profile sprawl.
- **Alternatives considered**:
  - New built-in security persona: rejected for v1 scope; remains valid for org-pack specialization later.

### Decision 4: Package vetting policy scope

- **Decision**: Encode threat-class checks (registry authenticity, freshness, script discipline, Node LTS awareness) rather than embedding a live package denylist.
- **Rationale**: Threat-specific package versions change quickly and must remain external authority (CAS/vendor feeds).
- **Alternatives considered**:
  - Core live denylist sync: rejected by scope and maintainability constraints.

## Resolved Clarifications

- **Adversarial evidence source scope** is resolved and recorded in DM-01KZBMQ8WBDZMQS9CFKTGARRJA.
- No unresolved technical-context placeholders remain for plan phase.

## Research Implications for Design

1. The doctrine layer must provide explicit evidence language for adversarial challenge outcomes in both planning and review guidance.
2. Step-contract changes should enforce visibility/order of security checks without adding new hard gate semantics.
3. Validation must include tests proving action/profile wiring plus at least one evidence-path assertion for adversarial disposition expectations.
