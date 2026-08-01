@echo off
setlocal
title Start Lords of the Fallen Archipelago
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-LotF-AP.ps1"
if errorlevel 1 pause
endlocal
