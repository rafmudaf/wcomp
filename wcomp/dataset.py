"""
Generates the on-disk, framework-agnostic dataset of wake-model comparison
results consumed by the frontend site (see `site/`). This module only
depends on `wcomp` and the integrated solvers -- its output is plain JSON
under `dataset/` at the repo root, decoupled from how the frontend is built.

Run with (inside the `wcomp` conda environment):
    python -m wcomp.dataset

To regenerate only a subset of the dataset:
    python -m wcomp.dataset floris
    python -m wcomp.dataset jensen
    python -m wcomp.dataset floris foxes turbopark
"""

import argparse
import json
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
from windIO import load_yaml

from . import WCompFloris, WCompFoxes, WCompPyWake, __version__
from .cache import quiet
from .comparison_metadata import build_model_configuration
from .metrics import plane_metrics, profile_metrics

REPO_ROOT = Path(__file__).resolve().parent.parent
CASE_ROOT = REPO_ROOT / "examples" / "cases_torque2024"
DATASET_ROOT = REPO_ROOT / "dataset"

# Scenario layouts, in rotor diameters downstream of the origin. The four-turbine
# scenario matches the farm used by the previous Jupyter Book dashboard. Yaw is not
# listed here since it varies per wake-model case (only deflection cases yaw any
# turbines) -- it's read directly from each case's own yaml in compute_case().
TURBINE_LOCATIONS_D = {
    "one_turbine": [0],
    "four_turbine": [0, 5, 10, 15],
}

# Maps each wake-model case (a subdirectory of examples/cases_torque2024/<scenario>/)
# to the software packages that implement it. Every interface supports both solving
# and horizontal-contour plotting, so the same list drives both. Each case's
# velocity/deflection *categories* aren't listed here since they're read directly
# from the case's own yaml in compute_case() -- every case configures a velocity
# model, and some also configure a deflection model on top of it.
WAKE_MODEL_CASES = {
    "jensen": {
        "software": [WCompFloris, WCompFoxes, WCompPyWake],
    },
    "bastankhah2014": {
        "software": [WCompFoxes, WCompPyWake],
    },
    "bastankhah2016": {
        "software": [WCompFloris, WCompFoxes],
    },
    "bastankhah2016_deflection": {
        "software": [WCompFloris, WCompFoxes],
    },
    "jimenez": {
        "software": [WCompFloris, WCompFoxes, WCompPyWake],
    },
    "turbopark": {
        "software": [WCompFloris, WCompFoxes, WCompPyWake],
    },
}

SCENARIOS = ["one_turbine", "four_turbine"]

SOFTWARE_FILTERS = {
    "floris": WCompFloris,
    "foxes": WCompFoxes,
    "pywake": WCompPyWake,
}

VALID_SELECTORS = sorted({*SOFTWARE_FILTERS, *WAKE_MODEL_CASES})

# Streamwise location (in rotor diameters from the origin) of the cross-section
# contour plane, in the y-z plane, per scenario. 20D for four_turbine sits a few
# diameters past the last turbine where the combined farm wake is developed; the
# same distance on one_turbine is far enough downstream that the single wake has
# mostly recovered to a near-uniform profile, so it uses a closer 5D instead.
XSECTION_CONTOUR_LOCATION_D = {
    "one_turbine": 5,
    "four_turbine": 20,
}

