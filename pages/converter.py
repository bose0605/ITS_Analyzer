import streamlit as st
import pandas as pd
from io import BytesIO, StringIO
import plotly.graph_objects as go # type: ignore
import plotly.express as px
from plotly.subplots import make_subplots
import xlsxwriter
import re
import os
import plotly.colors  # ファイル先頭付近でimport済みでなければ追加
import matplotlib.pyplot as plt  
import matplotlib as mpl
import matplotlib.colors as mcolors  # mcolorsをインポート
from streamlit_tags import st_tags  # 必要に応じてインポート

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """
    <style>
    div.stDownloadButton > button {
        background-color: crimson;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-size: 1rem;
    }
    div.stDownloadButton > button:hover {
        background-color: darkred;
    }
    </style>
    """,
    unsafe_allow_html=True
)

def sanitize_numeric_columns(df: pd.DataFrame, exclude_columns=None) -> pd.DataFrame:
    if exclude_columns is None:
        exclude_columns = []
    for col in df.columns:
        if col not in exclude_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

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
    df = sanitize_numeric_columns(df, exclude_columns=["Time"])
    return df
# === Wistron tool Parser ===
def convert_wistron_tool_file(uploaded_file):
    if uploaded_file is None:
        st.warning("⚠️ Wistron Tool file not uploaded.")
        return None, None

    try:
        content = uploaded_file.read().decode('utf-8', errors='ignore')
        df = pd.read_csv(StringIO(content), sep="\t")

        # ✅ Time 컬럼을 문자열 "HH:MM:SS" 형식으로 변환
        time_col = df.columns[0]
        df[time_col] = pd.to_datetime(df[time_col], format="%H:%M:%S", errors='coerce')
        df[time_col] = df[time_col].dt.strftime("%H:%M:%S")

    except Exception as e:
        st.error(f"❌ Failed to read Wistron Tool file: {e}")
        return None, None

    def convert_df_to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Wistron Tool Log')
        return output.getvalue()

    excel_data = convert_df_to_excel(df)
    df[time_col] = df[time_col].dt.strftime("%H:%M:%S")
    df = sanitize_numeric_columns(df, exclude_columns=["Time"])
    return df, excel_data

# === GPUmon tool Parser ===
def convert_gpumon_file(file) -> pd.DataFrame:
    try:
        # 64행이 헤더니까 그 전 줄은 건너뛰기
        df = pd.read_csv(file, encoding='utf-8', sep=",", engine="python", skiprows=63)

        df["Time"] = pd.to_datetime(df["date"] + " " + df["time"], errors='coerce')
        df = df.dropna(subset=["Time"]).copy()
        df["Time"] = df["Time"].dt.strftime("%H:%M:%S")

        time_col = df.pop("Time")
        df.insert(0, "Time", time_col)

        df.columns = ["Time"] + [f"{col} (GPUmon)" for col in df.columns[1:]]
        df = sanitize_numeric_columns(df, exclude_columns=["Time"]) 
        return df

    except Exception as e:
        st.warning(f"⚠️ GPUmon 파일 처리 오류: {e}")
        return pd.DataFrame()

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

    df.iloc[:, 0] = df.iloc[:, 0].apply(convert_to_time).astype(str)
    original_cols = df.columns.tolist()
    renamed_cols = ["Time"] + [f"{col}" for col in original_cols[1:]]
    df.columns = renamed_cols
    df = sanitize_numeric_columns(df, exclude_columns=["Time"])
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
    df = sanitize_numeric_columns(df, exclude_columns=[col for col in df.columns if "Time" in col])  # 追加
    return df

# === UI ===
top_col_right = st.columns([8, 1])
with top_col_right[1]:
    st.page_link("main.py", label="🏠 To Main")

# 🌈 虹色ライン
st.markdown("""
<hr style="
  height: 8px;
  border: none;
  border-radius: 3px;
  background: linear-gradient(to right, red, orange, yellow, green, blue, indigo, violet);
  margin-top: 10px;
  margin-bottom: 4px;
">
""", unsafe_allow_html=True)
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

