import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import torch
import yaml
import pandas as pd
import evaluate
import mlflow
import numpy as np
from register import register_model
from datetime import datetime
from transformers import (
    MBartForConditionalGeneration,
    AutoTokenizer,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    DataCollatorForSeq2Seq,
    EarlyStoppingCallback,
)
from datasets import Dataset
from mlflow.tracking import MlflowClient

with open("src/config/config_model.yaml") as f:
    config = yaml.safe_load(f)

from src.model.fetch_model import fetch_model_from_logged_artifact

def find_best_checkpoint(model_path):
    if os.path.basename(model_path).startswith('checkpoint-'):
        return model_path
    trainer_state_path = os.path.join(model_path, "trainer_state.json")
    if os.path.exists(trainer_state_path):
        import json
        with open(trainer_state_path, 'r') as f:
            trainer_state = json.load(f)
        if 'best_model_checkpoint' in trainer_state:
            return trainer_state['best_model_checkpoint']
    checkpoint_dirs = [d for d in os.listdir(model_path) if os.path.isdir(os.path.join(model_path, d)) and d.startswith('checkpoint-')]
    if checkpoint_dirs:
        latest_checkpoint = sorted(checkpoint_dirs, key=lambda x: int(x.split('-')[1]))[-1]
        return os.path.join(model_path, latest_checkpoint)
    return model_path

def get_model_tokenizer(source: str):
    if source == "bartpho-base":
        model_id = config["model"]["base_model_hf"]
        model = MBartForConditionalGeneration.from_pretrained(model_id)
        tokenizer = AutoTokenizer.from_pretrained(model_id)
    elif source == "bartpho-pretrain":
        path = config["model"]["pretrain_model_path"]
        try:
            model = MBartForConditionalGeneration.from_pretrained(
                path,
                low_cpu_mem_usage=True,
                ignore_mismatched_sizes=True
            )
            print(f"Loaded model from {path} with some missing weights")
        except Exception as e:
            print(f"Error loading model from {path}: {e}")
            print("Falling back to base model and loading available weights")
            base_model_id = config["model"]["base_model_hf"]
            model = MBartForConditionalGeneration.from_pretrained(base_model_id)
            missing_keys, unexpected_keys = model.load_state_dict(
                torch.load(os.path.join(path, "pytorch_model.bin"), map_location="cpu"),
                strict=False
            )
            print(f"Missing keys: {len(missing_keys)}, Unexpected keys: {len(unexpected_keys)}")
        tokenizer = AutoTokenizer.from_pretrained(path)
    elif source == "production":
        prod_dir = os.path.join("models", "production")
        subfolders = [f for f in os.listdir(prod_dir) if os.path.isdir(os.path.join(prod_dir, f))]
        if not subfolders:
            raise FileNotFoundError(f"No model subfolder found in {prod_dir}")
        local_prod_path = os.path.join(prod_dir, subfolders[0])
        print(f"Loading production model from local folder: {local_prod_path}")
        model = MBartForConditionalGeneration.from_pretrained(local_prod_path)
        tokenizer = AutoTokenizer.from_pretrained(local_prod_path)
    else:
        raise ValueError(f"Unknown model source: {source}")
    return model.cpu(), tokenizer


def preprocess_function(example, tokenizer, max_input_len, max_target_len):
    content_col = "content" if "content" in example else "article"
    # Debug: kiểm tra kiểu dữ liệu
    assert isinstance(example[content_col], list), f"{content_col} is not a list"
    assert isinstance(example["summary"], list), "summary is not a list"
    # Loại bỏ các phần tử None hoặc NaN nếu có
    contents = [c if c is not None else "" for c in example[content_col]]
    summaries = [s if s is not None else "" for s in example["summary"]]
    inputs = tokenizer(
        contents,
        max_length=max_input_len,
        truncation=True,
        padding="max_length"
    )
    targets = tokenizer(
        summaries,
        max_length=max_target_len,
        truncation=True,
        padding="max_length"
    )
    inputs["labels"] = targets["input_ids"]
    return inputs

def compute_metrics_fn(tokenizer):
    rouge = evaluate.load("rouge")
    def compute(eval_preds):
        preds, labels = eval_preds
        preds = np.where(preds != -100, preds, tokenizer.pad_token_id)
        decoded_preds = tokenizer.batch_decode(preds, skip_special_tokens=True)

        labels = np.where(np.array(labels) != -100, labels, tokenizer.pad_token_id)
        decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)
        result = rouge.compute(predictions=decoded_preds, references=decoded_labels, use_stemmer=True)
        return {k: result[k] * 100 for k in result}
    return compute

