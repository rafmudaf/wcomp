"""Resolve windIO `attributes.analyses` settings into each solver's native settings.

Keys that a case file omits fall back to each solver's legacy behaviour (the "default"
configuration). A setting a solver cannot honour is reported in `notes`, never ignored.
"""

import math
from dataclasses import dataclass, field

SETTING_DEFICIT = "Deficit reference wind speed"
SETTING_GRID = "Rotor grid"
SETTING_AVERAGING = "Power / thrust averaging"
SETTING_NAMES = (SETTING_DEFICIT, SETTING_GRID, SETTING_AVERAGING)

_EXPONENT_NAMES = {1: "linear", 2: "quadratic", 3: "cubic"}

# Each key is the grid type; values are the (power, thrust) averaging FLORIS applies when
# the input file does not name a method.
FLORIS_DEFAULT_METHODS = {
    "turbine_grid": ("cubic-mean", "cubic-mean"),
    "turbine_cubature_grid": ("cubic-mean", "linear-cubature"),
}
PYWAKE_CGI_POINTS = (4, 7, 9, 21)


@dataclass(frozen=True)
class SolverSettings:
    """A solver's resolved configuration.

    `values` is what the adapter applies, `summary` maps each name in `SETTING_NAMES`
    to display text, and `notes` lists requested settings the solver cannot honour.
    """

    values: dict
    summary: dict[str, str]
    notes: list[str] = field(default_factory=list)


def _rotor_averaging(analyses: dict) -> dict:
    return analyses.get("rotor_averaging") or {}


def _deficit_reference(analyses: dict) -> str | None:
    return (analyses.get("superposition") or {}).get("deficit_reference_wind_speed")


def _check_superposition(analyses: dict, software: str) -> None:
    method = (analyses.get("superposition") or {}).get("ws_superposition")
    if method not in (None, "Squared"):
        raise ValueError(f"{software} is configured for Squared superposition, got '{method}'.")


def _exponent(rotor_averaging: dict, key: str) -> int | None:
    value = rotor_averaging.get(key)
    if value is None:
        return None
    if value not in _EXPONENT_NAMES:
        raise ValueError(f"{key} must be 1, 2 or 3, got {value!r}.")
    return int(value)


def _grid_description(rotor_averaging: dict) -> str:
    grid = rotor_averaging.get("grid")
    if grid == "cubature":
        return f"cubature with {rotor_averaging.get('n_points')} points"
    if grid == "square":
        return f"{rotor_averaging.get('n_x_grid_points')} x {rotor_averaging.get('n_y_grid_points')} square"
    return str(grid)


def _unapplied_exponents(rotor_averaging: dict, software: str) -> list[str]:
    notes = []
    for key in ("wind_speed_exponent_for_power", "wind_speed_exponent_for_ct"):
        exponent = _exponent(rotor_averaging, key)
        if exponent not in (None, 1):
            notes.append(f"{software} averages linearly; {key}={exponent} is not applied.")
    return notes


def floris_settings(analyses: dict) -> SolverSettings:
    _check_superposition(analyses, "FLORIS")
    if _deficit_reference(analyses) == "local":
        raise ValueError(
            "FLORIS' sosfs superposition scales deficits by the freestream speed; "
            "deficit_reference_wind_speed='local' cannot be honoured."
        )
    rotor_averaging = _rotor_averaging(analyses)
    grid = rotor_averaging.get("grid")

    solver = {"type": "turbine_grid", "turbine_grid_points": 3}
    if grid == "cubature":
        n_points = rotor_averaging.get("n_points")
        if n_points is None:
            raise ValueError("rotor_averaging.n_points is required for the cubature grid.")
        points_per_axis = math.isqrt(n_points)
        if points_per_axis**2 != n_points:
            raise ValueError(f"FLORIS needs a perfect-square n_points, got {n_points}.")
        solver = {"type": "turbine_cubature_grid", "turbine_grid_points": points_per_axis}
    elif grid == "square":
        n_x = rotor_averaging.get("n_x_grid_points")
        n_y = rotor_averaging.get("n_y_grid_points")
        if n_x is None or n_x != n_y:
            raise ValueError(
                f"FLORIS needs equal n_x_grid_points and n_y_grid_points, got {n_x} and {n_y}."
            )
        solver["turbine_grid_points"] = n_x
    elif grid == "center":
        solver["turbine_grid_points"] = 1

    kind = "cubature" if solver["type"] == "turbine_cubature_grid" else "mean"
    methods = dict(
        zip(
            ("power_average_method", "thrust_average_method"),
            FLORIS_DEFAULT_METHODS[solver["type"]],
        )
    )
    for key, exponent_key in (
        ("power_average_method", "wind_speed_exponent_for_power"),
        ("thrust_average_method", "wind_speed_exponent_for_ct"),
    ):
        exponent = _exponent(rotor_averaging, exponent_key)
        if exponent is not None:
            methods[key] = f"{_EXPONENT_NAMES[exponent]}-{kind}"
            solver[key] = methods[key]

    n = solver["turbine_grid_points"]
    if solver["type"] == "turbine_cubature_grid":
        grid_text = f"TurbineCubatureGrid, {n * n} points"
    else:
        grid_text = f"TurbineGrid, {n} x {n} square"
    return SolverSettings(
        values={"solver": solver},
        summary={
            SETTING_DEFICIT: "Freestream (sosfs)",
            SETTING_GRID: grid_text,
            SETTING_AVERAGING: (
                f"power {methods['power_average_method']}, "
                f"thrust {methods['thrust_average_method']}"
            ),
        },
    )


