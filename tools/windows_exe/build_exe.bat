@echo off
setlocal
cd /d "%~dp0\..\.."

powershell -ExecutionPolicy Bypass -File "%~dp0build_exe.ps1"

if errorlevel 1 (
  echo.
  echo Build failed. Please copy the full output back.
  pause
)

