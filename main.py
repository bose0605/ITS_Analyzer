import streamlit as st
import os
import base64

# ページ設定
st.set_page_config(
    page_title="ITSツールメニュー",
    page_icon="📂",
    initial_sidebar_state="collapsed",
    layout="wide"
)

st.markdown("""
    <style>
    .tool-image {
        width: 100%;
        aspect-ratio: 1 / 1;
        object-fit: cover;
        border-radius: 10px;
        transition: border 0.3s ease-in-out;
        border: 2px solid #333333;
    }
    .tool-image:hover {
        border: 2px solid red;
        cursor: pointer;
    }
    .tool-label {
        text-align: center;
        margin-top: 5px;
        font-weight: bold;
        color: lightgray;
    }
    .update-box {
        background-color: #e6f7ff;
        border: 1px solid #ccc;
        padding: 0.5rem 1rem;
        margin-top: 1rem;
        border-radius: 10px;
        color: black;
    }
    .update-box h4 {
        margin-bottom: 0.3rem;
    }
    .stButton > button {
        font-size: 1.2rem !important;
        padding: 0.6rem 1.2rem;
        float: right;
    }
    </style>
""", unsafe_allow_html=True)

st.title(":open_file_folder: Converter&Viewer warehouse")

# ツール定義
tools = [
    {
        "label": "sensor correlation",
        "href": "sensor_correlation",
        "image": "fig/1.png"
    },
    {
        "label": "pTAT Viewer",
        "href": "pTAT_viewer",
        "image": "fig/2.png"
    },
    {
        "label": "DTT Viewer",
        "href": "DTT_viewer",
        "image": "fig/3.png"
    },
    {
        "label": "converter",
        "href": "converter",
        "image": "fig/4.png"
    }
]

# ヘッダー直下の行（左：説明文、右：Bug Reportボタン）
desc_col, feedback_col = st.columns([4, 1])
with desc_col:
    st.write("画像をクリックして各ツールページに移動できます。")
with feedback_col:
    if st.button("🐞 Bug report"):
        st.markdown("[アンケートフォームへ移動（ダミー）](https://example.com/survey-form)", unsafe_allow_html=True)

# 🌈 虹色ライン
st.markdown("""
<hr style="
  height: 6px;
  border: none;
  border-radius: 3px;
  background: linear-gradient(to right, red, orange, yellow, green, blue, indigo, violet);
  margin-top: 1px;
  margin-bottom: 26px;
">
""", unsafe_allow_html=True)

# メインレイアウト：左（ツールアイコン）、右（更新履歴）
left_col, right_col = st.columns([1, 1])

# 左側：ツール画像を4列で段組み表示
with left_col:
    num_cols = 4
    rows = [tools[i:i+num_cols] for i in range(0, len(tools), num_cols)]
    for row_tools in rows:
        row = st.columns(num_cols)
        for tool, col in zip(row_tools, row):
            with col:
                if os.path.exists(tool["image"]):
                    with open(tool["image"], "rb") as img_file:
                        encoded = base64.b64encode(img_file.read()).decode()
                    st.markdown(
                        f"""
                        <a href="/{tool['href']}" target="_self">
                            <img src="data:image/png;base64,{encoded}" class="tool-image" />
                            <div class="tool-label">{tool['label']}</div>
                        </a>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    st.error(f"画像が見つかりません: {tool['image']}")

# 右側：更新履歴
with right_col:
    st.markdown("""
    <div class="update-box">
      <h4>ver 1.0 (2025/xx/xx)</h4>
      <ul>
        <li>initial 4つのfunction実装</li>
        <li>Bug reportボタン（st.button）として追加</li>
        <li>左側：各種ツール（4列） ／ 上部右側：Bug report ／ 右下：更新履歴</li>
      </ul>
    </div>
    """, unsafe_allow_html=True)
