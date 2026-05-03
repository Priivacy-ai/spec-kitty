# Reliability Fixtures

These fixtures create local mission/work-package state for workflow reliability
regression tests. They intentionally avoid hosted services and SaaS imports.

Use fake sync clients for hosted sync failures unless a work package explicitly
scopes a real hosted path. On this computer, commands that exercise SaaS,
tracker, hosted auth, or sync behavior must be run with
`SPEC_KITTY_ENABLE_SAAS_SYNC=1`.
