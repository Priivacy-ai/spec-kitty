# Data Model: Supply Chain Security Checks Layer

This mission is doctrine/configuration heavy and does not introduce runtime database entities. The primary model is a set of governance artifacts and their bindings.

## Entities

### 1) SupplyChainInstallSafetyDirective

- **Kind**: Directive artifact (`packs/built-in/directives/*.directive.yaml`)
- **Identity**: Directive ID (`047-supply-chain-install-safety`)
- **Core fields**:
  - policy statements (registry authenticity, package freshness, script discipline, Node LTS posture)
  - action applicability
  - references to related tactics/styleguides
- **Invariants**:
  - Must remain technology-governance oriented (no ephemeral package-version embed as core truth)
  - Must be consumable by action context resolution

### 2) SupplyChainInstallSafetyTactic

- **Kind**: Tactic artifact (`packs/built-in/tactics/**/*.tactic.yaml`)
- **Identity**: Tactic ID (`supply-chain-install-safety`)
- **Core fields**:
  - ordered checklist steps
  - failure modes
  - related references
- **Invariants**:
  - Steps must be operational and evidence-producing
  - Must preserve advisory posture in v1

### 3) DependencyHygieneExtension

- **Kind**: Existing tactic extension
- **Identity**: `dependency-hygiene`
- **Core fields added**:
  - JS/TS applicability
  - registry and freshness checks
  - lifecycle script handling policy
  - Node LTS awareness expectations
- **Invariant**:
  - Existing Java/Python guidance remains intact

### 4) SoftwareDevActionBinding

- **Kind**: Mission action index binding (`src/doctrine/missions/software-dev/actions/*/index.yaml`)
- **Identity**: `(mission=software-dev, action in {plan,implement,review})`
- **Core fields**:
  - `directives[]`
  - `tactics[]`
  - optional related artifacts
- **Invariant**:
  - Security layer must appear for all three target actions

### 5) StepContractSecurityStage

- **Kind**: Step-contract stage (`src/doctrine/missions/built_in_step_contracts/*.step-contract.yaml`)
- **Identity**: step IDs added to plan/implement/review contracts
- **Core fields**:
  - `id`
  - `description`
  - `delegates_to` references
- **Invariant**:
  - Existing transition gate behavior unchanged in v1 (no new fail-closed handler)

### 6) ProfileSecurityBinding

- **Kind**: Agent profile governance (`packs/built-in/agent_profiles/*.agent.yaml` + graph edges)
- **Identity**: profile IDs (Renata/Ivan/Norris/Freddy/Pedro/Jenny/Alphonso)
- **Core fields**:
  - directive/tactic references
  - self-review expectations
  - mode guidance
- **Invariant**:
  - Existing profile purpose remains primary; security layer is integrated, not replacing role intent

### 7) AdversarialEvidenceDisposition

- **Kind**: Planning/review evidence expectation (artifact-level contract)
- **Identity**: tied to mission planning/review outputs
- **Core fields**:
  - challenge source (adversarial pass)
  - finding
  - disposition (`accepted`, `changed`, `deferred_with_rationale`)
  - evidence location
- **Invariants**:
  - Required in plan/research and review-facing outputs for security-sensitive decisions
  - Remains guidance-level in v1 (no runtime blocking dependency)

## Relationships

- `SupplyChainInstallSafetyDirective` -> scoped into `SoftwareDevActionBinding`.
- `SupplyChainInstallSafetyTactic` -> referenced by both action bindings and step-contract stages.
- `DependencyHygieneExtension` -> complements tactic coverage in implement/review paths.
- `ProfileSecurityBinding` -> consumes directive/tactic semantics for human-visible behavior.
- `AdversarialEvidenceDisposition` -> evidence artifact expected by plan/review guidance created from the above bindings.

## Validation Rules

1. Action-binding validation must show security coverage in `plan`, `implement`, and `review`.
2. Step-contract validation must show security stages while preserving advisory gate compatibility.
3. Profile validation must show consistent script and Node-LTS policy expectations for targeted profiles.
4. Evidence contract validation must show explicit disposition states for adversarial findings.
