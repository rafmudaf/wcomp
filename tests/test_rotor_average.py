import numpy as np
import pytest
from foxes.models.rotor_models.grid import GridRotor
import wcomp.rotor_average as rotor_average
from wcomp.comparison_metadata import ALIGNMENT_IDS
from wcomp.rotor_average import (
    build_rotor_average_dataset,
    compare_rotor_average_methods,
    dense_disk_average,
    get_rotor_average_cases,
    get_rotor_average_methods,
    quadratic_velocity,
    uniform_velocity,
)
from wcomp.dataset_validation import validate_dataset_document


def _case(key):
    return next(case for case in get_rotor_average_cases() if case.key == key)


@pytest.mark.parametrize("alignment", ALIGNMENT_IDS)
def test_uniform_case_is_exact_for_every_method(alignment):
    """Check that every method reproduces a uniform inflow exactly, in both alignments.

    Compares all methods on the uniform case and asserts each rotor average is
    1.0 with absolute error below 1e-12. It then evaluates each method
    directly on `uniform_velocity` and asserts the result is 1.0.

    Question answered: is every stencil a consistent quadrature, so any
    nonzero error on the harder cases comes from the sampling and not from a
    bug in the weights or aggregation?
    """
    for result in compare_rotor_average_methods(_case("uniform"), alignment=alignment):
        assert np.isclose(result.rotor_average, 1.0, atol=1.0e-12)
        assert result.absolute_error < 1.0e-12

    for method in get_rotor_average_methods(alignment):
        assert np.isclose(method.evaluate(uniform_velocity), 1.0, atol=1.0e-12)


def test_default_alignment_uses_each_solvers_legacy_stencil():
    """Check the default alignment samples the rotor the way each solver does out of the box.

    Asserts FLORIS uses its 3 x 3 TurbineGrid with a cubic mean, FOXES grid16, and
    PyWake's four-point GridRotorAvg.

    Question answered: does the default view really describe the unmodified solvers?
    """
    methods = {method.software: method for method in get_rotor_average_methods("default")}

    assert methods["FLORIS"].method.startswith("TurbineGrid")
    assert methods["FLORIS"].sample_count == 9
    assert methods["FLORIS"].aggregation == "cubic mean of velocity"
    assert methods["FOXES"].sample_count == 16
    assert methods["PyWake"].method == "GridRotorAvg"
    assert methods["PyWake"].sample_count == 4


def test_aligned_alignment_uses_nine_point_cubature_for_floris_and_pywake():
    """Check the aligned alignment samples FLORIS and PyWake with nine-point cubature.

    Asserts FLORIS uses TurbineCubatureGrid with a linear cubature, PyWake uses
    CGIRotorAvg(n=9), and FOXES keeps grid16 (it has no nine-point stencil).

    Question answered: are the settings the aligned yaml asks for the ones that run?
    """
    methods = {method.software: method for method in get_rotor_average_methods("aligned")}

    assert methods["FLORIS"].method.startswith("TurbineCubatureGrid")
    assert methods["FLORIS"].sample_count == 9
    assert methods["FLORIS"].aggregation == "linear cubature of velocity"
    assert methods["PyWake"].method == "CGIRotorAvg(n=9)"
    assert methods["PyWake"].sample_count == 9
    assert methods["FOXES"].sample_count == 16


def test_linear_case_is_exact_for_symmetric_arithmetic_stencils():
    """Check the linear vertical-shear case for each method.

    For FOXES and PyWake, which take a weighted arithmetic mean, asserts the
    rotor average is 1.0 and the error is below 1e-12 because their symmetric
    stencils cancel the linear term. For FLORIS, which now uses the native
    cubature grid, asserts the average is also exactly 1.0 and the error stays
    below 1e-12.

    Question answered: do symmetric stencils average linear shear correctly,
    and does FLORIS' cubature aggregation preserve that exactness?
    """
    results = {
        result.software: result
        for result in compare_rotor_average_methods(_case("linear"), alignment="aligned")
    }

    for software in ("FOXES", "PyWake"):
        assert results[software].aggregation == "weighted arithmetic mean of velocity"
        assert np.isclose(results[software].rotor_average, 1.0, atol=1.0e-12)
        assert results[software].absolute_error < 1.0e-12

    # FLORIS cancels the linear term by symmetry too, and its cubature quadrature
    # preserves the exact linear average.
    assert results["FLORIS"].aggregation == "linear cubature of velocity"
    assert np.isclose(results["FLORIS"].rotor_average, 1.0, atol=1.0e-12)
    assert np.isclose(results["FLORIS"].reference_average, 1.0, atol=1.0e-12)
    assert results["FLORIS"].absolute_error < 1.0e-12


def _quadratic_results(alignment):
    assert np.isclose(
        dense_disk_average(quadratic_velocity, "weighted arithmetic mean of velocity"),
        0.9,
        atol=1.0e-12,
    )
    return {
        result.software: result
        for result in compare_rotor_average_methods(_case("quadratic"), alignment=alignment)
    }


