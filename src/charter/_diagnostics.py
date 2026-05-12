"""Charter-encoding diagnostic codes.

See: src/charter/ERROR_CODES.md (hand-maintained mirror until the
code-to-docs flow envisioned in GitHub #645 ships).
"""

from enum import StrEnum


class CharterEncodingDiagnostic(StrEnum):
    """JSON-stable diagnostic codes emitted by src/charter/_io.py.

    Per-code remediation guidance is documented in src/charter/ERROR_CODES.md.
    """

    AMBIGUOUS = "CHARTER_ENCODING_AMBIGUOUS"
    NOT_NORMALIZED = "CHARTER_ENCODING_NOT_NORMALIZED"
