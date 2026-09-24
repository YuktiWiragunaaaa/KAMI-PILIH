"""Logika inti Sortir AI, bebas dari framework UI.

Alur (hemat token -> akurat):
1. Analisis lokal gratis : pratinjau 768 px tegak, ketajaman, exposure, dHash, deteksi wajah/mata.
2. Saring lokal          : blur berat, gelap/putih total, file kembar, subjek terpejam -> Bad tanpa AI.
3. Grup burst            : frame mirip yang berdekatan waktunya dikirim BERSAMA agar dibandingkan.
4. Gemini memberi nilai  : momen, ekspresi, gestur, teknis (0-10) lalu skor 0-100 + kode cacat.
5. Babak final           : kandidat teratas diadu dalam kelompok kecil ("mana momen terkuat?").
6. Ranking GLOBAL        : Excellent = terbaik se-folder, maksimal 1 per grup, tidak dipaksakan.
7. Cache per folder      : hasil AI disimpan per batch; jalan ulang tidak bayar token lagi.
8. Metadata + belajar    : XMP digabung + disematkan ke JPEG; koreksimu di editor dicatat.

Semua komunikasi ke UI lewat objek `Laporan` (callback dari thread worker).
"""

import hashlib
import json
import os
import random
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Optional

from pydantic import BaseModel, Field

from . import analisis as lokal
from . import belajar, selera
from . import metadata as metadata_xmp
from .analisis import EKSTENSI_JPEG, EKSTENSI_RAW, daftar_foto  # noqa: F401  (dipakai UI)
from .cache import CacheHasil
from .windows import (  # noqa: F401  (diekspor ulang untuk UI)
    KONFIGURASI_EDITOR,
    baca_login,
    buka_editor,
    deteksi_editor,
    hapus_login,
    simpan_login,
)

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------
MODEL_GEMINI_DEFAULT = "gemini-3.6-flash"
MODEL_GEMINI_OPTIONS = ("gemini-3.6-flash", "gemini-3.5-flash-lite")
# Dicoba berurutan bila model pilihan terus 503 (server penuh).
MODEL_GEMINI_CADANGAN = ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-lite-latest")
VERSI_PROMPT = "v3-momen"
MAKS_PER_GRUP = 8          # burst panjang dipangkas ke 8 frame tertajam sebelum ke AI
SKOR_MIN_EXCELLENT = 70
SKOR_MIN_GOOD = 50
SELISIH_KALAH_GRUP = 10    # frame yang kalah >= 10 poin dari saudara terbaiknya -> Bad
SKOR_MAKS_ADA_TERPEJAM = 55  # foto grup dengan sebagian wajah terpejam: boleh Good, bukan Excellent
UKURAN_KELOMPOK_FINAL = 6
BONUS_FINAL = 8            # peringkat 1 di kelompok final +8, terakhir -8
CACAT_FATAL = {"blur", "salah_fokus", "mata_tertutup", "subjek_tertutup"}
KODE_CACAT = (
    "blur", "salah_fokus", "mata_tertutup", "ekspresi_canggung", "terpotong_mengganggu",
    "komposisi_berantakan", "subjek_tertutup", "over_exposure", "under_exposure",
    "noise_berat", "horizon_miring", "latar_mengganggu", "momen_datar",
)


def ukuran_batch_untuk_model(nama_model):
    """Foto per panggilan API. Batch lebih besar = prompt dibayar lebih jarang,
    tapi perhatian model per foto menurun; 12 adalah titik seimbang."""
    return 8 if "pro" in nama_model.lower() else 12


def format_ukuran(byte_count):
    for batas, satuan in ((1000 ** 3, "GB"), (1000 ** 2, "MB"), (1000, "KB")):
        if byte_count >= batas:
            return f"{byte_count / batas:.2f} {satuan}"
    return f"{int(byte_count)} B"


