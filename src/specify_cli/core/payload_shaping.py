"""Generic pydantic-model wire-shaping primitive (#2407).

``core/mission_payload.py`` (#2270) and ``sync/emitter.py``'s
``_build_payload_via_model`` (#1198/#1200) each independently implemented the
same generic dump-twice-and-re-inject dance: drop ``None``-valued optionals
from the wire payload, except a caller-named allowlist of fields whose
``None`` is semantically meaningful (e.g. ``MissionCreated.mission_number``,
where the canonical contract distinguishes pre-merge nullity from field
absence, FR-024).

This module extracts that one shared primitive so a future change to
None-dropping wire-shape semantics is made once, not per-copy. It
deliberately does NOT extract each caller's own validation-failure policy:
``sync/emitter.py`` catches ``pydantic.ValidationError`` and returns
``None`` (its historical "invalid input -> silently skip emission"
contract); ``core/mission_payload.py`` lets it propagate (callers there
catch it at their own boundary). That split is a caller-specific concern,
correctly living at each call site, not in this shared primitive
(confirmed by the #2398 landing review — folding it in here would leak
INTEGRATION-specific console-warning behavior into a CORE module).

Pure CORE module: no I/O, no INTEGRATION imports.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def apply_keep_none_fields(
    model: BaseModel,
    *,
    keep_none_fields: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Dump ``model`` dropping ``None``-valued optionals, except kept fields.

    Mirrors the wire shape most producers want: fields not explicitly set
    are absent from the payload (not present as ``null``), EXCEPT the
    fields named in ``keep_none_fields`` — those survive as an explicit
    ``null`` even when unset, because the wire contract for that field
    distinguishes "known to be absent" from "not provided."
    """
    payload: dict[str, Any] = model.model_dump(mode="json", exclude_none=True)
    if keep_none_fields:
        full = model.model_dump(mode="json", exclude_none=False)
        for name in keep_none_fields:
            if name in full and name not in payload:
                payload[name] = full[name]
    return payload
