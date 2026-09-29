"""Sortir AI — kurasi foto otomatis dengan Gemini."""

import os

# OpenBLAS bawaan numpy memakai semua inti CPU; untuk matriks kecil (model selera ~500x500)
# thread yang saling berebut membuatnya ~35x lebih lambat. Harus diatur sebelum numpy diimpor.
_inti = str(max(1, min(4, os.cpu_count() or 1)))
for _nama in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_nama, _inti)
