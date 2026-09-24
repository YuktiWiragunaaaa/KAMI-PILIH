"""Sortir AI — antarmuka PySide6 bergaya organik: latar krem dengan gumpalan warna lembut,
kartu susu, aksen matcha + koral. Logika sortir ada di inti.py."""

import ctypes
import math
import os
import re
import sys
import threading

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSettings,
    QSize,
    Qt,
    QThread,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QButtonGroup,
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
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from . import inti as core

PATH_IKON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aset", "ikon.ico")
PILIHAN_TARGET = (15, 30, 50, 100)

# ---------------------------------------------------------------------------
# Palet organik (mode terang)
# ---------------------------------------------------------------------------
KREM = "#FBF7F0"
PASIR = "#F3EEE5"
INK = "#23201B"
MUTED = "#6F695F"
FAINT = "#9C958A"
MATCHA = "#3D7A5A"
MATCHA_MUDA = "#E3EFE6"
KORAL = "#EE6C4D"
KORAL_MUDA = "#FDE7DF"
AMBER = "#E3A33B"

STYLESHEET = f"""
* {{ font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif; color: {INK}; }}
QLabel {{ background: transparent; }}
QLabel#Title {{ font-family: "Segoe UI Variable Display", "Segoe UI"; font-size: 26px; font-weight: 700; }}
QLabel#Subtitle {{ color: {MUTED}; font-size: 13px; }}
QLabel#Section {{ font-family: "Segoe UI Variable Display", "Segoe UI"; font-size: 15px; font-weight: 600; }}
QLabel#FieldLabel {{ font-size: 12px; font-weight: 600; color: {MUTED}; }}
QLabel#Help {{ color: {FAINT}; font-size: 12px; }}
QLabel#Status {{ font-size: 14px; font-weight: 600; }}
QLabel#Pct {{ font-family: "Segoe UI Variable Display", "Segoe UI"; font-size: 22px; font-weight: 700; color: {MATCHA}; }}
QLabel#ZonaJudul {{ font-family: "Segoe UI Variable Display", "Segoe UI"; font-size: 17px; font-weight: 600; }}
QLabel#ZonaSub {{ color: {FAINT}; font-size: 12px; }}
QLabel#Badge {{ background: {MATCHA_MUDA}; color: {MATCHA}; border-radius: 11px; padding: 3px 10px;
               font-size: 12px; font-weight: 600; }}
QLabel#Hasil {{ border-radius: 13px; padding: 5px 12px; font-size: 13px; font-weight: 600; }}

QScrollArea, QWidget#Konten {{ background: transparent; border: 0; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 4px 0; }}
QScrollBar::handle:vertical {{ background: rgba(35,32,27,60); border-radius: 4px; min-height: 40px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QFrame#Kartu {{ background: rgba(255,255,255,205); border: 1px solid rgba(255,255,255,240); border-radius: 22px; }}

QLineEdit, QComboBox {{
    background: {PASIR}; border: 1px solid {PASIR}; border-radius: 12px;
    padding: 8px 12px; font-size: 13px; selection-background-color: {MATCHA};
}}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {MATCHA}; background: white; }}
QLineEdit:disabled, QComboBox:disabled {{ color: {FAINT}; }}
QLineEdit:read-only {{ color: {MUTED}; }}
QLineEdit#Angka {{ font-size: 15px; font-weight: 600; padding: 6px 4px; qproperty-alignment: AlignCenter; }}
QComboBox::drop-down {{ border: 0; width: 32px; }}
QComboBox::down-arrow {{ image: url("{{CHEVRON}}"); width: 12px; height: 12px; margin-right: 12px; }}
QComboBox QAbstractItemView {{
    background: white; border: 1px solid #ECE6DB; border-radius: 12px; padding: 6px; outline: 0;
    selection-background-color: {MATCHA_MUDA}; selection-color: {INK};
}}
QComboBox QAbstractItemView::item {{ min-height: 28px; padding: 5px 10px; }}

QPushButton {{
    font-size: 13px; font-weight: 600; background: {PASIR}; border: 0;
    border-radius: 14px; padding: 7px 16px;
}}
QPushButton:hover {{ background: #EAE3D6; }}
QPushButton:pressed {{ background: #E2DACB; }}
QPushButton:disabled {{ color: {FAINT}; background: {PASIR}; }}

QPushButton#Chip {{ border-radius: 17px; padding: 8px 18px; background: rgba(255,255,255,170);
                    border: 1px solid #ECE6DB; font-size: 14px; }}
QPushButton#Chip:hover {{ border: 1px solid {MATCHA}; }}
QPushButton#Chip:checked {{ background: {INK}; color: {KREM}; border: 1px solid {INK}; }}
QPushButton#Chip:disabled {{ color: {FAINT}; }}
QPushButton#Bulat {{ min-width: 34px; max-width: 34px; min-height: 34px; max-height: 34px;
                     padding: 0; border-radius: 17px; font-size: 16px; background: {PASIR}; }}
QPushButton#Bulat:checked {{ background: {INK}; color: {KREM}; }}
QPushButton#Eye {{ border: 0; background: transparent; padding: 0 6px; }}
QPushButton#Tautan {{ background: transparent; color: {MATCHA}; padding: 4px 2px; border-radius: 6px; }}
QPushButton#Tautan:hover {{ color: {INK}; background: transparent; }}
QPushButton#Tautan:disabled {{ color: {FAINT}; background: transparent; }}

QPushButton#Primary {{
    color: {KREM}; font-family: "Segoe UI Variable Display", "Segoe UI"; font-size: 15px;
    padding: 0 30px; border-radius: 23px; background: {INK};
}}
QPushButton#Primary:hover {{ background: #3A352D; }}
QPushButton#Primary:pressed {{ background: #000000; }}
QPushButton#Primary:disabled {{ color: rgba(251,247,240,150); background: #8F887C; }}
QPushButton#Ghost {{ padding: 0 20px; border-radius: 23px; background: rgba(255,255,255,170);
                     border: 1px solid #ECE6DB; }}
QPushButton#Ghost:hover {{ background: white; }}
QPushButton#Ghost:disabled {{ color: {FAINT}; background: rgba(255,255,255,90); }}
QPushButton#Finalize {{ color: white; font-size: 15px; padding: 0 24px; border-radius: 23px;
                        background: {KORAL}; }}
QPushButton#Finalize:hover {{ background: #F07F63; }}

QProgressBar {{ background: {PASIR}; border: 0; border-radius: 5px; min-height: 10px; max-height: 10px;
                color: transparent; }}
QProgressBar::chunk {{ border-radius: 5px;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #8CC7A1, stop:1 {MATCHA}); }}
QToolTip {{ background: {INK}; color: {KREM}; border: 0; padding: 6px 8px; border-radius: 6px; }}
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
    unduh_progres = Signal(int)
    unduh_selesai = Signal(str)  # "" = sukses, selain itu pesan galat


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


def bayangan(widget, blur=40, dy=12, alpha=22, warna="#5B4A2E"):
    efek = QGraphicsDropShadowEffect(widget)
    efek.setBlurRadius(blur)
    efek.setOffset(0, dy)
    c = QColor(warna)
    c.setAlpha(alpha)
    efek.setColor(c)
    widget.setGraphicsEffect(efek)


def kartu(jarak=18, tepi=(22, 20, 22, 20)):
    k = QFrame()
    k.setObjectName("Kartu")
    tata = QVBoxLayout(k)
    tata.setContentsMargins(*tepi)
    tata.setSpacing(jarak)
    bayangan(k)
    return k, tata


def segarkan_gaya(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class Field(QWidget):
    """Label kecil + widget isi + (opsional) teks bantuan."""

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


class Latar(QWidget):
    """Latar krem dengan gumpalan warna lembut; bergerak pelan saat `hidup` (sortir berjalan)."""

    GUMPALAN = (  # (x, y, jari-jari relatif, warna, fase)
        (0.05, 0.02, 0.62, (255, 204, 178), 0.0),   # peach
        (0.98, 0.30, 0.55, (196, 224, 202), 2.1),   # sage
        (0.10, 0.95, 0.60, (222, 212, 245), 4.2),   # lilac
        (0.90, 1.02, 0.45, (255, 236, 176), 1.3),   # mentega
    )

    def __init__(self):
        super().__init__()
        self._fase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._langkah)

    def hidup(self, nyala):
        self._timer.start() if nyala else self._timer.stop()

    def _langkah(self):
        self._fase += 0.035
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(KREM))
        w, h = self.width(), self.height()
        skala = max(w, h)
        for x, y, r, (cr, cg, cb), fase in self.GUMPALAN:
            cx = x * w + math.sin(self._fase + fase) * 0.04 * skala
            cy = y * h + math.cos(self._fase * 0.8 + fase) * 0.04 * skala
            g = QRadialGradient(QPointF(cx, cy), r * skala)
            g.setColorAt(0.0, QColor(cr, cg, cb, 170))
            g.setColorAt(0.55, QColor(cr, cg, cb, 60))
            g.setColorAt(1.0, QColor(cr, cg, cb, 0))
            p.fillRect(self.rect(), g)
        p.end()


class ZonaFolder(QFrame):
    """Area besar untuk memilih folder: klik atau tarik-lepas folder/foto ke sini."""

    diklik = Signal()
    dijatuhkan = Signal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(128)
        self._sorot = False
        tata = QVBoxLayout(self)
        tata.setContentsMargins(24, 20, 24, 20)
        tata.setSpacing(4)
        tata.addStretch(1)
        self.ikon = QLabel()
        self.ikon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ikon.setPixmap(buat_ikon_folder(MATCHA).pixmap(34, 34))
        self.judul = label("Tarik folder sesi ke sini", "ZonaJudul")
        self.judul.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub = label("atau klik buat pilih", "ZonaSub", wrap=True)
        self.sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge = label("", "Badge")
        self.badge.hide()
        baris_badge = QHBoxLayout()
        baris_badge.addStretch(1)
        baris_badge.addWidget(self.badge)
        baris_badge.addStretch(1)
        tata.addWidget(self.ikon)
        tata.addWidget(self.judul)
        tata.addWidget(self.sub)
        tata.addSpacing(4)
        tata.addLayout(baris_badge)
        tata.addStretch(1)

    def isi(self, judul, sub, badge=None, badge_ok=True):
        self.judul.setText(judul)
        self.sub.setText(sub)
        self.badge.setVisible(bool(badge))
        if badge:
            self.badge.setText(badge)
            self.badge.setStyleSheet("" if badge_ok else f"background:{KORAL_MUDA}; color:{KORAL};")

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        isi = QColor(MATCHA_MUDA) if self._sorot else QColor(255, 255, 255, 150)
        p.setBrush(isi)
        pena = QPen(QColor(MATCHA) if self._sorot else QColor("#CFC6B6"), 1.6)
        pena.setStyle(Qt.PenStyle.DashLine)
        pena.setDashPattern([5, 4])
        p.setPen(pena)
        p.drawRoundedRect(r, 20, 20)
        p.end()

    def _atur_sorot(self, nyala):
        self._sorot = nyala
        self.update()

    def enterEvent(self, e):
        if self.isEnabled():
            self._atur_sorot(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._atur_sorot(False)
        super().leaveEvent(e)

    def mouseReleaseEvent(self, e):
        if self.isEnabled() and e.button() == Qt.MouseButton.LeftButton:
            self.diklik.emit()

    @staticmethod
    def _folder_dari(mime):
        for url in mime.urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                return path
            if os.path.isfile(path):
                return os.path.dirname(path)
        return None

    def dragEnterEvent(self, e):
        if self.isEnabled() and self._folder_dari(e.mimeData()):
            e.acceptProposedAction()
            self._atur_sorot(True)

    def dragLeaveEvent(self, e):
        self._atur_sorot(False)

    def dropEvent(self, e):
        self._atur_sorot(False)
        folder = self._folder_dari(e.mimeData())
        if folder:
            self.dijatuhkan.emit(folder)


class Sakelar(QAbstractButton):
    """Sakelar on/off bergaya pil dengan kenop beranimasi."""

    def __init__(self):
        super().__init__()
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._posisi = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._geser)
        self.toggled.connect(self._animasikan)

    def sizeHint(self):
        return QSize(46, 28)

    def _geser(self, nilai):
        self._posisi = float(nilai)
        self.update()

    def _animasikan(self, nyala):
        self._anim.stop()
        self._anim.setStartValue(self._posisi)
        self._anim.setEndValue(1.0 if nyala else 0.0)
        self._anim.start()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(0.45)
        r = QRectF(0, 0, 46, 28)
        mati, nyala = QColor("#D9D2C5"), QColor(MATCHA)
        t = self._posisi
        warna = QColor(int(mati.red() + (nyala.red() - mati.red()) * t),
                       int(mati.green() + (nyala.green() - mati.green()) * t),
                       int(mati.blue() + (nyala.blue() - mati.blue()) * t))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(warna)
        p.drawRoundedRect(r, 14, 14)
        p.setBrush(QColor("white"))
        p.drawEllipse(QPointF(14 + 18 * t, 14), 11, 11)
        p.end()


# ---------------------------------------------------------------------------
# Jendela utama
# ---------------------------------------------------------------------------
class JendelaSortir(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sortir AI")
        self.setMinimumWidth(600)
        self.resize(620, 720)

        self.sinyal = Sinyal()
        self.penyortir = core.PenyortirFoto(core.Laporan(
            status=self.sinyal.status.emit,
            progress=self.sinyal.progress.emit,
            data=self.sinyal.data.emit,
            peringatan=self.sinyal.peringatan.emit,
            selesai=self.sinyal.selesai.emit,
        ))
        self.folder = ""
        self.jumlah_foto = 0
        self.editor_terdeteksi = {}
        self.api_tersimpan = False
        # Pilihan terakhir (model, editor, folder, target) disimpan di registry Windows (HKCU).
        self.pengaturan = QSettings("SortirAI", "SortirAI")
        self.model_tersimpan = self.pengaturan.value("model", "", str)

        self._bangun_ui()
        self.entry_api.installEventFilter(self)
        self._sambung_sinyal()
        self._muat_login()
        self._pulihkan_pilihan()

        self.pekerja_editor = PekerjaDeteksiEditor(self.sinyal)
        self.pekerja_editor.start()

    # ---- pembangunan UI -------------------------------------------------
    def _bangun_ui(self):
        self.latar = Latar()
        self.setCentralWidget(self.latar)
        luar = QVBoxLayout(self.latar)
        luar.setContentsMargins(20, 24, 20, 20)
        luar.setSpacing(12)
        # Isi bisa digulir bila layar pendek; tombol aksi di bawah selalu terlihat.
        self.gulir = QScrollArea()
        self.gulir.setWidgetResizable(True)
        self.gulir.setFrameShape(QFrame.Shape.NoFrame)
        self.gulir.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.gulir.viewport().setAutoFillBackground(False)
        self.konten = QWidget()
        self.konten.setObjectName("Konten")
        tata = QVBoxLayout(self.konten)
        tata.setContentsMargins(8, 0, 8, 12)  # ruang untuk bayangan kartu
        tata.setSpacing(16)
        self.gulir.setWidget(self.konten)
        luar.addWidget(self.gulir, 1)
        self.tata_luar = luar

        # Header
        header = QHBoxLayout()
        header.setSpacing(14)
        logo = QLabel()
        logo.setFixedSize(46, 46)
        logo.setPixmap(QIcon(PATH_IKON).pixmap(46, 46))
        header.addWidget(logo)
        judul = QVBoxLayout()
        judul.setSpacing(0)
        judul.addWidget(label("Sortir AI", "Title"))
        judul.addWidget(label("Pilih sesinya, biar AI yang kurasi.", "Subtitle"))
        header.addLayout(judul, 1)
        self.tombol_pengaturan = QPushButton()
        self.tombol_pengaturan.setObjectName("Bulat")
        self.tombol_pengaturan.setCheckable(True)
        ikon_gir = buat_ikon_gir(INK)
        ikon_gir.addPixmap(buat_ikon_gir(KREM).pixmap(48, 48), QIcon.Mode.Normal, QIcon.State.On)
        self.tombol_pengaturan.setIcon(ikon_gir)
        self.tombol_pengaturan.setIconSize(QSize(18, 18))
        self.tombol_pengaturan.setToolTip("Pengaturan")
        self.tombol_pengaturan.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tombol_pengaturan.toggled.connect(self._tampilkan_pengaturan)
        header.addWidget(self.tombol_pengaturan, 0, Qt.AlignmentFlag.AlignTop)
        tata.addLayout(header)

        # Kartu utama: folder + jumlah foto
        utama, isi = kartu(jarak=16)
        self.kartu_utama = utama
        tata.addWidget(utama)
        self.tombol_folder = ZonaFolder()  # nama lama dipertahankan: dipakai _atur_kontrol
        self.tombol_folder.diklik.connect(self._pilih_folder)
        self.tombol_folder.dijatuhkan.connect(self._folder_dijatuhkan)
        isi.addWidget(self.tombol_folder)

        isi.addWidget(label("Mau berapa foto terbaik?", "Section"))
        baris_target = QHBoxLayout()
        baris_target.setSpacing(8)
        self.grup_chip = QButtonGroup(self)
        self.grup_chip.setExclusive(False)  # angka manual boleh tidak cocok dengan chip mana pun
        self.chip_target = {}
        for n in PILIHAN_TARGET:
            chip = QPushButton(str(n))
            chip.setObjectName("Chip")
            chip.setCheckable(True)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.clicked.connect(lambda _c=False, nilai=n: self.entry_target.setText(str(nilai)))
            self.grup_chip.addButton(chip)
            self.chip_target[n] = chip
            baris_target.addWidget(chip)
        baris_target.addStretch(1)
        self.stepper = QWidget()
        tata_step = QHBoxLayout(self.stepper)
        tata_step.setContentsMargins(0, 0, 0, 0)
        tata_step.setSpacing(4)
        self.entry_target = QLineEdit("15")
        self.entry_target.setObjectName("Angka")
        self.entry_target.setFixedWidth(64)
        self.entry_target.textChanged.connect(self._sinkron_chip)
        for teks, delta in (("−", -1), (None, 0), ("+", 1)):
            if teks is None:
                tata_step.addWidget(self.entry_target)
                continue
            b = QPushButton(teks)
            b.setObjectName("Bulat")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setAutoRepeat(True)
            b.clicked.connect(lambda _c=False, d=delta: self._ubah_target(d))
            tata_step.addWidget(b)
        baris_target.addWidget(self.stepper)
        isi.addLayout(baris_target)

        self.label_ringkas = QPushButton("")
        self.label_ringkas.setObjectName("Tautan")
        self.label_ringkas.setCursor(Qt.CursorShape.PointingHandCursor)
        self.label_ringkas.setToolTip("Ubah pengaturan")
        self.label_ringkas.clicked.connect(lambda: self.tombol_pengaturan.setChecked(True))
        isi.addWidget(self.label_ringkas, 0, Qt.AlignmentFlag.AlignLeft)

        # Kartu pengaturan (tersembunyi; dibuka lewat tombol gir)
        self.panel_pengaturan, konf = kartu(jarak=14)
        self.panel_pengaturan.hide()
        tata.addWidget(self.panel_pengaturan)
        baris_judul = QHBoxLayout()
        baris_judul.addWidget(label("Pengaturan", "Section"), 1)
        kembali = QPushButton("← Kembali")
        kembali.setObjectName("Tautan")
        kembali.setCursor(Qt.CursorShape.PointingHandCursor)
        kembali.clicked.connect(lambda: self.tombol_pengaturan.setChecked(False))
        baris_judul.addWidget(kembali)
        konf.addLayout(baris_judul)

        self.entry_api = QLineEdit()
        self.entry_api.setEchoMode(QLineEdit.EchoMode.Password)
        self.entry_api.setPlaceholderText("Tempel API key Gemini di sini")
        self.entry_api.setTextMargins(0, 0, 36, 0)
        self.tombol_mata = QPushButton(self.entry_api)  # menempel di dalam kotak input
        self.tombol_mata.setObjectName("Eye")
        self.tombol_mata.setIcon(buat_ikon_mata(False))
        self.tombol_mata.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tombol_mata.setToolTip("Lihat / sembunyikan")
        self.tombol_mata.clicked.connect(self._toggle_mata)
        self.tombol_login = QPushButton("Simpan")
        self.tombol_login.clicked.connect(self._kelola_login)
        self.label_kredensial = label("", "Help", wrap=True)
        baris_api = QHBoxLayout()
        baris_api.setSpacing(8)
        baris_api.addWidget(self.entry_api, 1)
        baris_api.addWidget(self.tombol_login)
        kotak_api = QWidget()
        kotak_api.setLayout(baris_api)
        baris_api.setContentsMargins(0, 0, 0, 0)
        field_api = Field("API KEY GEMINI", kotak_api)
        field_api.layout().addWidget(self.label_kredensial)
        konf.addWidget(field_api)

        dua_kolom = QHBoxLayout()
        dua_kolom.setSpacing(12)
        self.pilihan_model = QComboBox()
        self.pilihan_model.addItems(core.MODEL_GEMINI_OPTIONS)
        self.field_model = Field("MODEL", self.pilihan_model, "Isi API key dulu.")
        self.pilihan_model.currentTextChanged.connect(self._perbarui_bantuan_model)
        dua_kolom.addWidget(self.field_model, 1)
        self.pilihan_editor = QComboBox()
        self.pilihan_editor.addItem("Mencari editor…")
        self.pilihan_editor.setEnabled(False)
        self.pilihan_editor.currentTextChanged.connect(self._perbarui_tombol_editor)
        self.field_editor = Field("BUKA HASIL DI", self.pilihan_editor, "Mencari editor…")
        dua_kolom.addWidget(self.field_editor, 1)
        konf.addLayout(dua_kolom)

        # Selera visual (model lanjutan): tidur sampai terbukti lebih akurat
        baris_selera = QHBoxLayout()
        baris_selera.setSpacing(12)
        self.tombol_visual = Sakelar()
        self.tombol_visual.clicked.connect(self._ubah_visual)
        teks_selera = QVBoxLayout()
        teks_selera.setSpacing(2)
        teks_selera.addWidget(label("Selera visual", "Status"))
        self.label_selera = label("Mengecek…", "Help", wrap=True)
        teks_selera.addWidget(self.label_selera)
        baris_selera.addWidget(self.tombol_visual, 0, Qt.AlignmentFlag.AlignTop)
        baris_selera.addLayout(teks_selera, 1)
        self.tombol_unduh_visual = QPushButton("Unduh model visual (89 MB)")
        self.tombol_unduh_visual.clicked.connect(self._unduh_visual)
        self.tombol_unduh_visual.hide()
        baris_selera.addWidget(self.tombol_unduh_visual, 0, Qt.AlignmentFlag.AlignTop)
        self.tombol_selera_baru = QPushButton("Mulai selera baru")
        self.tombol_selera_baru.setObjectName("Tautan")
        self.tombol_selera_baru.setToolTip("Belajar dari nol. Selera lama disimpan di 1 slot arsip.")
        self.tombol_selera_baru.clicked.connect(self._selera_baru)
        baris_selera.addWidget(self.tombol_selera_baru, 0, Qt.AlignmentFlag.AlignTop)
        konf.addLayout(baris_selera)

        # Kartu status
        panel_status, stat = kartu(jarak=10, tepi=(22, 16, 22, 16))
        tata.addWidget(panel_status)
        baris_status = QHBoxLayout()
        baris_status.setSpacing(10)
        self.titik = QLabel()
        self.titik.setFixedSize(10, 10)
        self._set_titik(MATCHA)
        self.label_status = label("Siap jalan.", "Status", wrap=True)
        self.label_persen = label("", "Pct")
        baris_status.addWidget(self.titik)
        baris_status.addWidget(self.label_status, 1)
        baris_status.addWidget(self.label_persen)
        stat.addLayout(baris_status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self._anim_progress = QPropertyAnimation(self.progress, b"value", self)
        self._anim_progress.setDuration(450)
        self._anim_progress.setEasingCurve(QEasingCurve.Type.OutCubic)
        stat.addWidget(self.progress)
        self.baris_hasil = QWidget()
        tata_hasil = QHBoxLayout(self.baris_hasil)
        tata_hasil.setContentsMargins(0, 2, 0, 0)
        tata_hasil.setSpacing(8)
        self.chip_hasil = {}
        for nama, latar_, tinta in (("Excellent", KORAL_MUDA, KORAL), ("Good", MATCHA_MUDA, MATCHA),
                                    ("Bad", PASIR, MUTED)):
            chip = label("", "Hasil")
            chip.setStyleSheet(f"background:{latar_}; color:{tinta};")
            self.chip_hasil[nama] = chip
            tata_hasil.addWidget(chip)
        tata_hasil.addStretch(1)
        self.baris_hasil.hide()
        stat.addWidget(self.baris_hasil)
        self.label_data = label("", "Help", wrap=True)
        self.label_data.hide()
        stat.addWidget(self.label_data)

        tata.addStretch(1)

        # Aksi
        aksi = QHBoxLayout()
        aksi.setSpacing(10)
        aksi.setContentsMargins(8, 0, 8, 0)  # sejajar dengan tepi kartu di area gulir
        self.tombol_belajar = QPushButton("Pelajari koreksi")
        self.tombol_belajar.setObjectName("Ghost")
        self.tombol_belajar.setToolTip("Sudah ubah rating di editor? Klik biar AI belajar seleramu.")
        self.tombol_belajar.clicked.connect(self._pelajari_koreksi)
        aksi.addWidget(self.tombol_belajar)
        aksi.addStretch(1)
        self.tombol_batal = QPushButton("Batal")
        self.tombol_batal.setObjectName("Ghost")
        self.tombol_batal.clicked.connect(self._batalkan)
        self.tombol_batal.hide()
        self.tombol_editor = QPushButton("Buka editor")
        self.tombol_editor.setObjectName("Finalize")
        self.tombol_editor.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tombol_editor.clicked.connect(self._buka_editor)
        self.tombol_editor.hide()
        self.tombol_mulai = QPushButton("Sortir sekarang  →")
        self.tombol_mulai.setObjectName("Primary")
        self.tombol_mulai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tombol_mulai.clicked.connect(self._mulai)
        bayangan(self.tombol_mulai, blur=28, dy=8, alpha=60, warna=INK)
        for b in (self.tombol_belajar, self.tombol_batal, self.tombol_editor, self.tombol_mulai):
            b.setFixedHeight(46)  # radius 23 = setengah tinggi: bentuk pil sempurna
        for b in (self.tombol_batal, self.tombol_editor, self.tombol_mulai):
            aksi.addWidget(b)
        luar.addLayout(aksi)
        self.tata_aksi = aksi

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_sudah_dipusatkan", False):
            self._sudah_dipusatkan = True
            self._pas_ukuran()
            layar = self.screen().availableGeometry()
            self.move(layar.center().x() - self.width() // 2,
                      max(layar.top(), layar.center().y() - self.height() // 2))

    def _pas_ukuran(self):
        """Tinggi jendela mengikuti isi (mis. saat pengaturan dibuka/ditutup)."""
        lebar = max(620, self.width())
        self.konten.layout().activate()
        m = self.tata_luar.contentsMargins()
        tinggi = (m.top() + m.bottom() + self.tata_luar.spacing() + self.tata_aksi.sizeHint().height()
                  + self.konten.layout().sizeHint().height() + 2)
        layar = self.screen().availableGeometry() if self.screen() else None
        if layar:  # jangan pernah melebihi layar; sisanya digulir
            tinggi = min(tinggi, layar.height() - 40)
            if self.y() + tinggi > layar.bottom():
                self.move(self.x(), max(layar.top(), layar.bottom() - tinggi - 30))
        self.resize(lebar, tinggi)

    def _tampilkan_pengaturan(self, nyala):
        # Pengaturan menggantikan kartu utama, bukan ditumpuk: tinggi jendela hampir tetap.
        self.kartu_utama.setVisible(not nyala)
        self.panel_pengaturan.setVisible(nyala)
        self.gulir.verticalScrollBar().setValue(0)
        QTimer.singleShot(0, self._pas_ukuran)

    def eventFilter(self, obj, event):
        if obj is self.entry_api and event.type() == event.Type.Resize:
            # Tombol mata menempel di sisi kanan-dalam kotak input.
            r = self.entry_api.rect()
            self.tombol_mata.setFixedSize(30, max(20, r.height() - 8))
            self.tombol_mata.move(r.right() - 34, 4)
        return super().eventFilter(obj, event)

    def _set_titik(self, warna):
        self.titik.setStyleSheet(f"background:{warna}; border-radius:5px;")

    def _perbarui_ringkas(self):
        bagian = [self.pilihan_model.currentText() or "model?"]
        if self.editor_terdeteksi:
            bagian.append(self.pilihan_editor.currentText())
        bagian.append("key tersimpan" if self.api_tersimpan else "key belum diisi")
        self.label_ringkas.setText("  ·  ".join(bagian) + "   ✎")

    # ---- sinyal ---------------------------------------------------------
    def _sambung_sinyal(self):
        s = self.sinyal
        s.status.connect(self.label_status.setText)
        s.progress.connect(self._atur_progress)
        s.data.connect(self._atur_data)
        s.peringatan.connect(lambda judul, pesan: QMessageBox.warning(self, judul, pesan))
        s.selesai.connect(self._tandai_selesai)
        s.editor_terdeteksi.connect(self._pasang_editor)
        s.model_tersedia.connect(self._pasang_model)
        s.unduh_progres.connect(lambda p: self.tombol_unduh_visual.setText(f"Mengunduh… {p}%"))
        s.unduh_selesai.connect(self._unduh_visual_selesai)
        s.editor_dibuka.connect(self._editor_dibuka)

    def _atur_data(self, teks):
        self.label_data.setText(teks)
        self.label_data.setVisible(bool(teks))

    def _atur_progress(self, persen, animasi=True):
        tujuan = int(persen * 10)
        self._anim_progress.stop()
        if animasi and tujuan > self.progress.value():
            self._anim_progress.setStartValue(self.progress.value())
            self._anim_progress.setEndValue(tujuan)
            self._anim_progress.start()
        else:
            self.progress.setValue(tujuan)
        self.label_persen.setText(f"{int(persen)}%")

    # ---- login ----------------------------------------------------------
    def _muat_login(self):
        login = core.baca_login() or {}
        api_key = login.get("api_key", "")
        model = login.get("model", os.getenv("GEMINI_MODEL", core.MODEL_GEMINI_DEFAULT))
        if api_key:
            teks = "Tersimpan aman di Windows ✓"
            self.api_tersimpan = True
        else:
            api_key = os.getenv("GEMINI_API_KEY", "").strip()
            teks = ("Dari variabel GEMINI_API_KEY" if api_key else
                    "Buat gratis di aistudio.google.com, lalu tempel di sini.")
        self.entry_api.setText(api_key)
        self.label_kredensial.setText(teks)
        if self.api_tersimpan:
            self.entry_api.setReadOnly(True)
            self.entry_api.setEchoMode(QLineEdit.EchoMode.Password)
            self.tombol_mata.setEnabled(False)
            self.tombol_login.setText("Ganti")
        elif not api_key:
            self.tombol_pengaturan.setChecked(True)  # belum ada key: langsung tunjukkan tempatnya
        if model in core.MODEL_GEMINI_OPTIONS:
            self.pilihan_model.setCurrentText(model)
        if api_key:
            self._muat_model(api_key)
        self._perbarui_ringkas()

    def _kelola_login(self):
        if self.api_tersimpan:
            core.hapus_login()
            self.api_tersimpan = False
            self.entry_api.setReadOnly(False)
            self.tombol_mata.setEnabled(True)
            self.tombol_login.setText("Simpan")
            self.label_kredensial.setText("Key dihapus dari Windows. Tempel key baru.")
            self._perbarui_ringkas()
            return
        api_key = self.entry_api.text().strip()
        if not api_key:
            QMessageBox.critical(self, "API key kosong", "Tempel API key Gemini dulu.")
            return
        try:
            core.simpan_login({"api_key": api_key, "model": self.pilihan_model.currentText()})
        except Exception as error:
            QMessageBox.critical(self, "Gagal menyimpan",
                                 "API key belum tersimpan. Pastikan aplikasi berjalan di Windows dan "
                                 f"punya izin menyimpan data login.\n\nDetail: {error}")
            return
        self.api_tersimpan = True
        self.entry_api.setReadOnly(True)
        self.entry_api.setEchoMode(QLineEdit.EchoMode.Password)
        self.tombol_mata.setEnabled(False)
        self.tombol_login.setText("Ganti")
        self.label_kredensial.setText("Tersimpan aman di Windows ✓")
        self._muat_model(api_key)
        self._perbarui_ringkas()

    def _toggle_mata(self):
        sembunyi = self.entry_api.echoMode() == QLineEdit.EchoMode.Password
        self.entry_api.setEchoMode(QLineEdit.EchoMode.Normal if sembunyi else QLineEdit.EchoMode.Password)
        self.tombol_mata.setIcon(buat_ikon_mata(not sembunyi))

    def _muat_model(self, api_key):
        self.field_model.help.setText("Memuat model…")

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
            self.field_model.help.setText("Gagal memuat daftar, pakai bawaan. Cek key & internet.")
            self._perbarui_ringkas()
            return
        saat_ini = self.pilihan_model.currentText()
        self.pilihan_model.clear()
        self.pilihan_model.addItems(daftar)
        if self.model_tersimpan in daftar:
            self.pilihan_model.setCurrentText(self.model_tersimpan)
        elif saat_ini in daftar:
            self.pilihan_model.setCurrentText(saat_ini)
        elif core.MODEL_GEMINI_DEFAULT in daftar:
            self.pilihan_model.setCurrentText(core.MODEL_GEMINI_DEFAULT)
        self._perbarui_bantuan_model(jumlah_model=len(daftar))

    def _perbarui_bantuan_model(self, _model=None, jumlah_model=None):
        """Panduan singkat sesuai model yang dipilih."""
        nama_model = self.pilihan_model.currentText().lower()
        if "pro" in nama_model:
            panduan = "Paling teliti, tapi lambat & mahal"
        elif "lite" in nama_model:
            panduan = "Paling cepat & hemat"
        elif "flash" in nama_model:
            panduan = "Seimbang"
        else:
            panduan = "Bisa dipakai"
        self.field_model.help.setText(f"{panduan} · {core.ukuran_batch_untuk_model(nama_model)} foto/panggilan")
        self._perbarui_ringkas()

    # ---- form -------------------------------------------------------------
    def _pulihkan_pilihan(self):
        target = self.pengaturan.value("target", "", str)
        if target.isdigit():
            self.entry_target.setText(target)
        self._sinkron_chip()
        folder = self.pengaturan.value("folder", "", str)
        if folder and os.path.isdir(folder):  # drive eksternal bisa sedang dicabut
            self._pasang_folder(folder)
        elif folder:
            self.folder = os.path.normpath(folder)  # tetap jadi titik awal dialog, tanpa dipilih
        self.pilihan_model.activated.connect(self._simpan_model)
        self._perbarui_selera()
        self.pilihan_editor.activated.connect(self._simpan_editor)

    def _simpan_model(self, _indeks=None):
        model = self.pilihan_model.currentText()
        if model:
            self.model_tersimpan = model
            self.pengaturan.setValue("model", model)

    def _simpan_editor(self, _indeks=None):
        self.pengaturan.setValue("editor", self.pilihan_editor.currentText())
        self._perbarui_ringkas()

    def _ubah_target(self, delta):
        try:
            nilai = int(self.entry_target.text())
        except ValueError:
            nilai = 0
        self.entry_target.setText(str(max(1, nilai + delta)))

    def _sinkron_chip(self, _teks=None):
        teks = self.entry_target.text().strip()
        for n, chip in self.chip_target.items():
            chip.setChecked(teks == str(n))

    def _pilih_folder(self):
        # Mulai dari induk folder terakhir: sesi foto baru biasanya bersebelahan.
        awal = os.path.dirname(self.folder) if self.folder else os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "Pilih folder foto", awal)
        if folder:
            self._folder_dijatuhkan(folder)

    def _folder_dijatuhkan(self, folder):
        self._pasang_folder(folder)
        self.pengaturan.setValue("folder", self.folder)

    def _pasang_folder(self, folder):
        self.folder = os.path.normpath(folder)
        self.jumlah_foto = jumlah = len(core.daftar_foto(self.folder))
        induk = os.path.dirname(self.folder)
        if jumlah:
            self.tombol_folder.isi(os.path.basename(self.folder) or self.folder, induk, f"{jumlah} foto")
        else:
            self.tombol_folder.isi(os.path.basename(self.folder) or self.folder, induk,
                                   "Nggak ada foto JPEG/RAW di sini", badge_ok=False)
        self.baris_hasil.hide()
        self.tombol_editor.hide()
        self._gaya_tombol_mulai(sekunder=False)

    def _gaya_tombol_mulai(self, sekunder):
        """Setelah selesai, 'Buka editor' jadi aksi utama dan sortir turun jadi sekunder."""
        self.tombol_mulai.setText("Sortir lagi" if sekunder else "Sortir sekarang  →")
        self.tombol_mulai.setObjectName("Ghost" if sekunder else "Primary")
        self.tombol_mulai.setGraphicsEffect(None)
        if not sekunder:
            bayangan(self.tombol_mulai, blur=28, dy=8, alpha=60, warna=INK)
        segarkan_gaya(self.tombol_mulai)

    def _pasang_editor(self, editor):
        # Baca dulu: addItems memicu penyimpanan item pertama dan akan menimpanya.
        tersimpan = self.pengaturan.value("editor", "", str)
        self.editor_terdeteksi = editor
        self.pilihan_editor.clear()
        if editor:
            self.pilihan_editor.addItems(list(editor))
            if tersimpan in editor:
                self.pilihan_editor.setCurrentText(tersimpan)
            self.pilihan_editor.setEnabled(True)
            self.field_editor.help.setText(f"{len(editor)} editor ditemukan")
        else:
            self.pilihan_editor.addItem("Tidak ada editor")
            self.field_editor.help.setText("Belum ada editor terpasang.")
        self._perbarui_tombol_editor()
        self._perbarui_ringkas()

    def _perbarui_tombol_editor(self, _teks=None):
        nama = self.pilihan_editor.currentText() if self.editor_terdeteksi else ""
        self.tombol_editor.setText(f"Buka di {nama}  →" if nama else "Buka editor")
        self.tombol_editor.setEnabled(bool(nama))

    # ---- proses -----------------------------------------------------------
    def _atur_kontrol(self, sedang_proses):
        for w in (self.pilihan_model, self.pilihan_editor, self.stepper, self.tombol_folder,
                  self.tombol_login, self.tombol_belajar, self.tombol_selera_baru, *self.chip_target.values()):
            w.setEnabled(not sedang_proses)
        self.entry_api.setEnabled(not sedang_proses)
        self.tombol_mulai.setVisible(not sedang_proses)
        self.tombol_batal.setVisible(sedang_proses)
        self.tombol_batal.setEnabled(sedang_proses)
        self.latar.hidup(sedang_proses)
        if not sedang_proses:
            self.pilihan_editor.setEnabled(bool(self.editor_terdeteksi))
            self._perbarui_selera()
        else:
            self.tombol_visual.setEnabled(False)

    def _mulai(self):
        api_key = self.entry_api.text().strip()
        target_teks = self.entry_target.text().strip()
        if not self.folder:
            QMessageBox.information(self, "Pilih folder dulu", "Tarik folder sesi ke kotak di atas, atau klik kotaknya.")
            return
        if not api_key:
            self.tombol_pengaturan.setChecked(True)
            self.entry_api.setFocus()
            QMessageBox.information(self, "API key belum ada", "Tempel API key Gemini di Pengaturan dulu.")
            return
        try:
            target = int(target_teks)
            if target < 1:
                raise ValueError
        except ValueError:
            QMessageBox.information(self, "Jumlah belum pas", "Jumlah foto terbaik harus angka, minimal 1.")
            self.entry_target.setFocus()
            return
        jumlah_foto = len(core.daftar_foto(self.folder))
        if target > jumlah_foto:
            QMessageBox.information(self, "Kebanyakan",
                                    f"Folder ini cuma berisi {jumlah_foto} foto JPEG/RAW.")
            self.entry_target.setFocus()
            return

        self._atur_kontrol(True)
        self.tombol_editor.hide()
        self.baris_hasil.hide()
        self._gaya_tombol_mulai(sekunder=False)
        self._set_titik(AMBER)
        self._atur_progress(0, animasi=False)
        self._atur_data("")
        self.label_status.setText("Mulai…")
        self.pengaturan.setValue("target", target)
        self._simpan_model()
        self.penyortir.mulai(self.folder, api_key, target, self.pilihan_model.currentText(),
                             pakai_visual=self._visual_aktif())

    def _batalkan(self):
        if not self.penyortir.sedang_berjalan:
            return
        self.penyortir.batalkan()
        self.tombol_batal.setEnabled(False)
        self.label_status.setText("Menghentikan…")

    def _tandai_selesai(self, teks, sukses):
        self._atur_kontrol(False)
        cocok = re.search(r"Excellent: (\d+) \| Good: (\d+) \| Bad: (\d+)", teks) if sukses else None
        if cocok:
            ex, good, bad = cocok.groups()
            self.chip_hasil["Excellent"].setText(f"★  {ex} Excellent")
            self.chip_hasil["Good"].setText(f"{good} Good")
            self.chip_hasil["Bad"].setText(f"{bad} Bad")
            self.baris_hasil.show()
            sisa = teks[cocok.end():].strip(" .")
            self.label_status.setText("Beres! " + (sisa + "." if sisa else "Tinggal cek di editor."))
        else:
            self.label_status.setText(teks)
        self._set_titik(MATCHA if sukses else KORAL)
        if sukses:
            self._atur_progress(100)
            self.tombol_editor.show()
            self._gaya_tombol_mulai(sekunder=bool(self.editor_terdeteksi))

    # ---- editor -----------------------------------------------------------
    def _buka_editor(self):
        nama = self.pilihan_editor.currentText()
        executable = self.editor_terdeteksi.get(nama)
        if not nama or not executable:
            QMessageBox.critical(self, "Editor tidak ditemukan", "Tidak ada editor yang bisa dibuka.")
            return
        if not self.folder:
            QMessageBox.warning(self, "Folder belum dipilih", "Pilih folder foto dulu.")
            return
        self.tombol_editor.setEnabled(False)
        self.label_status.setText(f"Membuka {nama}…")

        def kerja():
            try:
                self.sinyal.editor_dibuka.emit(core.buka_editor(nama, self.folder, executable), True)
            except Exception as error:
                self.sinyal.editor_dibuka.emit(f"{nama} gagal dibuka: {error}", False)

        threading.Thread(target=kerja, daemon=True).start()

    def _pelajari_koreksi(self):
        if not self.folder:
            QMessageBox.information(self, "Pilih folder dulu", "Pilih folder sesi yang sudah pernah disortir.")
            return
        from . import belajar
        try:
            tercatat, diubah = belajar.kumpulkan_koreksi(self.folder)
        except Exception as error:
            QMessageBox.critical(self, "Gagal mencatat koreksi", str(error))
            return
        if not tercatat:
            QMessageBox.information(self, "Belum ada data",
                                    "Folder ini belum pernah disortir dengan versi aplikasi ini, "
                                    "atau rating belum tersimpan ke file.")
            return
        from . import selera
        total, setuju = belajar.ringkasan()
        model = selera.latih()
        if model:
            nama = {"momen": "momen", "ekspresi": "ekspresi", "gestur": "gestur", "teknis": "teknis",
                    "skor": "skor AI", "ketajaman": "ketajaman", "kecerahan": "kecerahan",
                    "senyum": "senyum", "wajah": "jumlah wajah", "luas_wajah": "ukuran wajah"}
            aspek = ", ".join(f"{nama.get(k, k)} ({'lebih disukai' if t == '+' else 'kurang disukai'})"
                              for k, t in model.aspek_terpenting())
            info_selera = (f"Selera pribadi aktif (kepercayaan {round(model.kepercayaan * 100)}%).\n"
                           f"Paling memengaruhi pilihanmu: {aspek}.")
        else:
            info_selera = (f"Selera pribadi belum aktif: butuh minimal {selera.MIN_DATA} foto "
                           "yang sudah dinilai AI dan kamu review.")
        QMessageBox.information(
            self, "Koreksi tercatat",
            f"{tercatat} foto dicatat, {diubah} di antaranya kamu ubah.\n\n"
            f"Total data belajar: {total} foto. Kamu setuju dengan {setuju}% pilihan AI.\n\n"
            f"{info_selera}\n\n"
            "Di Lightroom, pastikan metadata disimpan ke file (Ctrl+S).")
        self._perbarui_selera(tawarkan=True)

    # ---- selera visual ---------------------------------------------------
    def _visual_aktif(self):
        return self.pengaturan.value("visual_aktif", False, bool)

    def _perbarui_selera(self, tawarkan=False):
        """Perbarui sakelar + teks bantuan; tampilkan popup sekali saat model visual siap."""
        from . import selera, visual
        if not visual.tersedia():
            self.tombol_visual.setEnabled(False)
            if not visual.onnxruntime_ada():
                self.tombol_unduh_visual.hide()
                self.label_selera.setText("Butuh onnxruntime. Buka lewat 'Buka Sortir AI.bat'.")
            else:
                self.tombol_unduh_visual.show()
                self.label_selera.setText("Opsional. Unduh sekali biar AI makin kenal gayamu.")
            return
        self.tombol_unduh_visual.hide()
        try:
            uji = selera.uji_visual()
        except Exception as error:
            print(f"Uji selera visual gagal: {error}")
            uji = {"siap": False, "jumlah": 0, "lebih_baik_persen": None}
        aktif = self._visual_aktif()
        self.tombol_visual.blockSignals(True)
        self.tombol_visual.setChecked(aktif)
        self.tombol_visual.blockSignals(False)
        self.tombol_visual._geser(1.0 if aktif else 0.0)
        self.tombol_visual.setEnabled(aktif or uji["siap"])
        if aktif:
            teks = f"Nyala · belajar dari {uji['jumlah']} foto"
        elif uji["siap"]:
            teks = f"Siap dinyalakan · {uji['lebih_baik_persen']}% lebih akurat"
        elif uji["jumlah"] < selera.MIN_DATA_VISUAL:
            teks = f"Masih belajar diam-diam · {uji['jumlah']}/{selera.MIN_DATA_VISUAL} foto"
        else:
            teks = "Data cukup, tapi belum lebih akurat. Dicek lagi nanti."
        self.label_selera.setText(teks)

        # Popup sekali; ditawarkan lagi setelah +500 foto bila tadi memilih "Nanti".
        ditawarkan = int(self.pengaturan.value("visual_ditawarkan", 0) or 0)
        if tawarkan and uji["siap"] and not aktif and (not ditawarkan or uji["jumlah"] >= ditawarkan + 500):
            self.pengaturan.setValue("visual_ditawarkan", uji["jumlah"])
            kotak = QMessageBox(self)
            kotak.setWindowTitle("Selera visual siap")
            kotak.setText(f"Selera visual menebak pilihanmu {uji['lebih_baik_persen']}% lebih akurat "
                          f"daripada model biasa ({uji['jumlah']} foto).\n\n"
                          "Nyalakan sekarang? Bisa dimatikan kapan saja di Pengaturan.")
            tombol_ya = kotak.addButton("Nyalakan", QMessageBox.ButtonRole.AcceptRole)
            kotak.addButton("Nanti", QMessageBox.ButtonRole.RejectRole)
            kotak.exec()
            if kotak.clickedButton() is tombol_ya:
                self.pengaturan.setValue("visual_aktif", True)
                self._perbarui_selera()

    def _unduh_visual(self):
        from . import visual
        jawab = QMessageBox.question(
            self, "Unduh model visual",
            "Unduh model CLIP (89 MB) dari Hugging Face (Xenova/clip-vit-base-patch32)?\n\n"
            f"Disimpan di: {visual.FILE_MODEL}")
        if jawab != QMessageBox.StandardButton.Yes:
            return
        self.tombol_unduh_visual.setEnabled(False)

        def kerja():
            try:
                visual.unduh_model(self.sinyal.unduh_progres.emit)
                self.sinyal.unduh_selesai.emit("")
            except Exception as error:
                self.sinyal.unduh_selesai.emit(f"{type(error).__name__}: {error}")

        threading.Thread(target=kerja, daemon=True).start()

    def _unduh_visual_selesai(self, galat):
        self.tombol_unduh_visual.setEnabled(True)
        self.tombol_unduh_visual.setText("Unduh model visual (89 MB)")
        if galat:
            QMessageBox.critical(self, "Unduhan gagal", f"Model visual gagal diunduh.\n\n{galat}")
        self._perbarui_selera()

    def _ubah_visual(self, nyala):
        self.pengaturan.setValue("visual_aktif", bool(nyala))
        self._perbarui_selera()

    def _selera_baru(self):
        from . import belajar
        kotak = QMessageBox(self)
        kotak.setWindowTitle("Selera baru")
        kotak.setText("Mulai belajar selera dari nol?\n\n"
                      "Data sekarang dipindah ke arsip (1 slot; arsip sebelumnya diganti). "
                      "AI belajar lagi dari koreksi berikutnya.")
        tombol_baru = kotak.addButton("Mulai selera baru", QMessageBox.ButtonRole.DestructiveRole)
        tombol_tukar = None
        if belajar.ada_arsip():
            tombol_tukar = kotak.addButton("Tukar dengan arsip", QMessageBox.ButtonRole.ActionRole)
        kotak.addButton("Batal", QMessageBox.ButtonRole.RejectRole)
        kotak.exec()
        dipilih = kotak.clickedButton()
        if dipilih is tombol_baru:
            jumlah = belajar.mulai_selera_baru()
            self.pengaturan.setValue("visual_aktif", False)
            self.pengaturan.setValue("visual_ditawarkan", 0)
            QMessageBox.information(self, "Selera baru", f"{jumlah} foto dipindah ke arsip. Mulai dari nol.")
        elif tombol_tukar is not None and dipilih is tombol_tukar:
            jumlah = belajar.pulihkan_selera_lama()
            QMessageBox.information(self, "Selera ditukar",
                                    f"{jumlah} foto dari arsip dipakai lagi; data sebelumnya kini jadi arsip.")
        self._perbarui_selera()

    def _editor_dibuka(self, pesan, sukses):
        self.label_status.setText(pesan)
        self.tombol_editor.setEnabled(True)
        if not sukses:
            QMessageBox.critical(self, "Editor gagal dibuka", pesan)

    def closeEvent(self, event):
        if self.penyortir.sedang_berjalan:
            jawab = QMessageBox.question(self, "Masih jalan",
                                         "Sortir masih berjalan. Tutup dan batalkan?")
            if jawab != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.penyortir.batalkan()
        event.accept()


# ---------------------------------------------------------------------------
# Ikon kecil (digambar, tanpa file gambar)
# ---------------------------------------------------------------------------
def _kanvas(ukuran=24):
    pix = QPixmap(ukuran, ukuran)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    return pix, p


def _pena(warna, tebal=2.0):
    pen = QPen(QColor(warna))
    pen.setWidthF(tebal)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def buat_ikon_mata(dicoret):
    pix, p = _kanvas()
    p.setPen(_pena(FAINT))
    p.drawEllipse(4, 7, 16, 10)
    p.setBrush(QColor(FAINT))
    p.drawEllipse(10, 10, 4, 4)
    if dicoret:
        p.drawLine(4, 4, 20, 20)
    p.end()
    return QIcon(pix)


def buat_ikon_gir(warna):
    pix, p = _kanvas(48)
    p.setPen(_pena(warna, 3.2))
    for i in range(8):
        sudut = i * math.pi / 4
        p.drawLine(QPointF(24 + 13 * math.cos(sudut), 24 + 13 * math.sin(sudut)),
                   QPointF(24 + 18 * math.cos(sudut), 24 + 18 * math.sin(sudut)))
    p.drawEllipse(QPointF(24, 24), 11, 11)
    p.drawEllipse(QPointF(24, 24), 4.5, 4.5)
    p.end()
    return QIcon(pix)


def buat_ikon_folder(warna):
    pix, p = _kanvas(68)
    jalur = QPainterPath()
    jalur.moveTo(8, 20)
    jalur.quadTo(8, 14, 14, 14)
    jalur.lineTo(26, 14)
    jalur.lineTo(31, 20)
    jalur.lineTo(54, 20)
    jalur.quadTo(60, 20, 60, 26)
    jalur.lineTo(60, 50)
    jalur.quadTo(60, 56, 54, 56)
    jalur.lineTo(14, 56)
    jalur.quadTo(8, 56, 8, 50)
    jalur.closeSubpath()
    muda = QColor(warna)
    muda.setAlpha(40)
    p.setBrush(muda)
    p.setPen(_pena(warna, 3.2))
    p.drawPath(jalur)
    p.drawLine(QPointF(34, 31), QPointF(34, 45))  # panah turun: "taruh di sini"
    p.drawLine(QPointF(28, 39), QPointF(34, 45))
    p.drawLine(QPointF(40, 39), QPointF(34, 45))
    p.end()
    return QIcon(pix)


def buat_ikon_chevron():
    """Gambar ikon panah dropdown ke file sementara (stylesheet Qt butuh path file)."""
    import tempfile
    path = os.path.join(tempfile.gettempdir(), "sortir_ai_chevron.png")
    pix, p = _kanvas()
    p.setPen(_pena(MUTED, 2.6))
    p.drawLine(6, 9, 12, 15)
    p.drawLine(12, 15, 18, 9)
    p.end()
    pix.save(path, "PNG")
    return path.replace("\\", "/")


def stylesheet():
    return STYLESHEET.replace("{CHEVRON}", buat_ikon_chevron())


def main():
    if os.name == "nt":
        # Tanpa ID sendiri, Windows mengelompokkan jendela ke pythonw.exe dan memakai logo Python di taskbar.
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SortirAI.SortirAI")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName("Sortir AI")
    app.setWindowIcon(QIcon(PATH_IKON))
    app.setStyleSheet(stylesheet())
    app.setFont(QFont("Segoe UI", 10))
    jendela = JendelaSortir()
    jendela.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
