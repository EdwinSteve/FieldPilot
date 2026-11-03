@echo off
rem Double-click to run the whole planner pipeline (see train_windows.ps1).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0train_windows.ps1" %*
pause
