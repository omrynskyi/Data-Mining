"""
Unit and Integration Tests for DataLoader and Data Ingestion Module.
"""

from pathlib import Path
from unittest.mock import patch
import pandas as pd
import pytest

from src.config import CANONICAL_COLUMNS
from src.data_loader import DataLoader, load_data


class TestDataLoader:
    """Test suite for DataLoader schema validation, ingestion, and offline fallback."""

    def test_load_local_dataset(self, tmp_path: Path):
        """Verifies DataLoader successfully ingests valid local CSV data."""
        loader = DataLoader()
        df = loader.load_raw_data()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 200
        assert list(df.columns) == CANONICAL_COLUMNS

    def test_embedded_fallback_when_file_missing(self, tmp_path: Path):
        """Verifies DataLoader falls back to embedded 200 records when file is absent and network fails."""
        non_existent_path = tmp_path / "subdir" / "Mall_Customers.csv"
        loader = DataLoader(data_path=non_existent_path)
        loader.is_custom_path = False  # Simulate default path behavior on new machine

        with patch("urllib.request.urlopen", side_effect=Exception("Network offline")):
            df = loader.load_raw_data(auto_download=True)

        assert len(df) == 200
        assert non_existent_path.exists()
        assert set(df["gender"].unique()) == {"Male", "Female"}

    def test_schema_validation_and_cleaning(self):
        """Verifies column alias renaming, case normalization, and type casting."""
        raw_mock = pd.DataFrame({
            "CustomerID": ["1", "2", "3"],
            "Genre": ["male", "FEMALE", "Female"],
            "Age": [19, 21, 20],
            "Annual Income (k$)": [15, 15, 16],
            "Spending Score (1-100)": [39, 81, 6],
        })
        loader = DataLoader()
        cleaned = loader.validate_and_clean(raw_mock)

        assert list(cleaned.columns) == CANONICAL_COLUMNS
        assert cleaned["gender"].tolist() == ["Male", "Female", "Female"]
        assert cleaned["customer_id"].tolist() == [1, 2, 3]
        assert cleaned["annual_income"].tolist() == [15.0, 15.0, 16.0]

    def test_invalid_schema_missing_columns_raises(self):
        """Verifies ValueError when required canonical columns are absent."""
        corrupt_df = pd.DataFrame({
            "CustomerID": [1, 2],
            "Age": [20, 30],
        })
        loader = DataLoader()
        with pytest.raises(ValueError, match="missing required canonical columns"):
            loader.validate_and_clean(corrupt_df)

    def test_invalid_schema_null_values_raises(self):
        """Verifies ValueError when unexpected NaN / Null values are present."""
        null_df = pd.DataFrame({
            "CustomerID": [1, 2],
            "Genre": ["Male", None],
            "Age": [25, 30],
            "Annual Income (k$)": [50, 60],
            "Spending Score (1-100)": [50, 60],
        })
        loader = DataLoader()
        with pytest.raises(ValueError, match="contains null values"):
            loader.validate_and_clean(null_df)

    def test_invalid_ranges_raise(self):
        """Verifies domain constraints: age bounds, negative income, spending score bounds."""
        loader = DataLoader()

        # Negative income
        bad_inc = pd.DataFrame({
            "CustomerID": [1], "Genre": ["Male"], "Age": [25],
            "Annual Income (k$)": [-10], "Spending Score (1-100)": [50],
        })
        with pytest.raises(ValueError, match="Annual income cannot be negative"):
            loader.validate_and_clean(bad_inc)

        # Spending score out of range
        bad_spd = pd.DataFrame({
            "CustomerID": [1], "Genre": ["Male"], "Age": [25],
            "Annual Income (k$)": [50], "Spending Score (1-100)": [150],
        })
        with pytest.raises(ValueError, match="Spending score must be bounded"):
            loader.validate_and_clean(bad_spd)

        # Unrecognized gender
        bad_gen = pd.DataFrame({
            "CustomerID": [1], "Genre": ["Alien"], "Age": [25],
            "Annual Income (k$)": [50], "Spending Score (1-100)": [50],
        })
        with pytest.raises(ValueError, match="unrecognized categories"):
            loader.validate_and_clean(bad_gen)

    def test_custom_file_not_found_raises(self, tmp_path: Path):
        """Verifies FileNotFoundError is raised if a user-specified custom path does not exist."""
        custom_missing = tmp_path / "custom_data_does_not_exist.csv"
        loader = DataLoader(data_path=custom_missing)
        with pytest.raises(FileNotFoundError):
            loader.load_raw_data()

    def test_load_data_convenience_function(self):
        """Verifies top-level load_data() function operates properly."""
        df = load_data()
        assert len(df) == 200
        assert "annual_income" in df.columns
