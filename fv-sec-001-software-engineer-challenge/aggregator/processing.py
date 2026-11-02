from __future__ import annotations

import csv
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

REQUIRED_COLUMNS = (
    "campaign_id",
    "impressions",
    "clicks",
    "spend",
    "conversions",
)

OUTPUT_COLUMNS = (
    "campaign_id",
    "total_impressions",
    "total_clicks",
    "total_spend",
    "total_conversions",
    "CTR",
    "CPA",
)


@dataclass(slots=True)
class CampaignStats:
    campaign_id: str
    impressions: int = 0
    clicks: int = 0
    spend: float = 0.0
    conversions: int = 0

    def add(self, impressions: int, clicks: int, spend: float, conversions: int) -> None:
        self.impressions += impressions
        self.clicks += clicks
        self.spend += spend
        self.conversions += conversions

    @property
    def ctr(self) -> float | None:
        if self.impressions <= 0:
            return None
        return self.clicks / self.impressions

    @property
    def cpa(self) -> float | None:
        if self.conversions <= 0:
            return None
        return self.spend / self.conversions


@dataclass(frozen=True, slots=True)
class AggregateResult:
    campaigns: dict[str, CampaignStats]
    rows_read: int
    rows_skipped: int


def aggregate_csv(
    path: Path,
    *,
    warn_stream: TextIO | None = sys.stderr,
    max_warnings: int = 20,
) -> AggregateResult:
    """Stream a CSV file and accumulate per-campaign totals.

    Memory use is O(unique campaigns), not O(rows). Date is ignored.
    """
    campaigns: dict[str, CampaignStats] = {}
    rows_read = 0
    rows_skipped = 0
    warnings_emitted = 0

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError(f"{path} is empty") from exc

        indexes = _column_indexes(header)

        for line_number, row in enumerate(reader, start=2):
            parsed = _parse_row(row, indexes)
            if parsed is None:
                rows_skipped += 1
                if warn_stream is not None and warnings_emitted < max_warnings:
                    warn_stream.write(
                        f"Skipping malformed row {line_number} in {path}\n"
                    )
                    warnings_emitted += 1
                continue

            campaign_id, impressions, clicks, spend, conversions = parsed
            rows_read += 1
            stats = campaigns.get(campaign_id)
            if stats is None:
                stats = CampaignStats(campaign_id)
                campaigns[campaign_id] = stats
            stats.add(impressions, clicks, spend, conversions)

    if warn_stream is not None and rows_skipped > max_warnings:
        warn_stream.write(
            f"... {rows_skipped - max_warnings} additional malformed rows skipped\n"
        )

    return AggregateResult(
        campaigns=campaigns,
        rows_read=rows_read,
        rows_skipped=rows_skipped,
    )


def rank_top_ctr(
    campaigns: Mapping[str, CampaignStats],
    n: int = 10,
) -> list[CampaignStats]:
    eligible = [stats for stats in campaigns.values() if stats.ctr is not None]
    eligible.sort(
        key=lambda stats: (
            -(stats.ctr or 0.0),
            -stats.impressions,
            stats.campaign_id,
        )
    )
    return eligible[:n]


def rank_top_cpa(
    campaigns: Mapping[str, CampaignStats],
    n: int = 10,
) -> list[CampaignStats]:
    eligible = [stats for stats in campaigns.values() if stats.cpa is not None]
    eligible.sort(
        key=lambda stats: (
            stats.cpa or 0.0,
            stats.campaign_id,
        )
    )
    return eligible[:n]


def write_campaign_csv(path: Path, rows: Sequence[CampaignStats]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(OUTPUT_COLUMNS)
        for stats in rows:
            writer.writerow(_format_row(stats))


def _column_indexes(header: Sequence[str]) -> dict[str, int]:
    normalized = [column.strip() for column in header]
    missing = [name for name in REQUIRED_COLUMNS if name not in normalized]
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")
    return {name: normalized.index(name) for name in REQUIRED_COLUMNS}


def _parse_row(
    row: Sequence[str],
    indexes: Mapping[str, int],
) -> tuple[str, int, int, float, int] | None:
    try:
        campaign_id = row[indexes["campaign_id"]].strip()
        if not campaign_id:
            return None
        impressions = int(row[indexes["impressions"]])
        clicks = int(row[indexes["clicks"]])
        spend = float(row[indexes["spend"]])
        conversions = int(row[indexes["conversions"]])
    except (IndexError, TypeError, ValueError):
        return None

    if min(impressions, clicks, conversions) < 0 or spend < 0:
        return None
    return campaign_id, impressions, clicks, spend, conversions


def _format_row(stats: CampaignStats) -> list[str]:
    ctr = stats.ctr
    cpa = stats.cpa
    return [
        stats.campaign_id,
        str(stats.impressions),
        str(stats.clicks),
        f"{stats.spend:.2f}",
        str(stats.conversions),
        "" if ctr is None else f"{ctr:.6f}",
        "" if cpa is None else f"{cpa:.2f}",
    ]
