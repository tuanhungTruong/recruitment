from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from aggregator.processing import (
    CampaignStats,
    aggregate_csv,
    rank_top_cpa,
    rank_top_ctr,
    write_campaign_csv,
)

FIXTURE = Path(__file__).parent / "fixtures" / "sample.csv"


class AggregateCsvTests(unittest.TestCase):
    def test_aggregates_valid_rows_and_skips_malformed(self) -> None:
        warnings = io.StringIO()
        result = aggregate_csv(FIXTURE, warn_stream=warnings)

        self.assertEqual(result.rows_read, 6)
        self.assertEqual(result.rows_skipped, 3)
        self.assertIn("CMP_A", result.campaigns)

        cmp_a = result.campaigns["CMP_A"]
        self.assertEqual(cmp_a.impressions, 2000)
        self.assertEqual(cmp_a.clicks, 200)
        self.assertAlmostEqual(cmp_a.spend, 100.0)
        self.assertEqual(cmp_a.conversions, 10)
        self.assertAlmostEqual(cmp_a.ctr or 0.0, 0.1)
        self.assertAlmostEqual(cmp_a.cpa or 0.0, 10.0)

        self.assertIsNone(result.campaigns["CMP_C"].cpa)
        self.assertIn("Skipping malformed row", warnings.getvalue())

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            aggregate_csv(Path("does-not-exist.csv"), warn_stream=None)

    def test_empty_file_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty.csv"
            empty.write_text("", encoding="utf-8")
            with self.assertRaises(ValueError):
                aggregate_csv(empty, warn_stream=None)

    def test_missing_columns_raise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text("campaign_id,date\nCMP_A,2025-01-01\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                aggregate_csv(path, warn_stream=None)


class RankingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.campaigns = {
            "HIGH_CTR": CampaignStats("HIGH_CTR", 1000, 200, 100.0, 5),
            "MID_CTR": CampaignStats("MID_CTR", 1000, 100, 80.0, 8),
            "LOW_CPA": CampaignStats("LOW_CPA", 1000, 10, 10.0, 10),
            "NO_CONV": CampaignStats("NO_CONV", 1000, 50, 40.0, 0),
            "NO_IMP": CampaignStats("NO_IMP", 0, 0, 0.0, 0),
        }

    def test_top_ctr_excludes_zero_impressions_and_sorts_desc(self) -> None:
        ranked = rank_top_ctr(self.campaigns, n=3)
        self.assertEqual(
            [stats.campaign_id for stats in ranked],
            ["HIGH_CTR", "MID_CTR", "NO_CONV"],
        )

    def test_top_cpa_excludes_zero_conversions_and_sorts_asc(self) -> None:
        ranked = rank_top_cpa(self.campaigns, n=10)
        self.assertEqual(
            [stats.campaign_id for stats in ranked],
            ["LOW_CPA", "MID_CTR", "HIGH_CTR"],
        )


class CsvOutputTests(unittest.TestCase):
    def test_writes_expected_headers_and_null_cpa(self) -> None:
        stats = [
            CampaignStats("CMP_A", 2000, 200, 100.0, 10),
            CampaignStats("CMP_C", 500, 50, 25.0, 0),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.csv"
            write_campaign_csv(path, stats)
            content = path.read_text(encoding="utf-8")

        lines = content.strip().splitlines()
        self.assertEqual(
            lines[0],
            "campaign_id,total_impressions,total_clicks,total_spend,total_conversions,CTR,CPA",
        )
        self.assertEqual(lines[1], "CMP_A,2000,200,100.00,10,0.100000,10.00")
        self.assertEqual(lines[2], "CMP_C,500,50,25.00,0,0.100000,")


if __name__ == "__main__":
    unittest.main()
