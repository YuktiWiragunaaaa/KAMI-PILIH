"""Uji tanpa jaringan: analisis lokal, XMP, keputusan global, dan pipeline dengan Gemini tiruan."""

import io
import os
import shutil
import sys
import threading

import numpy as np
import pytest
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sortir_ai import analisis as lokal  # noqa: E402
from sortir_ai import metadata as metadata_xmp  # noqa: E402
from sortir_ai import inti as core  # noqa: E402
from sortir_ai import belajar, wajah  # noqa: E402


def _gambar(seed, ukuran=(1200, 800)):
    rng = np.random.default_rng(seed)
    kasar = rng.integers(40, 215, (ukuran[1] // 40, ukuran[0] // 40, 3), dtype=np.uint8)
    img = Image.fromarray(kasar).resize(ukuran, Image.Resampling.NEAREST)
    return img


def _simpan(img, path, orientasi=None):
    exif = Image.Exif()
    if orientasi:
        exif[0x0112] = orientasi
    img.save(path, "JPEG", quality=90, exif=exif.tobytes())


@pytest.fixture
def folder(tmp_path):
    _simpan(_gambar(1), tmp_path / "a_tajam.jpg")
    _simpan(_gambar(1).filter(ImageFilter.GaussianBlur(25)), tmp_path / "b_blur.jpg")
    _simpan(Image.new("RGB", (1200, 800), (3, 3, 3)), tmp_path / "c_gelap.jpg")
    shutil.copy(tmp_path / "a_tajam.jpg", tmp_path / "d_kembar.jpg")
    _simpan(_gambar(2), tmp_path / "e_lain.jpg")
    _simpan(_gambar(3), tmp_path / "f_portrait.jpg", orientasi=6)
    return tmp_path


def test_pratinjau_tegak_dan_kecil(folder):
    info = lokal.analisis(str(folder / "f_portrait.jpg"))
    img = Image.open(io.BytesIO(info.pratinjau))
    assert max(img.size) == lokal.UKURAN_PRATINJAU
    assert img.height > img.width  # EXIF orientation 6 diputar jadi portrait


def test_saring_lokal(folder):
    daftar = [lokal.analisis(p, i) for i, p in enumerate(lokal.daftar_foto(str(folder)))]
    lolos = {i.nama for i in lokal.saring_lokal(daftar)}
    alasan = {i.nama: i.alasan_lokal for i in daftar}
    assert "c_gelap.jpg" not in lolos and "gelap_total" in alasan["c_gelap.jpg"]
    assert "b_blur.jpg" not in lolos and "blur_berat" in alasan["b_blur.jpg"]
    assert "a_tajam.jpg" in lolos


def test_kelompok_burst():
    a = lokal.InfoFoto("a", "a", "a", dhash=0b1111, waktu=100.0, urutan=0)
    b = lokal.InfoFoto("b", "b", "b", dhash=0b1110, waktu=100.5, urutan=1)
    c = lokal.InfoFoto("c", "c", "c", dhash=(1 << 63) - 1, waktu=101.0, urutan=2)  # beda jauh
    d = lokal.InfoFoto("d", "d", "d", dhash=(1 << 63) - 1, waktu=500.0, urutan=3)  # jauh waktunya
    lokal.kelompokkan([a, b, c, d])
    assert a.grup == b.grup != c.grup != d.grup


def test_xmp_gabung_tidak_menghapus_data_lama(tmp_path):
    foto = tmp_path / "x.arw"
    foto.write_bytes(b"raw")
    lama = ('<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
            '<rdf:Description rdf:about="" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"'
            ' crs:Exposure2012="+0.50"/></rdf:RDF></x:xmpmeta>')
    (tmp_path / "x.xmp").write_text(lama, encoding="utf-8")
    metadata_xmp.tulis_status(str(foto), "Excellent")
    baru = (tmp_path / "x.xmp").read_text(encoding="utf-8")
    assert 'crs:Exposure2012="+0.50"' in baru
    assert metadata_xmp.status_dari_xml(baru) == "Excellent"
    assert (tmp_path / "x.xmp.sortir.bak").exists()
    metadata_xmp.tulis_status(str(foto), "Bad")  # jalan ulang: ganti, tidak dobel
    baru = (tmp_path / "x.xmp").read_text(encoding="utf-8")
    assert baru.count("xmp:Rating") == 1 and metadata_xmp.status_dari_xml(baru) == "Bad"


def test_jpeg_disematkan_lossless(folder):
    path = str(folder / "e_lain.jpg")
    asli = open(path, "rb").read()
    mtime = os.stat(path).st_mtime_ns
    kunci = lokal.analisis(path).kunci
    metadata_xmp.tulis_status(path, "Excellent")
    metadata_xmp.tulis_status(path, "Good")
    baru = open(path, "rb").read()
    sos = asli.index(b"\xff\xda")
    assert baru.endswith(asli[sos:])                      # data gambar identik byte-per-byte
    assert metadata_xmp.status_dari_xml(metadata_xmp.baca_xmp_jpeg(baru)) == "Good"
    assert baru.count(metadata_xmp.HEADER_APP1_XMP) == 1
    assert os.stat(path).st_mtime_ns == mtime
    assert lokal.analisis(path).kunci == kunci            # cache tetap valid
    Image.open(path).load()                               # masih JPEG valid


def _info(nama, grup, tajam=1.0):
    return lokal.InfoFoto(path=nama, nama=nama, kunci=nama, grup=grup, ketajaman=tajam)


def test_tentukan_status_global_dan_grup():
    infos = [_info("a", 0), _info("b", 0), _info("c", 1), _info("d", 2), _info("e", 3), _info("f", 4)]
    nilai = {
        "a": {"skor": 88, "cacat": [], "terbaik": True},
        "b": {"skor": 72, "cacat": [], "terbaik": False},   # saudara a, kalah 16 poin -> Bad
        "c": {"skor": 80, "cacat": [], "terbaik": True},
        "d": {"skor": 92, "cacat": ["mata_tertutup"], "terbaik": True},  # fatal
        "e": {"skor": 65, "cacat": [], "terbaik": True},    # di bawah ambang Excellent
    }
    status, kandidat = core.tentukan_status(infos, nilai, target_excellent=5)
    assert status == {"a": "Excellent", "b": "Bad", "c": "Excellent", "d": "Bad", "e": "Good", "f": "Good"}
    assert [i.kunci for i in kandidat] == ["a", "c"]
    status, _ = core.tentukan_status(infos, nilai, target_excellent=1)
    assert status["a"] == "Excellent" and status["c"] == "Good"
    # Babak final bisa membalik urutan kandidat yang skornya berdekatan.
    status, _ = core.tentukan_status(infos, nilai, target_excellent=1, bonus={"a": -8, "c": 8})
    assert status["c"] == "Excellent" and status["a"] == "Good"
    # Foto grup dengan sebagian wajah terpejam dibatasi: tidak bisa Excellent.
    infos[2].wajah = wajah.InfoWajah(jumlah=4, terpejam=1)
    status, _ = core.tentukan_status(infos, nilai, target_excellent=5)
    assert status["c"] == "Good"


def test_aturan_wajah():
    kedip = {"eyeBlinkLeft": 0.9, "eyeBlinkRight": 0.8}
    assert wajah.nilai_dari_blendshape(kedip) == (True, False, False)
    # Tertawa lebar: mata menyipit tapi tidak dianggap terpejam.
    ketawa = {"eyeBlinkLeft": 0.65, "eyeBlinkRight": 0.7, "mouthSmileLeft": 0.8, "mouthSmileRight": 0.8,
              "jawOpen": 0.5}
    assert wajah.nilai_dari_blendshape(ketawa) == (False, True, False)
    bicara = {"jawOpen": 0.5}
    assert wajah.nilai_dari_blendshape(bicara) == (False, False, True)
    assert wajah.gagal_pasti(wajah.InfoWajah(jumlah=1, terpejam=1))
    assert not wajah.gagal_pasti(wajah.InfoWajah(jumlah=6, terpejam=1))  # foto grup: petunjuk saja
    assert wajah.gagal_pasti(wajah.InfoWajah(jumlah=3, terpejam=3))
    assert wajah.tersedia()


def test_kelompok_final_setiap_foto_diadu_dua_kali():
    kandidat = [_info(str(i), i) for i in range(10)]
    kelompok = core.kelompok_final(kandidat, ukuran=4)
    hitung = {}
    for kel in kelompok:
        assert 2 <= len(kel) <= 4
        for info in kel:
            hitung[info.kunci] = hitung.get(info.kunci, 0) + 1
    assert all(v == 2 for v in hitung.values()) and len(hitung) == 10
    bonus = core.bonus_dari_urutan(kelompok[0], list(range(len(kelompok[0]))))
    nilai = list(bonus.values())
    assert nilai[0] == core.BONUS_FINAL and nilai[-1] == -core.BONUS_FINAL


def test_susun_batch_tidak_memecah_grup():
    infos = [_info(str(i), g) for i, g in enumerate([0, 0, 0, 1, 1, 1, 1, 2, 3])]
    for batch in core.susun_batch(infos, 5):
        grup = [i.grup for i in batch]
        assert len(batch) <= 5
    semua_grup = [[i.grup for i in b] for b in core.susun_batch(infos, 5)]
    assert all(sum(g == 1 for g in b) in (0, 4) for b in semua_grup)


class GeminiTiruan:
    panggilan = 0
    adu = 0

    def __init__(self, api_key, nama_model, cancel_event):
        self.token = {"input": 0, "output": 0, "thinking": 0, "panggilan": 0}

    def nilai(self, batch):
        GeminiTiruan.panggilan += 1
        self.token["panggilan"] += 1
        # Lewatkan ID terakhir di panggilan pertama untuk menguji tanya-ulang.
        ids = range(len(batch) - 1) if GeminiTiruan.panggilan == 1 and len(batch) > 1 else range(len(batch))
        return {i: core.NilaiFoto(id=i, momen=8, ekspresi=8, gestur=7, teknis=8,
                                  skor=90 - i * 5, terbaik_di_grup=True) for i in ids}

    def urutkan(self, kelompok):
        GeminiTiruan.adu += 1
        # Babak final membalik urutan skor: foto dengan nama terakhir dianggap momen terkuat.
        return sorted(range(len(kelompok)), key=lambda i: kelompok[i].nama, reverse=True)


def test_pipeline_ujung_ke_ujung_dengan_cache_dan_belajar(folder, monkeypatch, tmp_path_factory):
    data_dir = tmp_path_factory.mktemp("appdata")
    monkeypatch.setattr(belajar, "FOLDER_DATA", str(data_dir))
    monkeypatch.setattr(belajar, "FILE_DATA", str(data_dir / "data_latihan.json"))
    monkeypatch.setattr(core, "KlienGemini", GeminiTiruan)
    GeminiTiruan.panggilan = GeminiTiruan.adu = 0
    hasil = {}
    selesai = threading.Event()

    def akhir(pesan, sukses):
        hasil.update(pesan=pesan, sukses=sukses)
        selesai.set()

    def jalankan():
        selesai.clear()
        p.mulai(str(folder), "kunci", 2, "gemini-x-flash")
        assert selesai.wait(120)
        assert hasil["sukses"], hasil["pesan"]

    def baca_status():
        return {os.path.basename(f): metadata_xmp.status_dari_xml(metadata_xmp.baca_xmp_jpeg(open(f, "rb").read()))
                for f in lokal.daftar_foto(str(folder))}

    p = core.PenyortirFoto(core.Laporan(selesai=akhir))
    jalankan()
    assert GeminiTiruan.panggilan == 2  # 1 batch + 1 tanya-ulang ID yang hilang
    assert GeminiTiruan.adu == 2        # 3 finalis untuk target 2: dua putaran adu

    status = baca_status()
    assert status["c_gelap.jpg"] == "Bad" and status["b_blur.jpg"] == "Bad" and status["d_kembar.jpg"] == "Bad"
    # Skor awal a > e > f, tetapi babak final membalik: f dan e terpilih.
    assert status["f_portrait.jpg"] == "Excellent" and status["e_lain.jpg"] == "Excellent"
    assert status["a_tajam.jpg"] == "Good"

    # Kamu mengoreksi di editor: a_tajam dinaikkan jadi Excellent.
    metadata_xmp.tulis_status(str(folder / "a_tajam.jpg"), "Excellent")
    assert belajar.kumpulkan_koreksi(str(folder)) == (6, 1)
    total, setuju = belajar.ringkasan()
    assert total == 6 and setuju == 83

    # Jalan ulang: semua dari cache (termasuk babak final), 0 panggilan API.
    jalankan()
    assert GeminiTiruan.panggilan == 2 and GeminiTiruan.adu == 2


def test_selera_belajar_prioritas_momen():
    from sortir_ai import selera
    rng = np.random.default_rng(0)
    data = {}
    for i in range(200):
        momen, komposisi = rng.integers(0, 11), rng.integers(0, 11)
        akhir = "Excellent" if momen >= 8 else ("Good" if momen >= 4 else "Bad")
        data[str(i)] = {"ai": {"momen": momen, "ekspresi": 5, "gestur": 5, "teknis": komposisi, "skor": 60},
                        "fitur": {"ketajaman": 100}, "akhir": akhir, "prediksi": "Good"}
    model = selera.latih(data)
    assert model is not None
    assert model.aspek_terpenting(1)[0] == ("momen", "+")
    tinggi = model.bonus({"momen": 10, "teknis": 3, "skor": 60}, {"ketajaman": 100})
    rendah = model.bonus({"momen": 2, "teknis": 10, "skor": 60}, {"ketajaman": 100})
    assert tinggi > 0 > rendah and abs(tinggi) <= selera.BONUS_MAKS
    assert selera.latih({k: data[k] for k in list(data)[:10]}) is None  # data belum cukup
