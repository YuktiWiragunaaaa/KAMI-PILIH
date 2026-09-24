"""Sortir AI — antarmuka liquid glass (PySide6) di atas sortir_core."""

import os
import sys
import threading

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPen,
    QIcon,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import sortir_core as core

TEKS_FOLDER_KOSONG = "Belum ada folder dipilih"

# ---------------------------------------------------------------------------
# Palet (mengikuti desain Figma / sortir-ai.html, mode terang)
# ---------------------------------------------------------------------------
INK = "#0f172a"
INK_2 = "#1e293b"
MUTED = "#475569"
FAINT = "#64748b"
PLACEHOLDER = "#94a3b8"
ACCENT_A = "#4f7bff"
ACCENT_B = "#995cff"
CHIP_INK = "#4f46e5"

STYLESHEET = f"""
* {{ font-family: "Segoe UI Variable Text", "Segoe UI", "Inter", sans-serif; }}
QWidget#Root {{ background: transparent; }}
QScrollArea {{ background: transparent; border: 0; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

QFrame#Card {{ background: rgba(255,255,255,165); border: 0; }}
QFrame#Panel {{
    background: rgba(255,255,255,150);
    border: 1px solid rgba(255,255,255,230);
    border-radius: 20px;
}}
QLabel {{ background: transparent; color: {INK_2}; }}
QLabel#Title {{ color: {INK}; font-size: 22px; font-weight: 700; }}
QLabel#Subtitle {{ color: {MUTED}; font-size: 12px; }}
QLabel#Eyebrow {{ color: {FAINT}; font-size: 11px; font-weight: 600; letter-spacing: 2px; }}
QLabel#FieldLabel {{ color: {INK_2}; font-size: 13px; font-weight: 500; }}
QLabel#Help {{ color: {FAINT}; font-size: 12px; }}
QLabel#Placeholder {{ color: {PLACEHOLDER}; font-size: 13px; }}
QLabel#Status {{ color: {INK_2}; font-size: 14px; font-weight: 500; }}
QLabel#Pct {{ color: {CHIP_INK}; font-size: 14px; font-weight: 600; }}
QLabel#Logo {{
    color: white; font-size: 18px; font-weight: 700;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {ACCENT_A}, stop:1 {ACCENT_B});
    border-radius: 16px;
}}

QLineEdit, QComboBox {{
    background: rgba(255,255,255,215);
    border: 1px solid rgba(148,163,184,90);
    border-radius: 12px;
    padding: 6px 12px 6px 14px;
    font-size: 13px;
    color: {INK};
    selection-background-color: {ACCENT_A};
}}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {ACCENT_A}; }}
QLineEdit:disabled, QComboBox:disabled {{ color: {PLACEHOLDER}; }}
QLineEdit:read-only {{ color: {MUTED}; }}
QComboBox::drop-down {{ border: 0; width: 32px; }}
QComboBox::down-arrow {{ image: url("{{CHEVRON}}"); width: 12px; height: 12px; margin-right: 12px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 6px 2px; }}
QScrollBar::handle:vertical {{ background: rgba(100,116,139,90); border-radius: 3px; min-height: 40px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QComboBox QAbstractItemView {{
    background: white; color: {INK}; border: 1px solid rgba(148,163,184,120); border-radius: 10px;
    padding: 6px; outline: 0; selection-background-color: #eef2ff; selection-color: {INK};
}}
QComboBox QAbstractItemView::item {{
    color: {INK}; min-height: 28px; padding: 5px 10px;
}}
QComboBox QAbstractItemView::item:hover {{
    color: {INK}; background: #f8fafc;
}}

QPushButton {{
    font-size: 13px; font-weight: 600; color: {INK_2};
    background: rgba(255,255,255,205);
    border: 1px solid rgba(255,255,255,255);
    border-radius: 12px;
    padding: 6px 14px;
}}
QPushButton:hover {{ background: rgba(255,255,255,240); }}
QPushButton:pressed {{ background: rgba(255,255,255,160); }}
QPushButton:disabled {{ color: {PLACEHOLDER}; background: rgba(255,255,255,100); }}

QPushButton#Step {{
    min-width: 24px; max-width: 24px; min-height: 24px; max-height: 24px;
    padding: 0; border: 0; border-radius: 8px;
    background: #eef2ff; color: {CHIP_INK}; font-size: 15px;
}}
QPushButton#Step:hover {{ background: #e0e7ff; }}
QPushButton#Eye {{ border: 0; background: transparent; padding: 0 6px; color: {FAINT}; font-size: 14px; }}

QPushButton#Primary {{
    color: white; font-size: 14px; padding: 9px 22px; border: 0; border-radius: 12px;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT_A}, stop:1 {ACCENT_B});
}}
QPushButton#Primary:hover {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #6189ff, stop:1 #a56dff);
}}
QPushButton#Primary:disabled {{ color: rgba(255,255,255,170);
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #9db3ff, stop:1 #c4a8ff); }}
QPushButton#Ghost {{
    font-size: 13px; padding: 9px 18px; border-radius: 12px;
    background: rgba(255,255,255,100); border: 1px solid rgba(255,255,255,230);
}}
QPushButton#Ghost:disabled {{ color: {PLACEHOLDER}; }}
QPushButton#Finalize {{
    color: white; font-size: 14px; padding: 9px 18px; border: 0; border-radius: 12px;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #f59e0b, stop:1 #f97316);
}}
QPushButton#Finalize:hover {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #fbbf24, stop:1 #fb923c);
}}

QProgressBar {{
    background: rgba(148,163,184,65); border: 0; border-radius: 5px;
    min-height: 10px; max-height: 10px; text-align: center; color: transparent;
}}
QProgressBar::chunk {{
    border-radius: 5px;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT_A}, stop:1 {ACCENT_B});
}}
"""


