import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import glob
from datetime import datetime
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import matplotlib.ticker as ticker
from io import BytesIO
import xlsxwriter
import matplotlib.colors as mcolors
import re  
import textwrap
from io import StringIO
import base64
st.set_page_config(layout="wide")

top_col_right = st.columns([8, 1])
with top_col_right[1]:
    st.page_link("main.py", label="🏠 To Main")

# def set_background(image_path: str):
#     with open(image_path, "rb") as image_file:
#         encoded = base64.b64encode(image_file.read()).decode()
#     background_css = f"""
#     <style>
#     [data-testid="stAppViewContainer"] {{
#         background-image: url("data:image/jpg;base64,{encoded}");
#         background-size: cover;
#         background-position: center;
#         background-repeat: no-repeat;
#         background-attachment: fixed;
#     }}
#     </style>
#     """
#     st.markdown(background_css, unsafe_allow_html=True)

# ✅ 画像ファイルのパスを指定（アプリと同じディレクトリにある想定）

# set_background("1938176.jpg")
def get_default_power_cols():
    preferred = [
        "TCPU_D0_Current Power(W)",
        "TCPU_PL1 Limit(W)",
        "TCPU_PL1 Min Power Limit(W)",
        "TCPU_PL1 Max Power Limit(W)",
        "TCPU_PL2 Limit(W)"
    ]
    # 列名の正規化：全体でstrip（空白削除）
    cleaned_cols = {col.strip(): col for col in df.columns}
    available = []
    seen = set()
    for name in preferred:
        if name in cleaned_cols and cleaned_cols[name] not in seen:
            available.append(cleaned_cols[name])
            seen.add(cleaned_cols[name])

    # 補完（重複防止付き）
    if len(available) < 5:
        extra = [
            col for col in df.columns
            if "(W)" in col and "power" in col.lower() and col not in seen
        ]
        for col in extra:
            if len(available) >= 5:
                break
            available.append(col)
            seen.add(col)

    return available

def sanitize_key(text: str) -> str:
    return re.sub(r'\W+', '_', text)

def get_color_hex(cmap, index, total):
    rgba = cmap(index / max(total - 1, 1))
    return mcolors.to_hex(rgba, keep_alpha=False)


plt.rcParams["font.family"] = "Times New Roman"
if "colormap_name" not in st.session_state:
    st.session_state["colormap_name"] = "Accent"

# 🌈 虹色ライン
st.markdown("""
<hr style="
  height: 8px;
  border: none;
  border-radius: 3px;
  background: linear-gradient(to right, #ff1493, #0000cd, #ffdab9, #00fa9a, #ff8c00,#cd5c5c);
  margin-top: 10px;
  margin-bottom: 4px;
">
""", unsafe_allow_html=True)

# 🎨 サイドバー用CSS
st.markdown("""
<style>
details > summary {
  font-size: 20px !important;
  font-weight: bold;
}
section[data-testid="stSidebar"] {
  font-family: Arial;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4,
section[data-testid="stSidebar"] .stHeading {
  color: goldenrod;
  font-size: 1.2rem;
}
</style>
""", unsafe_allow_html=True)

st.title("\U0001F4CADTT Viewer")

# ===== ファイルアップロード =====
with st.sidebar.expander("1️⃣ Choose your csv file", expanded=True):
    uploaded_file = st.file_uploader("Upload csv file", type="csv", accept_multiple_files=False)

    if not uploaded_file:
        st.warning("Upload your csv file")
        st.stop()

    file = uploaded_file.name
    x_axis_title = st.text_input("X-axis title", value="Time", key="x_axis_title_input")
    y_axis_title = st.text_input("Y-axis title", value="Power (W)", key="y_axis_title_input")
    previous_file = st.session_state.get("last_selected_file", None)

@st.cache_data
def load_csv(file_obj):
    try:
        # 最初にUTF-8で読み込む（成功すれば速い）
        return pd.read_csv(file_obj)
    except UnicodeDecodeError:
        # 失敗したらShift-JISで再読み込み（リセット必要）
        file_obj.seek(0)
        return pd.read_csv(file_obj, encoding="shift_jis")

# ===== mW列の変換処理 =====
df = load_csv(uploaded_file)
for col in df.columns:
    if "(mW)" in col and df[col].dtype != "O":
        new_col = col.replace("(mW)", "(W)")
        df[new_col] = df[col] / 1000

# ===== Time列の取得 =====
time_col_candidates = [col for col in df.columns if "time" in col.lower()]
if not time_col_candidates:
    st.error("Not found Time column.")
    st.stop()
time_col = time_col_candidates[0]

try:
    df[time_col] = pd.to_datetime(df[time_col])
    time_vals = df[time_col].dt.strftime("%H:%M:%S")
except:
    time_vals = df[time_col]

# CPU温度の列を抽出（DTS形式に限定せず、TempやCPU+温度のような名前も対象に）
temp_cols = [
    col for col in df.columns
    if "TCPU_D0_Temperature(C)" in col or re.match(r"SEN\d+_D0_Temperature\(C\)", col)
]

# ===== デフォルト縦軸列取得関数 =====

def reset_selected_y_cols():
    st.session_state.selected_y_cols = get_default_power_cols()

def reset_secondary_y_cols():
    st.session_state.secondary_y_cols = []

