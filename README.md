# Sortir AI

**Aplikasi yang membantu fotografer memilih foto terbaik dari ratusan foto satu sesi secara otomatis.**

Dari satu sesi, misalnya 800 foto, Sortir AI memberi setiap foto salah satu dari tiga label:

- ⭐ **Excellent**: foto terbaik, layak masuk album.
- 👍 **Good**: foto bagus, sebagai pelengkap.
- 👎 **Bad**: blur, mata terpejam, kembar, atau momennya kurang.

Label ini langsung terbaca di **Capture One, Lightroom, atau Photoshop**, jadi Anda cukup membuka editor dan mulai dari foto Excellent.

---

## Syarat

| Kebutuhan | Keterangan |
|---|---|
| **Windows 10 atau 11 (64-bit)** | Aplikasi memakai fitur Windows untuk menyimpan login dan mendeteksi editor |
| **Python 3.12 dari python.org** | Harus versi 3.12 (library tertentu belum mendukung versi lebih baru), dan **jangan dari Microsoft Store**: versi Store membuat logo di taskbar selalu tampil sebagai logo Python |
| **Ruang kosong ±1,5 GB di C:** | Sekitar 1,1 GB untuk library Python, ditambah 89 MB untuk model selera visual |
| **Internet** | Untuk penilaian Gemini dan pemasangan pertama kali |
| **API key Gemini** | Gratis dibuat di [Google AI Studio](https://aistudio.google.com) |
| **Editor foto** *(opsional)* | Capture One, Lightroom, atau Photoshop |

### Memasang Python 3.12

1. Buka [python.org/downloads/windows](https://www.python.org/downloads/windows/), lalu unduh **Windows installer (64-bit)** untuk versi **3.12.x** yang terbaru.
2. Jalankan installer, lalu **centang "Add python.exe to PATH"** di layar pertama.
3. Klik **Install Now**.
4. Untuk mengecek, buka Command Prompt dan ketik `py -0p`. Harus ada baris 3.12 yang **tidak** mengandung `WindowsApps`.

> **Sudah terlanjur memakai Python dari Microsoft Store?** Hapus lewat Settings → Apps → Installed apps → Python 3.12, pasang versi python.org, lalu hapus folder `.venv` dan jalankan `Buka Sortir AI.bat` lagi.

---

## Cara memakai

### Pertama kali

1. Klik dua kali **`Buka Sortir AI.bat`**. File ini otomatis membuat "venv" (folder `.venv`, tempat khusus untuk library aplikasi supaya tidak bercampur dengan program lain) dan memasang semua library yang dibutuhkan. Proses ini butuh **5–15 menit**, tergantung kecepatan internet. Selanjutnya aplikasi langsung terbuka.
2. Buka **Pengaturan** (tombol ⚙ di pojok kanan atas; terbuka otomatis saat pertama kali), tempel **API key Gemini**, lalu klik **Simpan**. Key disimpan aman dan terenkripsi oleh Windows.

<details>
<summary>Membuat venv secara manual (kalau file .bat gagal)</summary>

Buka Command Prompt di folder aplikasi (ketik `cmd` di address bar File Explorer lalu tekan Enter), kemudian jalankan perintah berikut satu per satu:

```bash
py -3.12 -m venv .venv
```

```bash
.venv\Scripts\python.exe -m pip install --upgrade pip
```

```bash
.venv\Scripts\pip install -r requirements.txt
```

Setelah itu, aplikasi bisa dibuka lewat `Buka Sortir AI.bat` atau dengan perintah:

```bash
.venv\Scripts\python.exe -m sortir_ai
```

**Kalau muncul masalah:**
- `py` tidak dikenali: Python belum terpasang, atau "Add to PATH" tidak dicentang. Pasang ulang Python.
- Error saat memasang `mediapipe` atau `onnxruntime`: pastikan venv dibuat dengan Python **3.12**. Hapus folder `.venv`, lalu ulangi dari langkah pertama.
- Ingin memulai dari awal: hapus folder `.venv`, lalu jalankan `.bat` lagi.

</details>

### Setiap sesi foto

1. **Tarik folder sesi** ke kotak besar di atas, atau klik kotaknya untuk memilih. Bisa juga dengan menarik satu foto dari folder itu.
2. Atur **jumlah foto Excellent** yang diinginkan, misalnya 30.
3. Klik **Sortir sekarang →** dan tunggu. Hasilnya langsung tampil, misalnya ★ 30 Excellent · 212 Good · 613 Bad.
4. Klik tombol oranye **Buka di Capture One →** (atau editor pilihan Anda). Setelah sortir selesai, tombol ini ditandai riak lembut sebagai langkah berikutnya. Foto sudah berlabel.

Aplikasi mengingat pilihan terakhir Anda (model, jumlah foto, folder, editor, dan semua pengaturan penilaian), jadi tidak perlu diatur ulang setiap kali.

### Pengaturan penilaian (tombol ⚙)

- **Jenis sesi**: Umum, Wedding, Prewed, Upacara / Oton, Event, atau Produk. **Setiap jenis sesi menyimpan pengaturannya sendiri**: bobot, aspek tambahan, catatan, label, dan editor yang dibuka. Contohnya, Oton bisa memakai Capture One dan Wedding memakai Lightroom. Berganti jenis sesi langsung memuat pengaturan milik jenis sesi itu. **Kembalikan ke bawaan** mengatur ulang hanya jenis sesi yang sedang aktif.
  - **Jenis sesi buatan sendiri:** klik **+ Jenis baru**, beri nama (misalnya "Wisuda"), lalu pilih mulai dari salinan jenis sesi yang aktif atau dari Umum. Klik kanan pada chip untuk **ganti nama** atau **hapus**. Maksimal 12 jenis buatan sendiri, dan enam jenis bawaan tidak bisa dihapus. Untuk jenis buatan sendiri, "Kembalikan ke bawaan" berarti kembali ke keadaan saat jenis itu dibuat.
- **Yang dinilai**: geser slider untuk menentukan seberapa penting momen, ekspresi, gestur, dan teknis (0 sampai 3×). Anda bisa menambah sampai 3 aspek sendiri, misalnya "warna" atau "pencahayaan".
- **Catatan untuk AI**: pesan singkat untuk AI, misalnya "utamakan foto candid".
- **Label di editor**: jumlah bintang (0–5) dan warna label untuk Excellent, Good, dan Bad. Contohnya, Excellent bisa ditulis sebagai 5 bintang ungu.

Mengubah bobot atau label **tidak** memakai token. Menambah aspek atau mengubah catatan membuat foto dinilai ulang oleh AI pada sortir berikutnya.

---

## Aplikasi bisa belajar selera Anda 🎯

Semakin sering dipakai, pilihan aplikasi semakin mirip dengan pilihan Anda sendiri.

**Caranya:**

1. Setelah sortir, buka editor dan **ubah label** yang menurut Anda kurang tepat.
2. Simpan metadata ke file (di Lightroom: Ctrl+S).
3. Kembali ke Sortir AI dan klik **📚 Pelajari koreksi**.

Aplikasi mencatat apa yang Anda ubah dan belajar darinya. Tidak ada biaya tambahan.

**Kapan mulai terasa?**

| Jumlah foto yang sudah Anda koreksi | Hasilnya |
|---|---|
| Kurang dari 60 | Belum berpengaruh |
| 60–400 | Mulai menyesuaikan, perlahan |
| 400 ke atas | Berpengaruh penuh |
| Sekitar 1.000 (±3–5 sesi) | Paling stabil, dan "selera visual" bisa diaktifkan |

Di Pengaturan (⚙) bagian **Selera kamu**, Anda bisa melihat progres data (%) dan seberapa cocok tebakan aplikasi dengan pilihan Anda (%). Angka kecocokan diuji pada foto yang tidak dipakai untuk belajar, jadi bukan angka hafalan.

Pembelajaran selera hanya **mengubah urutan foto terbaik**. Foto yang jelas jelek tidak akan naik menjadi Excellent hanya karena selera.

### Selera visual (tingkat lanjut)

Pembelajaran biasa hanya melihat angka penilaian, seperti skor momen, ekspresi, dan ketajaman. **Selera visual** juga melihat *tampilan* foto: warna, gaya, pose, dan suasana.

- Fitur ini **tidur** dulu. Selama tidur, aplikasi diam-diam mengumpulkan data tanpa mengubah hasil sortir.
- Setelah data cukup dan fitur ini terbukti lebih akurat, muncul pesan dengan tombol **Nyalakan**.
- Sesudah itu, fitur bisa dinyalakan atau dimatikan kapan saja lewat sakelar **Selera visual** di Pengaturan (⚙).

### Kalau selera Anda berubah

- **Berubah pelan-pelan:** tidak perlu melakukan apa pun. Koreksi terbaru selalu dihitung lebih penting daripada koreksi lama.
- **Berubah total:** klik **Mulai selera baru** di Pengaturan (⚙). Selera lama disimpan sebagai cadangan, dan bisa dikembalikan lewat **Tukar dengan arsip**.

---

## Pertanyaan umum

**Berapa biayanya?**
Hanya biaya pemakaian Gemini. Aplikasi menghemat biaya dengan cara:
- membuang foto yang jelas gagal sebelum dikirim ke Gemini, misalnya foto blur atau kembar;
- tidak menilai ulang foto yang sudah pernah dinilai.

**Muncul error "503" atau "high demand"?**
Server Google sedang penuh, bukan masalah di komputer Anda. Aplikasi otomatis mencoba lagi dan pindah ke model cadangan. Kalau tetap gagal, tunggu sebentar lalu klik Sortir sekarang lagi. Foto yang sudah dinilai tidak dihitung ulang.

**Model Gemini mana yang sebaiknya dipilih?**
Model **Flash Lite** paling hemat dan jarang penuh. Hasilnya bagus untuk menyaring foto yang blur, bermata terpejam, atau kembar. Untuk menilai ekspresi yang halus, model ini sedikit kurang tajam, dan di sinilah pembelajaran selera membantu.

**Berapa ruang penyimpanan yang dipakai?**
Paling banyak sekitar **115 MB** di drive C:, dan tidak akan terus bertambah. Rinciannya:
- model selera visual 89 MB;
- data belajar maksimal 5.000 foto terbaru, sekitar 12 MB;
- satu cadangan selera lama, sekitar 12 MB.

Foto asli Anda **tidak disalin**.

**Apakah foto saya diubah?**
Tidak. Aplikasi hanya menambahkan label (rating). Gambar tidak diubah sedikit pun.

**Apa itu folder `.sortir_backup`?**
Sebelum menulis label ke file `.xmp` untuk pertama kali, aplikasi menyimpan salinan `.xmp` asli (berisi editan Capture One/Lightroom Anda) di folder tersembunyi `.sortir_backup` di dalam folder sesi. Folder ini **dihapus otomatis** saat Anda mengklik **Pelajari koreksi**, karena artinya hasil sortir sudah Anda cek di editor. File `.xmp.sortir.bak` dari versi lama otomatis dipindahkan ke folder tersembunyi ini saat folder disortir lagi.

**Bagaimana memakai aplikasi di komputer lain?**
1. Salin folder aplikasi, lalu jalankan `Buka Sortir AI.bat`. Library yang dibutuhkan dipasang otomatis.
2. Untuk selera visual, klik **Unduh model visual (89 MB)** di Pengaturan (⚙).
3. Supaya selera Anda ikut pindah, salin juga file `%APPDATA%\SortirAI\data_latihan.json` dari komputer lama.

**Bolehkah folder sesi lama dihapus?**
Boleh, **setelah** Anda mengklik "Pelajari koreksi" untuk sesi tersebut. Data belajarnya sudah tersimpan terpisah.

---

## Untuk pengembang

<details>
<summary>Detail teknis (klik untuk membuka)</summary>

### Menjalankan dan tes

```bash
.venv\Scripts\python.exe -m sortir_ai
```

Tes butuh `pytest`, yang tidak ikut di `requirements.txt`:

```bash
.venv\Scripts\pip install pytest
```

```bash
.venv\Scripts\python.exe -m pytest -q tests
```

### Alur sortir

1. Analisis lokal: ketajaman, exposure, dHash, dan wajah dengan MediaPipe (mata terpejam, senyum).
2. Saring lokal: file kembar, blur berat, dan burst dipangkas ke 8 frame tertajam.
3. Sidik jari CLIP untuk foto yang lolos (kalau model tersedia).
4. Gemini menilai momen, ekspresi, gestur, teknis (0–10), skor 0–100, dan kode cacat. Hasilnya di-cache per folder di `.sortir_ai_cache.json`.
5. Babak final: kandidat teratas diadu ulang.
6. Bonus selera (±10 poin, hanya untuk urutan kandidat), lalu status ditulis ke XMP.

### Gemini

- Daftar model diambil dari `models.list()` sesuai API key.
- Kalau terjadi 503 setelah 4 kali retry, aplikasi pindah ke model cadangan: `gemini-3.5-flash-lite` → `gemini-3.1-flash-lite` → `gemini-flash-lite-latest`. Model 2.5 tidak tersedia untuk key ini.

### Model selera (`selera.py`)

- **Sederhana:** ridge regression berbobot (numpy) atas 14 kolom, yaitu nilai Gemini ditambah fitur lokal. Aktif mulai 60 baris, kepercayaan penuh di 400.
- **Visual:** 14 kolom ditambah embedding CLIP 512 dimensi, dengan λ lebih besar. Diuji mulai 1.000 baris dengan 5-fold CV terhadap model sederhana pada baris yang sama. Dinyatakan siap kalau galatnya minimal 3% lebih kecil.
- Bobot waktu memakai paruh waktu 180 hari. Target: Bad=0, Good=1, Excellent=2.

### Data

| Lokasi | Isi |
|---|---|
| `%APPDATA%\SortirAI\data_latihan.json` | Data koreksi, maksimal 5.000 baris terbaru |
| `%APPDATA%\SortirAI\data_latihan_arsip.json` | 1 slot arsip selera lama |
| `%APPDATA%\SortirAI\clip_vision.onnx` | CLIP ViT-B/32 quantized, 89.117.001 byte, dari HF `Xenova/clip-vit-base-patch32` |
| `HKCU\Software\SortirAI` | Pilihan UI terakhir dan status selera visual |
| `<folder foto>\.sortir_ai_cache.json` | Nilai Gemini, fitur, dan sidik jari per foto |

### Struktur

| File | Isi |
|---|---|
| `sortir_ai/tampilan.py` | Antarmuka PySide6 |
| `sortir_ai/inti.py` | Alur sortir, klien Gemini, penentuan status |
| `sortir_ai/analisis.py` | Analisis lokal |
| `sortir_ai/wajah.py` | Deteksi wajah MediaPipe |
| `sortir_ai/visual.py` | Sidik jari CLIP (ONNX) dan pengunduh model |
| `sortir_ai/konfigurasi.py` | Jenis sesi, bobot aspek, catatan AI, bintang & warna label |
| `sortir_ai/selera.py` | Model selera sederhana dan visual |
| `sortir_ai/belajar.py` | Pencatatan koreksi, batas data, arsip |
| `sortir_ai/cache.py` | Cache per folder |
| `sortir_ai/metadata.py` | Baca/tulis XMP |
| `sortir_ai/windows.py` | Deteksi editor, penyimpanan login |

</details>
