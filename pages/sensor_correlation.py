import sys
from io import BytesIO
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import tempfile
import plotly.io as pio
from sensor_correlation_modules.pipeline_module_to_4 import full_logger_ptat_pipeline as pipeline_4
from sensor_correlation_modules.pipeline_module_to_5 import full_logger_ptat_pipeline as pipeline_5

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

top_col_right = st.columns([8, 1])
with top_col_right[1]:
    st.page_link("main.py", label="🏠 To Main")

# ==== タブ表示・タイトル表示 ====
st.markdown("""
<hr style="
  height: 8px;
  border: none;
  border-radius: 3px;
  background: linear-gradient(to right, #60a760, #9c8eb0, #d69e6a, #dad577, #335f8c, #b10c67, #039CB2);
  margin-top: 10px;
  margin-bottom: 4px;
">
""", unsafe_allow_html=True)

# ==== ✅ タブのフォントサイズを大きくする ====
st.markdown("""
<style>
button[data-baseweb="tab"] > div[data-testid="stMarkdownContainer"] > p {
    font-size: 19px !important;
    font-weight: bold;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# st.button用css
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

#st.download用CSS
st.markdown("""
    <style>
    div.stDownloadButton > button {
        width: 100%;
        padding: 1rem;
        font-size: 1.2rem;
        background-color: crimson;
    }
    </style>
""", unsafe_allow_html=True)

col1, non_col, col2, = st.columns([3,1,2])
with col1:
    st.title("📊 Sensor correlation analyzer")
with col2:
    try:
        template_path = os.path.join(os.path.dirname(__file__), "../sensor_correlation_modules/Result_template.xlsm")

    except NameError:
        template_path = os.path.join(os.getcwd(), "Result_template.xlsm")

    if os.path.exists(template_path):
        with open(template_path, "rb") as f:
            st.download_button(
                label="📥 Download XLSX Template (for Logger-PTAT)",
                data=f.read(),
                file_name="Result_template.xlsm",
                key="template-download"
            )
    else:
        st.warning("❗ Template not found.")
# st.subheader("### ")
col1, col2, non_col,radio_col = st.columns([5, 5, 1, 5])
with col1:    
    st.markdown("### 1️⃣ Upload files for analysis")
    logger_file = st.file_uploader("Logger raw data", type=None)
with col2:
    st.markdown("### ")
    ptat_file = st.file_uploader("pTAT raw data", type=["csv"])
with radio_col:
    st.markdown("### 2️⃣ Select Experiment Split Mode")
    # 初期化フラグを使って、segment selectboxの初期化を制御
    if "segment_defaults_set" not in st.session_state:
        st.session_state.segment_defaults_set = False
    def reset_segment_defaults():
        if st.session_state.split_mode == "4 segments":
            st.session_state.segment_values = ["pTAT+Fur", "pTAT", "Fur", "Prime95", "None/other"]
        else:
            st.session_state.segment_values = ["pTAT+Fur", "pTAT", "Fur", "Prime95", "pTAT+Fur+Charging"]
        st.session_state.segment_defaults_set = True

    split_mode = st.radio(
        "Choose number of experiment segments",
        ["4 segments", "5 segments"],
        index=0,
        key="split_mode",
        on_change=reset_segment_defaults
    )


st.markdown("### 3️⃣ Select Segment Labels")
segment_labels = ["1st segment", "2nd segment", "3rd segment", "4th segment", "5th segment"]
default_values = ["pTAT+Fur", "pTAT", "Fur", "Prime95", "None/other"]
select_options = ["None/other", "pTAT+Fur", "pTAT", "Fur", "Prime95", "pTAT+Fur+Charging"]

# split_modeに応じて、デフォルト値を再初期化
if not st.session_state.segment_defaults_set:
    reset_segment_defaults()

seg_cols = st.columns(5)
selected_segments = []
for i in range(5):
    with seg_cols[i]:
        selected = st.selectbox(
            segment_labels[i],
            options=select_options,
            index=select_options.index(st.session_state.segment_values[i]),
            key=f"segment_select_{i}"
        )
        selected_segments.append(selected)

output_name = ("Merged")

if logger_file and ptat_file:
    # 横に中央配置
    col_left, col_center, col_right = st.columns([2, 3, 2])
    with col_center:
        # CSSで横長スタイルに
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

        if st.button("🚀 Run Analysis", key="run-analysis"):
            with tempfile.TemporaryDirectory() as tmpdir:
                logger_path = os.path.join(tmpdir, logger_file.name)
                ptat_path = os.path.join(tmpdir, ptat_file.name)
                output_excel = os.path.join(tmpdir, output_name.strip() + ".xlsx")

                with open(logger_path, "wb") as f:
                    f.write(logger_file.read())
                with open(ptat_path, "wb") as f:
                    f.write(ptat_file.read())

                with st.spinner("Processing..."):
                    full_logger_ptat_pipeline = pipeline_4 if split_mode == "4 segments" else pipeline_5

                    merged_df, _ = full_logger_ptat_pipeline(
                        logger_input_raw=logger_path,
                        ptat_input_raw=ptat_path,
                        merged_excel_output=output_excel
                    )

                if merged_df is not None:
                    with open(output_excel, "rb") as f:
                        st.session_state["excel_bytes"] = f.read()
                        st.session_state["excel_filename"] = output_name.strip() + ".xlsx"


if "excel_bytes" in st.session_state:
    st.header("📈 Visualization from Analysis Result")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_excel:
        tmp_excel.write(st.session_state["excel_bytes"])
        tmp_excel_path = tmp_excel.name

    try:
        df = pd.read_excel(tmp_excel_path, sheet_name="Experiment Labeled")
        numeric_cols = df.select_dtypes(include='number').columns.tolist()

        tabs = st.tabs(["Skintemp-Sensortemp", "Time-Power"])

        with tabs[0]:
            if len(numeric_cols) >= 2:
                row1_col1, row1_col2 = st.columns(2)

                with row1_col1:
                    col_x = st.selectbox("Select X-axis column", numeric_cols, index=0, key="x1")

                with row1_col2:
                    y_options = [col for col in numeric_cols if col != col_x]
                    current_y = st.session_state.get("y1", y_options[0])
                    if current_y in y_options:
                        y_index = y_options.index(current_y)
                    else:
                        y_index = 0
                    col_y = st.selectbox("Select Y-axis column", y_options, index=y_index, key="y1")

                row2_col1, row2_col2 = st.columns(2)
                with row2_col1:
                    bestp_val = st.number_input("BestP skin spec (deg)", value=0.0)
                with row2_col2:
                    bal_val = st.number_input("Bal skin spec (deg)", value=0.0)

                row3_col1, row3_col2, row3_col3 = st.columns([3,1,4])
                with row3_col1:
                    point_opacity = st.slider("Marker opacity", 0.1, 1.0, 0.7, 0.1, key="opacity1")
                # with row3_col2:
                #     show_y_equals_x = st.checkbox("Show y = x line", value=True)
                with row3_col2:
                    show_grid = st.checkbox("Show grid", value=True)
                with row3_col3:
                    if "Experiment" in df.columns:
                        # セグメント数と選択ラベルを取得
                        num_segments = 4 if split_mode == "4 segments" else 5
                        effective_segments = selected_segments[:num_segments]
                        # Experiment列のユニーク値取得（順序保持）
                        exp_options = df["Experiment"].dropna().unique().tolist()[:num_segments]
                        # ExperimentラベルとUIでの選択ラベルを対応づけ
                        exp_display_map = dict(zip(exp_options, effective_segments))  # 例: {"Exp1": "pTAT+Fur", ...}
                        # UIに表示するラベルリスト（選択肢）
                        exp_display_labels = [exp_display_map[exp] for exp in exp_options]
                        # ユーザーに表示されるselectは変換名（選択ラベル）、選択された値を元のExperimentに戻す
                        selected_display_labels = st.multiselect("Filter by Experiment", exp_display_labels, default=exp_display_labels)
                        selected_exps = [exp for exp, label in exp_display_map.items() if label in selected_display_labels]
                        # dfをフィルター
                        df_filtered = df[df["Experiment"].isin(selected_exps)]
                    else:
                        df_filtered = df.copy()

                # 横幅3分割で中央カラムにボタン配置
                left, center, right = st.columns([2, 3, 2])
                with center:
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                        # 既存シートのコピー
                        df_all = pd.read_excel(BytesIO(st.session_state["excel_bytes"]), sheet_name=None)
                        for sheet_name, sheet_df in df_all.items():
                            sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

                        # UIで選ばれたセグメントラベルを列名に使って横並びに出力
                        segment_data = {}
                        if "Experiment" in df_filtered.columns:
                            unique_exps = df_filtered["Experiment"].dropna().unique().tolist()
                            num_segments = 4 if split_mode == "4 segments" else 5
                            effective_segments = selected_segments[:num_segments]

                            for i, exp in enumerate(unique_exps):
                                if i >= len(effective_segments):
                                    continue
                                exp_label = effective_segments[i]
                                exp_df = df_filtered[df_filtered["Experiment"] == exp]
                                segment_data[f"{exp_label}_X"] = exp_df[col_x].reset_index(drop=True)
                                segment_data[f"{exp_label}_Y"] = exp_df[col_y].reset_index(drop=True)

                        segment_df = pd.DataFrame(segment_data)
                        segment_df.to_excel(writer, sheet_name="Selected XY Data", index=False)
                        df_all = pd.read_excel(BytesIO(st.session_state["excel_bytes"]), sheet_name=None)
                        for sheet_name, sheet_df in df_all.items():
                            if sheet_name != "Selected XY Data":  # 重複出力防止
                                sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)
                        # --- 📈 グラフを追加 ---
                        workbook  = writer.book
                        worksheet = writer.sheets["Selected XY Data"]
                        worksheet.activate()
                        chart = workbook.add_chart({'type': 'scatter', 'subtype': 'marker'})

                        max_row = len(segment_df)
                        num_cols = segment_df.shape[1]

                        for col in range(0, num_cols, 2):
                            if col + 1 >= num_cols:
                                break
                            x_range = f"='Selected XY Data'!${chr(65+col)}$2:${chr(65+col)}${max_row+1}"
                            y_range = f"='Selected XY Data'!${chr(65+col+1)}$2:${chr(65+col+1)}${max_row+1}"
                            series_name = segment_df.columns[col+1]
                            chart.add_series({
                                'name':       series_name,
                                'categories': x_range,
                                'values':     y_range,
                                'marker':     {'type': 'circle', 'size': 5},
                                'line':       {'none': True}  # ← 🟢 線なし＝マーカーのみ
                            })

                        chart.set_title({'name': 'Segment XY Correlation'})
                        chart.set_x_axis({'name': col_x})
                        chart.set_y_axis({'name': col_y})
                        chart.set_size({'width': 720, 'height': 480})
                        worksheet.insert_chart("J2", chart)
                    st.download_button(
                        label="📥 To XLSX Output (with XY)",
                        data=output.getvalue(),
                        file_name="sensor_correlation_output.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="centered-download"
                    )

                color_map = {
                    "TAT+Fur": "blue",
                    "TAT": "green",
                    "Fur": "orange",
                    "Prime95": "red",
                    "Charging": "#ee82ee"
                }

                num_segments = 4 if split_mode == "4 segments" else 5
                effective_segments = selected_segments[:num_segments]
                fig = go.Figure()

                if "Experiment" in df.columns:
                    unique_exps = df_filtered["Experiment"].dropna().unique().tolist()

                    for i, exp in enumerate(unique_exps):
                        if i >= len(effective_segments):
                            break  # セグメント数を超えたら無視
                        exp_df = df_filtered[df_filtered["Experiment"] == exp]
                        fig.add_trace(go.Scatter(
                            x=exp_df[col_x],
                            y=exp_df[col_y],
                            mode="markers",
                            name=effective_segments[i],  # 凡例を選択に同期
                            marker=dict(color=color_map.get(exp, "gray")),
                            opacity=point_opacity
                        ))

                fig.add_vline(
                    x=bal_val,
                    line=dict(color="green", dash="dot"),
                    annotation_text="Bal spec",
                    annotation_position="top left"
                )

                fig.add_vline(
                    x=bestp_val,
                    line=dict(color="red", dash="dot"),
                    annotation_text="BestP spec",
                    annotation_position="top right"
                )

                # if show_y_equals_x:
                fig.add_trace(go.Scatter(
                    x=[25, 60],
                    y=[25, 60],
                    mode="lines",
                    line=dict(color="cyan"),
                    name="y = x"
                ))

                fig.update_layout(
                    xaxis=dict(title=col_x, range=[25, 60], title_font=dict(size=18), tickfont=dict(size=14)),
                    yaxis=dict(title=col_y, range=[25, 60], title_font=dict(size=18), tickfont=dict(size=14)),
                    legend=dict(title="Experiment", font=dict(size=14)),
                    width=800,
                    height=870,
                    template="simple_white",
                    title=""
                )
                fig.update_xaxes(showgrid=show_grid)
                fig.update_yaxes(showgrid=show_grid)
                st.plotly_chart(fig, use_container_width=True)
                # try:
                #     png_bytes = pio.to_image(fig, format="png")
                #     st.download_button("📥 Download Chart as PNG", data=png_bytes, file_name="chart.png", mime="image/png")
                # except Exception:
                #     st.warning("⚠️ Install 'kaleido' for PNG export.")

                with st.expander("📋 View Raw Data", expanded=True):
                    cols_to_show = [col_x, col_y]
                    if "Experiment" in df.columns:
                        cols_to_show.append("Experiment")
                    st.dataframe(df[cols_to_show])
            else:
                st.warning("At least two numeric columns are required.")

        with tabs[1]:
            power_cols = [col for col in df.columns if any(key in col for key in ["IA", "GT", "Package"])]
            time_col = next((col for col in df.columns if "Time" in col), None)

            if power_cols and time_col:
                fig2 = go.Figure()
                for col in power_cols:
                    fig2.add_trace(go.Scatter(x=df[time_col], y=df[col], mode="lines", name=col))
                fig2.update_layout(
                    xaxis=dict(title=time_col, title_font=dict(size=18), tickfont=dict(size=14)),
                    yaxis=dict(title="Power (W)", title_font=dict(size=18), tickfont=dict(size=14)),
                    legend=dict(font=dict(size=14)),
                    width=900,
                    height=600,
                    template="simple_white",
                    title=""
                )
                st.plotly_chart(fig2, use_container_width=True)

    except Exception as e:
        st.error(f"Error reading Excel file: {e}")
