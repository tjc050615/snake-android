@echo off
chcp 65001 >nul
title 贪吃蛇 AI 模式启动器
color 0A

echo =========================================
echo       正在启动 贪吃蛇 AI 模式...
echo =========================================
echo.

:: 自动切换到当前 bat 所在的目录
cd /d "%~dp0"

:: 检查并激活虚拟环境
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
    echo [成功] 虚拟环境已激活
) else (
    echo [警告] 未找到虚拟环境 .venv，请检查文件是否完整
)

echo.
echo [启动] 正在打开游戏窗口，请稍候...
echo.

:: 运行游戏并开启 AI 模式
python main.py --ai

echo.
echo =========================================
echo 游戏已退出。
echo 如果上方有报错信息，请截图反馈。
echo =========================================
pause