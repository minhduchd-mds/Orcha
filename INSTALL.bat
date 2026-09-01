@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title KimiK3-Lite Desktop Studio Setup

set "MISSING=0"
where ollama.exe >nul 2>nul
if errorlevel 1 (
  echo [!] Ollama chua duoc cai.
  where winget.exe >nul 2>nul
  if errorlevel 1 (
    echo     Cai Ollama tu https://ollama.com/download
    set "MISSING=1"
  ) else (
    winget install --id Ollama.Ollama -e --accept-package-agreements --accept-source-agreements
    set "MISSING=1"
  )
) else echo [OK] Ollama

where py.exe >nul 2>nul
if errorlevel 1 where python.exe >nul 2>nul
if errorlevel 1 if not exist "C:\msys64\mingw64\bin\python.exe" (
  echo [!] Python 3 chua duoc cai.
  where winget.exe >nul 2>nul
  if errorlevel 1 (
    echo     Cai Python 3.10+ tu https://python.org
    set "MISSING=1"
  ) else (
    winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
    set "MISSING=1"
  )
) else echo [OK] Python 3

if "%MISSING%"=="1" (
  echo Neu vua cai dependency, hay dong cua so nay va mo INSTALL.bat lan nua.
  pause
  exit /b 0
)

cscript //nologo "%~dp0Create Desktop Shortcut.vbs" >nul 2>nul
echo [OK] Moi truong da san sang. Model se duoc cai trong giao dien Studio.
start "" wscript.exe "%~dp0KimiK3 Studio.vbs"
exit /b 0
