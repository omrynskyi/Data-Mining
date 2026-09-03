# SQL Explanation: churn_rate_by_contract

```sql
SELECT
    Contract,
    COUNT(*) AS n_customers,
    SUM(CASE WHEN Churn = 'Yes' THEN 1 ELSE 0 END) AS n_churned,
    ROUND(100.0 * SUM(CASE WHEN Churn = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 2) AS churn_rate_pct
FROM customers
GROUP BY Contract
ORDER BY churn_rate_pct DESC;
```

### What is being calculated (SELECT)
- Contract
- Count of * (as n_customers)
- Sum of CASE WHEN Churn = 'Yes' THEN 1 ELSE 0 END (as n_churned)
- Count of 100.0 * SUM(CASE WHEN Churn = 'Yes' THEN 1 ELSE 0 END (as churn_rate_pct)

### Data source (FROM)
- Start with: customers

### Grouping (GROUP BY)
- Calculate separately for each: Contract

### Sorting (ORDER BY)
- Sort by: churn_rate_pct DESC;

### Validation questions
- Are these the correct filter conditions for the intended population?
- Does the GROUP BY grain match what a single row should represent?
- Are NULL values handled explicitly in aggregations?
