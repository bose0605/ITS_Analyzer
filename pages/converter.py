import streamlit as st
import pandas as pd
from io import BytesIO
import plotly.express as px
import xlsxwriter
from streamlit_sortables import sort_items
import re
import os

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

# === Functions ===
def convert_thi_txt_to_df(file_content: str) -> pd.DataFrame:
    header = [
        "Count", "AC", "TM", "L0", "L1", "L2", "L3", "Fan", "ATM", "CPU",
        "S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9",
        "Sa", "Sb", "Sc", "Sd", "Se", "Sf", "Time"
    ]
    data = []
    lines = file_content.splitlines()
    for line in lines:
        if re.match(r"^\s*\d+", line):
            tokens = re.split(r"\s+", line.strip())
            try:
                if len(tokens) > 8 and tokens[7].endswith("/"):
                    tokens[7] = tokens[8]
                    del tokens[8]
                if len(tokens) > 9 and "/" not in tokens[8]:
                    tokens[8] = tokens[8] + tokens[9]
                    del tokens[9]
                if len(tokens) > 8:
                    tokens[8] = f"'{tokens[8]}"
                if re.match(r"\d{2}:\d{2}:\d{2}$", tokens[-1]):
                    time_value = tokens[-1]
                else:
                    time_value = ""
                tokens = tokens[:27]
                if len(tokens) == 27:
                    tokens[-1] = time_value
                    data.append(tokens)
            except:
                continue
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data, columns=header)
    df["ATM"] = df["ATM"].astype(str)
    return df

def convert_to_utf8_csv(input_file):
    filename, ext = os.path.splitext(input_file.name)
    ext = ext.lower()
    try:
        first_bytes = input_file.read(3)
        input_file.seek(0)
        encoding = 'utf-8-sig' if first_bytes.startswith(b'\xef\xbb\xbf') else 'cp949'
        df = pd.read_csv(input_file, encoding=encoding, low_memory=False, header=None)
    except Exception:
        input_file.seek(0)
        if ext == '.xls':
            df = pd.read_excel(input_file, engine='xlrd', header=None)
        elif ext == '.xlsx':
            df = pd.read_excel(input_file, engine='openpyxl', header=None)
        else:
            return None
    return df

def extract_logger_columns_with_conversion(uploaded_file, min_val=0, max_val=75, time_label="Time"):
    df = convert_to_utf8_csv(uploaded_file)
    if df is None:
        return None, "Unsupported logger file format or read error."
    try:
        header_row = df.iloc[8]
        time_row = df.iloc[9]
        data = df.iloc[10:].copy()
        time_index = list(time_row).index(time_label)
        valid_columns = []
        for col in data.columns:
            if col == time_index:
                continue
            try:
                col_values = pd.to_numeric(data[col], errors="coerce").dropna()
                if not col_values.empty and col_values.between(min_val, max_val).all():
                    valid_columns.append(col)
            except:
                continue
        col_indices = [time_index] + valid_columns
        selected_data = data.iloc[:, col_indices]
        selected_headers = header_row[col_indices].copy()
        selected_headers.iloc[0] = time_label
        selected_data.columns = selected_headers
        for col in selected_data.columns:
            if col != time_label:
                selected_data[col] = pd.to_numeric(selected_data[col], errors="coerce").round(1)
        return selected_data, None
    except Exception as e:
        return None, f"Error: {e}"

# === Initialize session ===
st.title("📊 Data Wrangling & Visualization UI")
if "uploaded_data" not in st.session_state:
    st.session_state.uploaded_data = {}
if "x_axis" not in st.session_state:
    st.session_state.x_axis = "Time"
if "y_axes" not in st.session_state:
    st.session_state.y_axes = {}
if "sorted_y_axes" not in st.session_state:
    st.session_state.sorted_y_axes = {}

uploaded_data = st.session_state.uploaded_data
file_labels = ["pTAT", "DTT", "THI", "FanCK", "logger"]
cols = st.columns(len(file_labels))

# ... (기존 업로더 및 변환 로직 그대로 유지)

# === Plotly 시각화 영역 ===
all_columns = sorted(set().union(*[
    df.columns.tolist()
    for dfs in uploaded_data.values()
    for df in dfs
]) if uploaded_data else [])

