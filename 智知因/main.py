"""
智知因 - 主程序入口
快速启动开发服务器
"""
import uvicorn
import streamlit as st
from loguru import logger

from config import settings


def main():
    """主函数"""
    logger.info(f"启动 {settings.APP_NAME} {settings.APP_VERSION}")

    # 选择运行模式
    mode = input("选择运行模式 (1: API / 2: Frontend / 3: All): ").strip()

    if mode == "1":
        # 仅启动 API
        uvicorn.run(
            "api.routes:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
        )
    elif mode == "2":
        # 仅启动前端
        import subprocess
        subprocess.run([
            "streamlit", "run", "streamlit_app.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0"
        ])
    elif mode == "3":
        # 全部启动
        import multiprocessing

        def run_api():
            uvicorn.run(
                "api.routes:app",
                host="0.0.0.0",
                port=8000,
                reload=False,
            )

        def run_frontend():
            import subprocess
            subprocess.run([
                "streamlit", "run", "streamlit_app.py",
                "--server.port", "8501",
                "--server.address", "0.0.0.0"
            ])

        # 启动两个进程
        p1 = multiprocessing.Process(target=run_api)
        p2 = multiprocessing.Process(target=run_frontend)

        p1.start()
        p2.start()

        p1.join()
        p2.join()
    else:
        logger.error("无效的选择")


if __name__ == "__main__":
    main()
