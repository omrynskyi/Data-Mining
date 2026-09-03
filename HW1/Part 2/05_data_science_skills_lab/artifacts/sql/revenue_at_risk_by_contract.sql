SELECT
    c1.Contract,
    COUNT(*) AS n_active_customers,
    ROUND(SUM(c1.MonthlyCharges), 2) AS active_mrr,
    ROUND(
        (SELECT 1.0 * SUM(CASE WHEN c2.Churn = 'Yes' THEN 1 ELSE 0 END) / COUNT(*)
         FROM customers c2 WHERE c2.Contract = c1.Contract),
        4
    ) AS historical_churn_rate,
    ROUND(
        SUM(c1.MonthlyCharges) *
        (SELECT 1.0 * SUM(CASE WHEN c2.Churn = 'Yes' THEN 1 ELSE 0 END) / COUNT(*)
         FROM customers c2 WHERE c2.Contract = c1.Contract),
        2
    ) AS expected_monthly_revenue_at_risk
FROM customers c1
WHERE c1.Churn = 'No'
GROUP BY c1.Contract
ORDER BY expected_monthly_revenue_at_risk DESC;
