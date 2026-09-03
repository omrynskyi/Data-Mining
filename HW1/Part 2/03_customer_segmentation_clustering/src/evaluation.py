"""
CRISP-DM Phase 5: Evaluation - Internal Validation Metrics, Hyperparameter Sweeps & Persona Profiling.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import KMeans
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)

from src.config import CANONICAL_PERSONAS


class ClusterEvaluator:
    """Computes clustering metrics, sweeps k values, and profiles business personas."""

    @staticmethod
    def compute_metrics(
        X: np.ndarray,
        labels: np.ndarray,
        inertia: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Computes internal cluster validation metrics.
        Robustly filters noise points (-1) and handles degenerate cluster counts.
        """
        total_samples = len(labels)
        unique_labels = set(labels)
        non_noise_labels = sorted(list(unique_labels - {-1}))
        n_clusters = len(non_noise_labels)
        noise_count = int(np.sum(labels == -1))
        noise_ratio = round(float(noise_count / total_samples), 4) if total_samples > 0 else 0.0

        metrics: Dict[str, Any] = {
            "silhouette_score": 0.0,
            "davies_bouldin_index": 99.0,
            "calinski_harabasz_score": 0.0,
            "inertia": round(float(inertia), 2) if inertia is not None else None,
            "n_clusters": n_clusters,
            "noise_count": noise_count,
            "noise_ratio": noise_ratio,
            "is_valid": False,
        }

        # Validate minimum cluster requirements
        if n_clusters < 2:
            return metrics

        # Filter noise points if present
        if noise_count > 0:
            mask = labels != -1
            X_clean = X[mask]
            labels_clean = labels[mask]
        else:
            X_clean = X
            labels_clean = labels

        if len(labels_clean) <= n_clusters:
            return metrics

        try:
            sil = float(silhouette_score(X_clean, labels_clean))
            dbi = float(davies_bouldin_score(X_clean, labels_clean))
            chi = float(calinski_harabasz_score(X_clean, labels_clean))

            metrics["silhouette_score"] = round(sil, 4)
            metrics["davies_bouldin_index"] = round(dbi, 4)
            metrics["calinski_harabasz_score"] = round(chi, 2)
            metrics["is_valid"] = True
        except Exception:
            metrics["is_valid"] = False

        return metrics

    @staticmethod
    def sweep_k(
        X: np.ndarray,
        k_min: int = 2,
        k_max: int = 10,
        random_state: int = 42,
    ) -> Dict[str, Any]:
        """
        Sweeps k across [k_min, k_max] and calculates metrics for elbow and silhouette curves.
        """
        k_values = list(range(k_min, k_max + 1))
        silhouette_scores: List[float] = []
        davies_bouldin_indices: List[float] = []
        calinski_harabasz_scores: List[float] = []
        inertias: List[float] = []
        sweep_table: List[Dict[str, Any]] = []

        for k in k_values:
            km = KMeans(
                n_clusters=k,
                init="k-means++",
                n_init=10,
                max_iter=300,
                random_state=random_state,
            )
            km.fit(X)
            sil = float(silhouette_score(X, km.labels_))
            dbi = float(davies_bouldin_score(X, km.labels_))
            chi = float(calinski_harabasz_score(X, km.labels_))
            ine = float(km.inertia_)

            silhouette_scores.append(round(sil, 4))
            davies_bouldin_indices.append(round(dbi, 4))
            calinski_harabasz_scores.append(round(chi, 2))
            inertias.append(round(ine, 2))

            sweep_table.append({
                "k": k,
                "silhouette": round(sil, 4),
                "davies_bouldin": round(dbi, 4),
                "calinski_harabasz": round(chi, 2),
                "inertia": round(ine, 2),
            })

        best_idx = int(np.argmax(silhouette_scores))
        optimal_k = k_values[best_idx]

        return {
            "k_values": k_values,
            "silhouette_scores": silhouette_scores,
            "davies_bouldin_indices": davies_bouldin_indices,
            "calinski_harabasz_scores": calinski_harabasz_scores,
            "inertias": inertias,
            "optimal_k": optimal_k,
            "sweep_table": sweep_table,
        }

    @staticmethod
    def map_clusters_to_personas(
        centroids: np.ndarray,
        feature_names: Optional[List[str]] = None,
    ) -> Dict[int, Dict[str, Any]]:
        """
        Binds cluster IDs to canonical personas using Hungarian bipartite matching on (Income, Spend).
        """
        if feature_names is not None:
            fn_lower = [str(f).lower() for f in feature_names]
            inc_idx = next((i for i, f in enumerate(fn_lower) if "income" in f), 0)
            spn_idx = next((i for i, f in enumerate(fn_lower) if "spending" in f or "score" in f), 1)
        else:
            inc_idx, spn_idx = 0, 1

        anchor_keys = list(CANONICAL_PERSONAS.keys())
        anchor_points = np.array([CANONICAL_PERSONAS[k]["anchor"] for k in anchor_keys])

        k = len(centroids)
        # Extract 2D centroids
        cluster_points = np.zeros((k, 2))
        for i in range(k):
            cluster_points[i, 0] = centroids[i, inc_idx] if centroids.shape[1] > inc_idx else 50.0
            cluster_points[i, 1] = centroids[i, spn_idx] if centroids.shape[1] > spn_idx else 50.0

        if k == 5:
            cost = np.linalg.norm(cluster_points[:, None, :] - anchor_points[None, :, :], axis=-1)
            row_ind, col_ind = linear_sum_assignment(cost)
            return {int(r): CANONICAL_PERSONAS[anchor_keys[c]] for r, c in zip(row_ind, col_ind)}
        else:
            # Greedy nearest anchor matching for non-5 clusterings
            mapping = {}
            for cid in range(k):
                dists = np.linalg.norm(anchor_points - cluster_points[cid], axis=-1)
                best_idx = int(np.argmin(dists))
                mapping[cid] = CANONICAL_PERSONAS[anchor_keys[best_idx]]
            return mapping

    def profile_clusters(
        self,
        df: pd.DataFrame,
        labels: np.ndarray,
        centroids: Optional[np.ndarray] = None,
        feature_names: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generates enriched cluster profiles with marketing personas, demographics, and recommendations.
        """
        df_eval = df.copy()
        df_eval["cluster_id"] = labels
        total_customers = len(df_eval)
        unique_cids = sorted(list(set(labels)))

        # Compute empirical centroids in original space if not provided
        if centroids is None:
            non_noise = [c for c in unique_cids if c >= 0]
            centroids_list = []
            for c in non_noise:
                sub = df_eval[df_eval["cluster_id"] == c]
                inc_m = float(sub["annual_income"].mean())
                spn_m = float(sub["spending_score"].mean())
                centroids_list.append([inc_m, spn_m])
            centroids = np.array(centroids_list) if centroids_list else np.array([[50.0, 50.0]])
            feature_names = ["annual_income", "spending_score"]

        persona_map = self.map_clusters_to_personas(centroids, feature_names)
        profiles: List[Dict[str, Any]] = []

        for cid in unique_cids:
            if cid == -1:
                # Noise cluster from DBSCAN
                sub = df_eval[df_eval["cluster_id"] == -1]
                count = len(sub)
                m_cnt = int((sub["gender"] == "Male").sum())
                f_cnt = int((sub["gender"] == "Female").sum())
                profiles.append({
                    "cluster_id": -1,
                    "name": "Noise / Outliers",
                    "persona": "Noise",
                    "color": "#94A3B8",
                    "count": count,
                    "percentage": round(count / total_customers * 100, 2),
                    "avg_age": round(float(sub["age"].mean()), 2) if count > 0 else 0.0,
                    "avg_income": round(float(sub["annual_income"].mean()), 2) if count > 0 else 0.0,
                    "avg_spending": round(float(sub["spending_score"].mean()), 2) if count > 0 else 0.0,
                    "male_count": m_cnt,
                    "female_count": f_cnt,
                    "female_percentage": round(f_cnt / count * 100, 2) if count > 0 else 0.0,
                    "gender_distribution": {"Male": m_cnt, "Female": f_cnt},
                    "centroid": {
                        "age": round(float(sub["age"].mean()), 2) if count > 0 else 0.0,
                        "annual_income": round(float(sub["annual_income"].mean()), 2) if count > 0 else 0.0,
                        "spending_score": round(float(sub["spending_score"].mean()), 2) if count > 0 else 0.0,
                    },
                    "business_recommendation": "Review individual anomaly records for fraud, data noise, or niche luxury behaviors.",
                    "key_traits": ["Statistical Outliers", "Boundary Points", "Low Density"],
                    "persona_details": {
                        "title": "Unassigned Outliers",
                        "subtitle": "Noise Cluster",
                        "description": "Customer records falling outside primary density clusters.",
                        "demographic_summary": "Scattered demographic distribution.",
                        "behavioral_traits": ["Non-standard spending patterns"],
                        "recommended_strategies": ["Individual customer inspection"],
                        "marketing_channels": ["Standard direct mail"],
                        "priority_tier": "Tier 5 (Ad-hoc)",
                        "spending_power": "Variable",
                    },
                })
                continue

            sub = df_eval[df_eval["cluster_id"] == cid]
            count = len(sub)
            pct = round(count / total_customers * 100, 2)
            p_data = persona_map.get(cid, CANONICAL_PERSONAS["standard"])

            avg_age = float(sub["age"].mean()) if count > 0 else 0.0
            avg_inc = float(sub["annual_income"].mean()) if count > 0 else 0.0
            avg_spd = float(sub["spending_score"].mean()) if count > 0 else 0.0

            m_cnt = int((sub["gender"] == "Male").sum())
            f_cnt = int((sub["gender"] == "Female").sum())

            profiles.append({
                "cluster_id": int(cid),
                "name": p_data["name"],
                "persona": p_data["persona"],
                "color": p_data["color"],
                "count": count,
                "percentage": pct,
                "avg_age": round(avg_age, 2),
                "avg_income": round(avg_inc, 2),
                "avg_spending": round(avg_spd, 2),
                "male_count": m_cnt,
                "female_count": f_cnt,
                "female_percentage": round(f_cnt / count * 100, 2) if count > 0 else 0.0,
                "gender_distribution": {"Male": m_cnt, "Female": f_cnt},
                "centroid": {
                    "age": round(avg_age, 2),
                    "annual_income": round(avg_inc, 2),
                    "spending_score": round(avg_spd, 2),
                },
                "business_recommendation": p_data["business_recommendation"],
                "key_traits": p_data["key_traits"],
                "persona_details": {
                    "title": p_data["title"],
                    "subtitle": f"{p_data['persona']} Segment",
                    "description": p_data["description"],
                    "demographic_summary": f"Avg Income: ${avg_inc:.1f}k, Avg Spend: {avg_spd:.1f}/100, Avg Age: {avg_age:.1f}",
                    "behavioral_traits": p_data["key_traits"],
                    "recommended_strategies": p_data["strategies"],
                    "marketing_channels": p_data["channels"],
                    "priority_tier": p_data["priority_tier"],
                    "spending_power": p_data["spending_power"],
                },
            })

        return self._disambiguate_persona_names(profiles)

    @staticmethod
    def _disambiguate_persona_names(profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Suffixes reused persona labels so every cluster is uniquely identifiable.

        With k != 5 the greedy anchor matching can assign the same canonical persona to
        several clusters; the Hungarian k=5 path never does, so names are left untouched
        in the canonical case.
        """
        name_counts: Dict[str, int] = {}
        for profile in profiles:
            name_counts[profile["name"]] = name_counts.get(profile["name"], 0) + 1

        seen: Dict[str, int] = {}
        for profile in profiles:
            base = profile["name"]
            if name_counts[base] < 2:
                continue
            seen[base] = seen.get(base, 0) + 1
            suffix = f" (Group {seen[base]})"
            profile["name"] = base + suffix
            details = profile.get("persona_details")
            if isinstance(details, dict):
                details["title"] = f"{details['title']}{suffix}"

        return profiles
