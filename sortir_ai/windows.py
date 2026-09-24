"""Integrasi Windows: penyimpanan API key (DPAPI + registry) dan deteksi/pembukaan editor foto."""

import base64
import ctypes
import glob
import json
import os
import shutil
import subprocess
import time
import winreg
from ctypes import wintypes

FILE_LOGIN = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "SortirAI", "login.dat")
REGISTRY_LOGIN_PATH = r"Software\SortirAI"

# (nama tampilan, nama executable, folder produk di Program Files)
# "Lightroom Classic" dan "Adobe Lightroom" sengaja dijadikan satu entri
# karena keduanya menunjuk Lightroom.exe yang sama.
KONFIGURASI_EDITOR = (
    ("Capture One", ("Capture One.exe", "CaptureOne.exe"), ("Capture One",)),
    ("Adobe Lightroom", ("Lightroom.exe",), ("Adobe", "Lightroom")),
    ("Photoshop", ("Photoshop.exe",), ("Adobe", "Adobe Photoshop")),
    ("Affinity Photo", ("AffinityPhoto.exe",), ("Affinity Photo",)),
    ("Luminar Neo", ("Luminar Neo.exe", "LuminarNeo.exe"), ("Skylum", "Luminar")),
    ("ON1 Photo RAW", ("ON1 Photo RAW.exe", "ON1 Photo RAW 2024.exe"), ("ON1",)),
)


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def enkripsi_login(teks):
    data = teks.encode("utf-8")
    buffer = ctypes.create_string_buffer(data)
    blob_masuk = DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    blob_keluar = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_masuk), None, None, None, None, 0, ctypes.byref(blob_keluar)
    ):
        raise OSError("Windows gagal mengenkripsi API key.")
    try:
        hasil = ctypes.string_at(blob_keluar.pbData, blob_keluar.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_keluar.pbData)
    return base64.b64encode(hasil).decode("ascii")


def dekripsi_login(teks):
    data = base64.b64decode(teks)
    buffer = ctypes.create_string_buffer(data)
    blob_masuk = DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    blob_keluar = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_masuk), None, None, None, None, 0, ctypes.byref(blob_keluar)
    ):
        raise OSError("Windows gagal membaca API key tersimpan.")
    try:
        return ctypes.string_at(blob_keluar.pbData, blob_keluar.cbData).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(blob_keluar.pbData)


def baca_login():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_LOGIN_PATH) as key:
            terenkripsi, _ = winreg.QueryValueEx(key, "Login")
        data = json.loads(dekripsi_login(terenkripsi))
        return data if data.get("api_key") else None
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    try:
        with open(FILE_LOGIN, "r", encoding="ascii") as file:
            data = json.loads(dekripsi_login(file.read()))
        if data.get("api_key"):
            simpan_login(data)
            return data
        return None
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def simpan_login(data):
    terenkripsi = enkripsi_login(json.dumps(data))
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, REGISTRY_LOGIN_PATH) as key:
        winreg.SetValueEx(key, "Login", 0, winreg.REG_SZ, terenkripsi)
    try:
        os.remove(FILE_LOGIN)
    except FileNotFoundError:
        pass


def hapus_login():
    terhapus = False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_LOGIN_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, "Login")
            terhapus = True
    except (FileNotFoundError, OSError):
        pass
    try:
        os.remove(FILE_LOGIN)
        terhapus = True
    except FileNotFoundError:
        pass
    return terhapus


def _cari_di_folder_produk(dasar, folder_produk, nama_executable):
    """Cari executable maksimal 3 tingkat ke bawah — cukup untuk semua editor
    yang didukung dan jauh lebih cepat dari glob rekursif tanpa batas."""
    for folder in folder_produk:
        for folder_cocok in {folder, folder.replace(" ", "")}:
            akar = os.path.join(dasar, folder_cocok)
            if not os.path.isdir(akar):
                continue
            for executable in nama_executable:
                for pola in ("", "*", os.path.join("*", "*")):
                    for path in glob.glob(os.path.join(akar, pola, executable)):
                        if os.path.isfile(path):
                            return path
    return None


