"""Kernel — zero-dependency shared utilities.

This package contains primitives shared by ``specify_cli``, ``constitution``,
and ``doctrine``.  It has **no imports from any of those packages**, keeping
the dependency direction clean:

    kernel  ←  constitution
    kernel  ←  doctrine
    kernel  ←  specify_cli
"""
