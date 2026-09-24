"""Logika inti Sortir AI, bebas dari framework UI.

Semua komunikasi ke antarmuka lewat objek `Laporan` (callback sederhana),
sehingga backend ini bisa dipakai oleh Tkinter, PySide6, Flet, atau CLI.
"""

import base64
import ctypes
import glob
import hashlib
import io
import json
import os
import shutil
import subprocess
import threading
import time
import winreg
from ctypes import wintypes
from dataclasses import dataclass, field
from typing import Callable, Optional

import google.generativeai as genai
import rawpy
from PIL import Image


# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------
UKURAN_MAKS_AI = 1280
KUALITAS_JPEG_AI = 78
UKURAN_BATCH = 30
MODEL_GEMINI_DEFAULT = "gemini-3.6-flash"
MODEL_GEMINI_OPTIONS = (
    "gemini-3.6-flash",
    "gemini-3.6-flash-lite",
)
FILE_LOGIN = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "SortirAI", "login.dat")
REGISTRY_LOGIN_PATH = r"Software\SortirAI"
EKSTENSI_JPEG = (".jpg", ".jpeg")
EKSTENSI_RAW = (".arw", ".cr2", ".cr3", ".nef", ".raf", ".orf", ".rw2", ".dng")


def ukuran_batch_untuk_model(nama_model):
    """Pilih batch yang lebih aman berdasarkan kecepatan model vision."""
    nama_model = nama_model.lower()
    if "pro" in nama_model:
        return 6
    if "lite" in nama_model:
        return 12
    return 10

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


# ---------------------------------------------------------------------------
# Callback ke UI
# ---------------------------------------------------------------------------
def _abaikan(*_args, **_kwargs):
    pass


@dataclass
class Laporan:
    """Kumpulan callback. UI cukup mengisi yang dibutuhkan; semuanya dipanggil
    dari thread worker, jadi UI wajib memindahkannya ke thread utama sendiri."""

    status: Callable[[str], None] = _abaikan
    progress: Callable[[float], None] = _abaikan
    data: Callable[[str], None] = _abaikan
    peringatan: Callable[[str, str], None] = _abaikan  # (judul, pesan)
    selesai: Callable[[str, bool], None] = _abaikan     # (pesan, sukses)


# ---------------------------------------------------------------------------
# Penyimpanan API key (DPAPI Windows)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Daftar model Gemini
# ---------------------------------------------------------------------------
def daftar_model_vision(api_key):
    """Model Gemini yang mendukung generateContent dengan input gambar."""
    genai.configure(api_key=api_key)
    hasil = []
    for model in genai.list_models():
        metode = getattr(model, "supported_generation_methods", [])
        nama = getattr(model, "name", "").replace("models/", "")
        if "generateContent" not in metode or not nama.startswith("gemini-"):
            continue
        # Model embedding / TTS / audio tidak menerima gambar.
        if any(kata in nama for kata in ("embedding", "tts", "audio", "live", "native")):
            continue
        hasil.append(nama)
    # Daftar berasal dari API agar mengikuti model yang tersedia untuk akun.
    return sorted(hasil, key=lambda nama: (
        "pro" in nama,
        "flash" not in nama,
        nama,
    ))


# ---------------------------------------------------------------------------
# Util
# ---------------------------------------------------------------------------
def format_ukuran(byte_count):
    if byte_count < 1000:
        return f"{int(byte_count)} B"
    if byte_count < 1000 ** 2:
        return f"{byte_count / 1000:.2f} KB"
    if byte_count < 1000 ** 3:
        return f"{byte_count / (1000 ** 2):.2f} MB"
    return f"{byte_count / (1000 ** 3):.2f} GB"


