"""Pengaturan penilaian yang bisa diubah pengguna: jenis sesi (preset), bobot aspek, aspek
tambahan, catatan untuk AI, dan jumlah bintang/warna label yang ditulis ke editor."""

import hashlib
import json
from dataclasses import dataclass, field

ASPEK_INTI = ("momen", "ekspresi", "gestur", "teknis")
STATUS = ("Excellent", "Good", "Bad")
WARNA_LABEL = ("", "Red", "Yellow", "Green", "Blue", "Purple")
MAKS_ASPEK_TAMBAHAN = 3
PORSI_BOBOT = 0.5  # skor akhir = 50% skor Gemini + 50% rata-rata aspek tertimbang (bila bobot diubah)

PRESET = {
    "Umum": ({"momen": 1.0, "ekspresi": 1.0, "gestur": 1.0, "teknis": 1.0}, ""),
    "Wedding": ({"momen": 1.5, "ekspresi": 1.3, "gestur": 1.0, "teknis": 0.8},
                "Utamakan momen emosional pengantin dan keluarga: tatapan, tawa, haru. "
                "Foto detail (cincin, dekorasi) boleh bagus bila bersih dan tajam."),
    "Prewed": ({"momen": 1.0, "ekspresi": 1.4, "gestur": 1.3, "teknis": 1.0},
               "Chemistry pasangan dan pose yang natural lebih penting daripada momen besar. "
               "Hargai komposisi dan cahaya yang indah."),
    "Upacara / Oton": ({"momen": 1.5, "ekspresi": 1.0, "gestur": 1.0, "teknis": 0.9},
                       "Ini dokumentasi upacara adat. Momen ritual penting (pemercikan tirta, persembahan, "
                       "anak bersama keluarga inti) lebih penting daripada pose. Tamu yang tidak terlibat "
                       "kurang penting."),
    "Event": ({"momen": 1.4, "ekspresi": 1.2, "gestur": 1.0, "teknis": 0.9},
              "Cari momen puncak acara dan reaksi orang. Foto suasana ramai yang bercerita juga berharga."),
    "Produk": ({"momen": 0.5, "ekspresi": 0.3, "gestur": 0.3, "teknis": 2.0},
               "Foto produk: nilai ketajaman, cahaya, warna akurat, dan latar bersih. "
               "Momen = kekuatan komposisi."),
}

RATING_BAWAAN = {
    "Excellent": {"bintang": 3, "warna": "Green"},
    "Good": {"bintang": 1, "warna": ""},
    "Bad": {"bintang": 0, "warna": ""},
}


PROFIL_KOLOM = ("bobot", "aspek_tambahan", "catatan", "rating", "editor")
MAKS_JENIS_KUSTOM = 12
MAKS_NAMA_JENIS = 24


def _salin(nilai):
    return json.loads(json.dumps(nilai))