def test_default_quadratic_case_ranks_methods_by_radial_reach():
    """Check the quadratic-deficit case and how stencil reach affects accuracy by default.

    Asserts the dense-disk average of the quadratic profile is 0.9. Then asserts FLORIS
    and PyWake overpredict relative to their reference because their stencils sit well
    inside the rim and miss the slow tip flow, while FOXES lands slightly low because its
    grid covers the whole disk and carries some weight beyond it. Finally asserts the
    error ordering FOXES < FLORIS < PyWake, which follows how far each stencil reaches
    toward the blade tips (full rotor, inner half radius, inner third radius).

    Question answered: how does the radial extent of each solver's own sampling grid
    affect its rotor-average error for a smoothly varying wake?
    """
    results = _quadratic_results("default")

    assert results["FLORIS"].rotor_average > results["FLORIS"].reference_average
    assert results["PyWake"].rotor_average > results["PyWake"].reference_average
    assert results["FOXES"].rotor_average < results["FOXES"].reference_average

    assert results["FOXES"].absolute_error < results["FLORIS"].absolute_error
    assert results["FLORIS"].absolute_error < results["PyWake"].absolute_error


def test_aligned_quadratic_case_is_exact_for_nine_point_cubature():
    """Check the nine-point cubature integrates the quadratic deficit exactly.

    Asserts FLORIS and PyWake, both now on nine-point cubature, recover the 0.9 area
    average to 1e-12, while FOXES' grid16 stays slightly low.

    Question answered: does matching the stencils remove the FLORIS and PyWake
    rotor-average difference on a smooth profile?
    """
    results = _quadratic_results("aligned")

    assert results["FLORIS"].absolute_error < 1.0e-12
    assert results["PyWake"].absolute_error < 1.0e-12
    assert results["FOXES"].rotor_average < results["FOXES"].reference_average


@pytest.mark.parametrize("alignment", ALIGNMENT_IDS)
def test_partial_wake_case_compares_all_methods_head_to_head(alignment):
    """Check the partial-wake case, the hardest case in the ladder.

    Asserts the results come back in the order FLORIS, FOXES, PyWake, that each
    rotor average is in (0, 1], that the three averages differ from each other
    (to 8 decimals), and that the largest absolute error is below 0.04. It also
    asserts that, for every method, the error is larger than on both the
    uniform and the linear cases.

    Question answered: when the wake covers only part of the rotor, do the
    solvers disagree with each other and with the reference, and does the
    error grow along the ladder of cases as the field gets harder to resolve?
    """
    results = compare_rotor_average_methods(_case("partial_wake"), alignment=alignment)

    assert [result.software for result in results] == ["FLORIS", "FOXES", "PyWake"]
    assert all(0.0 < result.rotor_average <= 1.0 for result in results)
    assert len({round(result.rotor_average, 8) for result in results}) == 3
    assert max(result.absolute_error for result in results) < 0.04

    # Errors grow monotonically along the ladder for every method: a field the stencils
    # cannot resolve costs more than the smooth cases that precede it.
    for method, result in {result.software: result for result in results}.items():
        for earlier in ("uniform", "linear"):
            earlier_result = next(
                item
                for item in compare_rotor_average_methods(_case(earlier), alignment=alignment)
                if item.software == method
            )
            assert result.absolute_error > earlier_result.absolute_error


def test_compare_rotor_average_methods_defaults_to_partial_wake():
    """Check the default argument of `compare_rotor_average_methods`.

    Asserts that calling the function with no case returns the same results as
    passing the "partial_wake" case explicitly.

    Question answered: does the comparison default to the partial-wake case,
    the scenario most representative of wake effects on a downstream rotor?
    """
    assert compare_rotor_average_methods() == compare_rotor_average_methods(_case("partial_wake"))


@pytest.mark.parametrize("alignment", ALIGNMENT_IDS)
def test_site_dataset_contains_case_ladder_and_method_provenance(alignment):
    """Check the structure of the dataset built for the rotor-averaging site page.

    Builds the dataset and asserts the cases appear in the order uniform,
    linear, quadratic, partial_wake, and that there are three methods.
    It also asserts every method has
    an implementation description and as many y nodes as sample points. For
    each case it asserts there are three results, the plotted field has one
    row of values per axis point, and the corner point outside the rotor disk
    is masked as None.

    Question answered: does the dataset consumed by the website contain every
    case, method, result and field the page needs, with provenance showing
    that the solvers' own averaging code produced the numbers?
    """
    dataset = build_rotor_average_dataset(alignment)
    validate_dataset_document(dataset, "RotorAverageDataset")

    assert [case["key"] for case in dataset["cases"]] == [
        "uniform",
        "linear",
        "quadratic",
        "partial_wake",
    ]
    assert len(dataset["methods"]) == 3
    assert all(method["implementation"] for method in dataset["methods"])
    assert all(len(method["nodes_y"]) == method["sample_count"] for method in dataset["methods"])

    for case in dataset["cases"]:
        assert len(case["results"]) == 3
        assert len(case["field"]["values"]) == len(case["field"]["axis"])
        # Points outside the rotor disk are masked out for plotting.
        assert case["field"]["values"][0][0] is None
