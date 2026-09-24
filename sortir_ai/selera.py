"""Model selera pribadi: belajar dari koreksimu di editor, tanpa token.

Dua tingkat, keduanya regresi ridge kecil (numpy) atas keputusan akhirmu (Bad/Good/Excellent):
- sederhana : "laporan" angka tiap foto (nilai Gemini + ukuran lokal). Tidak melihat foto;
              belajar aspek mana yang kamu prioritaskan.
- visual    : laporan yang sama + sidik jari CLIP 512 angka (lihat visual.py), sehingga bisa
              menangkap selera yang tidak punya kolom (warna, gaya, suasana). Tidur sampai
              terbukti lebih akurat pada datamu sendiri, lalu diaktifkan lewat sakelar di UI.

Koreksi terbaru lebih berbobot (paruh waktu WAKTU_PARUH_HARI), jadi bila seleramu berubah,
model ikut bergeser tanpa perlu reset. Hasilnya hanya bonus/penalti poin untuk MENGURUTKAN
kandidat; batas Good/Bad tidak diubah.
"""

import time

import numpy as np

from . import belajar

# Kolom laporan yang dipakai. Nilai hilang -> 0 (netral setelah standarisasi).
KOLOM_AI = ("momen", "ekspresi", "gestur", "teknis", "skor")
KOLOM_LOKAL = ("ketajaman", "kecerahan", "klip_terang", "klip_gelap",
               "wajah", "terpejam", "mulut_canggung", "senyum", "luas_wajah")
NILAI_STATUS = {"Bad": 0.0, "Good": 1.0, "Excellent": 2.0}

MIN_DATA = 60            # di bawah ini selera sederhana belum aktif
DATA_PENUH = 400         # kepercayaan penuh model sederhana
MIN_DATA_VISUAL = 1000   # model visual baru diuji mulai jumlah ini
SYARAT_LEBIH_BAIK = 0.03  # visual harus >= 3% lebih akurat daripada sederhana
BONUS_MAKS = 10          # poin maksimum yang boleh ditambah/dikurangi dari skor 0-100
POIN_PER_STATUS = 15     # selisih 1 tingkat status setara 15 poin
LAMBDA = 5.0
LAMBDA_VISUAL = 40.0     # 526 kolom: regularisasi lebih kuat agar tidak menghafal
WAKTU_PARUH_HARI = 180   # bobot koreksi turun setengah tiap ~6 bulan


def _vektor(ai, fitur):
    baris = [float((ai or {}).get(k) or 0) for k in KOLOM_AI]
    for k in KOLOM_LOKAL:
        v = (fitur or {}).get(k)
        baris.append(float(v) if isinstance(v, (int, float, bool)) else 0.0)
    i = len(KOLOM_AI) + KOLOM_LOKAL.index("ketajaman")
    baris[i] = float(np.log1p(max(baris[i], 0.0)))  # ketajaman sangat lebar rentangnya
    return baris


def _vektor_lengkap(ai, fitur, vis, pakai_visual):
    x = _vektor(ai, fitur)
    if pakai_visual:
        from .visual import ke_vektor
        x = x + list(ke_vektor(vis))
    return x


def _ridge(Z, y, w, lam):
    """Ridge berbobot pada Z yang sudah distandarkan. -> (bobot, intercept)."""
    w = w / w.sum()
    rata_y = float(w @ y)
    Zw = Z * w[:, None]
    koef = np.linalg.solve(Z.T @ Zw + lam / len(y) * np.eye(Z.shape[1]), Zw.T @ (y - rata_y))
    return koef, rata_y


class ModelSelera:
    def __init__(self, bobot, rata, skala, jumlah_data, pakai_visual=False):
        self.bobot, self.rata, self.skala = bobot, rata, skala
        self.jumlah_data = jumlah_data
        self.pakai_visual = pakai_visual
        self.kepercayaan = 1.0 if pakai_visual else min(1.0, jumlah_data / DATA_PENUH)

    def bonus(self, ai, fitur, vis=None):
        """Poin tambahan (bisa negatif) untuk satu foto."""
        if self.pakai_visual and not vis:
            return 0.0  # foto tanpa sidik jari: netral
        x = (np.array(_vektor_lengkap(ai, fitur, vis, self.pakai_visual)) - self.rata) / self.skala
        y = float(x @ self.bobot)  # selisih dari rata-rata status, satuan "tingkat status"
        return float(np.clip(y * POIN_PER_STATUS * self.kepercayaan, -BONUS_MAKS, BONUS_MAKS))

    def aspek_terpenting(self, n=3):
        """Hanya kolom bernama (sidik jari visual tidak bisa dibaca manusia)."""
        nama = KOLOM_AI + KOLOM_LOKAL
        b = self.bobot[:len(nama)]
        return [(nama[i], "+" if b[i] > 0 else "-") for i in np.argsort(-np.abs(b))[:n]]


