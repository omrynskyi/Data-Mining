# MLflow run comparison (queried via mlflow.search_runs)

| run_name                     |   metrics.cv_pr_auc_mean |   metrics.cv_pr_auc_mean_optuna |   metrics.test_pr_auc |   metrics.pr_auc |   metrics.roc_auc |   metrics.test_roc_auc |
|:-----------------------------|-------------------------:|--------------------------------:|----------------------:|-----------------:|------------------:|-----------------------:|
| final_calibrated_xgboost     |               nan        |                      nan        |            nan        |         0.668107 |          0.848176 |             nan        |
| mlp_torch                    |               nan        |                      nan        |              0.65324  |       nan        |        nan        |               0.84352  |
| xgboost_optuna_tuned         |               nan        |                        0.664568 |              0.662133 |       nan        |        nan        |               0.846498 |
| logreg_optuna_tuned          |               nan        |                        0.662182 |              0.660977 |       nan        |        nan        |               0.846963 |
| smote_honest_logreg          |                 0.657883 |                      nan        |            nan        |       nan        |        nan        |             nan        |
| logreg_class_weight_balanced |                 0.661746 |                      nan        |            nan        |       nan        |        nan        |             nan        |
| baseline_logreg              |                 0.663125 |                      nan        |            nan        |       nan        |        nan        |             nan        |
