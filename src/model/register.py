import os
import sys
import yaml

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
with open("src/config/config_model.yaml") as f:
    config = yaml.safe_load(f)

import argparse
import mlflow
from transformers import AutoTokenizer, MBartForConditionalGeneration
from mlflow.tracking import MlflowClient

def register_model(source_name: str, model_dir: str, alias: str = "Staging", rouge: int = 0):
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
    experiment = client.get_experiment_by_name(config["mlflow"]["experiment_name"])
    if experiment is None:
        experiment_id = client.create_experiment(config["mlflow"]["experiment_name"])
    else:
        experiment_id = experiment.experiment_id

    run_name = f"{source_name}_model_{alias}_dir_{os.path.basename(model_dir)}"
    run = client.create_run(experiment_id=experiment_id, tags={"run_name": run_name})
    run_id = run.info.run_id

    allowed_exts = {".bin", ".json", ".txt", ".model", ".vocab", ".config,",".safetensors"}
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