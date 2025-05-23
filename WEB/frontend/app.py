import streamlit as st
import requests

API_URL = "http://backend:8000/api/summarize/"

st.title("Tóm tắt văn bản bằng AI")

text_input = st.text_area("Nhập văn bản cần tóm tắt:", height=300)

if st.button("Tóm tắt"):
    if text_input.strip():
        with st.spinner("Đang tóm tắt..."):
            try:
                response = requests.post(API_URL, json={"text": text_input})
                if response.status_code == 200:
                    st.subheader("Kết quả tóm tắt:")
                    st.success(response.json()["summary"])
                else:
                    st.error(f"Lỗi: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"Lỗi không xác định: {e}")
    else:
        st.warning("Vui lòng nhập văn bản.")
