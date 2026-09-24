"""Model selera pribadi: belajar dari koreksimu di editor, tanpa token dan tanpa melihat foto.

Setiap foto di data latihan punya "laporan" angka (nilai Gemini + ukuran lokal) dan
keputusan akhirmu (Bad/Good/Excellent). Regresi ridge kecil (numpy) mempelajari aspek mana
yang kamu prioritaskan, lalu memberi bonus/penalti poin untuk MENGURUTKAN kandidat.
Batas Good/Bad tidak diubah: selera hanya menggeser siapa yang naik jadi Excellent.
"""

import numpy as np

from . import belajar

# Kolom laporan yang dipakai. Nilai hilang -> 0 setelah standarisasi (netral).
KOLOM_AI = ("momen", "ekspresi", "gestur", "teknis", "skor")
KOLOM_LOKAL = ("ketajaman", "kecerahan", "klip_terang", "klip_gelap",
               "wajah", "terpejam", "mulut_canggung", "senyum", "luas_wajah")
NILAI_STATUS = {"Bad": 0.0, "Good": 1.0, "Excellent": 2.0}

MIN_DATA = 60          # di bawah ini selera belum aktif (terlalu sedikit untuk dipercaya)
DATA_PENUH = 400       # kepercayaan penuh dicapai pada jumlah data ini
BONUS_MAKS = 10        # poin maksimum yang boleh ditambah/dikurangi dari skor 0-100
POIN_PER_STATUS = 15   # selisih 1 tingkat status (mis. Good -> Excellent) setara 15 poin
LAMBDA = 5.0           # kekuatan regularisasi ridge


def _vektor(ai, fitur):
    baris = []
    for k in KOLOM_AI:
        baris.append(float((ai or {}).get(k) or 0))
    for k in KOLOM_LOKAL:
        v = (fitur or {}).get(k)
        baris.append(float(v) if isinstance(v, (int, float, bool)) else 0.0)
    i = len(KOLOM_AI) + KOLOM_LOKAL.index("ketajaman")
    baris[i] = float(np.log1p(max(baris[i], 0.0)))  # ketajaman sangat lebar rentangnya
    return baris


class ModelSelera:
    def __init__(self, bobot, rata, skala, jumlah_data):
        self.bobot, self.rata, self.skala = bobot, rata, skala
        self.jumlah_data = jumlah_data
        self.kepercayaan = min(1.0, jumlah_data / DATA_PENUH)

    def bonus(self, ai, fitur):
        """Poin tambahan (bisa negatif) untuk satu foto."""
        x = (np.array(_vektor(ai, fitur)) - self.rata) / self.skala
        y = float(x @ self.bobot)  # selisih dari rata-rata status, satuan "tingkat status"
        return float(np.clip(y * POIN_PER_STATUS * self.kepercayaan, -BONUS_MAKS, BONUS_MAKS))

    def aspek_terpenting(self, n=3):
        urut = np.argsort(-np.abs(self.bobot))[:n]
        nama = KOLOM_AI + KOLOM_LOKAL
        return [(nama[i], "+" if self.bobot[i] > 0 else "-") for i in urut]


def latih(data=None):
    """-> ModelSelera, atau None bila data belum cukup / tidak bervariasi."""
    data = belajar._muat() if data is None else data
    X, y = [], []
    for d in data.values():
        if not d.get("ai") or d.get("akhir") not in NILAI_STATUS:
            continue  # foto yang dibuang saringan lokal tidak punya laporan Gemini
        X.append(_vektor(d["ai"], d.get("fitur")))
        y.append(NILAI_STATUS[d["akhir"]])
    if len(y) < MIN_DATA or len(set(y)) < 2:
        return None
    X, y = np.array(X), np.array(y)
    rata, skala = X.mean(axis=0), X.std(axis=0)
    skala[skala < 1e-6] = 1.0
    Z = (X - rata) / skala
    yc = y - y.mean()
    bobot = np.linalg.solve(Z.T @ Z + LAMBDA * np.eye(Z.shape[1]), Z.T @ yc)
    return ModelSelera(bobot, rata, skala, len(y))


def bonus_untuk(model, nilai_ai, fitur):
    """{kunci: poin} untuk semua foto yang punya nilai Gemini."""
    if model is None:
        return {}
    return {k: model.bonus(n, fitur.get(k)) for k, n in nilai_ai.items()}
