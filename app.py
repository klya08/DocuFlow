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
    page_title="DocuFlow | Document Management",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# INJEKSI CSS KUSTOM (UI/UX SAAS MODERN UNTUK DASHBOARD)
# =========================================================
CUSTOM_THEME_CSS = """
<style>
/* Import Font Modern */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

/* Global Reset & Typography */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    background-color: #F8F9FA !important; 
    color: #1F2937 !important; 
}

/* Hide Streamlit default elements for clean look */
header[data-testid="stHeader"] {
    background: transparent !important;
}
footer {visibility: hidden;}

/* Container adjustments */
.block-container {
    padding-top: 1rem !important;
    max-width: 1200px !important;
}

/* Navbar Minimalist */
.custom-navbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    background: white;
    border-radius: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    margin-bottom: 32px;
    border: 1px solid #F3F4F6;
}
.nav-logo {
    font-size: 20px;
    font-weight: 700;
    color: #065F46; 
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Landing Page Hero Section */
.hero-title {
    font-size: 3rem;
    font-weight: 800;
    line-height: 1.2;
    color: #111827;
    margin-bottom: 16px;
    letter-spacing: -0.02em;
}
.hero-highlight {
    color: #065F46;
}
.hero-subtitle {
    font-size: 1.125rem;
    color: #6B7280;
    line-height: 1.6;
    margin-bottom: 40px;
    max-width: 90%;
}

/* Abstract Floating Animation */
@keyframes float {
    0% { transform: translateY(0px); }
    50% { transform: translateY(-12px); }
    100% { transform: translateY(0px); }
}
.floating-element {
    animation: float 5s ease-in-out infinite;
}

/* Login Card Minimalist */
.login-card {
    background: white;
    padding: 48px 40px;
    border-radius: 24px;
    box-shadow: 0 20px 40px rgba(0,0,0,0.04);
    border: 1px solid #F3F4F6;
    text-align: center;
    transition: transform 0.3s ease;
}
.login-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 25px 50px rgba(0,0,0,0.06);
}
.login-icon-wrapper {
    width: 64px;
    height: 64px;
    background: #D1FAE5; 
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 32px;
    margin: 0 auto 24px auto;
}
.login-title {
    font-size: 24px;
    font-weight: 700;
    color: #111827;
    margin-bottom: 8px;
}
.login-desc {
    font-size: 14px;
    color: #6B7280;
    margin-bottom: 32px;
    line-height: 1.5;
}

/* Target Native Streamlit Buttons */
div[data-testid="stLoginButton"] > button {
    background-color: #065F46 !important;
    color: white !important;
    width: 100% !important;
    padding: 14px 24px !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 16px !important;
    border: none !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 6px rgba(6, 95, 70, 0.15) !important;
}
div[data-testid="stLoginButton"] > button:hover {
    background-color: #044E3A !important;
    transform: translateY(-2px);
    box-shadow: 0 6px 12px rgba(6, 95, 70, 0.25) !important;
}

/* Standard Buttons Restyle */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
button[kind="primary"] {
    background-color: #065F46 !important;
    border-color: #065F46 !important;
}
button[kind="primary"]:hover {
    background-color: #044E3A !important;
    border-color: #044E3A !important;
}

/* Cards (st.container with border) styling */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 16px !important;
    border: 1px solid #E5E7EB !important;
    background: white !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
    padding: 16px !important;
    margin-bottom: 24px !important;
}

/* Smooth Fade In */
.fade-in {
    animation: fadeIn 0.8s ease-in;
}
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>
"""
st.markdown(CUSTOM_THEME_CSS, unsafe_allow_html=True)

# =========================================================
# CUSTOM CAMERA - STREAMLIT COMPONENT V2 (PERSIS ASLI MILIK USER)
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
                ideal: 2560
            },

            height: {
                ideal: 1440
            },

            aspectRatio: {
                ideal: 16 / 9
            }
        },

        audio: false
    });


// =========================================
// AKTIFKAN AUTOFOCUS KAMERA
// =========================================

const videoTrack =
    stream.getVideoTracks()[0];