if file != previous_file:
    reset_selected_y_cols()
    reset_secondary_y_cols()
    st.session_state.last_selected_file = file
elif "selected_y_cols" not in st.session_state:
    reset_selected_y_cols()
# ===== 第一縦軸列選択（ExpanderでまとめてUI整理） =====
df_unique_columns = pd.Index(dict.fromkeys(df.columns))
with st.sidebar.expander("2️⃣ Setting for 1st Y-axis column", expanded=True):
    search_query = st.text_input("Searching (Y-axis)", value="Power", key="primary_search_input")
    y_axis_candidates = [col for col in df_unique_columns if search_query.lower() in col.lower() and col != time_col]

    if "selected_y_cols" not in st.session_state:
        st.session_state.selected_y_cols = get_default_power_cols()
    if "primary_add_selectbox" not in st.session_state:
        st.session_state["primary_add_selectbox"] = ""

    selected_to_add = st.selectbox(
        "Attend column",
        options=[""] + [col for col in y_axis_candidates if col not in st.session_state.selected_y_cols],
        index=0,
        key="primary_add_selectbox"
    )


    # セレクトボックスで新規選択されたら追加し rerun（session_stateは触らない！）
    if selected_to_add and selected_to_add not in st.session_state.selected_y_cols:
        st.session_state.selected_y_cols.append(selected_to_add)
        st.rerun() 


    st.markdown("### 1st Y-axis -on viewing-")
    current_selected = st.session_state.selected_y_cols.copy()
    updated_selection = st.multiselect(
        "Erase viewing by clicking",
        options=current_selected,
        default=current_selected,
        key="primary_remove_multiselect"
    )
    if set(updated_selection) != set(current_selected):
        st.session_state.selected_y_cols = updated_selection
        st.rerun()


# ===== グラフ書式設定 + フォント + 軸範囲 + 凡例 + 第二縦軸トグル まとめてexpander =====
with st.sidebar.expander("3️⃣ Chart setting", expanded=True):
    colormap_list = sorted(plt.colormaps())
    default_cmap = "Accent"
    st.session_state["colormap_name"] = st.selectbox(
        "Choose colormap",
        colormap_list,
        index=colormap_list.index(default_cmap) if default_cmap in colormap_list else 0,
        key="colormap_select"
    )
    width = st.slider("Chart width\n(For saving chart)", 8, 24, 14, key="plot_width")
    height = st.slider("Chart height\n(For saving chart)", 4, 16, 7, key="plot_height")
    ytick_step = st.number_input("Y-axis ticks duration", min_value=1, value=5, key="ytick_step")
    show_cursor = st.checkbox("View vertical line and labelname\n(For saving chart)", value=False, key="show_cursor")
    cursor_index = st.number_input("View oen vertical line\n(For saving chart)", min_value=0, max_value=len(df)-1, value=0, key="cursor_index")
    show_xgrid = st.checkbox("View start and end idx grid\n(For saving chart)", value=True, key="show_xgrid")

    st.markdown("### 🖋 Font size setting")
    label_font = st.slider("Y-axis label size\n(For saving chart)", 8, 24, 17, key="label_font")
    tick_font = st.slider("Both axis size\n(For saving chart)", 6, 20, 13, key="tick_font")
    title_font = st.slider("Chart title size\n(For saving chart)", 10, 30, 17, key="title_font")

    st.markdown("### 📐1st Y-axis title range")
    numeric_cols = df.select_dtypes(include='number').columns
    y_min = 0
    try:
        y_max_data = int(df[st.session_state.get("selected_y_cols", [])].max().max() * 1.1)
    except:
        y_max_data = 70
    y_max = st.number_input("1st Y-axis upper limit", min_value=1, value=y_max_data if y_max_data < 10000 else 100, key="y_max")

    st.markdown("### 📌 Legend setting (For saving chart)")
    show_legend = st.toggle("View legend\n(For saving chart)", value=True, key="show_legend")
    legend_font = None
    legend_alpha = None
    if show_legend:
        legend_font = st.slider("legend font size\n(For saving chart)", 6, 20, 10, key="legend_font")
        legend_alpha = st.slider("Legend opacity (0=transparent, 1=opaque)\n(For saving chart)", 0.0, 1.0, 0.5, step=0.05, key="legend_alpha")

# ===== 第二縦軸設定（expander内にトグルも含めて表示） =====
with st.sidebar.expander("4️⃣ 2nd Y-axis setting", expanded=True):
    use_secondary_axis = st.toggle("Utilize 2nd Y-axis", value=False, key="use_secondary_axis")

    if use_secondary_axis:
        secondary_y_axis_title = st.text_input("2nd Y-axis title", value="Temperature (deg)", key="y2_title")
        secondary_tick_step = st.number_input("2nd Y-axis ticks", min_value=1, value=5, key="secondary_tick_step")

        y2_max_data = int(df.select_dtypes(include='number').max().max() * 1.1)
        y2_max = st.number_input("2nd Y-axis upper limit\n(For saving chart)", min_value=1, value=y2_max_data if y2_max_data < 10000 else 100, key="y2_max")

        st.markdown("**Search and attend 2nd Y-axis column**")
        y2_search = st.text_input("Searching（2nd Y-axis）", value="Temp", key="y2_search")
        y2_candidates = [col for col in df.columns if y2_search.lower() in col.lower() and col != time_col]

        if "secondary_y_cols" not in st.session_state:
            st.session_state.secondary_y_cols = []

        y2_add = st.selectbox(
            "Attend column（2nd Y-axis)",
            options=[""] + [col for col in y2_candidates if col not in st.session_state.secondary_y_cols],
            index=0
        )

        # 候補追加があった場合にだけ append＋rerun し、直後に return しない
        if y2_add and y2_add not in st.session_state.secondary_y_cols:
            st.session_state.secondary_y_cols.append(y2_add)
            st.rerun()  # ← rerun後にマークダウン描画されるようになる！

        # ここは常に描画される（マークダウン＋チェックボックス）
        st.markdown("### 2nd Y-axis -on viewing-")
        y2_remove_cols = st.multiselect(
            "Erase viewing by clicking",
            options=st.session_state.secondary_y_cols,
            default=st.session_state.secondary_y_cols,
            key="y2_remove"
        )
        st.session_state.secondary_y_cols = y2_remove_cols


