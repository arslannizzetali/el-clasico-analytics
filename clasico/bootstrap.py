"""Match-level bootstrap with numpy: the method of scripts/uncertainty.py, vectorised so it runs on hundreds
of matches and many groups.

A group's matches are drawn with replacement B times (the match is the unit: events within a match are not
independent) and the metric is recomputed as a ratio of sums. The 5th and 95th percentiles give a 90% interval.
A difference between two groups (two periods, or Clásicos vs other matches) is the difference of independent
resamples, paired by draw; if its interval excludes 0 the difference is called clear.
"""
import numpy as np

B = 5000
SEED = 2021
LEVEL = 0.90


def ratio(num, den, scale=1):
    d = den.sum()
    return scale * num.sum() / d if d else np.nan


def resample(num, den, scale, rng, b=B):
    """b resampled ratio-of-sums values, in draw order. A draw with an empty denominator keeps the observed
    value (as the reference does), so the array always has b values."""
    num, den = np.asarray(num, float), np.asarray(den, float)
    idx = rng.integers(0, len(num), size=(b, len(num)))
    n, d = num[idx].sum(axis=1), den[idx].sum(axis=1)
    with np.errstate(divide='ignore', invalid='ignore'):
        out = scale * n / d
    out[d == 0] = ratio(num, den, scale)
    return out


def percentile(samples, q):
    """Nearest-rank percentile, the same rule as scripts/uncertainty.py."""
    s = np.sort(samples)
    return float(s[min(len(s) - 1, max(0, round(q * (len(s) - 1))))])


def interval(samples, level=LEVEL):
    lo = (1 - level) / 2
    return percentile(samples, lo), percentile(samples, 1 - lo)
