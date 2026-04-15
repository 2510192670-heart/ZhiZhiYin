"""
智知因 - Streamlit生产级前端应用
完整的个性化学习系统界面
"""
import streamlit as st
import requests
import json
import time
from datetime import datetime
from typing import Optional, Dict, List
import uuid

# ========== 页面配置 ==========
st.set_page_config(
    page_title="智知因 - 多智能体个性化学习系统",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "智知因 v1.0 - 基于大模型的多智能体个性化学习系统",
        'Get Help': None,
        'Report a Bug': None
    }
)

# ========== 配置 ==========
API_BASE = "http://localhost:8000"
API_TIMEOUT = 120


# ========== 工具函数 ==========

@st.cache_data(ttl=60)
def check_api_health() -> bool:
    """检查API健康状态"""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def api_call(method: str, endpoint: str, data: dict = None, params: dict = None) -> dict:
    """统一API调用"""
    url = f"{API_BASE}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=API_TIMEOUT)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=API_TIMEOUT)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=API_TIMEOUT)
        elif method == "DELETE":
            response = requests.delete(url, timeout=API_TIMEOUT)
        else:
            return {"error": "不支持的HTTP方法"}

        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "请求超时，请稍后重试"}
    except requests.exceptions.ConnectionError:
        return {"error": "无法连接到服务器，请确保API服务正在运行"}
    except Exception as e:
        return {"error": str(e)}


# ========== 会话状态初始化 ==========

