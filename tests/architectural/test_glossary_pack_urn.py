"""URN regression guard for the ``glossary_pack`` DRG node kind (NFR-001).

The doctrine-owned ``GLOSSARY_PACK`` node addresses itself with the
**underscore** URN prefix ``glossary_pack:<id>``. The hyphenated form
``glossary-pack:<id>`` MUST be rejected. Two independent guard layers in
:mod:`doctrine.drg.models` enforce this and are exercised explicitly here:

1. ``_URN_RE`` — the anchored URN regex only admits ``[a-z_]`` in the kind
   prefix, so a hyphen in the prefix fails the pattern outright.
2. the ``prefix == kind.value`` assertion in ``DRGNode._validate_urn`` — even
   were the regex to admit it, the prefix must byte-for-byte equal
   ``NodeKind.GLOSSARY_PACK.value`` (``"glossary_pack"``).
"""

from __future__ import annotations

import re

import pytest
from pydantic import ValidationError

from doctrine.drg.models import _URN_RE, DRGNode, NodeKind

pytestmark = pytest.mark.fast


class TestGlossaryPackNodeKindValue:
    def test_node_kind_value_is_underscore(self) -> None:
        assert NodeKind.GLOSSARY_PACK.value == "glossary_pack"


class TestGlossaryPackUrnAccepted:
    def test_underscore_urn_is_accepted(self) -> None:
        node = DRGNode(
            urn="glossary_pack:spec-kitty-core",
            kind=NodeKind.GLOSSARY_PACK,
        )
        assert node.urn == "glossary_pack:spec-kitty-core"
        assert node.kind is NodeKind.GLOSSARY_PACK


class TestGlossaryPackUrnRejected:
    """The hyphenated prefix is rejected at BOTH guard layers."""

    def test_hyphen_prefix_fails_urn_regex_layer(self) -> None:
        # Layer 1: the raw regex must not admit a hyphenated kind prefix.
        assert _URN_RE.match("glossary-pack:spec-kitty-core") is None

    def test_hyphen_prefix_rejected_by_model_validation(self) -> None:
        # Layer 1 surfaced through the model: hyphen prefix trips ``_URN_RE``
        # inside ``DRGNode._validate_urn`` before the prefix check runs.
        with pytest.raises(ValidationError, match=re.escape(_URN_RE.pattern)):
            DRGNode(
                urn="glossary-pack:spec-kitty-core",
                kind=NodeKind.GLOSSARY_PACK,
            )

    def test_prefix_mismatch_layer_rejects_wrong_prefix(self) -> None:
        # Layer 2: a syntactically valid underscore prefix that does not equal
        # ``kind.value`` is rejected by the ``prefix == kind.value`` assertion.
        with pytest.raises(ValidationError, match="does not match kind"):
            DRGNode(
                urn="glossary:spec-kitty-core",
                kind=NodeKind.GLOSSARY_PACK,
            )
