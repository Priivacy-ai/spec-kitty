# Spec — clean install fixture

This fixture mission is the smallest possible scaffold that `spec-kitty next`
operates on. It exists exclusively to verify that
`pip install spec-kitty-cli` followed by `spec-kitty next` succeeds in a
clean venv without `spec-kitty-runtime` installed (FR-010 / FR-017 of
mission `shared-package-boundary-cutover-01KQ22DS`).

The mission has one work package (`WP01-fixture`) with one trivial subtask
(create `hello.txt` with the word `OK`). The point is not real
implementation - it is that `spec-kitty next` can advance one step.

If `spec-kitty next` semantics change in a future release, this fixture is
the canary; update it together with the runtime contract.