selected_y_cols = st.session_state.selected_y_cols
selected_y_cols = list(dict.fromkeys(st.session_state.selected_y_cols))  # 重複除去
secondary_y_cols = st.session_state.get("secondary_y_cols", []) if use_secondary_axis else []

# ===== Plotlyグラフ描画 =====
if "style_map" not in st.session_state:
    st.session_state["style_map"] = {}

colormap_name = st.session_state["colormap_name"]
colormap = cm.get_cmap(colormap_name)
all_plot_cols = selected_y_cols + secondary_y_cols
color_map_ui = {}
color_map_excel = {}
plot_cols = selected_y_cols + secondary_y_cols
for idx, col in enumerate(plot_cols):
    color = get_color_hex(colormap, idx, len(plot_cols))
    color_map_ui[col] = color
    color_map_excel[col] = color
for col in selected_y_cols + secondary_y_cols:
    st.session_state["style_map"].setdefault(col, "直線")

colormap_name = st.session_state["colormap_name"]
colormap = cm.get_cmap(colormap_name)

style_options = {
    "-": {"linestyle": "-", "marker": ""},
    "--": {"linestyle": "--", "marker": ""},
    ".": {"linestyle": "", "marker": "o"},
    "-＋.": {"linestyle": "-", "marker": "o"},
    "--＋.": {"linestyle": "--", "marker": "o"},
    ".": {"linestyle": ":", "marker": ""}
}

# ===== 平均値表示のUI（Expanderでまとめて制御） =====
if "show_avg_lines" not in st.session_state:
    st.session_state.show_avg_lines = False

