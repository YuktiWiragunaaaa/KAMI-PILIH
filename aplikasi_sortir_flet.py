# Library standar dan dependensi eksternal
import os
import glob
import json
import hashlib
import io
import base64
import ctypes
import subprocess
import shutil
import time
import winreg
from ctypes import wintypes
import queue
import threading
import flet as ft
import google.generativeai as genai
import rawpy
from PIL import Image


# Konfigurasi aplikasi dan state global
cancel_event = threading.Event()
antrian_ui = queue.Queue()
antrian_selesai = queue.Queue()
worker_thread = None
UKURAN_MAKS_AI = 1280
KUALITAS_JPEG_AI = 78
MODEL_GEMINI_DEFAULT = "gemini-3.5-flash-lite"
MODEL_GEMINI_OPTIONS = (
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
)
FILE_LOGIN = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "SortirAI", "login.dat")
session_logged_out = False
api_key_sesi_sebelum_logout = ""
proses_sedang_berjalan = False
editor_terdeteksi = {}
EKSTENSI_RAW = (".arw", ".cr2", ".cr3", ".nef", ".raf", ".orf", ".rw2", ".dng")

KONFIGURASI_EDITOR = (
    ("Capture One", ("Capture One.exe", "CaptureOne.exe"), ("Capture One",)),
    ("Lightroom Classic", ("Lightroom.exe",), ("Adobe", "Lightroom")),
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
        with open(FILE_LOGIN, "r", encoding="ascii") as file:
            data = json.loads(dekripsi_login(file.read()))
        return data if data.get("api_key") else None
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def simpan_login(data):
    os.makedirs(os.path.dirname(FILE_LOGIN), exist_ok=True)
    with open(FILE_LOGIN, "w", encoding="ascii") as file:
        file.write(enkripsi_login(json.dumps(data)))


def perbarui_model_otomatis(api_key):
    if not api_key:
        return
    try:
        genai.configure(api_key=api_key)
        model_tersedia = []
        for model in genai.list_models():
            metode = getattr(model, "supported_generation_methods", [])
            nama = getattr(model, "name", "").replace("models/", "")
            if "generateContent" in metode and nama.startswith("gemini-"):
                model_tersedia.append(nama)
        if model_tersedia:
            kirim_ui(pasang_model_otomatis, sorted(model_tersedia))
    except Exception as error:
        print(f"Daftar model otomatis tidak tersedia: {error}")


def pasang_model_otomatis(model_tersedia):
    model_saat_ini = pilihan_model.get()
    pilihan_model.configure(values=model_tersedia)
    if model_saat_ini in model_tersedia:
        pilihan_model.set(model_saat_ini)
    elif MODEL_GEMINI_DEFAULT in model_tersedia:
        pilihan_model.set(MODEL_GEMINI_DEFAULT)
    elif model_tersedia:
        pilihan_model.set(model_tersedia[0])
    pilihan_model.configure(state="disabled" if proses_sedang_berjalan else "readonly")
    label_model.config(text=f"{len(model_tersedia)} model vision tersedia dari API Gemini.")


def kirim_ui(callback, *args, **kwargs):
    antrian_ui.put((callback, args, kwargs))


def proses_antrian_ui():
    while True:
        try:
            callback, args, kwargs = antrian_ui.get_nowait()
        except queue.Empty:
            break
        try:
            callback(*args, **kwargs)
        except Exception as error:
            print(f"Callback UI gagal: {error}")
            messagebox.showerror("Kesalahan callback UI", str(error))
    app.after(20, proses_antrian_ui)


def set_status(teks):
    kirim_ui(label_status.config, text=teks)


def format_ukuran(byte_count):
    """Format byte ke satuan yang mudah dibaca: B, KB, MB, GB."""
    if byte_count < 1000:
        return f"{int(byte_count)} B"
    if byte_count < 1000 ** 2:
        return f"{byte_count / 1000:.2f} KB"
    if byte_count < 1000 ** 3:
        return f"{byte_count / (1000 ** 2):.2f} MB"
    return f"{byte_count / (1000 ** 3):.2f} GB"


def atur_progress(persen):
    """Update progress bar dan teks persen pada UI."""
    progress_bar.config(value=persen)
    label_progress.config(text=f"{int(persen)}%")


def normalisasi_keputusan(nama_file_batch, keputusan, kuota_excellent, default_status="Bad"):
    """Validasi status tanpa mengubah foto Bad menjadi pilihan."""
    status_valid = {"Excellent", "Good", "Bad"}
    keputusan_normal = {
        os.path.basename(str(nama)).lower(): str(status).strip().title().replace("Choice", "Good")
        for nama, status in keputusan.items()
    }
    hasil = {
        nama: keputusan_normal.get(nama.lower(), default_status)
        if keputusan_normal.get(nama.lower(), default_status) in status_valid else default_status
        for nama in nama_file_batch
    }
    nama_excellent = [nama for nama in nama_file_batch if hasil[nama] == "Excellent"]

    if len(nama_excellent) > kuota_excellent:
        for nama in nama_excellent[kuota_excellent:]:
            hasil[nama] = "Good"
    elif len(nama_excellent) < kuota_excellent:
        kandidat = [nama for nama in nama_file_batch if hasil[nama] == "Good"]
        for nama in kandidat[:kuota_excellent - len(nama_excellent)]:
            hasil[nama] = "Excellent"
    return hasil


def baca_json_model(teks):
    """Ambil objek JSON meski model membungkusnya dengan Markdown atau teks tambahan."""
    teks = teks.strip().replace("```json", "").replace("```", "").strip()
    awal = teks.find("{")
    akhir = teks.rfind("}")
    if awal < 0 or akhir < awal:
        raise ValueError("Respons Gemini tidak berisi objek JSON.")
    hasil = json.loads(teks[awal:akhir + 1])
    if not isinstance(hasil, dict):
        raise ValueError("Respons Gemini bukan objek JSON.")
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
                nama_status = [
                    nama for nama, status in keputusan.items()
                    if status == status_kandidat
                ]
                if urutan < len(nama_status):
                    kandidat.append(nama_status[urutan])

    pilihan = set(kandidat[:target_excellent])
    for nama, status in keputusan_semua.items():
        if status in {"Excellent", "Good"}:
            keputusan_semua[nama] = "Excellent" if nama in pilihan else "Good"
    return keputusan_semua


# Persiapan foto dan checksum sebelum dikirim ke AI
def daftar_foto(folder):
    """Kumpulkan JPEG dan RAW tanpa menganalisis pasangan dengan basename sama dua kali."""
    jpeg = sorted(
        glob.glob(os.path.join(folder, "*.jpg"))
        + glob.glob(os.path.join(folder, "*.JPG"))
    )
    stem_jpeg = {os.path.splitext(os.path.basename(path))[0].lower() for path in jpeg}
    raw = sorted(
        path
        for ekstensi in EKSTENSI_RAW
        for path in glob.glob(os.path.join(folder, f"*{ekstensi}"))
        + glob.glob(os.path.join(folder, f"*{ekstensi.upper()}"))
        if os.path.splitext(os.path.basename(path))[0].lower() not in stem_jpeg
    )
    return jpeg + raw


def kompresi_untuk_ai(path_foto):
    """Buat salinan JPEG kecil di memori; file asli tidak pernah diubah."""
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

# Penulisan metadata XMP untuk JPEG dan RAW
def buat_file_xmp(path_foto, status):
    metadata = {
        "Excellent": ("Green", "3"),
        "Good": ("", "1"),
        "Bad": ("", "0"),
    }
    label, rating = metadata[status]
    base_name = os.path.splitext(path_foto)[0]
    xmp_path = f"{base_name}.xmp"
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


def tulis_ke_raw_sepasang(path_jpeg, status):
    """Salin metadata ke RAW dengan basename sama agar bisa dibaca Capture One."""
    dasar = os.path.splitext(path_jpeg)[0]
    for ekstensi in EKSTENSI_RAW:
        path_raw = dasar + ekstensi
        if os.path.exists(path_raw):
            buat_file_xmp(path_raw, status)


# Worker AI dan orkestrasi proses sortir
def proses_ai(folder, api_key, target_good, nama_model):
    set_status("Menghubungkan ke Gemini...")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(nama_model)

    semua_foto = daftar_foto(folder)
    total_foto = len(semua_foto)

    if total_foto == 0:
        kirim_ui(messagebox.showwarning, "Folder kosong", "Tidak ada file JPEG atau RAW yang didukung di folder tersebut.")
        selesai_worker("Tidak ada foto untuk diproses.")
        return

    ukuran_batch = 30
    kelompok_foto = [semua_foto[i:i + ukuran_batch] for i in range(0, total_foto, ukuran_batch)]
    jumlah_batch = len(kelompok_foto)
    kuota_dasar, sisa_kuota = divmod(target_good, jumlah_batch)
    total_byte = sum(os.path.getsize(path) for path in semua_foto)
    byte_terkirim = 0
    jumlah_hasil = {"Excellent": 0, "Good": 0, "Bad": 0}
    checksum_terlihat = set()
    keputusan_batch = []

    for indeks, batch in enumerate(kelompok_foto):
        if cancel_event.is_set():
            selesai_worker("Proses dibatalkan.")
            return

        kuota_batch = kuota_dasar + (1 if indeks < sisa_kuota else 0)
        set_status(f"Menganalisis batch {indeks + 1} dari {jumlah_batch}...")
        kirim_ui(atur_progress, (indeks / jumlah_batch) * 100)

        gambar_dikirim = []
        buffer_gambar = []
        nama_file_batch = []
        nama_file_unik = []
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
                gambar, ukuran_kompresi = kompresi_untuk_ai(file)
                gambar_dikirim.append(gambar)
                buffer_gambar.append(gambar)
                nama_file_unik.append(nama_file)
                byte_terkirim += ukuran_kompresi
            except Exception as error:
                print(f"Gagal memuat {nama_file}: {error}")
                keputusan_awal[nama_file] = "Bad"

        kirim_ui(
            label_data.config,
            text=f"Data salinan AI: {format_ukuran(byte_terkirim)} | Asli: {format_ukuran(total_byte)}",
        )
        prompt = f"""
                Anda adalah fotografer senior sekaligus kurator foto profesional. Analisis setiap foto secara
                ketat, objektif, dan konsisten. Nilai foto berdasarkan kualitas visual yang benar-benar terlihat,
                bukan berdasarkan asumsi tentang jenis acaranya. Standar ini berlaku untuk foto event, wedding,
                olahraga, dokumentasi, portrait, produk, maupun foto studio.

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

                Output WAJIB berupa JSON murni tanpa Markdown, komentar, atau teks tambahan. Gunakan key hanya
                nama file berikut dan nilai hanya salah satu dari "Excellent", "Good", atau "Bad":
                {', '.join(nama_file_unik)}
            """

        try:
            keputusan = keputusan_awal
            if gambar_dikirim:
                respons = model.generate_content([prompt] + gambar_dikirim)
                keputusan.update(baca_json_model(respons.text))
            if cancel_event.is_set():
                selesai_worker("Proses dihentikan setelah batch aktif selesai.")
                return
            keputusan = normalisasi_keputusan(nama_file_batch, keputusan, kuota_batch)
        except Exception as e:
            pesan_error = f"Gemini gagal di batch {indeks + 1}: {type(e).__name__}: {e}"
            print(pesan_error)
            selesai_worker(pesan_error)
            return
        finally:
            for gambar in buffer_gambar:
                gambar.close()

        keputusan_batch.append(keputusan)
        set_status(f"Batch {indeks + 1} dari {jumlah_batch} selesai.")
        kirim_ui(atur_progress, ((indeks + 1) / jumlah_batch) * 100)

    keputusan_semua = penuhi_target_global(keputusan_batch, target_good)
    for nama_file, status in keputusan_semua.items():
        path_foto = os.path.join(folder, nama_file)
        buat_file_xmp(path_foto, status)
        if os.path.splitext(path_foto)[1].lower() in (".jpg", ".jpeg"):
            tulis_ke_raw_sepasang(path_foto, status)
        jumlah_hasil[status] += 1
    kirim_ui(atur_progress, 100)
    selesai_worker(
        f"Selesai. Excellent: {jumlah_hasil['Excellent']} | Good: {jumlah_hasil['Good']} | Bad: {jumlah_hasil['Bad']}.",
        sukses=True,
    )


def jalankan_proses(folder, api_key, target_good, nama_model):
    try:
        proses_ai(folder, api_key, target_good, nama_model)
    except Exception as error:
        print(f"Proses gagal: {error}")
        selesai_worker(f"Proses gagal: {error}")


# Kontrol proses, folder, dan status tombol impor
def selesai_worker(teks, sukses=False):
    antrian_selesai.put((teks, sukses))


def pantau_worker():
    global worker_thread
    try:
        teks, sukses = antrian_selesai.get_nowait()
    except queue.Empty:
        teks = None
        sukses = False
    if teks is not None:
        tandai_selesai(teks, sukses)
    elif worker_thread is not None and not worker_thread.is_alive():
        tandai_selesai("Proses selesai tanpa laporan hasil.", False)
    app.after(100, pantau_worker)


def tandai_selesai(teks, sukses=False):
    global worker_thread
    worker_thread = None
    label_status.config(text=teks)
    if sukses:
        messagebox.showinfo("Sortir selesai", teks)
    try:
        atur_kontrol_proses(False)
    except Exception as error:
        print(f"Kontrol UI gagal dipulihkan: {error}")
        messagebox.showerror(
            "UI belum pulih",
            "Sortir sudah selesai, tetapi kontrol UI gagal dipulihkan. "
            f"Detail: {error}",
        )
    finally:
        tombol_import_editor.config(state=tk.NORMAL if editor_terdeteksi else tk.DISABLED)
        tombol_import_editor.pack(side="right", padx=(0, 10))


def _laporkan_error_tkinter_unused(exception_type, exception_value, traceback_object):
    """Tampilkan error callback Tkinter agar kegagalan UI tidak tersembunyi."""
    print("Tkinter callback error:", exception_value)
    messagebox.showerror("Kesalahan aplikasi", str(exception_value))

def mulai_thread():
    folder = label_folder.cget("text")
    api_key = entry_api.get().strip()
    if not api_key and not session_logged_out:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
    nama_model = pilihan_model.get().strip() or MODEL_GEMINI_DEFAULT
    target_teks = entry_target.get().strip()
    if folder == "Belum ada folder dipilih":
        messagebox.showerror("Folder belum dipilih", "Pilih folder foto terlebih dahulu.")
        return
    if not target_teks:
        messagebox.showerror("Target belum diisi", "Masukkan jumlah foto Excellent terlebih dahulu.")
        return
    if not api_key:
        messagebox.showerror("API Key belum diisi", "Masukkan API Key Gemini terlebih dahulu.")
        return
    try:
        target_good = int(target_teks)
        if target_good < 1:
            raise ValueError
    except ValueError:
        messagebox.showerror("Target tidak valid", "Target foto harus berupa angka bulat minimal 1.")
        return

    semua_foto = daftar_foto(folder)
    if target_good > len(semua_foto):
        messagebox.showerror(
            "Target terlalu besar",
            f"Folder hanya berisi {len(semua_foto)} foto JPEG/RAW yang didukung.",
        )
        entry_target.focus_set()
        return

    global proses_sedang_berjalan
    cancel_event.clear()
    proses_sedang_berjalan = True
    atur_kontrol_proses(True)
    tombol_mulai.config(state=tk.DISABLED)
    tombol_batal.config(state=tk.NORMAL)
    atur_progress(0)
    label_data.config(text="Data salinan AI: 0 B")
    global worker_thread
    worker_thread = threading.Thread(
        target=jalankan_proses, args=(folder, api_key, target_good, nama_model), daemon=True
    )
    worker_thread.start()


def batalkan_proses():
    if not proses_sedang_berjalan:
        return
    cancel_event.set()
    tombol_batal.config(state=tk.DISABLED)
    label_status.config(text="Stop diminta. Menunggu batch aktif selesai...")

def pilih_folder():
    folder_terpilih = filedialog.askdirectory()
    if folder_terpilih:
        label_folder.config(text=folder_terpilih)


def cari_executable_editor(nama_editor):
    konfigurasi = next((item for item in KONFIGURASI_EDITOR if item[0] == nama_editor), None)
    if not konfigurasi:
        return None
    _, nama_executable, folder_produk = konfigurasi

    kandidat = []
    if nama_editor == "Capture One":
        kandidat.extend([
            r"C:\Program Files\Capture One\Capture One\CaptureOne.exe",
            r"C:\Program Files (x86)\Capture One\Capture One\CaptureOne.exe",
        ])

    for dasar in (
        os.getenv("ProgramFiles"),
        os.getenv("ProgramW6432"),
        os.getenv("ProgramFiles(x86)"),
        os.getenv("LOCALAPPDATA"),
    ):
        if not dasar:
            continue
        for folder in folder_produk:
            folder_variants = {folder, folder.replace(" ", "")}
            for folder_cocok in folder_variants:
                for executable in nama_executable:
                    kandidat.append(os.path.join(dasar, folder_cocok, executable))
                    kandidat.extend(
                        glob.glob(os.path.join(dasar, folder_cocok, "**", executable), recursive=True)
                    )

    for executable in nama_executable:
        lokasi = shutil.which(executable)
        if lokasi:
            kandidat.append(lokasi)

        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for registry_path in (
                fr"Software\Microsoft\Windows\CurrentVersion\App Paths\{executable}",
                fr"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\{executable}",
            ):
                try:
                    with winreg.OpenKey(root, registry_path) as key:
                        lokasi_registry = winreg.QueryValue(key, None)
                    if lokasi_registry:
                        kandidat.append(lokasi_registry.strip('"'))
                except (FileNotFoundError, OSError):
                    continue

    executable_valid = next((path for path in kandidat if path and os.path.isfile(path)), None)
    if executable_valid:
        return executable_valid

    if nama_editor == "Capture One":
        shortcut_roots = (
            os.path.join(os.getenv("ProgramData", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
            os.path.join(os.getenv("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
        )
        shortcut = next(
            (
                path
                for root in shortcut_roots
                if root
                for path in glob.glob(os.path.join(root, "Capture One", "**", "Capture One.lnk"), recursive=True)
                if os.path.isfile(path)
            ),
            None,
        )
        if shortcut:
            return shortcut

    return None


def deteksi_editor():
    """Kembalikan editor foto yang terpasang dan executable-nya."""
    hasil = {}
    for nama_editor, _, _ in KONFIGURASI_EDITOR:
        executable = cari_executable_editor(nama_editor)
        if executable:
            hasil[nama_editor] = executable
    return hasil


def aktifkan_jendela_capture_one(hwnd_target=None, aktifkan=True):
    """Cari jendela utama Capture One dan, bila diminta, bawa ke depan."""
    user32 = ctypes.windll.user32
    nama_jendela = ctypes.create_unicode_buffer(256)
    jendela_ditemukan = []

    if hwnd_target and user32.IsWindow(hwnd_target):
        jendela_ditemukan.append(hwnd_target)

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def periksa_jendela(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        user32.GetWindowTextW(hwnd, nama_jendela, len(nama_jendela))
        kotak = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(kotak))
        lebar = kotak.right - kotak.left
        tinggi = kotak.bottom - kotak.top
        if (
            "Capture One" in nama_jendela.value
            and user32.IsWindowEnabled(hwnd)
            and lebar >= 500
            and tinggi >= 300
        ):
            jendela_ditemukan.append(hwnd)
        return True

    if not jendela_ditemukan:
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
    """Kirim Ctrl+Shift+I setelah fokus Capture One dipastikan aktif."""
    user32 = ctypes.windll.user32
    for kunci in (0x11, 0x10, 0x49):
        user32.keybd_event(kunci, 0, 0, 0)
    for kunci in (0x49, 0x10, 0x11):
        user32.keybd_event(kunci, 0, 2, 0)


def buka_import_capture_one(folder, executable):
    """Lewati proses sortir dan buka Capture One langsung ke panel import."""
    if not executable or not os.path.isfile(executable):
        executable = cari_executable_editor("Capture One")
    if not executable or not os.path.isfile(executable):
        raise FileNotFoundError("Executable Capture One tidak ditemukan saat akan dibuka.")

    flags = (
        subprocess.DETACHED_PROCESS
        | subprocess.CREATE_NEW_PROCESS_GROUP
        | subprocess.CREATE_BREAKAWAY_FROM_JOB
    )
    try:
        subprocess.Popen(
            [executable],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            cwd=os.path.dirname(executable),
            creationflags=flags,
        )
    except OSError:
        os.startfile(executable)

    time.sleep(2.0)
    hwnd = aktifkan_jendela_capture_one(aktifkan=True)
    if hwnd:
        try:
            time.sleep(0.3)
            kirim_shortcut_import_capture_one()
        except Exception as error:
            print(f"Gagal mengirim shortcut import Capture One: {error}")

    kirim_ui(
        label_status.config,
        text="Buka Capture One dan jalankan import manual dari tombol ini.",
    )


def status_dari_xmp(path_foto):
    """Baca status hasil sortir dari sidecar XMP yang dibuat aplikasi."""
    xmp_path = f"{os.path.splitext(path_foto)[0]}.xmp"
    try:
        with open(xmp_path, "r", encoding="utf-8") as file:
            isi = file.read()
    except OSError:
        return "Good"
    if '<xmp:Label>Green</xmp:Label>' in isi or '<xmp:Rating>3</xmp:Rating>' in isi:
        return "Excellent"
    if '<xmp:Rating>0</xmp:Rating>' in isi:
        return "Bad"
    return "Good"


def siapkan_session_capture_one(folder):
    """Siapkan folder session yang tidak memindahkan atau mengubah foto asli."""
    nama_folder = os.path.basename(os.path.normpath(folder)) or "Foto"
    cap_waktu = time.strftime("%Y%m%d-%H%M%S")
    nama_session = f"Capture One Session - {nama_folder} - {cap_waktu}"
    session_folder = os.path.join(os.path.dirname(folder), nama_session)
    nomor_session = 2
    while os.path.exists(session_folder):
        session_folder = os.path.join(
            os.path.dirname(folder),
            f"{nama_session}-{nomor_session}",
        )
        nomor_session += 1
    os.makedirs(session_folder, exist_ok=True)
    for nama_subfolder in ("Capture", "Selects", "Output", "Trash"):
        os.makedirs(os.path.join(session_folder, nama_subfolder), exist_ok=True)

    for status in ("Excellent", "Good", "Bad"):
        folder_status = os.path.join(session_folder, "Capture", status)
        os.makedirs(folder_status, exist_ok=True)
        for path_foto in daftar_foto(folder):
            nama_file = os.path.basename(path_foto)
            if status != status_dari_xmp(path_foto):
                continue
            target = os.path.join(folder_status, os.path.basename(nama_file))
            if os.path.exists(target):
                continue
            try:
                os.link(nama_file, target)
            except OSError:
                shutil.copy2(nama_file, target)
            xmp_asal = f"{os.path.splitext(nama_file)[0]}.xmp"
            if os.path.exists(xmp_asal):
                shutil.copy2(xmp_asal, f"{os.path.splitext(target)[0]}.xmp")
    return session_folder


def impor_ke_editor():
    """Buka editor terpilih dengan folder foto sebagai konteks kerja."""
    nama_editor = pilihan_editor.get().strip()
    executable = editor_terdeteksi.get(nama_editor)
    if executable and not os.path.isfile(executable):
        executable = None
    if executable:
        try:
            folder = label_folder.cget("text")
            if folder == "Belum ada folder dipilih":
                messagebox.showwarning("Folder belum dipilih", "Pilih folder foto terlebih dahulu.")
                return
            if nama_editor == "Capture One":
                target = buka_import_capture_one
                argumen = (folder, executable)
            else:
                executable = cari_executable_editor(nama_editor)
                if not executable:
                    raise FileNotFoundError(
                        f"Executable {nama_editor} tidak lagi ditemukan. Silakan buka ulang aplikasi."
                    )
                target = buka_editor_umum
                argumen = (folder, executable, nama_editor)
            target(*argumen)
            return
        except OSError as error:
            messagebox.showerror(
                f"{nama_editor} gagal dibuka",
                f"{error}\n\nPath yang terdeteksi: {executable or 'tidak ada'}",
            )
            return

    messagebox.showerror(
        "Editor tidak ditemukan",
        f"Executable {nama_editor or 'editor terpilih'} tidak ditemukan. Muat ulang aplikasi untuk mendeteksi ulang.",
    )


def buka_editor_umum(folder, executable, nama_editor):
    """Jalankan editor umum dan teruskan folder foto bila didukung editor tersebut."""
    flags = (
        subprocess.DETACHED_PROCESS
        | subprocess.CREATE_NEW_PROCESS_GROUP
        | subprocess.CREATE_BREAKAWAY_FROM_JOB
    )
    subprocess.Popen(
        [executable, folder],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=flags,
    )
    kirim_ui(label_status.config, text=f"{nama_editor} dibuka dengan folder foto terpilih.")


def _perbarui_editor_terpilih_unused(_event=None):
    nama_editor = pilihan_editor.get().strip()
    tombol_import_editor.config(
        text=f"Buka {nama_editor}" if nama_editor else "Buka editor"
    )


def _atur_kontrol_proses_unused(sedang_proses):
    global proses_sedang_berjalan
    proses_sedang_berjalan = sedang_proses
    if sedang_proses:
        entry_api.config(state=tk.DISABLED)
        pilihan_model.config(state=tk.DISABLED)
        pilihan_editor.config(state=tk.DISABLED)
        entry_target.config(state=tk.DISABLED)
        tombol_folder.config(state=tk.DISABLED)
        tombol_login.config(state=tk.DISABLED)
        tombol_mulai.config(state=tk.DISABLED)
        tombol_import_editor.config(state=tk.DISABLED)
        tombol_batal.config(state=tk.NORMAL)
    else:
        status_api = "readonly" if tombol_login.cget("text") == "Logout / Ganti API" else tk.NORMAL
        entry_api.config(state=status_api)
        pilihan_model.config(state="readonly")
        pilihan_editor.config(state="readonly" if editor_terdeteksi else tk.DISABLED)
        entry_target.config(state=tk.NORMAL)
        tombol_folder.config(state=tk.NORMAL)
        tombol_login.config(state=tk.NORMAL)
        tombol_mulai.config(state=tk.NORMAL)
        tombol_import_editor.config(state=tk.NORMAL if editor_terdeteksi else tk.DISABLED)
        tombol_batal.config(state=tk.DISABLED)


# Login, logout, dan pergantian API key
def _kelola_login_unused():
    global session_logged_out, api_key_sesi_sebelum_logout
    if tombol_login.cget("text") == "Logout / Ganti API":
        api_key_sesi_sebelum_logout = entry_api.get().strip()
        session_logged_out = True
        try:
            os.remove(FILE_LOGIN)
        except FileNotFoundError:
            pass
        entry_api.config(state=tk.NORMAL)
        entry_api.delete(0, tk.END)
        entry_api.insert(0, api_key_sesi_sebelum_logout)
        entry_api.pack(fill="x", before=label_kredensial)
        tombol_login.config(text="Login / Simpan API")
        label_kredensial.config(text="Sesi dihapus. API key tetap tersedia di form dan belum tersimpan.")
        return

    api_key = entry_api.get().strip()
    nama_model = pilihan_model.get().strip() or MODEL_GEMINI_DEFAULT
    if not api_key:
        messagebox.showerror("API key kosong", "Masukkan API key Gemini terlebih dahulu.")
        return
    try:
        simpan_login({"api_key": api_key, "model": nama_model})
    except Exception as error:
        messagebox.showerror(
            "Login gagal",
            "API key belum tersimpan. Pastikan aplikasi berjalan di Windows dan "
            f"memiliki izin menyimpan data login. Detail: {error}",
        )
        return
    entry_api.config(state="readonly")
    entry_api.pack_forget()
    session_logged_out = False
    tombol_login.config(text="Logout / Ganti API")
    label_kredensial.config(text="Login tersimpan aman di Windows untuk akun ini.")




def main(page: ft.Page):
    page.title = "Sortir AI"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.spacing = 0
    page.fonts = {
        "Inter": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
    }
    page.theme = ft.Theme(font_family="Inter")

    # Colors mapping from CSS
    bg1 = "#0f1120"
    bg2 = "#171a30"
    ink = "#f1f5f9"
    ink_2 = "#e2e8f0"
    muted = "#a5b0c4"
    faint = "#8b96ac"
    glass = ft.Colors.with_opacity(0.08, ft.Colors.WHITE)
    glass_2 = ft.Colors.with_opacity(0.06, ft.Colors.WHITE)
    glass_input = ft.Colors.with_opacity(0.08, ft.Colors.WHITE)
    line = ft.Colors.with_opacity(0.18, ft.Colors.WHITE)
    line_input = ft.Colors.with_opacity(0.14, ft.Colors.WHITE)
    chip_ink = "#a5b4fc"
    accent_a = "#4f7bff"
    accent_b = "#995cff"
    
    # State variables
    folder_path = ""
    api_key_data = baca_login()
    if api_key_data:
        api_key_str = api_key_data.get("api_key", "")
    else:
        api_key_str = ""
        
    def show_snack(message):
        page.snack_bar = ft.SnackBar(ft.Text(message))
        page.snack_bar.open = True
        page.update()

    def update_progress(p):
        bar.value = p / 100.0
        pct_text.value = f"{int(p)}%"
        page.update()

    def update_status(text):
        msg_text.value = text
        page.update()

    def handle_pick_folder(e):
        nonlocal folder_path
        if e.path:
            folder_path = e.path
            folder_status.value = f"{os.path.basename(folder_path)} terpilih"
            folder_status.color = ink_2
            page.update()

    folder_dialog = ft.FilePicker(on_result=handle_pick_folder)
    page.overlay.append(folder_dialog)

    def start_sortir(e):
        target_val = target_input.value
        if not folder_path:
            show_snack("Pilih folder foto terlebih dahulu.")
            return
        if not target_val.isdigit() or int(target_val) < 1:
            show_snack("Masukkan target foto Excellent minimal 1.")
            return
        if not apikey_input.value:
            show_snack("Masukkan API Key Gemini terlebih dahulu.")
            return

        global proses_sedang_berjalan
        proses_sedang_berjalan = True
        cancel_event.clear()
        
        btn_start.disabled = True
        btn_cancel.disabled = False
        update_progress(0)
        
        # Override UI callback for backend
        global kirim_ui
        def dummy_kirim(func, *args, **kwargs):
            if func == atur_progress:
                update_progress(args[0])
            elif func.__name__ == 'config' and getattr(func, '__self__', None):
                widget = func.__self__
                # Just string match mapping for the backend Tkinter widgets
                if hasattr(widget, "widgetName") and widget.widgetName == "label":
                    if "status" in str(widget):
                        update_status(kwargs.get("text", ""))
            
        kirim_ui = dummy_kirim

        global atur_progress
        atur_progress = update_progress

        global set_status
        set_status = update_status
        
        # Start AI worker thread
        global worker_thread
        worker_thread = threading.Thread(
            target=jalankan_proses, 
            args=(folder_path, apikey_input.value, int(target_val), model_dropdown.value),
            daemon=True
        )
        worker_thread.start()
        check_worker()
        page.update()

    def cancel_sortir(e):
        if proses_sedang_berjalan:
            cancel_event.set()
            btn_cancel.disabled = True
            update_status("Dibatalkan, menunggu batch selesai...")
            page.update()

    def check_worker():
        try:
            teks, sukses = antrian_selesai.get_nowait()
            update_status(teks)
            show_snack(teks)
            btn_start.disabled = False
            btn_cancel.disabled = True
            global proses_sedang_berjalan
            proses_sedang_berjalan = False
            page.update()
        except queue.Empty:
            if worker_thread and not worker_thread.is_alive():
                btn_start.disabled = False
                btn_cancel.disabled = True
                page.update()
            else:
                import threading
                threading.Timer(0.1, check_worker).start()

    # UI Components
    apikey_input = ft.TextField(
        value=api_key_str, password=True, can_reveal_password=True,
        border_color=line_input, bgcolor=glass_input, color=ink,
        text_size=14, height=40, content_padding=10
    )
    
    model_dropdown = ft.Dropdown(
        options=[ft.dropdown.Option(x) for x in MODEL_GEMINI_OPTIONS],
        value=MODEL_GEMINI_DEFAULT,
        border_color=line_input, bgcolor=glass_input, color=ink,
        text_size=14, height=40, content_padding=10
    )
    
    target_input = ft.TextField(
        value="15",
        border_color=line_input, bgcolor=glass_input, color=ink,
        text_size=14, height=40, content_padding=10, width=100
    )
    
    def step_target(d):
        try:
            val = int(target_input.value)
        except:
            val = 0
        target_input.value = str(max(1, val + d))
        page.update()

    folder_status = ft.Text("Belum ada folder dipilih", color=faint, size=13)
    
    editor_dropdown = ft.Dropdown(
        options=[ft.dropdown.Option(x) for x in tuple(deteksi_editor())],
        border_color=line_input, bgcolor=glass_input, color=ink,
        text_size=14, height=40, content_padding=10
    )
    if editor_dropdown.options:
        editor_dropdown.value = editor_dropdown.options[0].key
    else:
        editor_dropdown.options.append(ft.dropdown.Option("Tidak ada editor terdeteksi"))
        editor_dropdown.value = "Tidak ada editor terdeteksi"

    msg_text = ft.Text("Siap memulai.", color=ink_2, size=14, weight=ft.FontWeight.W_500, expand=True)
    pct_text = ft.Text("0%", color=chip_ink, size=14, weight=ft.FontWeight.W_600)
    bar = ft.ProgressBar(value=0, color=accent_a, bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE), height=10)
    
    btn_cancel = ft.ElevatedButton(
        "Batalkan", on_click=cancel_sortir, disabled=True,
        color=ink_2, bgcolor=ft.Colors.with_opacity(0.4, ft.Colors.WHITE),
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=14))
    )
    
    btn_start = ft.ElevatedButton(
        "✦ Mulai sortir", on_click=start_sortir,
        color=ft.Colors.WHITE, bgcolor=accent_a,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=14))
    )

    card = ft.Container(
        width=680,
        padding=36,
        border_radius=28,
        bgcolor=glass,
        border=ft.border.all(1.5, line),
        blur=ft.Blur(40, 40, ft.BlurTileMode.MIRROR),
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=60, color=ft.Colors.with_opacity(0.45, ft.Colors.BLACK), offset=ft.Offset(0, 24)),
        content=ft.Column(
            spacing=24,
            controls=[
                ft.Row([
                    ft.Container(
                        width=56, height=56, border_radius=16, alignment=ft.alignment.center,
                        gradient=ft.LinearGradient([accent_a, accent_b]),
                        content=ft.Text("✦", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
                    ),
                    ft.Column([
                        ft.Text("Sortir AI", size=30, weight=ft.FontWeight.BOLD, color=ink),
                        ft.Text("Pilih foto terbaik lalu buka hasilnya di editor pilihan", size=14, color=muted)
                    ], spacing=4)
                ]),
                
                ft.Container(
                    padding=24, border_radius=20, bgcolor=glass_2, border=ft.border.all(1, line),
                    content=ft.Column(
                        spacing=18,
                        controls=[
                            ft.Text("KONFIGURASI", size=11, weight=ft.FontWeight.W_600, color=faint),
                            ft.Column([
                                ft.Text("API Key Gemini", size=13, weight=ft.FontWeight.W_500, color=ink_2),
                                apikey_input,
                            ], spacing=8),
                            ft.Column([
                                ft.Text("Model Gemini", size=13, weight=ft.FontWeight.W_500, color=ink_2),
                                model_dropdown,
                            ], spacing=8),
                            ft.Column([
                                ft.Text("Target foto Excellent", size=13, weight=ft.FontWeight.W_500, color=ink_2),
                                ft.Row([
                                    target_input,
                                    ft.IconButton(ft.icons.REMOVE, on_click=lambda e: step_target(-1)),
                                    ft.IconButton(ft.icons.ADD, on_click=lambda e: step_target(1)),
                                ])
                            ], spacing=8),
                            ft.Column([
                                ft.Text("Folder foto", size=13, weight=ft.FontWeight.W_500, color=ink_2),
                                ft.Row([
                                    ft.ElevatedButton("📁 Pilih folder", on_click=lambda e: folder_dialog.get_directory_path()),
                                    folder_status
                                ])
                            ], spacing=8),
                            ft.Column([
                                ft.Text("Aplikasi editing", size=13, weight=ft.FontWeight.W_500, color=ink_2),
                                editor_dropdown,
                            ], spacing=8),
                        ]
                    )
                ),
                
                ft.Container(
                    padding=24, border_radius=20, bgcolor=glass_2, border=ft.border.all(1, line),
                    content=ft.Column(
                        spacing=14,
                        controls=[
                            ft.Row([
                                ft.Container(width=8, height=8, border_radius=4, bgcolor="#22c55e", shadow=ft.BoxShadow(blur_radius=8, color="#22c55e")),
                                msg_text,
                                pct_text
                            ]),
                            bar
                        ]
                    )
                ),
                
                ft.Row([btn_cancel, btn_start], alignment=ft.MainAxisAlignment.END, spacing=12)
            ]
        )
    )

    # Blobs and Background
    main_stack = ft.Stack([
        ft.Container(expand=True, gradient=ft.LinearGradient([bg1, bg2], begin=ft.alignment.top_left, end=ft.alignment.bottom_right)),
        ft.Container(width=460, height=460, border_radius=230, bgcolor="#4f7bff", filter=ft.Blur(90, 90), left=-140, top=-120, opacity=0.55),
        ft.Container(width=380, height=380, border_radius=190, bgcolor="#ff6bd6", filter=ft.Blur(90, 90), right=-80, top=120, opacity=0.55),
        ft.Container(width=420, height=420, border_radius=210, bgcolor="#8a5cff", filter=ft.Blur(90, 90), left=-60, bottom=-120, opacity=0.55),
        ft.Container(content=card, alignment=ft.alignment.center, expand=True, padding=40)
    ], expand=True)

    page.add(main_stack)

if __name__ == "__main__":
    ft.app(target=main)
