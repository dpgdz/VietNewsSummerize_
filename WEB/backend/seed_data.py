from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, DanhMuc, BaiViet
import os
from dotenv import load_dotenv
import time

load_dotenv()

# Wait for database to be ready
time.sleep(2)

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://newsadmin:123456@db:5432/newsdb")

# Create database engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Create tables
Base.metadata.create_all(bind=engine)

# Check if data already exists
if db.query(DanhMuc).count() == 0:
    # Create categories
    danh_muc_1 = DanhMuc(ten="Thời sự")
    danh_muc_2 = DanhMuc(ten="Thể thao")
    danh_muc_3 = DanhMuc(ten="Giải trí")
    danh_muc_4 = DanhMuc(ten="Kinh doanh")
    
    db.add_all([danh_muc_1, danh_muc_2, danh_muc_3, danh_muc_4])
    db.commit()
    
    # Create news articles
    bai_viet_1 = BaiViet(
        tieu_de="Tin tức thời sự mới nhất",
        mo_ta="Cập nhật tin tức thời sự mới nhất trong ngày",
        noi_dung="Đây là nội dung chi tiết về tin tức thời sự mới nhất. Nội dung này sẽ được hiển thị khi người dùng xem chi tiết bài viết.",
        hinh_anh="https://via.placeholder.com/600x400?text=Thoi+Su",
        la_tin_hot=True,
        danh_muc_id=1
    )
    
    bai_viet_2 = BaiViet(
        tieu_de="Kết quả bóng đá mới nhất",
        mo_ta="Cập nhật kết quả các trận đấu bóng đá",
        noi_dung="Đây là nội dung chi tiết về kết quả các trận đấu bóng đá. Nội dung này sẽ được hiển thị khi người dùng xem chi tiết bài viết.",
        hinh_anh="https://via.placeholder.com/600x400?text=The+Thao",
        la_tin_hot=True,
        danh_muc_id=2
    )
    
    bai_viet_3 = BaiViet(
        tieu_de="Tin tức giải trí hôm nay",
        mo_ta="Cập nhật tin tức về các nghệ sĩ nổi tiếng",
        noi_dung="Đây là nội dung chi tiết về tin tức giải trí và các nghệ sĩ nổi tiếng. Nội dung này sẽ được hiển thị khi người dùng xem chi tiết bài viết.",
        hinh_anh="https://via.placeholder.com/600x400?text=Giai+Tri",
        la_tin_hot=False,
        danh_muc_id=3
    )
    
    bai_viet_4 = BaiViet(
        tieu_de="Tin tức kinh doanh mới nhất",
        mo_ta="Cập nhật tin tức về thị trường tài chính",
        noi_dung="Đây là nội dung chi tiết về tin tức kinh doanh và thị trường tài chính. Nội dung này sẽ được hiển thị khi người dùng xem chi tiết bài viết.",
        hinh_anh="https://via.placeholder.com/600x400?text=Kinh+Doanh",
        la_tin_hot=False,
        danh_muc_id=4
    )
    
    bai_viet_5 = BaiViet(
        tieu_de="Tin nóng: Sự kiện quan trọng",
        mo_ta="Thông tin mới nhất về sự kiện đang diễn ra",
        noi_dung="Đây là nội dung chi tiết về sự kiện quan trọng đang diễn ra. Nội dung này sẽ được hiển thị khi người dùng xem chi tiết bài viết.",
        hinh_anh="https://via.placeholder.com/600x400?text=Su+Kien",
        la_tin_hot=True,
        danh_muc_id=1
    )
    
    db.add_all([bai_viet_1, bai_viet_2, bai_viet_3, bai_viet_4, bai_viet_5])
    db.commit()
    
    print("Đã tạo dữ liệu mẫu thành công!")
else:
    print("Dữ liệu đã tồn tại, không cần tạo mới.")

db.close()