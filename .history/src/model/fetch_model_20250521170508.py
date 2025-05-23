import os
import yaml
import mlflow
from mlflow.tracking import MlflowClient
from transformers import AutoTokenizer, MBartForConditionalGeneration
from functools import lru_cache

@lru_cache(maxsize=1)
def load_config():
    with open("src/config/config_model.yaml") as f:
        return yaml.safe_load(f)

config = load_config()

def fetch_model_from_logged_artifact(alias="Production"):
    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    model_name = config["mlflow"]["model_name"]
    artifact_path = config["paths"]["artifacts_path"]
    fetch_path = config["paths"]["fetch_cache_dir"]

    client = MlflowClient()

    print(f"Fetching model '{model_name}' from alias: {alias}")
    version = client.get_model_version_by_alias(model_name, alias)
    artifact_uri = version.source
    print(f"Artifact URI: {artifact_uri}")

    local_dir = mlflow.artifacts.download_artifacts(
        artifact_uri=artifact_uri,
        dst_path=fetch_path
    )

    print(f"Downloaded to: {local_dir}")

    tokenizer = AutoTokenizer.from_pretrained(local_dir)
    model = MBartForConditionalGeneration.from_pretrained(local_dir)
    return model, tokenizer

if __name__ == "__main__":
    model, tokenizer = fetch_model_from_logged_artifact(alias="Production")
    print("Model and tokenizer loaded successfully.")
