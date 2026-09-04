"""Ageroot Core: Safety-first dry-run comparison and update engine."""

from .comparison import (
    ResultClass,
    ComparisonResult,
    ThreeWayComparisonEngine,
    DeterministicNormalizer,
    ManagedRegionParser,
    SnapshotStore,
    SummaryReport,
)

__all__ = [
    "ResultClass",
    "ComparisonResult",
    "ThreeWayComparisonEngine",
    "DeterministicNormalizer",
    "ManagedRegionParser",
    "SnapshotStore",
    "SummaryReport",
]

