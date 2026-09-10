import io
import re
import base64

import cv2
import numpy as np
import streamlit as st

from PIL import Image

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


# =========================================================
# KONFIGURASI HALAMAN
# =========================================================

st.set_page_config(
    page_title="DocuFlow",
    page_icon="📄",
    layout="centered"
)


# =========================================================
# CUSTOM CAMERA - STREAMLIT COMPONENT V2
# =========================================================

CAMERA_HTML = """
<div class="scanner-app">

    <div class="scanner-header">
        <button id="backButton" class="icon-button">
            ←
        </button>

        <div class="header-title">
            <div class="title">Scan Dokumen</div>
            <div id="pageCounter" class="counter">
                0 / 5 halaman
            </div>
        </div>

        <div class="header-spacer"></div>
    </div>


    <div id="cameraArea" class="camera-area">

        <video
            id="camera"
            autoplay
            playsinline
            muted
        ></video>

        <div class="dark-top"></div>
        <div class="dark-bottom"></div>

        <div id="cameraMessage" class="camera-message">
            Tekan tombol kamera untuk memulai
        </div>

    </div>


    <div class="bottom-panel">

        <div id="thumbnailContainer" class="thumbnail-container">
        </div>

        <div class="camera-controls">

            <button id="cancelButton" class="secondary-button">
                Batal
            </button>

            <button id="captureButton" class="capture-button">
                <span></span>
            </button>

            <button id="doneButton" class="ok-button">
                OK
            </button>

        </div>

    </div>


    <div id="startOverlay" class="start-overlay">

        <div class="camera-icon">
            📷
        </div>

        <div class="start-title">
            Siap untuk scan?
        </div>

        <div class="start-description">
            Kamera belakang akan digunakan secara otomatis.
        </div>

        <button id="startButton" class="start-button">
            Mulai Kamera
        </button>

    </div>

</div>
"""


