# Contract: Dead-Code Review Verdict

## Supported Analysis

The gate must:

1. obtain the baseline-to-HEAD change set without assuming a `src/` root;
2. classify whether the changed source language/layout is supported;
3. extract added public Python `def` and `class` symbols when supported;
4. search Python files with a platform-neutral implementation;
5. preserve existing caller filtering and relative-path comparison semantics.

## Verdicts

### Clean

Allowed only after discovery and scanning complete successfully over a non-vacuous supported
denominator. Output may state `0 unreferenced public symbols`.

### Findings

One finding per unreferenced public symbol, using the existing `dead_code` finding shape.

### Undeterminable

Required when:

- the diff command fails;
- the source layout/language is unsupported;
- the scanner cannot establish which files it examined;
- filesystem decoding or traversal prevents a complete scan.

The finding must carry a stable diagnostic code, a reason, and remediation. Output must not contain
the clean-zero message.

## Portability Regression Contract

A fast test injects `FileNotFoundError` at the subprocess boundary and asserts a verdict rather than
a traceback. It must not patch `shutil.which`. A separate non-Python/non-`src` fixture asserts an
undeterminable result rather than a clean pass.

## Compatibility Contract

On the current POSIX, `src/`-rooted Python repository, the pre/post reported symbol set is identical.
The existing substring exclusion (`"test" not in path`) remains unchanged.

