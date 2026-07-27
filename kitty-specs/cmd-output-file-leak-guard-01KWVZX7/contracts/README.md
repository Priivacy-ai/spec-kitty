# Contracts — cmd-output-file-leak-guard-01KWVZX7 (#2169)

This mission ships **no new API contract**. It is a test-infrastructure fix: it stops a test double from leaking a `"${SPEC_KITTY_CMD_OUTPUT_FILE}"`-named junk file into the working tree, and adds a `tests/architectural/` guard (registered in the sharded arch pole) forbidding Windows-illegal / shell-leak-telltale tracked filenames. No production code or external contract changes.