# The full implementation matrix, including wake models that don't (yet) have an
# example case wired up above. This is the source of truth for the frontend's
# implementation-matrix page, replacing the hand-maintained markdown tables that
# used to live in docs/dashboard.md.
MODEL_REGISTRY = [
    {"name": "Jensen 1983", "category": "velocity", "software": ["FLORIS", "FOXES", "PyWake"], "case": "jensen"},
    {"name": "Larsen 2009", "category": "velocity", "software": ["PyWake"], "case": None},
    {"name": "Bastankhah / Porte Agel 2014", "category": "velocity", "software": ["FOXES", "PyWake"], "case": "bastankhah2014"},
    {"name": "Bastankhah / Porte Agel 2016", "category": "velocity", "software": ["FLORIS", "FOXES"], "case": "bastankhah2016"},
    {"name": "Niayifar / Porte-Agel 2016", "category": "velocity", "software": ["PyWake"], "case": None},
    {"name": "IEA Task 37 Bastankhah 2018", "category": "velocity", "software": ["PyWake"], "case": None},
    {"name": "Carbajo Fuertes / Markfort / Porte-Agel 2018", "category": "velocity", "software": ["PyWake"], "case": None},
    {"name": "Blondel / Cathelain 2020", "category": "velocity", "software": ["PyWake"], "case": None},
    {"name": "Zong / Porte-Agel 2020", "category": "velocity", "software": ["PyWake"], "case": None},
    {"name": "Cumulative Curl 2022", "category": "velocity", "software": ["FLORIS"], "case": None},
    {"name": "TurbOPark (Nygaard 2022)", "category": "velocity", "software": ["FLORIS", "FOXES", "PyWake"], "case": "turbopark"},
    {"name": "Empirical Gauss 2023", "category": "velocity", "software": ["FLORIS"], "case": None},
    {"name": "Jimenez 2010", "category": "deflection", "software": ["FLORIS", "FOXES", "PyWake"], "case": "jimenez"},
    {"name": "Bastankhah / Porte Agel 2016 (deflection)", "category": "deflection", "software": ["FLORIS", "FOXES"], "case": "bastankhah2016_deflection"},
    {"name": "Larsen et al 2020", "category": "deflection", "software": ["PyWake"], "case": None},
    {"name": "Empirical Gauss 2023 (deflection)", "category": "deflection", "software": ["FLORIS"], "case": None},
]


