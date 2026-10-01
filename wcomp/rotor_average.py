from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

import foxes.variables as FV
import numpy as np
from floris.core.grid import TurbineGrid
from floris.core.rotor_velocity import average_velocity as floris_average_velocity
from foxes.models.model_book import ModelBook
from py_wake.rotor_avg_models import GridRotorAvg


Profile = Callable[[np.ndarray, np.ndarray], np.ndarray]
ProfileEvaluator = Callable[[Profile], float]


@dataclass(frozen=True)
class RotorAverageMethod:
    software: str
    method: str
    sampling: str
    aggregation: str
    nodes_y: tuple[float, ...]
    nodes_z: tuple[float, ...]
    weights: tuple[float, ...]
    implementation: str
    evaluator: ProfileEvaluator = field(repr=False, compare=False)

    @property
    def sample_count(self) -> int:
        return len(self.weights)

    def evaluate(self, profile: Profile) -> float:
        return self.evaluator(profile)


@dataclass(frozen=True)
class RotorAverageCase:
    key: str
    name: str
    formula: str
    description: str
    profile: Profile
    analytic_area_average: float | None = None


@dataclass(frozen=True)
class RotorAverageResult:
    case: str
    software: str
    method: str
    sample_count: int
    aggregation: str
    rotor_average: float
    reference_average: float
    absolute_error: float
    relative_error: float


def _floris_rotor_average_method() -> RotorAverageMethod:
    """Build the configured FLORIS grid and execute FLORIS' native average."""
    rotor_radius = 1.0
    hub_height = 1.0
    grid_resolution = 3
    grid = TurbineGrid(
        turbine_coordinates=[np.array([0.0, 0.0, hub_height])],
        turbine_diameters=np.array([2.0 * rotor_radius]),
        wind_directions=np.array([270.0]),
        grid_resolution=grid_resolution,
    )
    nodes_y = np.asarray(grid.y_sorted) / rotor_radius
    nodes_z = (np.asarray(grid.z_sorted) - hub_height) / rotor_radius

    def evaluate(profile: Profile) -> float:
        velocities = profile(nodes_y, nodes_z)
        result = floris_average_velocity(
            velocities,
            method=grid.average_method,
            cubature_weights=grid.cubature_weights,
        )
        return float(np.asarray(result).item())

    sample_count = nodes_y.size
    return RotorAverageMethod(
        software="FLORIS",
        method=f"{type(grid).__name__} ({grid_resolution} x {grid_resolution})",
        sampling=(
            "Nine equal-weight points on a square spanning -0.5R to 0.5R "
            "in the lateral and vertical directions."
        ),
        aggregation=f"{grid.average_method.replace('-', ' ')} of velocity",
        nodes_y=tuple(float(value) for value in nodes_y.ravel()),
        nodes_z=tuple(float(value) for value in nodes_z.ravel()),
        weights=(1.0 / sample_count,) * sample_count,
        implementation=(
            "Executed with FLORIS TurbineGrid(grid_resolution=3) and FLORIS "
            "average_velocity using the grid's native average_method."
        ),
        evaluator=evaluate,
    )


