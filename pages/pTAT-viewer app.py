import streamlit as st
import pandas as pd
import os

# ===== CSV를 다양한 인코딩으로 읽어 UTF-8로 저장 =====
def convert_to_utf8_csv(input_path):
    filename, ext = os.path.splitext(input_path)
    output_file = filename + '_utf8.csv'
    encodings = ['utf-8-sig', 'utf-8', 'cp932', 'shift_jis']

    for enc in encodings:
        try:
            # 2행을 열 이름으로 사용
            df = pd.read_csv(input_path, encoding=enc, header=1)
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"✅ 인코딩 변환 성공: {enc}")
            return output_file
        except Exception:
            continue

    return None

# ===== 업로드된 파일을 UTF-8로 변환하고 DataFrame으로 로드 =====
@st.cache_data
def load_csv_and_convert(uploaded_file):
    temp_path = f"temp_{uploaded_file.name}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.read())

    converted_path = convert_to_utf8_csv(temp_path)
    if converted_path is None:
        st.error("❌ CSVのインコーディング変換に失敗しました。")
        st.stop()

    df = pd.read_csv(converted_path, encoding='utf-8-sig')
    return df

# ===== Streamlit UI 시작 =====
st.set_page_config(layout="wide")
st.title("📊 CSV 업로드 + 인코딩 자동 변환")

# ===== 파일 업로드 =====
uploaded_file = st.file_uploader("💾 CSVファイルをアップロード", type="csv")
if uploaded_file is not None:
    df = load_csv_and_convert(uploaded_file)

    st.success("✅ CSVファイルを正常に読み込みました（UTF-8変換済み）")
    st.write("📋 データプレビュー:")
    st.dataframe(df.head())

    # ===== Time 열 자동 감지 및 변환 =====
    time_col = None
    for col in df.columns:
        if col.strip().lower() == "time":
            time_col = col
            break

    if time_col:
        try:
            df[time_col] = pd.to_datetime(df[time_col])
            df[time_col] = df[time_col].dt.strftime("%H:%M:%S")
            st.success(f"🕒 '{time_col}' 열을 시:분:초 형식으로 변환했습니다。")
        except Exception as e:
            st.warning(f"⚠️ 時間変換失敗: {e}")

        st.dataframe(df[[time_col]].head())
    else:
        st.warning("⚠️ 'Time' 열이存在하지 않습니다。")
else:
    st.info("⬆ CSVファイルをアップロードしてください。")
