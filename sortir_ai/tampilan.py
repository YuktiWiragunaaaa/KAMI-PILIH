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
    QParallelAnimationGroup,
    QPauseAnimation,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSequentialAnimationGroup,
    QSettings,
    QSize,
    Qt,
    QThread,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QStyle,
    QStyleOptionButton,
    QVBoxLayout,
    QWidget,
)

from . import inti as core
from .konfigurasi import ASPEK_INTI, MAKS_ASPEK_TAMBAHAN, MAKS_JENIS_KUSTOM, MAKS_NAMA_JENIS, STATUS, Konfigurasi

PATH_IKON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aset", "ikon.ico")
PILIHAN_TARGET = (15, 30, 50, 100)
NAMA_WARNA = {"": "Tanpa warna", "Red": "Merah", "Yellow": "Kuning", "Green": "Hijau",
              "Blue": "Biru", "Purple": "Ungu"}
WARNA_HEX = {"": "#D9D2C5", "Red": "#E0524A", "Yellow": "#E8C33A", "Green": "#4E9A6A",
             "Blue": "#4A7FD6", "Purple": "#9061C9"}
NAMA_ASPEK = {"momen": "Momen", "ekspresi": "Ekspresi", "gestur": "Gestur & pose", "teknis": "Teknis"}

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
QLabel#Info {{ color: {MUTED}; font-size: 12px; }}
QLabel#Status {{ font-size: 14px; font-weight: 600; }}
QLabel#Nilai {{ color: {MATCHA}; font-size: 12px; font-weight: 600; }}
QLabel#Pct {{ font-family: "Segoe UI Variable Display", "Segoe UI"; font-size: 22px; font-weight: 700; color: {MATCHA}; }}
QLabel#ZonaJudul {{ font-family: "Segoe UI Variable Display", "Segoe UI"; font-size: 17px; font-weight: 600; }}
QLabel#ZonaSub {{ color: {FAINT}; font-size: 12px; }}
QLabel#Badge {{ background: {MATCHA_MUDA}; color: {MATCHA}; border-radius: 11px; padding: 3px 10px;
               font-size: 12px; font-weight: 600; }}
QLabel#Hasil {{ border-radius: 13px; padding: 5px 12px; font-size: 13px; font-weight: 600; }}

