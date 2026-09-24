"""Sidik jari visual (CLIP ViT-B/32, ONNX, CPU) untuk model selera lanjutan.

Setiap foto -> 512 angka yang merangkum isi visualnya (gaya, warna, pose, suasana).
Dihitung dari pratinjau yang sudah dibuat analisis lokal, disimpan sebagai float16
base64 (~1 KB per foto). Bila model atau onnxruntime tidak ada, semua fungsi diam-diam
mengembalikan kosong: aplikasi tetap berjalan seperti biasa.
"""

import base64
import io
import os
import threading

import numpy as np
from PIL import Image

FILE_MODEL = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "SortirAI", "clip_vision.onnx")
URL_MODEL = "https://huggingface.co/Xenova/clip-vit-base-patch32/resolve/main/onnx/vision_model_quantized.onnx"
UKURAN_MODEL = 89_117_001  # byte; dipakai untuk memastikan unduhan utuh
UKURAN_BATCH = 16

# Normalisasi bawaan CLIP.
_RATA = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32).reshape(3, 1, 1)
_STD = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32).reshape(3, 1, 1)

_sesi = None
_kunci = threading.Lock()


def onnxruntime_ada():
    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        return False
    return True


def model_ada():
    return os.path.exists(FILE_MODEL) and os.path.getsize(FILE_MODEL) == UKURAN_MODEL


def tersedia():
    return model_ada() and onnxruntime_ada()


def unduh_model(progres=lambda persen: None):
    """Unduh model CLIP ke FILE_MODEL (lewat file .part, dicek ukurannya). Error -> exception."""
    import urllib.request
    os.makedirs(os.path.dirname(FILE_MODEL), exist_ok=True)
    sementara = FILE_MODEL + ".part"
    with urllib.request.urlopen(URL_MODEL, timeout=60) as respons, open(sementara, "wb") as f:
        diterima = 0
        while True:
            potongan = respons.read(1 << 20)
            if not potongan:
                break
            f.write(potongan)
            diterima += len(potongan)
            progres(min(100, diterima * 100 // UKURAN_MODEL))
    if os.path.getsize(sementara) != UKURAN_MODEL:
        os.remove(sementara)
        raise IOError("Unduhan tidak utuh; coba lagi.")
    os.replace(sementara, FILE_MODEL)


def _muat_sesi():
    global _sesi
    with _kunci:
        if _sesi is None:
            import onnxruntime as ort
            opsi = ort.SessionOptions()
            opsi.log_severity_level = 3
            _sesi = ort.InferenceSession(FILE_MODEL, opsi, providers=["CPUExecutionProvider"])
    return _sesi


def _siapkan(jpeg_bytes):
    """Resize sisi pendek ke 224 lalu potong tengah 224x224 (seperti CLIP)."""
    g = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
    w, h = g.size
    s = 224 / min(w, h)
    g = g.resize((max(224, round(w * s)), max(224, round(h * s))), Image.Resampling.BICUBIC)
    w, h = g.size
    kiri, atas = (w - 224) // 2, (h - 224) // 2
    g = g.crop((kiri, atas, kiri + 224, atas + 224))
    x = np.asarray(g, dtype=np.float32).transpose(2, 0, 1) / 255.0
    return (x - _RATA) / _STD


def sidik_jari(daftar_pratinjau):
    """list bytes JPEG -> list str base64 (float16, dinormalisasi). Gagal per foto -> None."""
    sesi = _muat_sesi()
    hasil = [None] * len(daftar_pratinjau)
    for mulai in range(0, len(daftar_pratinjau), UKURAN_BATCH):
        indeks, masukan = [], []
        for i in range(mulai, min(mulai + UKURAN_BATCH, len(daftar_pratinjau))):
            try:
                masukan.append(_siapkan(daftar_pratinjau[i]))
                indeks.append(i)
            except Exception:
                continue
        if not masukan:
            continue
        emb = sesi.run(None, {"pixel_values": np.stack(masukan)})[0]
        emb = emb / np.maximum(np.linalg.norm(emb, axis=1, keepdims=True), 1e-6)
        for i, e in zip(indeks, emb):
            hasil[i] = base64.b64encode(e.astype(np.float16).tobytes()).decode("ascii")
    return hasil


def ke_vektor(teks):
    return np.frombuffer(base64.b64decode(teks), dtype=np.float16).astype(np.float32)
