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
import matplotlib.colors as mcolors
import re  
import textwrap
import chardet
from io import StringIO

def sanitize_key(text: str) -> str:
    return re.sub(r'\W+', '_', text)

def get_color_hex(cmap, index, total):
    rgba = cmap(index / max(total - 1, 1))
    return mcolors.to_hex(rgba, keep_alpha=False)


plt.rcParams["font.family"] = "Arial"
st.set_page_config(layout="wide")
if "colormap_name" not in st.session_state:
    st.session_state["colormap_name"] = "plasma"

# 🌈 虹色ライン
st.markdown("""
<hr style="
  height: 6px;
  border: none;
  border-radius: 3px;
  background: linear-gradient(to right, red, orange, yellow, green, blue, indigo, violet);
  margin-top: 20px;
  margin-bottom: 26px;
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
section[data-testid="stSidebar"] .stMarkdown p {
  color: white;
  font-size: 1.05rem;
}
section[data-testid="stSidebar"] label {
  color: white !important;
  font-size: 1.05rem;
}
</style>
""", unsafe_allow_html=True)

st.title("\U0001F4CA Fornewcreation-pTAT Viewer(Pyplot&Plotly)")

# ===== ファイルアップロード =====
with st.sidebar.expander("1️⃣ CSVファイルの選択", expanded=True):
    uploaded_file = st.file_uploader("CSVファイルをアップロード", type="csv", accept_multiple_files=False)

    if not uploaded_file:
        st.warning("CSVファイルをアップロードしてください。")
        st.stop()

    file = uploaded_file.name
    x_axis_title = st.text_input("X軸のタイトル", value="Time (s)", key="x_axis_title_input")
    y_axis_title = st.text_input("縦軸のタイトル", value="Power (W)", key="y_axis_title_input")
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


df = load_csv(uploaded_file)

# ===== Time列の取得 =====
time_col_candidates = [col for col in df.columns if "time" in col.lower()]
if not time_col_candidates:
    st.error("Time列が見つかりません。CSVに 'Time' 列を追加してください。")
    st.stop()
time_col = time_col_candidates[0]

try:
    df[time_col] = pd.to_datetime(df[time_col])
    time_vals = df[time_col].dt.strftime("%H:%M:%S")
except:
    time_vals = df[time_col]

# ===== デフォルト縦軸列取得関数 =====
def get_default_power_cols():
    # 優先順位で取得
    package_power = [col for col in df.columns if "package power" in col.lower()]
    ia_power = [col for col in df.columns if "ia power" in col.lower()]
    rest_package = [col for col in df.columns if "rest of package" in col.lower()]

    # その他のpower列（time列とすでに入ってるもの以外）
    existing = set(package_power + ia_power + rest_package + [time_col])
    other_powers = [col for col in df.columns if "power" in col.lower() and col not in existing]

    # 順に結合して最大5列まで返す
    seen = set()
    unique_cols = []
    for col in (package_power + ia_power + rest_package + other_powers):
        if col not in seen:
            unique_cols.append(col)
            seen.add(col)
    return unique_cols[:5]


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
with st.sidebar.expander("2️⃣ 第一縦軸の列設定", expanded=True):
    search_query = st.text_input("検索キーワード（縦軸）", value="Power", key="primary_search_input")
    y_axis_candidates = [col for col in df_unique_columns if search_query.lower() in col.lower() and col != time_col]

    if "selected_y_cols" not in st.session_state:
        st.session_state.selected_y_cols = get_default_power_cols()
    if "primary_add_selectbox" not in st.session_state:
        st.session_state["primary_add_selectbox"] = ""

    selected_to_add = st.selectbox(
        "候補から列を追加（即時追加）",
        options=[""] + [col for col in y_axis_candidates if col not in st.session_state.selected_y_cols],
        index=0,
        key="primary_add_selectbox"
    )


    # セレクトボックスで新規選択されたら追加し rerun（session_stateは触らない！）
    if selected_to_add and selected_to_add not in st.session_state.selected_y_cols:
        st.session_state.selected_y_cols.append(selected_to_add)
        st.rerun() 


    st.markdown("### 第一縦軸 描画中の列")
    remove_cols = st.multiselect(
        "チェックを外すと削除",
        options=st.session_state.selected_y_cols,
        default=st.session_state.selected_y_cols,
        key="primary_remove_multiselect"
    )
    st.session_state.selected_y_cols = remove_cols

    priority_col = "Power-Package Power(Watts)"
    if priority_col in st.session_state.selected_y_cols:
        st.session_state.selected_y_cols.remove(priority_col)
        st.session_state.selected_y_cols.insert(0, priority_col)


