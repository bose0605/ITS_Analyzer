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

st.markdown("""
<style>
button[data-testid="stDownloadButton-template-download"] {
    background-color: #039CB2;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    font-size: 1rem;
    margin-top: 30px;
}
button[data-testid="stDownloadButton-template-download"]:hover {
    background-color: #105d96;
}
</style>
""", unsafe_allow_html=True)

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
    return df, excel_data

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
st.subheader("Drag & drop log files (multiple or single)")


# === 1. File Upload UI ===
file_labels = ["pTAT", "DTT", "THI", "FanCK", "logger"]
cols = st.columns(len(file_labels))
uploaded_data = {}

# 첫 번째 줄 (기본 파일들)
for i, label in enumerate(file_labels):
    with cols[i]:
        st.markdown(f"<h5 style='text-align:left; margin-bottom: 0rem;'>📁 {label}</h5>", unsafe_allow_html=True)
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

plot_mode = st.radio("Select plotting mode (Segment : Not create merged time column, Merged : Create 'Time (Merged)' column", ["Segment", "Merged"], horizontal=True)
if "run_conversion" not in st.session_state:
    st.session_state.run_conversion = False
        # CSSで横長スタイルに
    
if st.button("▶️ Run Conversion"):
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
                st.info(f"⏰ Reference Time: {reference_time.strftime('%H:%M:%S')}")

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

        # --- 修正ここ부터 ---
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
        # --- 修正ここまで ---

        if not available_columns:
            st.warning("⚠️ データをアップロードし、Run Conversionを押してください。")
        else:
            st.session_state.x_axis = st.selectbox(
                "Select X-axis column",
                options=available_columns,
                index=available_columns.index(st.session_state.x_axis) if st.session_state.x_axis in available_columns else 0
            )

        # Add Y-axis column (5×2配置)
        y_axis_cols_row1 = st.columns(len(file_labels))  # 1行目: 각 업로더
        y_axis_cols_row2 = st.columns(5)  # 2행目: Wistron Tool + GPU mon + 空白3つ

        # 선택된 열을 저장할 리스트 (세션 스테이트로 관리)
        if "selected_columns" not in st.session_state:
            st.session_state.selected_columns = []

        # 1행目: 각 업로더에 대응하는 selectbox 생성
        for i, label in enumerate(file_labels):
            with y_axis_cols_row1[i]:
                if label in uploaded_data and uploaded_data[label]:  # 업로드된 데이터가 있는 경우
                    available_options = [
                        col for col in uploaded_data[label][0].columns
                        if col not in st.session_state.selected_columns
                    ]  # 이미 선택된 열 제외
                    selected_column = st.selectbox(
                        f"Add Y-axis column ({label})",
                        options=[""] + available_options,  # 빈 선택지 추가
                        key=f"y_axis_{label}"
                    )
                    if selected_column and selected_column not in st.session_state.selected_columns:
                        st.session_state.selected_columns.append(selected_column)
                else:  # 업로드되지 않은 경우
                    st.selectbox(
                        f"Add Y-axis column ({label})",
                        options=[],
                        key=f"y_axis_{label}",
                        disabled=True
                    )

        # 2행目: Wistron Tool 과 GPU mon 에 대응하는 selectbox 생성
        wistron_tool_label = "Wistron Tool"
        gpu_mon_label = "GPU mon"

        with y_axis_cols_row2[0]:  # 2행目の左から1番目
            if wistron_tool_label in uploaded_data and uploaded_data[wistron_tool_label]:
                available_options = [
                    col for col in uploaded_data[wistron_tool_label][0].columns
                    if col not in st.session_state.selected_columns
                ]  # すでに選択された列を除外
                selected_column = st.selectbox(
                    f"Add Y-axis column ({wistron_tool_label})",
                    options=[""] + available_options,  # 空の選択肢を追加
                    key=f"y_axis_{wistron_tool_label}"
                )
                if selected_column and selected_column not in st.session_state.selected_columns:
                    st.session_state.selected_columns.append(selected_column)
            else:
                st.selectbox(
                    f"Add Y-axis column ({wistron_tool_label})",
                    options=[],
                    key=f"y_axis_{wistron_tool_label}",
                    disabled=True
                )

        with y_axis_cols_row2[1]:  # 2行目の左から2番目
            if gpu_mon_label in uploaded_data and uploaded_data[gpu_mon_label]:
                available_options = [
                    col for col in uploaded_data[gpu_mon_label][0].columns
                    if col not in st.session_state.selected_columns
                ]  # すでに選択された列を除外
                selected_column = st.selectbox(
                    f"Add Y-axis column ({gpu_mon_label})",
                    options=[""] + available_options,  # 空の選択肢を追加
                    key=f"y_axis_{gpu_mon_label}"
                )
                if selected_column and selected_column not in st.session_state.selected_columns:
                    st.session_state.selected_columns.append(selected_column)
            else:
                st.selectbox(
                    f"Add Y-axis column ({gpu_mon_label})",
                    options=[],
                    key=f"y_axis_{gpu_mon_label}",
                    disabled=True
                )
        # ▼ ここでmultiselectを追加
        st.session_state.selected_columns = st.multiselect(
            "Selected Y-axis columns",
            options=st.session_state.selected_columns,
            default=st.session_state.selected_columns,
            key="y_axis_multiselect",
            disabled=False
        )

        # ▼▼▼ ここからPlotlyグラフ描画 ▼▼▼

        with st.expander(":hammer_and_wrench: Chart options", expanded=False):  # Expanderを追加
            # カラーマップ選択
            colormap_list = sorted(plt.colormaps())
            default_cmap = "viridis"

            if "plotly_colormap" not in st.session_state:
                st.session_state["plotly_colormap"] = default_cmap

            selected_cmap = st.selectbox(
                "🎨Choose colormap for the Chart",
                colormap_list,
                index=colormap_list.index(st.session_state["plotly_colormap"]),
                key="plotly_colormap_select"
            )

            # 選択されたカラーマップをセッションステートに保存
            st.session_state["plotly_colormap"] = selected_cmap

            # カラーマップを取得
            cmap = plt.get_cmap(st.session_state["plotly_colormap"])

            # X軸とY軸の列を取得
            x_col = st.session_state.get("x_axis")
            y_cols = st.session_state.get("selected_columns", [])

            # 2段組みのテキスト入力を追加
            x_y_title_cols = st.columns(2)
            with x_y_title_cols[0]:
                x_axis_title = st.text_input("X-axis title", value="X-axis", key="x_axis_title")
            with x_y_title_cols[1]:
                y_axis_title = st.text_input("Y-axis title", value="Y-axis", key="y_axis_title")

        if plot_df is not None and x_col and y_cols:
            fig = go.Figure()

            # データ数に依存する配色
            for i, y in enumerate(y_cols):
                if y in plot_df.columns:
                    color = mcolors.to_hex(cmap(i / max(len(y_cols) - 1, 1)))  # データ数に基づく色を取得
                    fig.add_trace(go.Scatter(
                        x=plot_df[x_col],
                        y=plot_df[y],
                        mode="lines",
                        name=y,
                        line=dict(color=color)
                    ))

            # X軸とY軸のタイトルを設定
            fig.update_layout(
                xaxis_title=x_axis_title,
                yaxis_title=y_axis_title,
                legend_title="Y Columns",
                height=500,
                margin=dict(l=40, r=40, t=40, b=40)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ Please select at least one X-axis and Y-axis column to plot.")