def foxes_settings(analyses: dict) -> SolverSettings:
    _check_superposition(analyses, "FOXES")
    rotor_averaging = _rotor_averaging(analyses)
    freestream = _deficit_reference(analyses) == "freestream"

    notes = []
    grid = rotor_averaging.get("grid")
    is_grid16 = (
        grid == "square"
        and rotor_averaging.get("n_x_grid_points") == 4
        and rotor_averaging.get("n_y_grid_points") == 4
    )
    if grid is not None and not is_grid16:
        notes.append(
            f"FOXES keeps its grid16 rotor model; the requested {_grid_description(rotor_averaging)} "
            "rotor grid is not applied."
        )
    notes.extend(_unapplied_exponents(rotor_averaging, "FOXES"))

    return SolverSettings(
        values={
            "superposition": "ws_quadratic_amb_target" if freestream else "ws_quadratic",
            "rotor_model": "grid16",
        },
        summary={
            SETTING_DEFICIT: (
                "Freestream (ws_quadratic_amb_target)" if freestream else "Local (ws_quadratic)"
            ),
            SETTING_GRID: "grid16, 4 x 4 cell centers",
            SETTING_AVERAGING: "linear",
        },
        notes=notes,
    )


def pywake_settings(analyses: dict) -> SolverSettings:
    _check_superposition(analyses, "PyWake")
    rotor_averaging = _rotor_averaging(analyses)
    effective_ws = _deficit_reference(analyses) != "freestream"

    grid = rotor_averaging.get("grid")
    if grid is None:
        rotor, grid_text = ("GridRotorAvg", None), "GridRotorAvg, 4 points"
    elif grid == "center":
        rotor, grid_text = ("RotorCenter", None), "RotorCenter, 1 point"
    elif grid == "cubature":
        n_points = rotor_averaging.get("n_points")
        if n_points not in PYWAKE_CGI_POINTS:
            raise ValueError(
                f"PyWake's CGIRotorAvg supports n_points in {PYWAKE_CGI_POINTS}, got {n_points}."
            )
        rotor, grid_text = ("CGIRotorAvg", n_points), f"CGIRotorAvg, {n_points} points"
    elif rotor_averaging.get("n_x_grid_points") == 2 == rotor_averaging.get("n_y_grid_points"):
        rotor, grid_text = ("GridRotorAvg", None), "GridRotorAvg, 4 points"
    else:
        raise ValueError(
            f"PyWake's GridRotorAvg is a 2 x 2 grid; cannot honour {_grid_description(rotor_averaging)}."
        )

    return SolverSettings(
        values={"use_effective_ws": effective_ws, "rotor": rotor},
        summary={
            SETTING_DEFICIT: (
                "Local effective (use_effective_ws=True)"
                if effective_ws
                else "Freestream (use_effective_ws=False)"
            ),
            SETTING_GRID: grid_text,
            SETTING_AVERAGING: "linear",
        },
        notes=_unapplied_exponents(rotor_averaging, "PyWake"),
    )


SETTINGS_RESOLVERS = {
    "FLORIS": floris_settings,
    "FOXES": foxes_settings,
    "PyWake": pywake_settings,
}