# ===== グラフ書式設定 + フォント + 軸範囲 + 凡例 + 第二縦軸トグル まとめてexpander =====
with st.sidebar.expander("3️⃣ グラフ書式設定", expanded=True):
    colormap_list = sorted(plt.colormaps())
    default_cmap = "brg"
    st.session_state["colormap_name"] = st.selectbox(
        "カラーマップを選択",
        colormap_list,
        index=colormap_list.index(default_cmap) if default_cmap in colormap_list else 0,
        key="colormap_select"
    )
    width = st.slider("グラフの横幅\n(For saving chart)", 8, 24, 14, key="plot_width")
    height = st.slider("グラフの縦幅\n(For saving chart)", 4, 16, 7, key="plot_height")
    ytick_step = st.number_input("縦軸の目盛間隔", min_value=1, value=5, key="ytick_step")
    show_cursor = st.checkbox("垂線とラベルを表示\n(For saving chart)", value=False, key="show_cursor")
    cursor_index = st.number_input("任意点で垂線を表示\n(For saving chart)", min_value=0, max_value=len(df)-1, value=0, key="cursor_index")
    show_xgrid = st.checkbox("始点・終点のグリッドを表示\n", value=True, key="show_xgrid")

    st.markdown("### 🖋 フォントサイズ設定")
    label_font = st.slider("軸ラベルのサイズ\n(For saving chart)", 8, 24, 17, key="label_font")
    tick_font = st.slider("目盛のフォントサイズ\n(For saving chart)", 6, 20, 13, key="tick_font")
    title_font = st.slider("タイトルのサイズ\n(For saving chart)", 10, 30, 17, key="title_font")

    st.markdown("### 📐第一縦軸の範囲")
    numeric_cols = df.select_dtypes(include='number').columns
    y_min = 0
    try:
        y_max_data = int(df[st.session_state.get("selected_y_cols", [])].max().max() * 1.1)
    except:
        y_max_data = 70
    y_max = st.number_input("第一縦軸の上限", min_value=1, value=y_max_data if y_max_data < 10000 else 100, key="y_max")

    st.markdown("### 📌 凡例の設定 (For saving chart)")
    show_legend = st.toggle("凡例を表示する\n(For saving chart)", value=True, key="show_legend")
    legend_font = None
    legend_alpha = None
    if show_legend:
        legend_font = st.slider("凡例のフォントサイズ\n(For saving chart)", 6, 20, 10, key="legend_font")
        legend_alpha = st.slider("凡例の透過度 (0=透明, 1=不透明)\n(For saving chart)", 0.0, 1.0, 0.5, step=0.05, key="legend_alpha")

# ===== 第二縦軸設定（expander内にトグルも含めて表示） =====
with st.sidebar.expander("4️⃣ 第二縦軸の設定", expanded=True):
    use_secondary_axis = st.toggle("第二縦軸を使用する", value=False, key="use_secondary_axis")

    if use_secondary_axis:
        secondary_y_axis_title = st.text_input("第二縦軸のタイトル", value="Temperature (deg)", key="y2_title")
        secondary_tick_step = st.number_input("第二縦軸の目盛間隔", min_value=1, value=5, key="y2_tick_step")

        y2_max_data = int(df.select_dtypes(include='number').max().max() * 1.1)
        y2_max = st.number_input("第二縦軸の上限\n(For saving chart)", min_value=1, value=y2_max_data if y2_max_data < 10000 else 100, key="y2_max")

        st.markdown("**第二縦軸の列を検索・追加**")
        y2_search = st.text_input("検索キーワード（第二縦軸）", value="Temp", key="y2_search")
        y2_candidates = [col for col in df.columns if y2_search.lower() in col.lower() and col != time_col]

        if "secondary_y_cols" not in st.session_state:
            st.session_state.secondary_y_cols = []

        y2_add = st.selectbox(
            "候補から列を追加（第二縦軸)",
            options=[""] + [col for col in y2_candidates if col not in st.session_state.secondary_y_cols],
            index=0
        )

        # 候補追加があった場合にだけ append＋rerun し、直後に return しない
        if y2_add and y2_add not in st.session_state.secondary_y_cols:
            st.session_state.secondary_y_cols.append(y2_add)
            st.rerun()  # ← rerun後にマークダウン描画されるようになる！

        # ここは常に描画される（マークダウン＋チェックボックス）
        st.markdown("### 第二縦軸 描画中の列")
        y2_remove_cols = st.multiselect(
            "チェックを外すと削除",
            options=st.session_state.secondary_y_cols,
            default=st.session_state.secondary_y_cols,
            key="y2_remove"
        )
        st.session_state.secondary_y_cols = y2_remove_cols


