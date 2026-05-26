@echo off
echo Building World Cup 2026 Sweepstake...

py -3.14 -m pip install --upgrade pip
py -3.14 -m pip install -r requirements.txt

py -3.14 -m PyInstaller --noconfirm ^
  --windowed ^
  --onefile ^
  --name "WorldCupSweepstake" ^
  --add-data "src\sweepstake\web;sweepstake\web" ^
  --add-data "src\sweepstake\storage\schema.sql;sweepstake\storage" ^
  src\sweepstake\__main__.py

echo.
echo Done. Find your .exe in dist\WorldCupSweepstake.exe
pause
