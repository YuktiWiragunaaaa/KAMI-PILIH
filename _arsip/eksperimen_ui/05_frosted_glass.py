import sys
import os
import ctypes

from PIL import Image, ImageFilter

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor,
    QImage,
    QPainter,
    QPainterPath,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLineEdit,
    QComboBox,
)


# ============================================================
# WINDOWS MICA
# ============================================================

def aktifkan_mica(hwnd):

    if os.name != "nt":
        return False

    try:
        DWMWA_SYSTEMBACKDROP_TYPE = 38
        DWMSBT_MAINWINDOW = 2

        value = ctypes.c_int(DWMSBT_MAINWINDOW)

        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd),
            DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )

        print("DwmSetWindowAttribute result =", result)

        if result == 0:
            print("Mica berhasil diaktifkan.")
            return True

        return False

    except Exception as error:
        print("Mica error:", error)
        return False


# ============================================================
# BACKGROUND
# ============================================================

class Background(QWidget):

    def __init__(self):

        super().__init__()

        self.setObjectName("Background")

    def gambar_scene(self, painter):

        width = self.width()
        height = self.height()

        # ----------------------------------------------------
        # Background gradient
        # ----------------------------------------------------

        from PySide6.QtGui import QLinearGradient

        gradient = QLinearGradient(
            0,
            0,
            width,
            height,
        )

        gradient.setColorAt(
            0.0,
            QColor("#06121E"),
        )

        gradient.setColorAt(
            0.45,
            QColor("#0A2233"),
        )

        gradient.setColorAt(
            1.0,
            QColor("#050B12"),
        )

        painter.fillRect(
            0,
            0,
            width,
            height,
            gradient,
        )

        painter.setPen(
            Qt.PenStyle.NoPen
        )

        # ----------------------------------------------------
        # CYAN GLOW
        # ----------------------------------------------------

        for radius, alpha in [
            (330, 12),
            (270, 18),
            (210, 24),
            (150, 32),
            (100, 42),
        ]:

            painter.setBrush(
                QColor(
                    40,
                    210,
                    220,
                    alpha,
                )
            )

            painter.drawEllipse(
                -radius // 2,
                -radius // 2,
                radius,
                radius,
            )

        # ----------------------------------------------------
        # ORANGE GLOW
        # ----------------------------------------------------

        for radius, alpha in [
            (300, 8),
            (240, 13),
            (180, 20),
            (120, 28),
        ]:

            painter.setBrush(
                QColor(
                    235,
                    145,
                    70,
                    alpha,
                )
            )

            painter.drawEllipse(
                width - radius // 2,
                height - radius // 2,
                radius,
                radius,
            )

        # ----------------------------------------------------
        # DECORATIVE CODE
        # ----------------------------------------------------

        painter.setPen(
            QColor(
                85,
                170,
                200,
                35,
            )
        )

        code = [
            "vision_score = composition + focus + moment",
            "model.generate_content(images)",
            "classification = Excellent / Good / Bad",
            "for batch in photo_batches:",
            "    analyze(frame)",
            "    write_xmp(metadata)",
            "RAW -> JPEG -> AI -> XMP -> EDITOR",
            "sort_result = curate_collection()",
        ]

        y = 65

        for line in code:

            painter.drawText(
                24,
                y,
                line,
            )

            y += 21

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        self.gambar_scene(
            painter
        )


# ============================================================
# FROSTED GLASS CARD
# ============================================================