def _siapkan_data(data, pakai_visual):
    X, y, umur = [], [], []
    sekarang = time.time()
    for d in data.values():
        if not d.get("ai") or d.get("akhir") not in NILAI_STATUS:
            continue  # foto yang dibuang saringan lokal tidak punya laporan Gemini
        if pakai_visual and not d.get("visual"):
            continue
        X.append(_vektor_lengkap(d["ai"], d.get("fitur"), d.get("visual"), pakai_visual))
        y.append(NILAI_STATUS[d["akhir"]])
        umur.append(max(0.0, sekarang - d.get("waktu", sekarang)) / 86400)
    if not y:
        return None
    w = 0.5 ** (np.array(umur) / WAKTU_PARUH_HARI)
    return np.array(X), np.array(y), w


def _latih_array(X, y, w, pakai_visual):
    rata, skala = X.mean(axis=0), X.std(axis=0)
    skala[skala < 1e-6] = 1.0
    koef, _ = _ridge((X - rata) / skala, y, w, LAMBDA_VISUAL if pakai_visual else LAMBDA)
    return ModelSelera(koef, rata, skala, len(y), pakai_visual)


def latih(data=None, pakai_visual=False):
    """-> ModelSelera, atau None bila data belum cukup / tidak bervariasi."""
    data = belajar._muat() if data is None else data
    siap = _siapkan_data(data, pakai_visual)
    if siap is None:
        return None
    X, y, w = siap
    if len(y) < (MIN_DATA_VISUAL if pakai_visual else MIN_DATA) or len(set(y)) < 2:
        return None
    return _latih_array(X, y, w, pakai_visual)


def _galat_cv(X, y, w, pakai_visual, lipatan=5):
    """Galat kuadrat rata-rata berbobot dengan validasi silang (urutan acak tetap)."""
    idx = np.random.default_rng(7).permutation(len(y))
    total = bobot = 0.0
    for k in range(lipatan):
        uji = idx[k::lipatan]
        latih_ = np.setdiff1d(idx, uji)
        m = _latih_array(X[latih_], y[latih_], w[latih_], pakai_visual)
        tebak = ((X[uji] - m.rata) / m.skala) @ m.bobot + float(w[latih_] @ y[latih_] / w[latih_].sum())
        total += float(w[uji] @ (y[uji] - tebak) ** 2)
        bobot += float(w[uji].sum())
    return total / bobot


def uji_visual(data=None):
    """Bandingkan model visual vs sederhana pada foto yang punya sidik jari.
    -> dict {siap, jumlah, lebih_baik_persen} ; siap=False bila data belum cukup/tidak lebih baik."""
    data = belajar._muat() if data is None else data
    dv = _siapkan_data(data, True)
    jumlah = 0 if dv is None else len(dv[1])
    hasil = {"siap": False, "jumlah": jumlah, "lebih_baik_persen": None}
    if jumlah < MIN_DATA_VISUAL or len(set(dv[1])) < 2:
        return hasil
    # Model sederhana diuji pada foto yang SAMA agar adil.
    dengan_visual = {k: d for k, d in data.items() if d.get("visual")}
    ds = _siapkan_data(dengan_visual, False)
    galat_s = _galat_cv(*ds, pakai_visual=False)
    galat_v = _galat_cv(*dv, pakai_visual=True)
    lebih_baik = 1 - galat_v / galat_s if galat_s > 0 else 0.0
    hasil["lebih_baik_persen"] = round(100 * lebih_baik)
    hasil["siap"] = lebih_baik >= SYARAT_LEBIH_BAIK
    return hasil


def bonus_untuk(model, nilai_ai, fitur, visual=None):
    """{kunci: poin} untuk semua foto yang punya nilai Gemini."""
    if model is None:
        return {}
    visual = visual or {}
    return {k: model.bonus(n, fitur.get(k), visual.get(k)) for k, n in nilai_ai.items()}
