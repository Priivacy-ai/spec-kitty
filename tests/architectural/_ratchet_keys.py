"""Shared key-building primitives for architectural ratchets (FR-008 / WP06).

.. note::
   **Promoted to ``src/`` (#2441 / FR-003).** The implementation now lives in
   :mod:`specify_cli.contracts.anchoring` so production code (the Contract
   Registry loader/validator + the retirement absence-sweep driver) can depend
   on the same DIR-041-compliant content-anchoring primitive — ``src/`` cannot
   import from ``tests/``, so the primitive had to move to ``src/``. This module
   is now a thin **re-export shim**: every existing ratchet caller keeps
   importing ``composite_key`` / ``code_tokens_by_line`` / ``enclosing_qualname``
   / ``composite_key_from_file`` from ``tests.architectural._ratchet_keys`` with
   NO behaviour change.

Provides two complementary building blocks that together produce a drift-proof
``(enclosing_qualname, normalized_token_line)`` composite key for any line in a
Python source file.  The composite survives a ``+1`` line drift caused by
inserting a blank or comment line above a pinned site: neither the enclosing
function name nor the content of the guarded code line changes, so the ratchet
stays GREEN.  Only a genuine semantic change — a new offending line or a
function rename — produces a different key.

Usage
-----
::

    from tests.architectural._ratchet_keys import composite_key

    source = Path("src/foo/bar.py").read_text(encoding="utf-8")
    key = composite_key(source, lineno=42)
    # returns (qualname_str, token_line_str)

See :mod:`specify_cli.contracts.anchoring` for the full design notes.
"""

from __future__ import annotations

from specify_cli.contracts.anchoring import (
    code_tokens_by_line,
    composite_key,
    composite_key_from_file,
    enclosing_qualname,
)

__all__ = [
    "code_tokens_by_line",
    "composite_key",
    "composite_key_from_file",
    "enclosing_qualname",
]
