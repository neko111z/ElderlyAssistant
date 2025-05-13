@echo off
echo 正在启动老年人智能出行助手系统...
echo.

REM 检查docker是否在运行
docker ps >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo 检测到Docker正在运行，尝试使用Docker启动...
    echo.
    
    cd /d "%~dp0"
    docker-compose up -d
    if %ERRORLEVEL% neq 0 (
        echo Docker启动失败，尝试使用Python直接启动...
    ) else (
        echo Docker启动成功! 请访问 http://localhost:8000 使用系统
        echo.
        echo 按任意键退出...
        pause >nul
        exit /b 0
    )
)

REM 直接使用Python启动
echo 使用Python直接启动应用...
echo.

cd /d "%~dp0"
python run.py
if %ERRORLEVEL% neq 0 (
    echo 启动失败! 请查看错误信息。
    echo 可能需要先运行 install_dependencies.bat 安装依赖。
    echo.
    pause
) else (
    echo 应用已成功关闭。
    echo.
    pause
) 