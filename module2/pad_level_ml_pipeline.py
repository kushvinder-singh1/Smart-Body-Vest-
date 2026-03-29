"""
High-accuracy tabular pipeline for pad_level (OFF / LOW / MEDIUM / HIGH).

Steps: EDA → preprocessing → feature engineering → RF / boosting / MLP comparison
with RandomizedSearchCV → 5-fold CV → hold-out test → save best bundle (.joblib).

Labels use deterministic heat-demand quartiles (see label_rules) so the task is learnable.
For real-world noisy labels, expect lower scores unless labels are cleaned.

Usage (from project root):
  python -m module2.pad_level_ml_pipeline
"""
from __future__ import annotations

import json
import os
import warnings
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    make_scorer,
)
from sklearn.model_selection import (
    RandomizedSearchCV,
    StratifiedKFold,
    cross_val_score,
    train_test_split,
)
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from . import config
from .data_prep import read_dataset_file
from .label_rules import apply_deterministic_pad_labels

warnings.filterwarnings("ignore", category=UserWarning)

RANDOM_STATE = config.SHUFFLE_SEED
CV_FOLDS = 5
TEST_SIZE = 0.15
N_ITER_SEARCH = 28


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def engineer_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Add interaction / normalized features; return matrix and column names."""
    d = df.copy()
    t = d[config.COL_TEMP].astype(float)
    p = d[config.COL_PULSE].astype(float)
    m = d[config.COL_MOTION].astype(float)
    td = d[config.COL_TEMP_DELTA].astype(float)
    age = d[config.COL_AGE].astype(float)
    h = d[config.COL_HEIGHT_CM].astype(float)
    w = d[config.COL_WEIGHT_KG].astype(float)
    g = d[config.COL_GENDER].astype(float)

    d["temp_x_motion"] = t * m
    d["temp_x_pulse"] = t * p / 1000.0
    d["pulse_dev_norm"] = (p - 72.0) / 18.0
    d["pulse_motion"] = p * m / 100.0
    d["temp_delta_sq"] = td**2
    d["bmi_proxy"] = w / ((h / 100.0) ** 2 + 1e-6)
    d["age_pulse_interaction"] = age * p / 5000.0
    d["comfort_gap"] = np.maximum(0.0, 36.5 - t)

    base = list(config.FEATURE_COLS)
    extra = [
        "temp_x_motion",
        "temp_x_pulse",
        "pulse_dev_norm",
        "pulse_motion",
        "temp_delta_sq",
        "bmi_proxy",
        "age_pulse_interaction",
        "comfort_gap",
    ]
    cols = base + extra
    return d[cols], cols


def build_feature_row(
    temp: float,
    pulse: float,
    motion: float,
    age: float,
    height: float,
    weight: float,
    gender: float,
) -> np.ndarray:
    """Single-row feature vector aligned with engineer_features."""
    motion = 1.0 if float(motion) >= 0.5 else 0.0
    temp_delta = float(temp) - 36.5
    t, p, m, td = float(temp), float(pulse), motion, temp_delta
    row = {
        config.COL_TEMP: t,
        config.COL_TEMP_DELTA: td,
        config.COL_PULSE: p,
        config.COL_MOTION: m,
        config.COL_AGE: float(age),
        config.COL_HEIGHT_CM: float(height),
        config.COL_WEIGHT_KG: float(weight),
        config.COL_GENDER: float(gender),
    }
    df = pd.DataFrame([row])
    X, _ = engineer_features(df)
    return X.values.astype(np.float32)


@dataclass
class PadLevelPredictorBundle:
    """
    Production artifact: sklearn Pipeline (scaler + classifier) + metadata.
    """

    pipeline: Pipeline
    feature_names: List[str]
    model_name: str
    cv_accuracy_mean: float = 0.0
    test_accuracy: float = 0.0
    report: str = ""

    def predict_proba(
        self,
        temp: float,
        pulse: float,
        motion: float,
        age: float,
        height: float,
        weight: float,
        gender: float,
    ) -> np.ndarray:
        X = build_feature_row(temp, pulse, motion, age, height, weight, gender)
        return self.pipeline.predict_proba(X)[0]

    def predict_class_index(
        self,
        temp: float,
        pulse: float,
        motion: float,
        age: float,
        height: float,
        weight: float,
        gender: float,
    ) -> int:
        return int(np.argmax(self.predict_proba(temp, pulse, motion, age, height, weight, gender)))


# ---------------------------------------------------------------------------
# EDA
# ---------------------------------------------------------------------------

def run_eda(df: pd.DataFrame, y: np.ndarray, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    print("\n=== Summary statistics (numeric features) ===")
    print(df[config.FEATURE_COLS].describe().T)

    print("\n=== Class distribution ===")
    vc = pd.Series(y).value_counts().sort_index()
    names = list(config.PAD_LEVEL_CLASSES)
    for i, c in enumerate(names):
        n = int(vc.get(i, 0))
        print(f"  {c}: {n} ({100.0 * n / len(y):.1f}%)")

    fig, ax = plt.subplots(figsize=(6, 4))
    uc, cnt = np.unique(y, return_counts=True)
    ax.bar([names[int(u)] for u in uc], cnt, color="steelblue", edgecolor="black")
    ax.set_title("pad_level class distribution")
    ax.set_xlabel("pad_level")
    plt.tight_layout()
    p1 = os.path.join(out_dir, "pad_level_class_distribution.png")
    plt.savefig(p1, dpi=120)
    plt.close()
    print(f"Saved: {p1}")

    # Correlation with encoded target
    Xnum = df[config.FEATURE_COLS].copy()
    Xnum["_target"] = y
    s = Xnum.corr(numeric_only=True)["_target"].drop("_target")
    corr = s.reindex(s.abs().sort_values(ascending=False).index)
    print("\n=== Correlation |feature| vs target (encoded 0–3) ===")
    print(corr.to_string())

    plt.figure(figsize=(8, 5))
    sns.heatmap(
        Xnum.corr(numeric_only=True),
        cmap="coolwarm",
        center=0,
        annot=False,
        fmt=".2f",
    )
    plt.title("Feature correlation matrix (incl. encoded target)")
    plt.tight_layout()
    p2 = os.path.join(out_dir, "pad_level_feature_correlation.png")
    plt.savefig(p2, dpi=120)
    plt.close()
    print(f"Saved: {p2}")


# ---------------------------------------------------------------------------
# Model training & search
# ---------------------------------------------------------------------------

def _make_cv():
    return StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)


def tune_random_forest(X: np.ndarray, y: np.ndarray) -> Tuple[Pipeline, float, Dict[str, Any]]:
    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "clf",
                RandomForestClassifier(
                    random_state=RANDOM_STATE,
                    class_weight="balanced_subsample",
                    n_jobs=-1,
                ),
            ),
        ]
    )
    param_dist = {
        "clf__n_estimators": [200, 350, 500, 700],
        "clf__max_depth": [12, 20, 28, 36, None],
        "clf__min_samples_leaf": [1, 2, 4, 8],
        "clf__max_features": ["sqrt", "log2", 0.35, 0.5],
    }
    search = RandomizedSearchCV(
        pipe,
        param_distributions=param_dist,
        n_iter=N_ITER_SEARCH,
        cv=_make_cv(),
        scoring=make_scorer(f1_score, average="macro"),
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbose=0,
    )
    search.fit(X, y)
    best = search.best_estimator_
    cv_acc = cross_val_score(
        best, X, y, cv=_make_cv(), scoring="accuracy", n_jobs=-1
    ).mean()
    return best, float(cv_acc), {"best_params": search.best_params_, "best_cv_f1_macro": search.best_score_}


def tune_hist_gradient_boosting(
    X: np.ndarray, y: np.ndarray
) -> Tuple[Pipeline, float, Dict[str, Any]]:
    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "clf",
                HistGradientBoostingClassifier(
                    random_state=RANDOM_STATE,
                    class_weight="balanced",
                ),
            ),
        ]
    )
    param_dist = {
        "clf__max_depth": [8, 12, 16, 20],
        "clf__max_iter": [250, 400, 550],
        "clf__learning_rate": [0.03, 0.06, 0.1],
        "clf__min_samples_leaf": [10, 20, 40],
        "clf__l2_regularization": [0.0, 0.1, 0.5, 1.0],
    }
    search = RandomizedSearchCV(
        pipe,
        param_distributions=param_dist,
        n_iter=N_ITER_SEARCH,
        cv=_make_cv(),
        scoring=make_scorer(f1_score, average="macro"),
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbose=0,
    )
    search.fit(X, y)
    best = search.best_estimator_
    cv_acc = cross_val_score(
        best, X, y, cv=_make_cv(), scoring="accuracy", n_jobs=-1
    ).mean()
    return best, float(cv_acc), {"best_params": search.best_params_, "best_cv_f1_macro": search.best_score_}


def tune_xgboost(X: np.ndarray, y: np.ndarray) -> Optional[Tuple[Pipeline, float, Dict[str, Any]]]:
    try:
        from xgboost import XGBClassifier
    except ImportError:
        return None

    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "clf",
                XGBClassifier(
                    random_state=RANDOM_STATE,
                    objective="multi:softprob",
                    num_class=config.NUM_PAD_CLASSES,
                    eval_metric="mlogloss",
                    tree_method="hist",
                    n_jobs=-1,
                ),
            ),
        ]
    )
    param_dist = {
        "clf__n_estimators": [200, 400, 600],
        "clf__max_depth": [4, 6, 8, 10],
        "clf__learning_rate": [0.03, 0.06, 0.12],
        "clf__subsample": [0.7, 0.85, 1.0],
        "clf__colsample_bytree": [0.6, 0.8, 1.0],
        "clf__min_child_weight": [1, 3, 7],
        "clf__reg_lambda": [0.5, 1.0, 2.0],
    }
    search = RandomizedSearchCV(
        pipe,
        param_distributions=param_dist,
        n_iter=N_ITER_SEARCH,
        cv=_make_cv(),
        scoring=make_scorer(f1_score, average="macro"),
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbose=0,
    )
    search.fit(X, y)
    best = search.best_estimator_
    cv_acc = cross_val_score(
        best, X, y, cv=_make_cv(), scoring="accuracy", n_jobs=-1
    ).mean()
    return best, float(cv_acc), {"best_params": search.best_params_, "best_cv_f1_macro": search.best_score_}


def tune_mlp_dnn(X: np.ndarray, y: np.ndarray) -> Tuple[Pipeline, float, Dict[str, Any]]:
    """Feedforward network (sklearn MLP); early stopping reduces overfitting."""
    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "clf",
                MLPClassifier(
                    random_state=RANDOM_STATE,
                    max_iter=800,
                    early_stopping=True,
                    validation_fraction=0.15,
                    n_iter_no_change=40,
                    learning_rate_init=1e-3,
                    alpha=1e-3,
                ),
            ),
        ]
    )
    param_dist = {
        "clf__hidden_layer_sizes": [(128, 64), (256, 128), (256, 128, 64), (128,)],
        "clf__alpha": [1e-4, 1e-3, 1e-2],
        "clf__learning_rate_init": [5e-4, 1e-3, 2e-3],
    }
    search = RandomizedSearchCV(
        pipe,
        param_distributions=param_dist,
        n_iter=min(20, N_ITER_SEARCH),
        cv=_make_cv(),
        scoring=make_scorer(f1_score, average="macro"),
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbose=0,
    )
    search.fit(X, y)
    best = search.best_estimator_
    cv_acc = cross_val_score(
        best, X, y, cv=_make_cv(), scoring="accuracy", n_jobs=-1
    ).mean()
    return best, float(cv_acc), {"best_params": search.best_params_, "best_cv_f1_macro": search.best_score_}


def feature_importance_summary(
    pipeline: Pipeline, feature_names: List[str], model_name: str
) -> str:
    clf = pipeline.named_steps["clf"]
    if hasattr(clf, "feature_importances_"):
        imp = clf.feature_importances_
        order = np.argsort(imp)[::-1]
        lines = [f"Feature importance ({model_name}):"]
        for i in order[:12]:
            lines.append(f"  {feature_names[i]}: {imp[i]:.4f}")
        return "\n".join(lines)
    return f"No feature_importances_ for {model_name} (e.g. MLP)."


def main() -> PadLevelPredictorBundle:
    print("Dataset:", config.DATASET_PATH)
    df = read_dataset_file(sync_labels_from_rules=False)
    df = apply_deterministic_pad_labels(df, save_bins=True)

    y_raw = (
        df[config.COL_PAD_LEVEL].astype(str).str.strip().str.upper()
    )
    class_to_idx = {c: i for i, c in enumerate(config.PAD_LEVEL_CLASSES)}
    y = y_raw.map(lambda s: class_to_idx.get(s, 0)).astype(np.int32).values

    X_df, feature_names = engineer_features(df)
    X = X_df.values.astype(np.float32)

    run_eda(df, y, config.PLOTS_DIR)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        stratify=y,
        random_state=RANDOM_STATE,
    )

    results: List[Tuple[str, Pipeline, float, Dict[str, Any]]] = []

    print("\n=== Tuning Random Forest ===")
    pipe_rf, cv_rf, meta_rf = tune_random_forest(X_train, y_train)
    results.append(("RandomForest", pipe_rf, cv_rf, meta_rf))
    print(f"  CV accuracy (mean, {CV_FOLDS}-fold): {cv_rf:.4f}")
    print(f"  best params: {meta_rf.get('best_params')}")

    print("\n=== Tuning HistGradientBoosting ===")
    pipe_hgb, cv_hgb, meta_hgb = tune_hist_gradient_boosting(X_train, y_train)
    results.append(("HistGradientBoosting", pipe_hgb, cv_hgb, meta_hgb))
    print(f"  CV accuracy (mean): {cv_hgb:.4f}")

    xgb_out = tune_xgboost(X_train, y_train)
    if xgb_out is not None:
        pipe_xgb, cv_xgb, meta_xgb = xgb_out
        results.append(("XGBoost", pipe_xgb, cv_xgb, meta_xgb))
        print("\n=== Tuning XGBoost ===")
        print(f"  CV accuracy (mean): {cv_xgb:.4f}")
    else:
        print("\n=== XGBoost skipped (install xgboost) ===")

    print("\n=== Tuning MLP (DNN) ===")
    pipe_mlp, cv_mlp, meta_mlp = tune_mlp_dnn(X_train, y_train)
    results.append(("MLP_DNN", pipe_mlp, cv_mlp, meta_mlp))
    print(f"  CV accuracy (mean): {cv_mlp:.4f}")

    # Pick best by CV accuracy
    best_name, best_pipe, best_cv_acc, best_meta = max(results, key=lambda r: r[2])
    print(f"\n*** Best model by CV accuracy: {best_name} ({best_cv_acc:.4f}) ***")

    # Refit best architecture on full train+val (train split only was used for search; refit on all X_train)
    best_pipe.fit(X_train, y_train)

    y_pred = best_pipe.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)

    report = classification_report(
        y_test,
        y_pred,
        target_names=list(config.PAD_LEVEL_CLASSES),
        zero_division=0,
    )
    cm = confusion_matrix(y_test, y_pred)

    print("\n=== Hold-out test set ===")
    print(f"Accuracy:  {acc:.4f}")
    print(f"Macro F1:  {macro_f1:.4f}")
    print(f"Weighted F1: {weighted_f1:.4f}")
    print("\nConfusion matrix:\n", cm)
    print("\n", report)

    fi_text = feature_importance_summary(best_pipe, feature_names, best_name)
    print("\n", fi_text)

    bundle = PadLevelPredictorBundle(
        pipeline=best_pipe,
        feature_names=feature_names,
        model_name=best_name,
        cv_accuracy_mean=best_cv_acc,
        test_accuracy=float(acc),
        report=report,
    )

    joblib.dump(bundle, config.BEST_PAD_CLASSIFIER_BUNDLE_PATH)
    print(f"\nSaved bundle: {config.BEST_PAD_CLASSIFIER_BUNDLE_PATH}")

    meta_path = os.path.join(config.DATA_DIR, "pad_level_ml_pipeline_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "best_model": best_name,
                "cv_accuracy_mean": best_cv_acc,
                "test_accuracy": acc,
                "macro_f1": macro_f1,
                "weighted_f1": weighted_f1,
                "feature_names": feature_names,
                "best_params": best_meta,
                "confusion_matrix": cm.tolist(),
            },
            f,
            indent=2,
        )
    print(f"Saved meta: {meta_path}")

    report_path = os.path.join(config.DATA_DIR, "pad_level_ml_pipeline_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("Pad level ML pipeline — test evaluation\n")
        f.write(f"Best model: {best_name}\n")
        f.write(f"CV accuracy (~{CV_FOLDS}-fold): {best_cv_acc:.4f}\n")
        f.write(f"Hold-out accuracy: {acc:.4f}\n\n")
        f.write(fi_text)
        f.write("\n\n")
        f.write(report)
    print(f"Saved report: {report_path}")

    return bundle


def predict_pad_level_proba(
    temp: float,
    pulse: float,
    motion: float,
    age: float,
    height: float,
    weight: float,
    gender: float,
    bundle_path: Optional[str] = None,
) -> np.ndarray:
    """Load saved bundle and return class probabilities."""
    path = bundle_path or config.BEST_PAD_CLASSIFIER_BUNDLE_PATH
    bundle: PadLevelPredictorBundle = joblib.load(path)
    return bundle.predict_proba(temp, pulse, motion, age, height, weight, gender)


if __name__ == "__main__":
    main()