CAMERA_CSS = """

* {
    box-sizing: border-box;
}

.scanner-app {
    width: 100%;
    min-height: 720px;
    background: #111;
    color: white;
    border-radius: 20px;
    overflow: hidden;
    position: relative;
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}


/* HEADER */

.scanner-header {
    height: 64px;
    background: #171717;

    display: flex;
    align-items: center;

    padding: 8px 12px;

    position: relative;
    z-index: 20;
}

.icon-button {
    width: 44px;
    height: 44px;

    border: none;
    background: transparent;

    color: white;

    font-size: 30px;

    cursor: pointer;

    border-radius: 50%;
}

.icon-button:active {
    background: rgba(255,255,255,0.15);
}

.header-title {
    flex: 1;
    text-align: center;
}

.title {
    font-size: 18px;
    font-weight: 700;
}

.counter {
    font-size: 12px;
    color: #aaa;
    margin-top: 2px;
}

.header-spacer {
    width: 44px;
}


/* CAMERA */

.camera-area {
    position: relative;
    width: 100%;
    height: 530px;
    background: #000;
    overflow: hidden;
}

#camera {
    width: 100%;
    height: 100%;

    object-fit: cover;

    display: block;

    background: #000;
}


/* GUIDE */

.document-guide {

    position: absolute;

    left: 7%;
    right: 7%;

    top: 12%;
    bottom: 12%;

    border: 2px solid rgba(255,255,255,0.85);

    border-radius: 8px;

    pointer-events: none;

    box-shadow:
        0 0 0 9999px rgba(0,0,0,0.18);
}


/* CORNERS */

.corner {
    position: absolute;

    width: 32px;
    height: 32px;

    border-color: white;
    border-style: solid;
}

.top-left {
    left: -2px;
    top: -2px;

    border-width: 4px 0 0 4px;
}

.top-right {
    right: -2px;
    top: -2px;

    border-width: 4px 4px 0 0;
}

.bottom-left {
    left: -2px;
    bottom: -2px;

    border-width: 0 0 4px 4px;
}

.bottom-right {
    right: -2px;
    bottom: -2px;

    border-width: 0 4px 4px 0;
}


/* MESSAGE */

.camera-message {

    position: absolute;

    left: 50%;
    top: 50%;

    transform: translate(-50%, -50%);

    background: rgba(0,0,0,0.55);

    padding: 10px 16px;

    border-radius: 20px;

    font-size: 14px;

    color: white;

    text-align: center;

    pointer-events: none;
}


/* BOTTOM */
.bottom-panel {
    background: #171717;
    padding: 0 12px 12px;
    margin-top: 0;
}


/* THUMBNAILS */

.thumbnail-container {

    min-height: 84px;

    display: flex;

    gap: 8px;

    overflow-x: auto;

    padding: 4px 0 10px;
}

.thumbnail {

    position: relative;

    width: 58px;
    height: 72px;

    flex-shrink: 0;

    border-radius: 7px;

    overflow: hidden;

    border: 2px solid #555;

    background: #333;
}

.thumbnail img {

    width: 100%;
    height: 100%;

    object-fit: cover;

}

.thumbnail-number {

    position: absolute;

    left: 4px;
    top: 4px;

    background: rgba(0,0,0,0.7);

    color: white;

    width: 20px;
    height: 20px;

    border-radius: 50%;

    font-size: 11px;

    display: flex;

    align-items: center;
    justify-content: center;
}

.thumbnail-delete {

    position: absolute;

    right: 3px;
    top: 3px;

    width: 20px;
    height: 20px;

    border: none;

    border-radius: 50%;

    background: rgba(0,0,0,0.7);

    color: white;

    cursor: pointer;

    font-size: 12px;

    padding: 0;
}


/* CONTROLS */

.camera-controls {

    display: flex;

    align-items: center;

    justify-content: space-between;

    padding: 4px 4px 0;
}

.secondary-button,
.ok-button {

    border: none;

    border-radius: 12px;

    height: 44px;

    padding: 0 20px;

    font-size: 15px;

    font-weight: 600;

    cursor: pointer;
}

.secondary-button {

    background: #2c2c2c;

    color: white;
}

.ok-button {

    background: #ffffff;

    color: #111;
}

.ok-button:disabled {

    opacity: 0.35;

    cursor: not-allowed;
}


/* SHUTTER */

.capture-button {

    width: 72px;
    height: 72px;

    border-radius: 50%;

    border: 5px solid white;

    background: transparent;

    display: flex;

    align-items: center;
    justify-content: center;

    cursor: pointer;

    padding: 0;
}

.capture-button span {

    width: 56px;
    height: 56px;

    background: white;

    border-radius: 50%;

    display: block;

    transition: transform 0.1s;
}

.capture-button:active span {

    transform: scale(0.85);
}


/* START OVERLAY */

.start-overlay {

    position: absolute;

    inset: 64px 0 0 0;

    background: rgba(15,15,15,0.97);

    z-index: 30;

    display: flex;

    flex-direction: column;

    align-items: center;

    justify-content: center;

    text-align: center;

    padding: 30px;
}

.camera-icon {

    font-size: 64px;

    margin-bottom: 20px;
}

.start-title {

    font-size: 24px;

    font-weight: 700;

    margin-bottom: 8px;
}

.start-description {

    color: #aaa;

    font-size: 14px;

    line-height: 1.5;

    max-width: 300px;

    margin-bottom: 24px;
}

.start-button {

    border: none;

    background: white;

    color: #111;

    font-size: 16px;

    font-weight: 700;

    padding: 14px 28px;

    border-radius: 14px;

    cursor: pointer;
}


/* MOBILE */

@media (max-width: 600px) {

    .scanner-app {
        border-radius: 0;
        min-height: 100vh;
    }

    .camera-area {
        height: calc(100vh - 200px);
        min-height: 400px;
    }

    .bottom-panel {
        padding: 0 12px 12px;
    }

    .thumbnail-container {
        min-height: 0;
        padding: 0;
    }

    .camera-controls {
        padding: 8px 4px 0;
    }

}

    .document-guide {

        left: 5%;
        right: 5%;

        top: 10%;
        bottom: 10%;
    }

}
"""


