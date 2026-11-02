from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from aggregator.cli import main

FIXTURE = Path(__file__).parent / "fixtures" / "sample.csv"


class CliTests(unittest.TestCase):
    def test_writes_ranked_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            exit_code = main(["--input", str(FIXTURE), "--output", str(output)])
            self.assertEqual(exit_code, 0)
            self.assertTrue((output / "top10_ctr.csv").is_file())
            self.assertTrue((output / "top10_cpa.csv").is_file())

            ctr_lines = (output / "top10_ctr.csv").read_text(encoding="utf-8").splitlines()
            self.assertEqual(ctr_lines[1].split(",")[0], "CMP_A")

            cpa_lines = (output / "top10_cpa.csv").read_text(encoding="utf-8").splitlines()
            self.assertEqual(cpa_lines[1].split(",")[0], "CMP_D")

    def test_missing_input_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            exit_code = main(
                ["--input", str(Path(tmp) / "missing.csv"), "--output", tmp]
            )
        self.assertEqual(exit_code, 2)
