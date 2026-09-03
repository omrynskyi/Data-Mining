"""
Multi-dataset loader for Associative Pattern Mining.
Supports Online Retail, Groceries, Bread Basket Bakery, Synthetic Retail, and arbitrary CSV files.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Union
import pandas as pd

from config import RAW_DATA_DIR, SUPPORTED_DATASETS, SYNTHETIC_DATA_PATH
from data.generate_synthetic import generate_synthetic_retail
from src.data.schema import TransactionDataset
from src.utils.logger import get_logger

logger = get_logger("crisp_dm.loader")


def get_dataset_info() -> Dict[str, str]:
    """Return dictionary of supported dataset names and their default paths."""
    return {k: str(v) for k, v in SUPPORTED_DATASETS.items()}


def load_dataset(
    name_or_path: str = "online_retail",
    force_synthetic: bool = False,
    data_dir: Optional[Union[str, Path]] = None,
    num_synthetic_invoices: int = 2500,
) -> TransactionDataset:
    """
    Load a transaction dataset by name or filepath.

    Parameters:
    -----------
    name_or_path : str
        Predefined dataset key ('online_retail', 'groceries', 'bakery', 'synthetic')
        or a path to a CSV file.
    force_synthetic : bool
        If True, forces generation of synthetic data.
    data_dir : Optional[Union[str, Path]]
        Override root data directory.
    num_synthetic_invoices : int
        Number of invoices to synthesize if synthetic data is used.

    Returns:
    --------
    TransactionDataset
    """
    target_dir = Path(data_dir) if data_dir else RAW_DATA_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    dataset_key = str(name_or_path).lower().strip()
    source_file: Optional[Path] = None

    if force_synthetic or dataset_key == "synthetic":
        synth_path = target_dir / "synthetic_retail.csv"
        if not synth_path.exists() or force_synthetic:
            logger.info(f"Synthesizing {num_synthetic_invoices} retail transactions to {synth_path}...")
            df = generate_synthetic_retail(output_path=str(synth_path), num_invoices=num_synthetic_invoices)
        else:
            logger.info(f"Loading existing synthetic dataset from {synth_path}")
            df = pd.read_csv(synth_path)
        return TransactionDataset(
            name="synthetic_retail",
            source_path=str(synth_path),
            raw_df=df,
            total_records=len(df),
            loaded_at=datetime.utcnow().isoformat() + "Z",
        )

    # Check if name_or_path is an existing filesystem path
    custom_path = Path(name_or_path)
    if custom_path.is_file():
        source_file = custom_path
        dataset_name = custom_path.stem
    elif dataset_key in SUPPORTED_DATASETS:
        dataset_name = dataset_key
        # Check standard file extensions (.csv, .xlsx, .csv.gz)
        base_name = dataset_key
        candidates = [
            target_dir / f"{base_name}.csv",
            target_dir / f"{base_name}.xlsx",
            target_dir / f"{base_name}.csv.gz",
        ]
        for candidate in candidates:
            if candidate.exists():
                source_file = candidate
                break

    if source_file is None or not source_file.exists():
        # Fallback to synthetic dataset if raw Kaggle file is not present locally
        logger.warning(
            f"Dataset source '{name_or_path}' not found at {target_dir}. "
            f"Automatically generating deterministic synthetic retail transactions for offline execution."
        )
        synth_path = target_dir / "synthetic_retail.csv"
        df = generate_synthetic_retail(output_path=str(synth_path), num_invoices=num_synthetic_invoices)
        return TransactionDataset(
            name=f"{dataset_key}_synthetic_fallback",
            source_path=str(synth_path),
            raw_df=df,
            total_records=len(df),
            loaded_at=datetime.utcnow().isoformat() + "Z",
        )

    logger.info(f"Loading dataset from: {source_file}")
    if source_file.suffix in [".xlsx", ".xls"]:
        df = pd.read_excel(source_file)
    else:
        # CSV format (handles comma, semicolon, tab)
        try:
            df = pd.read_csv(source_file, encoding="utf-8", low_memory=False)
        except UnicodeDecodeError:
            df = pd.read_csv(source_file, encoding="latin1", low_memory=False)

    return TransactionDataset(
        name=dataset_name,
        source_path=str(source_file),
        raw_df=df,
        total_records=len(df),
        loaded_at=datetime.utcnow().isoformat() + "Z",
    )
