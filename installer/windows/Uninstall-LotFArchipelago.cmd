@echo off
setlocal
title Uninstall Lords of the Fallen Archipelago
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Uninstall-LotFArchipelago.ps1"
if errorlevel 1 pause
endlocal