# ---------------------------------------------------------------------------
# Callback ke UI
# ---------------------------------------------------------------------------
def _abaikan(*_args, **_kwargs):
    pass


@dataclass
class Laporan:
    """Kumpulan callback; dipanggil dari thread worker, UI wajib memindahkannya ke thread utama."""

    status: Callable[[str], None] = _abaikan
    progress: Callable[[float], None] = _abaikan
    data: Callable[[str], None] = _abaikan
    peringatan: Callable[[str, str], None] = _abaikan  # (judul, pesan)
    selesai: Callable[[str, bool], None] = _abaikan     # (pesan, sukses)


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------
def _klien(api_key):
    from google import genai
    from google.genai import types
    return genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=180_000))


def daftar_model_vision(api_key):
    """Model Gemini yang mendukung generateContent (untuk dropdown UI)."""
    hasil = []
    klien = _klien(api_key)  # simpan referensi agar klien tidak ditutup saat pager masih dibaca
    for model in klien.models.list():
        nama = (model.name or "").replace("models/", "")
        aksi = model.supported_actions or []
        if "generateContent" not in aksi or not nama.startswith("gemini-"):
            continue
        if any(k in nama for k in ("embedding", "tts", "audio", "live", "native", "image")):
            continue
        hasil.append(nama)
    return sorted(hasil, key=lambda n: ("pro" in n, "flash" not in n, "latest" in n, n))


PROMPT = f"""Kamu editor foto senior yang mengkurasi foto untuk album klien profesional
(wedding, event, portrait, produk). Kamu menerima beberapa foto; tiap foto diawali label
"ID <n> | grup <g>" dan kadang hasil deteksi wajah otomatis. Foto dengan grup sama adalah
burst / frame yang sangat mirip.

Yang paling membedakan foto bagus dari foto biasa adalah MOMEN. Periksa tiap foto:
- momen (0-10): apakah ini puncak kejadian (tawa lepas, pelukan, tatapan, aksi di titik
  tertinggi, reaksi emosional)? 2 = orang menunggu / jeda / sedang bersiap / membelakangi.
- ekspresi (0-10): emosi alami dan jelas? Rendah bila mata setengah terpejam, mulut sedang
  bicara atau mengunyah, senyum kaku, pandangan kosong, atau wajah tertutup tangan/benda.
- gestur (0-10): tangan, postur, dan interaksi terlihat wajar dan terbaca? Rendah bila tangan
  canggung, badan tertutup orang lain, atau subjek saling membelakangi tanpa cerita.
- teknis (0-10): fokus tepat di mata/subjek, exposure, komposisi, latar bersih.
Tanpa manusia (produk, dekorasi, lanskap): momen = kekuatan cerita/detail, ekspresi = 5.

Lalu beri skor akhir 0-100 dengan jangkar KETAT:
- 90-100 hero shot: momen puncak + ekspresi kuat + teknis tepat. Layak cover. Sangat jarang.
- 75-89 sangat bagus: layak satu halaman album; momen jelas, cacat kecil saja.
- 60-74 bagus: teknis benar, momen biasa; pelengkap cerita.
- 40-59 lemah: momen datar/jeda, ekspresi kurang, atau redundan.
- 0-39 buang: cacat fatal.

Aturan wajib:
1. Nilai hanya yang terlihat. Abaikan urutan dan ID.
2. Foto yang teknisnya sempurna tetapi momennya datar TIDAK boleh di atas 65.
3. Mata terpejam/setengah terpejam pada subjek utama, blur gerak, atau salah fokus pada
   subjek = skor maksimal 35. Percayai "deteksi wajah" bila tersedia.
4. Gaya disengaja (siluet, low-key, high-key, backlight, bokeh, grain) BUKAN cacat bila
   subjek dan maksud foto jelas.
5. Jangan murah hati: rata-rata folder normal sekitar 55; 85+ hanya ±1 dari 10 foto.
6. Dalam satu grup, tandai tepat satu terbaik_di_grup=true (momen dan ekspresi terbaik,
   lalu fokus), dan beri frame yang lebih lemah skor lebih rendah.
7. "cacat" hanya boleh berisi kode dari daftar ini yang benar-benar terlihat:
   {", ".join(KODE_CACAT)}.

Keluarkan satu entri untuk SETIAP ID yang dikirim. Isi nilai aspek sebelum skor."""

