"""Validation helpers for the generated JSON dataset."""

import json
from functools import lru_cache
from pathlib import Path, PurePosixPath

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "dataset" / "schema.json"


@lru_cache(maxsize=1)
def _schema() -> dict:
    with SCHEMA_PATH.open(encoding="utf-8") as schema_file:
        schema = json.load(schema_file)
    Draft202012Validator.check_schema(schema)
    return schema


@lru_cache(maxsize=None)
def _validator(schema_name: str) -> Draft202012Validator:
    schema = _schema()
    if schema_name not in schema["$defs"]:
        raise ValueError(f"Unknown dataset schema definition: {schema_name}")
    scoped_schema = {
        "$schema": schema["$schema"],
        "$defs": schema["$defs"],
        "$ref": f"#/$defs/{schema_name}",
    }
    return Draft202012Validator(scoped_schema, format_checker=FormatChecker())


def schema_name_for_path(relative_path: str | Path) -> str:
    """Return the schema definition used by a dataset JSON path."""
    parts = PurePosixPath(str(relative_path).replace("\\", "/")).parts
    if parts == ("manifest.json",):
        return "Manifest"
    if parts == ("models.json",):
        return "ModelRegistry"
    if parts == ("rotor_average.json",):
        return "RotorAverageDataset"
    if parts == ("turbine_performance.json",):
        return "TurbinePerformanceDataset"
    if len(parts) == 3 and parts[0] == "cases" and parts[2] == "case.json":
        return "Case"
    if len(parts) == 3 and parts[0] == "cases" and parts[2] == "metrics.json":
        return "Metrics"
    if len(parts) >= 5 and parts[0] == "cases" and parts[2] == "software":
        if parts[-1] == "meta.json":
            return "SoftwareMetadata"
        if parts[-1] in {"contour.json", "contour_vertical.json", "contour_xsection.json"}:
            return "WakePlane"
        if parts[-1] == "streamwise.json" or (len(parts) >= 6 and parts[-2] == "xsections"):
            return "WakeProfile"
    raise ValueError(f"No dataset schema is defined for path: {relative_path}")


def validate_dataset_document(document: object, schema_name: str, source: str = "<memory>") -> None:
    """Validate one decoded dataset document, raising ValueError with its location."""
    validator = _validator(schema_name)
    errors = sorted(
        validator.iter_errors(document),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
            for error in errors[:5]
        )
        raise ValueError(f"Invalid {schema_name} document at {source}: {details}")

    if schema_name == "WakeProfile" and len(document["x1"]) != len(document["values"]):
        raise ValueError(f"Invalid WakeProfile document at {source}: x1 and values lengths differ")
    if schema_name == "WakePlane":
        lengths = {len(document[key]) for key in ("x1", "x2", "values")}
        if len(lengths) != 1:
            raise ValueError(f"Invalid WakePlane document at {source}: x1, x2, and values lengths differ")
    if schema_name == "Case":
        if len(document["turbine_locations_d"]) != len(document["turbine_yaw_deg"]):
            raise ValueError(f"Invalid Case document at {source}: turbine location and yaw lengths differ")
        if set(document["xsection_labels"]) != set(document["xsection_locations_d"]):
            raise ValueError(f"Invalid Case document at {source}: cross-section labels and locations differ")
    if schema_name == "RotorAverageDataset":
        for method in document["methods"]:
            lengths = {len(method[key]) for key in ("nodes_y", "nodes_z", "weights")}
            if lengths != {method["sample_count"]}:
                raise ValueError(
                    f"Invalid RotorAverageDataset document at {source}: "
                    f"method {method['method']} sample arrays differ"
                )
        for case in document["cases"]:
            axis_length = len(case["field"]["axis"])
            rows = case["field"]["values"]
            if len(rows) != axis_length or any(len(row) != axis_length for row in rows):
                raise ValueError(
                    f"Invalid RotorAverageDataset document at {source}: "
                    f"case {case['key']} field dimensions differ from axis"
                )
    if schema_name == "TurbinePerformanceDataset":
        lengths = {
            len(document["wind_speeds"]),
            len(document["reference_curves"]["power_kw"]),
            len(document["reference_curves"]["ct"]),
            *(len(result[key]) for result in document["results"] for key in ("power_kw", "ct")),
        }
        if len(lengths) != 1:
            raise ValueError(
                f"Invalid TurbinePerformanceDataset document at {source}: "
                "result series lengths differ from wind_speeds"
            )
        curve = document["turbine"]["curve"]
        if len({len(curve[key]) for key in ("wind_speeds", "power_kw", "ct")}) != 1:
            raise ValueError(
                f"Invalid TurbinePerformanceDataset document at {source}: "
                "turbine curve series lengths differ"
            )