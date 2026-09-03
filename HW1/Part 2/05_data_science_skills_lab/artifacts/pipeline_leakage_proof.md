# sklearn-pipelines: leakage proof

## Fold-statistic drift (the mechanism)
Naive preprocessing freezes numeric medians from all 5,634 rows once. Proper CV refits the median on each fold's ~4,507-row training portion. The two disagree — this is the leakage vector:

|                     |   full_data_median |   max_abs_diff_vs_any_fold |
|:--------------------|-------------------:|---------------------------:|
| tenure              |             29     |                      0     |
| MonthlyCharges      |             70.5   |                      0.2   |
| TotalCharges        |           1394.92  |                      9.725 |
| avg_monthly_spend   |             70.589 |                      0.444 |
| spend_gap           |              0     |                      0     |
| num_addon_services  |              2     |                      0     |
| charges_per_service |             19.3   |                      0.1   |

## Cross-validated ROC AUC: proper vs naive

- **Proper** (preprocessing refit inside every fold): mean AUC = **0.84761** ± 0.01138 (folds: [0.84468, 0.82942, 0.84436, 0.85928, 0.8603])
- **Naive** (preprocessing fit once on all of train, then CV'd on frozen matrix): mean AUC = **0.84759** ± 0.01136 (folds: [0.84462, 0.82946, 0.84434, 0.85915, 0.86036])
- Difference (naive - proper): **-0.00002** AUC

On this dataset the numeric/categorical leakage effect is small in absolute AUC terms (the OneHotEncoder vocabulary and imputer statistics barely move between a 4,507-row fold and the full 5,634-row train set), because there is no rare-category or heavy-tailed column here — the -0.00002 AUC gap is within CV fold noise, i.e. statistically indistinguishable from zero on this split. That near-null result is itself informative: it confirms the fold-statistic drift table above (largest gap 9.7 on TotalCharges, a column with std ~2,300) is too small relative to the feature's scale to move a StandardScaler-fed logistic regression. The same underlying mechanism becomes severe with high-cardinality target encoding — see `artifacts/target_encoding_leakage_demo.json` from the feature-engineering step, where the same naive-vs-OOF comparison inflates AUC by 0.0075 on the real target and manufactures 0.02 AUC of pure noise out of a shuffled target. The mechanism is identical; the magnitude depends entirely on how much a column's statistic can overfit to the specific rows it's computed from — which is why the skill's rule is structural (always fit inside the pipeline/CV), not case-by-case judgment.
