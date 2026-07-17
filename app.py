import streamlit as st
import pandas as pd
import os
import base64
import time
import asyncio
from datetime import datetime, timedelta
from gtts import gTTS
import edge_tts

st.set_page_config(page_title="Hệ thống thông báo thu tiền", page_icon="💰", layout="centered")
st.title("Hệ thống thông báo thu tiền tự động")

# 1. Cấu hình chọn giọng đọc trên giao diện
st.sidebar.header("⚙️ Cấu hình giọng đọc")
voice_option = st.sidebar.selectbox(
    "Chọn giọng đọc:",
    options=["Chị Google (mặc định)", "Nữ (Giọng miền Nam)", "Nam (Giọng miền Nam)"],
    index=0
)

# Ánh xạ giọng đọc cho Edge-TTS
VOICE_MAP = {
    "Nữ (Giọng miền Nam)": "vi-VN-HoaiMyNeural",
    "Nam (Giọng miền Nam)": "vi-VN-NamMinhNeural"
}

def clean_amount_for_speech(amount_val):
    """Quy đổi toàn bộ số tiền sang đơn vị tỷ đồng (Kể cả < 1 tỷ sẽ đọc là 0 phẩy... tỷ)"""
    try:
        clean_val = str(amount_val).replace(",", "").strip()
        num = float(clean_val)
        if num == 0: 
            return "0 tỷ đồng"
        
        # Quy đổi ra đơn vị tỷ
        ty_val = num / 1_000_000_000
        
        # Làm tròn đến tối đa 3 chữ số thập phân để tránh đọc số lẻ quá dài
        ty_rounded = round(ty_val, 3)
        
        # Chuyển đổi dấu chấm thập phân thành chữ để công cụ TTS đọc đúng từ "phẩy"
        ty_str = str(ty_rounded)
        if "." in ty_str:
            nguyen, thap_phan = ty_str.split(".")
            # Loại bỏ số 0 thừa ở cuối phần thập phân
            thap_phan = thap_phan.rstrip("0")
            
            if thap_phan:
                speech_text = f"{nguyen} phẩy {thap_phan} tỷ đồng"
            else:
                speech_text = f"{nguyen} tỷ đồng"
        else:
            speech_text = f"{ty_str} tỷ đồng"
            
        return speech_text
    except:
        return str(amount_val)

# Hàm bất đồng bộ xử lý chuyển văn bản thành âm thanh qua Edge-TTS (Đã tích hợp giảm tốc độ đọc)
async def generate_edge_tts(text, voice, output_file):
    # rate="-15%" giúp giảm tốc độ đọc đi 15% so với bình thường để nghe số tiền rõ ràng hơn
    communicate = edge_tts.Communicate(text, voice, rate="-15%")
    await communicate.save(output_file)

def play_combined_audio(text_list, selected_option):
    """Gom dữ liệu văn bản thành 1 file MP3 và phát trên trình duyệt dựa theo cấu hình đã chọn"""
    if not text_list:
        return
    
    full_text = ", , ".join(text_list)
    temp_file = "temp_voice.mp3"
    
    try:
        # Xử lý tạo file âm thanh tùy theo tùy chọn được chọn
        if selected_option == "Chị Google (mặc định)":
            tts = gTTS(text=full_text, lang='vi', slow=False)
            tts.save(temp_file)
        else:
            voice_code = VOICE_MAP[selected_option]
            asyncio.run(generate_edge_tts(full_text, voice_code, temp_file))
        
        with open(temp_file, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            
            # Sử dụng HTML5 audio kết hợp Javascript để ép trình duyệt autoplay
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
                            console.log("Autoplay bị chặn bởi trình duyệt:", error);
                        }});
                    }}
                </script>
            """
            st.markdown(audio_html, unsafe_allow_html=True)
            
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        # Tăng thời gian chờ lên một chút (0.6 giây / 1 từ) vì tốc độ đọc đã được giảm xuống
        estimated_seconds = max(5, int(len(full_text.split()) * 0.6))
        
        with st.spinner(f"🔊 Đang phát thông báo bằng {selected_option}..."):
            time.sleep(estimated_seconds)
            
    except Exception as e:
        st.error(f"Lỗi khởi tạo giọng đọc: {e}")

# Khu vực quản lý dữ liệu file Excel
uploaded_file = st.file_uploader("Kéo thả hoặc chọn file Excel dữ liệu mới tại đây (.xlsx)", type=["xlsx"])

df = None

# CHỈ xử lý hiển thị khi người dùng tải file mới lên
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.info("🔄 Đang hiển thị dữ liệu từ file bạn vừa tải lên:")
else:
    st.warning("Chưa có dữ liệu mới được tải lên. Vui lòng kéo thả file Excel vào để bắt đầu.")

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
                total_amt = 0  # Biến lưu tổng số tiền thu được
                
                # Duyệt qua các dòng dữ liệu chưa đọc
                for index, row in unread_rows.iterrows():
                    team_val = str(row["team"]).strip()
                    user_val = str(row["user"]).strip()
                    
                    # Cộng dồn giá trị số tiền của dòng hiện tại
                    try:
                        amt_val = float(str(row["amt"]).replace(",", "").strip())
                        total_amt += amt_val
                    except:
                        pass
                    
                    amt_speech = clean_amount_for_speech(row["amt"])
                    sentence = f"{team_val}, {user_val} đã thu {amt_speech}"
                    
                    sentences_to_speak.append(sentence)
                    st.success(f"✓ Đã duyệt: {sentence}")
                    
                    # Đổi trạng thái trực tiếp trên bộ nhớ giao diện
                    df.at[index, "status"] = 1
                
                # Tính toán ngày T-1 (hôm qua)
                yesterday = datetime.now() - timedelta(days=1)
                date_str = f"ngày {yesterday.day} tháng {yesterday.month} năm {yesterday.year}"
                
                # Thêm câu thông báo tổng số tiền thu ngày T-1 vào cuối danh sách đọc
                total_speech = clean_amount_for_speech(total_amt)
                total_sentence = f"Tổng số thu {date_str} là {total_speech}"
                sentences_to_speak.append(total_sentence)
                st.info(f"📊 {total_sentence}")
                
                # Gọi hàm phát âm thanh với cấu hình tùy chọn giọng
                play_combined_audio(sentences_to_speak, voice_option)
                
                # Cập nhật và làm sạch phiên hoạt động
                st.session_state["updated_df"] = df
                st.rerun()
            else:
                st.toast("Không có dữ liệu mới (status = 0) cần phát âm thanh!")

if "updated_df" in st.session_state:
    st.success("✓ Đã xử lý và thông báo xong toàn bộ danh sách dữ liệu mới.")