class GlassCard(QFrame):

    def __init__(self, background):

        super().__init__()

        self.background = background

        self.blurred_image = None

        self.setObjectName(
            "GlassCard"
        )

        # ----------------------------------------------------
        # Content
        # ----------------------------------------------------

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            30,
            28,
            30,
            30,
        )

        layout.setSpacing(
            8
        )

        eyebrow = QLabel(
            "CONFIGURATION"
        )

        eyebrow.setObjectName(
            "Eyebrow"
        )

        title = QLabel(
            "Sortir AI"
        )

        title.setObjectName(
            "CardTitle"
        )

        subtitle = QLabel(
            "Frosted glass panel dengan "
            "background blur."
        )

        subtitle.setObjectName(
            "CardSubtitle"
        )

        layout.addWidget(
            eyebrow
        )

        layout.addWidget(
            title
        )

        layout.addWidget(
            subtitle
        )

        layout.addSpacing(
            18
        )

        # ----------------------------------------------------
        # API
        # ----------------------------------------------------

        api_label = QLabel(
            "API KEY GEMINI"
        )

        api_label.setObjectName(
            "FieldLabel"
        )

        api_input = QLineEdit()

        api_input.setPlaceholderText(
            "Masukkan API key..."
        )

        api_input.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        api_input.setObjectName(
            "GlassInput"
        )

        layout.addWidget(
            api_label
        )

        layout.addWidget(
            api_input
        )

        # ----------------------------------------------------
        # Model
        # ----------------------------------------------------

        model_label = QLabel(
            "MODEL GEMINI"
        )

        model_label.setObjectName(
            "FieldLabel"
        )

        model = QComboBox()

        model.addItems(
            [
                "gemini-3.5-flash-lite",
                "gemini-2.5-flash",
                "gemini-2.5-pro",
            ]
        )

        model.setObjectName(
            "GlassCombo"
        )

        layout.addWidget(
            model_label
        )

        layout.addWidget(
            model
        )

        # ----------------------------------------------------
        # Target
        # ----------------------------------------------------

        target_label = QLabel(
            "TARGET FOTO EXCELLENT"
        )

        target_label.setObjectName(
            "FieldLabel"
        )

        target = QLineEdit()

        target.setPlaceholderText(
            "Jumlah foto..."
        )

        target.setObjectName(
            "GlassInput"
        )

        layout.addWidget(
            target_label
        )

        layout.addWidget(
            target
        )

        # ----------------------------------------------------
        # Folder
        # ----------------------------------------------------

        folder_label = QLabel(
            "FOLDER FOTO"
        )

        folder_label.setObjectName(
            "FieldLabel"
        )

        folder_row = QHBoxLayout()

        folder_button = QPushButton(
            "Pilih folder"
        )

        folder_button.setObjectName(
            "SecondaryButton"
        )

        folder_text = QLabel(
            "Belum ada folder dipilih"
        )

        folder_text.setObjectName(
            "MutedText"
        )

        folder_row.addWidget(
            folder_button
        )

        folder_row.addWidget(
            folder_text
        )

        folder_row.addStretch()

        layout.addWidget(
            folder_label
        )

        layout.addLayout(
            folder_row
        )

        layout.addStretch()

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        status_row = QHBoxLayout()

        status = QLabel(
            "●  Siap memulai"
        )

        status.setObjectName(
            "Status"
        )

        percent = QLabel(
            "0%"
        )

        percent.setObjectName(
            "Percent"
        )

        status_row.addWidget(
            status
        )

        status_row.addStretch()

        status_row.addWidget(
            percent
        )

        layout.addLayout(
            status_row
        )

        # ----------------------------------------------------
        # Buttons
        # ----------------------------------------------------

        button_row = QHBoxLayout()

        button_row.addStretch()

        cancel = QPushButton(
            "Batalkan"
        )

        cancel.setObjectName(
            "CancelButton"
        )

        start = QPushButton(
            "✦  Mulai sortir"
        )

        start.setObjectName(
            "PrimaryButton"
        )

        button_row.addWidget(
            cancel
        )

        button_row.addWidget(
            start
        )

        layout.addLayout(
            button_row
        )

        # ----------------------------------------------------
        # Initial blur
        # ----------------------------------------------------

        self.update_blur()

    # ========================================================
    # CONVERT QIMAGE -> PIL
    # ========================================================

    def qimage_to_pil(self, image):

        image = image.convertToFormat(
            QImage.Format.Format_RGBA8888
        )

        width = image.width()
        height = image.height()

        data = image.bits().tobytes()

        return Image.frombytes(
            "RGBA",
            (width, height),
            data,
        )

    # ========================================================
    # CONVERT PIL -> QIMAGE
    # ========================================================

    def pil_to_qimage(self, image):

        image = image.convert(
            "RGBA"
        )

        width, height = image.size

        data = image.tobytes(
            "raw",
            "RGBA",
        )

        result = QImage(
            data,
            width,
            height,
            width * 4,
            QImage.Format.Format_RGBA8888,
        )

        return result.copy()

    # ========================================================
    # CREATE TRUE BLUR
    # ========================================================

    def update_blur(self):

        if not self.isVisible():
            return

        width = self.width()
        height = self.height()

        if width <= 0 or height <= 0:
            return

        # ----------------------------------------------------
        # Render background
        # ----------------------------------------------------

        image = QImage(
            self.background.size(),
            QImage.Format.Format_ARGB32,
        )

        image.fill(
            Qt.GlobalColor.transparent
        )

        painter = QPainter(image)

        self.background.gambar_scene(
            painter
        )

        painter.end()

        # ----------------------------------------------------
        # Position card relative to background
        # ----------------------------------------------------

        x = self.x()
        y = self.y()

        source = image.copy(
            x,
            y,
            width,
            height,
        )

        # ----------------------------------------------------
        # Gaussian Blur
        # ----------------------------------------------------

        pil = self.qimage_to_pil(
            source
        )

        pil = pil.filter(
            ImageFilter.GaussianBlur(
                radius=28
            )
        )

        self.blurred_image = self.pil_to_qimage(
            pil
        )

        self.update()

    # ========================================================
    # PAINT GLASS
    # ========================================================

    def paintEvent(self, event):

        painter = QPainter(
            self
        )

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        # ----------------------------------------------------
        # Rounded shape
        # ----------------------------------------------------

        path = QPainterPath()

        path.addRoundedRect(
            0,
            0,
            self.width(),
            self.height(),
            24,
            24,
        )

        painter.setClipPath(
            path
        )

        # ----------------------------------------------------
        # BLURRED BACKGROUND
        # ----------------------------------------------------

        if self.blurred_image is not None:

            painter.drawImage(
                0,
                0,
                self.blurred_image
            )

        # ----------------------------------------------------
        # GLASS TINT
        # ----------------------------------------------------

        painter.fillPath(
            path,
            QColor(
                15,
                37,
                52,
                85,
            )
        )

        # ----------------------------------------------------
        # SUBTLE WHITE HIGHLIGHT
        # ----------------------------------------------------

        top_path = QPainterPath()

        top_path.addRoundedRect(
            1,
            1,
            self.width() - 2,
            65,
            22,
            22,
        )

        painter.fillPath(
            top_path,
            QColor(
                255,
                255,
                255,
                9,
            )
        )

        # ----------------------------------------------------
        # BORDER
        # ----------------------------------------------------

        painter.setClipping(
            False
        )

        painter.setPen(
            QColor(
                220,
                240,
                248,
                65,
            )
        )

        painter.setBrush(
            Qt.BrushStyle.NoBrush
        )

        painter.drawRoundedRect(
            0.5,
            0.5,
            self.width() - 1,
            self.height() - 1,
            24,
            24,
        )

        # ----------------------------------------------------
        # TOP EDGE
        # ----------------------------------------------------

        painter.setPen(
            QColor(
                120,
                232,
                214,
                150,
            )
        )

        painter.drawLine(
            24,
            1,
            min(
                self.width() - 24,
                260,
            ),
            1,
        )

        painter.end()

    def resizeEvent(self, event):

        super().resizeEvent(
            event
        )

        self.update_blur()


