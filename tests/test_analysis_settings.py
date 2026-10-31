import copy

import pytest
from windIO import load_yaml

from wcomp.analysis_settings import floris_settings, foxes_settings, pywake_settings
from wcomp.comparison_metadata import (
    ALIGNMENT_IDS,
    ALIGNMENTS,
    CASE_ROOT,
    build_alignment_settings,
    build_model_configuration,
    load_alignment_analyses,
)

LEGACY = {
    "yaw_angles": [0.0],
    "wake_model": {
        "velocity": {"name": "jensen", "parameters": {"alpha": 0.1}},
        "deflection": {"name": None},
    },
}


def _with(**blocks):
    analyses = copy.deepcopy(LEGACY)
    analyses.update(blocks)
    return analyses


ALIGNED = _with(
    superposition={"ws_superposition": "Squared", "deficit_reference_wind_speed": "freestream"},
    rotor_averaging={
        "grid": "cubature",
        "n_points": 9,
        "wind_speed_exponent_for_power": 1,
        "wind_speed_exponent_for_ct": 1,
    },
)


def test_omitted_keys_give_each_solvers_legacy_settings():
    """Check a case file without the new keys resolves to the unmodified solver settings.

    Asserts FLORIS keeps its 3 x 3 turbine grid with no averaging keys, FOXES uses
    ws_quadratic with grid16, and PyWake uses the effective wind speed with GridRotorAvg.

    Question answered: does leaving the keys out reproduce the pre-alignment behaviour?
    """
    assert floris_settings(LEGACY).values["solver"] == {
        "type": "turbine_grid",
        "turbine_grid_points": 3,
    }
    assert foxes_settings(LEGACY).values == {"superposition": "ws_quadratic", "rotor_model": "grid16"}
    assert pywake_settings(LEGACY).values == {"use_effective_ws": True, "rotor": ("GridRotorAvg", None)}
    for resolve in (floris_settings, foxes_settings, pywake_settings):
        assert resolve(LEGACY).notes == []


def test_aligned_keys_map_to_each_solvers_native_settings():
    """Check the aligned block maps to FLORIS cubature, FOXES freestream and PyWake CGI.

    Question answered: do the windIO keys translate to the native solver settings the
    alignment plan lists?
    """
    assert floris_settings(ALIGNED).values["solver"] == {
        "type": "turbine_cubature_grid",
        "turbine_grid_points": 3,
        "power_average_method": "linear-cubature",
        "thrust_average_method": "linear-cubature",
    }
    assert foxes_settings(ALIGNED).values["superposition"] == "ws_quadratic_amb_target"
    assert pywake_settings(ALIGNED).values == {
        "use_effective_ws": False,
        "rotor": ("CGIRotorAvg", 9),
    }


def test_foxes_reports_the_nine_point_grid_it_cannot_honour():
    """Check FOXES notes the requested cubature grid instead of silently ignoring it.

    Question answered: is the residual FOXES difference reported to the site?
    """
    (note,) = foxes_settings(ALIGNED).notes
    assert "grid16" in note and "cubature with 9 points" in note
    assert pywake_settings(ALIGNED).notes == []


def test_exponents_select_the_floris_averaging_method():
    """Check exponents 1, 2 and 3 select linear, quadratic and cubic averaging.

    Question answered: does wind_speed_exponent_* map onto FLORIS' method names for
    both grid kinds, and are other exponents rejected?
    """
    square = _with(
        rotor_averaging={
            "grid": "square",
            "n_x_grid_points": 3,
            "n_y_grid_points": 3,
            "wind_speed_exponent_for_power": 2,
            "wind_speed_exponent_for_ct": 3,
        }
    )
    solver = floris_settings(square).values["solver"]
    assert solver["power_average_method"] == "quadratic-mean"
    assert solver["thrust_average_method"] == "cubic-mean"

    with pytest.raises(ValueError, match="must be 1, 2 or 3"):
        floris_settings(_with(rotor_averaging={"wind_speed_exponent_for_power": 4}))

    notes = foxes_settings(square).notes
    assert any("wind_speed_exponent_for_power=2" in note for note in notes)


