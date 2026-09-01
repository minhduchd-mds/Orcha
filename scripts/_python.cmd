@echo off
setlocal EnableExtensions
set "PY="
where py.exe >nul 2>nul && set "PY=py.exe -3"
if not defined PY where python.exe >nul 2>nul && set "PY=python.exe"
if not defined PY if exist "C:\msys64\mingw64\bin\python.exe" set "PY=C:\msys64\mingw64\bin\python.exe"
if not defined PY if exist "C:\msys64\usr\bin\python.exe" set "PY=C:\msys64\usr\bin\python.exe"
if not defined PY (
  echo Python 3 not found.
  echo Install with: winget install Python.Python.3.12
  exit /b 1
)
%PY% %*
exit /b %ERRORLEVEL%
