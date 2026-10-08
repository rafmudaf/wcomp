"""
Compares the turbine power and thrust computations of FLORIS, FOXES, and PyWake.

One common turbine definition (a power curve and a thrust coefficient curve) is
handed to each software through its own native tabular turbine input. A single,
unwaked turbine in uniform flow is then simulated over a sweep of wind speeds,
so every difference comes from the turbine model rather than the flow.

Run with (inside the `wcomp` conda environment):
    python -m wcomp.turbine_performance --output dataset/turbine_performance.json
"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import foxes
import foxes.variables as FV
import numpy as np
import pandas as pd
from floris import FlorisModel
from foxes.models.turbine_types import PCtFromTwo
from py_wake import NOJ
from py_wake.site import UniformSite
from py_wake.wind_turbines import WindTurbine
from py_wake.wind_turbines.power_ct_functions import PowerCtTabular
from windIO import load_yaml

from .cache import quiet

REPO_ROOT = Path(__file__).resolve().parent.parent
TURBINE_FILE = (
    REPO_ROOT / "examples" / "cases_torque2024" / "one_turbine" / "jensen" / "wind_farm.yaml"
)

AIR_DENSITY = 1.225
WIND_DIRECTION = 270.0
TURBULENCE_INTENSITY = 0.075
SWEEP_STEP = 0.1
SWEEP_MAX = 30.0


@dataclass(frozen=True)
class CommonTurbine:
    """The single turbine definition shared by every software."""

    name: str
    rotor_diameter: float
    hub_height: float
    air_density: float
    wind_speeds: np.ndarray
    power_kw: np.ndarray
    ct: np.ndarray

    @property
    def rotor_area(self) -> float:
        return float(np.pi * self.rotor_diameter**2 / 4.0)

    @property
    def cut_in(self) -> float:
        return float(self.wind_speeds[0])

    @property
    def cut_out(self) -> float:
        return float(self.wind_speeds[-1])

    @property
    def rated_power_kw(self) -> float:
        return float(self.power_kw.max())


def get_common_turbine(path: Path = TURBINE_FILE) -> CommonTurbine:
    """Load the IEA 15 MW curves used by the wake cases and express them as power and Ct.

    windIO tabulates a power coefficient, so the power curve in kW is derived once here
    (P = 1/2 rho A U^3 Cp at the reference air density). Every software then receives the
    same power and Ct tables on the same wind speed grid.
    """
    turbine = load_yaml(path)["turbines"]
    cp_curve = turbine["performance"]["Cp_curve"]
    ct_curve = turbine["performance"]["Ct_curve"]
    wind_speeds = np.asarray(ct_curve["Ct_wind_speeds"], dtype=float)
    if not np.allclose(wind_speeds, cp_curve["Cp_wind_speeds"]):
        raise ValueError("The Cp and Ct curves must share a wind speed grid.")

    diameter = float(turbine["rotor_diameter"])
    area = np.pi * diameter**2 / 4.0
    power_kw = (
        0.5 * AIR_DENSITY * area * wind_speeds**3 * np.asarray(cp_curve["Cp_values"]) / 1.0e3
    )
    return CommonTurbine(
        name=str(turbine["name"]),
        rotor_diameter=diameter,
        hub_height=float(turbine["hub_height"]),
        air_density=AIR_DENSITY,
        wind_speeds=wind_speeds,
        power_kw=power_kw,
        ct=np.asarray(ct_curve["Ct_values"], dtype=float),
    )


def get_sweep_wind_speeds(turbine: CommonTurbine) -> np.ndarray:
    """Uniform sweep through and beyond the curve, plus the exact curve end points."""
    sweep = np.round(np.arange(0.0, SWEEP_MAX + SWEEP_STEP / 2, SWEEP_STEP), 6)
    return np.unique(np.concatenate([sweep, turbine.wind_speeds[[0, -1]]]))


def evaluate_floris(turbine: CommonTurbine, wind_speeds: np.ndarray) -> dict[str, np.ndarray]:
    """Run FLORIS with the common curves as a tabulated `power_thrust_table`."""
    n = wind_speeds.size
    config = {
        "name": "turbine performance",
        "description": "Single turbine power and thrust sweep",
        "floris_version": "v4",
        "logging": {
            "console": {"enable": False, "level": "WARNING"},
            "file": {"enable": False, "level": "WARNING"},
        },
        "solver": {"type": "turbine_grid", "turbine_grid_points": 3},
        "farm": {
            "layout_x": [0.0],
            "layout_y": [0.0],
            "turbine_type": [
                {
                    "turbine_type": turbine.name,
                    "hub_height": turbine.hub_height,
                    "rotor_diameter": turbine.rotor_diameter,
                    "TSR": 8.0,
                    "operation_model": "cosine-loss",
                    "power_thrust_table": {
                        "ref_air_density": turbine.air_density,
                        "ref_tilt": 5.0,
                        "cosine_loss_exponent_yaw": 1.88,
                        "cosine_loss_exponent_tilt": 1.88,
                        # FLORIS expects the tabulated power in kW
                        "power": turbine.power_kw.tolist(),
                        "thrust_coefficient": turbine.ct.tolist(),
                        "wind_speed": turbine.wind_speeds.tolist(),
                    },
                }
            ],
        },
        "flow_field": {
            "air_density": turbine.air_density,
            "reference_wind_height": -1,
            "turbulence_intensities": [TURBULENCE_INTENSITY],
            "wind_directions": [WIND_DIRECTION],
            "wind_shear": 0.0,
            "wind_speeds": [9.8],
            "wind_veer": 0.0,
        },
        "wake": {
            "model_strings": {
                "combination_model": "sosfs",
                "deflection_model": "none",
                "turbulence_model": "crespo_hernandez",
                "velocity_model": "jensen",
            },
            "enable_secondary_steering": False,
            "enable_yaw_added_recovery": False,
            "enable_transverse_velocities": False,
            "enable_active_wake_mixing": False,
            "wake_deflection_parameters": {"none": {}},
            "wake_velocity_parameters": {"jensen": {"we": 0.05}},
            "wake_turbulence_parameters": {
                "crespo_hernandez": {
                    "initial": 0.1,
                    "constant": 0.5,
                    "ai": 0.8,
                    "downstream": -0.32,
                }
            },
        },
    }
    fmodel = FlorisModel(config)
    fmodel.set(
        wind_speeds=wind_speeds,
        wind_directions=np.full(n, WIND_DIRECTION),
        turbulence_intensities=np.full(n, TURBULENCE_INTENSITY),
    )
    fmodel.run()
    return {
        "power_kw": fmodel.get_turbine_powers()[:, 0] / 1.0e3,
        "ct": fmodel.get_turbine_thrust_coefficients()[:, 0],
    }


def evaluate_foxes(turbine: CommonTurbine, wind_speeds: np.ndarray) -> dict[str, np.ndarray]:
    """Run FOXES with the common curves as a `PCtFromTwo` turbine type."""
    n = wind_speeds.size
    mbook = foxes.ModelBook()
    mbook.turbine_types["common_turbine"] = PCtFromTwo(
        pd.DataFrame({"ws": turbine.wind_speeds, "P": turbine.power_kw}),
        pd.DataFrame({"ws": turbine.wind_speeds, "ct": turbine.ct}),
        col_ws_P_file="ws",
        col_ws_ct_file="ws",
        col_P="P",
        col_ct="ct",
        D=turbine.rotor_diameter,
        H=turbine.hub_height,
        P_nominal=turbine.rated_power_kw,
        P_unit="kW",
    )
    farm = foxes.WindFarm()
    with quiet():
        foxes.input.farm_layout.add_from_df(
            farm,
            pd.DataFrame({"x": [0.0], "y": [0.0]}),
            col_x="x",
            col_y="y",
            turbine_models=["common_turbine"],
        )
    states_data = pd.DataFrame(
        {
            FV.WS: wind_speeds,
            FV.WD: np.full(n, WIND_DIRECTION),
            FV.TI: np.full(n, TURBULENCE_INTENSITY),
            FV.RHO: np.full(n, turbine.air_density),
        }
    )
    states_data.index.name = "state"
    states = foxes.input.states.StatesTable(
        states_data, output_vars=[FV.WS, FV.WD, FV.TI, FV.RHO]
    )
    with quiet():
        algo = foxes.algorithms.Downwind(
            farm,
            states,
            wake_models=[],
            rotor_model="grid16",
            mbook=mbook,
            verbosity=0,
        )
        results = algo.calc_farm()
    return {
        "power_kw": np.asarray(results[FV.P].values)[:, 0],
        "ct": np.asarray(results[FV.CT].values)[:, 0],
    }


def evaluate_pywake(turbine: CommonTurbine, wind_speeds: np.ndarray) -> dict[str, np.ndarray]:
    """Run PyWake with the common curves as a `PowerCtTabular` function."""
    # PyWake clamps a tabular curve to its end values outside the table unless the cut-in
    # and cut-out speeds are supplied, so they are set to the ends of the common curve.
    wind_turbine = WindTurbine(
        name=turbine.name,
        diameter=turbine.rotor_diameter,
        hub_height=turbine.hub_height,
        powerCtFunction=PowerCtTabular(
            turbine.wind_speeds,
            turbine.power_kw,
            "kW",
            turbine.ct,
            ws_cutin=turbine.cut_in,
            ws_cutout=turbine.cut_out,
        ),
    )
    wind_farm_model = NOJ(UniformSite(ti=TURBULENCE_INTENSITY), wind_turbine)
    result = wind_farm_model([0.0], [0.0], wd=[WIND_DIRECTION], ws=wind_speeds)
    return {
        "power_kw": result.Power.values.reshape(-1) / 1.0e3,
        "ct": result.CT.values.reshape(-1),
    }


def reference_curves(turbine: CommonTurbine, wind_speeds: np.ndarray) -> dict[str, np.ndarray]:
    """Linear interpolation of the common curves; zero outside the tabulated range."""
    inside = (wind_speeds >= turbine.cut_in) & (wind_speeds <= turbine.cut_out)
    return {
        "power_kw": np.where(
            inside, np.interp(wind_speeds, turbine.wind_speeds, turbine.power_kw), 0.0
        ),
        "ct": np.where(inside, np.interp(wind_speeds, turbine.wind_speeds, turbine.ct), 0.0),
    }


SOFTWARE_EVALUATORS = {
    "FLORIS": evaluate_floris,
    "FOXES": evaluate_foxes,
    "PyWake": evaluate_pywake,
}

SOFTWARE_DESCRIPTIONS = {
    "FLORIS": {
        "turbine_model": "power_thrust_table with the cosine-loss operation model",
        "inputs": (
            "Power in kW, thrust coefficient, and wind speed arrays in a "
            "power_thrust_table; yaw and tilt are zero so the cosine losses are inactive."
        ),
        "interpolation": "Linear (scipy interp1d) in wind speed.",
        "out_of_range": (
            "Power is zero outside the tabulated wind speeds. Thrust coefficient is "
            "clipped to the range [0.0001, 0.9999], so it never reaches zero."
        ),
        "implementation": (
            "Executed with FlorisModel.run(), get_turbine_powers(), and "
            "get_turbine_thrust_coefficients()."
        ),
    },
    "FOXES": {
        "turbine_model": "PCtFromTwo turbine type",
        "inputs": "Separate power (kW) and Ct tables, each with its own wind speed column.",
        "interpolation": "Linear (numpy interp) in rotor effective wind speed.",
        "out_of_range": "Power and Ct are exactly zero outside the tabulated wind speeds.",
        "implementation": (
            "Executed with the Downwind algorithm, no wake models, and the grid16 rotor "
            "model; results read from calc_farm() P and CT."
        ),
    },
    "PyWake": {
        "turbine_model": "WindTurbine with a PowerCtTabular function",
        "inputs": (
            "Wind speed, power (kW), and Ct arrays plus the cut-in and cut-out wind speeds, "
            "which are set to the first and last tabulated speeds."
        ),
        "interpolation": "Linear (numpy interp) in wind speed.",
        "out_of_range": (
            "With cut-in and cut-out set, power and Ct take their idle values (zero) "
            "outside the table. Without them PyWake would hold the end values."
        ),
        "implementation": (
            "Executed with the NOJ wind farm model on a UniformSite; with one turbine no "
            "wake is applied. Results read from the Power and CT outputs."
        ),
    },
}


def build_turbine_performance_dataset() -> dict[str, object]:
    """Build the static dataset consumed by the turbine-performance site page."""
    turbine = get_common_turbine()
    wind_speeds = get_sweep_wind_speeds(turbine)
    reference = reference_curves(turbine, wind_speeds)

    results = []
    for software, evaluate in SOFTWARE_EVALUATORS.items():
        values = evaluate(turbine, wind_speeds)
        power, ct = values["power_kw"], values["ct"]
        inside = (wind_speeds >= turbine.cut_in) & (wind_speeds <= turbine.cut_out)
        results.append(
            {
                "software": software,
                **SOFTWARE_DESCRIPTIONS[software],
                "power_kw": power.tolist(),
                "ct": ct.tolist(),
                "max_abs_power_error_kw": float(np.max(np.abs(power - reference["power_kw"]))),
                "max_abs_ct_error": float(np.max(np.abs(ct - reference["ct"]))),
                "max_abs_power_error_in_range_kw": float(
                    np.max(np.abs(power - reference["power_kw"])[inside])
                ),
                "max_abs_ct_error_in_range": float(
                    np.max(np.abs(ct - reference["ct"])[inside])
                ),
            }
        )

    return {
        "turbine": {
            "name": turbine.name,
            "rotor_diameter": turbine.rotor_diameter,
            "hub_height": turbine.hub_height,
            "air_density": turbine.air_density,
            "cut_in": turbine.cut_in,
            "cut_out": turbine.cut_out,
            "rated_power_kw": turbine.rated_power_kw,
            "curve": {
                "wind_speeds": turbine.wind_speeds.tolist(),
                "power_kw": turbine.power_kw.tolist(),
                "ct": turbine.ct.tolist(),
            },
        },
        "setup": (
            "One unwaked turbine in uniform, shear-free flow at "
            f"{turbine.air_density} kg/m³ air density, evaluated at "
            f"{wind_speeds.size} wind speeds."
        ),
        "execution": (
            "The common curves are passed to each installed software's native tabular "
            "turbine input and the turbine is simulated with that software's own solver. "
            "No software result is calculated by a wcomp replacement formula."
        ),
        "reference": (
            "Linear interpolation of the common power and Ct curves inside the tabulated "
            "range, and zero outside it."
        ),
        "wind_speeds": wind_speeds.tolist(),
        "reference_curves": {
            "power_kw": reference["power_kw"].tolist(),
            "ct": reference["ct"].tolist(),
        },
        "results": results,
    }


def _main() -> None:
    parser = argparse.ArgumentParser(description="Compare turbine power and thrust curves.")
    parser.add_argument("--output", type=Path, required=True, help="Write the site dataset as JSON.")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(build_turbine_performance_dataset(), indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    _main()
