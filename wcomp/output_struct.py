
from typing import Tuple

import numpy as np


class WakeProfile:
    def __init__(self, x1: np.ndarray, values: np.ndarray):
        self.x1 = x1
        self.values = values

    def __sub__(self, other):
        if np.shape(self.x1) != np.shape(other.x1):
            raise ValueError(
                "Operands must have consistent grid shapes. "
                f"self {self.x1.shape}, other {other.x1.shape}."
            )

        return WakeProfile(
            self.x1,
            self.values - other.values
        )

class WakePlane:

    def __init__(
        self,
        x1: np.ndarray,
        x2: np.ndarray,
        values: np.ndarray,
        normal_vector: str,
    ):
        self.x1 = x1
        self.x2 = x2
        self.values = values
        self.normal_vector = normal_vector

    def __sub__(self, other):

        if self.normal_vector != other.normal_vector:
            raise ValueError(
                "Operands must have consistent normal vectors. "
                f"self {self.normal_vector}, other {other.normal_vector}."
            )
        if np.shape(self.x1) != np.shape(other.x1) \
            or np.shape(self.x2) != np.shape(other.x2):
            raise ValueError(
                "Operands must have consistent grid shapes. "
                f"self {self.x1.shape}, other {other.x1.shape}."
            )

        return WakePlane(
            self.x1,
            self.x2,
            self.values - other.values,
            self.normal_vector,
        )

class WakeVolume:
    def __init__(self, df, x1_resolution, x2_resolution, normal_vector):
        pass
