"""Thin, real dataset loaders for the Data Science Skills Mastery Lab webapp.

Every function reads a real file from webapp/data/ into a pandas.DataFrame.
No np.random synthesis anywhere in this module.
"""
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=1)
def load_titanic() -> pd.DataFrame:
    """Real Titanic passenger manifest (seaborn-data mirror of the Kaggle dataset).

    891 rows x 15 cols. Real survival rate: 38.38%. `deck` is ~77% missing (genuine
    real-world data-cleaning talking point, not synthetic dirtiness).
    """
    return pd.read_csv(DATA_DIR / "titanic.csv")


@lru_cache(maxsize=1)
def load_house_prices() -> pd.DataFrame:
    """Real Ames Housing dataset (Dean De Cock's official source, tab-separated).

    2,930 rows x 82 cols. Kaggle's House Prices competition is built directly from
    this file. Real SalePrice mean: $180,796.06.
    """
    return pd.read_csv(DATA_DIR / "AmesHousing.txt", sep="\t")


@lru_cache(maxsize=1)
def load_fraud() -> pd.DataFrame:
    """Real ULB Credit Card Fraud dataset. 284,807 rows x 31 cols, ~102MB.

    Real fraud rate: 0.1727% (492 fraud / 284,807 transactions) -- the famous published
    number for this dataset. Loaded once and cached; do not reload per request.
    """
    return pd.read_csv(DATA_DIR / "creditcard.csv")


@lru_cache(maxsize=1)
def load_online_retail() -> pd.DataFrame:
    """Real UCI Online Retail transaction export. ~541,909 rows x 8 cols, ~24MB.

    Genuinely messy as shipped: ~25% missing CustomerID, real negative Quantity
    (returns), real cancelled invoices (InvoiceNo starting with "C"), real duplicate
    rows. Loaded once and cached; do not reload per request.
    """
    return pd.read_excel(DATA_DIR / "online_retail.xlsx")
