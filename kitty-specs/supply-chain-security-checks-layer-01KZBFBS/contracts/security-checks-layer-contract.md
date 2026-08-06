# Contract: Security Checks Layer Wiring

## Purpose

Define the minimum behavior contract for integrating the supply-chain security layer into software-dev workflow resolution surfaces.

## Contract Scope

1. Directive contract
2. Tactic contract
3. Action index binding contract
4. Step-contract sequencing contract
5. Profile binding contract

## Normative Rules

### Rule 1 — Directive existence and scope

- A directive with ID `047-supply-chain-install-safety` exists in built-in directives.
- It covers, at minimum:
  - official registry authenticity checks
  - package age/recency visibility
  - deny-by-default lifecycle script policy
  - Node Active LTS awareness and skew disclosure
  - incident-list and IoC posture guidance

### Rule 2 — Tactic availability

- A tactic `supply-chain-install-safety` exists and is referenceable from software-dev action indexes and targeted profile guidance.
- `dependency-hygiene` remains available and is extended to include JS/TS concerns.

### Rule 3 — Action binding completeness

For mission type `software-dev`, action indexes for:
- `plan`
- `implement`
- `review`

must each include at least one security-layer artifact introduced by this mission.

### Rule 4 — Step-contract security stages

Plan/implement/review step contracts include explicit security stages that delegate to the security directive/tactic layer.

### Rule 5 — Advisory compatibility

- No new fail-closed transition gate handler is introduced by this mission.
- Existing transition behavior remains compatible while guidance/evidence obligations increase.

### Rule 6 — Profile coverage

Targeted profiles include security-layer references and expectations:
- `reviewer-renata`
- `implementer-ivan`
- `node-norris`
- `frontend-freddy`
- `python-pedro`
- `java-jenny`
- `architect-alphonso`

## Verification Hooks

Minimum verification evidence:

1. Action context resolution output includes new layer for plan/implement/review.
2. Step contract files show explicit security stages.
3. Profile resolution or profile YAML shows required references.
4. Tests prove at least one path each for action binding, step-contract binding, and profile binding.
