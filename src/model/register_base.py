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
# model = MBartForConditionalGeneration.from_pretrained(model_path)
print(f"Model loaded from: {model_path}")
run = client.create_run(experiment_id=experiment_id)
run_id = run.info.run_id

print(f"Run ID: {run_id}")

client.log_artifacts(run_id=run_id, local_dir="/home/mlops/recovered/models/base_model", artifact_path=artifact_path)

model_uri = f"runs:/{run_id}/{artifact_path}"
print(f"Model URI: {model_uri}")

time.sleep(5)

result = mlflow.register_model(model_uri=model_uri, name=model_name)

client.set_registered_model_alias(
    name=model_name,
    alias="Production",
    version=result.version
)

client.set_model_version_tag(name=model_name, version=result.version, key="source model", value=model_name)
client.set_model_version_tag(name=model_name, version=result.version, key="source tag", value=source_tag)
client.set_model_version_tag(name=model_name, version=result.version, key="source path", value=model_path)

print(f"Pretrained model from '{model_path}' registered successfully as '{model_name}'")

client.set_terminated(run_id, status="FINISHED")