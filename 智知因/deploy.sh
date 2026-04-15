#!/bin/bash
# 智知因 - Linux/Mac 一键部署脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   智知因 - 基于大模型的多智能体学习系统${NC}"
echo -e "${GREEN}   一键部署脚本 (Linux/Mac)${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[错误] 未检测到 Python，请先安装 Python 3.10+${NC}"
    echo "下载地址: https://www.python.org/downloads/"
    exit 1
fi

echo -e "${GREEN}[✓] 检测到 Python$(python3 --version)${NC}"
echo ""

# 创建虚拟环境
echo -e "${YELLOW}[1/5] 创建虚拟环境...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}[✓] 虚拟环境创建完成${NC}"
else
    echo -e "${GREEN}[跳过] 虚拟环境已存在${NC}"
fi
echo ""

# 安装依赖
echo -e "${YELLOW}[2/5] 安装依赖包...${NC}"
source venv/bin/activate
pip install -r requirements.txt -q
echo -e "${GREEN}[✓] 依赖安装完成${NC}"
echo ""

# 创建目录
echo -e "${YELLOW}[3/5] 创建数据目录...${NC}"
mkdir -p data logs knowledge_base
echo -e "${GREEN}[✓] 目录创建完成${NC}"
echo ""

# 配置环境变量
echo -e "${YELLOW}[4/5] 配置环境变量...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}[✓] 已创建 .env 文件，请编辑填入 API Key${NC}"
else
    echo -e "${GREEN}[跳过] .env 文件已存在${NC}"
fi
echo ""

# 启动服务
echo -e "${YELLOW}[5/5] 启动服务...${NC}"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "启动选项："
echo -e "1 - 仅启动后端 API (localhost:8000)"
echo -e "2 - 仅启动前端界面 (localhost:8501)"
echo -e "3 - 同时启动前后端"
echo -e "4 - 使用 Docker 部署"
echo -e "0 - 退出"
echo -e "${GREEN}========================================${NC}"
echo ""

read -p "请选择 (0-4): " choice

case $choice in
    1)
        echo -e "${GREEN}正在启动后端 API 服务...${NC}"
        uvicorn api.routes:app --reload --port 8000 &
        ;;
    2)
        echo -e "${GREEN}正在启动前端界面...${NC}"
        streamlit run streamlit_app.py --server.port 8501 &
        ;;
    3)
        echo -e "${GREEN}正在启动全部服务...${NC}"
        uvicorn api.routes:app --reload --port 8000 &
        sleep 3
        streamlit run streamlit_app.py --server.port 8501 &
        ;;
    4)
        echo -e "${GREEN}使用 Docker Compose 部署...${NC}"
        if ! command -v docker &> /dev/null; then
            echo -e "${RED}[错误] 未检测到 Docker${NC}"
            exit 1
        fi
        docker-compose up -d --build
        ;;
    0)
        echo "已退出"
        exit 0
        ;;
esac

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "启动成功！"
echo -e "API 文档: http://localhost:8000/docs"
echo -e "前端界面: http://localhost:8501"
echo -e "${GREEN}========================================${NC}"
