@echo off
setlocal
title Create Lords of the Fallen Archipelago Diagnostic Bundle
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0New-LotFDiagnosticBundle.ps1"
if errorlevel 1 pause
endlocal