st.title("📊 Data Wrangling & Visualization UI", help="This application allows you to upload, process, and visualize various log files. Use the drag-and-drop feature to upload files, select plotting modes, and customize your charts.")
st.subheader(
    ":one: Drag & drop log files (Available multiple or single)",
    help="Upload your log files here. Supported formats include CSV, TXT, and Excel files. The application will automatically process the files and prepare them for visualization."
)

# === 1. File Upload UI ===
file_labels = ["pTAT", "DTT", "THI", "FanCK", "logger"]
cols = st.columns(len(file_labels))
uploaded_data = {}

# 첫 번째 줄 (기본 파일들)
for i, label in enumerate(file_labels):
    with cols[i]:
        if label == "pTAT":
            st.markdown(
                f"<h5 style='text-align:left; margin-bottom: 0rem;'>📁 {label}</h5>",
                help="pTAT: convert Time column from hh:mm:ss:msec → hh:mm:ss",
                unsafe_allow_html=True,
                
            )
        elif label == "DTT":
            st.markdown(
                f"<h5 style='text-align:left; margin-bottom: 0rem;'>📁 {label}</h5>",
                unsafe_allow_html=True,
                help="DTT: new creation Watts column from all (mW)"
            )
        elif label == "THI":
            st.markdown(
                f"<h5 style='text-align:left; margin-bottom: 0rem;'>📁 {label}</h5>",
                unsafe_allow_html=True,
                help="THI: new creation to 1 sec period"
            )
        else:
            st.markdown(
                f"<h5 style='text-align:left; margin-bottom: 0rem;'>📁 {label}</h5>",
                unsafe_allow_html=True
            )
        uploaded_files = st.file_uploader(
            label=" ",  # 빈 문자열로 label 경고 피하기
            accept_multiple_files=True,
            key=f"file_{label}",
            label_visibility="collapsed"
        )
        if uploaded_files:
            uploaded_data[label] = []
            for idx, f in enumerate(uploaded_files):
                try:
                    if label == "THI":
                        file_str = f.read().decode('utf-8', errors='ignore')
                        df = convert_thi_txt_to_df(file_str)
                        df.columns = [col if col.lower() == "time" else f"{col} ({label})" for col in df.columns]
                    elif label == "logger":
                        df, error = extract_logger_columns_with_conversion(f)
                        if error:
                            st.warning(f"Logger parse error: {error}")
                            continue
                        df.columns = [col if col.lower() == "time" else f"{col} ({label})" for col in df.columns]
                    elif label == "FanCK":
                        df = convert_fanck_file(f)
                        df.columns = [col if col.lower() == "time" else f"{col} ({label})" for col in df.columns]
                    else:
                        df = read_generic_csv(f, label)

                    uploaded_data[label].append(df)

                    csv = df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label=f"📥 {label}_{idx+1} download converted file (CSV)",
                        data=csv,
                        file_name=f"{label}_{idx+1}_converted.csv",
                        mime='text/csv'
                    )
                except Exception as e:
                    st.warning(f"❗ Error processing {label}: {e}")
                    continue

# === Wistron Tool 파일 업로드 UI 영역 ===
cols = st.columns([1, 1, 1, 2])  # 가운데만 사용

with cols[0]:
    label = "Wistron Tool"
    st.markdown(f"<h5 style='text-align:left;'>📁 {label}</h5>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        label=" ",
        accept_multiple_files=True,
        key=f"file_{label}",
        label_visibility="collapsed"
    )

    if uploaded_files:
        uploaded_data[label] = []
        for idx, f in enumerate(uploaded_files):
            try:
                df, _ = convert_wistron_tool_file(f)
                if df is not None:
                    df.columns = [col if col.lower() == "time" else f"{col} ({label})" for col in df.columns]
                    uploaded_data[label].append(df)
                    csv = df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label=f"📥 {label}_{idx+1} download converted file (CSV)",
                        data=csv,
                        file_name=f"{label}_{idx+1}_converted.csv",
                        mime='text/csv'
                    )
            except Exception as e:
                st.warning(f"❗ Error processing {label}: {e}")
                continue

