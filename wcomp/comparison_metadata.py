"""Human-readable wake-model configuration metadata for comparison pages."""

from pathlib import Path

from windIO import load_yaml

from .analysis_settings import (
    SETTING_AVERAGING,
    SETTING_DEFICIT,
    SETTING_GRID,
    SETTING_NAMES,
    SETTINGS_RESOLVERS,
)

# Each alignment is a complete set of case files (`yaml_file` inside every case directory)
# and a full copy of the dataset under `dataset/<id>/`.
ALIGNMENTS = [
    {
        "id": "default",
        "label": "Default",
        "description": (
            "Each solver runs with its own legacy settings. Differences between the solvers "
            "therefore mix model differences with configuration differences such as how the "
            "rotor is sampled and which wind speed scales the wake deficit."
        ),
        "yaml_file": "wind_energy_system.yaml",
    },
    {
        "id": "aligned",
        "label": "Aligned",
        "description": (
            "The solver settings that can be matched across the three packages are matched: "
            "the wake deficit is scaled by the freestream speed, rotor averaging is linear, "
            "and FLORIS and PyWake sample the rotor with a nine-point cubature. The "
            "remaining differences are listed below."
        ),
        "yaml_file": "wind_energy_system_aligned.yaml",
    },
]
ALIGNMENT_IDS = tuple(alignment["id"] for alignment in ALIGNMENTS)
DEFAULT_ALIGNMENT = ALIGNMENT_IDS[0]

CASE_ROOT = Path(__file__).resolve().parent.parent / "examples" / "cases_torque2024"
DATASET_ROOT = Path(__file__).resolve().parent.parent / "dataset"
# Every case shares one analyses block per alignment; a test enforces it.
REFERENCE_CASE_DIR = CASE_ROOT / "one_turbine" / "jensen"


def load_alignment_analyses(alignment_id: str) -> dict:
    """The `attributes.analyses` block of the reference case for an alignment."""
    case_file = REFERENCE_CASE_DIR / get_alignment(alignment_id)["yaml_file"]
    return load_yaml(case_file)["attributes"]["analyses"]


def get_alignment(alignment_id: str) -> dict:
    for alignment in ALIGNMENTS:
        if alignment["id"] == alignment_id:
            return alignment
    raise ValueError(f"Unknown alignment '{alignment_id}'. Choose from: {', '.join(ALIGNMENT_IDS)}")


def resolve_output_paths(alignment: str, output: Path | None, filename: str) -> dict[str, Path]:
    """Map each alignment a generator CLI was asked for to the file it writes."""
    alignment_ids = ALIGNMENT_IDS if alignment == "all" else (get_alignment(alignment)["id"],)
    if output is not None:
        if len(alignment_ids) != 1:
            raise ValueError("--output writes one file; choose a single --alignment.")
        return {alignment_ids[0]: output}
    return {alignment_id: DATASET_ROOT / alignment_id / filename for alignment_id in alignment_ids}


def build_alignment_settings(analyses: dict, software_names: list[str]) -> dict:
    """Settings table and unapplied-setting notes for one alignment's `analyses` block."""
    resolved = {name: SETTINGS_RESOLVERS[name](analyses) for name in software_names}
    return {
        "settings": [
            {"name": setting, **{name: resolved[name].summary[setting] for name in software_names}}
            for setting in SETTING_NAMES
        ],
        "residual_differences": [
            {"software": name, "note": note}
            for name in software_names
            for note in resolved[name].notes
        ],
    }


def build_software_note(software: str, analyses: dict) -> str:
    """Describe a solver's configuration from the settings actually applied."""
    summary = SETTINGS_RESOLVERS[software](analyses).summary
    deficit = summary[SETTING_DEFICIT].lower()
    grid = summary[SETTING_GRID]
    averaging = summary[SETTING_AVERAGING]
    if software == "FLORIS":
        return (
            "Uses sum-of-squares freestream deficit superposition (sosfs), the "
            f"{grid} rotor grid with {averaging} averaging, and Crespo-Hernandez "
            "wake-added turbulence. Secondary steering, yaw-added recovery, transverse "
            "velocities, and active wake mixing are disabled."
        )
    if software == "FOXES":
        return (
            f"Uses Betz induction, quadratic wind-speed superposition with a {deficit} "
            f"deficit reference, {grid} rotor sampling, rotor-point partial wakes, and the "
            "rotor_wd wake frame. No separate wake-added turbulence model is configured."
        )
    return (
        "Uses PropagateDownwind with squared-sum superposition, "
        f"{grid} rotor averaging, {deficit} deficit reference, and ct2a_mom1d induction. "
        "No separate wake-added turbulence model is configured."
    )

