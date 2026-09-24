import sys
import os
import ctypes

from PIL import Image, ImageFilter

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QImage,
    QPainter,
    QPainterPath,
    QLinearGradient,
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
    QProgressBar,
)
from numpy import gradient


# ============================================================
# WINDOWS MICA
# ============================================================

def aktifkan_mica(hwnd):

    if os.name != "nt":
        return False

    try:
        DWMWA_SYSTEMBACKDROP_TYPE = 38
        DWMSBT_MAINWINDOW = 3

        value = ctypes.c_int(DWMSBT_MAINWINDOW)
        dwmapi = ctypes.WinDLL("dwmapi")

        result = dwmapi.DwmSetWindowAttribute(
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

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )

    def gambar_scene(self, painter):

        width = self.width()
        height = self.height()

        # ----------------------------------------------------
        # BACKGROUND GRADIENT
        # ----------------------------------------------------

        gradient = QLinearGradient(
            0,
            0,
            width,
            height,
        )

        gradient.setColorAt(
            0.0,
            QColor(6, 18, 30, 105),
        )

        gradient.setColorAt(
            0.42,
            QColor(10, 36, 53, 95),
        )

        gradient.setColorAt(
            0.72,
            QColor(7, 23, 34, 90),
        )

        gradient.setColorAt(
            1.0,
            QColor(4, 10, 16, 100),
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

        cyan_x = int(width * 0.12)
        cyan_y = int(height * 0.12)

        for radius, alpha in [
            (420, 5),
            (340, 8),
            (280, 12),
            (220, 17),
            (170, 24),
            (120, 32),
            (80, 42),
        ]:

            painter.setBrush(
                QColor(
                    45,
                    215,
                    225,
                    alpha,
                )
            )

            painter.drawEllipse(
                cyan_x - radius // 2,
                cyan_y - radius // 2,
                radius,
                radius,
            )

        # ----------------------------------------------------
        # SECOND CYAN GLOW
        # ----------------------------------------------------

        cyan2_x = int(width * 0.90)
        cyan2_y = int(height * 0.30)

        for radius, alpha in [
            (280, 4),
            (220, 7),
            (170, 11),
            (120, 16),
            (80, 22),
        ]:

            painter.setBrush(
                QColor(
                    50,
                    180,
                    230,
                    alpha,
                )
            )

            painter.drawEllipse(
                cyan2_x - radius // 2,
                cyan2_y - radius // 2,
                radius,
                radius,
            )

        # ----------------------------------------------------
        # ORANGE GLOW
        # ----------------------------------------------------

        orange_x = int(width * 0.88)
        orange_y = int(height * 0.88)

        for radius, alpha in [
            (320, 4),
            (260, 7),
            (210, 11),
            (160, 16),
            (110, 23),
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
                orange_x - radius // 2,
                orange_y - radius // 2,
                radius,
                radius,
            )

        # ----------------------------------------------------
        # DECORATIVE AI CODE
        # ----------------------------------------------------

        painter.setPen(
            QColor(
                100,
                190,
                215,
                30,
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
            "confidence = model.evaluate(photo)",
        ]

        y = 72

        for line in code:

            painter.drawText(
                28,
                y,
                line,
            )

            y += 23

        # ----------------------------------------------------
        # SECONDARY CODE
        # ----------------------------------------------------

        painter.setPen(
            QColor(
                100,
                190,
                215,
                16,
            )
        )

        right_code = [
            "AI PHOTO CURATION",
            "batch.process()",
            "metadata.write()",
            "editor.detect()",
            "collection.optimize()",
        ]

        y2 = int(height * 0.48)

        for line in right_code:

            painter.drawText(
                int(width * 0.70),
                y2,
                line,
            )

            y2 += 22

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        self.gambar_scene(
            painter
        )

        painter.end()


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
        # CONTENT LAYOUT
        # ----------------------------------------------------

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            34,
            30,
            34,
            32,
        )

        layout.setSpacing(
            8
        )

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

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
            "AI-powered photo curation"
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
            20
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
        # MODEL
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
        # TARGET
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
        # FOLDER
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

        # ----------------------------------------------------
        # SPACE
        # ----------------------------------------------------

        layout.addStretch()

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        status_row = QHBoxLayout()

        self.status = QLabel(
            "●  Siap memulai"
        )

        self.status.setObjectName(
            "Status"
        )

        self.status_dots = 0

        self.status_timer = QTimer(self)

        self.status_timer.timeout.connect(
            self.update_status_animation
        )

        progress = QProgressBar()

        progress.setRange(
            0,
            100
        )

        progress.setValue(0)

        progress.setTextVisible(
            False
        )

        progress.setObjectName(
            "GlassProgress"
        )

        percent = QLabel(
            "42%"
        )

        percent.setObjectName(
            "Percent"
        )

        status_row.addWidget(
            self.status
        )

        status_row.addSpacing(
            12
        )

        status_row.addWidget(
            progress
        )

        status_row.addSpacing(
            12
        )

        status_row.addWidget(
            percent
        )

        layout.addLayout(
    status_row
)

        # ----------------------------------------------------
        # BUTTONS
        # ----------------------------------------------------

        button_row = QHBoxLayout()

        button_row.setSpacing(
            8
        )

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
        # INITIAL BLUR
        # ----------------------------------------------------

        self.update_blur()

    # ========================================================
    # QIMAGE -> PIL
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
    # PIL -> QIMAGE
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
    # CREATE FROSTED BACKGROUND
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

        painter = QPainter(
            image
        )

        self.background.gambar_scene(
            painter
        )

        painter.end()

        # ----------------------------------------------------
        # Card position
        # ----------------------------------------------------

        x = self.x()
        y = self.y()

        # Tambahkan area sedikit di luar card supaya blur
        # tidak berhenti terlalu keras di tepi.

        padding = 18

        source_x = max(
            0,
            x - padding
        )

        source_y = max(
            0,
            y - padding
        )

        source_width = min(
            width + padding * 2,
            image.width() - source_x
        )

        source_height = min(
            height + padding * 2,
            image.height() - source_y
        )

        if source_width <= 0 or source_height <= 0:
            return

        source = image.copy(
            source_x,
            source_y,
            source_width,
            source_height,
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

        blurred = self.pil_to_qimage(
            pil
        )

        # Crop kembali ke ukuran card

        crop_x = x - source_x
        crop_y = y - source_y

        self.blurred_image = blurred.copy(
            crop_x,
            crop_y,
            width,
            height,
        )

        self.update()

    def update_status_animation(self):

        self.status_dots += 1

        if self.status_dots > 3:
            self.status_dots = 1

        dots = "." * self.status_dots

        self.status.setText(
            f"●  Menganalisis{dots}"
        )


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
        # ROUNDED CLIP
        # ----------------------------------------------------

        path = QPainterPath()

        path.addRoundedRect(
            0,
            0,
            self.width(),
            self.height(),
            26,
            26,
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
                self.blurred_image,
            )

        # ----------------------------------------------------
        # VERY LIGHT GLASS TINT
        # ----------------------------------------------------

        painter.fillPath(
            path,
            QColor(
                225,
                225,
                225,
                10,
            ),
        )

        # ----------------------------------------------------
        # SOFT WHITE GLASS LAYER
        # ----------------------------------------------------

        painter.fillPath(
            path,
            QColor(
                255,
                255,
                255,
                4,
            ),
        )

        # ----------------------------------------------------
        # TOP GLASS HIGHLIGHT
        # ----------------------------------------------------

        highlight = QLinearGradient(
            0,
            0,
            0,
            110,
        )

        highlight.setColorAt(
            0.0,
            QColor(
                255,
                255,
                255,
                24,
            ),
        )

        highlight.setColorAt(
            0.45,
            QColor(
                255,
                255,
                255,
                7,
            ),
        )

        highlight.setColorAt(
            1.0,
            QColor(
                255,
                255,
                255,
                0,
            ),
        )

        painter.fillPath(
            path,
            highlight,
        )

        # ----------------------------------------------------
        # INNER TOP LINE
        # ----------------------------------------------------

        painter.setClipping(
            False
        )

        painter.setPen(
            QColor(
                220,
                245,
                250,
                70,
            )
        )

        painter.drawLine(
            26,
            1,
            min(
                self.width() - 26,
                300,
            ),
            1,
        )

        # ----------------------------------------------------
        # OUTER BORDER
        # ----------------------------------------------------

        painter.setPen(
            QColor(
                215,
                240,
                248,
                32,
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
            26,
            26,
        )

        # ----------------------------------------------------
        # SUBTLE CYAN EDGE
        # ----------------------------------------------------

        painter.setPen(
            QColor(
                120,
                232,
                214,
                22,
            )
        )

        painter.drawRoundedRect(
            1.5,
            1.5,
            self.width() - 3,
            self.height() - 3,
            25,
            25,
        )

        painter.end()

    # ========================================================
    # RESIZE
    # ========================================================

    def resizeEvent(self, event):

        super().resizeEvent(
            event
        )

        QTimer.singleShot(
            20,
            self.update_blur
        )


# ============================================================
# MAIN WINDOW
# ============================================================

class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "Sortir AI | Glass UI"
        )

        self.resize(
            920,
            820,
        )

        # ----------------------------------------------------
        # BACKGROUND
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

        layout.setSpacing(
            0
        )

        # ----------------------------------------------------
        # HEADER
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
            "Intelligent photo curation, "
            "inside a frosted glass interface."
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
        # GLASS CARD
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
                background: #06121E;
            }

            QWidget#Background {
                background: transparent;
            }


            /* ==================================================
               HEADER
               ================================================== */

            QLabel#HeaderEyebrow {
                color: #78E8D6;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 2px;
            }

            QLabel#MainTitle {
                color: #F4FAFD;
                font-size: 36px;
                font-weight: 700;
            }

            QLabel#MainSubtitle {
                color: rgba(220,235,245,175);
                font-size: 11px;
            }


            /* ==================================================
               GLASS CARD
               ================================================== */

            QFrame#GlassCard {
                background: transparent;
            }


            /* ==================================================
               CARD TEXT
               ================================================== */

            QLabel#Eyebrow {
                color: #78E8D6;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1.5px;
            }

            QLabel#CardTitle {
                color: #F4FAFD;
                font-size: 28px;
                font-weight: 700;
            }

            QLabel#CardSubtitle {
                color: rgba(220,235,245,180);
                font-size: 10px;
            }


            /* ==================================================
               FIELD LABEL
               ================================================== */

            QLabel#FieldLabel {
                color: rgba(225,242,248,220);
                font-size: 9px;
                font-weight: 600;
            }


            /* ==================================================
               INPUT
               ================================================== */

            QLineEdit#GlassInput {

                background-color:
                    rgba(2, 14, 24, 95);

                color:
                    #F4FAFD;

                border:
                    1px solid
                    rgba(220,240,248,55);

                border-radius:
                    11px;

                padding:
                    10px 12px;

                selection-background-color:
                    rgba(120,232,214,90);

                selection-color:
                    white;
            }

            QLineEdit#GlassInput:hover {

                background-color:
                    rgba(5, 22, 34, 115);

                border:
                    1px solid
                    rgba(220,240,248,75);
            }

            QLineEdit#GlassInput:focus {

                background-color:
                    rgba(4, 24, 36, 125);

                border:
                    1px solid
                    rgba(120,232,214,190);
            }


            /* ==================================================
               COMBOBOX
               ================================================== */

            QComboBox#GlassCombo {

                background-color:
                    rgba(2,14,24,95);

                color:
                    #F4FAFD;

                border:
                    1px solid
                    rgba(220,240,248,55);

                border-radius:
                    11px;

                padding:
                    9px 12px;
            }

            QComboBox#GlassCombo:hover {

                background-color:
                    rgba(5,22,34,115);

                border:
                    1px solid
                    rgba(220,240,248,75);
            }

            QComboBox#GlassCombo:focus {

                border:
                    1px solid
                    rgba(120,232,214,190);
            }

            QComboBox#GlassCombo QAbstractItemView {

                background:
                    #102636;

                color:
                    #F4FAFD;

                border:
                    1px solid
                    rgba(220,240,248,60);

                selection-background-color:
                    #176181;
            }


            /* ==================================================
               SECONDARY BUTTON
               ================================================== */

            QPushButton#SecondaryButton {

                background-color:
                    rgba(255,255,255,22);

                color:
                    #EAF5F9;

                border:
                    1px solid
                    rgba(255,255,255,48);

                border-radius:
                    10px;

                padding:
                    9px 16px;
            }

            QPushButton#SecondaryButton:hover {

                background-color:
                    rgba(255,255,255,38);

                border:
                    1px solid
                    rgba(255,255,255,70);
            }

            QPushButton#SecondaryButton:pressed {

                background-color:
                    rgba(255,255,255,50);
            }


            /* ==================================================
               MUTED TEXT
               ================================================== */

            QLabel#MutedText {

                color:
                    rgba(215,235,245,145);

                font-size:
                    9px;
            }


            /* ==================================================
               STATUS
               ================================================== */

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

            /* ==================================================
   GLASS PROGRESS
   ================================================== */