# 📁 GPU mon
with cols[1]:
    label = "GPU mon"
    st.markdown(f"<h5 style='text-align:left;'>📁 {label}</h5>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        label=" ",
        accept_multiple_files=True,
        key=f"file_{label}",
        label_visibility="collapsed"
    )
    if uploaded_files:
        uploaded_data[label] = []
        for idx, f in enumerate(uploaded_files):
            try:
                df = convert_gpumon_file(f)  # ✅ 정확하게 호출됨
                df.columns = [col if col.lower() == "time" else f"{col} ({label})" for col in df.columns]
                uploaded_data[label].append(df)
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label=f"📥 {label}_{idx+1} download converted file (CSV)",
                    data=csv,
                    file_name=f"{label}_{idx+1}_converted.csv",
                    mime="text/csv"
                )
            except Exception as e:
                st.warning(f"❗ Error processing {label}: {e}")
                continue

st.markdown("""
        <style>
        div.stButton > button {
            width: 100%;
            padding: 1rem;
            font-size: 1.2rem;
            background-color: #28a745;
            color: white;
            border: none;
            border-radius: 8px;
        }
        div.stButton > button:hover {
            background-color: #218838;
        }
        </style>
    """, unsafe_allow_html=True)
# === 2. Run Conversion Condition Check ===
valid_uploaded_count = sum(1 for label in uploaded_data if uploaded_data[label])

st.subheader(":two: Select plotting mode")
plot_mode = st.radio(
    "Segment : Not create merged time column, Merged : Create 'Time (Merged)' column",
    ["Segment", "Merged"],
    horizontal=True
)
if "run_conversion" not in st.session_state:
    st.session_state.run_conversion = False
        # CSSで横長スタイルに
    
if st.button("🚀 Run Conversion"):
    if valid_uploaded_count >= 1:
        with st.spinner("⏳ Converting and Merging logs..."):
            st.session_state.run_conversion = True


