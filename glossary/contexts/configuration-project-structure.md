## Context: Configuration and Project Structure

Terms describing where policy, runtime configuration, and mission artifacts live in a Spec Kitty project.

### `.kittify/`

| | |
|---|---|
| **Definition** | Project-local configuration and shared memory directory. |
| **Context** | Configuration & Project Structure |
| **Status** | canonical |
| **Key contents** | `config.yaml`, `memory/constitution.md`, command templates, migration metadata |
| **Related terms** | [Constitution](./governance.md#constitution), [Mission](./orchestration.md#mission) |

---

### `kitty-specs/`

| | |
|---|---|
| **Definition** | Feature planning artifacts (`spec.md`, `plan.md`, `tasks.md`, plus supporting files). |
| **Context** | Configuration & Project Structure |
| **Status** | canonical |
| **Related terms** | [Feature](./orchestration.md#feature), [Work Package](./orchestration.md#work-package) |

---

### `.worktrees/`

| | |
|---|---|
| **Definition** | Isolated implementation workspaces used for parallel work package execution. |
| **Context** | Configuration & Project Structure |
| **Status** | canonical |
| **Related terms** | [Work Package](./orchestration.md#work-package), [Lane](./orchestration.md#lane) |

---

### `glossary/`

| | |
|---|---|
| **Definition** | Policy-level language authority for terminology and semantic contracts. |
| **Context** | Configuration & Project Structure |
| **Status** | canonical |
| **Related terms** | [Glossary Scope](./system-events.md#glossary-scope), [Semantic Check](./execution.md#semantic-check) |

---

### Bootstrap (Candidate)

| | |
|---|---|
| **Definition** | Proposed onboarding flow to collect project intent, constraints, and glossary context early. |
| **Context** | Configuration & Project Structure |
| **Status** | candidate |
| **Related terms** | [Constitution](./governance.md#constitution), [Mission](./orchestration.md#mission) |

---

### Project Constitution

| | |
|---|---|
| **Definition** | The compiled, project-specific constitution containing the HiC's governance decisions, doctrine selections, interview answers, and reference manifest. Stored in `.kittify/constitution/`. Use "Project Constitution" when distinguishing from the Constitution Library. |
| **Context** | Configuration & Project Structure |
| **Status** | candidate |
| **Related terms** | [Constitution](./governance.md#constitution), [Constitution Library](#constitution-library), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |

---

### Constitution Library

| | |
|---|---|
| **Definition** | The project-local collection of doctrine source documents that the HiC has selected, stored alongside the Project Constitution and indexed by a reference manifest. |
| **Context** | Configuration & Project Structure |
| **Status** | candidate |
| **Related terms** | [Project Constitution](#project-constitution), [Doctrine Catalog](./doctrine.md#doctrine-catalog) |
