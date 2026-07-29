@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo === Slay the Spire 观者点穴+ 开局 ===

where py >nul 2>nul
if %errorlevel%==0 (
  set PY=py -3
) else (
  set PY=python
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] 创建虚拟环境 .venv ...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo 创建 venv 失败。请确认已安装 Python 3.10+ 并勾选 "Add to PATH"。
    pause
    exit /b 1
  )
)

echo [2/3] 安装依赖 ...
".venv\Scripts\python.exe" -m pip install -U pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements-pc.txt
if errorlevel 1 (
  echo 依赖安装失败。
  pause
  exit /b 1
)

echo.
echo 请先确保：
echo   1. Steam 版杀戮尖塔已安装
echo   2. 游戏里已选观者并开始新游戏（到 Neow 或能 Continue 的界面）
echo   3. 游戏已完全关闭
echo.
pause

echo [3/3] 修改观者存档：Strike -^> 点穴+ ...
".venv\Scripts\python.exe" start_watcher_pressure_run.py %*
set ERR=%errorlevel%
echo.
if %ERR%==0 (
  echo 完成。现在打开游戏点 Continue 即可。
) else (
  echo 失败，错误码 %ERR%。可尝试：
  echo   run_watcher_pressure.bat --game-root "你的SlayTheSpire路径"
  echo   run_watcher_pressure.bat --save "完整路径\WATCHER.autosave"
)
pause
exit /b %ERR%
