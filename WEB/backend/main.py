import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import os
from dotenv import load_dotenv
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline


load_dotenv()

import os

def get_latest_model_path(base_path="./models/production"):
    subfolders = [os.path.join(base_path, f) for f in os.listdir(base_path)
                  if os.path.isdir(os.path.join(base_path, f))]
    if not subfolders:
        raise FileNotFoundError("Không tìm thấy mô hình trong thư mục production")

    latest_folder = max(subfolders, key=os.path.getmtime)
    return latest_folder

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://newsadmin:123456@localhost:5432/newsdb")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


from models import Base, BaiViet, DanhMuc
from transformers import pipeline


class SummarizeRequest(BaseModel):
    text: str

class SummarizeResponse(BaseModel):
    summary: str


class DanhMucBase(BaseModel):
    ten: str

class DanhMucResponse(DanhMucBase):
    id: int
    class Config:
        orm_mode = True

class BaiVietBase(BaseModel):
    tieu_de: str
    mo_ta: Optional[str] = None
    noi_dung: str
    hinh_anh: Optional[str] = None
    la_tin_hot: Optional[bool] = False
    danh_muc_id: int

class BaiVietCreate(BaiVietBase):
    pass

class BaiVietResponse(BaiVietBase):
    id: int
    ngay_dang: datetime
    luot_xem: int
    class Config:
        orm_mode = True


app = FastAPI(title="Tin Tức API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_PATH = get_latest_model_path("./models/production")

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH)

summarizer = pipeline("summarization", model=model, tokenizer=tokenizer)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_tin_hot(db: Session, skip=0, limit=10):
    return db.query(BaiViet).filter(BaiViet.la_tin_hot == True).order_by(BaiViet.ngay_dang.desc()).offset(skip).limit(limit).all()

def get_tin_moi_nhat(db: Session, skip=0, limit=10):
    return db.query(BaiViet).order_by(BaiViet.ngay_dang.desc()).offset(skip).limit(limit).all()

def get_bai_viet_by_id(db: Session, bai_viet_id: int):
    return db.query(BaiViet).filter(BaiViet.id == bai_viet_id).first()

def get_bai_viet_by_danh_muc(db: Session, danh_muc_id: int, skip=0, limit=10):
    return db.query(BaiViet).filter(BaiViet.danh_muc_id == danh_muc_id).order_by(BaiViet.ngay_dang.desc()).offset(skip).limit(limit).all()

def create_bai_viet(db: Session, bai_viet: BaiVietCreate):
    db_item = BaiViet(**bai_viet.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@app.get("/")
def root():
    return {"message": "Chào mừng đến với API tin tức"}

@app.get("/api/tintuc/hot", response_model=List[BaiVietResponse])
def api_get_tin_hot(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return get_tin_hot(db, skip, limit)

@app.get("/api/tintuc/moinhat", response_model=List[BaiVietResponse])
def api_get_tin_moi_nhat(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return get_tin_moi_nhat(db, skip, limit)

@app.get("/api/tintuc/{tin_id}", response_model=BaiVietResponse)
def api_get_chi_tiet(tin_id: int, db: Session = Depends(get_db)):
    tin = get_bai_viet_by_id(db, tin_id)
    if tin is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")
    tin.luot_xem += 1
    db.commit()
    return tin

@app.get("/api/danhmuc/{danh_muc_id}/tintuc", response_model=List[BaiVietResponse])
def api_get_theo_danh_muc(danh_muc_id: int, skip=0, limit=10, db: Session = Depends(get_db)):
    return get_bai_viet_by_danh_muc(db, danh_muc_id, skip, limit)

@app.post("/api/tintuc/", response_model=BaiVietResponse, status_code=status.HTTP_201_CREATED)
def api_tao_bai_viet(bai_viet: BaiVietCreate, db: Session = Depends(get_db)):
    return create_bai_viet(db, bai_viet)

@app.post("/api/summarize/", response_model=SummarizeResponse)
def summarize_text(req: SummarizeRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Văn bản trống")
    try:
        result = summarizer(req.text, max_length=130, min_length=30, do_sample=False)
        return {"summary": result[0]['summary_text']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tóm tắt: {str(e)}")