PROMPT_FINAL = """Kamu editor foto senior yang memilih foto terbaik untuk album klien.
Semua foto berikut sudah lolos seleksi teknis. Urutkan dari yang PALING layak dipilih
ke yang paling tidak, dengan prioritas: 1) kekuatan momen dan emosi, 2) ekspresi dan
gestur, 3) nilai cerita dan keunikan dibanding foto lain, 4) kualitas teknis.
Keluarkan semua ID tepat satu kali di "urutan"."""


class NilaiFoto(BaseModel):
    # Urutan field = urutan pengisian oleh model: aspek dulu, baru skor akhir.
    id: int
    momen: int = Field(ge=0, le=10)
    ekspresi: int = Field(ge=0, le=10)
    gestur: int = Field(ge=0, le=10)
    teknis: int = Field(ge=0, le=10)
    cacat: list[str] = []
    terbaik_di_grup: bool = False
    skor: int = Field(ge=0, le=100)


class UrutanFinal(BaseModel):
    urutan: list[int]


class GagalAI(Exception):
    pass


class KlienGemini:
    """Pembungkus panggilan Gemini: skema JSON terstruktur, retry + backoff,
    fallback konfigurasi bila model menolak parameter tertentu, dan hitung token."""

    def __init__(self, api_key, nama_model, cancel_event):
        from google.genai import types
        self.types = types
        self.klien = _klien(api_key)
        self.nama_model = nama_model
        self.cancel = cancel_event
        self.token = {"input": 0, "output": 0, "thinking": 0, "panggilan": 0}
        self._varian = self._buat_varian_konfig()

    def _buat_varian_konfig(self):
        t = self.types
        dasar = dict(temperature=0.0, seed=7, response_mime_type="application/json", max_output_tokens=4096)
        nama = self.nama_model.lower()
        thinking = None
        if "gemini-3" in nama:
            # Thinking rendah: cukup untuk membandingkan frame tanpa meledakkan token.
            thinking = t.ThinkingConfig(thinking_level=t.ThinkingLevel.LOW)
        elif "2.5" in nama:
            thinking = t.ThinkingConfig(thinking_budget=512 if "lite" in nama else 1024)
        media = t.MediaResolution.MEDIA_RESOLUTION_MEDIUM
        varian = []
        if thinking:
            varian.append(dict(dasar, thinking_config=thinking, media_resolution=media))
        varian.append(dict(dasar, media_resolution=media))
        varian.append(dasar)
        return varian

    def _ganti_model_cadangan(self):
        """Server model penuh (503): pindah ke model cadangan berikutnya yang belum dicoba."""
        self._sudah_dicoba = getattr(self, "_sudah_dicoba", {self.nama_model})
        for nama in MODEL_GEMINI_CADANGAN:
            if nama not in self._sudah_dicoba:
                self._sudah_dicoba.add(nama)
                print(f"{self.nama_model} sibuk, beralih ke {nama}")
                self.nama_model = nama
                self._varian = self._buat_varian_konfig()
                return True
        return False

    def _tunggu(self, detik):
        if self.cancel.wait(detik):
            raise GagalAI("Dibatalkan")

    def _panggil(self, isi, skema):
        from google.genai import errors
        t = self.types
        jeda = (3, 10, 25, 60)
        percobaan = 0
        while True:
            try:
                respons = self.klien.models.generate_content(
                    model=self.nama_model, contents=isi,
                    config=t.GenerateContentConfig(**self._varian[0], response_schema=skema),
                )
                break
            except errors.ClientError as error:
                kode = getattr(error, "code", None)
                if kode == 400 and len(self._varian) > 1:
                    # Model tidak mendukung thinking/media_resolution: turunkan konfigurasi.
                    self._varian.pop(0)
                    continue
                if kode == 429 and percobaan < len(jeda):
                    self._tunggu(jeda[percobaan] * 2)
                    percobaan += 1
                    continue
                raise GagalAI(f"Gemini menolak permintaan ({kode}): {error}") from error
            except GagalAI:
                raise
            except Exception as error:  # ServerError, timeout jaringan, dsb.
                if percobaan >= len(jeda) and self._ganti_model_cadangan():
                    percobaan = 0
                    continue
                if percobaan >= len(jeda):
                    raise GagalAI(f"Gemini tidak merespons: {type(error).__name__}: {error}") from error
                self._tunggu(jeda[percobaan])
                percobaan += 1

        pakai = respons.usage_metadata
        if pakai:
            self.token["input"] += pakai.prompt_token_count or 0
            self.token["output"] += pakai.candidates_token_count or 0
            self.token["thinking"] += pakai.thoughts_token_count or 0
        self.token["panggilan"] += 1
        return respons

    def _isi_gambar(self, prompt, batch, dengan_grup=True):
        t = self.types
        isi = [prompt]
        for i, info in enumerate(batch):
            label = f"ID {i} | grup {info.grup}" if dengan_grup else f"ID {i}"
            petunjuk = info.wajah.petunjuk()
            isi.append(f"{label} | {petunjuk}" if petunjuk else label)
            isi.append(t.Part.from_bytes(data=info.pratinjau, mime_type="image/jpeg"))
        return isi

    def nilai(self, batch):
        """batch: list InfoFoto. -> {indeks_dalam_batch: NilaiFoto}"""
        respons = self._panggil(self._isi_gambar(PROMPT, batch), list[NilaiFoto])
        daftar = respons.parsed
        if not isinstance(daftar, list):
            try:
                daftar = [NilaiFoto(**d) for d in json.loads(respons.text or "[]")]
            except Exception as error:
                raise GagalAI(f"Respons Gemini tidak valid: {error}") from error
        hasil = {}
        for n in daftar:
            if isinstance(n, NilaiFoto) and 0 <= n.id < len(batch):
                n.cacat = [c for c in n.cacat if c in KODE_CACAT]
                hasil.setdefault(n.id, n)
        return hasil

    def urutkan(self, kelompok):
        """kelompok: list InfoFoto. -> list indeks dari terbaik ke terburuk (selalu lengkap)."""
        respons = self._panggil(self._isi_gambar(PROMPT_FINAL, kelompok, dengan_grup=False), UrutanFinal)
        hasil = respons.parsed
        try:
            urutan = hasil.urutan if isinstance(hasil, UrutanFinal) else json.loads(respons.text)["urutan"]
        except Exception:
            urutan = []
        bersih = []
        for i in urutan:
            if isinstance(i, int) and 0 <= i < len(kelompok) and i not in bersih:
                bersih.append(i)
        return bersih + [i for i in range(len(kelompok)) if i not in bersih]


