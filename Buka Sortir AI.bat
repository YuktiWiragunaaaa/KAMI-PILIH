@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\pythonw.exe (
  rem Python dari Microsoft Store mengunci logo taskbar ke logo Python; sarankan versi python.org.
  py -3.12 -c "import sys; sys.exit('WindowsApps' in sys.base_prefix)" 2>nul || (
    echo PERINGATAN: Python 3.12 yang terpasang berasal dari Microsoft Store.
    echo Aplikasi tetap jalan, tapi logo di taskbar akan tampil sebagai logo Python.
    echo Disarankan: pasang Python 3.12 dari python.org dan hapus versi Microsoft Store.
    echo.
    pause
  )
  echo Menyiapkan Python pertama kali, tunggu beberapa menit...
  py -3.12 -m venv .venv || goto :gagal
  .venv\Scripts\pip install -r requirements.txt || goto :gagal
)
rem Instalasi lama: pasang library yang ditambahkan belakangan (mis. onnxruntime untuk selera visual).
.venv\Scripts\python.exe -c "import onnxruntime" 2>nul || (
  echo Memasang pembaruan library, tunggu sebentar...
  .venv\Scripts\pip install -q -r requirements.txt || goto :gagal
)
start "" .venv\Scripts\pythonw.exe -m sortir_ai
exit /b
:gagal
echo Gagal menyiapkan Python 3.12. Pastikan Python 3.12 terpasang.
pause