# === 3. Conversion Output & Plotly Graph Settings ===
if st.session_state.run_conversion:
    if plot_mode == "Merged":
        valid_uploaded = {label: dfs[0] for label, dfs in uploaded_data.items() if dfs}

        if len(valid_uploaded) >= 1:
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

                reference_time = min(start_times) if len(start_times) > 1 else start_times[0]
                
                # 2段組みのレイアウトを作成 (1:4の比率)
                ref_time_cols = st.columns([1, 2,1])

                with ref_time_cols[1]:  # 左側にReference Timeを表示
                    st.info(f"⏰ Reference Time: {reference_time.strftime('%H:%M:%S')}")

                with ref_time_cols[0]:  # 右側にダウンロードボタンを配置
                    trimmed_dfs = [df[df["Time"] >= reference_time].copy().reset_index(drop=True) for df in dfs]

                    merged_df = trimmed_dfs[0]
                    for df in trimmed_dfs[1:]:
                        merged_df = pd.merge(merged_df, df, on="Time", how="outer")

                    merged_df = merged_df.sort_values("Time").reset_index(drop=True)
                    merged_df["Time"] = merged_df["Time"].dt.strftime("%H:%M:%S")

                    # 重複防止して1回だけTime (Merged) にする
                    if "Time (Merged)" not in merged_df.columns:
                        merged_df.rename(columns={"Time": "Time (Merged)"}, inplace=True)

                    st.session_state["merged_df"] = merged_df

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
            st.stop()

    elif plot_mode == "Segment":
        # Segmentではマージ処理しない、個別のファイルを使用する
        st.session_state["merged_df"] = None

    # === 이후 Plotly 그래프 출력 ===
    st.subheader("📈 Chart Settings")
    with st.spinner("Drawing chart..."):

        # Select X-axis column
        if "x_axis" not in st.session_state:
            st.session_state.x_axis = None

        merged_df = st.session_state.get("merged_df")

        # --- 修正ここから ---
        if merged_df is not None and isinstance(merged_df, pd.DataFrame):
            available_columns = list(merged_df.columns)
            plot_df = merged_df
        else:
            # Segmentモードやデータがない場合、アップロード済みの最初のデータフレームからカラムを取得
            plot_df = None
            available_columns = []
            for dfs in uploaded_data.values():
                if dfs and isinstance(dfs[0], pd.DataFrame):
                    available_columns = list(dfs[0].columns)
                    plot_df = dfs[0]
                    break

        # Mergedモード時は "Time (Merged)" をデフォルトでセット
        if plot_mode == "Merged" and "Time (Merged)" in available_columns:
            st.session_state.x_axis = "Time (Merged)"
        elif st.session_state.x_axis not in available_columns:
            st.session_state.x_axis = available_columns[0] if available_columns else None
            # ▼▼▼ 1st Y-axis Expander ▼▼▼
        with st.expander("1st X＆Y-axis", expanded=True):
            # Select X-axis column
            if not available_columns:
                st.warning("⚠️ Press Run conversion")
            else:
                st.session_state.x_axis = st.selectbox(
                    "Select X-axis column (Skin temp)",
                    options=available_columns,
                    index=available_columns.index(st.session_state.x_axis) if st.session_state.x_axis in available_columns else 0
                )
            # Add Y-axis column (5×2配置)
            y_axis_cols_row1 = st.columns(len(file_labels))  # 1行目: 各アップローダー
            y_axis_cols_row2 = st.columns(5)  # 2行目: Wistron Tool + GPU mon + 空白3つ

            # 선택된 열을 저장할 리스트 (세션 스테이트로 관리)
            if "selected_columns" not in st.session_state:
                st.session_state.selected_columns = []

            # 1行目: 各アップローダーに対応するselectboxを生成
            for i, label in enumerate(file_labels):
                with y_axis_cols_row1[i]:
                    if label in uploaded_data and uploaded_data[label]:  # アップロードされたデータがある場合
                        available_options = [
                            col for col in uploaded_data[label][0].columns
                            if col not in st.session_state.selected_columns
                        ]  # すでに選択された列を除外
                        selected_column = st.selectbox(
                            f"Add Y-axis column ({label})",
                            options=[""] + available_options,  # 空の選択肢を追加
                            key=f"y_axis_{label}"
                        )
                        if selected_column and selected_column not in st.session_state.selected_columns:
                            st.session_state.selected_columns.append(selected_column)  # 即座に追加
                            # st.session_state[f"y_axis_{label}"] = ""  ← この行を削除
                    else:  # アップロードされていない場合
                        st.selectbox(
                            f"Add Y-axis column ({label})",
                            options=[],
                            key=f"y_axis_{label}",
                            disabled=True
                        )

            # 2行目: Wistron ToolとGPU monに対応するselectboxを生成
            wistron_tool_label = "Wistron Tool"
            gpu_mon_label = "GPU mon"

            with y_axis_cols_row2[0]:  # 2行目の左から1番目
                selected_column_key = f"y_axis_{wistron_tool_label}"
                if wistron_tool_label in uploaded_data and uploaded_data[wistron_tool_label]:
                    available_options = [
                        col for col in uploaded_data[wistron_tool_label][0].columns
                        if col not in st.session_state.selected_columns
                    ]  # すでに選択された列を除外
                    selected_column = st.selectbox(
                        f"Add Y-axis column ({wistron_tool_label})",
                        options=[""] + available_options,  # 空の選択肢を追加
                        key=selected_column_key
                    )
                    if selected_column and selected_column not in st.session_state.selected_columns:
                        st.session_state.selected_columns.append(selected_column)  # 即座に追加
                        st.session_state[selected_column_key] = ""
                else:
                    st.selectbox(
                        f"Add Y-axis column ({wistron_tool_label})",
                        options=[],
                        key=f"y_axis_{wistron_tool_label}",
                        disabled=True
                    )

            with y_axis_cols_row2[1]:  # 2行目の左から2番目
                selected_column_key = f"y_axis_{gpu_mon_label}"
                if gpu_mon_label in uploaded_data and uploaded_data[gpu_mon_label]:
                    available_options = [
                        col for col in uploaded_data[gpu_mon_label][0].columns
                        if col not in st.session_state.selected_columns
                    ]  # すでに選択された列を除外
                    selected_column = st.selectbox(
                        f"Add Y-axis column ({gpu_mon_label})",
                        options=[""] + available_options,  # 空の選択肢を追加
                        key=selected_column_key
                    )
                    if selected_column and selected_column not in st.session_state.selected_columns:
                        st.session_state.selected_columns.append(selected_column)  # 即座に追加
                        st.session_state[selected_column_key] = ""
                else:
                    st.selectbox(
                        f"Add Y-axis column ({gpu_mon_label})",
                        options=[],
                        key=f"y_axis_{gpu_mon_label}",
                        disabled=True
                    )

            # ▼ multiselectを追加
            selected_columns = st.multiselect(
                "Selected Y-axis columns (Sensor temp)",
                options=st.session_state.get("selected_columns", []),
                default=st.session_state.get("selected_columns", []),
                key="y_axis_multiselect",
                disabled=False
            )

            # 選択された列を即座に反映
            st.session_state["selected_columns"] = selected_columns

        # 2nd Y-axis Expander
        with st.expander("2nd Y-axis", expanded=False):
            # Add Y-axis column (5×2配置)
            y_axis_cols_row1 = st.columns(len(file_labels))  # 1行目: 各アップローダー
            y_axis_cols_row2 = st.columns(5)  # 2行目: Wistron Tool + GPU mon + 空白3つ

            # 選択された列を保存するリスト (セッションステートで管理)
            if "secondary_selected_columns" not in st.session_state:
                st.session_state.secondary_selected_columns = []

            # 1行目: 各アップローダーに対応するselectboxを生成
            for i, label in enumerate(file_labels):
                with y_axis_cols_row1[i]:
                    if label in uploaded_data and uploaded_data[label]:  # アップロードされたデータがある場合
                        available_options = [
                            col for col in uploaded_data[label][0].columns
                            if col not in st.session_state.secondary_selected_columns
                        ]  # すでに選択された列を除外

                        # 動的にキーを生成
                        dynamic_key = f"secondary_y_axis_selectbox_{label}_{len(st.session_state.secondary_selected_columns)}"

                        selected_column = st.selectbox(
                            f"Add 2nd Y-axis column ({label})",
                            options=[""] + available_options,  # 空の選択肢を追加
                            key=dynamic_key
                        )
                        if selected_column and selected_column not in st.session_state.secondary_selected_columns:
                            st.session_state.secondary_selected_columns.append(selected_column)  # 即座に追加
                    else:
                        st.selectbox(
                            f"Add 2nd Y-axis column ({label})",
                            options=[],
                            key=f"secondary_y_axis_selectbox_{label}",
                            disabled=True
                        )

            # 2行目: Wistron ToolとGPU monに対応するselectboxを生成
            wistron_tool_label = "Wistron Tool"
            gpu_mon_label = "GPU mon"

            with y_axis_cols_row2[0]:  # 2行目の左から1番目
                selected_column_key =f"secondary_y_axis_selectbox_{wistron_tool_label}"
                if wistron_tool_label in uploaded_data and uploaded_data[wistron_tool_label]:
                    available_options = [
                        col for col in uploaded_data[wistron_tool_label][0].columns
                        if col not in st.session_state.secondary_selected_columns
                    ]  # すでに選択された列を除外
                    selected_column = st.selectbox(
                        f"Add 2nd Y-axis column ({wistron_tool_label})",
                        options=[""] + available_options,  # 空の選択肢を追加
                        key=selected_column_key
                    )
                    if selected_column and selected_column not in st.session_state.secondary_selected_columns:
                        st.session_state.secondary_selected_columns.append(selected_column)
                        st.session_state[selected_column_key] = ""  # 選択を即クリア
                else:
                    st.selectbox(
                        f"Add 2nd Y-axis column ({wistron_tool_label})",
                        options=[],
                        key=selected_column_key,
                        disabled=True
                    )

            with y_axis_cols_row2[1]:  # 2行目の左から2番目
                selected_column_key =f"secondary_y_axis_selectbox_{gpu_mon_label}"
                if gpu_mon_label in uploaded_data and uploaded_data[gpu_mon_label]:
                    available_options = [
                        col for col in uploaded_data[gpu_mon_label][0].columns
                        if col not in st.session_state.secondary_selected_columns
                    ]  # すでに選択された列を除外
                    selected_column = st.selectbox(
                        f"Add 2nd Y-axis column ({gpu_mon_label})",
                        options=[""] + available_options,  # 空の選択肢を追加
                        key=selected_column_key 
                    )
                    if selected_column and selected_column not in st.session_state.secondary_selected_columns:
                        st.session_state.secondary_selected_columns.append(selected_column)
                        st.session_state[selected_column_key] = ""  # 選択を即クリア
                else:
                    st.selectbox(
                        f"Add 2nd Y-axis column ({gpu_mon_label})",
                        options=[],
                        key=selected_column_key,
                        disabled=True
                    )

            # ▼ multiselectを追加
            selected_columns = st.multiselect(
                "Selected 2nd Y-axis columns (Sensor temp)",
                options=st.session_state.secondary_selected_columns,
                default=st.session_state.secondary_selected_columns,
                key="selected_secondary_y_axis_multiselect",
                disabled=False
            )

            # 選択された列をセッションステートに反映
            st.session_state.secondary_selected_columns = selected_columns

        # Chart options Expander
        with st.expander(":hammer_and_wrench: Chart options", expanded=False):
            # カラーマップ選択
            colormap_list = sorted(plt.colormaps())
            default_cmap = "jet" 

            # 3段組のレイアウトを作成
            chart_option_cols = st.columns(3)

            # 左の列: カラーマップ選択
            with chart_option_cols[0]:
                if "plotly_colormap" not in st.session_state:
                    st.session_state["plotly_colormap"] = "jet"

                # 明示的に現在の選択を取得する変数（この行で確実に更新された値が入る）
                current_cmap_selection = st.selectbox(
                    "🎨 Choose colormap for the Chart",
                    colormap_list,
                    index=colormap_list.index(st.session_state["plotly_colormap"]),
                    key="plotly_colormap"
                )
                # 明示的に選択を反映（セッションステートは更新されるが、即反映にはこの変数を使うのが安全）
                cmap = plt.get_cmap(current_cmap_selection)

            # 中央の列: 1st Y-axis shape
            with chart_option_cols[1]:
                y1_shapes = ["lines", "markers", "lines+markers"]
                selected_y1_shape = st.selectbox(
                    "1st Y-axis shape",
                    y1_shapes,
                    index=0,  # デフォルトは "lines"
                    key="y1_axis_shape_select"
                )

            # 右の列: 2nd Y-axis shape
            with chart_option_cols[2]:
                y2_shapes = ["lines", "markers", "lines+markers"]
                selected_y2_shape = st.selectbox(
                    "2nd Y-axis shape",
                    y2_shapes,
                    index=1,  # デフォルトは "markers"
                    key="y2_axis_shape_select"
                )

            # カラーマップを取得
            cmap = plt.get_cmap(st.session_state.get("plotly_colormap", "jet"))

            # X軸とY軸の列を取得
            x_col = st.session_state.get("x_axis")
            y_cols = st.session_state.get("selected_columns", [])  # 1st Y-axis columns
            secondary_y_cols = st.session_state.get("secondary_selected_columns", [])  # 2nd Y-axis columns

            # 第一軸と第二軸の列を結合
            plot_cols = y_cols + secondary_y_cols

            color_map_ui = {
                col: mcolors.to_hex(cmap(i / max(len(plot_cols) - 1, 1)))
                for i, col in enumerate(plot_cols)
            }

            # 3段組のテキスト入力を追加
            x_y_title_cols = st.columns(3)
            with x_y_title_cols[0]:
                x_axis_title = st.text_input("X-axis title", value="X-axis", key="x_axis_title")
            with x_y_title_cols[1]:
                y_axis_title = st.text_input("Y-axis title", value="Y-axis", key="y_axis_title")
            with x_y_title_cols[2]:
                second_y_axis_title = st.text_input("2nd Y-axis title", value="2nd Y-axis", key="second_y_axis_title")
        
