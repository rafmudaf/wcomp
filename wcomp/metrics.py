"""
Pairwise quantitative comparison metrics between two software packages'
results for the same case, used by the dataset generator so the frontend
can show error metrics as data (sortable tables) rather than recomputing
them from raw arrays in the browser.
"""

import numpy as np

from .output_struct import WakePlane, WakeProfile


def _summarize(diff_values: np.ndarray, reference_values: np.ndarray) -> dict:
    diff_values = np.asarray(diff_values)
    reference_values = np.asarray(reference_values)
    value_range = np.ptp(reference_values)

    rmse = float(np.sqrt(np.mean(diff_values ** 2)))
    max_abs = float(np.max(np.abs(diff_values)))
    mean_abs = float(np.mean(np.abs(diff_values)))
    # Normalized by the reference's own value range so it's comparable across
    # cases/locations with different wind speeds; undefined for a constant reference.
    nrmse = float(rmse / value_range) if value_range > 0 else None

    return {
        "rmse": rmse,
        "max_abs": max_abs,
        "mean_abs": mean_abs,
        "nrmse": nrmse,
    }


def profile_metrics(a: WakeProfile, b: WakeProfile) -> dict:
    """Compare two `WakeProfile`s sampled on the same grid."""
    diff = a - b
    return _summarize(diff.values, a.values)


def plane_metrics(a: WakePlane, b: WakePlane) -> dict:
    """Compare two `WakePlane`s sampled on the same grid."""
    diff = a - b
    return _summarize(diff.values, a.values)
