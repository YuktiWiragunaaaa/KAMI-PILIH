@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\pythonw.exe (
  echo Menyiapkan Python pertama kali, tunggu beberapa menit...
  py -3.12 -m venv .venv || goto :gagal
  .venv\Scripts\pip install -r requirements.txt || goto :gagal
)
start "" .venv\Scripts\pythonw.exe -m sortir_ai
exit /b
:gagal
echo Gagal menyiapkan Python 3.12. Pastikan Python 3.12 terpasang.
pause
