"""
智知因 - Streamlit 前端界面
基于大模型的多智能体个性化学习系统
"""
import streamlit as st
import requests
import json
import time
from datetime import datetime

# ============ 配置 ============

API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="智知因 - 个性化学习系统",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #4A90D9;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border-left: 4px solid #4A90D9;
    }
    .success-card {
        border-left-color: #28a745;
    }
    .warning-card {
        border-left-color: #ffc107;
    }
    .metric-card {
        background-color: #e9ecef;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap-gap: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ============ 辅助函数 ============

def api_request(method, endpoint, data=None):
    """API 请求封装"""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        else:
            return None, f"不支持的方法: {method}"

        if response.status_code in [200, 201]:
            return response.json(), None
        else:
            return None, f"请求失败: {response.status_code} - {response.text}"
    except requests.exceptions.ConnectionError:
        return None, "无法连接到后端服务，请确保 FastAPI 服务已启动"
    except Exception as e:
        return None, str(e)


def check_backend():
    """检查后端连接"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            return True
    except:
        pass
    return False


# ============ 页面组件 ============

def render_header():
    """渲染页头"""
    st.markdown('<p class="main-header">🎓 智知因</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">基于大模型的多智能体个性化学习系统</p>', unsafe_allow_html=True)


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.title("📚 功能导航")

        # 状态检查
        if check_backend():
            st.success("✅ 后端服务已连接")
        else:
            st.error("⚠️ 后端服务未连接")
            st.info("请运行: `uvicorn api.routes:app --reload`")

        st.divider()

        # 功能菜单
        page = st.radio(
            "选择功能",
            ["🏠 首页", "📝 开始学习", "📊 学习报告", "📖 知识库", "👤 个人中心"],
            index=0
        )

        st.divider()

        # 系统信息
        st.caption(f"版本: 1.0.0")
        st.caption(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        return page


def render_home():
    """首页"""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("📚 知识库", "持续更新中", "多学科覆盖")

    with col2:
        st.metric("🎯 智能诊断", "精准定位", "知识缺口")

    with col3:
        st.metric("🤖 AI 生成", "个性化内容", "难度适配")

    st.divider()

    # 功能介绍
    st.subheader("🚀 核心能力")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### 📊 多 Agent 协作
        - **诊断Agent** - 分析学习记录，定位知识缺口
        - **生成Agent** - 调用 RAG 知识库，生成个性化内容
        - **反思Agent** - 自动校验内容质量，确保准确性
        - **评估Agent** - 评估学习效果，持续优化画像
        """)

    with col2:
        st.markdown("""
        ### 📖 RAG 知识库
        - 支持上传教材 PDF
        - 向量检索，精准匹配
        - 术语准确，内容权威

        ### 🎚️ 难度自适应
        - 基础 - 适合初学者
        - 进阶 - 适合有一定基础
        - 拓展 - 适合深入研究
        """)

    # 快速开始
    st.divider()
    st.subheader("⚡ 快速开始")

    if st.button("🎯 开始个性化学习", type="primary", use_container_width=True):
        st.session_state.page = "📝 开始学习"
        st.rerun()


def render_learning():
    """学习页面"""
    st.subheader("📝 开始学习")

    # 用户输入
    col1, col2 = st.columns([3, 1])

    with col1:
        topic = st.text_input(
            "学习主题",
            placeholder="例如：Python 列表操作、牛顿运动定律",
            help="输入你想要学习的主题"
        )

    with col2:
        difficulty = st.selectbox(
            "难度选择",
            ["基础", "进阶", "拓展"],
            index=0
        )

    # 已有知识缺口
    use_existing = st.checkbox("使用已有知识缺口", value=False)

    if use_existing:
        gaps = st.text_area(
            "知识缺口（逗号分隔）",
            placeholder="例如：列表推导式, 切片操作, 列表方法",
            help="输入已诊断出的知识缺口"
        )
        knowledge_gaps = [g.strip() for g in gaps.split(",") if g.strip()] if gaps else None
    else:
        knowledge_gaps = None

    # 开始学习按钮
    if st.button("🚀 开始学习", type="primary", use_container_width=True):
        if not topic:
            st.warning("请输入学习主题")
        else:
            with st.spinner("正在分析并生成学习内容..."):
                # 创建会话
                result, error = api_request("POST", "/api/users", {
                    "username": f"user_{int(time.time())}"
                })

                if error:
                    st.error(f"创建用户失败: {error}")
                    return

                user_id = result["user_id"]

                # 生成内容
                result, error = api_request("POST", "/api/generate", {
                    "user_id": user_id,
                    "topic": topic,
                    "difficulty": difficulty,
                    "knowledge_gaps": knowledge_gaps
                })

                if error:
                    st.error(f"生成失败: {error}")
                    return

                # 渲染学习内容
                render_learning_content(result)


