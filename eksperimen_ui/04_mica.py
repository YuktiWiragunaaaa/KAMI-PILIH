import sys
import os
import ctypes

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
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

        return result == 0

    except Exception as error:
        print("Mica error:", error)
        return False


# ============================================================
# BACKGROUND
# ============================================================

class Background(QWidget):

    def __init__(self):
        super().__init__()

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )

    def paintEvent(self, event):

        painter = QPainter(self)

        rect = self.rect()

        # ----------------------------------------------------
        # Base background
        # ----------------------------------------------------

        gradient = QLinearGradient(
            0,
            0,
            rect.width(),
            rect.height(),
        )

        gradient.setColorAt(
            0.0,
            QColor("#071522"),
        )

        gradient.setColorAt(
            0.45,
            QColor("#0B2233"),
        )

        gradient.setColorAt(
            1.0,
            QColor("#050B12"),
        )

        painter.fillRect(
            rect,
            gradient,
        )

        # ----------------------------------------------------
        # CYAN GLOW
        # ----------------------------------------------------

        painter.setPen(Qt.PenStyle.NoPen)

        for radius, alpha in [
            (260, 18),
            (210, 22),
            (160, 28),
            (110, 35),
        ]:

            color = QColor(
                50,
                210,
                220,
                alpha,
            )

            painter.setBrush(color)

            painter.drawEllipse(
                20 - radius // 2,
                40 - radius // 2,
                radius,
                radius,
            )

        # ----------------------------------------------------
        # ORANGE GLOW
        # ----------------------------------------------------

        for radius, alpha in [
            (240, 12),
            (190, 18),
            (140, 23),
            (90, 30),
        ]:

            color = QColor(
                230,
                140,
                70,
                alpha,
            )

            painter.setBrush(color)

            painter.drawEllipse(
                rect.width() - radius // 2,
                rect.height() - radius // 2,
                radius,
                radius,
            )

        # ----------------------------------------------------
        # DECORATIVE CODE
        # ----------------------------------------------------

        painter.setPen(
            QColor(
                80,
                160,
                190,
                35,
            )
        )

        code_lines = [
            "vision_score = composition + focus + moment",
            "model.generate_content(images)",
            "classification = Excellent / Good / Bad",
            "for batch in photo_batches:",
            "    analyze(frame)",
            "    write_xmp(metadata)",
            "RAW -> JPEG -> AI -> XMP -> EDITOR",
        ]

        y = 70

        for line in code_lines:

            painter.drawText(
                20,
                y,
                line,
            )

            y += 22


# ============================================================
# GLASS CARD
# ============================================================

class GlassCard(QFrame):

    def __init__(self):

        super().__init__()

        self.setObjectName("GlassCard")

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            30,
            28,
            30,
            30,
        )

        layout.setSpacing(8)

        title = QLabel("Sortir AI")

        title.setObjectName(
            "CardTitle"
        )

        description = QLabel(
            "Frosted glass panel test."
        )

        description.setObjectName(
            "CardDescription"
        )

        layout.addWidget(title)

        layout.addWidget(description)

        layout.addStretch()


# ============================================================
# MAIN WINDOW
# ============================================================

class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "Sortir AI | True Glass Test"
        )

        self.resize(
            900,
            750,
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
            65,
            80,
            65,
        )

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        eyebrow = QLabel(
            "AI PHOTO CURATION"
        )

        eyebrow.setObjectName(
            "Eyebrow"
        )

        title = QLabel(
            "Sortir AI"
        )

        title.setObjectName(
            "MainTitle"
        )

        subtitle = QLabel(
            "Glassmorphism experiment"
        )

        subtitle.setObjectName(
            "Subtitle"
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

        card = GlassCard()

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
                background: transparent;
            }

            QLabel#Eyebrow {
                color: #78E8D6;
                font-size: 9px;
                font-weight: 700;
            }

            QLabel#MainTitle {
                color: #F4FAFD;
                font-size: 34px;
                font-weight: 700;
            }

            QLabel#Subtitle {
                color: rgba(220,235,245,180);
                font-size: 11px;
            }

            QFrame#GlassCard {

                background-color:
                    rgba(22, 45, 61, 170);

                border:
                    1px solid
                    rgba(220, 240, 250, 65);

                border-radius:
                    24px;
            }

            QLabel#CardTitle {

                color:
                    #F4FAFD;

                font-size:
                    28px;

                font-weight:
                    700;
            }

            QLabel#CardDescription {

                color:
                    rgba(220,235,245,180);

                font-size:
                    11px;
            }

        """)

        # ----------------------------------------------------
        # Enable Mica
        # ----------------------------------------------------

        self.show()

        hwnd = int(
            self.winId()
        )

        aktifkan_mica(
            hwnd
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