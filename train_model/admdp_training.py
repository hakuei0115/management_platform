from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from admdp_dataset import PASS_STATE, AdmdpDatasetConfig, build_admdp_transitions, load_transition_excel


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_POLICY_PATH = PROJECT_ROOT / "model" / "admdp_policy.pkl"


@dataclass
class AdmdpTrainingConfig:
    gamma: float = 0.85
    max_iterations: int = 1000
    tolerance: float = 1e-6
    min_action_count: int = 1


@dataclass
class AdmdpTrainingResult:
    policy: pd.DataFrame
    q_table: pd.DataFrame
    transition_model: pd.DataFrame
    metadata: dict[str, Any]
    model_path: Path


def train_admdp_policy(
    transitions: pd.DataFrame,
    *,
    model_path: str | Path = DEFAULT_POLICY_PATH,
    config: AdmdpTrainingConfig | None = None,
) -> AdmdpTrainingResult:
    config = config or AdmdpTrainingConfig()
    clean = clean_transition_frame(transitions)
    validate_transitions(clean)

    transition_model = estimate_transition_model(clean, min_action_count=config.min_action_count)
    values, q_table = value_iteration(transition_model, config=config)
    policy = build_policy(q_table, clean)

    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "model_name": "ADMDP",
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "transition_rows": int(len(clean)),
        "state_count": int(pd.concat([clean["state_before"], clean["state_after"]]).nunique()),
        "action_count": int(clean["action"].nunique()),
        "absorbing_transitions": int(clean["is_absorbing"].sum()),
        "absorbing_rate": float(clean["is_absorbing"].mean()),
        "avg_reward": float(clean["reward"].mean()),
        "gamma": config.gamma,
        "iterations": int(q_table.attrs.get("iterations", 0)),
        "converged": bool(q_table.attrs.get("converged", False)),
        "min_action_count": config.min_action_count,
    }

    payload = {
        "policy": policy,
        "q_table": q_table,
        "transition_model": transition_model,
        "values": values,
        "metadata": metadata,
    }
    joblib.dump(payload, model_path)

    return AdmdpTrainingResult(
        policy=policy,
        q_table=q_table,
        transition_model=transition_model,
        metadata=metadata,
        model_path=model_path,
    )


def train_admdp_from_excel(
    input_path: str | Path,
    *,
    sheet_name: str | None = None,
    model_path: str | Path = DEFAULT_POLICY_PATH,
    dataset_config: AdmdpDatasetConfig | None = None,
    training_config: AdmdpTrainingConfig | None = None,
) -> tuple[pd.DataFrame, AdmdpTrainingResult]:
    frame = load_transition_excel(input_path, sheet_name=sheet_name)
    transition_result = build_admdp_transitions(frame, config=dataset_config)
    training_result = train_admdp_policy(
        transition_result.transitions,
        model_path=model_path,
        config=training_config,
    )
    return transition_result.transitions, training_result


def clean_transition_frame(transitions: pd.DataFrame) -> pd.DataFrame:
    frame = transitions.copy()
    required = ["state_before", "action", "state_after", "reward", "is_absorbing"]
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError("缺少必要 transition 欄位：" + ", ".join(missing))

    frame = frame.dropna(subset=["state_before", "action", "state_after", "reward"])
    frame["state_before"] = frame["state_before"].astype(str).str.strip()
    frame["action"] = frame["action"].astype(str).str.strip()
    frame["state_after"] = frame["state_after"].astype(str).str.strip()
    frame["reward"] = pd.to_numeric(frame["reward"], errors="coerce")
    frame = frame.dropna(subset=["reward"])
    frame["is_absorbing"] = frame["is_absorbing"].map(to_bool)
    frame = frame[(frame["state_before"] != "") & (frame["action"] != "") & (frame["state_after"] != "")]
    return frame.reset_index(drop=True)


def validate_transitions(transitions: pd.DataFrame) -> None:
    if transitions.empty:
        raise ValueError("ADMDP transition 資料為空")
    if transitions["state_before"].nunique() < 1:
        raise ValueError("state_before 數量不足")
    if transitions["action"].nunique() < 1:
        raise ValueError("action 數量不足")


def estimate_transition_model(transitions: pd.DataFrame, *, min_action_count: int) -> pd.DataFrame:
    grouped = (
        transitions.groupby(["state_before", "action", "state_after"], dropna=False)
        .agg(
            count=("reward", "size"),
            reward=("reward", "mean"),
            is_absorbing=("is_absorbing", "max"),
        )
        .reset_index()
    )
    action_counts = (
        grouped.groupby(["state_before", "action"], dropna=False)["count"]
        .sum()
        .reset_index(name="state_action_count")
    )
    model = grouped.merge(action_counts, on=["state_before", "action"], how="left")
    model = model[model["state_action_count"] >= min_action_count].copy()
    model["probability"] = model["count"] / model["state_action_count"]
    return model.reset_index(drop=True)