plot_df = None  # 初期値としてNoneを設定
if st.session_state.run_conversion:
    # Run Conversionが押された後にplot_dfを設定
    merged_df = st.session_state.get("merged_df")

    if merged_df is not None and isinstance(merged_df, pd.DataFrame):
        plot_df = merged_df
    else:
        # Segmentモードやデータがない場合、アップロード済みの最初のデータフレームを使用
        for dfs in uploaded_data.values():
            if dfs and isinstance(dfs[0], pd.DataFrame):
                plot_df = dfs[0]
                break

if plot_df is not None and x_col:
    # 選択された列を含むデータフレームを作成
    selected_columns = [x_col] + y_cols + st.session_state.get("secondary_selected_columns", [])
    export_df = plot_df[selected_columns].copy()

    # --- ここで系列が1本もない場合をチェック ---
    if len(y_cols) + len(st.session_state.get("secondary_selected_columns", [])) == 0:
        st.warning("Add column at least one")
        excel_data = None  # 追加: エクセルデータもNoneに
    else:
        # データをExcelファイルに保存
        def convert_df_to_excel_with_chart(df):
            # Excel用にlineとmarkerの構成を返す関数
            def get_excel_line_marker_config(shape, color):
                if shape == "lines":
                    return {
                        "line": {"color": color},
                        "marker": {"type": "none"}  # 明示的にマーカー無しを指定
                    }
                elif shape == "markers":
                    return {
                        "line": {"none": True},
                        "marker": {"type": "circle", "size": 5, "border": {"none": True}, "fill": {"color": color}}
                    }
                elif shape == "lines+markers":
                    return {
                        "line": {"color": color},
                        "marker": {"type": "circle", "size": 5, "border": {"none": True}, "fill": {"color": color}}
                    }
                else:
                    return {
                        "line": {"color": color},
                        "marker": {"type": "none"}  # fallback
                    }

            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                # データを書き込む
                df.to_excel(writer, index=False, sheet_name="Plot Data")

                # ワークブックとワークシートを取得
                workbook = writer.book
                worksheet = writer.sheets["Plot Data"]

                # 各列の幅を77ピクセルに設定
                worksheet.set_column(0, len(df.columns) - 1, 77 / 7)  # 1文字幅は約7ピクセル

                # グラフを作成
                chart = workbook.add_chart({"type": "scatter", "subtype": "straight_with_markers"})

                # マーカータイプのマッピング
                marker_mapping = {
                    "lines": None,
                    "markers": "circle",
                    "lines+markers": "circle"
                }

                # 第一軸のデータを追加
                for i, y in enumerate(y_cols):
                    if y in df.columns:
                        color = color_map_ui[y]
                        config = get_excel_line_marker_config(selected_y1_shape, color)
                        chart.add_series({
                            "name": y,
                            "categories": ["Plot Data", 1, 0, len(df), 0],
                            "values": ["Plot Data", 1, i + 1, len(df), i + 1],
                            "line": config["line"],
                            "marker": config["marker"]
                        })

                # 第二軸のデータを追加
                secondary_y_cols = st.session_state.get("secondary_selected_columns", [])
                for i, y in enumerate(secondary_y_cols):
                    if y in df.columns:
                        color = color_map_ui[y]
                        config = get_excel_line_marker_config(selected_y2_shape, color)
                        chart.add_series({
                            "name": y,
                            "categories": ["Plot Data", 1, 0, len(df), 0],
                            "values": ["Plot Data", 1, len(y_cols) + i + 1, len(df), len(y_cols) + i + 1],
                            "line": config["line"],
                            "marker": config["marker"],
                            "y2_axis": True
                        })


                # グラフのレイアウトを設定
                chart.set_title({"name": "Plot Data Chart"})
                chart.set_x_axis({"name": x_axis_title})
                chart.set_y_axis({"name": y_axis_title})
                chart.set_y2_axis({"name": second_y_axis_title})

                # グラフをワークシートに挿入
                worksheet.insert_chart("B6", chart, {"x_scale": 1.8, "y_scale": 1.8})
            return output.getvalue() 

        excel_data = convert_df_to_excel_with_chart(export_df)

    # ダウンロードボタンはexcel_dataがNoneでない場合のみ表示
    if excel_data is not None:
        st.download_button(
            label="📥 To XLSX Output (with Charts)",
            data=excel_data,
            file_name="plot_data_with_chart.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # Plotlyグラフの描画も系列が1本以上ある場合のみ
    if len(y_cols) + len(st.session_state.get("secondary_selected_columns", [])) > 0:
        # Plotlyグラフの描画
        fig = go.Figure()

        # 第一軸の描画
        for i, y in enumerate(y_cols):
            if y in plot_df.columns:
                color = mcolors.to_hex(cmap(i / max(len(plot_cols) - 1, 1)))  # 選択したカラーマップを使用
                mode = selected_y1_shape  # 1st Y-axis shape の選択内容を反映
                fig.add_trace(go.Scatter(
                    x=plot_df[x_col],
                    y=plot_df[y],
                    mode=mode,  # 選択した形状を適用
                    name=y,
                    line=dict(color=color),  # カラーマップの色を適用
                    yaxis="y"
                ))

        # 第二軸の描画
        for i, y in enumerate(secondary_y_cols):
            if y in plot_df.columns:
                color = mcolors.to_hex(cmap((i + len(y_cols)) / max(len(plot_cols) - 1, 1)))  # 選択したカラーマップを使用
                mode = selected_y2_shape  # 2nd Y-axis shape の選択内容を反映
                fig.add_trace(go.Scatter(
                    x=plot_df[x_col],
                    y=plot_df[y],
                    mode=mode,  # 選択した形状を適用
                    name=y,
                    marker=dict(color=color),  # カラーマップの色を適用
                    yaxis="y2"
                ))

        # レイアウト設定
        fig.update_layout(
            xaxis=dict(
                title=dict(
                    text=x_axis_title,
                    font=dict(size=18)  # X軸タイトルのフォントサイズを設定
                ),
                tickfont=dict(size=16)  # X軸の値のフォントサイズを設定
            ),
            yaxis=dict(
                title=dict(
                    text=y_axis_title,
                    font=dict(size=18)  # Y軸タイトルのフォントサイズを設定
                ),
                tickfont=dict(size=16)  # Y軸の値のフォントサイズを設定
            ),
            yaxis2=dict(
                title=dict(
                    text=second_y_axis_title,
                    font=dict(size=18)  # 2nd Y軸タイトルのフォントサイズを設定
                ),
                tickfont=dict(size=16),  # 2nd Y軸の値のフォントサイズを設定
                overlaying="y",
                side="right",
                showgrid=False
            ),
            font=dict(size=16),  # 全体のフォントサイズを設定
            height=700,
            margin=dict(l=40, r=40, t=40, b=40),
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)

