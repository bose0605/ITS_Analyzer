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
    }
    .update-box {
        background-color: #e6f7ff;
        border: 1px solid #ccc;
        padding: 0.5rem 1rem;
        margin-top: 1.5rem;
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
    .tool-box {
        background-color: #101216;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #ccc;
        margin-top: 0.5rem;
}
    .tool-box {
        background-color: #0d1216;
        padding: 15px;
        border-radius: 10px;
        border: 0px solid #ccc;
        margin-top: 0.5rem;
}
    .tool-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);  /* 4列 */
        gap: 10px;
        align-items: start;
}
    .tool-wrapper {
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
}
    </style>
""", unsafe_allow_html=True)

# st.title(":open_file_folder: Converter&Viewer warehouse")
# ツール定義
tools = [
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
        "label": "Multiple rawdata<br>converter&viewer",
        "href": "converter",
        "image": "fig/4.png"
    },
    {
        "label": "sensor correlation",
        "href": "sensor_correlation",
        "image": "fig/1.png"
    },
]

# ヘッダー直下の行（左：説明文、右：Bug Reportボタン）
desc_col, feedback_col = st.columns([4, 1])
with desc_col:
    st.write("")
with feedback_col:
    st.markdown(
    """
    <a href="https://forms.office.com/r/vBCZR0tk9h" target="_blank">
        <button style="font-size: 1.2rem; padding: 0.6rem 1.2rem; float: right; background-color: orange; border: none; border-radius: 6px; cursor: pointer;">
            🐞 Bug report
        </button>
    </a>
    """,
    unsafe_allow_html=True
)
    
fig6="fig/6.png"
if os.path.exists(fig6):
    with open(fig6, "rb") as img_file:
        encoded_img = base64.b64encode(img_file.read()).decode()

    st.markdown(
        f"""
        <a href="https://streamlit.io/" target="_blank">
            <img src="data:image/png;base64,{encoded_img}" style="border:none; cursor:pointer;" />
        </a>
        """,
        unsafe_allow_html=True
    )


# 🌈 虹色ライン
# st.markdown("""
# <hr style="
#   height: 6px;
#   border: none;
#   border-radius: 3px;
#   background: linear-gradient(to right, red, orange, yellow, green, blue, indigo, violet);
#   margin-top: 1px;
#   margin-bottom: 26px;
# ">
# """, unsafe_allow_html=True)

# メインレイアウト：左（ツールアイコン）、右（更新履歴）
left_col, right_col = st.columns([1, 1])

# 左側：ツール画像を4列で段組み表示
with left_col:
    # HTML文字列組み立て（改行・空白を最小限に）
    tool_html = """
    <div class="tool-box">
        <div class="tool-grid">
    """
    for tool in tools:
        if os.path.exists(tool["image"]):
            with open(tool["image"], "rb") as img_file:
                encoded = base64.b64encode(img_file.read()).decode()
            tool_html += f"""<div class="tool-wrapper">
<a href="/{tool['href']}" target="_self">
<img src="data:image/png;base64,{encoded}" class="tool-image" />
<div class="tool-label">{tool['label']}</div>
</a>
</div>"""
        else:
            tool_html += f"""<div class="tool-wrapper"><p style="color:red;">画像が見つかりません:<br>{tool['image']}</p></div>"""
    tool_html += "</div></div>"

    st.markdown(tool_html, unsafe_allow_html=True)


# 右側：更新履歴
with right_col:
    st.markdown("""
    <div class="update-box">
      <h4>ver 1.0 (2025/xx/xx)</h4>
      <ul>
        <li>initial 4 function</li>
        <li>Help / Bug report button</li>
      </ul>
    </div>
    """, unsafe_allow_html=True)
