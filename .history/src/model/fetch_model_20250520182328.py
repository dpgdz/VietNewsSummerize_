import os
import yaml
import mlflow
from mlflow.tracking import MlflowClient
from transformers import AutoTokenizer, MBartForConditionalGeneration

# Load config
with open("src/config/config_model.yaml") as f:
    config = yaml.safe_load(f)

def fetch_model_from_logged_artifact(alias="Production"):
    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    model_name = config["mlflow"]["model_name"]
    artifact_name = config["paths"]["artifacts_path"]
    model_class = config["model"]["model_class"]

    client = MlflowClient()
    version = client.get_model_version_by_alias(model_name, alias)
    run_id = version.run_id
    experiment_id = version.source.split("/")[1]  

    artifact_uri= f"mlflow-artifacts://{experiment_id}/{run_id}/{artifact_name}"

    local = client.download_artifacts(
        run_id=run_id,
        path=artifact_name,
        dst_path="testtesttesst"
    )

if __name__ == "__main__":
    model, tokenizer = fetch_model_from_logged_artifact()
