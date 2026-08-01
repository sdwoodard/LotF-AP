@echo off
setlocal
title Lords of the Fallen Archipelago Installer
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-LotFArchipelago.ps1"
if errorlevel 1 pause
endlocal
