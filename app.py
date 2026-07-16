import streamlit as st
import pandas as pd
from gtts import gTTS
import os
import base64

st.title("Hệ thống thông báo thu tiền tự động")

EXCEL_FILE = "data.xlsx"

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
    tts.save("temp.mp3")

    with open("temp.mp3", "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        # Tạo thẻ audio tự động phát (autoplay)
        md = f"""
            <audio autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)
    os.remove("temp.mp3")

if os.path.exists(EXCEL_FILE):
    df = pd.read_excel(EXCEL_FILE)
    st.dataframe(df) # Hiển thị bảng Excel trực tiếp lên trang web

    # Nút bấm thủ công hoặc bạn có thể thiết lập tự động reload
    if st.button("Kiểm tra dữ liệu & Phát âm thanh mới"):
        df["status"] = pd.to_numeric(df["status"], errors='coerce').fillna(-1).astype(int)
        unread_rows = df[df["status"] == 0]

        if not unread_rows.empty:
            for index, row in unread_rows.iterrows():
                team_val = str(row["team"]).strip()
                user_val = str(row["user"]).strip()
                amt_speech = clean_amount_for_speech(row["amt"])
                sentence = f"{team_val} {user_val} đã thu {amt_speech}"

                st.success(f"Đang phát: {sentence}")
                autoplay_audio(sentence)

                df.at[index, "status"] = 1

            df.to_excel(EXCEL_FILE, index=False)
            st.rerun()
        else:
            st.info("Không có dữ liệu mới cần phát.")
else:
    st.error("Chưa tìm thấy file data.xlsx")