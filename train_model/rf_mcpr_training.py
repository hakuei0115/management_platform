from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from scipy.sparse import issparse, vstack
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support, precision_score, recall_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.preprocessing import LabelEncoder, OneHotEncoder


def oversample_minority_classes(
    x_data: Any,
    y_data: np.ndarray,
    *,
    min_samples: int = 5,
    random_state: int = 42,
) -> tuple[Any, np.ndarray]:
    """針對樣本數少於 min_samples 的類別進行離散過採樣 (Random Oversampling)"""
    if len(y_data) == 0:
        return x_data, y_data

    np.random.seed(random_state)
    unique_classes, counts = np.unique(y_data, return_counts=True)

    x_parts = [x_data]
    y_parts = [y_data]

    for cls, count in zip(unique_classes, counts):
        if count < min_samples:
            needed = min_samples - count
            cls_indices = np.where(y_data == cls)[0]
            sampled_indices = np.random.choice(cls_indices, size=needed, replace=True)
            x_parts.append(x_data[sampled_indices])
            y_parts.append(y_data[sampled_indices])

    if issparse(x_data):
        x_res = vstack(x_parts)
    else:
        x_res = np.vstack(x_parts)

    y_res = np.concatenate(y_parts)
    return x_res, y_res


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL_PATH = PROJECT_ROOT / "model" / "rf_mcpr.pkl"

FEATURE_COL = "NG項"
TARGET_COL = "維修建議"
GROUP_COL = "異常編號"


@dataclass
class TrainingResult:
    metrics: dict[str, Any]
    class_metrics: list[dict[str, Any]]
    top_ng_counts: list[dict[str, Any]]
    top_repair_counts: list[dict[str, Any]]
    model_path: Path


def train_rf_mcpr(
    rules: pd.DataFrame,
    *,
    model_path: str | Path = DEFAULT_MODEL_PATH,
    n_estimators: int = 300,
    test_size: float = 0.2,
    random_state: int = 42,
) -> TrainingResult:
    data = clean_rules(rules)
    validate_rules(data)

    split = make_eval_split(data, test_size=test_size, random_state=random_state)
    eval_metrics, class_metrics = evaluate_model(
        data,
        split=split,
        n_estimators=n_estimators,
        random_state=random_state,
    )

    model, onehot_encoder, label_encoder = fit_final_model(
        data,
        n_estimators=n_estimators,
        random_state=random_state,
    )

    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "model_name": "RF-MCPR",
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "training_rows": int(len(data)),
        "unique_ng_items": int(data[FEATURE_COL].nunique()),
        "unique_repairs": int(data[TARGET_COL].nunique()),
        "n_estimators": n_estimators,
        "test_size": test_size,
        "split_strategy": eval_metrics["split_strategy"],
    }
    joblib.dump(
        {
            "model": model,
            "onehot_encoder": onehot_encoder,
            "label_encoder": label_encoder,
            "metadata": metadata,
        },
        model_path,
    )

    metrics = {**eval_metrics, **metadata}
    return TrainingResult(
        metrics=metrics,
        class_metrics=class_metrics,
        top_ng_counts=value_counts_as_records(data[FEATURE_COL], limit=8),
        top_repair_counts=value_counts_as_records(data[TARGET_COL], limit=8),
        model_path=model_path,
    )


def clean_rules(rules: pd.DataFrame) -> pd.DataFrame:
    data = rules.copy()
    data = data.dropna(subset=[FEATURE_COL, TARGET_COL])
    data[FEATURE_COL] = data[FEATURE_COL].astype(str).str.strip()
    data[TARGET_COL] = data[TARGET_COL].astype(str).str.strip()
    data = data[(data[FEATURE_COL] != "") & (data[TARGET_COL] != "")]
    return data.reset_index(drop=True)


def validate_rules(data: pd.DataFrame) -> None:
    missing = sorted({FEATURE_COL, TARGET_COL} - set(data.columns))
    if missing:
        raise ValueError("缺少必要欄位：" + ", ".join(missing))
    if len(data) < 2:
        raise ValueError("可訓練資料少於 2 筆")
    if data[TARGET_COL].nunique() < 2:
        raise ValueError("維修建議類別少於 2 種，無法訓練分類模型")


def make_eval_split(data: pd.DataFrame, *, test_size: float, random_state: int) -> dict[str, Any] | None:
    if len(data) < 5:
        return None

    # 稀有類別保護 (Rare Class Protection):
    # 若某個類別總樣本數 <= 2 筆，強制分配至少 1 筆至訓練集 (train_idx)，避免測試集中包含訓練集未學過的類別
    class_counts = data[TARGET_COL].value_counts()
    rare_classes = set(class_counts[class_counts <= 2].index)

    protected_train_indices = []
    evaluable_indices = []

    for cls in data[TARGET_COL].unique():
        cls_indices = data[data[TARGET_COL] == cls].index.tolist()
        if cls in rare_classes:
            protected_train_indices.append(cls_indices[0])
            evaluable_indices.extend(cls_indices[1:])
        else:
            evaluable_indices.extend(cls_indices)

    if not evaluable_indices:
        evaluable_indices = data.index.tolist()
        protected_train_indices = []

    sub_data = data.loc[evaluable_indices]

    if GROUP_COL in sub_data.columns and sub_data[GROUP_COL].nunique() >= 5:
        splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
        sub_train_pos, sub_test_pos = next(splitter.split(sub_data, groups=sub_data[GROUP_COL].astype(str)))
        train_idx = np.unique(np.concatenate([protected_train_indices, sub_data.index[sub_train_pos].to_numpy()]))
        test_idx = sub_data.index[sub_test_pos].to_numpy()
        strategy = "group_holdout_rare_protected"
    else:
        sub_class_counts = sub_data[TARGET_COL].value_counts()
        stratify = sub_data[TARGET_COL] if len(sub_class_counts) > 0 and sub_class_counts.min() >= 2 else None
        sub_train_idx, sub_test_idx = train_test_split(
            sub_data.index.to_numpy(),
            test_size=test_size,
            random_state=random_state,
            stratify=stratify,
        )
        train_idx = np.unique(np.concatenate([protected_train_indices, sub_train_idx]))
        test_idx = sub_test_idx
        strategy = "row_holdout_rare_protected"

    return {
        "train_idx": train_idx,
        "test_idx": test_idx,
        "strategy": strategy,
    }