def load_and_prepare_dataset(tokenizer):
    df_train = pd.read_csv(config["retrain"]["train_data_path"], on_bad_lines="skip")
    df_eval = pd.read_csv(config["retrain"]["eval_data_path"], on_bad_lines="skip")
    train_ds = Dataset.from_pandas(df_train)
    eval_ds = Dataset.from_pandas(df_eval)
    max_len = config["predict"]["max_length"]
    train_ds = train_ds.map(lambda x: preprocess_function(x, tokenizer, max_len, max_len), batched=True)
    eval_ds = eval_ds.map(lambda x: preprocess_function(x, tokenizer, max_len, max_len), batched=True)
    return train_ds, eval_ds

def log_model_as_artifact(model, tokenizer, output_model_dir, client, run_id):
    os.makedirs(output_model_dir, exist_ok=True)
    model.to("cpu")
    model.save_pretrained(output_model_dir)
    tokenizer.save_pretrained(output_model_dir)
    client.log_artifacts(run_id, output_model_dir, artifact_path="model_artifacts")

def evaluate_on_test(model_path, model_name, client, experiment_id):
    print(f"Evaluating model: {model_name} from path: {model_path}")
    if model_path.startswith(config["paths"]["output_dir"]):
        checkpoint_path = find_best_checkpoint(model_path)
        print(f"Using best checkpoint: {checkpoint_path}")
    else:
        checkpoint_path = model_path

    tokenizer = AutoTokenizer.from_pretrained(checkpoint_path)
    model = MBartForConditionalGeneration.from_pretrained(checkpoint_path).cpu()

    df_test = pd.read_csv(config["evaluation"]["dataset_path"], on_bad_lines="skip")
    contents = df_test["content"].tolist()
    summaries = df_test["summary"].tolist()

    inputs = tokenizer(contents, return_tensors="pt", padding=True, truncation=True, max_length=config["predict"]["max_length"])
    inputs = {k: v.to("cpu") for k, v in inputs.items()}

    outputs = model.generate(
        input_ids=inputs["input_ids"],
        attention_mask=inputs["attention_mask"],
        max_length=config["predict"]["max_length"],
        min_length=20,
        num_beams=4
    )

    rouge = evaluate.load("rouge")
    decoded_preds = tokenizer.batch_decode(outputs, skip_special_tokens=True)
    result = rouge.compute(predictions=decoded_preds, references=summaries, use_stemmer=True)
    scores = {k: round(v * 100, 2) for k, v in result.items()}

    run = client.create_run(experiment_id)
    run_id = run.info.run_id
    client.log_param(run_id, "eval_model", model_name)
    client.log_param(run_id, "eval_dataset", config["evaluation"]["dataset_path"])
    client.log_param(run_id, "eval_type", "final_test")

    for k, v in scores.items():
        client.log_metric(run_id, f"test_{k}", v)

    client.set_terminated(run_id, status="FINISHED")
    print(f"Logged test evaluation for '{model_name}' to MLflow")

    scores["rougeL"] = scores.get("rougeL", 0.0)
    return scores, scores["rougeL"]

def cleanup_model_folders(output_dir, keep_best=None):
    if not os.path.exists(output_dir):
        return

    model_folders = []
    for item in os.listdir(output_dir):
        item_path = os.path.join(output_dir, item)
        if os.path.isdir(item_path) and "_" in item:
            model_source = item.split("_")[0]
            if model_source in ["bartpho-base", "bartpho-pretrain", "production"]:
                model_folders.append(item_path)

    for folder in model_folders:
        folder_name = os.path.basename(folder)
        if keep_best and folder_name.startswith(keep_best):
            print(f"Keeping best model folder: {folder_name}")
        else:
            import shutil
            print(f"Removing model folder: {folder_name}")
            shutil.rmtree(folder)

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        import gc
        gc.collect()

