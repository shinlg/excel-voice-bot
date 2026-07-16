import streamlit as st
import pandas as pd
import os
import base64
import time
import asyncio
import edge_tts

st.set_page_config(page_title="Hệ thống thông báo thu tiền", page_icon="💰", layout="centered")
st.title("Hệ thống thông báo thu tiền tự động")

# 1. Cấu hình chọn giọng đọc trên giao diện
st.sidebar.header("⚙️ Cấu hình giọng đọc")
voice_option = st.sidebar.selectbox(
    "Chọn giọng đọc:",
    options=["Nam (Giọng miền Nam)", "Nữ (Giọng miền Bắc)"],
    index=0
)

# Ánh xạ chuẩn xác theo thực tế phát âm của Microsoft Edge TTS mới nhất
VOICE_MAP = {
    "Nam (Giọng miền Nam)": "vi-VN-NamMinhNeural",  # Giọng Nam, miền Nam
    "Nữ (Giọng miền Bắc)": "vi-VN-HoaiMyNeural"     # Sửa thành HoaiMyNeural (Giọng Nữ, miền Bắc hoạt động ổn định)
}
selected_voice = VOICE_MAP[voice_option]

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

# Hàm bất đồng bộ xử lý chuyển văn bản thành âm thanh qua Edge-TTS
async def generate_edge_tts(text, voice, output_file):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def play_combined_audio(text_list, voice, voice_display_name):
    """Gom dữ liệu văn bản thành 1 file MP3 bằng Edge-TTS và phát trên trình duyệt"""
    if not text_list:
        return
    
    full_text = ", , ".join(text_list)
    temp_file = "temp_edge_tts.mp3"
    
    try:
        # Chạy hàm bất đồng bộ sinh file âm thanh
        asyncio.run(generate_edge_tts(full_text, voice, temp_file))
        
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
        
        # Tự động tính thời gian dừng dựa trên số lượng từ (khoảng 0.5 giây / 1 từ)
        estimated_seconds = max(4, int(len(full_text.split()) * 0.5))
        
        with st.spinner(f"🔊 Đang phát thông báo bằng {voice_display_name}..."):
            time.sleep(estimated_seconds)
            
    except Exception as e:
        st.error(f"Lỗi khởi tạo giọng đọc Edge-TTS: {e}")

# Khu vực quản lý dữ liệu file Excel
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
                
                for index, row in unread_rows.iterrows():
                    team_val = str(row["team"]).strip()
                    user_val = str(row["user"]).strip()
                    amt_speech = clean_amount_for_speech(row["amt"])
                    sentence = f"{team_val}, {user_val} đã thu {amt_speech}"
                    
                    sentences_to_speak.append(sentence)
                    st.success(f"✓ Đã duyệt: {sentence}")
                    
                    # Đổi trạng thái trực tiếp trên bộ nhớ giao diện
                    df.at[index, "status"] = 1
                
                # Gọi hàm phát âm thanh
                play_combined_audio(sentences_to_speak, selected_voice, voice_option)
                
                # Cập nhật và làm sạch phiên hoạt động
                st.session_state["updated_df"] = df
                st.rerun()
            else:
                st.toast("Không có dữ liệu mới (status = 0) cần phát âm thanh!")

if "updated_df" in st.session_state:
    st.success("✓ Đã xử lý và thông báo xong toàn bộ danh sách dữ liệu mới.")