def daftar_foto(folder):
    """Kumpulkan JPEG dan RAW; RAW yang punya pasangan JPEG dengan basename sama
    tidak dihitung dua kali. Pencocokan ekstensi tidak peka huruf besar/kecil."""
    semua = os.listdir(folder)
    jpeg = sorted(
        os.path.join(folder, nama)
        for nama in semua
        if os.path.splitext(nama)[1].lower() in EKSTENSI_JPEG
    )
    stem_jpeg = {os.path.splitext(os.path.basename(path))[0].lower() for path in jpeg}
    raw = sorted(
        os.path.join(folder, nama)
        for nama in semua
        if os.path.splitext(nama)[1].lower() in EKSTENSI_RAW
        and os.path.splitext(nama)[0].lower() not in stem_jpeg
    )
    return jpeg + raw


def kompresi_untuk_ai(path_foto):
    """Salinan JPEG kecil di memori; file asli tidak pernah diubah."""
    if os.path.splitext(path_foto)[1].lower() in EKSTENSI_RAW:
        with rawpy.imread(path_foto) as raw:
            data_rgb = raw.postprocess(use_camera_wb=True, output_bps=8, half_size=True)
        gambar_asli = Image.fromarray(data_rgb)
    else:
        gambar_asli = Image.open(path_foto)
    with gambar_asli:
        gambar = gambar_asli.convert("RGB")
        resampling = getattr(Image, "Resampling", Image)
        gambar.thumbnail((UKURAN_MAKS_AI, UKURAN_MAKS_AI), resampling.LANCZOS)
        buffer = io.BytesIO()
        gambar.save(buffer, format="JPEG", quality=KUALITAS_JPEG_AI, optimize=True, progressive=True)
    buffer.seek(0)
    return Image.open(buffer), buffer.getbuffer().nbytes


def checksum_file(path_foto):
    hash_file = hashlib.sha256()
    with open(path_foto, "rb") as file:
        for potongan in iter(lambda: file.read(1024 * 1024), b""):
            hash_file.update(potongan)
    return hash_file.hexdigest()


# ---------------------------------------------------------------------------
# Keputusan AI
# ---------------------------------------------------------------------------
def baca_json_model(teks):
    teks = teks.strip().replace("```json", "").replace("```", "").strip()
    awal = teks.find("{")
    akhir = teks.rfind("}")
    if awal < 0 or akhir < awal:
        raise ValueError("Respons Gemini tidak berisi objek JSON.")
    hasil = json.loads(teks[awal:akhir + 1])
    if not isinstance(hasil, dict):
        raise ValueError("Respons Gemini bukan objek JSON.")
    return hasil


def normalisasi_keputusan(nama_file_batch, keputusan, kuota_excellent, default_status="Bad"):
    """Validasi status dan batasi Excellent per batch sesuai kuota.

    Kalau Excellent melebihi kuota, kelebihannya diturunkan jadi Good.
    Kalau kurang, TIDAK dipaksa naik — konsisten dengan prompt yang melarang
    memaksakan foto. Pemenuhan target dilakukan lintas-batch di
    `penuhi_target_global` dengan mengambil kandidat Good terbaik.
    """
    status_valid = {"Excellent", "Good", "Bad"}
    keputusan_normal = {
        os.path.basename(str(nama)).lower(): str(status).strip().title().replace("Choice", "Good")
        for nama, status in keputusan.items()
    }
    hasil = {}
    for nama in nama_file_batch:
        status = keputusan_normal.get(nama.lower(), default_status)
        hasil[nama] = status if status in status_valid else default_status
    nama_excellent = [nama for nama in nama_file_batch if hasil[nama] == "Excellent"]
    for nama in nama_excellent[kuota_excellent:]:
        hasil[nama] = "Good"
    return hasil


def penuhi_target_global(keputusan_batch, target_excellent):
    """Pilih kandidat bergiliran antar-batch agar momen tidak didominasi satu urutan."""
    keputusan_semua = {
        nama: status
        for keputusan in keputusan_batch
        for nama, status in keputusan.items()
    }
    kandidat = []
    panjang_maksimum = max([len(keputusan) for keputusan in keputusan_batch] or [0])
    for status_kandidat in ("Excellent", "Good"):
        for urutan in range(panjang_maksimum):
            for keputusan in keputusan_batch:
                nama_status = [nama for nama, status in keputusan.items() if status == status_kandidat]
                if urutan < len(nama_status):
                    kandidat.append(nama_status[urutan])

    pilihan = set(kandidat[:target_excellent])
    for nama, status in keputusan_semua.items():
        if status in {"Excellent", "Good"}:
            keputusan_semua[nama] = "Excellent" if nama in pilihan else "Good"
    return keputusan_semua


