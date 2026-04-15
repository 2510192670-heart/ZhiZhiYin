#!/bin/bash
# 智知因 - 快速启动脚本

set -e

echo "=========================================="
echo "  智知因 - 多智能体个性化学习系统"
echo "=========================================="

# 检查Python版本
python_version=$(python --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.10"
if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "错误: 需要 Python 3.10+，当前版本: $python_version"
    exit 1
fi
echo "✓ Python版本检查通过: $python_version"

# 检查.env文件
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "⚠ .env文件不存在，已从.env.example创建"
        cp .env.example .env
        echo "请编辑.env文件填入API密钥"
    fi
fi

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python -m venv venv
    echo "✓ 虚拟环境创建完成"
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ 依赖安装完成"

# 初始化数据
echo "初始化数据..."
python -m app.db
echo "✓ 数据初始化完成"

echo ""
echo "=========================================="
echo "  启动服务"
echo "=========================================="
echo ""
echo "请在两个终端分别执行:"
echo ""
echo "终端1 - 启动API服务:"
echo "  source venv/bin/activate"
echo "  uvicorn app.api.routes:app --reload --port 8000"
echo ""
echo "终端2 - 启动前端:"
echo "  source venv/bin/activate"
echo "  streamlit run app/__init__.py --port 8501"
echo ""
echo "或使用Docker一键启动:"
echo "  docker-compose up -d"
echo ""
echo "访问地址:"
echo "  前端: http://localhost:8501"
echo "  API文档: http://localhost:8000/docs"
echo "=========================================="
