# Available Tooling (Session)

## Purpose

Record which preferred workspace tools are available at session startup, the final tooling decision for this session, and rationale for any missing-tool remediation guidance.

## Privacy Constraint

Do not store personally identifiable information (PII) in this file.

Do not include:

- IP addresses
- hostnames or system names
- usernames
- machine IDs or similar unique identifiers

## Session Summary

- Decision timestamp (UTC): 2026-03-09T05:26:16Z
- Final decision summary: Use the repo-local `.venv` plus `poetry`, `uv`, `ruff`, `mypy`, Mermaid CLI, and `rg` for this session.
- Rationale summary: All preferred tools are available, so no remediation is needed and the standard workspace toolchain can be used directly.

## Tool Availability

| Tool                  | Available (yes/no) | Version (optional) | Decision | Rationale / Remediation                                       |
|-----------------------|--------------------|--------------------|----------|---------------------------------------------------------------|
| `.venv` (repo-local)  | yes                | Python 3.12.3      | use      | Present in the repo and suitable for session commands.        |
| `poetry`              | yes                | 2.3.2              | use      | Available for dependency and environment workflows.           |
| `uv`                  | yes                | 0.10.9             | use      | Available for fast package and tool execution workflows.      |
| `ruff`                | yes                | 0.15.1             | use      | Available for linting when the task requires it.              |
| `mypy`                | yes                | 1.19.1             | use      | Available for strict type-checking when the task requires it. |
| local Mermaid tooling | yes                | 11.12.0            | use      | Mermaid CLI is installed locally for diagram rendering.       |
| `rg` (ripgrep)        | yes                | 15.1.0             | use      | Available and preferred for repository search/navigation.     |

## Notes

- Keep this file session-focused and concise.
- Prefer actionable remediation text when a tool is missing.
