
WITH contract_churn AS (
    SELECT Contract, 1.0*SUM(CASE WHEN Churn='Yes' THEN 1 ELSE 0 END)/COUNT(*) AS rate
    FROM customers GROUP BY Contract
)
SELECT
    c1.Contract,
    COUNT(*) AS n_active_customers,
    ROUND(SUM(c1.MonthlyCharges), 2) AS active_mrr,
    ROUND(cc.rate, 4) AS historical_churn_rate,
    ROUND(SUM(c1.MonthlyCharges) * cc.rate, 2) AS expected_monthly_revenue_at_risk
FROM customers c1
JOIN contract_churn cc ON cc.Contract = c1.Contract
WHERE c1.Churn = 'No'
GROUP BY c1.Contract, cc.rate
ORDER BY expected_monthly_revenue_at_risk DESC;
