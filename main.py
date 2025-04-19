import streamlit as st
import base64
import os

# ページ設定
st.set_page_config(
    page_title="ITSツールメニュー",
    page_icon="📂",
    initial_sidebar_state="collapsed",
    layout="wide"
)

st.title("📂 Converter&Viewer warehouse")
st.write("画像をクリックして各ツールページに移動できます。")

# Base64エンコード関数（画像パスは fig/ ディレクトリ内）
def get_base64_of_bin_file(bin_file_path):
    with open(bin_file_path, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# 表示するツールリストと画像パス
tools = [
    {
        "label": "📊 sensor correlation",
        "href": "/sensor_correlation", 
        "image": "fig/1.png"
    },
    {
        "label": "📈 pTAT Viewer",
        "href": "/pTAT_viewer_Pyplot_Plotly", 
        "image": "fig/2.png"
    },
    {
        "label": "📈 DTT Viewer",
        "href": "/DTT_viewer_Pyplot_Plotly",
        "image": "fig/3.png"
    },
    {
        "label": "📈 converter",
        "href": "/converter",
        "image": "fig/4.png"
    }
]

# 3列レイアウトで表示
cols = st.columns(4)

for i, tool in enumerate(tools):
    with cols[i % 3]:
        if os.path.exists(tool["image"]):
            image_base64 = get_base64_of_bin_file(tool["image"])
            st.markdown(
                f"""
                <a href="{tool['href']}" target="_self">
                    <img src="data:image/png;base64,{image_base64}" width="250" style="border-radius:10px;"/>
                </a>
                <p style="text-align:center;">{tool['label']}</p>
                """,
                unsafe_allow_html=True
            )
        else:
            st.error(f"画像が見つかりません: {tool['image']}")
