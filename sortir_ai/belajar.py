"""Kumpulkan koreksimu sebagai data latihan selera pribadi.

Setelah sortir, kamu mengubah rating di Lightroom/Capture One. Rating akhir itu
dibaca kembali dari XMP dan dibandingkan dengan prediksi aplikasi. Setiap foto
menjadi satu baris data (fitur + keputusan akhirmu) di
%APPDATA%\\SortirAI\\data_latihan.json — tersimpan permanen di komputer ini,
dan kelak dipakai untuk melatih model selera lokal.
"""

import json
import os
import time

from . import metadata
from .cache import CacheHasil

FOLDER_DATA = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "SortirAI")
FILE_DATA = os.path.join(FOLDER_DATA, "data_latihan.json")


def baca_status_file(path_foto):
    """Status dari JPEG (XMP tertanam) dan sidecar .xmp. -> list status yang ada."""
    hasil = []
    if os.path.splitext(path_foto)[1].lower() in (".jpg", ".jpeg"):
        try:
            with open(path_foto, "rb") as f:
                hasil.append(metadata.status_dari_xml(metadata.baca_xmp_jpeg(f.read(1024 * 1024))))
        except (OSError, ValueError):
            pass
    try:
        with open(f"{os.path.splitext(path_foto)[0]}.xmp", "r", encoding="utf-8", errors="replace") as f:
            hasil.append(metadata.status_dari_xml(f.read()))
    except OSError:
        pass
    return [s for s in hasil if s]


def _muat():
    try:
        with open(FILE_DATA, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _simpan(data):
    os.makedirs(FOLDER_DATA, exist_ok=True)
    tmp = FILE_DATA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, FILE_DATA)


def kumpulkan_koreksi(folder, cache=None):
    """Baca rating akhir di folder, simpan sebagai data latihan.
    -> (jumlah_foto_tercatat, jumlah_yang_kamu_ubah)"""
    cache = cache or CacheHasil(folder, tanda="")
    if not cache.prediksi:
        return 0, 0
    data = _muat()
    tercatat = diubah = 0
    for kunci, pred in cache.prediksi.items():
        path = os.path.join(folder, pred["file"])
        status_file = baca_status_file(path)
        if not status_file:
            continue
        # Bila JPEG dan sidecar berbeda, ambil yang tidak sama dengan prediksi (itu yang kamu ubah).
        akhir = next((s for s in status_file if s != pred["status"]), pred["status"])
        data[f"{os.path.normcase(os.path.abspath(folder))}|{kunci}"] = {
            "fitur": cache.fitur.get(kunci, {}),
            "ai": cache.data.get(kunci) or cache.hasil_semua.get(kunci),
            "prediksi": pred["status"],
            "akhir": akhir,
            "waktu": int(time.time()),
        }
        tercatat += 1
        diubah += akhir != pred["status"]
    if tercatat:
        _simpan(data)
    return tercatat, diubah


def ringkasan():
    """-> (total_foto, persen_prediksi_yang_kamu_setujui)"""
    data = _muat()
    if not data:
        return 0, None
    setuju = sum(1 for d in data.values() if d["akhir"] == d["prediksi"])
    return len(data), round(100 * setuju / len(data))
