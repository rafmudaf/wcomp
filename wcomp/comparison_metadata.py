"""Human-readable wake-model configuration metadata for comparison pages."""

SOFTWARE_NOTES = {
    "FLORIS": (
        "Uses sum-of-squares freestream deficit superposition (sosfs), a nine-point "
        "turbine-grid solver, and Crespo-Hernandez wake-added turbulence. Secondary "
        "steering, yaw-added recovery, transverse velocities, and active wake mixing "
        "are disabled."
    ),
    "FOXES": (
        "Uses Betz induction, quadratic wind-speed superposition, grid16 rotor sampling, "
        "rotor-point partial wakes, and the rotor_wd wake frame. No separate wake-added "
        "turbulence model is configured."
    ),
    "PyWake": (
        "Uses PropagateDownwind with squared-sum superposition, GridRotorAvg rotor "
        "averaging, effective local wind speed, and ct2a_mom1d induction. No separate "
        "wake-added turbulence model is configured."
    ),
}

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


def build_model_configuration(wake_model: dict, software_names: list[str]) -> dict:
    """Build display metadata from a case's windIO wake-model block."""
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
        notes = [SOFTWARE_NOTES[software]]
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
