"""
Data Cleaning, Transformation, and One-Hot Transaction Encoding.
"""

from typing import Any, Dict, List, Optional, Set, Tuple, Union
import numpy as np
import pandas as pd

from config import ADMINISTRATIVE_STOCK_CODES
from src.data.schema import CleanedDataset
from src.utils.logger import get_logger

logger = get_logger("crisp_dm.preprocessor")


def normalize_item_description(desc: Any) -> Optional[str]:
    """Clean and normalize raw product description strings."""
    if desc is None or pd.isna(desc):
        return None
    s = str(desc).strip().upper()
    # Replace multiple whitespaces with single space
    s = " ".join(s.split())
    if not s or len(s) < 2:
        return None
    return s


def filter_returns_and_cancellations(df: pd.DataFrame, invoice_col: str, qty_col: Optional[str] = None) -> Tuple[pd.DataFrame, int]:
    """Filter out invoice cancellations ('C' prefix) and negative/zero quantities."""
    initial_count = len(df)

    # Filter invoice numbers starting with 'C'
    is_cancellation = df[invoice_col].astype(str).str.upper().str.startswith("C")

    # Filter negative quantities if quantity column exists
    if qty_col and qty_col in df.columns:
        is_negative_qty = pd.to_numeric(df[qty_col], errors="coerce").fillna(0) <= 0
        drop_mask = is_cancellation | is_negative_qty
    else:
        drop_mask = is_cancellation

    cleaned_df = df[~drop_mask].copy()
    dropped_count = initial_count - len(cleaned_df)
    return cleaned_df, dropped_count


def clean_retail_data(
    df: pd.DataFrame,
    drop_cancellations: bool = True,
    min_unit_price: float = 0.001,
    min_basket_size: int = 2,
    country: Optional[str] = None,
) -> CleanedDataset:
    """
    Apply full CRISP-DM Data Preparation cleaning pipeline to transaction records.

    Parameters:
    -----------
    df : pd.DataFrame
        Raw dataset DataFrame.
    drop_cancellations : bool
        Whether to drop returns/cancellations.
    min_unit_price : float
        Minimum valid unit price threshold.
    min_basket_size : int
        Minimum distinct items per basket to retain.
    country : Optional[str]
        Filter transactions for a specific country ('all' for no filter).

    Returns:
    --------
    CleanedDataset
    """
    raw_record_count = len(df)
    cleaning_steps: List[str] = []
    df_clean = df.copy()

    # Detect dataset column mapping
    cols = {c.lower(): c for c in df_clean.columns}

    # Invoice / Transaction ID Column
    invoice_col = cols.get("invoiceno") or cols.get("invoice_no") or cols.get("transaction") or cols.get("order_id") or cols.get("member_number")
    # Item Description Column
    item_col = cols.get("description") or cols.get("itemdescription") or cols.get("item") or cols.get("product_name")
    # Stock Code Column
    code_col = cols.get("stockcode") or cols.get("item_code")
    # Quantity Column
    qty_col = cols.get("quantity") or cols.get("qty")
    # Unit Price Column
    price_col = cols.get("unitprice") or cols.get("price") or cols.get("item_price")
    # Country Column
    country_col = cols.get("country")

    if not invoice_col or not item_col:
        # Check if dataset is formatted as Groceries (Member_number + Date)
        if "member_number" in cols and "date" in cols and item_col:
            df_clean["__transaction_id__"] = df_clean[cols["member_number"]].astype(str) + "_" + df_clean[cols["date"]].astype(str)
            invoice_col = "__transaction_id__"
        else:
            raise ValueError(
                f"Unable to automatically identify transaction ID and Item Description columns in DataFrame. "
                f"Columns present: {list(df.columns)}"
            )

    cancellations_dropped = 0
    # Step 1: Filter Cancellations and Returns
    if drop_cancellations and invoice_col:
        df_clean, cancellations_dropped = filter_returns_and_cancellations(df_clean, invoice_col, qty_col)
        cleaning_steps.append("filter_negative_quantities_and_cancellations")

    # Step 2: Strip and Normalize Descriptions, Drop Nulls
    df_clean[item_col] = df_clean[item_col].apply(normalize_item_description)
    before_drop_null = len(df_clean)
    df_clean = df_clean.dropna(subset=[item_col])
    cleaning_steps.append("strip_whitespace_and_normalize_descriptions")
    cleaning_steps.append("drop_null_descriptions")

    # Step 3: Filter Administrative Codes
    if code_col and code_col in df_clean.columns:
        admin_mask = df_clean[code_col].astype(str).str.strip().str.upper().isin(ADMINISTRATIVE_STOCK_CODES)
        df_clean = df_clean[~admin_mask]
        cleaning_steps.append("filter_administrative_stock_codes")

    # Step 4: Filter Zero or Negative Unit Prices
    if price_col and price_col in df_clean.columns:
        price_series = pd.to_numeric(df_clean[price_col], errors="coerce").fillna(0)
        df_clean = df_clean[price_series >= min_unit_price]
        cleaning_steps.append("filter_zero_or_negative_unit_prices")

    # Step 5: Country Filter
    if country and country.lower() != "all" and country_col and country_col in df_clean.columns:
        df_clean = df_clean[df_clean[country_col].astype(str).str.lower() == country.lower()]
        cleaning_steps.append(f"filter_country_{country.lower()}")

    # Step 6: Extract Grouped Transactions List
    grouped = df_clean.groupby(invoice_col)[item_col].unique()

    # Step 7: Filter Single-Item Baskets
    single_item_baskets_dropped = 0
    valid_baskets = []
    valid_invoices = []
    for inv_id, items in grouped.items():
        # Keep items with clean unique strings
        items_list = [str(it) for it in items if str(it).strip()]
        if len(items_list) >= min_basket_size:
            valid_baskets.append(items_list)
            valid_invoices.append(inv_id)
        else:
            single_item_baskets_dropped += 1

    cleaning_steps.append("filter_single_item_baskets")

    # Filter df_clean to only rows in valid_invoices
    df_clean = df_clean[df_clean[invoice_col].isin(set(valid_invoices))]

    # Step 8: Encode One-Hot Matrix
    onehot_df = encode_transactions(valid_baskets)

    matrix_rows, matrix_cols = onehot_df.shape
    total_cells = matrix_rows * matrix_cols
    ones_count = int(onehot_df.values.sum()) if total_cells > 0 else 0
    matrix_density_pct = (ones_count / total_cells * 100.0) if total_cells > 0 else 0.0

    return CleanedDataset(
        cleaned_df=df_clean,
        transactions_list=valid_baskets,
        onehot_df=onehot_df,
        raw_record_count=raw_record_count,
        cleaned_record_count=len(df_clean),
        unique_invoices=len(valid_baskets),
        unique_items=matrix_cols,
        single_item_baskets_dropped=single_item_baskets_dropped,
        cancellations_dropped=cancellations_dropped,
        matrix_shape=(matrix_rows, matrix_cols),
        matrix_density_pct=matrix_density_pct,
        cleaning_steps=cleaning_steps,
    )


