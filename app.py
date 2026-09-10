import io
import re
import queue
import av
import cv2
import numpy as np
import streamlit as st
from PIL import Image
from streamlit_webrtc import webrtc_streamer, WebRtcMode
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ==========================================
# KONFIGURASI HALAMAN & CSS
# ==========================================
st.set_page_config(page_title="DocuFlow", page_icon="📄", layout="centered")

# Menggunakan CSS untuk membuat tampilan lebih clean
st.markdown(
    """
    <style>
    /* Menyembunyikan tombol header bawaan Streamlit untuk kesan rapi */
    header {visibility: hidden;}
    
    /* Tombol Utama */
    .stButton > button {
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    /* Container untuk mode kamera agar terasa penuh */
    .camera-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        width: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================================
# FUNGSI GOOGLE DRIVE
# ==========================================
def get_drive_folders(drive_service):
    results = drive_service.files().list(
        q="mimeType='application/vnd.google-apps.folder' and trashed=false",
        spaces="drive",
        fields="files(id, name, parents)",
        orderBy="name"
    ).execute()
    return results.get("files", [])

def create_drive_folder(drive_service, folder_name, parent_id=None):
    folder_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder"
    }
    if parent_id and parent_id != "root":
        folder_metadata["parents"] = [parent_id]
        
    return drive_service.files().create(
        body=folder_metadata,
        fields="id, name, parents"
    ).execute()

# ==========================================
# 1. INISIALISASI STATE
# ==========================================
if "daftar_foto" not in st.session_state:
    st.session_state.daftar_foto = []
if "kamera_key" not in st.session_state:
    st.session_state.kamera_key = 0
if "halaman_aktif" not in st.session_state:
    st.session_state.halaman_aktif = "UTAMA"
if "foto_sementara" not in st.session_state:
    st.session_state.foto_sementara = None

# ==========================================
# 2. LOGIN & KONEKSI
# ==========================================
if not st.user.is_logged_in:
    st.title("📄 DocuFlow")
    st.write("Scan dokumen dan simpan langsung ke Google Drive kamu.")
    if st.button("🔐 Login dengan Google", use_container_width=True):
        st.login()
    st.stop()

try:
    access_token = st.user.tokens["access"]
    credentials = Credentials(token=access_token)
    drive_service = build("drive", "v3", credentials=credentials, cache_discovery=False)
except Exception:
    st.error("Sesi Google tidak valid. Silakan login kembali.")
    if st.button("Logout"):
        st.logout()
    st.stop()


# ==========================================
# 3. KONTROL HALAMAN UTAMA (DASHBOARD)
# ==========================================
if st.session_state.halaman_aktif == "UTAMA":
    col_kiri, col_kanan = st.columns([3, 1])
    with col_kiri:
        st.title("📄 DocuFlow")
    with col_kanan:
        st.write("")
        if st.button("Logout", key="btn_logout"):
            st.logout()

    jumlah_jepretan = len(st.session_state.daftar_foto)
    
    st.markdown(f"**Tersimpan:** {jumlah_jepretan} / 5 halaman")

    # --- TOMBOL MENUJU KAMERA ---
    if jumlah_jepretan < 5:
        if st.button("📸 BUKA KAMERA & SCAN", type="primary", use_container_width=True):
            st.session_state.halaman_aktif = "KAMERA"
            st.rerun()
    else:
        st.warning("Batas maksimal dokumen tercapai.")
    
    st.divider()

    # --- PENGATURAN DRIVE & UPLOAD ---
    st.subheader("Pengaturan Penyimpanan")
    
    if "daftar_folder_drive" not in st.session_state:
        st.session_state.daftar_folder_drive = get_drive_folders(drive_service)
        
    folder_options = {"📂 My Drive": "root"}
    for folder in st.session_state.daftar_folder_drive:
        folder_options[f"📁 {folder['name']}"] = folder["id"]
        
    selected_folder_name = st.selectbox("Lokasi Folder:", list(folder_options.keys()))
    selected_folder_id = folder_options[selected_folder_name]

    file_name = st.text_input("Nama Dokumen:", value="Scan_Dokumen_Baru")

    if jumlah_jepretan > 0:
        if st.button("📤 SIMPAN KE GOOGLE DRIVE", use_container_width=True):
            # Proses Upload
            with st.spinner("Menggabungkan & Mengunggah..."):
                rgb_images = [foto.convert("RGB") for foto in st.session_state.daftar_foto]
                pdf_bytes = io.BytesIO()
                rgb_images[0].save(pdf_bytes, format="PDF", save_all=True, append_images=rgb_images[1:])
                pdf_bytes.seek(0)
                
                # Cek Tahun
                upload_target_id = selected_folder_id
                match_tahun = re.search(r'\b(19|20)\d{2}\b', file_name)
                
                if match_tahun:
                    tahun = match_tahun.group(0)
                    year_folders = drive_service.files().list(
                        q=f"name='{tahun}' and mimeType='application/vnd.google-apps.folder' and '{selected_folder_id}' in parents and trashed=false",
                        fields="files(id)"
                    ).execute().get("files", [])
                    
                    if year_folders:
                        upload_target_id = year_folders[0]["id"]
                    else:
                        new_folder = create_drive_folder(drive_service, tahun, selected_folder_id)
                        upload_target_id = new_folder["id"]

                file_metadata = {"name": f"{file_name}.pdf", "parents": [upload_target_id]}
                media = MediaIoBaseUpload(pdf_bytes, mimetype="application/pdf", resumable=True)
                uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields="id, webViewLink").execute()
                
            st.success("Berhasil disimpan!")
            if uploaded_file.get("webViewLink"):
                st.link_button("Buka di Drive", uploaded_file["webViewLink"])
                
            if st.button("Scan Dokumen Baru"):
                st.session_state.daftar_foto = []
                st.session_state.kamera_key += 1
                st.rerun()

# ==========================================
# 4. KONTROL HALAMAN KAMERA
# ==========================================
elif st.session_state.halaman_aktif == "KAMERA":
    st.markdown("<h3 style='text-align: center;'>Arahkan ke Dokumen</h3>", unsafe_allow_html=True)
    
    if "frame_queue" not in st.session_state:
        st.session_state.frame_queue = queue.Queue(maxsize=1)

    def video_frame_callback(frame: av.VideoFrame) -> av.VideoFrame:
        image = frame.to_ndarray(format="bgr24")
        try:
            if st.session_state.frame_queue.full():
                st.session_state.frame_queue.get_nowait()
            st.session_state.frame_queue.put_nowait(image.copy())
        except queue.Empty:
            pass
        except queue.Full:
            pass
        return av.VideoFrame.from_ndarray(image, format="bgr24")

    # Komponen WebRTC
    webrtc_ctx = webrtc_streamer(
        key=f"kamera_{st.session_state.kamera_key}",
        mode=WebRtcMode.SENDRECV,
        video_frame_callback=video_frame_callback,
        media_stream_constraints={"video": {"facingMode": {"ideal": "environment"}}, "audio": False},
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_toggle_controls=False,
    )

    if webrtc_ctx.state.playing:
        if st.button("⚪ AMBIL FOTO", type="primary", use_container_width=True):
            try:
                foto_bgr = st.session_state.frame_queue.get_nowait()
                foto_rgb = cv2.cvtColor(foto_bgr, cv2.COLOR_BGR2RGB)
                st.session_state.foto_sementara = Image.fromarray(foto_rgb)
                
                # Pindah ke layar preview
                st.session_state.halaman_aktif = "PREVIEW"
                st.rerun()
            except queue.Empty:
                st.warning("Kamera memuat, tunggu sebentar.")

    if st.button("Batal & Kembali", use_container_width=True):
        st.session_state.halaman_aktif = "UTAMA"
        st.session_state.kamera_key += 1 # Reset kamera
        st.rerun()

# ==========================================
# 5. KONTROL HALAMAN PREVIEW FOTO
# ==========================================
elif st.session_state.halaman_aktif == "PREVIEW":
    st.markdown("<h3 style='text-align: center;'>Hasil Jepretan</h3>", unsafe_allow_html=True)
    
    if st.session_state.foto_sementara:
        st.image(st.session_state.foto_sementara, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Ulangi Foto", use_container_width=True):
                st.session_state.foto_sementara = None
                st.session_state.halaman_aktif = "KAMERA"
                st.session_state.kamera_key += 1
                st.rerun()
        with col2:
            if st.button("✅ Simpan Halaman", type="primary", use_container_width=True):
                st.session_state.daftar_foto.append(st.session_state.foto_sementara)
                st.session_state.foto_sementara = None
                st.session_state.halaman_aktif = "UTAMA"
                st.session_state.kamera_key += 1
                st.rerun()
    else:
        st.error("Tidak ada foto ditemukan.")
        if st.button("Kembali"):
            st.session_state.halaman_aktif = "UTAMA"
            st.rerun()