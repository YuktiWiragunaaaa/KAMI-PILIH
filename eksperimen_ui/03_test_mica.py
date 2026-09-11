import sys
import os
import ctypes

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
)


def set_mica(hwnd):
    """
    Windows 11 Mica.
    DWMWA_SYSTEMBACKDROP_TYPE = 38
    DWMSBT_MAINWINDOW = 2
    """

    if os.name != "nt":
        print("Bukan Windows.")
        return

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
            print("Mica berhasil diterapkan.")
        else:
            print("Mica gagal diterapkan.")

    except Exception as e:
        print("ERROR:", e)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Sortir AI — Mica Test")
        self.resize(800, 600)

        central = QWidget()

        # Penting:
        # jangan beri background solid pada central widget.
        central.setAttribute(
            Qt.WA_TranslucentBackground,
            True
        )

        layout = QVBoxLayout(central)
        layout.setContentsMargins(50, 50, 50, 50)

        title = QLabel("SORTIR AI")

        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 34px;
                font-weight: bold;
            }
        """)

        info = QLabel(
            "TES MICA WINDOWS 11\n\n"
            "Pindahkan window ini ke atas wallpaper desktop "
            "atau buka aplikasi lain di belakangnya."
        )

        info.setStyleSheet("""
            QLabel {
                color: rgba(255,255,255,210);
                font-size: 14px;
            }
        """)

        button = QPushButton("TEST BUTTON")

        button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,25);
                color: white;

                border: 1px solid rgba(255,255,255,55);
                border-radius: 10px;

                padding: 12px 20px;
            }

            QPushButton:hover {
                background-color: rgba(255,255,255,45);
            }
        """)

        layout.addWidget(title)
        layout.addWidget(info)
        layout.addSpacing(20)
        layout.addWidget(button)
        layout.addStretch()

        self.setCentralWidget(central)

        self.show()

        # Ambil HWND setelah window benar-benar muncul.
        hwnd = int(self.winId())

        print("HWND =", hwnd)

        set_mica(hwnd)


def main():

    app = QApplication(sys.argv)

    window = MainWindow()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()