CAMERA_JS = """

export default function(component) {

    const {
        parentElement,
        setTriggerValue
    } = component;


    const video =
        parentElement.querySelector("#camera");

    const startButton =
        parentElement.querySelector("#startButton");

    const captureButton =
        parentElement.querySelector("#captureButton");

    const cancelButton =
        parentElement.querySelector("#cancelButton");

    const doneButton =
        parentElement.querySelector("#doneButton");

    const startOverlay =
        parentElement.querySelector("#startOverlay");

    const cameraMessage =
        parentElement.querySelector("#cameraMessage");

    const thumbnailContainer =
        parentElement.querySelector("#thumbnailContainer");

    const pageCounter =
        parentElement.querySelector("#pageCounter");


    let stream = null;

    let photos = [];


    /* =========================================
       UPDATE COUNTER
    ========================================= */

    function updateCounter() {

        pageCounter.textContent =
            photos.length + " / 5 halaman";

        doneButton.disabled =
            photos.length === 0;
    }


    /* =========================================
       RENDER THUMBNAILS
    ========================================= */

    function renderThumbnails() {

        thumbnailContainer.innerHTML = "";

        photos.forEach((photo, index) => {

            const wrapper =
                document.createElement("div");

            wrapper.className = "thumbnail";


            const image =
                document.createElement("img");

            image.src = photo;


            const number =
                document.createElement("div");

            number.className =
                "thumbnail-number";

            number.textContent =
                index + 1;


            const deleteButton =
                document.createElement("button");

            deleteButton.className =
                "thumbnail-delete";

            deleteButton.textContent =
                "×";


            deleteButton.onclick = () => {

                photos.splice(index, 1);

                renderThumbnails();

                updateCounter();
            };


            wrapper.appendChild(image);

            wrapper.appendChild(number);

            wrapper.appendChild(deleteButton);

            thumbnailContainer.appendChild(wrapper);

        });
    }


    /* =========================================
       START CAMERA
    ========================================= */

    async function startCamera() {

        try {

            if (
                !navigator.mediaDevices ||
                !navigator.mediaDevices.getUserMedia
            ) {

                throw new Error(
                    "Browser tidak mendukung akses kamera."
                );
            }


            stream =
                await navigator.mediaDevices.getUserMedia({

                    video: {

                        facingMode: {
                            ideal: "environment"
                        },

                        width: {
                            ideal: 1920
                        },

                        height: {
                            ideal: 1080
                        }

                    },

                    audio: false
                });


            video.srcObject = stream;

            await video.play();


            startOverlay.style.display =
                "none";

            cameraMessage.style.display =
                "none";

            captureButton.disabled =
                false;

        }

        catch (error) {

            cameraMessage.textContent =
                "Kamera tidak dapat dibuka: "
                + error.message;

            cameraMessage.style.display =
                "block";

            console.error(error);
        }
    }


    /* =========================================
       CAPTURE PHOTO
    ========================================= */
function capturePhoto() {

    if (!stream) {
        return;
    }


    if (photos.length >= 5) {

        cameraMessage.textContent =
            "Maksimal 5 halaman.";

        cameraMessage.style.display =
            "block";

        setTimeout(() => {

            cameraMessage.style.display =
                "none";

        }, 1500);

        return;
    }


    if (
        video.videoWidth === 0 ||
        video.videoHeight === 0
    ) {

        return;
    }


    // =========================================
    // SESUAIKAN HASIL FOTO DENGAN AREA PREVIEW
    // =========================================

    const videoWidth =
        video.videoWidth;

    const videoHeight =
        video.videoHeight;


    const displayWidth =
        video.clientWidth;

    const displayHeight =
        video.clientHeight;


    // object-fit: cover
    const scale =
        Math.max(
            displayWidth / videoWidth,
            displayHeight / videoHeight
        );


    // Ukuran gambar asli yang terlihat
    // di dalam preview
    const sourceWidth =
        displayWidth / scale;

    const sourceHeight =
        displayHeight / scale;


    // Posisi crop di gambar asli
    const sourceX =
        (videoWidth - sourceWidth) / 2;

    const sourceY =
        (videoHeight - sourceHeight) / 2;


    const canvas =
        document.createElement("canvas");


    canvas.width =
        Math.round(sourceWidth);

    canvas.height =
        Math.round(sourceHeight);


    const context =
        canvas.getContext("2d");


    context.drawImage(
        video,

        sourceX,
        sourceY,

        sourceWidth,
        sourceHeight,

        0,
        0,

        canvas.width,
        canvas.height
    );


    const image =
        canvas.toDataURL(
            "image/jpeg",
            0.92
        );


    photos.push(image);


    renderThumbnails();

    updateCounter();


    if (photos.length >= 5) {

        cameraMessage.textContent =
            "Maksimal 5 halaman tercapai.";

        cameraMessage.style.display =
            "block";
    }
}


    /* =========================================
       CANCEL
    ========================================= */

    function cancelScan() {

        stopCamera();

        setTriggerValue(
            "cancel",
            true
        );
    }


    /* =========================================
       DONE
    ========================================= */

    function finishScan() {

        if (photos.length === 0) {

            return;
        }


        stopCamera();


        setTriggerValue(
            "done",
            photos
        );
    }


    /* =========================================
       STOP CAMERA
    ========================================= */

    function stopCamera() {

        if (stream) {

            stream
                .getTracks()
                .forEach(
                    track => track.stop()
                );

            stream = null;
        }

        video.srcObject = null;
    }


    /* =========================================
       EVENTS
    ========================================= */

    startButton.onclick =
        startCamera;


    captureButton.onclick =
        capturePhoto;


    cancelButton.onclick =
        cancelScan;


    doneButton.onclick =
        finishScan;


    /* =========================================
       INITIAL
    ========================================= */

    updateCounter();


    /* =========================================
       CLEANUP
    ========================================= */

    return () => {

        stopCamera();
    };
}
"""


