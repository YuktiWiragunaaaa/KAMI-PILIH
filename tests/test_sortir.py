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
    assert (tmp_path / metadata_xmp.FOLDER_CADANGAN / "x.xmp").read_text(encoding="utf-8") == lama
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

    def nilai(self, batch, prompt=None):
        GeminiTiruan.panggilan += 1
        self.token["panggilan"] += 1
        # Lewatkan ID terakhir di panggilan pertama untuk menguji tanya-ulang.
        ids = range(len(batch) - 1) if GeminiTiruan.panggilan == 1 and len(batch) > 1 else range(len(batch))
        return {i: core.NilaiFoto(id=i, momen=8, ekspresi=8, gestur=7, teknis=8,
                                  skor=90 - i * 5, terbaik_di_grup=True) for i in ids}

    def urutkan(self, kelompok, prompt=None):
        GeminiTiruan.adu += 1
        # Babak final membalik urutan skor: foto dengan nama terakhir dianggap momen terkuat.
        return sorted(range(len(kelompok)), key=lambda i: kelompok[i].nama, reverse=True)


def test_pipeline_ujung_ke_ujung_dengan_cache_dan_belajar(folder, monkeypatch, tmp_path_factory):
    data_dir = tmp_path_factory.mktemp("appdata")
    monkeypatch.setattr(belajar, "FOLDER_DATA", str(data_dir))
    monkeypatch.setattr(belajar, "FILE_DATA", str(data_dir / "data_latihan.json"))
    monkeypatch.setattr(core, "KlienGemini", GeminiTiruan)
    # Gambar uji berupa mozaik acak yang bagi CLIP tampak "sama"; uji jalur dHash di sini,
    # jalur CLIP diuji terpisah dengan vektor terkendali.
    monkeypatch.setattr(core.visual, "tersedia", lambda: False)
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

    # Mode belajar: rating yang sudah ada (pilihan klien) tidak ditimpa, hanya dicatat.
    metadata_xmp.tulis_status(str(folder / "a_tajam.jpg"), "Excellent")
    selesai.clear()
    p.mulai(str(folder), "kunci", 2, "gemini-x-flash", hanya_belajar=True)
    assert selesai.wait(120) and hasil["sukses"], hasil["pesan"]
    assert hasil["pesan"].startswith("Belajar selesai: 6 foto dicatat, 1 berbeda")
    assert baca_status()["a_tajam.jpg"] == "Excellent"


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


def _data_sintetis(n, rng, visual_penentu=False, umur_hari=0):
    """Selera 'momen' (bisa dibaca dari laporan) atau 'arah visual' (hanya ada di sidik jari)."""
    import base64
    import time
    arah = np.zeros(512, dtype=np.float32)
    arah[:8] = 1
    data = {}
    for i in range(n):
        v = rng.normal(size=512).astype(np.float32)
        v /= np.linalg.norm(v)
        momen = int(rng.integers(0, 11))
        nilai = float(v @ arah) * 3 if visual_penentu else (momen - 5) / 2.5
        akhir = "Excellent" if nilai > 0.6 else ("Good" if nilai > -0.6 else "Bad")
        data[f"{umur_hari}|{i}"] = {
            "ai": {"momen": momen, "ekspresi": 5, "gestur": 5, "teknis": 5, "skor": 60},
            "fitur": {"ketajaman": 100}, "akhir": akhir, "prediksi": "Good",
            "visual": base64.b64encode(v.astype(np.float16).tobytes()).decode(),
            "waktu": int(time.time() - umur_hari * 86400),
        }
    return data


def test_selera_visual_hanya_siap_bila_lebih_akurat():
    from sortir_ai import selera
    rng = np.random.default_rng(1)
    assert not selera.uji_visual(_data_sintetis(300, rng, True))["siap"]  # data belum cukup
    visual = selera.uji_visual(_data_sintetis(1200, rng, visual_penentu=True))
    assert visual["siap"] and visual["lebih_baik_persen"] >= 3
    laporan = selera.uji_visual(_data_sintetis(1200, rng, visual_penentu=False))
    assert not laporan["siap"]  # selera sudah terbaca dari kolom: visual tidak diperlukan
    model = selera.latih(_data_sintetis(1200, rng, True), pakai_visual=True)
    assert model.pakai_visual and model.bonus({"momen": 5}, {}, None) == 0.0  # tanpa sidik jari: netral