def init_session_state():
    """初始化会话状态"""
    defaults = {
        'user_id': None,
        'user_name': None,
        'student_id': None,
        'profile': None,
        'session_id': None,
        'current_topic': None,
        'messages': [],
        'generated_resource': None,
        'knowledge_gaps': [],
        'learning_history': []
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_session():
    """清除会话状态"""
    for key in list(st.session_state.keys()):
        if key not in ['user_id', 'user_name', 'student_id', 'profile']:
            st.session_state[key] = None if key != 'messages' else []
    st.rerun()


# ========== 页面: 登录/注册 ==========

def show_auth_page():
    """认证页面"""
    col1, col2 = st.columns([1, 1], gap="medium")

    with col1:
        st.title("📚 智知因")
        st.markdown("### 基于大模型的多智能体个性化学习系统")
        st.markdown("---")
        st.markdown("""
        **核心功能**
        - 🎯 Multi-Agent智能协作：诊断→生成→审查→评测
        - 📖 RAG增强学习：基于权威教材的个性化资源
        - 🧠 知识图谱：动态追踪学习进度
        - ⚡ 流式生成：实时获取学习内容
        """)

        st.info("💡 演示账号: 学号 `2024001` 姓名 `张三`")

    with col2:
        tab1, tab2 = st.tabs(["🔐 登录", "📝 注册"])

        with tab1:
            st.subheader("用户登录")
            login_id = st.text_input("学号", placeholder="请输入学号", key="login_id")
            login_name = st.text_input("姓名", placeholder="请输入姓名", key="login_name")

            col_btn1, col_btn2 = st.columns([1, 2])
            with col_btn1:
                submitted = st.button("登录", use_container_width=True, type="primary")

            if submitted:
                if not login_id or not login_name:
                    st.warning("请填写学号和姓名")
                else:
                    result = api_call("POST", "/api/v1/users/login", {
                        "student_id": login_id,
                        "name": login_name
                    })

                    if "error" in result:
                        st.error(f"登录失败: {result['error']}")
                    elif result.get("success"):
                        st.session_state.user_id = result["data"]["user_id"]
                        st.session_state.user_name = result["data"]["name"]
                        st.session_state.student_id = result["data"]["student_id"]
                        st.session_state.profile = result["data"].get("profile", {})
                        st.success("登录成功！")
                        st.rerun()
                    else:
                        st.error("登录失败，请检查学号和姓名")

        with tab2:
            st.subheader("新用户注册")
            reg_id = st.text_input("学号", placeholder="请输入学号", key="reg_id")
            reg_name = st.text_input("姓名", placeholder="请输入姓名", key="reg_name")
            reg_major = st.selectbox(
                "专业",
                ["计算机科学", "软件工程", "数据科学", "人工智能", "其他"],
                key="reg_major"
            )
            reg_grade = st.selectbox(
                "年级",
                ["大一", "大二", "大三", "大四", "研究生"],
                key="reg_grade"
            )

            col_btn1, col_btn2 = st.columns([1, 2])
            with col_btn1:
                submitted = st.button("注册", use_container_width=True, type="primary")

            if submitted:
                if not reg_id or not reg_name:
                    st.warning("请填写学号和姓名")
                else:
                    result = api_call("POST", "/api/v1/users/register", {
                        "student_id": reg_id,
                        "name": reg_name,
                        "major": reg_major,
                        "grade": reg_grade
                    })

                    if "error" in result:
                        st.error(f"注册失败: {result['error']}")
                    elif result.get("success"):
                        st.success("注册成功！请使用新账号登录")
                        st.rerun()
                    else:
                        st.error("注册失败，请重试")


# ========== 页面: 主学习界面 ==========

def show_main_page():
    """主学习页面"""
    # 侧边栏
    with st.sidebar:
        st.header("👤 用户信息")
        if st.session_state.profile:
            profile = st.session_state.profile
            st.write(f"**姓名**: {st.session_state.user_name}")
            st.write(f"**学号**: {st.session_state.student_id}")
            st.write(f"**等级**: {profile.get('level', 1)}")
            st.write(f"**风格**: {profile.get('learning_style', '文本')}")

            mastered = profile.get('mastered_nodes', [])
            if mastered:
                st.write(f"**已掌握**: {len(mastered)} 个知识点")

        st.divider()

        if st.button("🚪 退出登录", use_container_width=True):
            clear_session()
            st.rerun()

        st.divider()

        # 学习历史
        st.subheader("📜 学习历史")
        history = api_call("GET", f"/api/v1/history/{st.session_state.user_id}")
        if "data" in history and history["data"]["history"]:
            for record in history["data"]["history"][:5]:
                with st.expander(f"📚 {record['topic']}"):
                    col_h1, col_h2 = st.columns([1, 1])
                    with col_h1:
                        st.metric("得分", f"{record.get('score', 0):.0%}")
                    with col_h2:
                        st.caption(record.get('timestamp', '')[:10])
        else:
            st.info("暂无学习记录")

    # 主内容区
    st.title("🎓 个性化学习中心")

    # 状态检查
    if not check_api_health():
        st.error("⚠️ 无法连接到后端API服务")
        st.code("启动命令: uvicorn app.api.routes:app --reload --port 8000")
        return

    # 学习会话管理
    if not st.session_state.session_id:
        show_topic_selection()
    else:
        show_learning_interface()


def show_topic_selection():
    """课题选择"""
    st.subheader("选择学习课题")

    col1, col2 = st.columns([2, 1])

    with col1:
        topic = st.text_input(
            "输入学习课题",
            placeholder="例如: Python装饰器、机器学习基础、算法复杂度",
            help="输入你想要学习的课题，系统会自动分析你的知识缺口并生成个性化学习资源"
        )

    with col2:
        st.write("")  # 间距
        st.write("")  # 间距
        if st.button("🚀 开始学习", use_container_width=True, type="primary"):
            if topic:
                start_learning(topic)
            else:
                st.warning("请输入学习课题")

    # 推荐课题
    st.markdown("---")
    st.subheader("💡 推荐课题")

    col_rec1, col_rec2, col_rec3 = st.columns(3)

    recommendations = [
        ("🐍 Python装饰器", "深入理解Python装饰器的原理和应用"),
        ("📊 数据结构", "掌握常见数据结构及其应用场景"),
        ("🤖 机器学习基础", "了解机器学习的核心概念和算法"),
        ("🧮 算法复杂度", "学会分析算法的时间和空间复杂度"),
        ("🔄 递归与迭代", "理解递归和迭代的区别和使用场景"),
        ("📦 面向对象设计", "掌握OOP的核心概念和设计原则")
    ]

    for i, (title, desc) in enumerate(recommendations):
        with [col_rec1, col_rec2, col_rec3][i % 3]:
            if st.button(f"{title}\n\n{desc}", use_container_width=True):
                start_learning(title.split(" ", 1)[1])
                st.rerun()


def start_learning(topic: str):
    """开始学习"""
    with st.spinner("🔍 正在分析学习需求..."):
        # 创建学习会话
        result = api_call("POST", "/api/v1/study/start", {
            "user_id": st.session_state.user_id,
            "topic": topic
        })

        if "error" in result:
            st.error(f"启动失败: {result['error']}")
        elif result.get("session_id"):
            st.session_state.session_id = result["session_id"]
            st.session_state.current_topic = topic
            st.session_state.knowledge_gaps = result.get("knowledge_gaps", [])

            st.success("✅ 学习会话已创建！")
            st.rerun()
        else:
            st.error("创建学习会话失败")


def show_learning_interface():
    """学习界面"""
    st.success(f"📖 当前课题: **{st.session_state.current_topic}**")
    st.caption(f"会话ID: {st.session_state.session_id}")

    # 知识缺口显示
    if st.session_state.knowledge_gaps:
        with st.expander("🔍 识别到的知识缺口", expanded=True):
            gaps_html = ", ".join([f"`{g}`" for g in st.session_state.knowledge_gaps])
            st.markdown(gaps_html)

    st.markdown("---")

    # 学习资源标签页
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 讲义",
        "❓ 练习",
        "🧠 思维导图",
        "📊 进度",
        "💬 评测"
    ])

    with tab1:
        show_lecture_tab()
    with tab2:
        show_practice_tab()
    with tab3:
        show_mindmap_tab()
    with tab4:
        show_progress_tab()
    with tab5:
        show_evaluation_tab()


