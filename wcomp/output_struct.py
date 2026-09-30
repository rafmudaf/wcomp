
import numpy as np


def _coordinates_match(a: np.ndarray, b: np.ndarray) -> bool:
    return np.allclose(a, b, rtol=1e-9, atol=1e-8)


def _validate_values(values: np.ndarray, coordinates: np.ndarray) -> None:
    if values.shape != coordinates.shape:
        raise ValueError(
            "Values and coordinates must have consistent shapes. "
            f"values {values.shape}, coordinates {coordinates.shape}."
        )


def _align_profile_values(
    self_x1: np.ndarray,
    other_x1: np.ndarray,
    other_values: np.ndarray,
) -> np.ndarray:
    if self_x1.shape != other_x1.shape:
        raise ValueError(
            "Operands must have consistent grid shapes. "
            f"self {self_x1.shape}, other {other_x1.shape}."
        )

    if _coordinates_match(self_x1, other_x1):
        return other_values

    self_order = np.argsort(self_x1, kind="stable")
    other_order = np.argsort(other_x1, kind="stable")
    if not _coordinates_match(self_x1[self_order], other_x1[other_order]):
        raise ValueError("Operands must have matching grid coordinates.")

    aligned_values = np.empty_like(other_values)
    aligned_values[self_order] = other_values[other_order]
    return aligned_values


def _align_plane_values(
    self_x1: np.ndarray,
    self_x2: np.ndarray,
    other_x1: np.ndarray,
    other_x2: np.ndarray,
    other_values: np.ndarray,
) -> np.ndarray:
    if self_x1.shape != other_x1.shape or self_x2.shape != other_x2.shape:
        raise ValueError(
            "Operands must have consistent grid shapes. "
            f"self ({self_x1.shape}, {self_x2.shape}), "
            f"other ({other_x1.shape}, {other_x2.shape})."
        )

    if (_coordinates_match(self_x1, other_x1) and _coordinates_match(self_x2, other_x2)):
        return other_values

    self_order = np.lexsort((self_x2, self_x1))
    other_order = np.lexsort((other_x2, other_x1))
    if (
        not _coordinates_match(self_x1[self_order], other_x1[other_order])
        or not _coordinates_match(self_x2[self_order], other_x2[other_order])
    ):
        raise ValueError("Operands must have matching grid coordinates.")

    aligned_values = np.empty_like(other_values)
    aligned_values[self_order] = other_values[other_order]
    return aligned_values


class WakeProfile:
    def __init__(self, x1: np.ndarray, values: np.ndarray):
        self.x1 = np.asarray(x1).reshape(-1)
        self.values = np.asarray(values).reshape(-1)
        _validate_values(self.values, self.x1)

    def __sub__(self, other):
        other_values = _align_profile_values(
            self.x1,
            other.x1,
            other.values,
        )

        return WakeProfile(
            self.x1,
            self.values - other_values,
        )

    def to_dict(self) -> dict:
        """JSON-serializable representation, used by the dataset generator."""
        return {
            "x1": np.round(np.asarray(self.x1), 3).tolist(),
            "values": np.round(np.asarray(self.values), 4).tolist(),
        }


class WakePlane:

    def __init__(
        self,
        x1: np.ndarray,
        x2: np.ndarray,
        values: np.ndarray,
        normal_vector: str,
    ):
        self.x1 = np.asarray(x1).reshape(-1)
        self.x2 = np.asarray(x2).reshape(-1)
        self.values = np.asarray(values).reshape(-1)
        self.normal_vector = normal_vector
        _validate_values(self.x2, self.x1)
        _validate_values(self.values, self.x1)

    def __sub__(self, other):

        if self.normal_vector != other.normal_vector:
            raise ValueError(
                "Operands must have consistent normal vectors. "
                f"self {self.normal_vector}, other {other.normal_vector}."
            )
        other_values = _align_plane_values(
            self.x1,
            self.x2,
            other.x1,
            other.x2,
            other.values,
        )

        return WakePlane(
            self.x1,
            self.x2,
            self.values - other_values,
            self.normal_vector,
        )

    def to_dict(self) -> dict:
        """JSON-serializable representation, used by the dataset generator."""
        return {
            "x1": np.round(np.asarray(self.x1), 3).tolist(),
            "x2": np.round(np.asarray(self.x2), 3).tolist(),
            "values": np.round(np.asarray(self.values), 4).tolist(),
            "normal_vector": self.normal_vector,
        }


class WakeVolume:
    def __init__(self, df, x1_resolution, x2_resolution, normal_vector):
        pass
