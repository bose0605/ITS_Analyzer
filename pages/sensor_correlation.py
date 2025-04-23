import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import tempfile
import plotly.io as pio

from pipeline_module_to_4 import full_logger_ptat_pipeline as pipeline_4
from pipeline_module_to_5 import full_logger_ptat_pipeline as pipeline_5

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
# ==== タブ表示・タイトル表示 ====
st.markdown("""
<hr style="
  height: 8px;
  border: none;
  border-radius: 3px;
  background: linear-gradient(to right, #60a760, #9c8eb0, #d69e6a, #dad577, #335f8c, #b10c67, #039CB2);
  margin-top: 44px;
  margin-bottom: 40px;
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

top_col_left, top_col_right = st.columns([8, 1])
with top_col_left:
    st.title("📊 Sensor correlation analyzer")
with top_col_right:
    st.page_link("main.py", label="🏠 To Main")

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
            help="Download Logger-PTAT Excel Template",
            key="template-download"
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

if logger_file or ptat_file:
    if st.button("🚀 Run Analysis"):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger_path = None
            ptat_path = None

            output_excel = os.path.join(tmpdir, output_name.strip() + ".xlsx")
            

            if logger_file:
                logger_path = os.path.join(tmpdir, logger_file.name)
                with open(logger_path, "wb") as f:
                    f.write(logger_file.read())

            if ptat_file:
                ptat_path = os.path.join(tmpdir, ptat_file.name)
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

        tabs = st.tabs(["Skintemp-Sensortemp", "Time-Power"])

        with tabs[0]:
            if len(numeric_cols) >= 2:
                row1_col1, row1_col2 = st.columns(2)
                with row1_col1:
                    col_x = st.selectbox("Select X-axis column", numeric_cols, index=0, key="x1")
                with row1_col2:
                    col_y = st.selectbox("Select Y-axis column", [col for col in numeric_cols if col != col_x], index=0, key="y1")

                row2_col1, row2_col2 = st.columns(2)
                with row2_col1:
                    bestp_val = st.number_input("BestP skin spec (deg)", value=0.0)
                with row2_col2:
                    bal_val = st.number_input("Bal skin spec (deg)", value=0.0)

                row3_col1, row3_col2, row3_col3 = st.columns(3)
                with row3_col1:
                    point_opacity = st.slider("🔆 Marker opacity", 0.1, 1.0, 0.7, 0.1, key="opacity1")
                with row3_col2:
                    show_y_equals_x = st.checkbox("⚫ Show y = x line", value=True)
                with row3_col3:
                    show_grid = st.checkbox("🗺 Show grid", value=True)

                if "Experiment" in df.columns:
                    exp_options = df["Experiment"].dropna().unique().tolist()
                    selected_exps = st.multiselect("Filter by Experiment", exp_options, default=exp_options)
                    df_filtered = df[df["Experiment"].isin(selected_exps)]
                else:
                    df_filtered = df.copy()

                color_map = {
                    "TAT+Fur": "blue",
                    "TAT": "green",
                    "Fur": "orange",
                    "Prime95": "red",
                    "Charging": "purple"
                }

                fig = go.Figure()

                if "Experiment" in df.columns:
                    for exp in df_filtered["Experiment"].unique():
                        exp_df = df_filtered[df_filtered["Experiment"] == exp]
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
                        x=df_filtered[col_x],
                        y=df_filtered[col_y],
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
                        x=[25, 60],
                        y=[25, 60],
                        mode="lines",
                        line=dict(color="black"),
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
