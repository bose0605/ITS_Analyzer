import streamlit as st
import pandas as pd
from io import BytesIO
import plotly.express as px
import xlsxwriter
import re
import os

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

# === THI parser ===
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

# === Logger converter + extractor ===
def convert_to_utf8_csv(input_file):
    filename, ext = os.path.splitext(input_file.name)
    ext = ext.lower()
    try:
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
                raise
        return df
    except Exception as e:
        return None

def extract_logger_columns_with_conversion(uploaded_file, min_val=0, max_val=75, time_label="Time"):
    df = convert_to_utf8_csv(uploaded_file)
    if df is None:
        return None, "Unsupported logger file format or read error."
    try:
        header_row = df.iloc[8]
        time_row = df.iloc[9]
        data = df.iloc[10:].copy()
        try:
            time_index = list(time_row).index(time_label)
        except ValueError:
            return None, "Time column not found."
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

# === UI ===
top_col_right = st.columns([8, 1])
with top_col_right[1]:
    st.page_link("main.py", label="\U0001F3E0 To Main")

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
    st.subheader(":one: Drag & drop log files (multiple or single)")
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
                if label == "THI":
                    file_str = f.read().decode('utf-8', errors='ignore')
                    df = convert_thi_txt_to_df(file_str)
                elif label == "logger":
                    df, error = extract_logger_columns_with_conversion(f)
                    if error:
                        st.warning(f"Logger parse error: {error}")
                        continue
                elif label == "FanCK":
                    try:
                        df = pd.read_csv(f, encoding_errors='ignore')

                        def convert_to_time(timestamp):
                            timestamp_str = str(int(timestamp))
                            time_digits = timestamp_str[-6:]  # Use only HHMMSS part
                            hours = int(time_digits[:2])
                            minutes = int(time_digits[2:4])
                            seconds = int(time_digits[4:])
                            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

                        df.iloc[:, 0] = df.iloc[:, 0].apply(convert_to_time)
                        original_cols = df.columns.tolist()
                        renamed_cols = ["Time"] + [f"{col} (FanCK)" for col in original_cols[1:]]
                        df.columns = renamed_cols
                    except Exception as e:
                        st.warning(f"Error processing FanCK file: {e}")
                        continue
                else:
                    try:
                        df = pd.read_csv(f, encoding_errors='ignore')
                    except pd.errors.ParserError:
                        st.warning(f"Error reading {label} file. Skipping.")
                        continue
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
                if label != "FanCK":
                    df.columns = renamed_cols
                uploaded_data[label].append(df)

# 나머지 시각화 및 다운로드는 이전 코드와 동일하게 이어서 사용 가능


# === Conversion Output ===
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

    st.subheader("📈 Plotly Graph Settings")

    source_label = next((label for label, dfs in uploaded_data.items() for df in dfs if st.session_state.x_axis in df.columns), None)
    source_suffix = f"<span style='color:green; font-size:0.8rem; margin-left:10px;'>From:{source_label}</span>" if source_label else ""
    st.markdown(f"<div style='margin-bottom:0rem;'><label style='font-size:1.1rem;'>Select X-axis column {source_suffix}</label></div>", unsafe_allow_html=True)
    st.session_state.x_axis = st.selectbox(" ", options=[""] + all_columns, index=([""] + all_columns).index(st.session_state.x_axis), key="x_axis_global")

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

        y_col = y_select_cols[i].selectbox(f"Add Y-axis column ({label})", options=[""] + [col for col in available_cols if col not in st.session_state.sorted_y_axes[label]], key=f"y_axis_add_{label}")
        if y_col:
            if y_col not in st.session_state.sorted_y_axes[label]:
                st.session_state.sorted_y_axes[label].append(y_col)
            st.session_state.y_axes[label] = st.session_state.sorted_y_axes[label].copy()

    st.markdown("#### Selected Y-axis columns (sortable & removable)")
    y_multi_cols = st.columns(len(file_labels))
    visible_all = []
    for i, label in enumerate(file_labels):
        sorted_y = st.session_state.sorted_y_axes[label]
        visible = y_multi_cols[i].multiselect(f"Columns to plot ({label})", options=sorted_y, default=st.session_state.y_axes[label], key=f"visible_{label}")
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

    st.subheader("📤 XLSX Column Reordering")
    reorder_cols = [st.selectbox(f"→ Column {chr(65+i)}", all_columns, key=f"reorder_{i}") for i in range(5)]

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for label, dfs in uploaded_data.items():
            for i, df in enumerate(dfs):
                df_out = df[reorder_cols].dropna()
                df_out.to_excel(writer, sheet_name=f"{label}_{i+1}", index=False)
    output.seek(0)

    st.download_button(
        label="📥 Download as XLSX",
        data=output,
        file_name="converted_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
