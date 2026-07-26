#!/usr/bin/env python3
"""Reproduce every numeric claim in the FoundationalValues design's maths section.

Usage:  python3 docs/plans/doctrine/_reproduce_matrix_findings.py
Reads:  docs/plans/doctrine/_ammerse-connascence-first-order.json
No dependencies beyond the standard library.
"""
from __future__ import annotations

import copy
import json
import math
import os
import random
from pathlib import Path

HERE = Path(__file__).parent

#: Random-basis samples. Kept small so the script stays fast; the committed figure
#: in the design document used 30000 samples with 400 power iterations each.
SAMPLES = int(os.environ.get("SAMPLES", "2000"))


def _power(matrix: list[list[float]], vector: list[float], iterations: int) -> float:
    """One power-iteration run from a given start vector."""
    size = len(matrix)
    magnitude = 0.0
    for _ in range(iterations):
        product = [sum(matrix[i][j] * vector[j] for j in range(size)) for i in range(size)]
        norm = math.sqrt(sum(x * x for x in product))
        if norm < 1e-15:
            return 0.0
        vector = [x / norm for x in product]
        magnitude = norm
    return magnitude


def spectral_radius(matrix: list[list[float]], iterations: int = 400) -> float:
    """Dominant |eigenvalue| by power iteration with seeded random restarts.

    A single fixed start vector is FAIL-OPEN: on a two-camp +-1 basis the
    all-ones vector is an eigenvector of a smaller eigenvalue, so plain power
    iteration reports gain 0.33 for a basis whose true gain is exactly 1.0.
    Random restarts (seeded, so figures stay reproducible) make the estimate
    start-vector independent with overwhelming probability. A shipping
    validator should use this or the characteristic polynomial at small N.
    """
    size = len(matrix)
    best = _power(matrix, [1.0] * size, iterations)
    # noqa rationale: numerical restart seeds for a reproducibility check, not a
    # security context; determinism is required for the figures to reproduce.
    rng = random.Random(1234)  # noqa: S311
    for _ in range(8):
        start = [rng.uniform(-1.0, 1.0) for _ in range(size)]
        best = max(best, _power(matrix, start, iterations))
    return best


def main() -> None:
    data = json.loads((HERE / "_ammerse-connascence-first-order.json").read_text())
    matrix, axes = data["matrix"], data["axes"]
    n = len(axes)
    divisor = n - 1

    lam = spectral_radius(matrix)
    gain = lam / divisor
    ratio = 0.5 * gain

    print(f"N = {n}, divisor = N-1 = {divisor}")
    print(f"lambda            = {lam:.4f}")
    print(f"gain lambda/(N-1) = {gain:.4f}   (bounded by 1 via Gershgorin)")
    print(f"damped ratio r    = {ratio:.4f}")
    print(f"residual, adopted two-term damped truncation r^2/(1-r) = {100 * ratio**2 / (1 - ratio):.2f}%")
    print(f"final scale (1-r) = {1 - ratio:.4f}")

    print("\nsensitivity to the asymmetric cell (maintainable <-> extensible):")
    for label, value in (("as published", None), ("symmetrised +0.75", 0.75),
                         ("symmetrised -0.75", -0.75), ("zeroed (abstain)", 0.0)):
        candidate = copy.deepcopy(matrix)
        if value is not None:
            i_m, i_e = axes.index("maintainable"), axes.index("extensible")
            candidate[i_m][i_e] = candidate[i_e][i_m] = value
        g = spectral_radius(candidate) / divisor
        r = 0.5 * g
        print(f"  {label:20s} gain={g:.4f}  residual={100 * r**2 / (1 - r):.2f}%")

    print("\nGershgorin equality cases (gain = 1 at perfect polarisation, not only perfect agreement):")
    for size in (3, 5, 7, 12):
        all_pos = [[0.0 if i == j else 1.0 for j in range(size)] for i in range(size)]
        all_neg = [[0.0 if i == j else -1.0 for j in range(size)] for i in range(size)]
        print(f"  N={size:2d}  all +1 -> {spectral_radius(all_pos) / (size - 1):.4f}"
              f"   all -1 -> {spectral_radius(all_neg) / (size - 1):.4f}")

    print(f"\nrandom admissible bases at N={n} (symmetric, zero diagonal, uniform [-1,1]):")
    print(f"  {SAMPLES} samples — the committed figure is 30000 samples: max 0.6225, mean 0.3841")
    # noqa rationale: numerical sampling for a reproducibility check, not a security
    # context. A fixed seed is required so the reported figures are reproducible.
    rng = random.Random(7)  # noqa: S311
    worst = 0.0
    total = 0.0
    for _ in range(SAMPLES):
        candidate = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                candidate[i][j] = candidate[j][i] = rng.uniform(-1.0, 1.0)
        sampled = spectral_radius(candidate, iterations=120) / divisor
        worst = max(worst, sampled)
        total += sampled
    print(f"  max gain = {worst:.4f}, mean = {total / SAMPLES:.4f}  (bound is 1.0)")


if __name__ == "__main__":
    main()