# ---------------------------------------------------------------------------
# XMP sidecar
# ---------------------------------------------------------------------------
def buat_file_xmp(path_foto, status):
    metadata = {"Excellent": ("Green", "3"), "Good": ("", "1"), "Bad": ("", "0")}
    label, rating = metadata[status]
    xmp_path = f"{os.path.splitext(path_foto)[0]}.xmp"
    xmp_content = f"""<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
        <rdf:Description rdf:about=""
            xmlns:xmp="http://ns.adobe.com/xap/1.0/"
            xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/">
            <xmp:Rating>{rating}</xmp:Rating>
            <xmp:Label>{label}</xmp:Label>
        </rdf:Description>
    </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>"""
    xmp_temp_path = f"{xmp_path}.tmp"
    with open(xmp_temp_path, "w", encoding="utf-8") as f:
        f.write(xmp_content)
    os.replace(xmp_temp_path, xmp_path)


def status_dari_xmp(path_foto):
    xmp_path = f"{os.path.splitext(path_foto)[0]}.xmp"
    try:
        with open(xmp_path, "r", encoding="utf-8") as file:
            isi = file.read()
    except OSError:
        return "Good"
    if "<xmp:Label>Green</xmp:Label>" in isi or "<xmp:Rating>3</xmp:Rating>" in isi:
        return "Excellent"
    if "<xmp:Rating>0</xmp:Rating>" in isi:
        return "Bad"
    return "Good"


