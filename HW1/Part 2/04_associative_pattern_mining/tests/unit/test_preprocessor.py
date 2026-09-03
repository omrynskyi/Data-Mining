"""
Unit tests for Data Preprocessing and One-Hot Encoding.
"""

import pandas as pd
import pytest

from src.data.preprocessor import clean_retail_data, encode_transactions, filter_returns_and_cancellations


def test_filter_returns_and_cancellations():
    df = pd.DataFrame({
        "InvoiceNo": ["536365", "C536366", "536367", "c536368"],
        "Quantity": [6, -1, 0, 5],
        "Description": ["A", "B", "C", "D"],
    })
    cleaned, dropped = filter_returns_and_cancellations(df, "InvoiceNo", "Quantity")
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["InvoiceNo"] == "536365"
    assert dropped == 3


def test_clean_retail_data(sample_raw_retail_df):
    """Test full cleaning pipeline on raw retail DataFrame."""
    cleaned = clean_retail_data(sample_raw_retail_df, min_basket_size=2)
    assert cleaned.unique_invoices > 0
    assert cleaned.unique_items > 0
    assert not cleaned.onehot_df.empty
    assert cleaned.matrix_density_pct > 0.0
    assert "filter_single_item_baskets" in cleaned.cleaning_steps


def test_encode_transactions():
    baskets = [["A", "B"], ["B", "C"], ["A", "B", "C"]]
    encoded = encode_transactions(baskets)
    assert encoded.shape == (3, 3)
    assert list(encoded.columns) == ["A", "B", "C"]
    assert encoded.loc[0, "A"] == True
    assert encoded.loc[0, "C"] == False
