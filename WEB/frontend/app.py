import streamlit as st
import requests
import os

# Get API base from environment variable or use default
API_BASE = os.environ.get("API_BASE", "http://localhost:8000/api")

st.set_page_config(page_title="Tin tức", layout="wide")
st.title("📰 Trang Tin Tức")

menu = ["Tin Mới Nhất", "Tin Hot", "Xem Chi Tiết", "Theo Danh Mục", "Tóm Tắt Văn Bản"]
choice = st.sidebar.selectbox("Chọn chức năng", menu)

if choice == "Tin Mới Nhất":
    st.subheader("🆕 Tin Mới Nhất")
    res = requests.get(f"{API_BASE}/tintuc/moinhat")
    if res.status_code == 200:
        for item in res.json():
            st.markdown(f"### {item['tieu_de']}")
            st.write(f"*Ngày đăng:* {item['ngay_dang']} | *Lượt xem:* {item['luot_xem']}")
            st.write(item.get("mo_ta", ""))
            st.write("---")
    else:
        st.error("Không lấy được dữ liệu")

elif choice == "Tin Hot":
    st.subheader("🔥 Tin Hot")
    res = requests.get(f"{API_BASE}/tintuc/hot")
    if res.status_code == 200:
        for item in res.json():
            st.markdown(f"### {item['tieu_de']}")
            st.write(f"*Ngày đăng:* {item['ngay_dang']} | *Lượt xem:* {item['luot_xem']}")
            st.write(item.get("mo_ta", ""))
            st.write("---")
    else:
        st.error("Không lấy được dữ liệu")

elif choice == "Xem Chi Tiết":
    st.subheader("🔎 Xem Chi Tiết Bài Viết")
    tin_id = st.number_input("Nhập ID bài viết", min_value=1, step=1)
    if st.button("Xem"):
        res = requests.get(f"{API_BASE}/tintuc/{tin_id}")
        if res.status_code == 200:
            tin = res.json()
            st.markdown(f"## {tin['tieu_de']}")
            st.write(f"*Ngày đăng:* {tin['ngay_dang']} | *Lượt xem:* {tin['luot_xem']}")
            st.image(tin['hinh_anh'] if tin['hinh_anh'] else "https://via.placeholder.com/300", width=300)
            st.write("### Nội dung:")
            st.write(tin['noi_dung'])
        else:
            st.error("Không tìm thấy bài viết")

elif choice == "Theo Danh Mục":
    st.subheader("📂 Xem Theo Danh Mục")
    danh_muc_id = st.number_input("Nhập ID danh mục", min_value=1, step=1)
    if st.button("Xem bài viết"):
        res = requests.get(f"{API_BASE}/danhmuc/{danh_muc_id}/tintuc")
        if res.status_code == 200:
            for item in res.json():
                st.markdown(f"### {item['tieu_de']}")
                st.write(f"*Ngày đăng:* {item['ngay_dang']} | *Lượt xem:* {item['luot_xem']}")
                st.write(item.get("mo_ta", ""))
                st.write("---")
        else:
            st.error("Không tìm thấy danh mục hoặc không có bài viết")


elif choice == "Tóm Tắt Văn Bản":
    st.subheader("📝 Tóm Tắt Văn Bản")
    user_text = st.text_area("Nhập đoạn văn bản cần tóm tắt", height=250)
    if st.button("Tóm tắt"):
        if not user_text.strip():
            st.warning("Vui lòng nhập văn bản.")
        else:
            res = requests.post(f"{API_BASE}/summarize/", json={"text": user_text})
            if res.status_code == 200:
                summary = res.json()["summary"]
                st.success("✅ Tóm tắt thành công:")
                st.markdown(f"**Tóm tắt:** {summary}")
            else:
                st.error(f"Lỗi: {res.json().get('detail', 'Không rõ lỗi')}")