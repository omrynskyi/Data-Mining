"""CRISP-DM Phase 4 -- pytorch-training-loop skill.

A small MLP on the 57 preprocessed features, built to demonstrate loop
CORRECTNESS per the skill's non-negotiable rules:

  1. model.train() before training, model.eval() before validation/inference
  2. optimizer.zero_grad() every step
  3. torch.no_grad() around validation/inference
  4. BCEWithLogitsLoss (not sigmoid+BCE) with pos_weight for imbalance
  5. gradient clipping
  6. early stopping on val loss + checkpointing best weights
  7. deterministic seeding (p4_repro.set_all_seeds) + explicit device selection

The point of this skill is correctness, not beating sklearn -- the honest
comparison against the tuned baselines from hyperparameter-tuning is reported
at the end, including the (expected, correct) finding if the MLP does not win
on this tabular dataset.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from p4_repro import DEFAULT_SEED, assert_dataset_pinned, set_all_seeds  # noqa: E402
from p3_pipeline import build_preprocessor  # noqa: E402

import torch
import torch.nn as nn
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, TensorDataset

ARTIFACTS = ROOT / "artifacts"
FIG_DIR = ROOT / "reports" / "figures"
CKPT_PATH = ARTIFACTS / "mlp_best.pt"


class ChurnMLP(nn.Module):
    def __init__(self, in_dim: int, hidden=(64, 32), dropout=0.3):
        super().__init__()
        layers = []
        d = in_dim
        for h in hidden:
            layers += [nn.Linear(d, h), nn.ReLU(), nn.Dropout(dropout)]
            d = h
        layers += [nn.Linear(d, 1)]  # raw logit -- pair with BCEWithLogitsLoss
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


def select_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def main():
    set_all_seeds(DEFAULT_SEED)
    assert_dataset_pinned()
    device = select_device()
    print(f"device: {device}")

    train_full = pd.read_csv(ROOT / "data" / "processed" / "train.csv")
    test = pd.read_csv(ROOT / "data" / "processed" / "test.csv")

    X_full = train_full.drop(columns=["customerID", "Churn"])
    y_full = train_full["Churn"]
    X_test_raw = test.drop(columns=["customerID", "Churn"])
    y_test = test["Churn"].values.astype(np.float32)

    # Train/val split for early stopping -- preprocessor is fit on the TRAIN
    # split only, then applied to val and test (no leakage of val/test
    # statistics into scaling/imputation).
    Xtr_raw, Xval_raw, ytr, yval = train_test_split(
        X_full, y_full, test_size=0.15, random_state=DEFAULT_SEED, stratify=y_full
    )

    prep = build_preprocessor()
    Xtr = prep.fit_transform(Xtr_raw).astype(np.float32)
    Xval = prep.transform(Xval_raw).astype(np.float32)
    Xtest = prep.transform(X_test_raw).astype(np.float32)
    ytr_arr = ytr.values.astype(np.float32)
    yval_arr = yval.values.astype(np.float32)

    n_pos, n_neg = (ytr_arr == 1).sum(), (ytr_arr == 0).sum()
    pos_weight = torch.tensor([n_neg / n_pos], dtype=torch.float32, device=device)
    print(f"train n={len(ytr_arr)} (pos={int(n_pos)}, neg={int(n_neg)}), "
          f"pos_weight={pos_weight.item():.4f}")

    g = torch.Generator()
    g.manual_seed(DEFAULT_SEED)
    train_ds = TensorDataset(torch.tensor(Xtr), torch.tensor(ytr_arr).unsqueeze(1))
    val_ds = TensorDataset(torch.tensor(Xval), torch.tensor(yval_arr).unsqueeze(1))
    train_loader = DataLoader(train_ds, batch_size=64, shuffle=True, generator=g)
    val_loader = DataLoader(val_ds, batch_size=256, shuffle=False)

    model = ChurnMLP(in_dim=Xtr.shape[1]).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-2)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)  # NOT sigmoid+BCE

    max_epochs = 100
    patience = 10
    best_val_loss = float("inf")
    epochs_without_improve = 0
    history = {"train_loss": [], "val_loss": [], "val_pr_auc": []}

    t0 = time.time()
    for epoch in range(max_epochs):
        # ---- TRAIN ----
        model.train()
        running_loss = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad(set_to_none=True)
            out = model(xb)
            loss = criterion(out, yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            running_loss += loss.item() * xb.size(0)
        train_loss = running_loss / len(train_ds)

        # ---- VALIDATE ----
        model.eval()
        val_loss = 0.0
        val_probs, val_targets = [], []
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                out = model(xb)
                loss = criterion(out, yb)
                val_loss += loss.item() * xb.size(0)
                val_probs.append(torch.sigmoid(out).cpu().numpy())
                val_targets.append(yb.cpu().numpy())
        val_loss /= len(val_ds)
        val_probs = np.concatenate(val_probs).ravel()
        val_targets = np.concatenate(val_targets).ravel()
        val_pr_auc = average_precision_score(val_targets, val_probs)

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_pr_auc"].append(float(val_pr_auc))

        improved = val_loss < best_val_loss - 1e-4
        if improved:
            best_val_loss = val_loss
            epochs_without_improve = 0
            torch.save({"model_state": model.state_dict(), "epoch": epoch,
                        "val_loss": val_loss, "in_dim": Xtr.shape[1]}, CKPT_PATH)
        else:
            epochs_without_improve += 1

        if epoch % 5 == 0 or improved:
            print(f"  epoch {epoch:3d}  train_loss={train_loss:.4f}  "
                  f"val_loss={val_loss:.4f}  val_pr_auc={val_pr_auc:.4f}"
                  f"{'  * best (checkpointed)' if improved else ''}")

        if epochs_without_improve >= patience:
            print(f"  early stopping at epoch {epoch} "
                  f"({patience} epochs without val_loss improvement)")
            break

    elapsed = time.time() - t0
    print(f"training done in {elapsed:.1f}s, {len(history['train_loss'])} epochs, "
          f"best val_loss={best_val_loss:.4f}")

    # ---- Load BEST checkpoint (not last epoch) and evaluate on TEST ----
    ckpt = torch.load(CKPT_PATH, map_location=device, weights_only=True)
    best_model = ChurnMLP(in_dim=ckpt["in_dim"]).to(device)
    best_model.load_state_dict(ckpt["model_state"])
    best_model.eval()
    with torch.no_grad():
        test_logits = best_model(torch.tensor(Xtest).to(device))
        test_probs = torch.sigmoid(test_logits).cpu().numpy().ravel()

    test_pred = (test_probs >= 0.5).astype(int)
    mlp_metrics = {
        "checkpoint_epoch": ckpt["epoch"],
        "best_val_loss": float(ckpt["val_loss"]),
        "test_roc_auc": float(roc_auc_score(y_test, test_probs)),
        "test_pr_auc": float(average_precision_score(y_test, test_probs)),
        "test_accuracy_at_0.5": float(accuracy_score(y_test, test_pred)),
        "test_recall_at_0.5": float(recall_score(y_test, test_pred)),
        "test_brier": float(brier_score_loss(y_test, test_probs)),
        "n_epochs_trained": len(history["train_loss"]),
        "device": str(device),
    }
    print("\n== MLP held-out TEST metrics (best checkpoint) ==")
    for k, v in mlp_metrics.items():
        print(f"  {k}: {v}")

    # ---- Honest comparison vs sklearn baselines from earlier Phase 4 steps ----
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline as SkPipeline

    sk_baseline = SkPipeline([
        ("prep", build_preprocessor()),
        ("clf", LogisticRegression(max_iter=1000, random_state=DEFAULT_SEED,
                                    class_weight="balanced")),
    ])
    sk_baseline.fit(X_full, y_full)
    sk_probs = sk_baseline.predict_proba(X_test_raw)[:, 1]
    sk_pred = (sk_probs >= 0.5).astype(int)
    sklearn_metrics = {
        "model": "LogisticRegression(class_weight=balanced), refit on full train",
        "test_roc_auc": float(roc_auc_score(y_test, sk_probs)),
        "test_pr_auc": float(average_precision_score(y_test, sk_probs)),
        "test_accuracy_at_0.5": float(accuracy_score(y_test, sk_pred)),
        "test_recall_at_0.5": float(recall_score(y_test, sk_pred)),
    }

    try:
        xgb_results = json.loads((ARTIFACTS / "hyperparameter_tuning_results.json").read_text())
        xgb_best_params = xgb_results["xgboost"]["best_params"]
        from xgboost import XGBClassifier
        xgb_pipe = SkPipeline([
            ("prep", build_preprocessor()),
            ("clf", XGBClassifier(**xgb_best_params, random_state=DEFAULT_SEED,
                                   eval_metric="aucpr", n_jobs=1, verbosity=0)),
        ])
        xgb_pipe.fit(X_full, y_full)
        xgb_probs = xgb_pipe.predict_proba(X_test_raw)[:, 1]
        xgb_pred = (xgb_probs >= 0.5).astype(int)
        xgb_metrics = {
            "model": "XGBoost (Optuna-tuned), refit on full train",
            "test_roc_auc": float(roc_auc_score(y_test, xgb_probs)),
            "test_pr_auc": float(average_precision_score(y_test, xgb_probs)),
            "test_accuracy_at_0.5": float(accuracy_score(y_test, xgb_pred)),
            "test_recall_at_0.5": float(recall_score(y_test, xgb_pred)),
        }
    except FileNotFoundError:
        xgb_metrics = None

    comparison = {
        "mlp": mlp_metrics,
        "sklearn_logreg_baseline": sklearn_metrics,
        "xgboost_tuned": xgb_metrics,
    }
    verdict_pr_auc = {
        "mlp": mlp_metrics["test_pr_auc"],
        "logreg": sklearn_metrics["test_pr_auc"],
        "xgboost": xgb_metrics["test_pr_auc"] if xgb_metrics else None,
    }
    winner = max((k for k in verdict_pr_auc if verdict_pr_auc[k] is not None),
                 key=lambda k: verdict_pr_auc[k])
    comparison["verdict"] = (
        f"By held-out test PR-AUC: {winner} wins "
        f"(mlp={verdict_pr_auc['mlp']:.4f}, logreg={verdict_pr_auc['logreg']:.4f}, "
        f"xgboost={verdict_pr_auc['xgboost']:.4f}). "
        + ("The MLP does NOT beat the sklearn baselines on this small tabular "
           "dataset (5,634 train rows, 57 features) -- expected and consistent "
           "with the well-known result that gradient-boosted trees and even "
           "plain logistic regression tend to match or beat deep nets on "
           "small/medium tabular data." if winner != "mlp" else
           "The MLP edges out the sklearn baselines here.")
    )
    print(f"\n{comparison['verdict']}")

    out_path = ARTIFACTS / "mlp_vs_sklearn_comparison.json"
    out_path.write_text(json.dumps(comparison, indent=2, default=float))
    print(f"wrote {out_path}")

    hist_path = ARTIFACTS / "mlp_training_history.json"
    hist_path.write_text(json.dumps(history, indent=2))

    # ---- training curve figure ----
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    epochs_range = range(len(history["train_loss"]))
    axes[0].plot(epochs_range, history["train_loss"], label="train loss")
    axes[0].plot(epochs_range, history["val_loss"], label="val loss")
    axes[0].axvline(ckpt["epoch"], color="green", linestyle=":",
                     label=f"best checkpoint (epoch {ckpt['epoch']})")
    axes[0].set_xlabel("epoch")
    axes[0].set_ylabel("BCEWithLogitsLoss")
    axes[0].set_title("MLP training curve (early stopping)")
    axes[0].legend(fontsize=8)

    axes[1].plot(epochs_range, history["val_pr_auc"], color="#55a868")
    axes[1].axvline(ckpt["epoch"], color="green", linestyle=":")
    axes[1].set_xlabel("epoch")
    axes[1].set_ylabel("Validation PR-AUC")
    axes[1].set_title("MLP validation PR-AUC per epoch")

    fig.tight_layout()
    fig_path = FIG_DIR / "p4_mlp_training_curve.png"
    fig.savefig(fig_path, dpi=130)
    plt.close(fig)
    print(f"wrote {fig_path}")


if __name__ == "__main__":
    main()