def extract_transactions_list(df: pd.DataFrame, invoice_col: str, item_col: str) -> List[List[str]]:
    """Group items by transaction identifier into a list of baskets."""
    grouped = df.groupby(invoice_col)[item_col].unique()
    return [list(items) for items in grouped if len(items) > 0]


def encode_transactions(transactions_list: List[List[str]], sparse: bool = False) -> pd.DataFrame:
    """
    Encode a list of transaction item lists into a boolean one-hot DataFrame.

    Parameters:
    -----------
    transactions_list : List[List[str]]
        List of baskets (e.g. [['MILK', 'BREAD'], ['BREAD', 'BUTTER']]).
    sparse : bool
        If True, uses sparse boolean dtype for memory optimization.

    Returns:
    --------
    pd.DataFrame with boolean (True/False) values.
    """
    if not transactions_list:
        return pd.DataFrame()

    try:
        from mlxtend.preprocessing import TransactionEncoder
        te = TransactionEncoder()
        te_ary = te.fit(transactions_list).transform(transactions_list, sparse=sparse)
        if sparse:
            onehot_df = pd.DataFrame.sparse.from_spmatrix(te_ary, columns=te.columns_)
        else:
            onehot_df = pd.DataFrame(te_ary, columns=te.columns_)
        return onehot_df
    except ImportError:
        # Fallback pure-Python / NumPy encoding
        all_items = sorted({item for basket in transactions_list for item in basket})
        item_to_idx = {item: i for i, item in enumerate(all_items)}
        num_baskets = len(transactions_list)
        num_items = len(all_items)

        matrix = np.zeros((num_baskets, num_items), dtype=bool)
        for row_idx, basket in enumerate(transactions_list):
            for item in basket:
                col_idx = item_to_idx.get(item)
                if col_idx is not None:
                    matrix[row_idx, col_idx] = True

        return pd.DataFrame(matrix, columns=all_items)