def test_selera_koreksi_terbaru_lebih_berbobot():
    from sortir_ai import selera
    rng = np.random.default_rng(2)
    lama = _data_sintetis(300, rng, umur_hari=720)          # dulu: suka momen tinggi
    for d in lama.values():
        d["akhir"] = {"Bad": "Excellent", "Excellent": "Bad"}.get(d["akhir"], "Good")  # dibalik
    baru = _data_sintetis(300, rng, umur_hari=0)            # sekarang: suka momen tinggi
    model = selera.latih({**lama, **baru})
    assert model.aspek_terpenting(1)[0] == ("momen", "+")


def test_batas_data_dan_arsip(tmp_path, monkeypatch):
    monkeypatch.setattr(belajar, "FILE_DATA", str(tmp_path / "data.json"))
    monkeypatch.setattr(belajar, "FILE_ARSIP", str(tmp_path / "arsip.json"))
    monkeypatch.setattr(belajar, "FOLDER_DATA", str(tmp_path))
    monkeypatch.setattr(belajar, "MAKS_DATA", 5)
    belajar._simpan({str(i): {"waktu": i, "akhir": "Good", "prediksi": "Good"} for i in range(8)})
    assert sorted(belajar._muat()) == ["3", "4", "5", "6", "7"]  # yang paling lama dibuang
    assert belajar.mulai_selera_baru() == 5 and belajar._muat() == {} and belajar.ada_arsip()
    belajar._simpan({"x": {"waktu": 1, "akhir": "Bad", "prediksi": "Good"}})
    assert belajar.pulihkan_selera_lama() == 5
    assert len(belajar._muat()) == 5 and belajar.pulihkan_selera_lama() == 1  # tukar balik


def test_sidik_jari_visual_nyata():
    from sortir_ai import visual
    if not visual.tersedia():
        pytest.skip("model CLIP belum diunduh")
    def jpeg(warna):
        buf = io.BytesIO()
        Image.new("RGB", (400, 300), warna).save(buf, format="JPEG")
        return buf.getvalue()
    merah, merah2, biru = [visual.ke_vektor(s) for s in visual.sidik_jari([jpeg((220, 30, 30)), jpeg((200, 40, 40)), jpeg((30, 30, 220))])]
    assert merah.shape == (512,)
    assert merah @ merah2 > merah @ biru  # warna mirip -> sidik jari mirip
    assert visual.sidik_jari([b"bukan jpeg"]) == [None]


def test_unduh_model_terputus_ditolak(tmp_path, monkeypatch):
    import urllib.request
    from sortir_ai import visual
    monkeypatch.setattr(visual, "FILE_MODEL", str(tmp_path / "clip.onnx"))
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: io.BytesIO(b"x" * 1000))
    with pytest.raises(IOError):
        visual.unduh_model()
    assert not os.listdir(tmp_path)  # tidak ada file setengah jadi
    assert not visual.model_ada()



def _foto_v(nama, waktu, vektor_dict, v, **wajah):
    info = lokal.InfoFoto(path=nama, nama=nama, kunci=nama, waktu=waktu, ketajaman=wajah.pop("tajam", 100))
    for k, nilai in wajah.items():
        setattr(info.wajah, k, nilai)
    vektor_dict[nama] = np.asarray(v, dtype=np.float32) / np.linalg.norm(v)
    return info