if (videoTrack) {

    const capabilities =
        videoTrack.getCapabilities();

    if (
        capabilities.focusMode &&
        capabilities.focusMode.includes("continuous")
    ) {

        try {

            await videoTrack.applyConstraints({
                advanced: [
                    {
                        focusMode: "continuous"
                    }
                ]
            });

        } catch (focusError) {

            console.log(
                "Autofocus continuous tidak tersedia:",
                focusError
            );
        }
    }
}

            video.srcObject = stream;

            await video.play();

            console.log(
                "RESOLUSI KAMERA:",
                video.videoWidth,
                "x",
                video.videoHeight
            );


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
    // UKURAN ASLI KAMERA
    // =========================================

    const videoWidth =
        video.videoWidth;

    const videoHeight =
        video.videoHeight;


    // =========================================
    // UKURAN PREVIEW
    // =========================================

    const displayWidth =
        video.clientWidth;

    const displayHeight =
        video.clientHeight;


    if (
        displayWidth === 0 ||
        displayHeight === 0
    ) {

        return;
    }


    // =========================================
    // SESUAIKAN DENGAN object-fit: cover
    // =========================================

    const videoRatio =
        videoWidth / videoHeight;

    const displayRatio =
        displayWidth / displayHeight;


    let sourceX = 0;
    let sourceY = 0;

    let sourceWidth =
        videoWidth;

    let sourceHeight =
        videoHeight;


    if (videoRatio > displayRatio) {

        sourceWidth =
            videoHeight * displayRatio;

        sourceX =
            (videoWidth - sourceWidth) / 2;

    } else {

        sourceHeight =
            videoWidth / displayRatio;

        sourceY =
            (videoHeight - sourceHeight) / 2;
    }


    // =========================================
    // CANVAS RESOLUSI TINGGI
    // =========================================

    const canvas =
        document.createElement("canvas");


    canvas.width =
        Math.round(sourceWidth);

    canvas.height =
        Math.round(sourceHeight);


    const context =
        canvas.getContext("2d");


    context.imageSmoothingEnabled =
        true;

    context.imageSmoothingQuality =
        "high";


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


    // =========================================
    // KUALITAS FOTO TINGGI
    // =========================================

    const image =
        canvas.toDataURL(
            "image/jpeg",
            0.95
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
# FUNGSI GOOGLE DRIVE - FOLDER (PERSIS ASLI MILIK USER)
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
# FUNGSI PEMOTONG OTOMATIS (PERSIS ASLI MILIK USER)
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
# SESSION STATE (PERSIS ASLI MILIK USER)
# =========================================================

if "halaman" not in st.session_state:
    st.session_state.halaman = "utama"

if "daftar_foto" not in st.session_state:
    st.session_state.daftar_foto = []

# =========================================================
# HALAMAN LANDING / LOGIN GOOGLE (SAAS UI)
# =========================================================
if not st.user.is_logged_in:
    
    # Navbar Minimalist
    st.markdown("""
    <div class="custom-navbar fade-in">
        <div class="nav-logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
            DocuFlow
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Layout 2 Kolom untuk Desktop
    col_hero, col_login = st.columns([1.2, 1], gap="large")

    with col_hero:
        # Hero Section dengan Abstract Illustration
        st.markdown("""
        <div class="fade-in" style="padding-right: 2rem;">
            <h1 class="hero-title">
                Kelola Dokumen Lebih Mudah dengan <span class="hero-highlight">DocuFlow</span>
            </h1>
            <p class="hero-subtitle">
                Scan, simpan, dan kelola dokumen fisik Anda langsung ke Google Drive dalam satu alur yang cerdas, otomatis, dan terenkripsi.
            </p>
            
            <div style="display: flex; justify-content: flex-start; align-items: center; margin-top: 2rem;">
                <svg width="320" height="280" viewBox="0 0 320 280" fill="none" xmlns="http://www.w3.org/2000/svg" class="floating-element">
                    <!-- Base Grid -->
                    <rect x="0" y="0" width="320" height="280" fill="transparent"/>
                    
                    <!-- Back Document -->
                    <rect x="60" y="40" width="160" height="200" rx="16" fill="white" stroke="#E5E7EB" stroke-width="3"/>
                    <rect x="85" y="70" width="110" height="6" rx="3" fill="#F3F4F6"/>
                    <rect x="85" y="90" width="80" height="6" rx="3" fill="#F3F4F6"/>
                    
                    <!-- Front Floating Document -->
                    <rect x="100" y="60" width="160" height="200" rx="16" fill="white" stroke="#065F46" stroke-width="3" filter="drop-shadow(0 15px 25px rgba(6, 95, 70, 0.15))"/>
                    <rect x="125" y="90" width="110" height="8" rx="4" fill="#D1FAE5"/>
                    <rect x="125" y="115" width="90" height="6" rx="3" fill="#F3F4F6"/>
                    <rect x="125" y="135" width="100" height="6" rx="3" fill="#F3F4F6"/>
                    <rect x="125" y="155" width="70" height="6" rx="3" fill="#F3F4F6"/>
                    
                    <!-- Abstract Scanning Line -->
                    <path d="M90 180 L270 180" stroke="#10B981" stroke-width="4" stroke-linecap="round" filter="drop-shadow(0 0 8px rgba(16, 185, 129, 0.4))"/>
                    
                    <!-- Cloud Icon Badge -->
                    <circle cx="260" cy="80" r="28" fill="white" filter="drop-shadow(0 4px 10px rgba(0,0,0,0.05))"/>
                    <path d="M268.04 77.014a4.5 4.5 0 0 0-8.66-2.122 3.5 3.5 0 1 0-.64 6.941h9.3a3.5 3.5 0 0 0 0-7v2.181z" fill="#065F46"/>
                </svg>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_login:
        st.write("") 
        st.write("")
        st.markdown("""
        <div class="login-card fade-in">
            <div class="login-icon-wrapper">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#065F46" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                </svg>
            </div>
            <div class="login-title">Akses DocuFlow</div>
            <div class="login-desc">Masuk menggunakan akun Google Anda untuk menghubungkan ruang penyimpanan awan.</div>
        """, unsafe_allow_html=True)

        st.login()

        st.markdown("""
            <div style="margin-top: 32px; font-size: 13px; color: #9CA3AF; border-top: 1px solid #F3F4F6; padding-top: 24px;">
                Terkoneksi aman dengan enkripsi Google OAuth 2.0
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.stop()


# =========================================================
# HALAMAN USER LOGIN & NAVBAR DASHBOARD (SAAS UI)
# =========================================================
nama_user = st.user.get("name", "Pengguna")
email_user = st.user.get("email", "")

# Custom Logged-in Navbar
col_logo, col_user = st.columns([1, 1])
with col_logo:
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 8px; font-size: 24px; font-weight: 700; color: #065F46; padding: 12px 0 24px 0;">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
        DocuFlow
    </div>
    """, unsafe_allow_html=True)
with col_user:
    st.markdown(f"""
    <div style="display: flex; flex-direction: column; align-items: flex-end; padding: 12px 0;">
        <span style="font-weight: 600; color: #111827;">{nama_user}</span>
        <span style="font-size: 13px; color: #6B7280;">{email_user}</span>
    </div>
    """, unsafe_allow_html=True)


# =========================================================
# ACCESS TOKEN (PERSIS ASLI MILIK USER)
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
# GOOGLE DRIVE KONEKSI (PERSIS ASLI MILIK USER)
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
# HALAMAN SCANNER (LOGIKA BACKEND PERSIS ASLI MILIK USER)
# =========================================================

if st.session_state.halaman == "scanner":
    
    st.markdown(
        """
        <style>
        .scanner-wrapper {
            margin-top: -20px;
        }
        /* Menghilangkan padding agar komponen muat */
        .block-container{padding-top: 0 !important; max-width: 800px !important;}
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
            st.warning("Belum ada foto yang diambil.")
        else:
            foto_baru = []
            try:
                for photo_data in foto_list:
                    image_data = photo_data.split(",", 1)[1]
                    image_bytes = base64.b64decode(image_data)
                    img = Image.open(
                        io.BytesIO(image_bytes)
                    ).convert("RGB")
                    
                    foto_baru.append(img)
                    
                st.session_state.daftar_foto = foto_baru
                st.session_state.halaman = "utama"
                st.rerun()

            except Exception as e:
                st.error(f"Gagal memproses hasil scan: {e}")

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
# HALAMAN UTAMA / DASHBOARD (UI SAAS DITERAPKAN)
# =========================================================

# Membagi dashboard menjadi 2 kolom (Tools & Setup)
dash_col1, dash_col2 = st.columns([2, 1.2], gap="large")

with dash_col2:
    with st.container(border=True):
        st.markdown("#### ⚙️ Pengaturan Penyimpanan")
        st.markdown("<span style='font-size:14px; color:#6B7280;'>Pilih tujuan folder Google Drive.</span>", unsafe_allow_html=True)
        st.write("")
        
        try:
            if "daftar_folder_drive" not in st.session_state:
                try:
                    st.session_state.daftar_folder_drive = get_drive_folders(drive_service)
                except Exception as drive_error:
                    error_text = str(drive_error).lower()
                    if ("refresh_token" in error_text or "credentials do not contain" in error_text or "invalid_grant" in error_text or "401" in error_text or "unauthorized" in error_text):
                        st.error("Sesi Google kedaluwarsa.")
                        if st.button("🔄 Relogin"): st.logout()
                        st.stop()
                    raise drive_error

            folders = st.session_state.daftar_folder_drive
            folder_options = {"📂 My Drive": "root"}
            for folder in folders:
                folder_options[f"📁 {folder['name']}"] = folder["id"]

            st.selectbox("Lokasi Folder", list(folder_options.keys()), key="pilihan_folder_utama")
            selected_folder_id = folder_options[st.session_state.pilihan_folder_utama]
        except Exception as e:
            st.error(f"Gagal memuat Drive: {e}")
            selected_folder_id = "root"

        with st.expander("➕ Buat Folder Baru"):
            new_folder_name = st.text_input("Nama folder", placeholder="Ex: Dokumen Legal")
            if st.button("Buat Folder", use_container_width=True):
                if new_folder_name.strip():
                    try:
                        new_folder = create_drive_folder(drive_service, new_folder_name.strip())
                        st.session_state.daftar_folder_drive = get_drive_folders(drive_service)
                        st.success(f"Dibuat: {new_folder['name']}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal: {e}")
                else:
                    st.warning("Nama kosong.")
                    
        st.write("")
        if st.button("Keluar dari Aplikasi", use_container_width=True):
            st.logout()

with dash_col1:
    with st.container(border=True):
        st.markdown("#### 📄 Dokumen Aktif")
        
        if len(st.session_state.daftar_foto) == 0:
            st.markdown("""
            <div style="background: #F9FAFB; padding: 40px 20px; border-radius: 12px; text-align: center; border: 1px dashed #D1D5DB; margin-bottom: 24px;">
                <div style="font-size: 32px; margin-bottom: 12px;">📷</div>
                <div style="color: #4B5563; font-weight: 500;">Belum ada dokumen yang dipindai</div>
                <div style="color: #9CA3AF; font-size: 13px; margin-top: 4px;">Klik tombol di bawah untuk mulai memindai dokumen fisik.</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Mulai Pemindai", type="primary", use_container_width=True):
                st.session_state.halaman = "scanner"
                st.rerun()
        else:
            st.success(f"✅ {len(st.session_state.daftar_foto)} halaman siap dikompilasi.")
            
            # Preview Thumbnail Modern
            cols = st.columns(5, gap="small", vertical_alignment="bottom")
            for i, foto in enumerate(st.session_state.daftar_foto):
                with cols[i]:
                    st.image(foto, caption=f"Hal {i + 1}", use_container_width=True)
                    if st.button("Hapus", key=f"hapus_halaman_{i}", use_container_width=True):
                        st.session_state.daftar_foto.pop(i)
                        st.rerun()
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("Ulangi / Tambah Halaman", use_container_width=True):
                    st.session_state.daftar_foto = []
                    st.session_state.halaman = "scanner"
                    st.rerun()

            # Proses Simpan
            st.divider()
            st.markdown("##### 💾 Konfigurasi File PDF")
            file_name = st.text_input("Beri nama file", value="Dokumen_Scan_DocuFlow")

            if st.button("Simpan & Unggah ke Google Drive", type="primary", use_container_width=True):
                if not file_name.strip():
                    st.warning("Masukkan nama file terlebih dahulu.")
                else:
                    try:
                        with st.spinner("Memproses dokumen..."):
                            rgb_images = [foto.convert("RGB") for foto in st.session_state.daftar_foto]
                            halaman_pertama = rgb_images[0]
                            halaman_sisa = rgb_images[1:]
                            pdf_bytes = io.BytesIO()
                            halaman_pertama.save(pdf_bytes, format="PDF", save_all=True, append_images=halaman_sisa)
                            pdf_bytes.seek(0)
                        
                        with st.spinner("Mengunggah ke jaringan cloud..."):
                            upload_target_id = selected_folder_id
                            match_tahun = re.search(r'\b(19|20)\d{2}\b', file_name)
                            selected_year = match_tahun.group(0) if match_tahun else None

                            if selected_year:
                                year_query = (f"name='{selected_year}' and mimeType='application/vnd.google-apps.folder' and '{selected_folder_id}' in parents and trashed=false")
                                year_result = drive_service.files().list(q=year_query, spaces="drive", fields="files(id, name)").execute()
                                year_folders = year_result.get("files", [])
                                if year_folders:
                                    upload_target_id = year_folders[0]["id"]
                                else:
                                    new_year_folder = create_drive_folder(drive_service, selected_year, selected_folder_id)
                                    upload_target_id = new_year_folder["id"]

                            file_metadata = {"name": f"{file_name}.pdf", "mimeType": "application/pdf", "parents": [upload_target_id]}
                            media = MediaIoBaseUpload(pdf_bytes, mimetype="application/pdf", resumable=True)
                            uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields="id, name, webViewLink").execute()

                        st.success("🎉 Berkas berhasil diamankan ke Google Drive!")
                        if uploaded_file.get("webViewLink"):
                            st.link_button("Buka File di Google Drive", uploaded_file["webViewLink"])
                        
                    except Exception as e:
                        st.error(f"Proses gagal: {e}")