if all_columns:
    time_candidates = [col for col in all_columns if "time" in col.lower()]
    st.session_state.x_axis = time_candidates[0] if time_candidates else all_columns[0]

    st.subheader("📈 Plotly Graph Settings")
    st.session_state.x_axis = st.selectbox("X-axis column", options=all_columns, index=all_columns.index(st.session_state.x_axis), key="x_axis_global")

    y_select_cols = st.columns(len(file_labels))
    for i, label in enumerate(file_labels):
        available_cols = []
        if label in uploaded_data:
            for df in uploaded_data[label]:
                available_cols += df.columns.tolist()
        available_cols = sorted(set(available_cols))

        if label not in st.session_state.sorted_y_axes:
            st.session_state.sorted_y_axes[label] = []
        if label not in st.session_state.y_axes:
            st.session_state.y_axes[label] = []

        y_col = y_select_cols[i].selectbox(f"Add Y-axis ({label})", options=[""] + [col for col in available_cols if col not in st.session_state.sorted_y_axes[label]], key=f"y_axis_add_{label}")
        if y_col:
            if y_col not in st.session_state.sorted_y_axes[label]:
                st.session_state.sorted_y_axes[label].append(y_col)
            st.session_state.y_axes[label] = st.session_state.sorted_y_axes[label].copy()

    st.markdown("#### Selected Y-axis columns")
    y_multi_cols = st.columns(len(file_labels))
    visible_all = []
    for i, label in enumerate(file_labels):
        sorted_y = st.session_state.sorted_y_axes[label]
        visible = y_multi_cols[i].multiselect(f"Visible ({label})", options=sorted_y, default=st.session_state.y_axes[label], key=f"visible_{label}")
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
            fig = px.line(
                combined_df,
                x=st.session_state.x_axis,
                y=visible_all,
                title="Merged Plot"
            )
            st.plotly_chart(fig, use_container_width=True)

# === XLSX Column Reordering ===
st.subheader("📤 XLSX Column Reordering")
all_columns = sorted(set().union(*[
    df.columns.tolist()
    for dfs in uploaded_data.values()
    for df in dfs
]) if uploaded_data else [])

if all_columns:
    reorder_cols = [st.selectbox(f"→ Column {chr(65+i)}", all_columns, key=f"reorder_{i}") for i in range(5)]
else:
    reorder_cols = []
    st.warning("⚠️ No columns available for reordering. Please upload files first.")

output = BytesIO()
with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    for label, dfs in uploaded_data.items():
        for i, df in enumerate(dfs):
            available_cols = [col for col in reorder_cols if col in df.columns]
            if not available_cols:
                st.warning(f"⚠️ No matching columns in {label}_{i+1} for selected reorder columns.")
                continue
            df_out = df[available_cols].dropna()
            df_out.to_excel(writer, sheet_name=f"{label}_{i+1}", index=False)
output.seek(0)

st.download_button(
    label="📥 Download as XLSX",
    data=output,
    file_name="converted_data.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# === Merge All Logs by Time ===
st.subheader("📤 Merge All Logs by Time")
time_column = st.session_state.x_axis
merged_df = pd.DataFrame()

for label, dfs in uploaded_data.items():
    for i, df in enumerate(dfs):
        df_copy = df.copy()
        time_candidates = [c for c in df_copy.columns if time_column.lower() in c.lower() or "time" in c.lower()]
        if time_candidates:
            time_col = time_candidates[0]
            df_copy = df_copy.dropna(subset=[time_col])
            df_copy = df_copy.set_index(time_col)
            merged_df = merged_df.join(df_copy, how="outer") if not merged_df.empty else df_copy

if not merged_df.empty:
    merged_df = merged_df.sort_index().reset_index()
    output_merged = BytesIO()
    with pd.ExcelWriter(output_merged, engine="xlsxwriter") as writer:
        merged_df.to_excel(writer, sheet_name="Merged_All", index=False)
    output_merged.seek(0)

    st.download_button(
        label="📥 Download Merged File (Time-based)",
        data=output_merged,
        file_name="merged_all_by_time.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
