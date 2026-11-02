"""Streaming ad-performance aggregation."""

from .processing import CampaignStats, aggregate_csv, rank_top_cpa, rank_top_ctr

__all__ = [
    "CampaignStats",
    "aggregate_csv",
    "rank_top_cpa",
    "rank_top_ctr",
]