# ---------------------------------------------------------------------------
# Proses sortir
# ---------------------------------------------------------------------------
PROMPT_TEMPLATE = """
Anda adalah fotografer senior sekaligus kurator foto profesional. Analisis setiap foto secara
ketat, objektif, dan konsisten. Nilai foto berdasarkan kualitas visual yang benar-benar terlihat,
bukan berdasarkan asumsi tentang jenis acaranya. Standar ini berlaku untuk foto event, wedding,
olahraga, dokumentasi, portrait, produk, maupun foto studio. Pastikan foto memiliki nilai story yang kuat secara objektif, 
wajah subjek jelas, dan momen yang paling menarik. Jangan menilai berdasarkan preferensi pribadi,
tren, atau gaya artistik. Jangan menilai berdasarkan metadata, nama file, atau urutan pengambilan. Jangan menilai berdasarkan kualitas teknis yang tidak terlihat, seperti resolusi asli, ISO, atau lensa yang digunakan. 

Klasifikasi:
* Excellent: hero shot yang layak untuk cetakan besar 16R, halaman utama, atau cover album.
    Foto memiliki komposisi kuat (rule of thirds, leading lines, framing, layering, atau
    keseimbangan visual), pencahayaan berdimensi, detail dan fokus yang baik pada subjek utama,
    serta momen, gestur, ekspresi, atau bentuk yang paling bermakna. Untuk manusia, mata harus
    terbuka dan fokus utama setajam kondisi foto memungkinkan. Foto harus cukup terang dan tidak
    rusak oleh highlight atau shadow ekstrem agar masih fleksibel untuk retouching. Pilih TEPAT
    {kuota_batch} foto Excellent bila foto layak tersedia; jika kandidat lebih sedikit, pilih semua
    kandidat terbaik yang benar-benar memenuhi standar tanpa memaksakan foto buruk. Utamakan narasi
    yang beragam: kombinasi wide, medium, dan detail; variasi sudut, subjek, momen, dan komposisi.
    Dari rangkaian yang sangat mirip, pilih hanya frame terkuat.
* Good: foto teknis yang solid dan berguna sebagai pelengkap album atau dokumentasi. Foto masih
    tajam secukupnya, terekspos dengan wajar, memiliki subjek yang jelas, dan tidak gagal secara
    komposisi, tetapi tidak sekuat Excellent dalam momen, emosi, keunikan, atau estetika. Bila ada
    frame yang jelas lebih baik, tandai frame yang lemah sebagai Bad.
* Bad: out of focus atau motion blur yang merusak subjek, mata tertutup saat mata penting,
    ekspresi canggung atau missed moment, subjek terpotong pada persendian secara mengganggu,
    komposisi berantakan, wajah atau subjek utama tertutup, highlight/shadow fatal, noise atau
    artefak berat, foto duplikat, atau frame yang jelas lebih buruk dari frame serupa.

Jangan menghukum gaya artistik yang disengaja seperti backlight, low-key, high-key, siluet,
grain, atau shallow depth of field selama hasilnya terlihat terkontrol dan subjek/tujuannya jelas.
Untuk foto studio atau produk, prioritaskan bentuk, detail, kebersihan latar, pencahayaan, dan
ketepatan fokus; untuk event, prioritaskan momen, emosi, interaksi, dan variasi cerita.
Foto yang tidak dikirim karena duplicate file sudah diberi Bad oleh aplikasi.

Prosedur penilaian wajib:
1. Periksa setiap foto satu per satu sebelum membandingkan foto yang mirip.
2. Untuk setiap foto, nilai secara internal lima aspek dari 0 sampai 20: fokus/subjek,
    exposure, komposisi, momen/ekspresi, dan nilai cerita/keunikan.
3. Jangan memberi Excellent hanya karena foto terlihat menarik. Excellent harus kuat pada
    sebagian besar aspek dan tidak memiliki cacat besar pada fokus, mata, exposure, atau momen.
4. Jika ragu antara dua label, pilih label yang lebih rendah. Jangan memaksakan target
    Excellent; kuota adalah batas maksimum, bukan alasan untuk menaikkan foto yang lemah.
5. Jika beberapa foto hampir sama, pilih frame dengan fokus, ekspresi, gestur, dan komposisi
    terbaik. Tetap pertahankan variasi subjek dan momen.
6. Setelah penilaian selesai, keluarkan hanya satu label untuk setiap nama file yang dikirim.

Output WAJIB berupa JSON murni tanpa Markdown, komentar, atau teks tambahan. Gunakan key hanya
nama file berikut dan nilai hanya salah satu dari "Excellent", "Good", atau "Bad":
{daftar_nama}
"""


