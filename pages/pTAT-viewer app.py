
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import os
from datetime import datetime
import matplotlib.ticker as ticker

plt.rcParams["font.family"] = "Arial"
st.set_page_config(layout="wide")

# ===== Sidebar custom CSS =====
st.markdown("""
    <style>
    section[data-testid="stSidebar"] {
        font-family: Arial;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] .stHeading {
        color: goldenrod;
        font-size: 1.2rem;
    }
    section[data-testid="stSidebar"] .stMarkdown p {
        color: white;
        font-size: 1.05rem;
    }
    section[data-testid="stSidebar"] label {
        color: white !important;
        font-size: 1.05rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 pTAT Viewer")

with st.sidebar.expander("1️⃣ CSVファイルの選択", expanded=True):
    uploaded_file = st.file_uploader("CSVファイルをアップロード", type="csv", accept_multiple_files=False)

    if not uploaded_file:
        st.warning("CSVファイルをアップロードしてください。")
        st.stop()

    file_label = uploaded_file.name
    x_axis_title = st.text_input("X軸のタイトル", value="Time (s)", key="x_axis_title_input")
    y_axis_title = st.text_input("縦軸のタイトル", value="Power (W)", key="y_axis_title_input")
    previous_file = st.session_state.get("last_selected_file", None)

@st.cache_data
def load_csv(file_obj):
    try:
        return pd.read_csv(file_obj, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(file_obj, encoding="cp932") 

df = load_csv(uploaded_file)

if file_label != previous_file:
    st.session_state.selected_y_cols = []
    st.session_state.secondary_y_cols = []
    st.session_state.last_selected_file = file_label

# Time column detection
time_col_candidates = [col for col in df.columns if "time" in col.lower()]
if not time_col_candidates:
    st.error("Time列が見つかりません。CSVに 'Time' 列を追加してください。")
    st.stop()
time_col = time_col_candidates[0]

try:
    df[time_col] = pd.to_datetime(df[time_col])
    time_vals = df[time_col].dt.strftime("%H:%M:%S")
except:
    time_vals = df[time_col]

# Plotting logic or further UI continues...
st.success("✅ CSV 読み込み成功！以下にグラフや設定を追加してください。")
