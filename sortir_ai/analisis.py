"""Analisis foto lokal tanpa AI: pratinjau, ketajaman, exposure, hash, dan grup mirip.

Semua di sini gratis (tanpa token) dan dipakai untuk:
- membuang foto yang jelas gagal sebelum dikirim ke Gemini,
- mengelompokkan burst / frame mirip supaya Gemini membandingkannya berdampingan,
- membuat pratinjau kecil yang hemat token.
"""

import hashlib
import io
import os
import struct
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
from PIL import Image, ImageOps

from .metadata import _segmen_jpeg
from .wajah import InfoWajah, analisis_wajah, gagal_pasti

EKSTENSI_JPEG = (".jpg", ".jpeg")
EKSTENSI_RAW = (".arw", ".cr2", ".cr3", ".nef", ".raf", ".orf", ".rw2", ".dng")

# 768 px = satu "tile" gambar Gemini, jadi jauh lebih murah daripada 1280 px
# (yang terpecah jadi beberapa tile) tapi masih cukup untuk menilai fokus mata.
UKURAN_PRATINJAU = 768
KUALITAS_PRATINJAU = 80
UKURAN_METRIK = 384

TAG_DATETIME_ORIGINAL = 36867
TAG_SUBSEC_ORIGINAL = 37521


@dataclass
class InfoFoto:
    path: str
    nama: str
    kunci: str                      # kunci cache: nama + hash ekor file
    pratinjau: Optional[bytes] = None
    ketajaman: float = 0.0
    kecerahan: float = 0.0          # 0..255
    klip_terang: float = 0.0        # fraksi piksel hampir putih
    klip_gelap: float = 0.0         # fraksi piksel hampir hitam
    dhash: int = 0
    waktu: Optional[float] = None   # detik epoch dari EXIF
    urutan: int = 0
    grup: int = -1
    galat: Optional[str] = None
    alasan_lokal: list = field(default_factory=list)
    wajah: InfoWajah = field(default_factory=InfoWajah)


def daftar_foto(folder):
    """JPEG + RAW; RAW yang punya pasangan JPEG (basename sama) tidak dihitung dua kali."""
    semua = os.listdir(folder)
    jpeg = sorted(n for n in semua if os.path.splitext(n)[1].lower() in EKSTENSI_JPEG)
    stem_jpeg = {os.path.splitext(n)[0].lower() for n in jpeg}
    raw = sorted(
        n for n in semua
        if os.path.splitext(n)[1].lower() in EKSTENSI_RAW
        and os.path.splitext(n)[0].lower() not in stem_jpeg
    )
    return [os.path.join(folder, n) for n in jpeg + raw]


