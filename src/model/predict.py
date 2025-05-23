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

def daily_summarize():
    print("Running daily summarize...")
    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    client = MlflowClient()

    model, tokenizer = fetch_model_from_logged_artifact()
    model = model.cpu()

    dataset_path = config["predict"]["data_path"]
    df = pd.read_csv(dataset_path)
    contents = df["content"].tolist()

    preds = generate_summaries(model, tokenizer, contents, max_len)

    df["predicted_summary"] = preds
    output_path = config["predict"]["output_path"]
    df.to_csv(output_path, index=False)

    experiment = client.get_experiment_by_name(config["mlflow"]["experiment_name"])
    experiment_id = experiment.experiment_id if experiment else client.create_experiment(config["mlflow"]["experiment_name"])
    run = client.create_run(experiment_id=experiment_id)
    run_id = run.info.run_id

    client.log_param(run_id, "predict", "daily")
    client.log_param(run_id, "model_source", "production")
    client.log_param(run_id, "raw_data_path", dataset_path)
    client.log_param(run_id, "output_path", output_path)
    client.log_param(run_id, "timestamp", datetime.now().isoformat())

    if "summary" in df.columns:
        references = df["summary"].tolist()
        scores = compute_metrics(preds, references, tokenizer)
        for k, v in scores.items():
            client.log_metric(run_id, f"predict_{k}", v)

    client.log_artifact(run_id, output_path)
    client.set_terminated(run_id, status="FINISHED")
    print(f"Finished prediction. Output saved to: {output_path}")


if __name__ == "__main__":
    daily_summarize()
