import json

import pytest

from wcomp import dataset
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


def test_export_rejects_invalid_document_before_writing(tmp_path, monkeypatch):
    monkeypatch.setattr(dataset, "DATASET_ROOT", tmp_path)
    output_path = tmp_path / "cases" / "sample" / "software" / "FLORIS" / "streamwise.json"

    with pytest.raises(ValueError, match="x1 and values lengths differ"):
        dataset._write_json(output_path, {"x1": [0.0], "values": [1.0, 2.0]}, compact=True)

    assert not output_path.exists()