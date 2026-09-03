# Schema Quick Reference — Telco Customer (inferred normalized model)

**IMPORTANT — this schema is inferred, not given.** `data/Telco-Customer-Churn.csv` is a single
denormalized mart (7,043 rows × 21 columns, one row per customer). No source database, ERD, or
data dictionary was provided. The 5-table model below is a plausible reverse-engineering of what
an upstream OLTP system *could* look like, built by reading column semantics and verifying
candidate keys/cardinalities against the actual data (not assumed). Treat this as a documented
hypothesis for a future normalization/dbt-modeling exercise, not a fact about a real upstream system.

## Tables Overview

- **customer** (~7,043 rows) — one row per person/account holder
  - Primary Key: `customer_id`
  - Columns: 5
- **subscription** (~7,043 rows in this snapshot) — one row per active service subscription
  - Primary Key: `subscription_id`
  - Columns: 7
- **service_addon** (~34,548 rows if unpivoted — see derivation below) — one row per applicable add-on per subscription
  - Primary Key: `addon_id`
  - Columns: 4
- **billing_account** (~7,043 rows) — one row per subscription's billing configuration
  - Primary Key: `billing_account_id`
  - Columns: 6
- **payment_method** (4 rows) — lookup/dimension table
  - Primary Key: `payment_method_id`
  - Columns: 3

`service_addon` row-count derivation (computed from the real data, not guessed): 7,043 subscriptions
× up to 7 addon types (MultipleLines + 6 internet add-ons), minus rows suppressed by the "not
applicable" sentinels — `MultipleLines` never applies when `PhoneService=='No'` (682 rows), and the
6 internet add-ons never apply when `InternetService=='No'` (1,526 rows × 6 columns). Net emitted
rows = 7,043×7 − 682 − 1,526×6 = 49,301 − 682 − 9,156 = **39,463** applicable (addon_type, status)
pairs across all subscriptions — i.e. every subscription contributes between 1 and 7 addon rows
depending on which services it has.

## Common Join Patterns

### From customer:

```sql
JOIN subscription ON customer.customer_id = subscription.customer_id
```

### From subscription:

```sql
JOIN service_addon ON subscription.subscription_id = service_addon.subscription_id
JOIN billing_account ON subscription.subscription_id = billing_account.subscription_id
```

### From billing_account:

```sql
JOIN payment_method ON billing_account.payment_method_id = payment_method.payment_method_id
```

### Full join path: customer -> subscription -> billing_account -> payment_method

```sql
SELECT c.customer_id, s.contract_type, b.monthly_charges, pm.method_name
FROM customer c
JOIN subscription s ON c.customer_id = s.customer_id
JOIN billing_account b ON s.subscription_id = b.subscription_id
JOIN payment_method pm ON b.payment_method_id = pm.payment_method_id;
```

### customer -> service_addon (via subscription, 1-hop indirect)

```sql
SELECT c.customer_id, sa.addon_type, sa.addon_status
FROM customer c
JOIN subscription s ON c.customer_id = s.customer_id
JOIN service_addon sa ON s.subscription_id = sa.subscription_id
WHERE sa.addon_type = 'OnlineSecurity';
```

## Reconciling this model back to the flat file

The flat `Telco-Customer-Churn.csv` is what you get by:
1. `customer JOIN subscription JOIN billing_account JOIN payment_method` (all 1:1 or *:1, no fan-out)
2. `PIVOT`-ing `service_addon` back out to one column per `addon_type`, filling `'No phone service'`
   / `'No internet service'` for the suppressed (not-applicable) rows.

This is exactly the operation `schema-mapper-mapping.md` documents in reverse (raw → analytics
target); see that document for the column-by-column mapping and the actual dtype casts applied.
