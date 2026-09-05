---
name: wrong-name
description: >-
  Deliberately-broken discrimination control fixture for the skills static
  conformance suite (FR-005). Its frontmatter `name` intentionally does not
  match its parent directory's basename (`name-mismatch`), tripping muster's
  name-must-equal-directory-basename static gate. This fixture exists to
  prove the suite can register a genuine failure, not to be a usable skill.
  Do not "fix" this mismatch; see conformance/skills/manifest.yaml's
  control-name-mismatch case and its expectations.ok: false declaration.
---

# Discrimination control fixture (do not use)

This file exists solely to back the `control-name-mismatch` case in
`conformance/skills/manifest.yaml`. Its frontmatter `name` (`wrong-name`)
deliberately does not equal this directory's basename (`name-mismatch`),
which trips muster's `@garrison-hq/muster` static gate requiring the
frontmatter `name` to match the directory it lives in.

This is intentional. If a future change "fixes" the mismatch by aligning
`name` with the directory, the manifest's `control-name-mismatch` case
(declared `expectations: {ok: false}`) will start failing, because the
suite's `passed = ok === expectations.ok` rule will see the harness report
`ok: true` against a declared `ok: false` — that failure is the point: it
proves the control still discriminates. Do not update the manifest's
expectation to `ok: true` to make it pass again; that removes the fail-safe
this fixture exists to provide.