class PenyortirFoto:
    """Menjalankan sortir di thread terpisah dan melapor lewat `Laporan`."""

    def __init__(self, laporan: Laporan):
        self.laporan = laporan
        self.cancel_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def sedang_berjalan(self):
        return self._thread is not None and self._thread.is_alive()

    def mulai(self, folder, api_key, target_excellent, nama_model):
        if self.sedang_berjalan:
            raise RuntimeError("Proses sortir masih berjalan.")
        self.cancel_event.clear()
        self._thread = threading.Thread(
            target=self._jalankan, args=(folder, api_key, target_excellent, nama_model), daemon=True
        )
        self._thread.start()

    def batalkan(self):
        self.cancel_event.set()

    def _jalankan(self, folder, api_key, target_excellent, nama_model):
        try:
            self._proses(folder, api_key, target_excellent, nama_model)
        except Exception as error:
            self.laporan.selesai(f"Proses gagal: {type(error).__name__}: {error}", False)

    def _proses(self, folder, api_key, target_excellent, nama_model):
        lapor = self.laporan
        lapor.status("Menghubungkan ke Gemini...")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(nama_model)

        semua_foto = daftar_foto(folder)
        if not semua_foto:
            lapor.peringatan("Folder kosong", "Tidak ada file JPEG atau RAW yang didukung di folder tersebut.")
            lapor.selesai("Tidak ada foto untuk diproses.", False)
            return

        ukuran_batch = ukuran_batch_untuk_model(nama_model)
        kelompok_foto = [semua_foto[i:i + ukuran_batch] for i in range(0, len(semua_foto), ukuran_batch)]
        jumlah_batch = len(kelompok_foto)
        kuota_dasar, sisa_kuota = divmod(target_excellent, jumlah_batch)
        total_byte = sum(os.path.getsize(path) for path in semua_foto)
        byte_terkirim = 0
        checksum_terlihat = set()
        keputusan_batch = []

        for indeks, batch in enumerate(kelompok_foto):
            if self.cancel_event.is_set():
                lapor.selesai("Proses dibatalkan.", False)
                return

            kuota_batch = kuota_dasar + (1 if indeks < sisa_kuota else 0)
            lapor.status(f"Menganalisis batch {indeks + 1} dari {jumlah_batch}...")
            lapor.progress(indeks / jumlah_batch * 100)

            gambar_dikirim, nama_file_batch, nama_file_unik = [], [], []
            keputusan_awal = {}
            for file in batch:
                nama_file = os.path.basename(file)
                nama_file_batch.append(nama_file)
                checksum = checksum_file(file)
                if checksum in checksum_terlihat:
                    keputusan_awal[nama_file] = "Bad"
                    continue
                checksum_terlihat.add(checksum)
                try:
                    gambar, ukuran = kompresi_untuk_ai(file)
                    gambar_dikirim.append(gambar)
                    nama_file_unik.append(nama_file)
                    byte_terkirim += ukuran
                except Exception as error:
                    print(f"Gagal memuat {nama_file}: {error}")
                    keputusan_awal[nama_file] = "Bad"

            lapor.data(f"Data salinan AI: {format_ukuran(byte_terkirim)} | Asli: {format_ukuran(total_byte)}")
            prompt = PROMPT_TEMPLATE.format(kuota_batch=kuota_batch, daftar_nama=", ".join(nama_file_unik))

            try:
                keputusan = dict(keputusan_awal)
                if gambar_dikirim:
                    respons = model.generate_content(
                        [prompt] + gambar_dikirim,
                        generation_config={
                            "temperature": 0.1,
                            "response_mime_type": "application/json",
                        },
                    )
                    keputusan.update(baca_json_model(respons.text))
                keputusan = normalisasi_keputusan(nama_file_batch, keputusan, kuota_batch)
            except Exception as error:
                lapor.selesai(f"Gemini gagal di batch {indeks + 1}: {type(error).__name__}: {error}", False)
                return
            finally:
                for gambar in gambar_dikirim:
                    gambar.close()

            keputusan_batch.append(keputusan)
            lapor.status(f"Batch {indeks + 1} dari {jumlah_batch} selesai.")
            lapor.progress((indeks + 1) / jumlah_batch * 100)

            if self.cancel_event.is_set():
                lapor.selesai("Proses dihentikan setelah batch aktif selesai.", False)
                return

        lapor.status("Menulis metadata XMP...")
        keputusan_semua = penuhi_target_global(keputusan_batch, target_excellent)
        jumlah_hasil = {"Excellent": 0, "Good": 0, "Bad": 0}
        for nama_file, status in keputusan_semua.items():
            path_foto = os.path.join(folder, nama_file)
            buat_file_xmp(path_foto, status)
            jumlah_hasil[status] += 1
        lapor.progress(100)
        lapor.selesai(
            f"Selesai. Excellent: {jumlah_hasil['Excellent']} | Good: {jumlah_hasil['Good']} | Bad: {jumlah_hasil['Bad']}.",
            True,
        )


# ---------------------------------------------------------------------------
# Deteksi & pembukaan editor
# ---------------------------------------------------------------------------
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
    """Buka editor terpilih. Fungsi ini memblokir sampai ~2,5 detik untuk
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
        time.sleep(2.0)
        if aktifkan_jendela_capture_one(aktifkan=True):
            time.sleep(0.3)
            try:
                kirim_shortcut_import_capture_one()
            except Exception as error:
                print(f"Gagal mengirim shortcut import Capture One: {error}")
        return "Capture One dibuka. Jalankan import dari panel yang muncul (Ctrl+Shift+I)."

    _jalankan_terpisah([executable, folder])
    return f"{nama_editor} dibuka dengan folder foto terpilih."
