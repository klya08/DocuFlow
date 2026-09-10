import io
import re
import base64
import cv2
import numpy as np
import streamlit as st

from PIL import Image, ImageOps, ImageEnhance

from camera_component import camera

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


# ==========================================
# FUNGSI GOOGLE DRIVE - FOLDER
# ==========================================
def get_drive_folders(drive_service):
    """Mengambil daftar folder dari Google Drive user."""
    results = drive_service.files().list(
        q="mimeType='application/vnd.google-apps.folder' and trashed=false",
        spaces="drive",
        fields="files(id, name, parents)",
        orderBy="name"
    ).execute()

    return results.get("files", [])


def create_drive_folder(drive_service, folder_name, parent_id=None):
    """Membuat folder baru di Google Drive."""
    folder_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder"
    }

    # Jika ada folder induk
    if parent_id and parent_id != "root":
        folder_metadata["parents"] = [parent_id]

    folder = drive_service.files().create(
        body=folder_metadata,
        fields="id, name, parents"
    ).execute()

    return folder


# ==========================================
# FUNGSI PEMOTONG OTOMATIS (CROP)
# ==========================================
def potong_dokumen_otomatis(image):
    """Mendeteksi tepi kertas dan meluruskannya secara otomatis."""

    # 1. Ubah gambar ke array OpenCV
    img_array = np.array(image)

    # 2. Grayscale
    gray = cv2.cvtColor(
        img_array,
        cv2.COLOR_RGB2GRAY
    )

    # 3. Blur
    blur = cv2.GaussianBlur(
        gray,
        (5, 5),
        0
    )

    # 4. Deteksi tepi
    edged = cv2.Canny(
        blur,
        75,
        200
    )

    # 5. Cari kontur
    contours, _ = cv2.findContours(
        edged,
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE
    )

    contours = sorted(
        contours,
        key=cv2.contourArea,
        reverse=True
    )[:5]

    dokumen_contour = None

    for c in contours:

        peri = cv2.arcLength(
            c,
            True
        )

        approx = cv2.approxPolyDP(
            c,
            0.02 * peri,
            True
        )

        if len(approx) == 4:
            dokumen_contour = approx
            break

    # ==========================================
    # JIKA DOKUMEN DITEMUKAN
    # ==========================================

    if dokumen_contour is not None:

        pts = dokumen_contour.reshape(
            4,
            2
        )

        rect = np.zeros(
            (4, 2),
            dtype="float32"
        )

        s = pts.sum(axis=1)

        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        diff = np.diff(
            pts,
            axis=1
        )

        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        (tl, tr, br, bl) = rect

        widthA = np.sqrt(
            ((br[0] - bl[0]) ** 2)
            +
            ((br[1] - bl[1]) ** 2)
        )

        widthB = np.sqrt(
            ((tr[0] - tl[0]) ** 2)
            +
            ((tr[1] - tl[1]) ** 2)
        )

        maxWidth = max(
            int(widthA),
            int(widthB)
        )

        heightA = np.sqrt(
            ((tr[0] - br[0]) ** 2)
            +
            ((tr[1] - br[1]) ** 2)
        )

        heightB = np.sqrt(
            ((tl[0] - bl[0]) ** 2)
            +
            ((tl[1] - bl[1]) ** 2)
        )

        maxHeight = max(
            int(heightA),
            int(heightB)
        )

        dst = np.array(
            [
                [0, 0],
                [maxWidth - 1, 0],
                [maxWidth - 1, maxHeight - 1],
                [0, maxHeight - 1]
            ],
            dtype="float32"
        )

        M = cv2.getPerspectiveTransform(
            rect,
            dst
        )

        warped = cv2.warpPerspective(
            img_array,
            M,
            (
                maxWidth,
                maxHeight
            )
        )

        return Image.fromarray(warped)

    # Jika gagal mendeteksi dokumen
    return image


# ==========================================
# KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(
    page_title="DocuFlow",
    page_icon="📄",
    layout="centered"
)


# ==========================================
# 1. LOGIN GOOGLE
# ==========================================
if not st.user.is_logged_in:

    st.title("📄 DocuFlow")

    st.write(
        "Scan dokumen dan simpan langsung "
        "ke Google Drive kamu."
    )

    st.info(
        "Silakan login dengan akun Google "
        "untuk mulai menggunakan DocuFlow."
    )

    if st.button(
        "🔐 Login dengan Google",
        use_container_width=True
    ):
        st.login()

    st.stop()


# ==========================================
# 2. USER SUDAH LOGIN
# ==========================================
st.title("📄 DocuFlow")

nama_user = st.user.get(
    "name",
    "Pengguna"
)

email_user = st.user.get(
    "email",
    ""
)

st.success(
    f"Halo, {nama_user}! 👋"
)

st.caption(
    f"Login sebagai: {email_user}"
)

if st.button("Logout"):
    st.logout()


# ==========================================
# 3. CEK ACCESS TOKEN GOOGLE
# ==========================================
try:

    access_token = st.user.tokens["access"]

