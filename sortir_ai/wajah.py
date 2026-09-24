"""Deteksi wajah lokal (MediaPipe Face Landmarker, CPU): mata terpejam, senyum, mulut canggung.

Hal yang bisa diukur pasti tidak diserahkan ke AI: lebih akurat dan tanpa token.
Hasilnya dipakai sebagai aturan keras (subjek tunggal terpejam -> Bad) dan sebagai
petunjuk yang dikirim ke Gemini untuk foto grup.
"""

import os
import threading
from dataclasses import dataclass, field

import numpy as np

os.environ.setdefault("GLOG_minloglevel", "2")  # redam log MediaPipe di konsol


def _path_model():
    # Juga benar di build PyInstaller selama model dibundel ke sortir_ai/model.
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "model", "face_landmarker.task")


# Ambang blendshape (0..1). Tertawa lebar membuat mata menyipit, jadi senyum
# menaikkan ambang agar ketawa tidak dianggap berkedip.
AMBANG_KEDIP = 0.55
AMBANG_KEDIP_SAAT_SENYUM = 0.80
AMBANG_SENYUM = 0.45
AMBANG_MULUT_TERBUKA = 0.35
MIN_LUAS_WAJAH = 0.004        # fraksi luas gambar; wajah lebih kecil diabaikan
RASIO_WAJAH_UTAMA = 0.25      # wajah >= 25% luas wajah terbesar dihitung "utama"


@dataclass
class InfoWajah:
    jumlah: int = 0                 # wajah utama
    terpejam: int = 0               # wajah utama dengan mata terpejam
    mulut_canggung: int = 0         # mulut terbuka tanpa senyum (sedang bicara/mengunyah)
    senyum: int = 0
    luas_terbesar: float = 0.0      # fraksi luas gambar
    catatan: list = field(default_factory=list)

    def petunjuk(self):
        """Teks singkat untuk Gemini; kosong bila tidak ada wajah."""
        if not self.jumlah:
            return ""
        bagian = [f"{self.jumlah} wajah utama"]
        if self.terpejam:
            bagian.append(f"{self.terpejam} mata terpejam")
        if self.mulut_canggung:
            bagian.append(f"{self.mulut_canggung} mulut canggung")
        if self.senyum:
            bagian.append(f"{self.senyum} tersenyum")
        return "deteksi wajah: " + ", ".join(bagian)

    def untuk_fitur(self):
        return {"wajah": self.jumlah, "terpejam": self.terpejam, "mulut_canggung": self.mulut_canggung,
                "senyum": self.senyum, "luas_wajah": round(self.luas_terbesar, 4)}


_lokal = threading.local()
_tersedia = None


def tersedia():
    global _tersedia
    if _tersedia is None:
        try:
            import mediapipe  # noqa: F401
            _tersedia = os.path.isfile(_path_model())
        except Exception:
            _tersedia = False
    return _tersedia


def _detektor():
    # FaceLandmarker tidak thread-safe: satu instance per thread worker.
    if getattr(_lokal, "detektor", None) is None:
        from mediapipe.tasks.python import BaseOptions, vision
        opsi = vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=_path_model()),
            running_mode=vision.RunningMode.IMAGE,
            num_faces=8,
            output_face_blendshapes=True,
            min_face_detection_confidence=0.5,
        )
        _lokal.detektor = vision.FaceLandmarker.create_from_options(opsi)
    return _lokal.detektor


def nilai_dari_blendshape(bentuk):
    """bentuk: {nama_blendshape: skor}. -> (terpejam, senyum, mulut_canggung)"""
    kedip = (bentuk.get("eyeBlinkLeft", 0) + bentuk.get("eyeBlinkRight", 0)) / 2
    senyum = (bentuk.get("mouthSmileLeft", 0) + bentuk.get("mouthSmileRight", 0)) / 2
    mulut = bentuk.get("jawOpen", 0)
    tersenyum = senyum >= AMBANG_SENYUM
    terpejam = kedip >= (AMBANG_KEDIP_SAAT_SENYUM if tersenyum else AMBANG_KEDIP)
    canggung = mulut >= AMBANG_MULUT_TERBUKA and not tersenyum
    return terpejam, tersenyum, canggung


def analisis_wajah(gambar_rgb):
    """gambar_rgb: PIL.Image RGB (pratinjau). -> InfoWajah"""
    info = InfoWajah()
    if not tersedia():
        return info
    import mediapipe as mp
    larik = np.ascontiguousarray(np.asarray(gambar_rgb.convert("RGB")))
    hasil = _detektor().detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=larik))

    wajah = []
    for titik, bentuk in zip(hasil.face_landmarks, hasil.face_blendshapes):
        xs = [p.x for p in titik]
        ys = [p.y for p in titik]
        luas = max(0.0, min(max(xs), 1) - max(min(xs), 0)) * max(0.0, min(max(ys), 1) - max(min(ys), 0))
        if luas >= MIN_LUAS_WAJAH:
            wajah.append((luas, {b.category_name: b.score for b in bentuk}))
    if not wajah:
        return info

    terbesar = max(l for l, _ in wajah)
    info.luas_terbesar = terbesar
    for luas, bentuk in wajah:
        if luas < RASIO_WAJAH_UTAMA * terbesar:
            continue
        terpejam, senyum, canggung = nilai_dari_blendshape(bentuk)
        info.jumlah += 1
        info.terpejam += terpejam
        info.senyum += senyum
        info.mulut_canggung += canggung
    return info


def gagal_pasti(info: InfoWajah):
    """Aturan keras: subjek tunggal/berdua dengan mata terpejam, atau semua wajah utama terpejam."""
    if not info.jumlah or not info.terpejam:
        return False
    return info.jumlah <= 2 or info.terpejam == info.jumlah
