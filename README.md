# Sortir AI

Aplikasi desktop Windows untuk memilih foto terbaik dari satu sesi pemotretan, lalu membuka hasilnya di editor (Capture One, Lightroom, Photoshop). Rating ditulis ke metadata XMP, jadi langsung terbaca di editor.

## Menjalankan

Klik dua kali **`Buka Sortir AI.bat`**. Saat pertama kali dijalankan, aplikasi menyiapkan Python 3.12 dan library-nya di `.venv` (perlu beberapa menit).

Atau lewat terminal:

```bash
.venv\Scripts\python.exe -m sortir_ai
```

Tes:

```bash
.venv\Scripts\python.exe -m pytest -q tests
```

## Alur sortir

1. **Analisis lokal (tanpa token):** ketajaman, exposure, deteksi wajah (mata terpejam, senyum) dengan MediaPipe, dan pengelompokan foto burst yang mirip.
2. **Saring lokal:** foto yang jelas gagal dan file kembar tidak dikirim ke Gemini.
3. **Gemini menilai:** momen, ekspresi, gestur, teknis (0–10), skor 0–100, dan kode cacat. Hasilnya di-cache per folder (`.sortir_ai_cache.json`), jadi token tidak terpakai dua kali.
4. **Babak final:** kandidat teratas diadu ulang supaya Excellent berisi momen terkuat.
5. **Selera pribadi:** urutan kandidat disesuaikan dengan kebiasaan koreksi Anda (lihat di bawah).
6. **Tulis metadata:** Excellent / Good / Bad ditulis ke XMP.

## Model Gemini

- Daftar model di dropdown diambil langsung dari Google sesuai API key Anda.
- Kalau server model sedang penuh (error 503), aplikasi mencoba ulang lalu otomatis pindah ke model cadangan: `gemini-3.5-flash-lite` → `gemini-3.1-flash-lite` → `gemini-flash-lite-latest`.
- Model 2.5 tidak dipakai sebagai cadangan karena tidak bisa dipakai dengan key ini.

## Selera pribadi (belajar dari koreksi)

Setelah sortir, ubah rating di editor sesuai selera Anda, simpan metadata ke file, lalu tekan **Pelajari koreksi**. Aplikasi juga otomatis mencatat koreksi saat folder yang sama disortir ulang.

- Data latihan disimpan di `%APPDATA%\SortirAI\data_latihan.json` (sekitar 1 MB per sesi).
- Model di `sortir_ai/selera.py` adalah regresi ridge kecil (numpy) atas skor Gemini dan ukuran lokal. Model ini tidak melihat foto. Ia belajar aspek mana yang Anda prioritaskan.
- Bonus maksimal **±10 poin**, dan hanya mengubah urutan kandidat Excellent. Batas Good/Bad tidak diubah.
- Mulai aktif di **60 foto** koreksi, lalu pengaruhnya penuh di **400 foto**. Hasil paling stabil tercapai di sekitar 1.000–2.000 foto dari beberapa jenis sesi, kira-kira 3–5 sesi.
- Hanya foto yang sudah dinilai Gemini yang dihitung. Foto yang dibuang oleh saringan lokal tidak ikut.

## Pilihan tersimpan

Model, target Excellent, folder terakhir, dan aplikasi editing disimpan di registry Windows (`HKCU\Software\SortirAI`) dan dipulihkan saat aplikasi dibuka. Dialog "Pilih folder" terbuka di folder induk sesi terakhir.

## Rencana: model selera lanjutan (ditunda)

Sidik jari visual dengan **CLIP**. Model ini bisa menangkap selera yang tidak ada di kolom skor, seperti warna, gaya, dan suasana.

- **Kapan dipasang:** setelah sekitar 5 sesi dikoreksi (1.000+ foto), dan hanya kalau persentase "setuju" di Pelajari koreksi mentok di angka rendah.
- **Bentuk:** fitur opsional. Model sekitar 90–150 MB diunduh hanya saat fitur dinyalakan. Perhitungannya berjalan di CPU, sekitar 1,5–4 menit per 855 foto, dengan RAM sekitar 300–600 MB selama proses.
- **Syarat:** folder sesi yang sudah dikoreksi harus masih ada, karena sidik jarinya dihitung dari foto aslinya.
- Model ini hanya dipakai kalau terbukti lebih akurat daripada model sederhana, diuji dengan data Anda sendiri.

## Struktur

| File | Isi |
|---|---|
| `sortir_ai/tampilan.py` | Antarmuka PySide6 |
| `sortir_ai/inti.py` | Alur sortir, klien Gemini, penentuan status |
| `sortir_ai/analisis.py` | Analisis lokal: ketajaman, exposure, grup mirip |
| `sortir_ai/wajah.py` | Deteksi wajah MediaPipe |
| `sortir_ai/selera.py` | Model selera pribadi |
| `sortir_ai/belajar.py` | Pencatatan koreksi dari XMP |
| `sortir_ai/cache.py` | Cache hasil per folder |
| `sortir_ai/metadata.py` | Baca/tulis XMP |
| `sortir_ai/windows.py` | Deteksi editor, penyimpanan login |
