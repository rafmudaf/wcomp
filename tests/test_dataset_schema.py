import json

import pytest

from wcomp import dataset
from wcomp.comparison_metadata import ALIGNMENT_IDS
from wcomp.dataset_validation import schema_name_for_path, validate_dataset_document


def test_checked_in_dataset_documents_match_schema():
    for path in dataset.DATASET_ROOT.rglob("*.json"):
        relative_path = path.relative_to(dataset.DATASET_ROOT)
        if relative_path.as_posix() == "schema.json":
            continue
        schema_name = schema_name_for_path(relative_path)
        validate_dataset_document(json.loads(path.read_text()), schema_name, str(relative_path))


@pytest.mark.parametrize(
    ("schema_name", "document"),
    [
        ("WakeProfile", {"x1": [0.0], "values": []}),
        ("WakePlane", {"x1": [0.0], "x2": [0.0, 1.0], "values": [1.0], "normal_vector": "z"}),
        ("Metrics", [{"pair": ["FLORIS"], "target": "streamwise"}]),
    ],
)
def test_invalid_documents_are_rejected(schema_name, document):
    with pytest.raises(ValueError, match=f"Invalid {schema_name}"):
        validate_dataset_document(document, schema_name)


def test_manifest_lists_each_alignment_with_its_generated_cases():
    manifest = json.loads((dataset.DATASET_ROOT / "manifest.json").read_text())

    assert [item["id"] for item in manifest["alignments"]] == list(ALIGNMENT_IDS)
    for item in manifest["alignments"]:
        for case_id in item["cases"]:
            case = json.loads(
                (dataset.DATASET_ROOT / item["id"] / "cases" / case_id / "case.json").read_text()
            )
            assert case["alignment"] == item["id"]
        assert (dataset.DATASET_ROOT / item["id"] / "rotor_average.json").exists()
        assert (dataset.DATASET_ROOT / item["id"] / "turbine_performance.json").exists()


@pytest.mark.parametrize(
    ("path", "schema_name"),
    [
        ("default/cases/a__b/case.json", "Case"),
        ("aligned/cases/a__b/metrics.json", "Metrics"),
        ("aligned/cases/a__b/software/FLORIS/xsections/5D.json", "WakeProfile"),
        ("default/rotor_average.json", "RotorAverageDataset"),
        ("aligned/turbine_performance.json", "TurbinePerformanceDataset"),
        ("manifest.json", "Manifest"),
    ],
)
def test_paths_resolve_to_schemas_under_an_alignment(path, schema_name):
    assert schema_name_for_path(path) == schema_name


@pytest.mark.parametrize("path", ["cases/a__b/case.json", "rotor_average.json", "other/cases/a__b/case.json"])
def test_paths_outside_an_alignment_are_rejected(path):
    with pytest.raises(ValueError, match="No dataset schema"):
        schema_name_for_path(path)


def test_export_rejects_invalid_document_before_writing(tmp_path, monkeypatch):
    monkeypatch.setattr(dataset, "DATASET_ROOT", tmp_path)
    output_path = tmp_path / "default" / "cases" / "sample" / "software" / "FLORIS" / "streamwise.json"

    with pytest.raises(ValueError, match="x1 and values lengths differ"):
        dataset._write_json(output_path, {"x1": [0.0], "values": [1.0, 2.0]}, compact=True)

    assert not output_path.exists()