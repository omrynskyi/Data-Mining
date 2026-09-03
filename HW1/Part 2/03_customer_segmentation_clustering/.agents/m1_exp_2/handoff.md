# Handoff Report: Milestone 1 Edge Cases, Scaling, DBSCAN Metrics & Testing Strategy

**Agent**: Explorer 2 (`m1_exp_2`)  
**Parent Agent ID**: `205c1025-6744-49d9-995b-f49e76a9204f`  
**Working Directory**: `/Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/03_customer_segmentation_clustering/.agents/m1_exp_2/`  
**Target File**: `.agents/m1_exp_2/edge_cases_and_metrics.md`  
**Handoff Type**: Hard (Task Complete)  

---

## 1. Observation

1. **Dataset Structure and Scale Dispersion**:
   - The canonical Mall Customer dataset contains 200 rows with 5 attributes (`CustomerID`, `Genre`/`Gender`, `Age`, `Annual Income (k$)`, `Spending Score (1-100)`).
   - In 2D feature space (`Annual Income`, `Spending Score`), $\sigma_{\text{Income}} = 26.26$ and $\sigma_{\text{Spend}} = 25.82$ (ratio $\approx 1.017$).
   - In 3D feature space (`Age`, `Annual Income`, `Spending Score`), `Age` has $\sigma_{\text{Age}} = 13.97$ and variance $\sigma_{\text{Age}}^2 = 195.2$, whereas `Income` and `Spending` have variances $\sigma^2 \approx 690$ and $667$.

2. **Scaling Concordance & Metric Values**:
   - Direct execution on the Mall Customers dataset revealed that for 2D K-Means ($k=5$, `random_state=42`), `StandardScaler`, `MinMaxScaler`, `RobustScaler`, and unscaled data produce identical cluster assignments:
     ```python
     ARI vs Unscaled: 1.0000, AMI vs Unscaled: 1.0000
     ```
   - Transformed-space Silhouette scores: Unscaled = $0.5539$, StandardScaler = $0.5547$, MinMaxScaler = $0.5595$, RobustScaler = $0.5517$.
   - In 3D space, unscaled clustering ignores Age variance ($k=5$ ARI against StandardScaler is $0.6019$), while standardized clustering correctly partitions Age ($k=6$ achieves Silhouette $= 0.4284$, Davies-Bouldin $= 0.8254$, Calinski-Harabasz $= 135.10$).

3. **DBSCAN Noise Handling Verbatim Errors & Distortion**:
   - When noise points (label `-1`) are present, passing labels directly to `sklearn.metrics.silhouette_score` treats `-1` as a regular cluster:
     - Unfiltered Silhouette: `-0.0911` (severely degraded).
     - Filtered Silhouette (non-noise core points): `+0.5756`.
   - When all points are noise or all points belong to 1 cluster, `silhouette_score(X, labels)` raises:
     `ValueError: Number of labels is 1. Valid values are 2 to n_samples - 1 (inclusive)`
   - When $\text{eps}=0.10$, DBSCAN identifies 4 clusters but discards 166 noise points ($83\%$ noise ratio), demonstrating that noise point counts and ratios must be recorded alongside scores.

4. **PCA Dimensionality Reduction & Coordinate Properties**:
   - For 3D standardized features (`Age`, `Income`, `Spending`), 2 principal components capture $77.57\%$ of total variance ($\text{PC}_1 = 44.27\%$, $\text{PC}_2 = 33.31\%$), while 3 components capture $100\%$.
   - Standardized PCA coordinates fall in the range $[-2.5, +3.0]$, which maps cleanly to web rendering coordinate spaces without visual distortion.

---

## 2. Logic Chain

1. **Feature Scaling Logic (Observation 1 & 2 $\to$ Strategy)**:
   - In 2D space, because feature variances are isotropic ($\sigma_1 \approx \sigma_2$), any linear scaler preserves identical partition boundaries ($\text{ARI} = 1.0000$).
   - In 3D/4D space, unscaled Euclidean distance assigns over $87\%$ of weight to Income and Spending, effectively flattening the Age demographic.
   - *Inference*: Standardization (`StandardScaler`) is mathematically necessary for multidimensional clustering, and distance metrics must be evaluated on the transformed feature space used for model training to remain consistent with the objective function.

2. **DBSCAN Metric Isolation Logic (Observation 3 $\to$ Strategy)**:
   - Outliers and noise points in density clustering have high spatial dispersion. Treating label `-1` as an ordinary cluster invalidates intra-cluster compactness $a(i)$ in Silhouette and intra-cluster dispersion $s_i$ in Davies-Bouldin.
   - Single-cluster or all-noise segmentations fail scikit-learn's minimum label count assertion ($k \ge 2$).
   - *Inference*: The evaluation engine must filter out $-1$ labels before computing geometric metrics, return safe `null` (None) metrics with structured error status when $k < 2$ or $N_{\text{clean}} \le k$, and explicitly log `n_noise` and `noise_ratio`.

3. **PCA & JSON Contract Logic (Observation 4 $\to$ Strategy)**:
   - To avoid coordinate flipping across different OS platforms/LAPACK builds, SVD sign determinacy must be guaranteed using `svd_flip` via `sklearn.decomposition.PCA(random_state=42)`.
   - To comply with RFC 8259 JSON standards, all floating point outputs (`NaN`, `Infinity`) must be sanitized to `null` before export to `pipeline_output.json`.