camera_component = st.components.v2.component(
    name="docuflow_camera",
    html=CAMERA_HTML,
    css=CAMERA_CSS,
    js=CAMERA_JS
)


# =========================================================
# FUNGSI GOOGLE DRIVE - FOLDER
# =========================================================

def get_drive_folders(drive_service):

    results = drive_service.files().list(
        q="mimeType='application/vnd.google-apps.folder' and trashed=false",
        spaces="drive",
        fields="files(id, name, parents)",
        orderBy="name"
    ).execute()

    return results.get("files", [])


def create_drive_folder(
    drive_service,
    folder_name,
    parent_id=None
):

    folder_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder"
    }

    if parent_id and parent_id != "root":

        folder_metadata["parents"] = [
            parent_id
        ]

    folder = drive_service.files().create(
        body=folder_metadata,
        fields="id, name, parents"
    ).execute()

    return folder


# =========================================================
# FUNGSI PEMOTONG OTOMATIS
# =========================================================

def potong_dokumen_otomatis(image):

    img_array = np.array(image)

    gray = cv2.cvtColor(
        img_array,
        cv2.COLOR_RGB2GRAY
    )

    blur = cv2.GaussianBlur(
        gray,
        (5, 5),
        0
    )

    edged = cv2.Canny(
        blur,
        75,
        200
    )

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

        tl, tr, br, bl = rect


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


        if maxWidth <= 0 or maxHeight <= 0:

            return image


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


    return image


# =========================================================
# SESSION STATE
# =========================================================

if "halaman" not in st.session_state:

    st.session_state.halaman = "utama"


if "daftar_foto" not in st.session_state:

    st.session_state.daftar_foto = []


# =========================================================
# LOGIN GOOGLE
# =========================================================

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


# =========================================================
# USER LOGIN
# =========================================================

st.title("📄 DocuFlow")

nama_user = st.user.get(
    "name",
    "Pengguna"
)

email_user = st.user.get(
    "email",
    ""
)


# =========================================================
# HALAMAN SCANNER
# =========================================================

if st.session_state.halaman == "scanner":

    st.markdown(
        """
        <style>

        .scanner-wrapper {
            margin-top: -20px;
        }

        </style>
        """,
        unsafe_allow_html=True
    )


    hasil_scanner = camera_component(
        key="docuflow_camera",
        width="stretch",
        height=720,
        on_done_change=lambda: None,
        on_cancel_change=lambda: None
    )


    # =====================================================
    # SCAN SELESAI
    # =====================================================

    if (
        hasattr(hasil_scanner, "done")
        and hasil_scanner.done
    ):

        foto_list = hasil_scanner.done


        if len(foto_list) == 0:

            st.warning(
                "Belum ada foto yang diambil."
            )

        else:

            foto_baru = []


            try:

                for photo_data in foto_list:

                    image_data = photo_data.split(
                        ",",
                        1
                    )[1]


                    image_bytes = (
                        base64.b64decode(
                            image_data
                        )
                    )


                    img = Image.open(
                        io.BytesIO(
                            image_bytes
                        )
                    ).convert("RGB")


                    foto_baru.append(img)


                st.session_state.daftar_foto = (
                    foto_baru
                )

                st.session_state.halaman = (
                    "utama"
                )

                st.rerun()


            except Exception as e:

                st.error(
                    f"Gagal memproses hasil scan: {e}"
                )


    # =====================================================
    # SCAN DIBATALKAN
    # =====================================================

    if (
        hasattr(hasil_scanner, "cancel")
        and hasil_scanner.cancel
    ):

        st.session_state.daftar_foto = []

        st.session_state.halaman = "utama"

        st.rerun()


    st.stop()


# =========================================================
# HALAMAN UTAMA
# =========================================================

st.success(
    f"Halo, {nama_user}! 👋"
)

st.caption(
    f"Login sebagai: {email_user}"
)


if st.button("Logout"):

    st.logout()


# =========================================================
# ACCESS TOKEN
# =========================================================

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