def test_settings_a_solver_cannot_honour_raise():
    """Check unsupported requests fail loudly.

    Question answered: do FLORIS and PyWake refuse settings they cannot apply rather
    than running a different configuration?
    """
    with pytest.raises(ValueError, match="local"):
        floris_settings(_with(superposition={"deficit_reference_wind_speed": "local"}))
    with pytest.raises(ValueError, match="perfect-square"):
        floris_settings(_with(rotor_averaging={"grid": "cubature", "n_points": 7}))
    with pytest.raises(ValueError, match="supports n_points"):
        pywake_settings(_with(rotor_averaging={"grid": "cubature", "n_points": 5}))
    with pytest.raises(ValueError, match="Squared"):
        foxes_settings(_with(superposition={"ws_superposition": "Linear"}))


def _case_files(name):
    return sorted(CASE_ROOT.glob(f"*_turbine/*/{name}"))


def test_every_case_has_an_aligned_file():
    """Check all twelve cases ship both yaml files.

    Question answered: is any case missing its default or aligned configuration?
    """
    default_files = _case_files("wind_energy_system.yaml")
    aligned_files = _case_files("wind_energy_system_aligned.yaml")
    assert len(default_files) == len(aligned_files) == 12
    assert [f.parent for f in default_files] == [f.parent for f in aligned_files]


def test_aligned_files_differ_from_default_only_in_alignment_keys():
    """Check the aligned yaml adds the alignment keys and changes nothing else.

    Question answered: can a difference between the two views be attributed to the
    superposition and rotor_averaging settings alone?
    """
    for default_file, aligned_file in zip(
        _case_files("wind_energy_system.yaml"), _case_files("wind_energy_system_aligned.yaml")
    ):
        default, aligned = load_yaml(default_file), load_yaml(aligned_file)
        aligned_analyses = aligned["attributes"]["analyses"]
        assert set(aligned_analyses) - set(default["attributes"]["analyses"]) == {
            "superposition",
            "rotor_averaging",
        }
        del aligned_analyses["superposition"], aligned_analyses["rotor_averaging"]
        assert aligned == default, aligned_file


def test_alignment_analyses_are_identical_across_cases():
    """Check the reference case speaks for every case in an alignment.

    The site shows one settings table per alignment, taken from the reference case.

    Question answered: does any case configure the solvers differently from the others?
    """
    for alignment in ALIGNMENTS:
        reference = load_alignment_analyses(alignment["id"])
        for case_file in _case_files(alignment["yaml_file"]):
            analyses = load_yaml(case_file)["attributes"]["analyses"]
            for key in ("superposition", "rotor_averaging"):
                assert analyses.get(key) == reference.get(key), case_file


def test_alignment_settings_table_lists_every_difference():
    """Check the manifest settings table for both alignments.

    Question answered: does the table the site shows reflect the settings that run?
    """
    tables = {
        alignment_id: build_alignment_settings(
            load_alignment_analyses(alignment_id), ["FLORIS", "FOXES", "PyWake"]
        )
        for alignment_id in ALIGNMENT_IDS
    }
    default = {row["name"]: row for row in tables["default"]["settings"]}
    aligned = {row["name"]: row for row in tables["aligned"]["settings"]}

    assert default["Deficit reference wind speed"]["FOXES"].startswith("Local")
    assert aligned["Deficit reference wind speed"]["FOXES"].startswith("Freestream")
    assert "TurbineCubatureGrid" in aligned["Rotor grid"]["FLORIS"]
    assert "GridRotorAvg" in default["Rotor grid"]["PyWake"]
    assert tables["default"]["residual_differences"] == []
    assert [item["software"] for item in tables["aligned"]["residual_differences"]] == ["FOXES"]


def test_software_notes_follow_the_applied_settings():
    """Check the per-case implementation notes are built from the settings that ran.

    Question answered: do the notes describe the alignment they are shown under?
    """
    def notes(analyses):
        configuration = build_model_configuration(analyses, ["FLORIS", "FOXES", "PyWake"])
        return {item["software"]: " ".join(item["notes"]) for item in configuration["implementations"]}

    default_notes = notes(LEGACY)
    aligned_notes = notes(ALIGNED)

    assert "TurbineGrid" in default_notes["FLORIS"]
    assert "TurbineCubatureGrid" in aligned_notes["FLORIS"]
    assert "ws_quadratic" in default_notes["FOXES"] and "grid16" in aligned_notes["FOXES"]
    assert "not applied" in aligned_notes["FOXES"]
    assert "local" in default_notes["PyWake"].lower() and "freestream" in aligned_notes["PyWake"].lower()