def _write_json(path: Path, data, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        if compact:
            json.dump(data, f, separators=(",", ":"))
        else:
            json.dump(data, f, indent=2)


def _software_versions() -> dict:
    import floris
    import foxes

    try:
        import py_wake
        pywake_version = getattr(py_wake, "__version__", "unknown")
    except Exception:
        pywake_version = "unknown"

    return {
        "FLORIS": floris.__version__,
        "FOXES": foxes.__version__,
        "PyWake": pywake_version,
    }


def compute_case(scenario: str, wake_model: str) -> dict:
    """
    Run every software package integrated for a given (scenario, wake_model) pair
    and extract the plain data needed for the frontend comparison plots and metrics.
    """
    spec = WAKE_MODEL_CASES[wake_model]
    case_file = CASE_ROOT / scenario / wake_model / "wind_energy_system.yaml"
    turbine_locations_d = TURBINE_LOCATIONS_D[scenario]

    with quiet():
        instances = {cls: cls(case_file) for cls in spec["software"]}

        rotor_d = next(iter(instances.values())).rotor_diameter
        hub_height = next(iter(instances.values())).hub_height
        case_yaml = load_yaml(case_file)
        wind_speed = case_yaml["site"]["energy_resource"]["wind_resource"]["wind_speed"][0]
        # Yaw varies per wake-model case (only the deflection cases apply nonzero yaw),
        # so it's read from the case file rather than assumed from the scenario.
        yaw_angles = case_yaml["attributes"]["analyses"]["yaw_angles"]
        # Every case configures a velocity (deficit) model; only some also configure a
        # deflection model on top of it, so "velocity" and "deflection" are additive
        # tags rather than mutually exclusive categories. The case yaml always has a
        # `deflection` key, but its `name` is null/empty when no deflection is applied.
        case_wake_model = case_yaml["attributes"]["analyses"]["wake_model"]
        categories = [
            category for category in ("velocity", "deflection")
            if (case_wake_model.get(category) or {}).get("name")
        ]

        first_turbine_d = turbine_locations_d[0]
        last_turbine_d = turbine_locations_d[-1]
        xmin, xmax = -1 * rotor_d, (last_turbine_d + 20) * rotor_d
        ymin, ymax = -2 * rotor_d, 2 * rotor_d

        if scenario == "four_turbine":
            # 4D past the first turbine (before its wake reaches the second turbine),
            # then 1D/5D/10D past the last turbine where the combined farm wake has
            # had a chance to develop.
            xsection_locations = {
                "4D_past_first_turbine": first_turbine_d + 4,
                "1D_past_last_turbine": last_turbine_d + 1,
                "5D_past_last_turbine": last_turbine_d + 5,
                "10D_past_last_turbine": last_turbine_d + 10,
            }
        else:
            xsection_locations = {
                "1D_downstream": last_turbine_d + 1,
                "5D_downstream": last_turbine_d + 5,
                "10D_downstream": last_turbine_d + 10,
            }

        streamwise = {}
        xsections = {label: {} for label in xsection_locations}
        for cls, instance in instances.items():
            streamwise[cls.LEGEND] = instance.streamwise_profile_plot(
                wind_direction=270, y_coordinate=0.0, xmin=xmin, xmax=xmax
            )
            for label, location_d in xsection_locations.items():
                xsections[label][cls.LEGEND] = instance.xsection_profile_plot(
                    wind_direction=270,
                    x_coordinate=location_d * rotor_d,
                    ymin=ymin,
                    ymax=ymax,
                )

        planes = {
            cls.LEGEND: instances[cls].horizontal_contour(wind_direction=270)
            for cls in spec["software"]
        }
        vertical_planes = {
            cls.LEGEND: instances[cls].vertical_contour(wind_direction=270)
            for cls in spec["software"]
        }
        xsection_contour_location_d = XSECTION_CONTOUR_LOCATION_D[scenario]
        xsection_contour_planes = {
            cls.LEGEND: instances[cls].xsection_contour(
                wind_direction=270, x_coordinate=xsection_contour_location_d * rotor_d
            )
            for cls in spec["software"]
        }

    plt.close("all")  # discard the matplotlib figures created as a side effect above
    return {
        "rotor_diameter": rotor_d,
        "hub_height": hub_height,
        "wind_speed": wind_speed,
        "yaw_angles": yaw_angles,
        "categories": categories,
        "model_configuration": build_model_configuration(
            case_wake_model, [cls.LEGEND for cls in spec["software"]]
        ),
        "xsection_locations_d": xsection_locations,
        "streamwise": streamwise,
        "xsections": xsections,
        "planes": planes,
        "vertical_planes": vertical_planes,
        "xsection_contour_planes": xsection_contour_planes,
        "xsection_contour_location_d": xsection_contour_location_d,
    }


def write_case(scenario: str, wake_model: str, result: dict, software_versions: dict) -> str:
    case_id = f"{scenario}__{wake_model}"
    case_dir = DATASET_ROOT / "cases" / case_id
    software_names = list(result["streamwise"].keys())

    _write_json(case_dir / "case.json", {
        "scenario": scenario,
        "wake_model": wake_model,
        "categories": result["categories"],
        "rotor_diameter": result["rotor_diameter"],
        "hub_height": result["hub_height"],
        "wind_speed": result["wind_speed"],
        "turbine_locations_d": TURBINE_LOCATIONS_D[scenario],
        "turbine_yaw_deg": result["yaw_angles"],
        "software": software_names,
        "model_configuration": result["model_configuration"],
        "xsection_labels": list(result["xsections"].keys()),
        "xsection_locations_d": result["xsection_locations_d"],
        "has_contour": bool(result["planes"]),
        "xsection_contour_location_d": result["xsection_contour_location_d"],
    })

    for name, profile in result["streamwise"].items():
        _write_json(case_dir / "software" / name / "streamwise.json", profile.to_dict(), compact=True)
    for label, by_software in result["xsections"].items():
        for name, profile in by_software.items():
            _write_json(case_dir / "software" / name / "xsections" / f"{label}.json", profile.to_dict(), compact=True)
    for name, plane in result["planes"].items():
        _write_json(case_dir / "software" / name / "contour.json", plane.to_dict(), compact=True)
    for name, plane in result["vertical_planes"].items():
        _write_json(case_dir / "software" / name / "contour_vertical.json", plane.to_dict(), compact=True)
    for name, plane in result["xsection_contour_planes"].items():
        _write_json(case_dir / "software" / name / "contour_xsection.json", plane.to_dict(), compact=True)
    for name in software_names:
        _write_json(case_dir / "software" / name / "meta.json", {
            "version": software_versions.get(name, "unknown"),
        })

    metrics = []
    for a, b in combinations(software_names, 2):
        metrics.append({
            "pair": [a, b],
            "target": "streamwise",
            **profile_metrics(result["streamwise"][a], result["streamwise"][b]),
        })
    for label, by_software in result["xsections"].items():
        for a, b in combinations(by_software.keys(), 2):
            metrics.append({
                "pair": [a, b],
                "target": f"xsection:{label}",
                **profile_metrics(by_software[a], by_software[b]),
            })
    for a, b in combinations(result["planes"].keys(), 2):
        metrics.append({
            "pair": [a, b],
            "target": "contour",
            **plane_metrics(result["planes"][a], result["planes"][b]),
        })
    for a, b in combinations(result["vertical_planes"].keys(), 2):
        metrics.append({
            "pair": [a, b],
            "target": "contour_vertical",
            **plane_metrics(result["vertical_planes"][a], result["vertical_planes"][b]),
        })
    for a, b in combinations(result["xsection_contour_planes"].keys(), 2):
        metrics.append({
            "pair": [a, b],
            "target": "contour_xsection",
            **plane_metrics(result["xsection_contour_planes"][a], result["xsection_contour_planes"][b]),
        })
    _write_json(case_dir / "metrics.json", metrics)

    return case_id


def _case_matches_selectors(wake_model: str, selectors: set[str]) -> bool:
    if not selectors:
        return True

    wake_model_selectors = selectors.intersection(WAKE_MODEL_CASES)
    software_selectors = selectors.intersection(SOFTWARE_FILTERS)

    if wake_model_selectors and wake_model not in wake_model_selectors:
        return False

    if software_selectors and not any(
        cls.LEGEND.lower() in software_selectors for cls in WAKE_MODEL_CASES[wake_model]["software"]
    ):
        return False

    if wake_model_selectors or software_selectors:
        return True

    return False


def generate(selectors: set[str] | None = None) -> None:
    software_versions = _software_versions()
    case_ids = []
    for scenario in SCENARIOS:
        for selected_wake_model in WAKE_MODEL_CASES:
            if selectors is not None and not _case_matches_selectors(selected_wake_model, selectors):
                continue
            print(f"Computing {scenario}/{selected_wake_model}...")
            result = compute_case(scenario, selected_wake_model)
            case_ids.append(write_case(scenario, selected_wake_model, result, software_versions))

    if not case_ids:
        raise ValueError("No cases matched the requested selectors.")

    manifest_cases = case_ids
    if selectors is not None:
        manifest_path = DATASET_ROOT / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                existing_manifest = json.load(f)
            existing_cases = existing_manifest.get("cases", [])
            manifest_cases = list(dict.fromkeys([*existing_cases, *case_ids]))

    _write_json(DATASET_ROOT / "models.json", MODEL_REGISTRY)
    _write_json(DATASET_ROOT / "manifest.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "wcomp_version": __version__,
        "software_versions": software_versions,
        "cases": manifest_cases,
    })
    print(f"Wrote {len(case_ids)} case(s) to {DATASET_ROOT}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate the wcomp dataset.")
    parser.add_argument(
        "selectors",
        nargs="*",
        metavar="selector",
        help=(
            "Optional software and/or wake-model selectors, e.g. floris jensen turbopark. "
            "Multiple software selectors match any listed software; multiple wake-model "
            "selectors match any listed wake model; mixing the two narrows to their intersection. "
            "When downselecting, existing manifest cases are preserved and regenerated cases are merged in."
        ),
    )
    args = parser.parse_args(argv)

    selectors = {selector.lower() for selector in args.selectors}
    invalid = sorted(selectors.difference(VALID_SELECTORS))
    if invalid:
        parser.error(
            f"unrecognized selector(s): {', '.join(invalid)}. "
            f"Choose from: {', '.join(VALID_SELECTORS)}"
        )

    generate(selectors=selectors or None)


if __name__ == "__main__":
    main()
