SELECT
    Contract,
    COUNT(*) AS n_customers,
    SUM(CASE WHEN Churn = 'Yes' THEN 1 ELSE 0 END) AS n_churned,
    ROUND(100.0 * SUM(CASE WHEN Churn = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 2) AS churn_rate_pct
FROM customers
GROUP BY Contract
ORDER BY churn_rate_pct DESC;