def test_kelompok_clip_pose_berulang_dan_angle_bergantian():
    V = {}
    pose_a, pose_b, lain = [1, 0, 0], [0, 1, 0], [0, 0, 1]
    foto = [
        _foto_v("a1", 0, V, pose_a), _foto_v("b1", 3, V, pose_b),     # fotografer bergantian angle
        _foto_v("a2", 8, V, pose_a), _foto_v("b2", 12, V, pose_b),
        _foto_v("a3", 20, V, [1, 0.05, 0]),                          # pose A diulang 20 detik kemudian
        _foto_v("c1", 25, V, lain),
        _foto_v("a4", 200, V, pose_a),                               # pose A lagi, tapi 3 menit kemudian
    ]
    lokal.kelompokkan(foto, vektor=V)
    grup = {i.nama: i.grup for i in foto}
    assert grup["a1"] == grup["a2"] == grup["a3"]
    assert grup["b1"] == grup["b2"] != grup["a1"]
    assert grup["c1"] not in (grup["a1"], grup["b1"])
    assert grup["a4"] != grup["a1"]  # di luar jendela waktu: grup baru
    # Tanpa sidik jari lengkap: kembali ke cara lama (dHash), tidak error.
    lokal.kelompokkan(foto, vektor={"a1": V["a1"]})


def test_excellent_tidak_boleh_kembar():
    V = {}
    a = _foto_v("a", 0, V, [1, 0, 0])
    a_kembar = _foto_v("a_kembar", 600, V, [1, 0.02, 0])  # pose sama, 10 menit kemudian (beda grup)
    b = _foto_v("b", 900, V, [0, 1, 0])
    for i, g in zip((a, a_kembar, b), (0, 1, 2)):
        i.grup = g
    nilai = {"a": {"skor": 90, "cacat": [], "terbaik": True},
             "a_kembar": {"skor": 88, "cacat": [], "terbaik": True},
             "b": {"skor": 75, "cacat": [], "terbaik": True}}
    status, _ = core.tentukan_status([a, a_kembar, b], nilai, target_excellent=2, vektor=V)
    assert status["a"] == "Excellent" and status["b"] == "Excellent" and status["a_kembar"] == "Good"
    status, _ = core.tentukan_status([a, a_kembar, b], nilai, target_excellent=2)  # tanpa CLIP: perilaku lama
    assert status["a_kembar"] == "Excellent"


def test_prioritas_burst_ekspresi_sebelum_ketajaman():
    V = {}
    tajam_terpejam = _foto_v("tajam_terpejam", 0, V, [1, 0], tajam=200, terpejam=1)
    tawa_agak_lembut = _foto_v("tawa", 1, V, [1, 0], tajam=150, senyum=2)
    datar_tajam = _foto_v("datar", 2, V, [1, 0], tajam=190)
    buram = _foto_v("buram", 3, V, [1, 0], tajam=60, senyum=2)
    urut = [i.nama for i in lokal.prioritas_burst([tajam_terpejam, tawa_agak_lembut, datar_tajam, buram])]
    assert urut == ["tawa", "datar", "buram", "tajam_terpejam"]


def test_cadangan_xmp_tersembunyi_lalu_dibersihkan(tmp_path):
    raw = tmp_path / "IMG_1.RAF"
    raw.write_bytes(b"raw")
    asli = '<x:xmpmeta><rdf:RDF><rdf:Description crs:Crop="1"/></rdf:RDF></x:xmpmeta>'
    (tmp_path / "IMG_1.xmp").write_text(asli, encoding="utf-8")
    (tmp_path / "IMG_2.xmp.sortir.bak").write_text("lama", encoding="utf-8")  # sisa versi lama

    metadata_xmp.tulis_sidecar(str(raw), "Excellent")
    metadata_xmp.tulis_sidecar(str(raw), "Good")  # tulisan kedua tidak menimpa cadangan asli
    cadangan = tmp_path / metadata_xmp.FOLDER_CADANGAN
    assert (cadangan / "IMG_1.xmp").read_text(encoding="utf-8") == asli
    assert 'crs:Crop="1"' in (tmp_path / "IMG_1.xmp").read_text(encoding="utf-8")  # editan lama utuh

    assert metadata_xmp.rapikan_cadangan_lama(str(tmp_path)) == 1
    assert not list(tmp_path.glob("*.sortir.bak")) and (cadangan / "IMG_2.xmp").exists()
    if os.name == "nt":
        import ctypes
        assert ctypes.windll.kernel32.GetFileAttributesW(str(cadangan)) & 0x02  # tersembunyi

    assert metadata_xmp.hapus_cadangan(str(tmp_path)) == 2
    assert not cadangan.exists() and (tmp_path / "IMG_1.xmp").exists()


