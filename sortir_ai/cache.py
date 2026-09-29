"""Cache per folder foto (.sortir_ai_cache.json).

Isi:
- hasil    : penilaian Gemini per foto (dipakai ulang -> tidak bayar token dua kali)
- fitur    : ukuran lokal per foto (ketajaman, wajah, ...) untuk data latihan
- final    : hasil babak final (adu kandidat) + tanda kandidatnya
- visual   : sidik jari CLIP per foto (base64 float16), untuk selera lanjutan
- prediksi : status yang terakhir ditulis aplikasi, untuk mendeteksi koreksimu di editor
"""

import json
import os

FILE_CACHE = ".sortir_ai_cache.json"


class CacheHasil:
    def __init__(self, folder, tanda):
        self.path = os.path.join(folder, FILE_CACHE)
        self.tanda = tanda
        self.data = {}
        self.fitur = {}
        self.final = {}
        self.prediksi = {}
        self.hasil_semua = {}
        self.visual = {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                isi = json.load(f)
        except (OSError, ValueError):
            return
        # Prediksi lama tetap berguna untuk belajar walau model/prompt berganti.
        self.prediksi = isi.get("prediksi", {})
        self.fitur = isi.get("fitur", {})
        self.visual = isi.get("visual", {})  # tidak bergantung model/prompt Gemini
        # Nilai Gemini dari versi model/prompt mana pun: tetap berguna sebagai data latihan selera.
        self.hasil_semua = isi.get("hasil", {})
        if isi.get("tanda") == tanda:
            self.data = isi.get("hasil", {})
            self.final = isi.get("final", {})

    def ambil(self, kunci):
        return self.data.get(kunci)

    def simpan(self, kunci, nilai):
        self.data[kunci] = {
            "skor": nilai.skor, "momen": nilai.momen, "ekspresi": nilai.ekspresi,
            "gestur": nilai.gestur, "teknis": nilai.teknis,
            "cacat": nilai.cacat, "terbaik": nilai.terbaik_di_grup,
            "tambahan": {t.nama: t.nilai for t in getattr(nilai, "tambahan", None) or []},
        }

    def tulis(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"tanda": self.tanda, "hasil": self.data, "fitur": self.fitur,
                       "final": self.final, "prediksi": self.prediksi, "visual": self.visual}, f)
        os.replace(tmp, self.path)
