@echo off
REM 智知因 - 快速启动脚本 (Windows)

echo ==========================================
echo   智知因 - 多智能体个性化学习系统
echo ==========================================

REM 检查Python版本
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未检测到Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM 设置变量
set PROJECT_ROOT=%~dp0
cd /d %PROJECT_ROOT%

REM 检查.env文件
if not exist .env (
    if exist .env.example (
        echo .env文件不存在，已从.env.example创建
        copy .env.example .env
        echo 请编辑.env文件填入API密钥
    )
)

REM 创建虚拟环境
if not exist venv (
    echo 创建虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境并安装依赖
echo 安装依赖...
call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

REM 初始化数据
echo 初始化数据...
python -m app.db

echo.
echo ==========================================
echo   启动服务
echo ==========================================
echo.
echo 请在两个终端分别执行:
echo.
echo 终端1 - 启动API服务:
echo   call venv\Scripts\activate
echo   uvicorn app.api.routes:app --reload --port 8000
echo.
echo 终端2 - 启动前端:
echo   call venv\Scripts\activate
echo   streamlit run app/__init__.py --port 8501
echo.
echo 或使用Docker一键启动:
echo   docker-compose up -d
echo.
echo 访问地址:
echo   前端: http://localhost:8501
echo   API文档: http://localhost:8000/docs
echo ==========================================

pause