def train_and_eval_log(source):
    print(f"Training from source: {source}")
    model, tokenizer = get_model_tokenizer(source)
    train_ds, eval_ds = load_and_prepare_dataset(tokenizer)
    compute_metrics = compute_metrics_fn(tokenizer)
    data_collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model)

    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    client = MlflowClient()
    experiment = client.get_experiment_by_name(config["mlflow"]["experiment_name"])
    if experiment is None:
        experiment_id = client.create_experiment(config["mlflow"]["experiment_name"])
    else:
        experiment_id = experiment.experiment_id

    run = client.create_run(experiment_id)
    run_id = run.info.run_id
    client.log_param(run_id, "model_source", source)

    run_id_short = run_id[:8]
    output_dir = os.path.join(config["paths"]["output_dir"], f"{source}_{run_id_short}")
    log_dir = os.path.join(output_dir, config["paths"]["log_dir"])
    os.makedirs(output_dir, exist_ok=True)

    args = config["train_args"]
    batch_size = config["predict"]["batch_size"]
    if source == "bartpho-pretrain":
        batch_size = max(1, batch_size // 2)

    training_args = Seq2SeqTrainingArguments(
        output_dir=output_dir,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="rougeL",
        greater_is_better=True,
        logging_dir=log_dir,
        logging_steps=args["logging_steps"],
        save_total_limit=1,
        num_train_epochs=args["epochs"],
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        warmup_steps=args["warmup_steps"],
        weight_decay=0.01,
        learning_rate=args["learning_rate"],
        predict_with_generate=True,
        generation_max_length=config["predict"]["max_length"],
        gradient_accumulation_steps=1,
        gradient_checkpointing=True,
        optim="adamw_torch",
        no_cuda= config['train_args']['no_cuda'],
        fp16=True,
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )

    trainer.train()
    eval_metrics = trainer.evaluate()
    for k, v in eval_metrics.items():
        client.log_metric(run_id, k, v)

    model_output_path = os.path.join(output_dir, "model_files")
    log_model_as_artifact(model, tokenizer, model_output_path, client, run_id)
    client.set_terminated(run_id, status="FINISHED")

    return {
        "model": source,
        "run_id": run_id,
        "trained_model_path": output_dir,
        **{k: round(v, 2) for k, v in eval_metrics.items()}
    }

def main():
    results_dir = config["paths"]["results_dir"]
    output_dir = config["paths"]["output_dir"]
    os.makedirs(results_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_results = []

    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    client = MlflowClient()
    experiment = client.get_experiment_by_name(config["mlflow"]["experiment_name"])
    experiment_id = experiment.experiment_id if experiment else client.create_experiment(config["mlflow"]["experiment_name"])

    registered = {}
    for source in config["retrain"]["model_sources"]:
        result = train_and_eval_log(source)
        model_path = result["trained_model_path"]
        test_scores, rougeL = evaluate_on_test(model_path, result["model"] + "_trained", client, experiment_id)
        result.update({f"test_{k}": v for k, v in test_scores.items()})
        registered[source] = (model_path, rougeL)
        all_results.append(result)

    prod_dir = "models/production"
    prod_subfolders = [f for f in os.listdir(prod_dir) if os.path.isdir(os.path.join(prod_dir, f))]
    if not prod_subfolders:
        raise FileNotFoundError(f"No model subfolder found in {prod_dir}")
    prod_model_path = os.path.join(prod_dir, prod_subfolders[0])

    base_models = {
        "bartpho-base": config["model"]["base_model_hf"],
        "bartpho-pretrain": config["model"]["pretrain_model_path"],
        "production": prod_model_path,  
    }

    for name, path in base_models.items():
        test_scores, rougeL = evaluate_on_test(path, name + "_raw", client, experiment_id)
        registered[name] = (path, rougeL)
        all_results.append({
            "model": name + "_raw",
            "run_id": "none",
            **{f"test_{k}": v for k, v in test_scores.items()}
        })

    result_df = pd.DataFrame(all_results)
    result_path = os.path.join(results_dir, f"eval_test_metrics_{timestamp}.csv")
    result_df.to_csv(result_path, index=False)
    print(f"All results saved to: {result_path}")

    best = result_df.sort_values(by="test_rougeL", ascending=False).iloc[0]
    best_model_name = best["model"]
    print(f"Best model: {best_model_name} | test_rougeL = {best['test_rougeL']}")

    if best_model_name.endswith("_trained") or best_model_name.endswith("_raw") or best_model_name in ["bartpho-base", "bartpho-pretrain", "production"]:
        final_model_name = best_model_name.replace("_trained", "").replace("_raw", "")
        final_model_info = next((r for r in all_results if r["model"] == best_model_name), None)

        if final_model_info:
            final_model_path = final_model_info["trained_model_path"] if "trained_model_path" in final_model_info else registered[final_model_name][0]
            
            if final_model_path.startswith(config["paths"]["output_dir"]):
                final_model_path = find_best_checkpoint(final_model_path)
                print(f"Using best checkpoint for registration: {final_model_path}")
                
            final_rouge = final_model_info.get("test_rougeL", 0.0)
            register_model(source_name=final_model_name, model_dir=final_model_path, alias="Production", rouge=final_rouge)
            print(f"Registered '{final_model_name}' as Production")

        for name, (path, rougeL) in registered.items():
            if name != final_model_name:
                if path.startswith(config["paths"]["output_dir"]):
                    path = find_best_checkpoint(path)
                    print(f"Using best checkpoint for {name}: {path}")
                register_model(source_name=name, model_dir=path, alias=f"{name}-latest", rouge=rougeL)
                
        with open(os.path.join(results_dir, "best_model.txt"), "w") as f:
            f.write(final_model_name, timestamp, str(final_rouge))

        for r in all_results:
            path = r.get("trained_model_path")
            if path and path != final_model_path and os.path.exists(path):
                import shutil
                shutil.rmtree(path)
                print(f"Removed non-production model folder: {path}")
    else:
        print("No promotion — Production model is still best.")

    print("Cleaning up model folders...")
    cleanup_model_folders(output_dir, keep_best=best_model_name.replace("_trained", ""))


if __name__ == "__main__":
    main()
