import streamlit as st
import pandas as pd
from gtts import gTTS
import os
import base64
import time

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

def play_combined_audio(text_list):
    """Gom toàn bộ nội dung thành 1 file duy nhất và phát để tránh bị ngắt quãng"""
    if not text_list:
        return
    
    # Nối các câu lại với nhau, nghỉ 1 chút giữa các câu bằng dấu phẩy hoặc chấm
    full_text = " . Ngắt câu . ".join(text_list)
    
    try:
        tts = gTTS(text=full_text, lang='vi', slow=False)
        temp_file = "temp_all.mp3"
        tts.save(temp_file)
        
        with open(temp_file, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            
            # Sử dụng HTML5 chuẩn để tự động phát
            md = f"""
                <audio autoplay="true" style="display:none;">
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                </audio>
                """
            st.markdown(md, unsafe_allow_html=True)
            
        os.remove(temp_file)
        # Cho trình duyệt 2 giây để tải và bắt đầu phát trước khi thực hiện hành động khác
        time.sleep(2) 
    except Exception as e:
        st.error(f"Lỗi tạo âm thanh: {e}")

# Khu vực tải file
uploaded_file = st.file_uploader("Kéo thả hoặc chọn file Excel dữ liệu mới tại đây (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.info("🔄 Dạng dữ liệu từ file bạn vừa tải lên:")
else:
    if os.path.exists("data.xlsx"):
        df = pd.read_excel("data.xlsx")
        st.info("📂 Dạng dữ liệu mặc định hệ thống:")
    else:
        df = None
        st.warning("Chưa có dữ liệu. Vui lòng tải file Excel lên hệ thống.")

if df is not None:
    st.dataframe(df, use_container_width=True)

    if st.button("Kiểm tra dữ liệu & Phát âm thanh mới", type="primary"):
        required_cols = ["team", "user", "amt", "status"]
        if not all(col in df.columns for col in required_cols):
            st.error(f"Sai cấu trúc cột! File cần có đủ các cột: {required_cols}")
        else:
            df["status"] = pd.to_numeric(df["status"], errors='coerce').fillna(-1).astype(int)
            unread_rows = df[df["status"] == 0]
            
            if not unread_rows.empty:
                sentences_to_speak = []
                
                # Bước 1: Thu thập toàn bộ các câu cần đọc
                for index, row in unread_rows.iterrows():
                    team_val = str(row["team"]).strip()
                    user_val = str(row["user"]).strip()
                    amt_speech = clean_amount_for_speech(row["amt"])
                    sentence = f"{team_val} {user_val} đã thu {amt_speech}"
                    
                    sentences_to_speak.append(sentence)
                    st.success(f"🔊 Chuẩn bị phát: {sentence}")
                    
                    # Cập nhật trạng thái
                    df.at[index, "status"] = 1
                
                # Bước 2: Phát toàn bộ danh sách câu cùng một lúc
                play_combined_audio(sentences_to_speak)
                
                # Lưu ý: Vì Streamlit Cloud chạy online không thể lưu trực tiếp vào file Excel của bạn trên máy tính,
                # trạng thái thay đổi tạm thời sẽ hiển thị trên màn hình sau khi st.rerun()
                st.session_state["updated_df"] = df
                st.rerun()
            else:
                st.toast("Không có dữ liệu mới (status = 0) cần phát âm thanh!")

# Hiển thị lại bảng dữ liệu đã cập nhật nếu có
if "updated_df" in st.session_state:
    st.success("✓ Đã xử lý xong các dòng dữ liệu mới.")