def hash_ekor(path, ukuran=64 * 1024):
    """Hash 64 KB terakhir + ukuran data gambar. Ekor file berisi data piksel,
    jadi tidak berubah saat metadata XMP di header JPEG diperbarui."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        awal_data = 0
        if os.path.splitext(path)[1].lower() in EKSTENSI_JPEG:
            # Mulai dari akhir header (sebelum SOS) agar XMP/EXIF tidak ikut di-hash.
            try:
                segmen = _segmen_jpeg(f.read(1024 * 1024))
                if segmen:
                    pos, _, total = segmen[-1]
                    awal_data = pos + total
            except (ValueError, struct.error):
                pass
        f.seek(0, os.SEEK_END)
        panjang = f.tell()
        f.seek(max(awal_data, panjang - ukuran))
        h.update(f.read())
    return h.hexdigest()[:24]


def _waktu_exif(exif):
    try:
        sub = exif.get_ifd(0x8769)
        teks = sub.get(TAG_DATETIME_ORIGINAL) or exif.get(306)
        if not teks:
            return None
        detik = datetime.strptime(str(teks).strip("\x00 "), "%Y:%m:%d %H:%M:%S").timestamp()
        pecahan = str(sub.get(TAG_SUBSEC_ORIGINAL) or "").strip("\x00 ")
        if pecahan.isdigit():
            detik += float(f"0.{pecahan}")
        return detik
    except Exception:
        return None


_ROTASI_RAW = {3: Image.Transpose.ROTATE_180, 5: Image.Transpose.ROTATE_90, 6: Image.Transpose.ROTATE_270}


def _buka_gambar(path):
    """Kembalikan (gambar RGB tegak, waktu_exif). RAW memakai JPEG embedded
    (jauh lebih cepat daripada demosaic) dengan fallback ke decode setengah ukuran."""
    if os.path.splitext(path)[1].lower() in EKSTENSI_RAW:
        import rawpy
        with rawpy.imread(path) as raw:
            flip = raw.sizes.flip
            gambar = None
            try:
                thumb = raw.extract_thumb()
                if thumb.format == rawpy.ThumbFormat.JPEG:
                    gambar = Image.open(io.BytesIO(thumb.data))
                    gambar.load()
                elif thumb.format == rawpy.ThumbFormat.BITMAP:
                    gambar = Image.fromarray(thumb.data)
            except Exception:
                gambar = None
            if gambar is None or max(gambar.size) < UKURAN_PRATINJAU // 2:
                gambar = Image.fromarray(raw.postprocess(use_camera_wb=True, output_bps=8, half_size=True))
                flip = 0  # postprocess sudah memutar sesuai flip
        waktu = None
        try:
            waktu = _waktu_exif(gambar.getexif())
        except Exception:
            pass
        if gambar.getexif().get(0x0112, 1) != 1:
            gambar = ImageOps.exif_transpose(gambar)
        elif flip in _ROTASI_RAW:
            gambar = gambar.transpose(_ROTASI_RAW[flip])
        return gambar.convert("RGB"), waktu

    gambar = Image.open(path)
    # draft(): decoder JPEG langsung men-skala 1/2..1/8 — beberapa kali lebih cepat.
    gambar.draft("RGB", (UKURAN_PRATINJAU * 2, UKURAN_PRATINJAU * 2))
    waktu = _waktu_exif(gambar.getexif())
    gambar = ImageOps.exif_transpose(gambar)  # perbaiki foto portrait yang miring
    return gambar.convert("RGB"), waktu


def _dhash(abu, ukuran=8):
    kecil = np.asarray(abu.resize((ukuran + 1, ukuran), Image.Resampling.BILINEAR), dtype=np.int16)
    bit = (kecil[:, 1:] > kecil[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bit), 2)


def _ketajaman(abu):
    """Varians Laplacian pada 384 px; angka relatif — dibandingkan antar foto se-folder."""
    a = np.asarray(abu, dtype=np.float32)
    lap = a[1:-1, :-2] + a[1:-1, 2:] + a[:-2, 1:-1] + a[2:, 1:-1] - 4 * a[1:-1, 1:-1]
    return float(lap.var())


def analisis(path, urutan=0):
    nama = os.path.basename(path)
    info = InfoFoto(path=path, nama=nama, kunci=f"{nama.lower()}|{hash_ekor(path)}", urutan=urutan)
    try:
        gambar, info.waktu = _buka_gambar(path)
        with gambar:
            pratinjau = gambar.copy()
            pratinjau.thumbnail((UKURAN_PRATINJAU, UKURAN_PRATINJAU), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            pratinjau.save(buf, format="JPEG", quality=KUALITAS_PRATINJAU, optimize=True)
            info.pratinjau = buf.getvalue()

            abu = pratinjau.convert("L")
            abu.thumbnail((UKURAN_METRIK, UKURAN_METRIK), Image.Resampling.BILINEAR)
            piksel = np.asarray(abu)
            info.ketajaman = _ketajaman(abu)
            info.kecerahan = float(piksel.mean())
            info.klip_terang = float((piksel >= 250).mean())
            info.klip_gelap = float((piksel <= 5).mean())
            info.dhash = _dhash(abu)
            try:
                info.wajah = analisis_wajah(pratinjau)
            except Exception as error:  # deteksi wajah opsional; jangan gagalkan foto
                info.wajah.catatan.append(f"wajah gagal: {error}")
    except Exception as error:
        info.galat = f"{type(error).__name__}: {error}"
    return info


def jarak_hash(a, b):
    return (a ^ b).bit_count()


def kelompokkan(daftar, jeda_detik=2.5, batas_hash=14):
    """Grup burst/frame mirip: foto berurutan (waktu EXIF atau urutan nama) yang
    diambil berdekatan DAN tampak mirip menurut dHash."""
    urut = sorted(daftar, key=lambda i: (i.waktu is None, i.waktu or 0, i.urutan))
    grup = -1
    sebelumnya = None
    for info in urut:
        mirip = sebelumnya is not None and jarak_hash(info.dhash, sebelumnya.dhash) <= batas_hash
        if sebelumnya is not None and info.waktu is not None and sebelumnya.waktu is not None:
            dekat = abs(info.waktu - sebelumnya.waktu) <= jeda_detik
        else:
            dekat = sebelumnya is not None and info.urutan - sebelumnya.urutan == 1
        if not (mirip and dekat):
            grup += 1
        info.grup = grup
        sebelumnya = info
    return urut


def saring_lokal(daftar):
    """Tandai foto yang pasti gagal (tanpa perlu AI). Mengembalikan daftar yang lolos.

    Ambang ketajaman relatif terhadap median folder, jadi tidak menghukum
    foto low-key / bokeh yang memang lembut secara keseluruhan."""
    valid = [i for i in daftar if i.galat is None]
    if not valid:
        return []
    median = float(np.median([i.ketajaman for i in valid])) or 1.0
    lolos = []
    for info in valid:
        if info.ketajaman < 0.12 * median:
            info.alasan_lokal.append("blur_berat")
        if info.kecerahan < 12 or info.klip_gelap > 0.85:
            info.alasan_lokal.append("gelap_total")
        if info.kecerahan > 245 or info.klip_terang > 0.70:
            info.alasan_lokal.append("putih_total")
        if gagal_pasti(info.wajah):
            info.alasan_lokal.append("mata_tertutup")
        if not info.alasan_lokal:
            lolos.append(info)
    return lolos
