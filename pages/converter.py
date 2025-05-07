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

# === Logger Parser ===
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

        
        selected_data = selected_data.rename(columns={time_label: "Time"})
        for col in selected_data.columns:
            if col != "Time":
                selected_data[col] = pd.to_numeric(selected_data[col], errors="coerce").round(1)

      
        selected_data["Time"] = pd.to_datetime(selected_data["Time"], format="%H:%M:%S", errors="coerce")
        selected_data = selected_data.dropna(subset=["Time"]).sort_values("Time").reset_index(drop=True)

    
        df_expanded = selected_data.loc[selected_data.index.repeat(2)].reset_index(drop=True)
        df_expanded["Time"] = df_expanded["Time"] + pd.to_timedelta(df_expanded.index % 2, unit='s')
        df_expanded.iloc[1::2, 1:] = df_expanded.iloc[::2, 1:].values
        df_expanded = df_expanded.sort_values("Time").reset_index(drop=True)

        
        df_expanded["Time"] = df_expanded["Time"].dt.strftime("%H:%M:%S")

        return df_expanded, None

    except Exception as e:
        return None, f"Error: {e}"

# === FanCK Parser ===
def convert_fanck_file(file) -> pd.DataFrame:
    df = pd.read_csv(file, encoding_errors='ignore')

    def convert_to_time(timestamp):
        timestamp_str = str(int(timestamp))
        time_digits = timestamp_str[-6:]
        hours = int(time_digits[:2])
        minutes = int(time_digits[2:4])
        seconds = int(time_digits[4:])
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    df.iloc[:, 0] = df.iloc[:, 0].apply(convert_to_time)
    original_cols = df.columns.tolist()
    renamed_cols = ["Time"] + [f"{col} (FanCK)" for col in original_cols[1:]]
    df.columns = renamed_cols
    return df

# === Generic CSV Reader (pTAT, DTT) ===
def read_generic_csv(file, label: str) -> pd.DataFrame:
    df = pd.read_csv(file, encoding_errors='ignore')

    if label == "pTAT":
        if "Time" in df.columns:
            df["Time"] = df["Time"].astype(str).str.extract(r'(\d{2}:\d{2}:\d{2})')[0]
        
    elif label == "DTT":
        for col in df.columns:
            if "power" in col.lower() and "(mW)" in col:
                df[col] = pd.to_numeric(df[col], errors='coerce') / 1000
                df.rename(columns={col: col.replace("(mW)", "(W)")}, inplace=True)

    renamed_cols = []
    for col in df.columns:
        if col == "Time":
            renamed_cols.append(f"Time ({label})")
        else:
            renamed_cols.append(f"{col} ({label})")
    df.columns = renamed_cols
    return df

# === UI ===
# === UI Header & Controls ===

top_col_right = st.columns([8, 1])
with top_col_right[1]:
    st.page_link("main.py", label="🏠 To Main")

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

st.title("📊 Data Wrangling & Visualization UI")
st.subheader(":one: Drag & drop log files (multiple or single)")

# === 1. File Upload UI ===
file_labels = ["pTAT", "DTT", "THI", "FanCK", "logger"]
cols = st.columns(len(file_labels))
uploaded_data = {}

for i, label in enumerate(file_labels):
    with cols[i]:
        st.markdown(f"<h5 style='text-align:left; margin-bottom: 0rem;'>📁 {label}</h5>", unsafe_allow_html=True)
        uploaded_files = st.file_uploader("", accept_multiple_files=True, key=f"file_{label}")
        if uploaded_files:
            uploaded_data[label] = []
            for idx, f in enumerate(uploaded_files):
                try:
                    if label == "THI":
                        file_str = f.read().decode('utf-8', errors='ignore')
                        df = convert_thi_txt_to_df(file_str)
                    elif label == "logger":
                        df, error = extract_logger_columns_with_conversion(f)
                        if error:
                            st.warning(f"Logger parse error: {error}")
                            continue
                    elif label == "FanCK":
                        df = convert_fanck_file(f)
                    else:
                        df = read_generic_csv(f, label)
                except Exception as e:
                    st.warning(f"❗ Error processing {label}: {e}")
                    continue

                uploaded_data[label].append(df)

                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label=f"📥 {label}_{idx+1} download converted file (CSV)",
                    data=csv,
                    file_name=f"{label}_{idx+1}_converted.csv",
                    mime='text/csv'
                )

# === 2. Run Conversion Condition Check ===

valid_uploaded_count = sum(1 for label in file_labels if label in uploaded_data and uploaded_data[label])

if "run_conversion" not in st.session_state:
    st.session_state.run_conversion = False

if st.session_state.get("run_conversion", False):
    st.session_state.run_conversion = False

if st.button("▶️ Run Conversion"):
    if valid_uploaded_count >= 2:
        st.session_state.run_conversion = True
    else:
        st.warning("⚠️ Please upload at least 2 different log types before running conversion.")

# === 3. Conversion Output & Plotly Graph Settings ===

