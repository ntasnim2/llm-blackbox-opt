#!/usr/bin/env python3
"""Private objective used by the local hide-optimum evaluator.

The optimizing Codex session should not read or import this file. The public
interface reports only incumbent improvement, not objective values or distance
to a known optimum.
"""

from __future__ import annotations

import math


SHIFT = [3.3, -0.8, 1.7]
RIPPLE_AMPLITUDE = 0.05
RIPPLE_FREQUENCIES = [1.7, 2.3, 3.1]
RIPPLE_PHASES = [0.4, -1.1, 2.0]


def objective(x: list[float]) -> float:
    if not x:
        raise ValueError("objective requires at least one coordinate")
    if len(x) != len(SHIFT):
        raise ValueError(f"expected {len(SHIFT)} coordinates, got {len(x)}")
    if len(RIPPLE_FREQUENCIES) != len(SHIFT) or len(RIPPLE_PHASES) != len(SHIFT):
        raise ValueError("ripple parameters must match objective dimension")

    shifted_x = [value - shift for value, shift in zip(x, SHIFT)]

    d = len(shifted_x)
    sum_squares = sum(value * value for value in shifted_x)
    sum_cosines = sum(math.cos(2.0 * math.pi * value) for value in shifted_x)
    first_term = -20.0 * math.exp(-0.2 * math.sqrt(sum_squares / d))
    second_term = -math.exp(sum_cosines / d)
    base_value = first_term + second_term + 20.0 + math.e + 5.0
    ripple = RIPPLE_AMPLITUDE * sum(
        math.sin(frequency * value + phase)
        for value, frequency, phase in zip(x, RIPPLE_FREQUENCIES, RIPPLE_PHASES)
    )
    return base_value + ripple
