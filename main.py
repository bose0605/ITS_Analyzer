
import streamlit as st
import os

# 페이지 설정
st.set_page_config(
    page_title="Main Menu",
    page_icon="📂",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 타이틀 및 설명
st.title("📂 ITS Tool Menu")
st.markdown("### Select a tool to use:")

# 메인 파이프라인 페이지 링크
st.page_link("pages/sensor correlation.py", label="📊 sensor correlation")

# 트리 형식으로 하위 리소스 표시
with st.expander("   └ 📂 Download Excel Template (for Logger-PTAT)"):
    template_path = os.path.join(os.path.dirname(__file__), "Result_template.xlsm")
    if os.path.exists(template_path):
        with open(template_path, "rb") as f:
            st.download_button("📥 Result_template.xlsm", data=f.read(), file_name="Result_template.xlsm")
    else:
        st.warning("❗ Template file not found.")

# 다른 페이지 링크
st.page_link("pages/pTAT-viewer app.py", label="📈 pTAT Viewer")