def evaluate_model(
    data: pd.DataFrame,
    *,
    split: dict[str, Any] | None,
    n_estimators: int,
    random_state: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if split is None:
        return {
            "accuracy": None,
            "precision_weighted": None,
            "recall_weighted": None,
            "f1_weighted": None,
            "precision_macro": None,
            "recall_macro": None,
            "f1_macro": None,
            "train_rows": int(len(data)),
            "test_rows": 0,
            "split_strategy": "not_enough_data",
        }, []

    train = data.iloc[split["train_idx"]]
    test = data.iloc[split["test_idx"]]

    onehot_encoder = OneHotEncoder(handle_unknown="ignore")
    label_encoder = LabelEncoder().fit(data[TARGET_COL])

    x_train = onehot_encoder.fit_transform(train[[FEATURE_COL]])
    y_train = label_encoder.transform(train[TARGET_COL])
    x_test = onehot_encoder.transform(test[[FEATURE_COL]])
    y_test = label_encoder.transform(test[TARGET_COL])

    model = RandomForestClassifier(
        n_estimators=n_estimators,
        random_state=random_state,
        class_weight="balanced_subsample",
    )
    model.fit(x_train, y_train)
    y_pred = model.predict(x_test)

    labels = list(range(len(label_encoder.classes_)))
    precision, recall, f1, support = precision_recall_fscore_support(
        y_test,
        y_pred,
        labels=labels,
        zero_division=0,
    )

    class_metrics = []
    for index, label in enumerate(label_encoder.classes_):
        if int(support[index]) == 0:
            continue
        class_metrics.append(
            {
                "label": label,
                "precision": float(precision[index]),
                "recall": float(recall[index]),
                "f1": float(f1[index]),
                "support": int(support[index]),
            }
        )

    # 計算 Top-3 命中率 (使用平衡訓練模型)
    top3_hit = 0
    if hasattr(model, "predict_proba") and len(y_test) > 0:
        probs = model.predict_proba(x_test)
        for i, y_true_val in enumerate(y_test):
            top3_local_indices = np.argsort(probs[i])[-3:]
            top3_global_indices = model.classes_[top3_local_indices]
            if y_true_val in top3_global_indices:
                top3_hit += 1
        top3_accuracy = float(top3_hit / len(y_test))
    else:
        top3_accuracy = float(accuracy_score(y_test, y_pred))

    # 計算袋外評估分 (OOB Score)
    oob_score_val = None
    try:
        oob_clf = RandomForestClassifier(
            n_estimators=n_estimators,
            random_state=random_state,
            class_weight="balanced_subsample",
            oob_score=True,
            bootstrap=True,
        )
        x_all = onehot_encoder.fit_transform(data[[FEATURE_COL]])
        y_all = label_encoder.transform(data[TARGET_COL])
        oob_clf.fit(x_all, y_all)
        oob_score_val = float(oob_clf.oob_score_)
    except Exception:
        pass

    class_metrics.sort(key=lambda item: (-item["support"], item["label"]))

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "top3_accuracy": top3_accuracy,
        "oob_score": oob_score_val,
        "precision_weighted": float(precision_score(y_test, y_pred, average="weighted", zero_division=0)),
        "recall_weighted": float(recall_score(y_test, y_pred, average="weighted", zero_division=0)),
        "f1_weighted": float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
        "precision_macro": float(precision_score(y_test, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_test, y_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_test, y_pred, average="macro", zero_division=0)),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "split_strategy": split["strategy"],
    }
    return metrics, class_metrics


def fit_final_model(
    data: pd.DataFrame,
    *,
    n_estimators: int,
    random_state: int,
) -> tuple[RandomForestClassifier, OneHotEncoder, LabelEncoder]:
    onehot_encoder = OneHotEncoder(handle_unknown="ignore")
    label_encoder = LabelEncoder()

    features = onehot_encoder.fit_transform(data[[FEATURE_COL]])
    target = label_encoder.fit_transform(data[TARGET_COL])

    model = RandomForestClassifier(
        n_estimators=n_estimators,
        random_state=random_state,
        class_weight="balanced_subsample",
    )
    model.fit(features, target)
    return model, onehot_encoder, label_encoder


def value_counts_as_records(series: pd.Series, *, limit: int) -> list[dict[str, Any]]:
    counts = series.value_counts().head(limit)
    return [{"label": str(label), "count": int(count)} for label, count in counts.items()]
