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
    """Gom toàn bộ nội dung thành 1 file âm thanh và ép trình duyệt phát hết không ngắt quãng"""
    if not text_list:
        return
    
    # Nối các câu lại, tạo khoảng nghỉ ngắn bằng dấu chấm và dấu phẩy
    full_text = ", , ".join(text_list)
    
    try:
        tts = gTTS(text=full_text, lang='vi', slow=False)
        temp_file = "temp_all.mp3"
        tts.save(temp_file)
        
        with open(temp_file, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            
            # Sử dụng Audio Context qua thẻ HTML cố định để tránh bị Streamlit Rerun làm mất hiệu lực phát
            audio_html = f"""
                <div id="audio-player-container">
                    <audio id="speech-audio" autoplay>
                        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                    </audio>
                </div>
                <script>
                    var audio = document.getElementById('speech-audio');
                    if(audio) {{
                        audio.play().catch(function(error) {{
                            console.log("Chặn autoplay từ trình duyệt:", error);
                        }});
                    }}
                </script>
            """
            st.markdown(audio_html, unsafe_allow_html=True)
            
        os.remove(temp_file)
        
        # Tự động tính toán thời gian chờ dựa trên độ dài văn bản (tránh tắt giao diện quá sớm)
        # Trung bình 1 từ tiếng Việt đọc hết khoảng 0.4 giây. Cần tối thiểu 4 giây để khởi tạo.
        estimated_seconds = max(4, int(len(full_text.split()) * 0.45))
        
        with st.spinner(f"🔊 Hệ thống đang đọc thông báo (Vui lòng chờ trong {estimated_seconds} giây)..."):
            time.sleep(estimated_seconds)
            
    except Exception as e:
        st.error(f"Lỗi tạo âm thanh: {e}")

# Khu vực tải file dữ liệu
uploaded_file = st.file_uploader("Kéo thả hoặc chọn file Excel dữ liệu mới tại đây (.xlsx)", type=["xlsx"])

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
                
                # Thu thập toàn bộ danh sách nội dung cần đọc
                for index, row in unread_rows.iterrows():
                    team_val = str(row["team"]).strip()
                    user_val = str(row["user"]).strip()
                    amt_speech = clean_amount_for_speech(row["amt"])
                    sentence = f"{team_val}, {user_val} đã thu {amt_speech}"
                    
                    sentences_to_speak.append(sentence)
                    st.success(f"✓ Đã duyệt: {sentence}")
                    
                    # Cập nhật trạng thái dòng dữ liệu thành 1
                    df.at[index, "status"] = 1
                
                # Tiến hành phát toàn bộ danh sách câu gom cụm
                play_combined_audio(sentences_to_speak)
                
                # Lưu trạng thái mới vào bộ nhớ tạm thời và làm mới giao diện
                st.session_state["updated_df"] = df
                st.rerun()
            else:
                st.toast("Không có dữ liệu mới (status = 0) cần phát âm thanh!")

if "updated_df" in st.session_state:
    st.success("✓ Đã xử lý và thông báo xong toàn bộ danh sách dữ liệu mới.")
