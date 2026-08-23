# Tooling Friction Trace

## 2026-08-23 — setup-plan self-hosting refusal

Running the canonical setup-plan command with the ambient SaaS flag reproduced issue #3621: the command returned `SAAS_SYNC_UNAUTHENTICATED` with exit 2 before creating the local plan result. The user authorized disabling SaaS sync for this entire planning mission, so subsequent Spec Kitty commands use command-local `SPEC_KITTY_ENABLE_SAAS_SYNC=0`. No persistent environment or repository configuration was changed.

This friction is direct evidence for IC-02 and IC-03: the hosted diagnostic currently prevents the local planning operation it is meant only to accompany.