# ---------------------------------------------------------------------------
# Keputusan (murni, mudah diuji)
# ---------------------------------------------------------------------------
def tentukan_status(daftar_info, nilai_ai, target_excellent, bonus=None):
    """daftar_info: semua InfoFoto; nilai_ai: {kunci: {skor, cacat, terbaik, ...}};
    bonus: {kunci: poin dari babak final} (opsional, hanya mengubah urutan kandidat).

    -> ({path: status}, kandidat_excellent_terurut: list InfoFoto)"""
    bonus = bonus or {}
    status = {}
    per_grup = {}
    skor_efektif = {}
    for info in daftar_info:
        n = nilai_ai.get(info.kunci)
        if info.galat or info.alasan_lokal:
            status[info.path] = "Bad"
            continue
        if n is None:
            status[info.path] = "Good"  # tidak sempat dinilai: netral, jangan dibuang
            continue
        skor = n["skor"]
        if info.wajah.terpejam:
            skor = min(skor, SKOR_MAKS_ADA_TERPEJAM)
        skor_efektif[info.path] = skor
        fatal = bool(CACAT_FATAL & set(n["cacat"]))
        status[info.path] = "Bad" if fatal or skor < SKOR_MIN_GOOD else "Good"
        per_grup.setdefault(info.grup, []).append((info, n))

    kandidat = []
    for anggota in per_grup.values():
        anggota.sort(key=lambda x: (skor_efektif[x[0].path] + bonus.get(x[0].kunci, 0),
                                    x[1]["terbaik"], x[0].ketajaman), reverse=True)
        juara = anggota[0][0]
        for info, _ in anggota[1:]:
            if skor_efektif[juara.path] - skor_efektif[info.path] >= SELISIH_KALAH_GRUP:
                status[info.path] = "Bad"  # frame kembar yang jelas kalah
        if status[juara.path] == "Good" and skor_efektif[juara.path] >= SKOR_MIN_EXCELLENT:
            kandidat.append(juara)

    kandidat.sort(key=lambda i: (skor_efektif[i.path] + bonus.get(i.kunci, 0), i.ketajaman), reverse=True)
    for info in kandidat[:target_excellent]:
        status[info.path] = "Excellent"
    return status, kandidat


