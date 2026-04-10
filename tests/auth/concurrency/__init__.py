"""Concurrency tests for the spec-kitty auth subsystem.

Focus: single-flight refresh guarantees under high concurrent load.
Covers FR-009 (automatic refresh) and FR-010 (single-flight refresh).
"""