4. **Unit Test Strategy Logic (Observations 1-4 $\to$ Test Suite)**:
   - The test suite must independently verify data ingestion and column sanitization (`test_data_loader.py`), model clustering reproducibility and metric thresholds (`test_pipeline.py`), noise handling edge cases, and CLI return codes.

---

## 3. Caveats

1. **No Source Code Modifications Outside `.agents/`**:
   - In accordance with explorer role constraints, all code changes are formulated as specifications and reference snippets in `edge_cases_and_metrics.md`. No files in `src/` or `tests/` were modified directly.
2. **Assumptions on Dataset Consistency**:
   - The canonical 200-record dataset has 0 missing values and integer identifiers. If user-supplied custom CSVs are ingested, median imputation and range filtering should be enforced.
3. **Alternative Linkages for Hierarchical Clustering**:
   - Ward linkage was the primary benchmark examined ($S \approx 0.553$ in 2D); single and complete linkages were evaluated and found to produce lower silhouette scores ($S \approx 0.538$ for complete, chain-like clusters for single linkage).

---

## 4. Conclusion

1. **Scaling Recommendation**: The M1 pipeline should provide standard scaling support across `StandardScaler`, `MinMaxScaler`, and unscaled modes, defaulting to `StandardScaler` for 3D/4D feature sets and unscaled/StandardScaler for canonical 2D benchmarking.
2. **DBSCAN Metric Recommendation**: Implement `evaluate_clustering_robust()` with mandatory noise filtering ($X[\text{labels} \ne -1]$), boundary cluster guards ($k \ge 2$), and explicit reporting of `n_noise` and `noise_ratio`.
3. **PCA & Dashboard Recommendation**: Export both raw feature coordinates and 3D PCA coordinates (`pca_x`, `pca_y`, `pca_z`) with variance ratios in `pipeline_output.json`.
4. **Testing Recommendation**: Implement comprehensive test suites in `tests/test_data_loader.py` and `tests/test_pipeline.py` verifying data schema invariants, scaling, clustering models, metric bounds, and CLI execution contracts.

---

## 5. Verification Method

To independently verify the empirical findings and numerical bounds:

1. **Verify 2D and 3D Scaling Concordance**:
   ```bash
   python3 -c "
   import pandas as pd, numpy as np
   from sklearn.preprocessing import StandardScaler
   from sklearn.cluster import KMeans
   from sklearn.metrics import silhouette_score, adjusted_rand_score

   url = 'https://raw.githubusercontent.com/sharmaroshan/Clustering-of-Mall-Customers/master/Mall_Customers.csv'
   df = pd.read_csv(url)
   X_2d = df[['Annual Income (k$)', 'Spending Score (1-100)']].values
   X_2d_std = StandardScaler().fit_transform(X_2d)

   km_raw = KMeans(n_clusters=5, random_state=42, n_init=10).fit(X_2d)
   km_std = KMeans(n_clusters=5, random_state=42, n_init=10).fit(X_2d_std)

   print('2D ARI Raw vs Std:', adjusted_rand_score(km_raw.labels_, km_std.labels_))
   print('2D Silhouette (Raw):', silhouette_score(X_2d, km_raw.labels_))
   print('2D Silhouette (Std):', silhouette_score(X_2d_std, km_std.labels_))
   "
   ```
   *Expected output*: `2D ARI Raw vs Std: 1.0`, `2D Silhouette (Raw): ~0.5539`, `2D Silhouette (Std): ~0.5547`.

2. **Verify DBSCAN Noise Isolation**:
   ```bash
   python3 -c "
   import pandas as pd, numpy as np
   from sklearn.preprocessing import StandardScaler
   from sklearn.cluster import DBSCAN
   from sklearn.metrics import silhouette_score

   url = 'https://raw.githubusercontent.com/sharmaroshan/Clustering-of-Mall-Customers/master/Mall_Customers.csv'
   df = pd.read_csv(url)
   X_std = StandardScaler().fit_transform(df[['Annual Income (k$)', 'Spending Score (1-100)']].values)

   db = DBSCAN(eps=0.35, min_samples=5).fit(X_std)
   mask = db.labels_ != -1
   print('Clusters (excl noise):', len(set(db.labels_) - {-1}))
   print('Noise points:', np.sum(db.labels_ == -1))
   print('Silhouette (excl noise):', silhouette_score(X_std[mask], db.labels_[mask]))
   "
   ```
   *Expected output*: `Clusters: 6`, `Noise points: 23`, `Silhouette: ~0.5577`.

3. **Verify PCA Projection Explained Variance**:
   ```bash
   python3 -c "
   import pandas as pd
   from sklearn.preprocessing import StandardScaler
   from sklearn.decomposition import PCA

   url = 'https://raw.githubusercontent.com/sharmaroshan/Clustering-of-Mall-Customers/master/Mall_Customers.csv'
   df = pd.read_csv(url)
   X_std = StandardScaler().fit_transform(df[['Age', 'Annual Income (k$)', 'Spending Score (1-100)']].values)
   pca = PCA(n_components=3, random_state=42).fit(X_std)
   print('Explained Variance Ratios:', [round(x, 4) for x in pca.explained_variance_ratio_])
   "
   ```
   *Expected output*: `[0.4427, 0.3331, 0.2243]`.
