import sys
import os
import ctypes

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QComboBox,
)


# ============================================================
# WINDOWS MICA
# ============================================================

def aktifkan_mica(hwnd):
    """
    Mengaktifkan Mica Windows 11 melalui DWM.
    Jika tidak tersedia, aplikasi tetap berjalan.
    """

    if os.name != "nt":
        print("Bukan Windows. Mica dilewati.")
        return False

    try:
        # DWMWA_SYSTEMBACKDROP_TYPE
        DWMWA_SYSTEMBACKDROP_TYPE = 38

        # DWMSBT_MAINWINDOW = 2
        # Pada Windows 11 = Mica
        DWMSBT_MAINWINDOW = 2

        backdrop = ctypes.c_int(DWMSBT_MAINWINDOW)

        hasil = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd),
            DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(backdrop),
            ctypes.sizeof(backdrop),
        )

        print("DwmSetWindowAttribute result =", hasil)

        if hasil == 0:
            print("Mica berhasil diaktifkan.")
            return True

        print("Mica gagal diaktifkan.")
        return False

    except Exception as error:
        print("Mica tidak tersedia:", error)
        return False


# ============================================================
# GLASS CARD
# ============================================================

class GlassCard(QFrame):

    def __init__(self):
        super().__init__()

        self.setObjectName("GlassCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 30)
        layout.setSpacing(8)

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        eyebrow = QLabel("CONFIGURATION")
        eyebrow.setObjectName("Eyebrow")

        title = QLabel("Sortir AI")
        title.setObjectName("CardTitle")

        subtitle = QLabel(
            "Pilih foto terbaik lalu buka hasilnya "
            "di editor pilihan."
        )
        subtitle.setObjectName("CardSubtitle")

        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        layout.addSpacing(18)

        # ----------------------------------------------------
        # API
        # ----------------------------------------------------

        api_label = QLabel("API KEY GEMINI")
        api_label.setObjectName("FieldLabel")

        api_input = QLineEdit()
        api_input.setPlaceholderText("Masukkan API key...")
        api_input.setEchoMode(QLineEdit.Password)
        api_input.setObjectName("GlassInput")

        layout.addWidget(api_label)
        layout.addWidget(api_input)

        # ----------------------------------------------------
        # Model
        # ----------------------------------------------------

        model_label = QLabel("MODEL GEMINI")
        model_label.setObjectName("FieldLabel")

        model = QComboBox()
        model.addItems([
            "gemini-3.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
        ])
        model.setObjectName("GlassCombo")

        layout.addWidget(model_label)
        layout.addWidget(model)

        # ----------------------------------------------------
        # Folder
        # ----------------------------------------------------

        folder_label = QLabel("FOLDER FOTO")
        folder_label.setObjectName("FieldLabel")

        folder_row = QHBoxLayout()
        folder_row.setSpacing(10)

        folder_button = QPushButton("Pilih folder")
        folder_button.setObjectName("SecondaryButton")

        folder_text = QLabel("Belum ada folder dipilih")
        folder_text.setObjectName("MutedText")

        folder_row.addWidget(folder_button)
        folder_row.addWidget(folder_text)
        folder_row.addStretch()

        layout.addWidget(folder_label)
        layout.addLayout(folder_row)

        layout.addSpacing(15)

        # ----------------------------------------------------
        # Separator
        # ----------------------------------------------------

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setObjectName("Separator")

        layout.addWidget(separator)

        layout.addSpacing(8)

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        status_row = QHBoxLayout()

        status = QLabel("●  Siap memulai")
        status.setObjectName("Status")

        progress = QLabel("0%")
        progress.setObjectName("ProgressText")

        status_row.addWidget(status)
        status_row.addStretch()
        status_row.addWidget(progress)

        layout.addLayout(status_row)

        # ----------------------------------------------------
        # Buttons
        # ----------------------------------------------------

        buttons = QHBoxLayout()
        buttons.setSpacing(10)

        cancel = QPushButton("Batalkan")
        cancel.setObjectName("CancelButton")

        start = QPushButton("✦  Mulai sortir")
        start.setObjectName("PrimaryButton")

        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(start)

        layout.addLayout(buttons)


# ============================================================
# MAIN WINDOW
# ============================================================

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Sortir AI | Glass Test")
        self.resize(900, 800)

        # ----------------------------------------------------
        # Central widget
        # ----------------------------------------------------

        central = QWidget()
        central.setObjectName("Background")

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(70, 55, 70, 55)
        main_layout.setSpacing(0)

        # ----------------------------------------------------
        # App header
        # ----------------------------------------------------

        header = QLabel("SORTIR AI")
        header.setObjectName("Header")

        description = QLabel(
            "AI PHOTO CURATION"
        )
        description.setObjectName("HeaderSecondary")

        main_layout.addWidget(header)
        main_layout.addWidget(description)

        main_layout.addSpacing(25)

        # ----------------------------------------------------
        # Glass card
        # ----------------------------------------------------

        card = GlassCard()

        main_layout.addWidget(card)
        main_layout.addStretch()

        self.setCentralWidget(central)

        # ----------------------------------------------------
        # Global stylesheet
        # ----------------------------------------------------

        self.setStyleSheet("""

            /* =================================================
               WINDOW
               ================================================= */

            QMainWindow {
                background: transparent;
            }

            QWidget#Background {
                background-color: rgba(5, 14, 23, 35);
            }


            /* =================================================
               HEADER
               ================================================= */

            QLabel#Header {
                color: #F4FAFD;
                font-size: 30px;
                font-weight: 700;
            }

            QLabel#HeaderSecondary {
                color: #78E8D6;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1px;
            }


            /* =================================================
               GLASS CARD
               ================================================= */

            QFrame#GlassCard {

                background-color: rgba(16, 38, 54, 185);

                border:
                    1px solid rgba(220, 240, 248, 45);

                border-radius: 24px;

            }


            /* =================================================
               CARD HEADER
               ================================================= */

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
                color: rgba(220, 238, 246, 180);
                font-size: 10px;
            }


            /* =================================================
               LABEL
               ================================================= */

            QLabel#FieldLabel {
                color: #DCEBF3;
                font-size: 9px;
                font-weight: 600;
                margin-top: 6px;
            }


            /* =================================================
               INPUT
               ================================================= */

            QLineEdit#GlassInput {

                background-color:
                    rgba(3, 17, 28, 155);

                color: #F4FAFD;

                border:
                    1px solid rgba(180, 220, 235, 35);

                border-radius: 10px;

                padding:
                    10px 12px;

                selection-background-color:
                    #176181;
            }

            QLineEdit#GlassInput:focus {

                border:
                    1px solid #78E8D6;
            }


            /* =================================================
               COMBOBOX
               ================================================= */

            QComboBox#GlassCombo {

                background-color:
                    rgba(3, 17, 28, 155);

                color: #F4FAFD;

                border:
                    1px solid rgba(180, 220, 235, 35);

                border-radius: 10px;

                padding:
                    8px 10px;
            }

            QComboBox#GlassCombo:hover {

                border:
                    1px solid rgba(120, 232, 214, 100);
            }


            /* =================================================
               SECONDARY BUTTON
               ================================================= */

            QPushButton#SecondaryButton {

                background-color:
                    rgba(255, 255, 255, 22);

                color: #E9F5F9;

                border:
                    1px solid rgba(220, 240, 248, 45);

                border-radius: 9px;

                padding:
                    9px 16px;
            }

            QPushButton#SecondaryButton:hover {

                background-color:
                    rgba(255, 255, 255, 38);
            }


            /* =================================================
               TEXT
               ================================================= */

            QLabel#MutedText {

                color:
                    rgba(210, 230, 240, 145);

                font-size:
                    9px;
            }


            /* =================================================
               SEPARATOR
               ================================================= */

            QFrame#Separator {

                color:
                    rgba(180, 220, 235, 30);

                background:
                    rgba(180, 220, 235, 30);

                max-height:
                    1px;
            }


            /* =================================================
               STATUS
               ================================================= */

            QLabel#Status {

                color: #78E8D6;

                font-size:
                    9px;

                font-weight:
                    600;
            }

            QLabel#ProgressText {

                color:
                    #78E8D6;

                font-size:
                    9px;

                font-weight:
                    700;
            }


            /* =================================================
               CANCEL
               ================================================= */

            QPushButton#CancelButton {

                background-color:
                    rgba(255, 255, 255, 18);

                color:
                    #FF9999;

                border:
                    1px solid rgba(255, 255, 255, 30);

                border-radius:
                    10px;

                padding:
                    10px 18px;
            }

            QPushButton#CancelButton:hover {

                background-color:
                    rgba(255, 100, 100, 25);
            }


            /* =================================================
               PRIMARY
               ================================================= */

            QPushButton#PrimaryButton {

                background-color:
                    rgba(23, 97, 129, 225);

                color:
                    white;

                border:
                    1px solid rgba(140, 230, 235, 80);

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
        # Enable Mica
        # ----------------------------------------------------

        self.show()

        hwnd = int(self.winId())

        print("HWND =", hwnd)

        aktifkan_mica(hwnd)


# ============================================================
# MAIN
# ============================================================

def main():

    app = QApplication(sys.argv)

    window = MainWindow()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()