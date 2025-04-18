import streamlit as st
import os

# 페이지 설정
st.set_page_config(
    page_title="Main Menu",
    page_icon="📂",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("📂 ITS Tool Menu")
st.markdown("### Select a tool to use:")

with st.expander("📁 Pull down to choose"):
    # sensor correlation 링크
    st.page_link("pages/sensor correlation.py", label="📊 sensor correlation")

    # sensor correlation 하위 리소스처럼 들여쓰기
    with st.container():
        st.markdown('<div style="margin-left: 25px;">', unsafe_allow_html=True)
        try:
            template_path = os.path.join(os.path.dirname(__file__), "Result_template.xlsm")
        except NameError:
            template_path = os.path.join(os.getcwd(), "Result_template.xlsm")

        if os.path.exists(template_path):
            with open(template_path, "rb") as f:
                st.download_button(
                    "📥 Download Excel Template (for Logger-PTAT)",
                    data=f.read(),
                    file_name="Result_template.xlsm"
                )
        else:
            st.warning("❗ Template file not found.")
        st.markdown('</div>', unsafe_allow_html=True)

    # 같은 레벨: pTAT Viewer
    st.page_link("pages/pTAT-viewer app.py", label="📈 pTAT Viewer")