def show_lecture_tab():
    """讲义标签"""
    st.subheader("个性化学习讲义")

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])

    resource = st.session_state.generated_resource

    with col_btn1:
        generate = st.button("📖 生成讲义", use_container_width=True, type="primary")

    with col_btn2:
        if st.button("🔄 重新生成", use_container_width=True):
            generate = True

    with col_btn3:
        if st.button("➕ 新课题", use_container_width=True):
            st.session_state.session_id = None
            st.session_state.current_topic = None
            st.session_state.generated_resource = None
            st.rerun()

    if generate or resource:
        if not resource:
            with st.spinner("🤖 正在生成学习讲义..."):
                result = generate_resource("lecture")
                if result:
                    st.session_state.generated_resource = result

        if st.session_state.generated_resource:
            content = st.session_state.generated_resource

            st.markdown("---")
            st.markdown(content)


def show_practice_tab():
    """练习标签"""
    st.subheader("针对性练习")

    col1, col2 = st.columns([1, 1])

    with col1:
        topic = st.text_input("练习课题", value=st.session_state.current_topic or "")

    with col2:
        st.write("")  # 间距
        if st.button("🎯 生成练习", use_container_width=True, type="primary"):
            if topic:
                with st.spinner("生成中..."):
                    result = generate_resource("practice")
                    if result:
                        st.session_state.practice_content = result
                        st.rerun()

    if hasattr(st.session_state, 'practice_content') and st.session_state.practice_content:
        st.markdown("---")
        st.markdown(st.session_state.practice_content)


def show_mindmap_tab():
    """思维导图标签"""
    st.subheader("知识结构图")

    if st.button("🗺️ 生成思维导图", type="primary"):
        with st.spinner("生成中..."):
            result = generate_resource("mindmap")
            if result:
                st.session_state.mindmap_content = result
                st.rerun()

    if hasattr(st.session_state, 'mindmap_content') and st.session_state.mindmap_content:
        st.markdown("---")
        st.markdown(st.session_state.mindmap_content)
    else:
        st.info("点击上方按钮生成思维导图")


