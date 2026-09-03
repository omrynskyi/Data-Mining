"""
Configuration constants and defaults for the CRISP-DM Customer Segmentation Pipeline.
"""

from pathlib import Path
from typing import Any, Dict, List

# Filesystem Paths
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw"
PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
DEFAULT_RAW_DATA_PATH: Path = RAW_DATA_DIR / "Mall_Customers.csv"

ARTIFACTS_DIR: Path = PROJECT_ROOT / "artifacts"
MODELS_DIR: Path = ARTIFACTS_DIR / "models"
DASHBOARD_DATA_DIR: Path = PROJECT_ROOT / "dashboard" / "public" / "data"

REMOTE_DATASET_URL: str = (
    "https://raw.githubusercontent.com/sharmaroshan/Clustering-of-Mall-Customers/master/Mall_Customers.csv"
)

# Schema & Column Aliases
RAW_COLUMN_ALIASES: Dict[str, str] = {
    "CustomerID": "customer_id",
    "customerid": "customer_id",
    "customer_id": "customer_id",
    "Genre": "gender",
    "genre": "gender",
    "Gender": "gender",
    "gender": "gender",
    "Age": "age",
    "age": "age",
    "Annual Income (k$)": "annual_income",
    "annual income (k$)": "annual_income",
    "annual_income": "annual_income",
    "Annual_Income_k": "annual_income",
    "Annual Income": "annual_income",
    "Spending Score (1-100)": "spending_score",
    "spending score (1-100)": "spending_score",
    "spending_score": "spending_score",
    "Spending_Score": "spending_score",
    "Spending Score": "spending_score",
}

CANONICAL_COLUMNS: List[str] = [
    "customer_id",
    "gender",
    "age",
    "annual_income",
    "spending_score",
]

# Feature Set Presets
FEATURE_SETS: Dict[str, List[str]] = {
    "2d": ["annual_income", "spending_score"],
    "3d": ["age", "annual_income", "spending_score"],
    "all": ["gender", "age", "annual_income", "spending_score"],
    "4d": ["gender", "age", "annual_income", "spending_score"],
}

# Persona Profiles and Anchor Definitions
CANONICAL_PERSONAS: Dict[str, Dict[str, Any]] = {
    "target": {
        "key": "target",
        "title": "The Affluent Spenders",
        "name": "Target / Affluent Spenders",
        "persona": "Whales / Target",
        "color": "#10B981",
        "priority_tier": "Tier 1 (High ROI)",
        "spending_power": "Very High",
        "anchor": (86.5, 82.1),
        "key_traits": ["High Purchasing Power", "Status Conscious", "Brand Loyal", "Impulse Luxury Buyers"],
        "strategies": ["VIP lounge access", "Personal concierge", "Private luxury previews", "Tailored rewards"],
        "channels": ["Private Concierge SMS", "Direct Luxury Email", "Instagram VIP"],
        "business_recommendation": "Provide premium concierge loyalty programs, exclusive product previews, and high-touch customer support.",
        "description": "High-income, high-spending individuals representing the primary revenue and profit driver for premium retailers.",
    },
    "savers": {
        "key": "savers",
        "title": "The Careful Conservatives",
        "name": "Careful / Savers",
        "persona": "Savers",
        "color": "#F59E0B",
        "priority_tier": "Tier 2 (High Potential Upsell)",
        "spending_power": "High",
        "anchor": (88.2, 17.1),
        "key_traits": ["High Income", "Frugal / Discerning", "Value Oriented", "Research Driven"],
        "strategies": ["Value-add premium warranties", "Cashback rewards", "High-end electronics promotions"],
        "channels": ["LinkedIn", "Financial Newsletters", "Premium Direct Mail"],
        "business_recommendation": "Deploy targeted promotional campaigns highlighting product longevity, quality assurance, and high-value proposition.",
        "description": "Affluent customers with conservative spending habits. High potential for targeted upsell campaigns focusing on quality and utility.",
    },
    "spendthrifts": {
        "key": "spendthrifts",
        "title": "The Spendthrifts",
        "name": "Spendthrifts / Trendsetters",
        "persona": "Spendthrifts",
        "color": "#EC4899",
        "priority_tier": "Tier 3 (High Volume, Credit Sensitive)",
        "spending_power": "Moderate",
        "anchor": (25.7, 79.4),
        "key_traits": ["Young / Trend-driven", "High Spending Ratio", "Fashion Forward", "Experience Seeking"],
        "strategies": ["Buy-Now-Pay-Later (BNPL)", "Flash sales", "Student discounts", "Influencer activations"],
        "channels": ["TikTok", "Instagram Reels", "Snapchat", "Live In-Mall Events"],
        "business_recommendation": "Target with flexible buy-now-pay-later (BNPL) options, flash sales, influencer partnerships, and experiential marketing.",
        "description": "Younger demographic with lower income but exceptionally high spending score. Responsive to viral social trends and flexible financing.",
    },
    "budget": {
        "key": "budget",
        "title": "The Budget Conscious",
        "name": "Sensible / Budget",
        "persona": "Budget",
        "color": "#3B82F6",
        "priority_tier": "Tier 4 (Utility Retention)",
        "spending_power": "Low",
        "anchor": (26.3, 20.9),
        "key_traits": ["Price Sensitive", "Pragmatic", "Essentials First", "Coupon Users"],
        "strategies": ["Discount grocery coupons", "Bundle specials", "Seasonal clearance sales"],
        "channels": ["SMS Alerts", "Local Print Circulars", "Coupon Apps"],
        "business_recommendation": "Offer essential bundle discounts, reward-point cashbacks, and clear budget-friendly value items.",
        "description": "Pragmatic consumers with limited income and conservative spending. Motivated primarily by price, utility, and essential goods.",
    },
    "standard": {
        "key": "standard",
        "title": "The Moderate Mainstream",
        "name": "Moderate / Standard",
        "persona": "Standard",
        "color": "#6366F1",
        "priority_tier": "Tier 2 (Core Revenue Anchor)",
        "spending_power": "Moderate",
        "anchor": (55.3, 49.5),
        "key_traits": ["Balanced Spenders", "Family Oriented", "Routine Shoppers", "Dependable"],
        "strategies": ["Family bundle packages", "Seasonal mall festivals", "General points loyalty program"],
        "channels": ["Mall App Push Notifications", "Multi-Channel Email", "Weekend Mall Signage"],
        "business_recommendation": "Engage through regular seasonal newsletters, standardized loyalty points, and broad-appeal merchandise.",
        "description": "The largest customer cohort with average income and moderate spending. Represents the steady foot traffic and core revenue foundation of the mall.",
    },
}

DEFAULT_RANDOM_STATE: int = 42
DEFAULT_K: int = 5
