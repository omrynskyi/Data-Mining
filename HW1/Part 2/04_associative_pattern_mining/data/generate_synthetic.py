"""
Deterministic Realistic Retail Transaction Generator.
Seeds realistic retail baskets with planted affinities, noise items,
anomalies, and cancellations for robust offline testing and benchmark verification.
"""

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np
import pandas as pd

# Planted affinity item clusters (Item Name, StockCode, Base Unit Price)
AFFINITY_CLUSTERS = [
    # Cluster 1: Breakfast Essentials
    [
        ("ORGANIC WHOLE MILK", "22423", 3.49),
        ("WHOLE WHEAT BREAD", "22424", 2.99),
        ("SWEET CREAM BUTTER", "22425", 4.25),
        ("STRAWBERRY PRESERVES", "22426", 3.89),
        ("ORGANIC EGGS DOZEN", "22427", 4.99),
    ],
    # Cluster 2: Coffee & Tea Break
    [
        ("COLOMBIAN ROAST COFFEE", "85123A", 8.99),
        ("PURE CANE SUGAR", "85123B", 2.49),
        ("DARK CHOCOLATE BAR 85%", "85123C", 3.50),
        ("FRENCH VANILLA SYRUP", "85123D", 5.99),
        ("CERAMIC COFFEE MUG", "85123E", 6.50),
    ],
    # Cluster 3: Gourmet Italian Dinner
    [
        ("ITALIAN EXTRA VIRGIN OLIVE OIL", "21733", 12.99),
        ("ARTISAN PASTA PENNE", "21734", 3.29),
        ("AGED PARMESAN REGGIANO", "21735", 7.89),
        ("ORGANIC TOMATO BASIL SAUCE", "21736", 4.49),
        ("GARLIC HERB BREADSTICKS", "21737", 2.99),
    ],
    # Cluster 4: Bakery & Pastry Selection
    [
        ("CROISSANT ALL BUTTER", "20725", 2.25),
        ("PAIN AU CHOCOLAT", "20726", 2.50),
        ("ALMOND DANISH", "20727", 2.75),
        ("CAPPUCCINO CUP & SAUCER", "20728", 8.50),
        ("BLUEBERRY SCONE", "20729", 2.40),
    ],
    # Cluster 5: Tech & Desk Workspace
    [
        ("WIRELESS ERGONOMIC MOUSE", "71053", 29.99),
        ("MECHANICAL KEYBOARD", "71054", 69.99),
        ("USB-C MULTIPORT ADAPTER", "71055", 24.99),
        ("LARGE DESK PAD BLACK", "71056", 15.99),
        ("MONITOR LIGHT BAR", "71057", 39.99),
    ],
    # Cluster 6: Garden & Home Planting
    [
        ("CERAMIC PLANT POT WHITE", "84879", 9.99),
        ("WATERING CAN GREEN 2L", "84880", 11.50),
        ("ORGANIC POTTING SOIL 10L", "84881", 6.99),
        ("GARDENING GLOVES PAIR", "84882", 4.99),
        ("LED GROW LIGHT BULB", "84883", 14.99),
    ],
    # Cluster 7: Vintage Home Fragrance & Decor
    [
        ("WHITE HANGING HEART T-LIGHT HOLDER", "85099B", 2.55),
        ("REGENCY CAKESTAND 3 TIER", "22423", 12.75),
        ("SET OF 3 CAKE TINS PANTRY", "22720", 4.95),
        ("HEART OF WICKER SMALL", "22960", 1.65),
        ("HEART OF WICKER LARGE", "22961", 2.95),
    ],
]

# Background noise items (infrequent or independent items)
NOISE_ITEMS = [
    ("VINTAGE SNAP CARDS", "21212", 0.85),
    ("MINI PAINT SET 9 COLOURS", "21213", 1.25),
    ("RECIPE BOX PANTRY DESIGN", "21214", 7.95),
    ("WOODEN PICTURE FRAME", "21215", 5.50),
    ("EMERGENCY FIRST AID TIN", "21216", 3.75),
    ("PACK OF 20 NAPKINS", "21217", 1.45),
    ("SCENTED CANDLE LAVENDER", "21218", 4.20),
    ("TRAVEL SEWING KIT", "21219", 2.10),
    ("BICYCLE PUNCTURE REPAIR KIT", "21220", 3.00),
    ("RETRO SPOT TEA TOWEL", "21221", 2.50),
    ("RETRO SPOT APRON", "21222", 6.95),
    ("SET OF 6 SPICE JARS", "21223", 9.95),
    ("GLASS STORAGE JAR SMALL", "21224", 2.25),
    ("GLASS STORAGE JAR LARGE", "21225", 3.95),
    ("CHILLI LIGHTS STRING", "21226", 8.50),
    ("VINTAGE UNION JACK CUSHION", "21227", 14.95),
    ("WALL CLOCK RETRO RED", "21228", 18.50),
    ("HAND WARMER BIRD DESIGN", "21229", 1.95),
    ("BATHROOM SCALE VINTAGE", "21230", 22.00),
    ("FELTCRAFT DOLL ROSIE", "21231", 2.95),
]

# Administrative items to simulate realistic raw data anomalies
ADMIN_ITEMS = [
    ("POSTAGE", "POST", 18.00),
    ("MANUAL", "M", 2.50),
    ("BANK CHARGES", "BANK CHARGES", 15.00),
    ("Discount", "D", -10.00),
]

COUNTRIES = [
    ("United Kingdom", 0.85),
    ("Germany", 0.04),
    ("France", 0.04),
    ("EIRE", 0.02),
    ("Spain", 0.02),
    ("Netherlands", 0.015),
    ("Belgium", 0.01),
    ("Switzerland", 0.005),
]


