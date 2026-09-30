import numpy as np
import pytest

from wcomp.metrics import plane_metrics, profile_metrics
from wcomp.output_struct import WakePlane, WakeProfile


def test_profile_metrics_convert_array_like_values_to_numpy():
    class ArrayLike:
        def __array__(self, dtype=None, copy=None):
            return np.asarray([8.0, 9.0, 10.0], dtype=dtype)

    a = WakeProfile(np.array([0.0, 1.0, 2.0]), np.array([8.0, 9.0, 10.0]))
    b = WakeProfile(np.array([0.0, 1.0, 2.0]), ArrayLike())

    assert profile_metrics(a, b)["rmse"] == 0.0


def test_profile_metrics_align_reordered_coordinates():
    a = WakeProfile(np.array([0.0, 1.0, 2.0]), np.array([8.0, 9.0, 10.0]))
    b = WakeProfile(np.array([2.0, 0.0, 1.0]), np.array([10.0, 8.0, 9.0]))

    assert profile_metrics(a, b)["rmse"] == 0.0


def test_plane_metrics_align_different_flattening_orders():
    a = WakePlane(
        np.array([0.0, 0.0, 1.0, 1.0]),
        np.array([0.0, 1.0, 0.0, 1.0]),
        np.array([8.0, 9.0, 10.0, 11.0]),
        "y",
    )
    b = WakePlane(
        np.array([0.0, 1.0, 0.0, 1.0]),
        np.array([0.0, 0.0, 1.0, 1.0]),
        np.array([8.0, 10.0, 9.0, 11.0]),
        "y",
    )

    assert plane_metrics(a, b)["rmse"] == 0.0


def test_subtraction_rejects_different_coordinates():
    a = WakeProfile(np.array([0.0, 1.0]), np.array([8.0, 9.0]))
    b = WakeProfile(np.array([0.0, 2.0]), np.array([8.0, 9.0]))

    with pytest.raises(ValueError, match="matching grid coordinates"):
        a - b
