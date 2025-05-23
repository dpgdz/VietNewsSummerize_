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
max_len = config["predict"]["max_length"]

def generate_summaries(model, tokenizer, articles, max_len=max_len):
    inputs = tokenizer(articles, return_tensors="pt", padding=True, truncation=True, max_length=max_len)
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

def daily_summarize():
    print("Running daily summerize...")
    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    client = MlflowClient()

    model, tokenizer = fetch_model_from_logged_artifact()

    dataset_path = config["predict"]["data_path"]
    df = pd.read_csv(dataset_path)
    articles = df["article"].tolist()
    references = df["summary"].tolist()

    preds = generate_summaries(model, tokenizer, articles, config["predict"]["max_length"])

    df["predicted_summary"] = preds
    df.to_csv(config["predict"]["output_path"], index=False)

    experiment = client.get_experiment_by_name(config["mlflow"]["experiment_name"])
    if experiment is None:
        experiment_id = client.create_experiment(config["mlflow"]["experiment_name"])
    else:
        experiment_id = experiment.experiment_id
    run = client.create_run(experiment_id=experiment_id)
    run_id = run.info.run_id
    client.log_param(run_id, "predict", "daily")
    client.log_param(run_id, "model_source", "production")
    client.log_param(run_id, "raw_data_path", dataset_path)
    client.log_param(run_id, "output_path", config["predict"]["output_path"])
    client.log_param(run_id, "timestamp", datetime.now().isoformat())


if __name__ == "__main__":
    daily_summarize()