# =========================================================
# GOOGLE DRIVE
# =========================================================

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


# =========================================================
# FOLDER PENYIMPANAN
# =========================================================

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


    folder_options = {
        "📂 My Drive": "root"
    }


    for folder in folders:

        folder_options[
            f"📁 {folder['name']}"
        ] = folder["id"]


    st.selectbox(
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


# =========================================================
# BUAT FOLDER BARU
# =========================================================

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


# =========================================================
# SCAN DOKUMEN
# =========================================================

st.divider()

st.subheader(
    "📄 Dokumen"
)


if len(st.session_state.daftar_foto) == 0:

    st.info(
        "Belum ada dokumen yang dipindai."
    )


    if st.button(
        "📷 Scan Dokumen",
        use_container_width=True
    ):

        st.session_state.halaman = (
            "scanner"
        )

        st.rerun()


else:

    st.success(
        f"✅ {len(st.session_state.daftar_foto)} "
        "halaman siap disimpan."
    )


    if st.button(
        "📷 Scan Ulang / Tambah Dokumen",
        use_container_width=True
    ):

        st.session_state.daftar_foto = []

        st.session_state.halaman = (
            "scanner"
        )

        st.rerun()


# =========================================================
# PREVIEW
# =========================================================

if len(st.session_state.daftar_foto) > 0:

    st.write(
        "### Preview Hasil Scan"
    )


    cols = st.columns(
        len(st.session_state.daftar_foto)
    )


    for i, foto in enumerate(
        st.session_state.daftar_foto
    ):


cols = st.columns(
    len(st.session_state.daftar_foto)
)

for i, foto in enumerate(
    st.session_state.daftar_foto
):

    with cols[i]:

        st.image(
            foto,
            caption=f"Halaman {i + 1}",
            width=300
        )

        if st.button(
            "❌ Hapus",
            key=f"hapus_halaman_{i}",
            use_container_width=True
        ):

            st.session_state.daftar_foto.pop(i)

            st.rerun()
        
        if cols[i].button(
            "❌ Hapus",
            key=f"hapus_halaman_{i}",
            use_container_width=True
        ):

            st.session_state.daftar_foto.pop(i)

            st.rerun()


# =========================================================
# NAMA FILE
# =========================================================

if len(st.session_state.daftar_foto) > 0:

    st.divider()

    st.subheader(
        "💾 Simpan Dokumen"
    )


    file_name = st.text_input(
        "Nama file PDF:",
        value="Dokumen_Scan_DocuFlow"
    )


    # =====================================================
    # UPLOAD
    # =====================================================

    if st.button(
        "📤 Simpan ke Google Drive",
        use_container_width=True
    ):

        if not file_name.strip():

            st.warning(
                "Masukkan nama file terlebih dahulu."
            )

        else:

            try:

                # =========================================
                # BUAT PDF
                # =========================================

                with st.spinner(
                    "Sedang membuat PDF..."
                ):

                    rgb_images = [
                        foto.convert("RGB")
                        for foto
                        in st.session_state.daftar_foto
                    ]


                    halaman_pertama = (
                        rgb_images[0]
                    )


                    halaman_sisa = (
                        rgb_images[1:]
                    )


                    pdf_bytes = io.BytesIO()


                    halaman_pertama.save(
                        pdf_bytes,
                        format="PDF",
                        save_all=True,
                        append_images=halaman_sisa
                    )


                    pdf_bytes.seek(0)


                # =========================================
                # FOLDER TAHUN
                # =========================================

                with st.spinner(
                    "Menyiapkan folder Google Drive..."
                ):

                    upload_target_id = (
                        selected_folder_id
                    )


                    match_tahun = re.search(
                        r'\b(19|20)\d{2}\b',
                        file_name
                    )


                    selected_year = None


                    if match_tahun:

                        selected_year = (
                            match_tahun.group(0)
                        )


                    if selected_year:

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


                # =========================================
                # UPLOAD PDF
                # =========================================

                with st.spinner(
                    "Mengunggah PDF ke Google Drive..."
                ):

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


                # =========================================
                # BERHASIL
                # =========================================

                st.success(
                    "🎉 PDF berhasil disimpan "
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


# =========================================================
# SCAN BARU
# =========================================================

if len(st.session_state.daftar_foto) > 0:

    st.divider()


    if st.button(
        "🔄 Selesai / Scan Dokumen Baru",
        use_container_width=True
    ):

        st.session_state.daftar_foto = []

        st.session_state.halaman = (
            "scanner"
        )

        st.rerun()
