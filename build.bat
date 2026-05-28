@echo off
echo Building World Cup 2026 Sweepstake...

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m PyInstaller --noconfirm ^
  --windowed ^
  --onefile ^
  --name "WorldCupSweepstake" ^
  --add-data "src\sweepstake\web;web" ^
  --add-data "src\sweepstake\storage\schema.sql;sweepstake\storage" ^
  src\sweepstake\__main__.py

echo.
echo Done. Find your .exe in dist\WorldCupSweepstake.exe
pause
