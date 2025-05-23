import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import mlflow
import mlflow.transformers
from mlflow.tracking import MlflowClient
from transformers import AutoTokenizer, MBartForConditionalGeneration
import os
import yaml

with open("src/config/config_model.yaml") as f:
    config = yaml.safe_load(f)

def register_model(source_name, model_dir, alias):
    tracking_uri = config["mlflow"]["tracking_uri"]
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient()

    artifact_path = config["paths"]["artifacts_path"]

    if not os.path.exists(model_dir):
        raise FileNotFoundError(f"Model checkpoint not found at {model_dir}")
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = MBartForConditionalGeneration.from_pretrained(model_dir)
    experiment_name = config["mlflow"]["experiment_name"]
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        experiment_id = client.create_experiment(experiment_name)
    else:
        experiment_id = experiment.experiment_id
    run = client.create_run(experiment_id=experiment_id)
    mlflow.transformers.log_model(
        transformers_model={"model": model, "tokenizer": tokenizer},
        artifact_path=artifact_path
    )
    client.log_param(run.info.run_id, "model_source", source_name)
    client.log_param(run.info.run_id, "source_path", model_dir)
    client.log_param(run.info.run_id, "model_type", "bartpho")

    model_uri = f"runs:/{run.info.run_id}/{artifact_path}"
    try:
        client.create_registered_model(source_name)
        client.set_registered_model_tag(source_name, "model_source", source_name)
        client.set_registered_model_alias(source_name, alias, run_id=run.info.run_id)
    except mlflow.exceptions.RestException:
        pass

    client.create_model_version(
        name=source_name,
        source=model_uri,
        run_id=run.info.run_id,
        description=f"Model registered from {model_dir}"
    )
    client.set_terminated(run.info.run_id, status="FINISHED")
    print(f"Model from '{model_dir}' registered successfully as '{source_name}'")
    return model_uri
