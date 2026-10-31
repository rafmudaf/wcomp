import numpy as np
from foxes.models.rotor_models.grid import GridRotor
import wcomp.rotor_average as rotor_average
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


def test_uniform_case_is_exact_for_every_method():
    """Check that every method reproduces a uniform inflow exactly.

    Compares all methods on the uniform case and asserts each rotor average is
    1.0 with absolute error below 1e-12. It then evaluates each method
    directly on `uniform_velocity` and asserts the result is 1.0.

    Question answered: is every stencil a consistent quadrature, so any
    nonzero error on the harder cases comes from the sampling and not from a
    bug in the weights or aggregation?
    """
    for result in compare_rotor_average_methods(_case("uniform")):
        assert np.isclose(result.rotor_average, 1.0, atol=1.0e-12)
        assert result.absolute_error < 1.0e-12

    for method in get_rotor_average_methods():
        assert np.isclose(method.evaluate(uniform_velocity), 1.0, atol=1.0e-12)


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
        result.software: result for result in compare_rotor_average_methods(_case("linear"))
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


def test_quadratic_case_ranks_methods_by_radial_reach():
    """Check the quadratic-deficit case and how stencil reach affects accuracy.

    Asserts the dense-disk average of the quadratic profile is 0.9. Then
    asserts FLORIS and PyWake overpredict relative to their reference because
    they sample well inside the rim and miss the slow tip flow, while FOXES
    lands slightly low because its grid covers the whole disk and carries some
    weight beyond it. Finally asserts the error ordering PyWake < FOXES <
    FLORIS, which follows how far each stencil reaches toward the blade tips
    (CGI quadrature, full rotor, inner half radius).

    Question answered: how does the radial extent of each solver's sampling
    grid affect its rotor-average error for a smoothly varying wake?
    """
    results = {
        result.software: result for result in compare_rotor_average_methods(_case("quadratic"))
    }

    assert np.isclose(
        dense_disk_average(quadratic_velocity, "weighted arithmetic mean of velocity"),
        0.9,
        atol=1.0e-12,
    )

    # FLORIS and PyWake sample well inside the rim, so both miss the slow tip flow and
    # overpredict. FOXES spans the whole disk and even carries weight slightly beyond it,
    # so it lands marginally low instead.
    assert results["FLORIS"].rotor_average > results["FLORIS"].reference_average
    assert results["PyWake"].rotor_average > results["PyWake"].reference_average
    assert results["FOXES"].rotor_average < results["FOXES"].reference_average

    # Accuracy tracks how far each stencil reaches toward the blade tips: PyWake's CGI
    # quadrature is exact for this quadratic profile, FOXES covers the full rotor, and
    # FLORIS only the inner half radius.
    assert results["PyWake"].absolute_error < results["FLORIS"].absolute_error
    assert results["PyWake"].absolute_error < results["FOXES"].absolute_error
    assert results["FOXES"].absolute_error < results["FLORIS"].absolute_error


def test_partial_wake_case_compares_all_methods_head_to_head():
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
    results = compare_rotor_average_methods(_case("partial_wake"))

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
                for item in compare_rotor_average_methods(_case(earlier))
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


def test_site_dataset_contains_case_ladder_and_method_provenance():
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
    dataset = build_rotor_average_dataset()
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