#===== グラフ化のための変換コード
def export_xlsx(df, selected_y_cols, time_vals, fig, temp_cols, power_cols, epp_col=None, os_power_col=None):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Data")
    col_offset = 0

    header_format = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2'})
    gray_fill = workbook.add_format({'bg_color': '#D9D9D9'})

    # --- MainPlotのデータ書き込み ---
    worksheet.write(0, 0, "Time", header_format)
    for idx, col in enumerate(selected_y_cols):
        worksheet.write(0, idx + 1, col, header_format)

    for row_idx, (time_val, *values) in enumerate(df[[time_col] + selected_y_cols].itertuples(index=False), start=1):
        worksheet.write(row_idx, 0, str(time_val))
        for col_idx, value in enumerate(values):
            worksheet.write(row_idx, col_idx + 1, value)

    # --- グレー塗りつぶし2列 ---
    start_col = len(selected_y_cols) + 1
    worksheet.set_column(start_col, start_col+1, 4, gray_fill)

    # --- CPUtempデータ書き込み ---
    temp_start_col = start_col + 2
    for idx, col in enumerate(temp_cols):
        worksheet.write(0, temp_start_col + idx, col, header_format)

    for row_idx, (time_val, *values) in enumerate(df[[time_col] + temp_cols].itertuples(index=False), start=1):
        for col_idx, value in enumerate(values[1:]):  # skip time_val
            worksheet.write(row_idx, temp_start_col + col_idx, value)

    # --- MainPlotグラフ書き込み ---
    chart = workbook.add_chart({'type': 'line'})
    for idx, col in enumerate(selected_y_cols):
        chart.add_series({
            'name': ['Data', 0, idx + 1],
            'categories': ['Data', 1, 0, len(df), 0],
            'values': ['Data', 1, idx + 1, len(df), idx + 1],
            'line': {'color': get_color_hex(cm.get_cmap(colormap_name), idx, len(selected_y_cols))}
        })
    chart.set_title({'name': 'Main Plot'})
    chart.set_x_axis({'name': 'Time'})
    chart.set_y_axis({'name': 'Value'})
    worksheet.insert_chart(9, col_offset, chart, {"x_scale": 1.6, "y_scale": 1.9})

    # --- CPUtempグラフ書き込み ---
    chart2 = workbook.add_chart({'type': 'line'})
    for idx, col in enumerate(temp_cols):
        chart2.add_series({
            'name': ['Data', 0, temp_start_col + idx],
            'categories': ['Data', 1, 0, len(df), 0],
            'values': ['Data', 1, temp_start_col + idx, len(df), temp_start_col + idx],
            'line': {'color': get_color_hex(cm.get_cmap(colormap_name), idx, len(temp_cols))}
        })
    chart2.set_title({'name': 'CPU & Sensors Temperature'})
    chart2.set_x_axis({'name': 'Time'})
    chart2.set_y_axis({'name': 'Temperature (°C)'})
    worksheet.insert_chart(9, temp_start_col, chart2, {"x_scale": 1.6, "y_scale": 1.9})

    # --- グレー塗りつぶし2列 ---
    power_start_col = temp_start_col + len(temp_cols) + 2
    worksheet.set_column(power_start_col - 2, power_start_col - 1, 4, gray_fill)

    # --- Powerlimitデータ書き込み ---
    for idx, col in enumerate(power_cols):
        worksheet.write(0, power_start_col + idx, col, header_format)

    for row_idx, row in enumerate(df[[time_col] + power_cols].itertuples(index=False), start=1):
        for col_idx, val in enumerate(row[1:]):
            worksheet.write(row_idx, power_start_col + col_idx, val)

    # --- Powerlimitグラフ描き込み ---
    chart3 = workbook.add_chart({'type': 'line'})
    for idx, col in enumerate(power_cols):
        chart3.add_series({
            'name': ['Data', 0, power_start_col + idx],
            'categories': ['Data', 1, 0, len(df), 0],
            'values': ['Data', 1, power_start_col + idx, len(df), power_start_col + idx],
            'line': {'color': get_color_hex(cm.get_cmap(colormap_name), idx, len(power_cols))}
        })
    chart3.set_title({'name': 'Power Limit Chart'})
    chart3.set_x_axis({'name': 'Time'})
    chart3.set_y_axis({'name': 'Power (W)'})
    worksheet.insert_chart(9, power_start_col, chart3, {"x_scale": 1.6, "y_scale": 1.9})

        # --- グレー塗りつぶし2列（Powerlimitの右） ---
    epp_start_col = power_start_col + len(power_cols) + 2
    worksheet.set_column(epp_start_col - 2, epp_start_col - 1, 4, gray_fill)

    # --- EPP & Mode データ書き込み ---
    epp_cols = []
    if epp_col:
        epp_cols.append(epp_col)
    if os_power_col:
        epp_cols.append(os_power_col)

    for idx, col in enumerate(epp_cols):
        worksheet.write(0, epp_start_col + idx, col, header_format)

    for row_idx, row in enumerate(df[[time_col] + epp_cols].itertuples(index=False), start=1):
        for col_idx, val in enumerate(row[1:]):
            worksheet.write(row_idx, epp_start_col + col_idx, val)

    # --- グラフ描画（もし両方あれば） ---
    if epp_col and os_power_col:
        chart4 = workbook.add_chart({'type': 'line'})
        chart4.add_series({
            'name': ['Data', 0, epp_start_col],
            'categories': ['Data', 1, 0, len(df), 0],
            'values': ['Data', 1, epp_start_col, len(df), epp_start_col],
            'line': {'color': '#800080'}  # purple
        })
        chart4.add_series({
            'name': ['Data', 0, epp_start_col + 1],
            'categories': ['Data', 1, 0, len(df), 0],
            'values': ['Data', 1, epp_start_col + 1, len(df), epp_start_col + 1],
            'line': {'color': '#228B22'},  # green
            'marker': {'type': 'circle', 'size': 5}
        })
        chart4.set_title({'name': 'EPP & Power Mode'})
        chart4.set_x_axis({'name': 'Time'})
        chart4.set_y_axis({'name': 'EPP / Power Mode'})
        worksheet.insert_chart(9, epp_start_col, chart4, {"x_scale": 1.6, "y_scale": 1.9})

    workbook.close()
    output.seek(0)
    return output

fig = go.Figure()
total_lines = len(selected_y_cols) + len(secondary_y_cols)

for i, col in enumerate(selected_y_cols):
    style = style_options.get(st.session_state["style_map"].get(col, "直線"), {})
    fig.add_trace(go.Scatter(
        x=time_vals,
        y=df[col],
        name=col,
        line=dict(
            color=get_color_hex(colormap, i, total_lines),  # ← ここが統一の肝
            dash=style.get("dash")
        ),
        mode="lines+markers" if style.get("marker") else "lines",
        marker=dict(symbol=style.get("marker")) if style.get("marker") else None,
        yaxis="y1",
        showlegend=True
    ))

for j, col in enumerate(secondary_y_cols):
    style = style_options.get(st.session_state["style_map"].get(col, "点のみ"), {})
    fig.add_trace(go.Scatter(
        x=time_vals,
        y=df[col],
        name=col,
        mode="markers",
        marker=dict(
            color=get_color_hex(colormap, len(selected_y_cols) + j, total_lines),
            size=6,
            symbol="circle"
        ),
        yaxis="y2",
        legendgroup="group2",
        showlegend=True
    ))



st.markdown("""
<style>
div.stDownloadButton > button {
    background-color: crimson;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    font-size: 1rem;
    transition: background-color 0.3s;
}
div.stDownloadButton > button:hover {
    background-color: #105d96;
}
</style>
""", unsafe_allow_html=True)
# Powerlimit用の列（tabs[1]でも使っている同じ列セット）
power_cols = [
    "TCPU_D0_Current Power(W)", "TCPU_D1_Current Power(W)", "TCPU_D2_Current Power(W)",
    "TCPU_PL1 Limit(W)", "TCPU_PL1 Min Power Limit(W)", "TCPU_PL1 Max Power Limit(W)",
    "TCPU_PL2 Limit(W)"
]