def generate_synthetic_retail(
    output_path: Optional[str] = None,
    num_invoices: int = 2500,
    seed: int = 42,
    cancellation_rate: float = 0.03,
    anomaly_rate: float = 0.015,
) -> pd.DataFrame:
    """
    Generate deterministic synthetic retail transactions with planted market basket affinities.

    Parameters:
    -----------
    output_path : Optional[str]
        File path to save CSV output. If None, returns DataFrame only.
    num_invoices : int
        Number of distinct transactions/invoices to generate.
    seed : int
        Random seed for full reproducibility.
    cancellation_rate : float
        Proportion of invoices that represent cancellations/returns ('C' prefix).
    anomaly_rate : float
        Proportion of anomalous / administrative records (POST, null descriptions, etc.).

    Returns:
    --------
    pd.DataFrame with schema matching UCI Online Retail dataset.
    """
    rng = random.Random(seed)
    np_rng = np.random.RandomState(seed)

    country_names = [c[0] for c in COUNTRIES]
    country_weights = [c[1] for c in COUNTRIES]

    start_date = datetime(2025, 1, 10, 8, 30, 0)
    customer_ids = list(range(12340, 18280))

    rows = []
    invoice_counter = 536365

    for inv_idx in range(num_invoices):
        is_cancellation = (rng.random() < cancellation_rate)
        inv_number_base = invoice_counter + inv_idx
        invoice_no = f"C{inv_number_base}" if is_cancellation else str(inv_number_base)

        # Country & Customer
        country = rng.choices(country_names, weights=country_weights, k=1)[0]
        # ~20% guest checkouts with null CustomerID
        customer_id = None if (rng.random() < 0.20) else rng.choice(customer_ids)

        # Invoice Date (spread across 365 days, realistic shopping hours 8am-20pm)
        days_offset = rng.randint(0, 360)
        hour = rng.randint(8, 20)
        minute = rng.randint(0, 59)
        second = rng.randint(0, 59)
        invoice_date = start_date + timedelta(days=days_offset, hours=hour, minutes=minute, seconds=second)
        date_str = invoice_date.strftime("%Y-%m-%d %H:%M:%S")

        # Determine Basket Contents
        basket_items: List[Tuple[str, str, float]] = []

        # 1. Decide which affinity cluster(s) to sample
        num_clusters = rng.choices([1, 2, 3], weights=[0.75, 0.20, 0.05], k=1)[0]
        chosen_clusters = rng.sample(AFFINITY_CLUSTERS, k=min(num_clusters, len(AFFINITY_CLUSTERS)))

        for cluster in chosen_clusters:
            # Pick a subset of items from this cluster (high co-occurrence probability)
            k_items = rng.choices([2, 3, 4, 5], weights=[0.40, 0.35, 0.18, 0.07], k=1)[0]
            k_items = min(k_items, len(cluster))
            selected_cluster_items = rng.sample(cluster, k=k_items)
            basket_items.extend(selected_cluster_items)

        # 2. Add some random noise items
        if rng.random() < 0.40:
            num_noise = rng.choices([1, 2, 3], weights=[0.7, 0.2, 0.1], k=1)[0]
            basket_items.extend(rng.sample(NOISE_ITEMS, k=num_noise))

        # 3. Handle single-item basket edge case (~8% of baskets naturally)
        if rng.random() < 0.08:
            basket_items = [rng.choice(NOISE_ITEMS)]

        # 4. Add occasional administrative record
        if rng.random() < anomaly_rate:
            basket_items.append(rng.choice(ADMIN_ITEMS))

        # Deduplicate items in the same basket
        unique_basket = {}
        for desc, code, price in basket_items:
            if desc not in unique_basket:
                unique_basket[desc] = (code, price)

        # Generate transaction rows
        for desc, (code, price) in unique_basket.items():
            if is_cancellation:
                quantity = -rng.randint(1, 12)
            else:
                quantity = rng.choices([1, 2, 3, 4, 6, 12, 24], weights=[0.35, 0.25, 0.15, 0.10, 0.10, 0.03, 0.02], k=1)[0]

            # Price variation (small noise around base price)
            unit_price = max(0.10, round(price * (1.0 + rng.uniform(-0.05, 0.05)), 2)) if price > 0 else price

            # Rare data anomalies
            final_desc = desc
            if rng.random() < 0.003:
                final_desc = None  # Missing description anomaly
            elif rng.random() < 0.003:
                final_desc = f"  {desc}   "  # Whitespace padding

            if rng.random() < 0.001:
                unit_price = 0.0  # Zero unit price anomaly

            rows.append({
                "InvoiceNo": invoice_no,
                "StockCode": code,
                "Description": final_desc,
                "Quantity": quantity,
                "InvoiceDate": date_str,
                "UnitPrice": unit_price,
                "CustomerID": float(customer_id) if customer_id is not None else np.nan,
                "Country": country,
            })

    df = pd.DataFrame(rows)

    if output_path:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_file, index=False)

    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic retail transaction dataset.")
    parser.add_argument("--output", type=str, default="data/raw/synthetic_retail.csv", help="Output CSV path")
    parser.add_argument("--num-invoices", type=int, default=2500, help="Number of invoices/baskets")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    args = parser.parse_args()

    print(f"[+] Generating synthetic dataset with {args.num_invoices} invoices (seed={args.seed})...")
    generated_df = generate_synthetic_retail(
        output_path=args.output,
        num_invoices=args.num_invoices,
        seed=args.seed,
    )
    print(f"[✓] Generated {len(generated_df)} transaction rows across {generated_df['InvoiceNo'].nunique()} invoices.")
    print(f"[✓] Saved to: {args.output}")