def test_konfigurasi_bobot_rating_dan_prompt(tmp_path):
    from sortir_ai.konfigurasi import Konfigurasi
    k = Konfigurasi()
    n = {"skor": 50, "momen": 10, "ekspresi": 2, "gestur": 2, "teknis": 2, "tambahan": {"warna": 9}}
    assert k.skor(n) == 50 and k.tanda_prompt() == ""  # bawaan: skor Gemini apa adanya, cache lama tetap berlaku

    k.bobot["momen"] = 3.0  # momen jauh lebih penting: foto bermomen kuat naik
    assert k.skor(n) > 50
    k.bobot["momen"] = 0.2  # momen hampir diabaikan: turun
    assert k.skor(n) < 50
    k.aspek_tambahan = [{"nama": "warna", "bobot": 2.0}]
    assert k.tanda_prompt() != "" and '"warna"' in k.tambahan_prompt()

    k.pakai_preset("Produk")
    assert k.bobot["teknis"] == 2.0 and "produk" in k.catatan.lower()

    # Rating custom: Excellent = 5 bintang ungu, Good = 3, Bad = 1.
    k.rating = {"Excellent": {"bintang": 5, "warna": "Purple"}, "Good": {"bintang": 3, "warna": ""},
                "Bad": {"bintang": 1, "warna": ""}}
    foto = tmp_path / "x.arw"
    foto.write_bytes(b"raw")
    metadata_xmp.tulis_status(str(foto), "Excellent", konfig=k)
    xml = (tmp_path / "x.xmp").read_text(encoding="utf-8")
    assert 'xmp:Rating="5"' in xml and 'xmp:Label="Purple"' in xml
    assert metadata_xmp.status_dari_xml(xml, k) == "Excellent"
    assert k.status_dari_rating(4) == "Excellent" and k.status_dari_rating(2) == "Good"  # seri -> lebih tinggi
    assert k.status_dari_rating(0) == "Bad"

    # Simpan/muat, termasuk nilai liar yang harus dijinakkan.
    k.editor = "Capture One"
    k2 = Konfigurasi.dari_json(k.ke_json())
    assert k2.preset == "Produk" and k2.rating["Excellent"]["bintang"] == 5 and k2.editor == "Capture One"
    # Profil per jenis sesi: kembali ke Umum memulihkan pengaturan Umum yang tadi (aspek warna, momen 0.2).
    k2.pakai_preset("Umum")
    assert k2.aspek_tambahan[0]["nama"] == "warna" and k2.bobot["momen"] == 0.2
    assert k2.rating["Excellent"]["bintang"] == 3 and k2.editor == ""
    k2.pakai_preset("Produk")
    assert k2.editor == "Capture One" and k2.rating["Excellent"]["warna"] == "Purple"
    assert not k2.sama_dengan_bawaan()
    k2.kembalikan_bawaan()
    assert k2.sama_dengan_bawaan() and k2.rating["Excellent"]["bintang"] == 3
    k2.pakai_preset("Umum")
    assert k2.aspek_tambahan  # mengembalikan Produk tidak menyentuh profil Umum
    liar = Konfigurasi.dari_json('{"bobot": {"momen": 99}, "rating": {"Good": {"bintang": 9, "warna": "Pink"}},'
                                 ' "aspek_tambahan": [{"nama": " "}, {"nama": "a"}, {"nama": "b"}, {"nama": "c"}, {"nama": "d"}]}')
    assert liar.bobot["momen"] == 3.0 and liar.rating["Good"] == {"bintang": 5, "warna": ""}
    assert [t["nama"] for t in liar.aspek_tambahan] == ["a", "b", "c"]
    assert Konfigurasi.dari_json("bukan json").preset == "Umum"


