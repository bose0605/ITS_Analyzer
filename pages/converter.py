#multiselect 1回で反映されない(sortables使えんかね)
import streamlit as st
import pandas as pd
from io import BytesIO
import plotly.express as px
import xlsxwriter
from streamlit_sortables import sort_items

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

# ✅ 全体フォントをArialに統一
st.markdown("""
    <style>
    html, body, [class^="css"]  {
        font-family: Arial, sans-serif !important;
    }
    .stButton button {
        padding: 0.4rem 1rem;
        font-size: 1.1rem;
    }
    </style>
""", unsafe_allow_html=True)

row = st.columns([6, 1])
with row[0]:
    st.title(" Data Wrangling & Visualization UI")
    st.subheader(":one: 各種ログをドラッグ＆ドロップ（複数or単数 可)")
with row[1]:
    st.markdown("<div style='padding-top: 2.5rem;'>", unsafe_allow_html=True)
    if st.button("▶️ Run Conversion"):
        st.session_state.run_conversion = True
    st.markdown("</div>", unsafe_allow_html=True)

file_labels = ["pTAT", "DTT", "THI", "FanCK", "logger"]
cols = st.columns(len(file_labels))
uploaded_data = {}

for i, label in enumerate(file_labels):
    with cols[i]:
        st.markdown(f"<h5 style='text-align:left; margin-bottom: 0rem;'>📁 {label}</h5>", unsafe_allow_html=True)
        uploaded_files = st.file_uploader("", accept_multiple_files=True, key=f"file_{label}")
        if uploaded_files:
            uploaded_data[label] = []
            for f in uploaded_files:
                df = pd.read_csv(f, encoding_errors='ignore')
                if label == "pTAT":
                    for col in df.columns:
                        if "time" in col.lower():
                            df[col] = df[col].astype(str).str.extract(r'(\d{2}:\d{2}:\d{2})')[0]
                if label == "DTT":
                    for col in df.columns:
                        if "power" in col.lower() and "(mW)" in col:
                            df[col] = pd.to_numeric(df[col], errors='coerce') / 1000
                            df.rename(columns={col: col.replace("(mW)", "(W)")}, inplace=True)
                renamed_cols = []
                for col in df.columns:
                    if "time" in col.lower():
                        renamed_cols.append(f"Time ({label})")
                    else:
                        renamed_cols.append(f"{col} ({label})")
                df.columns = renamed_cols
                uploaded_data[label].append(df)

run_conversion = st.session_state.get("run_conversion", False)

if run_conversion:
    all_columns = sorted(set().union(*[df.columns.tolist() for dfs in uploaded_data.values() for df in dfs]))

    if "x_axis" not in st.session_state or st.session_state.x_axis not in all_columns:
        time_candidates = [col for col in all_columns if "time" in col.lower()]
        st.session_state.x_axis = time_candidates[0] if time_candidates else all_columns[0]

    if "y_axes" not in st.session_state:
        st.session_state.y_axes = {}
    if "sorted_y_axes" not in st.session_state:
        st.session_state.sorted_y_axes = {}

    st.subheader("\U0001F4CA Plotlyグラフ設定")

    source_label = next((label for label, dfs in uploaded_data.items() for df in dfs if st.session_state.x_axis in df.columns), None)
    source_suffix = f"<span style='color:green; font-size:0.8rem; margin-left:10px;'>From:{source_label}</span>" if source_label else ""
    st.markdown(f"<div style='margin-bottom:0rem;'><label style='font-size:1.1rem;'>X軸に使用する列を選択 {source_suffix}</label></div>", unsafe_allow_html=True)
    st.session_state.x_axis = st.selectbox(" ", options=[""] + all_columns, index=( [""] + all_columns ).index(st.session_state.x_axis) if st.session_state.x_axis in all_columns else 0, key="x_axis_global")

    y_select_cols = st.columns(len(file_labels))
    for i, label in enumerate(file_labels):
        available_cols = []
        if label in uploaded_data:
            for df in uploaded_data[label]:
                available_cols += df.columns.tolist()
        available_cols = sorted(set(available_cols))

        if label not in st.session_state.y_axes:
            st.session_state.y_axes[label] = []
        if label not in st.session_state.sorted_y_axes:
            st.session_state.sorted_y_axes[label] = []

        y_col = y_select_cols[i].selectbox(f"Y軸の列を追加 ({label})", options=[""] + [col for col in available_cols if col not in st.session_state.sorted_y_axes[label]], key=f"y_axis_add_{label}")
        if y_col:
            if y_col not in st.session_state.sorted_y_axes[label]:
                st.session_state.sorted_y_axes[label].append(y_col)
            st.session_state.y_axes[label] = st.session_state.sorted_y_axes[label].copy()

    st.markdown("#### 選択中のY軸カラム（並び替え＆削除可）")
    y_multi_cols = st.columns(len(file_labels))
    visible_all = []
    for i, label in enumerate(file_labels):
        sorted_y = st.session_state.sorted_y_axes[label]
        visible = y_multi_cols[i].multiselect(f"描画する列（{label}）", options=sorted_y, default=st.session_state.y_axes[label], key=f"visible_{label}")
        st.session_state.y_axes[label] = visible
        visible_all += visible

    if st.session_state.x_axis and visible_all:
        combined_df = pd.DataFrame()
        for label, dfs in uploaded_data.items():
            for df in dfs:
                if st.session_state.x_axis in df.columns:
                    valid_y = [y for y in st.session_state.y_axes[label] if y in df.columns]
                    if valid_y:
                        temp_df = df[[st.session_state.x_axis] + valid_y].dropna()
                        combined_df = pd.concat([combined_df, temp_df], ignore_index=True)

        if not combined_df.empty:
            combined_df = combined_df.loc[:, ~combined_df.columns.duplicated()]
            valid_columns = [col for col in visible_all if col in combined_df.columns]
            fig = px.line(
                combined_df,
                x=st.session_state.x_axis,
                y=valid_columns,
                title="Multiselect chart"
            )
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("\U0001F4C4 XLSX列並び替え設定")
    reorder_cols = [st.selectbox(f"→ {chr(65+i)}列に表示", all_columns, key=f"reorder_{i}") for i in range(5)]

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for label, dfs in uploaded_data.items():
            for i, df in enumerate(dfs):
                df_out = df[reorder_cols].dropna()
                df_out.to_excel(writer, sheet_name=f"{label}_{i+1}", index=False)
    output.seek(0)

    st.download_button(
        label="\U0001F4E5 XLSXとしてダウンロード",
        data=output,
        file_name="converted_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
