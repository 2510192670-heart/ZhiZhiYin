@echo off
chcp 65001 >nul
REM 智知因 - Windows 一键部署脚本

echo ========================================
echo   智知因 - 基于大模型的多智能体学习系统
echo   一键部署脚本 (Windows)
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [✓] 检测到 Python
echo.

REM 创建虚拟环境
echo [1/5] 创建虚拟环境...
if not exist "venv" (
    python -m venv venv
    echo [✓] 虚拟环境创建完成
) else (
    echo [跳过] 虚拟环境已存在
)
echo.

REM 激活虚拟环境并安装依赖
echo [2/5] 安装依赖包...
call venv\Scripts\activate.bat
pip install -r requirements.txt -q
echo [✓] 依赖安装完成
echo.

REM 创建必要的目录
echo [3/5] 创建数据目录...
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "knowledge_base" mkdir knowledge_base
echo [✓] 目录创建完成
echo.

REM 复制环境变量文件
echo [4/5] 配置环境变量...
if not exist ".env" (
    copy .env.example .env
    echo [✓] 已创建 .env 文件，请编辑填入 API Key
) else (
    echo [跳过] .env 文件已存在
)
echo.

REM 启动服务
echo [5/5] 启动服务...
echo.
echo ========================================
echo   启动选项：
echo   1 - 仅启动后端 API (localhost:8000)
echo   2 - 仅启动前端界面 (localhost:8501)
echo   3 - 同时启动前后端
echo   4 - 使用 Docker 部署
echo   0 - 退出
echo ========================================
echo.

set /p choice=请选择 (0-4):

if "%choice%"=="1" goto :start_api
if "%choice%"=="2" goto :start_frontend
if "%choice%"=="3" goto :start_all
if "%choice%"=="4" goto :docker_deploy
if "%choice%"=="0" goto :end

:start_api
echo 正在启动后端 API 服务...
start "智知因 API" cmd /k "venv\Scripts\activate.bat && uvicorn api.routes:app --reload --port 8000"
goto :done

:start_frontend
echo 正在启动前端界面...
start "智知因 前端" cmd /k "venv\Scripts\activate.bat && streamlit run streamlit_app.py"
goto :done

:start_all
echo 正在启动全部服务...
start "智知因 API" cmd /k "venv\Scripts\activate.bat && uvicorn api.routes:app --reload --port 8000"
timeout /t 3 /nobreak >nul
start "智知因 前端" cmd /k "venv\Scripts\activate.bat && streamlit run streamlit_app.py"
goto :done

:docker_deploy
echo 检查 Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Docker，请先安装 Docker Desktop
    pause
    exit /b 1
)

echo 使用 Docker Compose 部署...
docker-compose up -d --build
goto :done

:done
echo.
echo ========================================
echo   启动成功！
echo   API 文档: http://localhost:8000/docs
echo   前端界面: http://localhost:8501
echo ========================================
echo.
echo 按任意键退出...
pause >nul
exit /b 0

:end
echo 已退出
