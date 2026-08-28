"""Validate the public paper-to-code map without claiming empirical reproduction."""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PaperCodeMapTests(unittest.TestCase):
    def test_paper_code_map_references_existing_public_artifacts(self) -> None:
        mapping_path = ROOT / "docs" / "paper_code_map.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))

        self.assertEqual(
            mapping["paper"]["empirical_reproduction"],
            {"400_case": False, "100_case": False, "40_case": False},
        )
        for concept in mapping["concepts"]:
            self.assertTrue((ROOT / concept["source_file"]).is_file(), concept["id"])
            self.assertTrue((ROOT / concept["test"]).is_file(), concept["id"])
            self.assertTrue((ROOT / concept["synthetic_example"]).is_file(), concept["id"])
            self.assertFalse(concept["empirical_reproduction"])
            self.assertIsInstance(concept["boundary"], str)
            self.assertTrue(concept["boundary"])
