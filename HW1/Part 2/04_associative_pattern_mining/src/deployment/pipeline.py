"""
End-to-End CRISP-DM Pipeline Orchestrator for Associative Pattern Mining.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd

from config import ARTIFACTS_DIR
from src.data.loader import load_dataset
from src.data.preprocessor import clean_retail_data
from src.data.schema import CleanedDataset, EDAProfile
from src.deployment.exporter import (
    export_frequent_itemsets,
    export_markdown_report,
    export_pipeline_summary,
    export_rules,
)
from src.eda.profiler import profile_dataset
from src.evaluation.filter import categorize_rules, compute_composite_scores, filter_rules
from src.evaluation.redundancy import prune_redundant_rules
from src.mining.engine import mine_association_rules, mine_frequent_itemsets
from src.utils.logger import get_logger
from src.utils.timer import Timer

logger = get_logger("crisp_dm.pipeline")


class PipelineResult(dict):
    """Result container for complete CRISP-DM pipeline run, behaving as both dict and result object."""

    def __init__(
        self,
        summary_dict: Dict[str, Any],
        rules_df: pd.DataFrame,
        itemsets_df: pd.DataFrame,
        eda_profile: EDAProfile,
        cleaned_data: CleanedDataset,
        execution_time_seconds: float,
        output_dir: Path,
    ):
        super().__init__(summary_dict)
        self.summary_dict = summary_dict
        self.rules_df = rules_df
        self.itemsets_df = itemsets_df
        self.eda_profile = eda_profile
        self.cleaned_data = cleaned_data
        self.execution_time_seconds = execution_time_seconds
        self.output_dir = output_dir



class CRISPDMPipeline:
    """CRISP-DM 6-Phase Associative Pattern Mining Pipeline."""

    def __init__(
        self,
        dataset_name: str = "online_retail",
        algorithm: str = "fpgrowth",
        min_support: float = 0.01,
        min_confidence: float = 0.3,
        metric: str = "lift",
        min_metric_val: float = 1.2,
        max_len: int = 4,
        country: str = "all",
        engine: str = "auto",
        prune_redundant: bool = True,
        output_dir: Optional[Union[str, Path]] = None,
        force_synthetic: bool = False,
    ):
        self.dataset_name = dataset_name
        self.algorithm = algorithm
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.metric = metric
        self.min_metric_val = min_metric_val
        self.max_len = max_len
        self.country = country
        self.engine = engine
        self.prune_redundant = prune_redundant
        self.output_dir = Path(output_dir) if output_dir else ARTIFACTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.force_synthetic = force_synthetic

    def run(self) -> PipelineResult:
        """
        Execute the 6 phases of the CRISP-DM methodology.
        """
        total_timer = Timer("CRISP_DM_Pipeline")
        total_timer.start()

        logger.info("=================================================================")
        logger.info("  STARTING CRISP-DM ASSOCIATIVE PATTERN MINING PIPELINE")
        logger.info("=================================================================")

        # -------------------------------------------------------------
        # Phase 1: Business Understanding
        # -------------------------------------------------------------
        logger.info("[PHASE 1] Business Understanding: Formulating Objectives & Targets...")
        business_understanding = {
            "objective": "E-commerce market basket cross-sell discovery and catalog bundle optimization",
            "target_kpi": f"Lift >= {self.min_metric_val}, Confidence >= {self.min_confidence}, Zhang Metric > 0.0",
            "business_questions": [
                "Which product combinations drive highest joint purchase affinities?",
                "What complementary products should be recommended on checkout?",
                "Which product pairs exhibit strong symmetric cross-shopping behavior?",
            ],
        }

        # -------------------------------------------------------------
        # Phase 2: Data Understanding (Ingestion & EDA Profiling)
        # -------------------------------------------------------------
        logger.info(f"[PHASE 2] Data Understanding: Ingesting dataset '{self.dataset_name}'...")
        dataset = load_dataset(
            name_or_path=self.dataset_name,
            force_synthetic=self.force_synthetic,
        )

        logger.info("[PHASE 2] Data Understanding: Profiling raw dataset distributions & sparsity...")
        raw_df = dataset.raw_df
        eda_profile = profile_dataset(raw_df=raw_df, dataset_name=dataset.name)

        # -------------------------------------------------------------
        # Phase 3: Data Preparation
        # -------------------------------------------------------------
        logger.info("[PHASE 3] Data Preparation: Cleaning transactions & encoding boolean matrix...")
        cleaned_data = clean_retail_data(
            df=raw_df,
            drop_cancellations=True,
            min_basket_size=2,
            country=self.country,
        )

        # Update EDA profile with cleaned density metrics
        eda_profile.matrix_density_pct = cleaned_data.matrix_density_pct
        eda_profile.sparsity_pct = 100.0 - cleaned_data.matrix_density_pct

        # -------------------------------------------------------------
        # Phase 4: Modeling (Frequent Itemset Mining & Rule Extraction)
        # -------------------------------------------------------------
        logger.info(f"[PHASE 4] Modeling: Mining frequent patterns with {self.algorithm.upper()}...")
        itemsets_df, raw_rules_df = mine_association_rules(
            df_onehot=cleaned_data.onehot_df,
            min_support=self.min_support,
            min_confidence=self.min_confidence,
            metric=self.metric,
            min_metric_val=self.min_metric_val,
            max_len=self.max_len,
            algorithm=self.algorithm,
            engine=self.engine,
        )

        # Count itemsets by length
        itemsets_by_len: Dict[str, int] = {}
        if not itemsets_df.empty and "length" in itemsets_df.columns:
            for k_len, count in itemsets_df["length"].value_counts().items():
                itemsets_by_len[f"k={k_len}"] = int(count)

        # -------------------------------------------------------------
        # Phase 5: Evaluation
        # -------------------------------------------------------------
        logger.info("[PHASE 5] Evaluation: Scoring, categorizing, and pruning redundant rules...")
        evaluated_rules = compute_composite_scores(raw_rules_df)
        categorized_rules = categorize_rules(evaluated_rules)

        redundant_pruned_count = 0
        if self.prune_redundant:
            final_rules_df, redundant_pruned_count = prune_redundant_rules(
                categorized_rules, return_stats=True
            )
        else:
            final_rules_df = categorized_rules

        # Category breakdown
        cat_counts = {}
        if not final_rules_df.empty and "rule_category" in final_rules_df.columns:
            for cat_name, count in final_rules_df["rule_category"].value_counts().items():
                cat_counts[cat_name] = int(count)

        evaluation_stats = {
            "rules_after_threshold_filtering": len(raw_rules_df),
            "redundant_rules_pruned": redundant_pruned_count,
            "final_actionable_rules_count": len(final_rules_df),
            "rule_categories": cat_counts,
        }

        total_duration = total_timer.stop()
        logger.info(f"[PHASE 5] Evaluation completed: {len(final_rules_df)} actionable rules identified in {total_duration:.2f}s.")

        # -------------------------------------------------------------
        # Phase 6: Deployment (Artifact Generation)
        # -------------------------------------------------------------
        logger.info(f"[PHASE 6] Deployment: Writing artifacts to {self.output_dir}...")
        deployed_files = [
            str(self.output_dir / "pipeline_summary.json"),
            str(self.output_dir / "pipeline_report.md"),
            str(self.output_dir / "rules.csv"),
            str(self.output_dir / "rules.json"),
            str(self.output_dir / "frequent_itemsets.csv"),
        ]

        # Assemble summary dict conforming to interface contracts
        summary_dict = {
            "pipeline_metadata": {
                "run_timestamp": datetime.utcnow().isoformat() + "Z",
                "execution_time_seconds": round(total_duration, 4),
                "framework": "CRISP-DM",
                "dataset_name": dataset.name,
                "algorithm": self.algorithm,
                "engine": self.engine,
                "parameters": {
                    "min_support": self.min_support,
                    "min_confidence": self.min_confidence,
                    "primary_metric": self.metric,
                    "min_metric_val": self.min_metric_val,
                    "max_len": self.max_len,
                    "country": self.country,
                },
            },
            "crisp_dm_stages": {
                "business_understanding": business_understanding,
                "data_understanding": eda_profile.to_dict(),
                "data_preparation": cleaned_data.to_dict(),
                "modeling": {
                    "frequent_itemsets_total": len(itemsets_df),
                    "itemsets_by_length": itemsets_by_len,
                    "raw_rules_generated": len(raw_rules_df),
                },
                "evaluation": evaluation_stats,
                "deployment": {
                    "artifacts_generated": deployed_files,
                },
            },
            "top_rules": [
                {
                    "id": int(row.get("id", idx + 1)),
                    "antecedents": list(row["antecedents"]) if isinstance(row["antecedents"], (list, set, frozenset)) else [str(row["antecedents"])],
                    "consequents": list(row["consequents"]) if isinstance(row["consequents"], (list, set, frozenset)) else [str(row["consequents"])],
                    "support": round(float(row.get("support", 0.0)), 6),
                    "confidence": round(float(row.get("confidence", 0.0)), 6),
                    "lift": round(float(row.get("lift", 0.0)), 6),
                    "leverage": round(float(row.get("leverage", 0.0)), 6),
                    "conviction": round(float(row.get("conviction", 0.0)), 6),
                    "zhangs_metric": round(float(row.get("zhangs_metric", 0.0)), 6),
                    "kulczynski": round(float(row.get("kulczynski", 0.0)), 6),
                    "imbalance_ratio": round(float(row.get("imbalance_ratio", 0.0)), 6),
                    "cosine": round(float(row.get("cosine", 0.0)), 6),
                    "rule_category": str(row.get("rule_category", "General")),
                    "composite_score": round(float(row.get("composite_score", 0.0)), 4) if "composite_score" in row else None,
                }
                for idx, row in final_rules_df.head(20).iterrows()
            ],
        }

        # Export all artifacts
        export_pipeline_summary(summary_dict, self.output_dir / "pipeline_summary.json")
        export_rules(final_rules_df, self.output_dir / "rules.csv", self.output_dir / "rules.json")
        export_frequent_itemsets(itemsets_df, self.output_dir / "frequent_itemsets.csv")
        export_markdown_report(summary_dict, final_rules_df, self.output_dir / "pipeline_report.md")

        logger.info("=================================================================")
        logger.info("  CRISP-DM PIPELINE RUN COMPLETED SUCCESSFULLY (EXIT 0)")
        logger.info("=================================================================")

        return PipelineResult(
            summary_dict=summary_dict,
            rules_df=final_rules_df,
            itemsets_df=itemsets_df,
            eda_profile=eda_profile,
            cleaned_data=cleaned_data,
            execution_time_seconds=total_duration,
            output_dir=self.output_dir,
        )


def run_crisp_dm_pipeline(
    dataset: Optional[str] = None,
    dataset_name: Optional[str] = None,
    **kwargs,
) -> PipelineResult:
    """Helper functional interface for executing the CRISP-DM pipeline."""
    target_dataset = dataset_name or dataset or "online_retail"
    pipeline = CRISPDMPipeline(dataset_name=target_dataset, **kwargs)
    return pipeline.run()


