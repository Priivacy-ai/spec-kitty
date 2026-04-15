"""Compatibility alias for the canonical charter interview module."""

from __future__ import annotations

import sys

from charter import interview as _interview

sys.modules[__name__] = _interview
