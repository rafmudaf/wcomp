
import numpy as np
from typing import Tuple


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

        _x1 = self.x1 - other.x1
        _x2 = self.x2 - other.x2
        _values = self.values - other.values

        return WakePlane(_x1, _x2, _values, self.normal_vector, self.resolution)

class WakeVolume:
    def __init__(self, df, x1_resolution, x2_resolution, normal_vector):
        pass