def value_iteration(
    transition_model: pd.DataFrame,
    *,
    config: AdmdpTrainingConfig,
) -> tuple[dict[str, float], pd.DataFrame]:
    states = set(transition_model["state_before"]).union(set(transition_model["state_after"]))
    absorbing_states = set(transition_model.loc[transition_model["is_absorbing"], "state_after"])
    absorbing_states.add(PASS_STATE)

    values = {state: 0.0 for state in states}
    grouped = {
        state: state_frame
        for state, state_frame in transition_model.groupby("state_before", sort=False)
    }

    converged = False
    iterations = 0
    for iteration in range(1, config.max_iterations + 1):
        iterations = iteration
        delta = 0.0
        next_values = values.copy()
        for state, state_frame in grouped.items():
            if state in absorbing_states:
                continue

            q_values = []
            for _, action_frame in state_frame.groupby("action", sort=False):
                q_values.append(compute_q_value(action_frame, values, absorbing_states, config.gamma))

            if not q_values:
                continue

            best_value = max(q_values)
            delta = max(delta, abs(best_value - values[state]))
            next_values[state] = best_value

        values = next_values
        if delta < config.tolerance:
            converged = True
            break

    q_records = []
    for state, state_frame in grouped.items():
        for action, action_frame in state_frame.groupby("action", sort=False):
            q_records.append(
                {
                    "state": state,
                    "action": action,
                    "q_value": compute_q_value(action_frame, values, absorbing_states, config.gamma),
                    "visits": int(action_frame["count"].sum()),
                    "avg_immediate_reward": float(
                        (action_frame["reward"] * action_frame["probability"]).sum()
                    ),
                    "absorbing_probability": float(
                        action_frame.loc[action_frame["is_absorbing"], "probability"].sum()
                    ),
                }
            )

    q_table = pd.DataFrame(q_records)
    if not q_table.empty:
        q_table = q_table.sort_values(["state", "q_value", "visits"], ascending=[True, False, False]).reset_index(
            drop=True
        )
    q_table.attrs["iterations"] = iterations
    q_table.attrs["converged"] = converged
    return values, q_table


def compute_q_value(
    action_frame: pd.DataFrame,
    values: dict[str, float],
    absorbing_states: set[str],
    gamma: float,
) -> float:
    total = 0.0
    for _, row in action_frame.iterrows():
        state_after = row["state_after"]
        future_value = 0.0 if row["is_absorbing"] or state_after in absorbing_states else values.get(state_after, 0.0)
        total += row["probability"] * (row["reward"] + gamma * future_value)
    return float(total)


def build_policy(q_table: pd.DataFrame, transitions: pd.DataFrame) -> pd.DataFrame:
    if q_table.empty:
        return pd.DataFrame(
            columns=["state", "best_action", "q_value", "visits", "avg_immediate_reward", "absorbing_probability"]
        )

    policy = q_table.sort_values(["state", "q_value", "visits"], ascending=[True, False, False]).drop_duplicates(
        "state", keep="first"
    )

    state_counts = transitions["state_before"].value_counts().rename_axis("state").reset_index(name="state_visits")
    policy = policy.rename(columns={"action": "best_action"}).merge(state_counts, on="state", how="left")
    return policy.reset_index(drop=True)


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def load_transitions(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="訓練 ADMDP policy")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--transitions", help="ADMDP transition CSV 路徑")
    input_group.add_argument("--excel", help="合併後訓練 Excel 路徑")
    parser.add_argument("--sheet", default=None, help="Excel 工作表名稱")
    parser.add_argument("--model", default=str(DEFAULT_POLICY_PATH), help="輸出 policy pkl 路徑")
    parser.add_argument("--gamma", type=float, default=0.85, help="折扣係數")
    parser.add_argument("--leak-threshold", type=float, default=0.0, help="洩漏量變化門檻")
    parser.add_argument("--min-action-count", type=int, default=1, help="保留 action 的最小出現次數")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    training_config = AdmdpTrainingConfig(gamma=args.gamma, min_action_count=args.min_action_count)

    if args.transitions:
        transitions = load_transitions(args.transitions)
        result = train_admdp_policy(transitions, model_path=args.model, config=training_config)
    else:
        dataset_config = AdmdpDatasetConfig(leak_threshold=args.leak_threshold)
        transitions, result = train_admdp_from_excel(
            args.excel,
            sheet_name=args.sheet,
            model_path=args.model,
            dataset_config=dataset_config,
            training_config=training_config,
        )

    print("ADMDP training summary:")
    for key, value in result.metadata.items():
        print(f"  {key}: {value}")
    print("\nPolicy preview:")
    print(result.policy.head(10))
    print(f"\nSaved: {result.model_path}")


if __name__ == "__main__":
    main()