@dataclass
class Konfigurasi:
    """Isi aktif = profil jenis sesi yang sedang dipilih. Setiap jenis sesi menyimpan profilnya
    sendiri di `profil`, jadi berganti jenis sesi tidak menghapus pengaturan jenis lain.
    Jenis sesi buatan pengguna ada di `kustom` beserta "bawaan"-nya (keadaan saat dibuat)."""

    preset: str = "Umum"
    bobot: dict = field(default_factory=lambda: dict(PRESET["Umum"][0]))
    aspek_tambahan: list = field(default_factory=list)  # [{"nama": str, "bobot": float}]
    catatan: str = ""
    rating: dict = field(default_factory=lambda: _salin(RATING_BAWAAN))
    editor: str = ""  # aplikasi editing untuk jenis sesi ini ("" = ikuti pilihan terakhir)
    profil: dict = field(default_factory=dict)  # {nama_jenis: {kolom: nilai}}
    kustom: dict = field(default_factory=dict)  # {nama_jenis_buatan: profil_bawaan}
    alias: dict = field(default_factory=dict)  # {nama_bawaan: nama_tampil} untuk jenis bawaan yang diganti nama

    # ---- simpan / muat ------------------------------------------------------
    def ke_json(self):
        self.simpan_profil()
        return json.dumps(self.__dict__, ensure_ascii=False)

    @classmethod
    def dari_json(cls, teks):
        k = cls()
        try:
            data = json.loads(teks) if teks else {}
        except ValueError:
            return k
        if not isinstance(data, dict):
            return k
        if isinstance(data.get("kustom"), dict):
            for nama, isi in list(data["kustom"].items())[:MAKS_JENIS_KUSTOM]:
                nama = str(nama).strip()[:MAKS_NAMA_JENIS]
                if nama and nama not in PRESET and isinstance(isi, dict):
                    k.kustom[nama] = k._bersihkan("Umum", isi)
        if isinstance(data.get("profil"), dict):
            for nama, isi in data["profil"].items():
                if k.ada_jenis(nama) and isinstance(isi, dict):
                    k.profil[nama] = k._bersihkan(nama, isi)
        if isinstance(data.get("alias"), dict):
            for nama, tampil in data["alias"].items():
                tampil = str(tampil).strip()[:MAKS_NAMA_JENIS]
                if nama in PRESET and tampil and tampil != nama:
                    k.alias[nama] = tampil
        if k.ada_jenis(data.get("preset")):
            k.preset = data["preset"]
        k._muat(k._bersihkan(k.preset, data if "bobot" in data else k.profil.get(k.preset, {})))
        return k

    def _bawaan(self, nama):
        if nama in self.kustom:
            return _salin(self.kustom[nama])
        bobot, catatan = PRESET[nama]
        return {"bobot": dict(bobot), "aspek_tambahan": [], "catatan": catatan,
                "rating": _salin(RATING_BAWAAN), "editor": ""}

    def _bersihkan(self, nama, data):
        """Isi profil dari data mentah; nilai hilang/liar diganti nilai bawaan jenis sesi."""
        p = self._bawaan(nama)
        for a in ASPEK_INTI:
            try:
                p["bobot"][a] = min(3.0, max(0.0, float(data.get("bobot", {}).get(a, p["bobot"][a]))))
            except (TypeError, ValueError, AttributeError):
                pass
        try:
            if "aspek_tambahan" in data:
                p["aspek_tambahan"] = [
                    {"nama": str(t["nama"]).strip()[:30], "bobot": min(3.0, max(0.0, float(t.get("bobot", 1.0))))}
                    for t in data.get("aspek_tambahan", []) if isinstance(t, dict) and str(t.get("nama", "")).strip()
                ][:MAKS_ASPEK_TAMBAHAN]
        except (TypeError, ValueError):
            pass
        if "catatan" in data:
            p["catatan"] = str(data.get("catatan", ""))[:600]
        for s in STATUS:
            r = data.get("rating", {}).get(s, {}) if isinstance(data.get("rating"), dict) else {}
            try:
                p["rating"][s]["bintang"] = min(5, max(0, int(r.get("bintang", p["rating"][s]["bintang"]))))
            except (TypeError, ValueError, AttributeError):
                pass
            if isinstance(r, dict) and r.get("warna", p["rating"][s]["warna"]) in WARNA_LABEL:
                p["rating"][s]["warna"] = r.get("warna", p["rating"][s]["warna"])
        if "editor" in data:
            p["editor"] = str(data.get("editor", ""))[:80]
        return p

    def _muat(self, isi):
        for kolom in PROFIL_KOLOM:
            setattr(self, kolom, _salin(isi[kolom]))

    def simpan_profil(self):
        self.profil[self.preset] = _salin({k: getattr(self, k) for k in PROFIL_KOLOM})

    def pakai_preset(self, nama):
        """Simpan profil jenis sesi sekarang, lalu muat profil `nama` (atau bawaannya bila belum pernah diatur)."""
        self.simpan_profil()
        self.preset = nama
        self._muat(self.profil.get(nama) or self._bawaan(nama))

    def kembalikan_bawaan(self):
        self._muat(self._bawaan(self.preset))
        self.simpan_profil()

    def sama_dengan_bawaan(self):
        b = self._bawaan(self.preset)
        return all(json.dumps(getattr(self, k), sort_keys=True) == json.dumps(b[k], sort_keys=True)
                   for k in PROFIL_KOLOM if k != "editor")

    # ---- jenis sesi buatan pengguna ------------------------------------------
    def daftar_jenis(self):
        return list(PRESET) + list(self.kustom)

    def ada_jenis(self, nama):
        return nama in PRESET or nama in self.kustom

    def nama_tampil(self, nama):
        """Nama yang dilihat pengguna (jenis bawaan bisa diganti nama tanpa mengubah kuncinya)."""
        return self.alias.get(nama, nama)

    def _cek_nama(self, nama, kecuali=None):
        nama = (nama or "").strip()
        if not nama:
            raise ValueError("Nama jenis sesi belum diisi.")
        if len(nama) > MAKS_NAMA_JENIS:
            raise ValueError(f"Nama terlalu panjang (maksimal {MAKS_NAMA_JENIS} huruf).")
        terpakai = {x.lower() for n in self.daftar_jenis() if n != kecuali for x in (n, self.nama_tampil(n))}
        if kecuali not in PRESET:
            terpakai |= {n.lower() for n in PRESET}  # kunci bawaan tidak boleh dipakai jenis buatan
        if nama.lower() in terpakai:
            raise ValueError(f"Jenis sesi \"{nama}\" sudah ada.")
        return nama

    def tambah_jenis(self, nama, salin_aktif=True):
        """Buat jenis sesi baru (salinan jenis aktif atau Umum) lalu jadikan aktif. Error -> ValueError."""
        if len(self.kustom) >= MAKS_JENIS_KUSTOM:
            raise ValueError(f"Maksimal {MAKS_JENIS_KUSTOM} jenis sesi buatan sendiri.")
        nama = self._cek_nama(nama)
        self.simpan_profil()
        awal = _salin({k: getattr(self, k) for k in PROFIL_KOLOM}) if salin_aktif else self._bawaan("Umum")
        self.kustom[nama] = awal
        self.profil[nama] = _salin(awal)
        self.preset = nama
        self._muat(awal)
        return nama

    def ganti_nama_jenis(self, lama, baru):
        """Ganti nama jenis sesi. Jenis bawaan hanya berganti nama tampil (kosong = nama asli).
        -> kunci jenis setelah diganti."""
        if lama in PRESET:
            baru = (baru or "").strip() or lama
            if baru == lama:
                self.alias.pop(lama, None)
            else:
                self.alias[lama] = self._cek_nama(baru, kecuali=lama)
            return lama
        if lama not in self.kustom:
            raise ValueError(f"Jenis sesi \"{lama}\" tidak ada.")
        baru = self._cek_nama(baru, kecuali=lama)
        self.simpan_profil()
        # Pertahankan urutan: bangun ulang dict dengan kunci baru di posisi yang sama.
        self.kustom = {(baru if n == lama else n): v for n, v in self.kustom.items()}
        if lama in self.profil:
            self.profil[baru] = self.profil.pop(lama)
        if self.preset == lama:
            self.preset = baru
        return baru

    def hapus_jenis(self, nama):
        if nama not in self.kustom:
            raise ValueError("Jenis sesi bawaan tidak bisa dihapus.")
        del self.kustom[nama]
        self.profil.pop(nama, None)
        if self.preset == nama:
            self.preset = "Umum"
            self._muat(self.profil.get("Umum") or self._bawaan("Umum"))

    # ---- dipakai penilaian ---------------------------------------------------
    def nama_tambahan(self):
        return [t["nama"] for t in self.aspek_tambahan]

    def tanda_prompt(self):
        """Berubah hanya bila isi prompt berubah (aspek tambahan / catatan). Bobot dan rating
        tidak memengaruhi jawaban Gemini, jadi tidak membuat foto dinilai ulang."""
        if not self.aspek_tambahan and not self.catatan.strip():
            return ""
        isi = json.dumps([self.nama_tambahan(), self.catatan.strip()], ensure_ascii=False)
        return hashlib.sha1(isi.encode("utf-8")).hexdigest()[:10]

    def tambahan_prompt(self):
        bagian = []
        if self.aspek_tambahan:
            daftar = ", ".join(f'"{n}"' for n in self.nama_tambahan())
            bagian.append(
                f"Nilai juga aspek tambahan berikut (0-10) di field \"tambahan\", satu entri per aspek "
                f"dengan nama persis seperti ini: {daftar}.")
        if self.catatan.strip():
            bagian.append("Catatan dari fotografer (ikuti selama tidak bertentangan dengan aturan wajib):\n"
                          + self.catatan.strip())
        return ("\n\n" + "\n\n".join(bagian)) if bagian else ""

    def bobot_netral(self):
        return all(abs(self.bobot[a] - 1.0) < 1e-6 for a in ASPEK_INTI) and not self.aspek_tambahan

    def skor(self, n):
        """Skor akhir 0-100 dari nilai Gemini `n` (dict cache) sesuai bobot pengguna."""
        if self.bobot_netral():
            return n["skor"]
        total = berat = 0.0
        for a in ASPEK_INTI:
            if n.get(a) is not None:
                total += self.bobot[a] * n[a]
                berat += self.bobot[a]
        tambahan = n.get("tambahan") or {}
        for t in self.aspek_tambahan:
            if t["nama"] in tambahan:
                total += t["bobot"] * tambahan[t["nama"]]
                berat += t["bobot"]
        if berat <= 0:
            return n["skor"]
        return round((1 - PORSI_BOBOT) * n["skor"] + PORSI_BOBOT * 10 * total / berat)

    # ---- rating di editor ----------------------------------------------------
    def rating_untuk(self, status):
        r = self.rating[status]
        return r["warna"], str(r["bintang"])

    def status_dari_rating(self, bintang):
        """Bintang di editor -> status terdekat (seri: status yang lebih tinggi)."""
        return min(STATUS, key=lambda s: (abs(self.rating[s]["bintang"] - bintang), STATUS.index(s)))