except Exception:

    access_token = None


if not access_token:

    st.error(
        "Access token Google tidak tersedia. "
        "Pastikan expose_tokens = [\"access\"] "
        "sudah ada di secrets.toml."
    )

    st.stop()


# ==========================================
# 4. MEMBUAT KONEKSI GOOGLE DRIVE
# ==========================================
try:

    credentials = Credentials(
        token=access_token
    )

    drive_service = build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False
    )

except Exception as e:

    st.error(
        f"Gagal menghubungkan ke Google Drive: {e}"
    )

    st.stop()


# ==========================================
# 5. PILIH / BUAT FOLDER PENYIMPANAN
# ==========================================
st.subheader(
    "📁 Folder Penyimpanan"
)

try:

    if "daftar_folder_drive" not in st.session_state:

        try:

            st.session_state.daftar_folder_drive = (
                get_drive_folders(
                    drive_service
                )
            )

        except Exception as drive_error:

            error_text = str(
                drive_error
            ).lower()

            if (
                "refresh_token" in error_text
                or "credentials do not contain" in error_text
                or "invalid_grant" in error_text
                or "401" in error_text
                or "unauthorized" in error_text
            ):

                st.error(
                    "🔐 Sesi Google sudah kedaluwarsa. "
                    "Silakan logout lalu login kembali "
                    "dengan Google."
                )

                if st.button(
                    "🔄 Login Google Lagi"
                ):
                    st.logout()

                st.stop()

            raise drive_error

    folders = (
        st.session_state.daftar_folder_drive
    )

    # Folder utama
    folder_options = {
        "📂 My Drive": "root"
    }

    # Folder milik user
    for folder in folders:

        folder_options[
            f"📁 {folder['name']}"
        ] = folder["id"]

    selected_folder_name = st.selectbox(
        "Pilih folder untuk menyimpan hasil scan:",
        list(folder_options.keys()),
        key="pilihan_folder_utama"
    )

    selected_folder_id = folder_options[
        st.session_state.pilihan_folder_utama
    ]

except Exception as e:

    st.error(
        f"Gagal mengambil folder Google Drive: {e}"
    )

    selected_folder_id = "root"


# ==========================================
# BUAT FOLDER BARU
# ==========================================
with st.expander(
    "➕ Buat Folder Baru"
):

    new_folder_name = st.text_input(
        "Nama folder baru",
        placeholder="Contoh: Dokumen Kuliah"
    )

    if st.button(
        "📁 Buat Folder",
        use_container_width=True
    ):

        if new_folder_name.strip():

            try:

                new_folder = create_drive_folder(
                    drive_service,
                    new_folder_name.strip()
                )

                st.session_state.daftar_folder_drive = (
                    get_drive_folders(
                        drive_service
                    )
                )

                st.success(
                    f"Folder '{new_folder['name']}' "
                    "berhasil dibuat! 🎉"
                )

                st.rerun()

            except Exception as e:

                st.error(
                    f"Gagal membuat folder: {e}"
                )

        else:

            st.warning(
                "Masukkan nama folder terlebih dahulu."
            )


# ==========================================
# 6. STATE MANAGEMENT
# ==========================================
if "daftar_foto" not in st.session_state:

    st.session_state.daftar_foto = []


if "kamera_key" not in st.session_state:

    st.session_state.kamera_key = 0


jumlah_sekarang = len(
    st.session_state.daftar_foto
)


st.info(
    f"Jumlah jepretan saat ini: "
    f"{jumlah_sekarang} / 5"
)


# ==========================================
# 7. ANTARMUKA KAMERA
# ==========================================
if jumlah_sekarang < 5:

    st.markdown(
        """
        <div style="
            text-align:center;
            font-size:18px;
            font-weight:600;
            margin-bottom:10px;
        ">
            📷 Arahkan kamera ke dokumen
        </div>
        """,
        unsafe_allow_html=True
    )

    # ==========================================
    # KAMERA CUSTOM
    # ==========================================

    captured_photo = camera(
        key=f"kamera_{st.session_state.kamera_key}"
    )

    # ==========================================
    # JIKA FOTO BERHASIL DIAMBIL
    # ==========================================

    if captured_photo is not None:

        try:

            # Hilangkan prefix base64
            image_data = captured_photo.split(
                ",",
                1
            )[1]

            # Decode gambar
            image_bytes = base64.b64decode(
                image_data
            )

            # Buka gambar
            img = Image.open(
                io.BytesIO(image_bytes)
            ).convert("RGB")

            # ==========================================
            # SIMPAN FOTO
            # ==========================================

            st.session_state.daftar_foto.append(
                img
            )

            # Ganti kamera
            st.session_state.kamera_key += 1

            st.success(
                f"✅ Halaman "
                f"{len(st.session_state.daftar_foto)} "
                "berhasil diambil!"
            )

            st.rerun()

        except Exception as e:

            st.error(
                f"❌ Gagal mengambil foto: {e}"
            )

