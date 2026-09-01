---
divio_type: explanation
audience: agentic-framework-core-team
updated: 2026-08-23
---

# Tooling Friction Tracer

## Planning

1. The pasted `/spec-kitty.plan` prompt was older than the repository's canonical mission-step prompt. Planning followed the repository-local canonical source, including decision moments, tracer files, and the setup-plan completion boundary.
2. `SPEC_KITTY_ENABLE_SAAS_SYNC=1` inherited from the environment caused unauthenticated sync attempts and sync-store lock warnings during setup. Planning commands were rerun with SaaS sync unset and local sync disabled.
3. The globally installed `spec-kitty` entry point was unavailable to one research worker because its module path was broken. Repository-local `uv run spec-kitty` remained available; implementation and validation commands should prefer the repository environment.

Append new friction and its resolution during implementation.
