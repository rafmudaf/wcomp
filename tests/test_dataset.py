import json

from wcomp import dataset


def test_case_matches_selectors_by_software_or_wake_model():
    """Check how `_case_matches_selectors` decides whether a wake model is selected.

    Calls the function with an empty selector set, a software selector
    ("floris"), a wake-model selector ("jensen"), and a mix of software and
    wake-model selectors. It asserts that an empty set matches every wake
    model, that a software selector matches wake models run by that software,
    that a wake-model selector matches only that wake model, and that a
    combined selector set excludes a wake model that matches none of the
    selectors ("bastankhah2016").

    Question answered: when a user passes selectors such as `floris` or
    `jensen` to the dataset generator, does the project include exactly the
    wake-model cases they asked for?
    """
    assert dataset._case_matches_selectors("jensen", set())
    assert dataset._case_matches_selectors("jensen", {"floris"})
    assert dataset._case_matches_selectors("jensen", {"jensen"})
    assert dataset._case_matches_selectors("turbopark", {"floris", "turbopark"})
    assert not dataset._case_matches_selectors("bastankhah2016", {"floris", "turbopark"})


def test_downselect_preserves_existing_manifest_cases(tmp_path, monkeypatch):
    """Check that a downselected `generate` run merges into an existing manifest.

    Points the dataset module at a temporary directory with a single scenario
    and a single FLORIS "jensen" wake model, and stubs out the computation and
    file writing so no real simulation runs. It pre-writes a `manifest.json`
    that already lists "existing_case", then calls `generate(selectors={"jensen"})`.
    It asserts the rewritten manifest lists the pre-existing case followed by
    the newly generated "one_turbine__jensen" case.

    Question answered: when only a subset of cases is regenerated, does the
    project keep the previously generated cases in the manifest instead of
    overwriting them?
    """
    monkeypatch.setattr(dataset, "DATASET_ROOT", tmp_path)
    monkeypatch.setattr(dataset, "SCENARIOS", ["one_turbine"])
    monkeypatch.setattr(dataset, "WAKE_MODEL_CASES", {"jensen": {"software": [dataset.WCompFloris]}})
    monkeypatch.setattr(dataset, "_software_versions", lambda: {"FLORIS": "1.0"})
    monkeypatch.setattr(dataset, "compute_case", lambda scenario, wake_model: {
        "streamwise": {"FLORIS": object()},
        "categories": [],
        "rotor_diameter": 1.0,
        "hub_height": 1.0,
        "wind_speed": 1.0,
        "yaw_angles": [],
        "model_configuration": {},
        "xsections": {},
        "xsection_locations_d": {},
        "planes": {},
        "vertical_planes": {},
        "xsection_contour_planes": {},
        "xsection_contour_location_d": 0,
    })
    monkeypatch.setattr(
        dataset, "write_case", lambda scenario, wake_model, result, software_versions: f"{scenario}__{wake_model}"
    )

    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-10-01T00:00:00Z",
                "wcomp_version": "old",
                "software_versions": {"FLORIS": "old"},
                "cases": ["existing_case"],
            }
        )
    )

    dataset.generate(selectors={"jensen"})

    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["cases"] == ["existing_case", "one_turbine__jensen"]