# ---------------------------------------------------------------------------
# Jembatan thread worker -> thread UI
# ---------------------------------------------------------------------------
class Sinyal(QObject):
    status = Signal(str)
    progress = Signal(float)
    data = Signal(str)
    peringatan = Signal(str, str)
    selesai = Signal(str, bool)
    editor_terdeteksi = Signal(dict)
    model_tersedia = Signal(list)
    editor_dibuka = Signal(str, bool)


class PekerjaDeteksiEditor(QThread):
    def __init__(self, sinyal):
        super().__init__()
        self.sinyal = sinyal

    def run(self):
        self.sinyal.editor_terdeteksi.emit(core.deteksi_editor())


# ---------------------------------------------------------------------------
# Widget kecil
# ---------------------------------------------------------------------------
def label(teks, nama=None, wrap=False):
    lbl = QLabel(teks)
    if nama:
        lbl.setObjectName(nama)
    if wrap:
        lbl.setWordWrap(True)
    return lbl


def bayangan(widget, blur=60, dy=24, alpha=30, warna="#1a2666"):
    efek = QGraphicsDropShadowEffect(widget)
    efek.setBlurRadius(blur)
    efek.setOffset(0, dy)
    c = QColor(warna)
    c.setAlpha(alpha)
    efek.setColor(c)
    widget.setGraphicsEffect(efek)


class Field(QWidget):
    """Label + widget isi + (opsional) teks bantuan."""

    def __init__(self, judul, isi, bantuan=None):
        super().__init__()
        tata = QVBoxLayout(self)
        tata.setContentsMargins(0, 0, 0, 0)
        tata.setSpacing(6)
        tata.addWidget(label(judul, "FieldLabel"))
        tata.addWidget(isi)
        self.help = None
        if bantuan is not None:
            self.help = label(bantuan, "Help", wrap=True)
            tata.addWidget(self.help)


# ---------------------------------------------------------------------------
# Efek kaca Windows (acrylic blur di belakang jendela)
# ---------------------------------------------------------------------------
import ctypes
from ctypes import wintypes


