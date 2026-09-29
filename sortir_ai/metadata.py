"""Tulis rating/label XMP tanpa merusak metadata yang sudah ada.

- RAW  -> sidecar .xmp (digabung dengan isi lama; cadangan asli dibuat sekali di folder
  tersembunyi .sortir_backup, dihapus setelah koreksimu dicatat).
- JPEG -> XMP disematkan di segmen APP1 JPEG (lossless: data gambar tidak
  di-encode ulang) karena Lightroom membaca rating JPEG dari dalam file,
  bukan dari sidecar. Sidecar tetap ditulis untuk Capture One / Bridge.
"""

import os
import re
import shutil
import struct

NS_XMP = "http://ns.adobe.com/xap/1.0/"
HEADER_APP1_XMP = NS_XMP.encode("ascii") + b"\x00"
METADATA_STATUS = {"Excellent": ("Green", "3"), "Good": ("", "1"), "Bad": ("", "0")}

PAKET_BARU = """<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:xmp="http://ns.adobe.com/xap/1.0/"
    xmp:Rating="{rating}"
    xmp:Label="{label}"/>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>"""


def _atur_properti(xml, nama, nilai):
    """Set xmp:<nama> dalam bentuk atribut atau elemen; sisipkan bila belum ada."""
    pola_atribut = re.compile(rf'xmp:{nama}\s*=\s*"[^"]*"')
    if pola_atribut.search(xml):
        return pola_atribut.sub(f'xmp:{nama}="{nilai}"', xml, count=1)
    pola_elemen = re.compile(rf"<xmp:{nama}>.*?</xmp:{nama}>|<xmp:{nama}\s*/>", re.S)
    if pola_elemen.search(xml):
        return pola_elemen.sub(f"<xmp:{nama}>{nilai}</xmp:{nama}>", xml, count=1)
    cocok = re.search(r"<rdf:Description\b", xml)
    if not cocok:
        raise ValueError("rdf:Description tidak ditemukan")
    sisip = f' xmp:{nama}="{nilai}"'
    if f'xmlns:xmp="{NS_XMP}"' not in xml:
        sisip = f' xmlns:xmp="{NS_XMP}"' + sisip
    return xml[:cocok.end()] + sisip + xml[cocok.end():]


def gabung_xmp(xml_lama, status, konfig=None):
    """konfig: Konfigurasi (opsional) berisi jumlah bintang & warna label pilihan pengguna."""
    label, rating = konfig.rating_untuk(status) if konfig else METADATA_STATUS[status]
    if not xml_lama or "<rdf:Description" not in xml_lama:
        return PAKET_BARU.format(rating=rating, label=label)
    try:
        xml = _atur_properti(xml_lama, "Rating", rating)
        return _atur_properti(xml, "Label", label)
    except ValueError:
        return PAKET_BARU.format(rating=rating, label=label)


def status_dari_xml(xml, konfig=None):
    m = re.search(r'xmp:Rating\s*=\s*"(-?\d+)"|<xmp:Rating>(-?\d+)</xmp:Rating>', xml or "")
    if not m:
        return None
    rating = int(m.group(1) or m.group(2))
    if konfig:
        return konfig.status_dari_rating(rating)
    return "Excellent" if rating >= 3 else "Good" if rating >= 1 else "Bad"


