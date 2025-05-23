from prometheus_client import Summary, Gauge, Counter

PREDICT_LATENCY = Summary("predict_latency_seconds", "Time per prediction")
PREDICT_TOTAL = Counter("predict_requests_total", "Total predictions made")
PREDICT_ERRORS = Counter("predict_errors_total", "Total prediction errors")

TRAIN_LOSS = Gauge("train_loss", "Training loss")
TRAIN_ROUGE = Gauge("train_rougeL", "Training ROUGE-L")

EVAL_ROUGE_L = Gauge("eval_rougeL", "Evaluation ROUGE-L")

DAILY_EVAL_ROUGE_1 = Gauge("daily_eval_rouge1", "Daily ROUGE-1")
DAILY_EVAL_ROUGE_2 = Gauge("daily_eval_rouge2", "Daily ROUGE-2")
DAILY_EVAL_ROUGE_L = Gauge("daily_eval_rougeL", "Daily ROUGE-L")
