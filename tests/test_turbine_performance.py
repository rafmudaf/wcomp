import numpy as np
import pytest
from wcomp.comparison_metadata import ALIGNMENT_IDS, load_alignment_analyses
from wcomp.dataset_validation import validate_dataset_document

from wcomp.turbine_performance import (
    SOFTWARE_EVALUATORS,
    build_turbine_performance_dataset,
    evaluate_floris,
    get_common_turbine,
    get_sweep_wind_speeds,
    reference_curves,
)


@pytest.fixture(scope="module")
def turbine():
    return get_common_turbine()


@pytest.fixture(scope="module")
def sweep(turbine):
    return get_sweep_wind_speeds(turbine)


@pytest.fixture(scope="module")
def results(turbine, sweep):
    return {name: evaluate(turbine, sweep) for name, evaluate in SOFTWARE_EVALUATORS.items()}


def test_common_turbine_is_a_power_and_thrust_curve(turbine):
    """Check the shared turbine definition is a sane power and thrust table.

    Asserts the wind speed, power and Ct arrays have the same length, that the
    wind speeds are strictly increasing, that rated power is between 15,000 and
    16,500 kW (the IEA 15 MW turbine), and that every Ct value is positive.

    Question answered: is the single turbine all three solvers are fed a valid
    and plausible 15 MW power and thrust curve?
    """
    assert turbine.wind_speeds.size == turbine.power_kw.size == turbine.ct.size
    assert np.all(np.diff(turbine.wind_speeds) > 0.0)
    assert 15000.0 < turbine.rated_power_kw < 16500.0
    assert np.all(turbine.ct > 0.0)


def test_sweep_extends_beyond_the_curve_and_includes_its_end_points(turbine, sweep):
    """Check the wind speed sweep covers the whole curve and its edges.

    Asserts the sweep starts at 0 m/s, ends at least 1 m/s above the cut-out
    wind speed, and contains the exact cut-in and cut-out wind speeds.

    Question answered: does the sweep test the turbine below cut-in, across
    the tabulated range, and above cut-out, with the curve end points
    evaluated exactly?
    """
    assert sweep[0] == 0.0
    assert sweep[-1] >= turbine.cut_out + 1.0
    assert turbine.cut_in in sweep
    assert turbine.cut_out in sweep


def test_every_software_reproduces_the_common_power_curve(turbine, sweep, results):
    """Check FLORIS, FOXES and PyWake all return the common power curve.

    Evaluates each solver on the sweep and compares its power in kW with the
    reference curve (linear interpolation of the common table, zero outside
    the range) with rtol 1e-9 and atol 1e-6.

    Question answered: do the three solvers produce the same power for the
    same turbine, so differences in wake results are not caused by differences
    in the power curve?
    """
    reference = reference_curves(turbine, sweep)
    for name, values in results.items():
        assert np.allclose(values["power_kw"], reference["power_kw"], rtol=1e-9, atol=1e-6), name


def test_thrust_coefficient_matches_inside_the_tabulated_range(turbine, sweep, results):
    """Check every solver's Ct matches the reference between cut-in and cut-out.

    Restricts the sweep to wind speeds from cut-in to cut-out inclusive and
    asserts each solver's Ct equals the reference Ct within an absolute
    tolerance of 1e-9.

    Question answered: do the three solvers use the same thrust coefficient
    wherever the turbine is operating?
    """
    reference = reference_curves(turbine, sweep)
    inside = (sweep >= turbine.cut_in) & (sweep <= turbine.cut_out)
    for name, values in results.items():
        assert np.allclose(values["ct"][inside], reference["ct"][inside], atol=1e-9), name


def test_thrust_coefficient_outside_the_range_differs_by_software(turbine, sweep, results):
    """Document how each solver handles Ct below cut-in and above cut-out.

    Asserts FOXES and PyWake return Ct of 0 outside the tabulated range, while
    FLORIS returns a small positive floor of 1e-4.

    Question answered: where the solvers are known to disagree on thrust
    outside the operating range, exactly how do they differ?
    """
    outside = (sweep < turbine.cut_in) | (sweep > turbine.cut_out)
    assert np.allclose(results["FOXES"]["ct"][outside], 0.0)
    assert np.allclose(results["PyWake"]["ct"][outside], 0.0)
    # FLORIS clips Ct to a small positive floor instead of reaching zero.
    assert np.allclose(results["FLORIS"]["ct"][outside], 1.0e-4)


def test_floris_turbine_curves_do_not_depend_on_the_rotor_grid(turbine, sweep):
    """Check the aligned FLORIS grid reproduces the default grid's power and Ct.

    Question answered: in uniform flow, is the turbine-performance comparison the same
    in both alignments, as the site page states?
    """
    default = evaluate_floris(turbine, sweep, load_alignment_analyses("default"))
    aligned = evaluate_floris(turbine, sweep, load_alignment_analyses("aligned"))
    for key in ("power_kw", "ct"):
        assert np.allclose(default[key], aligned[key], rtol=1e-9, atol=1e-9), key


@pytest.mark.parametrize("alignment", ALIGNMENT_IDS)
def test_site_dataset_describes_the_common_turbine_and_each_software(sweep, alignment):
    """Check the structure of the dataset built for the turbine-performance site page.

    Builds the dataset and asserts its wind speeds equal the sweep, its
    results list FLORIS, FOXES and PyWake in that order, and its "execution"
    entry mentions "native". For each result it asserts the power and Ct
    arrays match the sweep length, an implementation description is present,
    and the maximum absolute power error is below 1e-6 kW. It also asserts the
    reference power and Ct curves match the sweep length.

    Question answered: does the dataset consumed by the website contain the
    sweep, each solver's results and provenance, and the reference curves the
    page needs?
    """
    dataset = build_turbine_performance_dataset(alignment)
    validate_dataset_document(dataset, "TurbinePerformanceDataset")

    assert dataset["wind_speeds"] == sweep.tolist()
    assert [item["software"] for item in dataset["results"]] == ["FLORIS", "FOXES", "PyWake"]
    assert "native" in dataset["execution"]
    for item in dataset["results"]:
        for key in ("power_kw", "ct"):
            assert len(item[key]) == len(sweep)
        assert item["implementation"]
        assert item["max_abs_power_error_kw"] < 1.0e-6
    for key in ("power_kw", "ct"):
        assert len(dataset["reference_curves"][key]) == len(sweep)