selected_y_cols = st.session_state.selected_y_cols
secondary_y_cols = st.session_state.get("secondary_y_cols", []) if use_secondary_axis else []

# ===== Plotlyグラフ描画 =====
if "style_map" not in st.session_state:
    st.session_state["style_map"] = {}

for col in selected_y_cols + secondary_y_cols:
    st.session_state["style_map"].setdefault(col, "直線")

colormap_name = st.session_state["colormap_name"]
colormap = cm.get_cmap(colormap_name)

style_options = {
    "直線": {"dash": None, "marker": None},
    "点線": {"dash": "dash", "marker": None},
    "点のみ": {"dash": None, "marker": "circle"},
    "線＋点": {"dash": None, "marker": "circle"},
    "破線＋点": {"dash": "dash", "marker": "circle"},
    "ドット線": {"dash": "dot", "marker": None}
}

# ===== 平均値表示のUI（Expanderでまとめて制御） =====
if "show_avg_lines" not in st.session_state:
    st.session_state.show_avg_lines = False


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
        legendgroup="group1",
        showlegend=True
    ))

for j, col in enumerate(secondary_y_cols):
    style = style_options.get(st.session_state["style_map"].get(col, "点のみ"), {})
    fig.add_trace(go.Scatter(
        x=time_vals,
        y=df[col],
        name=col,
        line=dict(
            color=get_color_hex(colormap, len(selected_y_cols) + j, total_lines),  # ← 同じ関数で
            dash=style.get("dash")
        ),
        mode="lines+markers" if style.get("marker") else "lines",
        marker=dict(symbol=style.get("marker")) if style.get("marker") else None,
        yaxis="y2",
        legendgroup="group2",
        showlegend=True
    ))

# ==== 📏 平均値と垂線表示用 toggle（Expanderの代替） ====
show_avg = st.toggle("📏 任意区間の平均値を表示", value=False)

if show_avg:
    midpoint = len(df) // 2
    col1, col2, col3, col4 = st.columns([1, 1, 2, 2])
    with col1:
        idx_start = st.number_input("開始インデックス", min_value=0, max_value=len(df)-1, value=0, step=1, key="idx_start")
    with col2:
        idx_end = st.number_input("終了インデックス", min_value=0, max_value=len(df)-1, value=midpoint, step=1, key="idx_end")
    with col3:
        available_avg_cols = st.session_state.selected_y_cols or df.select_dtypes(include='number').columns.tolist()
        avg_target_col = st.selectbox("対象データ列", options=available_avg_cols, index=0, key="avg_col")

    if idx_start < idx_end and avg_target_col in df.columns:
        avg_val = df[avg_target_col].iloc[idx_start:idx_end+1].mean()
        with col4:
            st.success(f"📏 {avg_target_col} の {idx_start}〜{idx_end} の平均値: {avg_val:.2f}")

        x_start = time_vals.iloc[idx_start] if hasattr(time_vals, "iloc") else time_vals[idx_start]
        x_end = time_vals.iloc[idx_end] if hasattr(time_vals, "iloc") else time_vals[idx_end]

        # 垂線の追加（同期済み）
        fig.add_vline(x=x_start, line=dict(dash="dot", width=5, color="red"))
        fig.add_vline(x=x_end, line=dict(dash="dot", width=5, color="blue"))

layout_dict = dict(
    title="",
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
                    label="凡例表示",
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
                    label="凡例非表示",
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
        range=[0, st.session_state.get("y2_max", 100)]
    )
fig.update_layout(**layout_dict)

st.plotly_chart(fig, use_container_width=True)

    # ===== Pyplotでの保存用チャート表示（メイン画面） =====
st.markdown('<p style="font-size: 30px; margin-top: 0em;"><b>↓🎨For saving chart↓</b></p>', unsafe_allow_html=True)