# ============================================================
# MAIN WINDOW
# ============================================================

class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "Sortir AI | Frosted Glass Test"
        )

        self.resize(
            920,
            820
        )

        # ----------------------------------------------------
        # Background
        # ----------------------------------------------------

        background = Background()

        layout = QVBoxLayout(
            background
        )

        layout.setContentsMargins(
            80,
            55,
            80,
            55,
        )

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        eyebrow = QLabel(
            "AI PHOTO CURATION"
        )

        eyebrow.setObjectName(
            "HeaderEyebrow"
        )

        title = QLabel(
            "Sortir AI"
        )

        title.setObjectName(
            "MainTitle"
        )

        subtitle = QLabel(
            "True frosted glass experiment"
        )

        subtitle.setObjectName(
            "MainSubtitle"
        )

        layout.addWidget(
            eyebrow
        )

        layout.addWidget(
            title
        )

        layout.addWidget(
            subtitle
        )

        layout.addSpacing(
            25
        )

        # ----------------------------------------------------
        # Glass card
        # ----------------------------------------------------

        card = GlassCard(
            background
        )

        layout.addWidget(
            card
        )

        layout.addStretch()

        self.setCentralWidget(
            background
        )

        # ----------------------------------------------------
        # STYLE
        # ----------------------------------------------------

        self.setStyleSheet("""

            QMainWindow {
                background: #071522;
            }

            QWidget#Background {
                background: transparent;
            }


            QLabel#HeaderEyebrow {
                color: #78E8D6;
                font-size: 9px;
                font-weight: 700;
            }

            QLabel#MainTitle {
                color: #F4FAFD;
                font-size: 34px;
                font-weight: 700;
            }

            QLabel#MainSubtitle {
                color: rgba(220,235,245,180);
                font-size: 11px;
            }


            QLabel#Eyebrow {
                color: #78E8D6;
                font-size: 9px;
                font-weight: 700;
            }

            QLabel#CardTitle {
                color: #F4FAFD;
                font-size: 28px;
                font-weight: 700;
            }

            QLabel#CardSubtitle {
                color: rgba(220,235,245,185);
                font-size: 10px;
            }


            QLabel#FieldLabel {
                color: #DCEBF3;
                font-size: 9px;
                font-weight: 600;
            }


            QLineEdit#GlassInput {

                background-color:
                    rgba(3, 17, 28, 150);

                color:
                    #F4FAFD;

                border:
                    1px solid
                    rgba(190,220,235,40);

                border-radius:
                    10px;

                padding:
                    9px 11px;
            }

            QLineEdit#GlassInput:focus {

                border:
                    1px solid
                    #78E8D6;
            }


            QComboBox#GlassCombo {

                background-color:
                    rgba(3,17,28,150);

                color:
                    #F4FAFD;

                border:
                    1px solid
                    rgba(190,220,235,40);

                border-radius:
                    10px;

                padding:
                    8px 10px;
            }


            QPushButton#SecondaryButton {

                background-color:
                    rgba(255,255,255,24);

                color:
                    #EAF5F9;

                border:
                    1px solid
                    rgba(255,255,255,45);

                border-radius:
                    9px;

                padding:
                    9px 16px;
            }

            QPushButton#SecondaryButton:hover {

                background-color:
                    rgba(255,255,255,42);
            }


            QLabel#MutedText {

                color:
                    rgba(215,235,245,145);

                font-size:
                    9px;
            }


            QLabel#Status {

                color:
                    #78E8D6;

                font-size:
                    9px;

                font-weight:
                    600;
            }

            QLabel#Percent {

                color:
                    #78E8D6;

                font-size:
                    9px;

                font-weight:
                    700;
            }


            QPushButton#CancelButton {

                background-color:
                    rgba(255,255,255,18);

                color:
                    #FF9999;

                border:
                    1px solid
                    rgba(255,255,255,30);

                border-radius:
                    10px;

                padding:
                    10px 18px;
            }


            QPushButton#PrimaryButton {

                background-color:
                    rgba(23,97,129,220);

                color:
                    white;

                border:
                    1px solid
                    rgba(140,230,235,80);

                border-radius:
                    10px;

                padding:
                    10px 20px;

                font-weight:
                    700;
            }

            QPushButton#PrimaryButton:hover {

                background-color:
                    #227EA3;
            }

            QPushButton#PrimaryButton:pressed {

                background-color:
                    #14536E;
            }

        """)

        # ----------------------------------------------------
        # Mica
        # ----------------------------------------------------

        self.show()

        hwnd = int(
            self.winId()
        )

        print(
            "HWND =",
            hwnd
        )

        aktifkan_mica(
            hwnd
        )

        # ----------------------------------------------------
        # Refresh glass after layout
        # ----------------------------------------------------

        from PySide6.QtCore import QTimer

        QTimer.singleShot(
            150,
            card.update_blur
        )


# ============================================================
# MAIN
# ============================================================

def main():

    app = QApplication(
        sys.argv
    )

    window = MainWindow()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()