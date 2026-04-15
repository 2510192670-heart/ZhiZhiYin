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
    import argparse

    parser = argparse.ArgumentParser(description=settings.APP_NAME)
    parser.add_argument("--mode", "-m", choices=["api", "frontend", "all"],
                       default="all", help="运行模式: api(仅API) / frontend(仅前端) / all(全部)")
    args = parser.parse_args()

    logger.info(f"启动 {settings.APP_NAME} {settings.APP_VERSION} (模式: {args.mode})")

    if args.mode == "api":
        # 仅启动 API
        uvicorn.run(
            "api.routes:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
        )
    elif args.mode == "frontend":
        # 仅启动前端
        import subprocess
        subprocess.run([
            "streamlit", "run", "streamlit_app.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0"
        ])
    else:
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

        logger.info("API: http://localhost:8000")
        logger.info("前端: http://localhost:8501")

        p1.join()
        p2.join()


if __name__ == "__main__":
    main()
