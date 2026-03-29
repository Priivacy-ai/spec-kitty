## Context: Technology Foundations

General technology terms that appear throughout Spec Kitty documentation. Included here so that readers unfamiliar with these concepts have a clear reference point.

### API

| | |
|---|---|
| **Definition** | Application Programming Interface — a defined way for one piece of software to talk to another. Instead of a human clicking buttons, an API lets programs send requests and receive structured responses. |
| **Context** | Technology Foundations |
| **Status** | candidate |
| **Applicable to** | `1.x`, `2.x` |

---

### CLI

| | |
|---|---|
| **Definition** | Command Line Interface — a text-based way to interact with software by typing commands into a terminal, rather than clicking through a graphical interface. Spec Kitty's primary interface is a CLI. |
| **Context** | Technology Foundations |
| **Status** | candidate |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [UI](#ui) |

---

### UI

| | |
|---|---|
| **Definition** | User Interface — any surface through which a person interacts with software. This can be graphical (buttons, windows) or text-based (a CLI). |
| **Context** | Technology Foundations |
| **Status** | candidate |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [CLI](#cli) |

---

### Markdown

| | |
|---|---|
| **Definition** | A lightweight text formatting language that uses simple symbols (like `#` for headings and `**` for bold) to create readable documents. Files use the `.md` extension. |
| **Context** | Technology Foundations |
| **Status** | candidate |
| **Applicable to** | `1.x`, `2.x` |

---

### YAML

| | |
|---|---|
| **Definition** | A human-readable configuration file format that uses indentation and key-value pairs to structure data. Files use the `.yaml` or `.yml` extension. Used in Spec Kitty for mission definitions and project configuration. |
| **Context** | Technology Foundations |
| **Status** | candidate |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [JSON](#json) |

---

### JSON

| | |
|---|---|
| **Definition** | A structured data format using curly braces and key-value pairs, commonly used for machine-to-machine communication. Less human-readable than YAML but widely supported by programming tools. |
| **Context** | Technology Foundations |
| **Status** | candidate |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [YAML](#yaml) |

---

### SHA256

| | |
|---|---|
| **Definition** | A hashing algorithm that produces a fixed-length checksum from any input. Even a tiny change in the input produces a completely different checksum, making it useful for detecting whether content has been modified. |
| **Context** | Technology Foundations |
| **Status** | candidate |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Content Hash](./dossier.md#content-hash), [Parity Hash](./dossier.md#parity-hash) |

---

### Common Kernel

| | |
|---|---|
| **Definition** | A zero-dependency shared utility package (`src/kernel/`) that provides primitives needed by multiple peer packages (`specify_cli`, `constitution`, `doctrine`). The kernel has no imports from any of these packages — only they import from it. This pattern (also called "extract kernel") breaks cyclic dependencies by extracting the shared logic into a foundation layer that all packages can safely consume without introducing dependency cycles. |
| **Context** | Technology Foundations |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Extract Kernel (refactoring tactic)](#extract-kernel-refactoring-tactic) |

---

### Extract Kernel (Refactoring Tactic)

| | |
|---|---|
| **Definition** | A refactoring approach for resolving cyclic package dependencies. When package A and package B both need a shared utility, and that utility currently lives inside A (causing B to import A), the fix is to extract the utility into a new zero-dependency package C (the kernel). Both A and B then import from C, and the cycle is broken. The key invariant: the kernel must have no imports from A or B. |
| **Context** | Technology Foundations |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Common Kernel](#common-kernel) |
