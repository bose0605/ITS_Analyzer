import streamlit as st
import os

# 페이지 설정
st.set_page_config(
    page_title="Main Menu",
    page_icon="📂",
    layout="centered",
    initial_sidebar_state="collapsed"
)
# CSS 스타일: 도라에몽 회전 + 팝업 애니메이션
st.markdown("""
<style>
@keyframes spin-pop {
  0% {
    transform: rotate(0deg) scale(0.3);
    opacity: 0;
  }
  50% {
    transform: rotate(360deg) scale(1.2);
    opacity: 1;
  }
  100% {
    transform: rotate(720deg) scale(1.0);
    opacity: 1;
  }
}

.doraemon-box {
    display: flex;
    justify-content: center;
    margin-top: 30px;
}

.doraemon-img {
    animation: spin-pop 1.8s ease-out;
    width: 220px;
    border-radius: 50%;
    box-shadow: 0 0 20px rgba(0,0,0,0.3);
}
</style>
""", unsafe_allow_html=True)



st.title("📂 ITS Tool Menu")

    # sensor correlation 링크
st.page_link("pages/sensor correlation.py", label="📊 sensor correlation")
st.page_link("pages/pTAT-viewer app.py", label="📈 pTAT Viewer")
