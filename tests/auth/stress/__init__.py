"""Stress tests for the spec-kitty auth subsystem.

Focus: file-fallback storage under concurrent writes. Covers NFR-010
(no corruption under concurrent access) and NFR-011 (atomic ops only).
"""