QScrollArea, QWidget#Konten, QStackedWidget {{ background: transparent; border: 0; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 4px 0; }}
QScrollBar::handle:vertical {{ background: rgba(35,32,27,60); border-radius: 4px; min-height: 40px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QFrame#Kartu {{ background: rgba(255,255,255,205); border: 1px solid rgba(255,255,255,240); border-radius: 22px; }}

QLineEdit, QComboBox, QPlainTextEdit {{
    background: {PASIR}; border: 1px solid {PASIR}; border-radius: 12px;
    padding: 8px 12px; font-size: 13px; selection-background-color: {MATCHA};
}}
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus {{ border: 1px solid {MATCHA}; background: white; }}
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

QSlider {{ min-height: 24px; background: transparent; }}
QSlider::groove:horizontal {{ height: 6px; background: {PASIR}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: #9CCBAB; border-radius: 3px; }}
QSlider::handle:horizontal {{ width: 14px; height: 14px; margin: -6px 0; border-radius: 9px;
                              background: white; border: 2px solid {MATCHA}; }}
QSlider::handle:horizontal:hover {{ background: {MATCHA_MUDA}; }}

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
                     padding: 0; border-radius: 17px; font-size: 16px; background: rgba(255,255,255,170); }}
QPushButton#Bulat:hover {{ background: white; }}
QPushButton#Bulat:checked {{ background: {MATCHA}; }}
QPushButton#Eye {{ border: 0; background: transparent; padding: 0 6px; }}
QPushButton#Tautan {{ background: transparent; color: {MATCHA}; padding: 4px 2px; border-radius: 6px; }}
QPushButton#Tautan:hover {{ color: {INK}; background: transparent; }}
QPushButton#Tautan:disabled {{ color: {FAINT}; background: transparent; }}
QPushButton#Hapus {{ background: transparent; color: {FAINT}; padding: 2px 8px; font-size: 15px; }}
QPushButton#Hapus:hover {{ color: {KORAL}; background: transparent; }}

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
QProgressBar#Tipis {{ min-height: 6px; max-height: 6px; border-radius: 3px; }}
QProgressBar#Tipis::chunk {{ border-radius: 3px; }}
QToolTip {{ background: {INK}; color: {KREM}; border: 0; padding: 6px 8px; border-radius: 6px; }}

QDialog, QMessageBox, QInputDialog {{ background: {KREM}; }}
QMessageBox QLabel, QInputDialog QLabel {{ color: {INK}; }}
QDialog QPushButton {{ min-width: 72px; padding: 8px 18px; border-radius: 15px; background: {PASIR}; }}
QDialog QPushButton:default {{ background: {INK}; color: {KREM}; }}
QDialog QPushButton:default:hover {{ background: #3A352D; }}
QMenu {{ background: white; border: 1px solid #ECE6DB; border-radius: 10px; padding: 6px; }}
QMenu::item {{ color: {INK}; padding: 6px 18px; border-radius: 6px; }}
QMenu::item:selected {{ background: {MATCHA_MUDA}; }}
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
    selera_siap = Signal(object)  # (tanda_data, laporan, uji_visual, tawarkan)


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
    return efek


def kartu(jarak=18, tepi=(22, 20, 22, 20)):
    k = QFrame()
    k.setObjectName("Kartu")
    tata = QVBoxLayout(k)
    tata.setContentsMargins(*tepi)
    tata.setSpacing(jarak)
    bayangan(k)
    return k, tata


def tanya(induk, judul, teks, ya="Ya", tidak="Batal"):
    """Konfirmasi dengan tombol berbahasa Indonesia. -> True bila `ya` diklik."""
    kotak = QMessageBox(QMessageBox.Icon.Question, judul, teks, parent=induk)
    tombol_ya = kotak.addButton(ya, QMessageBox.ButtonRole.AcceptRole)
    kotak.addButton(tidak, QMessageBox.ButtonRole.RejectRole)
    kotak.setDefaultButton(tombol_ya)
    kotak.exec()
    return kotak.clickedButton() is tombol_ya


def segarkan_gaya(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def area_gulir(isi):
    gulir = QScrollArea()
    gulir.setWidgetResizable(True)
    gulir.setFrameShape(QFrame.Shape.NoFrame)
    gulir.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    gulir.viewport().setAutoFillBackground(False)
    gulir.setWidget(isi)
    return gulir


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


def teruskan_roda(widget, e):
    """Roda gulir di atas kontrol diteruskan ke area gulir terdekat, jadi halaman tetap bergulir
    dan nilai kontrol tidak berubah tanpa sengaja."""
    induk = widget.parentWidget()
    while induk is not None and not isinstance(induk, QScrollArea):
        induk = induk.parentWidget()
    if induk is not None:
        QApplication.sendEvent(induk.verticalScrollBar(), e)
    e.accept()


class KotakPilih(QComboBox):
    """Dropdown yang tidak berubah oleh roda gulir."""

    def wheelEvent(self, e):
        teruskan_roda(self, e)


class GeserTenang(QSlider):
    """Slider yang tidak berubah oleh roda gulir (nilai hanya lewat klik/seret)."""

    def wheelEvent(self, e):
        teruskan_roda(self, e)


class Tombol(QPushButton):
    """Tombol yang sedikit mengecil saat ditekan dan memantul saat dilepas."""

    def __init__(self, teks="", nama=None):
        super().__init__(teks)
        if nama:
            self.setObjectName(nama)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._skala = 1.0
        self._anim = QVariantAnimation(self)
        self._anim.valueChanged.connect(self._atur_skala)

    def _atur_skala(self, nilai):
        self._skala = float(nilai)
        self.update()

    def _ke(self, tujuan, durasi, kurva):
        self._anim.stop()
        self._anim.setStartValue(self._skala)
        self._anim.setEndValue(tujuan)
        self._anim.setDuration(durasi)
        self._anim.setEasingCurve(kurva)
        self._anim.start()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._ke(0.94, 90, QEasingCurve.Type.OutQuad)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._ke(1.0, 320, QEasingCurve.Type.OutBack)
        super().mouseReleaseEvent(e)

    def _gambar_dasar(self, p, tanpa_ikon=False):
        opsi = QStyleOptionButton()
        self.initStyleOption(opsi)
        if tanpa_ikon:
            opsi.icon = QIcon()
        self.style().drawControl(QStyle.ControlElement.CE_PushButton, opsi, p, self)

    def paintEvent(self, event):
        if abs(self._skala - 1.0) < 1e-3:
            return super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QPointF(self.rect().center())
        p.translate(c)
        p.scale(self._skala, self._skala)
        p.translate(-c)
        self._gambar_dasar(p)
        p.end()


class TombolGir(Tombol):
    """Tombol pengaturan: ikon gir berputar setengah putaran saat dibuka/ditutup."""

    def __init__(self):
        super().__init__(nama="Bulat")
        self.setCheckable(True)
        self.setToolTip("Pengaturan")
        self._sudut = 0.0
        self._putar = QVariantAnimation(self)
        self._putar.setDuration(420)
        self._putar.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._putar.valueChanged.connect(self._atur_sudut)
        self.toggled.connect(lambda nyala: self._mulai_putar(90.0 if nyala else 0.0))
        self._ikon = {False: buat_ikon_gir(INK).pixmap(48, 48), True: buat_ikon_gir(KREM).pixmap(48, 48)}

    def _atur_sudut(self, nilai):
        self._sudut = float(nilai)
        self.update()

    def _mulai_putar(self, tujuan):
        self._putar.stop()
        self._putar.setStartValue(self._sudut)
        self._putar.setEndValue(tujuan)
        self._putar.start()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        c = QPointF(self.rect().center())
        p.translate(c)
        p.scale(self._skala, self._skala)
        p.translate(-c)
        self._gambar_dasar(p, tanpa_ikon=True)
        p.translate(c)
        p.rotate(self._sudut)
        pix = self._ikon[self.isChecked()]
        p.drawPixmap(QRectF(-9, -9, 18, 18), pix, QRectF(pix.rect()))
        p.end()


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
        self._cache = None  # (kunci, QPixmap): menggambar 4 gradien penuh tiap frame itu mahal
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._langkah)

    def hidup(self, nyala):
        self._timer.start() if nyala else self._timer.stop()

    def _langkah(self):
        self._fase += 0.035
        self.update()

    def _gambar_latar(self):
        # Setengah resolusi lalu diperbesar halus: gradien lembut tidak kehilangan detail.
        w, h = max(1, self.width() // 2), max(1, self.height() // 2)
        pix = QPixmap(w, h)
        pix.fill(QColor(KREM))
        p = QPainter(pix)
        skala = max(w, h)
        for x, y, r, (cr, cg, cb), fase in self.GUMPALAN:
            cx = x * w + math.sin(self._fase + fase) * 0.04 * skala
            cy = y * h + math.cos(self._fase * 0.8 + fase) * 0.04 * skala
            g = QRadialGradient(QPointF(cx, cy), r * skala)
            g.setColorAt(0.0, QColor(cr, cg, cb, 170))
            g.setColorAt(0.55, QColor(cr, cg, cb, 60))
            g.setColorAt(1.0, QColor(cr, cg, cb, 0))
            p.fillRect(pix.rect(), g)
        p.end()
        return pix

    def paintEvent(self, event):
        kunci = (self.width(), self.height(), round(self._fase, 4))
        if self._cache is None or self._cache[0] != kunci:
            self._cache = (kunci, self._gambar_latar())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawPixmap(QRectF(self.rect()), self._cache[1], QRectF(self._cache[1].rect()))
        p.end()


class ZonaFolder(QFrame):
    """Area besar untuk memilih folder: klik atau tarik-lepas folder/foto ke sini.
    Saat masih kosong, ikon panahnya bergerak naik-turun pelan sebagai ajakan."""

    diklik = Signal()
    dijatuhkan = Signal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(128)
        self._sorot = False
        self._ayun = 0.0
        self._kosong = True
        self._pix = {False: buat_ikon_folder(MATCHA).pixmap(68, 68),
                     True: buat_ikon_folder(MATCHA, centang=True).pixmap(68, 68)}
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(2 * math.pi)
        self._anim.setDuration(1800)
        self._anim.setLoopCount(-1)
        self._anim.valueChanged.connect(self._atur_ayun)
        self._anim.start()
        tata = QVBoxLayout(self)
        tata.setContentsMargins(24, 20, 24, 20)
        tata.setSpacing(4)
        tata.addStretch(1)
        self.tempat_ikon = QWidget()
        self.tempat_ikon.setFixedHeight(38)
        self.judul = label("Taruh folder sesi di sini", "ZonaJudul")
        self.judul.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub = label("atau klik untuk mencari", "ZonaSub", wrap=True)
        self.sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge = label("", "Badge")
        self.badge.hide()
        baris_badge = QHBoxLayout()
        baris_badge.addStretch(1)
        baris_badge.addWidget(self.badge)
        baris_badge.addStretch(1)
        tata.addWidget(self.tempat_ikon)
        tata.addWidget(self.judul)
        tata.addWidget(self.sub)
        tata.addSpacing(4)
        tata.addLayout(baris_badge)
        tata.addStretch(1)

    def _atur_ayun(self, nilai):
        self._ayun = float(nilai)
        self.update()

    def isi(self, judul, sub, badge=None, badge_ok=True):
        self._kosong = False
        self.judul.setText(judul)
        self.sub.setText(sub)
        self.badge.setVisible(bool(badge))
        if badge:
            self.badge.setText(badge)
            self.badge.setStyleSheet("" if badge_ok else f"background:{KORAL_MUDA}; color:{KORAL};")
        self._anim.stop()
        self._ayun = 0.0
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        r = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        p.setBrush(QColor(MATCHA_MUDA) if self._sorot else QColor(255, 255, 255, 150))
        pena = QPen(QColor(MATCHA) if self._sorot else QColor("#CFC6B6"), 1.6)
        pena.setStyle(Qt.PenStyle.DashLine)
        pena.setDashPattern([5, 4])
        p.setPen(pena)
        p.drawRoundedRect(r, 20, 20)
        g = self.tempat_ikon.geometry()
        dy = math.sin(self._ayun) * 3.0
        pix = self._pix[not self._kosong]
        p.drawPixmap(QRectF(g.center().x() - 17, g.top() + 2 + dy, 34, 34), pix, QRectF(pix.rect()))
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


class Riak(QWidget):
    """Riak halus di sekeliling sebuah tombol: dua cincin tipis mengembang lalu memudar, berulang.
    Menempel di atas `induk` (tidak menangkap klik) agar cincin bisa keluar dari batas tombol."""

    RUANG = 18      # jarak maksimum cincin dari tepi tombol (px); < margin bawah jendela agar tidak terpotong
    PERIODE = 2600  # ms per gelombang

    def __init__(self, induk, target, warna):
        super().__init__(induk)
        self.target = target
        self.warna = QColor(warna)
        self._t = 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(self.PERIODE)
        self._anim.setLoopCount(-1)
        self._anim.valueChanged.connect(self._langkah)
        for w in (target, target.parentWidget(), induk):
            w.installEventFilter(self)
        self.hide()

    def _langkah(self, nilai):
        self._t = float(nilai)
        self.update()

    def mulai(self):
        self._atur_posisi()
        self.show()
        self.raise_()
        self._anim.start()

    def berhenti(self):
        self._anim.stop()
        self.hide()

    def _atur_posisi(self):
        kiri_atas = self.target.mapTo(self.parentWidget(), QPoint(0, 0))
        r = self.RUANG
        self.setGeometry(QRect(kiri_atas, self.target.size()).adjusted(-r, -r, r, r))

    def eventFilter(self, obj, event):
        if self.isVisible() and event.type() in (event.Type.Move, event.Type.Resize, event.Type.Show):
            self._atur_posisi()
        if obj is self.target and event.type() == event.Type.Hide:
            self.berhenti()
        return False

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.RUANG
        tombol = QRectF(r, r, self.width() - 2 * r, self.height() - 2 * r)
        for geser in (0.0, 0.5):
            fase = (self._t + geser) % 1.0
            jarak = 2 + (r - 4) * (1 - (1 - fase) ** 3)   # melambat saat menjauh
            warna = QColor(self.warna)
            warna.setAlphaF(0.42 * (1 - fase) ** 2)       # memudar
            pena = QPen(warna, 2.0 - fase)
            p.setPen(pena)
            p.setBrush(Qt.BrushStyle.NoBrush)
            kotak = tombol.adjusted(-jarak, -jarak, jarak, jarak)
            p.drawRoundedRect(kotak, kotak.height() / 2, kotak.height() / 2)
        p.end()


class Sakelar(QAbstractButton):
    """Sakelar on/off bergaya pil dengan kenop beranimasi."""

    def __init__(self):
        super().__init__()
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._posisi = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)
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
        mati, nyala = QColor("#D9D2C5"), QColor(MATCHA)
        t = max(0.0, min(1.0, self._posisi))
        warna = QColor(int(mati.red() + (nyala.red() - mati.red()) * t),
                       int(mati.green() + (nyala.green() - mati.green()) * t),
                       int(mati.blue() + (nyala.blue() - mati.blue()) * t))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(warna)
        p.drawRoundedRect(QRectF(0, 0, 46, 28), 14, 14)
        p.setBrush(QColor("white"))
        p.drawEllipse(QPointF(14 + 18 * self._posisi, 14), 11, 11)
        p.end()


class PilihBintang(QWidget):
    """Lima bintang yang bisa diklik (klik bintang yang sama lagi = 0 bintang)."""

    berubah = Signal(int)

    def __init__(self, nilai=0):
        super().__init__()
        self.nilai = nilai
        self._arah = -1
        self.setFixedSize(5 * 24, 24)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Klik bintang yang sama lagi untuk 0 bintang")

    def atur(self, nilai):
        self.nilai = nilai
        self.update()

    def wheelEvent(self, e):
        teruskan_roda(self, e)

    def mouseMoveEvent(self, e):
        self._arah = int(e.position().x() // 24)
        self.update()

    def leaveEvent(self, e):
        self._arah = -1
        self.update()

    def mouseReleaseEvent(self, e):
        n = min(5, int(e.position().x() // 24) + 1)
        self.nilai = 0 if n == self.nilai else n
        self.berubah.emit(self.nilai)
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        tampil = self._arah + 1 if self._arah >= 0 else self.nilai
        for i in range(5):
            cx, cy, r = 12 + 24 * i, 12, 9
            titik = [QPointF(cx + (r if k % 2 == 0 else r * 0.45) * math.cos(-math.pi / 2 + k * math.pi / 5),
                             cy + (r if k % 2 == 0 else r * 0.45) * math.sin(-math.pi / 2 + k * math.pi / 5))
                     for k in range(10)]
            isi = i < tampil
            p.setPen(QPen(QColor(AMBER if isi else "#CFC6B6"), 1.4))
            p.setBrush(QColor(AMBER) if isi else Qt.BrushStyle.NoBrush)
            p.drawPolygon(QPolygonF(titik))
        p.end()


class BarisBobot(QWidget):
    """Nama aspek + slider bobot (0–3×) + angka; opsional nama bisa diedit dan tombol hapus."""

    berubah = Signal()
    dihapus = Signal(object)

    def __init__(self, nama, bobot, bisa_diedit=False):
        super().__init__()
        tata = QHBoxLayout(self)
        tata.setContentsMargins(0, 0, 0, 0)
        tata.setSpacing(10)
        if bisa_diedit:
            self.nama = QLineEdit(nama)
            self.nama.setPlaceholderText("mis. warna")
            self.nama.setMaxLength(30)
            self.nama.setFixedWidth(130)
            self.nama.textChanged.connect(lambda _t: self.berubah.emit())
        else:
            self.nama = label(nama)
            self.nama.setFixedWidth(130)
        self.slider = GeserTenang(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 30)
        self.slider.setValue(round(bobot * 10))
        self.slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.angka = label("", "Nilai")
        self.angka.setFixedWidth(38)
        self.slider.valueChanged.connect(self._ubah)
        tata.addWidget(self.nama)
        tata.addWidget(self.slider, 1)
        tata.addWidget(self.angka)
        if bisa_diedit:
            hapus = Tombol("✕", "Hapus")
            hapus.setToolTip("Hapus aspek ini")
            hapus.clicked.connect(lambda: self.dihapus.emit(self))
            tata.addWidget(hapus)
        self._ubah(self.slider.value(), diam=True)

    def _ubah(self, nilai, diam=False):
        self.angka.setText("mati" if nilai == 0 else f"{nilai / 10:.1f}×")
        if not diam:
            self.berubah.emit()

    def teks_nama(self):
        return self.nama.text().strip()

    def bobot(self):
        return self.slider.value() / 10


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
        # Pilihan terakhir (model, editor, folder, target, konfigurasi) disimpan di registry Windows (HKCU).
        self.pengaturan = QSettings("SortirAI", "SortirAI")
        self.model_tersimpan = self.pengaturan.value("model", "", str)
        self.konfig = Konfigurasi.dari_json(self.pengaturan.value("konfigurasi", "", str))
        self._simpan_tertunda = QTimer(self)
        self._simpan_tertunda.setSingleShot(True)
        self._simpan_tertunda.setInterval(400)
        self._simpan_tertunda.timeout.connect(self._simpan_konfig)

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
        luar.setContentsMargins(20, 22, 20, 20)
        luar.setSpacing(14)
        self.tata_luar = luar

        # Header (tetap di atas kedua halaman)
        header = QHBoxLayout()
        header.setContentsMargins(8, 0, 8, 0)
        header.setSpacing(14)
        logo = QLabel()
        logo.setFixedSize(46, 46)
        logo.setPixmap(QIcon(PATH_IKON).pixmap(46, 46))
        header.addWidget(logo)
        judul = QVBoxLayout()
        judul.setSpacing(0)
        self.label_judul = label("Sortir AI", "Title")
        self.label_sub = label("Pilih foto terbaik dari satu sesi.", "Subtitle")
        judul.addWidget(self.label_judul)
        judul.addWidget(self.label_sub)
        header.addLayout(judul, 1)
        self.tombol_pengaturan = TombolGir()
        self.tombol_pengaturan.toggled.connect(self._tampilkan_pengaturan)
        header.addWidget(self.tombol_pengaturan, 0, Qt.AlignmentFlag.AlignTop)
        luar.addLayout(header)

        self.halaman = QStackedWidget()
        luar.addWidget(self.halaman, 1)
        self.halaman.addWidget(self._bangun_halaman_utama())
        self.halaman.addWidget(self._bangun_halaman_pengaturan())
        self._bangun_aksi(luar)

    def _bangun_halaman_utama(self):
        self.konten = QWidget()
        self.konten.setObjectName("Konten")
        tata = QVBoxLayout(self.konten)
        tata.setContentsMargins(8, 0, 8, 12)  # ruang untuk bayangan kartu
        tata.setSpacing(16)

        # Kartu utama: folder + jumlah foto
        utama, isi = kartu(jarak=16)
        tata.addWidget(utama)
        self.tombol_folder = ZonaFolder()  # nama lama dipertahankan: dipakai _atur_kontrol
        self.tombol_folder.diklik.connect(self._pilih_folder)
        self.tombol_folder.dijatuhkan.connect(self._folder_dijatuhkan)
        isi.addWidget(self.tombol_folder)

        isi.addWidget(label("Jumlah foto terbaik", "Section"))
        baris_target = QHBoxLayout()
        baris_target.setSpacing(8)
        self.chip_target = {}
        for n in PILIHAN_TARGET:
            chip = Tombol(str(n), "Chip")
            chip.setCheckable(True)
            chip.clicked.connect(lambda _c=False, nilai=n: self.entry_target.setText(str(nilai)))
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
            b = Tombol(teks, "Bulat")
            b.setAutoRepeat(True)
            b.clicked.connect(lambda _c=False, d=delta: self._ubah_target(d))
            tata_step.addWidget(b)
        baris_target.addWidget(self.stepper)
        isi.addLayout(baris_target)
        # Ringkasan pengaturan aktif: informasi saja, bukan tombol (pengaturan dibuka lewat ⚙).
        self.label_ringkas = label("", "Info", wrap=True)
        isi.addWidget(self.label_ringkas)

        # Kartu status
        panel_status, stat = kartu(jarak=10, tepi=(22, 16, 22, 16))
        tata.addWidget(panel_status)
        baris_status = QHBoxLayout()
        baris_status.setSpacing(10)
        self.titik = QLabel()
        self.titik.setFixedSize(10, 10)
        self._set_titik(MATCHA)
        self.label_status = label("Siap.", "Status", wrap=True)
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
            chip.setGraphicsEffect(QGraphicsOpacityEffect(chip))
            self.chip_hasil[nama] = chip
            tata_hasil.addWidget(chip)
        tata_hasil.addStretch(1)
        self.baris_hasil.hide()
        stat.addWidget(self.baris_hasil)
        self.label_data = label("", "Help", wrap=True)
        self.label_data.hide()
        stat.addWidget(self.label_data)
        tata.addStretch(1)
        self.gulir = area_gulir(self.konten)
        return self.gulir

    def _bangun_halaman_pengaturan(self):
        self.konten_pengaturan = QWidget()
        self.konten_pengaturan.setObjectName("Konten")
        tata = QVBoxLayout(self.konten_pengaturan)
        tata.setContentsMargins(8, 0, 8, 12)
        tata.setSpacing(16)
        kembali = Tombol("←  Kembali", "Tautan")
        kembali.clicked.connect(lambda: self.tombol_pengaturan.setChecked(False))
        tata.addWidget(kembali, 0, Qt.AlignmentFlag.AlignLeft)

        # Jenis sesi
        k, isi = kartu(jarak=12)
        isi.addWidget(label("Jenis sesi", "Section"))
        self.chip_preset = {}
        self.wadah_jenis = QWidget()
        self.tata_jenis = QVBoxLayout(self.wadah_jenis)
        self.tata_jenis.setContentsMargins(0, 0, 0, 0)
        self.tata_jenis.setSpacing(6)
        isi.addWidget(self.wadah_jenis)
        self._bangun_chip_jenis()
        baris_bawaan = QHBoxLayout()
        baris_bawaan.addWidget(label("Tiap jenis sesi menyimpan pengaturannya sendiri, termasuk editor yang dibuka.",
                                     "Help", wrap=True), 1)
        self.tombol_bawaan = Tombol("Kembalikan ke bawaan", "Tautan")
        self.tombol_bawaan.clicked.connect(self._kembalikan_bawaan)
        baris_bawaan.addWidget(self.tombol_bawaan)
        isi.addLayout(baris_bawaan)
        tata.addWidget(k)

        # Yang dinilai
        k, isi = kartu(jarak=12)
        isi.addWidget(label("Yang dinilai", "Section"))
        isi.addWidget(label("Geser untuk menentukan seberapa penting tiap aspek. 1.0× = biasa.", "Help", wrap=True))
        self.baris_bobot = {}
        for a in ASPEK_INTI:
            b = BarisBobot(NAMA_ASPEK[a], self.konfig.bobot[a])
            b.berubah.connect(self._konfig_diubah)
            self.baris_bobot[a] = b
            isi.addWidget(b)
        self.wadah_tambahan = QVBoxLayout()
        self.wadah_tambahan.setSpacing(10)
        isi.addLayout(self.wadah_tambahan)
        self.baris_tambahan = []
        for t in self.konfig.aspek_tambahan:
            self._tambah_aspek(t["nama"], t["bobot"], simpan=False)
        self.tombol_tambah_aspek = Tombol("+  Tambah aspek", "Tautan")
        self.tombol_tambah_aspek.clicked.connect(lambda: self._tambah_aspek("", 1.0))
        isi.addWidget(self.tombol_tambah_aspek, 0, Qt.AlignmentFlag.AlignLeft)
        self.label_info_aspek = label("Aspek tambahan ikut dinilai AI, jadi foto yang sudah pernah dinilai "
                                      "akan dinilai ulang saat sortir berikutnya.", "Help", wrap=True)
        isi.addWidget(self.label_info_aspek)
        tata.addWidget(k)

        # Catatan untuk AI
        k, isi = kartu(jarak=10)
        isi.addWidget(label("Catatan untuk AI", "Section"))
        self.entry_catatan = QPlainTextEdit(self.konfig.catatan)
        self.entry_catatan.setPlaceholderText("Contoh: utamakan foto candid, abaikan foto dekorasi.")
        self.entry_catatan.setFixedHeight(84)
        self.entry_catatan.textChanged.connect(self._konfig_diubah)
        isi.addWidget(self.entry_catatan)
        isi.addWidget(label("Mengubah catatan juga membuat foto dinilai ulang pada sortir berikutnya.", "Help", wrap=True))
        tata.addWidget(k)

        # Label di editor
        k, isi = kartu(jarak=12)
        isi.addWidget(label("Label di editor", "Section"))
        isi.addWidget(label("Bintang dan warna yang ditulis ke Capture One / Lightroom.", "Help", wrap=True))
        self.pilih_bintang, self.pilih_warna = {}, {}
        for s in STATUS:
            baris = QHBoxLayout()
            baris.setSpacing(12)
            nama = label(s, "Status")
            nama.setFixedWidth(90)
            bintang = PilihBintang(self.konfig.rating[s]["bintang"])
            bintang.berubah.connect(lambda _n: self._konfig_diubah())
            warna = KotakPilih()
            for kode, teks in NAMA_WARNA.items():
                warna.addItem(buat_ikon_bulat(WARNA_HEX[kode]), teks, kode)
            warna.setCurrentIndex(max(0, warna.findData(self.konfig.rating[s]["warna"])))
            warna.currentIndexChanged.connect(lambda _i: self._konfig_diubah())
            self.pilih_bintang[s], self.pilih_warna[s] = bintang, warna
            baris.addWidget(nama)
            baris.addWidget(bintang)
            baris.addStretch(1)
            baris.addWidget(warna)
            isi.addLayout(baris)
        tata.addWidget(k)

        # Akun & alat
        k, konf = kartu(jarak=14)
        konf.addWidget(label("Akun & alat", "Section"))
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
        self.tombol_login = Tombol("Simpan")
        self.tombol_login.clicked.connect(self._kelola_login)
        self.label_kredensial = label("", "Help", wrap=True)
        baris_api = QHBoxLayout()
        baris_api.setContentsMargins(0, 0, 0, 0)
        baris_api.setSpacing(8)
        baris_api.addWidget(self.entry_api, 1)
        baris_api.addWidget(self.tombol_login)
        kotak_api = QWidget()
        kotak_api.setLayout(baris_api)
        field_api = Field("API KEY GEMINI", kotak_api)
        field_api.layout().addWidget(self.label_kredensial)
        konf.addWidget(field_api)
        dua_kolom = QHBoxLayout()
        dua_kolom.setSpacing(12)
        self.pilihan_model = KotakPilih()
        self.pilihan_model.addItems(core.MODEL_GEMINI_OPTIONS)
        self.field_model = Field("MODEL", self.pilihan_model, "Isi API key dulu.")
        self.pilihan_model.currentTextChanged.connect(self._perbarui_bantuan_model)
        dua_kolom.addWidget(self.field_model, 1)
        self.pilihan_editor = KotakPilih()
        self.pilihan_editor.addItem("Mencari editor…")
        self.pilihan_editor.setEnabled(False)
        self.pilihan_editor.currentTextChanged.connect(self._perbarui_tombol_editor)
        self.field_editor = Field("BUKA HASIL DI", self.pilihan_editor, "Mencari editor…")
        dua_kolom.addWidget(self.field_editor, 1)
        konf.addLayout(dua_kolom)
        tata.addWidget(k)

        # Selera
        k, isi = kartu(jarak=10)
        isi.addWidget(label("Selera kamu", "Section"))
        isi.addWidget(label("Makin sering kamu koreksi hasil lalu klik Pelajari koreksi, makin mirip "
                            "pilihannya dengan pilihanmu.", "Help", wrap=True))
        isi.addWidget(label("Dasar", "FieldLabel"))
        self.progres_dasar = QProgressBar()
        self.progres_dasar.setObjectName("Tipis")
        self.progres_dasar.setRange(0, 100)
        isi.addWidget(self.progres_dasar)
        self.label_dasar = label("", "Help", wrap=True)
        isi.addWidget(self.label_dasar)
        isi.addSpacing(6)
        baris_visual = QHBoxLayout()
        baris_visual.setSpacing(10)
        baris_visual.addWidget(label("Visual", "FieldLabel"))
        baris_visual.addStretch(1)
        self.tombol_unduh_visual = Tombol("Unduh model visual (89 MB)")
        self.tombol_unduh_visual.clicked.connect(self._unduh_visual)
        self.tombol_unduh_visual.hide()
        baris_visual.addWidget(self.tombol_unduh_visual)
        self.tombol_visual = Sakelar()
        self.tombol_visual.clicked.connect(self._ubah_visual)
        baris_visual.addWidget(self.tombol_visual)
        isi.addLayout(baris_visual)
        self.progres_visual = QProgressBar()
        self.progres_visual.setObjectName("Tipis")
        self.progres_visual.setRange(0, 100)
        isi.addWidget(self.progres_visual)
        self.label_selera = label("Mengecek…", "Help", wrap=True)
        isi.addWidget(self.label_selera)
        self.tombol_selera_baru = Tombol("Mulai selera baru", "Tautan")
        self.tombol_selera_baru.setToolTip("Belajar dari nol. Selera lama disimpan di 1 slot arsip.")
        self.tombol_selera_baru.clicked.connect(self._selera_baru)
        isi.addWidget(self.tombol_selera_baru, 0, Qt.AlignmentFlag.AlignLeft)
        tata.addWidget(k)
        tata.addStretch(1)
        self._sinkron_preset()
        self.gulir_pengaturan = area_gulir(self.konten_pengaturan)
        return self.gulir_pengaturan

    def _bangun_aksi(self, luar):
        self.bar_aksi = QWidget()
        aksi = QHBoxLayout(self.bar_aksi)
        aksi.setContentsMargins(8, 0, 8, 0)  # sejajar dengan tepi kartu
        aksi.setSpacing(10)
        self.tombol_belajar = Tombol("Pelajari koreksi", "Ghost")
        self.tombol_belajar.setToolTip("Sudah ubah label di editor? Klik agar pilihanmu dipelajari.")
        self.tombol_belajar.clicked.connect(self._pelajari_koreksi)
        aksi.addWidget(self.tombol_belajar)
        aksi.addStretch(1)
        self.tombol_batal = Tombol("Batal", "Ghost")
        self.tombol_batal.clicked.connect(self._batalkan)
        self.tombol_batal.hide()
        self.tombol_editor = Tombol("Buka editor", "Finalize")
        self.tombol_editor.clicked.connect(self._buka_editor)
        self.tombol_editor.hide()
        self.tombol_mulai = Tombol("Sortir sekarang  →", "Primary")
        self.tombol_mulai.clicked.connect(lambda: self._mulai())
        for b in (self.tombol_belajar, self.tombol_batal, self.tombol_editor, self.tombol_mulai):
            b.setFixedHeight(46)  # radius 23 = setengah tinggi: bentuk pil sempurna
        for b in (self.tombol_batal, self.tombol_editor, self.tombol_mulai):
            aksi.addWidget(b)
        luar.addWidget(self.bar_aksi)
        # Sorotan "langkah berikutnya": riak lembut di sekitar tombol buka editor setelah sortir selesai.
        self.riak_editor = Riak(self.latar, self.tombol_editor, KORAL)
        # Tombol sortir "bernapas" pelan saat siap dipakai (folder sudah dipilih).
        self._efek_mulai = None
        self._denyut = None
        self._gaya_tombol_mulai(sekunder=False)

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_sudah_dipusatkan", False):
            self._sudah_dipusatkan = True
            self.resize(max(620, self.width()), self._tinggi_ideal())
            layar = self.screen().availableGeometry()
            self.move(layar.center().x() - self.width() // 2,
                      max(layar.top(), layar.center().y() - self.height() // 2))

    def _tinggi_ideal(self):
        """Tinggi jendela mengikuti isi halaman aktif, tapi tidak melebihi layar (sisanya digulir)."""
        halaman = self.konten_pengaturan if self.halaman.currentIndex() == 1 else self.konten
        halaman.layout().activate()
        m = self.tata_luar.contentsMargins()
        header = self.tata_luar.itemAt(0).sizeHint().height()
        tinggi = (m.top() + m.bottom() + 2 * self.tata_luar.spacing() + header + 4
                  + halaman.layout().sizeHint().height()
                  + (self.bar_aksi.sizeHint().height() if self.bar_aksi.isVisible() else 0))
        layar = self.screen().availableGeometry() if self.screen() else None
        if layar:
            tinggi = min(tinggi, layar.height() - 40)
        return tinggi

    def _pas_ukuran(self, animasi=True):
        tujuan = QSize(max(620, self.width()), self._tinggi_ideal())
        layar = self.screen().availableGeometry() if self.screen() else None
        if layar and self.y() + tujuan.height() > layar.bottom():
            self.move(self.x(), max(layar.top(), layar.bottom() - tujuan.height() - 30))
        if not animasi or not self.isVisible():
            self.resize(tujuan)
            return
        self._anim_ukuran = QPropertyAnimation(self, b"size", self)
        self._anim_ukuran.setDuration(260)
        self._anim_ukuran.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_ukuran.setEndValue(tujuan)
        self._anim_ukuran.start()

    def _tampilkan_pengaturan(self, nyala):
        """Morph antar halaman: jendela berubah ukuran di sekitar titik tengahnya sendiri
        sementara halaman lama memudar menjadi halaman baru. Halaman asli disembunyikan
        selama animasi; yang bergerak hanya dua pixmap, jadi tetap ringan."""
        if getattr(self, "_anim_halaman", None):
            self._anim_halaman.stop()
            self._selesai_morph()
        lama = self.halaman.currentWidget()
        pix_lama = lama.grab()
        halaman = self.gulir_pengaturan if nyala else self.gulir
        self.halaman.setCurrentWidget(halaman)
        self.bar_aksi.setVisible(not nyala)
        self.label_sub.setText("Pengaturan" if nyala else "Pilih foto terbaik dari satu sesi.")
        if nyala:
            self._perbarui_selera()
            self.gulir_pengaturan.verticalScrollBar().setValue(0)
        else:
            self._perbarui_ringkas()

        # Geometri tujuan: tinggi baru, titik tengah tetap (sehingga tutup kembali ke posisi semula).
        awal = self.geometry()
        tinggi = self._tinggi_ideal()
        if nyala:
            self._tengah_utama = awal.center().y()  # dikembalikan persis ke sini saat ditutup
        tengah = awal.center().y() if nyala else getattr(self, "_tengah_utama", awal.center().y())
        tujuan = QRect(awal.x(), tengah - tinggi // 2, awal.width(), tinggi)
        layar = self.screen().availableGeometry() if self.screen() else None
        if layar:
            if tujuan.bottom() > layar.bottom():
                tujuan.moveBottom(layar.bottom())
            if tujuan.top() < layar.top():
                tujuan.moveTop(layar.top())
        if not self.isVisible():
            self.setGeometry(tujuan)
            return

        # Pixmap halaman baru pada ukuran akhirnya.
        ukuran_baru = self.halaman.size() + QSize(0, tinggi - awal.height())
        halaman.resize(ukuran_baru)
        pix_baru = halaman.grab()

        if not hasattr(self, "_tirai"):
            self._tirai = []
            for _ in range(2):
                t = QLabel(self.halaman)
                t.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                t.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
                t.setGraphicsEffect(QGraphicsOpacityEffect(t))
                self._tirai.append(t)
        t_lama, t_baru = self._tirai
        luas = QSize(max(pix_lama.width(), pix_baru.width()), max(pix_lama.height(), pix_baru.height()))
        for t, pix in ((t_lama, pix_lama), (t_baru, pix_baru)):
            t.setPixmap(pix)
            t.resize(luas)
            t.show()
            t.raise_()
        t_lama.move(0, 0)
        halaman.setVisible(False)
        self._halaman_morph = halaman

        durasi, kurva = 320, QEasingCurve.Type.InOutCubic
        grup = QParallelAnimationGroup(self)

        ukuran = QPropertyAnimation(self, b"geometry", self)
        ukuran.setDuration(durasi)
        ukuran.setEasingCurve(kurva)
        ukuran.setStartValue(awal)
        ukuran.setEndValue(tujuan)
        grup.addAnimation(ukuran)

        pudar = QPropertyAnimation(t_lama.graphicsEffect(), b"opacity", self)
        pudar.setDuration(int(durasi * 0.6))
        pudar.setStartValue(1.0)
        pudar.setEndValue(0.0)
        grup.addAnimation(pudar)

        muncul = QSequentialAnimationGroup(self)
        muncul.addPause(int(durasi * 0.25))
        a = QPropertyAnimation(t_baru.graphicsEffect(), b"opacity", self)
        a.setDuration(int(durasi * 0.75))
        a.setEasingCurve(QEasingCurve.Type.OutCubic)
        a.setStartValue(0.0)
        a.setEndValue(1.0)
        muncul.addAnimation(a)
        grup.addAnimation(muncul)
        t_baru.graphicsEffect().setOpacity(0.0)

        geser = QPropertyAnimation(t_baru, b"pos", self)
        geser.setDuration(durasi)
        geser.setEasingCurve(QEasingCurve.Type.OutCubic)
        geser.setStartValue(QPoint(0, 10))
        geser.setEndValue(QPoint(0, 0))
        grup.addAnimation(geser)

        grup.finished.connect(self._selesai_morph)
        self._anim_halaman = grup
        grup.start()

    def _selesai_morph(self):
        halaman = getattr(self, "_halaman_morph", None)
        if halaman is not None:
            halaman.setVisible(True)
            self._halaman_morph = None
        for t in getattr(self, "_tirai", []):
            t.hide()
            t.graphicsEffect().setOpacity(1.0)

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
        bagian = [self._nama_preset_aktif(), self.pilihan_model.currentText() or "model belum dipilih"]
        if self.editor_terdeteksi:
            bagian.append(f"buka di {self.pilihan_editor.currentText()}")
        if not self.api_tersimpan:
            bagian.append("API key belum diisi")
        self.label_ringkas.setText("  ·  ".join(bagian))

    # ---- konfigurasi penilaian ---------------------------------------------
    def _nama_preset_aktif(self):
        return self.konfig.nama_tampil(self.konfig.preset) + ("" if self.konfig.sama_dengan_bawaan() else " (disesuaikan)")

    def _bangun_chip_jenis(self):
        """Chip jenis sesi (bawaan + buatan sendiri) 3 per baris, diakhiri chip '+ Jenis baru'."""
        while self.tata_jenis.count():
            item = self.tata_jenis.takeAt(0)
            if item.layout():
                while item.layout().count():
                    w = item.layout().takeAt(0).widget()
                    if w:
                        w.setParent(None)  # lepas sekarang juga agar tidak sempat tergambar bertumpuk
                        w.deleteLater()
        self.chip_preset = {}
        tombol = []
        for nama in self.konfig.daftar_jenis():
            chip = Tombol(self.konfig.nama_tampil(nama), "Chip")
            chip.setCheckable(True)
            chip.clicked.connect(lambda _c=False, n=nama: self._pilih_preset(n))
            chip.setToolTip("Klik kanan untuk ganti nama atau hapus" if nama in self.konfig.kustom
                            else "Klik kanan untuk ganti nama")
            chip.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            chip.customContextMenuRequested.connect(lambda _p, n=nama, c=chip: self._menu_jenis(n, c))
            self.chip_preset[nama] = chip
            tombol.append(chip)
        if len(self.konfig.kustom) < MAKS_JENIS_KUSTOM:
            tambah = Tombol("+  Jenis baru", "Chip")
            tambah.setToolTip("Buat jenis sesi sendiri, mis. Wisuda atau Maternity")
            tambah.clicked.connect(self._tambah_jenis)
            tombol.append(tambah)
        for i in range(0, len(tombol), 3):  # 3 per baris agar tidak melebar di jendela sempit
            baris = QHBoxLayout()
            baris.setSpacing(6)
            for t in tombol[i:i + 3]:
                baris.addWidget(t, 1)
            for _ in range(3 - len(tombol[i:i + 3])):
                baris.addStretch(1)  # baris terakhir tetap selebar kolom di atasnya
            self.tata_jenis.addLayout(baris)
        self._sinkron_preset()

    def _tambah_jenis(self):
        nama, ok = QInputDialog.getText(self, "Jenis sesi baru",
                                        f"Nama jenis sesi (maks. {MAKS_NAMA_JENIS} huruf):")
        if not ok or not nama.strip():
            return
        kotak = QMessageBox(self)
        kotak.setWindowTitle("Jenis sesi baru")
        kotak.setText(f"Mulai \"{nama.strip()}\" dari mana?")
        salin = kotak.addButton(f"Salin dari {self.konfig.nama_tampil(self.konfig.preset)}", QMessageBox.ButtonRole.AcceptRole)
        kotak.addButton("Mulai dari Umum", QMessageBox.ButtonRole.ActionRole)
        kotak.addButton("Batal", QMessageBox.ButtonRole.RejectRole)
        kotak.exec()
        if kotak.buttonRole(kotak.clickedButton()) == QMessageBox.ButtonRole.RejectRole:
            return
        try:
            self.konfig.tambah_jenis(nama, salin_aktif=kotak.clickedButton() is salin)
        except ValueError as error:
            QMessageBox.information(self, "Belum bisa dibuat", str(error))
            return
        self._bangun_chip_jenis()
        self._muat_ke_form()
        self._simpan_tertunda.start()

    def _menu_jenis(self, nama, chip):
        menu = QMenu(self)
        ganti = menu.addAction("Ganti nama…")
        asli = menu.addAction(f"Kembalikan nama \"{nama}\"") if nama in self.konfig.alias else None
        hapus = menu.addAction("Hapus") if nama in self.konfig.kustom else None
        pilihan = menu.exec(chip.mapToGlobal(chip.rect().bottomLeft()))
        try:
            if pilihan is None:
                return
            if pilihan is ganti:
                tampil = self.konfig.nama_tampil(nama)
                baru, ok = QInputDialog.getText(self, "Ganti nama",
                                                f"Nama baru (maks. {MAKS_NAMA_JENIS} huruf):", text=tampil)
                if not ok or baru.strip() == tampil:
                    return
                self.konfig.ganti_nama_jenis(nama, baru)
            elif pilihan is asli:
                self.konfig.ganti_nama_jenis(nama, nama)
            elif pilihan is hapus:
                if not tanya(self, "Hapus jenis sesi", f"Hapus \"{nama}\" beserta pengaturannya?", "Hapus"):
                    return
                self.konfig.hapus_jenis(nama)
            else:
                return
        except ValueError as error:
            QMessageBox.information(self, "Belum bisa diubah", str(error))
            return
        self._bangun_chip_jenis()
        self._muat_ke_form()
        self._simpan_tertunda.start()

    def _sinkron_preset(self):
        for nama, chip in self.chip_preset.items():
            chip.setChecked(nama == self.konfig.preset)
        if hasattr(self, "tombol_bawaan"):
            self.tombol_bawaan.setVisible(not self.konfig.sama_dengan_bawaan())

    def _pilih_preset(self, nama):
        self.konfig.pakai_preset(nama)
        self._muat_ke_form()
        self._simpan_tertunda.start()

    def _kembalikan_bawaan(self):
        self.konfig.kembalikan_bawaan()
        self._muat_ke_form()
        self._simpan_tertunda.start()

    def _muat_ke_form(self):
        """Tampilkan profil jenis sesi aktif di semua kontrol pengaturan."""
        self._memuat = True
        try:
            for a, baris in self.baris_bobot.items():
                baris.slider.setValue(round(self.konfig.bobot[a] * 10))
                baris._ubah(baris.slider.value(), diam=True)
            for b in list(self.baris_tambahan):
                self.baris_tambahan.remove(b)
                b.setParent(None)
                b.deleteLater()
            for t in self.konfig.aspek_tambahan:
                self._tambah_aspek(t["nama"], t["bobot"], simpan=False)
            self.tombol_tambah_aspek.setVisible(len(self.baris_tambahan) < MAKS_ASPEK_TAMBAHAN)
            self.entry_catatan.setPlainText(self.konfig.catatan)
            for st in STATUS:
                self.pilih_bintang[st].atur(self.konfig.rating[st]["bintang"])
                w = self.pilih_warna[st]
                w.setCurrentIndex(max(0, w.findData(self.konfig.rating[st]["warna"])))
            if self.konfig.editor and self.konfig.editor in self.editor_terdeteksi:
                self.pilihan_editor.setCurrentText(self.konfig.editor)
        finally:
            self._memuat = False
        self._sinkron_preset()
        self._perbarui_ringkas()

    def _tambah_aspek(self, nama, bobot, simpan=True):
        if len(self.baris_tambahan) >= MAKS_ASPEK_TAMBAHAN:
            return
        b = BarisBobot(nama, bobot, bisa_diedit=True)
        b.berubah.connect(self._konfig_diubah)
        b.dihapus.connect(self._hapus_aspek)
        self.baris_tambahan.append(b)
        self.wadah_tambahan.addWidget(b)
        if hasattr(self, "tombol_tambah_aspek"):
            self.tombol_tambah_aspek.setVisible(len(self.baris_tambahan) < MAKS_ASPEK_TAMBAHAN)
        if simpan:
            b.nama.setFocus()
            self._konfig_diubah()

    def _hapus_aspek(self, baris):
        self.baris_tambahan.remove(baris)
        baris.setParent(None)
        baris.deleteLater()
        self.tombol_tambah_aspek.setVisible(True)
        self._konfig_diubah()

    def _konfig_diubah(self):
        if getattr(self, "_memuat", False):
            return
        k = self.konfig
        for a, baris in self.baris_bobot.items():
            k.bobot[a] = baris.bobot()
        k.aspek_tambahan = [{"nama": b.teks_nama(), "bobot": b.bobot()}
                            for b in self.baris_tambahan if b.teks_nama()]
        k.catatan = self.entry_catatan.toPlainText()[:600]
        for s in STATUS:
            k.rating[s] = {"bintang": self.pilih_bintang[s].nilai,
                           "warna": self.pilih_warna[s].currentData() or ""}
        self._sinkron_preset()
        self._perbarui_ringkas()
        self._simpan_tertunda.start()

    def _simpan_konfig(self):
        self.pengaturan.setValue("konfigurasi", self.konfig.ke_json())

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
        s.selera_siap.connect(self._selera_dihitung)
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
            teks = "Tersimpan di Windows ✓"
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
            self.label_kredensial.setText("Key lama dihapus. Tempel key baru.")
            self._perbarui_ringkas()
            return
        api_key = self.entry_api.text().strip()
        if not api_key:
            QMessageBox.information(self, "API key kosong", "Tempel API key Gemini dulu.")
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
        self.label_kredensial.setText("Tersimpan di Windows ✓")
        self._muat_model(api_key)
        self._perbarui_ringkas()

    def _toggle_mata(self):
        sembunyi = self.entry_api.echoMode() == QLineEdit.EchoMode.Password
        self.entry_api.setEchoMode(QLineEdit.EchoMode.Normal if sembunyi else QLineEdit.EchoMode.Password)
        self.tombol_mata.setIcon(buat_ikon_mata(not sembunyi))

    def _muat_model(self, api_key):
        self.field_model.help.setText("Memuat daftar model…")

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
            self.field_model.help.setText("Daftar model tidak bisa dimuat. Cek key dan internet.")
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
            panduan = "Paling teliti, tapi lambat dan mahal"
        elif "lite" in nama_model:
            panduan = "Paling cepat dan hemat"
        elif "flash" in nama_model:
            panduan = "Seimbang"
        else:
            panduan = "Bisa dipakai"
        self.field_model.help.setText(panduan)
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
        nama = self.pilihan_editor.currentText()
        self.pengaturan.setValue("editor", nama)
        self.konfig.editor = nama  # diingat untuk jenis sesi aktif
        self._sinkron_preset()
        self._perbarui_ringkas()
        self._simpan_tertunda.start()

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
                                   "Tidak ada JPEG/RAW di sini", badge_ok=False)
        self.baris_hasil.hide()
        self.tombol_editor.hide()
        self._gaya_tombol_mulai(sekunder=False)

    def _gaya_tombol_mulai(self, sekunder):
        """Setelah selesai, 'Buka editor' jadi aksi utama dan sortir turun jadi sekunder.
        Saat siap (folder dipilih), bayangan tombol sortir berdenyut pelan."""
        self.tombol_mulai.setText("Sortir lagi" if sekunder else "Sortir sekarang  →")
        self.tombol_mulai.setObjectName("Ghost" if sekunder else "Primary")
        if self._denyut:
            self._denyut.stop()
            self._denyut = None
        self.tombol_mulai.setGraphicsEffect(None)
        self._efek_mulai = None
        if not sekunder:
            self._efek_mulai = bayangan(self.tombol_mulai, blur=26, dy=8, alpha=60, warna=INK)
            if self.folder and self.jumlah_foto:
                self._denyut = QPropertyAnimation(self._efek_mulai, b"blurRadius", self)
                self._denyut.setDuration(2200)
                self._denyut.setKeyValueAt(0.0, 22.0)
                self._denyut.setKeyValueAt(0.5, 44.0)
                self._denyut.setKeyValueAt(1.0, 22.0)
                self._denyut.setEasingCurve(QEasingCurve.Type.InOutSine)
                self._denyut.setLoopCount(-1)
                self._denyut.start()
        segarkan_gaya(self.tombol_mulai)

    def _pasang_editor(self, editor):
        # Baca dulu: addItems memicu penyimpanan item pertama dan akan menimpanya.
        tersimpan = self.konfig.editor or self.pengaturan.value("editor", "", str)
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
            self.field_editor.help.setText("Belum ada editor foto yang terpasang.")
        self._perbarui_tombol_editor()
        self._perbarui_ringkas()

    def _perbarui_tombol_editor(self, _teks=None):
        nama = self.pilihan_editor.currentText() if self.editor_terdeteksi else ""
        self.tombol_editor.setText(f"Buka di {nama}  →" if nama else "Buka editor")
        self.tombol_editor.setEnabled(bool(nama))

    # ---- proses -----------------------------------------------------------
    def _atur_kontrol(self, sedang_proses):
        for w in (self.stepper, self.tombol_folder, self.tombol_belajar, self.tombol_pengaturan,
                  *self.chip_target.values()):
            w.setEnabled(not sedang_proses)
        self.tombol_mulai.setVisible(not sedang_proses)
        self.tombol_batal.setVisible(sedang_proses)
        self.tombol_batal.setEnabled(sedang_proses)
        self.latar.hidup(sedang_proses)

    def _mulai(self, hanya_belajar=False):
        api_key = self.entry_api.text().strip()
        target_teks = self.entry_target.text().strip()
        if not self.folder or not self.jumlah_foto:
            QMessageBox.information(self, "Pilih folder dulu", "Taruh folder sesi ke kotak di atas, atau klik kotaknya.")
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
            QMessageBox.information(self, "Kebanyakan", f"Folder ini hanya berisi {jumlah_foto} foto JPEG/RAW.")
            self.entry_target.setFocus()
            return

        self._simpan_tertunda.stop()
        self._simpan_konfig()
        self._atur_kontrol(True)
        self.tombol_editor.hide()
        self.baris_hasil.hide()
        self._gaya_tombol_mulai(sekunder=False)
        self._set_titik(AMBER)
        self._atur_progress(0, animasi=False)
        self._atur_data("")
        self.label_status.setText("Mulai belajar… file fotomu tidak diubah." if hanya_belajar else "Mulai…")
        self.pengaturan.setValue("target", target)
        self._simpan_model()
        self.penyortir.mulai(self.folder, api_key, target, self.pilihan_model.currentText(),
                             pakai_visual=self._visual_aktif(),
                             konfig=Konfigurasi.dari_json(self.konfig.ke_json()),  # salinan: aman diubah saat jalan
                             hanya_belajar=hanya_belajar)

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
            self._munculkan_hasil()
            sisa = teks[cocok.end():].strip(" .")
            self.label_status.setText("Selesai. " + (sisa + "." if sisa else "Cek hasilnya di editor."))
        else:
            self.label_status.setText(teks)
        if sukses and teks.startswith("Belajar selesai"):
            self._perbarui_selera(tawarkan=True)
        self._set_titik(MATCHA if sukses else KORAL)
        if sukses:
            self._atur_progress(100)
            self.tombol_editor.show()
            self.tombol_editor._skala = 0.86
            self.tombol_editor._ke(1.0, 480, QEasingCurve.Type.OutBack)  # muncul dengan sedikit "pop"
            QTimer.singleShot(500, self._mulai_riak)
            self._gaya_tombol_mulai(sekunder=bool(self.editor_terdeteksi))

    def _munculkan_hasil(self):
        """Chip hasil muncul satu per satu (memudar masuk)."""
        self.baris_hasil.show()
        self._anim_hasil = QSequentialAnimationGroup(self)
        for i, chip in enumerate(self.chip_hasil.values()):
            efek = chip.graphicsEffect()
            efek.setOpacity(0.0)
            if i:
                self._anim_hasil.addAnimation(QPauseAnimation(90, self))
            a = QPropertyAnimation(efek, b"opacity", self)
            a.setDuration(260)
            a.setStartValue(0.0)
            a.setEndValue(1.0)
            a.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._anim_hasil.addAnimation(a)
        self._anim_hasil.start()

    # ---- editor -----------------------------------------------------------
    def _mulai_riak(self):
        if self.tombol_editor.isVisible() and self.tombol_editor.isEnabled():
            self.riak_editor.mulai()

    def _buka_editor(self):
        nama = self.pilihan_editor.currentText()
        executable = self.editor_terdeteksi.get(nama)
        if not nama or not executable:
            QMessageBox.critical(self, "Editor tidak ditemukan", "Tidak ada editor yang bisa dibuka.")
            return
        if not self.folder:
            QMessageBox.information(self, "Pilih folder dulu", "Pilih folder foto dulu.")
            return
        self.riak_editor.berhenti()  # klimaks tercapai: sorotan tidak diperlukan lagi
        self.tombol_editor.setEnabled(False)
        self.label_status.setText(f"Membuka {nama}…")

        def kerja():
            try:
                self.sinyal.editor_dibuka.emit(core.buka_editor(nama, self.folder, executable), True)
            except Exception as error:
                self.sinyal.editor_dibuka.emit(f"{nama} gagal dibuka: {error}", False)

        threading.Thread(target=kerja, daemon=True).start()

    def _pelajari_koreksi(self):
        if not self.folder or not self.jumlah_foto:  # folder lama yang hanya jadi titik awal dialog tidak dihitung
            QMessageBox.information(self, "Pilih folder dulu", "Pilih folder sesi berisi foto yang ingin dipelajari.")
            return
        from . import belajar
        try:
            tercatat, diubah = belajar.kumpulkan_koreksi(self.folder, konfig=self.konfig)
        except Exception as error:
            QMessageBox.critical(self, "Gagal mencatat koreksi", str(error))
            return
        if not tercatat:
            from .cache import CacheHasil
            if not CacheHasil(self.folder, tanda="").prediksi:
                if tanya(self, "Pelajari pilihan yang sudah ada",
                         "Folder ini belum pernah disortir oleh Sortir AI.\n\n"
                         "Aplikasi bisa menilai foto-fotonya dulu (memakai token Gemini) lalu "
                         "membandingkan dengan rating yang sudah kamu atau klienmu berikan. "
                         "File fotomu tidak diubah sama sekali.\n\n"
                         "Foto tanpa rating dianggap tidak dipilih (Bad). Di Lightroom, "
                         "pastikan rating sudah disimpan ke file (Ctrl+S).",
                         "Pelajari"):
                    self._mulai(hanya_belajar=True)
                return
            else:
                pesan = ("Label di file belum terbaca.\n\n"
                         "Di Lightroom pilih semua foto lalu Ctrl+S (Save Metadata to File); "
                         "di Capture One pastikan sidecar XMP disinkronkan.")
            QMessageBox.information(self, "Belum ada data", pesan)
            return
        # Koreksi sudah tercatat = hasil sudah dicek di editor: cadangan XMP tidak diperlukan lagi.
        from . import metadata
        try:
            dibersihkan = metadata.hapus_cadangan(self.folder)
        except OSError as error:
            print(f"Gagal menghapus cadangan: {error}")
            dibersihkan = 0
        info_cadangan = f"\n\n{dibersihkan} file cadangan XMP dibersihkan." if dibersihkan else ""
        from . import selera
        total, setuju = belajar.ringkasan()
        lap = selera.laporan()["dasar"]
        if lap["kecocokan"] is not None:
            info_selera = f"Tebakan seleramu sekarang cocok {lap['kecocokan']}% dengan pilihanmu."
        else:
            info_selera = f"Seleramu mulai dipakai setelah {selera.MIN_DATA} foto ({lap['progres']}% terkumpul)."
        QMessageBox.information(
            self, "Koreksi tercatat",
            f"{tercatat} foto dicatat, {diubah} di antaranya kamu ubah.\n\n"
            f"Kamu setuju dengan {setuju}% pilihan aplikasi (dari {total} foto).\n{info_selera}\n\n"
            "Di Lightroom, pastikan metadata disimpan ke file (Ctrl+S)." + info_cadangan)
        self._perbarui_selera(tawarkan=True)

    # ---- selera ----------------------------------------------------------
    def _visual_aktif(self):
        return self.pengaturan.value("visual_aktif", False, bool)

    @staticmethod
    def _tanda_data_selera():
        """Berubah bila data koreksi (atau ketersediaan model visual) berubah."""
        from . import belajar, visual
        try:
            st = os.stat(belajar.FILE_DATA)
            return (st.st_mtime_ns, st.st_size, visual.tersedia())
        except OSError:
            return (0, 0, visual.tersedia())

    def _perbarui_selera(self, tawarkan=False):
        """Angka selera dihitung di thread terpisah dan disimpan sampai data koreksi berubah,
        jadi membuka pengaturan tidak pernah membekukan tampilan."""
        tanda = self._tanda_data_selera()
        cache = getattr(self, "_cache_selera", None)
        if cache and cache[0] == tanda:
            self._tampilkan_selera(cache[1], cache[2], tawarkan)
            return
        if cache is None:
            self.label_dasar.setText("Menghitung…")
            self.label_selera.setText("Menghitung…")
        if getattr(self, "_selera_dihitung_jalan", False):
            self._selera_tawarkan_nanti = self._selera_tawarkan_nanti or tawarkan
            return
        self._selera_dihitung_jalan = True
        self._selera_tawarkan_nanti = tawarkan

        def kerja():
            from . import selera, visual
            try:
                lap = selera.laporan()
            except Exception as error:
                print(f"Laporan selera gagal: {error}")
                lap = {k: {"jumlah": 0, "minimum": m, "progres": 0, "kecocokan": None}
                       for k, m in (("dasar", selera.MIN_DATA), ("visual", selera.MIN_DATA_VISUAL))}
            uji = {"siap": False, "jumlah": 0, "lebih_baik_persen": None}
            if visual.tersedia():
                try:
                    uji = selera.uji_visual()
                except Exception as error:
                    print(f"Uji selera visual gagal: {error}")
            self.sinyal.selera_siap.emit((tanda, lap, uji))

        threading.Thread(target=kerja, daemon=True).start()

    def _selera_dihitung(self, hasil):
        self._selera_dihitung_jalan = False
        self._cache_selera = hasil
        tawarkan, self._selera_tawarkan_nanti = self._selera_tawarkan_nanti, False
        if hasil[0] != self._tanda_data_selera():  # data berubah saat menghitung: hitung lagi
            self._perbarui_selera(tawarkan)
            return
        self._tampilkan_selera(hasil[1], hasil[2], tawarkan)

    def _tampilkan_selera(self, lap, uji, tawarkan=False):
        from . import visual
        d = lap["dasar"]
        self.progres_dasar.setValue(d["progres"])
        if d["kecocokan"] is not None:
            self.label_dasar.setText(f"Aktif · {d['jumlah']} foto · cocok {d['kecocokan']}% dengan pilihanmu")
        else:
            self.label_dasar.setText(f"Mengumpulkan data · {d['jumlah']}/{d['minimum']} foto ({d['progres']}%)")

        v = lap["visual"]
        self.progres_visual.setValue(v["progres"])
        if not visual.tersedia():
            self.tombol_visual.setEnabled(False)
            if not visual.onnxruntime_ada():
                self.tombol_unduh_visual.hide()
                self.label_selera.setText("Butuh onnxruntime. Buka aplikasi lewat 'Buka Sortir AI.bat'.")
            else:
                self.tombol_unduh_visual.show()
                self.label_selera.setText("Opsional. Unduh sekali agar aplikasi juga belajar dari tampilan foto.")
            return
        self.tombol_unduh_visual.hide()
        aktif = self._visual_aktif()
        self.tombol_visual.blockSignals(True)
        self.tombol_visual.setChecked(aktif)
        self.tombol_visual.blockSignals(False)
        self.tombol_visual._geser(1.0 if aktif else 0.0)
        self.tombol_visual.setEnabled(aktif or uji["siap"])
        cocok = f" · cocok {v['kecocokan']}%" if v["kecocokan"] is not None else ""
        if aktif:
            teks = f"Nyala · {v['jumlah']} foto{cocok}"
        elif uji["siap"]:
            teks = f"Siap dinyalakan · {uji['lebih_baik_persen']}% lebih tepat dari yang dasar{cocok}"
        elif v["jumlah"] < v["minimum"]:
            teks = f"Mengumpulkan data · {v['jumlah']}/{v['minimum']} foto ({v['progres']}%)"
        else:
            teks = f"Data cukup, tapi belum lebih tepat dari yang dasar{cocok}. Dicek lagi tiap koreksi."
        self.label_selera.setText(teks)

        # Tawaran sekali; muncul lagi setelah +500 foto bila tadi memilih "Nanti".
        ditawarkan = int(self.pengaturan.value("visual_ditawarkan", 0) or 0)
        if tawarkan and uji["siap"] and not aktif and (not ditawarkan or uji["jumlah"] >= ditawarkan + 500):
            self.pengaturan.setValue("visual_ditawarkan", uji["jumlah"])
            kotak = QMessageBox(self)
            kotak.setWindowTitle("Selera visual siap")
            kotak.setText(f"Selera visual menebak pilihanmu {uji['lebih_baik_persen']}% lebih tepat "
                          f"dari yang dasar ({uji['jumlah']} foto).\n\n"
                          "Nyalakan sekarang? Bisa dimatikan kapan saja di Pengaturan.")
            tombol_ya = kotak.addButton("Nyalakan", QMessageBox.ButtonRole.AcceptRole)
            kotak.addButton("Nanti", QMessageBox.ButtonRole.RejectRole)
            kotak.exec()
            if kotak.clickedButton() is tombol_ya:
                self.pengaturan.setValue("visual_aktif", True)
                self._perbarui_selera()

    def _unduh_visual(self):
        from . import visual
        if not tanya(self, "Unduh model visual",
                     "Unduh model CLIP (89 MB) dari Hugging Face (Xenova/clip-vit-base-patch32)?\n\n"
                     f"Disimpan di: {visual.FILE_MODEL}", "Unduh"):
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
                      "Data sekarang disimpan di arsip (1 slot; arsip sebelumnya diganti). "
                      "Aplikasi belajar lagi dari koreksi berikutnya.")
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
            if not tanya(self, "Masih jalan", "Sortir masih berjalan. Tutup dan batalkan?", "Tutup"):
                event.ignore()
                return
            self.penyortir.batalkan()
        self._simpan_tertunda.stop()
        self._simpan_konfig()
        event.accept()


# ---------------------------------------------------------------------------
# Ikon kecil (digambar dengan gaya garis yang sama, tanpa file gambar)
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
    """Gir lembut: lingkaran bergerigi membulat, sesuai gaya garis ikon lain."""
    pix, p = _kanvas(48)
    jalur = QPainterPath()
    gigi = 8
    for i in range(gigi * 4 + 1):
        sudut = i * 2 * math.pi / (gigi * 4)
        r = 18 if (i // 2) % 2 == 0 else 14.5
        titik = QPointF(24 + r * math.cos(sudut), 24 + r * math.sin(sudut))
        jalur.moveTo(titik) if i == 0 else jalur.lineTo(titik)
    p.setPen(_pena(warna, 3.2))
    p.drawPath(jalur)
    p.drawEllipse(QPointF(24, 24), 5.5, 5.5)
    p.end()
    return QIcon(pix)


def buat_ikon_folder(warna, centang=False):
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
    # Gaya logo: badan matcha padat dengan kilau lembut, bintang krem, aksen koral.
    dasar = QColor(warna)
    kilau = QRadialGradient(QPointF(20, 18), 52)
    kilau.setColorAt(0.0, dasar.lighter(128))
    kilau.setColorAt(1.0, dasar.darker(112))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(kilau)
    p.drawPath(jalur)
    if centang:  # folder sudah dipilih
        pena = _pena(KREM, 4.0)
        p.setPen(pena)
        p.drawLine(QPointF(25, 38), QPointF(31.5, 44.5))
        p.drawLine(QPointF(31.5, 44.5), QPointF(44, 31))
    else:
        p.setBrush(QColor(KREM))
        p.drawPath(_bintang(QPointF(34, 38), 11))
        p.setBrush(QColor(KORAL))
        p.drawPath(_bintang(QPointF(49, 29), 5.5))
    p.end()
    return QIcon(pix)


def _bintang(pusat, r):
    """Bintang empat sudut dengan sisi melengkung ke dalam, seperti pada logo."""
    jalur = QPainterPath(QPointF(pusat.x(), pusat.y() - r))
    titik = [QPointF(pusat.x() + r, pusat.y()), QPointF(pusat.x(), pusat.y() + r),
             QPointF(pusat.x() - r, pusat.y()), QPointF(pusat.x(), pusat.y() - r)]
    sebelum = jalur.currentPosition()
    for t in titik:
        # Titik kendali sedikit keluar dari pusat agar bintang "gemuk", tidak lancip seperti jarum.
        kendali = pusat + ((sebelum + t) / 2 - pusat) * 0.28
        jalur.quadTo(kendali, t)
        sebelum = t
    return jalur


def buat_ikon_bulat(warna):
    pix, p = _kanvas(16)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(warna))
    p.drawEllipse(2, 2, 12, 12)
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
    # Desain krem dirancang untuk mode terang; tanpa ini dialog Qt ikut mode gelap Windows
    # dan teks tinta jadi tak terbaca di atas latar gelap.
    try:
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    except AttributeError:  # Qt < 6.8
        pass
    app.setApplicationName("Sortir AI")
    app.setWindowIcon(QIcon(PATH_IKON))
    app.setStyleSheet(stylesheet())
    app.setFont(QFont("Segoe UI", 10))
    jendela = JendelaSortir()
    jendela.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