def _foxes_rotor_average_method() -> RotorAverageMethod:
    """Build FOXES grid16 and execute FOXES' native REWS calculation."""
    rotor = ModelBook().rotor_models["grid16"]
    rotor.initialize(None)
    design_points = np.asarray(rotor.design_points())
    weights = np.asarray(rotor.rotor_point_weights())
    nodes_y = design_points[:, 1]
    nodes_z = design_points[:, 2]
    rotor.calc_vars = [FV.REWS]

    def evaluate(profile: Profile) -> float:
        velocities = profile(nodes_y, nodes_z)
        farm_data = {FV.YAW: np.array([[270.0]])}
        rotor_point_data = {
            FV.WD: np.full((1, 1, velocities.size), 270.0),
            FV.WS: velocities.reshape(1, 1, -1),
        }
        rotor.eval_rpoint_results(
            None,
            None,
            farm_data,
            rotor_point_data,
            weights,
        )
        return float(np.asarray(farm_data[FV.REWS]).item())

    return RotorAverageMethod(
        software="FOXES",
        method=f"{type(rotor).__name__} (grid16)",
        sampling=(
            "Sixteen cell-center points on a 4 x 4 square spanning the rotor. "
            "Weights are evaluated by FOXES from each cell's overlap with the disk; "
            "the four corner cell centers lie outside the disk but retain partial-cell weight."
        ),
        aggregation="weighted arithmetic mean of velocity",
        nodes_y=tuple(float(value) for value in nodes_y),
        nodes_z=tuple(float(value) for value in nodes_z),
        weights=tuple(float(weight) for weight in weights),
        implementation=(
            "Executed with FOXES ModelBook grid16 and GridRotor.eval_rpoint_results, "
            "requesting FOXES' native REWS output."
        ),
        evaluator=evaluate,
    )


def _pywake_rotor_average_method() -> RotorAverageMethod:
    """Build GridRotorAvg and execute PyWake's native deficit averaging."""
    rotor = GridRotorAvg()
    nodes_y = np.asarray(rotor.nodes_x)
    nodes_z = np.asarray(rotor.nodes_y)
    weights = getattr(rotor, "nodes_weight", None)
    if weights is None:
        weights = np.full(nodes_y.size, 1.0 / nodes_y.size)
    else:
        weights = np.asarray(weights)

    def evaluate(profile: Profile) -> float:
        shape = (1, 1, 1, 1)

        def deficit(hcw_ijlk: np.ndarray, dh_ijlk: np.ndarray, **_: object) -> np.ndarray:
            return 1.0 - profile(hcw_ijlk, dh_ijlk)

        averaged_deficit = rotor(
            deficit,
            D_dst_ijl=np.full((1, 1, 1), 2.0),
            hcw_ijlk=np.zeros(shape),
            dh_ijlk=np.zeros(shape),
            dw_ijlk=np.ones(shape),
        )
        return 1.0 - float(np.asarray(averaged_deficit).item())

    return RotorAverageMethod(
        software="PyWake",
        method=type(rotor).__name__,
        sampling="Four equal-weight points at (+/-R/3, +/-R/3) in the rotor plane.",
        aggregation="weighted arithmetic mean of velocity",
        nodes_y=tuple(float(value) for value in nodes_y),
        nodes_z=tuple(float(value) for value in nodes_z),
        weights=tuple(float(weight) for weight in weights),
        implementation=(
            "Executed with PyWake GridRotorAvg.__call__. PyWake averages the supplied "
            "deficit at its native rotor nodes; the comparison converts that result back "
            "to normalized velocity."
        ),
        evaluator=evaluate,
    )


def get_rotor_average_methods() -> tuple[RotorAverageMethod, ...]:
    """Instantiate the configured native rotor-average models."""
    return (
        _floris_rotor_average_method(),
        _foxes_rotor_average_method(),
        _pywake_rotor_average_method(),
    )


def uniform_velocity(y_over_r: np.ndarray, z_over_r: np.ndarray) -> np.ndarray:
    """Uniform inflow; every consistent quadrature must reproduce this exactly."""
    return np.ones_like(y_over_r)


def linear_velocity(
    y_over_r: np.ndarray,
    z_over_r: np.ndarray,
    *,
    shear: float = 0.20,
) -> np.ndarray:
    """Linear vertical shear across the rotor."""
    return 1.0 + shear * z_over_r


def quadratic_velocity(
    y_over_r: np.ndarray,
    z_over_r: np.ndarray,
    *,
    amplitude: float = 0.20,
) -> np.ndarray:
    """Axisymmetric quadratic deficit centered on the hub."""
    return 1.0 - amplitude * (y_over_r**2 + z_over_r**2)


