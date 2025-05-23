from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class DanhMuc(Base):
    __tablename__ = "danh_muc"
    
    id = Column(Integer, primary_key=True, index=True)
    ten = Column(String, nullable=False)
    
    bai_viet = relationship("BaiViet", back_populates="danh_muc")

class BaiViet(Base):
    __tablename__ = "bai_viet"
    
    id = Column(Integer, primary_key=True, index=True)
    tieu_de = Column(String, nullable=False)
    mo_ta = Column(String, nullable=True)
    noi_dung = Column(Text, nullable=False)
    hinh_anh = Column(String, nullable=True)
    ngay_dang = Column(DateTime, default=func.now())
    luot_xem = Column(Integer, default=0)
    la_tin_hot = Column(Boolean, default=False)
    danh_muc_id = Column(Integer, ForeignKey("danh_muc.id"))
    
    danh_muc = relationship("DanhMuc", back_populates="bai_viet")