@echo off
echo 正在安装老年人智能出行助手系统依赖...
echo.

REM 安装主要依赖
echo 1. 安装主要依赖
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo 错误: 主要依赖安装失败
    pause
    exit /b 1
)
echo 主要依赖安装成功!
echo.

REM 安装MySQL连接库
echo 2. 确保MySQL连接库正确安装
pip install mysql-connector-python --force-reinstall
if %ERRORLEVEL% neq 0 (
    echo 错误: MySQL连接库安装失败
    pause
    exit /b 1
)
echo MySQL连接库安装成功!
echo.

REM 安装完成
echo 所有依赖安装完成!
echo 你现在可以运行 python run.py 启动系统
echo.
pause 