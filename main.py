import streamlit as st
import os

# 페이지 설정
st.set_page_config(
    page_title="Main Menu",
    page_icon="📂",
    layout="centered",
    initial_sidebar_state="collapsed"
)


# 🔧 font style
st.markdown("""
    <style>
    a.st-emotion-cache-6c2g0o.ef3psqc11 {  
        font-size: 20px !important;
        font-weight: bold !important;
        color: #1f77b4 !important;  
    }
    </style>
""", unsafe_allow_html=True)

st.title("📂 ITS Tool Menu")

    # sensor correlation 링크
st.page_link("pages/sensor correlation.py", label="📊 sensor correlation")
st.page_link("pages/pTAT-viewer app.py", label="📈 pTAT Viewer")
