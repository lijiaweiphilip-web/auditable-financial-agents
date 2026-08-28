"""Validate the public paper-to-code map without claiming empirical reproduction."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_paper_code_map_references_existing_public_artifacts() -> None:
    mapping_path = ROOT / "docs" / "paper_code_map.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))

    assert mapping["paper"]["empirical_reproduction"] == {
        "400_case": False,
        "100_case": False,
        "40_case": False,
    }
    for concept in mapping["concepts"]:
        assert (ROOT / concept["source_file"]).is_file(), concept["id"]
        assert (ROOT / concept["test"]).is_file(), concept["id"]
        assert (ROOT / concept["synthetic_example"]).is_file(), concept["id"]
        assert concept["empirical_reproduction"] is False
        assert isinstance(concept["boundary"], str) and concept["boundary"]
