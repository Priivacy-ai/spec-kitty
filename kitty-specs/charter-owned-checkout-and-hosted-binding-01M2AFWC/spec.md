# Mission Specification: Owned checkout charter operations and hosted binding governance

**Mission Branch**: `codex/issue-4250-charter-owned-checkout`  
**Created**: 2026-09-12  
**Status**: Specified  
**Input**: User authorized recovery prevention across every involved project. CLI #4250 is a child of SaaS #1713 / recovery #1711.

## User Scenarios & Testing

### User Story 1 - Govern the checkout actually owned by the agent (Priority: P1)

A curator working in a canonical linked lane explicitly selects that checkout when creating doctrine and loading its effective context. The command must neither mutate the repository-root checkout nor silently serve its different charter.

**Why this priority**: Recovery doctrine cannot protect execution if authoring, activation and consumption resolve different authorities.

**Independent Test**: Execute real CLI commands in a temporary Git repository and linked worktree with deliberately different primary/lane charter content; verify target-only writes and effective lane activation.

**Acceptance Scenarios**:
1. **Given** a validated owned linked checkout, **When** the operator creates a project directive with explicit checkout selection, **Then** only that checkout gains the artifact.
2. **Given** different primary and lane doctrine, **When** context is explicitly selected for the lane, **Then** lane authority is returned and inactive primary content cannot satisfy it.
3. **Given** an unrelated directory, foreign worktree or malformed ownership request, **When** explicit selection is requested, **Then** the command refuses before writing or returning unrelated authority.
4. **Given** existing commands without explicit selection, **When** executed, **Then** documented default behavior remains compatible.

### User Story 2 - Preserve hosted repository binding identity (Priority: P1)

A CLI contributor receives activated project-specific instructions requiring native provider identity and supported hosted contracts. Release or merge evidence cannot be misrepresented as deployed repair evidence.

**Independent Test**: Resolve actual activated directive and procedure, remove activation, and demonstrate that the operational governance consumer refuses the absent authority.

**Acceptance Scenarios**:
1. **Given** renamed/transferred repository locators, **When** binding work is specified or implemented, **Then** the active doctrine requires matching immutable identity, eligibility and supported client/SaaS/relay combinations.
2. **Given** unavailable provider, denied installation, reused old locator or mismatched native ID, **When** evaluating eligibility, **Then** the rule requires explicit failure rather than implicit admission or false completion.
3. **Given** source tests or a merged PR, **When** reporting production status, **Then** release, deployment and complete repair remain separate claims bound to actual receipts.

### Edge Cases

Symlinked paths, detached linked worktrees, nested directories, stale registrations, absent charter, inactive directive despite source presence, and explicit project-root selection must follow existing canonical ownership rules rather than introducing a second classifier.

## Requirements

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Explicit owned checkout authoring | As a curator I create doctrine only in the validated checkout I own. | High | Open |
| FR-002 | Explicit owned checkout context | As an implementer I receive effective activated authority from that same checkout. | High | Open |
| FR-003 | Hosted binding authority | As a CLI contributor I receive activated native-identity and supported-version requirements. | High | Open |
| FR-004 | Truthful completion boundary | As an operator I distinguish client release from observed deployment and all-scope repair. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Ownership isolation | Every rejected selection writes zero files outside the owned checkout; real CLI regression covers both mutation and context. | Safety | High | Open |
| NFR-002 | Nonvacuous authority | Removing each required activation or source produces a failed consumer witness; no source-ID-only acceptance. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Canonical source | Reuse checkout identity and activation-aware resolver; no installed tool patch, parallel resolver or raw-service bypass. | Architecture | High | Open |
| C-002 | Operational boundary | No production mutation, package release or merge; source activation is recorded separately from installed protection. | Safety | High | Open |

### Key Entities

- Owned checkout: validated repository-root checkout or linked worktree identity, independent from the primary branch name.
- Activated artifact: effective project directive/procedure selected by canonical configuration and resolved source.
- Binding evidence: immutable provider identity, current locator, eligibility and supported contract versions.

## Success Criteria

### Measurable Outcomes

- SC-001: Real CLI regression proves zero primary-checkout mutations during explicit lane authoring.
- SC-002: Deliberately different lane/primary authority returns the intended active lane artifact; malformed or foreign selection fails.
- SC-003: Hosted binding directive and procedure resolve, and removal mutations fail before a completion claim.
- SC-004: Independent WP review verifies no production action and no claimed installed protection.
