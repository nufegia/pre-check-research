"""Central thresholds for deterministic PCR audit rules."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SimilarityConfig:
    row_threshold_high: float = 0.95
    row_threshold_medium: float = 0.90
    row_threshold_low: float = 0.85
    col_threshold_high: float = 0.95
    col_threshold_medium: float = 0.90
    min_comparable_fields: int = 3
    min_comparable_rows: int = 5
    max_row_pairs: int = 10_000
    row_bucket_token_size: int = 4
    numeric_relative_tolerance: float = 0.01


@dataclass(frozen=True)
class LinearTransformConfig:
    min_rows: int = 10
    r2_threshold_high: float = 0.999
    r2_threshold_medium: float = 0.995
    fixed_diff_slope_tolerance: float = 0.01


@dataclass(frozen=True)
class CorrelationConfig:
    min_rows: int = 10
    r_threshold_high: float = 0.98
    r_threshold_medium: float = 0.95
    table_ratio_threshold_high: float = 0.50
    table_ratio_threshold_medium: float = 0.30
    table_median_r_threshold: float = 0.80
    max_column_pairs: int = 500


@dataclass(frozen=True)
class CategoricalConfig:
    rare_ratio: float = 0.05
    rare_count: int = 2
    min_rows: int = 20
    min_categories: int = 3
    max_categories: int = 20


@dataclass(frozen=True)
class OrdinalConfig:
    min_rows: int = 20
    extreme_ratio_high: float = 0.80
    extreme_ratio_medium: float = 0.60
    max_unique_values: int = 15
    keywords: tuple[str, ...] = (
        "评分",
        "等级",
        "分级",
        "scale",
        "score",
        "grade",
        "level",
        "stage",
        "likert",
    )


@dataclass(frozen=True)
class ColumnRelationshipConfig:
    max_pairs: int = 500
    whitelist_pairs: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class PcrAuditConfig:
    similarity: SimilarityConfig = field(default_factory=SimilarityConfig)
    linear_transform: LinearTransformConfig = field(default_factory=LinearTransformConfig)
    correlation: CorrelationConfig = field(default_factory=CorrelationConfig)
    categorical: CategoricalConfig = field(default_factory=CategoricalConfig)
    ordinal: OrdinalConfig = field(default_factory=OrdinalConfig)
    column_relationship: ColumnRelationshipConfig = field(default_factory=ColumnRelationshipConfig)


DEFAULT_CONFIG = PcrAuditConfig()