with st.expander("🎨 Matplotlib chart (保存用chart)", expanded=False):

    colormap_name = st.session_state["colormap_name"]
    colormap = plt.get_cmap(colormap_name)

    style_options = {
        "直線": {"linestyle": "-", "marker": ""},
        "点線": {"linestyle": "--", "marker": ""},
        "点のみ": {"linestyle": "", "marker": "o"},
        "線＋点": {"linestyle": "-", "marker": "o"},
        "破線＋点": {"linestyle": "--", "marker": "o"},
        "ドット線": {"linestyle": ":", "marker": ""}
    }

    for i in range(0, len(selected_y_cols), 5):
            row_cols = st.columns(5)
            for j, col in enumerate(selected_y_cols[i:i+5]):
                safe_key = sanitize_key(f"style1_{i+j}_{col}")
                with row_cols[j]:
                    st.session_state["style_map"][col] = st.selectbox(
                        f"{col} の形式", list(style_options.keys()), index=0, key=safe_key)

    for i in range(0, len(secondary_y_cols), 5):
            row_cols = st.columns(5)
            for j, col in enumerate(secondary_y_cols[i:i+5]):
                safe_key = sanitize_key(f"style2_{i+j}_{col}")
                with row_cols[j]:
                    st.session_state["style_map"][col] = st.selectbox(
                        f"{col} の形式（第二縦軸）", list(style_options.keys()), index=2, key=safe_key)

   
    st.write({"第一縦軸": selected_y_cols, "第二縦軸": secondary_y_cols})

    try:
        if "color_map" not in st.session_state:
            st.session_state.color_map = {}

        fig, ax = plt.subplots(figsize=(width, height), dpi=150)
        n_total = len(selected_y_cols) + len(secondary_y_cols)

        for i, col in enumerate(selected_y_cols):
            color = st.session_state.color_map.get(col, colormap(i / max(n_total-1, 1)))
            style = style_options[st.session_state["style_map"].get(col, "直線")]
            ax.plot(time_vals, df[col], label=col, linewidth=1.5, linestyle=style["linestyle"], marker=style["marker"], color=color)

        ax2 = None
        if use_secondary_axis and secondary_y_cols:
            ax2 = ax.twinx()
            for j, col in enumerate(secondary_y_cols):
                color = st.session_state.color_map.get(col, colormap((len(selected_y_cols)+j) / max(n_total-1, 1)))
                style = style_options[st.session_state["style_map"].get(col, "点のみ")]
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
            st.warning("第一縦軸の目盛が多すぎるため、自動スケーリングに切り替えました。")
            ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=10))

        ax.tick_params(axis='x', labelsize=tick_font)
        ax.tick_params(axis='y', labelsize=tick_font)

        st.pyplot(fig)
    except Exception as e:
        st.error(f"グラフ描画中にエラーが発生しました: {e}")

# ==== タブのラベルと対応するヘッダー ====
tab_labels = ["Frequency", "CPU temp", "IA-clip reason","GT-clip reason", "Phidget"]
tab_headers = {
    "Frequency": ":part_alternation_mark: All-core Frequencys",
    "CPU temp": "🌡 All-core Temperature",
    "IA-clip reason": ":warning: IA-Clip Reason",
    "GT-clip reason": ":warning: GT-Clip Reason",
    "Phidget": ":thermometer: Phidget Sensors"
}
# ==== タブ表示・タイトル表示 ====
st.markdown("""
<hr style="
  height: 6px;
  border: none;
  border-radius: 3px;
  background: linear-gradient(to right, red, orange, yellow, green, blue, indigo, violet);
  margin-top: 30px;
  margin-bottom: 36px;
">
""", unsafe_allow_html=True)

tabs = st.tabs(tab_labels)

