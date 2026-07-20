@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动 Ai ...
"C:\Users\30974\Downloads\renpy-8.5.3-sdk\renpy.exe" "%~dp0."
if errorlevel 1 pause