power_cols = [col for col in power_cols if col in df.columns]  # 実在列だけ抽出
epp_col = next((col for col in df.columns if "epp" in col.lower()), None)
os_power_col = next((col for col in df.columns if "os power slider" in col.lower()), None)
towrite = export_xlsx(df, selected_y_cols, time_vals, fig, temp_cols, power_cols, epp_col, os_power_col)


xlsx_filename = file.replace(".csv", ".xlsx")
st.download_button(
    label="📥 To XLSX Output (with Charts)",
    data=towrite.getvalue(),
    file_name=xlsx_filename,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
# ==== 📏 平均値と垂線表示用 toggle（Expanderの代替） ====
show_avg = st.toggle("📏 Show the average value of the selected range", value=False)


if show_avg:
    midpoint = len(df) // 2
    col1, col2, col3, col4 = st.columns([1, 1, 2, 2])
    with col1:
        idx_start = st.number_input("Start index", min_value=0, max_value=len(df)-1, value=0, step=1, key="idx_start")
    with col2:
        idx_end = st.number_input("End index", min_value=0, max_value=len(df)-1, value=midpoint, step=1, key="idx_end")
    with col3:
        available_avg_cols = st.session_state.selected_y_cols or df.select_dtypes(include='number').columns.tolist()
        avg_target_col = st.selectbox("Target column", options=available_avg_cols, index=0, key="avg_col")

    if idx_start < idx_end and avg_target_col in df.columns:
        avg_val = df[avg_target_col].iloc[idx_start:idx_end+1].mean()
        with col4:
            st.success(f"📏 {avg_target_col} : {idx_start}〜{idx_end} Average: {avg_val:.2f}")

        x_start = time_vals.iloc[idx_start] if hasattr(time_vals, "iloc") else time_vals[idx_start]
        x_end = time_vals.iloc[idx_end] if hasattr(time_vals, "iloc") else time_vals[idx_end]

        # 垂線の追加（同期済み）
        fig.add_vline(x=x_start, line=dict(dash="dot", width=5, color="red"))
        fig.add_vline(x=x_end, line=dict(dash="dot", width=5, color="blue"))

layout_dict = dict(
    title=dict(
    text=f"{file}",
    font=dict(size=18),
    x=0.09,  # 👈 完全に左寄せ
    xanchor="left",  # 👈 左基準にする
    y=0.95,  # （オプション）縦位置調整（気になるなら）
    pad=dict(t=10, b=10)  # （オプション）上と下に少しだけ余白
    ),
    xaxis=dict(title=dict(text=x_axis_title, font=dict(size=18)),tickfont=dict(size=16)),
    yaxis=dict(
        title=dict(text=y_axis_title, font=dict(size=18)),
        tickfont=dict(size=16),
        side='left',
        tickmode='linear',
        tick0=0,
        dtick=st.session_state.get("ytick_step", 5),
        range=[0, st.session_state.get("y_max", 100)]
    ),
    legend=dict(x=1.05, y=1, font=dict(size=st.session_state.get("legend_font", 15)), traceorder="normal"),
    margin=dict(l=50, r=100, t=50, b=50),
    height=st.session_state.get("plot_height", 7) * 100,
    width=st.session_state.get("plot_width", 14) * 100,
    updatemenus=[
        dict(
            type="buttons",
            direction="right",
            xanchor="right",
            x=1.0,
            yanchor="top",
            y=1.08,
            showactive=True,
            pad={"r": 0, "t": 0},
            buttons=[
                dict(
                    label="Legend on",
                    method="relayout",
                    args=[{
                        "showlegend": True,
                        "updatemenus[0].x": 1.0,
                        "updatemenus[0].xanchor": "right",
                        "updatemenus[0].y": 1.08,
                        "updatemenus[0].yanchor": "top"
                    }]
                ),
                dict(
                    label="Legend off",
                    method="relayout",
                    args=[{
                        "showlegend": False,
                        "updatemenus[0].x": 1.0,
                        "updatemenus[0].xanchor": "right",
                        "updatemenus[0].y": 1.08,
                        "updatemenus[0].yanchor": "top"
                    }]
                )
            ]
        )
    ]
)

# 第二縦軸を使用する場合だけ追加
if st.session_state.get("use_secondary_axis", False):
    layout_dict["yaxis2"] = dict(
        title=dict(text=st.session_state.get("y2_title", ""), font=dict(size=18)),
        tickfont=dict(size=16),
        overlaying='y',
        side='right',
        tickmode='linear',
        tick0=0,
        dtick=st.session_state.get("secondary_tick_step", 5),
        range=[0, st.session_state.get("y2_max", 100)],
        showgrid=False
    )
fig.update_layout(**layout_dict)

st.plotly_chart(fig, use_container_width=True)

    # ===== Pyplotでの保存用チャート表示（メイン画面） =====
st.markdown('<p style="font-size: 30px; margin-top: 0em;"><b>↓🎨For saving chart↓</b></p>', unsafe_allow_html=True)

with st.expander("🎨 Matplotlib chart", expanded=False):

    colormap_name = st.session_state["colormap_name"]
    colormap = plt.get_cmap(colormap_name)

    style_options = {
        "-": {"linestyle": "-", "marker": ""},
        "--": {"linestyle": "--", "marker": ""},
        ".": {"linestyle": "", "marker": "o"},
        "-＋.": {"linestyle": "-", "marker": "o"},
        "--＋.": {"linestyle": "--", "marker": "o"},
        ".": {"linestyle": ":", "marker": ""}
    }

    for i in range(0, len(selected_y_cols), 5):
            row_cols = st.columns(5)
            for j, col in enumerate(selected_y_cols[i:i+5]):
                safe_key = sanitize_key(f"style1_{i+j}_{col}")
                with row_cols[j]:
                    st.session_state["style_map"][col] = st.selectbox(
                        f"{col} style", list(style_options.keys()), index=0, key=safe_key)

    for i in range(0, len(secondary_y_cols), 5):
            row_cols = st.columns(5)
            for j, col in enumerate(secondary_y_cols[i:i+5]):
                safe_key = sanitize_key(f"style2_{i+j}_{col}")
                with row_cols[j]:
                    st.session_state["style_map"][col] = st.selectbox(
                        f"{col} style（2nd Y-axis）", list(style_options.keys()), index=2, key=safe_key)

   
    st.write({"1st Y-axis": selected_y_cols, "2nd Y-axis": secondary_y_cols})

    try:
        if "color_map" not in st.session_state:
            st.session_state.color_map = {}

        fig, ax = plt.subplots(figsize=(width, height), dpi=150)
        n_total = len(selected_y_cols) + len(secondary_y_cols)

        for i, col in enumerate(selected_y_cols):
            color = st.session_state.color_map.get(col, colormap(i / max(n_total-1, 1)))
            style = style_options[st.session_state["style_map"].get(col, "line")]
            ax.plot(time_vals, df[col], label=col, linewidth=1.5, linestyle=style["linestyle"], marker=style["marker"], color=color)

        ax2 = None
        if use_secondary_axis and secondary_y_cols:
            ax2 = ax.twinx()
            for j, col in enumerate(secondary_y_cols):
                color = st.session_state.color_map.get(col, colormap((len(selected_y_cols)+j) / max(n_total-1, 1)))
                style = style_options[st.session_state["style_map"].get(col, "only markers")]
                ax2.plot(time_vals, df[col], label=col, linewidth=1.5, linestyle=style["linestyle"], marker=style["marker"], markersize=1.7,color=color)
            ax2.set_ylabel(secondary_y_axis_title, fontsize=label_font, labelpad=2)
            ax2.tick_params(axis='y', labelsize=tick_font)
            y2ticks = list(range(0, y2_max + 1, secondary_tick_step))
            if len(y2ticks) <= 100:
                ax2.set_ylim(0, y2_max)
                ax2.set_yticks(y2ticks)

        if show_cursor and 0 <= cursor_index < len(time_vals):
            ax.axvline(x=cursor_index, color='black', linestyle='--', linewidth=1)
            ax.annotate(
                f"{time_vals.iloc[cursor_index]}",
                xy=(cursor_index, ax.get_ylim()[0]),
                xycoords=('data', 'data'),
                textcoords='offset points',
                xytext=(0, -20),
                ha='center',
                fontsize=10,
                rotation=0
            )

        ax.set_xlabel(x_axis_title, fontsize=label_font, labelpad=5)
        ax.set_ylabel("")

       # 例: "NewBIOS PTAT.csv\n(Power)" のようにタイトルと検索語句（または軸のテーマ）をセットで縦ラベルとして表示
        vertical_label = f"{file}\n{y_axis_title}"

        max_ytick_label = max([str(int(t)) for t in ax.get_yticks()], key=len)
        offset = -0.03 - 0.013 * len(max_ytick_label)  # 長さに応じて左に寄せる

        # 組み合わせラベル
        vertical_label = f"{file}\n{y_axis_title}"

        # テキスト配置
        ax.text(
            offset,
            0.5,
            vertical_label,
            transform=ax.transAxes,
            fontsize=title_font,
            rotation=90,
            ha='center',
            va='center'
        )

        lines, labels = [], []
        if show_legend:
            lines, labels = ax.get_legend_handles_labels()
            if ax2:
                lines2, labels2 = ax2.get_legend_handles_labels()
                lines += lines2
                labels += labels2
            if len(lines) <= 4:
                legend = ax.legend(lines, labels, loc="upper right", fontsize=legend_font)
            else:
                legend = ax.legend(lines, labels, loc="upper center", bbox_to_anchor=(1.05, 1), borderaxespad=0., fontsize=legend_font, ncol=1 if height > 6 else 2)

            if legend_alpha is not None:
                legend.get_frame().set_facecolor("#FFFFFF")
                legend.get_frame().set_alpha(legend_alpha)

        ax.grid(axis='x', visible=show_xgrid)

        if len(time_vals) >= 2:
            if show_xgrid:
                ax.set_xticks([0, len(time_vals)-1])
                ax.set_xticklabels([time_vals.iloc[0], time_vals.iloc[-1]], rotation=0, ha='right', fontsize=tick_font)
            else:
                ax.set_xticks([])

        yticks = list(range(int(y_min), int(y_max)+1, ytick_step))
        if len(yticks) <= 100:
            ax.set_ylim(y_min, y_max)
            ax.set_yticks(yticks)
        else:
            st.warning("Turned auto scale due to much tickes.")
            ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=10))

        ax.tick_params(axis='x', labelsize=tick_font)
        ax.tick_params(axis='y', labelsize=tick_font)

        st.pyplot(fig)
    except Exception as e:
        st.error(f"Error: {e}")

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

