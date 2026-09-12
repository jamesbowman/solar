"""Reading, smoothing, and integrating time series without filling data gaps."""

import json
import math
import warnings
from pathlib import Path

import numpy as np


def load_records(directory):
    records = []
    skipped = 0
    for path in Path(directory).glob('*.json'):
        try:
            record = json.loads(path.read_text())
            if not isinstance(record, dict):
                raise ValueError('expected an object')
            records.append(record)
        except (FileNotFoundError, ValueError):
            # Mirroring can expose empty/partial files, or remove a file mid-read.
            skipped += 1
    if skipped:
        warnings.warn(f'Skipped {skipped} incomplete/invalid records in {directory}')
    return records


def clean_samples(samples, t0, t1):
    by_time = {}
    for timestamp, value in samples:
        try:
            timestamp, value = float(timestamp), float(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(timestamp) and math.isfinite(value) and t0 <= timestamp <= t1:
            by_time[timestamp] = value
    return sorted(by_time.items())


def gap_limit(samples):
    """Allow brief missed polls, including the bedroom sensor's 10-minute cadence."""
    if len(samples) < 2:
        return 300.0
    intervals = np.diff([t for t, _ in samples])
    # Use the faster half so an outage does not become the inferred poll interval.
    cadence = np.median(intervals[intervals <= np.median(intervals)])
    return float(np.clip(3 * cadence, 300, 1800))


def segments(samples, max_gap):
    start = 0
    for i in range(1, len(samples)):
        if samples[i][0] - samples[i - 1][0] > max_gap:
            yield samples[start:i]
            start = i
    if samples:
        yield samples[start:]


def smooth(samples, h, t0, t1, max_gap=None):
    samples = clean_samples(samples, t0, t1)
    max_gap = gap_limit(samples) if max_gap is None else max_gap
    grid = np.linspace(t0, t1, h)
    sigma = (t1 - t0) / max(1, h - 1)
    times, values = [], []
    for run in segments(samples, max_gap):
        tt, vv = np.asarray(run, dtype=float).T
        # Include actual endpoints so recordings shorter than a grid step survive.
        targets = np.unique(np.r_[tt[0], grid[(grid > tt[0]) & (grid < tt[-1])], tt[-1]])
        if times:
            times.append(float('nan'))
            values.append(float('nan'))
        for target in targets:
            delta = (tt - target) / sigma
            exponent = -0.5 * delta ** 2
            # Normalizing relative weights preserves constants even far from a poll.
            weights = np.exp(exponent - exponent.max())
            times.append(target)
            values.append(float(np.dot(weights, vv) / weights.sum()))
    values = np.asarray(values)
    return np.asarray(times), np.isfinite(values).astype(float), values


def recorded_energy(samples, max_gap):
    """Return joules and covered seconds; never extrapolate into missing periods."""
    energy = duration = 0.0
    for run in segments(samples, max_gap):
        for (t0, v0), (t1, v1) in zip(run, run[1:]):
            dt = t1 - t0
            energy += dt * (v0 + v1) / 2
            duration += dt
    return energy, duration
