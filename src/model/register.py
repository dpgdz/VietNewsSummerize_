import os
import sys
import yaml
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
with open("src/config/config_model.yaml") as f:
    config = yaml.safe_load(f)

import argparse
import mlflow
from transformers import AutoTokenizer, MBartForConditionalGeneration
from mlflow.tracking import MlflowClient

def register_model(source_name: str, model_dir: str, alias: str = "Staging", rouge: int = 0, training_run_id: str = None):
    model_name = config["mlflow"]["model_name"]
    artifact_path = f"{source_name}_retrain"
    tracking_uri = config["mlflow"]["tracking_uri"]
    source_tag = source_name

    if not os.path.exists(model_dir):
        raise FileNotFoundError(f"Model path not found: {model_dir}")

    model_files_dir = os.path.join(model_dir, "model_files")
    if os.path.isdir(model_files_dir):
        print(f"Found 'model_files' subfolder, registering from: {model_files_dir}")
        model_dir = model_files_dir

    print(f"Registering model from: {model_dir}")

    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient()
    # tokenizer = AutoTokenizer.from_pretrained(model_dir)
    experiment_name = "model-register"
    experiment = client.get_experiment_by_name(experiment_name)
    experiment_id = experiment.experiment_id if experiment else client.create_experiment(experiment_name)

    run = client.create_run(experiment_id=experiment_id)
    run_id = run.info.run_id 
    run_name = f"{source_name}_model_{alias}_dir_{os.path.basename(model_dir)}"
    client.update_run(run_id, name=run_name)


    client.set_tag(run_id, "pipeline", "registration")
    client.set_tag(run_id, "model_source", source_name)
    client.set_tag(run_id, "alias", alias)
    client.set_tag(run_id, "dashboard", "true")
    client.set_tag(run_id, "task", "register")
    client.set_tag(run_id, "stage", "finalize")
    client.set_tag(run_id, "owner", "registry-bot")

    allowed_exts = {".bin", ".json", ".txt", ".model", ".vocab", ".config", ".safetensors"}
    allowed_files = []
    for root, _, files in os.walk(model_dir):
        for file in files:
            if file.startswith("optimizer") or file.startswith("trainer_state"):
                continue
            if os.path.splitext(file)[1] in allowed_exts:
                allowed_files.append(os.path.join(root, file))

    import tempfile
    import shutil
    with tempfile.TemporaryDirectory() as temp_dir:
        for file_path in allowed_files:
            rel_path = os.path.relpath(file_path, model_dir)
            dest_path = os.path.join(temp_dir, rel_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(file_path, dest_path)
        client.log_artifacts(run_id=run_id, local_dir=temp_dir, artifact_path=artifact_path)

    model_uri = f"runs:/{run_id}/{artifact_path}"
    print(f"Model URI: {model_uri}")

    result = mlflow.register_model(model_uri=model_uri, name=model_name)

    import time
    for _ in range(10):
        model_ver = client.get_model_version(name=model_name, version=result.version)
        if model_ver.status == "READY":
            break
        time.sleep(1)

    try:
        existing = client.get_model_version_by_alias(model_name, alias)
        if existing:
            client.delete_registered_model_alias(name=model_name, alias=alias)
    except Exception as e:
        print(f"[WARN] No alias to delete: {e}")

    client.set_registered_model_alias(
        name=model_name,
        alias=alias,
        version=result.version
    )

    client.set_model_version_tag(name=model_name, version=result.version, key="source model", value=model_name)
    client.set_model_version_tag(name=model_name, version=result.version, key="source tag", value=source_tag)
    client.set_model_version_tag(name=model_name, version=result.version, key="source path", value=model_dir)
    client.set_model_version_tag(name=model_name, version=result.version, key="rougeL", value=str(rouge))
    client.set_model_version_tag(name=model_name, version=result.version, key="model_version", value=alias)
    
    if training_run_id:
        client.set_model_version_tag(
            name=model_name,
            version=result.version,
            key="training_run_id",
            value=training_run_id
        )

        tracking_ui = config["mlflow"]["tracking_uri"].rstrip("/")
        training_url = f"{tracking_ui}/#/experiments/{experiment_id}/runs/{training_run_id}"
        client.set_model_version_tag(
            name=model_name,
            version=result.version,
            key="training_run_url",
            value=training_url
        )


    client.set_terminated(run_id, status="FINISHED")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=str, required=True, help="model source name: bartpho-base / pretrain / production")
    parser.add_argument("--model_dir", type=str, required=True, help="directory path to trained model")
    parser.add_argument("--alias", type=str, default="Staging", help="alias to set in registry (optional)")
    parser.add_argument("--verbose", action='store_true', help="enable verbose output")
    args = parser.parse_args()

    register_model(args.source, args.model_dir, alias=args.alias)
    
    if args.verbose:
        print(f"Model source: {args.source}, Model directory: {args.model_dir}, Alias: {args.alias}")