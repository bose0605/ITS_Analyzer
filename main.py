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
    st.page_link("pages/pTAT-viewer app.py", label="📈 pTAT Viewer")
