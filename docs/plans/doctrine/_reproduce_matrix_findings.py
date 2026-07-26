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
from pathlib import Path

HERE = Path(__file__).parent


def spectral_radius(matrix: list[list[float]], iterations: int = 400) -> float:
    """Dominant |eigenvalue| by power iteration."""
    size = len(matrix)
    vector = [1.0] * size
    magnitude = 0.0
    for _ in range(iterations):
        product = [sum(matrix[i][j] * vector[j] for j in range(size)) for i in range(size)]
        norm = math.sqrt(sum(x * x for x in product))
        if norm < 1e-15:
            return 0.0
        vector = [x / norm for x in product]
        magnitude = norm
    return magnitude


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
            candidate[2][6] = candidate[6][2] = value
        g = spectral_radius(candidate) / divisor
        r = 0.5 * g
        print(f"  {label:20s} gain={g:.4f}  residual={100 * r**2 / (1 - r):.2f}%")

    print("\nGershgorin equality cases (gain = 1 at perfect polarisation, not only perfect agreement):")
    for size in (3, 5, 7, 12):
        all_pos = [[0.0 if i == j else 1.0 for j in range(size)] for i in range(size)]
        all_neg = [[0.0 if i == j else -1.0 for j in range(size)] for i in range(size)]
        print(f"  N={size:2d}  all +1 -> {spectral_radius(all_pos) / (size - 1):.4f}"
              f"   all -1 -> {spectral_radius(all_neg) / (size - 1):.4f}")


if __name__ == "__main__":
    main()