def render_learning_content(content: dict):
    """渲染学习内容"""
    st.divider()
    st.success("✅ 学习内容生成完成！")

    # 讲义
    st.subheader("📖 讲义内容")
    lecture = content.get("lecture", {})

    if lecture:
        st.markdown(f"### {lecture.get('title', '讲义')}")

        for section in lecture.get("sections", []):
            with st.expander(f"📌 {section.get('heading', '章节')}", expanded=True):
                st.markdown(section.get("content", ""))
                if section.get("key_points"):
                    st.info("**重点:** " + " | ".join(section["key_points"]))
    else:
        st.info("讲义内容加载中...")

    # 练习题
    st.divider()
    st.subheader("✏️ 练习题目")

    exercises = content.get("exercises", [])
    if not exercises:
        st.info("暂无练习题")
        return

    # 答题表单
    answers = {}

    for i, ex in enumerate(exercises):
        with st.container():
            st.markdown(f"**{i+1}. [{ex.get('type', '题目')}]** {ex.get('question', '')}")

            if ex.get("options"):
                answer_key = f"q_{i}"
                answers[answer_key] = st.radio(
                    "选择答案",
                    ex["options"],
                    key=answer_key,
                    index=None
                )

            st.divider()

    # 提交答案
    if st.button("📤 提交答案", type="primary"):
        st.info("答案已记录，可查看下方解析")


def render_reports():
    """学习报告页面"""
    st.subheader("📊 学习报告")

    # 统计数据
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("本周学习", "5", "📈 +2")

    with col2:
        st.metric("完成题目", "42", "正确率 85%")

    with col3:
        st.metric("学习时长", "3.5h", "⏱️")

    with col4:
        st.metric("知识掌握", "78%", "📈 +5%")

    st.divider()

    # 学习历史
    st.subheader("📜 学习历史")

    history_data = [
        {"时间": "2024-01-15 14:30", "主题": "Python 列表操作", "难度": "基础", "正确率": "85%", "状态": "✅ 完成"},
        {"时间": "2024-01-14 16:00", "主题": "牛顿第二定律", "难度": "进阶", "正确率": "72%", "状态": "✅ 完成"},
        {"时间": "2024-01-13 10:00", "主题": "光的折射", "难度": "基础", "正确率": "90%", "状态": "✅ 完成"},
    ]

    st.dataframe(history_data, use_container_width=True)


def render_knowledge_base():
    """知识库页面"""
    st.subheader("📖 RAG 知识库管理")

    tab1, tab2 = st.tabs(["📤 上传文档", "🔍 搜索知识"])

    with tab1:
        st.markdown("### 上传教材文档")
        st.info("支持 PDF、TXT 格式的教材或讲义")

        uploaded_file = st.file_uploader(
            "选择文件",
            type=["pdf", "txt"],
            help="上传后将自动分块并索引到知识库"
        )

        if uploaded_file:
            st.success(f"已选择: {uploaded_file.name}")
            if st.button("📤 上传到知识库", type="primary"):
                with st.spinner("正在处理..."):
                    st.info("文件上传功能开发中...")
                    st.success("功能开发中，敬请期待！")

    with tab2:
        st.markdown("### 搜索知识")
        query = st.text_input("输入关键词搜索", placeholder="例如：列表推导式")

        if st.button("🔍 搜索", type="secondary"):
            if query:
                st.info(f"搜索: {query}")
                st.success("搜索功能开发中，敬请期待！")


def render_profile():
    """个人中心"""
    st.subheader("👤 个人中心")

    # 用户信息
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("""
        <div class="card">
            <h3>👤 用户信息</h3>
            <p><strong>用户名:</strong> student_001</p>
            <p><strong>注册时间:</strong> 2024-01-01</p>
            <p><strong>学习等级:</strong> 🌟 进阶学习者</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="card">
            <h3>📊 学习统计</h3>
            <p>累计学习: <strong>45</strong> 次</p>
            <p>总学习时长: <strong>12.5</strong> 小时</p>
            <p>平均正确率: <strong>82%</strong></p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # 知识掌握度
    st.subheader("🧠 知识掌握情况")

    knowledge_data = {
        "Python 基础": 0.9,
        "列表操作": 0.85,
        "函数定义": 0.75,
        "字典操作": 0.6,
        "面向对象": 0.45,
    }

    for topic, mastery in knowledge_data.items():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.progress(mastery, text=f"{topic}: {mastery*100:.0f}%")
        with col2:
            status = "✅" if mastery > 0.7 else "📈" if mastery > 0.5 else "⚠️"
            st.write(f"{status} {'已掌握' if mastery > 0.7 else '学习中' if mastery > 0.5 else '待加强'}")


# ============ 主函数 ============

def main():
    """主函数"""
    # 初始化 session_state
    if "page" not in st.session_state:
        st.session_state.page = "🏠 首页"

    # 渲染
    render_header()
    page = render_sidebar()

    # 根据页面选择渲染
    if page == "🏠 首页":
        render_home()
    elif page == "📝 开始学习":
        render_learning()
    elif page == "📊 学习报告":
        render_reports()
    elif page == "📖 知识库":
        render_knowledge_base()
    elif page == "👤 个人中心":
        render_profile()


if __name__ == "__main__":
    main()
