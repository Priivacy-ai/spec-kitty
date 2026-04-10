## Context: Configuration and Project Structure

Terms describing where policy, runtime configuration, and mission artifacts live in a Spec Kitty repository.

### `.kittify/`

| | |
|---|---|
| **Definition** | Repository-local configuration and shared memory directory. |
| **Context** | Configuration & Project Structure |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Key contents** | `config.yaml`, `charter/charter.md` (canonical), command templates, migration metadata |
| **Related terms** | [Charter](./governance.md#charter), [Mission](./orchestration.md#mission) |

---

### `kitty-specs/`

| | |
|---|---|
| **Definition** | Feature planning artifacts (`spec.md`, `plan.md`, `tasks.md`, plus supporting files). |
| **Context** | Configuration & Project Structure |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Feature](./orchestration.md#feature), [Work Package](./orchestration.md#work-package) |

---

### `.worktrees/`

| | |
|---|---|
| **Definition** | Isolated implementation workspaces used for parallel work package execution. |
| **Context** | Configuration & Project Structure |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Work Package](./orchestration.md#work-package), [Lane](./orchestration.md#lane) |

---

### `glossary/`

| | |
|---|---|
| **Definition** | Policy-level language authority for terminology and semantic contracts. |
| **Context** | Configuration & Project Structure |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Glossary Scope](./system-events.md#glossary-scope), [Semantic Check](./execution.md#semantic-check) |

---

### Bootstrap (Candidate)

| | |
|---|---|
| **Definition** | Proposed onboarding flow to collect repository intent, constraints, and glossary context early. |
| **Context** | Configuration & Project Structure |
| **Status** | candidate |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Charter](./governance.md#charter), [Mission](./orchestration.md#mission) |

---

### Project Charter

| | |
|---|---|
| **Definition** | The compiled, repository-specific charter containing the HiC's governance decisions, doctrine selections, interview answers, and reference manifest. Stored in `.kittify/charter/`. Use "Project Charter" when distinguishing from the Charter Library. |
| **Context** | Configuration & Project Structure |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Note** | In this context, "Project Charter" names the governance artifact. It does not redefine [Project](./orchestration.md#project) as the local Git resource. |
| **Related terms** | [Charter](./governance.md#charter), [Charter Library](#charter-library), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |

---

### Charter Library

| | |
|---|---|
| **Definition** | The repository-local collection of doctrine source documents that the HiC has selected, stored alongside the Project Charter and indexed by a reference manifest. |
| **Context** | Configuration & Project Structure |
| **Status** | candidate |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Project Charter](#project-charter), [Doctrine Catalog](./doctrine.md#doctrine-catalog) |
