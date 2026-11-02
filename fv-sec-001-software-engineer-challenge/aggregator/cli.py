from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .processing import (
    aggregate_csv,
    rank_top_cpa,
    rank_top_ctr,
    write_campaign_csv,
)
from .resources import peak_rss_bytes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Aggregate advertising performance CSV data by campaign."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to the source CSV file",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Directory where top10_ctr.csv and top10_cpa.csv will be written",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Number of campaigns to include in each ranking (default: 10)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path: Path = args.input
    output_dir: Path = args.output
    top_n: int = args.top_n

    if top_n < 1:
        print("--top-n must be at least 1", file=sys.stderr)
        return 2
    if not input_path.is_file():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 2

    started = time.perf_counter()
    try:
        result = aggregate_csv(input_path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    top_ctr = rank_top_ctr(result.campaigns, n=top_n)
    top_cpa = rank_top_cpa(result.campaigns, n=top_n)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_campaign_csv(output_dir / "top10_ctr.csv", top_ctr)
    write_campaign_csv(output_dir / "top10_cpa.csv", top_cpa)

    elapsed = time.perf_counter() - started
    peak_bytes = peak_rss_bytes()
    print(f"Campaigns: {len(result.campaigns)}")
    print(f"Rows aggregated: {result.rows_read}")
    print(f"Rows skipped: {result.rows_skipped}")
    print(f"Wrote {output_dir / 'top10_ctr.csv'}")
    print(f"Wrote {output_dir / 'top10_cpa.csv'}")
    print(f"Elapsed: {elapsed:.2f}s")
    if peak_bytes is not None:
        print(f"Peak RSS: {peak_bytes / (1024 * 1024):.1f} MiB")
    return 0
