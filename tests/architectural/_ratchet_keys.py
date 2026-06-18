"""Shared key-building primitives for architectural ratchets (FR-008 / WP06).

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

Design notes
------------
* ``code_tokens_by_line`` is the tokenize-based half.  It strips STRING /
  COMMENT / whitespace tokens so docstrings and comments that merely *describe*
  a prior pattern are never treated as code.  The technique mirrors the private
  ``_code_tokens_by_line`` in ``test_no_write_side_rederivation.py``; that copy
  intentionally stays private (C-007 / the ``:295`` pin is out of scope for this
  WP).  This module is the canonical shared extraction point.

* ``enclosing_qualname`` is net-new.  It walks the ``ast`` tree to build a
  dotted ``OuterClass.inner_func`` qualname for the innermost
  ``FunctionDef`` / ``AsyncFunctionDef`` / ``ClassDef`` whose line-range
  contains ``lineno``.  Module-level code returns ``"<module>"``.

* ``composite_key`` combines both: it returns the ``(qualname, token_line)``
  tuple that serve as the allow-list lookup key.

* Complexity is kept well below 15 (ruff C901 / Sonar S3776).
"""

from __future__ import annotations

import ast
import io
import tokenize
from pathlib import Path


# ---------------------------------------------------------------------------
# Token-based half (tokenize)
# ---------------------------------------------------------------------------


# Py 3.12+ f-string delimiter token types (PEP 701). Absent on 3.11, where the
# whole f-string is a single ``STRING`` token. Used to bracket — and therefore
# uniformly drop — the f-string *interior* on 3.12 so the token-line is
# interpreter-independent (see ``code_tokens_by_line`` docstring).
_FSTRING_START = getattr(tokenize, "FSTRING_START", None)
_FSTRING_END = getattr(tokenize, "FSTRING_END", None)


def code_tokens_by_line(source: str) -> dict[int, str]:
    """Return ``{lineno: space-joined code tokens}`` with strings/comments dropped.

    Docstrings (``STRING`` tokens) and ``COMMENT`` tokens are excluded, so prose
    that merely *quotes* a prior pattern (e.g. a docstring documenting the old
    ``coord_branch or _current_branch`` selector) never registers as code.

    **Interpreter-independence (NFR-003).** On Python 3.11 an f-string is a single
    ``STRING`` token, so the *entire* f-string — including any ``{...}``
    interpolation — is dropped uniformly. PEP 701 (Python 3.12+) re-tokenizes
    f-strings into ``FSTRING_START`` / ``FSTRING_MIDDLE`` / ``FSTRING_END`` plus
    the interpolation's *ordinary* tokens (``{``, the expression names, ``}``),
    which are NOT ``FSTRING_*`` and would otherwise leak into the token-line
    (``pattern = { mission_slug }`` on 3.12 vs ``pattern =`` on 3.11). That makes
    the composite key — and every pinned ratchet baseline keyed off it — drift
    between local 3.11 and the CI 3.12 shard. To keep the key identical on both,
    the whole f-string interior (everything between ``FSTRING_START`` and the
    matching ``FSTRING_END``, inclusive of nesting) is dropped here, reproducing
    the 3.11 single-``STRING`` behaviour. This is a key-normalization change only:
    the set of flagged offenders and the allow-list semantics are unchanged.
    """
    skip: set[int] = {
        tokenize.STRING,
        tokenize.COMMENT,
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENCODING,
        tokenize.ENDMARKER,
    }
    # Py 3.12+ f-string middle token — dropped like the 3.11 STRING body. The
    # START/END delimiters are handled via the depth counter below.
    _middle = getattr(tokenize, "FSTRING_MIDDLE", None)
    if _middle is not None:
        skip.add(_middle)

    buckets: dict[int, list[str]] = {}
    fstring_depth = 0
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if _FSTRING_START is not None and tok.type == _FSTRING_START:
                fstring_depth += 1
                continue
            if _FSTRING_END is not None and tok.type == _FSTRING_END:
                fstring_depth = max(0, fstring_depth - 1)
                continue
            if fstring_depth > 0:
                # Inside an f-string: drop the interpolation tokens entirely so the
                # 3.12 token-line matches the 3.11 single-STRING form.
                continue
            if tok.type in skip:
                continue
            buckets.setdefault(tok.start[0], []).append(tok.string)
    except tokenize.TokenError:
        pass
    return {ln: " ".join(parts) for ln, parts in buckets.items()}


