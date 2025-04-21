import streamlit as st
import pandas as pd
from io import BytesIO
import plotly.express as px
import xlsxwriter
from streamlit_sortables import sort_items
import re
import os

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

# ✅ XLSX Column Reordering with KeyError-safe logic
st.subheader("📤 XLSX Column Reordering")
reorder_cols = [st.selectbox(f"→ Column {chr(65+i)}", all_columns, key=f"reorder_{i}") for i in range(5)]

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

# ✅ Merge All Logs by Time (Flexible matching for time column)
st.subheader("📤 Merge All Logs by Time")
time_column = st.session_state.x_axis
merged_df = pd.DataFrame()

for label, dfs in uploaded_data.items():
    for i, df in enumerate(dfs):
        df_copy = df.copy()
        # ⛳ 유연한 time 컬럼 매칭 처리
        time_candidates = [c for c in df_copy.columns if time_column.lower() in c.lower() or "time" in c.lower()]
        if time_candidates:
            time_col = time_candidates[0]  # 첫 번째 매칭 컬럼 사용
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