def susun_batch(daftar_lolos, ukuran):
    """Grup tidak dipecah antar batch agar frame mirip selalu dibandingkan berdampingan."""
    grup = {}
    for info in daftar_lolos:
        grup.setdefault(info.grup, []).append(info)
    batch, sekarang = [], []
    for anggota in grup.values():
        if sekarang and len(sekarang) + len(anggota) > ukuran:
            batch.append(sekarang)
            sekarang = []
        sekarang.extend(anggota)
    if sekarang:
        batch.append(sekarang)
    return batch


def kelompok_final(kandidat, ukuran=UKURAN_KELOMPOK_FINAL):
    """Dua putaran: (1) kandidat kuat dan lemah dicampur merata, (2) diacak tetap (seed).
    Setiap foto diadu dua kali melawan lawan berbeda -> peringkat lebih stabil."""
    n = len(kandidat)
    jumlah = max(1, -(-n // ukuran))
    putaran1 = [kandidat[i::jumlah] for i in range(jumlah)]
    acak = list(kandidat)
    random.Random(7).shuffle(acak)
    putaran2 = [acak[i:i + ukuran] for i in range(0, n, ukuran)]
    return [k for k in putaran1 + putaran2 if len(k) > 1]


def bonus_dari_urutan(kelompok, urutan):
    """Peringkat 1 -> +BONUS_FINAL, terakhir -> -BONUS_FINAL (linear)."""
    n = len(kelompok)
    return {kelompok[i].kunci: BONUS_FINAL * (1 - 2 * posisi / (n - 1)) for posisi, i in enumerate(urutan)}


# ---------------------------------------------------------------------------
# Proses sortir
# ---------------------------------------------------------------------------
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

    def _jalankan(self, *argumen):
        try:
            self._proses(*argumen)
        except GagalAI as error:
            self.laporan.selesai(f"{error}. Hasil yang sudah dinilai tersimpan; jalankan lagi untuk melanjutkan.", False)
        except Exception as error:
            self.laporan.selesai(f"Proses gagal: {type(error).__name__}: {error}", False)

    def _laporan_token(self, gemini, hemat):
        t = gemini.token
        self.laporan.data(
            f"Token: input {t['input']:,} · output {t['output']:,} · thinking {t['thinking']:,}"
            f" · {t['panggilan']} panggilan · {hemat} foto tanpa token (cache/saring lokal)"
        )

    def _proses(self, folder, api_key, target_excellent, nama_model):
        lapor = self.laporan
        semua = daftar_foto(folder)
        if not semua:
            lapor.peringatan("Folder kosong", "Tidak ada file JPEG atau RAW yang didukung di folder tersebut.")
            lapor.selesai("Tidak ada foto untuk diproses.", False)
            return

        cache = CacheHasil(folder, f"{nama_model}|{VERSI_PROMPT}")
        # Folder ini pernah disortir: catat koreksimu di editor SEBELUM rating ditimpa.
        try:
            belajar.kumpulkan_koreksi(folder, cache)
        except Exception as error:
            print(f"Gagal mencatat koreksi: {error}")

        # 1. Analisis lokal paralel
        lapor.status(f"Menganalisis {len(semua)} foto secara lokal (ketajaman, wajah, kemiripan)...")
        daftar_info = []
        with ThreadPoolExecutor(max_workers=min(6, os.cpu_count() or 4)) as pool:
            for i, info in enumerate(pool.map(lokal.analisis, semua, range(len(semua)))):
                daftar_info.append(info)
                if i % 10 == 0:
                    lapor.progress(i / len(semua) * 25)
                if self.cancel_event.is_set():
                    pool.shutdown(cancel_futures=True)
                    lapor.selesai("Proses dibatalkan.", False)
                    return

        # 2. File kembar (isi identik) -> hanya yang pertama dinilai
        terlihat = set()
        for info in daftar_info:
            hash_isi = info.kunci.split("|", 1)[1]
            if hash_isi in terlihat:
                info.alasan_lokal.append("file_kembar")
            terlihat.add(hash_isi)

        # 3. Saring lokal + grup burst + pangkas burst panjang
        lolos = lokal.saring_lokal([i for i in daftar_info if not i.alasan_lokal])
        lokal.kelompokkan(lolos)
        per_grup = {}
        for info in lolos:
            per_grup.setdefault(info.grup, []).append(info)
        dikirim = []
        for anggota in per_grup.values():
            anggota.sort(key=lambda i: i.ketajaman, reverse=True)
            for info in anggota[MAKS_PER_GRUP:]:
                info.alasan_lokal.append("burst_kurang_tajam")
            dikirim.extend(sorted(anggota[:MAKS_PER_GRUP], key=lambda i: i.urutan))

        for info in daftar_info:
            cache.fitur[info.kunci] = {
                "ketajaman": round(info.ketajaman, 1), "kecerahan": round(info.kecerahan, 1),
                "klip_terang": round(info.klip_terang, 3), "klip_gelap": round(info.klip_gelap, 3),
                "lokal": info.alasan_lokal, **info.wajah.untuk_fitur(),
            }

        # 4. Nilai dengan Gemini (lewati yang sudah ada di cache)
        belum = [i for i in dikirim if cache.ambil(i.kunci) is None]
        hemat = len(daftar_info) - len(belum)
        kelompok = susun_batch(belum, ukuran_batch_untuk_model(nama_model))
        gemini = None

        def klien():
            nonlocal gemini
            if gemini is None:
                gemini = KlienGemini(api_key, nama_model, self.cancel_event)
                self._laporan_token(gemini, hemat)
            return gemini

        for indeks, batch in enumerate(kelompok):
            if self.cancel_event.is_set():
                lapor.selesai("Proses dihentikan. Hasil yang sudah dinilai tersimpan di cache.", False)
                return
            lapor.status(f"Gemini menilai momen, batch {indeks + 1} dari {len(kelompok)} ({len(batch)} foto)...")
            lapor.progress(25 + indeks / len(kelompok) * 60)

            hasil = klien().nilai(batch)
            for i, info in enumerate(batch):
                if i in hasil:
                    cache.simpan(info.kunci, hasil[i])
            cache.tulis()  # simpan per batch: gagal di tengah tidak membuang token

            hilang = [info for i, info in enumerate(batch) if i not in hasil]
            if hilang:  # model melewatkan beberapa ID: tanyakan ulang sekali, hanya yang hilang
                ulang = klien().nilai(hilang)
                for j, info in enumerate(hilang):
                    if j in ulang:
                        cache.simpan(info.kunci, ulang[j])
                cache.tulis()
            self._laporan_token(gemini, hemat)

        # 5. Babak final: adu kandidat teratas agar Excellent = momen terkuat
        # Selera pribadi dari koreksi sebelumnya: hanya menggeser urutan kandidat.
        try:
            model_selera = selera.latih()
        except Exception as error:
            print(f"Model selera tidak dipakai: {error}")
            model_selera = None
        bonus_selera = selera.bonus_untuk(model_selera, cache.data, cache.fitur)
        _, kandidat = tentukan_status(daftar_info, cache.data, target_excellent, bonus_selera)
        bonus = {}
        if len(kandidat) > target_excellent:
            finalis = kandidat[:min(len(kandidat), max(2 * target_excellent, target_excellent + 4))]
            tanda = hashlib.sha1("|".join(sorted(i.kunci for i in finalis)).encode()).hexdigest()
            if cache.final.get("tanda") == tanda:
                bonus = cache.final["bonus"]
            else:
                adu = kelompok_final(finalis)
                terkumpul = {}
                for indeks, kel in enumerate(adu):
                    if self.cancel_event.is_set():
                        lapor.selesai("Proses dihentikan. Hasil penilaian tersimpan di cache.", False)
                        return
                    lapor.status(f"Babak final: membandingkan kandidat terbaik ({indeks + 1}/{len(adu)})...")
                    lapor.progress(85 + indeks / len(adu) * 10)
                    for kunci, poin in bonus_dari_urutan(kel, klien().urutkan(kel)).items():
                        terkumpul.setdefault(kunci, []).append(poin)
                    self._laporan_token(gemini, hemat)
                bonus = {k: sum(v) / len(v) for k, v in terkumpul.items()}
                cache.final = {"tanda": tanda, "bonus": bonus}
                cache.tulis()

        # 6. Keputusan global + tulis metadata
        lapor.status("Menentukan pilihan terbaik dan menulis metadata...")
        lapor.progress(96)
        total_bonus = {k: bonus_selera.get(k, 0) + bonus.get(k, 0) for k in set(bonus_selera) | set(bonus)}
        status, kandidat = tentukan_status(daftar_info, cache.data, target_excellent, total_bonus)
        kunci_path = {i.path: i for i in daftar_info}
        jumlah = {"Excellent": 0, "Good": 0, "Bad": 0}
        gagal_tulis = []
        cache.prediksi = {}
        for path, s in status.items():
            try:
                metadata_xmp.tulis_status(path, s)
                jumlah[s] += 1
                cache.prediksi[kunci_path[path].kunci] = {"file": os.path.basename(path), "status": s}
            except Exception as error:
                gagal_tulis.append(f"{os.path.basename(path)}: {error}")
        cache.tulis()
        lapor.progress(100)

        pesan = f"Selesai. Excellent: {jumlah['Excellent']} | Good: {jumlah['Good']} | Bad: {jumlah['Bad']}."
        if len(kandidat) < target_excellent:
            pesan += (f" Hanya {len(kandidat)} foto memenuhi standar Excellent (skor ≥ {SKOR_MIN_EXCELLENT});"
                      " sisanya tidak dipaksakan.")
        if model_selera:
            pesan += f" Selera pribadi aktif ({model_selera.jumlah_data} data koreksi)."
        if gagal_tulis:
            lapor.peringatan("Sebagian metadata gagal ditulis", "\n".join(gagal_tulis[:15]))
        lapor.selesai(pesan, True)
