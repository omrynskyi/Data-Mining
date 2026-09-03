"""
tests/unit/test_data_loader.py
Unit & Boundary Tests for Multi-Dataset Loader and Transaction Ingestion (Feature F1).
"""

from pathlib import Path
import pytest
import pandas as pd

from src.data.loader import get_dataset_info, load_dataset


def test_get_dataset_info():
    """Verify registry of supported dataset aliases."""
    info = get_dataset_info()
    assert "online_retail" in info
    assert "groceries" in info
    assert "synthetic" in info


def test_load_synthetic_dataset(tmp_path):
    """Verify loading synthetic dataset generates TransactionDataset with valid raw_df."""
    dataset = load_dataset("synthetic", force_synthetic=True, data_dir=tmp_path, num_synthetic_invoices=100)
    assert dataset.total_records > 0
    assert not dataset.raw_df.empty
    assert "InvoiceNo" in dataset.raw_df.columns
    assert "Description" in dataset.raw_df.columns
    assert dataset.name == "synthetic_retail"


def test_load_custom_csv(tmp_path):
    """Verify loading a custom CSV file from filesystem."""
    csv_file = tmp_path / "custom_test.csv"
    csv_file.write_text("InvoiceNo,Description,Quantity\n101,ITEM_A,1\n101,ITEM_B,2\n")
    dataset = load_dataset(str(csv_file))
    assert dataset.total_records == 2
    assert dataset.name == "custom_test"


def test_load_single_transaction_csv(tmp_path):
    """Verify loading CSV with single transaction."""
    csv_file = tmp_path / "single_tx.csv"
    csv_file.write_text("InvoiceNo,Description,Quantity\n536365,BREAD,1\n")
    dataset = load_dataset(str(csv_file))
    assert dataset.total_records == 1
    assert dataset.raw_df.iloc[0]["Description"] == "BREAD"


def test_load_empty_csv_boundary(tmp_path):
    """Verify loading an empty CSV file."""
    csv_file = tmp_path / "empty_file.csv"
    csv_file.write_text("InvoiceNo,Description,Quantity\n")
    dataset = load_dataset(str(csv_file))
    assert dataset.total_records == 0
    assert dataset.raw_df.empty