MODEL_NOTES = {
    "jensen": {
        "PyWake": (
            "Uses the lower-level NOJDeficit class rather than PyWake's Jensen_1983 "
            "literature preset."
        ),
    },
    "bastankhah2014": {
        "PyWake": (
            "Uses the lower-level BastankhahGaussianDeficit class rather than PyWake's "
            "Bastankhah_PorteAgel_2014 literature preset."
        ),
    },
    "bastankhah2016": {
        "FOXES": (
            "The ka and kb inputs configure a separate kTI turbine model; the wake model "
            "receives k=None so expansion is supplied by that turbine model."
        ),
    },
    "bastankhah2016_deflection": {
        "FLORIS": (
            "The gauss velocity and deflection models each receive their own copy of the "
            "four input coefficients."
        ),
        "FOXES": (
            "Uses FOXES' Bastankhah2016Deflection model with Betz induction. The "
            "duplicated windIO deflection parameters are not read; the velocity-block "
            "parameters govern the calculation."
        ),
    },
    "jimenez": {
        "FLORIS": (
            "Converts the windIO coefficient with kd = beta / 2 because FLORIS uses "
            "1 + 2*kd*x/D where the other implementations use 1 + beta*x/D."
        ),
        "FOXES": (
            "Uses JimenezDeflection with rotate=False, translating the wake path without "
            "rotating the wake cross-section."
        ),
    },
    "turbopark": {
        "PyWake": (
            "Uses the lower-level TurboGaussianDeficit class rather than PyWake's "
            "Nygaard_2022 literature preset."
        ),
    },
}

DEFLECTION_CASE_NOTE = (
    "This is a coupled comparison: yaw-dependent thrust, velocity deficit, deflection, "
    "rotor averaging, and wake superposition can all contribute to differences. It does "
    "not isolate the deflection equation."
)


def _implementation_model(software: str, category: str, model: dict) -> dict:
    name = model["name"]
    parameters = model.get("parameters") or {}

    if software == "FLORIS":
        model_names = {
            "jensen": "jensen",
            "bastankhah2016": "gauss",
            "bastankhah2016_deflection": "gauss",
            "jimenez": "jimenez",
            "turbopark": "turboparkgauss",
        }
        parameter_names = {
            "jensen": {"alpha": "we"},
            "bastankhah2016": {key: key for key in ("alpha", "beta", "ka", "kb")},
            "bastankhah2016_deflection": {
                key: key for key in ("alpha", "beta", "ka", "kb")
            },
            "jimenez": {"beta": "kd"},
            "turbopark": {"A": "A"},
        }
    elif software == "FOXES":
        model_names = {
            "jensen": "JensenWake",
            "bastankhah2014": "Bastankhah2014",
            "bastankhah2016": "Bastankhah2016",
            "bastankhah2016_deflection": "Bastankhah2016Deflection",
            "jimenez": "JimenezDeflection",
            "turbopark": "TurbOParkWake",
        }
        parameter_names = {
            "jensen": {"alpha": "k"},
            "bastankhah2014": {"k_star": "k"},
            "bastankhah2016": {
                "alpha": "alpha",
                "beta": "beta",
                "ka": "kTI",
                "kb": "kb",
            },
            "bastankhah2016_deflection": {},
            "jimenez": {"beta": "beta"},
            "turbopark": {"A": "ka"},
        }
    elif software == "PyWake":
        model_names = {
            "jensen": "NOJDeficit",
            "bastankhah2014": "BastankhahGaussianDeficit",
            "jimenez": "JimenezWakeDeflection",
            "turbopark": "TurboGaussianDeficit",
        }
        parameter_names = {
            "jensen": {"alpha": "k"},
            "bastankhah2014": {"k_star": "k"},
            "jimenez": {"beta": "beta"},
            "turbopark": {"A": "A"},
        }
    else:
        raise ValueError(f"Unknown wake-model software '{software}'")

    mapped_parameters = {
        implementation_name: parameters[input_name]
        for input_name, implementation_name in parameter_names[name].items()
    }
    if software == "FLORIS" and name == "jimenez":
        mapped_parameters["kd"] /= 2.0
    if software == "FOXES" and category == "velocity":
        mapped_parameters["induction"] = "Betz"
    if software == "FOXES" and name == "bastankhah2016":
        mapped_parameters["k"] = "from kTI turbine model"
    if software == "FOXES" and name == "jimenez":
        mapped_parameters["rotate"] = False

    return {
        "category": category,
        "name": model_names[name],
        "parameters": mapped_parameters,
    }


def build_model_configuration(analyses: dict, software_names: list[str]) -> dict:
    """Build display metadata from a case's windIO `attributes.analyses` block."""
    wake_model = analyses["wake_model"]
    input_models = [
        {
            "category": category,
            "name": model["name"],
            "parameters": model.get("parameters") or {},
        }
        for category in ("velocity", "deflection")
        if (model := wake_model.get(category) or {}).get("name")
    ]

    implementations = []
    for software in software_names:
        implementation_models = [
            _implementation_model(software, model["category"], model)
            for model in input_models
        ]
        notes = [build_software_note(software, analyses)]
        notes.extend(SETTINGS_RESOLVERS[software](analyses).notes)
        notes.extend(
            MODEL_NOTES.get(model["name"], {}).get(software)
            for model in input_models
            if MODEL_NOTES.get(model["name"], {}).get(software)
        )
        implementations.append(
            {
                "software": software,
                "models": implementation_models,
                "notes": notes,
            }
        )

    notes = [DEFLECTION_CASE_NOTE] if any(
        model["category"] == "deflection" for model in input_models
    ) else []
    return {
        "inputs": input_models,
        "implementations": implementations,
        "notes": notes,
    }
