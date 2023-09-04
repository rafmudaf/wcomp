
from typing import Tuple

import numpy as np


class WakeProfile:
    def __init__(self, x1: np.ndarray, values: np.ndarray):
        self.x1 = x1
        self.values = values

class WakePlane:

    def __init__(
        self,
        x1: np.ndarray,
        x2: np.ndarray,
        values: np.ndarray,
        normal_vector: str,
        resolution: Tuple
    ):
        self.x1 = x1
        self.x2 = x2
        self.values = values
        self.normal_vector = normal_vector
        self.resolution = resolution

    def __sub__(self, other):

        if self.normal_vector != other.normal_vector:
            raise ValueError("Operands must have consistent normal vectors.")
        if self.resolution != other.resolution:
            raise ValueError("Operands must have consistent resolutions.")
        if np.shape(self.x1) != np.shape(other.x1) \
            or np.shape(self.x2) != np.shape(other.x2):
            raise ValueError("Operands must have consistent grid shapes.")

        return WakePlane(
            self.x1,
            self.x2,
            self.values - other.values,
            self.normal_vector,
            self.resolution
        )

class WakeVolume:
    def __init__(self, df, x1_resolution, x2_resolution, normal_vector):
        pass
