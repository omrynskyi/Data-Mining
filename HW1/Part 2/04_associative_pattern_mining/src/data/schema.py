"""
Data schemas, types, and data models for Associative Pattern Mining.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd


@dataclass
class TransactionDataset:
    """Represents a loaded transaction dataset."""
    name: str
    source_path: str
    raw_df: pd.DataFrame
    total_records: int
    loaded_at: str


@dataclass
class CleanedDataset:
    """Represents cleaned transactions ready for basket encoding."""
    cleaned_df: pd.DataFrame
    transactions_list: List[List[str]]
    onehot_df: pd.DataFrame
    raw_record_count: int
    cleaned_record_count: int
    unique_invoices: int
    unique_items: int
    single_item_baskets_dropped: int
    cancellations_dropped: int
    matrix_shape: Tuple[int, int]
    matrix_density_pct: float
    cleaning_steps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_record_count": self.raw_record_count,
            "cleaned_record_count": self.cleaned_record_count,
            "cleaned_transactions_count": self.unique_invoices,
            "cleaned_unique_items_count": self.unique_items,
            "unique_invoices": self.unique_invoices,
            "unique_items": self.unique_items,
            "single_item_baskets_dropped": self.single_item_baskets_dropped,
            "cancellations_dropped": self.cancellations_dropped,
            "matrix_shape": list(self.matrix_shape),
            "matrix_density_pct": round(self.matrix_density_pct, 4),
            "cleaning_steps_applied": self.cleaning_steps,
        }


@dataclass
class EDAProfile:
    """Exploratory Data Analysis metrics summary."""
    dataset_name: str
    raw_records_count: int
    unique_invoices: int
    unique_items: int
    unique_customers: int
    cancellation_rate_pct: float
    sparsity_pct: float
    matrix_density_pct: float
    basket_size_stats: Dict[str, float]
    basket_size_distribution: List[Dict[str, Any]]
    top_frequent_items: List[Dict[str, Any]]
    pareto_analysis: Dict[str, float]
    country_distribution: List[Dict[str, Any]]
    temporal_stats: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "raw_records_count": self.raw_records_count,
            "unique_invoices": self.unique_invoices,
            "unique_items": self.unique_items,
            "unique_customers": self.unique_customers,
            "cancellation_rate_pct": round(self.cancellation_rate_pct, 4),
            "sparsity_pct": round(self.sparsity_pct, 4),
            "matrix_density_pct": round(self.matrix_density_pct, 4),
            "basket_size_stats": self.basket_size_stats,
            "basket_size_distribution": self.basket_size_distribution,
            "top_5_frequent_items": self.top_frequent_items[:5],
            "top_frequent_items": self.top_frequent_items,
            "pareto_analysis": self.pareto_analysis,
            "country_distribution": self.country_distribution,
            "temporal_stats": self.temporal_stats,
        }


@dataclass
class RuleRecord:
    """Representation of a mined association rule."""
    id: int
    antecedents: List[str]
    consequents: List[str]
    support: float
    confidence: float
    lift: float
    leverage: float
    conviction: float
    zhangs_metric: float
    kulczynski: float
    imbalance_ratio: float
    cosine: float
    antecedent_support: Optional[float] = None
    consequent_support: Optional[float] = None
    rule_category: Optional[str] = None
    composite_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "antecedents": list(self.antecedents),
            "consequents": list(self.consequents),
            "support": round(float(self.support), 6),
            "confidence": round(float(self.confidence), 6),
            "lift": round(float(self.lift), 6),
            "leverage": round(float(self.leverage), 6),
            "conviction": round(float(self.conviction), 6),
            "zhangs_metric": round(float(self.zhangs_metric), 6),
            "kulczynski": round(float(self.kulczynski), 6),
            "imbalance_ratio": round(float(self.imbalance_ratio), 6),
            "cosine": round(float(self.cosine), 6),
        }
        if self.antecedent_support is not None:
            d["antecedent_support"] = round(float(self.antecedent_support), 6)
        if self.consequent_support is not None:
            d["consequent_support"] = round(float(self.consequent_support), 6)
        if self.rule_category is not None:
            d["rule_category"] = self.rule_category
        if self.composite_score is not None:
            d["composite_score"] = round(float(self.composite_score), 6)
        return d