# ==== タブのラベルと対応するヘッダー ====
tab_labels = ["CPU&sensors temp", "Powerlimit", "EPP&Mode"]
tab_headers = {
    "CPU&sensors temp": ":thermometer: CPU & Sensors Temperature",
    "Powerlimit": ":zap: Power Limits",
    "EPP&Mode": ":battery: EPP & PowerMode",
}

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

# ==== タブ表示・タイトル表示 ====
tabs = st.tabs(tab_labels)
for i, tab in enumerate(tabs):
    with tab:
        st.session_state["tab_index"] = i

# ==== タブ処理 ====
with tabs[0]:
    st.markdown(f"## {tab_headers['CPU&sensors temp']}")

    if temp_cols:
        fig_temp = go.Figure()
        temp_abnormal = False
        for col in temp_cols:
            fig_temp.add_trace(go.Scatter(
                x=time_vals,
                y=df[col],
                mode='lines',
                name=col
            ))
            if df[col].max() > 130:
                temp_abnormal = True
                st.warning(f" {col} over 130deg", icon="⚠️")



        fig_temp.update_layout(
            xaxis_title="Time",
            yaxis_title="Temperature (°C)",
            height=600, 
            width=1400,
            margin=dict(l=40, r=40, t=40, b=40),
            legend=dict(x=1.05, y=1,font=dict(size=st.session_state.get("legend_font", 50)),traceorder="normal"),
            font=dict(size=14),
            xaxis=dict(
                title=dict(text="Time", font=dict(size=18)),
                tickfont=dict(size=16)
                ),
            yaxis=dict(
                title=dict(text="Temperature (°C)", font=dict(size=18)),
                tickfont=dict(size=16),
                range=[0, 130] if temp_abnormal else None
                ),
            updatemenus=[
                dict(
                    type="buttons",
                    direction="right",
                    xanchor="right",
                    x=1.0,
                    yanchor="top",
                    y=1.08,
                    showactive=True,
                    pad={"r": 0, "t": 0},
                    buttons=[
                        dict(
                            label="Legend on",
                            method="relayout",
                            args=[
                                {
                                    "showlegend": True,
                                    "updatemenus[0].x": 1.0,
                                    "updatemenus[0].xanchor": "right",
                                    "updatemenus[0].y": 1.08,
                                    "updatemenus[0].yanchor": "top"
                                }
                            ]
                        ),
                        dict(
                            label="Legend off",
                            method="relayout",
                            args=[
                                {
                                    "showlegend": False,
                                    "updatemenus[0].x": 1.0,
                                    "updatemenus[0].xanchor": "right",
                                    "updatemenus[0].y": 1.08,
                                    "updatemenus[0].yanchor": "top"
                                }
                            ]
                        )
                    ]
                )
            ]
        )

        st.plotly_chart(fig_temp, use_container_width=True)
    else:
        st.info("No found")