def show_progress_tab():
    """进度标签"""
    st.subheader("学习进度与成效")

    col1, col2, col3, col4 = st.columns(4)

    profile = st.session_state.profile or {}
    mastered = profile.get('mastered_nodes', [])
    weaknesses = profile.get('weaknesses', [])

    with col1:
        st.metric("学习主题", len(mastered) + 1)
    with col2:
        level = profile.get('level', 1)
        st.metric("当前等级", f"Lv.{level}")
    with col3:
        st.metric("掌握节点", len(mastered))
    with col4:
        st.metric("薄弱环节", len(weaknesses))

    st.markdown("---")

    # 知识掌握图
    st.subheader("📈 知识掌握图谱")

    if mastered:
        st.write("**已掌握知识点:**")
        for node in mastered[:10]:
            st.markdown(f"- ✅ {node}")
    else:
        st.info("暂无已掌握的知识点")

    if weaknesses:
        st.write("**需要加强的知识点:**")
        for node in weaknesses[:5]:
            st.markdown(f"- ⚠️ {node}")


def show_evaluation_tab():
    """评测标签"""
    st.subheader("学习效果评测")

    answer = st.text_area(
        "输入你的答案或理解",
        placeholder="请输入你对当前课题的理解或问题的答案...",
        height=150
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        submit = st.button("📤 提交评测", use_container_width=True, type="primary")

    with col2:
        if st.button("🗑️ 清空", use_container_width=True):
            answer = ""
            st.rerun()

    if submit and answer:
        with st.spinner("🔍 正在评测..."):
            result = api_call("POST", "/api/v1/study/evaluate", {
                "session_id": st.session_state.session_id,
                "student_answer": answer
            })

            if "error" in result:
                st.error(f"评测失败: {result['error']}")
            else:
                st.session_state.evaluation_result = result
                st.rerun()

    if hasattr(st.session_state, 'evaluation_result') and st.session_state.evaluation_result:
        result = st.session_state.evaluation_result

        st.markdown("---")
        st.subheader("📋 评测结果")

        col_res1, col_res2 = st.columns([1, 2])

        with col_res1:
            score = result.get("score", 0)
            st.metric("得分", f"{score:.0%}")

            if result.get("is_correct"):
                st.success("✅ 回答正确！")
            else:
                st.warning("⚠️ 需要改进")

        with col_res2:
            st.markdown("**反馈:**")
            st.info(result.get("feedback", "无"))

        if result.get("knowledge_gaps"):
            st.markdown("**检测到的知识缺口:**")
            for gap in result["knowledge_gaps"]:
                st.markdown(f"- 🔸 {gap}")

        if result.get("next_steps"):
            st.markdown("**下一步建议:**")
            st.success(result["next_steps"])


def generate_resource(mode: str) -> Optional[str]:
    """生成学习资源"""
    try:
        import httpx
        import asyncio

        async def fetch_sse():
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{API_BASE}/api/v1/study/generate",
                    json={
                        "session_id": st.session_state.session_id,
                        "mode": mode
                    },
                    timeout=120.0
                ) as response:
                    content = ""
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            data = line[5:].strip()
                            if data:
                                try:
                                    event_data = json.loads(data)
                                    if event_data.get("phase") == "generated":
                                        resource_data = event_data.get("resource", {})
                                        content = resource_data.get("content", "")
                                        st.session_state.knowledge_gaps = resource_data.get("knowledge_gaps", [])
                                except:
                                    pass
                    return content

        loop = asyncio.new_event_loop()
        content = loop.run_until_complete(fetch_sse())
        return content if content else None

    except Exception as e:
        st.error(f"生成失败: {str(e)}")
        return None


# ========== 主应用 ==========

def main():
    """主应用入口"""
    init_session_state()

    if st.session_state.user_id:
        show_main_page()
    else:
        show_auth_page()


if __name__ == "__main__":
    main()