QProgressBar#GlassProgress {

    background-color:
        rgba(2, 14, 24, 90);

    border:
        1px solid
        rgba(220, 240, 248, 45);

    border-radius:
        6px;

    min-height:
        10px;

    max-height:
        10px;
}

QProgressBar#GlassProgress::chunk {

    background-color:
        #3BCFC1;

    border-radius:
        5px;

    margin:
        1px;
}


            /* ==================================================
               CANCEL
               ================================================== */

            QPushButton#CancelButton {

                background-color:
                    rgba(255,255,255,15);

                color:
                    #FFAAAA;

                border:
                    1px solid
                    rgba(255,255,255,30);

                border-radius:
                    10px;

                padding:
                    10px 18px;
            }

            QPushButton#CancelButton:hover {

                background-color:
                    rgba(255,100,100,25);

                border:
                    1px solid
                    rgba(255,150,150,55);
            }


            /* ==================================================
               PRIMARY BUTTON
               ================================================== */

            QPushButton#PrimaryButton {

                background-color:
                    rgba(23,97,129,225);

                color:
                    white;

                border:
                    1px solid
                    rgba(140,230,235,95);

                border-radius:
                    10px;

                padding:
                    10px 21px;

                font-weight:
                    700;
            }

            QPushButton#PrimaryButton:hover {

                background-color:
                    rgba(34,126,163,245);

                border:
                    1px solid
                    rgba(160,240,240,150);
            }

            QPushButton#PrimaryButton:pressed {

                background-color:
                    rgba(20,80,105,245);
            }

        """)

        # ----------------------------------------------------
        # MICA
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
        # REFRESH BLUR AFTER LAYOUT
        # ----------------------------------------------------

        QTimer.singleShot(
            150,
            card.update_blur
        )

        QTimer.singleShot(
            500,
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