# === 追加: Powerlimitタブ ===
with tabs[1]:
    st.markdown(f"## {tab_headers['Powerlimit']}")

    # 描画対象の明示的な列指定
    target_cols = [
        "TCPU_D0_Current Power(W)",
        "TCPU_D1_Current Power(W)",
        "TCPU_D2_Current Power(W)",
        "TCPU_PL1 Limit(W)",
        "TCPU_PL1 Min Power Limit(W)",
        "TCPU_PL1 Max Power Limit(W)",
        "TCPU_PL2 Limit(W)"
    ]

    # 存在する列だけ抽出（ファイルによっては存在しない列もあり得るため）
    plot_cols = [col for col in target_cols if col in df.columns]

    if plot_cols:
        fig_power = go.Figure()
        power_abnormal = False

        for col in plot_cols:
            y_data = pd.to_numeric(df[col], errors="coerce")
            fig_power.add_trace(go.Scatter(
                x=time_vals,
                y=y_data,
                mode='lines',
                name=col
            ))
            if (y_data < 0).any() or (y_data > 250).any():
                power_abnormal = True
                st.warning(f"{col} found below 0deg or over 250deg", icon="⚠️")

        yaxis_range = [0, 100] if power_abnormal else None

        fig_power.update_layout(
            xaxis_title="Time",
            yaxis_title="Power(W)",
            height=600,
            width=1400,
            margin=dict(l=40, r=40, t=40, b=40),
            legend=dict(x=1.05, y=1, font=dict(size=st.session_state.get("legend_font", 50)), traceorder="normal"),
            font=dict(size=14),
            xaxis=dict(
                title=dict(text="Time", font=dict(size=18)),
                tickfont=dict(size=16)
            ),
            yaxis=dict(
                title=dict(text="Power(W)", font=dict(size=18)),
                tickfont=dict(size=16),
                range=yaxis_range
            ),
            updatemenus=[
                dict(
                    type="buttons",
                    direction="right",
                    xanchor="right",
                    x=1.0,
                    yanchor="top",
                    y=1.08,
                    showactive=True,
                    pad={"r": 0, "t": 0},
                    buttons=[
                        dict(
                            label="Legend on",
                            method="relayout",
                            args=[
                                {
                                    "showlegend": True,
                                    "updatemenus[0].x": 1.0,
                                    "updatemenus[0].xanchor": "right",
                                    "updatemenus[0].y": 1.08,
                                    "updatemenus[0].yanchor": "top"
                                }
                            ]
                        ),
                        dict(
                            label="Legend off",
                            method="relayout",
                            args=[
                                {
                                    "showlegend": False,
                                    "updatemenus[0].x": 1.0,
                                    "updatemenus[0].xanchor": "right",
                                    "updatemenus[0].y": 1.08,
                                    "updatemenus[0].yanchor": "top"
                                }
                            ]
                        )
                    ]
                )
            ]
        )

        st.plotly_chart(fig_power, use_container_width=True)
    else:
        st.info("No found")