def cari_executable_editor(nama_editor):
    konfigurasi = next((item for item in KONFIGURASI_EDITOR if item[0] == nama_editor), None)
    if not konfigurasi:
        return None
    _, nama_executable, folder_produk = konfigurasi

    if nama_editor == "Capture One":
        for path in (
            r"C:\Program Files\Capture One\Capture One\CaptureOne.exe",
            r"C:\Program Files (x86)\Capture One\Capture One\CaptureOne.exe",
        ):
            if os.path.isfile(path):
                return path

    for executable in nama_executable:
        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for registry_path in (
                fr"Software\Microsoft\Windows\CurrentVersion\App Paths\{executable}",
                fr"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\{executable}",
            ):
                try:
                    with winreg.OpenKey(root, registry_path) as key:
                        lokasi = winreg.QueryValue(key, None).strip('"')
                    if lokasi and os.path.isfile(lokasi):
                        return lokasi
                except (FileNotFoundError, OSError):
                    continue
        lokasi = shutil.which(executable)
        if lokasi:
            return lokasi

    for dasar in (
        os.getenv("ProgramFiles"),
        os.getenv("ProgramW6432"),
        os.getenv("ProgramFiles(x86)"),
        os.getenv("LOCALAPPDATA"),
    ):
        if dasar:
            path = _cari_di_folder_produk(dasar, folder_produk, nama_executable)
            if path:
                return path

    if nama_editor == "Capture One":
        for root in (
            os.path.join(os.getenv("ProgramData", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
            os.path.join(os.getenv("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
        ):
            for path in glob.glob(os.path.join(root, "Capture One", "**", "Capture One.lnk"), recursive=True):
                if os.path.isfile(path):
                    return path
    return None


def deteksi_editor():
    """{nama_editor: path_executable} untuk editor yang terpasang. Bisa memakan
    waktu beberapa detik — jalankan di thread background."""
    hasil = {}
    for nama_editor, _, _ in KONFIGURASI_EDITOR:
        executable = cari_executable_editor(nama_editor)
        if executable:
            hasil[nama_editor] = executable
    return hasil


_FLAGS_DETACHED = (
    subprocess.DETACHED_PROCESS
    | subprocess.CREATE_NEW_PROCESS_GROUP
    | subprocess.CREATE_BREAKAWAY_FROM_JOB
)


def _jalankan_terpisah(argumen, cwd=None):
    subprocess.Popen(
        argumen,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        close_fds=True, cwd=cwd, creationflags=_FLAGS_DETACHED,
    )


def aktifkan_jendela_capture_one(aktifkan=True):
    user32 = ctypes.windll.user32
    nama_jendela = ctypes.create_unicode_buffer(256)
    jendela_ditemukan = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def periksa_jendela(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        user32.GetWindowTextW(hwnd, nama_jendela, len(nama_jendela))
        kotak = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(kotak))
        if (
            "Capture One" in nama_jendela.value
            and user32.IsWindowEnabled(hwnd)
            and kotak.right - kotak.left >= 500
            and kotak.bottom - kotak.top >= 300
        ):
            jendela_ditemukan.append(hwnd)
        return True

    user32.EnumWindows(periksa_jendela, 0)
    if not jendela_ditemukan:
        return None
    hwnd = jendela_ditemukan[-1]
    if aktifkan:
        thread_target = user32.GetWindowThreadProcessId(hwnd, None)
        thread_depan = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
        thread_saat_ini = ctypes.windll.kernel32.GetCurrentThreadId()
        user32.AllowSetForegroundWindow(-1)
        user32.AttachThreadInput(thread_saat_ini, thread_depan, True)
        user32.AttachThreadInput(thread_saat_ini, thread_target, True)
        user32.ShowWindow(hwnd, 9)
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
        user32.SetFocus(hwnd)
        user32.AttachThreadInput(thread_saat_ini, thread_target, False)
        user32.AttachThreadInput(thread_saat_ini, thread_depan, False)
    return hwnd


def kirim_shortcut_import_capture_one():
    """Ctrl+Shift+I — panel import Capture One."""
    user32 = ctypes.windll.user32
    for kunci in (0x11, 0x10, 0x49):
        user32.keybd_event(kunci, 0, 0, 0)
    for kunci in (0x49, 0x10, 0x11):
        user32.keybd_event(kunci, 0, 2, 0)


def buka_editor(nama_editor, folder, executable=None):
    """Buka editor terpilih. Fungsi ini memblokir sampai ~15 detik untuk
    Capture One — panggil dari thread background, bukan thread UI.
    Mengembalikan pesan status."""
    if not executable or not os.path.isfile(executable):
        executable = cari_executable_editor(nama_editor)
    if not executable or not os.path.isfile(executable):
        raise FileNotFoundError(f"Executable {nama_editor} tidak ditemukan.")

    if nama_editor == "Capture One":
        try:
            _jalankan_terpisah([executable], cwd=os.path.dirname(executable))
        except OSError:
            os.startfile(executable)
        # Tunggu jendela muncul (cold start bisa lebih dari 2 detik), maksimal 15 detik.
        hwnd = None
        for _ in range(30):
            time.sleep(0.5)
            hwnd = aktifkan_jendela_capture_one(aktifkan=True)
            if hwnd:
                break
        time.sleep(0.4)
        # Kirim Ctrl+Shift+I hanya bila Capture One benar-benar di depan,
        # supaya tombol tidak nyasar ke aplikasi lain.
        if hwnd and ctypes.windll.user32.GetForegroundWindow() == hwnd:
            try:
                kirim_shortcut_import_capture_one()
            except Exception as error:
                print(f"Gagal mengirim shortcut import Capture One: {error}")
        return "Capture One dibuka. Jalankan import dari panel yang muncul (Ctrl+Shift+I)."

    _jalankan_terpisah([executable, folder])
    return f"{nama_editor} dibuka dengan folder foto terpilih."