def test_laporan_selera_progres_dan_kecocokan():
    from sortir_ai import selera
    rng = np.random.default_rng(3)
    kosong = selera.laporan({})
    assert kosong["dasar"]["progres"] == 0 and kosong["dasar"]["kecocokan"] is None
    data = _data_sintetis(300, rng)  # selera "momen" yang konsisten
    lap = selera.laporan(data)
    assert lap["dasar"]["progres"] == 100 and lap["dasar"]["kecocokan"] >= 70
    assert lap["visual"]["progres"] == 30 and lap["visual"]["kecocokan"] is None  # 300/1000


def test_jenis_sesi_buatan_sendiri():
    from sortir_ai.konfigurasi import Konfigurasi, MAKS_JENIS_KUSTOM
    k = Konfigurasi()
    k.pakai_preset("Wedding")
    k.bobot["teknis"] = 2.5
    k.editor = "Capture One"
    assert k.tambah_jenis("Wisuda") == "Wisuda"          # salinan dari Wedding yang sedang aktif
    assert k.preset == "Wisuda" and k.bobot["teknis"] == 2.5 and k.editor == "Capture One"
    k.bobot["momen"] = 0.5
    assert not k.sama_dengan_bawaan()
    k.kembalikan_bawaan()                                 # kembali ke keadaan saat dibuat
    assert k.bobot["momen"] == 1.5 and k.bobot["teknis"] == 2.5

    k.tambah_jenis("Maternity", salin_aktif=False)        # mulai dari Umum
    assert k.bobot == {"momen": 1.0, "ekspresi": 1.0, "gestur": 1.0, "teknis": 1.0}
    for nama in ("wisuda", "Umum", "", "x" * 30):
        with pytest.raises(ValueError):
            k.tambah_jenis(nama)                          # kembar (tak peka huruf), bawaan, kosong, kepanjangan

    k.ganti_nama_jenis("Wisuda", "Wisuda UNUD")
    assert k.daftar_jenis()[-2:] == ["Wisuda UNUD", "Maternity"]  # urutan tetap
    # Jenis bawaan: hanya nama tampil yang berubah, kunci (dan bobot bawaannya) tetap.
    assert k.ganti_nama_jenis("Wedding", "Nikahan") == "Wedding"
    assert k.nama_tampil("Wedding") == "Nikahan" and "Wedding" in k.daftar_jenis()
    for nama in ("nikahan", "Maternity"):
        with pytest.raises(ValueError):
            k.ganti_nama_jenis("Prewed", nama)            # bentrok dengan nama tampil / jenis lain
    with pytest.raises(ValueError):
        k.tambah_jenis("Wedding")                         # kunci bawaan tetap tidak boleh dipakai
    with pytest.raises(ValueError):
        k.hapus_jenis("Umum")

    k2 = Konfigurasi.dari_json(k.ke_json())               # tersimpan dan termuat utuh
    assert k2.preset == "Maternity" and "Wisuda UNUD" in k2.kustom
    assert k2.nama_tampil("Wedding") == "Nikahan"
    k2.ganti_nama_jenis("Wedding", "Wedding")             # kembalikan nama asli
    assert k2.nama_tampil("Wedding") == "Wedding" and not k2.alias
    k2.pakai_preset("Wisuda UNUD")
    assert k2.bobot["teknis"] == 2.5 and k2.editor == "Capture One"
    k2.hapus_jenis("Wisuda UNUD")                         # menghapus jenis aktif -> kembali ke Umum
    assert k2.preset == "Umum" and "Wisuda UNUD" not in k2.profil

    for i in range(MAKS_JENIS_KUSTOM - len(k2.kustom)):
        k2.tambah_jenis(f"Jenis {i}")
    with pytest.raises(ValueError):
        k2.tambah_jenis("Satu lagi")