# ==== タブ処理 ====
with tabs[0]:
    st.markdown(f"## {tab_headers['Frequency']}")
    # Frequency タブ専用の処理
    frequency_cols = [
    col for col in df.columns
    if re.fullmatch(r"CPU\d+-Frequency\(MHz\)", col, flags=re.IGNORECASE)
]
    if frequency_cols:
        fig_freq = go.Figure()
        freq_abnormal = False
        for col in frequency_cols:
            fig_freq.add_trace(go.Scatter(
                x=time_vals,
                y=df[col],
                mode='lines',
                name=col
            ))
            if df[col].max() > 8000:
                freq_abnormal = True
                st.warning(f" {col} に8000MHz超あり", icon="⚠️")


        fig_freq.update_layout(
            xaxis_title="Time",
            yaxis_title="Frequency (MHz)",
            height=600, 
            width=1400,
            margin=dict(l=40, r=40, t=40, b=40),
            legend=dict(x=1.05, y=1,font=dict(size=st.session_state.get("legend_font", 15)),traceorder="normal"),
            font=dict(size=14),
            xaxis=dict(
                title=dict(text="Time", font=dict(size=18)),
                tickfont=dict(size=16)
                ),
            yaxis=dict(
                title=dict(text="Frequency (MHz)", font=dict(size=18)),
                tickfont=dict(size=16),
                range=[0, 8000] if freq_abnormal else None
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
                            label="凡例表示",
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
                            label="凡例非表示",
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

        st.plotly_chart(fig_freq, use_container_width=True)
    else:
        st.info("CPUのFrequencyに関わる列が見つかりませんでした。")
with tabs[1]:
    st.markdown(f"## {tab_headers['CPU temp']}")

# CPU温度の列を抽出（DTS形式に限定せず、TempやCPU+温度のような名前も対象に）
    temp_cols = [
        col for col in df.columns
        if (
            (re.search(r"CPU\d+-DTS", col) or
            (("temp" in col.lower() or "temperature" in col.lower()) and "cpu" in col.lower()))
            and not col.startswith("TCPU")
        )
    ]
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
                st.warning(f" {col} に130℃超あり", icon="⚠️")



        fig_temp.update_layout(
            xaxis_title="Time",
            yaxis_title="Temperature (°C)",
            height=600, 
            width=1400,
            margin=dict(l=40, r=40, t=40, b=40),
            legend=dict(x=1.05, y=1,font=dict(size=st.session_state.get("legend_font", 35)),traceorder="normal"),
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
                            label="凡例表示",
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
                            label="凡例非表示",
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
        st.info("CPU温度に関する列（CPUxx-DTS）が見つかりませんでした。")


with tabs[2]:
    st.markdown(f"## {tab_headers['IA-clip reason']}")
    ia_clip_col = next((col for col in df.columns if "ia clip reason" in col.lower()), None)

    if ia_clip_col:
        ia_reasons = sorted(df[ia_clip_col].dropna().unique())
        ia_map = {v: i+1 for i, v in enumerate(ia_reasons)}
        df["IA_ClipReason_Mapped"] = df[ia_clip_col].map(ia_map)

        fig_ia = go.Figure()
        fig_ia.add_trace(go.Scatter(
            x=time_vals,
            y=df["IA_ClipReason_Mapped"],
            mode="lines+markers",
            line=dict(color="orange"),
            showlegend=False
        ))

        # ✅ ここが追加された部分（update_layoutの外）
        if priority_col in df.columns:
            fig_ia.add_trace(go.Scatter(
                x=time_vals,
                y=df[priority_col],
                mode="lines",
                name=priority_col,
                yaxis="y2",
                line=dict(color="red"),
                showlegend=True
            ))

            fig_ia.update_layout(
                yaxis2=dict(
                    title=dict(text="Package Power (W)", font=dict(size=16)),  
                    tickfont=dict(size=14),
                    overlaying='y',
                    side='right'
                )
            )

        # ✅ 元の update_layout はここでOK
        fig_ia.update_layout(
            height=600, width=1400,
            margin=dict(l=50, r=100, t=50, b=50),
            xaxis=dict(
                title=dict(text="Time", font=dict(size=18)),
                tickfont=dict(size=16)
            ),
            yaxis=dict(
                title=dict(text="IA Clip Reason", font=dict(size=18)),
                tickmode="array",
                tickvals=list(ia_map.values()),
                ticktext=[f"   {label}" for label in ia_map.keys()],
                tickfont=dict(size=16),
                gridcolor='rgba(255, 165, 0, 0.3)'
            ),
            yaxis2=dict(
                title=dict(text="Package Power (W)", font=dict(size=16)),
                tickfont=dict(size=14),
                overlaying='y',
                side='right',
                showgrid=False  # ← グリッド非表示
            )
        )

        st.plotly_chart(fig_ia, use_container_width=True)
    else:
        st.info("IA Clip Reason列が見つかりませんでした。")


with tabs[3]:
    st.markdown(f"## {tab_headers['GT-clip reason']}")
    gt_clip_col = next((col for col in df.columns if "gt clip reason" in col.lower()), None)
    if gt_clip_col:
        gt_reasons = sorted(df[gt_clip_col].dropna().unique())
        gt_map = {v: i+1 for i, v in enumerate(gt_reasons)}
        df["GT_ClipReason_Mapped"] = df[gt_clip_col].map(gt_map)

        fig_gt = go.Figure()
        fig_gt.add_trace(go.Scatter(
            x=time_vals,
            y=df["GT_ClipReason_Mapped"],
            mode="lines+markers",
            line=dict(color='rgba(0, 206, 209, 1)'),
            showlegend=False
        ))

                # ✅ ここが追加された部分（update_layoutの外）
        if priority_col in df.columns:
            fig_gt.add_trace(go.Scatter(
                x=time_vals,
                y=df[priority_col],
                mode="lines",
                name=priority_col,
                yaxis="y2",
                line=dict(color="red"),
                showlegend=True
            ))

            fig_gt.update_layout(
                yaxis2=dict(
                    title=dict(text="Package Power (W)", font=dict(size=16)),  
                    tickfont=dict(size=14),
                    overlaying='y',
                    side='right',
                    showgrid=False  # ← グリッド非表示
                )
            )

        # ✅ 元の update_layout はここでOK
        fig_gt.update_layout(
            height=600, width=1400,
            xaxis=dict(title=dict(text="Time",font=dict(size=18)),tickfont=dict(size=16)),
            yaxis=dict(
                title=dict(text="GT Clip Reason",font=dict(size=18)),
                tickmode="array",
                tickvals=list(gt_map.values()),
                ticktext=[f"   {label}" for label in gt_map.keys()],  # 👈 空白で左ラベルを中央寄せ風に
                tickfont=dict(size=16),
                gridcolor='rgba(0, 206, 209, 0.3)',
                showgrid=True  # ← グリッド非表示
            )
        )
        st.plotly_chart(fig_gt, use_container_width=True)
    else:
        st.info("GT Clip Reason列が見つかりませんでした。")

# === 追加: Phidgetタブ ===
with tabs[4]:
    st.markdown(f"## {tab_headers['Phidget']}")

    phidget_cols = [
        col for col in df.columns
        if "phidget" in col.lower() and "degree" in col.lower()
    ]

    if phidget_cols:
        fig_phidget = go.Figure()
        phidget_abnormal = False

        for col in phidget_cols:
            y_data = pd.to_numeric(df[col], errors="coerce")  # 数値変換してから使う
            fig_phidget.add_trace(go.Scatter(
                x=time_vals,
                y=y_data,
                mode='lines',
                name=col
            ))
            if (y_data < 0).any() or (y_data > 100).any():  # ← ✅ 数値に変換した結果で比較
                phidget_abnormal = True
                st.warning(f"{col} に0℃未満または100℃超のデータがあります", icon="⚠️")

        yaxis_range = [0, 100] if phidget_abnormal else None

        fig_phidget.update_layout(
            xaxis_title="Time",
            yaxis_title="Temperature (°C)",
            height=600,
            width=1400,
            margin=dict(l=40, r=40, t=40, b=40),
            legend=dict(x=1.05, y=1, font=dict(size=st.session_state.get("legend_font", 15)), traceorder="normal"),
            font=dict(size=14),
            xaxis=dict(
                title=dict(text="Time", font=dict(size=18)),
                tickfont=dict(size=16)
            ),
            yaxis=dict(
                title=dict(text="Temperature (°C)", font=dict(size=18)),
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
                            label="凡例表示",
                            method="relayout",
                            args=[{"showlegend": True}]
                        ),
                        dict(
                            label="凡例非表示",
                            method="relayout",
                            args=[{"showlegend": False}]
                        )
                    ]
                )
            ]
        )

        st.plotly_chart(fig_phidget, use_container_width=True)
    else:
        st.info("Phidget温度に関する列が見つかりませんでした。")

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
        <div style='font-weight:bold; font-size:18px; margin-bottom:10px;'>Core Type Overview</div>
        <div style='display:flex; flex-wrap:wrap; gap:20px;'>
    """)

    for ctype, cores in grouped.items():
        html += f"<div><div style='font-weight:bold; margin-bottom:0px'>{ctype} Cores</div>"
        html += "<div style='display:flex; flex-wrap:wrap; gap:8px; font-size:14px;'>"
        for core in cores:
            html += f"<span>{core}</span>"
        html += "</div></div>"

    html += "</div></div>"

    st.markdown(html, unsafe_allow_html=True)