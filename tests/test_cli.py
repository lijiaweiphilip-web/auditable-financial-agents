from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from auditable_financial_agents.cli import demo, evaluate_path, main

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_evaluate_path_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "result.json"
            payload = evaluate_path(ROOT / "examples" / "clean_case.json", out)
            self.assertEqual(payload["opinion"], "Clean")
            saved = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(saved["case_id"], "clean_revenue_table")

    def test_demo_runs_all_examples(self) -> None:
        results = demo(ROOT / "examples")
        self.assertGreaterEqual(len(results), 5)
        labels = {row["case_id"]: row["opinion"] for row in results}
        self.assertEqual(labels["clean_revenue_table"], "Clean")
        self.assertEqual(labels["disclaimer_missing_evidence"], "Disclaimer")

    def test_main_evaluate(self) -> None:
        code = main(["evaluate", str(ROOT / "examples" / "clean_case.json")])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
