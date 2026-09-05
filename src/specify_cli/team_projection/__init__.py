"""Compatibility package for the retired team-projection pipeline.

The D1 publish pipeline (``team-index.json``, per-mission
``team-snapshot.json``, opt-in public variants, attestation manifest) and the
``spec-kitty team-projection publish`` command were deleted: consumers read the
tracked repository directly at an exact pushed commit instead of a published
gitignored projection.
"""