def offset_gaussian_velocity(
    y_over_r: np.ndarray,
    z_over_r: np.ndarray,
    *,
    depth: float = 0.35,
    center_y: float = 0.35,
    center_z: float = 0.0,
    sigma: float = 0.28,
) -> np.ndarray:
    """Normalized velocity field for the shared partial-wake-like test case."""
    radius_squared = (y_over_r - center_y) ** 2 + (z_over_r - center_z) ** 2
    return 1.0 - depth * np.exp(-radius_squared / (2.0 * sigma**2))


def get_rotor_average_cases() -> tuple[RotorAverageCase, ...]:
    """Return the case ladder, from an exactness check to a partial wake."""
    return (
        RotorAverageCase(
            key="uniform",
            name="Uniform inflow",
            formula="U/U∞ = 1",
            description=(
                "A constant field. Any quadrature whose weights sum to one is exact here, "
                "so this verifies the harness and the normalization of each stencil rather "
                "than discriminating between methods."
            ),
            profile=uniform_velocity,
            analytic_area_average=1.0,
        ),
        RotorAverageCase(
            key="linear",
            name="Linear vertical shear",
            formula="U/U∞ = 1 + 0.2 (z/R)",
            description=(
                "A linear profile. Because all three stencils are symmetric about the hub "
                "height, the positive and negative contributions cancel and the area average "
                "is still recovered exactly. Point placement starts to matter only once the "
                "aggregation is nonlinear."
            ),
            profile=linear_velocity,
            analytic_area_average=1.0,
        ),
        RotorAverageCase(
            key="quadratic",
            name="Quadratic radial deficit",
            formula="U/U∞ = 1 - 0.2 (r/R)²",
            description=(
                "The first case with real curvature. The exact area average is 0.9. Stencils "
                "clustered near the hub under-resolve the slower flow near the blade tips and "
                "overpredict the rotor average, which exposes how far each sampling pattern "
                "reaches toward the rotor edge."
            ),
            profile=quadratic_velocity,
            analytic_area_average=0.9,
        ),
        RotorAverageCase(
            key="partial_wake",
            name="Offset Gaussian velocity deficit",
            formula="U/U∞ = 1 - 0.35 exp(-((y/R - 0.35)² + (z/R)²) / (2 · 0.28²))",
            description=(
                "A laterally offset deficit that approximates a partially waked rotor. It is "
                "neither symmetric nor smooth on the scale of the coarse stencils, so it is "
                "the most demanding case and the one most representative of wake-model use."
            ),
            profile=offset_gaussian_velocity,
        ),
    )


def dense_disk_average(
    profile: Profile,
    aggregation: str,
    *,
    radial_order: int = 128,
    azimuth_count: int = 720,
) -> float:
    """Integrate a normalized profile over the unit disk."""
    radial_nodes, radial_weights = np.polynomial.legendre.leggauss(radial_order)
    radius = 0.5 * (radial_nodes + 1.0)
    radial_weights = 0.5 * radial_weights
    theta = np.linspace(0.0, 2.0 * np.pi, azimuth_count, endpoint=False)
    rr, tt = np.meshgrid(radius, theta, indexing="ij")
    values = profile(rr * np.cos(tt), rr * np.sin(tt))
    area_weights = 2.0 * radial_weights[:, None] * rr / azimuth_count

    if aggregation == "cubic mean of velocity":
        return float(np.cbrt(np.sum(area_weights * values**3)))
    if aggregation == "quadratic mean of velocity":
        return float(np.sqrt(np.sum(area_weights * values**2)))
    if aggregation == "weighted arithmetic mean of velocity":
        return float(np.sum(area_weights * values))
    raise ValueError(f"Unsupported aggregation: {aggregation}")


