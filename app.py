import streamlit as st
import pandas as pd
from gtts import gTTS
import os
import base64

st.set_page_config(page_title="Hệ thống thông báo thu tiền", page_icon="💰", layout="centered")

st.title("Hệ thống thông báo thu tiền tự động")

def clean_amount_for_speech(amount_val):
    try:
        clean_val = str(amount_val).replace(",", "").strip()
        num = int(float(clean_val))
        if num == 0: return "0 đồng"
        trieu = num // 1_000_000
        nghin = (num % 1_000_000) // 1_000
        dong = num % 1_000
        speech_text = ""
        if trieu > 0: speech_text += f"{trieu} triệu "
        if nghin > 0: speech_text += f"{nghin} nghìn "
        if dong > 0: speech_text += f"{dong} đồng"
        return speech_text.strip()
    except:
        return str(amount_val)

def autoplay_audio(text):
    """Tạo thẻ HTML audio tự động phát âm thanh trên trình duyệt người dùng"""
    tts = gTTS(text=text, lang='vi', slow=False)
    temp_file = "temp.mp3"
    tts.save(temp_file)
    
    with open(temp_file, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f"""
            <audio autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)
    os.remove(temp_file)

# ---- CHỨC NĂNG TẢI FILE TRỰC TIẾP TRÊN WEB ----
uploaded_file = st.file_uploader("Kéo thả hoặc chọn file Excel dữ liệu mới tại đây (.xlsx)", type=["xlsx"])

# Nếu người dùng tải file lên web, sử dụng file đó. Nếu không, dùng file mặc định data.xlsx
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.info("🔄 Đang hiển thị dữ liệu từ file bạn vừa tải lên:")
else:
    if os.path.exists("data.xlsx"):
        df = pd.read_excel("data.xlsx")
        st.info("📂 Đang hiển thị dữ liệu mặc định hệ thống:")
    else:
        df = None
        st.warning("Chưa có dữ liệu. Vui lòng tải file Excel lên hệ thống.")

if df is not None:
    # Hiển thị bảng dữ liệu lên giao diện
    st.dataframe(df, use_container_width=True)

    # Nút xử lý phát âm thanh
    if st.button("Kiểm tra dữ liệu & Phát âm thanh mới", type="primary"):
        required_cols = ["team", "user", "amt", "status"]
        if not all(col in df.columns for col in required_cols):
            st.error(f"Sai cấu trúc cột! File cần có đủ các cột: {required_cols}")
        else:
            df["status"] = pd.to_numeric(df["status"], errors='coerce').fillna(-1).astype(int)
            unread_rows = df[df["status"] == 0]
            
            if not unread_rows.empty:
                for index, row in unread_rows.iterrows():
                    team_val = str(row["team"]).strip()
                    user_val = str(row["user"]).strip()
                    amt_speech = clean_amount_for_speech(row["amt"])
                    sentence = f"{team_val} {user_val} đã thu {amt_speech}"
                    
                    st.success(f"🔊 Đang phát: {sentence}")
                    autoplay_audio(sentence)
                    
                    # Cập nhật tạm thời trạng thái thành 1 trong phiên làm việc hiện tại
                    df.at[index, "status"] = 1
                
                # Hiển thị lại bảng sau khi đã xử lý xong âm thanh
                st.rerun()
            else:
                st.toast("Không có dữ liệu mới (status = 0) cần phát âm thanh!")