def _tulis_atomik(path, data, mode="wb"):
    tmp = f"{path}.sortir.tmp"
    with open(tmp, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        f.write(data)
    os.replace(tmp, path)


FOLDER_CADANGAN = ".sortir_backup"
AKHIRAN_LAMA = ".sortir.bak"  # cadangan versi lama, dulu diletakkan di samping foto


def _folder_cadangan(folder, buat=False):
    path = os.path.join(folder, FOLDER_CADANGAN)
    if buat and not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
        if os.name == "nt":
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(path, 0x02)  # FILE_ATTRIBUTE_HIDDEN
    return path


def tulis_sidecar(path_foto, status, konfig=None):
    xmp_path = f"{os.path.splitext(path_foto)[0]}.xmp"
    lama = None
    if os.path.exists(xmp_path):
        with open(xmp_path, "r", encoding="utf-8", errors="replace") as f:
            lama = f.read()
        # Sidecar asli milik Lightroom/C1: simpan sekali, sebelum ditulis pertama kali.
        cadangan = os.path.join(_folder_cadangan(os.path.dirname(xmp_path), buat=True),
                                os.path.basename(xmp_path))
        if not os.path.exists(cadangan):
            shutil.copy2(xmp_path, cadangan)
    _tulis_atomik(xmp_path, gabung_xmp(lama, status, konfig), mode="w")


def rapikan_cadangan_lama(folder):
    """Pindahkan cadangan versi lama (foto.xmp.sortir.bak) ke folder tersembunyi. -> jumlah."""
    pindah = 0
    for nama in os.listdir(folder):
        if not nama.endswith(AKHIRAN_LAMA):
            continue
        tujuan = os.path.join(_folder_cadangan(folder, buat=True), nama[:-len(AKHIRAN_LAMA)])
        asal = os.path.join(folder, nama)
        if os.path.exists(tujuan):
            os.remove(asal)
        else:
            os.replace(asal, tujuan)
        pindah += 1
    return pindah


def hapus_cadangan(folder):
    """Hapus semua cadangan sesi ini (dipanggil setelah koreksimu dicatat). -> jumlah file."""
    jumlah = 0
    path = _folder_cadangan(folder)
    if os.path.isdir(path):
        jumlah += len(os.listdir(path))
        shutil.rmtree(path)
    for nama in os.listdir(folder):
        if nama.endswith(AKHIRAN_LAMA):
            os.remove(os.path.join(folder, nama))
            jumlah += 1
    return jumlah


# ---------------------------------------------------------------------------
# XMP di dalam JPEG (segmen APP1)
# ---------------------------------------------------------------------------
def _segmen_jpeg(data):
    """Daftar (offset, marker, panjang_total) sampai sebelum SOS."""
    if data[:2] != b"\xff\xd8":
        raise ValueError("Bukan file JPEG")
    hasil, pos = [], 2
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            raise ValueError("Struktur JPEG tidak dikenali")
        marker = data[pos + 1]
        if marker == 0xFF:  # padding
            pos += 1
            continue
        if marker == 0xDA:  # SOS: data gambar dimulai, berhenti
            break
        panjang = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        hasil.append((pos, marker, panjang + 2))
        pos += panjang + 2
    return hasil


def baca_xmp_jpeg(data):
    for pos, marker, total in _segmen_jpeg(data):
        isi = data[pos + 4:pos + total]
        if marker == 0xE1 and isi.startswith(HEADER_APP1_XMP):
            return isi[len(HEADER_APP1_XMP):].decode("utf-8", errors="replace")
    return None


def sematkan_xmp_jpeg(data, status, konfig=None):
    segmen = _segmen_jpeg(data)
    xml_lama, lokasi = None, None
    for pos, marker, total in segmen:
        isi = data[pos + 4:pos + total]
        if marker == 0xE1 and isi.startswith(HEADER_APP1_XMP):
            xml_lama, lokasi = isi[len(HEADER_APP1_XMP):].decode("utf-8", errors="replace"), (pos, total)
            break
    payload = HEADER_APP1_XMP + gabung_xmp(xml_lama, status, konfig).encode("utf-8")
    if len(payload) + 2 > 0xFFFF:
        raise ValueError("Paket XMP terlalu besar untuk satu segmen APP1")
    segmen_baru = b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload
    if lokasi:
        pos, total = lokasi
        return data[:pos] + segmen_baru + data[pos + total:]
    # Sisipkan setelah APP0/APP1 (JFIF/EXIF) yang berada di awal.
    sisip = 2
    for pos, marker, total in segmen:
        if marker in (0xE0, 0xE1):
            sisip = pos + total
        else:
            break
    return data[:sisip] + segmen_baru + data[sisip:]


def tulis_jpeg(path_foto, status, konfig=None):
    with open(path_foto, "rb") as f:
        data = f.read()
    baru = sematkan_xmp_jpeg(data, status, konfig)
    if baru == data:
        return
    stat = os.stat(path_foto)
    _tulis_atomik(path_foto, baru)
    os.utime(path_foto, ns=(stat.st_atime_ns, stat.st_mtime_ns))  # jaga urutan tanggal di editor


def tulis_status(path_foto, status, sematkan_jpeg=True, konfig=None):
    tulis_sidecar(path_foto, status, konfig)
    if sematkan_jpeg and os.path.splitext(path_foto)[1].lower() in (".jpg", ".jpeg"):
        tulis_jpeg(path_foto, status, konfig)