def compare_rotor_average_methods(
    case: RotorAverageCase | None = None,
    methods: tuple[RotorAverageMethod, ...] | None = None,
) -> list[RotorAverageResult]:
    """Run the native framework methods on one common rotor-plane case."""
    if case is None:
        case = get_rotor_average_cases()[-1]
    if methods is None:
        methods = get_rotor_average_methods()

    references: dict[str, float] = {}
    results = []
    for method in methods:
        reference = references.setdefault(
            method.aggregation,
            dense_disk_average(case.profile, method.aggregation),
        )
        sample = method.evaluate(case.profile)
        absolute_error = abs(sample - reference)
        results.append(
            RotorAverageResult(
                case=case.key,
                software=method.software,
                method=method.method,
                sample_count=method.sample_count,
                aggregation=method.aggregation,
                rotor_average=sample,
                reference_average=reference,
                absolute_error=absolute_error,
                relative_error=absolute_error / abs(reference),
            )
        )
    return results


def build_rotor_average_plan(
    methods: tuple[RotorAverageMethod, ...] | None = None,
) -> list[dict[str, object]]:
    """Return a serializable description of the configured methods."""
    if methods is None:
        methods = get_rotor_average_methods()
    return [
        {
            "software": method.software,
            "method": method.method,
            "sample_count": method.sample_count,
            "sampling": method.sampling,
            "aggregation": method.aggregation,
            "implementation": method.implementation,
            "nodes_y": list(method.nodes_y),
            "nodes_z": list(method.nodes_z),
            "weights": list(method.weights),
        }
        for method in methods
    ]


def build_rotor_average_dataset() -> dict[str, object]:
    """Build the static dataset consumed by the rotor-averaging site page."""
    methods = get_rotor_average_methods()
    return {
        "coordinates": "All sampling coordinates are normalized by rotor radius R.",
        "execution": (
            "Each common velocity field is passed to the installed framework's native "
            "rotor-grid and rotor-averaging implementation. No framework result is "
            "calculated by a wcomp replacement formula."
        ),
        "reference": (
            "128-point Gauss-Legendre radial integration with 720 azimuthal points. "
            "Each software result is compared with a dense-disk reference using the "
            "same aggregation semantics."
        ),
        "methods": build_rotor_average_plan(methods),
        "cases": [
            {
                "key": case.key,
                "name": case.name,
                "formula": case.formula,
                "description": case.description,
                "analytic_area_average": case.analytic_area_average,
                "field": _sample_field(case.profile),
                "results": [
                    asdict(result)
                    for result in compare_rotor_average_methods(case, methods)
                ],
            }
            for case in get_rotor_average_cases()
        ],
    }


def _sample_field(profile: Profile, resolution: int = 81) -> dict[str, object]:
    """Sample a profile on a square grid for plotting, masking points off the disk."""
    axis = np.linspace(-1.0, 1.0, resolution)
    yy, zz = np.meshgrid(axis, axis, indexing="xy")
    values = np.where(yy**2 + zz**2 <= 1.0, profile(yy, zz), np.nan)
    return {
        "axis": [float(value) for value in axis],
        "values": [[None if np.isnan(v) else float(v) for v in row] for row in values],
    }


def format_rotor_average_summary(results: list[RotorAverageResult]) -> str:
    """Return a compact Markdown table for one case."""
    lines = [
        "| Software | Method | Points | Aggregation | Rotor avg | Reference | Abs. error |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: |",
    ]
    for result in results:
        lines.append(
            f"| {result.software} | {result.method} | {result.sample_count} | "
            f"{result.aggregation} | {result.rotor_average:.6f} | "
            f"{result.reference_average:.6f} | {result.absolute_error:.6f} |"
        )
    return "\n".join(lines)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Compare configured rotor-average methods.")
    parser.add_argument("--output", type=Path, help="Write the site dataset as JSON.")
    args = parser.parse_args()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(build_rotor_average_dataset(), indent=2) + "\n",
            encoding="utf-8",
        )
    else:
        for case in get_rotor_average_cases():
            print(f"## {case.name}")
            print()
            print(f"{case.formula}")
            if case.analytic_area_average is not None:
                print(f"Exact area average: {case.analytic_area_average}")
            print()
            print(format_rotor_average_summary(compare_rotor_average_methods(case)))
            print()


if __name__ == "__main__":
    _main()