if st.session_state.run_conversion:
    st.subheader("🔗 Auto Merge Logs (Triggered by ▶️ Run Conversion)")

    valid_uploaded = {label: dfs[0] for label, dfs in uploaded_data.items() if dfs}

    if len(valid_uploaded) >= 2:
        try:
            def extract_time(df):
                for col in df.columns:
                    if "time" in col.lower():
                        try:
                            converted = pd.to_datetime(df[col], format="%H:%M:%S", errors='coerce')
                            if converted.notna().sum() > 0:
                                df = df.copy()
                                df["Time"] = converted
                                return df.dropna(subset=["Time"]).sort_values("Time").reset_index(drop=True)
                        except Exception:
                            continue
                raise ValueError("No valid Time column found")

            dfs = []
            start_times = []
            for label, df in valid_uploaded.items():
                df = extract_time(df)
                dfs.append(df)
                start_times.append(df["Time"].iloc[0])

            reference_time = min(start_times)
            st.info(f"⏰ Reference Time: {reference_time.strftime('%H:%M:%S')}")

            trimmed_dfs = [df[df["Time"] >= reference_time].copy().reset_index(drop=True) for df in dfs]

            merged_df = trimmed_dfs[0]
            for df in trimmed_dfs[1:]:
                merged_df = pd.merge(merged_df, df, on="Time", how="outer")

            merged_df = merged_df.sort_values("Time").reset_index(drop=True)
            merged_df["Time"] = merged_df["Time"].dt.strftime("%H:%M:%S")

            time_related_cols = [col for col in merged_df.columns if col.lower().startswith("time") and col != "Time"]
            other_cols = [col for col in merged_df.columns if col not in ["Time"] + time_related_cols]
            merged_df = merged_df[["Time"] + time_related_cols + other_cols]

            st.session_state["merged_df"] = merged_df
            st.success("✅ Merge completed successfully!")

            csv_merged = merged_df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 Download Merged CSV",
                data=csv_merged,
                file_name="merged_logs.csv",
                mime="text/csv"
            )

        except Exception as e:
            st.error(f"❌ Merge failed during conversion: {e}")
            st.stop()
    else:
        st.warning("⚠️ Please upload at least two different log types.")
        st.stop()

    st.session_state.run_conversion = False

    # === 이후 Plotly 그래프 출력 ===
st.subheader("📈 Plotly Graph Settings")

plot_mode = st.radio("Select plotting mode", ["Segment", "Merged"], horizontal=True)

if plot_mode == "Segment":
    all_columns = sorted(set().union(*[df.columns.tolist() for dfs in uploaded_data.values() for df in dfs]))
else:
    merged_df = st.session_state.get("merged_df", None)
    all_columns = merged_df.columns.tolist()

if not all_columns:
    st.warning("❗ No columns available for plotting.")
    st.stop()

if "x_axis" not in st.session_state or st.session_state.x_axis not in all_columns:
    time_candidates = [col for col in all_columns if "time" in col.lower()]
    st.session_state.x_axis = time_candidates[0] if time_candidates else all_columns[0]

if "y_axes" not in st.session_state:
    st.session_state.y_axes = {}
if "sorted_y_axes" not in st.session_state:
    st.session_state.sorted_y_axes = {}

st.markdown("#### Select X-axis column")
st.session_state.x_axis = st.selectbox(" ", options=all_columns, key="x_axis_global")

y_select_cols = st.columns(len(file_labels))
for i, label in enumerate(file_labels):
    if plot_mode == "Segment":
        available_cols = []
        if label in uploaded_data:
            for df in uploaded_data[label]:
                available_cols += df.columns.tolist()
    else:
        available_cols = merged_df.columns.tolist()

    available_cols = sorted(set(available_cols))

    if label not in st.session_state.y_axes:
        st.session_state.y_axes[label] = []
    if label not in st.session_state.sorted_y_axes:
        st.session_state.sorted_y_axes[label] = []

    y_col = y_select_cols[i].selectbox(
        f"Add Y-axis column ({label})",
        options=[""] + [col for col in available_cols if col not in st.session_state.sorted_y_axes[label]],
        key=f"y_axis_add_{label}"
    )
    if y_col:
        if y_col not in st.session_state.sorted_y_axes[label]:
            st.session_state.sorted_y_axes[label].append(y_col)
        st.session_state.y_axes[label] = st.session_state.sorted_y_axes[label].copy()

st.markdown("#### Selected Y-axis columns (sortable & removable)")
y_multi_cols = st.columns(len(file_labels))
visible_all = []
for i, label in enumerate(file_labels):
    sorted_y = st.session_state.sorted_y_axes[label]
    visible = y_multi_cols[i].multiselect(
        f"Columns to plot ({label})",
        options=sorted_y,
        default=st.session_state.y_axes[label],
        key=f"visible_{label}"
    )
    st.session_state.y_axes[label] = visible
    visible_all += visible

if st.session_state.x_axis and visible_all:
    combined_df = pd.DataFrame()

    if plot_mode == "Segment":
        for label, dfs in uploaded_data.items():
            for df in dfs:
                if st.session_state.x_axis in df.columns:
                    valid_y = [y for y in st.session_state.y_axes[label] if y in df.columns]
                    if valid_y:
                        temp_df = df[[st.session_state.x_axis] + valid_y].dropna()
                        combined_df = pd.concat([combined_df, temp_df], ignore_index=True)
    elif plot_mode == "Merged" and merged_df is not None:
        valid_y = [y for y in visible_all if y in merged_df.columns]
        if st.session_state.x_axis in merged_df.columns and valid_y:
            combined_df = merged_df[[st.session_state.x_axis] + valid_y].dropna()

    if not combined_df.empty:
        combined_df = combined_df.loc[:, ~combined_df.columns.duplicated()]
        fig = px.line(
            combined_df,
            x=st.session_state.x_axis,
            y=[col for col in visible_all if col in combined_df.columns],
            title=f"{plot_mode} Mode Chart"
        )
st.plotly_chart(fig, use_container_width=True)






