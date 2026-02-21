"""Backwards-compatible glossary hook import path.

Glossary hook implementation moved under ``doctrine.missions``. This
module preserves legacy imports from ``specify_cli.missions``.
"""

from doctrine.missions.glossary_hook import execute_with_glossary

__all__ = ["execute_with_glossary"]