with tabs[2]:
    st.markdown(f"## {tab_headers['EPP&Mode']}")

    epp_col = next((col for col in df.columns if "epp" in col.lower()), None)
    os_power_col = next((col for col in df.columns if "os power slider" in col.lower()), None)
    if os_power_col:
        mapping = {25: "Energy saver", 50: "Best Power Efficiency", 75: "Balanced", 100: "Best Performance"}
        df[os_power_col + "_str"] = df[os_power_col].map(mapping)


    if epp_col:
        df[epp_col] = df[epp_col].apply(lambda x: round(x / 2.55) if pd.notnull(x) else x)

    if epp_col and os_power_col:
        fig_epp = go.Figure()

        fig_epp.add_trace(go.Scatter(
            x=time_vals,
            y=df[epp_col],
            mode="lines",
            name=epp_col,
            yaxis="y1",
            line=dict(color="purple")
        ))

        fig_epp.add_trace(go.Scatter(
            x=time_vals,
            y=df[os_power_col],
            mode="markers",
            name="Power Mode",
            yaxis="y2",
            text=df[os_power_col + "_str"],
            textposition="top center",
            marker=dict(color="green", size=8)
        ))

        fig_epp.update_layout(
            height=600,
            width=1400,
            margin=dict(l=40, r=40, t=40, b=40),
            legend=dict(x=1.05, y=1, font=dict(size=st.session_state.get("legend_font", 50)), traceorder="normal"),
            xaxis=dict(title="Time", tickfont=dict(size=18)),
            yaxis=dict(
            title=dict(text=epp_col, font=dict(size=18)),
            tickfont=dict(size=16),
            dtick=5,
            gridcolor='rgba(200, 150, 255, 0.17)'
            ),
            yaxis2=dict(
            title=dict(text="Power Mode", font=dict(size=18)),
            tickfont=dict(size=16),
            overlaying='y',
            side='right',
            showgrid=False,
            tickmode='array',
            tickvals=[25, 50, 75, 100],
            ticktext=["Energy saver", "Best Power Efficiency", "Balanced", "Best Performance"],
            tick0=0,
            dtick=25          # 目盛間隔を1に
            ),
            updatemenus=[
                dict(
                    type="buttons",
                    direction="right",
                    xanchor="right",
                    x=1.0,
                    yanchor="top",
                    y=1.08,
                    showactive=True,
                    pad={"r": 0, "t": 0},
                    buttons=[
                        dict(
                            label="Legend on",
                            method="relayout",
                            args=[
                                {
                                    "showlegend": True,
                                    "updatemenus[0].x": 1.0,
                                    "updatemenus[0].xanchor": "right",
                                    "updatemenus[0].y": 1.08,
                                    "updatemenus[0].yanchor": "top"
                                }
                            ]
                        ),
                        dict(
                            label="Legend off",
                            method="relayout",
                            args=[
                                {
                                    "showlegend": False,
                                    "updatemenus[0].x": 1.0,
                                    "updatemenus[0].xanchor": "right",
                                    "updatemenus[0].y": 1.08,
                                    "updatemenus[0].yanchor": "top"
                                }
                            ]
                        )
                    ]
                )
            ]
    )

        st.plotly_chart(fig_epp, use_container_width=True)

    else:
        st.warning("No found")

# ===== CoreType表示（段組＋カラーマップ対応）を成功風UIで表示 =====
core_type_map = {}
for col in df.columns:
    if "core type" in col.lower():
        core_id = col.split("-")[0]
        core_type = df[col].iloc[0]
        core_type_map[core_id] = core_type

if core_type_map:
    grouped = {}
    for core, ctype in core_type_map.items():
        grouped.setdefault(ctype, []).append(core)

    html = textwrap.dedent("""
    <div style='
        background-color:#1e3d32;
        padding:16px 24px;
        border-radius:12px;
        margin:20px 0;
        color:white;
    '>
        <div style='font-weight:bold; font-size:25px; margin-bottom:10px;'>Core Type Overview</div>
        <div style='display:flex; flex-wrap:wrap; gap:20px;'>
    """)

    for ctype, cores in grouped.items():
        html += f"<div><div style='font-weight:bold; font-size:18px; margin-bottom:0px'>{ctype} Cores</div>"
        html += "<div style='display:flex; flex-wrap:wrap; gap:11px; font-size:17px;'>"
        for core in cores:
            html += f"<span>{core}</span>"
        html += "</div></div>"

    html += "</div></div>"

    st.markdown(html, unsafe_allow_html=True)