class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [("AccentState", ctypes.c_int), ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_uint), ("AnimationId", ctypes.c_int)]


class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [("Attribute", ctypes.c_int), ("Data", ctypes.c_void_p), ("SizeOfData", ctypes.c_size_t)]


def aktifkan_acrylic(hwnd, warna_abgr=0x99F4F6FB):
    """Acrylic (Win10 1803+) dengan fallback blur biasa. Warna ABGR: alpha di byte tertinggi."""
    if os.name != "nt":
        return False
    try:
        set_attr = ctypes.windll.user32.SetWindowCompositionAttribute
        for state in (4, 3):  # 4 = ACRYLICBLURBEHIND, 3 = BLURBEHIND
            policy = ACCENT_POLICY(state, 2, warna_abgr, 0)
            data = WINDOWCOMPOSITIONATTRIBDATA(19, ctypes.addressof(policy), ctypes.sizeof(policy))
            if set_attr(wintypes.HWND(hwnd), ctypes.byref(data)):
                return True
    except Exception as error:
        print(f"Acrylic tidak tersedia: {error}")
    return False


# ---------------------------------------------------------------------------
# Jendela utama
# ---------------------------------------------------------------------------
class JendelaSortir(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sortir AI | Editor Foto")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumWidth(700)
        self.resize(740, 760)

        self.sinyal = Sinyal()
        self.penyortir = core.PenyortirFoto(core.Laporan(
            status=self.sinyal.status.emit,
            progress=self.sinyal.progress.emit,
            data=self.sinyal.data.emit,
            peringatan=self.sinyal.peringatan.emit,
            selesai=self.sinyal.selesai.emit,
        ))
        self.folder = ""
        self.editor_terdeteksi = {}
        self.api_tersimpan = False

        self._bangun_ui()
        self.entry_api.installEventFilter(self)
        self.entry_target.installEventFilter(self)
        self._sambung_sinyal()
        self._muat_login()

        self.pekerja_editor = PekerjaDeteksiEditor(self.sinyal)
        self.pekerja_editor.start()

    # ---- pembangunan UI -------------------------------------------------
    def _bangun_ui(self):
        card = QFrame()
        card.setObjectName("Card")
        self.card = card
        self.setCentralWidget(card)
        tata = QVBoxLayout(card)
        tata.setContentsMargins(20, 16, 20, 16)
        tata.setSpacing(12)

        # Header
        header = QHBoxLayout()
        header.setSpacing(16)
        logo = label("✦", "Logo")
        logo.setFixedSize(44, 44)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(logo)
        judul = QVBoxLayout()
        judul.setSpacing(2)
        judul.addWidget(label("Sortir AI", "Title"))
        judul.addWidget(label("Pilih foto terbaik lalu buka hasilnya di editor pilihan", "Subtitle"))
        header.addLayout(judul, 1)
        tata.addLayout(header)

        # Panel konfigurasi
        panel = QFrame()
        panel.setObjectName("Panel")
        tata.addWidget(panel)
        konf = QVBoxLayout(panel)
        konf.setContentsMargins(16, 14, 16, 14)
        konf.setSpacing(10)
        konf.addWidget(label("KONFIGURASI", "Eyebrow"))

        # API key
        self.entry_api = QLineEdit()
        self.entry_api.setEchoMode(QLineEdit.EchoMode.Password)
        self.entry_api.setPlaceholderText("Tempel API key Gemini di sini")
        self.tombol_mata = QPushButton()
        self.tombol_mata.setObjectName("Eye")
        self.tombol_mata.setIcon(buat_ikon_mata(False))
        self.tombol_mata.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tombol_mata.setToolTip("Tampilkan / sembunyikan API key")
        self.tombol_mata.clicked.connect(self._toggle_mata)
        baris_api = QHBoxLayout()
        baris_api.setContentsMargins(0, 0, 0, 0)
        baris_api.setSpacing(0)
        kotak_api = QWidget()
        kotak_api.setLayout(baris_api)
        baris_api.addWidget(self.entry_api, 1)
        baris_api.addWidget(self.tombol_mata)
        self.tombol_mata.setParent(self.entry_api)  # menempel di dalam kotak input
        self.entry_api.setTextMargins(0, 0, 40, 0)

        self.tombol_login = QPushButton("🔑  Login / Simpan API")
        self.tombol_login.clicked.connect(self._kelola_login)
        self.label_kredensial = label("", "Help", wrap=True)
        baris_login = QHBoxLayout()
        baris_login.setSpacing(12)
        baris_login.addWidget(self.tombol_login)
        baris_login.addWidget(self.label_kredensial, 1)
        kotak_login = QWidget()
        kotak_login.setLayout(baris_login)
        baris_login.setContentsMargins(0, 0, 0, 0)

        field_api = Field("API Key Gemini", kotak_api)
        field_api.layout().addWidget(kotak_login)
        konf.addWidget(field_api)

        # Model
        self.pilihan_model = QComboBox()
        self.pilihan_model.setEditable(False)
        self.pilihan_model.addItems(core.MODEL_GEMINI_OPTIONS)
        self.field_model = Field("Model Gemini", self.pilihan_model, "Masukkan API key untuk memuat daftar model.")
        self.pilihan_model.currentTextChanged.connect(self._perbarui_bantuan_model)
        konf.addWidget(self.field_model)

        # Target
        self.entry_target = QLineEdit("15")
        self.entry_target.setTextMargins(0, 0, 66, 0)
        stepper = QWidget(self.entry_target)
        tata_step = QHBoxLayout(stepper)
        tata_step.setContentsMargins(0, 0, 0, 0)
        tata_step.setSpacing(4)
        for teks, delta in (("−", -1), ("+", 1)):
            b = QPushButton(teks)
            b.setObjectName("Step")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _c=False, d=delta: self._ubah_target(d))
            tata_step.addWidget(b)
        self.stepper = stepper
        konf.addWidget(Field(
            "Target foto Excellent", self.entry_target,
            "Jumlah tidak boleh melebihi total foto JPEG ataupun RAW di folder.",
        ))

        # Folder
        self.tombol_folder = QPushButton("📁  Pilih folder")
        self.tombol_folder.clicked.connect(self._pilih_folder)
        self.label_folder = label(TEKS_FOLDER_KOSONG, "Placeholder", wrap=True)
        baris_folder = QHBoxLayout()
        baris_folder.setContentsMargins(0, 0, 0, 0)
        baris_folder.setSpacing(12)
        baris_folder.addWidget(self.tombol_folder)
        baris_folder.addWidget(self.label_folder, 1)
        kotak_folder = QWidget()
        kotak_folder.setLayout(baris_folder)
        konf.addWidget(Field("Folder foto", kotak_folder))

        # Editor
        self.pilihan_editor = QComboBox()
        self.pilihan_editor.setEditable(False)
        self.pilihan_editor.addItem("Mendeteksi editor...")
        self.pilihan_editor.setEnabled(False)
        self.pilihan_editor.currentTextChanged.connect(self._perbarui_tombol_editor)
        self.field_editor = Field("Aplikasi editing", self.pilihan_editor, "Mencari editor yang terpasang di Windows...")
        konf.addWidget(self.field_editor)

        # Panel status
        panel_status = QFrame()
        panel_status.setObjectName("Panel")
        tata.addWidget(panel_status)
        stat = QVBoxLayout(panel_status)
        stat.setContentsMargins(16, 12, 16, 12)
        stat.setSpacing(8)
        baris_status = QHBoxLayout()
        baris_status.setSpacing(8)
        self.titik = QLabel()
        self.titik.setFixedSize(8, 8)
        self._set_titik("#22c55e")
        self.label_status = label("Siap memulai.", "Status", wrap=True)
        self.label_persen = label("0%", "Pct")
        baris_status.addWidget(self.titik)
        baris_status.addWidget(self.label_status, 1)
        baris_status.addWidget(self.label_persen)
        stat.addLayout(baris_status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        stat.addWidget(self.progress)
        self.label_data = label("Data salinan AI: 0 B", "Help")
        stat.addWidget(self.label_data)

        # Aksi
        aksi = QHBoxLayout()
        aksi.setSpacing(12)
        aksi.addStretch(1)
        self.tombol_editor = QPushButton("Buka editor")
        self.tombol_editor.setObjectName("Finalize")
        self.tombol_editor.clicked.connect(self._buka_editor)
        self.tombol_editor.hide()
        self.tombol_batal = QPushButton("Batalkan")
        self.tombol_batal.setObjectName("Ghost")
        self.tombol_batal.setEnabled(False)
        self.tombol_batal.clicked.connect(self._batalkan)
        self.tombol_mulai = QPushButton("✦  Mulai sortir")
        self.tombol_mulai.setObjectName("Primary")
        self.tombol_mulai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tombol_mulai.clicked.connect(self._mulai)
        bayangan(self.tombol_mulai, blur=24, dy=10, alpha=115, warna=ACCENT_A)
        for b in (self.tombol_editor, self.tombol_batal, self.tombol_mulai):
            aksi.addWidget(b)
        tata.addLayout(aksi)

    def showEvent(self, event):
        super().showEvent(event)
        aktifkan_acrylic(int(self.winId()))
        if not getattr(self, "_sudah_dipusatkan", False):
            self._sudah_dipusatkan = True
            layar = self.screen().availableGeometry()
            self.adjustSize()
            self.resize(max(740, self.width()), self.height())
            self.move(layar.center().x() - self.width() // 2,
                      max(layar.top(), layar.center().y() - self.height() // 2))

    def eventFilter(self, obj, event):
        if event.type() == event.Type.Resize:
            self._letakkan_overlay()
        return super().eventFilter(obj, event)

    def _letakkan_overlay(self):
        # Tombol mata dan stepper menempel di sisi kanan-dalam kotak input.
        r = self.entry_api.rect()
        self.tombol_mata.setFixedSize(30, max(20, r.height() - 8))
        self.tombol_mata.move(r.right() - 40, 4)
        r = self.entry_target.rect()
        self.stepper.adjustSize()
        self.stepper.move(r.right() - self.stepper.width() - 12, (r.height() - self.stepper.height()) // 2)

    def _set_titik(self, warna):
        self.titik.setStyleSheet(f"background:{warna}; border-radius:4px;")

    # ---- sinyal ---------------------------------------------------------
    def _sambung_sinyal(self):
        s = self.sinyal
        s.status.connect(self.label_status.setText)
        s.progress.connect(self._atur_progress)
        s.data.connect(self.label_data.setText)
        s.peringatan.connect(lambda judul, pesan: QMessageBox.warning(self, judul, pesan))
        s.selesai.connect(self._tandai_selesai)
        s.editor_terdeteksi.connect(self._pasang_editor)
        s.model_tersedia.connect(self._pasang_model)
        s.editor_dibuka.connect(self._editor_dibuka)

    def _atur_progress(self, persen):
        self.progress.setValue(int(persen))
        self.label_persen.setText(f"{int(persen)}%")

    # ---- login ----------------------------------------------------------
    def _muat_login(self):
        login = core.baca_login() or {}
        api_key = login.get("api_key", "")
        model = login.get("model", os.getenv("GEMINI_MODEL", core.MODEL_GEMINI_DEFAULT))
        if api_key:
            teks = "Login API tersambung dari penyimpanan Windows."
            self.api_tersimpan = True
        else:
            api_key = os.getenv("GEMINI_API_KEY", "").strip()
            teks = ("API key tersambung dari variabel GEMINI_API_KEY."
                    if api_key else
                    "Masukkan API key lalu login; key disimpan terenkripsi oleh Windows.")
        self.entry_api.setText(api_key)
        self.label_kredensial.setText(teks)
        if self.api_tersimpan:
            self.entry_api.setReadOnly(True)
            self.entry_api.setEchoMode(QLineEdit.EchoMode.Password)
            self.tombol_mata.setEnabled(False)
            self.tombol_login.setText("Logout / Ganti API")
        if model in core.MODEL_GEMINI_OPTIONS:
            self.pilihan_model.setCurrentText(model)
        if api_key:
            self._muat_model(api_key)

    def _kelola_login(self):
        if self.api_tersimpan:
            core.hapus_login()
            self.api_tersimpan = False
            self.entry_api.setReadOnly(False)
            self.tombol_mata.setEnabled(True)
            self.tombol_login.setText("🔑  Login / Simpan API")
            self.label_kredensial.setText("Sesi dihapus. API key tetap tersedia di form dan belum tersimpan.")
            return
        api_key = self.entry_api.text().strip()
        if not api_key:
            QMessageBox.critical(self, "API key kosong", "Masukkan API key Gemini terlebih dahulu.")
            return
        try:
            core.simpan_login({"api_key": api_key, "model": self.pilihan_model.currentText()})
        except Exception as error:
            QMessageBox.critical(self, "Login gagal",
                                 "API key belum tersimpan. Pastikan aplikasi berjalan di Windows dan "
                                 f"memiliki izin menyimpan data login.\n\nDetail: {error}")
            return
        self.api_tersimpan = True
        self.entry_api.setReadOnly(True)
        self.entry_api.setEchoMode(QLineEdit.EchoMode.Password)
        self.tombol_mata.setEnabled(False)
        self.tombol_login.setText("Logout / Ganti API")
        self.label_kredensial.setText("Login tersimpan aman di Windows untuk akun ini.")
        self._muat_model(api_key)

    def _toggle_mata(self):
        sembunyi = self.entry_api.echoMode() == QLineEdit.EchoMode.Password
        self.entry_api.setEchoMode(QLineEdit.EchoMode.Normal if sembunyi else QLineEdit.EchoMode.Password)
        self.tombol_mata.setIcon(buat_ikon_mata(not sembunyi))

    def _muat_model(self, api_key):
        self.field_model.help.setText("Memuat daftar model Gemini...")

        def kerja():
            try:
                self.sinyal.model_tersedia.emit(core.daftar_model_vision(api_key))
            except Exception as error:
                print(f"Daftar model otomatis tidak tersedia: {error}")
                self.sinyal.model_tersedia.emit([])

        threading.Thread(target=kerja, daemon=True).start()

    def _pasang_model(self, daftar):
        if not daftar:
            self.pilihan_model.clear()
            self.pilihan_model.addItems(core.MODEL_GEMINI_OPTIONS)
            self.pilihan_model.setCurrentText(core.MODEL_GEMINI_DEFAULT)
            self.field_model.help.setText(
                "Daftar model API tidak dapat dimuat; memakai model terbaru bawaan. "
                "Pastikan API key dan koneksi internet tersedia."
            )
            self._perbarui_bantuan_model()
            return
        saat_ini = self.pilihan_model.currentText()
        self.pilihan_model.clear()
        self.pilihan_model.addItems(daftar)
        if saat_ini in daftar:
            self.pilihan_model.setCurrentText(saat_ini)
        elif core.MODEL_GEMINI_DEFAULT in daftar:
            self.pilihan_model.setCurrentText(core.MODEL_GEMINI_DEFAULT)
        self._perbarui_bantuan_model(jumlah_model=len(daftar))

    def _perbarui_bantuan_model(self, _model=None, jumlah_model=None):
        """Tampilkan panduan model dan ukuran batch sesuai pilihan pengguna."""
        nama_model = self.pilihan_model.currentText().lower()
        jumlah_foto = len(core.daftar_foto(self.folder)) if self.folder else 0
        if "pro" in nama_model:
            panduan = "Baik digunakan apabila kualitas penilaian paling penting."
            batch = "Aplikasi otomatis memakai 6 foto per batch; proses lebih lambat dan lebih mudah timeout."
        elif "lite" in nama_model:
            panduan = "Baik digunakan apabila ingin proses cepat dan hemat untuk folder besar."
            batch = "Aplikasi otomatis memakai 18 foto per batch."
        elif "flash" in nama_model:
            panduan = "Baik digunakan untuk kurasi foto harian: seimbang antara kualitas dan kecepatan."
            batch = "Aplikasi otomatis memakai 10 foto per batch."
        else:
            panduan = "Model ini dapat digunakan untuk kurasi foto dengan output Excellent, Good, atau Bad."
            batch = "Aplikasi otomatis memakai batch kecil untuk mengurangi risiko timeout."
        if "latest" in nama_model:
            panduan += " Alias latest mengikuti versi terbaru dan perilakunya dapat berubah."
        if jumlah_foto:
            batch += f" Folder saat ini berisi {jumlah_foto} foto."
        if jumlah_model is not None:
            batch += f" {jumlah_model} model vision tersedia."
        self.field_model.help.setText(f"{panduan} {batch}")

    # ---- form -------------------------------------------------------------
    def _ubah_target(self, delta):
        try:
            nilai = int(self.entry_target.text())
        except ValueError:
            nilai = 0
        self.entry_target.setText(str(max(1, nilai + delta)))

    def _pilih_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Pilih folder foto", self.folder or os.path.expanduser("~"))
        if not folder:
            return
        self.folder = os.path.normpath(folder)
        jumlah = len(core.daftar_foto(self.folder))
        self.label_folder.setText(f"{self.folder}  ·  {jumlah} foto")
        self.label_folder.setObjectName("Help")
        self.label_folder.style().unpolish(self.label_folder)
        self.label_folder.style().polish(self.label_folder)
        self._perbarui_bantuan_model()

    def _pasang_editor(self, editor):
        self.editor_terdeteksi = editor
        self.pilihan_editor.clear()
        if editor:
            self.pilihan_editor.addItems(list(editor))
            self.pilihan_editor.setEnabled(True)
            self.field_editor.help.setText(f"{len(editor)} editor terdeteksi di Windows.")
        else:
            self.pilihan_editor.addItem("Tidak ada editor terdeteksi")
            self.field_editor.help.setText("Tidak ada editor umum yang terdeteksi di lokasi instalasi Windows.")
        self._perbarui_tombol_editor()

    def _perbarui_tombol_editor(self, _teks=None):
        nama = self.pilihan_editor.currentText() if self.editor_terdeteksi else ""
        self.tombol_editor.setText(f"Buka {nama}" if nama else "Buka editor")
        self.tombol_editor.setEnabled(bool(nama))

    # ---- proses -----------------------------------------------------------
    def _atur_kontrol(self, sedang_proses):
        for w in (self.pilihan_model, self.pilihan_editor, self.entry_target,
                  self.tombol_folder, self.tombol_login, self.stepper):
            w.setEnabled(not sedang_proses)
        self.entry_api.setEnabled(not sedang_proses)
        self.tombol_mulai.setEnabled(not sedang_proses)
        self.tombol_batal.setEnabled(sedang_proses)
        self.tombol_editor.setEnabled(not sedang_proses and bool(self.editor_terdeteksi))
        if not sedang_proses:
            self.pilihan_editor.setEnabled(bool(self.editor_terdeteksi))

    def _mulai(self):
        api_key = self.entry_api.text().strip()
        target_teks = self.entry_target.text().strip()
        if not self.folder:
            QMessageBox.critical(self, "Folder belum dipilih", "Pilih folder foto terlebih dahulu.")
            return
        if not api_key:
            QMessageBox.critical(self, "API Key belum diisi", "Masukkan API Key Gemini terlebih dahulu.")
            return
        try:
            target = int(target_teks)
            if target < 1:
                raise ValueError
        except ValueError:
            QMessageBox.critical(self, "Target tidak valid", "Target foto harus berupa angka bulat minimal 1.")
            self.entry_target.setFocus()
            return
        jumlah_foto = len(core.daftar_foto(self.folder))
        if target > jumlah_foto:
            QMessageBox.critical(self, "Target terlalu besar",
                                 f"Folder hanya berisi {jumlah_foto} foto JPEG/RAW yang didukung.")
            self.entry_target.setFocus()
            return

        self._atur_kontrol(True)
        self.tombol_editor.hide()
        self._set_titik(ACCENT_A)
        self._atur_progress(0)
        self.label_data.setText("Data salinan AI: 0 B")
        self.penyortir.mulai(self.folder, api_key, target, self.pilihan_model.currentText())

    def _batalkan(self):
        if not self.penyortir.sedang_berjalan:
            return
        self.penyortir.batalkan()
        self.tombol_batal.setEnabled(False)
        self.label_status.setText("Stop diminta. Menunggu batch aktif selesai...")

    def _tandai_selesai(self, teks, sukses):
        self.label_status.setText(teks)
        self._set_titik("#22c55e" if sukses else "#f59e0b")
        self._atur_kontrol(False)
        if sukses:
            self.tombol_editor.show()
            QMessageBox.information(self, "Sortir selesai", teks)

    # ---- editor -----------------------------------------------------------
    def _buka_editor(self):
        nama = self.pilihan_editor.currentText()
        executable = self.editor_terdeteksi.get(nama)
        if not nama or not executable:
            QMessageBox.critical(self, "Editor tidak ditemukan", "Tidak ada editor yang bisa dibuka.")
            return
        if not self.folder:
            QMessageBox.warning(self, "Folder belum dipilih", "Pilih folder foto terlebih dahulu.")
            return
        self.tombol_editor.setEnabled(False)
        self.label_status.setText(f"Membuka {nama}...")

        def kerja():
            try:
                self.sinyal.editor_dibuka.emit(core.buka_editor(nama, self.folder, executable), True)
            except Exception as error:
                self.sinyal.editor_dibuka.emit(f"{nama} gagal dibuka: {error}", False)

        threading.Thread(target=kerja, daemon=True).start()

    def _editor_dibuka(self, pesan, sukses):
        self.label_status.setText(pesan)
        self.tombol_editor.setEnabled(True)
        if not sukses:
            QMessageBox.critical(self, "Editor gagal dibuka", pesan)

    def closeEvent(self, event):
        if self.penyortir.sedang_berjalan:
            jawab = QMessageBox.question(self, "Proses masih berjalan",
                                         "Sortir masih berjalan. Tutup aplikasi dan batalkan proses?")
            if jawab != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.penyortir.batalkan()
        event.accept()


def buat_ikon_mata(dicoret):
    pix = QPixmap(24, 24)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(FAINT))
    pen.setWidth(2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.drawEllipse(4, 7, 16, 10)
    painter.setBrush(QColor(FAINT))
    painter.drawEllipse(10, 10, 4, 4)
    if dicoret:
        painter.drawLine(4, 4, 20, 20)
    painter.end()
    return QIcon(pix)


def buat_ikon_chevron():
    """Gambar ikon panah dropdown ke file sementara (stylesheet Qt butuh path file)."""
    import tempfile
    from PySide6.QtGui import QPen, QPixmap
    path = os.path.join(tempfile.gettempdir(), "sortir_ai_chevron.png")
    pix = QPixmap(24, 24)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(FAINT))
    pen.setWidth(3)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(6, 9, 12, 15)
    p.drawLine(12, 15, 18, 9)
    p.end()
    pix.save(path, "PNG")
    return path.replace("\\", "/")


def stylesheet():
    return STYLESHEET.replace("{CHEVRON}", buat_ikon_chevron())


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(stylesheet())
    app.setFont(QFont("Segoe UI", 10))
    jendela = JendelaSortir()
    jendela.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