# ---------------------------------------------------------------------------
# AST qualname half (net-new)
# ---------------------------------------------------------------------------


def _build_qualname_map(tree: ast.AST) -> dict[tuple[int, int], str]:
    """Return ``{(start_line, end_line): qualname}`` for every scope node.

    Walks the AST and records the dotted qualname (``Outer.inner``) for every
    ``FunctionDef`` / ``AsyncFunctionDef`` / ``ClassDef`` together with its
    ``(lineno, end_lineno)`` span.  The walk is depth-first so a deeper
    (more-specific) entry is recorded after its enclosing parent; the caller
    resolves ambiguity by picking the innermost span that contains the target
    line.
    """
    entries: dict[tuple[int, int], str] = {}

    def _walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name: str = child.name
                qualname = f"{prefix}.{name}" if prefix else name
                if (
                    hasattr(child, "lineno")
                    and hasattr(child, "end_lineno")
                    and child.end_lineno is not None
                ):
                    entries[(child.lineno, child.end_lineno)] = qualname
                _walk(child, qualname)
            else:
                _walk(child, prefix)

    _walk(tree, "")
    return entries


def enclosing_qualname(source: str, lineno: int) -> str:
    """Return the dotted qualname of the innermost scope enclosing ``lineno``.

    Uses ``ast.parse`` + a full-tree walk to map each ``FunctionDef`` /
    ``AsyncFunctionDef`` / ``ClassDef`` to its line-range, then picks the
    deepest (smallest span) that contains ``lineno``.  Module-level code
    (not inside any function or class) returns ``"<module>"``.

    The returned string is stable across blank-line / comment-line insertions
    anywhere outside the function body boundary, making it suitable as the
    first component of a drift-proof composite key.

    Parameters
    ----------
    source:
        Full Python source text of the file.
    lineno:
        1-based line number to look up (matching ``ast.AST.lineno`` convention).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return "<module>"

    qualname_map = _build_qualname_map(tree)
    if not qualname_map:
        return "<module>"

    # Among all spans that contain lineno, the innermost has the smallest
    # (end - start) difference.
    candidates = [
        (end - start, qn)
        for (start, end), qn in qualname_map.items()
        if start <= lineno <= end
    ]
    if not candidates:
        return "<module>"

    _, best_qualname = min(candidates)
    return best_qualname


# ---------------------------------------------------------------------------
# Composite key builder
# ---------------------------------------------------------------------------


def composite_key(source: str, lineno: int) -> tuple[str, str]:
    """Return the drift-proof ``(qualname, token_line)`` composite key.

    Both components are stable against blank-line / comment-line insertions
    near the guarded site:

    * ``qualname`` — enclosing function/class dotted name via
      :func:`enclosing_qualname`.
    * ``token_line`` — space-joined code tokens on ``lineno`` via
      :func:`code_tokens_by_line` (strings/comments stripped).

    A key mismatch means a **semantic** change: the function was renamed, or
    the guarded code line changed.  A ``+1`` drift from an inserted blank /
    comment produces the same key because both components are content-addressed,
    not line-number-addressed.
    """
    qn = enclosing_qualname(source, lineno)
    tokens = code_tokens_by_line(source)
    tl = tokens.get(lineno, "")
    return (qn, tl)


def composite_key_from_file(path: Path, lineno: int) -> tuple[str, str]:
    """Convenience wrapper: read ``path`` then delegate to :func:`composite_key`."""
    source = path.read_text(encoding="utf-8")
    return composite_key(source, lineno)
