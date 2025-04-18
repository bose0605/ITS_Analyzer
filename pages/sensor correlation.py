import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import tempfile
import plotly.io as pio

# 모듈 둘 다 import (이름 충돌 방지)
from pipeline_module_to_4 import full_logger_ptat_pipeline as pipeline_4
from pipeline_module_to_5 import full_logger_ptat_pipeline as pipeline_5

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

# 타이틀 + 템플릿 다운로드 버튼을 한 줄에 배치
col_title, col_button = st.columns([5, 3])  # 버튼이 길기 때문에 비율 조정
with col_title:
    st.title("📊 Logger-PTAT Analysis Pipeline")
with col_button:
    try:
        template_path = os.path.join(os.path.dirname(__file__), "../Result_template.xlsm")
    except NameError:
        template_path = os.path.join(os.getcwd(), "Result_template.xlsm")

    if os.path.exists(template_path):
        with open(template_path, "rb") as f:
            st.download_button(
                label="📥 Download Excel Template (for Logger-PTAT)",
                data=f.read(),
                file_name="Result_template.xlsm",
                help="Download Logger-PTAT Excel Template"
            )
    else:
        st.warning("❗ Template not found.")

st.markdown("### Upload files for analysis")
col1, col2 = st.columns(2)
with col1:
    logger_file = st.file_uploader("📝 Logger File (.xls/.xlsx)", type=["xls", "xlsx"])
with col2:
    ptat_file = st.file_uploader("🌡 PTAT File (.csv)", type=["csv"])

st.markdown("### ⚙️ Select Experiment Split Mode")
split_mode = st.radio("Choose number of experiment segments", ["4 segments", "5 segments"], index=0)

output_name = st.text_input("💾 Output filename (without extension)", value="Merged_result_final")

if logger_file and ptat_file:
    if st.button("🚀 Run Analysis"):
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
                st.success("✅ Analysis Complete!")

                with open(output_excel, "rb") as f:
                    st.session_state["excel_bytes"] = f.read()
                    st.session_state["excel_filename"] = output_name.strip() + ".xlsx"

if "excel_bytes" in st.session_state:
    st.download_button(
        label="📥 Download Excel File",
        data=st.session_state["excel_bytes"],
        file_name=st.session_state["excel_filename"],
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if "excel_bytes" in st.session_state:
    st.header("📈 Visualization from Analysis Result")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_excel:
        tmp_excel.write(st.session_state["excel_bytes"])
        tmp_excel_path = tmp_excel.name

    try:
        df = pd.read_excel(tmp_excel_path, sheet_name="Experiment Labeled")
        numeric_cols = df.select_dtypes(include='number').columns.tolist()

        if len(numeric_cols) >= 2:
            col_x = st.selectbox("Select X-axis column", numeric_cols, index=0)
            col_y = st.selectbox("Select Y-axis column", [col for col in numeric_cols if col != col_x], index=0)

            point_opacity = st.slider("🔆 Marker opacity", 0.1, 1.0, 0.7, 0.1)

            bestp_val = st.number_input("BestP skin spec (deg)", value=0.0)
            bal_val = st.number_input("Bal skin spec (deg)", value=0.0)
            show_y_equals_x = st.checkbox("⚫ Show y = x line", value=True)
            show_grid = st.checkbox("🗺 Show grid", value=True)

            if "Experiment" in df.columns:
                exp_options = df["Experiment"].dropna().unique().tolist()
                selected_exps = st.multiselect("Filter by Experiment", exp_options, default=exp_options)
                df = df[df["Experiment"].isin(selected_exps)]
            else:
                selected_exps = []

            color_map = {
                "TAT+Fur": "blue",
                "TAT": "green",
                "Fur": "orange",
                "Prime95": "red",
                "Charging": "purple"
            }

            fig = go.Figure()

            if "Experiment" in df.columns:
                for exp in selected_exps:
                    exp_df = df[df["Experiment"] == exp]
                    fig.add_trace(go.Scatter(
                        x=exp_df[col_x],
                        y=exp_df[col_y],
                        mode="markers",
                        name=exp,
                        marker=dict(color=color_map.get(exp, "gray")),
                        opacity=point_opacity
                    ))
            else:
                fig.add_trace(go.Scatter(
                    x=df[col_x],
                    y=df[col_y],
                    mode="markers",
                    name=f"{col_y} vs {col_x}",
                    marker=dict(color="crimson"),
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

            if show_y_equals_x:
                fig.add_trace(go.Scatter(
                    x=[25, 55],
                    y=[25, 55],
                    mode="lines",
                    line=dict(color="black"),
                    name="y = x"
                ))

            fig.update_layout(
                xaxis=dict(title=col_x, range=[25, 55]),
                yaxis=dict(title=col_y, range=[25, 55]),
                title=f"{col_y} vs {col_x}",
                legend=dict(title="Experiment"),
                width=800,
                height=800,
                template="simple_white"
            )

            fig.update_xaxes(showgrid=show_grid)
            fig.update_yaxes(showgrid=show_grid)

            st.plotly_chart(fig, use_container_width=True)

            try:
                png_bytes = pio.to_image(fig, format="png")
                st.download_button("📥 Download Chart as PNG", data=png_bytes, file_name="chart.png", mime="image/png")
            except Exception:
                st.warning("⚠️ Install 'kaleido' for PNG export.")

            with st.expander("📋 View Raw Data"):
                cols_to_show = [col_x, col_y]
                if "Experiment" in df.columns:
                    cols_to_show.append("Experiment")
                st.dataframe(df[cols_to_show])
        else:
            st.warning("At least two numeric columns are required.")
    except Exception as e:
        st.error(f"Error reading Excel file: {e}")
