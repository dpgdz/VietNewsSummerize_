import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pandas as pd
from evaluate import load
import mlflow
from datetime import datetime
from transformers import AutoTokenizer, MBartForConditionalGeneration
from src.model.fetch_model import fetch_model_from_logged_artifact
from mlflow.tracking import MlflowClient
import yaml

with open("src/config/config_model.yaml") as f:
    config = yaml.safe_load(f)
THRESHOLD_DROP = config["evaluation"]["threshold_drop"]
max_len = config["predict"]["max_length"]

def generate_summaries(model, tokenizer, contents, max_len=max_len):
    inputs = tokenizer(contents, return_tensors="pt", padding=True, truncation=True, max_length=max_len)
    outputs = model.generate(
        input_ids=inputs["input_ids"],
        attention_mask=inputs["attention_mask"],
        max_length=max_len,
        min_length=20,
        num_beams=4
    )
    return tokenizer.batch_decode(outputs, skip_special_tokens=True)


def compute_metrics(preds, labels,tokenizer):
    rouge = load("rouge")
    results = rouge.compute(predictions=preds, references=labels, use_stemmer=True)
    return {k: round(v * 100, 2) for k, v in results.items()}

def daily_evaluate():
    print("Running daily production evaluation...")
    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    client = MlflowClient()

    model, tokenizer = fetch_model_from_logged_artifact()

    dataset_path = config["evaluation"]["dataset_path"]
    df = pd.read_csv(dataset_path)
    contents = df["content"].tolist()
    references = df["summary"].tolist()

    preds = generate_summaries(model, tokenizer, contents, config["predict"]["max_length"])
    metrics = compute_metrics(preds, references, tokenizer)

    experiment = client.get_experiment_by_name(config["mlflow"]["experiment_name"])
    if experiment is None:
        experiment_id = client.create_experiment(config["mlflow"]["experiment_name"])
    else:
        experiment_id = experiment.experiment_id
    run = client.create_run(experiment_id=experiment_id)
    run_id = run.info.run_id

    client.log_param(run_id, "eval_type", "daily")
    client.log_param(run_id, "model_source", "production")
    client.log_param(run_id, "eval_data", dataset_path)

    for k, v in metrics.items():
        client.log_metric(run_id, k, v)
        print(f"{k}: {v}")

    client.set_terminated(run_id, status="FINISHED")

    baseline_path = "results/baseline_metrics.csv"
    if os.path.exists(baseline_path):
        baseline = pd.read_csv(baseline_path)
        base_rougeL = baseline["rougeL"].values[0]
    else:
        print("Baseline not found. Saving current as baseline.")
        base_rougeL = metrics["rougeL"]
        try:
            os.makedirs(os.path.dirname(baseline_path), exist_ok=True)
            pd.DataFrame([metrics]).to_csv(baseline_path, index=False)
        except Exception as e:
            print(f"Failed to save baseline metrics: {e}")
        return

    drop = base_rougeL - metrics["rougeL"]
    print(f"rougeL drop: {drop:.2f} points")

    if drop > THRESHOLD_DROP:
        print("Performance dropped! Retraining needed.")
        retrain=1
    else:
       retrain=0
    client.log_param(run_id, "retrain", retrain)
    client.log_param(run_id, "drop", drop)
    client.log_param(run_id, "base_rougeL", base_rougeL)
    client.log_param(run_id, "current_rougeL", metrics["rougeL"])

    run_name = f"daily_eval_timestamp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    client.update_run(run_id, name=run_name)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("results", exist_ok=True)
    pd.DataFrame([metrics]).to_csv(f"results/daily_eval_{timestamp}.csv", index=False)

    return retrain

if __name__ == "__main__":
    daily_evaluate()
