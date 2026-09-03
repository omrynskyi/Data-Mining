Build a churn-risk model and monthly ranked risk list for the Telco Customer Churn
dataset (data/Telco-Customer-Churn.csv, 7,043 customers) so the retention team can
prioritize outreach. Follow the full CRISP-DM cycle (phases 1-6, plan in
crisp_dm/01_business_understanding/analysis-planning.md). For any downstream task,
produce output as: a ranked customer list (customerID, churn_probability,
recommended_action) plus a short narrative of the top risk drivers. Use only the
columns present in data/Telco-Customer-Churn.csv / data/processed/{train,test}.csv.
