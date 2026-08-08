# Contract: Adversarial Evidence Disposition (v1)

## Purpose

Define how adversarial-squad findings are captured for this mission's security-layer decisions.

## Scope Decision

Resolved by decision `01KZBMQ8WBDZMQS9CFKTGARRJA`:

- Mandatory in **plan/research artifacts**
- Mandatory in **review-facing artifacts**

## Evidence Record Shape

Each challenged security finding must have an explicit disposition record containing:

- **finding_id**: stable identifier in local artifact context
- **challenge_summary**: what was challenged
- **source**: adversarial pass / reviewer challenge
- **disposition**: one of
  - `accepted`
  - `changed`
  - `deferred_with_rationale`
- **rationale**: required for `deferred_with_rationale`, recommended otherwise
- **evidence_location**: path/section where resulting change or acknowledgment is captured

## Normative Rules

1. No contested security finding may be silently dropped.
2. Every disposition is explicit and traceable to an artifact location.
3. v1 remains advisory cadence: missing evidence is governance-noncompliant but does not introduce a new fail-closed transition gate handler in this mission.

## Out of Scope

- Runtime orchestration dependency on squad tooling.
- Automatic cross-repo evidence sync.
- Mandatory hard-gate enforcement at lane transition level.
