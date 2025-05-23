from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline
import os

app = FastAPI(title="Text Summarization API")

def get_latest_model_path(base_path=None):
    if base_path is None:
        base_path = "/models/production"
    if not os.path.exists(base_path):
        raise FileNotFoundError("Model folder not found")
    subfolders = [os.path.join(base_path, f) for f in os.listdir(base_path)
                  if os.path.isdir(os.path.join(base_path, f))]
    if not subfolders:
        raise FileNotFoundError("No models found in production folder")
    return max(subfolders, key=os.path.getmtime)

MODEL_PATH = get_latest_model_path()
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH)
summarizer = pipeline("summarization", model=model, tokenizer=tokenizer)

# Schema cho API
class SummarizeRequest(BaseModel):
    text: str

class SummarizeResponse(BaseModel):
    summary: str

@app.get("/")
def read_root():
    return {"message": "Welcome to the summarization API"}

@app.post("/api/summarize/", response_model=SummarizeResponse)
def summarize_text(req: SummarizeRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is empty")
    try:
        result = summarizer(req.text, max_length=130, min_length=30, do_sample=False)
        return {"summary": result[0]["summary_text"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization error: {str(e)}")
