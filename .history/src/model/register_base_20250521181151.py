import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import time

import mlflow
import mlflow.transformers
from mlflow.tracking import MlflowClient
from transformers import AutoTokenizer, MBartForConditionalGeneration
import yaml

with open("src/config/config_model.yaml") as f:
    config_model = yaml.safe_load(f)

tracking_uri = config_model["mlflow"]["tracking_uri"]
experiment_name = config_model["mlflow"]["experiment_name"]
model_name = config_model["mlflow"]["model_name"]
model_path = config_model["model"]["pretrain_model_path"]
artifact_path = config_model["paths"]["artifacts_path"]
source_tag = config_model["model"]["base_model_source"]

if not os.path.exists(model_path):
    raise FileNotFoundError(f"Model checkpoint not found at {model_path}")

mlflow.set_tracking_uri(tracking_uri)
client = MlflowClient()

experiment = client.get_experiment_by_name(experiment_name)
if experiment is None:
    experiment_id = client.create_experiment(experiment_name)
else:
    experiment_id = experiment.experiment_id

tokenizer = AutoTokenizer.from_pretrained(model_path)
model = MBartForConditionalGeneration.from_pretrained(model_path)

activate_run = mlflow.start_run(run_name="base_model", experiment_id=experiment_id)
client.log_param(activate_run.info.run_id, "model_source", source_tag)
client.log_param(activate_run.info.run_id, "pretrained", "true")
client.log_param(activate_run.info.run_id, "model_type", "bartpho-pretrain")
client.log_param(activate_run.info.run_id, "source_path", model_path)


model_uri = f"runs:/{activate_run.info.run_id}/{artifact_path}"

client.log_artifact(activate_run.info.run_id, local_path=model_path, artifact_path=artifact_path)

run = activate_run
client.create_model_version(
    name=model_name,
    source=model_uri,
    run_id=run.info.run_id,
    description="Fine-tuned BARTpho model (pretrained checkpoint)"
)

client.set_registered_model_tag(model_name, "model_source", source_tag)
client.set_registered_model_alias(model_name, "Production", run_id=run.info.run_id)

mlflow.end_run(status="FINISHED")
print(f"Pretrained model from '{model_path}' registered successfully as '{model_name}'")