else:

    st.warning(
        "Batas maksimal 5 foto per dokumen "
        "sudah tercapai!"
    )


# ==========================================
# 8. PREVIEW FOTO
# ==========================================
if jumlah_sekarang > 0:

    st.write(
        "### Preview Halaman Terpilih"
    )

    cols = st.columns(
        jumlah_sekarang
    )

    for i, foto in enumerate(
        st.session_state.daftar_foto
    ):

        cols[i].image(
            foto,
            caption=f"Halaman {i + 1}",
            use_container_width=True
        )

        if cols[i].button(
            "❌ Hapus",
            key=f"hapus_halaman_{i}",
            use_container_width=True
        ):

            st.session_state.daftar_foto.pop(i)

            st.rerun()


# ==========================================
# 9. PROSES PDF & UPLOAD KE DRIVE
# ==========================================
if jumlah_sekarang >= 2:

    st.divider()

    file_name = st.text_input(
        "Beri nama file PDF:",
        value="Dokumen_Scan_DocuFlow"
    )

    if st.button(
        "📤 Proses & Upload ke Google Drive",
        use_container_width=True
    ):

        try:

            # ==========================================
            # GABUNGKAN GAMBAR MENJADI PDF
            # ==========================================

            with st.spinner(
                "Sedang menggabungkan halaman "
                "menjadi PDF..."
            ):

                rgb_images = [
                    foto.convert("RGB")
                    for foto
                    in st.session_state.daftar_foto
                ]

                halaman_pertama = rgb_images[0]

                halaman_sisa = rgb_images[1:]

                pdf_bytes = io.BytesIO()

                halaman_pertama.save(
                    pdf_bytes,
                    format="PDF",
                    save_all=True,
                    append_images=halaman_sisa
                )

                pdf_bytes.seek(0)


            # ==========================================
            # MENYIAPKAN FOLDER TAHUN & UPLOAD
            # ==========================================

            with st.spinner(
                "Sedang menyiapkan folder dan "
                "mengunggah ke Google Drive..."
            ):

                upload_target_id = (
                    selected_folder_id
                )

                # ==========================================
                # EKSTRAK TAHUN DARI NAMA FILE
                # ==========================================

                match_tahun = re.search(
                    r'\b(19|20)\d{2}\b',
                    file_name
                )

                selected_year = (
                    "Tidak menggunakan tahun"
                )

                if match_tahun:

                    selected_year = (
                        match_tahun.group(0)
                    )


                # ==========================================
                # CEK / BUAT FOLDER TAHUN
                # ==========================================

                if selected_year != (
                    "Tidak menggunakan tahun"
                ):

                    year_query = (
                        f"name='{selected_year}' "
                        "and mimeType="
                        "'application/vnd.google-apps.folder' "
                        f"and '{selected_folder_id}' in parents "
                        "and trashed=false"
                    )

                    year_result = (
                        drive_service.files()
                        .list(
                            q=year_query,
                            spaces="drive",
                            fields="files(id, name)"
                        )
                        .execute()
                    )

                    year_folders = (
                        year_result.get(
                            "files",
                            []
                        )
                    )

                    if year_folders:

                        upload_target_id = (
                            year_folders[0]["id"]
                        )

                    else:

                        new_year_folder = (
                            create_drive_folder(
                                drive_service,
                                selected_year,
                                selected_folder_id
                            )
                        )

                        upload_target_id = (
                            new_year_folder["id"]
                        )


                # ==========================================
                # UPLOAD PDF
                # ==========================================

                file_metadata = {
                    "name": f"{file_name}.pdf",
                    "mimeType": "application/pdf",
                    "parents": [
                        upload_target_id
                    ]
                }

                media = MediaIoBaseUpload(
                    pdf_bytes,
                    mimetype="application/pdf",
                    resumable=True
                )

                uploaded_file = (
                    drive_service.files()
                    .create(
                        body=file_metadata,
                        media_body=media,
                        fields="id, name, webViewLink"
                    )
                    .execute()
                )


            # ==========================================
            # BERHASIL
            # ==========================================

            st.success(
                "🎉 PDF berhasil di-upload "
                "ke Google Drive!"
            )

            st.write(
                f"**Nama file:** "
                f"{uploaded_file.get('name')}"
            )

            if uploaded_file.get(
                "webViewLink"
            ):

                st.link_button(
                    "📂 Buka di Google Drive",
                    uploaded_file[
                        "webViewLink"
                    ]
                )

        except Exception as e:

            st.error(
                f"Gagal mengunggah ke Google Drive: {e}"
            )


# ==========================================
# 10. SCAN DOKUMEN BARU
# ==========================================
if jumlah_sekarang > 0:

    st.divider()

    if st.button(
        "🔄 Scan Dokumen Baru",
        use_container_width=True
    ):

        st.session_state.daftar_foto = []

        st.session_state.kamera_key += 1

        st.rerun()